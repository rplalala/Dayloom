# Evaluation artifacts, scope and time

Current shared contract for native evaluation and source-bound suite orchestration.
[PROJECT.md](../../PROJECT.md) owns scope; [evaluation architecture](../0006-independent-evaluation.md)
owns implemented/deferred boundaries. GitHub owns task state. This reference states current
rules together; dated proposals, approvals and validation remain in linked history.

<a id="rtpeval-spec"></a>
## Batch ownership and reader separation

The final-quality workflow consumes an explicitly selected, producer-attested batch of
four-version groups.
It does not select cases, rerun planners, recompute workflow completion or improve the source
itineraries. The isolated Ticket 11 controlled V3 replay has the execution boundary
below; it does not require invented V0-V2 outputs. A qualifying group means workflow completion
was established upstream, not that
its itinerary is factually correct. Failed construction attempts stay upstream.

Quality readers use original Input, reviewed RequirementSpec, projected itinerary claims,
independent identity/evidence and versioned rules. Planner requirements, candidate ledgers,
RAG origins, internal validation, Repair findings and cache contents do not decide independent
quality. Mechanism readers have a separate channel. Human reviewers see anonymous original
request/itinerary material; RequirementSpec, automatic scores and private mappings are hidden.

The request/group is the comparison unit; visits, obligations and legs are nested observations.
Formal selection, sampling, cross-request inference and research conclusions remain separately
authorized work. Shared normalized DTOs do not make planner decisions independent evidence.

## Material integrity and source identity

`rtpeval_batch_1` contains `batch_id`, `revision`, `created_at`, `qualification_policy_ref`,
ordered `selected_group_ids` and `groups`. Each group has `group_id`,
`completion_attested=true`, `input_ref`, `requirement_spec_ref` and `selected_runs` with exactly
four entries keyed by v0-v3. Every run has a globally unique `run_id`, `result_ref`, `usage_ref` and required
`provenance_ref`. Optional files are explicitly referenced, never guessed from filenames.

Artifact references carry a relative path, exact-byte SHA-256, media type and availability;
schema version is declared where the envelope defines it. A result identifies its own
system version and itinerary output version, rather than an invented result schema name.
Paths resolve within the batch root, including link/junction resolution. Duplicate JSON keys,
escaping paths, duplicate IDs, missing required material and wrong linkage require whole-batch
correction; no convenient smaller cohort is silently scored.

The complete original input hash includes preference text; `structured_hash` is insufficient.
Each `rtpeval_provenance_1` sidecar binds `group_id`, `run_id`, `version`, `input_sha256` and
`result_sha256`. These must match the selected group and exact saved bytes. Configuration and
source revision metadata retain missing values; filenames do not supply provenance.

Sources are identified by batch/group/run, artifact-byte hash and JSON pointer. Derived IDs
also bind the projection contract. Original array positions, raw values and timestamps stay
intact; sorted views do not rewrite pointers. Activity IDs are itinerary-scoped, not global
identities or proof of cross-Repair correspondence. Source changes require relinking/replay.

Original result bytes are immutable. Canonical object digests, exact-file hashes and generated
report hashes have distinct domains. Hashes establish supplied-material linkage/integrity,
not cryptographic authorship, provider authenticity or factual correctness. Preserve trusted
plan/manifest hashes when operational provenance requires them. Secrets are excluded.

Intake recognizes `planning_request_2`, `itinerary_1` and `itinerary_2`, recording historical
absence of an output version. Fatal structure failures prevent stable inventory; representable
quality issues stay diagnostic. Current live-request date limits do not reject historical
submitted inputs. Missing optional V3 draft/final-primary projections disable dependent paired
work only; they are not reconstructed. Usage may explicitly be unavailable, rather than zero.
Exact parsing/projection wire is owned by [intake](0002-intake-identity-usage.md#rtpeval-intake-projection-contract).

## Paired evidence acquisition

`rtpeval pair acquire prepare/execute/replay/export` is an explicit producer for
the [same-run V3 diagnostic](0005-quality-human-review.md#v3-pairs). It uses native
paired plans, deterministic API identity, route preparation, independent Google
transport, pricing and scorers. It does not dispatch review agents or add a second
evaluator. The [operational guide](../guides/experiments.md#v3-paired-diagnostics)
owns commands and examples.

`rtpeval_pair_selection_1` identifies the batch/revision and every selected
group's V3 run, original input, reviewed RequirementSpec and original result hashes,
in manifest group order, with fixed `/v3/draft` and `/v3/final_primary` pointers.
The original selected bytes remain authoritative. Native missing/invalid optional
stages retain `pair_unavailable`, diagnostics and null deltas; they are never
reconstructed. With no available pair, processing sends nothing and needs no
fictional snapshot.

Preparation requires explicit independent schedule context and route reviews for
available pairs. Nonempty preferences additionally require a density review, which
may preserve unresolved meaning. Optional occupancy/correspondence reviews retain
their existing semantics. Acquisition limits are a positive integer
`max_google_sends`, a positive decimal-string `max_cost_usd` in USD, and finite
positive per-call and total timeouts. Offline imported phases permit explicit zero
send/spend limits. Credentials/model settings are forbidden in these options.
The price snapshot must support the native Google request identities and execution
date. Human preference and personal-intent clarification remain external work.

`rtpeval_pair_acquisition_preparation_1` retains compatibility identity policy 4.
Explicit `--subject-primary-run` selects preparation 2, identity policy 6 and
subject policy 2. Its completed preparation-3 Primary must have the exact native
intake, including original inputs, reviewed RequirementSpecs and selected outputs.
Closed provider receipts and the original subject packet/model HTTP capture are
validated without rebuilding Primary quality scores. Only the common target
observations and their original judgment are reused, with unchanged IDs and bytes;
paired visit evidence and stage associations remain independent. The source inventory,
policies and subject material are frozen and copied into `material/subjects`.
Missing, foreign, conflicting or stale material is rejected; there is no fresh
subject-model fallback or automatic policy upgrade for legacy preparations.

Both preparation versions freeze exact original source and
implementation hashes, closed copied material inventory, selection, intake,
reviews, limits, prices and native `paired=True` identity/evidence plans under a
canonical `content_sha256`. Identity requests are exact before execution.
Without a verified saved identity snapshot, canonical venue coordinates and
evidence requests are not yet known: `evidence_status=deferred_until_identity`
retains native occurrence/leg inventory, a null exact evidence request count and
an occurrence-based request/cost upper bound. No guessed place or route query is
sent. After identity acquisition, native route preparation persists the exact
paired evidence plan. Saved identity evidence permits an exact plan at prepare time.

Execution requires approval of that exact preparation digest. Original sources,
implementation, copied material, reviews, prices and plans are checked before
credential access or sends. Only missing phases read an independent Google
credential and construct a client. Native cumulative send/reference-spend ceilings
apply across both phases; per-call and overall deadlines constrain acquisition.
Each native request gets at most one attempt. A started directory is consumed,
including stopped work, with no retry/resume, Planner regeneration or Repair.
The native required primary/draft/final union retains source occurrences and
directed route mode/departure context while deduplicating exact requests. Evidence
reuse of a complete acquired snapshot requires the exact current native paired plan,
source/context/date and coverage. Final-only snapshots cannot be relabeled as paired
acquisition. Per-request reuse uses the explicit import contract below.

### Source-labelled offline imports

`pair acquire import` builds fresh `rtpeval_imported_snapshot_1` identity and
evidence snapshots for the accepted batch and reviewed paired context. It sends
no requests. Primary sources must replay successfully and retain closed execution
receipts. The explicitly selected `--subject-primary-run` instead validates its closed
provider facts and original subject-model receipt without rebuilding Primary quality;
the exact source-bound common targets remain separate from imported observations.
Use the same flag again when preparing the paired acquisition from those snapshots.
Saved generation sources must bind the selected V3 run, original input,
result, usage, provenance, runtime configuration and hashed evidence index.
When native finalization qualifies a producer declaration, the import retains its
exact bytes and selected hash alongside the generation's original provenance.
The declaration's explicit `native_provenance_ref` must bind those original bytes;
the original fields must agree, except qualification actor/time/rationale metadata.
This explicit lineage replaces direct hash equality between the two different
artifacts; missing, changed or contradictory links remain material errors.
Raw filtered request/response bodies must be complete. Partial captures can supply
only individually supported observations; source drift requires material correction.

Native primary requests match their complete semantics and verified Google wire.
Route endpoint evidence digests retain their own validated coordinate lineage;
an import changes these digests without changing the query. Matching still requires
the same directed place IDs, coordinates, mode, departure/time basis and options.
Generation requests match provider operation, method, endpoint, full request body
and required fields. Details can omit `addressComponents` because claimed-ID
assessment supports exact names and formatted addresses; absence cannot supply
address-component judgments. Searches retain the full native mask and scope.
Details accept the producer's explicit `languageCode=en` alongside the native
unspecified locale: the English name/address assessment and stable ID, coordinate,
business-status and hours fields remain independently checked. The full original
URL and language are recorded; other locales and additional query parameters do
not match. No search or route locale is silently changed.
Routes retain directed coordinates, mode, routing options and explicit departure.
Aware departure timestamps match by instant, including equivalent `Z` and offset
spellings, while original request bytes remain unchanged. Generation matrices
without an explicit departure are unsupported. Batch matrix
responses are not sliced into invented single-request observations.

The import preserves original bytes, paths through a flat copy map, hashes and
acquisition origin. Primary observations retain per-request UTC times. Generation
observations retain their recorded run capture interval, explicitly labelled
`run_capture_window`; its upper bound is not claimed as a measured per-request time.
`imported_at` records the new import operation. A separate import receipt closes
all copied bytes. Missing/incompatible observations have empty attempts and
`no_compatible_observation`, independently of acquisition budget exhaustion.

Imported identity evidence declares `reused_google_places` with import provenance,
rather than fresh acquisition. Native identity, opening, schedule and route checks
run again; Planner validation and Repair judgments are never adopted. The paired
report exposes source origins and inherited usage. Current send/matrix ledgers are
zero; inherited source usage is informational and is not added to current costs.
The snapshot cost reader emits no new provider events for imports and retains
inherited usage separately; the original source remains the accounting authority.
Preparing with imported evidence requires both phases and selects `offline_reuse`;
execution cannot fall back to paid acquisition. Unsupported facts remain UNKNOWN.
Any supplemental acquisition needs its own concrete approved scope and allowance.

The execution bundle saves paired snapshots, original request context and times,
redacted captured bodies, native failures/hashes, current identity, route plan,
edit lineage, pair report, journal inventory, oracle usage and a closed receipt.
`rtpeval_pair_acquisition_report_1` separates processing/acquisition/evidence status:
completed processing may contain partial provider evidence or FAIL/UNKNOWN units.
Cancelled, interrupted, timeout and budget-stopped attempts retain observed sends
and partial records without claiming a completed pair. If interruption occurs
after HTTP persistence but before snapshot consumption, closeout copies only
observed response bytes into partial raw storage without completing the snapshot.
Reference cost reservations,
measured request counts and estimated costs are distinct from actual account billing;
cached phases retain their prior capture provenance without counting inherited sends
as current usage. No model or supplemental opening judgment is dispatched.

Offline replay checks original/code/material bindings, the complete receipt,
HTTP/native snapshot correspondence, request context, usage and budgets, then
rebuilds current identity, exact route plan, native edit lineage and pair diagnostics.
Stopped attempts verify retained HTTP/partial snapshot responses and their inventory;
they do not become complete.
Fresh export verifies completed processing first, copies original bytes and evidence,
and writes `rtpeval_pair_acquisition_export_1` handoff plus a closed root receipt.
Its `research_pair` descriptor and `suite_pair` paths target existing opt-in
consumers; the matching research census/profile remains separately supplied.
Export preserves the report's mask, signed final-minus-draft deltas and
correspondence uncertainty without changing four-final arithmetic.

## Source-bound suite lifecycle

`rtpeval_suite_1` declares a nonempty ordered `cases` array, `suite_id` and an
explicit positive decimal `max_cost_usd`. Each case supplies a unique `case_id`, the
accepted native `revision`, and relative `manifest`, `options` and `prices` paths.
Optional `context`, `occupancy_reviews`, `route_reviews` and `density_reviews` retain
native schemas. Paths resolve within the declaration root, including junction/link
resolution. Each manifest must qualify exactly one four-version request group;
selected native batch/revision/group identities and all selected run IDs are unique
across the suite. Selection has no fixed case count and never scans for replacements.

Offline `prepare` validates the complete selection and supplied track material before
provider work. The sum of native per-case reference-price reservations must fit the
whole-suite allowance; native request, token and duration ceilings still apply.
`rtpeval_suite_preparation_1` binds exact source bytes, accepted native preparations,
ordered case identities, limits, prices, track configuration and implementation hashes.
A fresh output directory owns `cases/NNNN/primary/` and frozen `tracks/` artifacts.
Native source/result originals remain immutable. The returned preparation digest is
an integrity selector; operational live authorization is separate.

Explicit `execute` verifies the exact supplied digest, source and implementation
bindings again, then consumes cases sequentially through native execution. A started
suite cannot be retried or resumed. A primary stop or integrity failure stops new
provider work and retains attempted output; later cases remain `unstarted`. Cooperative
cancellation closes the attempted native receipt and the stopped suite index. An invalid
frozen track retains its material-correction diagnostic without preventing the primary
stop index from being saved; it cannot establish successful complete replay. A stop
before native execution has `not_started` acquisition and no native report pointer. A new
attempt requires another fresh directory and explicitly declared selection. Completed
processing can retain factual FAIL/UNKNOWN and optional unavailable tracks.

`rtpeval_suite_report_1` indexes the ordered cases and separate tracks. Each track
retains processing, evidence availability, applicability, reasons and native artifact
pointers; acquisition state remains separate for primary work. Descriptive or study
coverage cannot replace primary status or alter native scores. `summary.json` and
`receipt.json` close the execution inventory; later `reports/NNNN/` revisions have
independent receipts and preserve the earlier closed bytes. Replay verifies original
sources, closed inventories and native saved evidence without credentials or sends.
A stopped or incomplete native evaluation cannot become a successful full replay.

Saved mechanism reporting is enabled per selected case by default. Optional
`tracks.mechanism.observations` names a declaration-relative JSON envelope whose
`records` array contains native linked observations. Preparation validates supplied
observation linkage and freezes native `tracks/NNNN/mechanism_preparation.json` and
`mechanism.json`. Missing observations remain explicit; readers do not reconstruct
traces from finals or execute planning. Native descriptive material status remains
independent of accepted primary qualification and quality. Exact artifact bytes and
all supplied source bytes participate in suite integrity and offline replay.

The [installed suite guide](../guides/experiments.md#evaluate-multiple-cases)
owns command usage; [selection and resource scope](0002-intake-identity-usage.md#suite-selection-and-generation-resources)
owns selected generation data. Native scoring, paired diagnostics, human answers and
controlled cases keep their existing topic contracts.

### Existing study attachments and refresh

Suite-level `tracks.human` and `tracks.controlled_repair` are explicit attachment
arrays. Each report reference declares a relative `path`, exact-byte `sha256` and
native `schema_version`; dependencies use the same source-bound reference form.
Missing studies stay visible independently of primary quality.

| Track | Native dependencies | Declared source context |
| --- | --- | --- |
| `human` | `rtpeval_human_report_1` report, public `presentation`, private `mapping`, and `answers` references | One selected `case_ids` entry per native package, its `rater_ref` and the exact private preparation `source_hashes` |
| `controlled_repair` | `rtpeval_controlled_batch_report_1` report and `rtpeval_controlled_batch_1` manifest with its referenced existing reports | Separate `population_id`, `batch_id`, `revision` and ordered `cases` with native case ID, role, `expected_goal_ids`, preparation/expectations references and their canonical digests |

Human verification rebuilds the native report from presentation, mapping and all
answer revisions, preserving the effective revisions and source hashes. Controlled
verification rebuilds the batch from saved reports and verifies each case's declared
preparation/expectations context. Its population and goal denominators remain separate
from primary requests. Explicit unavailable native report inventory remains unavailable;
foreign, stale or corrupt supplied reports require material correction. Attachments
never collect answers, execute controlled cases, invoke Repair or rescore primary work.

`rtpeval_suite_attachments_1` contains the existing `suite_id` and a `tracks` object.
Offline `report --attachments` preflights the entire supplied refresh before creating
a revision. Supplied human/controlled lists replace their previous attachment selection;
omitted study tracks inherit the prior summary. Research selection and inheritance follow
the wire below. A revision freezes original attachment/dependency
bytes, attachment declaration and independently closed summary lineage under
`reports/NNNN/`, including its parent summary hash. Earlier execution/summary receipts
remain unchanged. Replay verifies every revision's closed inventory and deterministic
native study reconstruction, follows parent lineage and returns the latest summary.

### Optional research attachment wire

Initial `rtpeval_suite_1.tracks.research` and refreshed
`rtpeval_suite_attachments_1.tracks.research` use the same explicit object:

| Field | Required value |
| --- | --- |
| `schema_version` | `rtpeval_suite_research_1` |
| `declaration_ref` | Available exact-byte artifact reference to `rtpeval_research_declaration_1`, relative to the outer suite/attachment declaration |
| `selected_tracks` | Nonempty distinct list selected from `population`, `opportunities`, `relevance`, `repair`, `tradeoffs` |

The object has exactly these fields. The referenced declaration and every consumed
dependency must remain within the outer source root; its own references resolve relative
to its directory. Each selected track loads a fresh research context and uses its existing
standalone builder. Selection order does not change per-track semantics or source digests.
Only selected material is consumed. Valid missing optional material remains unavailable
or partial; structurally supplied, foreign, stale or escaped material requires correction
before output creation. The [research declaration](#original-input-research-declarations-and-attempt-census)
owns population/profile/census validation. Its planned inventory is independent of native
quality `cases`, including failed, cancelled, unstarted and unknown generation slots.

`summary.json.tracks.research` exposes `rtpeval_suite_research_index_1` and an exact-byte
`index` reference. The saved index carries population/profile identities and digests,
census reference, unique-request/planned-slot counts, selected track names, per-track
measurement/review coverage, diagnostics, applicability, source bindings and their union
`source_digest`. Its `semantic_sha256` digests the saved index excluding that field; the
summary preserves this digest while locating its artifact references within the suite.
Each selected entry in `tracks` retains its native research schema, processing/applicability,
coverage, population/source/semantic digests, diagnostics, JSON/Markdown exact-byte
references and `source_dependencies`. Unselected entries are `not_requested` with
`track_not_selected`. Complete report processing does not assert complete measurements.

Initial output stores `tracks/research/index.json`, `tracks/research/reports/<track>.json`
and `.md`, and the exact consumed source union under `tracks/research/sources/`. The union
includes native snapshot raw responses and preserves original relative layouts and bytes.
Markdown references resolve from each output location to the frozen sources. Initial
original-source checks remain part of the accepted suite lifecycle. Source drift during
execution stops new native work and records `primary_report.research_material_correction`
for the affected frozen dependency paths; only consuming research tracks and their links
lose availability. Restoring original sources preserves the recorded stopped outcome.

Offline refresh writes fresh index/reports under `reports/NNNN/tracks/research/` and frozen
dependencies under that revision's `sources/`, alongside the attachment declaration,
configuration, summary, parent-summary lineage and closed receipt. A supplied research
object replaces the previous selection. Omitted research rebuilds fresh report artifacts
from the prior frozen sources and selection; its semantic content remains unchanged.
Every refresh is preflighted before creating a revision. Report/replay verify initial
research composition, all closed inventories, exact artifact bytes, parent hashes and
deterministic source-bound reconstruction of every appended research report. Rehashing
corrupt report/summary metadata cannot substitute for reconstruction. Primary evidence,
native scores and earlier closed bytes retain the existing lifecycle.

`benefit_resource_links` retains three rows per planned case revision/repetition:
`rag_v2_minus_v1`, `repair_v3_minus_v2_finals`, and `repair_same_run_v3`. Each row identifies
selected primary attempts with version, attempt/run/group identities, input/configuration
hashes and supplied result/usage/provenance hashes. Report pointers bind population, source
and semantic digests. Linkage checks selected attempts and exact usage hashes against
independently rebuilt resource rows, rather than joining by case ID alone. RAG links use
reviewed relevance when selected, otherwise observed opportunity comparisons. Repair
links retain separate four-final and same-run native views. The same-run resource view
binds one selected V3 invocation; its draft never supplies an independent V2 measurement.
Retries remain in all-attempt consumption and cannot replace selected primary resources.

`status`, `benefit_status`, `resource_status`, `source_compatible` and `reasons` retain
unmatched or partial rows. Source compatibility is independent of measurement availability.
`resource_measurement_coverage` states known/missing selected-attempt counts per native
usage metric and observed-subtotal counts. Monetary coverage retains observed/missing
attempt counts and, separately for native `actual`, `estimated` and `best_available`,
known/missing total and observed-subtotal counts. A legitimate observed zero is known;
an observed subtotal does not establish a complete total. Known
elapsed time, calls, HTTP sends or cost remain visible when tokens are missing; absent
metrics are not zero. A `matched` usage link has complete declared usage metrics; optional
cost coverage remains explicit and does not create a monetary estimate. The resource
report owns literal values, timing/currency/billing scope and missing-value semantics
defined in [generation resources](0002-intake-identity-usage.md#generation-research-tradeoffs).
Controlled target inventory remains a separate population: `controlled_resource_link` is
`not_applicable` with `controlled_simulation_is_a_separate_population`. These are descriptive
source-compatible links, without a combined score, ranking or causal interpretation.
The [installed suite guide](../guides/experiments.md#evaluate-multiple-cases)
owns operator commands.

## Original-input research declarations and attempt census

The offline `rtpeval research validate/report` boundary consumes one explicit
`rtpeval_research_declaration_1`, rooted at its parent directory. It binds
`population_ref`, `profile_ref`, optional `census_ref`, and optional `track_refs`
for separately selected research tracks. References use the existing available
artifact wire: relative `path`, exact-byte `sha256`, `media_type`, and
`schema_version` for versioned JSON envelopes. Resolved links and junctions must
remain inside the declaration root. Configuration artifacts may bind JSON or
exact non-JSON bytes such as YAML. No directory discovery occurs.

`rtpeval_research_population_1` has `population_id`, `revision`, and ordered
nonempty `cases`. Each case has a unique `case_id`, case `revision`, original
`input_ref`, explicit `metadata`, ordered unique `planned_versions`, and ordered
unique `repetition_ids`. Metadata may be empty; it does not infer research strata.
Slots are the case-local product of repetitions and declared V0-V3 versions;
case identity remains distinct from repetition identity. Population size is arbitrary.
An unrepeated twenty-case four-version inventory has eighty planned slots without
requiring results, reviewed requirements, or qualified quality groups.

`rtpeval_research_profile_1` declares the following fixed selection contract:

| Field | Meaning |
| --- | --- |
| `profile_id`, `revision`, `source_revision` | Selection identity, revision, and declared implementation/source context |
| `population_id`, `population_revision` | Exact inventory revision |
| `declared_at`, `timing_basis` | Timezone-aware declaration time and `prospective`, `retrospective`, or `unverified` timing |
| `first_attempt_rule` | Required `first_dispatched`; planner dispatch is distinct from HTTP sends or evaluator execution |
| `retry_rule` | Explicit `selection=none` or `last_dispatched`, with `scope=slot`; any retry-policy result is separate from the primary attempt |
| `completion_policy_ref`, `completion_mapping` | Native producer policy and explicit native-status normalization, defined in [completion semantics](0002-intake-identity-usage.md#research-completion-and-selection) |
| `configurations` | Exact configuration artifact references keyed by every declared version |
| `previous_profile_ref` | Optional exact reference to the preceding profile revision |

Prospective declaration time cannot follow any recorded dispatch. Retrospective
and unverified timing remain visible. Changed profiles use new linked revisions;
when history is supplied, its profile/population identities, distinct revisions,
ordered declaration times, schema, and bytes are verified. Hashes preserve supplied
history; they do not independently prove when a declaration was made.

`rtpeval_research_census_1` binds `population_id`, `population_revision`,
`profile_id`, `profile_revision`, and an explicit `attempts` array. Missing census
or missing slot records means unknown availability, rather than unstarted or failed.
Every supplied record binds the following:

- Slot fields `case_id`, `case_revision`, `version`, and `repetition_id`.
- Globally unique `attempt_id` and `run_id`; positive contiguous per-slot `order`
  starting at one; explicit `prior_attempt_id=null` for the first record and the
  immediate predecessor for subsequent records. Per-slot array order and dispatch
  timestamps must agree.
- `dispatched` and timezone-aware `dispatched_at`, with null timestamp when false;
  exact `input_sha256` and `configuration_sha256`; `reason_type`; and explicit
  `execution_metadata` for observed cache, concurrency, invocation order, and
  other execution conditions. An empty metadata object means these conditions
  were not supplied, rather than equal or controlled.
- Optional `completion_ref`, `result_ref`, `usage_ref`, and `provenance_ref`.
  Absence remains unavailable. Supplied JSON is strictly parsed and its exact
  bytes/schema are checked. Native usage/provenance require `group_id` on the
  record and match group/run/version/result bindings. Provenance additionally
  matches the original input; generation usage requires explicit planner namespace.
  Result `system_version` must match the slot. Any supplied extra native input or
  configuration hash must also match.

Failed, clarified, cancelled, or pending records need no adopted result. Supplied
producer completion carries `declared_by`, timezone-aware `declared_at`,
`policy_ref`, `workflow_status`, and a typed `required_mechanisms` object including
generation. It cannot precede dispatch. Optional `producer_policy_ref` must agree.
Result existence, quality PASS, and accepted Repair are never completion evidence.
A non-dispatch record can declare unstarted or unknown/pending; terminal generation
outcomes require dispatch. The first dispatched record is selected even if an
unstarted record precedes it. Further dispatches are explicit retries.

### Installed census export and dispatch observations

`rtpeval research export-census INVENTORY --directory FRESH_DIRECTORY` produces
the existing census and declaration wires from one `rtpeval_research_census_export_1`
inventory. The inventory's parent is its source root. It supplies exact
`population_ref`, `profile_ref`, and an explicit ordered `attempt_sources` array;
there is no directory discovery, latest-result selection or implicit retry.

Each entry supplies `case_id`, `case_revision`, `version`, `repetition_id`,
`attempt_id`, `order`, `prior_attempt_id`, `group_id`, `run_id`, `reason_type`,
and `producer_metadata_ref`. Optional `completion_ref`, `result_ref`, `usage_ref`
and `provenance_ref` use the existing artifact wire. All attempts are retained.
The exporter derives dispatch observations and input/configuration hashes from
referenced metadata and checks them against the exact population/profile sources.
Entries must not separately override these observations. Slot order, predecessor
links, timestamps, native statuses and primary/retry selection use the existing reader.

`rtpeval_planner_dispatch_1` contains `source_kind=installed_generate` or
`historical_import`, nonempty `declared_by`, timezone-aware `recorded_at`,
`group_id`, `run_id`, `version`, `input_sha256`, `configuration_sha256`, explicit
`dispatched`, nullable `dispatched_at`, `planner_dispatches` and
`execution_metadata`. Dispatch count is zero or one for this single invocation,
agrees with `dispatched`, and is unrelated to provider HTTP sends or evaluator work.
An observed dispatch timestamp cannot follow `recorded_at`; a non-dispatch has no
dispatch timestamp. Conditions absent from `execution_metadata` remain unknown.

Historical import requires nonempty exact-byte `evidence_refs` identifying the
source of the operator's explicit observation. The declaration preserves its
author, time and evidence; it does not independently establish historical truth.
Missing dispatch metadata/time is a material-correction error. File modification
times, preparation/export timestamps and result existence cannot fill that gap.
Missing inventory entries retain unknown slots rather than creating non-dispatch
rows. Optional unavailable artifact references become null census references with
their reasons in export diagnostics; they do not acquire a result or receipt.

The bundle keeps copied originals byte-for-byte under `material/`, preserving their
source-root-relative layout, plus `census-export.json` and `research-export.json`.
Explicit nested completion/provenance dependencies are resolved from their owning
artifact, hash-checked and copied within the same bounded root; they do not trigger
run discovery. Nested references retain each logical directory layout, including
multiple root-bounded aliases of the same original; root and hash checks use resolved
source locations. Derived census refs use the canonical location of those native files.
Those two filenames are reserved at the material root. `export.json` and stdout
carry `rtpeval_research_census_export_report_1`: completion status, usable census
and declaration refs, source hashes, slot/attempt counts, missing/unavailable
diagnostics and metadata provenance. Source and provenance paths are relative to
its declared `source_root=material`. Originals are checked again before publication;
the existing population reader and report builder validate the pending bundle.
Failed validation does not publish the destination. Existing destinations, including
links with missing targets, are refused. Export completion does not qualify a quality
batch or indicate that a workflow succeeded.
After pending validation, the exporter creates the fresh destination, verifies each
copied file and revalidates the published declaration before writing `export.json`
last. A publication IO failure may leave an incomplete destination; absent or invalid
completion receipt means unvalidated export, and a retry requires a new destination.

Exported census records retain `producer_metadata_ref`. The common research reader
revalidates that metadata, its evidence hashes and its agreement with census fields.
Historical census records without this optional reference retain their existing
validation behavior. Exact original population/profile bytes and profile history
are preserved; track attachments are supplied separately after export.

The population report wire is `rtpeval_research_population_report_1`. It retains
ordered slots and all attempts, selection profile, case/version/repetition views,
all-four request/repetition rows, reasons, and distinct completion denominators.
Source bindings are declaration-root-relative, include the declaration's own byte
hash, and produce a deterministic `source_digest`; `population_digest` binds the
inventory's canonical content. `semantic_sha256` hashes the full report except
itself using sorted compact UTF-8 JSON with finite numbers. There is no generated
clock or output-directory value inside the semantic report.

`validate` returns JSON on stdout without writing artifacts. `report` requires
`--directory` naming a fresh directory and writes `population.json` and
`population.md`. Both require explicit `--track population`. Processing returns
zero on valid material and two with `needs_material_correction` on malformed,
foreign, stale, contradictory, or unsafe material; it never silently reports a
smaller cohort. Reports preserve sources byte-for-byte. This boundary reads saved
material only and does not qualify raw attempts for native quality intake, run
planners, acquire evidence, or select benchmark cases.

## Canonical candidate opportunity observations

`rtpeval research validate/report --track opportunities` produces
`rtpeval_research_opportunities_report_1` from the original-input declaration.
Every planned V1/V2 slot remains a row, including missing, failed and cancelled
attempts. The identity unit is a canonical Google Place ID. This observational
track does not decide relevance, verify quality or execute a historical planner.

The report envelope records processing status separately from track applicability:
no planned V1/V2 slots means `not_applicable`; missing historical captures for
planned slots remain applicable and unavailable. Profile IDs, population/source
digests, ordered rows and the semantic hash retain their source bindings.
`measurement_coverage` counts planned and captured V1/V2 slots and complete,
partial and unavailable slots for each discovery stage and independent scheduling.
`review_coverage` counts slots with independent final-place associations and marks
relevance review as not performed by this track. Top-level diagnostics retain
case/revision/version/repetition/attempt identity alongside each per-run conflict.

`track_refs.opportunities` references `rtpeval_research_opportunities_1` with an
explicit `observations` array. Each observation binds `case_id`, `case_revision`,
`version`, `repetition_id`, the census-selected first dispatched `attempt_id` and
`run_id`, exact `input_sha256` and `configuration_sha256`, and explicit nullable
`result_sha256`. `capture_ref` uses the common root-bounded byte reference contract.
Foreign, duplicate, retry-selected or stale bindings require material correction.

The saved `rtpeval_candidate_capture_1` binds `version` and `run_id`. Its `stages`
map contains `discovered`, `admitted`, `enriched` and `supplied`; a missing stage
stays unavailable. Each captured stage declares `status=complete|partial|unavailable`,
`places` and `reasons`. Each place retains `canonical_place_id`, native
`google_origins` (query/intent/raw rank/count) and `rag_origins` (entity, typed query,
rank, similarity, distance, artifact/text hashes, space, policy, resolution and
Google evidence reference). The exporter retains native query planning, omitted
queries, entity outcomes, limits and fates under `rag`. Omission rows bind canonical
place, stage and reason. Complete predecessor inventories cannot contradict later
memberships; neither an absent history nor a truncated capture establishes zero.

Reports deduplicate places within stages and union their native origins. They retain
Google-only, RAG-only and mixed partitions, observed counts and nullable complete
counts. Google used only to resolve a RAG identity is not Google discovery.
`pre_rag_google_ids` binds the same run's pre-extension Google inventory;
`incremental_rag_ids` and its completeness remain distinct from complete paired
V2-versus-V1 stage additions/losses under `cross_version`. Multiple entities, queries
and intents can remain evidence without adding venues to denominators.

Optional `identity_sources` binds an exact native `manifest_ref`, `evidence_ref`
and `mode=program|legacy`. The reader loads the native four-final intake, verifies
its selected input/run/result against the census, and recomputes identity offline.
Program mode may bind a saved `model_result_ref`; legacy replay requires its native
`audit_ref` and may bind `reviews_ref`. Projection reviews and all native source
files retain exact byte links. A self-declared identity digest or producer place ID
alone cannot establish scheduling. Only independently resolved native final
primary-visit associations count; Nearby references and generic activities do not.
Missing associations or unresolved roles keep scheduling partial. Producer supplied
or scheduled fate conflicts remain diagnostics. The capture's optional
`result_semantic_sha256`, when present, must match the saved selected final.

JSON and Markdown retain slot identities, completeness, canonical memberships,
reasons, exact source paths/hashes and deterministic digests without altering input
files. Source paths resolve under the research declaration's root. Fresh output
rules follow the [research declaration boundary](#original-input-research-declarations-and-attempt-census).
[Independent interest comparisons](#independent-interest-relevance-and-corpus-coverage)
consume original-input interest definitions, reviewed canonical relevance labels and
their source bindings alongside these inventories. Producer intent associations and
RAG origin do not supply those verdicts.

## Independent interest relevance and corpus coverage

`rtpeval research validate/report --track relevance` imports independent reviewed
material and produces `rtpeval_research_relevance_report_1`. It reuses selected
first-attempt opportunity rows and native independent scheduling. Material readers
verify exact bytes, case/source bindings and declared completeness; they do not
execute reviewers or corpus measurements. This view remains separate from primary
quality scoring.

The report envelope retains profile identity, population/source digests and a
semantic hash. `measurement_coverage` preserves the opportunity slot/stage census
and counts complete, partial and unavailable corpus observations per original
request. `review_coverage` separately counts source-bound interest inventories,
cases with saved relevance judgments and independent review records, without
counting version/repetition rows as additional requests. Source-bound opportunity
conflicts remain top-level diagnostics. No planned V1/V2 slots is not applicable;
missing independent interest material for planned slots remains unavailable.

`track_refs.relevance` references `rtpeval_research_relevance_1`, binding
`population_id`, `population_revision`, `profile_id` and `profile_revision`. Its
explicit `interest_inventory_refs`, `review_refs` and `coverage_refs` arrays may
be empty; optional `coverage_profile_ref` is a common root-bounded byte reference.
The subordinate materials are:

| Reference / schema | Required binding and contents |
| --- | --- |
| Interest inventory / `rtpeval_research_interests_1` | `case_id`, `case_revision`, `input_sha256`, independently reviewed `requirement_spec_ref`, review metadata and explicit `interests` |
| Labels / `rtpeval_research_relevance_reviews_1` | Explicit `records` with stable `review_id`, case/input/inventory/spec hashes, interest identity/pointer, venue subject/evidence and independent review metadata |
| Corpus sidecar / `rtpeval_research_corpus_coverage_1` | Case/input, pinned `snapshot_identity`, fixed `scope`/`scope_sha256`, measurement/declaration times, method and eligible count/completeness |
| Strata profile / `rtpeval_research_coverage_profile_1` | Stable `coverage_profile_id`/`revision`, population binding, snapshot, fixed case scopes, declaration timing, metric and ordered thresholds |
| Optional sample measure / `rtpeval_research_interest_coverage_1` | Case/input/scope/snapshot/inventory hashes, `taxonomy_ref`, `sample_ref`, `coding_review_ref`, literal numerator/denominator, method and uncertainty |

Every inventory and label retains `revision`, `reviewer_ref`,
`reviewer_kind=human|external_model`, timezone-aware `reviewed_at` and `rationale`.
An external-model record is saved independent review material; importing it invokes
no model. Each interest has a unique `interest_id`, original-input JSON
`source_pointer` and exact `source_text`, plus a `requirement_pointer` into the
reviewed RequirementSpec. The pointed requirement must carry the same stable
interest/preference/obligation identity. Missing inventories stay unavailable;
an explicit independently reviewed empty inventory is not applicable.

A label binds `input_sha256`, `interest_inventory_sha256`,
`requirement_spec_sha256`, `interest_id` and `source_pointer`. It declares exactly
one nonempty `canonical_place_id` or `unresolved_subject_id`, and a
`verdict=relevant|not_relevant|unknown`. Known verdicts require
`venue_evidence_refs`; each saved evidence object binds the same venue subject and
an independent Google Places, official or reviewed-description source kind.
Planner judgments, query links, rank and cosine are not review evidence. Duplicate
review identities, duplicate/contradictory interest-subject judgments, foreign
venues and stale source bindings require correction. Unresolved judgments retain
their reviewer/evidence trail without adding a canonical venue count.

Each discovered/admitted/enriched/supplied/scheduled row reports deduplicated
relevant `canonical_ids`, an observed lower count and nullable `complete_count`,
with native stage completeness and review reasons. Overall relevance is the union
across applicable interests; per-interest rows count an identity once. Review
coverage retains judged/inventoried subjects, their fraction, relevant/negative/
unknown/absent subjects, expected/supplied judgments and unknown/missing judgments.
Exact counts require a complete stage and known judgments for every applicable
interest-subject pair, even when one known positive already establishes the
observed union. An empty inventory denominator has no review-coverage fraction.

The principal `end_to_end` set is relevant AND admitted AND supplied AND
independently scheduled, overall and per interest. A final scheduled venue cannot
reconstruct missing admission or supply history. Selected completed V1/V2 pairs
with the same case/revision/repetition and reviewed inventory retain signed
V2-minus-V1 deltas and gained/lost/retained IDs only when the relevant chain is
complete. Other pairs retain nullable deltas and explicit omission reasons.
Conversions use the relevant intersection as numerator and the earlier stage's
relevant count as denominator, including admission-to-supply and
supply-to-scheduled. Incomplete stages/reviews and zero denominators have no exact
fraction; observed zero is not substituted for missing evidence.

A corpus `snapshot_identity` includes a byte-bound `snapshot_ref`,
`artifact_sha256`, `policy_version`, `space_id` and `identity_pointers` mapping each
identity field to its exact JSON pointer in the saved snapshot manifest. The
reader checks these values against the manifest and any selected RAG origin.
Scopes use `kind=radius` with latitude/longitude/positive `radius_m`, or
`kind=bounding_box` with south<north and west<east within coordinate bounds.
`scope_sha256` hashes canonical JSON. Profile and sidecar must retain identical
snapshot identities and exact case scopes; incompatible material fails validation.
The [retrieval contract](../0004-retrieval-persistence%28v2v3%29.md#pinned-corpus-coverage-sidecars)
explains the entity/geographic interpretation.

Sidecars retain `measurement_method`, `measured_at`, `declared_at`,
`timing_basis=prospective|retrospective|unverified`, `count_status`,
`eligible_entity_count`, `observed_subtotal` and `reasons`. Complete counts are
nonnegative integers with matching subtotals, including a valid zero. Partial or
unavailable counts have null eligible counts and explicit reasons, so timeouts,
truncation or unsuccessful retrieval cannot become exact zero coverage.

Optional reviewed interest coverage binds the same case/input/scope/snapshot and
interest inventory. `rtpeval_research_interest_taxonomy_1` lists unique applicable
`interest_ids`; `rtpeval_research_corpus_sample_1` lists unique `entity_ids`.
`rtpeval_research_corpus_coding_1` binds exact taxonomy/sample/inventory hashes,
independent reviewer metadata, independent `evidence_refs` covering the sampled
entities and disjoint `relevant_entity_ids`/`unknown_entity_ids` subsets. The
numerator equals reviewed relevant entities; the denominator equals sample size
and cannot exceed a complete eligible census. Unknown coding keeps the fraction
null and bounds [relevant/sample, (relevant+unknown)/sample]; a zero-size sample
has no fraction or bounds. Saved method and uncertainty remain in the output.

A strata profile declares `metric=eligible_entity_count|interest_coverage_fraction`
and ordered nonoverlapping `strata` with stable `stratum_id`, `min_inclusive` and
nullable final `max_exclusive`. Complete compatible coverage values select a
stratum; missing or partial measures retain continuous observations without an
exact assignment. Prospective declarations must precede the first selected
dispatch; absent dispatch evidence is labeled unverified. Retrospective timing
remains explicit, alongside the originally declared basis. No input replacement
or threshold fitting occurs during reporting.

JSON and Markdown retain exact case/repetition rows, stage memberships, reviewer
metadata, continuous coverage, fixed thresholds, source/semantic digests and
interpretation limits. Summary `available_pairs`/`omitted_pairs` count complete
principal comparisons overall; `unstratified_pairs` identifies pairs without an
exact coverage assignment. Each stratum separately reports its case IDs, available
and omitted pairs and descriptive principal-delta median. Repeated slots remain
visible and are not independent samples. Entity/geographic proxies and reviewed
sample fractions make no citywide recall, unique-venue coverage, ranking,
statistical-inference or causal-attribution claim.

### Pinned corpus measurement producer

`rtpeval research corpus prepare REQUEST --directory FRESH` accepts
`rtpeval_corpus_request_1`. Required fields are `declaration_ref`, `case_id`,
`case_revision`, `input_sha256`, `scope`, `scope_sha256`, `snapshot_identity`,
`declared_at`, `timing_basis`, `measurement_configuration` and `source`.
`coverage_profile_ref` is optional; when absent or null, an existing relevance
declaration's profile is retained and checked against the requested snapshot/scope.
The declaration shares the request's source root; references use that root.
Case/input, snapshot JSON pointers, canonical
scope hash, any supplied profile and selected RAG origins must agree. The request
can select one case from a larger population; other cases retain their own coverage.

Configuration supplies positive integer `max_entities`, `max_source_bytes`,
`statement_timeout_ms`, `connect_timeout_seconds` and `batch_size`, plus numeric
`timeout_seconds` in (0, 3600]. Batch size cannot exceed the entity scan limit.
Request metadata is limited to one MiB; each selected source and their combined
saved bytes obey `max_source_bytes` before dependency reading/parsing. Retained
observation bytes have the same bound. No geography, repetition, thresholds or
budgets are inferred.

`source.kind=saved_dataset` supplies `dataset_ref` and `embedding_index_ref`;
`source.kind=database` supplies neither. Optional `manifest_pointer` selects a
native manifest within the pinned snapshot; otherwise the snapshot is that
manifest. `output_sha256`, nonnegative `entity_count` and the established
`inputs` entity-builder/text versions are required. Saved dataset bytes must
match the pinned artifact hash and declared row count. JSON uses
`rtpeval_corpus_entities_1` with an `entities` array; Parquet uses native
`RetrievalEntity` columns. The exact `rtpeval_corpus_embedding_index_1` declares
`artifact_sha256`, production `space_id`, exact production `configuration` and
saved `text_hashes`. Presence is evaluated per entity text, including multiple
entities sharing one embedding or resolved venue. No vectors are generated.

Preparation writes `rtpeval_corpus_preparation_1` in `receipt.json` with
`processing_status=prepared`, `request_ref`, source bindings and zero database
connections. It produces no measurement. `corpus measure PREPARATION` validates
those saved request/source hashes again. Saved-data measurement remains offline;
database measurement additionally requires `--database --dsn-env NAME`. The
connection string is read only at that explicit operation and is never serialized.

Database defaults and the transaction are read-only. Build manifest/count,
embedding configuration, all-entity artifact/policy drift checks and bounded
server-cursor reads share a repeatable-read transaction and captured snapshot ID.
Connection and statement waits are bounded; each query uses the remaining overall
deadline, including the final scan-completion check. Rows use production eligibility
and compatible embedding membership, then the exact radius or bounding-box
inclusion rule. The configured row budget
covers all scanned entities, not only eligible entities in scope. No retrieval
top-k or venue-ID deduplication substitutes for a complete scan.

`rtpeval_corpus_measurement_1` preserves exact request binding, method,
start/finish times, verified source identity, entity observations and explicit
termination reason. Completed scans match the pinned entity count and have no
duplicate IDs. Scan/observation-byte caps, timeouts, truncated scans and retrieval
failures preserve a nullable exact count and any supported observed subtotal;
connection/identity failure cannot assert an observed exact zero. Invalid or
drifted source identity is a material correction, not accepted complete coverage.

Measurement writes the existing coverage sidecar plus an evidence artifact,
`rtpeval_corpus_result_1` receipt and derived relevance/declaration material.
`count_status` is distinct from operation `processing_status=completed`.
Existing coverage for other cases and externally supplied semantic material are
retained; the derived declaration carries only relevance and opportunities.
New artifact names avoid copied originals. Every output uses a fresh directory.

Produced sidecars include `producer_completion_ref` to
`rtpeval_corpus_completion_1`: `processing_status=completed`,
`measurement_ref` and canonical `coverage_sha256` of the sidecar excluding that
completion ref. Pending material is checked by the existing reader before
publication. Exact originals and derived files are copied and verified, the root
receipt is saved, and the final completion artifact is written last before final
reader validation. Its absence, corruption or disagreement invalidates the
produced sidecar even if a root receipt already exists. Legacy manually supplied
sidecars without this optional ref retain their current validation rules.

`corpus export MEASUREMENT --directory FRESH` is offline. It verifies exact
request/evidence/sidecar/completion references, replays saved observations against
retained dataset material or checked saved database identity, and validates the
exported relevance declaration. It neither reconnects nor changes saved times.
Original bytes, fixed thresholds and declaration timing stay unchanged; absent
dispatch evidence remains unverified. Root receipts expose sidecar, evidence,
completion and declaration references plus all copied source hashes. A failed
publication can retain incomplete files for diagnosis; reuse requires a new
destination. Engineering completion does not qualify a quality batch or produce
interest/sample judgments or a formal benchmark result.

## Activity, transport and occupancy scope

Each primary visit is one concrete place occurrence with its own interval. A confirmed
multi-POI block sharing an interval is a delivery diagnostic; do not split places or invent
times. Structural `main_poi`/`place_name` claims determine visit classification under the
intake rules; title patterns do not override declared visit/transport roles. Bounded
competing-claim metadata is separate from role classification. Unresolved named visits remain
visits with identity uncertainty. Generic locationless placeholders supply no invented venue.

Nearby is unscheduled and excluded from primary counts, required/excluded checks, opening
and main-route adjacency. Count visit occurrences separately from unique canonical identities.
An unresolved role remains visible as applicability uncertainty, not a deleted denominator.

Submitted transport authority is **V0 Activity; V1-V3 Transfer**, including optional V3 stages.
Ignored representations retain diagnostics/source records but provide no occupancy, mode,
time or fallback. Missing transfers stay missing. Same-source duplicates share one logical
journey; segments retain their intervals; conflicting claims stay alternatives. Independent
association does not certify identity, chronology or real route feasibility.

Route candidates join consecutive primary occurrences within each delivered day. Inter-day
travel is outside the product/evaluator scope. Independently confirmed same-canonical endpoints
are route N/A, not a measured zero-duration PASS. Different venues sharing an address are distinct.
Unknown intermediate roles retain uncertain adjacency. Sorting does not repair overlaps.

An explicitly uncommitted, locationless free-time slot can be travel slack. Fixed rest,
reservations and reviewed protected time cannot be consumed; unclear flexibility requires
independent review. Planner lineage cannot authorize that classification. Scoped protections
retain their original obligations and block applicable commitments without adding non-overlap
units. Detailed occupancy/counting is owned by
[requirements and schedule](0003-requirement-schedule.md#rtpeval-requirement-schedule-contract).

<a id="time"></a>

## Independent time and provider observations

Preserve timestamp strings and explicit offsets. Aware values identify instants; destination-
local rules require independently supported IANA context. Naive clocks are localized only
when the local interpretation is unique. Missing/conflicting zones, DST folds/gaps and
declared-day/offset inconsistencies keep dependent checks UNKNOWN. Host/browser timezones and
planner metadata are not substitutes. Consistent declared days can still support structural
date counts when precise instants are unavailable.

Intervals are half-open: touching endpoints do not overlap, and visit end equal to opening
close is allowed. Preserve microsecond timestamp precision; greater precision is unsupported
rather than truncated. Full-day protections use local midnight to next local midnight,
including 23/25-hour days. Ticket 06 permits explicit cross-date visit endpoints; no next-day
end is inferred. Duration comparisons use instants, not a fixed civil-day length.

Frozen snapshots retain original raw provider bytes, request parameters and ordered attempt/
collection times. Provider failure, explicit no-route/closed observations, incomplete evidence
and malformed material are distinct. Raw response replay precedes derived interpretation;
planner-rounded DTO values do not replace original precision or field-presence semantics.

Opening uses current request-local windows, regular weekly patterns and known/unknown spans;
any proven closure inside a visit is decisive FAIL, complete open containment is PASS, otherwise
UNKNOWN. Original explicit empty periods differ from missing/null/derived-empty values.
Route evidence keeps status, condition, direction, mode, departure and raw nanosecond duration.
An applicable successful no-route is FAIL with null duration; accepted traffic fallback remains
usable without silently switching endpoints, mode or date. The complete truth tables,
applicability and independent tolerances live in
[opening/routes](0004-opening-routes.md), rather than a second rule copy here.

## Report and track boundaries

Reports retain source/rule/preparation/review hashes, units, applicable populations, raw states,
coverage, reasons and null unavailable values. Material correction, UNKNOWN, N/A and a numeric
zero are distinct. Deterministic replay uses frozen inputs/rules; generation time is metadata.
Ticket 08's content hash excludes generation time and itself; CLI file hashes remain separate
from object digests. [Quality/human review](0005-quality-human-review.md) owns exact score,
mask and answer/report wire. Resources have a separate observed ledger and no implicit cost score.

Implemented outputs include intake, identity/adjudication, usage, snapshots, requirements/
schedule, opening, routes, final multimetric reports and anonymous human packages/import/reports.
Not every optional track is integrated into the quality report. Its availability metadata does
not manufacture resource/human/mechanism aggregation. Paired snapshot support in preparation/
individual scorers alone is distinct from the implemented Ticket 10 paired report.

<a id="planned"></a>

## Optional diagnostics and controlled studies

Ticket 10 retains independently evaluated V3 draft/final-primary under one compatible snapshot,
validated adopted-edit/activity/split provenance before content fallback and residual review,
and a paired common dimension mask. Unresolved local correspondence does not suppress an otherwise
valid paired aggregate. The offline reader/report/CLI is implemented; current behavior
is in the [paired contract](0005-quality-human-review.md#v3-pairs), with actual validation
and review corrections in [acceptance](../records/evaluation/v3-pair-report.md).

Ticket 11's accepted controlled composition is 24 targets plus 8 controls, with confirmed
evidence/policy conflicts distinguished from optional review opportunities. Independent target
outcomes include detection failures, residuals, regressions and control invariants; disappearance
of a planner target ID is insufficient. Cases/evidence/capability configuration must be frozen
for separately authorized work. No controlled cases or rates are created by this document.

<a id="controlled-repair"></a>

### Ticket 11 controlled replay contract

The offline V3-only executor and independent report are implemented. The accepted
study basis is 24 target cases plus 8 controls; formal construction/execution is
separate from the synthetic development checks in the
[implementation record](../records/evaluation/2026-10-04-controlled-repair.md).

#### Cases, targets and controls

Consume separately supplied V3 cases with original input, reviewed obligations, a pre-repair
primary itinerary, frozen execution capabilities and separately sourced evaluation material.
Case metadata declares the expected target conditions, their subjects and classification,
the intended improvement and the conditions to preserve. Actual findings and permissions
are measured outputs, not caller-supplied authorizations. Keep confirmed factual conflicts,
explicit requirement violations, declared product-policy violations and optional review
opportunities distinguishable. A sparse, repeated or overfull itinerary is not automatically
defective; apply the actual user obligations and frozen policy/review configuration.

A control checks whether an initially compliant itinerary becomes worse against its declared
constraints or acquires new independently established problems. It does **not** require
byte-identical output or an empty Repair scope. Legitimate review-policy changes may occur;
report detection, authorization, attempted edits and adopted changes separately from harm.
An added visit is acceptable only when the user's requirements remain satisfied and the
relevant added schedule, identity, opening and route conditions are independently supported.
An internally accepted patch is not independent proof of this outcome.

For example, adding Gallery C to a feasible Museum A/Garden B day is not automatically a
control regression. If the user explicitly requires exactly one primary visit on Tuesday,
adding a second Tuesday visit violates that reviewed obligation, even if opening and route
checks pass or the planner accepts the patch. Generic quantity recommendations do not waive
explicit counts, dates, exclusivity, required visits or protected time. Updated diagnostics
and transfer presentation are not themselves harmful itinerary changes.

Identify regression units through original obligation IDs, independently established visit
correspondence, directed route endpoints and the applicable conflict/protection subjects.
Reuse [paired continuity](0005-quality-human-review.md#v3-pairs): retained comparable
FAIL-to-PASS is resolution; deletions, replacements, removed connections and changed contexts
remain explicit rather than proving the old fact repaired. PASS-to-FAIL is a confirmed
regression; PASS-to-UNKNOWN is lost verification, not a confirmed regression or safe change.
Check newly introduced visits/connections and retain missingness. Product-policy or optional
review goals use their declared applicable conditions, not invented factual obligations.

Retain every expected target and control in the inventory. For each expected target, distinguish
detection, authorization, candidate opportunity, model attempt, adoption and independent
outcome. A detection miss stays in the expected-target denominator; later skips, unavailable
capability, rejected patches or missing independent verdicts do not silently remove the unit.
Report residual conditions, partial improvements, regressions, valid no-change and lawful
changes separately. Do not import Ticket 08's four-final total or manufacture a causal verdict.

#### Human supplementation and unresolved outcomes

Missing provider fields do not alone prevent a human from establishing an evaluation fact.
Review may clarify an obligation from the original request or supply separately verified
opening/route/identity evidence. Record the reviewer, review time, rationale, supporting
source references, exact case/source revision, affected subject, date/query applicability
and rule context. Use the existing identity, requirement, correspondence and scoped evidence
review mechanisms where they cover the subject; add only the missing controlled-case linkage.
A bare assertion of success or safety is not a substitute for the relevant fact or condition.

Preserve the original planner/provider material. Human supplements enter the independently
versioned evaluation channel; they do not retroactively grant the replay planner additional
evidence, supply, budget or permissions. Changed supplements produce a new linked preparation
revision. They cannot silently override contradictory established evidence.

After review, supported subjects receive their independent verdict. Remaining local uncertainty
stays unresolved/UNKNOWN, with affected units and coverage visible; it proves neither successful
repair nor confirmed harm. Preserve unaffected, valid observations. Corrupt sources, stale or
foreign reviews, missing required execution inputs and incomplete replay scripts are material/
execution errors, distinct from an unresolved real-world fact or an itinerary FAIL.

#### Frozen execution and the real V3 path

Reuse production post-primary initialization, `assess`, `operation_scope`, `run_repair_stage`
and finalization through `final_primary`. Recompute schedule, transitions, visit bindings,
targets, scope and round localization from frozen original inputs. Do not inject a target,
scope, prepared authorization or an adopted itinerary to bypass these measured stages.
Candidate preparation, model input construction, patch/component acceptance, re-validation
and final source/date/transfer handling remain the real production operations.

Freeze the runtime/review/transport configuration, candidate supply, geographic/intention
inputs, semantic assessments and active ledger, request time remaining, cache values/attempt
states and external response scripts. A case may explicitly declare an empty cache; historical
key hashes alone do not restore captured cache behavior. Supply typed local responses or
declared failures for Places, Routes, retrieval/embedding and model/semantic requests actually
needed by that case. Match calls against their declared input context. Supply deterministic
logical time and declared call durations without measuring real provider latency.

Unexpected or mismatched calls, absent script entries and any unintended live model/provider/
database access fail replay integrity. Frozen adapters retain an out-of-band error ledger,
because production Repair may catch ordinary provider/model exceptions. Declared provider
failures remain valid frozen responses; swallowed script errors cannot become ordinary skips,
detection misses or no-change outcomes. Replay usage is declared/simulated usage, not observed
live cost or a model-quality estimate.

The existing `tools/validation/repair_replay.py` is evidence-only scope/candidate preparation;
it does not replay model proposals or adoption. Reuse its capture concepts where applicable,
but preserve that diagnostic contract and do not claim old snapshots contain complete replay
capabilities. The isolated executor reuses production initialization/finalization and independent
identity, requirement/schedule, opening, route and paired checks. Controlled goal/
invariant linkage adds no second general quality scorer or fabricated four-version
batch. Default live clocks, policies and version entry paths retain their behavior;
this interface does not generate the formal 32-case corpus.

#### Controlled executable wire

`backend.evaluation.controlled_cli` owns the isolated command workflow. Ordinary
four-version intake still requires V0-V3. Controlled preparation contains only actual
V3 final/draft/final-primary sources; it never synthesizes V0-V2 results. The production
V3 post-primary and POI semantic services accept an optional clock; live defaults and
existing entry points preserve their behavior. Replay logical time starts at zero,
with `request_remaining` as the frozen deadline and declared durations added at calls.

The strict `rtpeval_controlled_case_1` envelope is defined by `ControlledCase` in
`backend/evaluation/controlled_models.py`. It embeds original input, primary itinerary,
interpreted requirements, runtime, transport, supply, place/route evidence, review switch,
reference date and request time remaining. Optional frozen funnel, geographic, RAG and
semantic state retain the execution capability. `calls` is required; explicitly empty
cache/attempt lists are valid. Cache entries preserve full keys, typed values and provider
wrapping. Semantic state preserves its fingerprint cache, active assessments, calls,
elapsed time and failed flag. Recomputed targets, scope and adopted outputs are forbidden
case inputs.

External scripts declare an operation, exact JSON request, response or nonempty declared
failure, and nonnegative duration. Repeated identical requests consume that request's
response queue in order; unused capability responses are permitted. Operations cover
Repair and semantic model calls, Places search/Details, Routes, embedding and retrieval.
Model matching excludes usage callback objects. Missing/mismatched calls and malformed
typed model/semantic/provider/retrieval responses remain out-of-band execution errors even if Repair
catches them. Declared model/provider outages are execution observations. A fatal production
exception without a completed V3 outcome is `execution_failed`; it cannot enter scoring.
Network connects are blocked inside replay. Use an exclusive event loop in a dedicated
offline process with no other network work, and execute cases serially. The guard patches
process-wide socket functions and the active loop clock; unrelated async tasks would observe
logical time too. This is a CLI/development executor, not a concurrent web-service runner.
The real asyncio timeout handles run against logical time before scripted replies are
delivered, so a response exceeding a configured call timeout is not silently adopted.
Tokenizer assets must already be local;
tests use the repository's offline structural tokenizer rather than live token measurements.

Replay emits `rtpeval_controlled_replay_1` with normalized case hash, actual V3 outcome,
request ledger, logical elapsed time, diagnostics and replay hash. Preparation verifies
that hash and original draft, then emits `rtpeval_controlled_preparation_1`. The embedded
original-input hash is the canonical JSON digest, not an original external file-byte hash;
reviewed requirements must bind to that digest and case ID. Executed source JSON is
serialized deterministically into genuine Ticket 10 result-source records.

`rtpeval_controlled_expectations_1` binds case ID/hash and a reviewed revision, reviewer,
offset-aware time, rationale and supporting references. Its `targets` and `guards` have
unique `goal_id`, `basis` and `condition`; targets additionally declare a `detector`.
Basis is `confirmed_conflict`, `explicit_requirement`, `product_policy` or
`review_opportunity`. Explicit requirements cite `{field, quote}` in the original input.
Check conditions select an independent dimension and exact original activity IDs or
obligation ID; optional canonical venue/date further restrict applicability. Dimensions
are requirements, grounding, opening, routes, conflicts and protection conflicts. Count
conditions use `daily_count` with date or `repeat_count` with canonical venue, with a
declared minimum/maximum. These are reviewer-supplied conditions, not title inference or
automatic sparse/repeated-day defects. Daily bounds include uncertain role/date occurrences;
repetition bounds include unresolved identities. Detector selectors use production check,
optional reason, activity/place/requirement IDs and dates. Confirmed goals match CONFIRMED
findings; review opportunities match NEEDS_REVIEW findings.

Per-goal output retains initial detection and authorization, round-linked candidate and
identity-free opportunities, model attempt and dependency-linked component adoption.
Independent outcomes reuse paired continuity and preserve structural changes, residual
FAIL, partial improvement, regression and unresolved evidence. Missing/corrupt execution
material retains expected goal inventory with unavailable outcomes and null measured counts.
An obligation-only protection condition reuses the independently scored `protected_time`
check for that original obligation. A cleared visit conflict alone does not establish that
all applicable commitments are clear; uncertain transport/candidate occupancy remains UNKNOWN.
An absent protected blocker cannot prove compliance.
Control baselines with confirmed violations are invalid control material. Unknown initial
compliance remains unresolved. Control regression checks guards and introduced/continued
independent failures; a lawful changed control need not have an empty scope. Raw paired
checks/scores remain separate from reviewed check outcomes.

Optional `rtpeval_controlled_facts_1` binds exact case and replay hashes with reviewed
revision/provenance. Opening facts select canonical venue, declared date and timezone,
with verified offset-aware `open_intervals`/`closed_intervals`. They fill only supported
coverage using the existing interval arithmetic and cannot contradict known intervals
or timezone. Route facts bind `expected_context_hash` from an independently prepared leg;
`availability` is `route_exists` or `no_route`, with optional integer duration nanoseconds
and distance meters. The existing route component rules evaluate those facts, retaining
missing components and rejecting contrary established observations. An unapplied, stale
or duplicate fact is material error. No human PASS assertion is accepted. Remaining
occupancy uncertainty uses the existing occupancy review channel; route facts alone do
not fabricate transfer occupancy. Raw paired metrics and deltas are preserved, while
`reviewed_checks` exposes supplemental checks/continuity without claiming recalculated
five-dimension scores.

The optional `rtpeval_controlled_batch_1` manifest inventories case ID, role,
`expected_goal_ids` and content-addressed report artifact references under one root.
Its report assembler verifies file/content hashes and exact case/goal inventory, keeps
unavailable cases and expected targets, and exposes descriptive counts. It imposes no
case-count cap and does not generate the formal 24-target/8-control corpus.

<a id="research-controlled"></a>

#### Declared research controlled view

Research Repair material can include a `controlled` object with `study_id`,
`revision` and an ordered `cases` inventory. Each case declares `case_id`,
`revision`, `role` (`target` or `control`), unique `expected_goal_ids`,
unique `expected_guard_ids`, `expectations_sha256` and `descriptor`.
Target and guard identifiers are disjoint. This population is separate from
declared original-request generation slots and does not assume a fixed study size.

A present descriptor binds `case_ref`, `execution_ref`, `expectations_ref`,
`report_ref` and `snapshot_ref`; the last reference names the snapshot's
`manifest.json`. Native builder inputs use their argument name followed by
`_ref`, including `requirement_spec_ref`, `identity_report_ref`,
`schedule_context_ref` and optional correspondence/factual reviews.
The declaration's expectations hash is the exact file-byte hash. Case identity,
revision, role and complete target/guard inventory must match the native sources.
The reader rebuilds the native controlled report from these frozen artifacts and
requires exact equality; corrupt, foreign or self-rehashed fabricated reports
are material errors. It does not execute controlled replay.

A missing case uses `descriptor=null` and `expectations_sha256=null`, retaining
every declared goal and guard as unavailable material. Resolution and preserved
resolution retain all expected targets; verdict coverage identifies which targets
have native independent outcomes. Detection is measured over available expected
targets, authorization over detected targets, model attempts over authorized
targets, and adoption over operation-attempted targets, including system deletion.
Historical records without `operation_attempted` retain their model-attempt fallback.
Each channel also exposes
the full expected-target count and coverage. Native candidate/identity-free
opportunities remain observations with their own units, rather than independent
successes.

Preservation is assessed only after the native target is independently resolved.
It requires every declared guard's independent final verdict to be PASS, complete
applicable continuity/correspondence, and no confirmed regression or introduced
failure. Guard FAIL or a confirmed continuity regression is `violated`;
guard UNKNOWN, lost verification or unresolved continuity is `unknown`.
Supplemented `reviewed_checks.continuity` and final checks govern this decision,
while raw paired scores remain unchanged. No guard is omitted because its material
is missing. Nonresolved targets remain separately labelled.

Case-level joint success requires all declared targets in that target case to be
resolved and preserved; its denominator is expected target cases. Controls retain
native valid-no-change, lawful-change, regressed and unresolved outcomes, with
missing controls explicitly unavailable. Neither case-level rates nor control
counts are pooled into generation-slot or target-resolution denominators.


The dated [implementation and review record](../records/evaluation/2026-10-04-controlled-repair.md)
retains development validation, corrections and execution limitations.

Ticket 12 separates mechanism exposure/usage from independent quality and causality;
its reports are specified in the [mechanism contract](#mechanism).
See [Ticket 11](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/23) and
[Ticket 12](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/24).

<a id="mechanism"></a>

### Mechanism reporting

The selected-source reader, mechanism report and default-off local capture are implemented.
Missing optional observations remain partial/unavailable without invalidating independent
quality material. The
[development record](../records/evaluation/2026-10-04-mechanism-report.md)
explains the original capture gap and consequential corrections. New rule replay cannot
establish which facts an older execution actually used.

#### Accepted mechanism units and denominators

Inventory selected source runs by group/version/run ID and exact original input/result
hashes. V3 Repair is not applicable to V0-V2; absence of V3 metadata is unavailable, not
zero triggers or zero model attempts. Distinguish available, partial, unavailable and
not-applicable coverage per observation. Positive zero is allowed only with complete
observations establishing that no event occurred.

Report initial improvement targets, initial authorized targets, model attempts, accepted
rounds, accepted/proposed components, per-round target presence and internal progress
separately. Versioned search observations distinguish exploration transitions, retained-result
promotions and deterministic attempts; an exploration transition alone is not final adoption.
The [Repair outcome contract](../0005-validation-repair%28v3%29.md#outcomes-and-compatibility)
owns selected-result and historical compatibility semantics.
Trigger means a nonempty authorized scope, not merely a NEEDS_REVIEW finding.
For each optional fraction, expose its numerator, denominator, unit and covered/missing
run counts. A run acceptance fraction uses triggered runs; a round acceptance fraction
uses model-attempted rounds; component acceptance uses components actually evaluated,
with pending/not-evaluated components reported separately. Do not merge these fractions.

Original authorized targets use original finding IDs; round-local target links map back
to them. Newly activated related/coverage targets remain a separate inventory. Per-target
internal progress does not become an independent resolution rate. Independently supplied
Ticket 10/11 reports may be linked with exact source hashes, but their outcomes remain
separate and are never inferred from an accepted patch or vanished target ID.

Round identity is run ID plus round index. Identical repeated observations are counted
once with their source references retained; contradictory records for the same identity
are material errors in that observation channel. Do not count both embedded round records
and trace copies, count the cumulative result as a final extra round, sum cumulative
counter snapshots, or add cumulative usage to its per-round children. Incomplete trace
fragments may support explicitly observed cells, never a fabricated complete denominator.

#### Accepted minimum capture and delivery scope

Reuse complete saved V3 outcomes and existing compatible trace/usage observations.
The default-off caller-owned wrapper provides best-effort local normalized capture of the accepted
claim catalog, actual primary/Repair model-input submission links and rule-selected
evidence links. Capture the facts at their existing seams without changing prompts,
model schemas, gate rules, Repair permissions, provider requests or runtime budgets.
Observe failed/uncertain submissions and capture truncation/write failure explicitly;
recording failures must not change planning. Do not require raw prompts/provider bodies
or enabled usage collection. Preserve existing trace redaction and size controls.

Old runs use only surviving, source-linked observations: complete V3 outcomes can still
support mechanism cells while capture observations remain partial/unavailable. Historical
accepted/exposed/used facts must not be reconstructed from the final itinerary or by
rerunning the current gate. Existing Ticket 11 frozen material may supply actual replay
observations only when linked to that replay; it cannot certify an older live execution.

The implemented boundary consists of the immutable mechanism reader/report, researcher
CLI and minimum opt-in capture above. Reuse artifact
hash/link validation and usage summarization. Keep four-final quality scores, identity,
paired metrics and anonymous review unchanged. No frontend or new acquisition system.
The extension adds local serialization/storage work; it adds no model input/output
tokens or provider/model calls by design. Offline regressions must verify identical
prompts/call counts with capture disabled/enabled and best-effort failure behavior;
real overhead was not measured by the offline development checks.

<a id="ticket12-implementation-scope"></a>

<a id="mechanism-executable-wire"></a>

#### Executable wire

The [mechanism CLI](../../backend/evaluation/mechanism_cli.py) has `prepare` and `report`
commands. `prepare --manifest` reuses the existing
four-version intake; `prepare --selection` reads the saved Ticket 11 preparation and
its embedded exact `result_sources`. Neither command invokes a planner or reconstructs
a controlled case. Optional `--observations` reads `{ "records": [...] }` with these fields:

- `group_id`, `run_id`, `version`, original `input_sha256`, exact saved `result_sha256`;
- `channel`: `capture`, `trace`, `usage` or `independent`;
- `content`: the supplied JSON envelope; `content_sha256`: its canonical JSON digest;
- optional `artifact_sha256`: retained saved-file byte provenance, not a substitute for
  the verified content digest or source linkage.

Canonical digests use sorted keys, compact separators and UTF-8 with non-ASCII characters
preserved. Original result hashes remain byte hashes using the exact caller serializer;
preparation retains the original result bytes as UTF-8 and rechecks them on reporting.
Preparation is an immutable snapshot. Channel-local errors preserve other mechanisms
and never change Ticket 08/10/11 quality, identity or scoring material.

The `trace` channel accepts an `events` array from the current tracer. Only surviving
`v3_repair_round` payloads are recognized as round observations; matching embedded copies
are not added to counts. The trace does not certify a complete attempt/target/component
denominator. `usage` uses the existing independent summarizer once; parent cumulative
tokens/counters are retained separately from child observations. An `independent` channel
accepts a complete Ticket 10 pair or Ticket 11 controlled report with verified semantic
content hash and its `source_hashes.intake` or `.preparation` binding the original selection.
These attachments retain independent outcomes without upgrading internal acceptance.

The [capture wrapper](../../backend/app/observability/mechanism_capture.py) accepts a
zero-argument async invocation, group/run/version, original input hash, exact result
serializer, synchronous local sink and positive `max_bytes` (default 1,000,000).
It observes only normalized official projections/catalogs and actual opening selections;
no always-on configuration or extra API/CLI planner field is introduced. Default adapter
submission is application-interface entry, including later failed calls. Per-call return,
failure or cancellation remains in `prepared_calls`; missing injected-client observation
does not become submission. Existing redaction rules are reused: a secret-bearing
observation is omitted with partial diagnostics rather than altering an exact claim.
Capacity and observation failures are bounded; sink failure logs only its error type.
Result/exception preservation includes cancellation, independent of enabled usage/tracing.

Capture retains accepted claim/source hashes and actual submitted/selected representations
with their occurrence links. Missing observations stay partial or unavailable. Trace copies
are checked against matching saved round status, continuation, usage and shared cumulative
counter cells; contradiction fails only the trace channel.

Offline acceptance and implementation/review history are recorded in the
[Ticket 12 record](../records/evaluation/2026-10-04-mechanism-report.md).

Whole-trip factual budget PASS, verified access/fees and false-certainty metrics remain deferred.
Amounts can be descriptive; source role does not certify affordability. V0-V3 comparisons are
incremental system comparisons; no extra strict module-ablation study is introduced.

## Decision and acceptance history

The [parent specification](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12),
[published work breakdown](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12#issuecomment-5956237972)
and [historical review](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12#issuecomment-5956197027)
preserve the earlier design/approval sequence. Implementation evidence is indexed in
[records](../records/README.md); executable commands are in the
[package guide](../../backend/evaluation/README.md). Legacy anchors resolve to their current
topic or this history section; they do not restore superseded wording as current policy.
