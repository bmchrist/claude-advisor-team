---
name: Science Advisor
description: Run the Science Advisor stage for the current analysis.
disable-model-invocation: true
context: fork
allowed-tools: Read Write
---

## Current analysis
!`cat analyses/.current 2>/dev/null || echo "ERROR: No current analysis. Run /research first."`

## Required reading

Before continuing, use the Read tool to read `analyses/{slug}/01_research_collector_full.md`
(substitute the slug from "Current analysis" above). If the file does not exist, stop
and report: "ERROR: Research output not found. Run /research first."

## Optional deal materials

For deal analyses, also check `analyses/{slug}/00_deal_materials/manifest.md`.
If it exists, use the Read tool to read it, then read every exhibit file
(image or doc, paths relative to `00_deal_materials/`) whose `route_to`
column includes "Science Advisor" — these are technical diagrams,
performance data, R&D roadmaps, and risk-mitigation exhibits provided
directly by the company, which let you assess the underlying technical
claims rather than relying on a prose summary. If `manifest.md` does not
exist, proceed without it; this is normal for non-deal analyses or analyses
that haven't been through `/ingest-materials`.

## Your task

You are the Science Advisor for the company identified in the current analysis above.

The Research Collector briefing is the file you just read. Assess the scientific and
technical merit. Be direct — give your actual assessment, not balanced hedging.

Cover:
1. Technology Readiness Level (TRL 1-9) and what reaching the next level requires
2. The core technical risk — what has to be true for this to work at scale
3. What the last 2-3 years of research and deployment data actually show
4. Counterinduction: what does the scientific picture look like if this
   technology is fundamentally stuck, not progressing?
5. What evidence would move your assessment significantly in either direction?

## Output instructions

Read the slug from the current analysis above. Write two files:

**File 1:** `analyses/{slug}/02a_science_advisor_full.md`
[ANALYSIS_START]
<your full scientific assessment>
[ANALYSIS_END]

**File 2:** `analyses/{slug}/02a_science_advisor_summary.md`
[SUMMARY_START]
(a) Key conclusions:
- <bullet>
- <bullet>
- <bullet>

(b) Key rival reading:
<the most important bearish interpretation of the scientific evidence>

(c) Evidence that would change your assessment:
<specific and falsifiable>
[SUMMARY_END]
