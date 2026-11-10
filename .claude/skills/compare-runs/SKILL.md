---
name: Compare Runs
description: Compare the current run of an analysis against an earlier snapshot in its history/ folder — what new evidence arrived, which open questions it answered, and why scores moved. Writes 06_run_comparison.md and a Notion sub-page. Only invoke when Ben runs it directly or when /rerun-analysis directs it — never on your own initiative.
disable-model-invocation: false
context: fork
model: opus
allowed-tools: Read Write Bash mcp__notion__notion-create-pages mcp__notion__notion-update-page mcp__notion__notion-fetch
argument-hint: "[company-or-slug] [base-snapshot]"
arguments: target base
---

## Setup

```!
setup_out=$(python3 scripts/resolve_target.py "$target")
echo "$setup_out"
SLUG=$(echo "$setup_out" | grep "^slug:" | sed 's/^slug: *//')
if [ -n "$SLUG" ]; then python3 scripts/compare_runs.py "$SLUG" $base; fi
```

If Setup printed an ERROR line, stop and report it to Ben verbatim.

Setup ran the deterministic diff. It printed `base` (the snapshot under
`history/`), `base_dir`, `base_date`, `head_date`, `notion_key`,
`notion_title` and `data_file`. "Base" is the earlier run; "head" is the
current one.

## Required reading

Read these with the Read tool. `{base_dir}` is from Setup, and
`analyses/{slug}/` is the head run. If a base or head file is missing,
note it and continue. Only the data file and the two executive reports
are required.

1. `{data_file}`: parsed verdict, scorecard deltas, crux row, materials
   changes, ingestion-log rows and pipeline changes. Treat it as fact.
   Don't recompute it.
2. Executive reports: `{base_dir}/05_executive_report.md` and
   `analyses/{slug}/05_executive_report.md`.
3. Advisor summaries, base and head: `02a_science_advisor_summary.md`,
   `02b_investment_advisor_summary.md`, `02c_political_advisor_summary.md`.
   Older base runs may lack the "Data room gaps (conclusion-material)"
   block. If so, fall back on the base executive report's open items.
4. Bull and Bear, base and head: `03_bull_full.md`, `04_bear_full.md`.

You're the only stage allowed to read `history/` besides Research's prior
briefing. Read only `{base_dir}`, not other snapshots.

## Your task

Explain what changed between the two runs and why, so Ben can tell real
movement from noise. Every claim cites its source: a file and section, an
exhibit, or a data-file line.

The pipeline isn't deterministic. A re-run with zero new evidence can
still move scores. Apply these rules throughout:

- **Attribution.** Tag every score movement exactly one of:
  - `NEW EVIDENCE`: cite the specific new document, exhibit or public
    finding (head RC's `[NEW SINCE …]` tags mark findings first found in
    this run) and show how it bears on that row.
  - `PIPELINE CHANGE`: the data file lists a changed prompt file for a
    stage that drives that row, and you can't find new evidence that
    explains it.
  - `UNEXPLAINED`: neither applies.
- **Noise.** An `UNEXPLAINED` move of ±1 is possible run-to-run noise. Say
  so, and don't build the headline on it. Call a move real only when you
  can cite new evidence or a pipeline change.
- **No fingerprint.** If the data file's pipeline section reads
  `unknown (no fingerprint)`, write `unknown (no fingerprint)` wherever
  you'd otherwise assess pipeline change. Never write "none" in that case.
  `PIPELINE CHANGE` can't be assigned, so unexplained moves stay
  `UNEXPLAINED`.
- **Partial re-run.** If the data file has a "Partial re-run" section,
  open Section 4 by naming the stages that re-ran. Differences upstream of
  the starting stage are impossible by construction.

### Sections

1. **Headline.** Old verdict → new verdict (grade / Tech · Comm / status),
   then one sentence on why. If nothing moved beyond noise, say that
   plainly: "No material change; differences are within run-to-run noise."
2. **New evidence received.** What the new or changed documents (data
   file materials and ingestion-log rows) and new public research
   (`[NEW SINCE]` findings in the head RC summary) actually contained.
   Facts, not significance. Write "None" for a pure refresh that found
   nothing new.
3. **Open questions, then and now.** Gather every item from the base
   report's "What Would Change This" and "Next Actions", plus each base
   advisor summary's conclusion-material data-room gaps. Give one table
   row per item: the item, its source, a status, and a citation. The
   status is one of:
   - *answered: moved toward bull*
   - *answered: moved toward bear*
   - *partially answered*
   - *still open*

   An item counts as answered only if head-run evidence addresses it.
   Then list any new open questions the head run raised that weren't
   asked before.
4. **Score movements with attribution.** One table row per scorecard row
   whose bear, central or bull moved: the move, the attribution tag, and a
   one-line justification with a citation. Then cover changes to the crux
   row and to the risk level or type.
5. **Argument shifts.** Bear points that were rebutted, dropped, or new.
   Bull concessions gained or withdrawn. Compare base and head Bull and
   Bear directly. Name the argument, don't paraphrase whole sections.
6. **Catalysts.** From the two reports' Catalysts & Triggers tables: which
   catalysts resolved (and how), which are new, and which slipped (the
   window moved later, or passed without the event).

## Output

Write `analyses/{slug}/06_run_comparison.md`. Copy the frontmatter values
from Setup:

```markdown
---
slug: <slug>
base: <base>
base_date: <base_date>
head_date: <head_date>
notion_key: <notion_key>
notion_title: "<notion_title>"
---
# <company> — Run comparison (<base_date> → <head_date>)

[COMPARISON_START]
## 1. Headline
…
## 6. Catalysts
…
[COMPARISON_END]
```

Write plain markdown, with `$` as `$`. Escaping happens at push time.

## Notion sync

Run `python3 scripts/notion_push.py {slug} compare executive` and handle its
output per `.claude/skills/notion-sync/REFERENCE.md`'s "Scripted push". It
pushes the comparison page (key and title from `06_run_comparison.md`'s
frontmatter), records both keys, then re-pushes the main page so it links
the new page. If the `executive` line reports an error, name
`/notion-sync {slug} executive` as the fix.

Only if it prints `MODE: mcp`, do the following instead. Run
REFERENCE.md's Preconditions, then its "Stage sub-page push" procedure for
stage 6. Run
`python3 scripts/notion_body.py {slug} compare` for the payload. Use
`notion_key` as the `.notion` key: if `.notion` already has it (a re-run
compared on the same day), update that page instead of creating one. Use
`notion_title` as the title. Record the page with both keys, as
REFERENCE.md's stage 6 note describes:

```
python3 scripts/notion_state.py set {slug} <notion_key> <page id> <notion_key minus _id>_title "<notion_title>"
```

Then link it from the main page. The main page lists its sub-pages only
when it's pushed, and Executive has already pushed it in this run, so
follow REFERENCE.md's "Main-page push" procedure for
`05_executive_report.md` now (properties, the `replace_content` body from
`notion_body.py {slug} executive`, which now includes this page, and the
sub-page check). If it fails, say so and name `/notion-sync {slug}
executive` as the fix.

End your summary with the headline sentence, then `Notion: {main_page_url}`
on success, or the matching skip/failure line from REFERENCE.md.
