# Itinerary, transport and presentation contracts

Status: Implemented shared output contract, consolidated 2026-10-03;
V0 structured declarations added 2026-10-05.

## Scheduled activities and references

Output role accounting separates scheduled identities, unlinked activities, unused supply,
independently acquired references and unarranged REQUIRED identities. Policy completion and
goal progress are diagnostic observations, distinct from real-world feasibility.

`itinerary_2` separates dated/timed primary activities from optional unscheduled Nearby
references. References have no scheduled occupancy, planned cost or booking implication;
they do not fulfill a required visit or increase primary-visit counts. Empty reference
output is valid. V0's optional references are model knowledge with no fabricated provider
identity. V1-V3 use independent bounded Nearby acquisition after the final primary plan.

Primary source identities resolve against authorized supply. Generic activities can have
no venue identity where supported, but missing named identities are not fuzzy-matched into
validity. Nearby identities resolve against that acquisition's evidence, which can differ
from the primary supply. The application preserves attribution and deduplicates references
against scheduled identities. An unused supply candidate is not automatically a reference.

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
unspecified hotel or cross-day journey. V0 transport activities can carry `transport: {mode, from_activity_id, to_activity_id}`.
Mode is `WALK`, `TRANSIT`, `DRIVE` or null; endpoints are nonempty activity IDs.
The new V0 provider schema requires the nullable field on every activity. Its prompt
requires an object on transport activities and null elsewhere, directed between
consecutive visits on the same day. Titles/notes describe estimates but do not replace
these fields. This declaration supplies neither verified duration nor route evidence.

Shared Activity accepts historical missing/null declarations and omits them on output,
preserving the old activity wire shape. A present object survives nested PlanningResult
serialization; a declaration on a non-transport activity fails structural validation.
V1-V3 provider DTOs do not gain the field. V0 keeps its tool-free generation path and
does not validate/repair endpoint feasibility or create application-owned transfers.
Independent evaluation retains invalid associations and unknown modes, with separate
review precedence; see the [intake contract](contracts/0002-intake-identity-usage.md#claims)
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
Semantic eligibility controls canonical primary qualification independently of model relabeling.

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
