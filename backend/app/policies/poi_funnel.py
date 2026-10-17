"""Deterministic V1-A search-intent and observation-merge policies."""

import json
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from backend.app.evidence.selection_models import (
    PlaceOpeningDate,
    PlaceSearchIntent,
    PlaceSelectionInput,
)
from backend.app.schemas.named_place_intent import NamedPlaceInclusion, NamedPlaceIntent

GENERIC_SEARCH_TERMS = (
    "top attractions",
    "local food",
    "museums and cultural attractions",
)
_CATEGORY_TERMS = frozenset(
    {
        "attraction",
        "attractions",
        "beach",
        "beaches",
        "food",
        "local food",
        "museum",
        "museums",
        "park",
        "parks",
        "wildlife",
        "coastal views",
        "harbour views",
    }
)
_OTHER_GENERIC_CATEGORIES = frozenset(
    {"viewpoint", "viewpoints", "cultural attraction", "cultural attractions"}
)


def normalize_exact_name(value: str) -> str:
    """Conservative Unicode/case/spacing normalization, not alias inference."""

    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def is_generic_category_surface(value: str) -> bool:
    """Guard only controlled complete category surfaces, not words inside names."""

    return normalize_exact_name(value) in _CATEGORY_TERMS | _OTHER_GENERIC_CATEGORIES


def opening_dates_compatible(a: PlaceOpeningDate, b: PlaceOpeningDate) -> bool:
    return all(
        left is None or right is None or left == right
        for left, right in ((a.year, b.year), (a.month, b.month), (a.day, b.day))
    )


def opening_date_precision(value: PlaceOpeningDate) -> int:
    return sum(part is not None for part in (value.year, value.month, value.day))


@dataclass(frozen=True)
class MergedSearchObservations:
    """All unique Place IDs, with every original query hit retained."""

    places: tuple[PlaceSelectionInput, ...]
    raw_observation_count: int


def merge_search_observations(
    observations: Sequence[PlaceSelectionInput],
) -> MergedSearchObservations:
    """Merge identity by Place ID without losing any raw hit or opening-date fact."""

    groups: dict[str, list[PlaceSelectionInput]] = {}
    for observation in observations:
        groups.setdefault(observation.candidate.place_id, []).append(observation)
    merged: list[PlaceSelectionInput] = []
    for place_id in sorted(groups):
        group = groups[place_id]
        canonical = min(
            group,
            key=lambda item: (
                min(hit.provider_rank for hit in item.query_hits),
                min(hit.intent_id for hit in item.query_hits),
                json.dumps(item.candidate.model_dump(mode="json"), sort_keys=True),
            ),
        )
        hits = tuple(
            sorted(
                (hit for item in group for hit in item.query_hits),
                key=lambda hit: (
                    hit.intent_id,
                    hit.provider_rank,
                    hit.actual_result_count,
                    hit.source_query,
                ),
            )
        )
        dates = tuple(
            sorted(
                {
                    observed
                    for item in group
                    for observed in (
                        item.search_opening_date,
                        *item.search_opening_date_observations,
                    )
                    if observed is not None
                },
                key=lambda value: (
                    value.year is None,
                    -opening_date_precision(value),
                    value.year or 0,
                    value.month or 0,
                    value.day or 0,
                ),
            )
        )
        conflict = any(
            not opening_dates_compatible(a, b)
            for index, a in enumerate(dates)
            for b in dates[index + 1 :]
        )
        merged.append(
            canonical.model_copy(
                update={
                    "landmark_nomination": min(
                        (p.landmark_nomination for p in group if p.landmark_nomination),
                        key=lambda row: row.rank,
                        default=None,
                    ),
                    "query_hits": list(hits),
                    "search_opening_date": dates[0] if dates else None,
                    "search_opening_date_observations": dates,
                    "opening_date_conflict": conflict,
                }
            )
        )
    return MergedSearchObservations(tuple(merged), len(observations))


class NamedPlaceResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    NO_EXACT_CANDIDATE_MATCH = "no_exact_candidate_match"
    AMBIGUOUS_EXACT_NAME = "ambiguous_exact_name"
    SEARCH_NOT_ISSUED_BUDGET = "search_not_issued_budget"
    SEARCH_FAILED = "search_failed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    AMBIGUOUS_CANDIDATES = "ambiguous_candidates"
    EMPTY_SEARCH = "empty_search"


@dataclass(frozen=True)
class NamedPlaceResolution:
    """One typed user intent reconciled against all merged provider identities."""

    named_place_intent: NamedPlaceIntent
    search_intent_id: str | None
    status: NamedPlaceResolutionStatus
    matching_place_ids: tuple[str, ...]
    resolved_place_id: str | None
    considered_place_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    method: str = "exact_name_legacy"


def resolve_named_place_intents(
    named_place_intents: Sequence[NamedPlaceIntent],
    search_intents: Sequence[PlaceSearchIntent],
    places: Sequence[PlaceSelectionInput],
    *,
    failed_search_intent_ids: frozenset[str] = frozenset(),
    budget_not_attempted_intent_ids: frozenset[str] = frozenset(),
) -> tuple[NamedPlaceResolution, ...]:
    """Reconcile each typed surface by exact normalized provider display name."""

    by_name: dict[str, set[str]] = {}
    for place in places:
        by_name.setdefault(normalize_exact_name(place.candidate.name), set()).add(
            place.candidate.place_id
        )
    search_by_name = {
        normalize_exact_name(intent.named_place_intent.place_text): intent.intent_id
        for intent in search_intents
        if intent.named_place_intent is not None
    }
    resolutions: list[NamedPlaceResolution] = []
    for named in named_place_intents:
        key = normalize_exact_name(named.place_text)
        matching_ids = tuple(sorted(by_name.get(key, ())))
        search_intent_id = search_by_name.get(key)
        if named.inclusion is NamedPlaceInclusion.REQUIRED and (
            search_intent_id is None or search_intent_id in budget_not_attempted_intent_ids
        ):
            status = NamedPlaceResolutionStatus.SEARCH_NOT_ISSUED_BUDGET
        elif len(matching_ids) == 1:
            status = NamedPlaceResolutionStatus.RESOLVED
        elif len(matching_ids) > 1:
            status = NamedPlaceResolutionStatus.AMBIGUOUS_EXACT_NAME
        elif search_intent_id is None or search_intent_id in budget_not_attempted_intent_ids:
            status = NamedPlaceResolutionStatus.SEARCH_NOT_ISSUED_BUDGET
        elif search_intent_id in failed_search_intent_ids:
            status = NamedPlaceResolutionStatus.SEARCH_FAILED
        else:
            status = NamedPlaceResolutionStatus.NO_EXACT_CANDIDATE_MATCH
        resolutions.append(
            NamedPlaceResolution(
                named_place_intent=named,
                search_intent_id=search_intent_id,
                status=status,
                matching_place_ids=matching_ids,
                resolved_place_id=matching_ids[0]
                if status is NamedPlaceResolutionStatus.RESOLVED
                else None,
            )
        )
    return tuple(resolutions)
