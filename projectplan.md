# Investment Analysis Pipeline — Project Plan

For usage instructions, see `README.md`. For the technical/operational
reference (pipeline stages, file formats, methodology), see `CLAUDE.md`.

## Status

Pipeline fully implemented as skills (`/research` through `/executive`).

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

**Per-stage behavior:**
- [ ] RC: if `00_deal_materials/` exists, read `materials_digest.md` (as
      today) and fold it into Sections 1-3 as appropriate; note the
      manifest's existence for downstream stages but doesn't need to read
      every exhibit itself
- [ ] RC tagging vocabulary gains `[DATA ROOM]` alongside `[VERIFIED] |
      [SINGLE SOURCE] | [COMPANY CLAIM] | [NOT FOUND]` — findings sourced from
      the digest get this tag. Where RC can cross-check a data-room claim
      against web search, distinguish `[DATA ROOM, cross-checked]` vs
      `[DATA ROOM, uncorroborated]`
- [ ] Each advisor (Science, Investment, Political): after required reading,
      check `00_deal_materials/manifest.md` for rows where `route_to` includes
      its name, and Read those files directly (image or doc) as primary
      sources for that content
- [ ] Bull: no manifest access by default — works from advisor outputs as
      today, since advisors have already incorporated the relevant exhibits
- [ ] Bear: broader default access — if `00_deal_materials/manifest.md`
      exists, Bear reads *every* file listed in it regardless of routing tags,
      so it can check whether the Bull/advisors' reading of a chart or table
      actually matches the source

**Open items / decisions:**
- [ ] Who/what creates the digest + manifest? Today's Quaise materials were
      hand-curated before `/research` ran. Options: keep as a manual/
      Claude-assisted prep step per analysis, or formalize as a new skill
      (e.g. `/ingest-materials`) that takes raw uploads and produces digest +
      manifest + exhibit images
- [ ] Chart/table-heavy PDFs need to become images before any of this works
      (Quaise's `financial_exhibits/*.png` were extracted by hand) — same open
      question as section 2's ingestion note, likely resolved together
- [ ] Update `CLAUDE.md`'s "Output structure" section to document the digest +
      manifest convention and the `[DATA ROOM]` tag
- [ ] Update `README.md`'s "Adding deal materials" section once this lands

## Open issues
- JSON output from Executive may need prompt refinement if it doesn't parse
  cleanly on first real runs
- Confirm how research/advisor skills should handle non-text context docs
  (Quaise's financial exhibits are PNGs)
