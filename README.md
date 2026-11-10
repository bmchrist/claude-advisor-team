# Investment Analysis Pipeline

A multi-agent investment research system for clean energy companies, deals,
and policies. Each stage reads
the prior stages' outputs, does its analysis, and writes results to disk.

## Project layout

- `.claude/skills/` — pipeline stage definitions
- `analyses/` — per-company outputs (one folder per analysis)
- `README.md` — this file (usage)
- `CLAUDE.md` — technical reference for Claude Code (skill internals, methodology)
- `projectplan.md` — project status and planned changes

## Running an analysis

### One command (recommended)

```
/run-analysis "Company Name" TYPE [materials-path]
```

This runs the whole pipeline: `/ingest-materials` (only if you give a
materials path), `/research`, the three advisors in parallel, `/bull`,
`/bear`, `/executive`, then a Notion catch-up for any page that didn't
sync. It prints one line per finished stage and ends with the verdict and
the Notion link. A full run takes about 45 minutes. Start Claude Code
from the repo root.

- **Retries:** each stage gets one automatic retry. A stage that errored
  but still wrote complete outputs counts as done. A second failure stops
  the run rather than continuing with a gap.
- **Resume:** if the session dies or a stage fails twice, fix the cause
  and run `/run-analysis resume <slug>`. Progress is tracked in
  `analyses/<slug>/.run.json`, and `python3 scripts/pipeline.py status
  <slug>` shows it.
- **Existing analyses:** `/run-analysis` refuses a company that already
  has an analysis (use `/rerun-analysis`, below). It also refuses a path
  given in place of the company name.
- **Materials:** they're ingested and used straight away, with no pause to
  review `manifest.md` routing. If you want to review routing first, run
  `/ingest-materials` by hand and then use the stage-by-stage commands
  below.

### Re-running when new documents arrive

```
/rerun-analysis "Company Name" [new-docs-path] [--force] [--from <stage>]
```

- **With a path:** it first checks whether any file is new or changed.
  If every file matches what was already ingested, it stops with "nothing
  to re-run" before spending anything. Pass `--force` to re-run anyway.
- **Without a path:** it's a public-research refresh with the existing
  materials.
- **Before overwriting anything,** the previous run is archived to
  `analyses/<slug>/history/<date>_<reason>/`. Then the pipeline re-runs:
  ingest (new or changed files only), research, the three advisors in
  parallel, bull, bear, executive.
- **Research** reads the previous briefing, re-verifies its headline
  facts, and tags anything new `[NEW SINCE <date>]`. Every later stage
  judges from scratch, without seeing the previous verdict.
- **It ends with `/compare-runs`,** which writes `06_run_comparison.md`
  and a Notion sub-page with:
  - the old verdict → new verdict
  - what the new documents contained
  - every earlier open question marked answered, partially answered or
    still open
  - each score movement tagged `NEW EVIDENCE`, `PIPELINE CHANGE` or
    `UNEXPLAINED`
- **Run-to-run noise:** the pipeline isn't deterministic, so an
  unexplained ±1 move is flagged as possible noise.
- **`--from <stage>`** re-runs only that stage and the ones after it, for
  example after editing Bear's prompt. It can't be combined with new
  documents.
- **Comparing by hand:** `/compare-runs "Company" [snapshot]` compares
  the current run against any snapshot in `history/` (the newest by
  default).

### Stage by stage

1. `/research "Company Name" TYPE` — starts a new analysis. `TYPE` is one of
   `TECHNOLOGY`, `DEAL`, or `POLICY`. This writes `analyses/<slug>/.meta` and
   sets `analyses/.last_target` to this analysis, so it becomes the default
   target for subsequent commands.
2. Run the advisors, in any order:
   - `/science` — scientific/technical assessment
   - `/investment-advisor` — commercial viability and (for deals) deal terms
   - `/political` — political and regulatory risk
3. `/bull` — steelmans the investment thesis using the advisor outputs
4. `/bear` — generates rival readings against the Bull case
5. `/executive` — synthesizes everything into one report,
   `05_executive_report.md` (grade, scorecard, narrative, crux, catalysts,
   next actions), and pushes it to the Notion main page

Each step needs the previous ones to have run (advisors need research, Bull
needs advisors, Bear needs Bull, Executive needs everything). If a required
file is missing, the skill will tell you what to run first.

### Targeting a company

Every command except `/research` takes an optional `[company-or-slug]`
argument, e.g. `/bear "Fervo Energy"` or `/bear fervo`. This resolves to a
slug (via the standard slug convention below), looks up
`analyses/<slug>/.meta`, and becomes the new default target
(`analyses/.last_target`).

If you omit the argument, the command falls back to whatever was last
targeted by any command — so once you've pointed at a company, you can keep
running commands against it without repeating the name. To switch to a
different company, just pass its name or slug to the next command; no need
to re-run `/research`.

## Output structure

Each analysis lives in `analyses/<slug>/` (slug derived from the company
name — see Slug convention below):

```
analyses/
  .last_target           <- slug of the most recently targeted analysis
  <slug>/
    01_research_collector_full.md / _summary.md
    02a_science_advisor_full.md / _summary.md
    02b_investment_advisor_full.md / _summary.md
    02c_political_advisor_full.md / _summary.md
    03_bull_full.md
    04_bear_full.md
    05_executive_report.md
    .meta
    .notion
```

`_full.md` files are the complete analyses; `_summary.md` files are short
briefings for downstream stages.

Each stage (except `/ingest-materials`) also mirrors its output to Notion as
it finishes — Notion is the easiest way to browse a finished analysis (one
page per company, with sub-pages for each stage). If a stage reports that
Notion sync didn't happen, run `/notion-sync` to catch up without re-running
the analysis. See `CLAUDE.md`'s "Notion sync" section for setup.

## Adding deal materials (data rooms, pitch decks, etc.)

If you have non-public materials for a deal (pitch deck, financial model,
SPV/legal docs), process them before running `/research`:

1. Run `/ingest-materials "Company Name" <path-to-folder-or-file>` — pass the
   path to wherever the raw files currently live (e.g. a Downloads folder or
   a single PDF). This copies them into
   `analyses/<slug>/00_deal_materials/raw/` and processes them in one step;
   you don't need to know the slug or create any folders yourself.

   (Alternatively, run `/ingest-materials "Company Name"` with no path first —
   it creates `analyses/<slug>/00_deal_materials/raw/` and tells you the exact
   path and slug. Drop files in by hand, then run the same command again.)

2. The skill produces:
   - `materials_digest.md` — a prose digest of narrative/strategic content
   - `manifest.md` — a routing table for charts, tables, and other exhibits,
     with a suggested advisor for each (Science / Investment / Political)
   - `exhibits/` — the extracted chart/table images referenced by the manifest
3. Review `manifest.md` and adjust the routing if needed
4. Run `/research` as usual — it picks up `materials_digest.md`
   automatically, and advisors consult `manifest.md` for exhibits routed to
   them

**New documents later.** Run `/ingest-materials "Company Name" <path>`
again with the folder that holds the new or updated files. It processes
only files that are new or whose contents changed, and says "nothing to
ingest" if every file matches what it already has. An updated copy of an
existing file replaces that file's digest sections and exhibits, and the
old version is kept in `raw/.superseded/{date}/`. The digest's
`## Ingestion log` table records what came in and when.

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

- `claude-sonnet-5`: Science Advisor, Political Advisor, Bull, Notion Sync
- `claude-opus-5`: Research, Investment Advisor, Bear, Executive, Ingest Materials
  (higher-judgment stages — Investment Advisor is grouped here intentionally,
  for deal-terms judgment, even though the other advisors run on sonnet)

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

After `/executive` produces `05_executive_report.md`, paste its YAML
frontmatter (grade, confidences, status, risk) and its `## Scorecard` table
into a new conversation and run:

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
