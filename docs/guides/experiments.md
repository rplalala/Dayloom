# Reproduce an experiment

This guide follows one request through V0–V3 generation, independent review and
evaluation. Repeat the workflow for the selected twelve-case study. To check its
published findings from saved material, use [Verify the findings](verification.md).

## Choose the reproduction route

| Goal | Use |
| --- | --- |
| Recompute historical evaluations | The original native archives and their exact producer/evaluator code; follow [saved-evidence replay](verification.md#replay-native-evidence). |
| Repeat generation and evaluation | The workflow below, with explicit inputs, policies, source revisions and provider access. |

Historical cases used their recorded code, dates and policies. A current-code rerun
is a new experiment: model output and live travel evidence can change. Preserve the
published selections and write new runs into separate directories.

## Prepare the environment

Follow [local deployment](deployment.md) for Python dependencies, providers and
vocabularies. V2/V3 additionally need the compatible TripWorld database. CLI-only
experiments do not need Node.js, Product accounts or Product migrations.

Use one source revision for a new comparison and record the runtime policy for
each version. The default CLI policy is `config/runtime.yaml`; use `-c POLICY.yaml`
to select another. Read per-case provenance before reproducing historical conditions.

From the repository root, create a separate workspace:

```bash
mkdir material
cd material
```

The following commands run there. `uv` finds the project in the parent directory;
paths in material JSON files are relative to the file that declares them.

## Generate V0–V3 outputs

Save the complete request as `input.json`, for example:

```json
{
  "input_version": "planning_request_2",
  "destination": "Sydney, Australia",
  "start_date": "2026-11-05",
  "end_date": "2026-11-06",
  "traveler_count": 2,
  "budget": {"amount": "1600", "currency": "AUD"}
}
```

For a new generation, choose dates from today through 13 days later, with at most
ten inclusive trip days. Update this example before a later run. For a study-case
repeat, retain the original request separately and identify any revised dates as
a new input revision.

For a single itinerary:

```bash
uv run rtpeval generate v3 input.json --execute
```

The command prints its fresh output directory. Omit `--execute` to prepare inputs
and policy offline. Successful execution saves `result.json`, usage, provenance
and cost reports. Online execution uses your provider accounts and can incur charges.

For an evaluable four-version case, register each run against explicit selection
slots. Save the [selection template](#selection-file) as `selection.json`, fill the
exact input SHA-256, and then run:

```bash
uv run rtpeval generate v0 input.json -o captures/v0 -g trip -r trip-v0 -b selection.json -s stages/v0 --execute
uv run rtpeval generate v1 input.json -o captures/v1 -g trip -r trip-v1 -b selection.json -s stages/v1 --execute
uv run rtpeval generate v2 input.json -o captures/v2 -g trip -r trip-v2 -b selection.json -s stages/v2 --execute
uv run rtpeval generate v3 input.json -o captures/v3 -g trip -r trip-v3 -b selection.json -s stages/v3 --execute
```

`-g` and `-r` set group/run IDs; `-b` selects the registration file; `-s` chooses a
fresh registration destination. IDs and capture paths must match the slots.
Keep the selection file unchanged between these invocations. The final staging
contains all four completed runs; failed or unstarted versions remain explicit.
Use distinct case/run identities when repeating this for additional cases.

Registration records observed workflow completion; it does not score results or
supply independently reviewed requirements. If the Planner succeeds but registration
fails, its result is retained and the command reports the two statuses separately.
For pre-existing source-bound results, `rtpeval batch collect collection.json -o stages/imported`
performs offline collection using the [producer material contract](../contracts/0002-intake-identity-usage.md#producer-material-handoff).

## Independent requirements and activity review

Have the original request authored and independently reviewed under the
[requirements handoff contract](../contracts/0002-intake-identity-usage.md#external-requirements-handoff).
The requirements author/reviewer must not use generated plans or scores as context.
Retain the real draft, final requirements, execution records and available transcripts.
The CLI attaches those records; it does not operate an author or reviewer.

Save the [handoff template](#requirements-handoff-file) as `handoff.json`, replacing
its references and hashes with the real files. Attach and finalize:

```bash
uv run rtpeval batch preflight stages/v3/staging.json
uv run rtpeval batch attach-requirements stages/v3/staging.json handoff.json -o attached
uv run rtpeval batch finalize attached/attachment.json -o finalized
uv run rtpeval batch preflight finalized/manifest.json
uv run rtpeval validate finalized/manifest.json
```

Complete any required activity-role and occupancy review before evaluation. Supply
existing reviewed envelopes at finalization with `--projection-reviews` and
`--occupancy-reviews`, or bind them in the collection declaration. Do not supply the
same type twice. Route, density and destination-time context also remain independently
reviewed when applicable. The [review readiness contract](../contracts/0002-intake-identity-usage.md#post-generation-review-readiness)
defines which decisions are required.

An accepted manifest establishes material integrity. Missing required review still
blocks fresh acquisition; a completed review may legitimately retain UNKNOWN.
Keep original sources unchanged and accessible until finalization.

## Evaluate the selected outputs

Prepare `options.json` with explicit settings:

| Field | Meaning |
| --- | --- |
| `model`, `model_endpoint` | Model/deployment identity and HTTPS Responses base URL ending in `/openai/v1/` |
| `max_google_sends` | Google acquisition ceiling |
| `max_input_tokens`, `max_output_tokens` | Complete input allowance and server output limit |
| `timeout_seconds`, `total_timeout_seconds` | Per-request and whole-run deadlines |
| `max_cost_usd` | Reference-price allowance; separate from actual billing |

Optional `reasoning_effort` selects low or medium identity reasoning; the opening
workflow uses fixed medium effort. Primary evaluation normally assesses eligible
missing hours; `assess_missing_hours=false` explicitly selects API-only execution.
Prepare a dated `rtpeval_prices_1` book in `prices.json` covering the exact operations,
field masks and model. The [evaluation design](../0006-independent-evaluation.md)
owns scoring and execution semantics; command help lists review and policy inputs.

Prepare offline, inspect `preparation.json`, and retain the printed digest:

```bash
uv run rtpeval evaluate prepare finalized/manifest.json -o evaluation -c options.json -p prices.json
```

Execute that exact preparation with your own credentials:

```bash
uv run rtpeval evaluate execute evaluation -a PREPARATION_SHA256 -e ../.env
uv run rtpeval evaluate replay evaluation
```

Alternatively, `evaluate execute` accepts the manifest with `-o`, `-c` and `-p` to
prepare and execute once. Both paths preserve source hashes, limits and one-use
execution. A started directory cannot be reused for retries; retain failed attempts
and use a fresh destination for a separately selected attempt.

Inspect `evaluation/execution/report.json`. Processing completion is distinct from
acquisition/evidence availability and numerical PASS/FAIL/UNKNOWN. Evaluation uses
independently acquired facts, not the Planner's validation findings.

### Incremental opening assessment

Normal primary evaluation includes eligible missing-hours assessment before final
scoring. For a separate historical API-only parent or an explicit follow-up, use:

```bash
uv run rtpeval evaluate prepare-opening evaluation -o opening -c opening-options.json -p opening-prices.json
uv run rtpeval evaluate execute-opening opening -a OPENING_SHA256 -e ../.env
uv run rtpeval evaluate replay-opening opening
```

Preparation is offline. Execution makes at most one medium-effort model attempt,
with `max_google_sends=0` and no retries. Its price book must cover `opening_access`.
The original parent's evidence and report remain unchanged. The
[opening contract](../contracts/0004-opening-routes.md#missing-hours-access-judgment)
owns factual versus model-supported access decisions.

## Evaluate multiple cases

After each case is finalized, declare its exact revision, manifest, options and
prices in `suite.json` using `rtpeval_suite_1`. Include an ordered list of selected
cases and a whole-suite allowance covering their reservations. The
[suite contract](../contracts/0001-evaluation-artifacts.md#source-bound-suite-lifecycle)
defines the declaration and optional saved-study attachments.

```bash
uv run rtpeval suite prepare suite.json -o suite-run
uv run rtpeval suite execute suite-run -a SUITE_SHA256 -e ../.env
uv run rtpeval suite report suite-run
uv run rtpeval suite replay suite-run
```

Execution is sequential. Stops preserve attempted and unstarted cases; the suite
does not regenerate, select better outputs, retry or resume. Save all attempted
usage separately from the selected-output resource summaries.

## Additional experiment tracks

### V3 paired diagnostics

Use `rtpeval pair acquire` for independent draft/final evidence, then `rtpeval pair report`
for same-run Repair diagnostics. `rtpeval pair access` prepares/executes/replays
paired missing-hours assessment; `evaluate prepare-pair-opening` exposes the same
native preparation directly. See [paired acquisition](../contracts/0001-evaluation-artifacts.md#paired-evidence-acquisition)
and each command's `--help` for required context and prices.

### Blinded and controlled studies

`rtpeval review` prepares anonymous questionnaires, imports actual answers and
reports judgments. Participant assessment remains a separate activity.
`rtpeval controlled` executes a frozen post-primary V3 chain offline and reports
controlled outcomes. It is distinct from ordinary saved-evidence replay. Their
[contracts](../0006-independent-evaluation.md#research-track-relationships)
own populations and interpretation.

### Retrieval corpus coverage

Use `rtpeval research corpus` for pinned corpus preparation, explicit measurement
and offline export. Measurement can acquire fresh place evidence and is not part
of basic result verification. Follow [corpus coverage](../contracts/0001-evaluation-artifacts.md#pinned-corpus-measurement-producer).

### Development checks

`rtpeval dev` lists engineering smoke and diagnostic commands. Identity smoke and
V0 route-request preparation are development tools; they do not reproduce the
formal twelve-case study. Their help states which operations contact providers.

## Selection file

This template declares pending capture slots. Fill the exact hash of the saved
`input.json` (PowerShell: `(Get-FileHash input.json).Hash.ToLower()`; Bash:
`sha256sum input.json`). Example dates and IDs below are configuration values,
not records of an executed experiment.

```json
{
  "schema_version": "rtpeval_collection_1",
  "batch_id": "trip-batch",
  "revision": "1",
  "created_at": "2026-11-01T00:00:00Z",
  "qualification_policy_ref": "selected_workflow_1",
  "groups": [{
    "group_id": "trip",
    "input_ref": {
      "path": "input.json", "sha256": "EXACT_INPUT_SHA256",
      "media_type": "application/json", "availability": "available"
    },
    "selected_runs": {
      "v0": {"run_id": "trip-v0", "capture_directory": "captures/v0"},
      "v1": {"run_id": "trip-v1", "capture_directory": "captures/v1"},
      "v2": {"run_id": "trip-v2", "capture_directory": "captures/v2"},
      "v3": {"run_id": "trip-v3", "capture_directory": "captures/v3"}
    }
  }]
}
```

## Requirements handoff file

References resolve relative to `handoff.json` and bind exact original bytes. The
execution records must retain actual actor, configuration, timestamps and lineage;
a label saying reviewed is insufficient.

```json
{
  "schema_version": "rtpeval_requirement_handoff_1",
  "batch_id": "trip-batch",
  "groups": [
    {
      "group_id": "trip",
      "input_ref": {
        "path": "input.json",
        "sha256": "EXACT_INPUT_SHA256",
        "media_type": "application/json",
        "availability": "available"
      },
      "authored_requirement_spec_ref": {
        "path": "author-draft.json",
        "sha256": "EXACT_DRAFT_SHA256",
        "schema_version": "rtpeval_requirements_1",
        "media_type": "application/json",
        "availability": "available"
      },
      "requirement_spec_ref": {
        "path": "reviewed-final.json",
        "sha256": "EXACT_FINAL_SHA256",
        "schema_version": "rtpeval_requirements_1",
        "media_type": "application/json",
        "availability": "available"
      },
      "authoring_ref": {
        "path": "author-execution.json",
        "sha256": "EXACT_AUTHOR_EXECUTION_SHA256",
        "schema_version": "rtpeval_requirement_agent_execution_1",
        "media_type": "application/json",
        "availability": "available"
      },
      "review_ref": {
        "path": "review-execution.json",
        "sha256": "EXACT_REVIEW_EXECUTION_SHA256",
        "schema_version": "rtpeval_requirement_agent_execution_1",
        "media_type": "application/json",
        "availability": "available"
      }
    }
  ]
}
```
