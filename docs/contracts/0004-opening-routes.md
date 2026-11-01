# Independent opening and route compliance

This reference defines independent opening and route preparation, evidence
applicability and scoring. Follow [evaluation commands](../guides/experiments.md#evaluate-the-selected-outputs)
for execution and replay. Shared [artifact/time](0001-evaluation-artifacts.md),
[identity/snapshot](0002-intake-identity-usage.md) and
[occupancy](0003-requirement-schedule.md#occupancy) contracts own their respective inputs.
Scoring uses emitted frozen rules, preserving historical policy on replay.

<a id="opening"></a>

## Opening scope, evidence and verdicts

An independently associated primary place visit and independently interpretable interval are
the units. Nearby and unresolved role populations retain their separate scope diagnostics.
RequirementSpec has no entry/exterior distinction. Original activity prose can inform the
explicit missing-hours access policy below; it never creates an automatic opening exemption.
Planner-selected hours or V3 findings are not ground truth. Zero grace applies to full-visit
containment; touching closing time is allowed and a lunch closure is not bridged.

Under `versioned_api_identity_3`, a verified `place_association` supplies the API venue
even when the original name/address has grounding FAIL. `canonical_place_id` retains
claim-adoption semantics; opening checks expose `associated_place_id` separately and
retain `identity_grounding_verdict`. A missing/untrusted association remains UNKNOWN.
Details request/response IDs must match the associated venue. The original visit time
is unchanged; a PASS does not repair the original claim or prove a requirement.
Historical policies retain their original canonical-only eligibility.

Route preparation/scoring uses the same verified association for physical endpoints
and independent coordinates. The existing `canonical_endpoints` route field carries
those physical API IDs under the new source-linked identity policy, while endpoint
grounding verdicts remain explicit. Original order, time, reserved duration and mode
remain unchanged: DRIVE requires driving evidence, TRANSIT public transport and WALK
walking. Existing DRIVE `TRAFFIC_UNAWARE` semantics and 600-second reserve are unchanged.
The smoke request tool's separate DRIVE adapter remains outside this correction.

`--paired` includes available V3 draft
and final_primary projections independently, with the same paired snapshot scope.
No Repair delta or route verdict is calculated. Library entry:
`score_opening(intake, identity_report, snapshot_directory, schedule_context=None,
*, paired=False, expected_plan=None, opening_judgment=None)` returns immutable `OpeningResult`.
Schema: `rtpeval_opening_report_1`. API-only replay retains `rtpeval_opening_rules_2`;
validated access material selects `rtpeval_opening_rules_4`.

Exit 0 means complete processing, including visit FAIL/UNKNOWN; exit 2 means material
correction or identity replay. JSON is printed to stdout. Preparation file hashes,
canonical intake/identity/context/rule hashes, snapshot manifest hash and expected/
actual plan hashes remain auditable. Submitted bytes are never rewritten. Save the
report outside its source artifacts. CLI constructs no provider/model/database client.

Whole-batch source/policy validation precedes scoring. Source corruption, stale phase/
paired scope or incomplete request linkage returns no partial cohort. Identity policy,
references, review/audit metadata and source mismatch requires identity replay.
Valid but failed observations and missing/malformed hours produce visit UNKNOWN.
Mixed snapshots keep supplied route contexts and verify their linkage without choosing
routes. Optional trusted full-plan equality includes those routes; canonical opening
references/details are checked even without that optional plan.

One check is emitted per primary occurrence. Repeated canonical places remain repeated
checks; Nearby and requirement-subject-only records add no visit. Nonapplicable
activities and unresolved roles retain source/reason records. Applicable counts are
known occurrences; `applicable_denominator` is null while roles are unresolved.
Full-scope percentages, including conditional compliance, are then unavailable.
`counts` covers primary checks; nonapplicable records carry their own N/A/UNKNOWN states.
Empty applicable scope has state N/A and unavailable rates, never 100 percent.

Every check records original start/end, normalized UTC interval, declared date, source,
canonical identity, independent timezone/origin, provider timezone version when supplied,
actual installed zone-file hash/basis, selected details attempts/raw hashes, reasons and
explanation. Clock evaluability and identity availability are separate. Explicit offset/
date contradictions, naive DST folds/gaps and precision beyond six fractional digits
remain UNKNOWN. `allow_cross_date=True` is opening's explicit opt-in; Ticket 05's
same-date time behavior remains unchanged. Reversed same-date clocks are never repaired.

Opening uses original raw `currentOpeningHours` and `regularOpeningHours`. It retains
field presence, weekly/dated endpoint meaning and literal truncation. Optional endpoint
day/hour/minute require actual integer values; absence is not zero. Explicit applicable
`periods: []` means closed, while missing/null/invalid values remain unavailable.
Regular Sunday 00:00/no-close is the documented always-open sentinel; arbitrary current
missing-close periods do not imply continuous access. Split periods retain lunch gaps;
overnight and previous-day contributions and weekly rollover are supported.

Current applicability uses the selected attempt's place-local request date plus six
calendar dates. Post-trip current hours cannot become historical evidence. Usable
applicable current facts take precedence over regular hours for their established open
and closed intervals. Missing, null, malformed or incomplete current hours permit regular
fallback only over the remaining unresolved time; known current closure is never erased.
Dates outside the current window use regular hours directly. A valid regular schedule
establishes ordinary PASS or FAIL; no separate provisional verdict is introduced.

A special-date marker without an applicable schedule is diagnostic, not proof of closure
and not a veto of regular hours. Marker presence and parsing defects remain visible as
`special_date_marker` and `special_dates_invalid`. Collection crossing local midnight
retains current-evidence uncertainty; consistent literal dated spans may still prove
opening, and regular hours can resolve the remaining uncertainty. A truncated 23:59 close
does not itself establish the final minute; applicable regular fallback can cover it.
`openNow` describes the query instant and cannot establish closure at the planned visit.
Undated `businessStatus` is not converted to a future dated closure by this scorer.

Each date segment records preferred `selected_basis`, factual `basis` and the actual
`hours_fields` contributing open/closed spans. `hours_field` is that single field, or null
for mixed/unavailable evidence. `regular_fallback` is null when unneeded, otherwise it
records unresolved scope, applied regular open/closed intervals and regular diagnostics;
`regular_fallback_used` marks an actual contribution. Current parsing reasons remain
visible even if regular evidence determines PASS or FAIL. Missing both usable schedules
retains UNKNOWN in API-only scoring. A visit's factual basis is current, regular, mixed
or unavailable; the opt-in access judgment below supplies a distinct verdict basis.

<a id="missing-hours-access-judgment"></a>

### Source-bound missing-hours access assessment

[Issue #90](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/90) added the
source-bound fallback; [Issue #91](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/91)
revises it to `llm_access_reasonableness_2` equally for V0-V3. Identity resolution and requirement
target matching retain their existing version-specific policies. The narrow V1-V3
model exception applies only to access assessment when neither API schedule is supplied.

Eligible occurrences require verified independent identity/Details, a known original
interval and a valid nonconflicting timezone. Both hours fields or their `periods` must
be absent/null. Query-instant `openNow` without periods is not a schedule or a closure.
Empty periods are explicit closure; supplied malformed or incomplete periods remain
API diagnostics and are not replaced by model knowledge. API-decided visits never enter
the model packet. No failed acquisition, invalid identity or invalid time is rescued.

Preparation binds original title/place/notes/kind/time, version/projection, source record,
independent venue facts, raw hours observations, normalized interval/timezone and retained
Details attempt hashes. Notes are original claims/intent, not factual opening evidence.
The model classifies public outdoor/exterior versus indoor/ticketed/ambiguous access,
the entire window's reasonableness and applicable restrictions. It cannot reinterpret an
indoor visit as exterior viewing to obtain PASS or assume every public area is always open.

For confidently classified public landmarks/public areas, ordinary sightseeing may be
inferred from the original title, name and notes without explicit exterior wording.
Generic Harbour Bridge/Opera House visits may mean ordinary viewing; the mere possibility
of a paid climb, tour or interior visit is not a reason to force UNKNOWN. Explicit restricted
activities take precedence. Interpret negation and conditional mentions in context:
"no interior access" excludes entry; "verify if planning interior access" alone does not
commit to entry. Museum/indoor-attraction visits never use this default, even in famous
buildings. Museum admission remains unverified without applicable access evidence;
explicitly exterior-only museum viewing can be assessed without approving admission.

Structured decisions record `intent_basis` (`original_activity`, `public_landmark_default`,
`unresolved`) and `venue_category` (`public_landmark`, `public_area`, `museum`,
`indoor_attraction`, `other`, `unknown`). Category inference uses independent venue identity,
name/address, supplied provider `types` when present and original intent. It is a model
assessment, not an invented Google fact. Missing types alone does not prohibit inference;
`tourist_attraction` alone does not establish public access. Default PASS requires a public
category; museum/indoor/other/unknown default PASS and unresolved-intent PASS are rejected.
Quotes and rationale retain the unchanged original activity and identify the inference.

Ordinary PASS requires public outdoor/exterior access, a reasonable full interval and
`none_known` restrictions, with specific rationale and an exact original activity quote.
Otherwise the saved decision is UNKNOWN. A model does not manufacture a factual FAIL.
Model knowledge is fallible; rationale/schema acceptance cannot prove the semantic claim.
PASS uses `basis=llm_access_reasonableness` and participates in ordinary verdict scoring.
It does not supply hours, eliminate original grounding FAILs or fulfill requirements.

API `evidence_status`, segments, known-open/outside/unknown seconds and complete-evidence
coverage remain unchanged. `llm_assessed_count` and `llm_decidable_count` distinguish model
coverage; `verdict_decidable_coverage` can increase while factual coverage stays missing.
The new quality profile `rtpeval_access_quality_4` states this broader opening-PASS basis;
arithmetic and denominators are unchanged. Historical API-only profiles remain available.

Import reconstructs the complete packet from current sources and rejects foreign, stale,
duplicate, partial or contradictory decisions, unsupported original quotes, request/model
settings mismatches, invalid timestamps and missing/inconsistent actual token counts.
Raw request/response, prompt/policy/model identifiers and material/source hashes remain
auditable. Every packet carries evaluator implementation hashes, rebuilt on direct import
as well as incremental execution/replay. Direct import is supplied model material;
execution additionally binds
that material to captured HTTP bytes and the closed receipt inventory. Replay sends nothing.
New preparation serializes JSON object keys in `request.input` in sorted order, so equal
source mappings reconstructed from an original manifest or frozen intake produce the
same bound request. Array order and source values remain significant. Import still
requires the unchanged recorded request, complete packet and implementation binding;
it does not normalize an already sent request or rebind a historical response. Material
prepared before the serialization correction retains its original implementation for
replay; new execution uses fresh preparation and a genuinely acquired response.
Current packet/material schemas are `rtpeval_opening_judgment_packet_2` and
`rtpeval_opening_judgment_material_2`. Prior policy-1 material is rejected under the current
policy; preserve old reports and replay them with their retained implementation. Changing
the policy requires a newly bound packet and genuinely acquired response, not edited old
model decisions. No new Google acquisition is required merely to add absent provider types.

Fresh `evaluation_run_cli prepare / execute / replay` packages use
`rtpeval_execution_preparation_3`. After independent identity and Google evidence
acquisition, the executor prepares the source-bound missing-hours packet and, when
eligible visits exist, sends one medium-effort access assessment before composing
the single final primary report. It reuses the collected evidence and sends no
additional Google requests. No eligible visits skips the model call; explicit
`assess_missing_hours=false` selects API-only opening checks. The report records the stage
as complete, skipped or disabled and preserves factual/model-supported coverage.

Stage eligibility, the common-subject and V0 visit stages, and the total model ceiling
follow the [identity preparation contract](0002-intake-identity-usage.md#version-specific-identity-evaluation).
Access uses medium effort under the same explicit model/deployment, token ceilings,
request deadlines, total time and USD allowance.
Prices must cover `opening_access` when that call is needed. A failed, malformed,
unpriced or unaffordable assessment stops execution with receipts/usage and no
preliminary quality score; it does not silently fall back or retry. Replay rebuilds
eligibility, validates all selected model HTTP/material/usage bindings and recomputes the
one final score without network access. Historical version-2 packages retain their original
two-stage ceiling; version-1 packages retain API-only execution semantics under their
recorded sources and rules.

For historical API-only runs and separately authorized corrections,
`evaluation_run_cli prepare-opening / execute-opening / replay-opening` consumes a completed
four-final run, verifies its immutable sources/receipt and independently replays identity.
It reuses retained Google evidence and never reruns Google acquisition or V0 identity calls.
A separately approved digest allows at most one Responses call at medium effort, zero
retries and an explicit token/time/USD reference allowance. Failed/partial attempts retain
raw receipts and usage. A separate full report includes the incremental opening cost;
original acquisition/identity costs remain in the parent report. No live approval is implied
by Issue completion or CLI preparation. Exact replay requires the recorded code policy.

Rules version 2 replaces the former current-defect/special-marker veto. Exact reproduction
of rules-1 reports uses their original code revision; save new policy recalculations
separately from original source artifacts and frozen execution receipts.

Half-open containment has zero grace: ending at close can PASS; any positive known
closure overlap yields FAIL even with other unknown time. Partial valid spans may prove
PASS containment but cannot establish a closed complement without bounded completeness.
Verdict, complete/partial/missing evidence, clock/identity availability and basis counts
are separate. Conditional compliance is PASS/(PASS+FAIL), including partial FAIL;
complete-evidence coverage and verdict-decidable coverage use the applicable population.
Two PASS plus one partial FAIL gives compliance 2/3, complete coverage 2/3 and decisive
coverage 1 when the first two visits are complete.

`outside_seconds` is exact only when all time is known; otherwise null.
`confirmed_outside_lower_bound_seconds`, `known_open_seconds`, `unknown_seconds` and
open/closed/unknown segment intervals preserve what is established. Missing visit
magnitude stays null; known zero stays zero. Integer microsecond interval measurement
prevents floating subtraction from hiding a fractional conflict. Duration summaries
are labelled observed per-visit subtotals with observed/missing counts; they do not
claim complete full-batch magnitudes or a global-time union.

[Acceptance](../records/evaluation/opening.md#initial-scorer-and-time-corrections) records the actual development
failures, corrections, retests and review. [Preflight](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/18#issuecomment-5955697757)
retains the approved decisions and original inspection checkpoint. Opening fixtures are
offline/synthetic; separately authorized local database/native checks are recorded in
acceptance and acquire no provider evidence. No provider availability, future factual certainty or booking/access
claim follows from this implementation. V0-V3 planner paths remain unchanged.

<a id="route-wire"></a>

## Route preparation and wire

`prepare_routes(intake, identity_report, schedule_context=None, occupancy_reviews=None,
route_reviews=None, coordinate_evidence=None, *, paired=False)` returns immutable
`RoutePreparation`. `score_routes` additionally takes a snapshot directory and optional
`expected_plan`, returning immutable `RouteResult`. `to_dict()` exports independent copies.
Schemas are `rtpeval_route_preparation_1`, `rtpeval_route_report_1`; rules are
`rtpeval_route_rules_3` with `transport_modes` obligations, otherwise
`rtpeval_route_rules_2` (historical reports retain rules 1). Preparation selects sources/intervals before observing route results
and emits both `route_contexts` and a complete Ticket 04 evidence plan. No provider is called.

Reuse existing rtpeval_schedule_context_1 and rtpeval_occupancy_reviews_1 unchanged.
Shared source/obligation/occupancy validators live in private `_schedule_preparation.py`.
The source-linked `transport_modes` operator supplements the independent route reviews.

rtpeval_route_reviews_1 requires batch_id, nonempty revision and groups. Each unique
group links group_id/input_sha256 with reviewer_ref and offset-aware reviewed_at:

- status unrestricted explicitly reviews the absence of hard mode constraints;
  no policies are supplied. Missing review is UNKNOWN, never guessed unrestricted.
- status restricted requires nonempty policies, each with unique policy_id, original
  Input source_refs, nonempty allowed_modes subset of WALK/TRANSIT/DRIVE, and scope
  whole_trip or specified_dates. The latter requires unique inclusive-request dates;
  whole_trip has no dates. Empty intersections require correction.
- status unresolved requires reason, with source_refs where available.

Optional stated_mode is `{"mode": "WALK", "source_refs": [...]}`: an independently
reviewed exact original-input mode, distinct from a soft preference or allowed set.
It supplies mode only if no usable itinerary mode fixes one and conflicting claims
are not hidden. Missing Transfer remains missing in claim coverage. Hard restrictions
need policy records; query defaults do not invent them. Source references reuse exact
field/quote/occurrence/Unicode-offset validation. Extraction/review is supplied external
preparation; the evaluator does not parse unrestricted prose or run an LLM.

rtpeval_route_coordinates_1 requires batch_id, nonempty revision and records. Each
unique independently associated place_id record has latitude/longitude (strict finite numeric
values in range), lowercase 64-hex evidence_sha256, independent source_ref, reviewer_ref
and offset-aware reviewed_at. Never borrow planner locations. This supplied review is
a trust boundary: the hash links evidence, but the evaluator does not certify coordinate
facts or acquire the referenced source. Exact coordinate/hash correspondence gates
query applicability. Missing coordinates retain pending contexts and UNKNOWN.

<a id="accepted-snapshot-coordinate-extension-2026-10-03"></a>

### Snapshot-derived coordinates

The implemented deterministic offline bridge provides `prepare_snapshot_coordinates(intake,
identity_report, snapshot_directory)` and optional `identity_snapshot_directory` on route
preparation/scoring and their CLI. The existing reviewed
coordinate envelope remains supported; selecting both sources is a material error.

The explicit [V0 model-assisted policy](0002-intake-identity-usage.md#v0-only-model-assisted-offline-adoption)
is accepted only after recomputing its report from bound saved inputs and genuine supplied
reviews. Merely changing a policy string or canonical ID is rejected before coordinate,
evidence-plan or route preparation. Native reports retain their existing path. This
extension supplies no journey observations, acquisition budget or new scoring thresholds.

Replay the identity-phase snapshot through existing safe-path/raw-hash validation, recompute
its identity plan from the supplied intake, and verify that its derived identity evidence
matches the replayed report. Only exact verified physical associations may contribute
coordinates under current policy; historical reports retain canonical-only eligibility.
See [physical association](0002-intake-identity-usage.md#identity) for claim correctness
versus evidence eligibility.
Preserve the snapshot manifest hash, original response hash, request key, candidate pointer
and retrieval timestamp. Automatic extraction is source preparation, not human review:
do not invent reviewer names or review timestamps. Return immutable source-derived coordinate
preparation with per-place diagnostics and deterministic evidence digests.

Use finite numeric latitude/longitude within geographic ranges. Repeated usable observations
must agree exactly; explicit malformed or contradictory coordinates block automatic adoption
for that place. Missing coordinates do not require acquisition. Missing/blocked points leave
route candidates and unavailable contexts visible while unaffected endpoints remain usable.
Requests marked unavailable by the identity-evidence conversion, including malformed Search
candidate lists, do not prevent using linked valid Details observations. Their original
snapshot evidence remains preserved; explicit invalid coordinates in usable observations
still block automatic coordinate adoption for the affected place.
An unresolved identity never becomes resolved through coordinates. Stale/foreign/corrupt
source material rejects the whole preparation. Extraction and replay perform no network,
LLM, planner-cache, database, field-mask or automatic-backfill work. Quality-report callers
may forward the same optional snapshot source without changing existing score/mask rules.

The [dated route acceptance record](../records/evaluation/routes.md#offline-scorer-and-coordinate-boundary)
preserves approval, reproduction, implementation and validation. The pre-existing reviewed
wire remains supported alongside the explicit snapshot-source option.

Optional mode_options maps modes to `{"time_basis": ..., "routing_options": {...}}`.
Defaults deliberately use time_independent WALK, time_independent DRIVE with explicit
TRAFFIC_UNAWARE, and explicit_departure TRANSIT. Explicit queries use the adopted
departure; time-independent queries use null departure and retain the estimate label
and acquisition timestamp, without claiming historical query support. Ticket 04 wire
validation and Ticket 07 provider/mode applicability are distinct: supported preferences,
modifiers/locales and exact departure are checked when interpreting frozen evidence.
Unsupported valid-wire context stays UNKNOWN without shifting dates or modes.

<a id="v0-route-request-package"></a>

## Offline V0 independent request package

This development smoke utility lives in
[`backend.evaluation.tools.route_requests`](../../backend/evaluation/tools/route_requests.py).
It is not an actual product planning stage or a prerequisite for final evaluator scoring.
The core `routes.py` preparation/scorer remains separate and is consumed by quality reports.
The CLI entry is `uv run rtpeval dev route-requests`; the former
root-level tool paths are historical identifiers, not current entry points.

`prepare_v0_route_requests(bundle_path, identity_report, *, prepared_at,
schedule_context=None, occupancy_reviews=None, route_reviews=None,
details_snapshot_directory=None, legacy=False, region_code="KR")` returns immutable `RouteRequestPackage`, schema
`rtpeval_v0_route_requests_2`. It replays the original V0/#66 material and the exact
current version-scoped identity report before using the existing occupancy/window preparation. It keeps
every selected V0 leg, source endpoints/dates/mode/estimate and continuous window,
identity blockers and coordinate readiness. Native scorers and V0-V3 planners are unchanged.

Default replay rejects historical identity policies. `legacy=True` (CLI `--legacy`) is
an explicit historical input path; it cannot establish current acceptance or rewrite old
saved packages. Supplying `identity_report=None` derives the current report from verified
independent material without a model result or call; it preserves missing-evidence UNKNOWN
blockers. Current identity replay has no mandatory human/audit gate. Supplied reports must
replay exactly against original intake and independent facts; rejected/corrupt sources
return `needs_material_correction` with no partial requests. The package records policy,
legacy selection, report origin and presence of a current V0 model result.

Per-leg `identity_endpoints` retain original claims, canonical identity (or null), candidate
correspondence, physical association and grounding verdicts. `identity_blockers`
expose endpoints without verified physical association. A confirmed address error
retains grounding FAIL and null canonical adoption; independently verified physical
association may still supply its endpoint. Candidate presence or coordinates alone
cannot establish that association. The separate route verdict remains UNKNOWN
without journey evidence. `eligible_endpoint_occurrences` counts non-null directed endpoint
occurrences; `eligible_endpoint_venues` counts their unique IDs. Neither implies all legs
are identity-eligible, coordinate-ready or provider-supported. Unknown identity cannot be
replaced by historical adoptions to enlarge the request inventory.

### Provider profiles and applicability

The default preparation retains the KR provider profile checked 2026-10-05; it does
not infer geographic support from names. The
[official coverage table](https://developers.google.com/maps/coverage) marks KR walking
and driving unavailable or low quality and omits transit coverage. Those facts retain
blocked WALK and conditional TRANSIT inventories, rather than a provider NO_ROUTE
or factual FAIL. The [matrix reference](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRouteMatrix)
supports explicit TRANSIT departures including past timestamps, but supplies no guaranteed
schedule horizon. Do not copy Compute Routes' 7/100-day horizon into this method.
WALK stays time independent and cannot certify historical/future conditions.

`region_code="AU"` (CLI `--region AU`) explicitly selects the Australian profile,
checked 2026-10-07. The original input destination must explicitly declare Australia
(for example, `Sydney, Australia`); unresolved or foreign declarations reject the
whole package. This is a source-bound declaration check, not a geographic lookup or
independent proof that coordinates lie in Australia. The official coverage table marks
Australian WALK available with good coverage/quality. WALK can be `ready_for_approval`
only after current identity replay, independent coordinates, a resolved continuous
window and all other leg checks pass. Missing coordinates/windows remain conditional;
unverified physical association stays blocked. Readiness leaves factual feasibility UNKNOWN.
AU TRANSIT retains the unverified-coverage and original-departure conditions. DRIVE
remains unsupported by this WALK/TRANSIT acquisition path despite national driving
coverage; there is no mode fallback. Unsupported region values are rejected.

AU selection is frozen in `replay_inputs` and the inventory digest; profile changes
fail exact preflight replay. Omitted region and explicit KR produce the unchanged
historical structure without an added replay field, so saved KR packages remain exact.
Budget and send counters count unique directed matrix requests, retaining every leg
occurrence. Duplicate links cannot promote a blocked/conditional query to ready. Neither
AU selection nor preflight creates live authority or actual route evidence. See the
[Sydney offline acceptance](../records/evaluation/routes.md#australian-preparation).

### Coordinates, directed requests and replay

Only independently associated endpoint IDs enter the venue inventory. Exact IDs deduplicate
Details while preserving every reference link. Replayed saved independent coordinates
retain raw hashes, pointers, request keys and timestamps. Reused Details additionally
require requested/returned canonical-ID equality. Missing coordinates may produce
`id,location` Details requests; invalid/conflicting observations remain blocked and
do not automatically backfill. Planner/model points are never admitted.

Supplied Details must use the package's exact `details_plan`. Offline snapshot replay
checks its intake/identity link, plan, safe paths, raw hashes and zero-retry attempt
ledger. Only exact requested/returned associated IDs and strict finite numeric coordinates
in range contribute. Evidence later than preparation is invalid. Unavailable/bad
responses stay diagnostic without proposing retries. An invalid plan/source rejects the
whole package rather than yielding partial requests.

Directed requests retain source WALK/TRANSIT and explicit original TRANSIT departure.
Requests without coordinates or required departure have no executable body. Full query,
coordinates/evidence and mask determine exact request keys; duplicate queries retain
leg links rather than collapsing occurrences. Every leg retains `UNKNOWN` without
independent journey evidence; confirmed same-canonical legs retain native `N/A`.
`ready_for_approval`, `conditional` and `blocked` describe preparation, never authorization.

### Reference prices and preflight limits

Masks/SKUs are frozen: Details `id,location` uses Place Details Essentials; 1x1 Compute
Route Matrix uses `originIndex,destinationIndex,status,condition,distanceMeters,duration,fallbackInfo`
and Compute Route Matrix Essentials without Pro/Enterprise modifiers. The
[official price list](https://developers.google.com/maps/billing-and-pricing/pricing) and
[SKU triggers](https://developers.google.com/maps/billing-and-pricing/sku-details), checked
2026-10-05, give USD 5/1,000 per Details request or matrix element at the global first
paid tier. No credit, discount, tax or actual invoice is assumed. Proposed sends/cost
and unready hypothetical inventory are separate; the eight-Details/four-Routes ceiling
is a planning bound, not an allowance.

The frozen package includes source hashes, `inventory_sha256`, masks/options/SKUs,
dated links, per-item/aggregate estimates, missing billing, a 20-second single-call
timeout, 300-second total deadline, exact operation counters and zero retries/search/model
calls. `preflight_v0_route_requests(bundle_path, identity_report, package, *, ledger,
next_request_key)` recomputes the package and checks exact sent keys, pending-item
cost/time reservation, duplicate/foreign requests, forbidden calls and limits. Its
result always says `live_authorized=false`. Source/inventory changes, unsupported context,
identity/coordinate mismatch, any provider failure/timeout or limit require stopping.
No live acquisition executor is implemented by this package.

The ledger has `sent_request_keys`, finite nonnegative `elapsed_seconds` and `cost_usd`,
and nonnegative integer `retry_sends`, `search_sends`, `model_sends`. Counts refer to
attempted sends (one element per matrix); cost must cover their undiscounted estimate.
Supplied snapshot sends are historical observations, separate from zero preparation sends.
Changed readiness needs a regenerated inventory and separate budget approval. Later
authorized execution uses a current-session child with `gpt-6.1-sol` / `medium`,
following a prepared, explicitly approved handoff and its numeric limits.

The [package guide](../guides/experiments.md#development-checks) owns CLI
invocation and exit codes. The [route history](../records/evaluation/routes.md) records
October 5–8 KR/AU preparations and executions, including zero-ready packages,
identity refreshes and provider-specific UNKNOWNs. Those dated inventories do not
establish new acquisition authority or update the frozen coverage/price references.

<a id="route-verdicts"></a>

## Route selection, applicability and scoring

The bridge adds resolved, source-linked `transport_modes` RequirementSpec
obligations to the existing independent mode-policy check. Applicable policies
intersect per date; contradictions require material correction. A known disallowed
claim FAILs, missing modes remain UNKNOWN, and another unresolved policy cannot
become PASS through the bridge. The requirement dimension owns these obligations;
route scoring excludes their duplicate mode policies while retaining full diagnostics.
Equivalent whole-trip mode sets with the same or nested original-source intervals
share that owner. Distinct source occurrences and independent restrictions remain
separate.

Keep consecutive primary occurrences within each delivered day; no inter-day routes.
Confirmed same-canonical legs are N/A; distinct venues at one address remain distinct.
V0 uses Activity claims, V1-V3 Transfers without ignored-Activity fallback. Duplicate
claims keep all sources but one leg. Conflicting Transfer or segmented/mixed Activity
journeys never become a favorable uninterrupted single-mode matrix claim.

Subtract applicable scheduled_commitments protections and fixed other occupancy from
the endpoint gap, excluding this leg's own transport. Preserve original obligation IDs
and scopes through blocker union. primary_visits-only protection does not block traffic.
Possibly overlapping unknown occupancy stays uncertain; known disjoint alternatives do
not contaminate unrelated routes. A guaranteed common occupation starting at the deadline
is a hard boundary; a merely possible deadline occupation stays UNKNOWN and cannot borrow
next-visit tolerance. Explicit departure controls and must fit one free span.
Otherwise choose the longest continuous fragment, tie earliest UTC start, before route
observations. Never concatenate spans, try a later fragment after failure or switch mode.

For provider duration d, reserve r and selected G, retain raw deficit max(0,d+r-G).
Hard protection/fixed-commitment deadlines require d+r <= G with zero grace; only the
next-visit deadline permits 300 seconds. DRIVE reserve is 600 seconds once, others zero.
Separate caps are WALK/TRANSIT 2700+300 seconds, DRIVE 1800+300 seconds, and WALK distance
<=3000 meters with no distance tolerance. Tolerances never sum. Exact and within-tolerance
PASS are labelled. Shared rule constants drive arithmetic and the emitted rules/hash.

Verify raw replay and full identity/occurrence/request reconstruction before scoring.
Corruption, foreign/unused linkage or wrong paired scope returns no partial cohort.
Valid wrong mode/departure/coordinates/options is inapplicable UNKNOWN evidence;
optional trusted plan additionally enforces exact acquisition-plan equality.
Historical non-TRANSIT explicit query is unsupported relative to acquisition; TRANSIT
and time-sensitive DRIVE need applicable explicit departure. No Compute Routes transit
horizon is copied into matrix policy. Query/itinerary clocks support six fractional
digits; provider durations preserve integer nanoseconds, without float rounding.

Parse raw status/condition independently of the available summary. Require a status
object: omitted code within it means default zero, malformed/error status stays UNKNOWN.
Successful ROUTE_NOT_FOUND FAILs with null duration/deficit; contradictory route fields
invalidate that observation. ROUTE_EXISTS uses nonnegative duration strings with up to
nine fractional digits, never staticDuration or rounded seconds. Missing WALK distance
or duration keeps its component UNKNOWN. Valid returned traffic fallback is accepted
and traced. Any independently proven component FAIL decides the leg; all required
components must PASS for combined PASS, otherwise UNKNOWN.

Report source claims/mode basis, selected fragment and deadline, component reasons and
classification, exact measurements, nominal caps/tolerances/reserve, expected/actual
query, raw attempts/hashes and preparation/source/rule/plan/manifest hashes. Structural,
applicable response, full-component, decisive and duration-available coverage differ.
No-route is decisive without duration; partial FAIL enters P/(P+F) without becoming
complete evidence. Unknown is null travel, never zero. Unresolved role/adjacency
populations and empty denominators suppress full-scope rates.

Daily/request sum, median and maximum are observed per-occurrence subtotals with missing
and unresolved counts; reserve is separate. Request deduplication never merges score
occurrences. Unknown potential legs prevent complete burden claims globally and on the
affected days. No route/overlap double weighting, auxiliary arithmetic, V3 repair delta
or formal comparison is calculated. Synthetic development tests do not establish real
provider availability, historical/future travel certainty or benchmark outcomes.

Nominal caps are independently applied product references, not planner verification verdicts.
The 300-second evaluation tolerance does not change planner thresholds or guarantee provider
error bounds. WALK's 2-km and motor 5-km geographic discovery filters are not provider route
distance caps. Only WALK has the 3-km observed-distance cap in this rule profile. A valid route
can exceed a cap and still count as observed evidence. Traffic fallback changes calculation
strategy, not the requested mode, and creates no independent traffic-fidelity score.

For example, TRANSIT duration 49 minutes passes the nominal 45+5 cap; in a 44-minute ordinary
next-visit gap it also passes the separate five-minute schedule tolerance, but in a 43-minute
gap schedule FAIL is decisive. A protection ending the same fragment permits no grace.
DRIVE duration 20 plus reserve 10 needs 30 minutes; the reserve is not added to provider burden.
These are rule illustrations, not measured provider outcomes or benchmark cases.

## Commands, code and decision history

Code owners: [opening](../../backend/evaluation/opening.py),
[routes](../../backend/evaluation/routes.py) and
[route preparation](../../backend/evaluation/_route_preparation.py).
[Package commands](../../backend/evaluation/README.md) own invocation/exit codes.
Opening [preflight](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/18#issuecomment-5955697757)
and [acceptance](../records/evaluation/opening.md#initial-scorer-and-time-corrections), route
[preflight](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/19#issuecomment-5955699412)
and [acceptance](../records/evaluation/routes.md#offline-scorer-and-coordinate-boundary) preserve decisions,
failed checks, corrections and executed validation. Historical immediate-departure, universal
schedule grace and partial-verdict proposals are superseded by the current rules above.
