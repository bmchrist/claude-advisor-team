# Investment Analysis Pipeline — Project Plan

For usage instructions, see `README.md`. For the technical/operational
reference (pipeline stages, file formats, methodology), see `CLAUDE.md`.

## Status

Pipeline fully implemented as skills (`/research` through `/executive`).
`/ingest-materials` (data room ingestion, see item 3) is also implemented;
the per-stage manifest-reading behavior it enables (RC/advisors/Bull/Bear) is
still pending.

## Planned changes (next iteration)

### 1. Drop `analyses/.current` — target each company's folder directly
Problem: `.current` is a single global pointer, so jumping between companies
means re-running `/research` (or hand-editing `.current`) every time.

- [ ] Stop writing/reading `analyses/.current` as the source of truth
- [ ] `/research` writes per-company metadata to `analyses/{slug}/.meta`
      (company name, slug, type) instead of the global `.current` — this
      keeps each analysis folder self-describing and jumpable
- [ ] `/research` also writes `analyses/.last_target` (single line: slug) —
      a lightweight "default target" pointer for convenience, distinct from
      `.current` in that it's just a fallback, not a gate
- [ ] Every downstream skill (`/science`, `/investment-advisor`, `/political`,
      `/bull`, `/bear`, `/executive`) gains an optional `target` argument
      (company name or slug):
      - if given, derive slug via the standard slug convention and look up
        `analyses/{slug}/.meta`
      - if omitted, fall back to `analyses/.last_target`, then read that
        slug's `.meta`
      - if neither resolves: clear error telling the user to run `/research`
        or pass a target
- [ ] Update `argument-hint` on each skill to `[company-or-slug]` (optional)
- [ ] Update `CLAUDE.md`'s "State" section to remove `.current` references
      and document `.meta` + `.last_target`
- [ ] Decide whether to delete the existing `analyses/.current`,
      `analyses/.current.fervo` files or just stop using them
- [ ] `analysis_pipeline.py` (the standalone API version) doesn't use
      `.current` today — confirm no changes needed there beyond consistency

### 2. Generate a matching PDF for every markdown output
- [ ] Confirm `npx md-to-pdf` runs in the skill sandbox without a global
      install (an existing `02b_investment_advisor_full.pdf` in
      `analyses/quaise_energy/` suggests this was already tried manually —
      check what produced it)
- [ ] Add a shared stylesheet/config at the project root (e.g.
      `pdf-style.css`) so every generated PDF shares one look ("same format")
- [ ] After each skill writes its markdown output(s), add a Bash step that
      runs `npx md-to-pdf <file>.md --stylesheet pdf-style.css` (or config-file
      equivalent) to produce a sibling `.pdf`:
      - Research Collector: `01_research_collector_full.pdf`
      - Science / Investment / Political advisors: `02a/02b/02c_..._full.pdf`
      - Bull / Bear: `03_bull_full.pdf`, `04_bear_full.pdf`
      - Executive: `05_executive_narrative.pdf` (the HTML report stays as-is)
- [ ] Decide: PDFs for `_summary.md` files too, or `_full` only? (default:
      `_full` + Executive narrative only)
- [ ] Update each `SKILL.md`'s "Output instructions" to mention the PDF step,
      and update `allowed-tools` to include `Bash` where it's currently
      `Read Write` only (science, political, bull, bear advisors)

### 3. Data room materials — digest + manifest
Goal: incorporate non-public materials (decks, financial exhibits, legal docs)
accurately, without every advisor reading every page, and while flagging
data-room-sourced claims distinctly from web-sourced ones. Builds on the
existing `00_deal_materials/` pattern used for Quaise (`pitch_deck_digest.md`
+ `financial_exhibits/*.png`).

**Components:**
- **Digest** (`00_deal_materials/materials_digest.md`, generalizing today's
  `pitch_deck_digest.md`) — prose summary of narrative/strategic content. Read
  by RC and folded into RC's full output, so it reaches every downstream stage
  at no extra cost (no advisor needs to re-read it).
- **Manifest** (`00_deal_materials/manifest.md`) — a routing table, one row per
  raw exhibit (chart, table, image, legal doc): file path, one-line
  description, and which advisor(s) should read the original directly.
  Proposed columns: `file`, `description`, `route_to` (comma-separated advisor
  names), `notes`.
- **Raw exhibits** — unchanged in spirit: images/docs in any subfolder (e.g.
  `financial_exhibits/`), referenced by path from the manifest. The manifest
  is the single source of routing truth, not folder naming — no need to
  generalize folder names like `financial_exhibits/` to match advisor domains.

**Ingestion (`/ingest-materials` skill):**

A new pipeline pre-stage, separate from RC and from advisor roles. Run before
`/research` against a folder of raw uploads (PDF, XLSX, PPTX, images, etc.);
produces the digest + manifest + exhibit images described above.

- [x] New skill `/ingest-materials [company-or-slug]`, model
      `claude-opus-4-6` — accuracy and judgment (narrative vs. exhibit, simple
      vs. complex table) matter more than cost for this one-time-per-deal step.
      Implemented at `.claude/skills/ingest-materials/SKILL.md`
- [x] Input: raw files dropped in `analyses/{slug}/00_deal_materials/raw/` —
      PDFs, Excel workbooks, PowerPoint decks, images, etc.
- [x] Output: `materials_digest.md`, `manifest.md`, and extracted exhibit
      images written to `00_deal_materials/exhibits/`, per the conventions
      above (existing `financial_exhibits/` for quaise_energy is left as-is —
      manifest paths are what matter, not folder naming)
- [x] PDF handling (using the `pdf` skill): split by page —
      narrative/strategy pages get summarized into `materials_digest.md`;
      chart/table/financial pages get rendered to images under
      `00_deal_materials/exhibits/` and added as rows to `manifest.md` with a
      description and proposed `route_to`
- [x] Excel handling (using the `xlsx` skill): simple tabular data gets
      transcribed as markdown tables directly into `materials_digest.md`;
      complex or visually-formatted models (multi-tab, heavy formatting, charts)
      get rendered to images and added to `manifest.md` instead
- [x] Other formats (PPTX, standalone images, Word docs) get the same
      narrative-vs-exhibit triage as PDFs
- [x] `route_to` values are a first-pass suggestion by `/ingest-materials`
      (e.g. financial models → Investment Advisor, technical diagrams →
      Science Advisor) — Ben can hand-edit `manifest.md` afterward to correct
      routing before running `/research`
- [x] This resolves the README's "(this is currently not accurate)" flag on
      "Adding deal materials" — `README.md` now documents the
      `/ingest-materials` → review manifest → `/research` flow
- [x] Optional `source` argument (`/ingest-materials "Company" <path>`) —
      copies files from an arbitrary local path (file or folder, recursive)
      into `analyses/{slug}/00_deal_materials/raw/` before processing, so Ben
      doesn't need to know the slug or create folders by hand. Without
      `source`, the skill still self-bootstraps: first run creates `raw/` and
      reports the path/slug for manual file placement
- [ ] Not yet implemented: `/ingest-materials` doesn't touch
      `analyses/.current` / `.meta` (consistent with item 1's direction —
      it derives the slug itself from the `company-or-slug` argument). Once
      item 1 lands, confirm this stays consistent
- [ ] Test `/ingest-materials` end-to-end against a real set of raw materials
      (e.g. the Quaise deck) once available, and sanity-check the
      digest/manifest output quality

**Per-stage behavior:**
- [x] RC: if `00_deal_materials/` exists, read `materials_digest.md` (as
      today) and fold it into Sections 1-3 as appropriate; note the
      manifest's existence for downstream stages but doesn't need to read
      every exhibit itself
- [x] RC tagging vocabulary gains `[DATA ROOM]` alongside `[VERIFIED] |
      [SINGLE SOURCE] | [COMPANY CLAIM] | [NOT FOUND]` — findings sourced from
      the digest get this tag. Where RC can cross-check a data-room claim
      against web search, distinguish `[DATA ROOM, cross-checked]` vs
      `[DATA ROOM, uncorroborated]`
- [x] Each advisor (Science, Investment, Political): after required reading,
      check `00_deal_materials/manifest.md` for rows where `route_to` includes
      its name, and Read those files directly (image or doc) as primary
      sources for that content
- [x] Bull: no manifest access by default — works from advisor outputs as
      today, since advisors have already incorporated the relevant exhibits
- [x] Bear: broader default access — if `00_deal_materials/manifest.md`
      exists, Bear reads *every* file listed in it regardless of routing tags,
      so it can check whether the Bull/advisors' reading of a chart or table
      actually matches the source

  Implemented 2026-06-10 across `research`, `science`, `investment-advisor`,
  `political`, `bull`, and `bear` SKILL.md files. Investment Advisor also
  retains a backward-compat fallback to the legacy `spv_deal_terms.md` /
  `financial_exhibits/` convention for analyses pre-dating
  `/ingest-materials` (e.g. `quaise_energy_original`).

  Follow-up (2026-06-10): RC's Section 2 (Technology & Science Briefing) was
  restructured into a bulleted list, with "known technical risks" pulled out
  into its own dedicated, more demanding instruction (run a separate search
  pass for independent technical critiques/failure-mode analyses, enumerate
  3-5 distinct risks for pre-commercial hardware, and use any
  `manifest.md` risk-mitigation exhibit as a checklist of categories to
  research). Section 3 also gained an instruction to research a project's
  site/asset history when applicable (e.g. would have surfaced
  Newberry/AltaRock's prior seismicity history for Quaise).

**Open items / decisions:**
- [x] Who/what creates the digest + manifest? Resolved — a new
      `/ingest-materials` skill (Opus), described above. Today's Quaise
      materials remain hand-curated as a reference example; new analyses go
      through `/ingest-materials`
- [x] Chart/table-heavy PDFs need to become images before any of this works —
      handled by `/ingest-materials`'s PDF page-splitting via the `pdf` skill
- [ ] Update `CLAUDE.md`'s "Output structure", "Pipeline stages", and "Models"
      sections to document the digest + manifest convention, the
      `[DATA ROOM]` tag, and the new `/ingest-materials` stage
- [ ] Update `README.md`'s "Adding deal materials" section once this lands —
      the ingestion step makes the "automatically picked up" claim accurate

## Open issues
- JSON output from Executive may need prompt refinement if it doesn't parse
  cleanly on first real runs
- Confirm how research/advisor skills should handle non-text context docs
  (Quaise's financial exhibits are PNGs)
