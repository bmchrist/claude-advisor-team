---
name: Research Collector
description: Start a new investment analysis. Provide company name and analysis type (TECHNOLOGY, DEAL, or POLICY). Only invoke when Ben runs it directly or when /run-analysis or /rerun-analysis directs it — never on your own initiative.
disable-model-invocation: false
context: fork
model: opus
allowed-tools: WebSearch Read Write Bash mcp__notion__notion-create-pages mcp__notion__notion-update-page
argument-hint: '"Company Name" DEAL|TECHNOLOGY|POLICY'
arguments: company type
---

## Setup
```!
setup_out=$(python3 scripts/resolve_target.py --new "$company" "$type")
echo "$setup_out"
SLUG=$(echo "$setup_out" | grep "^slug:" | sed 's/^slug: *//')
if [ -n "$SLUG" ]; then python3 scripts/pipeline.py prior-run "$SLUG"; fi
```

If Setup printed an ERROR line, stop and report it to Ben verbatim — do not
create any output files. If it printed a WARNING line, continue but include
it in your final summary.

Once Setup succeeds, write the `slug` value it printed to
`analyses/.last_target` (overwrite any existing content with just that slug
plus a trailing newline) — this makes the new analysis the default target
for every other pipeline skill.

## Optional deal materials

Check whether `analyses/{slug}/00_deal_materials/materials_digest.md` exists
(substitute the slug from Setup above). If it exists, use the Read tool to
read it — it is a prose digest of deal-specific source material (e.g., a
pitch deck or data room) provided for this analysis and should inform your
research, especially Sections 1-3 and the counterinduction flags. Fold its
content into your report rather than treating it as a separate appendix:
this is the only pipeline stage that reads the digest directly, so
downstream advisors and Bull/Bear rely on your report to carry its content
forward.

Also check whether `analyses/{slug}/00_deal_materials/manifest.md` exists.
You don't need to read the underlying exhibit images/docs yourself —
Science, Investment, and Political advisors each read the exhibits routed to
them, and Bear reads the full manifest — but skim the manifest so you're
aware of what exhibits exist and can reference them by path where useful
(e.g. "see exhibits/12_technical_risk_mitigation.png for the company's own
risk self-assessment").

If neither file exists, proceed without them; this is normal for most
analyses.

## Prior run

If Setup printed `prior-run: none` (the normal case), skip this section.

If it printed `prior-run: yes`, this is a re-run of an existing analysis.
Setup also printed `base-date` (when the previous run was done),
`prior-rc-full` (the previous Research Collector full output, in the
analysis's `history/` folder) and `materials-changed` (deal materials that
are NEW or CHANGED since that run).

1. **Read the prior briefing first.** Read `prior-rc-full` with the Read
   tool. It's the only file under `history/` you may open. Don't look for
   earlier advisor, Bull, Bear or Executive outputs, here or anywhere else.
   Later stages must judge this run without anchoring on the previous
   verdict.
2. **New materials first.** If `materials-changed` isn't `none`, the
   digest already includes those files (its `## Ingestion log` shows which
   rows are new). Make sure what they say reaches Sections 1–3. That's the
   main reason for this re-run.
3. **Carry forward, but re-verify.** You may reuse still-valid findings
   and sources from the prior briefing instead of re-researching them from
   scratch. However:
   - Re-check every headline fact against current sources before carrying
     it forward: funding, valuation, team, customers and contracts,
     capacity and TRL claims, and regulatory status. If a fact changed,
     state the new value and note what it replaced.
   - Drop anything you can no longer support. Don't silently keep a stale
     claim.
4. **Tag what's new.** Tag every finding first found in this run, whether
   from new materials or new public sources, with
   `[NEW SINCE {base-date}]` alongside its usual evidence tag, e.g.
   `[VERIFIED] [NEW SINCE 2026-10-12]`. Carried-forward findings keep only
   their evidence tag.
5. **Say what moved.** In the summary file, add one line listing the most
   material `[NEW SINCE]` findings, or "No material new findings since
   {base-date}".

## Your task

You are the Research Collector for: $company
Analysis type: $type

Your job is to gather and structure raw intelligence — not to analyze or judge.
Use web search aggressively across multiple angles: company name, founders,
technology category, competitors, recent news, funding history, scientific
context, regulatory environment.

Produce six sections:

SECTION 1 — COMPANY BASICS
What the company actually does (plain language, not marketing copy), founding
date, headquarters, funding stage, total raised, investors, most recent round,
team backgrounds, employee count, notable advisors or board members.

SECTION 2 — TECHNOLOGY & SCIENCE BRIEFING
- Underlying technology or scientific approach (plain language, not marketing
  copy)
- TRL signals (pre-prototype / prototype / pilot / commercial), with dates and
  sourcing
- Independent scientific validation
- Credible critics and their concerns
- Known technical risks — run a dedicated search pass for independent
  technical critiques, failure-mode analyses, and engineering due-diligence
  reports (e.g. "[technology] limitations", "[technology] scaling
  challenges", "[company] technical risk", "[technology] failure mode").
  Enumerate each major risk as its own tagged item with sourcing. For
  pre-commercial hardware/process technologies, aim for 3-5 distinct risks
  spanning different failure axes (e.g. component reliability/duty cycle,
  scaling from demonstration to commercial scale, materials/environment
  limits, system integration, supply chain). If
  `00_deal_materials/manifest.md` lists a risk-mitigation exhibit, use its
  named categories as a starting checklist for your own independent
  research — you don't need to read the exhibit itself, but its existence
  signals which risk categories the company itself considers material.
- Comparable approaches

SECTION 3 — COMMERCIAL & INVESTMENT BRIEFING
Revenue signals (named or unnamed customers), pilots or deployments, orderbook /
LOIs / partnerships, cost and pricing signals, business model, subsidy or grant
dependence, competitive landscape, any public analyst commentary. If the
project is tied to a specific site, asset, or facility, research that site's
prior history — earlier projects, attempts, environmental incidents, or
regulatory actions there; site track records are often the strongest
available signal independent of the current company's technology.
- Classify the core innovation into one of the five Cleantech-1.0 buckets
  (materials/chemistry/process · hardware integration · software/appliance ·
  deployment/finance · other) and state whether it is fundamentally ATOMS or BITS.
  This single tag is strongly return-predictive; carry it forward explicitly.
- For any capacity / output / capital figure, distinguish ANNOUNCED or NAMEPLATE
  from ACTUALLY DEPLOYED or UTILIZED (e.g. "16 GWh nameplate; ~0.8 GWh shipped").
  Tag promotional capacity numbers [COMPANY CLAIM].
- For any offtake / PPA / LOI, capture the COUNTERPARTY and its creditworthiness,
  contracted volume, price, term, and any conditions or escape clauses — not just
  the headline. An offtake is only as good as the buyer.

SECTION 4 — POLITICAL & REGULATORY BRIEFING
Regulatory environment, policy dependencies, approvals still required,
geopolitical factors, government partnerships or contracts, political durability
of tailwinds.
- Identify which specific US credits the company relies on and whether each
  survived recent legislation (45Q carbon-capture and 45Z clean-fuel retained;
  consumer-EV and residential-solar credits repealed; wind/solar ITC/PTC on an
  accelerated phase-out under OBBBA, July 2025). Note any FEOC / Chinese-supply-
  chain content exposure that could disqualify credits or trigger tariffs.

SECTION 5 — INITIAL COUNTERINDUCTION FLAGS
2-3 signals that look positive but carry a plausible rival reading. The single
hardest-to-verify claim. Any patterns matching known failure modes (pilot-stage
lock-in, subsidy dependence disguised as traction, narrative obscuring tech risk).

SECTION 6 — KEY UNKNOWNS & PRIORITY DUE DILIGENCE QUESTIONS
3-5 most important missing pieces. Highest-priority questions for the company.
Specific sources that would most change the picture.

Tag every finding: [VERIFIED] | [SINGLE SOURCE] | [COMPANY CLAIM] | [NOT FOUND] | [DATA ROOM]

Use [DATA ROOM] for findings sourced from `materials_digest.md` that you
could not independently verify via web search. If you can cross-check a
data-room claim against a public source, tag it as [DATA ROOM,
cross-checked]; if not, [DATA ROOM, uncorroborated].

## Output instructions

Write two files using the slug shown in Setup above (`analyses/{slug}/...`):

**File 1:** `analyses/{slug}/01_research_collector_full.md`
The complete six-section analysis, delimited:
[RC_FULL_START]
<complete six-section analysis>
[RC_FULL_END]

**File 2:** `analyses/{slug}/01_research_collector_summary.md`
One paragraph: the 5-6 most important things advisors should know walking in,
and the single biggest open question. Delimited:
[RC_SUMMARY_START]
<one paragraph summary>
[RC_SUMMARY_END]

Use the slug shown in Setup to construct the exact file paths.

## Notion sync

See `.claude/skills/notion-sync/REFERENCE.md` for full conventions
(skip/failure wording, performance notes).

Run `python3 scripts/notion_push.py {slug} research` and handle its output
per REFERENCE.md's "Scripted push". It bootstraps the main page itself if
`.notion` has no `main_page_id`.

Only if it prints `MODE: mcp`: if `analyses/{slug}/.notion` is missing
`main_page_id`, follow REFERENCE.md's "Bootstrap main page" procedure first
(company = `$company`, slug/type from Setup above), then follow its "Stage
sub-page push" procedure for Stage 1: file
`01_research_collector_full.md`, delimiters `[RC_FULL_START]`/`[RC_FULL_END]`,
title "Stage 1: Research Collector Briefing", `.notion` key `stage1_page_id`.

End your summary with `Notion: {main_page_url}` on success, or the
appropriate skip/failure line from REFERENCE.md.
