# Notion Sync — Reference Procedures

Canonical procedures for mirroring pipeline outputs to Notion. Every
pipeline skill's `## Notion sync` section (except `/ingest-materials`,
which doesn't sync) points here instead of repeating this content. See
`CLAUDE.md`'s "Notion sync" section for the MCP prerequisite and database
schema; this file covers the *procedures*, canonical wording, and the
stage-facts table.

## Skip / failure wording (canonical)

Use these exact messages so skip/failure reporting is consistent across
stages:

- **MCP not configured** (`mcp__notion__*` tools not available): skip the
  entire Notion sync section and note in your summary: "Notion sync
  skipped — `notion` MCP not configured; run /notion-sync once it is."
- **No `main_page_id` yet** (any stage except research, which bootstraps
  it): skip and note: "Notion sync skipped — run /research first to enable
  it (or /notion-sync to bootstrap and catch up in one go)."
- **A Notion call fails**: state it plainly in your summary: "Notion sync
  failed: <error> — run /notion-sync to retry." Never fail silently and
  never block on this — the markdown/JSON outputs remain the source of
  truth.

## Preconditions (check before any procedure below)

Run these gates, in order, before "Bootstrap main page", "Stage sub-page
push", or "Executive update-in-place". If a gate trips, do **not** call any
Notion tool — emit the matching line from "Skip / failure wording" above and
end the sync section:

1. If `mcp__notion__*` tools are not available → skip (MCP-not-configured
   message).
2. Read `analyses/{slug}/.notion`. If `main_page_id` is absent → skip
   (no-`main_page_id` message). **Exception:** `/research` and `/notion-sync`
   do not skip here — when `main_page_id` is absent and
   `01_research_collector_full.md` exists, they run "Bootstrap main page"
   first and then continue.

## Stage facts table

| Stage | File | Delimiters | Sub-page title | `.notion` key |
|---|---|---|---|---|
| 1 | `01_research_collector_full.md` | `[RC_FULL_START]` / `[RC_FULL_END]` | Stage 1: Research Collector Briefing | `stage1_page_id` |
| 2a | `02a_science_advisor_full.md` | `[ANALYSIS_START]` / `[ANALYSIS_END]` | Stage 2a: Science Advisor Assessment | `stage2a_page_id` |
| 2b | `02b_investment_advisor_full.md` | `[ANALYSIS_START]` / `[ANALYSIS_END]` | Stage 2b: Investment Advisor Assessment | `stage2b_page_id` |
| 2c | `02c_political_advisor_full.md` | `[ANALYSIS_START]` / `[ANALYSIS_END]` | Stage 2c: Political & Regulatory Risk Analysis | `stage2c_page_id` |
| 3 | `03_bull_full.md` | `[BULL_START]` / `[BULL_END]` | Stage 3: Bull Case | `stage3_page_id` |
| 4 | `04_bear_full.md` | `[BEAR_START]` / `[BEAR_END]` | Stage 4: Bear Case | `stage4_page_id` |

Stage 5 (Executive) has no sub-page — it updates the main page in place; see
"Executive update-in-place" below.

## Procedure: Bootstrap main page (research / notion-sync only)

Run this only when `analyses/{slug}/.notion` is missing `main_page_id`.

1. Call `notion-create-pages` with `parent: {"type": "data_source_id",
   "data_source_id": "8a829f17-bcb4-49d0-8562-26a0e6342df1"}` and:
   - `properties.title` = company name (from `analyses/{slug}/.meta`)
   - `properties.Slug` = slug
   - `properties.Type` = type (from `analyses/{slug}/.meta`)
   - `properties["date:Analysis Date:start"]` = today's date (YYYY-MM-DD)
   - `properties["date:Analysis Date:is_datetime"]` = `0`
   - `content` = the placeholder block:
     ```
     > **Grade: pending**
     > Run /executive to populate the grade, scorecard, and narrative.

     ## Executive Narrative
     _Pending — run /executive to populate this analysis._

     ## Stage Reports
     Full write-ups for each pipeline stage are linked as sub-pages below.
     ```
2. Write the returned page id and url to `analyses/{slug}/.notion` as
   `main_page_id="..."` / `main_page_url="..."` (creating the file if
   needed), before doing anything else. Everything before `## Stage
   Reports` is a placeholder that `/executive`'s "Executive
   update-in-place" procedure replaces wholesale later.

## Procedure: Stage sub-page push

For the stage identified by your skill's row in the stage-facts table:

1. Read the stage's `_full.md` file, strip the H1 title line and the row's
   delimiter lines — the page title comes from `properties.title`, and the
   delimiters are fork-handoff markers, not content. Markdown tables in the
   body are fine; `notion-create-pages` renders them.
2. If `.notion` already has the row's `.notion` key (re-run), call
   `notion-update-page` with `page_id` = that id, `command: replace_content`,
   `new_str` = the stripped content. These sub-pages have no children, so
   this is always safe.
3. Otherwise, call `notion-create-pages` with `parent: {"type": "page_id",
   "page_id": main_page_id}`, `properties.title` = the row's sub-page title,
   `content` = the stripped content. Write the returned page id to `.notion`
   under the row's key.

## Procedure: Executive update-in-place

Executive (and `/notion-sync` when `05_executive_data.json` /
`05_executive_narrative.md` exist) updates the main page rather than
creating a sub-page.

1. `notion-update-page` `command: update_properties` on `main_page_id`:
   - `Grade` = letter grade
   - `Grade driver` = one-sentence grade driver
   - `Status` = investment status (INVEST/TRACK/INVESTIGATE/PASS)
   - `date:Analysis Date:start` = today's date (YYYY-MM-DD)
   - `date:Analysis Date:is_datetime` = `0`
2. `notion-fetch` the main page. Take everything from the start of its
   content up to (not including) `## Stage Reports` as `old_str`. Build
   `new_str`:
   ```
   > **Grade {grade} · {status}**
   > {grade_driver}
   > _Status rule: {status_reason}_

   ## Executive Narrative
   {four narrative paragraphs, separated by blank lines}

   ## Scorecard
   {markdown table: Dimension | Bear | Central | Bull | Driver — one row
   per scored dimension}

   ## The Crux
   {crux}

   ## Catalysts & Triggers
   {markdown table: Event | Expected window | Scorecard rows moved | Flips to | Source stage — one row per `catalysts` entry}

   ## Sourcing Strength
   {sourcing_strength rollup line, or its 2-3 row table}

   ## Deal Terms & Price Sensitivity
   {deal_terms paragraph — DEAL analyses only; omit this heading entirely for non-DEAL}

   ## Values & Judgment Flags
   {one bullet per values_flags checklist item — subsidy dependence, dual-use/weapons adjacency, safety/environmental-justice exposure, governance, plus any extra flags — each stated flag-or-clear}

   ## What Would Change This
   {evidence-to-change items, bulleted}

   ## Next Actions
   {next-action items, bulleted}
   ```
   Call `notion-update-page` with `page_id` = `main_page_id`,
   `command: update_content`, one `content_updates` entry with this
   `old_str`/`new_str` pair. Leave `## Stage Reports` and everything after
   it untouched — that section lists the stage sub-pages as child pages,
   and `replace_content` there would delete them.

## Summary line

On any successful sync (bootstrap, sub-page push, or executive
update-in-place), end your stage's summary with a line:
`Notion: {main_page_url}` — so Ben always has a direct link to the
analysis, not just a "synced" confirmation. Omit this line if sync was
skipped or failed (use the skip/failure wording above instead).

## Performance notes

- Push time scales with block count, not file content size — long single
  paragraphs push faster than the same word count split across many list
  items or table rows.
- Push pages one at a time; don't try to batch multiple pages into one
  `notion-create-pages` call, so a failure on one page doesn't affect
  others.
- On automated/scheduled runs, skip post-push verification reads
  (`notion-fetch` to confirm content landed) — they roughly double sync
  time for negligible benefit. Verify manually only when debugging a sync
  issue.
