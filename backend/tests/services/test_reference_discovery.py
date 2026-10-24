"""Offline nearby discovery, timing, identity and primary-invariance checks."""

import asyncio
from datetime import date
from types import SimpleNamespace

import pytest

from backend.app.integrations.models import LatLng, PlaceCandidateDTO, PlaceSearchResponse
from backend.app.runtime.cache import RequestCache
from backend.app.runtime.config_models import ReferenceDiscoveryConfig
from backend.app.schemas.itinerary import Activity, ItineraryDay
from backend.app.schemas.itinerary_projection import EstimatedCostProjectionDiagnostic, V1Itinerary
from backend.app.services import reference_discovery as module
from backend.app.services.reference_discovery import ReferenceDiscoveryService, attach_references


def primary(*ids):
    return V1Itinerary(
        output_version="itinerary_2",
        destination="Test region",
        start_date="2026-10-01",
        end_date="2026-10-01",
        days=[
            ItineraryDay(
                date="2026-10-01",
                activities=[
                    Activity(
                        activity_id=f"activity-{i}",
                        title="Visit",
                        source_place_id=pid,
                        place_name=f"Place {pid}" if pid else None,
                        start_time="2026-10-01T09:00:00+00:00",
                        end_time="2026-10-01T10:00:00+00:00",
                        estimated_cost={"amount": "10", "currency": "USD"},
                    )
                    for i, pid in enumerate(ids)
                ],
            )
        ],
    )


def place(pid, lat=0, **changes):
    return SimpleNamespace(
        place_id=pid,
        name=f"Place {pid}",
        latitude=lat,
        longitude=0,
        business_status=changes.get("business_status"),
    )


def candidate(pid="new", lat=0.001, **changes):
    return PlaceCandidateDTO(
        place_id=pid,
        display_name=f"Nearby {pid}",
        location=LatLng(latitude=lat, longitude=0),
        provider_rank=0,
        types=("cafe",),
        attributions=({"provider": "Test attribution"},),
        **changes,
    )


def response(*candidates):
    return PlaceSearchResponse(
        candidates=list(candidates),
        actual_result_count=len(candidates),
        retrieved_at="2026-10-01T00:00:00Z",
    )


class Provider:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    async def search_nearby(self, request):
        self.requests.append(request)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def service(provider, cache=None, **config):
    return ReferenceDiscoveryService(
        provider, cache if cache is not None else RequestCache(), ReferenceDiscoveryConfig(**config)
    )


def run(provider, itinerary=None, places=None, excluded=(), **config):
    itinerary = itinerary or primary("a")
    places = places or [place("a")]
    return asyncio.run(
        service(provider, **config).discover(
            itinerary, places, [p.place_id for p in places], excluded
        )
    )


def test_only_scheduled_anchors_new_ledger_and_primary_unchanged():
    original = primary("a")
    original.set_cost_projections((EstimatedCostProjectionDiagnostic("cost", "exact_point"),))
    provider = Provider(response(candidate()))
    result = run(provider, original, [place("a"), place("unused", 1)])
    assert len(provider.requests) == 1 and provider.requests[0].center.latitude == 0
    assert provider.requests[0].rank_preference == "DISTANCE"
    assert result.itinerary.model_dump(
        exclude={"reference_recommendations"}
    ) == original.model_dump(exclude={"reference_recommendations"})
    assert result.itinerary.cost_projections == original.cost_projections
    ref = result.itinerary.reference_recommendations[0]
    entry = result.ledger["new"]
    assert ref.source_place_id == "new" and ref.source_ref == entry.source_ref
    assert ref.associated_day == date(2026, 10, 1)
    assert entry.anchor.place_id == "a" and entry.anchor.activity_id == "activity-0"
    assert entry.place.attributions == ({"provider": "Test attribution"},)
    assert "straight-line" in ref.reason and "unverified" in ref.uncertainty
    assert "unused" not in result.ledger


def test_unused_supply_only_qualifies_when_independently_rediscovered():
    assert not run(
        Provider(response()), places=[place("a"), place("unused")]
    ).itinerary.reference_recommendations
    result = run(Provider(response(candidate("unused"))), places=[place("a"), place("unused")])
    assert result.itinerary.reference_recommendations[0].source_place_id == "unused"


def test_non_transitive_reuse_duplicate_activities_and_actual_anchor_distance():
    provider = Provider(response(candidate("edge", 0.008)), response())
    result = run(
        provider, primary("a", "b", "b", "c"), [place("a"), place("b", 0.002), place("c", 0.004)]
    )
    assert len(provider.requests) == 2
    assert result.diagnostics["representative_groups"] == [["a", "b"], ["c"]]
    entry = result.ledger["edge"]
    assert entry.anchor.place_id == "b" and entry.representative.place_id == "a"
    assert entry.distance_metres < 800
    assert any(s["reason"] == "duplicate_place" for s in result.diagnostics["skipped_anchors"])


def test_radius_rechecked_and_light_filters_do_not_enrich():
    values = [
        candidate("a"),
        candidate("excluded"),
        candidate("closed", business_status="CLOSED_TEMPORARILY"),
        candidate("far", lat=1),
        candidate("valid"),
        candidate("valid"),
    ]
    result = run(Provider(response(*values)), excluded=("excluded",))
    assert [r.source_place_id for r in result.itinerary.reference_recommendations] == ["valid"]
    assert result.diagnostics["rejections"]["outside_radius"] == 1


def test_representative_cap_round_robin_and_no_type_quota():
    provider = Provider(*(response(candidate(str(i), lat=i)) for i in range(3)))
    result = run(
        provider,
        primary("a", "b", "c", "d"),
        [place("a"), place("b", 1), place("c", 2), place("d", 3)],
    )
    assert result.diagnostics["requests_sent"] == 3
    assert result.diagnostics["uncovered_anchor_ids"] == ["d"]
    assert [r.source_place_id for r in result.itinerary.reference_recommendations] == [
        "0",
        "1",
        "2",
    ]


def test_cache_hit_zero_budget_and_failures_consume_attempts_without_retry():
    async def scenario():
        provider, cache = Provider(response(candidate())), RequestCache()
        first = await service(provider, cache).discover(primary("a"), [place("a")], ["a"])
        second = await service(provider, cache, max_requests=0).discover(
            primary("a"), [place("a")], ["a"]
        )
        assert first.diagnostics["requests_sent"] == 1
        assert second.diagnostics["requests_sent"] == 0 and second.diagnostics["cache_hits"] == 1
        assert first.ledger["new"].call_id == second.ledger["new"].call_id
        failing = Provider(RuntimeError("offline failure"))
        single = service(failing, max_requests=1)
        result = await single.discover(primary("a", "b"), [place("a"), place("b", 1)], ["a", "b"])
        assert len(failing.requests) == 1
        assert result.diagnostics["outcomes"] == ["provider_error", "budget_exhausted"]
        again = await single.discover(primary("a"), [place("a")], ["a"])
        assert again.diagnostics["requests_sent"] == 0 and len(failing.requests) == 1

    asyncio.run(scenario())


def test_partial_and_all_failed_keep_successful_primary():
    provider = Provider(response(candidate()), RuntimeError("failure"))
    original = primary("a", "b")
    result = run(provider, original, [place("a"), place("b", 1)])
    assert result.diagnostics["status"] == "partial"
    assert len(result.itinerary.reference_recommendations) == 1
    result = run(Provider(RuntimeError("failure")), original, [place("a")])
    assert result.diagnostics["status"] == "provider_error"
    assert result.itinerary.model_dump() == original.model_dump()


def test_deadline_cancels_request_and_does_not_schedule_followups():
    class Slow:
        calls = 0
        cancelled = False

        async def search_nearby(self, request):
            self.calls += 1
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled = True

    provider = Slow()
    result = run(
        provider,
        primary("a", "b"),
        [place("a"), place("b", 1)],
        deadline_seconds=0.02,
        request_timeout_seconds=0.1,
    )
    assert provider.calls == 1 and provider.cancelled
    assert result.diagnostics["status"] == "deadline_exceeded"
    assert result.itinerary.reference_recommendations == []


def test_user_cancellation_propagates():
    class Cancels:
        async def search_nearby(self, request):
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        run(Cancels())


def test_no_anchors_or_invalid_coordinates_never_search():
    provider = Provider()
    result = run(provider, primary(None, "missing"), [place("a")])
    assert result.diagnostics["status"] == "no_anchors" and provider.requests == []
    assert (
        run(provider, primary("a"), [place("a", float("nan"))]).diagnostics["status"]
        == "no_anchors"
    )


def test_attachment_failure_falls_back_and_ledgers_cannot_be_interchanged(monkeypatch):
    original = primary("a")
    result = run(Provider(response(candidate())), original)
    with pytest.raises(ValueError, match="nearby ledger"):
        attach_references(original, result.itinerary.reference_recommendations, {}, [])
    with pytest.raises(ValueError, match="anchor"):
        attach_references(original, result.itinerary.reference_recommendations, result.ledger, [])

    def broken(*args):
        raise ValueError("invalid attachment")

    monkeypatch.setattr(module, "attach_references", broken)
    result = run(Provider(response(candidate())), original)
    assert result.itinerary is original and result.diagnostics["status"] == "attachment_error"


def test_exact_cache_parameters_do_not_collide():
    async def scenario():
        provider = Provider(response(), response())
        cache = RequestCache()
        await service(provider, cache).discover(primary("a"), [place("a")], ["a"])
        await service(provider, cache, radius_metres=700).discover(
            primary("a"), [place("a")], ["a"]
        )
        assert len(provider.requests) == 2

    asyncio.run(scenario())


def test_round_robin_duplicate_names_unknown_and_invalid_candidates():
    first = response(
        candidate("a1"),
        candidate("a2", 0.002),
        candidate("a3", 0.003).model_copy(update={"display_name": "Nearby a1"}),
        candidate("invalid").model_copy(update={"place_id": ""}),
        candidate("wrong").model_copy(update={"types": ("bank",)}),
    )
    second = response(candidate("b1", 1), candidate("b2", 1.001))
    result = run(Provider(first, second), primary("a", "b"), [place("a"), place("b", 1)])
    assert [r.source_place_id for r in result.itinerary.reference_recommendations] == [
        "a1",
        "b1",
        "a2",
    ]
    assert result.diagnostics["rejections"]["invalid_candidate"] == 1
    assert result.diagnostics["rejections"]["unsupported_type"] == 1


def test_known_closed_supply_not_overridden_by_unknown_nearby_status():
    result = run(
        Provider(response(candidate("unused"))),
        places=[place("a"), place("unused", business_status="CLOSED_PERMANENTLY")],
    )
    assert result.itinerary.reference_recommendations == []


def test_one_request_timeout_can_preserve_a_later_success():
    class SometimesSlow(Provider):
        cancelled = False

        async def search_nearby(self, request):
            if not self.requests:
                self.requests.append(request)
                try:
                    await asyncio.Event().wait()
                finally:
                    self.cancelled = True
            return await super().search_nearby(request)

    provider = SometimesSlow(response(candidate("new", 1)))
    result = run(
        provider,
        primary("a", "b"),
        [place("a"), place("b", 1)],
        deadline_seconds=1,
        request_timeout_seconds=0.01,
    )
    assert provider.cancelled and len(provider.requests) == 2
    assert result.diagnostics["status"] == "partial"
    assert len(result.itinerary.reference_recommendations) == 1


def test_radius_boundary_and_reused_candidate_outside_all_actual_anchors():
    from math import degrees

    within = degrees(799 / 6371000)
    outside = degrees(801 / 6371000)
    result = run(Provider(response(candidate("within", within), candidate("outside", outside))))
    assert [r.source_place_id for r in result.itinerary.reference_recommendations] == ["within"]
    result = run(
        Provider(response(candidate("outside", -outside))),
        primary("a", "b"),
        [place("a"), place("b", 0.002)],
    )
    assert result.itinerary.reference_recommendations == []


def test_budget_defaults_and_upper_bounds():
    from pydantic import ValidationError

    cfg = ReferenceDiscoveryConfig()
    assert (
        cfg.max_requests,
        cfg.max_result_count,
        cfg.radius_metres,
        cfg.anchor_reuse_metres,
        cfg.deadline_seconds,
        cfg.request_timeout_seconds,
        cfg.retries,
        cfg.max_references,
    ) == (3, 10, 800, 300, 10, 4, 0, 3)
    for changes in (
        {"max_requests": 11},
        {"retries": 1},
        {"rank_preference": "POPULARITY"},
        {"max_references": 21},
        {"included_types": ("casino",)},
    ):
        with pytest.raises(ValidationError):
            ReferenceDiscoveryConfig(**changes)


@pytest.mark.parametrize("days,expected_calls,expected_references", [(1, 1, 2), (10, 10, 20)])
def test_acceptance_nearby_scales_with_duration_without_changing_primary(
    days, expected_calls, expected_references,
):
    from datetime import timedelta

    from backend.app.runtime.config_loader import load_runtime_profile

    ids = [f"anchor-{index}" for index in range(days)]
    original = primary(*ids)
    first = original.days[0]
    original.days = [
        ItineraryDay(date=first.date + timedelta(days=index), activities=[
            activity.model_copy(update={
                "start_time": activity.start_time + timedelta(days=index),
                "end_time": activity.end_time + timedelta(days=index),
            })
        ]) for index, activity in enumerate(first.activities)
    ]
    original.end_date = original.days[-1].date
    provider = Provider(*[
        response(candidate(f"option-{i}-a", i * .01 + .001),
                 candidate(f"option-{i}-b", i * .01 + .002))
        for i in range(days)
    ])
    nearby = ReferenceDiscoveryService(
        provider, RequestCache(), load_runtime_profile("acceptance").reference_discovery
    )
    result = asyncio.run(nearby.discover(
        original, [place(pid, index * .01) for index, pid in enumerate(ids)], ids,
    ))
    assert len(provider.requests) == expected_calls
    assert len(result.itinerary.reference_recommendations) == expected_references
    before = original.model_dump(exclude={"reference_recommendations"})
    assert result.itinerary.model_dump(exclude={"reference_recommendations"}) == before
