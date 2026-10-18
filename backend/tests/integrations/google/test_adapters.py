"""Offline contract tests for Google V1-A HTTP adapters."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from backend.app.integrations.google.common import ProviderResponseError
from backend.app.integrations.google.places import (
    PLACES_CANDIDATE_FIELD_MASK,
    PLACES_DETAILS_FIELD_MASK,
    PLACES_REVIEWS_FIELD_MASK,
    GooglePlacesProvider,
)
from backend.app.integrations.google.routes import (
    ROUTE_MATRIX_FIELD_MASK,
    GoogleRoutesProvider,
)
from backend.app.integrations.models import (
    LatLng,
    PlaceDetailsRequest,
    PlaceReviewsRequest,
    PlaceSearchRequest,
    RouteMatrixRequest,
    RouteWaypoint,
)
from backend.app.observability.run_trace import (
    FileRunTracer,
    NullRunTracer,
    RunTraceContext,
    TracePayloadMode,
)
from backend.app.policies.trip_dates import create_trip_date_window
from backend.tests.request_fixtures import make_request


@dataclass
class FakeTransport:
    responses: list[object]
    calls: list[dict[str, object]] = field(default_factory=list)

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        json_body: object | None = None,
    ) -> object:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "json_body": json_body,
            }
        )
        return self.responses.pop(0)


TRACER = NullRunTracer(UUID("00000000-0000-0000-0000-000000000001"))


def test_places_candidate_and_details_field_masks_match_current_api_paths() -> None:
    transport = FakeTransport(
        responses=[
            {
                "places": [
                    {
                        "id": "poi-1",
                        "displayName": {"text": "Museum"},
                        "location": {"latitude": -33.8, "longitude": 151.2},
                        "formattedAddress": "Sydney",
                        "primaryType": "museum",
                        "businessStatus": "OPERATIONAL",
                        "openingDate": {"year": 2026, "month": 9, "day": 15},
                    }
                ]
            },
            {
                "id": "poi-1",
                "displayName": {"text": "Museum"},
                "location": {"latitude": -33.8, "longitude": 151.2},
                "timeZone": {"id": "Australia/Sydney", "version": "2026a"},
                "currentOpeningHours": {"weekdayDescriptions": ["Tuesday: Closed"]},
                "regularOpeningHours": {"weekdayDescriptions": ["Tuesday: 9:00 AM – 6:00 PM"]},
                "openingDate": {"year": 2026, "month": 9},
                "rating": 4.5,
                "userRatingCount": 123,
            },
        ]
    )
    provider = GooglePlacesProvider(api_key="secret-key", transport=transport, tracer=TRACER)

    async def scenario():
        await provider.search_text(
            PlaceSearchRequest(
                text_query="museums in Sydney",
                page_size=5,
                field_mask=PLACES_CANDIDATE_FIELD_MASK,
                include_future_opening_businesses=True,
            )
        )
        return await provider.get_place_details(
            PlaceDetailsRequest(place_id="poi-1", field_mask=PLACES_DETAILS_FIELD_MASK)
        )

    details = asyncio.run(scenario())

    assert PLACES_CANDIDATE_FIELD_MASK == (
        "places.id,places.displayName,places.location,places.formattedAddress,"
        "places.primaryType,places.businessStatus,places.openingDate"
    )
    assert "places.displayName.text" not in PLACES_CANDIDATE_FIELD_MASK
    assert "rating" not in PLACES_CANDIDATE_FIELD_MASK.casefold()
    assert "reviews" not in PLACES_CANDIDATE_FIELD_MASK.casefold()
    assert "reviews" not in PLACES_DETAILS_FIELD_MASK.casefold()
    assert "userRatingCount" not in PLACES_DETAILS_FIELD_MASK
    assert details.time_zone == "Australia/Sydney"
    assert details.current_opening_hours == {"weekdayDescriptions": ["Tuesday: Closed"]}
    assert details.regular_opening_hours == {"weekdayDescriptions": ["Tuesday: 9:00 AM – 6:00 PM"]}
    assert details.requested_at is not None
    assert details.requested_at <= details.retrieved_at
    assert details.rating == 4.5
    assert details.opening_date is not None
    assert details.opening_date.model_dump() == {"year": 2026, "month": 9, "day": None}
    assert "user_rating_count" not in type(details).model_fields
    assert transport.calls[0]["json_body"]["includeFutureOpeningBusinesses"] is True
    assert transport.calls[0]["headers"]["X-Goog-FieldMask"] == PLACES_CANDIDATE_FIELD_MASK
    assert transport.calls[1]["headers"]["X-Goog-FieldMask"] == PLACES_DETAILS_FIELD_MASK


def test_places_search_preserves_raw_result_count_original_rank_and_partial_dates() -> None:
    transport = FakeTransport(
        responses=[
            {
                "places": [
                    {"id": "invalid-without-name"},
                    {
                        "id": "full",
                        "displayName": {"text": "Full"},
                        "location": {"latitude": -33.8, "longitude": 151.2},
                        "openingDate": {"year": 2026, "month": 9, "day": 15},
                    },
                    {
                        "id": "partial",
                        "displayName": {"text": "Partial"},
                        "location": {"latitude": -33.8, "longitude": 151.2},
                        "openingDate": {"year": 2026, "month": 9},
                    },
                    {
                        "id": "absent",
                        "displayName": {"text": "Absent"},
                        "location": {"latitude": -33.8, "longitude": 151.2},
                    },
                ]
            }
        ]
    )
    provider = GooglePlacesProvider(api_key="secret", transport=transport, tracer=TRACER)
    response = asyncio.run(
        provider.search_text(
            PlaceSearchRequest(
                text_query="places in Sydney",
                page_size=5,
                field_mask=PLACES_CANDIDATE_FIELD_MASK,
            )
        )
    )

    assert response.actual_result_count == 4
    assert [item.provider_rank for item in response.candidates] == [1, 2, 3]
    assert response.candidates[0].opening_date.model_dump() == {
        "year": 2026,
        "month": 9,
        "day": 15,
    }
    assert response.candidates[1].opening_date.model_dump() == {
        "year": 2026,
        "month": 9,
        "day": None,
    }
    assert response.candidates[2].opening_date is None
    assert "includeFutureOpeningBusinesses" not in transport.calls[0]["json_body"]


def test_places_details_missing_or_invalid_rating_remains_a_successful_response() -> None:
    base = {
        "id": "poi-1",
        "displayName": {"text": "Museum"},
        "location": {"latitude": -33.8, "longitude": 151.2},
    }
    transport = FakeTransport(responses=[base, {**base, "rating": 6}])
    provider = GooglePlacesProvider(api_key="secret", transport=transport, tracer=TRACER)
    request = PlaceDetailsRequest(place_id="poi-1", field_mask=PLACES_DETAILS_FIELD_MASK)

    async def scenario():
        return await provider.get_place_details(request), await provider.get_place_details(request)

    missing, invalid = asyncio.run(scenario())
    assert missing.rating is None
    assert invalid.rating is None
    assert missing.place_id == invalid.place_id == "poi-1"


def test_places_review_only_details_support_empty_and_distinguish_provider_error() -> None:
    transport = FakeTransport(
        responses=[
            {
                "id": "poi-1",
                "reviews": [
                    {
                        "name": "places/poi-1/reviews/review-1",
                        "text": {"text": "Quiet in the morning", "languageCode": "en"},
                        "publishTime": "2026-09-10T00:00:00Z",
                        "googleMapsUri": "https://maps.google.com/review-1",
                    }
                ],
            },
            {"id": "poi-1", "reviews": []},
            {"id": "poi-1", "reviews": "malformed"},
        ]
    )
    provider = GooglePlacesProvider(api_key="secret", transport=transport, tracer=TRACER)
    request = PlaceReviewsRequest(place_id="poi-1", field_mask=PLACES_REVIEWS_FIELD_MASK)

    async def scenario():
        populated = await provider.get_place_reviews(request)
        empty = await provider.get_place_reviews(request)
        with pytest.raises(ProviderResponseError):
            await provider.get_place_reviews(request)
        return populated, empty

    populated, empty = asyncio.run(scenario())
    assert PLACES_REVIEWS_FIELD_MASK == (
        "id,reviews.name,reviews.text,reviews.publishTime,reviews.googleMapsUri"
    )
    assert "location" not in PLACES_REVIEWS_FIELD_MASK
    assert "displayName" not in PLACES_REVIEWS_FIELD_MASK
    assert len(populated.reviews) == 1
    assert populated.reviews[0].resource_name == "places/poi-1/reviews/review-1"
    assert populated.reviews[0].text == "Quiet in the morning"
    assert populated.reviews[0].publish_time.isoformat() == "2026-09-10T00:00:00+00:00"
    assert empty.reviews == []
    assert all(
        call["headers"]["X-Goog-FieldMask"] == PLACES_REVIEWS_FIELD_MASK for call in transport.calls
    )


def test_places_raw_trace_records_review_count_not_review_text(tmp_path: Path) -> None:
    tracer = FileRunTracer(
        RunTraceContext(
            run_id=UUID("00000000-0000-0000-0000-000000000022"),
            system_version="v1",
            reference_date=date(2026, 9, 11),
            date_window=create_trip_date_window(date(2026, 9, 11)),
            request=make_request(additional_preferences="Plan Sydney."),
            started_at=datetime(2026, 9, 11, tzinfo=UTC),
        ),
        root=tmp_path,
        payload_mode=TracePayloadMode.RAW,
        raw_provider_payloads=True,
    )
    transport = FakeTransport(
        responses=[
            {
                "id": "poi-1",
                "reviews": [{"text": {"text": "PRIVATE_REVIEW_TEXT_NOT_FOR_TRACE"}}],
            }
        ]
    )
    provider = GooglePlacesProvider(
        api_key="private-google-key", transport=transport, tracer=tracer
    )

    result = asyncio.run(
        provider.get_place_reviews(
            PlaceReviewsRequest(place_id="poi-1", field_mask=PLACES_REVIEWS_FIELD_MASK)
        )
    )
    trace_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in tracer.run_directory.rglob("*")
        if path.is_file()
    )
    assert result.reviews[0].text == "PRIVATE_REVIEW_TEXT_NOT_FOR_TRACE"
    assert "PRIVATE_REVIEW_TEXT_NOT_FOR_TRACE" not in trace_text
    assert "private-google-key" not in trace_text
    assert '"review_count": 1' in trace_text


def test_routes_adapter_uses_minimal_fields_and_omits_invalid_preference() -> None:
    transport = FakeTransport(responses=[[]])
    provider = GoogleRoutesProvider(api_key="secret-key", transport=transport, tracer=TRACER)
    waypoint = RouteWaypoint(place_id="poi-1", location=LatLng(latitude=-33.8, longitude=151.2))

    asyncio.run(
        provider.compute_route_matrix(
            RouteMatrixRequest(
                origins=[waypoint],
                destinations=[waypoint],
                travel_mode="WALK",
                field_mask=ROUTE_MATRIX_FIELD_MASK,
            )
        )
    )

    body = transport.calls[0]["json_body"]
    assert ROUTE_MATRIX_FIELD_MASK == (
        "originIndex,destinationIndex,duration,staticDuration,fallbackInfo,distanceMeters,status,condition"
    )
    assert body["travelMode"] == "WALK"
    assert "routingPreference" not in body
    assert "departureTime" not in body


@pytest.mark.parametrize("routing_preference", [None, "TRAFFIC_UNAWARE"])
def test_routes_adapter_omits_departure_for_traffic_unaware_drive(
    routing_preference: str | None,
) -> None:
    transport = FakeTransport(responses=[[]])
    provider = GoogleRoutesProvider(api_key="test-key", transport=transport, tracer=TRACER)
    waypoint = RouteWaypoint(place_id="poi-1", location=LatLng(latitude=41.36, longitude=2.16))
    asyncio.run(
        provider.compute_route_matrix(
            RouteMatrixRequest(
                origins=[waypoint],
                destinations=[waypoint],
                travel_mode="DRIVE",
                routing_preference=routing_preference,
                departure_time=datetime.fromisoformat("2026-10-30T13:00:00+01:00"),
                field_mask=ROUTE_MATRIX_FIELD_MASK,
            )
        )
    )
    body = transport.calls[0]["json_body"]
    assert "departureTime" not in body
    if routing_preference is not None:
        assert body["routingPreference"] == routing_preference


@pytest.mark.parametrize("routing_preference", ["TRAFFIC_AWARE", "TRAFFIC_AWARE_OPTIMAL"])
def test_routes_adapter_preserves_departure_for_traffic_aware_drive(
    routing_preference: str,
) -> None:
    transport = FakeTransport(responses=[[]])
    provider = GoogleRoutesProvider(api_key="test-key", transport=transport, tracer=TRACER)
    waypoint = RouteWaypoint(place_id="poi-1", location=LatLng(latitude=41.36, longitude=2.16))
    request = RouteMatrixRequest(
        origins=[waypoint],
        destinations=[waypoint],
        travel_mode="DRIVE",
        routing_preference=routing_preference,
        departure_time=datetime.fromisoformat("2026-10-30T13:00:00+01:00"),
        field_mask=ROUTE_MATRIX_FIELD_MASK,
    )
    asyncio.run(provider.compute_route_matrix(request))
    body = transport.calls[0]["json_body"]
    assert body["departureTime"] == "2026-10-30T12:00:00Z"
    assert body["routingPreference"] == routing_preference
    assert request.departure_time == datetime.fromisoformat("2026-10-30T13:00:00+01:00")


def test_routes_adapter_serializes_transit_departure_time() -> None:
    transport = FakeTransport(responses=[[]])
    provider = GoogleRoutesProvider(api_key="secret-key", transport=transport, tracer=TRACER)
    waypoint = RouteWaypoint(place_id="poi-1", location=LatLng(latitude=-33.8, longitude=151.2))

    asyncio.run(
        provider.compute_route_matrix(
            RouteMatrixRequest(
                origins=[waypoint],
                destinations=[waypoint],
                travel_mode="TRANSIT",
                departure_time=datetime.fromisoformat("2026-09-12T12:00:00+10:00"),
                field_mask=ROUTE_MATRIX_FIELD_MASK,
            )
        )
    )

    assert transport.calls[0]["json_body"]["departureTime"] == "2026-09-12T02:00:00Z"
