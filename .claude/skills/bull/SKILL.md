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
- Where the genuine structural upgrades over Cleantech 1.0 strengthen THIS case:
  secured/creditworthy offtake, AI/data-center power demand as a new deep-pocketed
  buyer, a diversified capital stack (project finance + public credit + patient
  capital, not VC alone), and a later-stage / de-risked entry point.
- The strongest bull case stands on subsidy-independent economics. If the thesis
  needs the credits to survive, say so plainly.

Give the strongest bull thesis. Do not pre-empt, anticipate, or name any
subsequent stage of the pipeline — argue your own case on its merits.

## Output instructions

Read the slug from the current analysis above. Write one file:

**File:** `analyses/{slug}/03_bull_full.md`
[BULL_START]
<your full bull analysis>
[BULL_END]

## Notion sync

See `.claude/skills/notion-sync/REFERENCE.md` for full conventions
(skip/failure wording, performance notes).

Follow REFERENCE.md's "Stage sub-page push" procedure for Stage 3: file
`03_bull_full.md`, delimiters `[BULL_START]`/`[BULL_END]`, title "Stage 3:
Bull Case", `.notion` key `stage3_page_id`.

End your summary with `Notion: {main_page_url}` on success, or the
appropriate skip/failure line from REFERENCE.md.
