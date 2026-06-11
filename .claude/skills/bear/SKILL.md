---
name: Bear
description: Run the Bear stage for the current analysis. Generates rival readings against the Bull thesis.
disable-model-invocation: true
context: fork
model: claude-opus-4-6
allowed-tools: Read Write Bash mcp__notion__notion-create-pages mcp__notion__notion-update-page
---

## Current analysis
!`cat analyses/.current 2>/dev/null || echo "ERROR: No current analysis. Run /research first."`

## Required reading

Before continuing, use the Read tool to read the following (substitute the slug from
"Current analysis" above):
- `analyses/{slug}/01_research_collector_summary.md` — if missing, stop and report:
  "ERROR: Research summary not found."
- `analyses/{slug}/02a_science_advisor_full.md` — if missing, proceed without it.
- `analyses/{slug}/02b_investment_advisor_full.md` — if missing, proceed without it.
- `analyses/{slug}/02c_political_advisor_full.md` — if missing, proceed without it.
- `analyses/{slug}/03_bull_full.md` — if missing, stop and report:
  "ERROR: Bull output not found. Run /bull first."

## Optional deal materials

For deal analyses, also check `analyses/{slug}/00_deal_materials/manifest.md`.
If it exists, use the Read tool to read it, then read EVERY exhibit file
listed in it (image or doc, paths relative to `00_deal_materials/`),
regardless of which advisor it was routed to. Your job here is to check
whether the Bull case and the advisors' readings of a given chart, table, or
legal document actually match what the source shows — discrepancies between
a synthesized claim and the underlying exhibit are exactly the kind of thing
this stage exists to catch. If `manifest.md` does not exist, proceed without
it.

## Your task

You are the Bear for the company identified in the current analysis above.

All advisor outputs and the full Bull thesis are the files you just read. Apply
counterinduction to everything — the scientific assessment, investment analysis,
political analysis, and especially the Bull case.

For each major Bull claim: what does the same evidence look like if the
bearish thesis is true?

Cover:
- The single most important thing the Bull case is getting wrong
- Which risks were underweighted and why
- What "failing gracefully" looks like — the outcome where everyone later says
  "it was promising but..."
- What evidence would make you update toward the Bull's position
- Where the advisors may be overweighting positive signals
- If you read exhibits from `00_deal_materials/manifest.md`: any cases where
  the Bull case or an advisor's reading of a specific chart, table, or
  document doesn't match what the source actually shows

Do not soften your critique. Give the strongest bear thesis.

## Output instructions

Read the slug from the current analysis above. Write one file:

**File:** `analyses/{slug}/04_bear_full.md`
[BEAR_START]
<your full bear analysis>
[BEAR_END]

## Notion sync

See `CLAUDE.md`'s "Notion sync" section for full conventions. If
`mcp__notion__*` tools aren't available, state this in your summary
(e.g. "Notion sync skipped — `notion` MCP not configured; run
/notion-sync once it is") rather than failing silently.

Read `analyses/{slug}/.notion`. If it has no `main_page_id`, skip this
section and note in your summary: "Notion sync skipped — run /research
first to enable it (or /notion-sync to bootstrap and catch up in one go)."

Otherwise, take `04_bear_full.md`, strip the H1 title line and the
`[BEAR_START]`/`[BEAR_END]` delimiter lines, then:

- If `.notion` already has `stage4_page_id`, call `notion-update-page` with
  `page_id` = that id, `command: replace_content`, `new_str` = the stripped
  content.
- Otherwise, call `notion-create-pages` with `parent: {"type": "page_id",
  "page_id": main_page_id}`, `properties.title` = "Stage 4: Bear Case",
  `content` = the stripped content. Append the returned page id to
  `.notion` as `stage4_page_id="..."`.

If the Notion call fails, state this clearly in your summary (e.g. "Notion
sync failed: <error> — run /notion-sync to retry") rather than burying it —
but don't block; the markdown output is the source of truth.
