---
name: Executive
description: Run the Executive synthesis stage. Produces scorecard, narrative, and HTML report.
disable-model-invocation: true
context: fork
model: claude-opus-4-6
allowed-tools: Read Write Bash
---

## Current analysis
!`cat analyses/.current 2>/dev/null || echo "ERROR: No current analysis. Run /research first."`

## Today's date
!`date +%Y-%m-%d`

## Required reading

Before continuing, use the Read tool to read the following (substitute the slug from
"Current analysis" above):
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

### STEP 3 — NARRATIVE (exactly four paragraphs)

Para 1: What this is and why it's on the radar (factual, 2-3 sentences)
Para 2: The bull case in specific terms (no hedging, 2-3 sentences)
Para 3: The bear case in specific terms (no hedging, 2-3 sentences)
Para 4: What needs to be true for the bull case to play out

### STEP 4 — CRUX

The single dimension where Bull and Bear diverge most sharply.
Why it's the crux. What resolving it means for the overall conclusion.
(2-3 sentences)

### STEP 5 — EVIDENCE THAT WOULD CHANGE THIS CONCLUSION

2-3 specific, falsifiable items. Not "more information" — specific data,
events, or disclosures that would materially move the Central score.

### STEP 6 — VALUES FLAGS

Flag any: fossil fuel dependency, policy-only viability, greenwashing signals,
currency repatriation risk, other values misalignments.
Write "None identified." if clean.

### STEP 7 — NEXT ACTIONS

2-3 concrete next actions. Not "do more research" — specific asks like
"request the technical whitepaper" or "schedule reference call with X customer."

## Output instructions

Read company, slug, type, and date from the current analysis and date sections above.
Write three files:

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
  "grade_driver": "<one sentence>",
  "status_reason": "<one sentence if PASS, else blank>",
  "scores": {
    "<Dimension>": {"bear": N, "central": N, "bull": N, "driver": "<10 words max>"}
  },
  "crux": "<2-3 sentences>",
  "evidence_to_change": ["<item 1>", "<item 2>"],
  "values_flags": ["<flag or None identified.>"],
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

---

**File 3:** `analyses/{slug}/05_executive_report.html`

A self-contained HTML report. Use this exact structure and styling, substituting
real values from the JSON data you produced above:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject} — Investment Analysis</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 15px; line-height: 1.65; color: #1a1a1a; background: #f5f5f4; }
  .page { max-width: 900px; margin: 40px auto; padding: 0 20px 80px; }
  .card { background: white; border-radius: 10px; padding: 24px 28px; margin-bottom: 16px; border: 1px solid #e7e5e4; }
  .label { font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #a8a29e; margin-bottom: 14px; }
  .company { font-size: 26px; font-weight: 700; margin-bottom: 4px; }
  .meta { font-size: 13px; color: #78716c; margin-bottom: 18px; }
  .badges { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .badge { display: inline-flex; align-items: center; padding: 7px 16px; border-radius: 7px; font-weight: 700; font-size: 14px; color: white; }
  .grade-badge { font-size: 20px; }
  .grade-driver { margin-top: 12px; font-size: 13px; color: #57534e; font-style: italic; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { padding: 7px 10px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; color: #a8a29e; border-bottom: 1px solid #e7e5e4; }
  td { padding: 9px 10px; border-bottom: 1px solid #f5f5f4; vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  .dim { font-weight: 500; }
  .num { text-align: center; width: 52px; font-weight: 600; }
  .central { font-size: 16px; }
  .muted { color: #a8a29e; }
  .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
  .spread { font-size: 12px; width: 80px; }
  .spread.wide { color: #f97316; }
  .spread.moderate { color: #eab308; }
  .spread.narrow { color: #84cc16; }
  .driver { font-size: 13px; color: #78716c; }
  .narrative p { margin-bottom: 13px; }
  .narrative p:last-child { margin-bottom: 0; }
  .crux { border-left: 3px solid #3b82f6; padding-left: 16px; color: #1c1917; }
  ul { padding-left: 18px; }
  li { margin-bottom: 7px; color: #292524; }
  .footer { text-align: center; color: #c4b5a5; font-size: 12px; margin-top: 32px; }
</style>
</head>
<body>
<div class="page">
  <!-- Header card: company name, meta, grade badge, status badge, grade_driver -->
  <!-- Scorecard table: bear / central / bull columns, spread column, driver column -->
  <!-- Color dots on central scores: 1=#dc2626 2=#f97316 3=#eab308 4=#84cc16 5=#22c55e -->
  <!-- Spread: bull-bear >= 3 = wide (#f97316), >= 2 = moderate (#eab308), else narrow (#84cc16) -->
  <!-- Grade colors: A=#15803d B=#65a30d C=#ca8a04 D=#ea580c F=#dc2626 (adjust +/- one shade) -->
  <!-- Status colors: INVEST=#22c55e TRACK=#3b82f6 INVESTIGATE=#f59e0b PASS=#ef4444 -->
  <!-- Narrative card -->
  <!-- Crux card -->
  <!-- Evidence that would change this conclusion card -->
  <!-- Values flags card -->
  <!-- Next actions card -->
  <!-- Footer: date · Investment Analysis Pipeline -->
</div>
</body>
</html>
```

Generate the full HTML directly — do not leave the comment placeholders in the
output. Substitute all real values from the JSON you produced.
