---
name: Notion Sync
description: Push or re-push one or all stages of the current analysis to Notion from its local outputs, without re-running any pipeline stage. Accepts an optional stage filter to re-push only one stage. Use after a sync failure or to bring a specific stage up to date.
disable-model-invocation: true
context: fork
model: claude-sonnet-4-6
allowed-tools: Read Write Bash mcp__notion__notion-create-pages mcp__notion__notion-update-page mcp__notion__notion-fetch
argument-hint: "[company-or-slug] [stage]"
arguments: target stage
---

## Argument parsing

`$stage` (optional) names a single stage to sync. Accepted values
(case-insensitive): `research` / `1`, `science` / `2a`, `investment` / `2b`,
`political` / `2c`, `bull` / `3`, `bear` / `4`, `executive` / `5`.
If `$stage` is empty, sync all stages.

Edge case: if `$target` is itself a stage keyword and `$stage` is empty, treat
`$target` as the stage filter and use an empty company string (Setup will fall
back to `.last_target`).

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
'Notion sync' section, then re-run /notion-sync." Don't attempt any of the
steps below.

## Your task

Canonical procedures live in `.claude/skills/notion-sync/REFERENCE.md`.
Substitute `{slug}` from Setup throughout.

Read `analyses/{slug}/.notion` if it exists. Treat a missing file or any
missing field as "not yet synced" rather than an error.

### Step 0 — determine what to sync

Set `stage_filter` from the parsed stage argument (or `all` if none).

Build the work list — the exact set of items you will attempt:

| stage_filter | Work list |
|---|---|
| `all` | bootstrap + stages 1, 2a, 2b, 2c, 3, 4 + executive |
| `executive` or `5` | bootstrap + executive only |
| `research` or `1` | bootstrap + stage 1 only |
| `science` or `2a` | bootstrap + stage 2a only |
| `investment` or `2b` | bootstrap + stage 2b only |
| `political` or `2c` | bootstrap + stage 2c only |
| `bull` or `3` | bootstrap + stage 3 only |
| `bear` or `4` | bootstrap + stage 4 only |

Every item **not** on the work list must appear in the output table as
`skipped — stage filter active`. Do not call any Notion tool for those items.

### Step 1 — Bootstrap / verify main page

Always on the work list. If `main_page_id` is missing:
- If `analyses/{slug}/01_research_collector_full.md` does not exist, stop —
  report: "Nothing to sync — run /research first."
- Otherwise follow REFERENCE.md's "Bootstrap main page" procedure
  (company/slug/type from `analyses/{slug}/.meta`, date = today).

If `main_page_id` is present, `notion-fetch` it to confirm it is reachable.
If unreachable, stop and report: "Notion sync failed — main page
`{main_page_id}` is unreachable (deleted or moved?). Remove `main_page_id`
and any `stageN_page_id` fields from `analyses/{slug}/.notion` and re-run
/notion-sync." Do not attempt sub-pages against an unreachable parent.

### Step 2 — Stage sub-pages

For each stage on the work list (1, 2a, 2b, 2c, 3, 4 — not executive):
follow REFERENCE.md's "Stage sub-page push" procedure if the file exists,
or mark `skipped — no local file` if it does not.

### Step 3 — Executive sync

If `executive` is on the work list and both
`analyses/{slug}/05_executive_data.json` and
`analyses/{slug}/05_executive_narrative.md` exist, follow REFERENCE.md's
"Executive update-in-place" procedure, reading all inputs from those two
files. If either file is missing, mark `skipped — no local file`.

## Output

Report a table with one row per item attempted (bootstrap/main page, stages
1/2a/2b/2c/3/4, executive), each marked `created`, `updated`,
`skipped — no local file`, `skipped — stage filter active`, or
`error: <message>`.

Update `analyses/{slug}/.notion` incrementally as each push succeeds, so a
re-run of `/notion-sync` only needs to retry whatever is still
missing/failed. If any call errors, state it plainly in the table and in a
one-line summary — don't bury it — but keep going with the remaining rows.
End with `Notion: {main_page_url}` if `main_page_id` is set.
