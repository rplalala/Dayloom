# Itinerary, transport and presentation contracts

Status: Implemented shared output contract, consolidated 2026-10-03;
V0 structured declarations added 2026-10-05; explicit activity/time-use wire added 2026-10-16.

## Scheduled activities and references

Output role accounting separates scheduled identities, unlinked activities, unused supply,
independently acquired references and unarranged REQUIRED identities. Policy completion and
goal progress are diagnostic observations, distinct from real-world feasibility.

`itinerary_3` separates dated/timed primary activities from optional unscheduled Nearby
references. References have no scheduled occupancy, planned cost or booking implication;
they do not fulfill a required visit or increase primary-visit counts. Empty reference
output is valid. V0's optional references are model knowledge with no fabricated provider
identity. V1-V3 use independent bounded Nearby acquisition after the final primary plan.
Product acceptance scales Nearby by trip duration under the
[resource profile](../config/README.md#product-acceptance-profile). The shared representation
can hold the expanded output, while V0's model-knowledge boundary retains at most three references.

Primary source identities resolve against authorized supply. Generic activities can have
no venue identity where supported, but missing named identities are not fuzzy-matched into
validity. Nearby identities resolve against that acquisition's evidence, which can differ
from the primary supply. The application preserves attribution and deduplicates references
against scheduled identities. An unused supply candidate is not automatically a reference.

For new tools-based `itinerary_3` output, a declared `main_poi` must have an authorized
acquired identity and an existing semantic assessment with `main_eligible=true`.
Generation acceptance, V3 patch adoption/final selection and final Product projection
use the same eligibility check. An unavailable place or missing/ineligible assessment
cannot be replaced by a generic title, broad area or photo. Supported special-experience
exceptions remain eligible under the existing assessment policy. A specific acquired
promenade, park or lookout can ground a waterfront experience when its supplied semantic
match supports it; a generic supporting walk cannot fulfill a required principal visit.
Photo availability does not affect eligibility. V0 keeps its pure-model name proxy,
and historical itinerary formats retain their compatibility path. No new model call,
V1/V2 Repair stage or budget increase is introduced by this boundary.

At V1-V3 output acceptance, each authorized `source_place_id` owns `place_name` and
`location`: the application copies the supplied normalized PlaceEvidence's `name` and
complete `formatted_address`, including null when the provider has no address. Model
aliases, abbreviated locations and invented addresses do not override those source facts.
An unavailable or foreign identity fails before backfill. Generic null-ID activities
retain their model text, and V0 retains its plain-model name/address behavior.

The same boundary runs for accepted generation and V3 final selection using original
supply plus verified Repair additions. Retained, retimed, added and replaced visits
therefore share source ownership. It preserves title, notes, roles, dates, times and
costs; raw model objects and wire captures remain unchanged. This is prospective
generation behavior, not retroactive correction of saved outputs or independent factual
verification. The evaluator still judges immutable submitted claims against fresh evidence.

Normalization stably sorts each existing day's activities by start time, preserving ties;
it does not reorder day groups, repair overlap, invent times or establish feasibility.
Cost-projection diagnostic paths follow the same activities
through the permutation. Raw model captures stay unchanged. This output-source boundary,
rather than standalone schema construction, owns normalization.

## Civil time and IANA acceptance

The tools-only `tools_civil_time_1` provider projection receives sourced IANA context and
local date/clock endpoints. Ordinary generated endpoints return `utc_offset=null`; the
application resolves each endpoint using that zone and its actual date. It does not reuse
a trip-wide offset across a DST boundary. New V3 patches use the same application-owned
context. V0 retains its independent model-authored offsets.

Local clocks in a DST gap are rejected. A repeated clock requires an explicit valid
offset to select its instant; the application never chooses a fold. Missing or conflicting
zone evidence cannot be replaced by a guessed destination zone. A missing venue zone may
use the single consistent supplied context zone. Explicit offsets, including historical
tool responses, are preserved and checked against known IANA evidence at both activity
endpoints. A known conflict fails acceptance before Routes/Nearby propagation, without
rewriting the response or retrying. Missing historical zone evidence remains unassessed.

The accepted domain values use fixed offsets. Chronology and elapsed route arithmetic
operate through UTC, then return to the applicable sourced zone, including across a
transition. DTO/source captures preserve the original local fields and explicit offsets;
saved failed outputs are not converted into successful observations by reading them.
Calendar days, fixed protections and blank-day policy windows map their two civil endpoints
separately, so a DST day can span 23 or 25 elapsed hours. An ambiguous protected clock stays
unresolved. Repair transfer reservations and derived free-window fragments use the same
elapsed-time mapping. Final transport formatting includes newly adopted Repair place evidence.

## Transport ownership

A source-linked hard `allowed_modes` set constrains V0 declarations and all V1-V3
route acquisition, offered options, cached evidence selection and adopted transfers.
The default WALK/TRANSIT/DRIVE expansion is limited to that set. DRIVE reserves and
fallbacks require DRIVE permission. Missing allowed-route evidence remains an explicit
UNKNOWN/deficit diagnostic; it never authorizes a disallowed fallback. Unrestricted
requests retain existing routing behavior. Under a hard restriction, V0 must declare
an allowed mode for transport activities and cover journeys between distinct named
visits; missing/unknown or disallowed declarations fail output acceptance without a retry.

| Version | Submitted transport representation | Evidence boundary |
| --- | --- | --- |
| V0 | Explicitly estimated model transport activities | No Routes request; estimates remain unverified |
| V1-V3 | Application-owned `transfers` for real adjacencies | Applicable provider facts plus separately represented reserves |

V0 estimates only same-day transport between adjacent different venues; it invents no
unspecified hotel or cross-day journey. Current V0 transport activities require `transport: {mode, from_activity_id, to_activity_id}`.
Mode is `WALK`, `TRANSIT`, `DRIVE` or null; endpoints are nonempty activity IDs.
The new V0 provider schema requires the nullable field on every activity. Its prompt
requires an object on transport activities and null elsewhere, directed between
consecutive visits on the same day. Titles/notes describe estimates but do not replace
these fields. This declaration supplies neither verified duration nor route evidence.

Shared Activity accepts historical missing/null declarations and omits them on output,
preserving the old activity wire shape. A present object survives nested PlanningResult
serialization; a declaration on a non-transport activity fails structural validation.
V1-V3 provider DTOs do not gain the field. V0 keeps its tool-free generation path and
checks declared endpoint structure without verifying travel feasibility or creating application-owned transfers.
Historical evaluation retains invalid associations and unknown modes with separate
review precedence; new-wire associations must identify one consecutive primary pair; see the [intake contract](contracts/0002-intake-identity-usage.md#claims)
and [development acceptance](records/evaluation/intake-identity-usage.md#v0-structured-transport-2026-10-05).

V1-V3 primary model DTOs forbid declared transport activities. A violation fails generation
without silently deleting the item or granting an extra retry. Prompts also prohibit
disguised transport prose; complete semantic detection of every paraphrase is not claimed.

The shared application layer acquires bounded route options before generation and binds
actual adjacencies with departure context after generation. WALK, TRANSIT and DRIVE retain
their distinct evidence/applicability rules. A representative transit option does not
inherit PASS at another departure time. Application reserves are not provider durations.
Missing bindings remain explicit through diagnostics; absence of a transfer does not erase
the real adjacency or authorize invented occupancy.

## Coverage, uncertainty and costs

Minimum daily coverage requires **one countable primary visit per requested day** and reports
`satisfied`, `missing`, `exempt` or `unknown`. V1-V3 count valid supplied canonical main visits
under the semantic eligibility policy; V0 uses its explicitly labelled name proxy without
external verification. Nearby, transfers, free time and unbound generic activities do not
satisfy coverage. A required named cafe may count as a main visit; a meal placeholder cannot.

An explicit source-linked full-day commitment, or fixed intervals covering the entire
established planning window, can exempt a day. Almost-full occupancy and a relaxed pace do
not suffice. Unresolved relevant obligations, roles/identities or remaining hours preserve
UNKNOWN. Blank-day windows follow the existing 09:00-18:00 policy only with reliable
destination timezone information; no minimum visit duration is invented.

V0-V2 expose diagnostics without repair. V3 prioritizes confirmed hard obligations before
minimum coverage, then ordinary opt-in review goals. Minimum completion is **0 to 1**;
optional quantity review may subsequently improve 1 to 2 on the authorized date. Disabling
quantity review does not disable the minimum. Missing coverage does not authorize arbitrary
refill or edits outside active targets. Unresolved coverage remains explicit in partial
output, rather than becoming a claim of objective infeasibility. Coverage/semantic completion
cannot certify opening, access, route feasibility or whole-trip affordability.

Unknown amounts remain unknown. Currency and expense scope are preserved; no exchange rate
or unsupported cost is invented to fit the budget. Provider/model/application provenance and
unsupported factual claims remain inspectable in Developer output. Product presentation uses
an allowlist; it does not expose internal prompts or raw provider envelopes as user content.

## Generation diagnostics and counting contract

The ordinary first-generation objective is full requested-date coverage with normally 2-5
distinct main visits per full day. Explicit rest/pace, long required visits and available
evidence take precedence; the target cannot justify filler, fabricated places or repeats.
Current model activities declare their role; historical missing roles default to unknown.
New-wire non-primary declarations cannot be promoted by a venue eligibility assessment.
Canonical qualification of a declared visit remains separate from its role; legacy
activity qualification keeps its original semantic policy.

[GenerationDiagnostics](../backend/app/schemas/generation_diagnostics.py) is application-owned
and optional for historical results. It is computed after version output/date/identity checks,
before final Nearby. [The counting policy](../backend/app/policies/generation_diagnostics.py)
inventories every inclusive requested date, including absent day groups:

| Measurement | Counting and uncertainty |
| --- | --- |
| Main visits | Qualified supplied canonical identities in V1-V3; normalized NFKC/whitespace/case name proxies in V0 |
| Distinct/repeated main visits | Distinct counted keys per day; counted occurrences minus distinct keys |
| Other roles | Generic, transport, free-time and unclassified counts remain separate from main visits |
| Default target | Within 2-5, below, above or not assessable; same-day remaining-hours and unclassified visits preserve not assessable |
| Empty day | No activities, including absent requested-day groups; `day_present` distinguishes missing groups; zero main visits alone does not imply empty |
| Supply use | Distinct counted supplied IDs scheduled across the trip and remaining unused IDs; V0 values are null, not zero |
| Cross-day repeats | Each distinct key counts once on each subsequent day on which it reappears, independently of same-day multiplicity |
| Policy completion | Complete, incomplete or unassessed under the sourced semantic contract; not global feasibility |

Unknown roles/identities do not become verified zero visits. Known non-main semantic objects
do not count; missing role assessment preserves uncertainty. Default target status and minimum
coverage are different observations. Partial known counts, reasons/evidence and linked requirement
IDs remain visible. `output_role_summary` counts all linked activities and consequently has a
different denominator from qualified-main diagnostics. Merely observing these counters never
launches acquisition, another generation or Repair; V3's separately authorized targets own edits.

## Failure and verification limits

Ordinary Nearby failure preserves primary success, while cancellation propagates. Structural
identity/date/role acceptance is not independent real-world verification. A successful run,
a bound route adjacency and a well-formed result are different levels of evidence.

Implementation owners: [itinerary schema](../backend/app/schemas/itinerary.py),
[initial routes](../backend/app/services/initial_routes.py),
[Nearby discovery](../backend/app/services/reference_discovery.py), and
[Product projection](../backend/app/services/product_presentation.py).
See [ADR: transport ownership](adr/0002-transport-ownership.md) and
[validation and repair](0005-validation-repair%28v3%29.md).

## Route evidence and projection details

The baseline route catalogue preserves all directed matrix facts, including not-observed
versus provider no-route outcomes. Chunking retains complete destinations. Sparse mixed-mode
work uses shared configured totals and post-generation reservations, not another full matrix.
Explicit supported mode restrictions constrain alternatives. Representative transit evidence
cannot inherit final-departure PASS; any mirrored duration is not a fabricated reverse route
condition, distance or timetable. Actual-adjacency binding checks the continuous free interval
at the bound departure, not an unrelated later free window. Unbound obligations remain in
`route_diagnostics`; missing transfer output does not erase them.

Provider duration and application reserves remain separate. Optional cost-range projection
uses a finite same-currency midpoint only when the supported range contract permits it;
ambiguous costs remain null, with no model retry or promotion to verified prices. The schema
retains nonnegative money and strict validation of unrelated fields.

## Nearby acquisition details

Nearby uses actual scheduled canonical anchors with known supply coordinates. Its bounded
area budget can leave later days uncovered. It performs no additional Details, Profile,
Routes, web or model work. Ordinary failure yields partial/empty references while preserving
primary dates, times, order, identity, costs and requirement decisions; cancellation propagates.

Anchors sort by requested date, start time and activity ID, then deduplicate canonical places.
Representative reuse compares each anchor directly with an existing representative; chains
of close anchors do not merge distant areas transitively. The configured first-area limit
can exclude later areas. Search uses DISTANCE and the configured circle/types/results limit;
actual-anchor distance is rechecked after reuse. The current defaults and independent
send/time/retry ceilings are documented under
[reference discovery configuration](../config/README.md#current-yaml-values-and-every-effective-path).

The provider field mask is limited to identity, display name, coordinates, formatted address,
primary/type collections, business status and attribution. It requests no wildcard, ratings,
reviews, opening hours or routing summaries. The cache key includes center/radius/types/rank,
language and mask; hits are free and failures count as sends. Known ineligible/excluded places,
invalid identity/name/location/type/radius and scheduled/reference duplicates cannot attach.
UNKNOWN alone neither rejects a reference nor establishes preference satisfaction. Selection
uses stable distance/identity order and anchor round-robin; reasons describe only supplied
type, anchor and straight-line relationship. An address does not prove a separate locality.
Only independently acquired ledger entries may attach, with matching source/name/day/address
and scheduled anchor. Straight-line distance is not walking distance or accessibility.

## Cost and legacy measurement semantics

The earlier output-design measurement contract remains a definition, not an assertion that
every metric is implemented by the planner or independent evaluator. For a future use of these
measurements, preserve the following meanings and report unavailable denominators explicitly:

| Measurement | Definition |
| --- | --- |
| Empty-day rate | Requested inclusive dates without any primary activity divided by all requested dates; not automatically a violation |
| Ordering violations | Adjacent start-time inversions, ties allowed; raw and normalized output measured separately |
| Repeated canonical instances | Linked occurrence count minus distinct linked identities; descriptive unless a separate sourced policy establishes a violation |
| Supply utilization | Scheduled supplied identities divided by distinct supply; unavailable for zero supply and V0 |
| Required coverage | Resolved required identities scheduled/unscheduled, with unresolved identities separately reported; V0 name observations remain separate |
| Cost evidence coverage | Reliably supported scope-compatible costs divided by primary activities; unavailable with no activities |
| Known cost subtotal | Reliable nonoverlapping nonnegative amounts in the same currency, party and time scope; an empty subtotal is not a zero trip cost |
| Whole-budget outcome | FAIL when comparable reliable subtotal already exceeds budget; PASS only with complete evidence for the declared scope; otherwise UNKNOWN |

A numeric model estimate or range midpoint does not establish reliable cost evidence.
Activity costs alone cannot certify a whole-trip budget when accommodation/transport or
other in-scope amounts are unobserved. No planner whole-budget factual validator is claimed.
The independent evaluator's implemented/deferred metric boundary remains in
[evaluation architecture](0006-independent-evaluation.md) and its contracts.

## Activity semantics contract (phase 2)

Status: **Accepted on 2026-10-16; implemented under Issue #172 and delivered through [PR #174](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/174).**
[Issue #172](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/172)
owns implementation and the accepted-case impact audit. Historical `itinerary_1/2`
and evaluator policies remain authoritative for existing material. The
[impact record](records/evaluation/intake-identity-usage.md#activity-semantics-design-and-accepted-case-audit-2026-10-15)
identifies the audited selections, actual supplementary review and evidence limits.

### Planning meaning and wire

Current generation uses the `itinerary_3` wire, with the existing activity identifiers and
source ownership, an explicit activity kind and a required `time_use` field.
Provider DTOs require these declarations; legacy domain readers retain absent fields.

| Term | Meaning |
| --- | --- |
| Primary visit | A selected principal sightseeing/experience occurrence, declared as `main_poi`; factual identity is checked independently. |
| Non-primary activity | A meal, rest, walk or other supporting activity declared as `generic_activity`; it can occupy planned time without increasing the main-visit count. |
| Scheduled time use | `time_use=scheduled`: the submitted plan assigns the activity to its start/end interval. It need not be booked, mandatory for the traveller or impossible to reschedule. |
| Free window | `time_use=free_window`: the interval is available for discretionary use; no activity commitment is adopted for occupancy. A suggestion inside it is not a scheduled primary visit. |
| Fixed-time constraint | An independently interpreted user requirement/reservation-time claim; separate from whether an activity occupies the submitted plan. |

Changing tomorrow's plan is different from evaluating today's submitted plan.
A movable 11:00-12:00 walk can be scheduled and occupy that hour. Calling a walk
relaxed or unstructured is not a declaration of a free window. Booking status,
pace and time use must not be inferred from each other.

| `activity_kind` | Legal `time_use` | Identity and counting |
| --- | --- | --- |
| `main_poi` | `scheduled` | One declared primary occurrence on its explicit date; preserve the place claim and independently assess identity. |
| `generic_activity` | `scheduled` or `free_window` | Explicitly non-primary; the time-use choice controls whether it occupies the plan. A venue name alone does not promote a supporting activity to a visit. |
| `free_time` | `free_window` | An unassigned interval. A specifically scheduled rest/meal uses `generic_activity` instead. |
| `transport` | `scheduled`, V0 only | One declared journey with directed occurrence endpoints; duration remains a model estimate. |

`unknown` remains readable in historical wires but is not a valid kind for a
newly accepted `itinerary_3` generation. Missing/null `time_use` is not defaulted.
Named optional principal visits belong in unscheduled references rather than
being counted as scheduled visits. A generic free-window suggestion must not
claim a completed booking, confirmed admission or a required visit's fulfillment.
An original hard required visit is still checked independently; changing its
output label does not remove that obligation or prove fulfillment.

Optional `atmosphere_theme` is a display hint independent of role, time use and identity.
The domain field remains optional and absent/null values preserve legacy serialization.
The strict Foundry Activity, Primary and Civil transport DTOs carry a required nullable
controlled value, and their shared mapper retains it without an extra model invocation.
The [Product atmosphere contract](0007-application-operations.md#supporting-atmosphere-photos)
defines its allowed themes, search mapping and media behavior.

A primary park visit must be declared as such and carry its actual proposed
place name; V0 may use a name without an external ID. V1-V3 retain authorized
supplied-identity ownership. An unspecified green space is not turned into a
named park by normalization, nearby context or a reviewer. Named non-primary
meal/rest locations remain legal without becoming main visits.

Retain valid explicit dates, offsets and positive intervals, unique occurrence
IDs and declared day membership. For a free window, clocks bound availability;
for scheduled use they bound planned occupancy. The normalized activity array
is the submitted intended sequence. The evaluator preserves that sequence rather
than inventing a different journey when times conflict. Overlap and infeasible
travel remain quality failures/UNKNOWN; structural acceptance must not erase them.

Each directed consecutive primary-occurrence pair identifies one potential
journey. A repeated physical venue with a different occurrence ID is still a
different occurrence. V0 must supply unambiguous structured endpoints and at most
one selected journey declaration per pair. V1-V3 keep application-owned selected
transfers; unused alternatives stay diagnostic. Missing transfers remain missing,
not invented occupied intervals. Null V0 mode remains distinguishable from an
invalid association and subject to existing hard-mode acceptance restrictions.

### Writer, reader and Repair alignment

| Interface | Implemented boundary |
| --- | --- |
| Provider DTOs and prompts | Require the new wire/kind/time-use declaration in V0 and the shared V1-V3 primary output; distinguish scheduled-but-movable activities from free windows. Do not introduce factual verification or tools into V0. |
| Internal schema and mapping | Preserve `time_use` through `FoundryActivityDTO`, `map_foundry_activity`, `Activity` and nested serialization; validate legal combinations without silently filling, deleting or relabelling content. |
| Output acceptance | Keep source-owned V1-V3 names/addresses and raw captures. Sorting preserves the time-use value with its original activity. Invalid declarations return a bounded contract failure, without a new automatic retry. |
| Schedule and V3 Repair | Build occupied and available intervals from explicit time use, separately applying sourced protection constraints. Preserve the field on retained, copied, retimed and serialized activities; model changes require existing permissions. A retime changes the interval, not the activity's semantics by default. |
| Evaluation intake/projection | Read original declarations as plan claims. Preserve source pointers and time-use provenance; do not import Planner schedule/validation conclusions as independent truth. |
| API/presentation and saved material | Carry the declaration through allowlisted output/readers; explain suggested availability versus an arranged activity without displaying internal scoring identifiers. Retain the original wire version. |

The pure activity-claim reader handles legacy wires and `itinerary_3`, returning
normalized declarations and provenance. Projection retains exact source linkage
and diagnostics. This is the test seam for both adapters. The reader performs no provider
access, scoring or semantic-prose guessing. Sharing a grammar does not authorize
sharing Planner truth judgments: independent evaluation reconstructs its view
from submitted bytes and its own versioned policies.

The new writer must not select an interpretation merely to improve a score.
Independent review remains available for conflicting supplied claims, legacy
ambiguity and genuinely uncertain meaning. Explicit structured roles retain the
precedence established by #53; a title regex is not a semantic adjudicator.

### Numerical scoring policy and limits

The researcher approved two separately versioned changes:

1. **Declaration contract:** the new role/time-use wire makes intended populations
   readable. On its own it fixes this activity ambiguity, but cannot promise that
   every other applicability/transport/requirement uncertainty becomes numerical.
2. **Candidate-population scoring profile:** `rtpeval_declared_population_1`
   retains a finite inventory under missing factual evidence. This changes applicability accounting;
   it is not an implementation-only correction or a retrospective old-policy fix.

For this profile, establish a finite source-linked candidate inventory
before acquisition: one parent check per executable reviewed obligation (retaining
its component results), one grounding
and opening candidate per declared primary occurrence, one non-overlap unit per
declared scheduled activity/selected logical journey, and one route candidate
per directed consecutive primary pair. Protections retain their separate
blocking/obligation meaning and do not create extra occupancy units. Explicit
dates/roles determine daily occurrence counts; retain the existing density table.

Keep candidate membership, factual outcome and verified inapplicability separate.
An identity failure, unavailable hours, unsupported route observation or uncertain
physical same-place association cannot erase its candidate. A definitely
inapplicable check may be labelled N/A with a recorded reason. Applicability that
is itself uncertain remains an UNKNOWN candidate rather than an unknown-sized
population. Thus `N = candidate_count - verified_NA_count` is known, and the
verified fraction is `100 * PASS / N` when N is positive. FAIL and UNKNOWN stay
distinct in the report, alongside verification coverage and unknown rate. A zero
verified fraction with zero coverage is not proof of zero real-world compliance.

Preserve explicitly versioned common-mask weighting and density subtraction.
The new profile's point value concerns retained candidate checks, not a claim
that all actual-world applicability is known. Do not compare it directly with
old totals as if only serialization changed. Confirmed N/A exclusions may change
the denominator; the complete candidate inventory and reasons remain visible.

An offline numerical-population readiness result is distinct from review
coverage. It establishes role/date membership, occupancy membership, unique
selected journey associations, reviewed requirement completeness and density
policy before a promised numerical run. Missing declarations, unresolved legacy
roles/occupancy, ambiguous journey selection or incomplete executable obligations
cannot be resolved by this score formula. Return an actionable `needs_population_resolution` preparation status
for that requested profile; retain the existing ability to report genuine
unavailable totals under historical policies. Do not change the phase-1 meaning
of a completed unresolved review into missing work.

A complete parseable, positive submitted interval whose only time error is
`timezone_offset_conflict` does not block this inventory when its declared date
and both endpoints still belong to the same requested date under the reviewed zone.
Keep the original source-linked candidates and record the interval in preparation's non-blocking
`time_uncertainties`; the instant remains UNKNOWN. This is not permission to
correct offsets, remove the reviewed zone, infer opening access or award verified
credit. Missing/unparseable dates, conflicting date membership and other interval
errors retain their existing blockers, as do unresolved roles, occupancy and
selected journey associations. `date_consistent` alone is insufficient to admit
missing timestamps. Scoring units, weighting, density deductions and historical
reports are unchanged; fresh preparations bind the corrected implementation.

The numerical guarantee is conditional on a source-valid, population-ready group,
a complete independent acquisition receipt (which may contain unavailable facts),
an established density deduction and at least one scored dimension. All-N/A groups
remain N/A. Unparseable material, abandoned acquisition, ambiguous membership and
empty score masks are explicit exceptions, not arbitrary zero/100 scores.
No new failure-submission score is proposed.

### Historical compatibility and case-07 examples

Keep `itinerary_1/2`, their projection/score policies and their original prepared
packages readable. New-generation declarations and historical derived semantics
must have different provenance. An adapter may derive scheduled occupancy for an
explicit historical primary visit or selected transport under its original
policy; it must not claim that the model emitted a missing field. Preserve source
bytes, original pointers/hashes and any source-to-derived mapping. A new projection
or scoring-policy identifier creates new report bindings, never a relabelled receipt.

Historical generic/free-time cases require existing source-bound decisions or
explicit uncertainty. Do not insert new time-use defaults into case-07. The five
remaining cases below are design alternatives only, not adopted corrections:

| Original source | Meaning a future generator must choose explicitly |
| --- | --- |
| V1 15 October, 11:00-12:15, Ile de la Cite exploration | A planned 75-minute non-primary walk (`scheduled`), or optional exploration inside a `free_window`; unstructured walking alone selects neither. |
| V2 15 October, 14:45-17:00, park/wandering | A particular selected main park visit, a planned non-primary outdoor activity, or discretionary availability; do not invent a park from the Eiffel Tower stop. |
| V2 16 October, 14:15-16:30, green-space/wandering | The same explicit alternatives, without treating the preceding Arc de Triomphe as a park locator. |
| V2 17 October, 10:00-12:00, park/wandering | The same explicit alternatives; the later Pantheon visit does not determine the morning's role. |
| V2 17 October, 15:00-16:30, relaxed architecture walk | A scheduled non-primary 90-minute walk or a free window; relaxed pace is independent of time use. |

Additional prospective controls are a movable scheduled walk, a fixed generic
appointment/rest, an unassigned free window and an explicit named primary visit.
`main_poi + free_window`, `free_time + scheduled`, unknown kinds, missing time use
and contradictory selected journeys are structural negative controls. A declared
visit with unavailable independent opening evidence remains an UNKNOWN check in
a known population; it is neither automatically PASS nor deleted.

### Selection and verification boundaries

New-wire batches automatically select `rtpeval_declared_population_1` in normal
`evaluation-run prepare` and quality reporting. Historical batches retain their
original default profile; opting in uses `--quality-profile rtpeval_declared_population_1`.
Preparation freezes the candidate inventory, review/source hashes and profile in
its content digest. Execution/replay verifies that population binding, and reports
carry the inventory and separately labelled legacy-derived claims. No old receipt
or snapshot is relabelled. The numerical readiness gate requires established daily
density policy and executable obligation structure before paid acquisition.
`activity_claims` describes source declarations and their original-policy derivation;
the retained role review and candidate inventory separately identify adopted membership.
It must not be read as a claim that legacy models emitted a missing field.

Non-primary scheduled activities remain route-planning barriers. The application
never adopts them as new-format primary journey endpoints; an absent selected
transfer remains missing, while independent route checks retain their consecutive
primary-pair candidate. Free windows are omitted from occupied adjacency. Repair
preserves declarations during retiming, copying and window fragmentation and assigns
scheduled time use to authorized new/replaced main visits.
Output-role summaries exclude free windows from scheduled identities. A new-wire
required primary visit is fulfilled only by a declared main visit; a scheduled
supporting activity at the same venue does not fulfill it.

Offline verification covers DTO/mapping/normalization/CLI seams, schedule and
permissioned Repair preservation, legal/illegal combinations, directed/duplicate/
missing transport, overlap and invalid dates, UNKNOWN versus N/A accounting,
density/common-mask arithmetic, historical readers and immutable sources. Tests use
synthetic material; they do not adopt corrections to case-07 or refresh any accepted
result. Live execution and data changes remain separate authorizations.
