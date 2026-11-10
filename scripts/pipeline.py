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
  reconcile <slug>
      For resume: any stage still marked `running` (its session died) is
      re-checked and set to `complete` if its outputs are complete and newer
      than its start, else `failed` (which leaves its retry, if any).
  root
      Print the repo root (`root: <path>`), so callers can confirm the
      working directory before invoking stage skills, whose Setup blocks use
      repo-relative paths.
  prior-run <slug>
      For /research's Setup. When .run.json marks a re-run in progress
      (`rerun_in_progress` with `prior_run.snapshot` naming a history/ dir),
      prints the base snapshot's name and analysis date, the absolute path
      of its RC full output, and the materials NEW/CHANGED since that
      snapshot. Otherwise prints `prior-run: none`.
  snapshot <slug> --reason <initial|new-materials|refresh|manual>
      Archive the current run before anything overwrites it, to
      analyses/{slug}/history/{YYYY-MM-DD_HHMM}_{reason}/: the 01-05
      outputs, manifest.md, materials_digest.md, .ingested.json, .meta and
      .run.json, plus snapshot.json (reason, analysis date, the run's
      pipeline fingerprint or null, and the sha256 of every materials file
      that run ingested, from .ingested.json — raw/ and exhibits/ themselves
      aren't copied). Prints `snapshot: <dir>`, or
      `snapshot: none` if there are no outputs to archive.
  materials <slug> [--source <path>] [--copy] [--commit]
      Classify deal materials as NEW / CHANGED / UNCHANGED / REMOVED against
      00_deal_materials/.ingested.json (bootstrap: if that file is missing
      but a digest exists — an analysis ingested before this record
      existed — everything currently in raw/ counts as already ingested;
      with no digest either, everything is NEW).
        --source <path>  compare the source file/folder, before any copy
        (no --source)    compare raw/ itself
        --copy           with --source: copy NEW/CHANGED files into raw/,
                         first moving each CHANGED file's old version to
                         raw/.superseded/{date}/
        --commit         record raw/'s current hashes in .ingested.json
                         (run after a successful ingest)
      Prints one line per non-UNCHANGED file, a counts line, and
      `to-process:` (the NEW/CHANGED files, relative to raw/) or
      `to-process: none`.

  rerun-init <company-or-slug> [--source <path>] [--force] [--from <stage>]
      Start a re-run of an existing analysis (for /rerun-analysis). Refuses
      unless the analysis has a completed run (.meta and
      05_executive_report.md) and no unfinished run. With --source,
      classifies the documents before copying anything and stops with
      `stop: no new or changed documents` unless --force. New documents
      require re-running from research. Then snapshots the current run
      (reason new-materials, refresh with no --source, or manual when
      forced) and writes a fresh .run.json marked as a re-run: ingest (only
      if documents are new or changed), stages from --from (default
      research) through executive, compare, notion-catchup.

Stage graph:
  ingest? -> research -> {science, investment, political} -> bull -> bear
  -> executive -> compare (re-runs only) -> notion-catchup
"""
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
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
# Notion catch-up is best-effort: one attempt, and its failure ends the run
# with a warning instead of stopping it.
STAGE_MAX_ATTEMPTS = {"notion-catchup": 1}


def max_attempts(stage):
    return STAGE_MAX_ATTEMPTS.get(stage, MAX_ATTEMPTS)

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
    # re-runs only: compare this run against the snapshot it replaced. Its
    # Notion key is dated (compare_YYYYMMDD_page_id), so it has no fixed key.
    "compare": (["executive"], [
        ("06_run_comparison.md", "[COMPARISON_START]", "[COMPARISON_END]"),
    ], []),
    "notion-catchup": (["executive", "compare"], [], []),
}
ORDER = list(STAGES)
# skill invoked for each stage (for the orchestrator)
SKILL = {"ingest": "ingest-materials", "research": "research", "science": "science",
         "investment": "investment-advisor", "political": "political", "bull": "bull",
         "bear": "bear", "executive": "executive", "compare": "compare-runs",
         "notion-catchup": "notion-sync"}
RERUN_FROM = ["research", "science", "investment", "political", "bull", "bear", "executive"]
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


# --- materials & snapshots ------------------------------------------------

def hash_tree(path):
    """{relpath: sha256} for a file or folder, skipping dotfiles/dot-dirs
    (so raw/.superseded/ is never counted)."""
    path = os.path.abspath(os.path.expanduser(path))
    if os.path.isfile(path):
        return {os.path.basename(path): sha256_file(path)}
    hashes = {}
    for dp, dnames, fnames in os.walk(path):
        dnames[:] = sorted(d for d in dnames if not d.startswith("."))
        for f in sorted(fnames):
            if f.startswith("."):
                continue
            full = os.path.join(dp, f)
            hashes[os.path.relpath(full, path)] = sha256_file(full)
    return hashes


def materials_dir(slug):
    return os.path.join(adir(slug), "00_deal_materials")


def ingested_record(slug):
    """(hashes, bootstrapped) — hashes from .ingested.json. Analyses
    ingested before .ingested.json existed have a digest but no record:
    then raw/'s current contents count as already ingested. With neither,
    nothing has been ingested yet."""
    p = os.path.join(materials_dir(slug), ".ingested.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return {k: v["sha256"] for k, v in json.load(f)["files"].items()}, False
    raw = os.path.join(materials_dir(slug), "raw")
    if not os.path.exists(os.path.join(materials_dir(slug), "materials_digest.md")):
        return {}, False
    return (hash_tree(raw) if os.path.isdir(raw) else {}), True


def classify(current, recorded, full_set=True):
    res = {"NEW": [], "CHANGED": [], "UNCHANGED": [], "REMOVED": []}
    for rel, h in sorted(current.items()):
        if rel not in recorded:
            res["NEW"].append(rel)
        elif recorded[rel] != h:
            res["CHANGED"].append(rel)
        else:
            res["UNCHANGED"].append(rel)
    if full_set:
        res["REMOVED"] = sorted(set(recorded) - set(current))
    return res


def report_age(slug, base_dir=None):
    """analysis_date of an executive report (falls back to RC full mtime)."""
    d = base_dir or adir(slug)
    rp = os.path.join(d, "05_executive_report.md")
    if os.path.exists(rp):
        fm = parse_frontmatter(open(rp, encoding="utf-8").read()) or {}
        if fm.get("analysis_date") and fm["analysis_date"] != "n/a":
            return fm["analysis_date"]
    rc = os.path.join(d, "01_research_collector_full.md")
    if os.path.exists(rc):
        return datetime.date.fromtimestamp(os.path.getmtime(rc)).isoformat()
    return "unknown"


def cmd_materials(slug, source=None, copy=False, commit=False):
    md = materials_dir(slug)
    raw = os.path.join(md, "raw")
    if copy and not source:
        fail("--copy requires --source")
    recorded, boot = ingested_record(slug)
    if source:
        src = os.path.abspath(os.path.expanduser(source))
        if not os.path.exists(src):
            fail(f"source path does not exist: {src}")
        current = hash_tree(src)
        if not current:
            fail(f"source has no files: {src}")
        # a source folder is usually a subset (new docs only), so files
        # missing from it aren't REMOVED unless we compare raw/ itself
        res = classify(current, recorded, full_set=False)
    else:
        current = hash_tree(raw) if os.path.isdir(raw) else {}
        res = classify(current, recorded, full_set=not boot)
    if boot:
        print("WARNING: no .ingested.json yet; treating everything currently in raw/ as already ingested")
    for status in ("NEW", "CHANGED", "REMOVED"):
        for rel in res[status]:
            print(f"{status}: {rel}")
    out(materials=" ".join(f"{k.lower()}={len(v)}" for k, v in res.items()))
    todo = res["NEW"] + res["CHANGED"]

    if copy and todo:
        stamp = datetime.date.today().isoformat()
        for rel in todo:
            dst = os.path.join(raw, rel)
            if rel in res["CHANGED"] and os.path.exists(dst):
                sup = os.path.join(raw, ".superseded", stamp, rel)
                os.makedirs(os.path.dirname(sup), exist_ok=True)
                if os.path.exists(sup):
                    sup += f".{int(time.time())}"
                shutil.move(dst, sup)
                print(f"superseded: {rel} -> raw/.superseded/{stamp}/{rel}")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            srcfile = src if os.path.isfile(src) else os.path.join(src, rel)
            shutil.copy2(srcfile, dst)
            print(f"copied: {rel}")
    out(to_process=", ".join(todo) if todo else "none")

    if commit:
        if not os.path.isdir(raw):
            fail(f"no raw/ folder at {os.path.relpath(raw, ROOT)}")
        now = now_iso()
        prev = {}
        p = os.path.join(md, ".ingested.json")
        if os.path.exists(p):
            prev = json.load(open(p, encoding="utf-8"))["files"]
        files = {}
        for rel, h in hash_tree(raw).items():
            same = prev.get(rel, {}).get("sha256") == h
            files[rel] = {"sha256": h, "ingested": prev[rel]["ingested"] if same else now}
        fd, tmp = tempfile.mkstemp(dir=md, prefix=".ingested.")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"updated": now, "files": files}, f, indent=2)
            f.write("\n")
        os.replace(tmp, p)
        out(committed=f"{len(files)} file(s) to 00_deal_materials/.ingested.json")


SNAPSHOT_REASONS = {"initial", "new-materials", "refresh", "manual"}


def cmd_snapshot(slug, reason, quiet=False):
    if reason not in SNAPSHOT_REASONS:
        fail(f"reason must be one of: {', '.join(sorted(SNAPSHOT_REASONS))}")
    d = adir(slug)
    if not os.path.isdir(d):
        fail(f"no analysis directory analyses/{slug}")
    outputs = sorted(f for f in os.listdir(d) if re.match(r"^0[1-6][a-c]?_.*\.(md|json)$", f))
    if not outputs:
        if not quiet:
            out(snapshot="none")
        return None
    name = f"{datetime.datetime.now().strftime('%Y-%m-%d_%H%M')}_{reason}"
    dest = os.path.join(d, "history", name)
    n = 2
    while os.path.exists(dest):
        dest = os.path.join(d, "history", f"{name}_{n}")
        n += 1
    os.makedirs(dest)
    copied = []
    extra = [".meta", ".run.json",
             os.path.join("00_deal_materials", "manifest.md"),
             os.path.join("00_deal_materials", "materials_digest.md"),
             os.path.join("00_deal_materials", ".ingested.json")]
    for rel in outputs + extra:
        srcp = os.path.join(d, rel)
        if os.path.exists(srcp):
            dstp = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(dstp), exist_ok=True)
            shutil.copy2(srcp, dstp)
            copied.append(rel)
    run = load_run(slug, required=False)
    meta = {
        "created": now_iso(),
        "reason": reason,
        "analysis_date": report_age(slug),
        # the fingerprint of the run that produced these outputs; runs from
        # before .run.json existed have none, and /compare-runs must report
        # "unknown (no fingerprint)" rather than "no pipeline change"
        "fingerprint": (run or {}).get("fingerprint"),
        # what this run ingested (.ingested.json), not raw/'s current state,
        # so the record is right even if new files were copied in first
        "materials": ingested_record(slug)[0],
        "files": copied,
    }
    with open(os.path.join(dest, "snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    if not quiet:
        out(snapshot=os.path.relpath(dest, ROOT), files=len(copied),
            fingerprint="recorded" if meta["fingerprint"] else "none (pre-pipeline run)")
    return os.path.basename(dest)


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
    if "/" in company or company.startswith("~"):
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
    stages = [s for s in ORDER if (s != "ingest" or src) and s != "compare"]
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


def finish_rerun(slug, run):
    # once the run is done, research must no longer see a "prior run"
    if run.get("rerun_in_progress"):
        run["rerun_in_progress"] = False
        save_run(slug, run)


def cmd_rerun_init(target, source=None, force=False, from_stage="research"):
    if from_stage not in RERUN_FROM:
        fail(f"--from must be one of: {', '.join(RERUN_FROM)}")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "resolve_target.py"),
                        "--slug-only", target], cwd=ROOT, capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    err = [l for l in lines if l.startswith("ERROR:")]
    if err:
        print(err[0])
        sys.exit(0)
    slug = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("slug:")), None)
    d = adir(slug or "")
    if not slug or not os.path.exists(os.path.join(d, ".meta")):
        fail(f"no analysis found for '{target}' (expected analyses/{slug}/.meta). "
             f"Start a new one with /run-analysis")
    meta = read_kv(os.path.join(d, ".meta"))
    run = load_run(slug, required=False)
    if run and any(i["status"] != "complete" for i in run["stages"].values()):
        fail(f"analyses/{slug} has an unfinished run. Use /run-analysis resume {slug} first")
    if not os.path.exists(os.path.join(d, "05_executive_report.md")):
        hint = (" (legacy JSON found: run python3 scripts/migrate_exec_report.py " + slug + ")"
                if os.path.exists(os.path.join(d, "05_executive_data.json")) else "")
        fail(f"analyses/{slug} has no 05_executive_report.md, so there's no completed run "
             f"to compare against{hint}")

    todo, src = [], None
    if source:
        src = os.path.abspath(os.path.expanduser(source))
        if not os.path.exists(src):
            fail(f"documents path does not exist: {src}")
        current = hash_tree(src)
        if not current:
            fail(f"documents path has no files: {src}")
        recorded, _ = ingested_record(slug)
        res = classify(current, recorded, full_set=False)
        for st in ("NEW", "CHANGED"):
            for rel in res[st]:
                print(f"{st}: {rel}")
        out(materials=" ".join(f"{k.lower()}={len(v)}" for k, v in res.items() if k != "REMOVED"))
        todo = res["NEW"] + res["CHANGED"]
        if not todo and not force:
            out(stop="no new or changed documents; nothing to re-run (pass --force to re-run anyway)")
            return
    if todo and from_stage != "research":
        fail(f"new documents only reach the analysis through research; drop --from {from_stage}")

    reason = "new-materials" if todo else ("manual" if force else "refresh")
    snap = cmd_snapshot(slug, reason, quiet=True)
    if not snap:
        fail(f"nothing to snapshot in analyses/{slug}")
    i = ORDER.index(from_stage)
    stages = (["ingest"] if todo else []) + [s for s in ORDER[i:] if s != "ingest"]
    new_run = {
        "slug": slug, "company": meta.get("company", slug), "type": meta.get("type", ""),
        "source": src if todo else None,
        "mode": "rerun", "rerun_in_progress": from_stage == "research",
        "prior_run": {"snapshot": snap}, "from_stage": from_stage,
        "created": now_iso(),
        "stages": {s: {"status": "pending", "attempts": 0, "started": None,
                       "started_epoch": None, "finished": None, "finished_epoch": None}
                   for s in stages},
        "materials": {},
        "fingerprint": fingerprint(),
    }
    save_run(slug, new_run)
    out(slug=slug, company=new_run["company"], type=new_run["type"], reason=reason,
        snapshot=snap, source=new_run["source"] or "none", stages=" ".join(stages))


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
        elif info["status"] == "failed" and info["attempts"] >= max_attempts(s):
            blocked.append(s)
        elif info["status"] in ("pending", "failed") and deps_done(run, s):
            ready.append(s)
    if all(i["status"] == "complete" for i in st.values()):
        finish_rerun(slug, run)
        out(ready="none", done="true", notion="synced")
        return
    if blocked == ["notion-catchup"] and all(
            i["status"] == "complete" for k, i in st.items() if k != "notion-catchup"):
        finish_rerun(slug, run)
        out(ready="none", done="true", notion="incomplete")
        print("WARNING: analysis complete, but Notion catch-up failed. Run /notion-sync "
              f"{slug} to retry; the local files are the source of truth")
        return
    if blocked:
        # a second failure stops the pipeline: launch nothing new, so nothing
        # downstream runs with a gap
        out(ready="none", running=" ".join(running) or "none", blocked=" ".join(blocked))
        print(f"ERROR: stage {blocked[0]} failed {max_attempts(blocked[0])} time(s); pipeline stopped. "
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
    if info["attempts"] >= max_attempts(stage):
        fail(f"stage {stage} has used its {max_attempts(stage)} attempt(s)")
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
    left = max_attempts(stage) - info["attempts"]
    out(stage=stage, status=info["status"], notion=nstate,
        retries_left=left if info["status"] == "failed" else "n/a")


def cmd_reconcile(slug):
    run = load_run(slug)
    changed = []
    for s, info in run["stages"].items():
        if info["status"] != "running":
            continue
        state, issues, _ = check_stage(slug, s, run)
        info.update(status="complete" if state == "complete" else "failed",
                    finished=now_iso(), finished_epoch=time.time())
        changed.append(f"{s}={info['status']}")
        for i in issues:
            print(f"detail: {s}: {i}")
    save_run(slug, run)
    out(reconciled=" ".join(changed) or "none")


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
        has_cmp = os.path.exists(os.path.join(adir(slug), "06_run_comparison.md"))
        stages = [s for s in ORDER if s != "notion-catchup" and (s != "ingest" or has_mat)
                  and (s != "compare" or has_cmp)]
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
    pr = (run or {}).get("prior_run") or {}
    snap = pr.get("snapshot")
    base = os.path.join(adir(slug), "history", snap) if snap else None
    if not run or not run.get("rerun_in_progress") or not base or not os.path.isdir(base):
        out(prior_run="none")
        return
    meta = {}
    sj = os.path.join(base, "snapshot.json")
    if os.path.exists(sj):
        meta = json.load(open(sj, encoding="utf-8"))
    rc = os.path.join(base, "01_research_collector_full.md")
    out(prior_run="yes", base=snap, base_date=meta.get("analysis_date") or report_age(slug, base),
        prior_rc_full=rc if os.path.exists(rc) else "none")
    raw = os.path.join(materials_dir(slug), "raw")
    res = classify(hash_tree(raw) if os.path.isdir(raw) else {}, meta.get("materials", {}))
    changed = [f"NEW {r}" for r in res["NEW"]] + [f"CHANGED {r}" for r in res["CHANGED"]]
    out(materials_changed="; ".join(changed) if changed else "none")


def main():
    a = sys.argv[1:]
    if not a:
        fail("usage: pipeline.py preflight|init|next|start|finish|check|reconcile|status|root|"
             "snapshot|materials|rerun-init|prior-run ...")
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
    elif cmd == "reconcile" and len(rest) == 1:
        cmd_reconcile(slug_arg(rest[0]))
    elif cmd == "snapshot" and len(rest) == 3 and rest[1] == "--reason":
        cmd_snapshot(slug_arg(rest[0]), rest[2])
    elif cmd == "materials" and rest:
        slug, flags = slug_arg(rest[0]), rest[1:]
        source = None
        if "--source" in flags:
            i = flags.index("--source")
            if i + 1 >= len(flags):
                fail("--source needs a path")
            source = flags[i + 1]
            del flags[i:i + 2]
        unknown = [f for f in flags if f not in ("--copy", "--commit")]
        if unknown:
            fail(f"unknown materials flag(s): {' '.join(unknown)}")
        cmd_materials(slug, source, "--copy" in flags, "--commit" in flags)
    elif cmd == "rerun-init" and rest:
        target, flags = rest[0], rest[1:]
        source, from_stage = None, "research"
        for opt in ("--source", "--from"):
            if opt in flags:
                i = flags.index(opt)
                if i + 1 >= len(flags):
                    fail(f"{opt} needs a value")
                if opt == "--source":
                    source = flags[i + 1]
                else:
                    from_stage = flags[i + 1]
                del flags[i:i + 2]
        unknown = [f for f in flags if f != "--force"]
        if unknown:
            fail(f"unknown rerun-init argument(s): {' '.join(unknown)}")
        cmd_rerun_init(target, source, "--force" in flags, from_stage)
    elif cmd == "root" and not rest:
        out(root=ROOT)
    elif cmd == "prior-run" and len(rest) == 1:
        cmd_prior_run(slug_arg(rest[0]))
    else:
        fail(f"bad arguments for '{cmd}' — see the docstring at the top of scripts/pipeline.py")


if __name__ == "__main__":
    main()
