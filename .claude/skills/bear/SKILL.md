---
name: Bear
description: Run the Bear stage for the current analysis. Generates rival readings against the Bull thesis.
disable-model-invocation: true
context: fork
model: claude-opus-4-6
allowed-tools: Read Write
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

Do not soften your critique. Give the strongest bear thesis.

## Output instructions

Read the slug from the current analysis above. Write one file:

**File:** `analyses/{slug}/04_bear_full.md`
[BEAR_START]
<your full bear analysis>
[BEAR_END]
