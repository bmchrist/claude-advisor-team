---
name: Run Analysis
description: Run a full analysis end to end — ingest (if materials are given), research, the three advisors in parallel, bull, bear, executive, then Notion catch-up — or resume an interrupted run. Only run when Ben invokes /run-analysis.
disable-model-invocation: true
allowed-tools: Bash Read Skill
argument-hint: '"Company Name" DEAL|TECHNOLOGY|POLICY [materials-path]  |  resume <slug>'
arguments: company type source
---

You are the orchestrator for a one-shot pipeline run. You run in the main
session (no fork) and launch each stage skill with the Skill tool. You do
**no analysis yourself**: never read stage outputs to judge them, never
write or edit analysis files, and never do a stage's work if its skill
fails. All bookkeeping lives in `scripts/pipeline.py`. You run its
commands and act on what they print.

## Rules

- **Paths:** call every script by its absolute path under the repo root
  printed in Setup (`python3 <root>/scripts/pipeline.py …`). Never `cd`.
  Stage skills' Setup blocks use repo-relative paths, so if the session's
  working directory isn't the root, stop and tell Ben (see Setup).
- **Explicit target:** pass every stage its target explicitly (table below).
  Never rely on `analyses/.last_target`.
- **One launch per stage:** always run `pipeline.py start <slug> <stage>`
  immediately before invoking a stage's skill, and only invoke it if
  `start` printed no `ERROR:`. `start` refuses a stage that's already
  running. Never launch the same stage twice: a second invocation of a
  running skill blocks the whole session.
- **Report back:** when a stage's background completion notification
  arrives, run `pipeline.py finish <slug> <stage> ok`. `finish` re-checks
  the outputs itself. It records `failed` if they're incomplete, even if
  the stage said it succeeded, and accepts complete outputs even if the
  stage reported an error (e.g. a network failure after the files were
  written). Never decide this yourself.
- **Output:** write exactly one status line to Ben per completed or failed
  stage, e.g. `✓ science (4m12s, notion: synced)` or `✗ bull (attempt 1/2)
  — relaunching`. Don't paste stage summaries.
- **Errors:** if any `pipeline.py` command prints `ERROR:`, report the line
  verbatim and follow its instruction. Don't work around it.

| stage | skill | arguments |
|---|---|---|
| ingest | `ingest-materials` | `"<slug>" "<source>"` |
| research | `research` | `"<company>" <TYPE>` (company exactly as printed by `init`) |
| science | `science` | `<slug>` |
| investment | `investment-advisor` | `<slug>` |
| political | `political` | `<slug>` |
| bull | `bull` | `<slug>` |
| bear | `bear` | `<slug>` |
| executive | `executive` | `<slug>` |
| compare | `compare-runs` | `<slug> <snapshot>` (re-runs only; snapshot is `prior_run.snapshot` in `.run.json`) |
| notion-catchup | `notion-sync` | `<slug>` (see step 3) |

## Setup

```!
python3 "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/scripts/pipeline.py" root
echo "cwd: $(pwd)"
```

If `cwd` differs from `root`, stop and tell Ben: "This session's working
directory is `<cwd>`, but the pipeline must run from `<root>`. Restart
Claude Code from the repo root and re-run." The stage skills' Setup blocks
would fail otherwise.

Arguments received: company=`$company`, type=`$type`, source=`$source`.

## Step 1 — Start or resume

**Resume** (`$company` is `resume`): the slug is `$type`. Run
`pipeline.py reconcile <slug>`, which settles stages a dead session left
running, then `pipeline.py status <slug>`, and show Ben the status table.
Read the company and type from `analyses/<slug>/.run.json` (`company`,
`type`, `source`). Continue at step 2.

**New run**: run `pipeline.py init "$company" $type "$source"` (leave out
`"$source"` if it's empty). If it prints `ERROR:`, report it verbatim and
stop. That includes "already exists", which points Ben to
`/rerun-analysis`. Otherwise note the `slug`, `company` and `stages`
lines, surface any `WARNING:` line, and tell Ben in one line what's about
to run and that a full run takes about 45 minutes.

## Step 2 — Loop

Repeat until done:

a. Run `pipeline.py next <slug>`.
b. **`done: true`**: go to Step 4.
c. **`blocked:` / `ERROR:`**: a stage failed twice. Go to Step 4 and report
   the failure; don't launch anything else.
d. **`ready:` lists stages**: for each listed stage, in one message, run
   `start` and then invoke its skill (table above). The three advisors are
   ready together and run in parallel. `notion-catchup` is handled by
   Step 3, not here.
e. **Otherwise** (`ready: none` with stages `running:`): end your turn and
   wait. Each stage's completion notification wakes you up. Don't poll,
   sleep, or check files while waiting.

On each completion notification: identify the stage from the
notification, run `finish <slug> <stage> ok`, write the status line, then
go back to (a). If `finish` recorded `failed` with retries left,
`next` lists the stage as ready again, and it's relaunched once by the
normal loop. Say so in the status line.

## Step 3 — Notion catch-up

When `next` lists `notion-catchup`, run
`pipeline.py check <slug> notion-catchup`:

- **`check: complete`**: every stage page and the main page are recorded
  in `.notion`. Run `start` then `finish … ok` for `notion-catchup`
  without invoking anything.
- **Otherwise**: run `start`, invoke `notion-sync` with `<slug>` once, and
  on its notification run `finish … ok`. It gets one attempt. If it still
  fails, `next` reports `done: true` with `notion: incomplete`, which is a
  warning, not a pipeline failure.

## Step 4 — Final report

Run `pipeline.py status <slug>`. If `analyses/<slug>/05_executive_report.md`
exists, read its frontmatter and its `## Next Actions` section only, not
the rest of the body. Report to Ben:

- **Verdict:** `Grade <grade> / Tech <technical_confidence> · Comm
  <commercial_confidence> · <status>`, then `grade_driver`. If Executive
  didn't complete, say so instead.
- **Stages:** the status table (stage, result, attempts, time).
- **Failures and retries:** which stages failed, which recovered on
  retry, and, if the run stopped, the exact `detail:` lines and
  "Fix the cause, then `/run-analysis resume <slug>`".
- **Notion:** `Notion: <main_page_url>` from `analyses/<slug>/.notion`,
  or the catch-up warning if it's incomplete.
- **Next Actions:** the report's Next Actions bullets, verbatim.
