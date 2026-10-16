# Reliable Trip Plan Agent terminology

These terms distinguish planning declarations, Repair exploration and selected delivery.

## Activity time use

**Scheduled** assigns an activity to its submitted interval, even when movable or
unbooked. **Free window** describes discretionary availability with no adopted
activity commitment. These are planning declarations, separate from primary-visit
role, fixed-time requirements and verified facts. The detailed legal combinations
belong to the [activity contract](docs/0003-itinerary-transport.md#activity-semantics-contract-phase-2).

## Repair

**Exploration itinerary**:
An intermediate itinerary considered during Repair search. It may have equal or
greater soft pace deductions than the best retained itinerary; exploration does
not imply final selection.

**Best retained itinerary**:
The publishable itinerary retained as the best found under the declared Repair
priorities. It may still contain explicitly reported unresolved targets.
