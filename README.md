# Investment Analysis Pipeline

A multi-agent investment research system for clean energy companies, deals,
and policies (with a focus on African energy transition). Each stage reads
the prior stages' outputs, does its analysis, and writes results to disk.

## Project layout

- `.claude/skills/` — pipeline stage definitions
- `analyses/` — per-company outputs (one folder per analysis)
- `README.md` — this file (usage)
- `CLAUDE.md` — technical reference for Claude Code (skill internals, methodology)
- `projectplan.md` — project status and planned changes

## Running an analysis

1. `/research "Company Name" TYPE` — starts a new analysis. `TYPE` is one of
   `TECHNOLOGY`, `DEAL`, or `POLICY`. This becomes the active analysis for
   subsequent commands (tracked in `analyses/.current`).
2. Run the advisors, in any order:
   - `/science` — scientific/technical assessment
   - `/investment-advisor` — commercial viability and (for deals) deal terms
   - `/political` — political and regulatory risk
3. `/bull` — steelmans the investment thesis using the advisor outputs
4. `/bear` — generates rival readings against the Bull case
5. `/executive` — synthesizes everything into a scorecard, narrative, and
   HTML report

Each step needs the previous ones to have run (advisors need research, Bull
needs advisors, Bear needs Bull, Executive needs everything). If a required
file is missing, the skill will tell you what to run first.

To switch to a different company, run `/research` again with the new
company/type. (See `projectplan.md` for planned changes to make jumping
between analyses less disruptive.)

## Output structure

Each analysis lives in `analyses/<slug>/` (slug derived from the company
name — see Slug convention below):

```
analyses/<slug>/
  01_research_collector_full.md / _summary.md
  02a_science_advisor_full.md / _summary.md
  02b_investment_advisor_full.md / _summary.md
  02c_political_advisor_full.md / _summary.md
  03_bull_full.md
  04_bear_full.md
  05_executive_data.json
  05_executive_narrative.md
  05_executive_report.html   <- open this for the polished report
```

`_full.md` files are the complete analyses; `_summary.md` files are short
briefings for downstream stages. `05_executive_report.html` is the
self-contained, shareable summary.

## Adding deal materials (data rooms, pitch decks, etc.)
(this is currently not accurate)
If you have non-public materials for a deal (pitch deck, financial exhibits,
SPV/legal docs), add them under `analyses/<slug>/00_deal_materials/` before
running `/research`:

- A prose digest of narrative content (e.g. `pitch_deck_digest.md`)
- Deal terms (e.g. `spv_deal_terms.md`)
- Chart/table-heavy content as images (e.g. `financial_exhibits/*.png`) — the
  Investment Advisor reads these directly

`/research` and the advisors pick these up automatically. See
`projectplan.md` for planned improvements (a routing manifest and
`[DATA ROOM]` evidence tagging).

## Slug convention

Company name → folder name: lowercase, `+` → `_plus`, `&` → `_and`,
non-alphanumeric runs → `_`, trim leading/trailing underscores.

Examples: `Acme+` → `acme_plus`, `AT&T` → `at_and_t`, `Bright Energy` →
`bright_energy`

## Methodology

Every stage applies counterinduction — for each major claim, it generates the
rival reading alongside the primary one (a pilot = progress OR inability to
escape pilot stage; grant funding = validation OR private capital won't carry
the risk; etc.). The full framing the agents use lives in `CLAUDE.md`.

Two definitions worth knowing when reading advisor outputs:

- **"Working"**: repeat orders without subsidy dependence, private capital at
  risk, costs approaching parity, high utilization
- **"Failing"**: niche-shifting, order cancellations, low utilization, cost
  curves not improving, continued subsidy dependence after 5+ years

## Reading the Executive scorecard

- Each dimension is scored 1-5, three times: Bear / Central / Bull. A wide
  spread means the dimension is genuinely contested — don't read it as noise.
- The overall letter grade (A-F) is a gestalt judgment, not an average of the
  scores.
- Status is one of: `INVEST` (proceed to commitment), `TRACK` (interesting,
  revisit later), `INVESTIGATE` (specific unknowns worth resolving), `PASS`
  (not a fit).
- Dimensions scored depend on analysis type (TECHNOLOGY / DEAL / POLICY) —
  see the `/executive` skill for the full list per type.


## Models

- Research, advisors, Bull: `claude-sonnet-4-6`
- Bear, Executive: `claude-opus-4-6` (higher-judgment stages)

## Ad hoc prompts (outside the pipeline)

For quick, one-off analysis without running the full pipeline:

### Quick rival reading

```
Apply counterinduction to the following:

[paste claim, signal, or summary]

For each major claim:
1. Primary reading (proponent's interpretation)
2. Rival reading (what the same evidence looks like if the bearish thesis is true)
3. What evidence would distinguish between them?
4. What would "actually working" vs "failing gracefully" look like here?
```

### Render scorecard as a visual artifact (radar chart)

After `/executive` produces `05_executive_data.json`, paste its header fields
and scores table into a new conversation and run:

```
Render the following executive summary scorecard as an interactive HTML artifact.

Include:
1. A header block showing Subject, Date, Grade, and Status — color-coded by
   status (INVEST = green, TRACK = blue, INVESTIGATE = amber, PASS = red)
2. A scorecard table with a visual indicator (colored bar or dot) for each
   Central score, and a subtle background showing the Bear–Bull spread
3. A radar chart showing the Central scores across all dimensions

Keep the design clean and minimal. The artifact should be readable at a glance
and printable.

[paste header fields and scorecard table here]
```
