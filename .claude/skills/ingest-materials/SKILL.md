---
name: Ingest Materials
description: Process raw deal materials (pitch decks, financial models, legal docs, images) into a digest, manifest, and exhibit images for an analysis. Run before /research.
disable-model-invocation: true
context: fork
model: claude-opus-4-6
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
export RESOLVED_SLUG=$(echo "$slug_out" | grep "^slug:" | sed 's/^slug: *//')

python3 - << 'EOF'
import os, shutil
slug = os.environ['RESOLVED_SLUG']
source = """$source""".strip().strip('"').strip("'")
raw_dir = f'analyses/{slug}/00_deal_materials/raw'
exhibits_dir = f'analyses/{slug}/00_deal_materials/exhibits'
os.makedirs(raw_dir, exist_ok=True)
os.makedirs(exhibits_dir, exist_ok=True)
print(f'raw_dir:     {raw_dir}')
print(f'exhibits_dir: {exhibits_dir}')

if source:
    source = os.path.expanduser(source)
    copied = []
    if os.path.isdir(source):
        for dp, dnames, fnames in os.walk(source):
            dnames[:] = [d for d in dnames if not d.startswith('.')]
            rel = os.path.relpath(dp, source)
            for f in fnames:
                if f.startswith('.'):
                    continue
                src_path = os.path.join(dp, f)
                dst_dir = raw_dir if rel == '.' else os.path.join(raw_dir, rel)
                os.makedirs(dst_dir, exist_ok=True)
                dst_path = os.path.join(dst_dir, f)
                shutil.copy2(src_path, dst_path)
                copied.append(os.path.relpath(dst_path, raw_dir))
    elif os.path.isfile(source):
        dst_path = os.path.join(raw_dir, os.path.basename(source))
        shutil.copy2(source, dst_path)
        copied.append(os.path.relpath(dst_path, raw_dir))
    else:
        print(f'WARNING: source path not found: {source}')
    if copied:
        print(f'copied {len(copied)} file(s) from {source}:')
        for f in copied:
            print(f'  - {f}')

files = sorted(
    os.path.join(dp, f)
    for dp, _, fnames in os.walk(raw_dir)
    for f in fnames
    if not f.startswith('.')
)
if files:
    print('files:')
    for f in files:
        print(f'  - {f}')
else:
    print('files: none')
EOF
```

If Setup printed an ERROR line, stop and report it to Ben verbatim. If it
printed a WARNING line, note it in your final summary.

If `files: none`, stop and report:

"No raw materials found. Either re-run `/ingest-materials {target} <path-to-folder-or-file>`
to copy materials in from elsewhere, or place files directly in
`analyses/{slug}/00_deal_materials/raw/` (the path printed above) and re-run
`/ingest-materials {target}`."

## Existing outputs

Before writing anything, check whether `analyses/{slug}/00_deal_materials/materials_digest.md`
and/or `analyses/{slug}/00_deal_materials/manifest.md` already exist (e.g. from
a prior run, or hand-curated). If they exist, use the
Read tool to read them first and **merge** — append new sections/rows for the
newly-processed files rather than discarding existing content. Don't duplicate
entries for files already covered.

## Your task

You are the materials ingestion stage for: $target (slug from Setup above).

Your job is pure triage and transcription — sort raw materials into narrative
content (→ digest) and exhibits (→ images + manifest rows). Don't analyze or
judge the content; that's the job of the Research Collector and advisors
downstream. Be thorough: it's better to over-include in the digest than to
drop context that later stages would need.

For every file in `raw_dir`, classify each section/page/sheet as either
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

Return a brief summary: number of source files processed, number of digest
sections written, number of exhibits extracted with their proposed routing
breakdown (e.g. "3 → Investment Advisor, 1 → Science Advisor"), and a
reminder that Ben should review `manifest.md` routing before running
`/research`.
