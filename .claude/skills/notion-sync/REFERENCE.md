# Notion Sync — Reference Procedures

Canonical procedures for mirroring pipeline outputs to Notion. Every
pipeline skill's `## Notion sync` section (except `/ingest-materials`,
which doesn't sync) points here instead of repeating this content. See
`CLAUDE.md`'s "Notion sync" section for the MCP prerequisite and database
schema; this file covers the *procedures*, canonical wording, and the
stage-facts table.

## Writing `.notion`

Never edit `analyses/{slug}/.notion` with the Write tool or a shell
redirect. The three advisors run in parallel and each adds its own key,
so an unlocked read-modify-write can silently drop another stage's page
id. Every write goes through
`python3 scripts/notion_state.py set {slug} <key> <value> [<key> <value> ...]`,
which takes an `fcntl` lock and replaces the file atomically. Reading the
file directly is fine.

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
  never block on this — the local markdown outputs remain the source of
  truth.

## Preconditions (check before any procedure below)

Run these gates, in order, before "Bootstrap main page", "Stage sub-page
push", or "Main-page push". If a gate trips, do **not** call any
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
| 5 | `05_executive_report.md` | `[REPORT_START]` / `[REPORT_END]` | (main page) | `main_page_id` |
| 6 | `06_run_comparison.md` | `[COMPARISON_START]` / `[COMPARISON_END]` | Run comparison: {base_date} → {head_date} | `compare_{YYYYMMDD}_page_id` |

Stage 5 (Executive) has no sub-page. Its report body *is* the main page's
content above `## Stage Reports`; see "Main-page push" below.
`scripts/notion_body.py` parses this table for file names, delimiters,
sub-page titles and `.notion` keys, so keep its column layout intact.

Stage 6 (run comparison, re-runs only) is a sub-page like stages 1–4, but
one is created per re-run, so its key and title are dated. The real values
are in `06_run_comparison.md`'s frontmatter (`notion_key`, `notion_title`).
When you record its page id, also record the title, so the main-page push
can link the page:
`python3 scripts/notion_state.py set {slug} <notion_key> <id> <notion_key minus _id>_title "<notion_title>"`.
For example, `compare_20261201_page_id` is paired with
`compare_20261201_page_title`.

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
2. Record the returned page id and url before doing anything else:
   `python3 scripts/notion_state.py set {slug} main_page_id <id> main_page_url <url>`
   (it creates `.notion` if needed). Everything before `## Stage
   Reports` is a placeholder that "Main-page push" replaces wholesale
   later.

## Escaping for Notion

Notion-flavored markdown renders `$…$` as inline math and `<tag>` as
markup. Local files stay plain markdown (`$` is written as `$`); escaping
happens **only at push time, only in `scripts/notion_body.py`**:

- every `$` not already escaped → `\$`
- `<` immediately followed by a letter or `/` → `\<`
- code spans and fenced code blocks are left untouched

Never hand-escape a body, and never paste a `_full.md` or report file into
a Notion call directly. Always push the script's output. (Notion's fetch
output shows its own escapes, like `\$`, `\~`, `\_` and `\[`. That is
display encoding, not something to copy into pushes.)

## Procedure: Stage sub-page push

For the stage identified by your skill's row in the stage-facts table:

1. Run `python3 scripts/notion_body.py {slug} {stage}` (stage = `1`, `2a`,
   `2b`, `2c`, `3` or `4`). It prints the push payload: the H1 title line
   and the row's delimiter lines stripped, the escape rule applied. Use
   its stdout **verbatim** as the content below. If it prints a line
   starting `ERROR:`, report it with the failure wording and stop.
2. If `.notion` already has the row's `.notion` key (re-run), call
   `notion-update-page` with `page_id` = that id, `command: replace_content`,
   `new_str` = the payload. These sub-pages have no children, so this is
   always safe.
3. Otherwise, call `notion-create-pages` with `parent: {"type": "page_id",
   "page_id": main_page_id}`, `properties.title` = the row's sub-page title,
   `content` = the payload. Record the returned page id with
   `python3 scripts/notion_state.py set {slug} <row's key> <id>`.

## Procedure: Main-page push

Executive (and `/notion-sync` when `05_executive_report.md` exists) updates
the main page from `analyses/{slug}/05_executive_report.md`. The report's
layout is defined once, in `.claude/skills/executive/SKILL.md`'s Output
instructions. This procedure copies it and never rebuilds it.

1. **Properties.** Run
   `python3 scripts/notion_body.py {slug} executive --properties`. It
   prints a JSON object built from the report's frontmatter with all seven
   properties: `Grade`, `Grade driver` (escaped), `Technical Confidence`,
   `Commercial Confidence`, `Status`, `date:Analysis Date:start` =
   `analysis_date` (**not today**: re-syncing an old analysis must not
   make it look new), and `date:Analysis Date:is_datetime` = `0` (the
   number, not a boolean). Call `notion-update-page`
   `command: update_properties` on `main_page_id` with that object as
   `properties`, unchanged, in a single call.

   A frontmatter value of `n/a` (older analyses migrated by
   `scripts/migrate_exec_report.py`) means "not assessed". The script
   leaves those properties out and names them in an `OMITTED:` line. Note
   them in the summary. If the API rejects a property, note it explicitly
   and retry without it.
2. **Content.** Run `python3 scripts/notion_body.py {slug} executive`. Its
   output is the report body (frontmatter, H1 and markers stripped,
   escaped). It already ends with `## Stage Reports` and one `<page url>`
   block per `stage*_page_id` in `.notion`, then one per run-comparison
   page (`compare_*_page_id`), generated from state. Call
   `notion-update-page` with `page_id` = `main_page_id`,
   `command: replace_content`, `new_str` = that output **verbatim**. Don't
   edit it, add links from memory, or set `allow_deleting_content`. If
   Notion refuses because child pages would be deleted, report the listed
   pages with the failure wording and stop. That means `.notion` is out of
   step with Notion. Don't retry.

   (Why `replace_content` and not `update_content`: `update_content` needs
   an exact `old_str` match against fetched text, and fetch output carries
   its own escapes, so the match is unreliable. `replace_content` is only
   dangerous when a child `<page>` tag is omitted, and generating the tags
   from `.notion` removes that risk.)
3. **Check the sub-pages.** `notion-fetch` the main page once and confirm
   every `stage*_page_id` and `compare_*_page_id` in `.notion` appears (dashes removed) in a
   `<page url>` under `## Stage Reports`. If one is missing, report it: the
   page is recoverable from Notion's trash, and `/notion-sync` can re-push
   it. This check is the exception to "skip post-push verification reads"
   below, because this is the one page with children.

## Summary line

On any successful sync (bootstrap, sub-page push, or main-page push), end your stage's summary with a line:
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
