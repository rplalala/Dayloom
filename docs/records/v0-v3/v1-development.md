# V1 acquisition and supply engineering evidence

September 2026 development evolved from a bounded tools baseline to qualified deterministic
planning supply. Current contracts belong to [requirements/evidence](../../0002-requirements-evidence.md)
and [transport](../../0003-itinerary-transport.md); [milestones](v1-milestone.md) retain
explicit freeze/reopening dates. Local evidence paths below are historical identifiers.

## Provider and evidence foundation

The 12 September baseline added Places, daily Weather and Routes without Reviews, Web,
RAG or Repair. Minimal discovery preceded rich Details; request-local caches and counters
separated critical failures from partial evidence. Missing facts were not synthesized.

Sydney run `83b678ac-3331-43b7-b9b0-847662d1a7e6` discovered 16 candidates, detailed eight
and queried 64 WALK elements. Forty-two directed nonwalkable observations collapsed to
21 pairs; eight alternatives were admitted. Six TRANSIT requests supplied eight elements
at a representative departure, with reverse estimates labelled rather than treated as
observed journeys. Total routes: seven calls/72 elements. The Weather payload was not
retained, so it cannot be reconstructed from metadata alone.

Revised review acquisition separated rating from source-linked ExperienceProfile, used
bounded deduplicated reviews and treated failure neutrally. A revised nine-day smoke reached
16 supplied POIs and 256 WALK elements. Broad official-web searching then exhausted six
search/six page calls across 16 tasks with no accepted fact; later policy focused on selected
places and explicit/concrete risks. UNKNOWN was retained instead of invented access facts.

## Retired selection approaches

QCGRE used greedy relevance/coverage/geography/rating/experience selection. B1 replaced
parts with direct model selection; B2 separated model judgments from deterministic subsets.
Repeated raw B1 outputs had incomplete coverage, overlap and unsupported references. After
B2 budget/serialization fixes, five identical-input judgments were valid but produced two-
or three-place sets: exact agreement 40%, Jaccard 0.8. Token fit did not remove semantic
variation or under-supply. Direct frozen matrices bypassed service repair/fallback, so
invalid fractions were not production failure rates.

A fixed-pool offline study found 41 observations→34 canonical→20 admitted→10 eligible→two
selected. Original subset sizes 2–8 tied on non-cardinality objectives; eight omitted venues
lost first on `-size` despite individually adding without degrading earlier objectives.
Minimal semantic coverage was therefore an unsuitable proxy for multi-day planning supply.
A qualified-supply counterfactual supplied the same eight places across six judgments;
a small baseline overlapped seven/eight. No full QCGRE or itinerary-quality comparison
was possible because old intent inputs/raw method logs were missing or overwritten.

The accepted replacement filled bounded options deterministically with required identities,
intent rotation, supported Profile direction/conflict, conservative variety and comparable
rating/geographic ties. It removed the mandatory subset evaluator without asserting model
judgments had no value. The affected gate passed 193; backend passed 673 with nine skips.
QCGRE/B1/B2 implementations and recovery snapshots were later deleted. QCGRE source remains
in Git at `60902ac09a1331f6eebddba8963efd24f6e8e61a`; uncommitted B1 has no guaranteed
complete recovery. Evidence: `logs/selector_live_20260918/`, `logs/selector_fix_20260919/`,
`logs/b2_budget_live_20260919/`, `artifacts/research/selection_objective/`.

## Shared requirements, Nearby and lifecycle corrections

The 19 September shared-input/supply gate recorded 829 passes, nine skips and eight failures:
seven stale fixtures plus a real bounded timeout problem. Correction stopped unconditionally
at timeout and awaited cancellation; 53 affected checks passed. The original full invocation
remained failed. Later [shared pilots](development-pilots.md) retain their separate results.

Post-primary Nearby acquired only bounded minimal discovery facts around actual scheduled
anchors. One Sydney V1 sample supplied eight places, scheduled five and independently attached
three references. Details/reviews/routes were not silently added to Nearby. Captured identity,
anchor and distance facts did not establish access or walking feasibility. Failure/cancellation/
cache branches had offline rather than universal live coverage.

## Shared mixed transport

The 25 September work made first-generation modes application-owned across V1–V3, with
actual-departure binding, shared acquisition limits and explicit DRIVE reserves. Admission
of a route pair was distinct from an actual send. Cache reuse did not reset failure history
or Repair counters. The transfer output preserved unresolved bindings rather than inventing
occupancy. Relevant consolidation passed 119 tests; later prompt-only changes did not imply
another complete live flow.

## Limits

Representative TRANSIT and mirrored reverse duration remain estimates, not timetable/fare
proof. Reviews, Web and selected candidate supply can remain sparse or unknown. Bounded
integration and historical freezes establish neither universal evidence-following nor a
formal version comparison. Required identity, non-main food support and later source-reference
changes retain their own [semantic evidence](poi-semantics-closeout.md).
