"""Pure declaration grammar and source-labelled legacy reading, never factual truth."""

from dataclasses import dataclass
from typing import Literal

TimeUse = Literal["scheduled", "free_window"]
LEGAL_TIME_USE = {
    "main_poi": {"scheduled"},
    "generic_activity": {"scheduled", "free_window"},
    "free_time": {"free_window"},
    "transport": {"scheduled"},
}

GENERATION_ACTIVITY_CONTRACT = """
Activity contract: itinerary_3. Every activity requires time_use=scheduled|free_window.
main_poi means a selected principal sightseeing/experience occurrence with its actual
place_name and time_use=scheduled. generic_activity is explicitly non-primary (a supporting
meal, rest or walk), even if it has a venue name. Choose scheduled when its interval is
occupied in this submitted plan; movable, relaxed or unbooked does not mean unoccupied.
Choose free_window only for discretionary availability with no adopted commitment.
free_time requires free_window; transport requires scheduled and is authored only by V0.
Never emit unknown roles, null/missing time_use or contradictory combinations. Keep optional
principal visits in unscheduled references, not scheduled counts. A free-window suggestion
cannot claim confirmed booking/admission or fulfillment of a required visit. Do not invent
a park identity for unspecified outdoor time. Hard fixed-time requirements, bookings and
pace are separate from planned occupancy. Keep unique IDs, positive offset-aware intervals
on the declared date, and the intended activity sequence. Never choose labels to improve
an evaluation score. Declarations do not verify real-world facts.
""".strip()


@dataclass(frozen=True)
class ActivityClaim:
    kind: str
    time_use: str | None
    provenance: str


def read_activity_claim(raw, wire):
    """Read a declaration without altering source bytes or guessing prose intent."""
    kind = raw.get("activity_kind", "unknown")
    if wire == "itinerary_3":
        time_use = raw.get("time_use")
        if kind not in LEGAL_TIME_USE or time_use not in LEGAL_TIME_USE[kind]:
            raise ValueError("itinerary_3 requires a legal activity_kind/time_use declaration")
        return ActivityClaim(kind, time_use, "declared_itinerary_3")
    if wire not in ("itinerary_1", "itinerary_2"):
        raise ValueError("Unsupported itinerary wire")
    # Historical primary visits and transports occupy the original submitted plan.
    # Free/generic prose needs the original policy/review; no new default is invented.
    return ActivityClaim(
        kind,
        "scheduled" if kind in ("main_poi", "transport") else None,
        "legacy_policy_derived" if kind in ("main_poi", "transport") else "legacy_unresolved",
    )
