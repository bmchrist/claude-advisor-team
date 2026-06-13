---
name: Bull
description: Run the Bull stage for the current analysis. Steelmans the investment thesis using advisor outputs.
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

Before continuing, use the Read tool to read the following (substitute the slug from
"Setup" above):
- `analyses/{slug}/01_research_collector_summary.md` — if missing, stop and report:
  "ERROR: Research summary not found."
- `analyses/{slug}/02a_science_advisor_full.md` — if missing, proceed without it
  (Science Advisor hasn't run).
- `analyses/{slug}/02b_investment_advisor_full.md` — if missing, proceed without it
  (Investment Advisor hasn't run).
- `analyses/{slug}/02c_political_advisor_full.md` — if missing, proceed without it
  (Political Advisor hasn't run).

Note: Bull does not read `analyses/{slug}/00_deal_materials/manifest.md`
directly. By design, each advisor above has already read the exhibits
routed to it and incorporated them into its analysis, so Bull works from
their synthesized outputs rather than re-reading source exhibits.

## Your task

You are the Bull for the company identified in the current analysis above.

All available advisor outputs are the files you just read. Build the strongest
possible case for this investment. Steelman it — find the version of the thesis
that a sophisticated, non-naive optimist would make.

Cover:
- What "winning" looks like and the realistic timeline
- The key evidence that supports the bull case
- Which risks are real but manageable, and why
- What the base rate for similar opportunities says, and why this beats it
- Where the advisors may be underweighting positive signals

Do not hedge on behalf of the bear. Give the strongest bull thesis.

## Output instructions

Read the slug from the current analysis above. Write one file:

**File:** `analyses/{slug}/03_bull_full.md`
[BULL_START]
<your full bull analysis>
[BULL_END]

## Notion sync

See `CLAUDE.md`'s "Notion sync" section for full conventions. If
`mcp__notion__*` tools aren't available, state this in your summary
(e.g. "Notion sync skipped — `notion` MCP not configured; run
/notion-sync once it is") rather than failing silently.

Read `analyses/{slug}/.notion`. If it has no `main_page_id`, skip this
section and note in your summary: "Notion sync skipped — run /research
first to enable it (or /notion-sync to bootstrap and catch up in one go)."

Otherwise, take `03_bull_full.md`, strip the H1 title line and the
`[BULL_START]`/`[BULL_END]` delimiter lines, then:

- If `.notion` already has `stage3_page_id`, call `notion-update-page` with
  `page_id` = that id, `command: replace_content`, `new_str` = the stripped
  content.
- Otherwise, call `notion-create-pages` with `parent: {"type": "page_id",
  "page_id": main_page_id}`, `properties.title` = "Stage 3: Bull Case",
  `content` = the stripped content. Append the returned page id to
  `.notion` as `stage3_page_id="..."`.

If the Notion call fails, state this clearly in your summary (e.g. "Notion
sync failed: <error> — run /notion-sync to retry") rather than burying it —
but don't block; the markdown output is the source of truth.
