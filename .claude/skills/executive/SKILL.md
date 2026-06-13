---
name: Executive
description: Run the Executive synthesis stage. Produces scorecard data and narrative, and syncs them to Notion.
disable-model-invocation: true
context: fork
model: claude-opus-4-6
allowed-tools: Read Write Bash mcp__notion__notion-update-page mcp__notion__notion-fetch
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

## Required reading

Before continuing, use the Read tool to read the following (substitute the slug from
"Setup" above):
- `analyses/{slug}/01_research_collector_summary.md` — if missing, stop and report:
  "ERROR: Research summary not found."
- `analyses/{slug}/02a_science_advisor_summary.md` — if missing, proceed without it.
- `analyses/{slug}/02b_investment_advisor_summary.md` — if missing, proceed without it.
- `analyses/{slug}/02c_political_advisor_summary.md` — if missing, proceed without it.
- `analyses/{slug}/03_bull_full.md` — if missing, stop and report:
  "ERROR: Bull output not found."
- `analyses/{slug}/04_bear_full.md` — if missing, stop and report:
  "ERROR: Bear output not found."

## Your task

You are the Executive synthesizing the analysis from the files you just read.
Do not re-run the analysis — synthesize what the advisors produced and apply
your own judgment on scoring and the overall assessment.

### STEP 1 — SCORECARD

Score each applicable dimension on a 1-5 integer scale, three times:
  bear:    score if the bearish thesis is correct
  central: your best estimate given all available evidence
  bull:    score if the bull thesis is correct

Score meanings:
  5 = Strong positive signal, well-evidenced
  4 = Positive signal with manageable risks
  3 = Genuinely neutral or mixed
  2 = Negative signal with some mitigating factors
  1 = Strong negative signal, significant concern

Wide Bear/Bull spreads signal genuinely contested dimensions.
Do not compress spreads toward the middle — that removes information.

High complexity = low score for Execution Complexity.
High risk = low score for Country/Counterparty Risk.

For TECHNOLOGY analyses, score:
  Technical Readiness, Commercial Viability, Team Quality, Political Stability,
  Subsidy Independence, Impact Alignment, Market Timing, Execution Complexity

For DEAL analyses, also score:
  Investment Structure Quality, Country/Counterparty Risk

For POLICY analyses, replace Commercial Viability / Team Quality /
Subsidy Independence with:
  Investable Signal, Implementation Risk, Political Durability

For each dimension, write a key driver of the Central score in 10 words max.

### STEP 2 — GRADE AND STATUS

Overall letter grade: A / B / C / D / F (with + or - if warranted).
This is a gestalt judgment, not a mathematical average.
Write one sentence explaining what most determines the grade.

Investment status — pick one:
  INVEST      — conviction positive, proceed to commitment
  TRACK       — interesting but insufficient signal; monitor and revisit
  INVESTIGATE — specific high-value unknowns worth actively resolving
  PASS        — not a fit; state primary reason in one sentence

Always populate `status_reason` (not only for PASS): one sentence stating the
decision *rule* behind the status, distinct from `grade_driver` (which states
what drives the grade). Model it on this example verbatim: "TRACK rather than
INVESTIGATE because no near-term action can change the crux before Eos's
first-plasma results." Keep it consistent with the Catalysts & Triggers table
(STEP 6) and use that table as a cross-check.

Hard rule: a `TRACK` status is invalid without at least one dated row in the
Catalysts & Triggers table (STEP 6). If no dated catalyst exists, either find
one or explain in `status_reason` why the position is currently untriggerable.

### STEP 3 — NARRATIVE (exactly four paragraphs)

Para 1: What this is and why it's on the radar (factual, 2-3 sentences)
Para 2: The bull case in specific terms (no hedging, 2-3 sentences)
Para 3: The bear case in specific terms (no hedging, 2-3 sentences)
Para 4: What needs to be true for the bull case to play out

### STEP 4 — CRUX

Select the crux by an explicit rule: the scorecard row with the widest
Bull/Bear spread; if tied, the row Bear identifies as load-bearing for its
central case. Name the rule that selected it in the output — do not just apply
it silently. Then: why it's the crux, and what resolving it means for the
overall conclusion. (2-3 sentences)

### STEP 5 — EVIDENCE THAT WOULD CHANGE THIS CONCLUSION

2-3 specific, falsifiable items. Not "more information" — specific data,
events, or disclosures that would materially move the Central score.

### STEP 6 — CATALYSTS & TRIGGERS

Build a dated table of forward catalysts — events that, when they land, would
move the assessment. Columns: event | expected window | scorecard rows it
moves | grade/status it would flip to | source stage.

Populate it from material you already have; do not re-derive. Use the advisors'
and Bear's "evidence that would change my assessment" lists (these largely
converge — treat the convergent set as the candidate trigger list), Bear's
failure timeline, and dated milestones already in the RC summary (regulatory
windows, site selections, funding rounds, first-X targets). Every row needs a
dated or windowed expectation; undated "would be nice to know" items stay in
STEP 5 and do not belong here. This table is what makes a `TRACK` status valid
(STEP 2's hard rule).

### STEP 7 — SOURCING STRENGTH

One mandatory rollup line (or a 2-3 row mini-table) summarizing the
evidence-tag tier of the load-bearing facts behind the grade — sourced from
the RC summary's existing tags ([VERIFIED] / [SINGLE SOURCE] / [COMPANY CLAIM]
/ [DATA ROOM] / [NOT FOUND]) and any `(analyst prior)` labels the advisors
surfaced. No new tagging work — just roll up what Stage 1 and the advisors
already tagged. Example: "All cost/LCOE figures and both timeline targets:
[COMPANY CLAIM]; magnet validation: [VERIFIED]."

### STEP 8 — DEAL TERMS & PRICE SENSITIVITY (DEAL analyses only)

If `analysis_type == DEAL`: write one paragraph on deal terms and price
sensitivity, sourced from the Investment Advisor summary's `## Deal terms`
block — state whether the grade is conditional on entry price (e.g. "A- at the
quoted cap; B if the round prices 2x higher"). If no materials were ingested
(no `## Deal terms` block available), instead write this line verbatim: "Deal
terms not analyzed — no materials ingested; grade is price-independent." For
non-DEAL analyses, omit this section entirely.

### STEP 9 — VALUES FLAGS

Evaluate an explicit checklist every run — answer each item flag-or-clear with
one line, even when all are clear (do not collapse to a single "None
identified."):
  - Subsidy dependence
  - Dual-use / weapons adjacency
  - Safety / environmental-justice exposure
  - Governance
Add any further material flag not covered above (fossil-fuel dependency,
greenwashing signals, currency-repatriation risk, etc.) as an extra line.

### STEP 10 — NEXT ACTIONS

2-3 concrete next actions. Not "do more research" — specific asks like
"request the technical whitepaper" or "schedule reference call with X customer."

## Output instructions

Read company, slug, type, and date from the current analysis and date sections above.
Write two files:

---

**File 1:** `analyses/{slug}/05_executive_data.json`

Valid JSON, no trailing commas, no comments:
```json
{
  "subject": "<company name>",
  "date": "<YYYY-MM-DD>",
  "analysis_type": "<type>",
  "grade": "<letter>",
  "status": "<INVEST|TRACK|INVESTIGATE|PASS>",
  "grade_driver": "<one sentence — what drives the grade>",
  "status_reason": "<one sentence — the decision rule behind the status; always populated, distinct from grade_driver>",
  "scores": {
    "<Dimension>": {"bear": N, "central": N, "bull": N, "driver": "<10 words max>"}
  },
  "crux": "<2-3 sentences; name the selection rule that chose this crux>",
  "evidence_to_change": ["<item 1>", "<item 2>"],
  "catalysts": [
    {"event": "<event>", "window": "<expected date/window>", "scorecard_rows": ["<dimension>"], "target_grade_status": "<grade/status it would flip to>", "source_stage": "<stage>"}
  ],
  "sourcing_strength": "<rollup of evidence-tag tiers for the load-bearing facts>",
  "deal_terms": "<DEAL only: deal-terms & price-sensitivity sentence, or the no-materials disclaimer; empty string for non-DEAL>",
  "values_flags": {
    "subsidy_dependence": "<flag-or-clear, one line>",
    "dual_use_weapons_adjacency": "<flag-or-clear, one line>",
    "safety_environmental_justice": "<flag-or-clear, one line>",
    "governance": "<flag-or-clear, one line>"
  },
  "next_actions": ["<action 1>", "<action 2>"]
}
```

---

**File 2:** `analyses/{slug}/05_executive_narrative.md`

[NARRATIVE_START]
Para 1: <what this is and why it's on the radar>

Para 2: <the bull case in specific terms>

Para 3: <the bear case in specific terms>

Para 4: <what needs to be true for the bull case to play out>
[NARRATIVE_END]

## Notion sync

See `.claude/skills/notion-sync/REFERENCE.md` for full conventions
(skip/failure wording, performance notes).

Follow REFERENCE.md's "Executive update-in-place" procedure: `Grade`,
`Grade driver`, and `Status` come from STEP 2 (with `status_reason` the
status decision-rule); the narrative paragraphs from STEP 3; the scorecard
from STEP 1; the crux from STEP 4; "Catalysts & Triggers" from STEP 6;
"Sourcing Strength" from STEP 7; "Deal Terms & Price Sensitivity" (DEAL only)
from STEP 8; "Values & Judgment Flags" from STEP 9; "What Would Change This"
from STEP 5; "Next Actions" from STEP 10.

End your summary with `Notion: {main_page_url}` on success, or the
appropriate skip/failure line from REFERENCE.md.
