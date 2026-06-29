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

The score is **Merit** — the size, durability, and credibility of the win on
this dimension *if the thesis holds*. Score the substance, not the proof: how
proven the dimension is right now lives in Confidence (STEP 1B), not here.

Merit (substance only; do NOT dock for lack of evidence):
  5 = Exceptional / best-in-class strength on this dimension
  4 = Clear positive
  3 = Genuinely neutral or mixed
  2 = Negative, partly mitigated
  1 = Severe negative, near-disqualifying

Two rules keep Merit honest — it must be able to score *low*, not just default
high once you "assume it works":
  - Assume resolution of *evidence/proof questions only* (is the pilot real, is
    the magnet validated). Do NOT suspend the bear's *structural* objections —
    a small or commoditized market, an uncreditworthy offtaker, escape clauses,
    a subsidy cliff, ATOMS-not-BITS scale/capital-intensity risk. Those are
    merit defects and still suppress the score even granting the tech works.
  - Reward magnitude and defensibility of the prize, not the binary "good if it
    works." A seed-stage company whose win — even fully granted — is a small
    market with no moat and commodity margins scores LOW Merit. A frontier deal
    with a large, defensible prize scores HIGH Merit at the same low Confidence.
    This separation (strong-but-unproven vs. no-real-merit) is the whole point;
    if every dimension drifts up, you are scoring "assume it works," not Merit.

"Well-evidenced" is deliberately removed from the 5 so the top of the scale is
reachable before commercial proof exists. Per CLAUDE.md's counterinduction
framing, name the ATOMS/BITS bucket where it bears on a dimension's Merit.

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

### STEP 1B — CONFIDENCE (evidence stage, two axes)

Merit asks *how good if it holds*; Confidence asks *how proven now*. Score
Confidence on the C1-C5 stage below, anchored to the sourcing tags STEP 7 rolls up.

  C5 Validated    — independent / third-party proof at commercial-relevant scale; load-bearing facts [VERIFIED]
  C4 Demonstrated — first-party proof at pilot / sub-scale; [VERIFIED] but first-party
  C3 Indicative   — partial or analogous evidence; key claims thinly sourced ([SINGLE SOURCE])
  C2 Projected    — modeled / asserted; the core proof point not yet attempted ([COMPANY CLAIM] + models)
  C1 Asserted     — load-bearing facts are company claims only ([COMPANY CLAIM] / [NOT FOUND])

Report Confidence on **two axes** — a deal can be far more proven on one than the
other (a demonstrated pilot with no revenue is Tech-proven but Commercial-unproven,
and collapsing the two to one number hides exactly that):

  - **Technical Confidence** — is the technology / science proven to work at
    relevant scale? Anchored to Technical Readiness (and any technical dimension
    the crux names). POLICY: anchor to Implementation Risk.
  - **Commercial Confidence** — is the business proven — economics, demand, deal
    structure? Anchored to the *lower* of Commercial Viability and (DEAL)
    Investment Structure Quality. POLICY: anchor to Investable Signal.

Also report each load-bearing dimension's own stage in the scorecard — that is the
source data the two axes roll up. The **gate Confidence** used by the STEP 2 status
matrix is the *lower of the two axes*: you are only committable once both the tech
and the business are proven. `confidence_driver` names which axis binds (the lower)
and the single fact it hinges on. No new tagging work — this surfaces what STEP 1 /
STEP 7 already tagged.

### STEP 2 — GRADE AND STATUS

The letter grades **Merit only**. Confidence (STEP 1B) rides alongside in the
display and drives the status matrix below — it is never averaged into the letter.

Form the letter as a gestalt read of the **load-bearing dimensions** (Technical
Readiness, Commercial Viability, and (DEAL) Investment Structure Quality — POLICY:
Implementation Risk, Investable Signal — plus any crux dimension), using the band
descriptors below as orientation. Do NOT average all ten dimensions — peripheral
rows (Country, Political Stability) must not dilute the signal back toward the
middle. The descriptors are gestalt guides; only the cap/floor rules are hard gates.

Bands (Merit):
  A / A-   Exceptional. >=2 load-bearing dimensions at 5, none below 3, no values flag.
  B+/B/B-  Strong. Several 4s; at most one load-bearing dimension at 2; no 1s on a load-bearing row.
  C+/C/C-  Mixed. Real strengths offset by >=1 serious concern, or a 1-2 on a load-bearing dimension.
  D+/D/D-  Weak. Multiple core dimensions <=2, or one near-disqualifying flaw. A no-real-merit deal lands here even at high Confidence.
  F        Disqualifying flaw on a load-bearing dimension or a values gate.

Cap / floor rules — hard gates, applied *after* the gestalt read; they can only
drag the letter down, never lift it:
  - A central 1 on a load-bearing dimension (Technical Readiness, Commercial
    Viability, or (DEAL) Investment Structure Quality) caps the letter at C+.
  - An unmitigated values FLAG (governance, dual-use, etc.) caps at B.
  - The A range requires >=2 fives — a deal cannot reach A by being uniformly "fine."

Write one sentence (`grade_driver`) explaining what most determines the Merit letter.

Investment status — set by the Merit x Confidence matrix (gate Confidence =
lower of the two STEP 1B axes), not free-form:

  |                  | Merit A-B   | Merit C             | Merit D-F |
  |------------------|-------------|---------------------|-----------|
  | Confidence C4-C5 | INVEST      | TRACK               | PASS      |
  | Confidence C3    | TRACK       | INVESTIGATE         | PASS      |
  | Confidence C1-C2 | INVESTIGATE | INVESTIGATE / TRACK | PASS      |

  INVEST      — conviction positive, proceed to commitment
  TRACK       — interesting but insufficient signal; monitor and revisit
  INVESTIGATE — specific high-value unknowns worth actively resolving
  PASS        — not a fit; state primary reason in one sentence

A strong-but-unproven deal sits at e.g. B / gate C2 -> INVESTIGATE — high Merit
held only by low Confidence — and climbs to INVEST as Confidence rises, *without
its Merit letter being marked down in the meantime*. A no-real-merit deal lands
Merit D-F -> PASS regardless of how well or poorly evidenced it is. Where the
matrix offers a choice (Merit C / gate C1-C2), pick on whether a near-term catalyst
can resolve the binding axis (INVESTIGATE) or not (TRACK). Because the binding axis
is named, two deals at the same gate read differently — a Tech C4 / Comm C2 deal is
one resolved gate from investable; a Tech C2 / Comm C2 deal needs both.

Always populate `status_reason` (not only for PASS): one sentence stating the
decision *rule* behind the status, distinct from `grade_driver` (which states
what drives the grade). Model it on this example verbatim: "TRACK rather than
INVESTIGATE because no near-term action can change the crux before Eos's
first-plasma results." Keep it consistent with the Catalysts & Triggers table
(STEP 6) and use that table as a cross-check.

Hard rule: a `TRACK` status is invalid without at least one dated row in the
Catalysts & Triggers table (STEP 6). If no dated catalyst exists, either find
one or explain in `status_reason` why the position is currently untriggerable.

### STEP 2B — RISK CHARACTERIZATION

State, on two explicit axes, what KIND of risk this is and how SEVERE — separate
from the grade (how good) and confidence (how proven). This is the line read first.

Risk LEVEL — severity of the downside if the bear case lands (pick one):
  CONTAINED — capital-light / staged; failure loses a fraction, recoverable
  MODERATE  — meaningful loss, partial recovery plausible (assets, IP, acquihire)
  SEVERE    — most capital impaired; capital-intensive with thin salvage value
  BINARY    — total-loss / all-or-nothing; one unproven step gates everything
              (typical of FOAK frontier hard-tech)

Risk TYPE — the dominant failure mode(s), primary first:
  TECHNOLOGY_SCALE_UP        — invention or FOAK manufacturing/yield risk
                               (the Cleantech-1.0 valley of death)
  COMMERCIAL_UNIT_ECONOMICS  — never reaches parity / commodity-margin trap
  POLICY_SUBSIDY_CLIFF       — economics depend on credits exposed to repeal
  COUNTERPARTY_OFFTAKE       — demand concentrated in weak or uncommitted buyers
  CAPITAL_STRUCTURE_FINANCING— can't fund the next scale step on viable terms
  EXECUTION                  — team/operational complexity, supply chain, permitting

Name a primary type and any material secondary types. Level and primary type must be
consistent with the crux (STEP 4) and the lowest-scoring load-bearing scorecard row —
if they disagree, reconcile before finalizing. Close with one sentence: level +
primary type + why (e.g. "BINARY / TECHNOLOGY_SCALE_UP: the 1 km drilling test gates
the entire thesis; everything downstream is modeled").

### STEP 3 — NARRATIVE (exactly four paragraphs)

Para 1: What this is and why it's on the radar (factual, 2-3 sentences)
Para 2: The bull case in specific terms (no hedging, 2-3 sentences)
Para 3: The bear case in specific terms (no hedging, 2-3 sentences) — name the risk
        level and primary type from STEP 2B in plain language
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
  "grade": "<Merit letter>",
  "technical_confidence": "<C1-C5 — is the tech proven; STEP 1B>",
  "commercial_confidence": "<C1-C5 — is the business proven; STEP 1B>",
  "confidence_driver": "<one sentence — which axis binds (the lower) and the fact it hinges on>",
  "grade_display": "<paired form, e.g. 'B- / Tech C4 · Comm C2'>",
  "status": "<INVEST|TRACK|INVESTIGATE|PASS>",
  "grade_driver": "<one sentence — what drives the Merit letter>",
  "status_reason": "<one sentence — the decision rule behind the status; always populated, distinct from grade_driver>",
  "risk_level": "<CONTAINED|MODERATE|SEVERE|BINARY>",
  "risk_primary_type": "<TECHNOLOGY_SCALE_UP|COMMERCIAL_UNIT_ECONOMICS|POLICY_SUBSIDY_CLIFF|COUNTERPARTY_OFFTAKE|CAPITAL_STRUCTURE_FINANCING|EXECUTION>",
  "risk_secondary_types": ["<type>"],
  "risk_characterization": "<one sentence: level + primary type + why, tied to the crux>",
  "scores": {
    "<Dimension>": {"bear": N, "central": N, "bull": N, "driver": "<10 words max>", "confidence": "<C1-C5; load-bearing dimensions only, omit key for others>"}
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
status decision-rule); the Risk Level / Type / characterization from STEP 2B (surface as a callout directly under Grade/Status); the narrative paragraphs from STEP 3; the scorecard
from STEP 1; the crux from STEP 4; "Catalysts & Triggers" from STEP 6;
"Sourcing Strength" from STEP 7; "Deal Terms & Price Sensitivity" (DEAL only)
from STEP 8; "Values & Judgment Flags" from STEP 9; "What Would Change This"
from STEP 5; "Next Actions" from STEP 10.

End your summary with `Notion: {main_page_url}` on success, or the
appropriate skip/failure line from REFERENCE.md.
