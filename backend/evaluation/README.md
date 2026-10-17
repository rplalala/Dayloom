# Independent evaluation package

Tickets 01-12 have offline implementations for explicitly submitted immutable material.
Ordinary scoring and Ticket 12 reporting consume saved outputs; the isolated
Ticket 11 command executes only frozen V3 post-primary cases. No formal corpus or
comparative research is constructed by these commands.
[Evaluation architecture](../../docs/0006-independent-evaluation.md) owns scope.
Ticket 11's [controlled replay contract](../../docs/contracts/0001-evaluation-artifacts.md#controlled-repair)
defines execution inputs, independent conditions and human supplementation.
Ticket 12's [contract](../../docs/contracts/0001-evaluation-artifacts.md#mechanism)
defines selected-source mechanism readers and explicit opt-in capture, disabled by default.
The [approved scope](../../docs/contracts/0001-evaluation-artifacts.md#ticket12-implementation-scope)
defines the local wrapper, mechanism CLI and offline acceptance boundaries.

## Installed batch validation

From the repository root, `uv sync` installs the editable project and its `rtpeval`
console command. Use `uv run rtpeval` or activate the existing `.venv` first:

```powershell
uv run rtpeval --help
uv run rtpeval validate --help
uv run rtpeval validate path/to/manifest.json
```

Validation delegates to the existing `python -m backend.evaluation MANIFEST` intake
command, preserving its JSON, material/projection diagnostics and exit codes. It reads
the manifest and referenced originals without modifying them, loading credentials,
constructing Planner/provider runtimes or sending requests. Exit 0 indicates accepted
material; exit 2 indicates material correction or argument errors. Acceptance does
not score quality or certify the producer's benchmark selection.

The installed interface also exposes [automatic evaluation](#installed-automatic-evaluation),
[multi-case suites](#installed-multi-case-suite),
[selected generation and material handoff](#installed-generation-and-material-handoff), and
[task-oriented tools](#installed-task-oriented-tools). Module interfaces below remain
available with their documented execution policies. The thin dispatcher lives in `backend/cli/`,
outside the evaluator implementation files bound by prepared execution hashes.

## Installed automatic evaluation

The primary route accepts an existing qualified four-final manifest and prepares and
executes its native evaluation in one invocation:

```powershell
uv run rtpeval evaluate execute manifest.json --directory artifacts/fresh-evaluation --options options.json --prices prices.json --env-file .env
uv run rtpeval evaluate replay artifacts/fresh-evaluation
```

Optional `--context`, `--occupancy-reviews`, `--route-reviews` and `--density-reviews`
forward applicable reviewed material unchanged. Local input, dependency, policy and
price validation completes before provider dispatch. Credentials are loaded only for
explicit execution; `--env-file` is optional when the required keys are already set.
The options, prices and credential names are documented under
[fresh automatic evaluation](#fresh-automatic-evaluation-cli).

Stdout contains the native final report, including automatic quality, with no separate
`quality` command needed. Preparation, source/implementation hashes, journals and receipts
remain native. The internal preparation digest proves integrity and does not establish
independent authorization. Exit 0 means processing completed and may coexist with quality
FAIL, UNKNOWN or unavailable values; exit 2 means invalid arguments, material correction
or a stopped attempt. Processing, acquisition and evidence statuses remain separate.

Optional offline preparation and explicit legacy execution remain available:

```powershell
uv run rtpeval evaluate prepare manifest.json --directory artifacts/fresh-evaluation --options options.json --prices prices.json
uv run rtpeval evaluate execute artifacts/fresh-evaluation --approved-sha256 EXACT_PREPARATION_SHA256 --env-file .env
uv run rtpeval evaluate replay artifacts/fresh-evaluation
```

`--directory` selects the one-step manifest route and requires `--options` and `--prices`.
`--approved-sha256` selects the prepared-directory route and rejects preparation flags;
the two selectors cannot be combined. Both routes preserve native budgets and one-use
rules. Preparation needs a fresh directory; a started execution consumes its package
even when stopped. A credential refusal before starting preserves the prepared package;
an operator may explicitly select the legacy route after correcting credentials. The CLI
does not automatically recover it or repeat an attempt. Eligible missing-hours access
assessment is included before final scoring under the prepared allowance. No retry,
resume or extra Google probe is added. Repository authorization and live execution
rules still apply; historical API-only and incremental interfaces remain available.

## Installed multi-case suite

A suite composes explicitly selected accepted case revisions. Each case owns one
request group and exactly four selected V0-V3 runs. Prepare material with the existing
collection/review/finalization flow first; a suite does not generate or qualify it.
There is no automatic source scan, best-run selection or fixed case count.

Create a declaration beside its selected source directories. All input paths are
relative to this declaration's directory and must remain inside it:

```json
{
  "schema_version": "rtpeval_suite_1",
  "suite_id": "selected-development-cases",
  "max_cost_usd": "4.00",
  "cases": [
    {"case_id": "case-a", "revision": "1", "manifest": "a/manifest.json",
     "options": "a/options.json", "prices": "oracle-prices.json"},
    {"case_id": "case-b", "revision": "1", "manifest": "b/manifest.json",
     "options": "b/options.json", "prices": "oracle-prices.json"}
  ]
}
```

Use the actual native manifest revision and globally distinct run IDs. Optional case
`context`, `occupancy_reviews`, `route_reviews` and `density_reviews` paths forward
existing reviewed material. Each native options file explicitly bounds acquisition;
the sum of its `max_cost_usd` reservations must fit the whole-suite allowance.
The illustrative allowance above is not live authorization or an account invoice.
Native credential names and request/token/time limits remain those of
[fresh automatic evaluation](#fresh-automatic-evaluation-cli).

```powershell
uv run rtpeval suite --help
uv run rtpeval suite prepare suite.json --directory artifacts/fresh-suite
# Only with authorization for this exact prepared acquisition:
uv run rtpeval suite execute artifacts/fresh-suite --approved-sha256 EXACT_PREPARATION_SHA256 --env-file .env
uv run rtpeval suite report artifacts/fresh-suite
uv run rtpeval suite replay artifacts/fresh-suite
```

Preparation is offline and prints the exact `preparation_sha256` required by execution.
It checks all selected sources and supplied optional material before sends. Execution
is sequential and consumes the prepared package once; stop/error retains attempted
work and leaves subsequent cases `unstarted`. To run an explicitly selected subset
later, declare it again into a fresh directory. The CLI never retries or resumes.

Inspect `preparation.json`, `summary.json`, `receipt.json`, native
`cases/0001/primary/` packages and frozen `tracks/` reports. The summary retains
ordered case rows and independent per-track processing, evidence and applicability.
Complete processing may contain FAIL/UNKNOWN or unavailable optional data. A stopped
case cannot be inferred complete from descriptive reports. Cooperative cancellation
saves attempted/stopped/unstarted status; an invalid frozen track has a separate
material-correction diagnostic and cannot establish successful replay. Exit 0 means successful
preparation or completed processing; invalid material, stopped work and incomplete
full replay exit 2. Replay needs no credentials and makes no provider calls.

Default generation resources and saved mechanism reports are available for every
selected case, including stopped/unstarted primary work. Optional case configuration
uses explicit local paths:

```json
{
  "tracks": {
    "resources": {"prices": "generation-prices.json", "bills": "saved-bills.json",
                  "annotations": "usage-annotations.json"},
    "mechanism": {"observations": "linked-observations.json"}
  }
}
```

These are optional case fields, not a second suite declaration. Omit unavailable
inputs; supplied ones must be valid. Generation prices are distinct from the required
primary evaluator `prices`. Without generation prices, cost stays unavailable with a
reason. The mechanism observations envelope has `records` containing native source-
linked observations. Inspect `tracks/NNNN/resources.json`, `cost.json`,
`mechanism_preparation.json` and `mechanism.json`; the [resource contract](../../docs/contracts/0002-intake-identity-usage.md#suite-selection-and-generation-resources)
and [mechanism contract](../../docs/contracts/0001-evaluation-artifacts.md#mechanism)
own missingness and native arithmetic.

For optional same-run V3 pairing, add case `tracks.pair` with existing `identity`
and `snapshot` paths. Independently prepare draft/final evidence through the
[V3 paired diagnostics](#v3-paired-diagnostics) workflow first. Optional pair fields
are `context`, `occupancy_reviews`, `route_reviews`, `coordinates`, `expected_plan`,
`identity_snapshot`, `edit_provenance`, `correspondence_reviews` and `density_reviews`.
All refer to existing declaration-relative material; nonempty supplied pair material
requires `identity` for native source-lineage checks. A final-only snapshot cannot
establish draft coverage; omit pairing when not requested, or declare `{}` to retain
requested/unavailable status. A valid unchanged no-Repair pair can have zero signed
deltas. Inspect `tracks/NNNN/pair.json` and its separate summary mask/status; the suite
adds no paired acquisition, opening assessment or Repair call.

Existing human and controlled studies attach through suite-level `tracks.human`
and `tracks.controlled_repair` arrays. First generate native saved reports with the
[human import/report](#local-blinded-ranking) or [controlled batch](#controlled-v3-offline-workflow)
commands. A human attachment declares `report`, `presentation`, `mapping`, `answers`
and a `source_context` containing one selected case ID, the package's rater and private
preparation source hashes. A controlled attachment declares `report`, `manifest` and
its own population/case/goal/preparation/expectations context. Every reference retains
its exact original byte hash and native schema. The
[attachment wire](../../docs/contracts/0001-evaluation-artifacts.md#existing-study-attachments-and-refresh)
owns the full field requirements; these are saved report dependencies, not study execution
inputs to the suite.

After importing later answers separately, declare an `rtpeval_suite_attachments_1`
file with the same `suite_id` and replacement `tracks` lists:

```powershell
uv run rtpeval suite report artifacts/fresh-suite --attachments attachments.json
uv run rtpeval suite replay artifacts/fresh-suite
```

Omitted track keys inherit earlier attachments. Supplied invalid/foreign/stale material
is rejected before a new revision, while earlier closed output remains intact. Refresh
checks saved primary integrity without primary rescoring and calls only native offline
study report builders. Raters, effective answer revisions and controlled denominators
remain separate; valid missing study results cannot lower or raise primary scores.

`report` appends a separately receipted `reports/0001/summary.json` revision and keeps
earlier execution evidence intact. The [suite artifact contract](../../docs/contracts/0001-evaluation-artifacts.md#source-bound-suite-lifecycle)
owns wire integrity and replay; native individual commands below remain available.

### Optional research attachments and offline refresh

A research population starts from original requests, independently of the suite's
accepted four-final cases. Prepare its population, selection profile, attempt
census and exact saved track material with the [offline research flow](#installed-offline-research)
first. Failed, cancelled, unstarted and unknown generation slots remain in that
population; the suite's qualified case list does not replace it.

Add a suite-level `tracks.research` object to the initial suite declaration or a
later `rtpeval_suite_attachments_1` declaration. Every path is relative to that
outer declaration; the research declaration's own references remain relative to
its directory. Keep both declarations and all dependencies within the outer root.
The [research attachment wire](../../docs/contracts/0001-evaluation-artifacts.md#optional-research-attachment-wire)
owns exact field and integrity requirements. Replace the illustrative hash below
with the SHA-256 of the exact saved bytes:

```json
{
  "schema_version": "rtpeval_suite_attachments_1",
  "suite_id": "selected-development-cases",
  "tracks": {
    "research": {
      "schema_version": "rtpeval_suite_research_1",
      "declaration_ref": {
        "path": "research/research.json",
        "sha256": "EXACT_RESEARCH_DECLARATION_SHA256",
        "schema_version": "rtpeval_research_declaration_1",
        "media_type": "application/json",
        "availability": "available"
      },
      "selected_tracks": ["population", "opportunities", "relevance", "repair", "tradeoffs"]
    }
  }
}
```

Select any nonempty list of distinct registered tracks explicitly. Omitted
research leaves the default suite unchanged; omitted track selections are
`not_requested`. Missing valid optional reviews, captures, native reports or
usage retain unavailable/partial measurements. Supplied malformed, foreign or
stale material is a track-specific material correction, even when native quality
material is valid.

```powershell
uv run rtpeval suite report artifacts/fresh-suite --attachments attachments.json
uv run rtpeval suite replay artifacts/fresh-suite
```

The report operation appends a new receipted revision. Inspect the research index
linked by `summary.json` under `tracks.research`; it binds the population/profile,
attempt census, selected reports and their exact source and semantic hashes.
Initial attachments write `tracks/research/index.json`,
`tracks/research/reports/<track>.json` and `.md`, with frozen dependencies under
`tracks/research/sources/`. Later attachments write corresponding reports under
`reports/NNNN/`, bind the previous summary hash, and freeze dependencies under
that revision's `sources/`. Earlier primary reports, receipts and summaries remain
intact. Omitted refresh keys inherit the previous attachments; a supplied
research object replaces its previous selection.

Processing completion is separate from measurement completeness. Planned slots,
qualified four-final groups, same-run V3 pairs and controlled targets retain their
own units and denominators. Source-compatible RAG and Repair benefit links use
exact selected-attempt bindings to resource evidence; missing benefits or usage
remain visible. Retries are separate consumption, a V3 draft is not an independent
V2 run, and frozen controlled simulation is excluded from live generation
resources. No combined score, ranking or causal conclusion is produced.

Successful replay preserves unavailable/partial measurements; it does not certify
complete measurement or successful generation. Replay requires no credentials or
network. It verifies the immutable inventories,
lineage and deterministically rebuilt research content. Initial suite sources
retain the native source-drift check against their original root; later attachment
revisions rebuild from their frozen dependency copies. Keep original initial
sources available and unchanged. Changed, escaped, missing or corrupt material
cannot establish successful complete research evidence. Reporting and replay do
not generate plans, acquire independent evidence, invoke reviewers or execute
controlled Repair.

## Installed generation and material handoff

`rtpeval generate` forwards the native [selected-version usage capture](#planner-usage-capture-cli)
arguments. Without `--execute` it prepares offline; with `--execute` it invokes exactly
one selected Planner. It retains the native runtime, date admission, usage/evidence options
and failure artifacts. V1/V2 also accept explicit `--opportunity-capture PATH` through
the [selected-generation capture contract](../../docs/contracts/0002-intake-identity-usage.md#selected-generation-opportunity-capture).
Registration is optional and requires both `--register-batch CONFIG`
and `--registration-directory FRESH`, together with `--execute`.

The original complete request, configuration and selected captures must remain under the
configuration's reference root. Every referenced path is relative to that JSON file; path
escape is refused. The following `selection.json` template declares explicit pending slots;
replace the input hash with the exact SHA-256 of saved bytes before using it:

```json
{
  "schema_version": "rtpeval_collection_1",
  "batch_id": "case-1-batch",
  "revision": "1",
  "created_at": "2026-10-09T00:00:00Z",
  "qualification_policy_ref": "selected_workflow_1",
  "groups": [{
    "group_id": "case-1",
    "input_ref": {
      "path": "input.json", "sha256": "EXACT_INPUT_SHA256",
      "media_type": "application/json", "availability": "available"
    },
    "selected_runs": {
      "v0": {"run_id": "case-1-v0", "capture_directory": "captures/v0"},
      "v1": {"run_id": "case-1-v1", "capture_directory": "captures/v1"},
      "v2": {"run_id": "case-1-v2", "capture_directory": "captures/v2"},
      "v3": {"run_id": "case-1-v3", "capture_directory": "captures/v3"}
    }
  }]
}
```

`created_at` and run identities above are template values, not evidence of an execution.
A pending slot has no result/usage/provenance/completion declaration. The selected
version, group, run and output directory must match its slot. Do not edit the selected
configuration between invocations: each recorded capture binds its original bytes.

```powershell
uv run rtpeval generate --version v0 --input-json material/input.json --output-directory material/captures/v0 --group-id case-1 --run-id case-1-v0 --execute --register-batch material/selection.json --registration-directory artifacts/staging-v0
uv run rtpeval generate --version v1 --input-json material/input.json --runtime-config config/runtime.yaml --output-directory material/captures/v1 --group-id case-1 --run-id case-1-v1 --execute --register-batch material/selection.json --registration-directory artifacts/staging-v1
uv run rtpeval generate --version v2 --input-json material/input.json --runtime-config config/runtime.yaml --rag-env-file .env.tripworld --output-directory material/captures/v2 --group-id case-1 --run-id case-1-v2 --execute --register-batch material/selection.json --registration-directory artifacts/staging-v2
uv run rtpeval generate --version v3 --input-json material/input.json --runtime-config config/runtime.yaml --rag-env-file .env.tripworld --output-directory material/captures/v3 --group-id case-1 --run-id case-1-v3 --execute --register-batch material/selection.json --registration-directory artifacts/staging-v3
```

These are four individually selected invocations, each needing its own applicable live
scope. There is no automatic four-version runner. Earlier captures are retained in later
registration; unstarted slots stay blocked. The CLI saves immutable
`generation-selection-UUID.json` and `generation-collection-UUID.json` beside CONFIG,
plus `operator-selection.json`, `producer-completion.json` and
`generation-registration.json` in the capture. Registration copies exact source bytes
and binds actual observations under `selected_workflow_1`. Keep all original files and
selection snapshots available until finalization. `--capture-evidence` remains explicit;
Planner evidence is not independent evaluator evidence.

Before dispatch, registration checks the explicit selection, selected input hash,
capture directory, replacement restrictions and fresh registration destination.
Invalid initial setup exits 2 with `planner.status=not_invoked` and registration
diagnostics, without creating a capture or loading credentials/constructing a runtime.
Execution-time source drift and destination conflicts remain checked after dispatch.
The [registration contract](../../docs/contracts/0002-intake-identity-usage.md#producer-material-handoff)
owns these boundaries.

The final stdout object and registration artifact separate `planner.status/exit_code`
from `registration.status/directory/blocking_reasons`. Planner failure retains exit 1;
successful Planner with registration failure exits 2 and preserves its result. Successful
collection may exit 0 with `incomplete`, `blocked` or `pending_review`. None is an accepted
manifest. Generation and registration require no RequirementSpec.

### Explicit existing-material collection

For preserved runs, use the same `rtpeval_collection_1` batch/group/input fields and
explicitly select all four run IDs. Replace each pending slot with a source-bound entry
as below; repeat for the selected V1, V2 and V3 artifacts with their actual IDs, hashes
and completion declarations. This is a run-entry template, not a complete batch:

```json
{
  "run_id": "case-1-v0",
  "result_ref": {
    "path": "existing/v0/result.json", "sha256": "EXACT_RESULT_SHA256",
    "media_type": "application/json", "availability": "available"
  },
  "usage_ref": {
    "path": "existing/v0/usage.json", "sha256": "EXACT_USAGE_SHA256",
    "schema_version": "rtpeval_usage_1",
    "media_type": "application/json", "availability": "available"
  },
  "provenance_ref": {
    "path": "existing/v0/provenance.json", "sha256": "EXACT_PROVENANCE_SHA256",
    "schema_version": "rtpeval_provenance_1",
    "media_type": "application/json", "availability": "available"
  },
  "completion": {
    "declared_by": "ACTUAL_PRODUCER", "declared_at": "ACTUAL_OFFSET_AWARE_TIME",
    "policy_ref": "ACTUAL_PRODUCER_POLICY", "workflow_status": "completed",
    "required_mechanisms": {"generation": "completed"}
  }
}
```

The batch's `qualification_policy_ref` must match the actual completion policy; existing
material does not acquire `selected_workflow_1` merely by copying that string. V2/V3 also
require completed retrieval, and V3 completed validation and completed/not-applicable
Repair. The producer declares these from retained workflow evidence. File existence,
exit 0, internal PASS, `policy_completion` or Repair `ACCEPTED_COMPLETE` alone is insufficient.
Missing provenance requires an explicit source-bound `producer_declaration` with actual
`declared_by`, `declared_at` and rationale, instead of `provenance_ref`; it is never guessed
from names. Explicit `rtpeval_usage_1` unavailable usage is supported and remains missing,
not zero. Failed new usage capture remains failure. See the
[producer contract](../../docs/contracts/0002-intake-identity-usage.md#producer-material-handoff).

```powershell
uv run rtpeval batch collect material/collection.json --directory artifacts/staging
```

Missing versions/material produce `incomplete` or blockers. All four qualified runs
produce `pending_review`; collection always sets `qualified_four_version_batch=false`
and `pending_requirement_review=true`. It does not scan, select another run, regenerate,
author requirements or construct a provider runtime.

Qualified selected results also emit `semantic-readiness.json` beside staging,
including when registration follows generation. This is a source-bound activity
review queue, separate from producer completion and requirements review. Recompute
it offline at any time:

```powershell
uv run rtpeval batch preflight artifacts/staging/staging.json
```

The command also accepts a finalized native manifest. Exit 2 with
`status=needs_semantic_review` identifies missing work; invalid material has a
separate correction status. Role and occupancy are separate decisions. Complete
review may still leave genuine UNKNOWN and unavailable scores. The
[readiness contract](../../docs/contracts/0002-intake-identity-usage.md#post-generation-review-readiness)
owns states, source/provenance requirements and compatibility.

### External requirements review and finalization

Operate the author and reviewer separately using **Codex `gpt-6.1-sol`, reasoning effort
`high`**. The author uses the complete original request, distinguishes hard obligations,
soft preferences and unresolved meaning, and produces native `rtpeval_requirements_1`.
A distinct reviewer reads that exact draft against the same request and produces the
final reviewed spec. Do not provide Planner interpretation, generated results, scores or
mechanisms as requirements-review context. This configuration does not change Planner or
evaluator reasoning options. Agent review is not human review.

Retain the actual author draft, reviewer final, execution records, transcript exports
and any referenced sidecars. A handoff template uses standard exact-byte JSON references
for every `*_ref` below; they resolve relative to `handoff.json`:

```json
{
  "schema_version": "rtpeval_requirement_handoff_1",
  "batch_id": "case-1-batch",
  "groups": [{
    "group_id": "case-1",
    "input_ref": {"path": "input.json", "sha256": "EXACT_INPUT_SHA256", "media_type": "application/json", "availability": "available"},
    "authored_requirement_spec_ref": {"path": "author-draft.json", "sha256": "EXACT_DRAFT_SHA256", "schema_version": "rtpeval_requirements_1", "media_type": "application/json", "availability": "available"},
    "requirement_spec_ref": {"path": "reviewed-final.json", "sha256": "EXACT_FINAL_SHA256", "schema_version": "rtpeval_requirements_1", "media_type": "application/json", "availability": "available"},
    "authoring_ref": {"path": "author-execution.json", "sha256": "EXACT_AUTHOR_EXECUTION_SHA256", "schema_version": "rtpeval_requirement_agent_execution_1", "media_type": "application/json", "availability": "available"},
    "review_ref": {"path": "review-execution.json", "sha256": "EXACT_REVIEW_EXECUTION_SHA256", "schema_version": "rtpeval_requirement_agent_execution_1", "media_type": "application/json", "availability": "available"}
  }]
}
```

Execution and transcript requirements, reviewer input/output links and timestamp rules
belong to the [external handoff contract](../../docs/contracts/0002-intake-identity-usage.md#external-requirements-handoff).
Capture actual identities/configuration/times and transcript messages; do not invent an
execution record to satisfy validation. A label `reviewed` establishes no review by itself.
The CLI validates recorded source/hash lineage and compatible configuration, but cannot
authenticate an external session or establish semantic completeness/independent review
quality. These remain operator responsibilities. The CLI performs no agent launch,
message, authoring, review or model request.

For existing collection use `artifacts/staging/staging.json`; for the generation example
use `artifacts/staging-v3/staging.json` after all four required workflows qualified:

```powershell
uv run rtpeval batch attach-requirements artifacts/staging/staging.json material/handoff.json --directory artifacts/attached
uv run rtpeval batch finalize artifacts/attached/attachment.json --directory artifacts/finalized --projection-reviews material/role-reviews.json --occupancy-reviews material/occupancy-reviews.json
uv run rtpeval batch preflight artifacts/finalized/manifest.json
uv run rtpeval validate artifacts/finalized/manifest.json
uv run rtpeval evaluate execute artifacts/finalized/manifest.json --directory artifacts/fresh-evaluation --options options.json --prices prices.json --env-file .env
uv run rtpeval evaluate replay artifacts/fresh-evaluation
```

Attachment emits `attached_pending_finalization`, not intake acceptance. Finalization
requires all four selected versions, completion declarations, required envelopes and
reviewed requirements. It verifies original/copy drift, copies all source and handoff
artifacts with unchanged bytes/layout, then publishes `manifest.json` only if native
intake accepts. Keep original input/config/capture/handoff files accessible and unchanged
until that gate; a changed request needs fresh authoring/review, not edited hashes. All
staging, attachment, finalization and evaluation destinations must be fresh. A failed
final destination is retained for diagnosis and is not accepted or reusable for recovery.

The two review arguments supply existing native envelopes, not review instructions;
omit a type when no decisions of that type are needed. Alternatively, collection can
retain `projection_reviews_ref` and `occupancy_reviews_ref` from its configuration.
Do not supply the same type again at finalization. Attach reviews linking protected
obligations at finalization, where reviewed requirements are available. Both paths
preserve exact review bytes and original result hashes without manual manifest edits.

Finalization reports structural `accepted` separately from its nested
`semantic_readiness`; an accepted manifest can still require review work. A missing
role decision appears before any dependent occupancy decision can be requested.
Reviewing a generic activity as non-primary alone does not establish whether its
window is committed. An empty source-only envelope cannot cover new activities.
Preparation, including one-step `evaluate execute`, stops missing required work
before provider sends. Bound occupancy reviews enter preparation automatically;
an explicit conflicting occupancy file is rejected. All preparation destinations
remain fresh, and completing reviews makes no guarantee of numerical scores.

The CLI does not call Codex or another reviewer. Independently operated output review
uses the original request and exact submitted activity context without scores or
desired outcomes; retain actual actor/settings/time and rationale, and disclose
unobservable external usage/billing. Requirement authoring above remains source-only.
Synthetic test decisions are not actual reviews. Existing accepted data, reports,
receipts and historical replay bindings stay immutable; later real reviews and a
revised evaluation need their own authorization and fresh package.

## Installed offline research

`rtpeval research` reads an explicitly declared original-input population and saved
material. It preserves planned case/version/repetition slots when generation is
failed, cancelled, incomplete, unstarted or unknown. Original input registration
does not require a completed four-version result bundle. Native four-final intake
continues to own final-quality eligibility.

Prepare material in this order:

1. Preserve the complete original requests and stable case revisions. Declare
   planned versions and repetition IDs in the population inventory.
2. Save a versioned selection profile with exact configuration references,
   first-dispatched primary selection, explicit retry/completion rules and its
   prospective, retrospective or unverified timing basis.
3. Export or supply an optional attempt census bound to that population and profile.
   Preserve every linked attempt, exact source hashes, dispatch timestamps, completion declarations,
   available result/usage/provenance and execution metadata. Missing census rows
   remain unknown; explicit producer evidence establishes an unstarted slot.
4. Declare applicable optional track material by exact references. Independent
   review and evidence preparation remain separate operator activities.

The [population and attempt contract](../../docs/contracts/0001-evaluation-artifacts.md#original-input-research-declarations-and-attempt-census)
owns detailed fields. References resolve relative to the research declaration;
all material must remain within its root and pass exact byte-hash validation.
The declaration uses `rtpeval_research_declaration_1`, `population_ref`,
`profile_ref`, optional `census_ref` and `track_refs`.

```powershell
uv run rtpeval research --help
uv run rtpeval research validate material/research.json --track population
uv run rtpeval research report material/research.json --track population --directory artifacts/fresh-population-report
```

### Exporting an attempt census

Use an explicit source inventory with `rtpeval_research_census_export_1`, exact
population/profile refs and ordered `attempt_sources`. Each entry identifies a
case revision, declared version/repetition, attempt/run/group, contiguous slot-local
order, immediate predecessor, reason and `producer_metadata_ref`. Supply available
completion/result/usage/provenance refs; the exporter does not choose or discover runs.
The [export wire](../../docs/contracts/0001-evaluation-artifacts.md#installed-census-export-and-dispatch-observations)
owns metadata fields, source-root rules and unavailable-material handling.

For example, a primary and its retry can be selected explicitly:

```json
{
  "schema_version": "rtpeval_research_census_export_1",
  "population_ref": {"path": "population.json", "sha256": "<exact digest>", "media_type": "application/json", "availability": "available", "schema_version": "rtpeval_research_population_1"},
  "profile_ref": {"path": "profile.json", "sha256": "<exact digest>", "media_type": "application/json", "availability": "available", "schema_version": "rtpeval_research_profile_1"},
  "attempt_sources": [
    {
      "case_id": "harbor-request", "case_revision": "input-7", "version": "v1",
      "repetition_id": "weekday", "attempt_id": "first", "run_id": "run-first",
      "group_id": "group-a", "order": 1, "prior_attempt_id": null,
      "reason_type": "original_dispatch",
      "producer_metadata_ref": {"path": "first/planner-dispatch.json", "sha256": "<exact digest>", "media_type": "application/json", "availability": "available", "schema_version": "rtpeval_planner_dispatch_1"}
    },
    {
      "case_id": "harbor-request", "case_revision": "input-7", "version": "v1",
      "repetition_id": "weekday", "attempt_id": "retry", "run_id": "run-retry",
      "group_id": "group-a", "order": 2, "prior_attempt_id": "first",
      "reason_type": "declared_retry",
      "producer_metadata_ref": {"path": "retry/planner-dispatch.json", "sha256": "<exact digest>", "media_type": "application/json", "availability": "available", "schema_version": "rtpeval_planner_dispatch_1"}
    }
  ]
}
```

Replace placeholder digests with exact saved-byte hashes. Add each available
`completion_ref`, `result_ref`, `usage_ref` and `provenance_ref` to its entry;
omitting completion keeps its outcome unknown even when a result exists.

```powershell
uv run rtpeval research export-census material/export-input.json --directory artifacts/fresh-census
uv run rtpeval research validate artifacts/fresh-census/material/research-export.json --track population
uv run rtpeval research report artifacts/fresh-census/material/research-export.json --track population --directory artifacts/fresh-census-report
```

Export is offline: it copies selected originals unchanged, validates the pending
bundle with existing readers and publishes only to a fresh destination. `export.json`
records exact source hashes, metadata provenance and source/slot diagnostics. Exit 2
indicates insufficient or invalid material; missing dispatch times are never invented.
The primary remains `first_dispatched`; any profile-selected retry view is separate.
The exported declaration initially has no optional track attachments.

Future `generate` captures actual Planner dispatch metadata; offline preparation
captures zero invocations, while invalid registration preflight reports zero without
creating a capture. Use the exact saved `runtime-policy.json` as the corresponding
profile configuration source. Earlier runs need an explicit `historical_import`
metadata declaration with author, observed dispatch/non-dispatch and exact evidence
refs. Preparation time, file timestamps and result existence cannot establish that
observation. Export neither launches runs nor constructs missing non-dispatch rows.

### Measuring and exporting pinned corpus coverage

This optional research workflow is not a prerequisite for ordinary V2 generation
or case acceptance. The [benchmark workflow](../../benchmark/README.md#workflow-and-responsibilities)
requires candidate POI process analysis from actual passive stage captures and
applicable independent relevance reviews; it does not require corpus measurement
or coverage sidecars. Candidate-stage capture is distinct from a corpus sidecar.

`research corpus` separates offline preparation, explicit measurement and saved
export. Supply one `rtpeval_corpus_request_1` per original case/revision/scope;
the population can contain other inputs. Geographic bounds and any coverage
profile remain caller-owned. The
[producer wire](../../docs/contracts/0001-evaluation-artifacts.md#pinned-corpus-measurement-producer)
defines exact references, configuration, saved evidence and completion checks.

An illustrative request uses a numeric scope, never an inferred city boundary:

```json
{
  "schema_version": "rtpeval_corpus_request_1",
  "declaration_ref": {"path": "research.json", "sha256": "<exact digest>", "media_type": "application/json", "availability": "available", "schema_version": "rtpeval_research_declaration_1"},
  "case_id": "harbor-request", "case_revision": "input-7",
  "input_sha256": "<exact original-input digest>",
  "scope": {"kind": "radius", "latitude": 10, "longitude": 20, "radius_m": 2000},
  "scope_sha256": "<canonical scope digest>",
  "snapshot_identity": {
    "snapshot_ref": {"path": "snapshot.json", "sha256": "<exact digest>", "media_type": "application/json", "availability": "available"},
    "artifact_sha256": "<exact corpus artifact digest>",
    "policy_version": "tripworld-production-policy-v1",
    "space_id": "<production SPACE_ID>",
    "identity_pointers": {"artifact_sha256": "/corpus/output_sha256", "policy_version": "/policy_version", "space_id": "/space_id"}
  },
  "declared_at": "2026-10-01T00:00:00Z", "timing_basis": "unverified",
  "measurement_configuration": {
    "max_entities": 10000, "max_source_bytes": 104857600,
    "timeout_seconds": 30, "statement_timeout_ms": 10000,
    "connect_timeout_seconds": 5, "batch_size": 1000
  },
  "source": {
    "kind": "saved_dataset", "manifest_pointer": "/corpus",
    "dataset_ref": {"path": "entities.parquet", "sha256": "<exact corpus artifact digest>", "media_type": "application/vnd.apache.parquet", "availability": "available"},
    "embedding_index_ref": {"path": "embedding-index.json", "sha256": "<exact digest>", "media_type": "application/json", "availability": "available", "schema_version": "rtpeval_corpus_embedding_index_1"}
  },
  "coverage_profile_ref": null
}
```

Replace placeholders with hashes of saved bytes and the established production
space ID. `snapshot.json` may wrap the unchanged native manifest under `corpus`,
alongside the pinned policy/space declarations. `manifest_pointer` selects that
native manifest. Its artifact hash, entity count and entity/text versions are
checked against the measured source. The declaration must reside directly in the
request's source root; references are relative to that root.

Saved data supports native `RetrievalEntity` Parquet or
`rtpeval_corpus_entities_1` JSON containing an `entities` array. It requires an exact
`rtpeval_corpus_embedding_index_1` with the corpus artifact hash, production
`space_id`/`configuration` and saved embedding `text_hashes`. This supplies vector
membership without loading or generating vectors. An existing named dump alone
does not establish the pinned source.

```powershell
uv run rtpeval research corpus prepare material/corpus-request.json --directory artifacts/fresh-corpus-plan
uv run rtpeval research corpus measure artifacts/fresh-corpus-plan/receipt.json --directory artifacts/fresh-corpus-measurement
uv run rtpeval research corpus export artifacts/fresh-corpus-measurement/receipt.json --directory artifacts/fresh-corpus-export
```

For PostgreSQL, declare `source={"kind":"database","manifest_pointer":"/corpus"}`
and omit dataset/index refs. Preparation stays offline. Only measurement accepts
explicit database access and an environment-variable name for its connection string:

```powershell
uv run rtpeval research corpus measure artifacts/fresh-corpus-plan/receipt.json --database --dsn-env CORPUS_READ_ONLY_DSN --directory artifacts/fresh-database-measurement
```

Use separately approved database access and limits. The connection defaults to
read-only, and all identity checks and the bounded server-cursor scan share a
`REPEATABLE READ / READ ONLY` view. No credentials or connection string enter the
bundle. Connection and statement limits constrain database waits; the remaining
measurement deadline constrains each query and scan. The scan processes corpus
entities, including excluded/out-of-scope ones, within `max_entities`; it is not a
top-k query or unique-venue count. Byte limits bound selected source material and
retained observations. Oversized inputs fail preparation; scan caps, observation
byte limits, timeouts and failures retain partial/unavailable counts and reasons.
Source limits are checked before dependency reads; the scan checks its deadline
again before declaring completion, including empty or last-row scans. An omitted
or null request profile retains a supplied relevance-declaration profile with its
original snapshot, scope and thresholds, subject to compatibility validation.

The root `receipt.json` provides exact `sidecar_ref`, `measurement_ref`,
`completion_ref` and `declaration_ref` under `material/`. Use the returned
declaration with `research validate/report --track relevance`. Copies preserve
original bytes and source layout; new producer filenames avoid existing originals.
The final source-bound completion record is mandatory for produced sidecars, so an
interrupted publication cannot pass the relevance reader. Every operation requires
a fresh destination; an incomplete directory is retained for diagnosis.

Saved export checks observations and original hashes without connecting to the
database or changing declaration/measurement times. Existing coverage rows,
interests, reviews and opportunity provenance are retained; exported declarations
carry relevance and opportunities, while other tracks remain in their original
declaration. Supplied profile thresholds are copied unchanged. Prospective timing
is checked against selected dispatch evidence; absent evidence remains unverified.
These counts describe an entity/geographic proxy. Independent interest inventories,
sample coding and venue relevance judgments remain separately prepared materials.

### Reporting saved research material

Each report requires a fresh output directory and writes `<track>.json` and
`<track>.md`. Stdout records processing status, the track and deterministic source
and semantic digests. Exit 0 means reporting completed; it does not establish
complete measurement or a successful generation outcome. Exit 2 reports material
correction or argument errors. Inputs are preserved, reporting sends no provider
requests and does not select replacements or retries.

Population output keeps planned completion, conditional first-dispatched completion
and all-four completion separate, with numerator/denominator units and unresolved
bounds. Repeated requests do not become additional unique requests. The
[completion contract](../../docs/contracts/0002-intake-identity-usage.md#research-completion-and-selection)
explains producer completion and the distinction from quality qualification.

Use the same declaration with explicit track selection:

```powershell
uv run rtpeval research report material/research.json --track opportunities --directory artifacts/fresh-opportunities
uv run rtpeval research report material/research.json --track relevance --directory artifacts/fresh-relevance
uv run rtpeval research report material/research.json --track repair --directory artifacts/fresh-repair
uv run rtpeval research report material/research.json --track tradeoffs --directory artifacts/fresh-tradeoffs
```

| Track | Additional saved material | Reading the output |
| --- | --- | --- |
| Opportunities | Exact V1/V2 first-attempt stage captures; native final associations when scheduled places are reported | Observed versus complete unique canonical stage counts and Google/RAG partitions; unavailable history stays missing |
| Relevance | Independent original-input interest/venue reviews; fixed corpus/scope/stratum sidecars only for an explicitly selected coverage study | Relevant stage/intersection counts, judged/inventoried coverage and compatible V2-minus-V1 sets/deltas; optional geography proxies retain entity units |
| Repair | Native four-final quality, same-run V3 pair/continuity, mechanism reports and separately declared controlled inventories | Final versus paired changes and controlled target/control preservation use distinct populations and availability denominators |
| Tradeoffs | Native planner usage, explicit saved prices/bills and compatible quality descriptors | Selected benefit/resource comparisons, all-attempt consumption and full-population completion remain separate |

The [opportunity contract](../../docs/contracts/0001-evaluation-artifacts.md#canonical-candidate-opportunity-observations)
and [independent relevance/coverage contract](../../docs/contracts/0001-evaluation-artifacts.md#independent-interest-relevance-and-corpus-coverage)
own track material schemas and stage/review completeness. The
[Repair contract](../../docs/contracts/0005-quality-human-review.md#declared-research-repair-view)
and [generation tradeoffs](../../docs/contracts/0002-intake-identity-usage.md#generation-research-tradeoffs)
explain compatible native sources, masks and resource accounting. Native report
references require their exact saved source descriptors, rather than an isolated
summary copied from another run. Relevant labels, coverage and controlled guards
are separately prepared evidence; reporting does not create or execute them.

The native relevance reader permits empty `coverage_refs`. Markdown reports omit
corpus sections unless explicit coverage material or a coverage profile selects
that study. Empty interests remain non-applicable, and missing candidate judgments
remain UNKNOWN. The [benchmark layout](../../benchmark/README.md#layout) retains
native dependency roots and source identities; final-case acceptance is tracked
in [#138](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/138).

To save future opportunity stages, installed `rtpeval generate` and the V1/V2 runner
CLIs accept the default-off
`--opportunity-capture PATH` option. Use a fresh file path and retain the resulting
`rtpeval_candidate_capture_1` bytes with their exact attempt/input/final references.
The programmatic equivalent is `opportunity_capture_path`; installed generation also
forwards the selected run ID as `opportunity_capture_run_id`. Preparation only records
intent; execution saves the sidecar and its manifest reference. Registration retains
available sidecar bytes, while the attempt census and research declaration remain
separate caller-prepared material. The
[passive export guide](../../docs/0004-retrieval-persistence%28v2v3%29.md#passive-candidate-opportunity-export)
explains stage availability and write-failure behavior. Historical final outputs
cannot reconstruct absent admission or supply traces.

Reports are descriptive: no pooled research score, causal claim, version ranking
or automatic thresholds are produced. To locate selected research reports alongside
native suite reports, use the explicit [suite research attachment](#optional-research-attachments-and-offline-refresh)
flow. Original-input populations and qualified suite cases remain separate.

### Material preparation support

The [responsibility map](../../docs/0006-independent-evaluation.md#preparation-and-decision-responsibilities)
defines operator, independent-agent and user duties. Current support separates
consuming saved material from producing or independently reviewing it:

| Work | Supported tools | External work or pending implementation |
| --- | --- | --- |
| RequirementSpec handoff | `batch collect`, `attach-requirements`, `finalize` and `validate` check and bind saved author/reviewer material | Two real source-only independent-agent operations are separately operated; the CLI does not launch them. |
| Interests, relevance, sample coding and request semantics | Research relevance readers and native context/review consumers validate saved source-bound material | Independent agents or selected humans prepare actual judgments and evidence; there is no general installed semantic-review launcher. |
| Generation originals, usage, provenance and registration | Selected-version `generate` supports passive V1/V2 opportunity capture, selected-run binding, registration preflight and cancelled native completion | Real generation remains separately operated within approved scope and budget. |
| Attempt census | `research export-census` copies explicitly selected producer sources into a validated bundle; future `generate` records actual dispatch metadata | Operators supply population/profile, slot ordering and traceable historical metadata; native registration does not choose census bindings. |
| Optional corpus measurement and sidecars | `research corpus prepare/measure/export` validates explicit snapshots/scopes, measures saved data or an explicitly selected read-only database, and exports evidenced sidecars | Only for an explicitly selected study: operators supply geographic bounds, source/membership material, budgets and optional thresholds; reviewed samples remain separate. |
| V3 paired evidence | `pair acquire prepare/execute/replay/export` connects native paired plans, independent acquisition, receipts and report handoff; `pair prepare/report` remains available | Caller supplies the original selected stages, independent contexts/reviews, compatible prices and explicit limits. Primary final evaluation does not implicitly acquire paired material. |
| Independent primary evaluation | `evaluate prepare/execute/replay` acquires, reports and replays qualified four-final material | Caller supplies required reviewed contexts, compatible prices/options and explicit live limits/authorization. |
| Deferred human assessment | Native human prepare/package/import/report and optional offline suite attachments exist | Real raters must supply answers; package processing, agent output and approval cannot generate human assessment. |
| Corpus-free mechanism reports and final-case handoff | Existing stage/pair/research tools provide native source material | #138 tracks corpus-free relevance presentation and verification of the public case materials and private working/archive layout described in [benchmark storage](../../benchmark/README.md#layout); implement only gaps established under an approved scope. |

The defects/enhancements above are tracked in
[#131](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/131),
[#132](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/132),
[#133](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/133),
[#134](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/134),
[#135](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/135) and
[#136](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/136).
Material readers establish recorded integrity, not that a review or measurement
really occurred. Tool availability alone does not satisfy case readiness or approve
execution; missing evidence remains explicit and cannot be supplied by guessing.

## Installed task-oriented tools

Use `uv run rtpeval GROUP --help` and leaf help for exact native parameters. `quality`
reads an existing independent evidence packet; it is not a necessary follow-up to
`evaluate execute`. `usage` and `cost` retain descriptive missingness and dated explicit
prices/bills. `pair`, `controlled`, `review` and `mechanism` keep their separate schemas
and research-track meanings. Blinded participant collection is a separate operation. Controlled replay executes the
real frozen V3 chain offline, distinct from saved automatic-evaluation replay.

`advanced` exposes individual identity, snapshot, schedule, opening and route operations.
Explicit `advanced opening-run prepare / execute / replay` retains the incremental
opening route; execute is online and requires its own prepared one-use package/digest.
The separate route supports historical API-only runs and corrections; fresh primary
evaluation includes eligible assessment before scoring. `dev` exposes development tools;
its smoke execution can be online and needs its own approved plan. See
[incremental opening](#incremental-missing-hours-access-assessment),
[development-only smoke](#development-only-v0-smoke-route-requests-and-budget), and
[development guidance](../../docs/guides/development.md#verification-and-evidence).
Historical module commands and switches below remain reproduction references for their
original packet/policy; none grants a fresh live execution allowance.

## Contract and module navigation

Current rules have one topic owner. Read the relevant contract before preparing inputs;
acceptance records and Issue comments preserve historical decisions, not alternate rules.

| Responsibility | Current contract | Implementation |
| --- | --- | --- |
| Batch/artifact wire and deferred tracks | [Artifacts](../../docs/contracts/0001-evaluation-artifacts.md) | [intake](intake.py), [records](records.py), [projection](projection.py) |
| Structural claims and occurrence association | [Intake/claims](../../docs/contracts/0002-intake-identity-usage.md#claims) | [preparation](preparation.py), [claims](_claims.py) |
| Independent identity judgment | [Identity](../../docs/contracts/0002-intake-identity-usage.md#identity) | [Version dispatch/API checks](identity_program.py), [target ownership](identity_targets.py), [V0 correspondence/historical LLM](identity_llm.py), [legacy replay](identity.py), [V0 material](identity_adoption.py) |
| Request planning and frozen replay | [Snapshots](../../docs/contracts/0002-intake-identity-usage.md#snapshots) | [snapshot](snapshot.py) |
| Opt-in usage and descriptive resources | [Usage](../../docs/contracts/0002-intake-identity-usage.md#usage) | [usage capture](../app/observability/usage_capture.py), [usage_report](usage_report.py) |
| Reviewed requirements, time and occupancy | [Requirement/schedule](../../docs/contracts/0003-requirement-schedule.md) | [requirement_schedule](requirement_schedule.py), [schedule_time](schedule_time.py), [occupancy](occupancy.py) |
| Opening and route compliance | [Opening/routes](../../docs/contracts/0004-opening-routes.md) | [opening](opening.py), [routes](routes.py), [route preparation](_route_preparation.py) |
| Final five-dimension auxiliary report | [Quality](../../docs/contracts/0005-quality-human-review.md#scores) | [quality_report](quality_report.py) |
| Anonymous packages, revisions and human reports | [Human](../../docs/contracts/0005-quality-human-review.md#human) | [human_tasks](human_tasks.py), [human_answers](human_answers.py), [human_report](human_report.py) |
| Frozen V3 execution and controlled outcomes | [Controlled Repair](../../docs/contracts/0001-evaluation-artifacts.md#controlled-repair) | [controlled CLI](controlled_cli.py), [replay](controlled_replay.py), [report](controlled_report.py) |

Development verification utilities live in `tools/` within this package. The V0
[route request tool](tools/route_requests.py) and its
[CLI](tools/route_requests_cli.py) prepare smoke inventories and budgets; neither
Product planning nor the final quality scorer calls them. Smoke is a development
activity, not a product runtime stage. Core identity, snapshot and scoring modules
and their CLIs remain at the package root. A CLI is not necessarily a smoke utility.

## Fresh automatic evaluation CLI

New `itinerary_3` batches automatically select `rtpeval_declared_population_1`.
Preparation freezes finite candidate populations and returns
`needs_population_resolution` before acquisition if role/occupancy/date/journey,
executable requirement or density membership remains unresolved.
Known-date offset conflicts remain source-linked time UNKNOWN under the
[population contract](../../docs/0003-itinerary-transport.md#numerical-scoring-policy-and-limits);
they do not by themselves make candidate membership unresolved. Historical batches
keep their original default; explicit `--quality-profile rtpeval_declared_population_1`
opts eligible saved sources into a separately bound evaluation. See the
[activity and numerical contract](../../docs/0003-itinerary-transport.md#selection-and-verification-boundaries).
Selecting a profile does not authorize execution, historical rescoring or evidence reuse.

`evaluation_run_cli` composes native intake, fresh Google Search/Details, common
requirement-subject correspondence, V0 visit correspondence, snapshot coordinates, hours and directed routes, eligible missing-hours
access assessment, requirements/schedule, daily density and one final quality calculation.
It consumes the selected originals without
generating or repairing itineraries. Its scope is the four final projections; optional
V3 stages, human review and controlled-Repair tracks are explicitly excluded.

```powershell
.venv/Scripts/python.exe -m backend.evaluation.evaluation_run_cli prepare manifest.json --directory artifacts/fresh-evaluation --options options.json --prices prices.json --context context.json
.venv/Scripts/python.exe -m backend.evaluation.evaluation_run_cli execute artifacts/fresh-evaluation --approved-sha256 EXACT_PREPARATION_SHA256 --env-file .env
.venv/Scripts/python.exe -m backend.evaluation.evaluation_run_cli replay artifacts/fresh-evaluation
```

`prepare` and `replay` use no network or credentials. `execute` sends fresh requests;
the digest check does not establish user authorization. Repository approval and execution
child rules still apply. The preparation directory must be new. An execution directory
is consumed on failure too, with no automatic retry/resume. `--help` lists optional
source-linked occupancy, route and density review files.

The options object requires these fields:

| Field | Meaning |
| --- | --- |
| `model`, `model_endpoint` | Explicit identity/access deployment and HTTPS Responses base URL ending in `/openai/v1/` |
| `max_google_sends` | Shared send ceiling across both fresh snapshot phases |
| `max_input_tokens`, `max_output_tokens` | Per-model complete packet sizing allowance and server output limit |
| `timeout_seconds`, `total_timeout_seconds` | Per-request and whole-execution limits |
| `max_cost_usd` | Conservative reference-price reservation allowance, not an invoice cap |

Identity execution also accepts optional `reasoning_effort` (`low` or `medium`).
An omitted field preserves historical `low` execution without adding a new field to
old preparations. The supplied value is frozen in the preparation digest, sent in
the Responses request and checked against the captured HTTP journal during replay.
Invalid values fail during offline preparation. The separately fixed-medium opening
workflow does not admit this identity-only option.

Fresh preparations use `rtpeval_execution_preparation_3`. Named requirements receive
one independent common-subject correspondence batch before the V0 visit-only batch;
conditional missing-hours assessment remains the final model stage. There are at most
three sends; absent named subjects and empty V0 primary visits each skip their respective
stage and lower the ceiling by one. Each stage has a distinct priced operation
and shares the configured total deadline and reference USD allowance. No additional
Google plan or retry is introduced. `assess_missing_hours=false` skips opening assessment
and lowers the ceiling by one; this option requires a JSON boolean. Subject pricing must
cover `requirement_subject`; missing prices block preparation. The
[identity contract](../../docs/contracts/0002-intake-identity-usage.md#version-specific-identity-evaluation)
owns source binding, uncertainty, location purpose and historical compatibility.

After evidence acquisition, `opening-packet.json` records source-bound eligibility.
Eligible assessment completes before `report.json` is composed; no eligible visits
skips the call. `opening_assessment` records complete/skipped/disabled status, while
the report retains separate factual and model-supported access coverage. An assessment
failure or exhausted allowance saves a stopped report and usage/receipt without an
initial quality score or silent API-only fallback. Replay checks eligibility and all selected
captured model responses before recomputing the one final score. Version-1 packages
retain their original API-only semantics; exact historical policy replay needs its
retained implementation. Full contract: [missing-hours assessment](../../docs/contracts/0004-opening-routes.md#missing-hours-access-judgment).

New current V0 identity requests require a `decisions` object with one required key per
prepared short reference, covering visits and requirement subjects. Each judgment's
`reference_id` must equal its key; an explicit UNKNOWN is valid when evidence is
insufficient, while an omitted judgment is not. Incomplete, duplicate or foreign IDs
stop execution without retry and preserve the original HTTP response. Historical
uniform/legacy arrays retain their original paths; earlier current packets require
their retained producer implementation rather than conversion to the new request.

Supply a dated USD `rtpeval_prices_1` book covering exact Google operations/masks and the
selected model. Credentials are loaded only for execution from `GOOGLE_MAPS_API_KEY`
and `AZURE_OPENAI_API_KEY`; they are excluded from preparation and receipt data. Prices
identify source URLs and validity intervals; inaccessible billing stays unknown. A packet
exceeding its input allowance stops without trimming or a model send.

Preparation freezes originals, reviewed contexts, limits, prices and implementation hashes.
Preparation and execution preflight validate the checksum-bound local tokenizer vocabulary
without downloading it. Runtime dependency errors after an attempt preserve the stopped
report and observed sends. Regression tests use synthetic tokenization; real packet sizing
uses the existing offline vocabulary.
Execution preserves request wires without credential headers, raw HTTP bytes, times,
native snapshots, identity/access material, full check reports and evaluator-only usage/cost estimates.
`report.json` distinguishes `processing_status`, `acquisition_status` and `evidence_status`,
retains source-linked UNKNOWN reasons and exclusions, and may complete with FAIL/UNKNOWN.
The UNKNOWN inventory includes daily density and links identity/downstream uncertainty
to source-owned acquisition status, failure reason, request keys and attempts. Full HTTP
wire stays in the evidence journal; `rtpeval_usage_1` contains allowlisted metadata only.
Failure preserves a stopped report and receipt. Replay verifies originals, artifact hashes,
model HTTP linkage and recomputed native reports. Exit 0 means preparation or processing
completed; exit 2 indicates stopped execution or material correction, not an all-PASS gate.

## Offline workflow and CLI

### Incremental missing-hours access assessment

The [access policy](../../docs/contracts/0004-opening-routes.md#missing-hours-access-judgment)
adds an opening-only model fallback equally for V0-V3. API schedule decisions retain
priority. Clearly supported outdoor/exterior access can PASS with an explicit model basis;
ordinary sightseeing at confidently classified public landmarks can be inferred without
explicit exterior wording. Explicit restricted activities and museum admission still
require applicable evidence; genuinely unresolved intent stays UNKNOWN. Model judgment does not invent hours or
remove missing factual evidence and original grounding errors.

For historical API-only material or a separately authorized correction, reuse a
completed four-final execution; no new Google or V0 identity request is made:

```powershell
.venv/Scripts/python.exe -m backend.evaluation.evaluation_run_cli prepare-opening artifacts/fresh-evaluation --directory artifacts/opening-access --options opening-options.json --prices opening-prices.json
.venv/Scripts/python.exe -m backend.evaluation.evaluation_run_cli execute-opening artifacts/opening-access --approved-sha256 EXACT_OPENING_PREPARATION_SHA256 --env-file .env
.venv/Scripts/python.exe -m backend.evaluation.evaluation_run_cli replay-opening artifacts/opening-access
```

Options use the existing eight-field schema, with `max_google_sends=0` mandatory and
the explicitly selected opening deployment/HTTPS endpoint, token/time limits and USD
reference allowance. The price book must cover `kind=model`, `provider=azure_foundry`,
`operation=opening_access` and the selected model. This is one medium-effort Responses
call and zero retries; preparation itself is offline and grants no paid authorization.
Execution loads only `AZURE_OPENAI_API_KEY`, verifies code/source/parent receipts and
consumes its new execution directory even on failure. It stores raw HTTP/material,
actual usage, incremental cost and a separate complete automatic report. Parent costs
remain in the original report. Replay validates both receipts and performs no model call.
Missing/incomplete/failed model material is preserved without silently resending.

For independently captured material, prepare/import without an execution client:

```powershell
.venv/Scripts/python.exe -m backend.evaluation.opening_judgment_cli prepare manifest.json identity-report.json evidence-snapshot --model YOUR_MODEL --context context.json --output packet.json
.venv/Scripts/python.exe -m backend.evaluation.opening_judgment_cli import manifest.json identity-report.json evidence-snapshot --context context.json --material model-material.json --output opening.json
```

Material schema `rtpeval_opening_judgment_material_2` contains the complete unchanged
`packet`, actual Responses `request`/`response`, `provider=azure_foundry` and offset-aware
`requested_at`/`retrieved_at`. The request retains packet fields plus `store=false`,
`reasoning={"effort":"medium"}` and positive `max_output_tokens`; raw response contains
one structured assistant decisions object and actual input/output/total token counts.
Packet schema specifies decision fields/enums and one short ID per eligible occurrence.
Current packet schema is `rtpeval_opening_judgment_packet_2`, policy
`llm_access_reasonableness_2`. Decisions additionally record `intent_basis` and
`venue_category`; only public landmark/area categories can receive an inferred-default
PASS. Venue category is model interpretation; optional provider types retain raw absence.
Explicit museum exterior viewing is distinct from museum admission. Prior policy-1 material
requires its historical implementation for replay and cannot be relabeled as current material.
The packet also freezes evaluator implementation hashes; importing with changed source
code requires new preparation rather than accepting an old judgment under new code.
New packets sort object keys inside the bound request input. Native opening execution,
manifest-based quality composition and frozen-intake replay therefore agree despite
dictionary insertion order. Recorded request strings remain exact evidence; replay
pre-correction packets with their retained implementation instead of rewriting them.
All decisions and original activity quotations are validated; partial/foreign material
fails the whole import. Empty explicit schedules are never model cases. `openNow` alone
does not establish a schedule; absent/null periods can qualify. Supplied malformed periods,
unverified identity and invalid time cannot qualify.

Both `opening_cli` and `quality_report_cli` accept `--opening-judgment model-material.json`.
Library callers use `opening_judgment=`. Without that material the existing API-only
behavior remains available. With it the report selects opening rules 4 and quality profile
`rtpeval_access_quality_4`, preserving API seconds/coverage and separate LLM counts.
Supplied import provenance is distinct from dispatch independently captured by execution.

### Ordinary saved-evidence workflow

Run from the repository root with the existing Python environment. Names below represent
researcher-prepared files; commands do not generate missing independent evidence. For each
CLI, `--help` gives executable arguments. Default reports go to stdout; save them outside
source artifacts. Human output paths must be new. No command below acquires live evidence.

### Start with the synthetic usage packet

For a small development demonstration without authoring envelopes, run the subprocess
acceptance tests. They reuse existing synthetic fixtures and exercise the actual module
commands; they do not generate real trips. With the existing Python/npm environments,
run this in PowerShell 7 from the repository root:

```powershell
npm --prefix frontend run build:blind-review
New-Item -ItemType Directory -Path artifacts/evaluation-usage -Force | Out-Null
$env:EVALUATION_USAGE_RENDERER_DIR = (Resolve-Path frontend/dist-blind-review).Path
.venv/Scripts/python.exe -m pytest backend/tests/evaluation/test_usage_workflow.py -q --basetemp artifacts/evaluation-usage/demo-01 -o cache_dir=artifacts/evaluation-usage/cache
Remove-Item Env:EVALUATION_USAGE_RENDERER_DIR
```

Use a fresh `--basetemp` name each time: pytest clears that directory before use.
Generated inputs, snapshots, package and reports remain under that ignored directory.
Each test folder's `cli-output/` retains numbered `*-command.json` (argv/exit code),
`*-stdout.json` and `*-stderr.txt`. Command records contain local absolute paths;
replay them only while that packet remains in its original location. Tests verify that
pre-existing source bytes survive each CLI unchanged. External connections are guarded;
loopback remains available for the event loop's internal socket pair. Regression runs
use synthetic tokenization, as the parent suite does, and do not measure payload size.
Without `EVALUATION_USAGE_RENDERER_DIR`, the package test uses a minimal renderer fixture
so ordinary Python regression tests need no npm build. Set it as above for the real renderer.

| Example | What to inspect | Expected interpretation |
| --- | --- | --- |
| Four-version quality/resources | Quality `groups[].versions`; resource `metrics` | All V0-V3 retained; the synthetic V1 score is 50 with two opening UNKNOWNs; missing tokens stay null |
| V3 overlap retime | Pair `continuity`, `correspondence`, `deltas`, `visit_changes` | Confirmed overlap resolved using adopted lineage, zero removed visits; grounding delta is exactly 0/1; unresolved total delta stays null |
| Four controlled cases | `targets[].independent_outcome` or `control.outcome` | `resolved`, `valid_no_change`, `lawful_change`, `regressed`, respectively |
| Mechanism reporting | Mechanism `runs` and observation coverage | Four-version selections remain complete; missing V3 observations stay unavailable |
| Anonymous package | `public/review.html`, private mapping, import/report stdout | Four labels A-D, one imported answer revision and one descriptive task; answers are synthetic |
| Invalid input | Intake `material_diagnostics`, command exit code | Missing file and changed-source hash mismatch exit 2 with the affected path |

The exclusive-addition example deliberately includes an independently reviewed quotation,
“Exactly one primary visit on this day.” Its planner interpretation misses that restriction.
V3's internal `ACCEPTED_COMPLETE` therefore coexists with the independent `regressed` verdict.
Without that restriction, the same independently feasible addition is `lawful_change`.
The synthetic ranking answers demonstrate file linkage and report processing;
they are not real human assessments or evidence that any venue fact is true.
Existing native browser acceptance remains separate from package generation/import checks.

For researcher-supplied material, follow the commands below and the relevant contract;
the demo does not collect missing independent evidence. Four-final scoring requires a
final-only snapshot, whereas V3 paired reporting requires a paired snapshot. Per-request
reuse creates a separately labelled imported snapshot; it does not relabel the original.
Exit 0 means processing completed, including FAIL,
UNKNOWN or unavailable totals; inspect the report rather than treating it as an itinerary PASS.

Save stdout JSON as UTF-8 without BOM. In PowerShell 7, set
`$env:PYTHONIOENCODING = 'utf-8'` and pipe a stdout-only command to
`Set-Content -Encoding utf8NoBOM`; native CLI output options already write UTF-8.
Windows PowerShell 5.1 `>` uses UTF-16, so it cannot be used for these JSON artifacts.
The [dated usage record](../../docs/records/evaluation/2026-10-04-evaluation-usage.md)
retains the observed validation sequence and limits.

<a id="entry-points"></a>
<a id="manifest-and-envelope-vocabulary"></a>
<a id="independent-review-replay"></a>
<a id="identity-replay-ticket-03"></a>
<a id="validation"></a>
<a id="ticket-04-independent-snapshots"></a>
<a id="independent-preparation-formats"></a>

### Intake and identity

```powershell
.venv/Scripts/python.exe -m backend.evaluation manifest.json
.venv/Scripts/python.exe -m backend.evaluation.snapshot_cli identity-plan manifest.json
.venv/Scripts/python.exe -m backend.evaluation.snapshot_cli replay identity-snapshot --expected-plan identity-plan.json
.venv/Scripts/python.exe -m backend.evaluation.snapshot_cli identity-evidence identity-snapshot
.venv/Scripts/python.exe -m backend.evaluation.identity_cli manifest.json identity-evidence.json
.venv/Scripts/python.exe -m backend.evaluation.identity_cli manifest.json identity-evidence.json --prepare --model YOUR_JUDGMENT_MODEL
.venv/Scripts/python.exe -m backend.evaluation.identity_cli manifest.json identity-evidence.json --model-result identity-model-result.json
```

An acquisition caller separately uses `build_identity_plan`, injected async
`acquire_snapshot`, immutable `load_snapshot`, then `identity_evidence`.
The formal client above supplies the injected transport; these individual planning and
identity commands remain offline. The caller owns credentials, authorization and explicit
send ceilings. Identity uses the
[version-specific policy](../../docs/contracts/0002-intake-identity-usage.md#version-specific-identity-evaluation).
Without `--common-subjects`, the standalone commands above retain compatibility policy 4.
V1-V3 final/optional visits and their requirement targets use program rules over independent
API facts, with literal name equality and full address equivalence explained by same-observation
Google component pairs. Unexplained address differences are FAIL; no model fallback is used.
No model result is needed
for those references. No human confirmation or sampling is mandatory. `--prepare` prints a
V0-only frozen packet covering generated visits and user-requested requirement targets;
it does not execute a model. Target judgments belong to their own version, while
independent acquisition evidence can be shared. Import a
separately authorized saved response through the contract's model-result envelope. The
command has no built-in model execution client. Missing V0 results remain UNKNOWN;
API-backed references continue independently. V0 semantic judgments remain fallible. Intake exits 0 for
accepted material or 2 for correction. Identity exits 0 for packet preparation/completed
judgments (including confirmed failures), 3 for UNKNOWN/missing judgment, and 2 for
material/linkage errors. Incorrect submitted addresses and different venues are grounding
FAIL, even when the intended venue is recognizable. Their canonical ID stays null.
A separate verified `place_association` permits requirement occurrence matching and
independent opening/routes using the API venue's identity/hours/coordinates against
original date, time, order, mode and reserved duration. V0
requires validated candidate correspondence; V1-V3 require the independently verified
original submitted ID, without evaluator LLM or searched replacement. Untrusted association
remains UNKNOWN. Original outputs and grounding failures are retained. Requirement targets
use version-owned references projected from common independent subjects in fresh Primary;
historical target FAIL components retain their original semantics. Unresolved dates/roles
remain part of requirement judgment.
Fresh Primary reports use `versioned_api_identity_6` with common independent subjects
and V0 visit-only packets. Offline use is explicit:

```powershell
.venv/Scripts/python.exe -m backend.evaluation.identity_cli manifest.json identity-evidence.json --common-subjects --prepare-subjects --model YOUR_JUDGMENT_MODEL
.venv/Scripts/python.exe -m backend.evaluation.identity_cli manifest.json identity-evidence.json --common-subjects --prepare --model YOUR_JUDGMENT_MODEL
.venv/Scripts/python.exe -m backend.evaluation.identity_cli manifest.json identity-evidence.json --common-subjects --subject-result subject-model-result.json --model-result visit-model-result.json
```

These commands prepare/import material offline and never send a provider request.
The current subject policy is `requirement_subject_correspondence_2`, including typed
`postal_town` city evidence. Use `--subject-policy requirement_subject_correspondence_1`
explicitly to reproduce the preceding common strategy. Preparation-3 packages retain
their frozen `subject_policy`; old packets and scores are not upgraded implicitly.
Unresolved common subjects remain UNKNOWN; actual requirement violations still fail.
Without `--common-subjects`, existing offline callers retain `versioned_api_identity_4`;
those historical-compatible V0 packets use
`v0_identity_correspondence_3`: citation paths are schema enums
shared with import. Address-presence schema alternatives bind short reference IDs;
every absent/null/blank address requires `not_supplied` and forbids `claim.location` citations.
A supplied address forbids `not_supplied`, including UNKNOWN/no-match decisions.
`candidate_correspondence` retains the validated match separately from original-claim
`grounding_verdict`; recognizing a candidate does not repair an erroneous occurrence.
Supported destination contradictions remain FAIL even without a supplied original address;
the response must cite original name/destination and independent candidate support.
Old policy-1 packets and rejected historical output cannot be normalized or relabeled for
current import. The frozen historical all-version schema remains explicitly replayable.

`--historical-association` explicitly replays `versioned_api_identity_2` reports with
the former canonical-only downstream eligibility; historical evidence/results are preserved.
`--historical-program` explicitly replays the former `versioned_api_identity_1`
shared-target policy and `v0_identity_correspondence_2` packet. Its material cannot
pass current import. `--historical-llm` remains the older all-version replay.

For V0 correspondence within a verified material bundle:

```powershell
.venv/Scripts/python.exe -m backend.evaluation.identity_adoption_cli v0-identity-material.json --prepare --model YOUR_JUDGMENT_MODEL
.venv/Scripts/python.exe -m backend.evaluation.identity_adoption_cli v0-identity-material.json --model-result identity-model-result.json
```

The historical proposal response lacks the new address assessments and is not silently
converted. For exact historical replay use `--legacy` with the original audit/review inputs:

```powershell
.venv/Scripts/python.exe -m backend.evaluation.identity_cli manifest.json identity-evidence.json audit-plan.json --legacy --reviews identity-reviews.json
.venv/Scripts/python.exe -m backend.evaluation.identity_adoption_cli v0-identity-material.json --legacy
# Explicit replay of the superseded all-version LLM policy:
.venv/Scripts/python.exe -m backend.evaluation.identity_cli manifest.json identity-evidence.json --historical-llm --model-result historical-model-result.json
```

The [historical material contract](../../docs/contracts/0002-intake-identity-usage.md#v0-only-model-assisted-offline-adoption)
defines the V0 source bundle. Both policies retain the original files. Save stdout as UTF-8
without BOM. New consumers replay the complete source-bound model material; historical
consumers replay their frozen inputs. A copied or edited report cannot unlock preparation.
No planner version or production provider caller changes.

Offline regression coverage: `backend/tests/evaluation/test_identity_program.py` exercises
mixed-version resolver/CLI-to-quality and V3-pair flows with disabled model/network clients,
independent synthetic snapshots, strict field equality, FAIL/UNKNOWN preservation, unadopted
coordinates/endpoints and stale/forged/historical material rejection. Existing historical
policy tests explicitly select their replay path. Run these tests with the backend gates;
no paid acquisition or smoke execution is part of this validation.
`backend/tests/evaluation/test_identity_v0_contract.py` covers current schema alternatives,
supported/nonempty and rejected citations, complete owned decision coverage, exact provenance,
CLI import, preserved correspondence versus FAIL/UNKNOWN, quality fractions and null route
endpoints using synthetic local snapshots. SDK execution tests use MockTransport only.

### Prepared one-call identity development smoke

The [post-merge #82 refresh](../../docs/records/evaluation/intake-identity-usage.md#post-merge-v0-smoke-refresh-2026-10-06)
replaces the stale #77 execution proposal with a new offline manifest bound to the merged
implementation. Both historical material and failed attempts remain preserved. The fresh
directory was unconsumed at preparation; readiness and Issue publication grant no execution
authority. Its subsequently approved [one-call execution](../../docs/records/evaluation/intake-identity-usage.md#v0-identity-smoke-execution-2026-10-06)
imported eight V0 primary PASS while preserving a requirement-subject UNKNOWN. That
execution directory is now consumed; do not reuse it or infer route validation from identity.

The subsequent [#85 offline refresh](../../docs/records/evaluation/intake-identity-usage.md#v0-target-smoke-refresh-2026-10-06)
binds merged #83 source and all nine V0 visit/target references (fourteen candidate
appearances). Real cached-tokenizer sizing is 16,111 input tokens, or 17,135 with reserve,
exceeding the original 16,000 preparation ceiling. The guard rejected that preparation;
the preserved blocked draft is not an executable manifest and grants no live authority.
The user subsequently approved only the offline smoke-limit correction and re-preparation:
the tool now uses an 18,000 input ceiling / USD 0.0042 reference allowance. A compatible
new manifest required separate exact-plan live approval; historical approval was not reused.
Do not substitute the historical eight-visit request or trim candidate evidence to fit.

The subsequent [approved #85 execution](../../docs/records/evaluation/intake-identity-usage.md#v0-target-identity-smoke-execution-2026-10-06)
completed exactly one request with zero retries: eight visits and one V0-owned requirement
target are PASS, with zero FAIL/UNKNOWN. Offline import replay is exact; the target's
missing original address remains null with `not_supplied`. Original claims, V1-V3 records,
all protected evidence and implementation hashes are unchanged. The fresh execution
directory is now consumed. This identity-only result does not establish route feasibility,
score results or another request's authority.

`tools.validation.identity_judgment_smoke` is a separate development executor for a verified
V0 material bundle. Preparation is offline; execution requires explicit user approval of
the exact manifest digest and the [smoke execution handoff](../../docs/agents/smoke-tests.md).
Existing historical authorization is used only to verify source material. It grants no
new request authority. Preparation accepts `--endpoint` without loading credentials;
otherwise it reads existing V0 settings. Execution requires `AZURE_OPENAI_ENDPOINT`,
`AZURE_OPENAI_DEPLOYMENT` and `AZURE_OPENAI_API_KEY` through V0 settings; no credentials
are written to preparation. The request itself selects `gpt-6-luna`.

```powershell
.venv/Scripts/python.exe -m tools.validation.identity_judgment_smoke prepare --material v0-identity-material.json --directory artifacts/new-identity-smoke --endpoint https://YOUR_RESOURCE.openai.azure.com/openai/v1/
# Execute only after this exact preparation and its limits receive user approval:
.venv/Scripts/python.exe -m tools.validation.identity_judgment_smoke execute --preparation artifacts/new-identity-smoke/preparation.json --approved-manifest-sha256 APPROVED_DIGEST
```

Optional `--protected-hashes` reads a JSON `file_hashes` map to preserve additional original
files. The preparation binds verified source hashes, implementation hashes, the original
identity packet, exact wire request, endpoint, token/retail-reference limits and a single
execution directory. Schema `rtpeval_identity_smoke_preparation_2` recomputes V0 visit/target
references and candidate counts under the corrected output contract, excluding V1-V3
from the model request; V0 requirement targets are included. It writes `preparation.json`,
`pending-identity-report.json` and private `handoff.md`; append the reviewed source revision
and configuration prerequisites before any future dispatch. The pending report has no new
V0 model evidence. Implementation hashes cover evaluator modules, local reference/token
code and dependency declarations. Re-preparation over an existing directory is rejected. One approved
execution consumes its directory, even when it fails; reusing it cannot send again.
The SDK has zero retries, redirects are disabled, and the HTTP boundary checks the exact
POST/request and rechecks sources before its sole attempt. Changed source material after
the response prevents import. No planner or Google calls are included.

The fixed development limits are one request, low reasoning, no tools, `store=false`,
18,000 estimated input tokens including 1,024 reserve, 3,000 output tokens and a 60-second
HTTP deadline. The locally cached tokenizer is a surrogate preflight estimate. Excessive
reported usage stops import after receipt; these checks cannot guarantee the provider's
tokenizer or invoice ceiling. The fresh proposed live reference allowance is USD 0.0042; it
requires new exact-plan approval and does not inherit #73's consumed allowance. Official
OpenAI reference rates checked 2026-10-06 are USD 0.10 ordinary input, 0.01 cached input,
0.125 cache writes and 0.50 output per million tokens. At these caps the maximum standard
reference is USD 0.00375; a regional +10% scenario is USD 0.004125. Output already includes
reasoning. Receipts retain original usage, partition reported input categories, and label
missing categories as a conservative reference upper bound rather than observed zero.
Malformed or excessive category counts stop import. These standard/regional scenarios do
not establish a service tier, Azure SKU, taxes or a Foundry invoice ceiling. See the
[model price reference](https://developers.openai.com/api/docs/models/gpt-6-luna) and
[cache usage reference](https://developers.openai.com/api/docs/guides/prompt-caching).

`execution.json` records attempts, usage, reference cost, raw byte digest and terminal error
type without SDK exception text or headers. Received complete raw bytes stay in `response.bin`;
`model-result.json` is imported through the current source-bound policy. Only a valid complete
result produces `identity-report.json`. Execution exit 0 means valid processing, including
FAIL/UNKNOWN; exit 1 means a terminal execution/import error. Missing approval or changed
preparation raises before sending. Original claims stay intact; wrong addresses remain FAIL
with null canonical identity. No paid execution is implied by preparation or an offline test.

Fresh-clone tests use synthetic fixtures rather than requiring ignored live artifacts:

```powershell
New-Item -ItemType Directory -Path artifacts/evaluation-adoption -Force | Out-Null
.venv/Scripts/python.exe -m pytest backend/tests/evaluation/test_identity_llm.py backend/tests/evaluation/test_identity_adoption.py -q --basetemp artifacts/evaluation-adoption/test-01 -o cache_dir=artifacts/evaluation-adoption/cache
```

<a id="v0-route-requests"></a>

### Development-only V0 smoke route requests and budget

This tool is in `backend.evaluation.tools`, separate from ordinary evaluator scoring.
It consumes core evaluator preparations without becoming a required scoring step.
Use the new module path below; the former root-level tool modules are retired.
Historical records and frozen manifests retain the paths of their own revisions.

The [#86 offline refresh](../../docs/records/evaluation/routes.md#accepted-v0-identity-route-refresh-2026-10-07)
uses #85's accepted current report: all four original legs are identity-eligible and reuse
eight independent coordinates, requiring no Details. The dated KR profile retains three
blocked WALK requests and one conditional TRANSIT, zero ready Routes and four UNKNOWN
feasibility verdicts. Actual CLI replay returns 3 and matches the library; the request
package is complete preparation without live authority. No provider/price refresh or
acquisition occurred; hypothetical inventory estimates are not a paid allowance.

The later [free KR support and budget assessment](../../docs/records/evaluation/routes.md#kr-route-support-budget-2026-10-07)
identifies Kakao Map V2 WALK as a documentation candidate for three calls (30 KRW
published reference), with TMAP pedestrian as an alternative. This is an offline draft,
not a supported provider in these commands. Retention/use conditions, account costs and
an offline adapter remain unresolved. Kakao/ODsay general TRANSIT cannot establish the
original explicit departure; Google KR TRANSIT coverage remains unconfirmed. The saved
#86 package, zero-send preflight and all four UNKNOWN verdicts are preserved.

The [Sydney offline preparation](../../docs/records/evaluation/routes.md#sydney-offline-route-preparation-2026-10-07)
adds explicit `--region AU` / `region_code="AU"`. Australian WALK can become ready for
approval with complete independent identity/coordinates/window checks; it stays UNKNOWN
without route evidence. TRANSIT remains conditional and DRIVE is unsupported by this
acquisition path. The input must explicitly declare Australia. Default KR output/replay
is unchanged; region is never inferred or a live authorization. Unique requests determine
budgets, while repeated leg occurrences remain visible.

The current [Sydney source request](../../tools/validation/packets/sydney-v0-route-smoke/request-natural.json)
is four days (October 14-17), two travelers and AUD 1600, with relaxed pace, natural
interests and required Sydney Opera House. It specifies no daily attraction count;
independent density scoring does not supply generation quotas. It is a generation
input, not a generated output, reviewed RequirementSpec or API snapshot. The earlier
[counted request](../../tools/validation/packets/sydney-v0-route-smoke/request.json)
is preserved as historical evidence. Its non-generation USD 0.3522 price scenario
includes unready routes and does not authorize their execution. That counted-input
generation smoke stopped after one requirements response because exact daily
cardinality is an unsupported hard semantic condition. It produced no itinerary or
evaluator bundle; the consumed plan cannot be reused. Original input and raw output
remain preserved, and actual billing is unknown. See the
[generation stop record](../../docs/records/v0-v3/development-pilots.md#sydney-v0-generation-smoke-2026-10-07).
The separately approved natural-input V0 smoke completed with two model sends,
zero retries and a valid original result; saved-response runner replay matches
exactly. Its declared main counts are 2/2/2/1, retained without quantity repair.
No independent identity, opening, route or score acceptance follows from generation.
See the [natural execution record](../../docs/records/v0-v3/development-pilots.md#sydney-v0-natural-generation-smoke-2026-10-07).
The subsequent [Sydney identity smoke](../../docs/records/evaluation/intake-identity-usage.md#sydney-v0-identity-smoke-2026-10-07)
acquired eight independent searches and made one V0-only model request: six primary
PASS, one retained primary FAIL and one requirement-target PASS. Official-source
inspection flags a possible address false positive; it does not rewrite the report.
This single-source library view is not a qualified four-version intake or a legacy
adoption bundle. Opening, route and final score evidence remains outstanding.
The subsequent [opening/route execution](../../docs/records/evaluation/routes.md#sydney-v0-opening-routes-smoke-2026-10-08)
made six Details and two WALK Matrix requests, with no model calls or retries. Identity
FAIL blocked acquisition for the affected venue/leg. Native opening reports four PASS
and three UNKNOWN; routes report two PASS and one UNKNOWN, retaining the unbound day-four
transport separately. Requirement/schedule reports retain unresolved evidence. Final
quality reporting rejects this V0-only view with `Exactly four versions required`;
the smoke does not bypass intake or establish an overall quality score.
The dated input needs trusted-day revalidation before later use.

The [Museum follow-up preparation](../../docs/records/evaluation/routes.md#sydney-museum-follow-up-preparation-2026-10-08)
uses current physical association while retaining the original address FAIL. The
original Museum-to-QVB leg is WALK with a 20-minute reservation. The separately approved
[execution](../../docs/records/evaluation/routes.md#sydney-museum-follow-up-execution-2026-10-08)
completed one Museum Details and one WALK Matrix request, both HTTP 200, zero retries.
Museum opening PASS uses regular hours; the WALK takes 562 seconds over 678 metres.
Combined opening counts are five PASS/two UNKNOWN and three evaluable routes PASS.
Eight prior observations retain their original bytes/timestamps; no DRIVE extension
is included. USD 0.025 is retail reference, with actual billing unknown. The one-use
directory/allowance is consumed. Saved reports replay exactly and requirement/schedule
sections remain unchanged; no overall score or final four-version acceptance follows.
The actual source remains a single-version library view. Existing bundle/CLI
regressions do not turn it into a qualified four-version intake or adoption bundle.

Prepare from an exact current `versioned_api_identity_4` report without acquiring evidence:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
.venv/Scripts/python.exe -m backend.evaluation.tools.route_requests_cli v0-identity-material.json identity-report.json --context schedule-context.json --route-reviews route-reviews.json --prepared-at 2026-10-05T10:23:02Z | Set-Content -Encoding utf8NoBOM request-package.json
# Missing current report: derive a current pending report without any model result or send.
.venv/Scripts/python.exe -m backend.evaluation.tools.route_requests_cli v0-identity-material.json --context schedule-context.json --prepared-at 2026-10-05T10:23:02Z
# Historical identity reports require explicit replay; they never replace current evidence.
.venv/Scripts/python.exe -m backend.evaluation.tools.route_requests_cli v0-identity-material.json historical-identity.json --legacy --context schedule-context.json --prepared-at 2026-10-05T10:23:02Z
# Illustrative qualified Australian material; the single-source smoke view is not this CLI bundle.
.venv/Scripts/python.exe -m backend.evaluation.tools.route_requests_cli sydney-identity-material.json identity-report.json --region AU --context schedule-context.json --prepared-at 2026-10-07T00:00:00Z
```

Schema `rtpeval_v0_route_requests_2` binds the selected identity policy and exact replay
inputs. Current reports require no human identity/audit gate; missing model evidence keeps
original legs visible with UNKNOWN endpoints. Rejected/stale reports or corrupt sources
return material diagnostics with no partial request inventory. A historical report supplied
without `--legacy` is rejected; historical saved packages are not rewritten or relabeled.
Each leg exposes original endpoint claims, candidate correspondence, grounding verdicts and
identity blockers separately from its route verdict. A verified `place_association` permits
independent coordinates and routes for the associated API venue while the original grounding
FAIL remains visible. Unresolved association blocks acquisition; no substitute venue or
repaired original claim is introduced. Historical policy-3 reports require `--legacy`.
Endpoint occurrence/unique-venue counts remain distinct from deduplicated Details/Routes
request counts.

Optional `--occupancy-reviews` retains reviewed occupancy; `--details-snapshot` consumes already supplied
independent Details with the package's exact `details_plan`. It sends nothing and never retries bad evidence.
Saved coordinates are reused only after source replay and ID/numeric validation. The current provider
preparation profile is KR, checked 2026-10-05. Original mode/timing/continuous windows and blocked legs stay visible.
WALK coverage and TRANSIT's unverified regional support can leave zero ready Routes.
Omit absent optional review flags; a supplied review file must contain its JSON object
envelope, not JSON null. Zero eligible venues is distinct from missing coordinates for
eligible venues. Zero ready requests is a complete preparation outcome; it cannot remove
actual identity blockers without separately accepted current evidence.

Exit 0 means complete preparation without pending applicable legs, 3 means a complete blocked/conditional
inventory, and 2 means invalid material. Save UTF-8 without BOM. Completion is not route feasibility or acquisition
approval. Masks, dated prices, source hashes, actual versus hypothetical budgets and stops are in the
[request contract](../../docs/contracts/0004-opening-routes.md#v0-route-request-package).

Library seams: `prepare_v0_route_requests` and `preflight_v0_route_requests` in [route_requests](tools/route_requests.py).
Preflight recomputes the frozen package before checking ledger/request limits and always returns
`live_authorized=false`. No provider or model client is present. Execution requires separate inventory/budget
approval and a current-session execution child configured `gpt-6.1-sol` / `medium`.

Fresh-clone fixtures are independently runnable:

```powershell
New-Item -ItemType Directory -Path artifacts/evaluation-route-requests -Force | Out-Null
.venv/Scripts/python.exe -m pytest backend/tests/evaluation/test_route_requests.py backend/tests/evaluation/test_route_requests_versioned.py -q --basetemp artifacts/evaluation-route-requests/test-01 -o cache_dir=artifacts/evaluation-route-requests/cache
```

<a id="offline-evaluation-preparation-and-metrics-tickets-01-06"></a>
<a id="ticket-05-offline-requirement-and-schedule-metrics"></a>
<a id="ticket-06-offline-opening-compliance"></a>
<a id="ticket-07-offline-same-day-routes"></a>
<a id="selection-and-scoring"></a>

### Independent schedule, opening and routes

```powershell
.venv/Scripts/python.exe -m backend.evaluation.requirement_schedule_cli manifest.json identity-report.json --context schedule-context.json --occupancy-reviews occupancy-reviews.json
.venv/Scripts/python.exe -m backend.evaluation.route_cli prepare manifest.json identity-report.json --context schedule-context.json --occupancy-reviews occupancy-reviews.json --route-reviews route-reviews.json --coordinates coordinates.json
.venv/Scripts/python.exe -m backend.evaluation.snapshot_cli evidence-plan manifest.json identity-report.json route-contexts.json
.venv/Scripts/python.exe -m backend.evaluation.opening_cli manifest.json identity-report.json evidence-snapshot --context schedule-context.json --expected-plan evidence-plan.json
.venv/Scripts/python.exe -m backend.evaluation.route_cli score manifest.json identity-report.json evidence-snapshot --context schedule-context.json --occupancy-reviews occupancy-reviews.json --route-reviews route-reviews.json --coordinates coordinates.json --expected-plan evidence-plan.json
```

Save prepared route contexts, build the evidence plan and acquire/replay its snapshot
through the separately authorized injected caller before scoring. Preparation does not
invent coordinates or transport restrictions. Missing optional context/review retains
UNKNOWN or applicability diagnostics. Route preparation exports `route_contexts` and its ready-made `evidence_plan`.

Requirement/schedule matching uses verified occurrence associations for count,
date, exclusion and fixed-time matching. Source-reviewed `transport_modes` obligations
are executable; the [RequirementSpec contract](../../docs/contracts/0003-requirement-schedule.md#obligations)
owns rule selection and aggregation. `requirement_identity` exposes the physical
identity and grounding provenance used. Historical identity reports retain canonical-only
matching. After an authorized rule change, save a new offline recalculation separately
from the frozen execution report/receipts. Exact replay of an earlier report uses its
original code revision; current rules do not overwrite or relabel historical results.

When the adopted identity report was resolved from an independent identity snapshot that
already contains coordinates, replace `--coordinates coordinates.json` with
`--identity-snapshot identity-snapshot` on route prepare/score or quality-report commands.
The library keyword is `identity_snapshot_directory`; direct inspection uses
`prepare_snapshot_coordinates` in [snapshot_coordinates](snapshot_coordinates.py).
Each replay verifies the snapshot and its exact identity linkage. Source-derived coordinate
records retain response hashes/pointers and retrieval times, without fabricated review fields.
Missing, invalid or conflicting coordinates stay diagnostic and do not trigger acquisition.
Select one coordinate source; the existing reviewed envelope and query options remain available.
The automatic path uses existing default query options and requires its own matching evidence
plan; previously prepared manual-coordinate query hashes are not interchangeable.
Use that plan directly, or put the context array under `{"contexts": [...]}` in
`route-contexts.json` for the snapshot planning CLI; the full preparation report is not
that CLI input. `--expected-plan` optionally enforces trusted full-plan equality.

Library seams: `score_requirement_schedule`, `prepare_routes`, `score_opening`, and
`score_routes`. Opening rules version 2 uses valid regular hours for unresolved intervals
after applicable current evidence; already established current closure/opening stays
authoritative. Special-date markers alone do not veto regular hours, and `openNow=false`
at query time does not close a planned visit. Regular evidence gives ordinary PASS/FAIL,
with its basis recorded. `basis_segments.hours_fields` names contributing fields;
`regular_fallback` exposes the scope, applied intervals and retained diagnostics.
Missing both usable schedules remains UNKNOWN. Save rule-change recalculations outside
the original frozen execution receipts; exact older reports require their original code.
See the [opening contract](../../docs/contracts/0004-opening-routes.md#opening).

These and identity/snapshot plan commands support `--paired` where
declared, selecting available V3 draft/final-primary projections; paired scope must
remain consistent across inputs. Ticket 10 combines these paired outputs below.
Scorers exit 0 for complete processing, including FAIL/UNKNOWN,
or 2 for material/replay correction. Snapshot commands exit 2 for invalid replay/input.

<a id="ticket-08-final-multimetric-report-and-auxiliary-scores"></a>

### Final report and resources

```powershell
.venv/Scripts/python.exe -m backend.evaluation.quality_report_cli manifest.json identity-report.json evidence-snapshot --context schedule-context.json --occupancy-reviews occupancy-reviews.json --route-reviews route-reviews.json --coordinates coordinates.json --expected-plan evidence-plan.json --generated-at 2026-10-03T00:00:00Z
.venv/Scripts/python.exe -m backend.evaluation.usage_report usage-v0.json usage-v1.json usage-v2.json usage-v3.json
```

`build_quality_report` combines the existing independent scorers and identity records.
It accepts final-only snapshots (`paired=False`); a paired snapshot reports
`unsupported_snapshot_scope`. It emits exact five-dimension scores/masks without resource,
human or mechanism penalties. Exit 0 means processing completed, not a passing itinerary
or available total; correction exits 2. `--generated-at` defaults to current UTC;
freeze it with the inputs for reproducible report content.

Current report schemas are `rtpeval_quality_report_2` and `rtpeval_v3_pair_report_2`.
Both use `rtpeval_daily_density_2` and the sole current
[approved table](../../docs/contracts/0005-quality-human-review.md#daily-density)
from [Issue #52](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/52).
Use `overall_total.score_0_100` for the density-adjusted score; `auxiliary_total`
remains the exact five-dimensional diagnostic. Both report commands accept
`--density-reviews density-reviews.json`. Review the complete original request once
per group, including dated count exceptions, and reuse that policy for final and paired
reports. A request containing nonempty `additional_preferences` needs this review to
establish density deductions; omitting it keeps the overall total unavailable.

Example preparation (replace all linkage and review fields with actual values):

```json
{
  "schema_version": "rtpeval_density_reviews_1",
  "batch_id": "submitted-batch",
  "batch_revision": "1",
  "groups": [{
    "group_id": "request-group",
    "input_sha256": "actual-input-file-sha256",
    "reviewer_ref": "independent-reviewer",
    "reviewed_at": "2026-10-04T00:00:00Z",
    "review_origin": "agent",
    "rationale": "Original request asks for relaxed pace without explicit daily counts.",
    "default": {
      "profile": "relaxed",
      "exact_count": null,
      "source_refs": [{
        "field_path": "additional_preferences",
        "quote": "Please keep the pace relaxed."
      }]
    },
    "days": []
  }]
}
```

The [density contract](../../docs/contracts/0005-quality-human-review.md#daily-density)
defines dated overrides, count exemptions/mismatches, penalty tables and UNKNOWN bounds.
Keep historical report files intact and write new replays to separate paths.

Usage envelopes come from opt-in [request-local capture](../app/observability/USAGE.md),
not automatic CLI/API collection. `compare_usage` keeps scopes/namespaces and missing
measurements explicit. Its CLI prints a descriptive report; invalid envelopes raise an
input error rather than partial comparisons. It adds no billing claim or quality penalty.

<a id="transport-responsibility-correction---2026-09-30"></a>
<a id="ticket-09-local-blinded-ranking-workflow"></a>

### Local blinded ranking

For the [staged acceptance workflow](../../docs/contracts/0005-quality-human-review.md#staged-automatic-acceptance-and-deferred-blinded-review),
complete automatic case acceptance first and retain the exact accepted manifest,
originals and matched evaluation evidence. Later prepare these same outputs for
consolidated blinded review; do not regenerate them or rerun primary evaluation.
The commands below require separately authorized real assessment and fresh output
paths. Replace the illustrative report timestamp with the actual human-report
creation time; it is not the time of earlier automatic acceptance.

```powershell
npm --prefix frontend run build:blind-review
.venv/Scripts/python.exe -m backend.evaluation.human_cli prepare manifest.json selection.json --out preparation.json
.venv/Scripts/python.exe -m backend.evaluation.human_cli package manifest.json selection.json display-review.json --out public-review --private-out private-mapping.json --renderer-js frontend/dist-blind-review/review.js --renderer-css frontend/dist-blind-review/review.css
.venv/Scripts/python.exe -m backend.evaluation.human_cli import public-review/presentation.json private-mapping.json answers.json --out imported-revisions.json
.venv/Scripts/python.exe -m backend.evaluation.human_cli report public-review/presentation.json private-mapping.json answers.json --generated-at 2026-10-03T00:00:00Z --out human-report.json
```

Prepare and independently review display material before packaging. Deliver only
`review.html` and `presentation.json`; retain preparation, display review and private
mapping outside the public directory. Open `review.html` directly in a local browser.
The package needs no account, server, CDN or submission endpoint. Use synthetic material
for development; real assessment needs separate approval. Successful processing exits 0;
invalid material or output conflicts exit 2. Import/report can take multiple answer files.

Keep the resulting native human report standalone when using the case workflow.
If suite integration is explicitly selected, export its source-bound report,
presentation, mapping and answers references and use the
[offline attachment refresh](#installed-multi-case-suite) commands. Each package/rater
remains separate, and the new summary revision preserves earlier primary scores
and receipts. Missing human answers remain visible; no combined automatic/human
score is produced.

The current renderer provides IANA zone selection and HH:mm clocks, labelled Inferred
arrival, drafts, submitted revision recovery, JSON download/import and confirmed Clear
answers. It hides Original timestamp controls and dedicated uncertainty/item/time-warning
hints; frozen material retains uncertainty. Clear only erases this package/rater's local
answer history. Download a backup first; researcher-held old revisions remain records.
The [human contract](../../docs/contracts/0005-quality-human-review.md#human) owns exact
answer, blinding and display semantics. Automated DOM checks do not prove native file://
storage behavior; the [acceptance record](../../docs/records/evaluation/blinded-ranking-record.md)
distinguishes automated checks from user-reported browser acceptance.

### V3 paired diagnostics

#### Installed paired acquisition

For offline reuse, provide the completed primary operation and, optionally, the
selected V3 generation capture. The [import contract](../../docs/contracts/0001-evaluation-artifacts.md#source-labelled-offline-imports)
defines request matching, source validation, original times and inherited accounting.

To retain current common-subject policy, add
`--subject-primary-run artifacts/primary` to **both** `import` and `prepare` below.
The explicitly selected completed preparation-3 Primary must match the exact native
intake and use `requirement_subject_correspondence_2` / `versioned_api_identity_6`.
Its closed facts and original subject-model HTTP receipt are verified without
rebuilding its quality scores. Preparation 2 freezes and copies that source; fresh,
cached and replayed paired identities reuse its original target observations and
judgment while resolving paired visits independently. Drift is rejected before
dispatch, with no new subject-model fallback. Omitting the flag retains preparation
1 / compatibility identity policy 4; supplying a Primary for factual import alone
does not select common-subject policy.

```powershell
uv run rtpeval pair acquire import manifest.json --directory artifacts/pair-import --primary-run artifacts/primary --generation generation/v3 --context schedule-context.json --route-reviews route-reviews.json --density-reviews density-reviews.json
uv run rtpeval pair acquire prepare manifest.json --directory artifacts/pair-report --selection selection.json --options pair-options.json --prices oracle-prices.json --context schedule-context.json --route-reviews route-reviews.json --density-reviews density-reviews.json --identity-snapshot artifacts/pair-import/identity-snapshot --snapshot artifacts/pair-import/evidence-snapshot
uv run rtpeval pair acquire execute artifacts/pair-report --approved-sha256 EXACT_CONTENT_SHA256
uv run rtpeval pair acquire replay artifacts/pair-report
uv run rtpeval pair acquire export artifacts/pair-report --directory artifacts/pair-export
```

Imported preparation selects `execution_mode=offline_reuse`. Both phases must be
provided; it never reads credentials or constructs an HTTP client. Use explicit
zero send/spend limits with positive timeouts. Imported mode enforces zero current
sends and a zero current request-price estimate. Missing
facts remain UNKNOWN. `pair acquire import` does not use paid options or prices.
Omit absent optional reviews. Supply original independent reviews; import does not
author them. All destinations are fresh. The remaining flow describes separately
authorized acquisition when suitable saved observations are unavailable.

`rtpeval pair acquire` connects the native paired workflow for an explicitly
selected qualified manifest. The [acquisition contract](../../docs/contracts/0001-evaluation-artifacts.md#paired-evidence-acquisition)
defines selection, source bindings, estimates, one-use execution and export.
Prepare the original input, reviewed RequirementSpec, original V3 stages and
independent schedule/route reviews first; nonempty preference text also requires
an independent density review, which may retain unresolved meaning. Optional
occupancy/correspondence reviews preserve their native uncertainty.

`selection.json` must exactly match the selected manifest groups in order:

```json
{
  "schema_version": "rtpeval_pair_selection_1",
  "batch_id": "selected-batch",
  "batch_revision": "1",
  "runs": [{
    "group_id": "selected-group",
    "run_id": "selected-v3-run",
    "input_sha256": "EXACT_INPUT_SHA256",
    "requirement_spec_sha256": "EXACT_REQUIREMENT_SPEC_SHA256",
    "result_sha256": "EXACT_V3_RESULT_SHA256",
    "stage_pointers": {"draft": "/v3/draft", "final_primary": "/v3/final_primary"}
  }]
}
```

The paired options file has exactly four numeric limits:

```json
{"max_google_sends": 30, "max_cost_usd": "1.00",
 "timeout_seconds": 10, "total_timeout_seconds": 120}
```

These illustrative limits are not execution authorization. Supply compatible
`rtpeval_prices_1` USD reference prices and fresh output directories:

```powershell
uv run rtpeval pair acquire --help
uv run rtpeval pair acquire prepare manifest.json --directory artifacts/fresh-pair --selection selection.json --options pair-options.json --prices oracle-prices.json --context schedule-context.json --route-reviews route-reviews.json --density-reviews density-reviews.json
# Only after approval of this exact preparation and its live limits:
uv run rtpeval pair acquire execute artifacts/fresh-pair --approved-sha256 EXACT_CONTENT_SHA256 --env-file .env
uv run rtpeval pair acquire replay artifacts/fresh-pair
uv run rtpeval pair acquire export artifacts/fresh-pair --directory artifacts/fresh-pair-export
```

Prepare, replay and export are offline. Execute reads `GOOGLE_MAPS_API_KEY` only
after local preflight and only for uncached phases. No model credential or model
send is used. Fresh acquisition also accepts `--subject-primary-run` with the same
binding rules as offline reuse. The native paired reporter requires the manifest's
primary reference
inventory as well as V3 draft/final occurrences; V0 identity needing a model remains
UNKNOWN. This workflow supplies paired diagnostics, not primary V0 evaluation.

Inspect `preparation.json`: exact identity requests, native evidence occurrence
inventory and, without saved identity evidence, a deferred evidence request count
with an occurrence-based cost upper bound. Canonical venue/route requests become
exact after identity acquisition; inspect `execution/route-preparation.json`,
`evidence-plan.json`, `inventory.json`, both snapshots and the HTTP journal.
Reference reservations and measured send counts are separate from invoice billing.
Provider failures retain units and partial evidence; stopped work keeps usage and
its closed receipt. A consumed package cannot retry or resume.

Optional `--identity-snapshot DIRECTORY` reuses only a verified exact paired
identity snapshot; `--snapshot DIRECTORY` additionally requires its matching
paired evidence plan. The cached native bytes and capture times are retained,
with zero current-phase sends. Planner or final-only snapshots do not qualify.

Export's `handoff.json` contains relative `manifest`, `suite_pair` paths and a
`research_pair` artifact descriptor. Use `suite_pair` as the selected case's
`tracks.pair`; use `research_pair` in the existing Repair material's
`pair_reports`, with the matching declared first attempts. References are relative
to the export root; rebase them when joining a larger declaration root. Export
does not create a population, selection profile or human answers. Stopped
acquisitions cannot publish a completed handoff.

#### Reporting previously prepared material

```powershell
$env:PYTHONIOENCODING = 'utf-8'
.venv/Scripts/python.exe -m backend.evaluation.v3_pair_cli prepare manifest.json identity-report.json | Set-Content -Encoding utf8NoBOM edit-provenance.json
.venv/Scripts/python.exe -m backend.evaluation.v3_pair_cli report manifest.json identity-report.json paired-evidence-snapshot --context schedule-context.json --route-reviews route-reviews.json --coordinates coordinates.json --expected-plan paired-evidence-plan.json --edit-provenance edit-provenance.json --generated-at 2026-10-03T00:00:00Z | Set-Content -Encoding utf8NoBOM v3-pair-report.json
```

Prepare the current identity replay and frozen evidence plan with `--paired`. Save
stdout JSON as UTF-8. The commands read the original selected V3 result bytes
automatically; `--edit-provenance`
is optional and, when supplied, is checked against a fresh source replay. Additional
report options are `--occupancy-reviews`, `--correspondence-reviews` and
`--identity-snapshot` (as an alternative to `--coordinates`). No provider/model/database
call or input modification occurs. The snapshot argument can be omitted when no group
has an available pair; supplied snapshots are still verified.

Library seams are `read_v3_result_sources`, `prepare_v3_correspondence` and
`build_v3_pair_report`. Original adopted edit/fragment sources establish occurrence
lineage, independent identities establish venue continuity, and the scorers establish
quality. The report retains local uncertainty, pair availability, exact signed deltas,
losses/replacements, route topology/context and independent conflict transitions.
Its pair mask/auxiliary totals remain separate from Ticket 08's four-final report.
Exit 0 means complete processing, including unavailable pairs and FAIL/UNKNOWN checks;
corrupt/stale material exits 2. See the [paired contract](../../docs/contracts/0005-quality-human-review.md#v3-pairs).

For authorized missing-hours assessment of both V3 stages, use the same access policy
and fresh V3-only material. Existing primary responses retain their original bindings.
Preparation and replay below are offline; execution is one model attempt with zero Google
sends and no retries. Options must explicitly set `max_google_sends=0` and all model,
token, timeout and USD reference limits. Batch call/cost limits remain the operator's gate.

```powershell
rtpeval pair access prepare manifest.json identity-report.json paired-evidence-snapshot --context schedule-context.json --directory artifacts/pair-access --options access-options.json --prices access-prices.json
rtpeval pair access execute artifacts/pair-access --approved-sha256 EXACT_PREPARATION_SHA256 --env-file .env
rtpeval pair access replay artifacts/pair-access
rtpeval pair report manifest.json identity-report.json paired-evidence-snapshot --context schedule-context.json --opening-judgment artifacts/pair-access/execution/model-result.json
```

Pass the same optional expected plan during packet preparation and report building.
Retain the pair's required route, occupancy, density and correspondence materials in
the report command. Zero eligible contexts skips model execution; preserve API UNKNOWNs
when the policy cannot support access. Pair scores and historical primary scores remain
distinct. The contract above defines context sharing and source binding.

## Verification and status boundary

<a id="offline-cost-report"></a>

### Offline cost report

```powershell
.venv/Scripts/python.exe -m backend.evaluation.cost_report --usage saved-v0-usage.json --usage saved-v3-usage.json --snapshot saved-oracle-snapshot --prices prices.json --bills normalized-bills.json --annotations historical-annotations.json --output cost-report.json
```

`--usage` and `--snapshot` are repeatable; either one alone suffices. `--bills` and
`--annotations` are optional. All inputs are local, and original files remain unchanged.
The report is independent of quality scores and does not launch any model/API call.
Native snapshots must pass the existing raw/plan/attempt hash replay before normalization.
Their collection is shown in the oracle namespace, without artificial version attribution.

A minimal illustrative price file (synthetic rates, not a current provider quotation):

```json
{"schema_version":"rtpeval_prices_1","currency":"USD","rows":[
  {"price_id":"fixture-model","source":"synthetic worked example","as_of":"2026-10-05",
   "valid_from":"2026-10-01","valid_until":"2026-11-01",
   "match":{"kind":"model","provider":"fixture","operation":"chat","model":"test"},
   "rates":{"input_tokens":"2","cached_input_tokens":"0.5","output_tokens":"4"},
   "per":"1000000"}
]}
```

For 1,000 input tokens including 400 cached, and 200 output tokens, this yields
`0.0022` USD. Reasoning tokens are part of output, not another charge. Missing cache
counts do not imply zero; a deliberate no-discount assumption needs a source-linked
annotation or explicit `unreported_cache_policy`, or the estimate stays unavailable.
Cache writes use their separate rate and partition input with reads. Reported nonzero
writes without a write rate keep costs unavailable. Each official price row must retain its
source/date/currency, billing unit and applicable context. Explicit proxy prices and SKU
scenarios must retain an `assumption`, rather than pretending unknown context is observed.

Normalize an existing invoice/export into rows according to its evidence:

```json
[
  {"bill_id":"invoice-line-1","scope":"event","currency":"USD","amount":"0.10",
   "source":"invoice.csv:1","usage_sha256":"<original usage file SHA-256>",
   "result_sha256":"<result hash from usage>","kind":"model","event_id":"<captured ID>"},
  {"bill_id":"resource-month","scope":"aggregate","currency":"KRW","amount":"12000",
   "source":"resource-month-export.csv:2"}
]
```

Those hash/ID placeholders must be replaced with genuine matching artifacts. A complete
run bill uses `scope: run`, artifact hashes and `complete: true` without kind/event ID.
Aggregate rows cannot bind events/runs, and no cross-currency conversion occurs.
Actual event charges override estimates; whole-run bills leave category/Repair allocation
unknown. Backing HTTP transport is not another model charge, and Repair is never added
to the run again. Missing costs remain null beside a partial observed subtotal.

The library seam is `build_cost_report(sources, prices, bills=..., annotations=...)`, where
each source has original `sha256` and `usage`. Annotation rows contain `usage_sha256`,
kind/event ID, `source`, `source_sha256`, `note` and `fields` (only missing billing context
or explicit cached-input assumptions). Import does not fetch cloud bills or query billing
warehouses. Do not attribute aggregate exports to individual runs without supporting data.

Relevant regression tests live in `backend/tests/evaluation/`
and the [blind-review frontend](../../frontend/src/features/blind-review/BlindReview.tsx).
Actual historical results are in [evaluation record index](../../docs/records/README.md)
and linked Issues. Synthetic checks do not establish real provider availability,
formal benchmark outcomes or a version freeze. Formal controlled-case construction/execution remains separately authorized.

## Mechanism reporting workflow

```powershell
.venv/Scripts/python.exe -m backend.evaluation.mechanism_cli prepare --manifest manifest.json --observations linked-observations.json --output mechanism-preparation.json
.venv/Scripts/python.exe -m backend.evaluation.mechanism_cli prepare --selection controlled-preparation.json --output controlled-mechanism-preparation.json
.venv/Scripts/python.exe -m backend.evaluation.mechanism_cli report mechanism-preparation.json --output mechanism-report.json
```

The two `prepare` examples are alternatives: an existing curated four-version manifest or
genuine saved Ticket 11 V3-only preparation. Optional observations may be omitted; missing
metadata is unavailable, not zero. Commands read local JSON without provider/model calls,
case replay or website checks. Reports retain internal mechanisms separately from independent
quality. Exit 2 identifies material corrections; valid missing observations remain in
successful processing.

Library seams: `prepare_sources`, `read_batch_sources` and `report_mechanism`.
The producer owns `backend.app.observability.mechanism_capture.capture_attempt`: wrap its
existing invocation, supply original input/run identity and the exact saved-result serializer,
and save the emitted envelope through a synchronous local sink. This capture is independent
of enabled tracing/usage; custom injected adapters lacking submission observations remain
partial. Sink/capacity/redaction failures preserve planning. See the
[wire contract](../../docs/contracts/0001-evaluation-artifacts.md#mechanism-executable-wire)
and [offline acceptance](../../docs/records/evaluation/2026-10-04-mechanism-report.md).

## Controlled V3 offline workflow

Run from the repository root with the existing Python environment. Commands emit JSON;
save artifacts as UTF-8 without BOM. Exit 0 means successful processing, including quality
FAIL/UNKNOWN outcomes; material/execution errors exit 2. Cases are supplied frozen
post-primary inputs, not ordinary planner captures automatically upgraded into runnable
cases. See the [case and review wire](../../docs/contracts/0001-evaluation-artifacts.md#controlled-executable-wire).
Use a dedicated offline process with an exclusive event loop and no other network work;
execute cases serially. The guard patches sockets and the loop clock. Do not embed this
executor in an active web-service event loop or run unrelated async tasks alongside it.

```text
python -m backend.evaluation.controlled_cli replay case.json
python -m backend.evaluation.controlled_cli prepare case.json execution.json requirements.json
python -m backend.evaluation.controlled_cli identity-references preparation.json
python -m backend.evaluation.controlled_cli identity-plan preparation.json
python -m backend.evaluation.controlled_cli identity preparation.json observations.json --prepare --model YOUR_JUDGMENT_MODEL
python -m backend.evaluation.controlled_cli identity preparation.json observations.json --model-result identity-model-result.json
python -m backend.evaluation.controlled_cli evidence-plan preparation.json identity.json --context context.json --route-reviews route-reviews.json --coordinates coordinates.json
python -m backend.evaluation.controlled_cli report case.json execution.json requirements.json expectations.json identity.json snapshot --context context.json --route-reviews route-reviews.json --coordinates coordinates.json --expected-plan plan.json --generated-at 2026-10-04T00:00:00Z
python -m backend.evaluation.controlled_cli batch controlled-batch.json --generated-at 2026-10-04T00:00:00Z
```

The evidence-plan command emits a route preparation containing `evidence_plan`; save that
plan separately for snapshot acquisition/verification. Collection remains the existing
injected-transport `acquire_snapshot` API and requires its own authorization if live.
The saved-snapshot replay and identity-evidence commands remain in `snapshot_cli`.
Use `identity-evidence DIRECTORY --historical` only to derive the original evidence wire
for historical policy replay. Current evidence keeps pagination metadata and uncertainty;
coordinate consumers select the derivation using the verified report's policy.
Independent identity observations, positive-count audit plan, schedule context, coordinates,
requirements and review material retain their existing schemas. No four-version manifest
is required for these controlled commands.

Both evidence preparation and reporting accept `--occupancy-reviews`. Reporting additionally
accepts `--correspondence-reviews` and `--factual-reviews` for separately linked human facts.
The raw Ticket 10 pair remains in `pair`; supplemental check outcomes remain in
`reviewed_checks`, with original scores/deltas untouched. A route fact may establish duration
compliance while a transfer commitment remains unknown; review occupancy through its own
source-backed channel rather than treating the route fact as a whole-itinerary PASS.

An expectations guard for an independently reviewed exact-one-visit requirement can be:

```json
{
  "goal_id": "one-visit-on-day",
  "basis": "explicit_requirement",
  "condition": {"kind": "daily_count", "date": "2026-09-26", "minimum": 1, "maximum": 1},
  "source": {"field": "additional_preferences", "quote": "Exactly one primary visit on this day."}
}
```

Place this in the reviewed expectations envelope's `guards` array and bind the envelope
to the emitted normalized `case_hash`. The quote must be present in that original request.
Such a guard is independent of the planner's interpreted requirements: a missed interpretation
can cause an internally adopted addition to be independently classified as regression.
Ordinary additions with supported new checks and preserved requirements are lawful changes.

Controlled batch manifests reference previously emitted reports with the standard relative
JSON artifact envelope (`path`, byte `sha256`, schema, media type and availability). Every
entry declares `case_id`, `role` and `expected_goal_ids`. Missing or invalid reports remain
unavailable inventory units. Counts describe submitted cases; no formal 32-case corpus,
live usage/cost measurement, version ranking or causal conclusion is produced.

<a id="planner-usage-capture-cli"></a>

### Selected-version usage capture CLI

Prepare without invoking providers (input must pass current-date admission):

```powershell
.venv/Scripts/python.exe -m backend.evaluation.tools.planner_usage_cli --version v1 --input-json original-input.json --runtime-config config/runtime.yaml --output-directory artifacts/usage-v1-preparation --group-id original-request --run-id v1-preparation
```

The directory must be new. Preparation saves exact input/configuration bytes,
`runtime-policy.json`, `price-basis.json` and `manifest.json`; it constructs no provider
runtime, requires no provider credentials and creates no result/usage file. Supply a new
output path for execution; a preparation directory cannot be reused.

Only after separate live approval, add `--execute` for one selected version and use its
actual selected run ID. Execution loads the repository `.env` by default; `--env-file`
selects another base file. V2/V3 can additionally load the approved local RAG environment
with `--rag-env-file .env.tripworld`. Existing process values take precedence over the
RAG file, which takes precedence over the base file; preparation loads neither file.
Query embedding requires `OPENAI_API_KEY` and the
existing compatible TripWorld database. The command uses existing runtime budgets,
version-specific runners and dependency cleanup. `--execute` records operator intent;
policy authorization and account invoice limits remain separate.

Successful execution saves `result.json`, `usage.json`, `provenance.json`,
`usage-summary.json`, `prices.json` and `cost-report.json`. Failures/cancellations retain
saved usage, partial costs and `failure.json` with exception type rather than message.
Known cancellation remains `cancelled` through capture and native completion; missing
usage capture is separately identified without inventing a canonical receipt.
The [usage capture policy](../../docs/contracts/0002-intake-identity-usage.md#selected-version-usage-preparation-and-capture)
defines cancellation, interrupt/deadline handling and saved observation fallback.
Exit 0 means preparation or this selected invocation completed; exit 1 means
capture/execution was unsuccessful.
Invalid input, configuration or output conflicts raise an error before provider dispatch.
Windows result writes use exact UTF-8 bytes to keep hashes consistent with capture.

The frozen price basis was checked on 2026-10-08 using
[OpenAI GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[query embedding](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[Web Search](https://developers.openai.com/api/docs/pricing) and
[Google global pricing](https://developers.google.com/maps/billing-and-pricing/pricing).
Foundry model/tool prices use the declared OpenAI proxy; Standard processing and no
account discounts/free quota/tax are assumptions. Generated rows bind observed event IDs,
model names, request masks/modes, billing units and acquisition day, retaining the
reference check date. Refresh official references before relying on an older price basis.
Unknown model identities, unsupported masks/modes, missing quantities and uncertain sends
remain unpriced. Account invoices can later be imported through the offline cost command.

Missing cached reads assume no discount only under the explicit conservative policy;
missing writes price all non-read input at the write rate. Those assumptions appear in
the pricing result, preserving usage missingness. Actual cache-hit events do not create
another API charge, Matrix uses requested elements, model transport stays a backing
observation and Repair stays a subset. Independent oracle snapshots/costs remain separate
shared runs.

Synthetic CLI tests check three sends, two Web Search tool calls, one cache reuse, six
Matrix elements and reported model read/write partitions: the retail example totals
USD 0.0821715. This is fixture arithmetic. Complete cost remains unavailable for
unverified injected adapters. Qualified four-version attestation retains its separate
producer flow; this command performs no independent evaluator requests.

Add `--capture-evidence` to prepare or capture selected-version generation evidence:

```powershell
uv run rtpeval generate --version v2 --input-json original-input.json --runtime-config config/runtime.yaml --rag-env-file .env.tripworld --output-directory artifacts/generation-v2-preparation --group-id original-request --run-id v2-preparation --capture-evidence --opportunity-capture artifacts/generation-v2-preparation/candidate-opportunities.json
```

This command remains offline and saves no candidate observations. After exact live approval,
use a different, unused output directory, a fresh sidecar path and the approved run ID,
then add `--execute`. The existing selected planner runs
once, with mechanism capture, RAW local trace, credential-filtered owned HTTP request/response
representations and query-vector capture. SDK stream bodies are observed during normal
consumption, including decoded gzip; raw HTML retains existing read limits. Nothing drains
an unread response or adds a provider call. Bodies above 10 MB, unsupported content,
interrupted streams, trace truncation and capture-write failures remain explicit missingness.

Inspect `mechanism.json`, `evidence-index.json`, `evidence/wire/`, `evidence/trace/` and any
`evidence/vectors/` NPZ files alongside result, usage, provenance and cost artifacts. The index
binds exact file hashes and original usage event IDs; provenance binds the index and mechanism.
Its artifact inventory excludes manifest, provenance and itself to avoid hash cycles.
Observed-body hashes describe the declared raw/decoded form; saved JSON is credential-filtered
and may be normalized rather than byte-identical to private provider content. Numeric cache
usage remains available. Query-vector metadata retains text hashes, not raw query text.

Exit 0 indicates invocation completion, even when optional evidence is partial. A missing
usage file exits 1 while retaining any original result and evidence index. Check collection
status and missing fields separately before the next stage. Failure/cancellation retains
observations without an adopted result. Ordinary planner budgets, prompts and V0-V3 behavior
are unchanged. See the [evidence contract](../../docs/contracts/0002-intake-identity-usage.md#planner-generation-evidence).
