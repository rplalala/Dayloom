"""Deterministic bounded transport selection for V1 and later versions."""

import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, model_serializer

from backend.app.evidence.models import (
    NonWalkablePairEvidence,
    NonWalkableTrigger,
    RouteEvidence,
)
from backend.app.schemas.request import PlanningRequest, TravelRequirements
from backend.app.schemas.trip_intent import TransportPreferenceIntent, TravelMode

MAX_WALK_DISTANCE_METERS = 3_000
MAX_WALK_DURATION_SECONDS = 2_700


class TransportModeDecision(BaseModel):
    """One reproducible mode decision and any valid Routes preference."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    travel_mode: TravelMode
    allowed_modes: tuple[TravelMode, ...] | None = None
    reason: str
    routing_preference: str | None = None

    @model_serializer(mode="wrap")
    def serialize_optional_modes(self, handler):
        result = handler(self)
        if self.allowed_modes is None:
            result.pop("allowed_modes", None)
        return result

    @property
    def is_explicit(self) -> bool:
        """Return whether the user or extracted requirements named this mode."""

        return self.reason.startswith("explicit_mode_")


_EXPLICIT_PREFERENCE_VALUES = {
    "drive": TravelMode.DRIVE,
    "driving": TravelMode.DRIVE,
    "car": TravelMode.DRIVE,
    "rental car": TravelMode.DRIVE,
    "walk": TravelMode.WALK,
    "walking": TravelMode.WALK,
    "on foot": TravelMode.WALK,
    "bike": TravelMode.BICYCLE,
    "bicycle": TravelMode.BICYCLE,
    "cycling": TravelMode.BICYCLE,
    "public transport": TravelMode.TRANSIT,
    "public transit": TravelMode.TRANSIT,
    "transit": TravelMode.TRANSIT,
}

_REQUEST_PATTERNS = {
    TravelMode.DRIVE: (
        r"\bby car\b",
        r"\brent(?:al|ing)? (?:a )?car\b",
        r"\b(?:we (?:will|plan to)|prefer to) drive\b",
    ),
    TravelMode.WALK: (
        r"\bon foot\b",
        r"\bwalking[- ]only\b",
        r"\bwalk everywhere\b",
        r"\bget(?:ting)? around by walking\b",
    ),
    TravelMode.BICYCLE: (
        r"\bby (?:bike|bicycle)\b",
        r"\bcycling[- ]only\b",
        r"\brent(?:ing)? (?:a )?(?:bike|bicycle)\b",
    ),
    TravelMode.TRANSIT: (
        r"\b(?:use|using|prefer|travel by|get(?:ting)? around by) public "
        r"(?:transport|transit)\b",
        r"\bby (?:bus|train|transit)\b",
        r"\buse (?:buses|trains|transit)\b",
    ),
}


def select_transport_mode(
    request: PlanningRequest,
    requirements: TravelRequirements,
) -> TransportModeDecision:
    """Historical test-only adapter for existing transport regression fixtures.

    The production V1 path uses select_transport_mode_from_intent instead.
    This helper does not interpret requirements for any active planning version.
    """

    normalized_request = request.additional_preferences.casefold()
    matches: list[tuple[int, TravelMode]] = []
    for mode, patterns in _REQUEST_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, normalized_request)
            if match is not None:
                matches.append((match.start(), mode))
    if matches:
        _, mode = min(matches, key=lambda item: (item[0], item[1].value))
        return TransportModeDecision(
            travel_mode=mode,
            reason="explicit_mode_in_user_request",
            routing_preference="TRAFFIC_UNAWARE" if mode is TravelMode.DRIVE else None,
        )

    for preference in requirements.preferences:
        mode = _EXPLICIT_PREFERENCE_VALUES.get(preference.casefold().strip())
        if mode is not None:
            return TransportModeDecision(
                travel_mode=mode,
                reason="explicit_mode_in_extracted_preferences",
                routing_preference=("TRAFFIC_UNAWARE" if mode is TravelMode.DRIVE else None),
            )

    return TransportModeDecision(
        travel_mode=TravelMode.WALK,
        reason="default_pedestrian_transfer_for_poi_grouping",
    )


def select_transport_mode_from_intent(
    intent: TransportPreferenceIntent | None,
    constraint=None,
) -> TransportModeDecision:
    """Apply the existing routing default to one validated typed user intent."""

    if constraint is not None:
        allowed = tuple(
            m
            for m in (TravelMode.WALK, TravelMode.TRANSIT, TravelMode.DRIVE)
            if m in constraint.allowed_modes
        )
        if not allowed:
            from backend.app.schemas.interpreted_requirements import ClarificationRequired

            raise ClarificationRequired("unsupported_transport_modes", constraint.requirement_refs)
        chosen = intent.mode if intent and intent.mode in allowed else allowed[0]
        return TransportModeDecision(
            travel_mode=chosen,
            allowed_modes=allowed,
            reason="hard_allowed_modes",
            routing_preference="TRAFFIC_UNAWARE" if chosen == "DRIVE" else None,
        )
    if intent is None:
        return TransportModeDecision(
            travel_mode=TravelMode.WALK,
            reason="default_pedestrian_transfer_for_poi_grouping",
        )
    return TransportModeDecision(
        travel_mode=intent.mode,
        reason="explicit_mode_in_user_request",
        routing_preference="TRAFFIC_UNAWARE" if intent.mode is TravelMode.DRIVE else None,
    )


def _non_walkable_trigger(
    *,
    condition: str | None,
    distance_meters: int | None,
    duration_seconds: int | None,
) -> NonWalkableTrigger | None:
    if condition == "ROUTE_NOT_FOUND":
        return NonWalkableTrigger.WALK_ROUTE_NOT_FOUND
    if distance_meters is not None and distance_meters > MAX_WALK_DISTANCE_METERS:
        return NonWalkableTrigger.DISTANCE_THRESHOLD
    if duration_seconds is not None and duration_seconds > MAX_WALK_DURATION_SECONDS:
        return NonWalkableTrigger.DURATION_THRESHOLD
    return None


@dataclass(frozen=True)
class DirectedWalkTrigger:
    """Internal directional trigger retained for ranking and trace provenance."""

    origin_place_id: str
    destination_place_id: str
    trigger: NonWalkableTrigger
    walk_distance_meters: int | None
    walk_duration_seconds: int | None


def _directed_severity(pair: DirectedWalkTrigger) -> tuple[int, float]:
    distance_ratio = (pair.walk_distance_meters or 0) / MAX_WALK_DISTANCE_METERS
    duration_ratio = (pair.walk_duration_seconds or 0) / MAX_WALK_DURATION_SECONDS
    route_not_found = int(pair.trigger is NonWalkableTrigger.WALK_ROUTE_NOT_FOUND)
    return route_not_found, max(distance_ratio, duration_ratio)


def _directed_sort_key(pair: DirectedWalkTrigger) -> tuple[int, float, str, str]:
    severity = _directed_severity(pair)
    return (
        -severity[0],
        -severity[1],
        pair.origin_place_id,
        pair.destination_place_id,
    )


def find_directed_non_walkable_pairs(
    evidence: RouteEvidence,
) -> list[DirectedWalkTrigger]:
    """Find and severity-sort directed WALK triggers without LLM involvement."""

    pairs: dict[tuple[str, str], DirectedWalkTrigger] = {}
    severity: dict[tuple[str, str], tuple[int, float]] = {}
    for element in evidence.elements:
        if element.origin_place_id == element.destination_place_id:
            continue
        trigger = _non_walkable_trigger(
            condition=element.condition,
            distance_meters=element.distance_meters,
            duration_seconds=element.duration_seconds,
        )
        if trigger is None:
            continue
        pair_key = (element.origin_place_id, element.destination_place_id)
        pair = DirectedWalkTrigger(
            origin_place_id=element.origin_place_id,
            destination_place_id=element.destination_place_id,
            trigger=trigger,
            walk_distance_meters=element.distance_meters,
            walk_duration_seconds=element.duration_seconds,
        )
        candidate_severity = _directed_severity(pair)
        if pair_key in severity and severity[pair_key] >= candidate_severity:
            continue
        severity[pair_key] = candidate_severity
        pairs[pair_key] = pair
    return sorted(pairs.values(), key=_directed_sort_key)


def collapse_non_walkable_pairs(
    directed_pairs: list[DirectedWalkTrigger],
) -> list[NonWalkablePairEvidence]:
    """Collapse directions and rank each logical pair by its most severe direction."""

    reasons: dict[tuple[str, str], set[NonWalkableTrigger]] = {}
    severity: dict[tuple[str, str], tuple[int, float]] = {}
    for pair in directed_pairs:
        logical_key = tuple(sorted((pair.origin_place_id, pair.destination_place_id)))
        reasons.setdefault(logical_key, set()).add(pair.trigger)
        severity[logical_key] = max(
            severity.get(logical_key, (0, 0.0)),
            _directed_severity(pair),
        )
    logical_pairs = [
        NonWalkablePairEvidence(
            place_id_a=place_id_a,
            place_id_b=place_id_b,
            trigger_reasons=sorted(reasons[(place_id_a, place_id_b)], key=lambda item: item.value),
        )
        for place_id_a, place_id_b in reasons
    ]
    return sorted(
        logical_pairs,
        key=lambda pair: (
            -severity[(pair.place_id_a, pair.place_id_b)][0],
            -severity[(pair.place_id_a, pair.place_id_b)][1],
            pair.place_id_a,
            pair.place_id_b,
        ),
    )


def find_non_walkable_pairs(evidence: RouteEvidence) -> list[NonWalkablePairEvidence]:
    """Return canonical logical pairs ranked by the worst directed WALK result."""

    return collapse_non_walkable_pairs(find_directed_non_walkable_pairs(evidence))


def select_alternative_route_pairs(
    pairs: list[NonWalkablePairEvidence],
    *,
    max_pairs: int,
    max_calls: int,
) -> tuple[list[NonWalkablePairEvidence], list[NonWalkablePairEvidence]]:
    """Select from severity-ranked logical pairs within pair and call limits."""

    selected: list[NonWalkablePairEvidence] = []
    selected_keys: set[tuple[str, str]] = set()
    selected_origins: set[str] = set()
    for pair in pairs:
        if len(selected) == max_pairs:
            break
        is_new_origin = pair.place_id_a not in selected_origins
        if is_new_origin and len(selected_origins) == max_calls:
            continue
        selected.append(pair)
        selected_keys.add((pair.place_id_a, pair.place_id_b))
        selected_origins.add(pair.place_id_a)
    truncated = [pair for pair in pairs if (pair.place_id_a, pair.place_id_b) not in selected_keys]
    return selected, truncated
