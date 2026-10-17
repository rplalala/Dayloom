# Reviewed requirements and schedule metrics

Current Ticket 05 contract, implemented and offline validated. Updated 2026-10-17.
This file owns RequirementSpec authoring/wire, obligation semantics, time/occupancy preparation,
non-overlap units and descriptive schedule measurements. It consumes accepted immutable intake
and independent identity; it calls no planner, model, provider or database. Optional V3 stages
can be scored independently; the implemented [Ticket 10 paired report](0005-quality-human-review.md#v3-pairs)
owns cross-stage deltas and continuity.

<a id="rtpeval-requirement-spec-contract"></a>
## RequirementSpec ownership and source linkage

Upstream preparation authors `requirement_spec.json` from the complete original Input
and obtains independent review before intake. Native `rtpeval_requirements_1` records
the actual reviewer and time; it does not establish that the reviewer is human. The
installed producer handoff requires separately operated external Codex author/reviewer
agents and bound execution/transcript provenance under the
[external handoff contract](0002-intake-identity-usage.md#external-requirements-handoff).
Direct reviewed material and historical user-reviewed preparation retain their actual
provenance. No agent execution is relabelled human review. Requirements are never copied
from planner interpretation or injected into planning.
Reviewed meaning, independent identity and external facts are separate. The rater sees the
original request, not this preparation file. Soft preferences remain descriptive, and an
unimplemented measurable obligation is retained as unsupported rather than silently softened.

`rtpeval_requirements_1` includes `spec_id`, `revision`, `group_id`, complete `input_sha256`,
`review` (`status=reviewed`, `reviewer_ref`, `reviewed_at`), `subjects`, `obligations`,
`soft_preferences` and `unresolved_items`. Each subject has a nonempty, unique `subject_id`
and preserves original wording. Identity preparation uses `place_name` or `wording`, plus
optional reviewed `location`; absent usable wording stays unavailable, not a guessed name.
Subject IDs/wording are independent of planner IDs.
Current identity policy shares these semantics and independent acquisition evidence,
but supplies one target identity per submitted version. Requirement checks select their
own version's target, compare adopted target/visit IDs and then evaluate counts, dates
and time conditions. V0 model target results cannot satisfy V1-V3 obligations or the
reverse. Target FAIL is retained as a failing component; unresolved identities retain
possible occurrences and UNKNOWN bounds. No name-only fulfillment fallback is used.
Explicit historical report replay retains its former shared-target semantics.
Each explicit clause retains a supported obligation or a source-linked unresolved/unsupported
item and reason. Reviewed empty obligations are valid; omission of review/material is not.
Changing meaning creates a new revision and requires dependent replay.

Source references use original top-level `field_path`, verbatim `quote`, zero-based `occurrence`
and optional paired `offset_start`/`offset_end` half-open Unicode-code-point offsets.
Text quote occurrence defaults to zero when omitted; supplied offsets must match that exact
occurrence. Structured fields can be referenced directly without a quote.
No fuzzy quote, nested source path, arbitrary afternoon clock range, hard quota from a subjective
wish, access/entry distinction or factual budget PASS is inferred. Trip facts remain in Input.
Mechanically contradictory executable payloads require upstream correction; semantic uncertainty
does not become a planner quality failure merely because the specification was reviewed.

<a id="rtpeval-requirement-schedule-contract"></a>
<a id="obligations"></a>

## Executable obligations and cardinality

Keep the existing `rtpeval_requirements_1` envelope, identifiers, review and
source references. Every obligation has a nonempty unique `obligation_id`, nonempty `kind`,
nonempty original-input `source_refs` and `resolution=resolved|unresolved|unsupported`.
Use `subject_ref` when the kind requires a subject. Non-resolved obligations retain a
nonempty `reason` and no invented executable values; review does not change their resolution.
Resolved obligations use only their common fields and the kind-specific fields below.
Executable fields below live directly on each obligation;
do not infer them from result prose. Unresolved/unsupported records retain reason
and source, without invented executable values. A resolved record with an unknown
operator is returned for specification correction instead of silently executing it.

| Kind | Executable fields |
| --- | --- |
| `daily_visit_count` | `date`; `scope=primary_visits`; `count={mode:minimum\|exact,value:nonnegative integer}`. All primary occurrences on the date; no venue subject. |
| `transport_modes` | `scope=whole_trip`; nonempty unique `allowed_modes` drawn from `WALK`, `TRANSIT`, `DRIVE`. No venue subject or invented mode claim. |
| `required_visit` | `subject_ref`; `count={mode:minimum\|exact,value:positive integer}`; optional `distinct_dates` boolean (omission means no extra distinct-date constraint); `date_obligations` array of `{date,count_mode:minimum\|exact,count:positive integer}` (omission means none). |
| `excluded_visit` | `subject_ref`; `scope=whole_trip\|specified_dates`; `dates` is required and nonempty for specified dates, absent for whole-trip scope. |
| `protected_time` | `date`; `interval={kind:full_day}` or `{kind:clock,start:HH:MM[:SS],end:HH:MM[:SS]}`; explicit `scope=primary_visits\|scheduled_commitments`. Clock endpoints are same-day, strictly increasing; `24:00` is allowed only as the end. |
| `fixed_visit_time` | `subject_ref`, `date`, `match=single_visit\|at_least_one` and nonempty `conditions`; the multiple-visit mode also requires `repeat_permission_refs` as defined below. |

Booleans are not integers. Named-visit counts must be positive; total daily counts also
permit zero. Dates are ISO
calendar dates within inclusive Input trip dates. Duplicate date entries for one
obligation, invalid references, nonpositive durations and unsupported resolved scope
values are material diagnostics. Full-day protection expands to local midnight to
the following local midnight, not a presumed 86400 seconds on a DST date.

`transport_modes` retains the independently reviewed original-input clause and sources.
Requirement/schedule rules 4 expose one check per obligation: permitted claims PASS,
disallowed claims FAIL and missing mode/association remains UNKNOWN. Resolved checks
declare `aggregation_owner=requirements` and count once in that dimension, including
unbound disallowed declarations. The route-policy bridge retains complete mode diagnostics
but excludes that obligation and source-equivalent reviewed policies from route scoring,
preventing the same mode violation from being counted in both dimensions.
Unsupported/unresolved obligations retain their original meaning and incomplete/UNKNOWN
status until explicitly resolved. Inputs without this new kind retain rules 3 and
their historical report hashes unless a separately reviewed daily total selects rules 5;
stored specifications/reports are never upgraded in place.

For an explicit named-place visit obligation without stated repeat/count meaning,
upstream preparation writes `count={mode:exact,value:1}` for the requested trip and
obtains review. Evaluation
reads the explicit reviewed count; it does not infer a default from request prose.
A second confirmed occurrence violates exact one; a potential second occurrence can
prevent PASS. This authoring rule applies to actual reviewed named-place obligations,
not every venue the planner selects or source-grounded soft interests.

Explicit two/three/repeated visits follow their reviewed count/date semantics. A
numeric exact count is never weakened into minimum one. Explicit minimum counts retain
minimum semantics; clearly allowed repetition enables the multiple-visit time mode
below. A vague numerical quota is not invented for a permission such as multiple
visits; retain unresolved count meaning if it cannot be represented independently.

For `required_visit`, global occurrence count and date counts are separate conditions.
`distinct_dates=true` requires the global count to be represented on at least
`count.value` distinct requested dates; exact count still constrains occurrences.
Per-date counts are evaluated on their named date; they do not imply global exactness.
All explicit components must hold, and they remain inside one parent check.
Known contradictions (for example global exact two with minimum two on each of two
different dates) require upstream correction. An unresolved apparent conflict remains
visible rather than being labelled a planner failure. Do not combine separate
obligations into a new quota or add tests for absent fields.

Whole-trip means inclusive original Input trip dates for both global REQUIRED counts
and whole-trip EXCLUDED checks. Use requested `declared_day` values for structural
count/date reporting when the submitted civil-date fields agree; an absent timezone
alone does not erase an explicitly declared calendar day. Extra declared output dates
with consistent outside-trip timestamps are diagnostic observations outside these
obligation counts and descriptive denominators. A visit after the trip cannot satisfy
a required visit within it. Do not add extra days to the requested denominator.

Where a supplied timestamp contradicts its declared day, or independently supported
zone/offset interpretation contradicts the required date, preserve the source occurrence
but do not assert a confirmed scoped count. It is a potential match for every requested
date/trip scope that the retained uncertainty could affect. This also applies to extra
declared days with contradictory potentially in-trip timestamps. Do not choose whichever
date helps PASS. Invalid/missing clocks need not erase a consistent declared calendar
count; precise fixed-time/occupancy checks still require valid temporal interpretation.
These are structural scheduled-visit counts, not proof of actual attendance.

### Dated total visits

An independently reviewed `daily_visit_count` represents an explicit total for one date,
such as exactly one sightseeing visit. It uses original Input sources and no fabricated
venue subject. It does not replace a named-venue count, category preference or full rest
day. Intake/preparation validate date scope, strict nonnegative count, supported selector
and mechanically contradictory daily totals/full-day protections. A resolved operator
enters the declared requirement population; unsupported obligations still block numerical
preparation until resolved.

The independent scorer counts source-distinct primary occurrences using its own role/date
projection. Repeated visits to one venue count separately. Supporting meals, transport,
free windows and Nearby suggestions are excluded. Venue identity is unnecessary for an
all-primary total; uncertain role or inconsistent date contributes a potential occurrence.
The ordinary lower/upper count rules below determine the check. Zero visits does not
forbid supporting activities or travel; `protected_time` keeps its separate commitment scope.

Reports containing this kind select `rtpeval_requirement_schedule_rules_5`, recording the
independent occurrence policy in the rules hash. Native preparation, scoring and replay
use the same reviewed operator; no Planner counting or verdict function is imported.
Specifications without it keep their prior rules 3/4 selection and report hashes. Applying
the new capability to a previously unsupported clause requires a new reviewed specification
and execution revision, preserving historical material and results.

## Count bounds and completeness

For each subject/date scope, compute confirmed matching occurrences `L` and an upper
bound `U=L+potential_matches`. Under `versioned_api_identity_3`, a verified physical
`place_association` establishes occurrence matches and nonmatches against the
requirement target's version-owned adopted canonical identity. Original claim grounding
remains separate: an occurrence's grounding FAIL does not erase its verified venue,
and a requirement target FAIL still contributes its failing component. The complete
identity report must pass source-bound replay before associations are consumed.
Occurrence source identity prevents repeated imports from counting twice.
Same-venue visits at different source occurrences remain distinct. An unresolved
identity can be a potential match; observed search `candidate_ids` are not exhaustive
and their absence does not prove a nonmatch. Unresolved role records that could be
primary visits remain potential matches, with their reasons and declared dates.
Unresolved subject identity prevents confirmed venue equality; do not compare only
planner supplied IDs or name strings. Missing identity does not erase a known visit.

Historical identity policies without association fields retain canonical-only occurrence
matching. Unverified or conflicting associations remain unresolved even if a canonical
field or candidate list suggests a venue. `requirement_identity` exposes each occurrence's
source, associated/canonical place IDs, grounding verdict and matching basis.
Requirement/schedule rules version 3 records this change; exact reproduction of an earlier
report requires its original rule/code revision, rather than relabeling that report.

| Count condition | PASS | FAIL | Otherwise |
| --- | --- | --- | --- |
| Minimum `k` | `L>=k` | `U<k` | UNKNOWN |
| Exact `k` | `L=U=k` | `L>k` or `U<k` | UNKNOWN |
| At least `k` distinct dates | At least `k` confirmed matching dates | Fewer than `k` potentially matching dates | UNKNOWN |
| Exclusion | No confirmed or potential scoped match | At least one confirmed scoped match | UNKNOWN |

A conjunction's proven failing component establishes parent FAIL; PASS requires all
components PASS, otherwise UNKNOWN. This allows two confirmed visits to satisfy
minimum two despite an additional unresolved visit, while exact two remains UNKNOWN.
Count bounds are conservative; if uncertainty coupling cannot establish a conclusion,
retain UNKNOWN rather than asserting a jointly possible assignment.

One original obligation ID contributes one requirement check, regardless of component
count. Recognized applicable kinds with unresolved semantics or unsupported operators
contribute one UNKNOWN, not an N/A success. Unclassified unresolved clauses whose
applicability cannot be established retain a separate structural availability count;
they cannot be silently deleted to declare a complete score. Unknown executable kinds
require correction. Reviewed soft preferences are outside the obligation denominator.
An explicitly reviewed empty obligation list gives N/A only when there is no
unlinked unresolved content that could represent an applicable obligation.

`obligations` is the only collection generating weighted obligation checks.
`unresolved_items` is a completeness/annotation collection, not a second set of
weighted checks. Each item has `item_id`, `source_refs` and `reason`, with optional
`obligation_ref` or explicit `classification=soft_preference`. A linked annotation
references an existing parent obligation and adds no check; multiple annotations do
not multiply its weight. An explicitly reviewed soft item adds no hard check.
An unlinked, unclassified item retains `requirement_completeness_unresolved`, including
when obligations is empty: the requirement dimension is unavailable, not true N/A.
Recognized unresolved/unsupported hard requirements should be represented as original
obligations upstream; Evaluation never manufactures that parent from an annotation.
Malformed source/parent linkage requires correction. A partial known-obligation report
may still be returned, but no complete denominator or score is asserted until this
unlinked content is resolved or explicitly classified upstream.

## Dated fixed-visit conditions

For an explicit date and subject, support a conjunction of any nonempty selection of:
`start_at=HH:MM[:SS]`, `within={start,end}` (whole visit containment),
and `duration={mode:minimum|exact,seconds:positive integer}`.
Wire: `kind=fixed_visit_time`, `subject_ref`, `date`, explicit
`match=single_visit|at_least_one`, and `conditions` containing those fields.
There is no hidden five-minute time/duration tolerance. End at window end is allowed.
Duration uses resolved instants, including elapsed-time DST effects.

Without explicit repetition/count meaning, preparation selects `match=single_visit`:
exactly one same-subject primary visit in the requested trip must occur on the named
date and satisfy the entire time conjunction. The parent check combines global exact
one with dated time compliance, without adding an inferred extra obligation/check.
Two confirmed occurrences make it FAIL even if one has the correct time. A possible
extra occurrence or uncertain time/date can make it UNKNOWN. PASS requires exact-one
certainty and a fully compliant confirmed visit.

Only explicit original-input permission/requirements for repeated visits enable
`match=at_least_one`. This mode requires nonempty `repeat_permission_refs` with original
Input source references verified using the existing quote/offset convention. It is not
a default, and an itinerary's repetition or a reviewer selecting a mode without source
permission cannot authorize it. Any explicit numeric/date quota remains in its reviewed
required_visit obligation, checked independently. Same-subject reviewed obligations
must be mutually consistent; do not combine a default exact-one parent with an explicit
multi-visit count. Absence of a count for a clearly stated permission does not invent
an exact or minimum number of repeated visits.

In multiple-visit mode, at least one scoped primary visit must satisfy the whole time
conjunction; different visits cannot each satisfy different components. PASS needs one
confirmed fully compliant matching visit. FAIL needs proof that no confirmed or
potential occurrence could satisfy it; otherwise UNKNOWN. Other occurrences do not
invalidate this time-only component, but exact/minimum/date quotas still apply.

All-occurrences conditions, ordinal selection, cross-midnight clock windows, relative
ordering, recurring daily constraints and unspecified afternoon/evening remain
unsupported/unresolved with original meaning preserved. An explicit all-occurrences
meaning remains unsupported rather than weakened to either supported selector.
The author reviews the selector and its cardinality/source basis before submission;
evaluator prose interpretation never supplies it. Mechanically impossible time
conjunctions or contradictory explicit quotas require correction.

Examples (documentation only): "Visit A on Wednesday at 10:00 for at least 60 minutes"
has one trip-wide A occurrence, on Wednesday, satisfying all time conditions. Two A
occurrences violate its single-visit rule. "Visit A twice, with a Wednesday visit at
10:00 for at least 60 minutes" retains exact two in the reviewed count obligation;
at least one Wednesday A must meet all the time conditions. Two visits with neither
meeting the conjunction do not satisfy the time obligation.

<a id="occupancy"></a>

## Independent time, commitments and protected blockers

Preserve original strings. Follow the [shared time contract](0001-evaluation-artifacts.md#time) for half-open intervals,
offsets, IANA zones, unique localization and DST folds/gaps. Never use host timezone,
planner timezone metadata or provider duration to repair submitted timestamps.
Aware endpoints can establish instant relations without localization when their
declared date context is consistent; local-clock requirements need a supported
destination zone. Clock/date mismatch, zone conflict or unsupported overnight activity
leaves dependent checks UNKNOWN. Date coverage can still use explicit declared days.
The [numerical population gate](../0003-itinerary-transport.md#numerical-scoring-policy-and-limits)
keeps known date membership separate from an offset-conflicted instant; its
non-blocking time observations neither repair the interval nor resolve its checks.

Offline time context uses `schema_version=rtpeval_schedule_context_1`, `batch_id`,
`revision`, and `groups`. Each group has `group_id`, exact `input_sha256`,
`timezone` (IANA), `source_ref` (independent evidence or reviewed factual context),
`reviewer_ref` and offset-aware `reviewed_at`. Source hashes/review revision are frozen
with the report. Missing context is permitted as uncertainty, not default localization.
Supplying a context is factual preparation, not another user obligation.

Occupancy decisions use a separate source-linked review envelope
`rtpeval_occupancy_reviews_1`, with batch/revision and records. A record links exact
activity source, review revision, reviewer/time and rationale, with
`occupancy=committed|uncommitted|unresolved` and optional `protected_obligation_refs`.
It never edits role, identity or timestamps. Frozen review decisions must be replayed;
stale source/hash, duplicate active decisions or contradictory links require correction.
Version/projection membership is preserved; one activity ID is not a global key.
This envelope decides activity flexibility and protection-placeholder correspondence
only. It does not point at transfers, select a winning transport alternative, merge
transport sources or invent endpoint associations. Existing Ticket 01 activity reviews
can resolve V0 endpoint/role ambiguity through a new source-linked projection. Unbound
V1-V3 transfers or conflicting journey alternatives remain UNKNOWN/denominator-unresolved
in this slice. Further transport-association adjudication is not silently introduced
as an occupancy review feature.

Fresh primary acquisition additionally checks [post-generation review coverage](0002-intake-identity-usage.md#post-generation-review-readiness).
Missing independent work is a preparation blocker, while a completed unresolved
review preserves the uncertainty below. This gate changes no scoring rule.

For `itinerary_3`, explicit `scheduled` non-primary activities are commitments and
`free_window` activities are uncommitted availability, even when named or movable.
Sourced protections remain separate blockers; declarations do not satisfy obligations.
Independent supplied review decisions retain their separate source-bound path.

Legacy automatic occupancy decisions are limited to established primary visits, selected
transport claims and clearly uncommitted placeholders. Named unresolved primary
visits remain commitments even when their canonical identity is unknown. Generic
locationless placeholders can be uncommitted under the accepted free-time rule;
notes stating a reservation/fixed rest/appointment or conflicting protection prevent
automatic flexibility. Remaining flexibility is unresolved and needs independent
review. No planner lineage or Repair permission supplies that review.

A primary visit is one commitment; a separately reviewed fixed generic activity is
one commitment. Each source-selected logical journey is one commitment. Consistent
V0 segments preserve their disjoint intervals within that journey and one score unit;
the gaps between segments are not occupied automatically. Same-source duplicate
claims contribute sources, not additional commitments. Repeated actual journeys
between different occurrence pairs remain separate even when both are A-to-B.
Unbound source-selected claims remain visible commitments or uncertain association
groups; they are not silently discarded or reassigned. If duplicate-vs-distinct
association is unresolved, the commitment denominator is not established.

A source-distinct V0 declared transport activity with unbound primary endpoints remains
one commitment from its own submitted clock, including travel to generic food/free-time
activities. Its route association remains unresolved. Missing/invalid clock values produce
a time-UNKNOWN commitment, not a missing occupancy denominator; known intersections still
produce FAIL. This adds no canonical venue, route or replacement timestamp. Unbound V1-V3
transfers and conflicting bound journey alternatives retain their existing uncertainty.
This occupancy correction introduced requirement/schedule and route rules version 2.
Physical-association matching subsequently introduced requirement/schedule rules 3.
The current transport operator selects the versions defined above. Old reports retain
their original rule/code revision for exact
reproduction.

Missing/invalid times on an established commitment give a time-UNKNOWN unit. Mode
uncertainty alone does not invalidate otherwise explicit occupancy times; route mode
evaluation remains separate. Conflicting same-journey claims are alternatives, not
two simultaneous journeys. While their alternatives remain unresolved, occupancy is UNKNOWN; clear common
overlap may be reported as a lower bound only if every surviving alternative proves it.
Never turn incomplete `journey.occupancy` into an empty known schedule.

V1-V3 ignored transport activities and V0 ignored transfers contribute no occupancy,
mode or fallback. An absent transfer stays missing: do not generate its interval from
adjacent visits or independent route duration. Missing journey claims are reported
as transport-structure coverage; schedule non-overlap assesses submitted commitments
and does not certify the physical feasibility of an unrepresented journey.

Normalize resolved protections by date and exact scope. Union overlapping/touching
same-scope intervals for occupancy checks, retaining every original obligation ID
and interval. Different scopes remain separate and are filtered by their explicit
meaning. Protections do not conflict with each other. `primary_visits` forbids primary
visits only; `scheduled_commitments` forbids primary visits, selected transport and
fixed generic commitments, while leaving genuine uncommitted free time available.
Do not guess a protection scope from its output placeholder or planner interpretation.

Protected blockers are not additional non-overlap score units. A forbidden commitment
overlapping a protection is FAIL in its non-overlap check; each affected original
protection obligation is also FAIL in the requirement dimension. This cross-dimension
relationship is explicit, as with existing correlated timing/route consequences.
Adding overlapping protection clauses cannot increase the activity denominator.

An output placeholder representing the same protection is not counted as a second
commitment. Equivalence needs source-linked independent review referencing the
original protection; simple temporal overlap or a shared word such as rest is not
enough. Keep an actually separate fixed appointment as its own commitment. Unknown
scope/time/placeholder correspondence retains dependent UNKNOWN or denominator
availability reasons. Unresolved protections are not unioned as guessed intervals.

Nonempty unclear placeholder notes require occupancy review; automatic flexibility requires
no further commitment claim. Exact reviewed protection-placeholder linkage is required to
exclude duplicate occupancy. Timestamp precision supports six fractional digits; greater
precision is unsupported. Original-aware instants can support whole-request overlap without
local context; local-clock duties and per-day attribution need independent context.

<a id="non-overlap"></a>

## Non-overlap units and interval measurements

One established distinct commitment contributes one check. A positive intersection
with another distinct commitment, or with an applicable protected blocker, yields
FAIL. Touching endpoints do not overlap. A commitment with known complete occupancy
and no possible unresolved conflict is PASS; if conflict cannot be excluded, UNKNOWN.
Confirmed conflict overrides unrelated uncertainty. Identity equality does not erase
an overlap between two separately scheduled same-venue visits.

`P/(P+F+U)` is the verified non-overlap fraction on an established commitment set.
Do not create O(n^2) passing pair checks. Unresolved role/flexibility or ambiguous
duplicate correspondence can leave unit applicability/count unknown: report known
units/states, candidate counts and `denominator_unresolved`; no full-scope percentage
is produced from a convenient smaller set. The aggregate report preserves
that availability diagnostic rather than treating it as group-wide N/A.

Report positive unordered commitment-pair conflicts once, separately from
commitment-to-protection conflicts. For each pair, union segment intersections;
do not multiply pairs by segment/source count. Sum-of-pair intersection time is not
union conflict time. Report per-day and request union of instants with at least two
distinct conflicting commitments, protection-conflict union, and their combined
conflict union. Protection-to-protection intersections do not add conflicts.
Report known durations with complete/lower-bound status and unknown record counts.
Do not round seconds before comparisons or treat an unknown interval as zero.

Scheduled occupied time is the union of submitted established commitments only.
Protected reservation union is separate; a combined occupancy/blocker view may be
exported for Ticket 07 but does not select departure or imply a continuous route gap.
Local-day slicing requires valid time context. Retain whole-request known instants
when only daily attribution is unresolved; DST days are not forced to 24 hours.

Non-overlap covers all submitted commitments, including extra output dates; reviewed counts
and descriptive denominators use requested dates. Missing journeys affect structural coverage,
not an invented interval. Opening, route feasibility and auxiliary scores have separate owners.

<a id="descriptive"></a>

## Descriptive coverage, density and repetition

- Date coverage uses inclusive Input requested days as denominator. Report declared
  day-present, any-submitted-activity, known-primary-covered and empty-primary-day
  counts. Possible-primary days have unknown coverage; raw submitted-activity counts
  are not assertions about evaluated occupancy. Missing requested days remain zero
  known visit days. Extra output dates are diagnostic, not extra denominator days.
- Density counts source-distinct primary occurrences on requested declared days,
  including empty days. Report known and possible counts, and `<2`, `2..5`, `>5`
  categories only when role uncertainty cannot change the category. These are
  descriptions, not quantity FAILs in this component. The final and paired reports
  additionally apply the [reviewed daily density policy](0005-quality-human-review.md#daily-density)
  to these counts. Canonical uncertainty does not remove an otherwise established
  visit from density.
- Canonical repetition groups adopted identities only. For venue occurrences `n`
  across `d` declared requested dates, extra occurrences are `n-1`, within-day extras
  are `sum(max(0,n_day-1))`, and across-day extras are `d-1`; the two extra counts
  sum to `n-1`. Report repeated venue counts, occurrence counts and unresolved
  identities separately. Observed known-identity repetition is a lower bound when
  unknown identities could merge/add repetitions.
- Display reviewed minimum/exact/date revisit obligations alongside observed counts.
  Do not allocate duplicate obligations as additive authorization, guess which
  occurrence was necessary, or report an automatic non-required-repetition defect
  ratio. Minimum revisits and visits beyond a minimum are not automatic violations;
  explicit exact-count excess is already assessed in its parent requirement check.

## Report, replay and code boundaries

Report schema `rtpeval_requirement_schedule_report_1` preserves batch/group/run/projection,
input/spec/result and identity/review/context/rules hashes, stable parent check IDs, sources,
applicability, PASS/FAIL/UNKNOWN/N/A, reasons, component outcomes, count bounds, interval
magnitudes, known/candidate units, denominator availability and descriptive measurements.
Null is unavailable, never NaN/Infinity or invented zero. Repeated replay preserves semantic
content; generation time is metadata. Material correction returns no partial cohort.

Identity preflight requires the complete original reference population, current
`subject_scope_version=required_excluded_fixed_time_1`, `reference_set_digest` and
exact replay under the [identity policy](0002-intake-identity-usage.md#identity).
The historical native policy `structural_claims_typed_addresses_3`, uniform-LLM and
V0-adoption reports retain their explicit replay paths; a policy string alone is
insufficient. Missing/stale references require `identity_replay_required`. A newly
included fixed-time subject requires recomputation of affected identity/review scope.
Missing observations remain UNKNOWN, distinct from missing preparation.
Scorer semantic validation follows tolerant intake, preserving original records.

Code owners: [requirement_schedule](../../backend/evaluation/requirement_schedule.py),
[schedule_time](../../backend/evaluation/schedule_time.py),
[occupancy](../../backend/evaluation/occupancy.py) and
[shared preparation](../../backend/evaluation/_schedule_preparation.py).
The immutable public report and CLI are described in [package commands](../../backend/evaluation/README.md#ticket-05-offline-requirement-and-schedule-metrics).

## Decision and acceptance history

[Ticket 05](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/17) and
[acceptance](../records/evaluation/requirements.md#rtpeval-ticket-05-acceptance) retain the
exact-one/single-visit correction, protection-as-boundary decision, implementation, review
and regression evidence. The earlier minimum-one authoring/default at-least-one proposals
are superseded.
