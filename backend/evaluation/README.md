# RTPEval

Independent evaluation and research tools for Dayloom's V0–V3 planners. RTPEval
keeps material qualification, factual evidence, scores, resource accounting and
study interpretation separate.

- [Reproduce an experiment](../../docs/guides/experiments.md): generate, review,
  evaluate and retain a new source-bound experiment.
- [Verify the findings](../../docs/guides/verification.md): check the saved twelve-case
  results, trace conclusions and replay native evidence.
- [Run Dayloom locally](../../docs/guides/deployment.md): install providers, data and
  runtime resources.

## Start here

Install from the repository root:

```bash
uv sync --locked --group retrieval
uv run rtpeval --help
```

Check the published study without provider keys or a database:

```bash
uv run rtpeval verify
```

For an already qualified four-version manifest, prepare an evaluation offline:

```bash
uv run rtpeval evaluate prepare manifest.json -o evaluation -c options.json -p prices.json
```

The [experiment guide](../../docs/guides/experiments.md#evaluate-the-selected-outputs)
explains reviewed inputs, limits, execution and replay. Every group and leaf accepts
`--help`; use the installed commands below rather than invoking Python modules.

## Commands

| Command | Use |
| --- | --- |
| `verify` | Check all twelve published cases offline |
| `generate VERSION REQUEST` | Prepare one planner; add `--execute` to generate online |
| `batch collect / attach-requirements / finalize / preflight` | Collect exact selected material, attach independent review and qualify it |
| `validate` | Validate a native manifest and its source bindings offline |
| `evaluate prepare / execute / replay` | Prepare, acquire independent evidence and replay automatic evaluation |
| `evaluate prepare-opening / execute-opening / replay-opening` | Separate parent-bound missing-hours assessment |
| `evaluate prepare-pair-opening` | Prepare the V3-only paired access packet |
| `suite prepare / execute / report / replay` | Operate an explicitly declared multi-case suite |
| `quality`, `usage`, `cost` | Inspect saved scores and descriptive resource/cost evidence |
| `pair` | Prepare, acquire and report independent V3 draft/final evidence |
| `review` | Package blinded questionnaires and import/report actual answers |
| `mechanism` | Report retained mechanism captures |
| `controlled` | Execute and evaluate frozen post-primary V3 cases offline |
| `research` | Validate/export declared populations and build saved-material reports |
| `advanced` | Individual identity, snapshot, schedule, opening and route tools |
| `dev` | Engineering smoke and diagnostics with explicit execution boundaries |

Common short flags are `-o` for fresh output, `-c` for evaluation/runtime options,
`-p` for prices, `-e` for a credentials file and `-a` for a prepared digest, where
shown in the command's help. Original long flags and advanced opening-run aliases
remain compatible.

## Evidence and execution

Preparation and saved-evidence replay are offline. Online `execute` commands use
explicit credentials and limits; generation additionally requires `--execute`.
Execution directories are one-use, including stopped attempts. No command retries
or replaces a selected research output automatically.

An exit code of 0 means that command's processing completed. It can coexist with
FAIL, UNKNOWN or unavailable evidence. Material correction and stopped execution
normally return 2; Planner failures retain their native status. Model-supported
access and participant judgments remain distinct from verified provider facts.

## Contracts and code

[Evaluation design](../../docs/0006-independent-evaluation.md) locates the five
current contracts for artifacts, intake/usage, requirements/schedule,
opening/routes and quality/human/paired review. They own detailed schemas and
scoring policy; the guides own runnable workflows.

`backend/cli/` contains installed adapters outside preparation-bound evaluator
files. This package contains the native implementations and replay readers;
`backend/evaluation/research/` owns source-bound research reports, and
`backend/evaluation/tools/` holds development captures.
