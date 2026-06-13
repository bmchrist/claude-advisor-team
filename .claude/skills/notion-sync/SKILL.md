---
name: Notion Sync
description: Push or re-push the current analysis to Notion from its local outputs, without re-running any pipeline stage. Use after a stage reported a Notion sync failure, or to bring an older analysis up to date.
disable-model-invocation: true
context: fork
model: claude-sonnet-4-6
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
'Notion sync' section, then re-run /notion-sync." Don't attempt any of the
steps below.

## Your task

Catch up Notion sync for the analysis named in "Setup" above (substitute
`{slug}` throughout below). Canonical procedures, the stage-facts table, and
skip/failure wording live in `.claude/skills/notion-sync/REFERENCE.md` — this
skill applies them unconditionally: it (re-)pushes anything whose local
output exists, whether or not a previous attempt succeeded.

Read `analyses/{slug}/.notion` if it exists. Treat a missing file, or any
missing field within it, as "not yet synced" rather than an error.

### 1. Bootstrap / verify main page

If `main_page_id` is missing:
- If `analyses/{slug}/01_research_collector_full.md` does not exist, stop —
  report: "Nothing to sync — run /research first."
- Otherwise, follow REFERENCE.md's "Bootstrap main page" procedure
  (company/slug/type from `analyses/{slug}/.meta`, date = today from above).

If `main_page_id` is already present, call `notion-fetch` on it to confirm
the page is reachable. If the fetch fails (page deleted or moved), stop and
report: "Notion sync failed — main page `{main_page_id}` is unreachable
(deleted or moved?). To re-bootstrap, remove `main_page_id` and any
`stageN_page_id` fields from `analyses/{slug}/.notion` and re-run
/notion-sync." Do not attempt sub-pages against an unreachable parent.

### 2. Stage sub-pages (1, 2a, 2b, 2c, 3, 4)

For each row in REFERENCE.md's stage-facts table whose file exists under
`analyses/{slug}/`, follow REFERENCE.md's "Stage sub-page push" procedure for
that row. Skip rows whose file doesn't exist — that stage just hasn't run
yet.

### 3. Executive sync

If both `analyses/{slug}/05_executive_data.json` and
`analyses/{slug}/05_executive_narrative.md` exist, follow REFERENCE.md's
"Executive update-in-place" procedure, sourcing its inputs from the JSON and
narrative file. If either is missing, skip — Executive hasn't run yet.

## Output

Report a table with one row per item attempted (bootstrap/main page, stages
1/2a/2b/2c/3/4, executive), each marked `created`, `updated`,
`skipped — no local file`, `skipped — already in sync` (only if you can tell
without an API call, otherwise treat as `updated`), or `error: <message>`.

Update `analyses/{slug}/.notion` incrementally as each push succeeds, so a
re-run of `/notion-sync` only needs to retry whatever is still
missing/failed. If any call errors, state it plainly in the table and in a
one-line summary — don't bury it — but keep going with the remaining rows.
End with `Notion: {main_page_url}` if `main_page_id` is set.
