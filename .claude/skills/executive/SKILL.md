---
name: Executive
description: Run the Executive synthesis stage. Produces scorecard data and narrative, and syncs them to Notion.
disable-model-invocation: true
context: fork
model: claude-opus-4-6
allowed-tools: Read Write Bash mcp__notion__notion-update-page mcp__notion__notion-fetch
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

## Notion sync

See `CLAUDE.md`'s "Notion sync" section for full conventions. If
`mcp__notion__*` tools aren't available, state this in your summary
(e.g. "Notion sync skipped — `notion` MCP not configured; run
/notion-sync once it is") rather than failing silently.

Read `analyses/{slug}/.notion`. If it has no `main_page_id`, skip this
section and note in your summary: "Notion sync skipped — run /research
first to enable it (or /notion-sync to bootstrap and catch up in one go)."

Otherwise:

1. **Update properties** — call `notion-update-page` with `page_id` =
   `main_page_id`, `command: update_properties`:
   - `Grade` = the letter grade from STEP 2
   - `Grade driver` = the one-sentence grade driver from STEP 2
   - `Status` = the investment status from STEP 2
   - `date:Analysis Date:start` = today's date (YYYY-MM-DD)
   - `date:Analysis Date:is_datetime` = `0`

2. **Replace main page content** — call `notion-fetch` on `main_page_id` to
   get its current content. Take everything from the start of the content up
   to (not including) `## Stage Reports` as `old_str`. Build `new_str` from
   the values produced in STEPS 1-7:
   ```
   > **Grade {grade} · {status}**
   > {grade_driver}

   ## Executive Narrative
   {the four narrative paragraphs from STEP 3, separated by blank lines}

   ## Scorecard
   {markdown table: Dimension | Bear | Central | Bull | Driver — one row
   per dimension scored in STEP 1}

   ## The Crux
   {STEP 4}

   ## Values & Judgment Flags
   {STEP 6, as a bulleted list, or "None identified."}

   ## What Would Change This
   {STEP 5 items, as a bulleted list}

   ## Next Actions
   {STEP 7 items, as a bulleted list}
   ```
   Then call `notion-update-page` with `page_id` = `main_page_id`,
   `command: update_content`, and one entry in `content_updates` with this
   `old_str`/`new_str` pair. Leave `## Stage Reports` and everything after it
   untouched — that section lists the stage sub-pages as child pages, and
   `replace_content` would delete them.

If any Notion call fails, state this clearly in your summary (e.g. "Notion
sync failed: <error> — run /notion-sync to retry") rather than burying it —
but don't block; the markdown/JSON outputs are the source of truth.
