# Independent evaluation architecture

RTPEval consumes selected planner outputs, acquires independent evidence and produces
source-bound quality, resource and research reports. Use [experiments](guides/experiments.md)
for new runs and [verification](guides/verification.md) for saved results. The five
[technical contracts](README.md#detailed-technical-contracts) own wire-level rules.

## Separation from planning and benchmark construction

The evaluator assesses an explicit curated batch. It does not select replacement
cases or decide benchmark completion. Planner caches, internal validation and target
disappearance are not independent factual truth. Original result bytes, hashes,
claims and source pointers remain intact.

Version-neutral projection separates visits, protections, references and transport.
V0 uses declared transport activities; V1–V3 use application transfers. Ignored sources
retain diagnostics without supplying fallback occupancy. Independent observations
retain their identity, provider, query and temporal applicability.

## Implemented module boundaries

| Capability | Responsibility | Contract |
| --- | --- | --- |
| Intake, identity and usage | Source validation/projection, independent correspondence, snapshots and resource accounting | [Intake/identity/usage](contracts/0002-intake-identity-usage.md) |
| Requirements and schedule | Reviewed obligations, count bounds, occupied time and protections | [Requirements/schedule](contracts/0003-requirement-schedule.md) |
| Opening and routes | Independent applicable evidence and separate availability/quality outcomes | [Opening/routes](contracts/0004-opening-routes.md) |
| Final quality and human review | Common-mask scores, density deductions, anonymous packages and imported answers | [Quality/review](contracts/0005-quality-human-review.md) |
| V3 stage pairs | Source-driven draft/final correspondence and independent paired deltas | [Pairs](contracts/0005-quality-human-review.md#v3-pairs) |
| Controlled Repair | Isolated frozen real post-primary execution with target/control review | [Controlled Repair](contracts/0001-evaluation-artifacts.md#controlled-repair) |
| Mechanisms | Selected-source observations and opt-in passive execution capture | [Mechanisms](contracts/0001-evaluation-artifacts.md#mechanism) |

`evaluation_run.prepare_run / execute_run / replay_run` composes native final-quality
consumers. Preparation freezes sources, reviews, contexts, limits, prices and code;
execution persists independent evidence and failures; replay sends nothing.
Processing status, acquisition completion and unresolved facts are separate.

The installed `uv run rtpeval evaluate` commands expose this lifecycle. Optional
pair, controlled and human work has its own scope/material. Development helpers in
`backend/evaluation/tools/` are not Product stages or scoring dependencies. Product
planning does not import the evaluator.

## Batch and research extensions

`uv run rtpeval suite` composes reports over explicit accepted case revisions.
`uv run rtpeval research validate` and `report` process declared original-input
populations offline. Optional suite attachments retain each track's lineage and
population; adding reports does not rescore Primary.

### Research track relationships

Original requests, planned version/repetition slots and all attempts define research
populations. Completed four-version bundles are a qualified subset. First dispatch
owns primary selection; retries retain their separate outcomes and consumption.

| Track | Evidence and unit | Output |
| --- | --- | --- |
| Population | Inputs, fixed selection profile and all attempts | Planned/dispatched completion with unresolved bounds |
| Opportunities | V1/V2 stage captures and independent associations | Canonical discovery/admission/enrichment/supply/scheduled sets and origin partitions |
| Relevance/coverage | Independently reviewed interests/venues; optional pinned census | Relevant sets, compatible V2-minus-V1 differences and optional strata |
| Repair | Four-final, same-run V3 pair or separately controlled sources | Final differences, stage deltas, continuity and target/control preservation |
| Tradeoffs | Exact selected attempts, native quality/usage/cost and all-attempt ledger | Compatible benefits/resources, failed/retry consumption and completion |

Canonical venues, corpus entities, request/repetition groups and controlled targets
are different units. Missing stages, reviews, coverage and usage remain unavailable
or partial. Producer fates do not establish relevance or independent repair success.
Capture adds no provider/model calls; local capture overhead is unmeasured.

Saved report revisions preserve prior receipts. Network-denied replay reconstructs
report semantics under checked bindings. The [suite contract](contracts/0001-evaluation-artifacts.md#source-bound-suite-lifecycle)
owns composition; [additional reports](guides/verification.md#inspect-additional-reports)
owns operator handoff.

## Scoring semantics and uncertainty

| Term | Meaning |
| --- | --- |
| Submitted group | One request and selected source-linked version artifacts; inclusion is not quality |
| Claim | A proposition in submitted output or a reviewed obligation |
| Independent observation | Separately acquired evidence with identity/query/time applicability |
| Physical association | Verified venue usable for matching, hours and coordinates without erasing original grounding FAIL |
| Identity judgment | Version-scoped program checks or V0 model correspondence with independent facts |
| Compliance | Outcome against a criterion, separate from evidence availability |
| Access reasonableness | Fallible missing-hours assessment; PASS does not establish factual hours |
| Common mask | Explicit shared comparison dimensions with missing evidence visible |
| UNKNOWN | An unresolved outcome, not PASS or a measured zero |
| Blinded review | Preference assessment without version attribution or automatic scores |

[Identity rules](contracts/0002-intake-identity-usage.md#version-specific-identity-evaluation)
separate common requirement subjects, V0 correspondence and V1–V3 API/program checks.
Physical association may support downstream matching while original grounding FAIL
remains. Recognizing a venue does not fulfill every obligation component.
[Count bounds](contracts/0003-requirement-schedule.md#count-bounds-and-completeness)
retain exact dates, counts, subjects and uncertainty. Overlapping protections share
blocking spans but retain separate obligations; they add no non-overlap score units.

Opening/routes distinguish proven FAIL, complete PASS and unresolved evidence.
Reports expose availability, denominators and burden. Common-mask arithmetic cannot
hide UNKNOWN by shrinking a denominator or treating unavailable dimensions as zero.
Structural acceptance certifies neither fees nor access.

The [declared-population profile](0003-itinerary-transport.md#numerical-scoring-policy-and-limits)
freezes candidates before acquisition and distinguishes missing facts from missing
population structure. Historical policies and receipts retain their original meaning.

## Paired, controlled and mechanism boundaries

A V3 pair compares its own pre-repair draft and final primary under one compatible
snapshot; the draft is not an independently run V2 result. Correspondence uses
validated edit lineage before content fallback/residual review. Unresolved local
correspondence need not invalidate a valid paired aggregate. The two-stage mask is
separate from the four-final mask. Exact unchanged access contexts share one judgment;
Primary evidence retains its original bindings.

Controlled Repair isolates actual frozen V3 execution and independently reviewed
target/control outcomes. Mechanism reports read selected saved observations. Internal
acceptance, independent quality and resources remain separate; final output cannot
reconstruct missing execution history. See [pair evidence](records/evaluation/v3-pair-report.md).

## Batch and benchmark terminology

| Term | Meaning |
| --- | --- |
| Qualifying group | Request plus V0–V3 outputs whose workflow completion is established, regardless of quality |
| Benchmark candidate list | Available qualifying groups; adding one does not initiate evaluation |
| Evaluation batch | Explicit user-selected groups; size is not hardcoded in the evaluator |
| Requirement Specification | Independently authored/reviewed obligations from the complete original request |
| Evaluation snapshot | Preserved independent external evidence, not absolute real-world truth |

### Material admission and scenario acceptance

Native admission establishes source/review/envelope eligibility. Evaluation completion
means reports were produced under recorded evidence and policies, possibly with FAIL,
UNKNOWN or unavailable values. Scenario automatic acceptance is the user's review
of selected input, requirements, outputs and applicable reports. Deferred blinded
assessment then attaches real answers to those selections without changing Primary.

Known material/processing defects must be resolved before accepting interpretation;
genuine low quality or unresolved facts can remain valid observations. Source revisions
stay traceable. The [twelve-case index](../benchmark/README.md) identifies accepted
material, and the [staged contract](contracts/0005-quality-human-review.md#staged-automatic-acceptance-and-deferred-blinded-review)
defines the handoff.

### Preparation and decision responsibilities

The [benchmark workflow](../benchmark/README.md#workflow-and-responsibilities) owns
execution responsibility. Separate source-only agents author/review RequirementSpec
and applicable interest, relevance, pace and transport semantics. These are agent
judgments, not human answers. Tools consume the judgments; personal intent comes
from the user and blinded preferences from actual raters.

[Review readiness](guides/experiments.md#independent-requirements-and-activity-review)
distinguishes installed tools from externally prepared judgments. Corpus coverage
and controlled studies remain optional. Execution limits and unresolved defects follow
the benchmark's intervention boundary.

## Requirement and schedule units

| Unit | Definition |
| --- | --- |
| Submitted place claim | Structured scheduled place, independently checked; a descriptive title need not equal its name |
| Transport association | Source-linked directed occurrence pair, without a feasibility claim |
| Obligation check | One reviewed requirement outcome retaining count/date/time components |
| Schedule commitment | A scheduled visit, journey or fixed activity; uncertain timing does not erase it |
| Daily density deduction | Reviewed pace/count policy adjusting total while retaining auxiliary scores |
| Protected blocker | Interval restricting commitments, separate from each original obligation |
| Potential match | Unresolved source occurrence that could affect an obligation |

## Route evaluation concepts

A route candidate is each directed consecutive primary pair on a delivered day.
Submitted departure and evidence-query departure are distinct. A continuous travel
interval cannot cross occupied commitments. Provider duration/distance caps differ
from available time; hard fixed/protected deadlines permit no grace, including DRIVE
reserve. Any proven FAIL may decide a leg while missing component evidence stays visible.

## V3 before/after concepts

Edit provenance records adopted transformations, not quality or venue identity.
Occurrence correspondence first validates lineage, then source content or review.
Complexity alone does not require review if validated evidence resolves it. Stage-pair
masks and final-four masks retain distinct denominators.

## Blinded ranking concepts

A/B/C/D labels are fixed across a task's dimensions; the private version mapping stays
outside rater material. Display preparation removes attribution without altering travel
facts/uncertainty. Ordered tie groups partition all four labels. Unable-to-judge and
not-applicable responses provide no ordering. The highest valid complete task/rater
revision is effective; older revisions remain auditable.

Inferred display arrival is labelled and never becomes a submitted claim or score
input. Hidden duplicates test within-rater consistency and are excluded from main
counts. Consistency compares only version pairs ranked in both original and duplicate;
no comparable pairs means unavailable, not perfect agreement.
