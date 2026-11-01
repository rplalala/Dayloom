# Capstone Project Context

Current source of truth. Updated 2026-11-01.
Detailed design, development and acceptance records are indexed in
[docs/README.md](docs/README.md).

## 1. Purpose and responsibility

This Capstone / Thesis B project builds an LLM-based travel planner for feasible
and reliable itinerary generation. It maintains four independently runnable
versions so their mechanisms remain distinguishable.

The project covers system design, implementation, engineering validation and
RTPEval. The authorized twelve-case benchmark, blinded assessments and final comparison
are complete and published. Further benchmark execution, version-comparison
experiments, thesis writing and broader research conclusions require separate
authorization. Development smoke results remain bounded engineering evidence;
neither they nor benchmark acceptance automatically freeze a version.

[AGENTS.md](AGENTS.md) and its linked policies own collaboration, language, approval,
Git and archive rules; detailed rules are loaded for the relevant operation.
Repository content is English; user-facing development discussion is Chinese.

## 2. Architecture and version boundaries

Use a modular monolith: React frontend; FastAPI API/application/backend services;
shared LLM, evidence, RAG and orchestration components with version-specific
entry points; the shared `dayloom` PostgreSQL database with pgvector for TripWorld
retrieval and the `dayloom` login role.
Product uses the separate `app` schema in that database for accounts/profiles,
incomplete drafts, durable account-owned tasks, recoverable previews and normalized
saved trips. Checksum-protected migrations and owner-scoped operation receipts support
explicit Save/Discard, historical import and recovery across application recreation. See the
[Product design overview](docs/0007-application-operations.md#product-experience-and-persistence-design).
External provider payloads are normalized before entering application policies.

| Version | Implemented mechanism | Independent entry point |
| --- | --- | --- |
| V0 | Plain LLM with shared input interpretation; model-estimated transport and optional model-knowledge references | `scripts/run_v0.py` |
| V1 | External place, weather, route and supported official/current evidence; shared candidate supply and post-primary Nearby | `scripts/run_v1.py` |
| V2 | V1 plus bounded TripWorld RAG discovery, Google identity resolution and canonical merge | `scripts/run_v2.py` |
| V3 | V2 plus structured validation, authorized targeted Repair and re-validation | `scripts/run_v3.py` |

V1-V3 share the tools-generation pipeline; V3 adds its own post-primary extension.
Shared correctness fixes must preserve the intended behavior of dependent versions.
Supplied model identities now use request-local short references at the affected
provider boundaries, with exact restoration before existing domain/ownership checks;
see the [identity transport contract](docs/0001-system-architecture.md#model-identity-references).
Earlier milestone freezes retain their original scope; later changes are separately
recorded and do not automatically re-freeze any version.

The current local Dayloom Product was accepted by the user on 1 November 2026 at
`e2f38b0fb402b1b6e8eebccd07281dd7ffe7159b`, after the configuration-console and
Product web cleanup delivery in [PR #242](https://github.com/rplalala/Dayloom/pull/242)
and [Issue #241](https://github.com/rplalala/Dayloom/issues/241).
The built frontend and normal API share `http://localhost:5173`; the `dayloom` Compose
project runs `postgres` against the retained runtime volume. Git delivery is complete through
merged [PR #210](https://github.com/rplalala/Dayloom/pull/210) and completed
[#208](https://github.com/rplalala/Dayloom/issues/208); hosting remains separate and
pending. See the [local acceptance record](docs/records/frontend/dayloom-product-lifecycle-acceptance.md#final-local-product-acceptance).

The complete-media and acceptance-resource follow-up was accepted by the user on
24 October 2026. Merged [PR #232](https://github.com/rplalala/Dayloom/pull/232) completes
[Issue #231](https://github.com/rplalala/Dayloom/issues/231); the [acceptance record](docs/records/frontend/dayloom-product-lifecycle-acceptance.md#complete-media-and-acceptance-resources-24-october-2026)
retains the bounded live result and unverified retrieval/search coverage.

One ignored root `.env` supplies credentials and machine-specific overrides. Root
`product.yaml` supplies Product options, shared database connection fields and Foundry
endpoint/deployment settings. `scripts/run_database.py` passes the same resolved
connection settings to Compose. Planning policies
use `config/runtime.yaml` for development and `config/runtime.acceptance.yaml` for Product
acceptance, selected by `product.yaml: runtime_profile`. Planning and Product photos share `GOOGLE_MAPS_API_KEY`.
Acceptance uses larger input and supply capacity with bounded execution budgets and a shared per-run
spending guard that excludes web search. Both standard profiles use Azure Foundry search;
the [profile reference](config/README.md#product-acceptance-profile) owns
current values and the development rollback.
See the [development guide](docs/guides/development.md#local-postgresql-naming-and-storage)
for storage retention, overrides and isolated test settings.

The local Product launcher also serves `/config` with independent loopback-only
management access. New installations use the displayed local test password,
with persisted password verification on every page entry and a bottom-right settings shortcut.
Existing custom passwords and explicit verification preferences are retained. It edits
Foundry endpoint/deployment in `product.yaml` and provider credentials in `.env`,
shows local resource readiness and offers
explicit bounded API capability checks. Saved provider changes require restart;
password-access changes apply immediately. Incomplete local installs
can open the console while business APIs remain paused. Database/data preparation,
model providers, spending policies and V0-V3 mechanisms retain their current scope.
See the [configuration guide](docs/guides/development.md#local-configuration-console).

Guest example itineraries are read-only showcases with bundled local photographs
and illustration fallbacks, without media provider requests. Source and license
credits ship with the assets; authenticated travelers can keep an independent copy.

Product UI/API uses V3 and an allowlisted presentation contract. V0-V3 remain
independently accessible through command-line and programmatic entry points. The Developer
web page and its dedicated APIs are removed. Current input assistance includes destination suggestions,
currency/date controls and optional user-reviewed preference polishing.
Itinerary activity/Nearby photographs now reuse validated links within the browser tab
session; the [media contract](docs/0007-application-operations.md#browser-tab-photo-session)
defines expiry, isolation, bounded recovery and browser lifecycle limits.
Product diagnostics now correlate HTTP operations, durable tasks and planner runs,
preserving native Repair decisions, bounded payloads and independent completion/usage
summaries alongside public progress. Local lookup and retention are described in the
[development guide](docs/guides/development.md#product-diagnostics); the
[application contract](docs/0007-application-operations.md#product-diagnostics) defines
coverage and privacy. Earlier Product runs without persisted diagnostics cannot be reconstructed.

Details: [shared architecture](docs/0001-system-architecture.md),
[frontend design](docs/0007-application-operations.md), and the
[version design index](docs/README.md#core-designs).

## 3. Current behavioral contracts

### Requirements and candidate supply

- `planning_request_2` supplies destination, supported dates, traveler count,
  whole-trip budget/currency and optional additional preferences.
- Nonempty preferences use one shared interpretation stage; empty preferences
  skip that model call. Application-owned requirements retain exact source and
  subject provenance. Unsupported hard conditions and unresolved required identities
  preserve clarification boundaries.
- Current interpretation uses compact request-bound integer source selections and a required pace
  default. Whole-trip hard transport mode sets constrain V0 acceptance and V1-V3
  acquisition, selection and Repair; unsupported hard semantics still require clarification.
- Explicit dated totals count primary visit occurrences and protect each hard obligation
  throughout V3 Repair; zero sightseeing remains distinct from a full rest day. Independent
  evaluation has its own reviewed count operator and prospective rules version.
- User-named places bind to acquired candidates through sourced semantic correspondence
  and unique application adoption; provider-standard names need not match user wording exactly.
- Ordinary positive POI interests use soft targets of one distinct qualifying POI,
  or two for an explicitly sourced trip focus. Explicit counts, dates, exclusions
  and exclusive restrictions take priority. Broad enjoyment does not invent quotas.
- V1-V3 support [required category visits](docs/0002-requirements-evidence.md#required-category-visits)
  without weakening hard strength or original meaning. Final scheduled coverage and
  unresolved evidence remain visible; V3 Repair protects attained required coverage.
- V1-V3 use bounded discovery, evidence acquisition, semantic assessment and
  deterministic candidate supply. Shared landmark opportunities remain available
  after preference targets are met. Candidate opportunity is not final fulfillment.
- V2/V3 use the existing TripWorld exact geographic retrieval and canonical merge;
  no new vector rebuild, ANN index or alternate persistence layer is implied.

Details: [requirements](docs/0002-requirements-evidence.md),
[POI supply](docs/0002-requirements-evidence.md),
[landmark discovery](docs/0002-requirements-evidence.md), and
[V2 retrieval](docs/0004-retrieval-persistence%28v2v3%29.md).

### Itinerary, transport and Repair

Tools versions derive new local timestamps from sourced IANA zones per endpoint and date,
reject conflicting explicit offsets and ambiguous/nonexistent clocks, and use elapsed UTC
arithmetic for transfers. V0 retains its independent time generation. See the
[civil-time contract](docs/0003-itinerary-transport.md#civil-time-and-iana-acceptance).

- Current generation uses `itinerary_3` with explicit roles and scheduled/free-window
  time use; historical `itinerary_1/2` remain readable. Primary visits and optional unscheduled Nearby
  references stay separate. References do not satisfy required visits or count as
  scheduled activities or planned costs.
- V1-V3 acceptance restores the authorized source's name and complete formatted
  address, including after V3 Repair. Generic activities and V0 retain model text;
  raw model captures and historical submitted outputs remain immutable.
- V0 generates explicitly estimated transport activities without Routes calls.
  New output includes structured mode and directed activity endpoints; absent/null
  declarations remain compatible with historical outputs. These are model estimates.
- V1-V3 model output must not contain transport activities. Their primary DTO and
  shared output acceptance enforce the declared-role boundary; prompts also prohibit
  disguised transport. Application-owned `transfers` use Routes evidence. Models may
  use supplied route evidence to leave suitable gaps between visits.
- A forbidden declared transport activity fails generation without automatic deletion
  or an extra retry. Comprehensive semantic detection of disguised prose is not claimed.
- V3 uses bounded, permissioned patches and re-validates proposed/adopted results.
  It preserves prior accepted improvements when later attempts fail. No unsupported
  evidence is manufactured to turn UNKNOWN into PASS.
- Minimum daily coverage and optional quantity review are distinct. Sparse/overfull
  days do not automatically authorize arbitrary changes; review flags and permissions
  are recorded per run.
- V3 Repair's optional quantity review optimizes source-linked daily pace toward zero
  deductions. It accepts legal partial reductions and preserves the best accepted
  result at stops. Under `rtpeval_daily_density_3`, full Rich Repair completion requires
  exactly three known primary visits on each default-Rich date and satisfied supported
  return checks. Sourced exceptions, residuals and unavailable results retain distinct
  states through Product preview and save/reopen. See the
  [final completion contract](docs/0005-validation-repair%28v3%29.md#final-rich-completion).
  V0-V2 and V3 initial generation have no zero-penalty requirement.

V3 Repair now separates exploration from the best retained result, enumerates bounded
authorized deletions and replans causally linked affected dates. Local proposals and
replans share up to six model sends under the existing stage deadline; deterministic deletion
has its own limit. Production delivery, saved-record compatibility, offline verification
and independent review are complete;
see [the search contract](docs/0005-validation-repair%28v3%29.md#accepted-bounded-search-redesign).

Details: [shared output](docs/0003-itinerary-transport.md),
[minimum coverage](docs/0003-itinerary-transport.md),
[V3 current design](docs/0005-validation-repair%28v3%29.md), and
[transport correction acceptance](docs/records/evaluation/intake-identity-usage.md#rtpeval-transport-correction-acceptance).

## 4. RTPEval implementation status

RTPEval runs independently over source-linked submitted outputs. Planner validation,
internal findings and caches are not independent factual ground truth. The operational
`evaluation_run_cli prepare / execute / replay` flow captures independent evidence,
records actual requests/usage and produces native automatic reports for V0-V3 finals.

The editable repository installation exposes offline `rtpeval validate` and one-step
`rtpeval evaluate execute`. The latter accepts a qualified manifest, a fresh directory
and explicit options/prices/reviewed contexts; native preparation and execution emit the
existing automatic report without manual digest transfer or a subsequent quality command.
Optional offline prepare/replay and prepared-directory/exact-digest execution remain
available. Top-level and evaluate-group help load no evaluator implementation. Dispatch
lives outside preparation-bound evaluator files. Budgets, credentials, source/receipt
integrity, one-use rules, version-specific identity/reasoning policies and separate statuses
remain native. Eligible missing-hours access assessment now precedes the single final
primary score within the prepared allowance; API-only execution is an explicit option.
No automatic retry is added. See
[installed evaluation](backend/evaluation/README.md#installed-automatic-evaluation).
The integrated implementation also exposes explicit offline collection, external reviewed
requirements attachment/native finalization, selected generation registration and task-oriented
adapters to the existing tools. Collection stays unqualified until reviewed four-version
finalization; external agents are separately operated. Post-generation offline review
queues distinguish missing activity-role/occupancy work from reviewed uncertainty;
fresh primary preparation blocks missing required coverage before acquisition.
See the [review readiness contract](docs/contracts/0002-intake-identity-usage.md#post-generation-review-readiness) and
[material handoff](backend/evaluation/README.md#installed-generation-and-material-handoff).

| Capability | Current behavior | Detailed owner |
| --- | --- | --- |
| Intake and identity | Original claims, source hashes and common independently resolved requirement targets; V0 visit correspondence and unchanged V1-V3 API/program visit grounding | [Intake/identity/usage](docs/contracts/0002-intake-identity-usage.md) |
| Evidence and accounting | Frozen Search/Details/Matrix snapshots, failure receipts, source-linked coordinates, source-labelled offline paired imports, actual usage and explicit retail estimates when billing is unavailable | [Artifacts](docs/contracts/0001-evaluation-artifacts.md), [usage](docs/contracts/0002-intake-identity-usage.md#offline-cost-accounting) |
| Requirements and schedule | Explicit counts/dates/exclusions/fixed times; verified occurrence associations with separate grounding; V0 declared transport occupancy and V1-V3 transfers | [Requirements/schedule](docs/contracts/0003-requirement-schedule.md) |
| Opening | Current/regular API schedules take priority; missing-hours LLM assessment can infer ordinary public-landmark viewing, while explicit restricted activities and museum admission need access evidence; factual coverage stays separate | [Opening/routes](docs/contracts/0004-opening-routes.md#opening) |
| Routes | Independent coordinates and mode/time-applicable route evidence against original reserved duration; unsupported provider scope remains unresolved | [Opening/routes](docs/contracts/0004-opening-routes.md#route-wire) |
| Quality and density | Five automatic dimensions with separate evidence availability; source-linked pace deductions adjust the final total without adding hard generation quotas | [Quality/density](docs/contracts/0005-quality-human-review.md) |
| Multi-case suite | Explicit ordered accepted revisions, sequential native primary limits, default saved generation-resource/mechanism reports, optional independent pairs and source-bound study refresh | [Suite guide](backend/evaluation/README.md#installed-multi-case-suite), [artifact contract](docs/contracts/0001-evaluation-artifacts.md#source-bound-suite-lifecycle) |
| Additional evaluation tracks | Blinded review, V3 paired reports, controlled Repair and mechanism reports are implemented; their execution and research populations require their own scope | [Evaluation design](docs/0006-independent-evaluation.md), [artifacts](docs/contracts/0001-evaluation-artifacts.md) |
| Original-input research | Installed offline population, canonical opportunity, independent relevance/coverage, Repair and generation tradeoff reports, with explicit optional suite attachments, fresh report revisions and deterministic offline replay | [Offline research](backend/evaluation/README.md#installed-offline-research), [track relationships](docs/0006-independent-evaluation.md#research-track-relationships) |

Fresh Primary identity uses `versioned_api_identity_6`, independent
`requirement_subject_correspondence_2` and `v0_visit_correspondence_1`; requirement rules 6
conjoin target uncertainty with conservative checks, preserving proven violations. Existing offline callers retain explicit
policy-4 compatibility; the first common-subject policy remains explicitly replayable.
Common-subject destination checks accept typed `postal_town` with consistent city/country
evidence. Paired acquisition explicitly opts into policy 6 / subject policy 2 with
`--subject-primary-run`, reusing exact closed Primary target material without rescoring
Primary or sending a new subject-model request; legacy preparations retain policy 4.
Historical requirement/schedule rules select version 5 for a reviewed
`daily_visit_count`, otherwise version 4 for `transport_modes` or version 3 without either.
Route rules select version 3 with `transport_modes` and retain version 2 without it.
Opening retains
API-only rules 2 and selects rules 4 with validated policy-2 access judgments. Verified physical
associations can support occurrence matching,
opening and route checks while original grounding FAILs remain visible. Common requirement
targets project to version-owned references while visit associations remain independent. Historical reports retain their original policies,
code and source bindings; a rule change produces a separate recalculation.

The [common-subject correction acceptance](docs/records/evaluation/intake-identity-usage.md#common-requirement-subjects-and-geographic-purpose-2026-10-17)
records offline validation, independent review corrections and unchanged case-08 evidence.

The supplemented Sydney development case recorded on 2026-10-09 uses the original
V0-V2 and the source-protected V3 without changing submitted outputs. Fresh
independent acquisition and the complete
native evaluator, supplemental opening and manifest-based quality CLI agree; exact
zero-network replay verifies source hashes and closed receipts. Current V0 identity
requests require every prepared reference as an object key, with strict complete
coverage and existing correspondence checks. Legacy uniform/V0 paths retain their
original request format; older current packets retain their producer implementation.

| Version | Overall score | Opening UNKNOWN | Grounding FAIL | Mean soft pace deduction |
| --- | ---: | ---: | ---: | ---: |
| V0 | 89.2857 | 1 | 1 | 5 |
| V1 | 80.0000 | 0 | 0 | 20 |
| V2 | 85.0000 | 0 | 0 | 15 |
| V3 | 100.0000 | 0 | 0 | 0 |

All four Opera House exact-once obligations PASS. The latest V3 has eight independently
verified visits and no factual FAIL/UNKNOWN or pace deduction. Its initial generation
already met the pace objective, so this output does not exercise Repair. The model's
Australian Museum address assessment remains a V0 FAIL; V0 Powerhouse indoor admission
remains UNKNOWN because applicable opening/admission evidence is missing. Twelve other
missing-hours checks PASS on the existing public-landmark/outdoor access policy, with
explicit model-reasoning basis rather than certified API hours. Residual judgments and
five auxiliary daily pace deductions remain source-linked in the final report. This is
bounded engineering integration evidence, not a formal ranking or version freeze.

Current acceptance and actual failure/correction/retest sequence:
[identity coverage and complete CLI acceptance](docs/records/evaluation/intake-identity-usage.md#complete-v0-identity-coverage-acceptance-2026-10-09).
Earlier unchanged outputs, policies and reports remain historical evidence in the
[evaluator record](docs/records/evaluation/intake-identity-usage.md) and
[opening record](docs/records/evaluation/opening.md); they are not substituted for the
latest result. Commands and preparation: [evaluation package guide](backend/evaluation/README.md).

## 5. Configuration, evidence and limitations

The development and Product acceptance runtime files and typed configuration own active limits;
[config reference](config/README.md) explains them. Entry-point deadlines and stage
budgets are distinct. Dated execution allowances do not become runtime defaults.
[Development guide](docs/guides/development.md) owns runnable commands.

Initial Product engineering checkpoint (22 October 2026): the Dayloom Product
lifecycle passed 263 API/PostgreSQL/browser tests, including 62 actual Chromium
cases with no Product skips. The frontend passed 174 tests in 27 files, build and
lint; two Fast Refresh warnings remain. The initial full backend run at `74d1603`
recorded 4,907 passes, seven platform skips and four failures. Test-only corrections
resolved the keyboard expectation and inherited CLI environment; the paused CLI
case passed in the complete isolated environment. The affected CLI check passed
941 distinct cases across its original invocation and a short-path follow-up,
with six of the same platform skips. No single all-green full-backend invocation
is claimed. Source and correction Standards/Spec reviews have no remaining finding.
The [lifecycle record](docs/records/frontend/dayloom-product-lifecycle-acceptance.md)
owns exact revisions, the failure/correction sequence and evidence limits.

Earlier engineering evidence includes the 18 October
[bounded case-refresh delivery #193](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/193)
at `23e47eb` (4,619 backend passes and 16 environment skips), and the
[case-12 r07 integration](benchmark/case-12/report.md#main-worktree-integration).
The latter records sandbox-dependent fixture failures and a test-only deadline
telemetry normalization correction. Its original results and remote delivery state
belong to that dated record; this Product checkpoint adds no benchmark assessment.

The migrated case-12 archive passed all retained-byte/public-source checks and ten
exact native report reconstructions with its original producer source, network and
original working-data access blocked. Current main independently rebuilds candidate
opportunities/relevance but rejects historical Repair rebuilding because its opening
packet binds older evaluator implementation hashes. No fingerprint gate was bypassed
or accepted output rescored. The case report owns reproduction limits and the actual
failure/correction/retest sequence. Earlier [activity-semantics integration](docs/records/evaluation/intake-identity-usage.md#activity-semantics-implementation-and-offline-validation-2026-10-16)
and [case-05 integration](benchmark/case-05/report.md#acceptance) retain their original
sources and validation limits; earlier evidence was not refreshed by this checkpoint.

Remaining limitations:

- Missing opening/access facts, unsupported route-provider scopes and unresolved
  identity/time/role evidence remain visible. A complete process can contain UNKNOWN.
- Common subject and V0 visit correspondence are fallible. V1-V3 visit checks retain literal names and binary
  address equivalence; unexplained address differences fail. Google-supported aliases
  do not waive identity/provenance requirements.
- Undated business status does not establish future closure dates. Optional public/exterior
  access assessment is model reasoning, not certified hours. Official web acquisition is
  not implemented; ambiguous or indoor access can remain UNKNOWN after model assessment.
- The retained KR V0 route package has unresolved provider/departure support. Proposed
  alternate providers need an approved adapter/evidence scope; Sydney acceptance does
  not resolve those historical legs. See [route support](docs/records/evaluation/routes.md#kr-route-support-budget-2026-10-07).
- Provider invoices and some billed quantities are unavailable; explicit retail/proxy
  estimates are not actual bills. RAG coverage and retrieval performance remain bounded
  by corpus/runtime evidence, not a general availability guarantee.
- Opening serialization and complete V0 identity coverage are corrected for newly
  prepared material. A 3,000-token identity response truncated during the latest live
  run; a separate 8,000-token package completed within its bounds. Output allowances
  include reasoning tokens. Incomplete responses still stop and preserve their receipts;
  successful processing can retain genuine factual UNKNOWN judgments.
- Blinded review, V3 paired diagnostics, controlled Repair and mechanism reports exist.
  Accepted per-case process/pair reports retain their own evidence limits; controlled
  studies, additional assessments and broader research conclusions need their covered scope.

Detailed engineering history is indexed in [records](docs/records/README.md), including
[evaluator records](docs/records/evaluation/intake-identity-usage.md),
[V3 development](docs/records/v0-v3/v3-development.md) and
[shared transport validation](docs/records/v0-v3/transport-responsibility-smoke.md).
Ignored logs, artifacts and thesis notes are local evidence, not project authorities
or guaranteed fresh-clone assets.

## 6. Next work and authorization boundary

The Dayloom Product lifecycle in [#198](https://github.com/rplalala/Dayloom/issues/198)
is implemented across its thirteen native children: account-owned tasks, incomplete
drafts, recoverable generated/imported previews, explicit manual saving, a mixed
library, independent copies, known-input replanning and credited media with honest
fallbacks. The fixed r7 design remains the visual reference; its standalone prototype
still uses browser-local simulations. Product refinements in
[#212](https://github.com/rplalala/Dayloom/issues/212),
[#213](https://github.com/rplalala/Dayloom/issues/213) and
[#214](https://github.com/rplalala/Dayloom/issues/214) provide two complete historical
guest itineraries, clearer text/mobile cards and a compact initial planning page.
#119 retains the historical foundation mapping.
Account images use initials; avatar upload remains deferred.

[Application operations](docs/0007-application-operations.md#product-experience-and-persistence-design)
owns the current contract. The [lifecycle acceptance record](docs/records/frontend/dayloom-product-lifecycle-acceptance.md)
records isolated database/browser verification, review corrections and bounded live
acceptance. The [complete local runtime](docs/guides/development.md#complete-local-product-runtime)
serves the built frontend and normal API together using the daily database and real
providers. One separately authorized Sydney one-day journey passed generation,
preview, explicit Save and My trips reload on 22 October, with real model, map/route,
weather, embedding and image HTTP success evidence. This does not establish general
provider quality, full billing, public deployment or scale. Independent V0–V3
and research commands retain their entrypoints and behavior. Git delivery
is complete through PR #210, #208 and the accepted follow-up in PR #232 / #231.
Additional live runs, public hosting and research
require separate scope; no version freeze follows from acceptance.

Evaluation extensions are developed independently:

| Work | Specification | Current state |
| --- | --- | --- |
| Unified batch entry point and report integration | [#106](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/106), children #107-#111 | Merged; synthetic engineering acceptance complete; [PR #128](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/128) |
| RAG, Repair and generation tradeoff reports | [#112](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/112), children #113-#118 | Merged; synthetic/offline engineering acceptance, combined backend regression and independent Standards/Spec review complete; [PR #129](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/129) |

Their responsibilities and relationship to native scoring are summarized in the
[Evaluation extensions](docs/0006-independent-evaluation.md#batch-and-research-extensions).
GitHub Issues own detailed specifications, dependencies and acceptance state.
The combined main-worktree offline gate [#130](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/130)
is accepted at the checkpoint in section 5.
Suite engineering acceptance used synthetic saved material and injected transport.

### Final benchmark and blinded assessment

The [selection index](benchmark/README.md#accepted-selections) identifies the twelve
cases and their exact datasets. The [case-04 replacement](benchmark/case-04/report.md)
under [#218](https://github.com/rplalala/Dayloom/issues/218) has four newly generated
versions and matching independent Primary/Pair evaluation for 25–26 October 2026.
V3 retains three primary visits per day with native Rich completion `complete` and
independent score 100. V0 has a route timing FAIL; V2 retains missing-mode UNKNOWNs.
The other eleven cases retain their outputs, factual rules and scores.

The [benchmark report](benchmark/report.md) gives the automatic mean-score order
**V3 > V2 > V1 > V0**, exact ranks, Pair summaries and selected-generation resources.
Original evidence and all-attempt costs remain preserved. The researcher accepted
the complete replacement on 24 October 2026 under #218. Blinded display content
is synchronized under #219. Thesis synchronization under
[#220](https://github.com/rplalala/Dayloom/issues/220) is complete and was accepted
by the author on 24 October 2026. The separate local thesis repository contains
the final English PDF, LaTeX sources, Chinese companions, reproducible extraction
scripts and matching Overleaf export. Acceptance does not establish school archival
submission or final project sign-off.

The [blinded-review report](benchmark/blinded-results/report.md) covers one human
and one GPT-6.1 sol xhigh assessment of the twelve accepted itinerary comparisons.
The researcher confirmed both reviewers' results for the current questionnaire on
24 October 2026. English/Chinese questionnaires, the two directly importable answer
exports and exact source bindings are maintained in `benchmark/blinded-results/`.
Both reviewers rank V3 first overall; the human
places V2 second and the model places V0 second. Publication and report delivery
are completed under [#196](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/196);
the [roadmap #51](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/51)
tracks the remaining project work.

The [current-data replacement record](docs/records/evaluation/accepted-case-compatibility.md#current-data-replacement)
documents the 04/05/09/11 selections accepted on 18 October and their matched
analyses. Historical evaluation policies and unresolved evidence remain visible;
case-09's pair retains its original runtime and unchanged V3. Earlier selections
and native evidence remain in immutable archives and Git history, with case
details and retired-ID mappings maintained in the benchmark index.

The [benchmark workflow](benchmark/README.md#workflow-and-responsibilities) and
[staged acceptance contract](docs/contracts/0005-quality-human-review.md#staged-automatic-acceptance-and-deferred-blinded-review)
own the detailed sequence and material boundaries. Blind judgments do not change
accepted automatic scores. Private mappings and native report/replay dependencies
remain in private evidence storage; corpus measurement and controlled studies
remain optional work.

### School archival submission

The supervisor requires a repository under the University GitHub Enterprise
organization `ThesisProjects-ECE`, containing the final thesis PDF, source code,
relevant datasets, experiment scripts and instructions sufficient to reproduce or
verify the findings. Confidential or restricted material needs an appropriate
access and distribution arrangement. Required thesis and clearance forms must be
uploaded as clearly named PDFs to the supervisor's designated OneDrive folder;
both submissions precede final project sign-off.

School archival submission is pending. Current preparation covers the
[deployment guide](docs/guides/deployment.md),
[reproduction and materials guide](docs/guides/reproduction.md), local inventory
and completeness verification; upload, repository creation, form submission and
new paid execution remain outside that scope. The project Git repository excludes
the separate `thesis/` working repository,
TripWorld runtime data and private native experiment archives; a source-only copy
does not by itself include the complete research submission. Archive preparation
must account for these dependencies and historical producer-code requirements.
GitHub Issues own subsequent task state.

### Earlier evaluator acceptance

[CLI entry/validation #96](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/96)
and [one-step evaluation #97](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/97)
were delivered as the first slices of
[unified CLI parent #95](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/95).
Collection, finalization, generation registration and task-oriented tools are integrated;
#102 adds complete public synthetic workflow acceptance and operational guidance.
[PR #105](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/105) contains the
completed implementation and offline acceptance. The current backend validation
checkpoint is in section 5; implementation and documentation review history belongs
to the acceptance record.
See [unified acceptance](docs/records/evaluation/intake-identity-usage.md#unified-rtpeval-material-workflow-acceptance-2026-10-09).

On 2026-10-10, a separately approved real-material acceptance at `3ae30b7` reused
the saved Sydney V0-V3 outputs. Two isolated Codex author/reviewer executions
produced source-bound requirements; public collection, attachment, finalization
and validation yielded a directory accepted directly by one-step evaluation.
Fresh independent acquisition and processing completed with 67 Google sends,
one model send, zero retries and USD 1.381796925 in reference cost against a
USD 3 allowance. Network-blocked replay reproduced the report without modifying
sources or evidence. Actual billing remains unavailable. The original report retains
48 UNKNOWN inventory entries. A separately saved offline recalculation reviewed
activity role/occupancy, original transport constraints and relaxed pace, resolving
35 entries using the same captured responses. A subsequently approved, newly bound
access assessment made one model request and no Google requests, resolving 12 of
the 13 missing-hours verdicts through the public-landmark policy. V0 Powerhouse
Museum indoor admission remains UNKNOWN. Model PASS does not supply verified hours.
Native opening and quality replay matched under network denial, with factual hours
and other quality dimensions unchanged. Cumulative reference cost is USD 1.385057975;
actual billing remains unavailable. This small real-material acceptance is complete
with the remaining uncertainty retained; resolving museum admission needs applicable
authoritative evidence rather than another identical Google query.
Details: [installed CLI real-material evidence](docs/records/evaluation/intake-identity-usage.md#installed-cli-and-reviewed-material-workflow).
Fresh Planner generation, formal research and version freeze remain separate work.
Live Issues and PRs own delivery and lifecycle state. Retained earlier evidence:
[validation acceptance](docs/records/evaluation/intake-identity-usage.md#installed-rtpeval-validation-acceptance-2026-10-09),
[one-step acceptance](docs/records/evaluation/intake-identity-usage.md#one-step-rtpeval-evaluation-acceptance-2026-10-09).

The earlier implementation and acceptance covered
[public-landmark access #91](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/91),
[address equivalence #92](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/92),
[V3 soft pace optimization #93](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/93)
and [planner source protection #94](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/94),
plus the separately requested opening serialization and identity-coverage corrections.
The complete CLI flow over the unchanged original V0-V2 and source-protected V3 is
accepted as engineering integration evidence. Final scores, check inventories and usage
are saved; repeated native/quality replay preserves all originals and stopped attempts.

That Sydney integration retained the V0 Australian Museum address assessment and
Powerhouse indoor-access uncertainty. Further official evidence acquisition or policy
changes need their own scope. The latest V3 starts with zero pace deduction and makes
no Repair attempt; earlier actual Repair improvement remains separate dated evidence.
V0 baseline changes and formal research also remain separate. Consumed one-use packages
are not retry authority, and this acceptance grants no version freeze or remote Git
delivery. GitHub Issues own specifications and live task state; consequential decisions, results
and evidence are summarized in the [acceptance record](docs/records/evaluation/intake-identity-usage.md#complete-v0-identity-coverage-acceptance-2026-10-09).

## 7. Keeping this file current

Maintain current capability, version boundaries, latest validation, unresolved limits
and authorized next work in place. Keep one current validation checkpoint, with explicit
scope and date. Summarize consequential decisions, failures, results, limitations and
evidence in existing topic records, retaining causal sequence only where it explains
the result. Routine operations belong in Git, Issues or chat. Follow
[AGENTS.md Documentation](AGENTS.md#documentation); do not append each completed task
to this file.
Historical records and previous PROJECT revisions do not override current scope or
renew execution authority. Use [docs/README.md](docs/README.md) for detailed navigation.
