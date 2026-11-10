---
name: Rerun Analysis
description: Re-run an existing analysis when new documents arrive (or as a public-research refresh), keeping the previous run in history/ and ending with a comparison of what changed and why. Only run when Ben invokes /rerun-analysis.
disable-model-invocation: true
allowed-tools: Bash Read Skill
argument-hint: '"Company Name" [new-docs-path] [--force] [--from <stage>]'
---

You are the orchestrator for a re-run. You run in the main session (no
fork). Like `/run-analysis`, you do **no analysis yourself**. All
bookkeeping goes through `scripts/pipeline.py`.

## Setup

```!
python3 "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/scripts/pipeline.py" root
echo "cwd: $(pwd)"
```

If `cwd` differs from `root`, stop and tell Ben: "This session's working
directory is `<cwd>`, but the pipeline must run from `<root>`. Restart
Claude Code from the repo root and re-run."

Arguments received: `$ARGUMENTS`

## Step 0 — Read the engine rules

Read `.claude/skills/run-analysis/SKILL.md` with the Read tool. Its
**Rules**, its stage table, and its **Step 2 (Loop)** and **Step 3
(Notion catch-up)** apply here unchanged. This run adds the `compare`
stage, whose arguments are `<slug> <snapshot>` (the `snapshot` line from
Step 1).

## Step 1 — Check, snapshot, start

Parse the arguments:

- **Company:** the first argument, quoted if it has spaces.
- **Documents path:** an optional path to new documents.
- **Flags:** optional `--force` and `--from <stage>`.

Then run:

```
python3 <root>/scripts/pipeline.py rerun-init "<company>" [--source "<path>"] [--force] [--from <stage>]
```

- **`ERROR:`**: report it verbatim and stop. This covers "no analysis
  found" (point Ben to `/run-analysis`), "unfinished run" (point to
  `/run-analysis resume <slug>`), and new documents combined with
  `--from`.
- **`stop:`**: the documents are all unchanged. Report "No new or changed
  documents; nothing to re-run. Pass `--force` to re-run anyway." and stop.
  No tokens have been spent and nothing was written.
- **Otherwise**: the previous run is archived. Note the `slug`, `company`,
  `snapshot`, `reason` and `stages` lines. Tell Ben in two lines which
  documents are new or changed (the `NEW:`/`CHANGED:` lines), or that this
  is a public-research refresh. Then say which stages will re-run, that the
  previous run is in `analyses/<slug>/history/<snapshot>/`, and that it
  takes about 45 minutes from research.

## Step 2 — Run the engine

Follow run-analysis's Step 2 (Loop) and Step 3 (Notion catch-up) exactly,
with this slug. Ingest (if listed) gets the documents path from the
`source` line. `compare` gets `<slug> <snapshot>`.

Research learns it's a re-run on its own: its Setup calls
`pipeline.py prior-run`. Don't pass it anything extra, and don't tell
later stages anything about the previous run's conclusions. They must
judge blind.

## Step 3 — Final report

Run `pipeline.py status <slug>`. If `analyses/<slug>/06_run_comparison.md`
exists, read its "1. Headline" and "3. Open questions, then and now"
sections only. Report to Ben, in this order:

1. **What changed:** the comparison headline, verbatim.
2. **Open questions, then and now:** the table from section 3, verbatim.
3. **Verdict now:** from `05_executive_report.md`'s frontmatter,
   `Grade <grade> / Tech <tc> · Comm <cc> · <status>`.
4. **Stages:** the status table, plus failures, retries and resume
   instructions if the run stopped. If it stopped before `compare`, say
   so. The previous run is safe in `history/<snapshot>/`, and
   `/run-analysis resume <slug>` finishes the re-run, including the
   comparison.
5. **Notion:** `Notion: <main_page_url>`. The comparison is a sub-page of
   the main page.
