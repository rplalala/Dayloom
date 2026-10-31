"""Controlled final planning evidence for a complete 47-slot Product journey."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from backend.app.evidence.models import PlaceEvidence
from backend.app.policies.generation_diagnostics import observe_generation
from backend.app.product.preview_projection import generated_detail
from backend.app.schemas.interpreted_requirements import ExperienceGoal, SemanticRequirement
from backend.app.schemas.itinerary import (
    Activity,
    Itinerary,
    ItineraryDay,
    ReferenceRecommendation,
    Transfer,
)
from backend.app.schemas.poi_semantics import POISemanticAssessment, RequirementMatch
from backend.app.schemas.request import PlanningRequest
from backend.app.services.product_presentation import present_product
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.services.test_product_presentation import example
from backend.tests.versions.v3.test_b_targets import setup, visit


def complete_media_detail():
    quote = "Must include: an art museum, a waterfront walk."
    payload = make_product_payload() | {
        "destination": "Sydney",
        "start_date": "2026-11-01",
        "end_date": "2026-11-09",
        "additional_preferences": quote,
    }
    request = PlanningRequest.model_validate(payload)
    requirements = request.trip_requirements()
    _, context, _, _ = setup([[visit("a", "a")]], reviews=())
    semantic = tuple(
        SemanticRequirement(
            requirement_id=rid,
            normalized_text=label,
            kind="goal",
            polarity="favor",
            strength="hard",
            scope="whole_trip",
            subject_refs=("party",),
            source_refs=({"quote": quote, "start": 0, "end": len(quote), "occurrence": 0},),
            experience_goal=ExperienceGoal(
                frequency="one_off",
                count=None,
                target="category",
                distinct_dates=False,
                explicit_primary_exception=False,
                trip_scope="ordinary",
            ),
        )
        for rid, label in [("art", "An art museum"), ("water", "A waterfront walk")]
    )
    contract = context.contract.model_copy(
        update={
            "requirements": requirements,
            "semantic_requirements": semantic,
            "named_places": (),
            "visit_requirements": (),
            "daily_visit_constraints": (),
        }
    )
    days, places, judgments, transfers, routes = [], [], [], [], []
    mains = []
    retrieved = datetime.fromisoformat("2026-10-31T00:00:00+00:00")
    for di in range(9):
        day = date(2026, 11, 1) + timedelta(days=di)
        activities = []
        for ai, hour in enumerate((9, 11, 14)):
            index = di * 3 + ai
            pid = f"place-{index}"
            name = f"Art museum {index + 1}" if index < 2 else f"Landmark {index + 1}"
            place = PlaceEvidence(
                place_id=pid,
                name=name,
                formatted_address="Sydney, Australia",
                latitude=-33.86,
                longitude=151.2,
                availability="available",
                retrieved_at=retrieved,
                source_ref=f"google_places:{pid}",
            )
            places.append(place)
            judgments.append(
                POISemanticAssessment(
                    place_id=pid,
                    visit_object=name,
                    role="attraction",
                    categories=["museum" if index < 2 else "landmark"],
                    reason="Controlled visit object",
                    evidence_refs=[place.source_ref],
                    exception_requirement_ids=[],
                    matches=[
                        RequirementMatch(
                            requirement_id="art",
                            relation="supported" if index < 2 else "mismatch",
                            evidence_refs=[place.source_ref],
                        ),
                        RequirementMatch(
                            requirement_id="water",
                            relation="unresolved" if index == 2 else "mismatch",
                            evidence_refs=[place.source_ref],
                        ),
                    ],
                )
            )
            activity = Activity(
                activity_id=f"visit-{index}",
                activity_kind="main_poi",
                time_use="scheduled",
                title=name,
                place_name=name,
                source_place_id=pid,
                location=place.formatted_address,
                start_time=f"{day}T{hour:02}:00:00+11:00",
                end_time=f"{day}T{hour + 1:02}:00:00+11:00",
                notes="Check opening hours before travel.",
            )
            activities.append(activity)
            mains.append((day, activity))
        left, right = activities[:2]
        transfers.append(
            Transfer(
                from_activity_id=left.activity_id,
                to_activity_id=right.activity_id,
                origin_place_id=left.source_place_id,
                destination_place_id=right.source_place_id,
                mode="WALK",
                mode_source="USER_EXPLICIT",
                departure_time=left.end_time,
                provider_duration_seconds=600,
                distance_meters=700,
                reserve_seconds=300,
                calculation_basis="provider",
                validation_state="PASS",
                evidence_refs=("google_routes:fixture",),
            )
        )
        routes.append(
            dict(
                from_activity_id=left.activity_id,
                to_activity_id=right.activity_id,
                origin=left.source_place_id,
                destination=right.source_place_id,
                departure=left.end_time.isoformat(),
                next_start=right.start_time.isoformat(),
            )
        )
        if di in (1, 5):
            meal = di == 1
            activities.append(
                Activity(
                    activity_id="support-meal" if meal else "support-walk",
                    activity_kind="generic_activity",
                    time_use="scheduled",
                    atmosphere_theme="meal" if meal else "walk",
                    title="Explore local food options" if meal else "Waterfront walk",
                    location="Sydney",
                    start_time=f"{day}T{'12:30' if meal else '15:30'}:00+11:00",
                    end_time=f"{day}T{'13:15' if meal else '16:15'}:00+11:00",
                    notes="Enjoy a relaxed local break.",
                )
            )
        days.append(
            ItineraryDay(date=day, activities=sorted(activities, key=lambda a: a.start_time))
        )
    references, ledger = [], {}
    for ni in range(18):
        day, anchor = mains[(ni // 2) * 3 + ni % 2]
        pid = f"nearby-{ni}"
        name = f"Optional discovery {ni + 1}"
        references.append(
            ReferenceRecommendation(
                place_name=name,
                source_place_id=pid,
                reason="An optional unscheduled discovery",
                associated_day=day,
            )
        )
        anchor_data = dict(
            place_id=anchor.source_place_id,
            activity_id=anchor.activity_id,
            day=day,
            name=anchor.place_name,
            location={"latitude": -33.86, "longitude": 151.2},
        )
        ledger[pid] = dict(
            place={
                "place_id": pid,
                "display_name": name,
                "provider_rank": 0,
                "location": {"latitude": -33.8601, "longitude": 151.2},
            },
            anchor=anchor_data,
            representative=anchor_data,
            distance_metres=100,
            call_id=f"fixture-{ni}",
            source_ref=f"google_places_nearby:fixture-{ni}:0",
            retrieved_at=retrieved.isoformat(),
        )
    itinerary = Itinerary(
        output_version="itinerary_3",
        destination="Sydney",
        start_date=requirements.start_date,
        end_date=requirements.end_date,
        days=days,
        transfers=transfers,
        route_diagnostics=routes,
        reference_recommendations=references,
    )
    result, evidence = example()
    result.itinerary, result.requirements = itinerary, requirements
    result.interpreted_requirements, result.nearby_ledger = contract, ledger
    result.semantic_assessment = {"assessments": [row.model_dump(mode="json") for row in judgments]}
    ids = tuple(place.place_id for place in places)
    result.generation_diagnostics = observe_generation(
        itinerary,
        requirements,
        reference_date=date(2026, 10, 31),
        supplied_ids=ids,
        places=places,
        semantic_assessments=judgments,
        contract=contract,
    )
    result.v3 = SimpleNamespace(
        final_places=places,
        final_identity_ids=ids,
        repair=None,
        soft_pace={
            "completion": {
                "status": "unavailable",
                "days": [
                    {"date": day.date, "count": 3, "target_count": 3, "state": "satisfied"}
                    for day in days
                ],
            }
        },
    )
    detail = generated_detail(present_product(result, evidence), request)
    return detail, request
