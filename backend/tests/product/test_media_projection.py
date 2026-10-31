"""Product media authority follows final adoption rather than display names."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from backend.app.evidence.models import PlaceEvidence
from backend.app.product.preview_projection import generated_detail
from backend.app.schemas.request import PlanningRequest
from backend.app.services.product_presentation import present_product
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.services.test_product_presentation import example


def test_adopted_final_google_identity_survives_private_preview_projection():
    result, evidence = example()
    activity = result.itinerary.days[0].activities[0]
    result.v3 = SimpleNamespace(
        final_places=(
            PlaceEvidence(
                place_id=activity.source_place_id,
                name="Provider name",
                latitude=1,
                longitude=2,
                availability="available",
                retrieved_at=datetime.now(),
                source_ref="google_places:left-place",
            ),
        )
    )
    public = present_product(result, evidence)
    detail = generated_detail(public, PlanningRequest.model_validate(make_product_payload()))
    assert detail._media_bindings == {f"activity:{activity.activity_id}": "left-place"}
    assert "left-place" not in detail.model_dump_json()
    activity.source_place_id = "unadopted"
    assert not present_product(result, evidence)._media_bindings


@pytest.mark.parametrize(
    "condition", ["early-only", "unavailable", "other-provider", "free-window", "transport"]
)
def test_lookalikes_and_nonadopted_evidence_do_not_grant_photo_identity(condition):
    result, evidence = example()
    activity = result.itinerary.days[0].activities[0]
    place = PlaceEvidence(
        place_id=activity.source_place_id,
        name=activity.place_name or activity.title,
        latitude=1,
        longitude=2,
        availability="available",
        retrieved_at=datetime.now(),
        source_ref=f"google_places:{activity.source_place_id}",
    )
    if condition == "unavailable":
        place = place.model_copy(update={"availability": "unavailable"})
    if condition == "other-provider":
        place = place.model_copy(update={"source_ref": "imported:google_claim"})
    if condition == "free-window":
        activity.time_use = "free_window"
    if condition == "transport":
        activity.activity_kind = "transport"
    result.places = [place]
    result.v3 = SimpleNamespace(final_places=() if condition == "early-only" else (place,))
    assert not present_product(result, evidence)._media_bindings


def test_nearby_media_uses_strict_final_ledger_slots_and_rejects_stale_anchor():
    from backend.app.schemas.itinerary import ReferenceRecommendation

    result, evidence = example()
    activity = result.itinerary.days[0].activities[0]
    day = result.itinerary.start_date
    anchor = {
        "place_id": activity.source_place_id,
        "activity_id": activity.activity_id,
        "day": day,
        "name": "Parent",
        "location": {"latitude": 1, "longitude": 2},
    }
    result.nearby_ledger["nearby"] = {
        "place": {
            "place_id": "nearby",
            "display_name": "Same display name",
            "provider_rank": 0,
            "location": {"latitude": 1, "longitude": 2},
        },
        "anchor": anchor,
        "representative": anchor,
        "distance_metres": 100,
        "call_id": "controlled",
        "source_ref": "google_places_nearby:controlled:0",
        "retrieved_at": "2026-09-11T00:00:00Z",
    }
    result.itinerary.reference_recommendations = [
        ReferenceRecommendation(
            source_place_id="nearby",
            place_name="Same display name",
            reason="Optional",
            associated_day=day,
        )
    ]
    public = present_product(result, evidence)
    detail = generated_detail(public, PlanningRequest.model_validate(make_product_payload()))
    assert detail._media_bindings == {"nearby:0": "nearby"}
    activity.source_place_id = "changed-adoption"
    assert not present_product(result, evidence)._media_bindings
