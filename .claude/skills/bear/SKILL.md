---
name: Bear
description: Run the Bear stage for the current analysis. Generates rival readings against the Bull thesis.
disable-model-invocation: true
context: fork
model: claude-opus-4-6
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
- `analyses/{slug}/02a_science_advisor_full.md` — if missing, proceed without it.
- `analyses/{slug}/02b_investment_advisor_full.md` — if missing, proceed without it.
- `analyses/{slug}/02c_political_advisor_full.md` — if missing, proceed without it.
- `analyses/{slug}/03_bull_full.md` — if missing, stop and report:
  "ERROR: Bull output not found. Run /bull first."

## Optional deal materials

For deal analyses, also check `analyses/{slug}/00_deal_materials/manifest.md`.
If it exists, use the Read tool to read it, then read EVERY exhibit file
listed in it (image or doc, paths relative to `00_deal_materials/`),
regardless of which advisor it was routed to. Your job here is to check
whether the Bull case and the advisors' readings of a given chart, table, or
legal document actually match what the source shows — discrepancies between
a synthesized claim and the underlying exhibit are exactly the kind of thing
this stage exists to catch. If `manifest.md` does not exist, proceed without
it.

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
- If you read exhibits from `00_deal_materials/manifest.md`: any cases where
  the Bull case or an advisor's reading of a specific chart, table, or
  document doesn't match what the source actually shows

Do not soften your critique. Give the strongest bear thesis.

## Output instructions

Your full analysis (File 1) must include a subsection headed "Working/failing signals for this company" that instantiates the pipeline's "working" vs. "failing" definitions (see CLAUDE.md's "System framing — counterinduction") for THIS specific company. Translate each generic signal into what it concretely looks like here — for the working side: repeat orders without subsidy dependence, private capital at risk, costs approaching parity, high utilization; for the failing side: niche-shifting, order cancellations, low utilization, flat cost curves, continued subsidy dependence after 5+ years. State the concrete, observable signals for this company rather than restating the definitions verbatim.

When you state a quantitative threshold or cutoff that is not drawn from a cited source, label it `(analyst prior)` inline — this keeps invented numbers (e.g. failure-probability or downside-magnitude estimates) visibly distinct from sourced ones as they flow downstream into Bull/Bear/Executive.

Read the slug from the current analysis above. Write one file:

**File:** `analyses/{slug}/04_bear_full.md`
[BEAR_START]
<your full bear analysis>
[BEAR_END]

## Notion sync

See `.claude/skills/notion-sync/REFERENCE.md` for full conventions
(skip/failure wording, performance notes).

Follow REFERENCE.md's "Stage sub-page push" procedure for Stage 4: file
`04_bear_full.md`, delimiters `[BEAR_START]`/`[BEAR_END]`, title "Stage 4:
Bear Case", `.notion` key `stage4_page_id`.

End your summary with `Notion: {main_page_url}` on success, or the
appropriate skip/failure line from REFERENCE.md.
