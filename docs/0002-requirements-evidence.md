# Requirements, candidate supply and evidence

Status: Implemented shared contracts, updated 2026-10-15.

## Request and interpretation

`planning_request_2` carries destination, ISO trip dates, traveler count, a whole-trip
budget with currency, and optional preferences. Structured form facts are authoritative;
the interpretation stage does not re-extract or overwrite them. Invalid dates, range
violations and oversized text fail at their declared boundaries. Current exact limits
belong to [request schema](../backend/app/schemas/request.py), date policy and configuration.

Dates are strict date-only values. Traveler count is a strict positive integer and money
is finite, nonnegative Decimal with an explicit uppercase three-letter currency; boolean
amounts are rejected. Null/blank preferences become empty while nonblank text retains its
source content. The trusted reference date follows the application's configured timezone,
not the destination or browser clock. Product cannot supply the research reference-date
override. Source hashes bind normalized structured facts separately from optional preference text.

Empty preferences skip the interpretation model call. Nonempty preferences use one
shared interpretation stage. Exact source spans and subject provenance distinguish
hard named/count/date/exclusion obligations, qualitative wishes and unsupported or
ambiguous conditions. Gate validity is input acceptability, not a feasibility guarantee.
Clarification, dedicated safety outcomes, provider failure and malformed model output
remain different outcomes. Unsupported hard conditions are not silently softened.

The interpretation call returns `daily_pace`: one null-date default and unique
requested-date overrides, with `ordinary`, `relaxed`, `rich` or
`unresolved` profile, optional explicitly requested exact daily count and original
source quotes. Canonicalization verifies quote spans and date scope. Relaxed/rich
style does not invent an exact count. Empty preferences supply ordinary style locally;
historical absent/null metadata stays unassessed. `PreferenceDraftV13` and
`preference_prompt_20` identify the current wire/prompt. Only V3 Repair uses this
metadata as an optimization target; initial generation gains no zero-penalty constraint.

## Evidence ownership

| Source | Appropriate use | Limit |
| --- | --- | --- |
| Place details | Identity, location and supplied factual fields | Missing fields stay unknown |
| Weather | Available forecast context with source/units | Not a guarantee of conditions |
| Routes | Directed, applicable mode/time/endpoint estimates | Representative transit is not final-time proof |
| Official web evidence | Bounded supported claims with provenance | Extraction is not authority for unrelated claims |
| Reviews | Selective qualitative signals | Not official access, opening or cost truth |
| TripWorld | Retrieval prior and candidate discovery | Not current independent factual evidence |

Provider schemas stay behind adapters. Input-assistance GeoDB identifiers are UI selection
identifiers, not Google identities or planner evidence. Evidence acquisition obeys shared
limits and request deadlines; increasing a budget never relaxes correctness requirements.

Implementation owners include [interpretation](../backend/app/services/preference_interpretation.py),
[supply pipeline](../backend/app/services/planning_supply_pipeline.py),
[semantic service](../backend/app/services/poi_semantics.py), and
[landmark discovery](../backend/app/services/landmark_discovery.py).
Task histories are [preference/landmark #26](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/26)
and [semantic correction #28](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/28).

## Input gate and provenance contract

Schema/date validation precedes interpretation. A current wire response must include
`preference_input_assessment`; a nullable historical domain field means unassessed,
not VALID. Application policy validates disposition, typed issues and exact case-sensitive
quote occurrences. Safety blocks precede rewrite, clarification and continuation.
Missing assessment, inconsistent disposition and invalid source references are system
contract failures, not evidence that the user wrote an invalid request.

Current planning envelopes select `preference_draft_13` and canonical
`interpreted_requirements_5`. The provider receives request-bound IDs for original
single-codepoint spans, including whitespace. Every original substring boundary is
representable, including short scopes within unbroken text. Each source selects inclusive
`first_id`/`last_id` endpoints;
the program restores the exact contiguous original text, occurrence and Unicode
offsets before existing provenance validation. This covers semantic, focus, subject,
issue, operational, pace and transport sources, including source-text fields. Unknown,
reversed and foreign-request IDs fail with a field path. Selection does not certify
the model's semantic interpretation. No fuzzy matching or retry is added. The inventory
grows with preference length; fresh live preparation must account for the actual expanded
request. Required prompt projection replacements are checked before any model send;
instruction drift is a configuration failure.

The new pace wire has a required `trip_default` object and `date_overrides` array.
The mapper requires a null default date and non-null override dates; canonical checks
enforce unique in-trip dates and sources for expressed styles/counts. An ordinary
unsourced default has no exact count. Relaxed/rich styles create no numerical quota.
Historical quote/occurrence DTOs, list/null pace and canonical versions 3/4 retain
their existing read paths; malformed historical empty pace remains invalid.

Native generation `failure.json` retains the exception type and allowlisted
category/status, code, stage, field paths or requirement IDs from the boundary cause.
Source, pace and hard-gate failures remain distinguishable without copying sensitive
source quotations into default failure telemetry.

Supported input issues cover destination/structured-field conflicts, scoped hard
contradictions, unsupported scope, material ambiguity, non-travel task control and the
explicit supported safety categories. Contradictions require distinct located sources.
A missing quotation is permitted only by the structured-field conflict rule and its
independently sourced operational conflict; no fuzzy quotation is fabricated. Structural
grounding cannot certify that a model's interpretation is semantically correct.

Semantic text remains open vocabulary with typed strength, polarity, subject, scope and
source links. Canonicalization rewrites duplicate links without duplicate reward. Unknown
subjects are not silently party-wide. Named counts/dates belong to named visit obligations;
category goals use semantic assessment. Unsupported hard semantics require clarification;
ordinary rich/varied/enjoyable wishes stay soft without invented quotas or luxury budgets.
The supported exception is a whole-party, whole-trip `transport_constraint`: a nonempty
unique `allowed_modes` set linked to hard transport constraint requirements and their
exact canonical sources. Its narrow registered predicate authorizes enforcement;
it does not establish route feasibility. Single-mode `transport_preference` remains
a preference subordinate to this set. Unsupported modes/semantics remain explicit.
The narrowed experience scope is ordinary/exclusive. Historical themed payloads are
not silently upgraded.

Typed requested-place information, transport restrictions and experience dimensions keep
their acquisition meanings while semantic text stays open vocabulary. Preferred/avoided
experience values obey membership, uniqueness and disjointness checks; category priors cannot
be promoted into experience facts. Initial RequirementAssessment distinguishes evidence-linked
from semantic-only capability with not-acquired/unknown status; there is no general predicate
certifying arbitrary text. [Canonical requirements](../backend/app/schemas/interpreted_requirements.py)
and [boundary validation](../backend/app/schemas/requirement_boundary.py) own current field/count/
quote/subject bounds, canonical offsets and reference membership. These serialization limits
are distinct from runtime discovery/query limits.

Gate execution precedes lazy travel/retrieval acquisition. Provider refusals, model-authored
safety decisions and malformed output remain distinct. Product retains the form and clears
stale feedback on edit, renders quotations as text and does not echo sensitive safety quotes.
Developer contract failures use HTTP 502 versus clarification 422; CLI failure and
clarification have distinct exit outcomes. Default telemetry excludes raw preference quotes.

## Semantic qualification and multiplicity

An ordinary count-free positive POI interest has a soft target of one distinct qualifying
POI. An explicitly sourced trip focus has target two, requiring exact focus provenance. Explicit
counts, dated obligations, exclusions and exclusive restrictions take priority. Broad
enjoyment creates no invented numerical obligation. Explicit exclusive scope and ordinary
interests remain distinguishable. Candidate opportunity is not final scheduled fulfillment.

V0 receives shared interpretation/generation guidance but has no externally grounded
candidate-semantic verification. Name-based observations are proxies. V1-V3 can report
grounded coverage against canonical identities and actual visit-object judgments.

Models receive compact application-owned references; strict mapping restores canonical
identities. A model cannot create a new identity, evidence citation or exception by naming
one in its answer. Responses are validated before caching/admission. Bounded correction
is restricted to its declared invalid/missing-reference cases; ordinary semantic rejection
or an unrelated failure does not authorize arbitrary retries. Missing assessment remains
unauthorized rather than silently qualifying a candidate.

All factual-gate-qualified candidates competing for main supply receive bounded semantic
assessment. Actual visit object, role, scoped exception, per-requirement relation and supplied
evidence references remain separate fields. Ordinary restaurants/cafes/offices are not main
attractions absent an explicit applicable exception. A corporate museum and its cafe are
different visit objects. Related alternatives do not establish the original goal satisfied.
Unknown role does not establish coverage; known role with unknown hours retains that uncertainty.

Exactly one valid result per submitted identity is required. Unknown/duplicate/missing
identities and invalid exception/evidence references fail the contract. Supported matches
require same-candidate supplied evidence. Application-owned compact handles resolve to
canonical references; syntactic membership alone is not semantic proof. Assessment caching
binds identity, decision-relevant evidence, requirements/exceptions and prompt/schema context,
not round or trace IDs. Beyond the explicitly supported bounded reference correction,
semantic/model failures do not silently continue to generation or return successful Repair.

Unrequested canonical repeat visits are policy violations within or across days. Explicit
exact/minimum counts, distinct dates and revisit permissions retain their own meanings;
minimum counts are not maxima. Exception allowances apply to the goal across alternatives,
not once per candidate. Historical missing multiplicity remains unassessed. Soft coverage
counts distinct supported scheduled identities, not candidate matches or repeated visits;
one place may satisfy multiple goals. Soft gaps do not create new confirmed Repair targets.

## Admission, acquisition and deterministic supply

The shared V1-V3 pipeline discovers bounded candidates, resolves/deduplicates identities,
acquires normalized details and permitted supplementary evidence, assesses semantics,
and selects a bounded supply. Destination landmark nomination is an independent bounded
opportunity source, not a substitute for satisfying requirements. Landmark opportunities
remain eligible after preference targets are met. Discovery source and factual evidence
source are recorded separately; Google resolution does not imply Google discovery.

TripWorld adds retrieval candidates in V2/V3 before canonical merge. Admission still
requires the applicable identity and evidence checks. A retrieval score, category label
or review signal does not independently prove current availability or suitability.

Discovery provenance gives an opportunity, not proof of a preference match. Soft targets
receive one additional distinct candidate alternative; saturation reduces priority without
capping final category counts or suppressing independent landmark value. Multiple intents
cannot reset the same goal. Before assessment, discovery associations order opportunities;
after assessment only supported matches establish semantic progress.

Google and resolved RAG identities share one canonical admission pool and capacity policy.
Required identities precede strength/intent rotation and cheap eligibility/geography checks.
Admission does not reward cache presence, ratings, provider rank or cosine as factual quality.
Details first reuses all compatible successful cache entries passing the common factual gate,
then sends bounded new requests. Success and send ceilings differ; failed sends count and
failed/cancelled attempts are not secretly repeated. Semantic qualification can continue the
existing Details queue within the same original counters; it does not reset budgets.

Final deterministic supply protects required/excluded obligations, rotates linked opportunities,
then considers supported alignment, conflicts and experience diversity. Unknown Profile
judgments abstain. Ratings only break eligible ties when all compared entries have them;
distance and stable identity preserve deterministic fallback. No RAG quota, cosine reward
or model subset-search is introduced. Reviews/Profile are selective bounded acquisitions.
Supply can remain below its target. Runtime policy owns exact capacities and send ceilings.

Exploration opportunities apply at admission, acquisition and optional final supply, rather
than reserving final slots after general candidates have already been lost. The configured
fraction rotates source opportunities after required identities; an exhausted lane can
release capacity. A mixed-source identity occupies one position. Explicit exclusive scope
constrains exploration without inventing a general-tourism obligation. Exception alternatives
share the existing supply capacity and their configured per-goal allowance; they are not
extra slots or extra scheduled exception visits. Unattempted candidates are not classified
as unsuitable merely because preparation reached a capacity/deadline boundary.

Reliably resolved required identities may expand acquisition and supply within the required
capacity ceiling. Duration-dependent acquisition basis and final supply floor remain distinct;
a larger final supply target does not automatically grant more Details sends. Exceeding the
required-identity ceiling is an explicit capacity conflict, while an ordinary supply shortfall
does not itself demand clarification. Exact formulas belong to
[capacity policy](../backend/app/policies/poi_capacity.py) and active limits to runtime config.
Candidate acquisition is composed into the supply pipeline; retired selector/subset experiments
are not runtime dependencies. Discovery sends, Details successes/failures, semantic assessment,
Profile, final supply and scheduled identities retain separate accounting.

## Forecast, operating facts and official web

Open-Meteo supplies trip-date daily forecasts, normalized units and source timestamps.
Out-of-range days are excluded; absent/provider-failed forecasts remain unavailable. There
is no historical/hourly forecast fallback or invented weather. Applicable current opening
windows and regular weekly hours remain separate; regular hours do not prove no holiday
override, nor establish ticket/access availability.

Official web work starts from typed requested-place information and concrete residual risks
on the selected shortlist, not a second interpretation of raw preferences. Tasks deduplicate
identity, need, trip date and subject scope. Explicit required needs precede optional risks;
not every venue gets a speculative exception search. One bounded reasoner uses supplied
material, followed by source-authority/support/applicability checks and claim-scoped resolution.
Query context, community summaries and model explanations are not official factual evidence.
No discovered exception is not proof of its absence. Incompatible facts remain conflicts.

Factual precedence is authoritative official evidence, authoritative structured provider
evidence, other recent web material, then visitor/community experience. A rating or review
summary cannot override a confirmed date-specific closure. This is claim-scoped evidence
resolution, not a rule that one provider wins every unrelated dimension.

Web tasks run after final supply selection. Their priority is required-place explicit residual
needs, other named-place explicit residual needs, required-place concrete risks, other named
risks, then other selected-place risks. Temporary closure, future opening, contradictory or
missing operational status and trip-relevant date conflicts are concrete risks. Equivalent
tasks merge requested facets. Optional page retrieval is bounded and used only when supplied
native evidence is insufficient. There is no experience Web Search path. Weather informs
scheduling rather than reselecting the supplied POI set; its destination-local daily records
retain condition, min/max Celsius, precipitation probability and maximum wind in km/h, with
availability, location, retrieval timestamp and source reference.

## Discovery and identity

User-named search intents run first. General top-attractions discovery gets the next
opportunity when the shared search pool remains, including requests with eight interests.
Ordinary discovery then leaves up to four opportunities for unresolved nominations;
unused opportunities return to ordinary work. Supplementary sends are part of the existing
twelve candidate-search sends, never an additional pool. Cache hits consume no sends.

Existing exact normalized provider display-name matching resolves names against acquired
results. Ambiguous names, aliases and unmatched names remain unresolved; first hits and
nearby/parent attractions are not substitutes. Identity is reconciled again after RAG
source expansion, clearing metadata if a later same-name, different-ID result is ambiguous.

Resolved candidates retain model origin and earliest rank through merge, Details,
qualification, selection input and generation projection. They do not become user REQUIRED
places. Existing exclusions, exclusive scopes, role and factual eligibility still apply.
Nomination is not evidence of opening hours, tickets, costs, suitability or feasibility.
Existing C/G/K, Details, RAG, semantic, route and Repair limits remain unchanged.

## Failure and observability

Landmark nomination/discovery invalid or empty output, auxiliary provider failure, timeout
and unresolved nominations fall back to the available qualified pool with recorded degraded status. Cancellation
propagates; unrelated identity/qualification failures retain their existing behavior.

Trace events `landmark_nomination` and `landmark_discovery` record attempts, elapsed time,
reported usage, resolution/reuse counts, qualification/selection counts and allocation stops.
The independent `budget.json` stage `landmark_nomination` retains numeric observations,
limits and allowlisted statuses. Missing billed usage stays missing. Existing 32-call-record
and 64-KiB artifact limits remain; no names, prompts or raw provider envelopes are added
to the compact summary. Token engineering estimates are not billed usage.

Landmark nomination is one destination-only auxiliary names call after gate acceptance in
V1-V3, with no retry/correction; V0 and V3 Repair do not call it. Limits are configured under
`landmark_nomination`. A nomination is neither REQUIRED nor evidence of visit feasibility.

## Calendar support versus same-day remaining-time planning

Current trip_dates admits today through today+13, with end-start+1 <=10. The shared validator
serves V0/V1/V2, CLI and development runners; capacity depends on duration, not departure offset.
GET /api/planning/date-window publishes the server's bounds without initializing any model/provider.
The frontend end-date maximum is min(start+9, allowedEnd); backend submission validation is authoritative.
The developer page initializes its explicitly editable research reference date from the same endpoint.
Unavailable date-policy loading disables product submission; no browser-local fallback is guessed.

Same-day remaining-hour planning remains unsupported: accepting today does not ensure past
hours are avoided. The earlier +9 calendar window is recorded in
[V1 history](records/v0-v3/v1-development.md); it does not constrain the current +13 window
or authorize a formal evaluation protocol.
