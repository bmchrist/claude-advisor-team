# Investment Analysis Pipeline — Technical Reference

Multi-agent investment analysis. Each pipeline stage runs as an isolated
skill with `context: fork` — it receives only the specific prior-stage files
it needs, writes its outputs to disk, and returns a brief summary.

For human-facing usage instructions, see `README.md`. For status and planned
changes, see `projectplan.md`.

## Pipeline stages

| Command | Needs | Writes |
|---|---|---|
| `/research "Company" TYPE` | — | `01_research_collector_full.md`, `01_research_collector_summary.md` |
| `/science` | research full | `02a_science_advisor_full.md`, `02a_science_advisor_summary.md` |
| `/investment-advisor` | research full | `02b_investment_advisor_full.md`, `02b_investment_advisor_summary.md` |
| `/political` | research full | `02c_political_advisor_full.md`, `02c_political_advisor_summary.md` |
| `/bull` | rc summary + advisor fulls | `03_bull_full.md` |
| `/bear` | rc summary + advisor fulls + bull | `04_bear_full.md` |
| `/executive` | rc summary + advisor summaries + bull + bear | `05_executive_data.json`, `05_executive_narrative.md`, `05_executive_report.html` |

## Context window discipline

- Advisors receive: RC full output + any local context docs (no web search)
- Bull receives: advisor full outputs + RC summary
- Bear receives: advisor full outputs + Bull full + RC summary
- Executive receives: advisor summaries (not full) + Bull full + Bear full

## State

The active analysis is tracked in `analyses/.current`:
```
company="Acme+"
slug="acme_plus"
type="DEAL"
```

`/research` writes this file. All subsequent skills read it automatically.

**This mechanism is planned to change — see `projectplan.md` item 1** (per-folder
`.meta` + a `.last_target` fallback, with an optional target argument on each
skill). Until that lands, this is the current behavior.

## Output structure

```
analyses/
  acme_plus/
    01_research_collector_full.md
    01_research_collector_summary.md
    02a_science_advisor_full.md
    02a_science_advisor_summary.md
    02b_investment_advisor_full.md
    02b_investment_advisor_summary.md
    02c_political_advisor_full.md
    02c_political_advisor_summary.md
    03_bull_full.md
    04_bear_full.md
    05_executive_data.json
    05_executive_narrative.md
    05_executive_report.html
```

Deal analyses may also include `00_deal_materials/` (pitch deck digest, deal
terms, financial exhibits) as input context for `/research` — see
`projectplan.md` item 3 for the planned digest + manifest convention.

## Slug convention

Company name → slug: lowercase, `+` → `_plus`, `&` → `_and`, non-alphanumeric
runs → `_`, trim leading/trailing underscores.

Examples: `Acme+` → `acme_plus`, `AT&T` → `at_and_t`, `Bright Energy` →
`bright_energy`

## Models

- Research, advisors, Bull: `claude-sonnet-4-6`
- Bear, Executive: `claude-opus-4-6`

Update these in the relevant SKILL.md frontmatter if you want to switch models.

## Architecture notes

- Adversarial spine: Bull + Bear are primary agents, not parallel specialists
  reporting to a synthesizer
- Ben plays the Executive/judge role for the final investment call, informed
  by the automated Executive synthesis
- Each skill is isolated (`context: fork`) — don't assume shared state beyond
  the files documented above

## System framing — counterinduction

Apply counterinduction to every key claim — generate the rival reading
alongside the primary reading:
- A pilot = progress OR inability to escape pilot stage
- Grant/public funding = strategic validation OR private capital won't carry
  the risk
- Strong orderbook = genuine demand OR policy hedging by buyers
- First-mover position = durable moat OR first-mover disadvantage

Define "working": repeat orders without subsidy dependence, private capital
at risk, costs approaching parity, high utilization.

Define "failing": niche-shifting, order cancellations, low utilization, cost
curves not improving, continued subsidy dependence after 5+ years.

Always explicitly state what evidence would change your conclusion. Stay in
your assigned role. Give the strongest version of your perspective.
