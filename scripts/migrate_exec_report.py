#!/usr/bin/env python3
"""Render analyses/{slug}/05_executive_report.md from the legacy
05_executive_data.json + 05_executive_narrative.md pair.

Usage:
  python3 scripts/migrate_exec_report.py <slug> [--dry-run]
  python3 scripts/migrate_exec_report.py --all [--dry-run]

Rules:
  - Uses the same layout Executive writes (template owner:
    .claude/skills/executive/SKILL.md "Output instructions"). Fields missing
    from older JSON schemas render as `n/a`.
  - Writes a report only where none exists; never overwrites.
  - Never touches Notion.
  - Leaves the JSON and narrative files in place.
  - Reports gaps: an analysis with JSON but no narrative, or the reverse.
  - --dry-run prints what it would write (path + rendered report) and
    writes nothing.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSES = os.path.join(ROOT, "analyses")
NA = "n/a"

CORE_FLAGS = [
    ("subsidy_dependence", "Subsidy dependence"),
    ("dual_use_weapons_adjacency", "Dual-use / weapons adjacency"),
    ("safety_environmental_justice", "Safety / environmental justice"),
    ("governance", "Governance"),
]


def val(j, key):
    v = j.get(key)
    if v is None or (isinstance(v, str) and not v.strip()):
        return NA
    return v


def yaml_str(s):
    return json.dumps(s, ensure_ascii=False)


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def read_meta(slug):
    meta = {}
    p = os.path.join(ANALYSES, slug, ".meta")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            m = re.match(r'^\s*(\w+)\s*=\s*"?(.*?)"?\s*$', line)
            if m:
                meta[m.group(1)] = m.group(2)
    return meta


def parse_narrative(text):
    m = re.search(r"\[NARRATIVE_START\](.*?)\[NARRATIVE_END\]", text, re.S)
    body = m.group(1) if m else text
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    paras = [re.sub(r"^Para\s*\d+\s*:\s*", "", p) for p in paras]
    return "\n\n".join(paras)


def render(slug, j, narrative):
    meta = read_meta(slug)
    company = j.get("subject") or meta.get("company") or slug
    atype = (j.get("analysis_type") or meta.get("type") or NA).upper()
    grade, status = val(j, "grade"), val(j, "status")
    tc, cc = val(j, "technical_confidence"), val(j, "commercial_confidence")
    risk_level, risk_primary = val(j, "risk_level"), val(j, "risk_primary_type")
    secondary = j.get("risk_secondary_types") or []

    fm = [
        "---",
        f"company: {yaml_str(company)}",
        f"slug: {slug}",
        f"type: {atype}",
        f"analysis_date: {val(j, 'date')}",
        f"grade: {grade}",
        f"technical_confidence: {tc}",
        f"commercial_confidence: {cc}",
        f"status: {status}",
        f"grade_driver: {yaml_str(val(j, 'grade_driver'))}",
        f"risk_level: {risk_level}",
        f"risk_primary_type: {risk_primary}",
        f"risk_secondary_types: [{', '.join(secondary)}]",
        "---",
    ]

    b = []
    b.append(f"> **Grade {grade} / Tech {tc} · Comm {cc} · {status}**")
    b.append(f"> {val(j, 'grade_driver')}")
    b.append(f"> _Confidence: Tech {tc} · Comm {cc} — {val(j, 'confidence_driver')}_")
    b.append(f"> _Status rule: {val(j, 'status_reason')}_")
    b.append("")
    sec = f" (secondary: {', '.join(secondary)})" if secondary else ""
    rc = val(j, "risk_characterization")
    # drop a leading "LEVEL / TYPE:" label — the bold callout label already shows it
    rc = re.sub(r"^\s*[A-Z]+\s*/\s*[A-Z_]+\s*:\s*", "", rc)
    rc = rc[:1].upper() + rc[1:]
    b.append(f"> **Risk: {risk_level} / {risk_primary}**{sec}. {rc}")
    b.append("")

    b.append("## Executive Narrative")
    b.append("")
    b.append(narrative)
    b.append("")

    b.append("## Scorecard")
    b.append("")
    b.append("| Dimension | Bear | Central | Bull | Confidence | Driver |")
    b.append("| --- | --- | --- | --- | --- | --- |")
    for dim, s in (j.get("scores") or {}).items():
        b.append("| " + " | ".join(cell(x) for x in [
            dim, s.get("bear", NA), s.get("central", NA), s.get("bull", NA),
            s.get("confidence", ""), s.get("driver", NA)]) + " |")
    b.append("")

    b.append("## The Crux")
    b.append("")
    b.append(val(j, "crux"))
    b.append("")

    b.append("## Catalysts & Triggers")
    b.append("")
    cats = j.get("catalysts")
    if cats:
        b.append("| Event | Expected window | Scorecard rows moved | Flips to | Source stage |")
        b.append("| --- | --- | --- | --- | --- |")
        for c in cats:
            rows = c.get("scorecard_rows") or []
            rows = ", ".join(rows) if isinstance(rows, list) else rows
            b.append("| " + " | ".join(cell(x) for x in [
                c.get("event", NA), c.get("window", NA), rows or NA,
                c.get("target_grade_status", NA), c.get("source_stage", NA)]) + " |")
    else:
        b.append(NA)
    b.append("")

    b.append("## Sourcing Strength")
    b.append("")
    b.append(val(j, "sourcing_strength"))
    b.append("")

    if atype == "DEAL":
        b.append("## Deal Terms & Price Sensitivity")
        b.append("")
        b.append(val(j, "deal_terms"))
        b.append("")

    b.append("## Values & Judgment Flags")
    b.append("")
    vf = j.get("values_flags")
    if isinstance(vf, dict):
        for key, label in CORE_FLAGS:
            b.append(f"- **{label}:** {vf.get(key) or NA}")
        for key, v in vf.items():
            if key in dict(CORE_FLAGS):
                continue
            label = key.replace("_", " ").capitalize()
            b.append(f"- **{label}:** {v}")
    elif isinstance(vf, list) and vf:
        for v in vf:
            b.append(f"- {v}")
    else:
        b.append(NA)
    b.append("")

    for heading, key in [("What Would Change This", "evidence_to_change"),
                         ("Next Actions", "next_actions")]:
        b.append(f"## {heading}")
        b.append("")
        items = j.get(key) or []
        if items:
            b.extend(f"- {x}" for x in items)
        else:
            b.append(NA)
        b.append("")

    body = "\n".join(b).rstrip("\n")
    return "\n".join(fm) + f"\n# {company} — Executive Report ({atype})\n\n[REPORT_START]\n" + body + "\n[REPORT_END]\n"


def migrate(slug, dry_run):
    d = os.path.join(ANALYSES, slug)
    jp = os.path.join(d, "05_executive_data.json")
    np_ = os.path.join(d, "05_executive_narrative.md")
    rp = os.path.join(d, "05_executive_report.md")
    has_j, has_n = os.path.exists(jp), os.path.exists(np_)
    if os.path.exists(rp):
        return "skip", "report exists"
    if not has_j and not has_n:
        return "none", "no executive output"
    if has_j != has_n:
        return "gap", ("JSON but no narrative" if has_j else "narrative but no JSON")
    try:
        j = json.load(open(jp, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return "gap", f"JSON unreadable: {e}"
    report = render(slug, j, parse_narrative(open(np_, encoding="utf-8").read()))
    if dry_run:
        print(f"===== would write {os.path.relpath(rp, ROOT)} =====")
        print(report)
        return "would-write", ""
    with open(rp, "w", encoding="utf-8") as f:
        f.write(report)
    return "wrote", ""


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    if args == ["--all"]:
        slugs = sorted(s for s in os.listdir(ANALYSES)
                       if os.path.isdir(os.path.join(ANALYSES, s)) and not s.startswith("."))
    elif len(args) == 1:
        slugs = args
        if not os.path.isdir(os.path.join(ANALYSES, slugs[0])):
            print(f"ERROR: analyses/{slugs[0]} not found")
            sys.exit(1)
    else:
        print("usage: migrate_exec_report.py <slug>|--all [--dry-run]")
        sys.exit(1)

    results = [(s, *migrate(s, dry)) for s in slugs]
    print("\n===== summary =====")
    for s, status, note in results:
        print(f"{status:12} {s}" + (f"  ({note})" if note else ""))
    gaps = [r for r in results if r[1] == "gap"]
    print(f"gaps: {len(gaps)}" + ("" if not gaps else " — " + "; ".join(f"{s}: {n}" for s, _, n in gaps)))


if __name__ == "__main__":
    main()
