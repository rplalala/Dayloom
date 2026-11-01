# Itinerary and transport

The itinerary separates scheduled primary visits, supporting activities, free windows,
application-owned transfers and optional Nearby references. These roles determine
counting and occupancy; display titles and photographs do not.

## Scheduled activities and references

`itinerary_3` requires explicit activity kind and `time_use`. Historical readers
retain missing declarations rather than manufacturing them.

| Kind | Legal time use | Meaning |
| --- | --- | --- |
| `main_poi` | `scheduled` | Principal visit occurrence; identity checked separately |
| `generic_activity` | `scheduled` or `free_window` | Supporting activity or discretionary suggestion |
| `free_time` | `free_window` | Unassigned availability |
| `transport` | `scheduled`, V0 only | Declared journey with directed occurrence endpoints |

A movable walk can occupy planned time. Booking, pace, fixed-time requirements and
occupancy are independent. Unknown kinds and absent/null time use are invalid in a
new generation; named optional principal visits belong in unscheduled references.
Relabeling cannot remove an original hard visit obligation.

For V1–V3, a main visit must use an authorized acquired identity whose semantic
assessment is `main_eligible=true`. A generic title cannot repair an invalid main
visit. The application supplies `place_name` and complete `formatted_address`
(including null) from evidence; foreign IDs fail before normalization. V0 retains
its model-name boundary. Original captures are never rewritten.

Normalization stably sorts activities by start within each existing day, preserving
ties, group membership, fields and diagnostic pointers. It does not fix overlap,
reorder days or invent time. Optional `atmosphere_theme` affects presentation only;
[Product media](0007-application-operations.md#supporting-atmosphere-photos) owns its mapping.

Nearby is optional, unscheduled and excluded from primary counts, occupancy, costs,
booking and required fulfillment. V0 uses up to three model-knowledge references;
V1–V3 acquire bounded references after final primary selection. Unused supply does
not become Nearby automatically. Regular Nearby failure preserves the primary;
cancellation propagates.

## Civil time and IANA acceptance

Tools generation uses `tools_civil_time_1`: local date/clock plus a sourced IANA
zone. Normally null offsets are resolved for each endpoint and date. Repair uses
the same boundary; V0 keeps its independent explicit-offset format.

DST gaps fail. Repeated clocks require a valid explicit offset; the application
never guesses a fold. Missing/conflicting zones cannot be invented. A venue without
a zone may use one consistent recognized planning context. Historical explicit
offsets are checked when a zone is known; missing legacy context stays unassessed.

Elapsed calculations use UTC instants and return to local time. Protection windows
may span 23 or 25 hours; both endpoints and free-window/transfer arithmetic use the
same mapping. Ambiguous protected clocks remain unresolved.

## Transport ownership

V0 declares estimated transport activities with structured nullable
`transport: {mode, from_activity_id, to_activity_id}`. Supported modes are WALK,
TRANSIT and DRIVE, or null when allowed. Endpoints identify a directed consecutive
primary pair on the same day. Distinct occurrences at one venue remain distinct
endpoints. There is at most one selected declaration per pair; hotels and cross-day
journeys are not invented. Historical absent fields remain absent.

V1–V3 cannot emit transport activities. They use application-owned route options and
final transfers bound to actual adjacency and departure. Invalid model declarations
fail rather than being silently dropped. Representative transit evidence is not a
final-time PASS. Missing transfer evidence does not erase a real candidate journey.

A sourced hard allowed-mode set constrains generation, acquisition, caches, Repair
and final adoption. Soft transport priorities cannot expand it. V0 must explicitly
cover required adjacent named journeys with allowed declarations; missing, unknown
or disallowed modes fail without a corrective retry. Unavailable allowed routes
remain UNKNOWN rather than triggering disallowed DRIVE fallback.

## Coverage, uncertainty and costs

Minimum daily coverage is one countable main visit, classified satisfied, missing,
exempt or unknown. V0 uses name proxies; tools versions use qualified identities.
Meals, filler, Nearby and transfers do not count. A supported required cafe exception
can count as main. Explicit zero totals or established full-day protection can exempt
coverage; relaxed pace or a nearly full day does not. Unresolved roles, obligations
or time remain UNKNOWN. A blank day's 09:00–18:00 window requires reliable zone context.

V0–V2 diagnose coverage; V3 can repair it. Priority is hard obligations, then minimum
coverage, then optional quantity. Disabling optional quantity leaves minimum coverage
active. No inferred visit duration or incomplete search proves infeasibility.

Money remains nullable with currency and scope. A range midpoint is usable only under
its declared mapping policy, not as independent cost evidence. Sum only reliable,
nonoverlapping, scope-compatible amounts. Exceeding a comparable budget can establish
FAIL; whole-budget PASS needs complete in-scope evidence. Activity estimates alone
cannot certify accommodation/transport or total affordability.

## Generation diagnostics and counting contract

Diagnostics inventory every requested date, including missing/empty days. They keep
main occurrences, distinct identities, repeats and other roles separate. Initial
generation normally targets two to five distinct main visits on a full day, subject
to sourced pace, long visits, rest, requirements and evidence; this is not a hard quota.

| Observation | Interpretation |
| --- | --- |
| Empty day | No primary activities, distinct from zero main visits among supporting activities |
| Repetition | Occurrences minus distinct identities; policy violations require sourced multiplicity rules |
| Supply utilization | Scheduled supplied identities / distinct supply; unavailable for V0 or zero supply |
| Required coverage | Resolved scheduled/unscheduled obligations, with unresolved identities separate |
| Output roles | Linked versus qualified-main populations, excluding free windows from scheduled identities |
| Cost coverage | Reliable compatible costs / primary activities; no activities means unavailable |

Same-day remaining-hour or unresolved-role quantity diagnostics remain unassessable.
Cross-day repeats are counted on each subsequent day. Unknown is not zero. Diagnostics
alone do not trigger extra acquisition or generation; V3 needs an authorized target.
These definitions do not claim that every historical measurement is implemented.

## Route evidence and projection details

Route matrices preserve directed observations, no-route and not-observed states.
Chunking must cover the requested destination inventory. Sparse/mixed queries share
limits and explicit reserves. A mirrored estimate cannot fabricate reverse conditions.
A leg needs one continuous available interval; disconnected gaps cannot be added.
Unbound journeys retain diagnostics without invented occupancy. Provider seconds/
metres and application reserves remain separate in public projection.

## Nearby acquisition details

Use qualified scheduled anchors with coordinates, ordered by date/start/ID and
canonical place. Direct representative matching is not transitive clustering; an
area cap can leave later dates without references. DISTANCE queries use bounded
radius/types and a minimal identity/name/coordinate/address/type/status/attribution
mask. This stage performs no Details, ratings/reviews, hours, routes, web or model work.

Cache keys bind the full query; successful results can be reused, while failed sends
still consume limits. Remove invalid identities, geographic mismatches, scheduled
places and duplicates. Unknown eligibility is neither rejection nor preference proof.
Stable round-robin selection uses distance and identity. Attach references only through
their own acquired ledger, source/name, exact anchor and compatible date. Straight-line
distance establishes neither walking time nor access.

## Activity semantics

The current declaration contract separates planned occupancy from optional availability.
DTOs, mapping, output acceptance, schedule, Repair, persistence and evaluation retain
these declarations without silently filling, deleting or relabeling them. The pure
claim reader shares grammar, not planner truth judgments. Independent evaluation
reconstructs its view from submitted bytes and versioned policies.

### Numerical scoring policy and limits

`rtpeval_declared_population_1` is a separately versioned scoring profile. Before
acquisition it freezes a finite source-linked inventory:

- One parent check per executable reviewed obligation, retaining component outcomes.
- One grounding and opening candidate per declared primary occurrence.
- One non-overlap unit per scheduled activity or selected logical journey.
- One route candidate per directed consecutive primary pair.

Protections block occupancy and retain obligation checks; they add no occupancy unit.
Candidate membership, factual outcome and verified inapplicability remain separate.
Missing identity, hours or route evidence cannot erase a candidate. Confirmed N/A
requires a reason; uncertain applicability remains UNKNOWN. For positive
`N = candidate_count - verified_NA_count`, the verified fraction is `100 * PASS / N`.
FAIL, UNKNOWN, coverage and unknown rate remain visible. Zero verified fraction with
zero coverage does not establish zero real-world compliance.

Common-mask weights and density subtraction remain versioned. This profile changes
population accounting and must not be described as merely a serialization correction
to historical totals. Unresolved membership, roles, journeys, requirement structure
or density policy yields `needs_population_resolution` before paid acquisition.

A parseable positive interval whose only defect is `timezone_offset_conflict` may
retain its population when the declared date and both endpoints still belong to the
same requested date under the reviewed zone. Record the instant as non-blocking
`time_uncertainties`; award no factual credit or inferred correction. Missing or
unparseable timestamps and conflicting membership retain blockers.

Numerical totals require population-ready source material, complete acquisition
receipts (possibly unavailable facts), established density and a nonempty score mask.
All-N/A stays N/A; abandoned acquisition or ambiguous populations receive no invented
zero/100 score.

### Selection and verification boundaries

New-wire normal preparation and quality reporting select this profile automatically.
Historical batches retain their defaults; explicit opt-in uses
`--quality-profile rtpeval_declared_population_1`. Preparation binds inventory,
review/source hashes and profile in its digest; execution/replay verify that binding.
Historical `itinerary_1/2` and original prepared packages remain readable, with derived
claims labelled by their original policy rather than attributed to a model.

Supporting scheduled activities remain route barriers without becoming primary
endpoints; free windows create no occupancy. Repair preserves declarations through
retiming, copying and fragmentation, assigning scheduled use to authorized new main
visits. A same-venue supporting activity cannot fulfill a new-wire required main visit.
The [implementation/audit record](records/evaluation/intake-identity-usage.md)
retains the historical ambiguity and validation evidence.
