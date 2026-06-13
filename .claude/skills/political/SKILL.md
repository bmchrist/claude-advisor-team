---
name: Political Advisor
description: Run the Political Advisor stage for the current analysis.
disable-model-invocation: true
context: fork
model: claude-sonnet-4-6
allowed-tools: Read Write Bash mcp__notion__notion-create-pages mcp__notion__notion-update-page
argument-hint: "[company-or-slug]"
arguments: target
---

## Setup

```!
python3 scripts/resolve_target.py "$target"
```

If Setup printed an ERROR line, stop and report it to Ben verbatim.

## Required reading

Before continuing, use the Read tool to read `analyses/{slug}/01_research_collector_full.md`
(substitute the slug from "Setup" above). If the file does not exist, stop
and report: "ERROR: Research output not found. Run /research first."

## Optional deal materials

For deal analyses, also check `analyses/{slug}/00_deal_materials/manifest.md`.
If it exists, use the Read tool to read it, then read every exhibit file
(image or doc, paths relative to `00_deal_materials/`) whose `route_to`
column includes "Political Advisor" — these are regulatory filings, permits,
and policy/legal exhibits provided directly, which let you review them
rather than relying on a prose summary. If `manifest.md` does not exist,
proceed without it; this is normal for non-deal analyses or analyses that
haven't been through `/ingest-materials`.

## Your task

You are the Political Advisor for the company identified in the current analysis above.

The Research Collector briefing is the file you just read. Analyze political and
regulatory risk. Be direct.

Cover:
1. Regulatory framework stability — policy / PPA / permit structure and
   political continuity risk
2. Country/jurisdiction risk — realistic downside if political environment shifts
3. Stakeholder map — who benefits, who loses, who can block or undermine this?
4. US political context if relevant — ITC / PTC / IRA / tariff exposure
5. For African market deals: PPA enforcement track record, utility
   creditworthiness, currency repatriation mechanics, permitting culture
   vs. law on paper
6. Counterinduction: what does this look like if political tailwinds reverse
   in the next 3-5 years?

## Output instructions

Read the slug from the current analysis above. Write two files:

**File 1:** `analyses/{slug}/02c_political_advisor_full.md`
[ANALYSIS_START]
<your full political and regulatory analysis>
[ANALYSIS_END]

**File 2:** `analyses/{slug}/02c_political_advisor_summary.md`
[SUMMARY_START]
(a) Key conclusions:
- <bullet>
- <bullet>
- <bullet>

(b) Key rival reading:
<the most important bearish interpretation of the political/regulatory picture>

(c) Evidence that would change your assessment:
<specific and falsifiable>
[SUMMARY_END]

## Notion sync

See `CLAUDE.md`'s "Notion sync" section for full conventions. If
`mcp__notion__*` tools aren't available, state this in your summary
(e.g. "Notion sync skipped — `notion` MCP not configured; run
/notion-sync once it is") rather than failing silently.

Read `analyses/{slug}/.notion`. If it has no `main_page_id`, skip this
section and note in your summary: "Notion sync skipped — run /research
first to enable it (or /notion-sync to bootstrap and catch up in one go)."

Otherwise, take `02c_political_advisor_full.md`, strip the H1 title line and the
`[ANALYSIS_START]`/`[ANALYSIS_END]` delimiter lines, then:

- If `.notion` already has `stage2c_page_id`, call `notion-update-page` with
  `page_id` = that id, `command: replace_content`, `new_str` = the stripped
  content.
- Otherwise, call `notion-create-pages` with `parent: {"type": "page_id",
  "page_id": main_page_id}`, `properties.title` = "Stage 2c: Political & Regulatory Risk Analysis",
  `content` = the stripped content. Append the returned page id to
  `.notion` as `stage2c_page_id="..."`.

If the Notion call fails, state this clearly in your summary (e.g. "Notion
sync failed: <error> — run /notion-sync to retry") rather than burying it —
but don't block; the markdown output is the source of truth.
