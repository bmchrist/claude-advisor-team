#!/usr/bin/env python3
"""Deterministic bookkeeping for one-shot pipeline runs.

The /run-analysis orchestrator (Phase 4) is a loop: launch what `next`
says, and when a stage reports back, run `check` and `finish`. Everything
stateful lives here and in analyses/{slug}/.run.json, so a run can be
resumed after the session dies.

All paths are absolute (resolved from this file's location), so a stray
`cd` in the session can't break anything. Output is plain `key: value`
lines like resolve_target.py. A line starting `ERROR:` means stop and report
it verbatim; `WARNING:` is informational.

Subcommands:
  preflight <company> <type> [source]
      Validate a new run without writing anything: company isn't a path,
      type is valid, source exists and has files, and the slug has no
      existing analysis. Prints slug and passes through the resolver's
      near-miss WARNING.
  init <company> <type> [source]
      Run preflight, then create analyses/{slug}/.run.json (the stage list
      includes `ingest` only when a source is given). Does not write .meta;
      /research does that.
  next <slug>
      Stages ready to launch: pending, or failed with one attempt (the
      single retry), with all dependencies complete. Prints `ready:`, plus
      `running:`, `blocked:` (a stage failed twice) or `done: true`.
  start <slug> <stage>
      Mark running, bump attempts, stamp started_at.
  finish <slug> <stage> ok|fail
      `ok` re-runs `check` first and records `fail` instead if the outputs
      aren't complete. Stamps finished_at.
  check <slug> <stage>
      Validate outputs: `check: complete|incomplete|missing`, `notion:
      synced|missing|n/a`, and `detail:` lines for each problem.
  status <slug>
      One-screen table for humans and for resume. Works on analyses with no
      .run.json (derived from files alone).
  prior-run <slug>
      For /research's Setup. Prints the base snapshot's RC path and the
      NEW/CHANGED materials list when .run.json marks a re-run in progress,
      else `prior-run: none`. (Snapshots arrive in Phase 5.)

Stage graph:
  ingest? -> research -> {science, investment, political} -> bull -> bear
  -> executive -> notion-catchup
"""
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSES = os.path.join(ROOT, "analyses")
VALID_TYPES = {"DEAL", "TECHNOLOGY", "POLICY"}
GRADES = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"}  # Notion select options
STATUSES = {"INVEST", "TRACK", "INVESTIGATE", "PASS"}
MAX_ATTEMPTS = 2

# stage -> (deps, [(relative file, start marker, end marker)], .notion keys)
STAGES = {
    "ingest": ([], [], []),
    "research": (["ingest"], [
        ("01_research_collector_full.md", "[RC_FULL_START]", "[RC_FULL_END]"),
        ("01_research_collector_summary.md", "[RC_SUMMARY_START]", "[RC_SUMMARY_END]"),
    ], ["main_page_id", "stage1_page_id"]),
    "science": (["research"], [
        ("02a_science_advisor_full.md", "[ANALYSIS_START]", "[ANALYSIS_END]"),
        ("02a_science_advisor_summary.md", "[SUMMARY_START]", "[SUMMARY_END]"),
    ], ["stage2a_page_id"]),
    "investment": (["research"], [
        ("02b_investment_advisor_full.md", "[ANALYSIS_START]", "[ANALYSIS_END]"),
        ("02b_investment_advisor_summary.md", "[SUMMARY_START]", "[SUMMARY_END]"),
    ], ["stage2b_page_id"]),
    "political": (["research"], [
        ("02c_political_advisor_full.md", "[ANALYSIS_START]", "[ANALYSIS_END]"),
        ("02c_political_advisor_summary.md", "[SUMMARY_START]", "[SUMMARY_END]"),
    ], ["stage2c_page_id"]),
    "bull": (["science", "investment", "political"], [
        ("03_bull_full.md", "[BULL_START]", "[BULL_END]"),
    ], ["stage3_page_id"]),
    "bear": (["bull"], [
        ("04_bear_full.md", "[BEAR_START]", "[BEAR_END]"),
    ], ["stage4_page_id"]),
    "executive": (["bear"], [
        ("05_executive_report.md", "[REPORT_START]", "[REPORT_END]"),
    ], ["main_page_id"]),
    "notion-catchup": (["executive"], [], []),
}
ORDER = list(STAGES)
# skill invoked for each stage (for the orchestrator)
SKILL = {"ingest": "ingest-materials", "research": "research", "science": "science",
         "investment": "investment-advisor", "political": "political", "bull": "bull",
         "bear": "bear", "executive": "executive", "notion-catchup": "notion-sync"}
# the .notion keys every stage page needs, for notion-catchup's check
ALL_NOTION_KEYS = ["main_page_id", "stage1_page_id", "stage2a_page_id", "stage2b_page_id",
                   "stage2c_page_id", "stage3_page_id", "stage4_page_id"]


# --- helpers -----------------------------------------------------------------

def out(**kv):
    for k, v in kv.items():
        print(f"{k.replace('_', '-')}: {v}")


def fail(msg):
    print(f"ERROR: {msg}")
    sys.exit(0)  # same convention as resolve_target.py: callers read the ERROR line


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def adir(slug):
    return os.path.join(ANALYSES, slug)


def run_path(slug):
    return os.path.join(adir(slug), ".run.json")


def load_run(slug, required=True):
    p = run_path(slug)
    if not os.path.exists(p):
        if required:
            fail(f"no run state at analyses/{slug}/.run.json — start with /run-analysis")
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_run(slug, run):
    d = adir(slug)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".run.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2)
        f.write("\n")
    os.replace(tmp, run_path(slug))


def read_kv(path):
    kv = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            m = re.match(r'^\s*([A-Za-z0-9_]+)\s*=\s*"?(.*?)"?\s*$', line)
            if m:
                kv[m.group(1)] = m.group(2)
    return kv


def stage_arg(s):
    if s not in STAGES:
        fail(f"unknown stage '{s}' (expected one of: {', '.join(ORDER)})")
    return s


def slug_arg(slug):
    if not re.match(r"^[a-z0-9_]+$", slug or ""):
        fail(f"invalid slug '{slug}'")
    return slug


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint():
    files = sorted(glob.glob(os.path.join(ROOT, ".claude", "skills", "**", "*.md"), recursive=True))
    files.append(os.path.join(ROOT, "CLAUDE.md"))
    fp = {os.path.relpath(p, ROOT): sha256_file(p) for p in files if os.path.exists(p)}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", ".claude", "CLAUDE.md"],
                                    cwd=ROOT, capture_output=True, text=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {"git_commit": commit, "uncommitted_prompt_edits": dirty, "files": fp}


# --- validation --------------------------------------------------------------

def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            v = m.group(2).strip()
            if v.startswith('"'):
                try:
                    v = json.loads(v)
                except json.JSONDecodeError:
                    pass
            fm[m.group(1)] = v
    return None


def check_ingest(slug, issues, present):
    md = os.path.join(adir(slug), "00_deal_materials")
    for name in ("materials_digest.md", "manifest.md"):
        p = os.path.join(md, name)
        if os.path.exists(p):
            present.append(p)
        else:
            issues.append(f"00_deal_materials/{name} missing")
    man = os.path.join(md, "manifest.md")
    if os.path.exists(man):
        for line in open(man, encoding="utf-8"):
            m = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
            if m and not os.path.exists(os.path.join(md, m.group(1))):
                issues.append(f"manifest path does not resolve: {m.group(1)}")


def check_stage(slug, stage, run=None):
    """Return (state, issues, notion_state). state: complete|incomplete|missing."""
    _, files, keys = STAGES[stage]
    issues, present = [], []
    started = None
    if run:
        started = run["stages"].get(stage, {}).get("started_epoch")

    if stage == "ingest":
        check_ingest(slug, issues, present)
    elif stage == "notion-catchup":
        notion = read_kv(os.path.join(adir(slug), ".notion"))
        missing = [k for k in ALL_NOTION_KEYS if not notion.get(k)]
        state = "complete" if not missing else "incomplete"
        return state, [f".notion missing {k}" for k in missing], "synced" if not missing else "missing"
    for rel, start, end in files:
        p = os.path.join(adir(slug), rel)
        if not os.path.exists(p):
            issues.append(f"{rel} missing")
            continue
        present.append(p)
        text = open(p, encoding="utf-8").read()
        for marker in (start, end):
            if not re.search(r"^" + re.escape(marker) + r"\s*$", text, re.M):
                issues.append(f"{rel} lacks {marker}")
        if stage == "executive":
            fm = parse_frontmatter(text)
            if fm is None:
                issues.append(f"{rel} has no YAML frontmatter")
            else:
                if fm.get("grade") not in GRADES:
                    issues.append(f"{rel} frontmatter grade {fm.get('grade')!r} is not a Notion grade option")
                if fm.get("status") not in STATUSES:
                    issues.append(f"{rel} frontmatter status {fm.get('status')!r} is invalid")
    if started:
        for p in present:
            if os.path.getmtime(p) < started:
                issues.append(f"{os.path.relpath(p, adir(slug))} is older than this stage's start (stale output from an earlier run)")

    expected = len(files) if stage != "ingest" else 2
    if not present:
        state = "missing"
    elif issues:
        state = "incomplete"
    else:
        state = "complete"
    if present and len(present) < expected and state == "complete":
        state = "incomplete"

    if not keys:
        nstate = "n/a"
    else:
        notion = read_kv(os.path.join(adir(slug), ".notion"))
        nstate = "synced" if all(notion.get(k) for k in keys) else "missing"
    return state, issues, nstate


# --- subcommands -------------------------------------------------------------

def preflight(company, type_, source=None, quiet=False):
    company = (company or "").strip()
    if not company:
        fail("company name is empty")
    expanded = os.path.expanduser(company)
    if "/" in company or company.startswith("~") or os.path.exists(expanded):
        fail(f"'{company}' looks like a path, not a company name. Usage: "
             f"/run-analysis \"Company\" TYPE [materials-path]")
    t = (type_ or "").strip().strip("'\"").upper()
    if t not in VALID_TYPES:
        fail(f"invalid type '{type_}' — expected DEAL|TECHNOLOGY|POLICY")
    src = None
    if source:
        src = os.path.abspath(os.path.expanduser(source))
        if not os.path.exists(src):
            fail(f"materials path does not exist: {src}")
        if os.path.isdir(src):
            n = sum(1 for _, _, fs in os.walk(src) for f in fs if not f.startswith("."))
            if n == 0:
                fail(f"materials path has no files: {src}")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "resolve_target.py"),
                        "--slug-only", company], cwd=ROOT, capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    err = [l for l in lines if l.startswith("ERROR:")]
    if err:
        print(err[0])
        sys.exit(0)
    slug = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("slug:")), None)
    if not slug:
        fail(f"resolver returned no slug: {r.stdout.strip() or r.stderr.strip()}")
    warnings = [l for l in lines if l.startswith("WARNING:")]
    d = adir(slug)
    existing_run = load_run(slug, required=False)
    unfinished = bool(existing_run) and any(
        i["status"] != "complete" for i in existing_run["stages"].values())
    if unfinished:
        fail(f"analyses/{slug} has an unfinished run. Use /run-analysis resume {slug}")
    if os.path.exists(os.path.join(d, ".meta")):
        fail(f"analyses/{slug} already exists. Use /rerun-analysis \"{company}\" to re-run it")
    if existing_run:
        fail(f"analyses/{slug} has an unfinished run (.run.json, no .meta yet). "
             f"Use /run-analysis resume {slug}")
    if not quiet:
        out(slug=slug, company=company, type=t, source=src or "none")
        for w in warnings:
            print(w)
    return slug, company, t, src, warnings


def cmd_init(company, type_, source=None):
    slug, company, t, src, warnings = preflight(company, type_, source, quiet=True)
    os.makedirs(adir(slug), exist_ok=True)
    stages = [s for s in ORDER if s != "ingest" or src]
    run = {
        "slug": slug, "company": company, "type": t, "source": src,
        "mode": "run", "rerun_in_progress": False, "prior_run": None,
        "created": now_iso(),
        "stages": {s: {"status": "pending", "attempts": 0, "started": None,
                       "started_epoch": None, "finished": None, "finished_epoch": None}
                   for s in stages},
        "materials": {},
        "fingerprint": fingerprint(),
    }
    save_run(slug, run)
    out(slug=slug, company=company, type=t, source=src or "none", stages=" ".join(stages))
    for w in warnings:
        print(w)


def deps_done(run, stage):
    for d in STAGES[stage][0]:
        if d in run["stages"] and run["stages"][d]["status"] != "complete":
            return False
    return True


def cmd_next(slug):
    run = load_run(slug)
    st = run["stages"]
    ready, running, blocked = [], [], []
    for s in ORDER:
        if s not in st:
            continue
        info = st[s]
        if info["status"] == "running":
            running.append(s)
        elif info["status"] == "failed" and info["attempts"] >= MAX_ATTEMPTS:
            blocked.append(s)
        elif info["status"] in ("pending", "failed") and deps_done(run, s):
            ready.append(s)
    if all(i["status"] == "complete" for i in st.values()):
        out(ready="none", done="true")
        return
    if blocked:
        # a second failure stops the pipeline: launch nothing new, so nothing
        # downstream runs with a gap
        out(ready="none", running=" ".join(running) or "none", blocked=" ".join(blocked))
        print(f"ERROR: stage {blocked[0]} failed {MAX_ATTEMPTS} times; pipeline stopped. "
              f"Fix the cause, then /run-analysis resume {slug}")
        return
    out(ready=" ".join(f"{s}({SKILL[s]})" for s in ready) or "none",
        running=" ".join(running) or "none")


def cmd_start(slug, stage):
    run = load_run(slug)
    info = run["stages"].get(stage)
    if info is None:
        fail(f"stage {stage} is not part of this run")
    if info["status"] == "running":
        fail(f"stage {stage} is already running — never launch a stage twice")
    if info["status"] == "complete":
        fail(f"stage {stage} is already complete")
    if info["attempts"] >= MAX_ATTEMPTS:
        fail(f"stage {stage} has used its {MAX_ATTEMPTS} attempts")
    if not deps_done(run, stage):
        fail(f"stage {stage} has incomplete dependencies")
    info.update(status="running", attempts=info["attempts"] + 1,
                started=now_iso(), started_epoch=time.time(), finished=None, finished_epoch=None)
    save_run(slug, run)
    out(stage=stage, status="running", attempt=info["attempts"], skill=SKILL[stage])


def cmd_finish(slug, stage, result):
    if result not in ("ok", "fail"):
        fail("finish result must be ok or fail")
    run = load_run(slug)
    info = run["stages"].get(stage)
    if info is None:
        fail(f"stage {stage} is not part of this run")
    state, issues, nstate = check_stage(slug, stage, run)
    if result == "ok" and state != "complete":
        print(f"WARNING: finish ok requested but check says {state}; recording failed")
        for i in issues:
            print(f"detail: {i}")
        result = "fail"
    elif result == "fail" and state == "complete":
        # the Investment Advisor case: the call errored but the files are complete
        print("WARNING: stage reported failure but its outputs are complete; accepting it")
        result = "ok"
    info.update(status="complete" if result == "ok" else "failed",
                finished=now_iso(), finished_epoch=time.time())
    save_run(slug, run)
    left = MAX_ATTEMPTS - info["attempts"]
    out(stage=stage, status=info["status"], notion=nstate,
        retries_left=left if info["status"] == "failed" else "n/a")


def cmd_check(slug, stage):
    run = load_run(slug, required=False)
    state, issues, nstate = check_stage(slug, stage, run)
    out(check=state, notion=nstate)
    for i in issues:
        print(f"detail: {i}")


def fmt_dur(info):
    if info.get("started_epoch") and info.get("finished_epoch"):
        s = int(info["finished_epoch"] - info["started_epoch"])
        return f"{s // 60}m{s % 60:02d}s"
    return ""


def cmd_status(slug):
    if not os.path.isdir(adir(slug)):
        fail(f"no analysis directory analyses/{slug}")
    run = load_run(slug, required=False)
    meta = read_kv(os.path.join(adir(slug), ".meta"))
    print(f"analysis: {slug}  ({meta.get('company') or (run or {}).get('company', '?')}, "
          f"{meta.get('type') or (run or {}).get('type', '?')})")
    print(f"run-state: {'.run.json created ' + run['created'] if run else 'none (derived from files)'}")
    if run:
        stages = list(run["stages"])
    else:
        has_mat = os.path.isdir(os.path.join(adir(slug), "00_deal_materials"))
        stages = [s for s in ORDER if s != "notion-catchup" and (s != "ingest" or has_mat)]
    print(f"{'stage':15} {'run':10} {'tries':5} {'files':10} {'notion':7} time")
    for s in stages:
        info = run["stages"][s] if run else {}
        state, issues, nstate = check_stage(slug, s, run)
        print(f"{s:15} {info.get('status', '-'):10} {str(info.get('attempts', '-')):5} "
              f"{state:10} {nstate:7} {fmt_dur(info)}")
        for i in issues:
            print(f"    detail: {i}")


def cmd_prior_run(slug):
    run = load_run(slug, required=False)
    if not run or not run.get("rerun_in_progress") or not run.get("prior_run"):
        out(prior_run="none")
        return
    pr = run["prior_run"]
    out(prior_run="yes", base=pr.get("base", "?"),
        prior_rc_full=pr.get("rc_full_path", "none"))
    changed = pr.get("materials_changed") or []
    out(materials_changed=", ".join(changed) if changed else "none")


def main():
    a = sys.argv[1:]
    if not a:
        fail("usage: pipeline.py preflight|init|next|start|finish|check|status|prior-run ...")
    cmd, rest = a[0], a[1:]
    if cmd == "preflight" and len(rest) in (2, 3):
        preflight(*rest)
    elif cmd == "init" and len(rest) in (2, 3):
        cmd_init(*rest)
    elif cmd == "next" and len(rest) == 1:
        cmd_next(slug_arg(rest[0]))
    elif cmd == "start" and len(rest) == 2:
        cmd_start(slug_arg(rest[0]), stage_arg(rest[1]))
    elif cmd == "finish" and len(rest) == 3:
        cmd_finish(slug_arg(rest[0]), stage_arg(rest[1]), rest[2])
    elif cmd == "check" and len(rest) == 2:
        cmd_check(slug_arg(rest[0]), stage_arg(rest[1]))
    elif cmd == "status" and len(rest) == 1:
        cmd_status(slug_arg(rest[0]))
    elif cmd == "prior-run" and len(rest) == 1:
        cmd_prior_run(slug_arg(rest[0]))
    else:
        fail(f"bad arguments for '{cmd}' — see the docstring at the top of scripts/pipeline.py")


if __name__ == "__main__":
    main()
