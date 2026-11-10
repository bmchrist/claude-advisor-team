# Investment Analysis Pipeline — Project Plan

For usage instructions, see `README.md`. For the technical/operational
reference (pipeline stages, file formats, methodology), see `CLAUDE.md`.

## Status

The pipeline runs end to end as skills: `/ingest-materials`, `/research`,
the three advisors, `/bull`, `/bear`, `/executive`, plus the
`/run-analysis` / `/rerun-analysis` orchestrators and `/compare-runs`.

## Planned work

### 1. Push to Notion by script

See `implementation_plan_2026-11-09_notion_api.md`.

### 2. Analysis coverage additions

Six areas the analyses should cover explicitly. Today each is either
missing or only gathered as raw facts by RC without being assessed. For
each one, decide which stage owns the assessment, and whether Executive
surfaces it as its own short section.

- [ ] **Competitors and how they stack up.** RC already collects
      competitors and the competitive landscape. Nothing compares them.
      Add a comparison section to Science (competing or equivalent
      technologies: performance, maturity, cost curve) and to Investment
      (competing companies: funding, traction, pricing, positioning).
- [ ] **Technologies arriving in the next 5 years.** What else is likely
      to mature within about 5 years and change the picture, good or bad:
      substitutes that could leapfrog the company, and enablers that could
      help it. Nothing covers this today. Natural home: Science, with Bear
      using the threats.
- [ ] **Team deep dive.** RC lists team backgrounds. No stage assesses
      them: who the people are, why they're suited to this problem, gaps
      in the team, and track record of building and scaling this kind of
      thing.
- [ ] **IP breakdown.** Where IP is actually locked down (patents, trade
      secrets, process know-how), how strong it is, and how much of an
      edge it gives against the competitors above. Nothing covers this
      today.
- [ ] **Exit paths.** Partially covered: the counterinduction framing in
      CLAUDE.md treats named acquirer interest as possibly a thin field,
      and Bear flags weak exits. No stage lays out the realistic exit
      paths (acquirers, IPO, project-finance or infrastructure sale),
      precedents, and timing.
- [ ] **Adoption Readiness Levels / bankability.** Incorporate ARL and the
      CTVC bankability framing: https://www.ctvc.co/project-finance-bankability/
      Investment Advisor asks a general bankability question ("can this
      get project finance? What does a lender need to see?") but doesn't
      use a structured framework. Natural home: Investment Advisor, with
      the ARL level reported alongside the Technical/Commercial Confidence
      stages in Executive.
