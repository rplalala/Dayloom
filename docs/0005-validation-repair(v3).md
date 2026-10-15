# Structured validation and targeted repair

Status: Validation and bounded Repair search are implemented. Integrated offline
verification and independent review of the October 13 redesign are complete;
[the development record](records/v0-v3/v3-development.md#bounded-repair-search-and-selected-result-integration-2026-10-13)
preserves the regression failures, corrections and final checks.
The [search contract](#accepted-bounded-search-redesign) defines exploration,
retained results and proposal strategies.

## Validation is a separate stage

V3 consumes the shared V2 primary result, normalized evidence and source-linked requirements.
The validator produces structured findings with evidence/applicability boundaries. Confirmed
contradictions, missing facts and optional quality observations are not interchangeable.
UNKNOWN never becomes PASS simply because a model offers a plausible explanation.

Validation includes supported requirement, schedule, coverage, repetition and factual
consistency policies. Applicability depends on available evidence and declared scope.
This is planner-internal validation, not the independent evaluator's ground truth.

### Supported findings and factual limits

[Validation](../backend/app/versions/v3/validation.py) emits `PASS`, `CONFIRMED`,
`NEEDS_REVIEW` or `UNKNOWN`; only `CONFIRMED` is a violation. A finding or improvement
target is distinct from the later operation permission. Its supported boundaries are:

| Finding family | Current scope |
| --- | --- |
| Named/semantic and primary policy | Source-bound named inclusion/count/date obligations, supported semantic count/date goals and primary-role/exception policy; arbitrary open text remains unassessed. See [shared semantics](0002-requirements-evidence.md#semantic-qualification-and-multiplicity). |
| Overlap, repetition and coverage | Supported schedule conflicts, unauthorized canonical repeats and minimum coverage; optional quantity/overfull review remains separate. See [counting](0003-itinerary-transport.md#generation-diagnostics-and-counting-contract). |
| Opening | Complete visit containment in adopted structured intervals, with selected-hours provenance and outside-hours magnitude; this is not admission or ticket verification. |
| Route | Actual directed transition bindings and applicable evidence; missing mode/departure/binding remains UNKNOWN. |
| Visitor suitability and budget | Admission eligibility, reservation/ticket possession, special-area access and verified whole-trip affordability remain UNKNOWN. Reported conditions are context, not certified fulfillment. |

[Opening selection](../backend/app/evidence/opening_hours.py) prefers applicable adopted
official date/range facts, then request-window current Places periods and eligible regular
weekly periods. Conflicting, invalid or missing applicable material retains UNKNOWN.
Without an explicit visit binding, the application uses the recorded `obey_place_hours`
scheduling policy. An explicit exterior/non-entry binding cannot acquire an entry-hours
PASS. A missing venue timezone may use the single recognized timezone of related scheduled
places; this is planner context, not the evaluator's independent timezone evidence.
The selected intervals may cover overnight visits; older whole-venue/date-only limitations
in records describe their earlier checkpoints. Even an hours PASS establishes only that
adopted-hours condition, not real-world access or independent factual completeness.

## Authority precedes editing

Target selection and operation permissions are application-owned. Hard protections,
required/excluded identity obligations, fixed time and existing accepted state constrain
each proposed patch. Optional quantity review is recorded separately from minimum daily
coverage. A sparse or overfull day alone does not grant unrestricted rescheduling.

Confirmed opening/route conflicts can authorize duration-preserving retiming of affected
main visits and policy-bounded moves. Delete/replace requires the existing dispensable-visit
and sourced count/date/access protections; the application does not shorten a visit merely
to fit hours. Removed-obligation progress stays distinct from verified resolution, and
retained route endpoints require applicable checks of the actual changed chain.

Repair receives compact current context, canonical candidates, target worksheets, allowed
operations, route options and bounded feedback. Each editable activity includes
application-computed `duration_seconds` for its current
interval, so preservation instructions do not require timestamp subtraction by the model.
The model proposes edits and target dispositions; it cannot author provider evidence or
expand its own operation scope. Invalid structured
output fails before adoption; partial malformed JSON is not salvaged as an itinerary.

## Components, adoption and fallback

The [joint component contract](#joint-repair-and-component-atomicity) defines dependencies,
ordering, adoption and safe fallback. Independent rejected components preserve earlier
accepted improvements; missing facts never become a successful repair claim.

## Transport and resource boundaries

Repair scope inherits the shared hard transport-mode set. The Repair entry intersects
its scoped modes with the authoritative requirement set before candidate work or model
proposals. Cached DRIVE evidence and unchanged saved transfers cannot bypass a
WALK/TRANSIT restriction; final validation checks adopted modes again.

Changed real adjacencies require both neighboring legs to be considered at applicable
departure times. Representative route preparation is not insertion feasibility. Fixed
occupancy, required visits, daily burden and separately represented application reserves
remain binding. Missing evidence permits only the explicitly coded conservative fallback,
not fabricated driving or transit estimates.

Rounds, per-stage work and total request deadlines are bounded by runtime configuration.
The V3 runner establishes the whole-request deadline before owned retrieval setup; later
stages cannot reset it. Exhaustion, cancellation, no authorized target, rejected proposal
and accepted repair are separate recorded outcomes. Final Nearby runs after final primary
selection and cannot modify the accepted primary plan.

Retrieval initialization is lazy. If the request expires before its factory runs, no
runtime exists to release. A factory-created runtime is released once on timeout or
cancellation; a caller-owned runtime remains caller-owned. Offline deadline regressions
must establish which phase was reached before asserting its resource lifecycle, rather
than relying on a short wall-clock delay to select that phase.

Accepted draft and final selection use the shared
[source-fact ownership boundary](0003-itinerary-transport.md#scheduled-activities-and-references).
Final selection includes original supply and the verified Repair whitelist, so retaining
or retiming a visit preserves its provider name and complete address just as add/replace
does. This application normalization requires no extra model/Google call and does not
make the read-only validator mutate its input or certify independent ground truth.

## Soft pace objective

V3 Repair aims for zero soft pace deductions under the existing daily-density table.
Zero is an optimization objective, not output validity or a failure gate. The
`quantity_review_enabled` flag enables this optional quantity optimization; opting out
preserves hard Repair. A resolved pace policy supersedes the generic 2-5 quantity
target on that date. Minimum daily coverage and hard visit protections remain separate.

Read-only validation counts primary visit occurrences, including assessed visits that
the model labels as generic; Nearby, transport and unlinked filler do not count.
`soft_pace` findings retain source-linked policy, count, penalty and zero-penalty counts.
Positive known penalties are review targets, never CONFIRMED violations; unavailable
policy/roles/counts remain diagnostic uncertainty without guessed edit authority.
The numeric curves live in `backend/pace_policy.py`; independent evaluation retains
its own reviewed input policies and evidence rather than consuming planner interpretation.

The application permits bounded additions or removal/movement of dispensable visits,
then reuses existing mandatory count/date/time, role, coverage, route/occupancy and
budget checks. [Search and retention](#exploration-and-retained-result) use aggregate
deductions over the original comparable dates. Individual dates and intermediate states
may worsen without becoming the delivered result. No role relabeling is an edit operation,
and retained penalties do not fail V3 generation.
`soft_pace` summaries in V3 outcome and stage result expose before/after days and mean,
`reached`/`residual`/`unavailable` state and `is_failure_constraint=false`. Existing
round patches, stop reasons and actual usage remain authoritative. V0-V2 and V3 draft
acceptance gain no zero-penalty condition; independent evaluation still scores all normally.

Offline tests exercise authorization, regressions, component interactions, rejection and
fallback with controlled evidence. Bounded historical live repairs demonstrate only their
observed paths. They do not establish universal improvement or factual completeness, and
do not retroactively validate later code. V0/V1/V2 retain independent paths without this
repair stage.

Implementation owners: [runner](../backend/app/versions/v3/runner.py),
[validation](../backend/app/versions/v3/validation.py),
[acceptance](../backend/app/versions/v3/repair_acceptance.py),
[components](../backend/app/versions/v3/repair_components.py),
[search](../backend/app/versions/v3/repair_search.py),
[deletion](../backend/app/versions/v3/repair_deletion.py),
[replanning](../backend/app/versions/v3/repair_replan.py) and
[service](../backend/app/versions/v3/repair_service.py).

## Request flow and ownership

The default-disabled post-primary hook in the shared graph runs after primary identity/date
checks and before one final Nearby stage. V3 does not rerun interpretation, initial discovery
or primary generation. Request resources, caches, send/failure records and the request
entry deadline are shared. Repair counters and its deadline start once per stage.
The immutable draft, original report, fairly reassessed draft, component proposals,
exploration itinerary and best retained itinerary remain distinct. Final source normalization,
schedule, semantic assessments, transfers, validation and Nearby bind the selected result.
Nearby references never supplement primary counts.

## Per-leg mixed transport

`repair_transport.py` uses the soft WALK, TRANSIT, DRIVE preference. Supported explicit
requirements restrict allowed modes. No raw preference or note keywords are interpreted.
Existing applicable evidence for any allowed mode is examined before sending another query;
existing DRIVE can be used without a ceremonial TRANSIT call. Sent failures retain their
request key; a failed TRANSIT query can be followed by a distinct allowed DRIVE query.

| Mode | Automatic selection window | Occupancy |
| --- | --- | --- |
| WALK | Provider distance <=3 km and duration <=45 min | Provider duration |
| TRANSIT | Applicable provider total duration <=45 min | Provider total, without duplicate access walking |
| DRIVE | Provider driving duration <=30 min | Provider duration plus 10 min application reserve |

These values come from runtime.yaml, not user statements. The 2 km WALK / 5 km motor
geographic prefilters support discovery and missing-route screening; applicable provider
options proceed to temporal, burden and detour checks. They are not permanent place labels.
Missing routes permit only the existing conservative WALK <=1 km / 45-minute reservation;
no driving estimate is inferred from coordinates. All chosen legs must fit one continuous
available interval, respect fixed occupancy and both adjacent visits, and preserve the
stage-original daily added traffic limit of 90 itinerary minutes. DRIVE reserves count.
No comparable original route means no invented baseline credit.

Preparation rotates active addition opportunities by target, using a nearest real anchor
and directed options rather than fetching the whole pool in three modes. This provisional
anchor/time is explicitly not insertion feasibility. Retime/delete and other actual changed
chains obtain necessary routes after legal patch construction. Final binding checks every
changed real adjacency, including both sides, with its actual departure. TRANSIT remains
exact-time-sensitive; basic DRIVE and WALK retain their provider-estimate evidence basis.

## Joint repair and component atomicity

`repair_input_2` uses projection revision `mixed_transport_components_1`: canonical catalog,
separate operation authorizations, protected/current context, compact target worksheet,
transport options, adopted transfers, constraints and bounded feedback. A strict model result
contains edits and target dispositions. Model explanations are not evidence. The application
selects allowed per-leg modes and reserves; the model cannot write provider facts.

`repair_components.py` partitions a maximum of 50 parsed edits using concrete dependencies:
activity, source identity obligation, affected dates/adjacency/elastic roots/daily burden,
protected cost association, parent compensation and shared target. Same-date edits are
conservatively atomic. Common validator kind alone does not link unrelated dates.
New-identity competition across independent dates is resolved sequentially, not by accepting
a duplicate. Malformed structured output fails before partition; no partial JSON salvage.

Components run once in deterministic confirmed/compensation/review order with a stable edit
index tie-break. Each uses the latest working itinerary and runs authorization, schedule,
route acquisition/binding, occupancy adjustment, spatial policy, validator and business
comparison. Dependent deletion and compensation stay together, except existing narrowly
authorized EXCLUDED/unexecutable-visit partial-removal policies. A checked component may
advance soft-pace exploration without promoting the best result. Other goals retain their
verifiable progress checks. A rejected independent component leaves earlier checked
components intact. Final global checks reject an illegal combination; the minimal
safe fallback is the round input if the final combination cannot be justified. There is no
exponential subset search. Actual sends, obtained evidence and failure history never roll back.

Remaining goals continue from the exploration state. Compact component decisions and
localized failures enter existing material feedback. Presentation is not qualification;
a rejected component does not taint unedited candidates. Fingerprints include actual
transport options/bindings and permissions, not just a round number.

## Limits

No global transport optimizer, vehicle-location/parking state, rideshare pricing, detailed
transit navigation, semantic evaluator or arbitrary public-access inference is introduced.
The nearest-anchor preparation is provisional, not exhaustive; exact final TRANSIT departure
may need a fresh bounded query. Conservative same-date components can reject more edits than
a finer proven dependency partition. Budget exhaustion can leave legitimate goals unresolved.
Offline evidence does not prove real provider availability, model throughput or quality gains.

## Target priority and stage accounting

Confirmed/hard obligations precede activated compensation and optional review. Minimum
coverage gaps precede optional quantity review but do not override hard protections.
Unauthorized repeats are automatic policy targets; historical unassessed multiplicity is
not proof that deletion is safe. Deferred targets cannot drive current acquisition or edits.
Dependent deduplication/compensation can remain unpublished until its whole group is accepted.
Only the narrowly authorized removal exceptions permit partial deletion without compensation.

Local proposals and affected-day replanning share at most six actual Repair model sends,
including failed sends, under one 360-second stage deadline shortened by the remaining
request deadline. The default model-round ceiling permits six sends; a lower configured
ceiling can stop earlier. System deletion
has a separate default ceiling of 12 attempts; zero disables that strategy. It does not
consume model rounds or sends, and remains available when model sending is disabled.
All strategies share acquisition counters, evidence cache, actual-send/failure history and time.
Preparation leaves configured reserves for model/recheck/finalization and final Nearby;
the average per-round allocation limits optional preparation, while model and recheck work
may use the remaining hard round allowance without restarting preparation or a failed call.
Local input work counts toward that allowance, and late results cannot consume the recheck
reserve or authorize adoption beyond the hard deadline. Timing details belong to the
[configuration reference](../config/README.md#counting-timing-and-invariants).
Reviews/Profile and official web are not
new Repair acquisitions. Semantic assessment retains separate counters. Expired check allowance
blocks adoption even when a provider returns a usable value. Input overflow and terminal model
failure stop at their declared boundary. The final stage summary compares original and selected
plans. Transport thresholds above are configurable policy, not user facts.

## Pending compensation and publishable state

Deduplication cannot evade counting by moving a visit to another date or changing its role.
Checked proposals choose the retained occurrence using sourced obligations, actual windows
and route context; the application does not always keep the first. Explicit count/date-bound
copies remain protected. The minimum-one rule does not replace the existing conditional
coverage floor merely to permit a deletion.

An otherwise valid deduplication group awaiting coverage compensation may be retained as a
bounded unpublished proposal. The pending group carries affected dates, base-state fingerprint,
edits and proposal days; only a matching current base can reactivate it. Descendant edits stay
in the same atomic group, while independent accepted edits remain publishable. Completion
rechecks the combined group against the current exploration base. System deletion candidates
are checked independently: failed alternatives do not create or accumulate pending edits,
and existing model compensation remains subject to its original atomic checks.
Exhaustion discards pending
dependent windows/transfers without reverting independent improvements or waiving coverage.
Residual repetition/coverage remains explicit incomplete output. Confirmed excluded or
unexecutable-visit removal retains its separately authorized partial-removal policy.

Already assessed candidates may be reused after the semantic preparation budget is exhausted;
new ADD/REPLACE candidates require shared qualification before authorization. Budgets are
request-wide, not reset per round. Terminal semantic model/contract failures remain failures,
not a successful generic Repair fallback. Final Nearby occurs once only after normal finalization,
with no continuation after terminal failure, cancellation or an exhausted request deadline.
Implementation: [pending groups](../backend/app/versions/v3/repair_pending.py).

## Accepted bounded search redesign

The October 13 implementation replaces material-repeat early stops and per-date
pace non-regression with bounded exploration and separate final retention.
The [glossary](../GLOSSARY.md) distinguishes exploration from final selection.
[Specification #139](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/139)
owns implementation scope and live progress.

### Exploration and retained result

Maintain an exploration itinerary separately from the best retained itinerary.
Prioritize confirmed/hard goals and applicable minimum coverage before optional pace.
For pace evidence, optimize aggregate deductions over the fixed set of dates whose
original deductions are known. Never drop a formerly comparable date or treat missing
evidence as zero. An improvement on known dates may coexist with an unavailable overall
objective; newly available dates do not silently change the comparison denominator.

An authorized, checked intermediate state may have equal or greater pace deductions
than the best retained itinerary. For example, daily counts `3,2,3 -> 2,3,3 -> 2,2,3
-> 2,2,2` may remain a search path even though its first move has no aggregate gain.
Such a state is exploration, not a claimed improvement. Temporary soft regression
does not authorize new hard/protection violations, bypass required checks or erase
unresolved original findings. Existing dependent compensation remains unpublished
until its applicable conditions are met.

Promote a publishable improvement under those priorities to the best retained result.
Preserve it when later proposals are rejected, exploration worsens or limits stop work.
At finalization, return that result with its matching schedule, candidate/source bindings,
semantic assessments and arrangement evidence, or the original draft when no improvement
was found. Report residual and unavailable goals explicitly. Neither intermediate acceptance nor
internal pace progress establishes an independent quality-score improvement.

### Proposal strategy and affected-day replanning

The application enumerates a bounded set of already authorized deletions of dispensable
visits and validates them without a Repair proposal model call. Deletion still uses the
same requirement, coverage and changed-adjacency checks as model-proposed operations.
Validation can require service calls and consumes the shared deadline and acquisition
limits. The system does not blindly trim counts or choose protected visits for removal.

Use local edits before affected-day replanning when they offer a viable next step.
Local nonprogress switches the next model proposal to a distinct affected-day arrangement
prompt and structured context, leaving time and model
capacity for replanning rather than consuming the entire allowance first. Replanning
may jointly edit affected dates when a move or other dependency links them. Unaffected
dates remain unchanged; this is not a fresh whole-trip primary-generation run.
Replanning produces structured edits through the existing permission and validation
path. Linked dates include original move and compensation dependencies. Only existing
authorized peer operations can enter that closure; unrelated dates remain outside it.
Mandatory visits, fixed commitments, source identities, visit durations and application-owned
transport remain protected. Original source-date and destination permissions are not rebased
after a move, so successive steps cannot bypass the original move limit.

Reuse existing candidates and applicable evidence first. If they cannot support an
authorized next step, bounded discovery and qualification may introduce new POIs;
necessary place, opening and route acquisitions share the existing stage limits.
Missing required evidence blocks adoption instead of becoming a plausible model fact.

### Feedback, deduplication and applicability

Unchanged evidence alone does not stop exploration. Rejection feedback identifies
attributable conflicts and supports a different authorized proposal using the same
materials. Deduplicate semantic proposals against their base itinerary, permissions
and relevant evidence; differences in timestamps or explanation text are not progress.
Skip a previously failed equivalent proposal without declaring other operations exhausted.
Detect repeated exploration states so equal/worse transitions cannot create a cycle.

Assess quantity applicability, minimum coverage, deletion authority and route feasibility
separately. A `not_assessable` quantity diagnostic is not an unconditional ban on reducing
counts if deletion has an independent authorization and the necessary checks can be
confirmed. It supplies neither guessed edit authority nor a coverage PASS. An actually
unresolved condition required for that operation still blocks adoption.

### Outcomes and compatibility

The [shared limits](#target-priority-and-stage-accounting) apply across every state and strategy.

Stop when applicable authorized goals are complete, shared limits prevent further work,
required evidence is unavailable or the bounded authorized strategies are exhausted.
Preserve existing terminal failure/cancellation semantics; there are no hidden retries.
Do not equate one rejected proposal, unchanged materials or a skipped duplicate with
all strategies exhausted. Record each proposal's base state, strategy, check outcomes,
exploration transition, best-result promotion, actual calls and final stop reason.
Residual soft deductions mean partial/no improvement, not a successful zero target.

`search_version=1` distinguishes new search records from the historical adopted-state chain.
Records identify strategy, base state, exploration transition, best promotion and the selected
round. A null selected round in the new version returns the original draft. Selected provenance
includes necessary intermediate ancestors and excludes discarded exploration after that result.
Historical records retain their original interpretation without invented strategy observations.
Model usage, semantic calls, deterministic attempts and provider acquisitions remain separate;
missing usage is unavailable rather than a measured zero.

Offline verification uses `run_repair_stage`, actual V3 initialization/finalization and native
saved-result readers with controlled external dependencies. These checks establish implemented
behavior and compatible records, not live model effectiveness.

Paid case execution is separate from implementation checks. Preserve original case-01
results; controlled original-draft comparisons require sufficient retained context and
must disclose scripted dependencies. Any later fresh V3 result requires its own provenance
and independent scoring. Follow the [primary-score handoff](../benchmark/README.md#workflow-and-responsibilities)
before supplements or process diagnostics.
Case acceptance follows the
[staged automatic acceptance contract](contracts/0005-quality-human-review.md#staged-automatic-acceptance-and-deferred-blinded-review).
The [initial case-01 record](../benchmark/case-01/report.md#acceptance) identifies
its accepted outputs and limitations. Separate engineering diagnostics do not
replace case evidence or add mandatory strategies to ordinary Repair execution.
