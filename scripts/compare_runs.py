#!/usr/bin/env python3
"""Deterministic diff between a previous run (a history/ snapshot) and the
current run of an analysis. Step 1 of /compare-runs; the judgment step
reads its output.

Usage:
  python3 scripts/compare_runs.py <slug> [base-snapshot]

  base-snapshot is a directory name under analyses/{slug}/history/; it
  defaults to the newest one.

Writes analyses/{slug}/06_run_comparison_data.md and prints `key: value`
lines (base, base_dir, base_date, head_date, notion_key, notion_title,
data_file) for the skill to use. A line starting `ERROR:` means stop.

What it compares (all parsed, nothing judged):
  - verdict: grade, both confidences, status, risk level / types
  - scorecard: bear/central/bull per dimension, with deltas
  - crux row: the first scorecard dimension named in each report's crux
  - materials: NEW/CHANGED/REMOVED between the base snapshot's ingested
    hashes and the current .ingested.json
  - ingestion-log rows dated on or after the base run
  - pipeline: which prompt files changed between the two runs'
    fingerprints, mapped to stages — `unknown (no fingerprint)` when either
    side has none, which is true of every run before .run.json existed
  - --from: which stages the head run re-ran, when it didn't start at research
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NA = "n/a"
VERDICT_KEYS = ["grade", "technical_confidence", "commercial_confidence", "status",
                "risk_level", "risk_primary_type", "risk_secondary_types"]
SKILL_TO_STAGE = {"research": "research", "science": "science", "investment-advisor": "investment",
                  "political": "political", "bull": "bull", "bear": "bear",
                  "executive": "executive", "ingest-materials": "ingest",
                  "notion-sync": "notion formatting only", "compare-runs": "compare",
                  "run-analysis": "orchestration only", "rerun-analysis": "orchestration only"}


def fail(msg):
    print(f"ERROR: {msg}")
    sys.exit(0)


def frontmatter(text):
    lines = text.splitlines()
    fm = {}
    if not lines or lines[0].strip() != "---":
        return fm
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            v = m.group(2).strip()
            if v.startswith('"'):
                try:
                    v = json.loads(v)
                except json.JSONDecodeError:
                    pass
            fm[m.group(1)] = v
    return fm


def section(text, heading):
    m = re.search(r"^## " + re.escape(heading) + r"\s*$(.*?)(?=^## |^\[REPORT_END\]|\Z)",
                  text, re.M | re.S)
    return m.group(1).strip() if m else ""


def scorecard(text):
    rows = {}
    for line in section(text, "Scorecard").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("Dimension", "") or set(cells[0]) <= set("-: "):
            continue
        def num(x):
            try:
                return int(x)
            except ValueError:
                return None
        rows[cells[0]] = {"bear": num(cells[1]), "central": num(cells[2]), "bull": num(cells[3]),
                          "confidence": cells[4] if len(cells) > 4 else ""}
    return rows


def crux_row(text, dims):
    crux = section(text, "The Crux")
    hits = [(crux.find(d), d) for d in dims if crux.find(d) >= 0]
    return min(hits)[1] if hits else NA


def hash_tree(path):
    """{relpath: sha256}, skipping dotfiles/dot-dirs (same rule as pipeline.py)."""
    out = {}
    if not os.path.isdir(path):
        return out
    for dp, dnames, fnames in os.walk(path):
        dnames[:] = sorted(x for x in dnames if not x.startswith("."))
        for f in sorted(fnames):
            if f.startswith("."):
                continue
            full = os.path.join(dp, f)
            h = hashlib.sha256()
            with open(full, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            out[os.path.relpath(full, path)] = h.hexdigest()
    return out


def load_json(p):
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def fmt_delta(a, b):
    if a is None or b is None:
        return NA
    d = b - a
    return f"{d:+d}" if d else "0"


def cell(x):
    return str(x).replace("|", "\\|")


def main():
    if len(sys.argv) not in (2, 3):
        fail("usage: compare_runs.py <slug> [base-snapshot]")
    slug = sys.argv[1]
    d = os.path.join(ROOT, "analyses", slug)
    hist = os.path.join(d, "history")
    if not os.path.isdir(hist) or not os.listdir(hist):
        fail(f"analyses/{slug} has no history/ snapshots to compare against")
    snaps = sorted(x for x in os.listdir(hist) if os.path.isdir(os.path.join(hist, x)))
    base = sys.argv[2] if len(sys.argv) == 3 else snaps[-1]
    bdir = os.path.join(hist, base)
    if not os.path.isdir(bdir):
        fail(f"no snapshot analyses/{slug}/history/{base} (have: {', '.join(snaps)})")
    brep_p, hrep_p = (os.path.join(x, "05_executive_report.md") for x in (bdir, d))
    for p in (brep_p, hrep_p):
        if not os.path.exists(p):
            fail(f"{os.path.relpath(p, ROOT)} not found")
    btext, htext = (open(p, encoding="utf-8").read() for p in (brep_p, hrep_p))
    bfm, hfm = frontmatter(btext), frontmatter(htext)
    snapmeta = load_json(os.path.join(bdir, "snapshot.json")) or {}
    hrun = load_json(os.path.join(d, ".run.json")) or {}
    bdate = snapmeta.get("analysis_date") or bfm.get("analysis_date", NA)
    hdate = hfm.get("analysis_date", NA)

    L = [f"# {hfm.get('company', slug)} — Run comparison data", "",
         "Generated by `scripts/compare_runs.py`. Parsed facts only, no judgment.", "",
         f"- **Base:** `history/{base}` (analysis date {bdate}, snapshot reason "
         f"`{snapmeta.get('reason', NA)}`)",
         f"- **Head:** current run (analysis date {hdate})", ""]

    # verdict
    L += ["## Verdict", "", "| Field | Base | Head | Changed |", "| --- | --- | --- | --- |"]
    for k in VERDICT_KEYS:
        a, b = bfm.get(k, NA), hfm.get(k, NA)
        L.append(f"| {k} | {cell(a)} | {cell(b)} | {'yes' if a != b else ''} |")
    L.append("")

    # scorecard
    bs, hs = scorecard(btext), scorecard(htext)
    dims = list(hs) + [x for x in bs if x not in hs]
    L += ["## Scorecard", "",
          "| Dimension | Bear | Central | Bull | Δ central | Confidence |",
          "| --- | --- | --- | --- | --- | --- |"]
    moved = []
    for dim in dims:
        a, b = bs.get(dim, {}), hs.get(dim, {})
        cols = []
        for k in ("bear", "central", "bull"):
            av, bv = a.get(k), b.get(k)
            cols.append(f"{NA if av is None else av} → {NA if bv is None else bv}")
        dc = fmt_delta(a.get("central"), b.get("central"))
        conf = f"{a.get('confidence') or '–'} → {b.get('confidence') or '–'}"
        note = "" if dim in bs and dim in hs else (" (new row)" if dim not in bs else " (dropped)")
        L.append(f"| {cell(dim)}{note} | {' | '.join(cols)} | {dc} | {conf} |")
        if any(a.get(k) != b.get(k) for k in ("bear", "central", "bull")):
            moved.append(dim)
    L += ["", f"Rows whose bear, central or bull score moved: {', '.join(moved) if moved else 'none'}.", ""]

    # crux
    L += ["## Crux row", "",
          f"- Base: {crux_row(btext, list(bs))}",
          f"- Head: {crux_row(htext, list(hs))}", ""]

    # materials
    bmat = snapmeta.get("materials") or {}
    ij = load_json(os.path.join(d, "00_deal_materials", ".ingested.json"))
    if ij:
        hmat = {k: v["sha256"] for k, v in ij.get("files", {}).items()}
    elif os.path.exists(os.path.join(d, "00_deal_materials", "materials_digest.md")):
        # ingested before .ingested.json existed: raw/ is what was ingested
        hmat = hash_tree(os.path.join(d, "00_deal_materials", "raw"))
    else:
        hmat = {}
    L += ["## Materials between runs", ""]
    if not bmat and not hmat:
        L.append("No deal materials in either run.")
    else:
        new = sorted(set(hmat) - set(bmat))
        changed = sorted(k for k in hmat if k in bmat and hmat[k] != bmat[k])
        removed = sorted(set(bmat) - set(hmat))
        for label, items in (("NEW", new), ("CHANGED", changed), ("REMOVED", removed)):
            L.append(f"- {label}: {', '.join(items) if items else 'none'}")
        if not bmat:
            L.append("- (Base snapshot recorded no materials hashes.)")
    log = []
    dig = os.path.join(d, "00_deal_materials", "materials_digest.md")
    if os.path.exists(dig):
        for line in section(open(dig, encoding="utf-8").read(), "Ingestion log").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and re.match(r"^\d{4}-\d{2}-\d{2}$", cells[0]) and cells[0] >= str(bdate):
                log.append(f"- {cells[0]}: {cells[1]} ({cells[2]})")
    L += ["", "Ingestion-log rows dated on or after the base run's analysis date:"] + (log or ["- none"]) + [""]

    # pipeline
    L += ["## Pipeline changes", ""]
    bfp = snapmeta.get("fingerprint")
    hfp = hrun.get("fingerprint")
    if not bfp or not hfp:
        side = "base" if not bfp else "head"
        L.append(f"unknown (no fingerprint): the {side} run predates `.run.json` fingerprints, so "
                 f"score movements can't be attributed to or ruled out as prompt changes.")
    else:
        bf, hf = bfp.get("files", {}), hfp.get("files", {})
        changed = sorted(f for f in set(bf) | set(hf) if bf.get(f) != hf.get(f))
        if not changed:
            L.append("none: every prompt file is identical between the two runs.")
        else:
            for f in changed:
                m = re.match(r"\.claude/skills/([^/]+)/", f)
                stage = SKILL_TO_STAGE.get(m.group(1), m.group(1)) if m else (
                    "all stages" if f == "CLAUDE.md" else "?")
                L.append(f"- `{f}` → {stage}")
        for k, label in (("git_commit", "commit"),):
            L.append(f"- {label}: {bfp.get(k) or NA} → {hfp.get(k) or NA}"
                     + ("; uncommitted prompt edits in head run" if hfp.get("uncommitted_prompt_edits") else ""))
    L.append("")
    frm = hrun.get("from_stage")
    if frm and frm != "research":
        L += ["## Partial re-run", "",
              f"The head run started at `{frm}` (`--from {frm}`). Stages before it were not re-run, so "
              f"differences upstream of `{frm}` are impossible by construction.", ""]

    out_p = os.path.join(d, "06_run_comparison_data.md")
    with open(out_p, "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    key_date = (hdate if hdate != NA else "undated").replace("-", "")
    print(f"base: {base}")
    print(f"base_dir: {bdir}")
    print(f"base_date: {bdate}")
    print(f"head_date: {hdate}")
    print(f"notion_key: compare_{key_date}_page_id")
    print(f"notion_title: Run comparison: {bdate} → {hdate}")
    print(f"data_file: {out_p}")


if __name__ == "__main__":
    main()
