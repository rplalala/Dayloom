# RTPEval

Independent evaluation and research tools for Dayloom's V0–V3 planners.

- [Reproduce an experiment](../../docs/guides/experiments.md): generate outputs,
  obtain independent review, evaluate and retain a new experiment.
- [Verify the findings](../../docs/guides/verification.md): check the saved twelve-case
  scores, resources and blinded assessments, or replay retained native evidence.
- [Deploy Dayloom](../../docs/guides/deployment.md): prepare providers, data and runtime resources.

## Quick start

From the repository root:

```bash
uv sync --locked --group retrieval
uv run rtpeval verify
```

Verification needs no database or provider keys. To prepare an evaluation of an
already qualified four-version manifest, without sending provider requests:

```bash
uv run rtpeval evaluate prepare manifest.json -o evaluation -c options.json -p prices.json
```

Continue with the [evaluation workflow](../../docs/guides/experiments.md#evaluate-the-selected-outputs)
for reviewed inputs, execution limits and replay.

## Command map

| Task | Command group |
| --- | --- |
| Prepare or run a planner | `generate v0`, `generate v1`, `generate v2`, `generate v3` |
| Collect and qualify selected material | `batch`, `validate` |
| Prepare, execute or replay automatic evaluation | `evaluate` |
| Missing-hours assessment | `evaluate prepare-opening`, `execute-opening`, `replay-opening` |
| Multi-case execution | `suite` |
| Resources and saved study reports | `usage`, `cost`, `quality`, `research` |
| Additional studies | `pair`, `review`, `mechanism`, `controlled` |
| Individual evidence tools and engineering diagnostics | `advanced`, `dev` |

Every group and operation accepts `--help`. Common short flags are `-o` for output,
`-c` for options, `-p` for prices, `-e` for credentials and `-a` for a prepared digest,
where shown in help. Existing long flags remain supported.

## Evidence and execution

Preparation and replay are offline. Online execution uses explicit credentials
and limits; generation requires `--execute`. Each execution directory is one-use,
including a stopped attempt. Selected research outputs are never replaced automatically.

Exit 0 means processing completed; reports can still contain FAIL, UNKNOWN or
unavailable evidence. Material corrections and stopped execution normally return 2;
planner failures retain their native status. Model-supported access judgments and
participant assessments remain distinct from verified provider facts.

## Code and contracts

`backend/cli/` exposes installed commands; this package implements native evaluation
and replay. `research/` contains source-bound study reports and `tools/` contains
development captures. The [evaluation design](../../docs/0006-independent-evaluation.md)
locates the five detailed artifact, intake, schedule, opening/route and quality/review
contracts. Guides own runnable workflows; contracts own schemas and scoring policy.
