"""Mechanical output identity boundaries, without semantic judgments or repair."""

from dataclasses import replace

from pydantic import BaseModel, ConfigDict

from backend.app.policies.visit_multiplicity import is_primary_visit
from backend.app.schemas.itinerary_projection import V1Itinerary


def normalize_activity_order(itinerary):
    """Stable per-day ordering only; preserve fields and diagnostic attribution."""
    paths = {}
    days = []
    for day_index, day in enumerate(itinerary.days):
        ordered = sorted(enumerate(day.activities), key=lambda item: item[1].start_time)
        for new_index, (old_index, _) in enumerate(ordered):
            prefix = f"days[{day_index}].activities"
            paths[f"{prefix}[{old_index}].estimated_cost"] = f"{prefix}[{new_index}].estimated_cost"
        days.append(day.model_copy(update={"activities": [a for _, a in ordered]}))
    result = itinerary.model_copy(update={"days": days})
    if isinstance(result, V1Itinerary):
        result.set_cost_projections(
            tuple(
                replace(item, field_path=paths.get(item.field_path, item.field_path))
                for item in itinerary.cost_projections
            )
        )
    if result.output_version == "itinerary_3":
        type(result).model_validate(result.model_dump())
    return result


class OutputRoleSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheduled_place_ids: tuple[str, ...]
    reference_place_ids: tuple[str, ...]
    unused_candidate_ids: tuple[str, ...]
    unscheduled_required_ids: tuple[str, ...]
    unlinked_activity_ids: tuple[str, ...]
    supply_not_scheduled_ids: tuple[str, ...] = ()
    references_outside_supply_ids: tuple[str, ...] = ()


def output_role_summary(itinerary, supply):
    activities = [a for day in itinerary.days for a in day.activities]
    scheduled = {
        a.source_place_id for a in activities if a.source_place_id and a.time_use != "free_window"
    }
    required_visits = (
        {a.source_place_id for a in activities if a.source_place_id and is_primary_visit(a)}
        if itinerary.output_version == "itinerary_3"
        else scheduled
    )
    references = {
        r.source_place_id for r in itinerary.reference_recommendations if r.source_place_id
    }
    return OutputRoleSummary(
        scheduled_place_ids=tuple(sorted(scheduled)),
        reference_place_ids=tuple(sorted(references)),
        unused_candidate_ids=tuple(sorted(set(supply.selected_place_ids) - scheduled - references)),
        unscheduled_required_ids=tuple(
            sorted(set(supply.required_canonical_ids) - required_visits)
        ),
        unlinked_activity_ids=tuple(a.activity_id for a in activities if not a.source_place_id),
        supply_not_scheduled_ids=tuple(sorted(set(supply.selected_place_ids) - scheduled)),
        references_outside_supply_ids=tuple(sorted(references - set(supply.selected_place_ids))),
    )


def validate_principal_places(itinerary, places, supplied_ids, assessments):
    """New tools principals need both acquired identity and existing semantic eligibility."""
    if itinerary.output_version != "itinerary_3":
        return
    allowed = set(supplied_ids)
    acquired = {p.place_id: p for p in places if p.place_id in allowed}
    rows = {row.place_id: row for row in assessments}
    for day in itinerary.days:
        for activity in day.activities:
            if activity.activity_kind != "main_poi":
                continue
            place = acquired.get(activity.source_place_id)
            row = rows.get(activity.source_place_id)
            if (
                place is None
                or getattr(place, "availability", None) == "unavailable"
                or row is None
                or not row.main_eligible
            ):
                raise ValueError("Principal visit requires an eligible acquired place")


def validate_output_sources(itinerary, *, places=None, supplied_ids=(), semantic_assessments=None):
    """Validate V0 output or restore supplied V1-V3 source facts at acceptance.

    Missing scheduled REQUIRED visits are observable in OutputRoleSummary, not repaired.
    Historical domain results keep defaults; real model outputs require itinerary_3.
    """
    validated = type(itinerary).model_validate(itinerary.model_dump())
    activities = [a for d in validated.days for a in d.activities]
    references = validated.reference_recommendations
    if any(r.source_ref is not None for r in references):
        raise ValueError("Model-authored source_ref is not allowed")
    if places is None:
        if len(references) > 3:
            raise ValueError("V0 accepts at most three model-knowledge references")
        if any(a.source_place_id is not None for a in activities) or any(
            r.source_place_id is not None for r in references
        ):
            raise ValueError("V0 cannot author external place identities")
        return normalize_activity_order(itinerary)
    if references:
        raise ValueError("V1 model references are not allowed; use post-itinerary discovery")
    if any(a.activity_kind == "transport" for a in activities):
        raise ValueError(
            "V1-V3 model transport activities are not allowed; use application transfers"
        )
    ledger = {p.place_id: p for p in places if p.place_id in supplied_ids}
    if semantic_assessments is not None:
        validate_principal_places(validated, places, supplied_ids, semantic_assessments)
    from backend.app.policies.schedule_time import ScheduleTimeContext, validate_endpoint

    time_context = ScheduleTimeContext([p for p in places if p.place_id in supplied_ids])
    for activity in activities:
        if activity.source_place_id is not None and activity.source_place_id not in ledger:
            raise ValueError("Activity identity is outside the supplied candidate ledger")
        if (
            validated.output_version in ("itinerary_2", "itinerary_3")
            and activity.place_name is not None
            and activity.source_place_id is None
        ):
            raise ValueError(
                "Named V1 activity requires a supplied identity; generic activities use null"
            )
        zone = time_context.zone_for(activity.source_place_id)
        for endpoint in (activity.start_time, activity.end_time):
            validate_endpoint(endpoint, zone, activity_id=activity.activity_id)
    # Copy keeps V1's private cost projection diagnostics intact; validate public fields.
    days = [
        day.model_copy(
            update={
                "activities": [
                    activity.model_copy(
                        update={
                            "place_name": ledger[activity.source_place_id].name,
                            "location": ledger[activity.source_place_id].formatted_address,
                        }
                    )
                    if activity.source_place_id
                    else activity
                    for activity in day.activities
                ]
            }
        )
        for day in itinerary.days
    ]
    result = itinerary.model_copy(update={"days": days})
    type(result).model_validate(result.model_dump())
    return normalize_activity_order(result)
