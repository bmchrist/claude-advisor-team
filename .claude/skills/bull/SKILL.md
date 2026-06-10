---
name: Bull
description: Run the Bull stage for the current analysis. Steelmans the investment thesis using advisor outputs.
disable-model-invocation: true
context: fork
allowed-tools: Read Write
---

## Current analysis
!`cat analyses/.current 2>/dev/null || echo "ERROR: No current analysis. Run /research first."`

## Required reading

Before continuing, use the Read tool to read the following (substitute the slug from
"Current analysis" above):
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
