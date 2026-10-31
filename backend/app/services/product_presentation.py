"""Project only final, identity-matched evidence into the Product contract."""

from pydantic import ValidationError

from backend.app.schemas.generation_diagnostics import public_minimum_coverage
from backend.app.schemas.product import (
    ProductActivity,
    ProductDay,
    ProductItinerary,
    ProductNearby,
    ProductPlanResult,
    ProductTransfer,
    ProductWeather,
)
from backend.app.services.reference_discovery import NearbyReferenceEvidence


def present_product(result, evidence, introductions=None):
    introductions = introductions or {}
    final = result.itinerary
    outcome = getattr(result, "v3", None)
    assessments = ()
    if outcome is not None and hasattr(outcome, "final_identity_ids"):
        from backend.app.policies.itinerary_output import validate_principal_places
        from backend.app.schemas.poi_semantics import POISemanticAssessment

        selected = getattr(getattr(outcome, "repair", None), "selected_semantic_assessments", None)
        assessments = selected if selected is not None else tuple(
            POISemanticAssessment.model_validate(row)
            for row in (getattr(result, "semantic_assessment", None) or {}).get("assessments", ())
        )
        validate_principal_places(
            final, outcome.final_places, outcome.final_identity_ids, assessments
        )
    days = []
    activities = {a.activity_id: (d.date, a) for d in final.days for a in d.activities}
    nearby = {}
    nearby_identities = {}
    ledger = getattr(result, "nearby_ledger", {})
    for reference in final.reference_recommendations:
        raw = ledger.get(reference.source_place_id)
        if raw is None:
            continue
        try:
            entry = NearbyReferenceEvidence.model_validate(raw)
        except ValidationError:
            continue
        parent = activities.get(entry.anchor.activity_id)
        if (
            parent is None
            or parent[0] != entry.anchor.day
            or parent[1].source_place_id != entry.anchor.place_id
            or entry.place.place_id != reference.source_place_id
            or reference.associated_day != parent[0]
        ):
            continue
        nearby.setdefault(entry.anchor.activity_id, []).append(
            ProductNearby(
                place_name=reference.place_name,
                reason=reference.reason,
                associated_day=parent[0],
                anchor_activity_id=entry.anchor.activity_id,
                area=reference.area,
                uncertainty=reference.uncertainty,
                attribution="Google Places"
                if entry.source_ref.startswith("google_places_nearby:")
                else None,
            )
        )
        nearby_identities.setdefault(entry.anchor.activity_id, []).append(
            entry.place.place_id if entry.source_ref.startswith("google_places_nearby:") else None
        )
    weather = evidence.weather
    if weather and weather.destination != result.requirements.destination:
        weather = None
    for day in final.days:
        forecast = next((w for w in weather.days if w.date == day.date), None) if weather else None
        if weather and (weather.availability == "unavailable" or day.date in weather.missing_dates):
            forecast = None
        if forecast and not any(
            v is not None for k, v in forecast.model_dump().items() if k != "date"
        ):
            forecast = None
        public_weather = ProductWeather(
            status="available" if forecast else "unavailable",
            forecast=forecast,
            attribution=weather.attribution if forecast else None,
            source_url="https://open-meteo.com/"
            if forecast and weather.source_ref.startswith("open_meteo:")
            else None,
        )
        days.append(
            ProductDay(
                date=day.date,
                weather=public_weather,
                activities=[
                    ProductActivity(
                        activity_id=a.activity_id,
                        activity_kind=a.activity_kind,
                        atmosphere_theme=(
                            (a.atmosphere_theme or "general")
                            if a.activity_kind == "generic_activity" else None
                        ),
                        time_use=a.time_use,
                        title=a.title,
                        place_name=a.place_name,
                        location=a.location,
                        start_time=a.start_time,
                        end_time=a.end_time,
                        estimated_cost=a.estimated_cost,
                        notes=a.notes,
                        introduction=introductions.get(a.activity_id),
                        nearby=nearby.get(a.activity_id, []),
                    )
                    for a in day.activities
                ],
            )
        )
    pairs = {}
    for day in final.days:
        ordered = sorted(day.activities, key=lambda a: (a.start_time, a.end_time, a.activity_id))
        pairs.update(
            {
                (a.activity_id, b.activity_id): (a, b)
                for a, b in zip(ordered, ordered[1:], strict=False)
            }
        )
    if getattr(result, "v3", None) is not None:
        # V3 final adjacency excludes elastic windows. Use its final application-owned ledger,
        # checking identities and times, rather than reconstructing that policy in Product.
        pairs = {}
        for row in final.route_diagnostics:
            left = activities.get(row.get("from_activity_id"))
            right = activities.get(row.get("to_activity_id"))
            if (
                left
                and right
                and left[0] == right[0]
                and row.get("origin") == left[1].source_place_id
                and row.get("destination") == right[1].source_place_id
                and row.get("departure") == left[1].end_time.isoformat()
                and row.get("next_start") == right[1].start_time.isoformat()
            ):
                pairs[(left[1].activity_id, right[1].activity_id)] = (left[1], right[1])
    transfers = []
    for transfer in final.transfers:
        pair = pairs.get((transfer.from_activity_id, transfer.to_activity_id))
        if pair is None:
            continue
        left, right = pair
        if (
            left.source_place_id != transfer.origin_place_id
            or right.source_place_id != transfer.destination_place_id
            or transfer.departure_time < left.end_time
            # A final binding at the preceding activity's end can legitimately conflict
            # with the following start. Preserve that warning, not arbitrary late departures.
            or (
                transfer.departure_time > right.start_time
                and transfer.departure_time != left.end_time
            )
        ):
            continue
        verified = transfer.provider_duration_seconds is not None
        derived = (
            "mirrored" in transfer.calculation_basis or "derived" in transfer.calculation_basis
        )
        transfers.append(
            ProductTransfer(
                from_activity_id=left.activity_id,
                to_activity_id=right.activity_id,
                preceding_end_time=left.end_time,
                following_start_time=right.start_time,
                mode=transfer.mode if verified else None,
                provider_duration_seconds=transfer.provider_duration_seconds if verified else None,
                distance_meters=transfer.distance_meters if verified else None,
                reserve_seconds=transfer.reserve_seconds,
                validation_state=transfer.validation_state,
                unknowns=list(transfer.unknowns),
                estimate_kind="derived"
                if verified and derived
                else "provider"
                if verified
                else "unverified",
                attribution=("Derived from Google Routes estimates" if derived else "Google Routes")
                if verified and any(r.startswith("google_routes:") for r in transfer.evidence_refs)
                else None,
            )
        )
    completion = getattr(getattr(result, "v3", None), "soft_pace", {}).get("completion")
    from backend.app.services.product_guidance import attention_items

    projected = ProductPlanResult(
        attention_items=attention_items(result),
        required_experiences=tuple(
            dict(
                requirement=row["requirement"], source_quotes=row["source_quotes"],
                target=row["expected"], scheduled=row["matched"], frequency=row["frequency"],
                status=row["status"], reason=row["reason"],
                planned_visits=tuple(
                    dict(activity_id=a.activity_id, date=day.date, place_name=a.place_name)
                    for day in final.days for a in day.activities
                    if a.activity_kind == "main_poi" and a.place_name
                    and any(
                        assessment.place_id == a.source_place_id and assessment.main_eligible
                        and any(m.requirement_id == row["requirement_id"]
                                and m.relation == "supported" for m in assessment.matches)
                        for assessment in assessments
                    )
                ),
            )
            for row in result.generation_diagnostics.goal_progress if row.get("required")
        ) if result.generation_diagnostics else (),
        pace_review={
            "status": completion["status"],
            "days": [
                {key: day[key] for key in ("date", "count", "target_count", "state")}
                for day in completion["days"]
            ],
        }
        if completion
        else None,
        preference_coverage=tuple(
            dict(
                preference=row["preference"],
                target=row["expected"],
                scheduled=row["matched"],
                remaining=row["remaining"],
                status=row["coverage_status"],
                target_origin=row["target_origin"],
            )
            for row in result.generation_diagnostics.goal_progress
            if row.get("soft")
        )
        if result.generation_diagnostics
        else (),
        policy_completion=result.generation_diagnostics.policy_completion
        if result.generation_diagnostics
        else "unassessed",
        policy_reasons=tuple(
            dict.fromkeys(row["reason"] for row in result.generation_diagnostics.policy_issues)
        )
        if result.generation_diagnostics
        else (),
        requirements=result.requirements,
        itinerary=ProductItinerary(
            destination=final.destination,
            start_date=final.start_date,
            end_date=final.end_date,
            days=days,
            transfers=transfers,
        ),
        minimum_daily_coverage=public_minimum_coverage(result.generation_diagnostics),
    )
    # Only the adopted V3 context is authority; early evidence and names are not.
    final_places = getattr(getattr(result, "v3", None), "final_places", ())
    verified = {
        p.place_id
        for p in final_places
        if p.source_ref == f"google_places:{p.place_id}" and p.availability != "unavailable"
    }
    bindings = {}
    nearby_position = 0
    for day in final.days:
        for activity in day.activities:
            if (
                activity.time_use != "free_window"
                and activity.activity_kind != "transport"
                and activity.source_place_id in verified
            ):
                bindings[f"activity:{activity.activity_id}"] = activity.source_place_id
            for place_id in nearby_identities.get(activity.activity_id, []):
                if place_id and activity.time_use != "free_window":
                    bindings[f"nearby:{nearby_position}"] = place_id
                nearby_position += 1
    projected._media_bindings = bindings
    return projected


def public_clarification(issues):
    """Keep input rewrite feedback, not research conflicts, provenance or contract versions."""
    from backend.app.policies.requirement_feedback import MESSAGES, feedback_rows

    code = issues.get("code")
    rows = []
    for row in issues.get("issues") or feedback_rows(code):
        public = {
            k: row[k]
            for k in (
                "issue_type",
                "quote_status",
                "related_field",
                "current_value",
                "reason",
                "action",
            )
            if k in row
        }
        public["source_refs"] = [
            {k: ref[k] for k in ("quote", "start", "end") if k in ref}
            for ref in row.get("source_refs", ())
        ]
        rows.append(public)
    return {
        **({"code": code, "requirement_ids": [
            ref for ref in issues.get("requirement_ids", ())
            if isinstance(ref, str) and len(ref) <= 40
            and ref.startswith(("semantic_", "named_")) and ref.rsplit("_", 1)[-1].isdigit()
        ]} if code in MESSAGES else {}),
        "input_disposition": issues.get("input_disposition", "CLARIFICATION_REQUIRED"),
        "issues": rows,
    }
