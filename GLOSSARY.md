# Reliable Trip Plan Agent terminology

These terms distinguish Product planning concepts, activity declarations and Repair selection.

## Product planning

**Planning draft**:
Travel requirements saved for later editing or submission. A draft is not a generated
itinerary.

**Planning task**:
An account-owned attempt to generate an itinerary from confirmed travel requirements.
Its progress and outcome remain accessible independently of the current page.

**Itinerary preview**:
A generated or imported itinerary awaiting the traveler's decision to save or
discard it. A preview is separate from the saved-trip library.

**Saved trip**:
An itinerary the traveler has explicitly saved to their trip library. Saving does
not mean that every requirement or travel detail has been verified.

**Example itinerary**:
A sample itinerary offered in the guest trip-library view, separate from an
account's own saved trips and planning drafts.

**Trip copy**:
An independent saved trip containing a copy of an existing itinerary without a new
generation. Managing the copy does not change its source trip.

**Replanning**:
A new planning task starting from an earlier itinerary's editable travel requirements.
The earlier itinerary remains unchanged.

**Transport preference**:
Travel modes the traveler would prefer the planner to prioritize. Selecting modes
does not prohibit other modes; an empty selection expresses no preference.

## Activity time use

**Scheduled** assigns an activity to its submitted interval, even when movable or
unbooked. **Free window** describes discretionary availability with no adopted
activity commitment. These are planning declarations, separate from primary-visit
role, fixed-time requirements and verified facts. The detailed legal combinations
belong to the [activity contract](docs/0003-itinerary-transport.md#activity-semantics).

## Repair

**Exploration itinerary**:
An intermediate itinerary considered during Repair search. It may have equal or
greater soft pace deductions than the best retained itinerary; exploration does
not imply final selection.

**Best retained itinerary**:
The publishable itinerary retained as the best found under the declared Repair
priorities. It may still contain explicitly reported unresolved targets.
