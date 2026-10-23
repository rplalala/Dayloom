"""Final-identity binding and allowlisted Product projection without external calls."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.app.evidence.models import WeatherDayEvidence, WeatherEvidence
from backend.app.observability.run_trace import NullRunTracer
from backend.app.schemas.itinerary import ReferenceRecommendation, Transfer
from backend.app.services.product_evidence import ProductEvidenceCollector
from backend.app.services.product_presentation import present_product, public_clarification
from backend.tests.versions.v0.fakes import make_itinerary, make_requirements


def example():
    itinerary = make_itinerary()
    left = itinerary.days[0].activities[0]
    left.source_place_id = "left-place"
    left.activity_kind = "main_poi"
    right = left.model_copy(
        update={
            "activity_id": "right",
            "source_place_id": "right-place",
            "start_time": left.end_time + timedelta(hours=1),
            "end_time": left.end_time + timedelta(hours=2),
        }
    )
    itinerary.days[0].activities.append(right)
    itinerary.transfers = [
        Transfer(
            from_activity_id=left.activity_id,
            to_activity_id=right.activity_id,
            origin_place_id=left.source_place_id,
            destination_place_id=right.source_place_id,
            mode="DRIVE",
            mode_source="USER_EXPLICIT",
            departure_time=left.end_time,
            provider_duration_seconds=1080,
            distance_meters=7200,
            reserve_seconds=600,
            calculation_basis="basic_drive_estimate",
            validation_state="UNKNOWN",
            evidence_refs=("google_routes:compute_route_matrix",),
            unknowns=("Car transport must be arranged; cost and availability not verified.",),
        )
    ]
    result = SimpleNamespace(
        requirements=make_requirements(),
        itinerary=itinerary,
        generation_diagnostics=None,
        nearby_ledger={},
        system_version="v3",
        request_resources={"PRIVATE": True},
    )
    return result, ProductEvidenceCollector(NullRunTracer(None))


def test_public_contract_excludes_debug_and_separates_route_reserve():
    result, evidence = example()
    result.itinerary.route_diagnostics = [{"PRIVATE": True}]
    public = present_product(result, evidence)
    wire = public.model_dump(mode="json")
    assert "PRIVATE" not in str(wire)
    assert "system_version" not in str(wire) and "source_place_id" not in str(wire)
    assert "route_diagnostics" not in str(wire) and "output_version" not in str(wire)
    leg = public.itinerary.transfers[0]
    assert leg.provider_duration_seconds == 1080 and leg.reserve_seconds == 600
    assert leg.distance_meters == 7200 and leg.attribution == "Google Routes"
    assert leg.preceding_end_time == result.itinerary.days[0].activities[0].end_time
    assert public.itinerary.days[0].weather.status == "unavailable"


def test_rich_partial_review_survives_public_preview_and_saved_detail_serialization():
    from backend.app.product.detail import ProductDetail
    from backend.app.product.preview_projection import generated_detail
    from backend.tests.request_fixtures import make_request
    from backend.tests.versions.v3.test_rich_pace_completion import run_rich

    result, _ = run_rich((2, 3))
    public = present_product(result, ProductEvidenceCollector(NullRunTracer(None)))
    assert public.pace_review.status == "partial"
    assert [day.count for day in public.pace_review.days] == [2, 3]
    detail = generated_detail(public, make_request("rich"))
    restored = ProductDetail.model_validate_json(detail.model_dump_json())
    assert restored.completion.pace_review == public.pace_review
    wire = public.model_dump_json()
    assert "rtpeval_daily_density" not in wire and "blocking_findings" not in wire


def test_historical_product_result_does_not_acquire_a_rich_review():
    result, evidence = example()
    assert present_product(result, evidence).pace_review is None


@pytest.mark.parametrize("mutation", ["identity", "departure", "removed", "reordered"])
def test_stale_transfer_is_omitted(mutation):
    result, evidence = example()
    left, right = result.itinerary.days[0].activities
    if mutation == "identity":
        right.source_place_id = "replacement"
    elif mutation == "departure":
        left.end_time += timedelta(minutes=1)
    elif mutation == "removed":
        result.itinerary.days[0].activities.pop()
    else:
        right.start_time = left.start_time - timedelta(hours=2)
        right.end_time = left.start_time - timedelta(hours=1)
    assert not present_product(result, evidence).itinerary.transfers


def test_unknown_route_does_not_invent_mode_distance_or_provider():
    result, evidence = example()
    result.itinerary.transfers[0] = result.itinerary.transfers[0].model_copy(
        update={
            "provider_duration_seconds": None,
            "distance_meters": 999,
            "reserve_seconds": 2700,
            "calculation_basis": "policy_reserve_route_unknown",
        }
    )
    leg = present_product(result, evidence).itinerary.transfers[0]
    assert leg.mode is None and leg.distance_meters is None and leg.attribution is None
    assert leg.estimate_kind == "unverified" and leg.reserve_seconds == 2700


def test_weather_is_date_matched_and_missing_dates_are_explicit():
    result, evidence = example()
    day = result.itinerary.start_date
    evidence.weather = WeatherEvidence(
        destination=result.requirements.destination,
        latitude=1,
        longitude=2,
        availability="partial",
        retrieved_at=datetime.now(),
        source_ref="open_meteo:daily_forecast",
        attribution="Open-Meteo (CC BY 4.0)",
        days=[WeatherDayEvidence(date=day, condition="Clear", max_temperature_c=22)],
    )
    weather = present_product(result, evidence).itinerary.days[0].weather
    assert weather.status == "available" and weather.forecast.max_temperature_c == 22
    assert weather.source_url == "https://open-meteo.com/"
    evidence.weather = evidence.weather.model_copy(update={"missing_dates": [day]})
    assert present_product(result, evidence).itinerary.days[0].weather.status == "unavailable"


def test_nearby_only_attaches_to_matching_final_activity():
    result, evidence = example()
    left = result.itinerary.days[0].activities[0]
    day = result.itinerary.start_date
    anchor = {
        "place_id": left.source_place_id,
        "activity_id": left.activity_id,
        "day": day,
        "name": "Parent",
        "location": {"latitude": 1, "longitude": 2},
    }
    result.nearby_ledger["nearby"] = {
        "place": {
            "place_id": "nearby",
            "display_name": "Nearby park",
            "provider_rank": 0,
            "location": {"latitude": 1, "longitude": 2},
        },
        "anchor": anchor,
        "representative": anchor,
        "distance_metres": 100,
        "call_id": "PRIVATE",
        "source_ref": "google_places_nearby:PRIVATE:0",
        "retrieved_at": "now",
    }
    result.itinerary.reference_recommendations = [
        ReferenceRecommendation(
            source_place_id="nearby",
            place_name="Nearby park",
            reason="A nearby option",
            associated_day=day,
        )
    ]
    public = present_product(result, evidence)
    attached = public.itinerary.days[0].activities[0].nearby
    assert len(attached) == 1 and attached[0].anchor_activity_id == left.activity_id
    assert attached[0].attribution == "Google Places"
    assert "PRIVATE" not in public.model_dump_json()
    left.source_place_id = "replacement"
    assert not present_product(result, evidence).itinerary.days[0].activities[0].nearby


def test_clarification_does_not_serialize_research_conflicts_or_versions():
    public = public_clarification(
        {
            "assessment_version": "private",
            "conflicts": [{"provider": "PRIVATE"}],
            "issues": [
                {
                    "reason": "Please review",
                    "stage": "PRIVATE",
                    "source_refs": [
                        {
                            "quote": "original text",
                            "start": 0,
                            "end": 13,
                            "contract_version": "PRIVATE",
                        }
                    ],
                }
            ],
        }
    )
    assert "PRIVATE" not in str(public) and "assessment_version" not in public
    assert public["issues"][0]["source_refs"][0]["quote"] == "original text"


def test_v3_adjacency_uses_final_application_ledger_and_rechecks_times():
    result, evidence = example()
    left, right = result.itinerary.days[0].activities
    result.v3 = object()
    elastic = left.model_copy(
        update={
            "activity_id": "flexible",
            "source_place_id": None,
            "activity_kind": "free_time",
            "start_time": left.end_time,
            "end_time": right.start_time,
        }
    )
    result.itinerary.days[0].activities.insert(1, elastic)
    result.itinerary.route_diagnostics = [
        {
            "from_activity_id": left.activity_id,
            "to_activity_id": right.activity_id,
            "origin": left.source_place_id,
            "destination": right.source_place_id,
            "departure": left.end_time.isoformat(),
            "next_start": right.start_time.isoformat(),
            "PRIVATE": True,
        }
    ]
    assert len(present_product(result, evidence).itinerary.transfers) == 1
    right.start_time += timedelta(minutes=10)
    assert not present_product(result, evidence).itinerary.transfers


def test_collector_retains_normalized_summary_without_recording_raw_payloads():
    from backend.app.evidence.experience_models import ExperienceProfile

    _, evidence = example()
    profile = ExperienceProfile(
        place_id="left-place", availability="available", summary="Existing."
    )
    evidence.payload("evidence", "v1_experience_profile", profile, minimum_mode=None)
    evidence.payload("llm", "raw_response", {"PRIVATE": "untrusted"}, minimum_mode=None)
    assert evidence.summaries == {"left-place": "Existing."}
    assert not hasattr(evidence, "raw_response")


@pytest.mark.parametrize("status", ["CONFIRMED", "UNKNOWN"])
@pytest.mark.parametrize("departure_offset", [-1, 0, 1])
def test_final_overlapping_connection_preserves_warning_but_not_stale_departure(
    status, departure_offset
):
    result, evidence = example()
    left, right = result.itinerary.days[0].activities
    right.start_time = left.end_time - timedelta(minutes=10)
    result.v3 = object()
    result.itinerary.route_diagnostics = [
        {
            "from_activity_id": left.activity_id,
            "to_activity_id": right.activity_id,
            "origin": left.source_place_id,
            "destination": right.source_place_id,
            "departure": left.end_time.isoformat(),
            "next_start": right.start_time.isoformat(),
        }
    ]
    result.itinerary.transfers = [
        result.itinerary.transfers[0].model_copy(
            update={
                "departure_time": left.end_time + timedelta(minutes=departure_offset),
                "validation_state": status,
            }
        )
    ]
    legs = present_product(result, evidence).itinerary.transfers
    if departure_offset:
        assert legs == []
    else:
        assert len(legs) == 1
        assert legs[0].validation_state == status
        assert legs[0].preceding_end_time > legs[0].following_start_time
        assert legs[0].unknowns == list(result.itinerary.transfers[0].unknowns)
        # An outdated ledger must still be rejected even when the transfer is conflicting.
        right.start_time -= timedelta(minutes=1)
        assert not present_product(result, evidence).itinerary.transfers
