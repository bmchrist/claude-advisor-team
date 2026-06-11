---
name: Notion Sync
description: Push or re-push the current analysis to Notion from its local outputs, without re-running any pipeline stage. Use after a stage reported a Notion sync failure, or to bring an older analysis up to date.
disable-model-invocation: true
context: fork
allowed-tools: Read Write Bash mcp__notion__notion-create-pages mcp__notion__notion-update-page mcp__notion__notion-fetch
argument-hint: "[company-or-slug]"
arguments: target
---

## Setup

```!
python3 scripts/resolve_target.py "$target"
```

If Setup printed an ERROR line, stop and report it to Ben verbatim.

## Today's date
!`date +%Y-%m-%d`

## Prerequisite

If `mcp__notion__*` tools aren't available, stop here and report: "Notion
sync unavailable — the `notion` MCP server isn't configured. See CLAUDE.md's
'Notion sync' > 'Prerequisite' section, then re-run /notion-sync." Don't
attempt any of the steps below.

## Your task

Catch up Notion sync for the analysis named in "Setup" above
(substitute `{slug}` throughout below). For full conventions — database
schema, page titles, stripping rules, content templates — see CLAUDE.md's
"Notion sync" section. This skill applies the same logic each pipeline stage
uses for its own sync step, but unconditionally: it (re-)pushes anything
whose local output exists, whether or not a previous attempt succeeded.

Read `analyses/{slug}/.notion` if it exists. Treat a missing file, or any
missing field within it, as "not yet synced" rather than an error.

### 1. Bootstrap / verify main page

If `main_page_id` is missing:
- If `analyses/{slug}/01_research_collector_full.md` does not exist, stop —
  there is nothing to sync yet. Report: "Nothing to sync — run /research
  first."
- Otherwise, bootstrap exactly as `/research` does: call
  `notion-create-pages` with `parent: {"type": "data_source_id",
  "data_source_id": "8a829f17-bcb4-49d0-8562-26a0e6342df1"}` and:
  - `properties.title` = company name (from `analyses/{slug}/.meta`)
  - `properties.Slug` = the slug
  - `properties.Type` = type (from `analyses/{slug}/.meta`)
  - `properties["date:Analysis Date:start"]` = today's date (YYYY-MM-DD)
  - `properties["date:Analysis Date:is_datetime"]` = `0`
  - `content` = the standard placeholder block:
    ```
    > **Grade: pending**
    > Run /executive to populate the grade, scorecard, and narrative.

    ## Executive Narrative
    _Pending — run /executive to populate this analysis._

    ## Stage Reports
    Full write-ups for each pipeline stage are linked as sub-pages below.
    ```
  Write the returned page id and url to `analyses/{slug}/.notion` as
  `main_page_id="..."` / `main_page_url="..."` (creating the file if needed).

If `main_page_id` is already present, call `notion-fetch` on it to confirm
the page is reachable. If the fetch fails (page deleted or moved), stop and
report: "Notion sync failed — main page `{main_page_id}` is unreachable
(deleted or moved?). To re-bootstrap, remove `main_page_id` and any
`stageN_page_id` fields from `analyses/{slug}/.notion` and re-run
/notion-sync." Do not attempt sub-pages against an unreachable parent.

### 2. Stage sub-pages (1, 2a, 2b, 2c, 3, 4)

For each row below whose file exists under `analyses/{slug}/`, push it. Skip
rows whose file doesn't exist — that stage just hasn't run yet.

| Stage | File | Delimiters to strip | Sub-page title | `.notion` key |
|---|---|---|---|---|
| 1 | `01_research_collector_full.md` | `[RC_FULL_START]` / `[RC_FULL_END]` | Stage 1: Research Collector Briefing | `stage1_page_id` |
| 2a | `02a_science_advisor_full.md` | `[ANALYSIS_START]` / `[ANALYSIS_END]` | Stage 2a: Science Advisor Assessment | `stage2a_page_id` |
| 2b | `02b_investment_advisor_full.md` | `[ANALYSIS_START]` / `[ANALYSIS_END]` | Stage 2b: Investment Advisor Assessment | `stage2b_page_id` |
| 2c | `02c_political_advisor_full.md` | `[ANALYSIS_START]` / `[ANALYSIS_END]` | Stage 2c: Political & Regulatory Risk Analysis | `stage2c_page_id` |
| 3 | `03_bull_full.md` | `[BULL_START]` / `[BULL_END]` | Stage 3: Bull Case | `stage3_page_id` |
| 4 | `04_bear_full.md` | `[BEAR_START]` / `[BEAR_END]` | Stage 4: Bear Case | `stage4_page_id` |

For each existing file:
1. Read it, strip the H1 title line and the listed delimiter lines.
2. If `.notion` already has that row's `.notion` key, call
   `notion-update-page` with `page_id` = that id, `command: replace_content`,
   `new_str` = the stripped content.
3. Otherwise, call `notion-create-pages` with `parent: {"type": "page_id",
   "page_id": main_page_id}`, `properties.title` = the title above, `content`
   = the stripped content. Write the returned page id to `.notion` under the
   listed key.

### 3. Executive sync

If both `analyses/{slug}/05_executive_data.json` and
`analyses/{slug}/05_executive_narrative.md` exist, run the same sync
`/executive` does:

1. `notion-update-page` `command: update_properties` on `main_page_id`:
   `Grade`, `Grade driver`, `Status` (from the JSON), and refresh
   `date:Analysis Date:start` to today with `date:Analysis Date:is_datetime`
   = `0`.
2. `notion-fetch` the main page, take everything from the start of its
   content up to (not including) `## Stage Reports` as `old_str`. Build
   `new_str` from the JSON + narrative file: Grade callout + Executive
   Narrative + Scorecard table (Dimension | Bear | Central | Bull | Driver,
   one row per entry in `scores`) + The Crux + Values & Judgment Flags +
   What Would Change This + Next Actions. Call `notion-update-page`
   `command: update_content` with this `old_str`/`new_str` pair. Leave
   `## Stage Reports` and everything after it untouched.

If either file is missing, skip this step — Executive hasn't run yet.

## Output

Report a table with one row per item attempted (bootstrap/main page, stages
1/2a/2b/2c/3/4, executive), each marked `created`, `updated`,
`skipped — no local file`, `skipped — already in sync` (only if you can tell
without an API call, otherwise treat as `updated`), or `error: <message>`.

Update `analyses/{slug}/.notion` incrementally as each push succeeds, so a
re-run of `/notion-sync` only needs to retry whatever is still
missing/failed. If any call errors, state it plainly in the table and in a
one-line summary — don't bury it — but keep going with the remaining rows.
