#!/usr/bin/env python3
"""Print the Notion push payload for one stage of an analysis.

Usage:
  python3 scripts/notion_body.py <slug> <stage>
  python3 scripts/notion_body.py <slug> executive --properties

  <stage> accepts the same values as /notion-sync: research|1, science|2a,
  investment|2b, political|2c, bull|3, bear|4, executive|5, compare|6.

What it does (the one strip-and-escape path for every Notion push — see
.claude/skills/notion-sync/REFERENCE.md):
  1. Reads the stage's local file (file name and delimiters come from
     REFERENCE.md's stage facts table, so that table stays the single source).
  2. Strips any YAML frontmatter (executive, compare), the first H1 title
     line, and the stage's delimiter marker lines.
  3. Applies the Notion escape rule (see escape_for_notion below).
  4. For executive only: appends `## Stage Reports`, its intro line, and one
     `<page url=...>` block per `stage*_page_id` in analyses/{slug}/.notion,
     in stage order, then one per run-comparison page
     (`compare_YYYYMMDD[_n]_page_id`, titled by its `..._page_title`), so
     the child-page links are generated from state rather than recalled. A
     comparison page left out here would be deleted (or block the push) by
     replace_content. These tags are appended AFTER escaping.

With --properties (executive only): prints instead a JSON object of the
main page's Notion properties built from the report's frontmatter: Grade,
Grade driver (escaped), Technical/Commercial Confidence, Status, and
Analysis Date = `analysis_date` (never today) with is_datetime 0. Any
property whose value is `n/a` is left out and listed in a final
`OMITTED: ...` line on stderr.

Prints the payload on stdout. On failure prints one line starting `ERROR:`
and exits non-zero.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE = os.path.join(ROOT, ".claude", "skills", "notion-sync", "REFERENCE.md")

ALIASES = {
    "research": "1", "1": "1",
    "science": "2a", "2a": "2a",
    "investment": "2b", "2b": "2b",
    "political": "2c", "2c": "2c",
    "bull": "3", "3": "3",
    "bear": "4", "4": "4",
    "executive": "5", "5": "5",
    "compare": "6", "6": "6",
}
STAGE_ORDER = ["1", "2a", "2b", "2c", "3", "4"]
STAGE_REPORTS_INTRO = "Full write-ups for each pipeline stage are linked as sub-pages below."


def fail(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)


def load_stage_facts():
    """Parse REFERENCE.md's stage facts table into {stage: dict}."""
    try:
        text = open(REFERENCE, encoding="utf-8").read()
    except OSError as e:
        fail(f"cannot read {REFERENCE}: {e}")
    facts = {}
    row = re.compile(
        r"^\|\s*(\w+)\s*\|\s*`([^`]+)`\s*\|\s*`(\[[A-Z_]+\])`\s*/\s*`(\[[A-Z_]+\])`\s*\|\s*([^|]+?)\s*\|\s*`([^`]+)`\s*\|\s*$"
    )
    for line in text.splitlines():
        m = row.match(line)
        if m:
            stage, fname, start, end, title, key = m.groups()
            facts[stage] = {"file": fname, "start": start, "end": end,
                            "title": title, "key": key}
    missing = [s for s in STAGE_ORDER + ["5"] if s not in facts]
    if missing:
        fail(f"REFERENCE.md stage facts table is missing rows for: {', '.join(missing)}")
    return facts


def read_kv(path):
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        m = re.match(r'^\s*([A-Za-z0-9_]+)\s*=\s*"?(.*?)"?\s*$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def strip_frontmatter(lines):
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[i + 1:]
    return lines


def strip_structure(text, start, end):
    lines = strip_frontmatter(text.splitlines())
    out, h1_done = [], False
    for line in lines:
        s = line.strip()
        if s in (start, end):
            continue
        if not h1_done and re.match(r"^# ", line):
            h1_done = True
            continue
        out.append(line)
    # trim leading/trailing blank lines, collapse runs of >2 blanks
    body = "\n".join(out).strip("\n")
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body


# --- Notion escape rule -----------------------------------------------------
# Notion-flavored markdown treats `$...$` as inline math and `<tag>` as markup.
# Local files stay plain markdown; escaping happens only here, at push time:
#   - every `$` not already escaped  -> `\$`
#   - `<` followed by a letter or `/` (looks like a tag) -> `\<`
# Code spans and fenced code blocks are left untouched.
_DOLLAR = re.compile(r"(?<!\\)\$")
_TAGLIKE = re.compile(r"(?<!\\)<(?=[A-Za-z/])")


def _escape_text(s):
    s = _DOLLAR.sub(r"\\$", s)
    s = _TAGLIKE.sub(r"\\<", s)
    return s


def escape_for_notion(body):
    out, in_fence, fence = [], False, ""
    for line in body.split("\n"):
        m = re.match(r"^\s*(`{3,}|~{3,})", line)
        if m:
            if not in_fence:
                in_fence, fence = True, m.group(1)
            elif m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                in_fence = False
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        # split on inline code spans; escape only the non-code parts
        parts = re.split(r"(`+[^`]*`+)", line)
        out.append("".join(p if p.startswith("`") else _escape_text(p) for p in parts))
    return "\n".join(out)


def stage_reports_block(slug, facts):
    notion = read_kv(os.path.join(ROOT, "analyses", slug, ".notion"))
    blocks = ["## Stage Reports", "", STAGE_REPORTS_INTRO]
    for st in STAGE_ORDER:
        pid = notion.get(facts[st]["key"])
        if not pid:
            continue
        url = f"https://app.notion.com/p/{pid.replace('-', '')}"
        blocks += ["", f'<page url="{url}">', facts[st]["title"], "</page>"]
    for key in sorted(k for k in notion if re.match(r"^compare_\w+_page_id$", k)):
        url = f"https://app.notion.com/p/{notion[key].replace('-', '')}"
        title = notion.get(key[:-len("_id")] + "_title") or "Run comparison"
        blocks += ["", f'<page url="{url}">', title, "</page>"]
    return "\n".join(blocks)


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        fail("report has no YAML frontmatter")
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if v.startswith('"'):
                v = json.loads(v)
            fm[k] = v
    fail("report frontmatter is not closed with ---")


def properties(text):
    fm = parse_frontmatter(text)
    mapping = [
        ("Grade", "grade"),
        ("Grade driver", "grade_driver"),
        ("Technical Confidence", "technical_confidence"),
        ("Commercial Confidence", "commercial_confidence"),
        ("Status", "status"),
        ("date:Analysis Date:start", "analysis_date"),
    ]
    props, omitted = {}, []
    for prop, key in mapping:
        v = fm.get(key, "n/a")
        if v in ("", "n/a"):
            omitted.append(prop)
            continue
        props[prop] = _escape_text(v) if prop == "Grade driver" else v
    if "date:Analysis Date:start" in props:
        props["date:Analysis Date:is_datetime"] = 0
    return props, omitted


def main():
    args = [a for a in sys.argv[1:] if a != "--properties"]
    want_props = "--properties" in sys.argv[1:]
    if len(args) != 2:
        fail("usage: notion_body.py <slug> <stage> [--properties]")
    slug, stage_arg = args[0], args[1].lower()
    stage = ALIASES.get(stage_arg)
    if not stage:
        fail(f"unknown stage '{args[1]}' (expected one of: {', '.join(sorted(set(ALIASES)))})")
    facts = load_stage_facts()
    f = facts[stage]
    path = os.path.join(ROOT, "analyses", slug, f["file"])
    if not os.path.exists(path):
        fail(f"{path} not found")
    text = open(path, encoding="utf-8").read()
    is_exec = stage == "5"
    if want_props:
        if not is_exec:
            fail("--properties is only valid for the executive stage")
        props, omitted = properties(text)
        print(json.dumps(props, ensure_ascii=False, indent=2))
        if omitted:
            print("OMITTED: " + ", ".join(omitted), file=sys.stderr)
        return
    body = escape_for_notion(strip_structure(text, f["start"], f["end"]))
    if is_exec:
        body = body + "\n\n" + stage_reports_block(slug, facts)
    sys.stdout.write(body + "\n")


if __name__ == "__main__":
    main()
