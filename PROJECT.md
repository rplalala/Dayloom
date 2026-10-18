# Capstone Project Context

Current source of truth. Updated 2026-10-18.
Detailed design, development and acceptance records are indexed in
[docs/README.md](docs/README.md).

## 1. Purpose and responsibility

This Capstone / Thesis B project builds an LLM-based travel planner for feasible
and reliable itinerary generation. It maintains four independently runnable
versions so their mechanisms remain distinguishable.

Current work covers system design, implementation, engineering validation and
approved RTPEval implementation. Formal benchmark construction/execution,
version-comparison experiments, thesis writing and final research conclusions
require separate authorization. Development smoke results are bounded evidence,
not general quality rankings or automatic version freezes.

[AGENTS.md](AGENTS.md) and its linked policies own collaboration, language, approval,
Git and archive rules; detailed rules are loaded for the relevant operation.
Repository content is English; user-facing development discussion is Chinese.

## 2. Architecture and version boundaries

Use a modular monolith: React frontend; FastAPI API/application/backend services;
shared LLM, evidence, RAG and orchestration components with version-specific
entry points; PostgreSQL + pgvector for TripWorld retrieval.
Accepted Product persistence will add `app` to the same PostgreSQL database; it is pending
implementation. See the [Product persistence overview](docs/0007-application-operations.md#accepted-product-persistence-design).
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

Product UI/API uses V3 and an allowlisted presentation contract. Developer mode
exposes V0-V3 independently. Current input assistance includes destination suggestions,
currency/date controls and optional user-reviewed preference polishing.

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
  result at stops; zero is not a failure constraint. V0-V2 and V3 initial generation
  have no zero-penalty requirement.

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

`config/runtime.yaml` and typed runtime configuration own active limits;
[config reference](config/README.md) explains them. Entry-point deadlines and stage
budgets are distinct. Dated execution allowances do not become runtime defaults.
[Development guide](docs/guides/development.md) owns runnable commands.

Latest offline checkpoint (18 October 2026): merged delivery of accepted
[case-12 r07](benchmark/case-12/report.md#main-worktree-integration) preserves the
original shared Repair corrections and includes remote main `7408df9` (case-08
closeout, PR #189). [PR #190](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/190)
merged as `8bedb15`; local main is synchronized, private migration is verified and
Issues #163/#184 are completed. Blinded human review remains deferred. The initial
full backend run completed with **4,608 passed,
16 skipped and seven failures**. Three junction-fixture failures passed unchanged
outside the sandbox. Four deadline-telemetry parity comparisons received a test-only
normalization correction; both affected modules then passed **24 tests**. No failures
remain unresolved; a second full corrected run was not performed. Ruff and formatting
pass for all 38 changed Python files. Independent Standards and Spec integration
reviews and correction rechecks report zero actionable findings. The skipped
environments remain unverified; frontend code was unchanged and was not retested.

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
  studies, real human assessment and final research conclusions need their covered scope.

Detailed engineering history is indexed in [records](docs/records/README.md), including
[evaluator records](docs/records/evaluation/intake-identity-usage.md),
[V3 development](docs/records/v0-v3/v3-development.md) and
[shared transport validation](docs/records/v0-v3/transport-responsibility-smoke.md).
Ignored logs, artifacts and thesis notes are local evidence, not project authorities
or guaranteed fresh-clone assets.

## 6. Next work and authorization boundary

Product backend persistence is accepted and pending implementation under
[#119](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/119), with children
#120-#123. It covers seven `app` tables in the existing PostgreSQL database,
JWT authentication with PostgreSQL `token_version`, profiles and owner-scoped storage
of only final V3 Product results. The [Product design overview](docs/0007-application-operations.md#accepted-product-persistence-design)
summarizes the boundary; the Issue owns detailed fields, constraints and acceptance.
Current scope covers documentation synchronization and Issue documentation requirements.
Code implementation, migration execution and frontend implementation/refactoring/testing
remain deferred. Backend implementation starts with #120 when separately authorized.

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
Suite engineering acceptance uses synthetic saved material and injected transport;
formal benchmark execution and paid acquisition remain separately authorized.

The [benchmark workflow](benchmark/README.md#workflow-and-responsibilities)
accepts automatic input/report evidence case by case, including V1/V2 candidate
POI process analysis and V2/V3 Repair process analysis. Corpus measurement,
coverage sidecars and corpus reporting are optional studies. Separately authorized
consolidated blinded review uses the same accepted outputs and adds independent
human reports without changing primary scores. The
[staged acceptance contract](docs/contracts/0005-quality-human-review.md#staged-automatic-acceptance-and-deferred-blinded-review)
owns that handoff; the benchmark README owns the detailed sequence, responsibilities
and final-case layout. [Common workflow #126](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/126)
records common workflow adoption; [parallel batch #151](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/151)
owns active case-03–12 dispatch, budgets and worker integration under the
[parallel workflow](benchmark/README.md#parallel-sessions-and-integration).
The coordinator stays in the main worktree; five workers own disjoint case queues.
[Adoption plan #138](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/138)
owns case-01 workflow acceptance. The active set has 12 requests in four groups of three, following the
user-approved 16 October 2026 selection revision. Former case-14 becomes case-12
and former 12/13/15 are retired unexecuted. Cases 01–03/06 retain their selected data.
Case-07 retains its accepted generation
and scores with its canonical input aligned to accepted revision 2. Earlier
researcher decisions remain source-bound when current material is replaced. Their V3 paired views
and case-09's paired view were separately refreshed under the common access policy on
17 October 2026; the [refresh record](docs/records/evaluation/v3-pair-report.md#paired-access-refresh-2026-10-17)
owns exact outcomes and bounds. [Case-09](benchmark/case-09/report.md#acceptance) was
automatically accepted on 17 October 2026 with its updated pair and disclosed limitations;
blinded review is deferred. Its accepted package and required private evidence are
integrated into the main worktree; [delivery #158](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/158)
tracks publication and preserved validation limits. The
benchmark index owns coverage, historical mappings and the revised pending dates. The [accepted selection index](benchmark/README.md#accepted-selections)
locates researcher decisions, exact datasets and stated limitations. The authorized
18 October [current-data replacement](docs/records/evaluation/accepted-case-compatibility.md#current-data-replacement)
directly updates 04/05/09/11, including the five missing generations, fresh 04/05
Primary and 04/05/11 independent pairs. Current candidate/relevance/Repair/resource
views and canonical inputs are aligned. Unchanged donors retain their exact sources;
case-09's pair is explicitly retained on its historical runtime and unchanged V3.
Only one current public dataset is kept; former native evidence and Git history remain
immutable. Updated material does not silently extend researcher acceptance.
Case-05 revision 3 /
input revision 2 and its integrated CLI GBK and Repair timing corrections were accepted
on 16 October 2026 Australia/Sydney, following main-worktree tests and source-bound
verification. That historical selection remains in immutable native archives; the current
26–30 October dataset is identified by the replacement above.
[Case-05 acceptance](benchmark/case-05/report.md#acceptance) owns its exact scope,
including UNKNOWN and producer-runtime replay limits. Blinded human assessment
remains deferred. Git publication remains separately authorized; the retired former
case-15 remains unexecuted.
Case-07 execution revision 3 / input revision 2 was separately accepted on
16 October 2026 with partial V2 discovery, 108 relevance UNKNOWNs and unverified
whole-trip EUR 650 affordability. Its
[acceptance record](benchmark/case-07/report.md#acceptance) owns the selected
materials and limitations. Issue #172's prospective activity contract and these
sanitized materials are delivered through [PR #174](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/174); historical results remain unchanged.
Subsequent runs report primary scores and pause before further diagnostics.

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

Current local implementation and acceptance cover
[public-landmark access #91](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/91),
[address equivalence #92](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/92),
[V3 soft pace optimization #93](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/93)
and [planner source protection #94](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/94),
plus the separately requested opening serialization and identity-coverage corrections.
The complete CLI flow over the unchanged original V0-V2 and source-protected V3 is
accepted as engineering integration evidence. Final scores, check inventories and usage
are saved; repeated native/quality replay preserves all originals and stopped attempts.

Remaining itinerary follow-ups are the V0 Australian Museum address assessment and
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
