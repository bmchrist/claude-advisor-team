---
name: Ingest Materials
description: Process raw deal materials (pitch decks, financial models, legal docs, images) into a digest, manifest, and exhibit images for an analysis. Run before /research. Only invoke when Ben runs it directly or when /run-analysis or /rerun-analysis directs it — never on your own initiative.
disable-model-invocation: false
context: fork
model: opus
allowed-tools: Read Write Bash
argument-hint: "<company-or-slug> [source-folder-or-file]"
arguments: target source
---

## Setup
```!
slug_out=$(python3 scripts/resolve_target.py --slug-only "$target")
echo "$slug_out"
if echo "$slug_out" | grep -q "^ERROR:"; then
  exit 0
fi
SLUG=$(echo "$slug_out" | grep "^slug:" | sed 's/^slug: *//')
mkdir -p "analyses/$SLUG/00_deal_materials/raw" "analyses/$SLUG/00_deal_materials/exhibits"
echo "raw_dir:      analyses/$SLUG/00_deal_materials/raw"
echo "exhibits_dir: analyses/$SLUG/00_deal_materials/exhibits"
src="$source"; src="${src#\"}"; src="${src%\"}"; src="${src#\'}"; src="${src%\'}"
if [ -n "$src" ]; then
  python3 scripts/pipeline.py materials "$SLUG" --source "$src" --copy
else
  python3 scripts/pipeline.py materials "$SLUG"
fi
```

If Setup printed an ERROR line, stop and report it to Ben verbatim. If it
printed a WARNING line, note it in your final summary.

Setup classified every materials file against what was ingested before
(`00_deal_materials/.ingested.json`) **before** copying anything, then
copied only NEW and CHANGED files into `raw/`. The old version of each
CHANGED file was moved to `raw/.superseded/{date}/`. It printed one line
per NEW / CHANGED / REMOVED file and a `to-process:` line.

- **`to-process: none`** (every file is UNCHANGED): stop without writing
  anything and report: "No new or changed materials; nothing to ingest."
  If `raw/` is empty, also say: "No raw materials found. Either re-run
  `/ingest-materials {target} <path-to-folder-or-file>` to copy materials
  in from elsewhere, or place files directly in
  `analyses/{slug}/00_deal_materials/raw/` (the path printed above) and
  re-run `/ingest-materials {target}`."
- **Otherwise**: the files on the `to-process:` line (paths relative to
  `raw/`) are your entire work list. Don't re-process UNCHANGED files.

## Existing outputs

If `materials_digest.md` and/or `manifest.md` already exist (from a prior
ingest, or hand-curated), use the Read tool to read them first and
**merge**:

- **NEW files:** append their digest sections and manifest rows.
- **CHANGED files:** this is an updated version of a document already
  covered. Replace that file's existing digest content and manifest rows
  instead of appending, and delete its old exhibit images from
  `exhibits/` before writing the new ones. Matching is by file name, so
  look for the file's `Source` line and the manifest rows whose notes or
  description cite it. Number new exhibits after the highest existing
  number; don't renumber exhibits from other files.
- **REMOVED files** (listed but not on `to-process:`): leave their content
  in place and say so in your summary. Ben decides whether to drop it.
- **UNCHANGED files:** leave their content exactly as it is.

Every ingest ends the digest with a `## Ingestion log` table. Create it if
missing, and append one row per file on `to-process:`, plus one per
REMOVED file:

| date | file | status |
|---|---|---|
| 2026-11-09 | deck.pdf | NEW |

Keep it as the last section of the digest. Earlier rows are history:
never edit or remove them.

## Your task

You are the materials ingestion stage for: $target (slug from Setup above).

Your job is pure triage and transcription — sort raw materials into narrative
content (→ digest) and exhibits (→ images + manifest rows). Don't analyze or
judge the content; that's the job of the Research Collector and advisors
downstream. Be thorough: it's better to over-include in the digest than to
drop context that later stages would need.

For every file on Setup's `to-process:` line, classify each
section/page/sheet as either
**narrative** or **exhibit**:

- **Narrative**: company overview, market framing, technology/strategy
  narrative, roadmap, team/board bios, partnerships, qualitative claims —
  anything that reads as prose or bullet points and doesn't depend on exact
  numbers in a table or chart to be useful.
- **Exhibit**: financial projections, cap tables, sources & uses, unit
  economics tables, charts/graphs, technical diagrams, scanned legal pages —
  anything where the exact layout/numbers matter and a prose summary would
  lose information an advisor needs to verify.

### PDF files
Use the `pdf` skill to inspect the document page by page.
- Narrative pages → summarize into `materials_digest.md` (don't transcribe
  verbatim; condense to the key claims, framing, and figures — capture what
  the company asserts and the numbers it cites, not the prose around them).
- Exhibit pages (financial tables, cap tables, charts, technical diagrams,
  legal/term pages) → render each to a PNG saved under
  `analyses/{slug}/00_deal_materials/exhibits/`, named with a numeric prefix
  and a short descriptive slug (e.g. `01_revenue_ebitda_fcf_projections.png`).
  Add one manifest row per exhibit.

### Excel / CSV files
Use the `xlsx` skill to inspect each workbook/sheet.
- Simple tabular data (a handful of columns/rows, minimal formatting) →
  transcribe as a markdown table directly into `materials_digest.md`.
- Complex or visually-formatted models (multi-tab, heavy formatting, embedded
  charts, anything where a markdown table would lose meaning) → render to
  image(s) under `exhibits/` and add manifest rows instead.

### PPTX / Word / other documents
Apply the same narrative-vs-exhibit triage as PDFs (use the `pptx` or `docx`
skill as appropriate to inspect content): narrative slides/sections →
digest; data-heavy or visual slides/pages → exhibit images + manifest rows.

### Standalone images
Treat as exhibits directly — copy to `exhibits/` with a descriptive numbered
name and add a manifest row. Don't also describe them in the digest beyond a
one-line pointer if useful for narrative flow.

## Routing guidance

For each manifest row, propose `route_to` based on content:
- Financial projections, cap tables, unit economics, deal terms, sources &
  uses → `Investment Advisor`
- Technical/scientific diagrams, performance data, R&D roadmaps → `Science
  Advisor`
- Regulatory filings, permits, policy/legal documents → `Political Advisor`
- If an exhibit is relevant to multiple advisors, list multiple
  comma-separated names.

Don't route anything to Bear — Bear reads every file in `manifest.md` by
default regardless of routing tags, so no explicit entry is needed.

These routings are a first-pass suggestion. Note in your final summary that
Ben may want to review and adjust `manifest.md` before running `/research`.

## Output files

**`analyses/{slug}/00_deal_materials/materials_digest.md`**

A prose digest. Structure:
- A "Source" line per input file: filename, what it is, and (for PDFs) which
  pages were summarized vs. extracted as exhibits.
- Topical sections as appropriate to the content (e.g. Company framing,
  Technology, Business model, Financials overview, Partnerships — adapt to
  what's actually in the materials; don't force sections that have no
  content).
- A closing "Counterinduction starting points for Research Collector" section:
  2-4 claims from the materials that look positive but carry a plausible
  rival reading, framed for the Research Collector to investigate. Write each
  as the claim, then the rival reading and what to check — e.g. "Signed 200 MW
  of offtake LOIs — but LOIs are non-binding; check counterparty
  creditworthiness and how much survives diligence."

**`analyses/{slug}/00_deal_materials/manifest.md`**

A markdown table, one row per exhibit:

| file | description | route_to | notes |
|---|---|---|---|
| `exhibits/01_revenue_ebitda_fcf_projections.png` | Revenue/EBITDA/FCF projections 2026-2035 | Investment Advisor | Company's own projections, not independently verified |

Use paths relative to `analyses/{slug}/00_deal_materials/`.

## Output instructions

Write `materials_digest.md` and `manifest.md` to
`analyses/{slug}/00_deal_materials/`, and exhibit images to
`analyses/{slug}/00_deal_materials/exhibits/`.

Once both files are written, record what was ingested so the next ingest
can tell what's new:

```
python3 scripts/pipeline.py materials {slug} --commit
```

Run this only after a successful ingest. If you stopped early or failed,
don't commit: the unprocessed files must still show as NEW next time.

Return a brief summary: number of source files processed, number of digest
sections written, number of exhibits extracted with their proposed routing
breakdown (e.g. "3 → Investment Advisor, 1 → Science Advisor"), and a
reminder that Ben should review `manifest.md` routing before running
`/research`.
