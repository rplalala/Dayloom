"""Shared mixed transport exercises real acquisition and binding with fake providers."""

import asyncio
from datetime import timedelta

import pytest
from pydantic import ValidationError

from backend.app.evidence.models import RouteEvidenceBundle
from backend.app.integrations.models import RouteMatrixDTO
from backend.app.policies.transport import TransportModeDecision
from backend.app.runtime.budget import ToolBudgetKey
from backend.app.runtime.config_loader import load_runtime_config
from backend.app.runtime.config_models import RuntimeConfig
from backend.app.services.initial_routes import InitialRoutes, RouteWork, compact_routes
from backend.tests.versions.v1.test_graph import _dependencies
from backend.tests.versions.v3.test_mixed_transport import measured
from backend.tests.versions.v3.test_repair import activity, context, draft, place


class Provider:
    def __init__(self, transit=600, drive=900, fail=False):
        self.requests = []
        self.transit, self.drive, self.fail = transit, drive, fail

    async def compute_route_matrix(self, request):
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("fixture provider failure")
        seconds = {"WALK": 3600, "TRANSIT": self.transit, "DRIVE": self.drive}[request.travel_mode]
        return RouteMatrixDTO(
            elements=[
                dict(
                    originIndex=i,
                    destinationIndex=j,
                    status={},
                    condition="ROUTE_EXISTS",
                    duration=f"{seconds}s",
                    distanceMeters=4000,
                )
                for i in range(len(request.origins))
                for j in range(len(request.destinations))
            ],
            retrieved_at="2026-09-11T00:00:00+00:00",
        )


def service(provider=None):
    *_, acq = _dependencies()
    acq._routes = provider or Provider()
    return InitialRoutes(acq, load_runtime_config())


def decision(explicit=False):
    return TransportModeDecision(
        travel_mode="WALK",
        reason="explicit_mode_fixture"
        if explicit
        else "default_pedestrian_transfer_for_poi_grouping",
    )


def bind(svc, evidence=(), explicit=False, start="12:00"):
    original = draft([activity(), activity("two", "b", start, "13:00")])
    ctx = context()
    bundle = RouteEvidenceBundle(baseline=measured("WALK", 3600), alternatives=list(evidence))
    result, routes = asyncio.run(
        svc.bind(original, ctx.contract, ctx.places, bundle, decision(explicit))
    )
    assert result.days == original.days
    assert original.transfers == [] and original.route_diagnostics == []
    return result, routes


def test_cached_drive_selected_without_transit_send_and_reserve_is_separate():
    svc = service()
    result, _ = bind(svc, [measured("DRIVE", 900)])
    assert not svc.acq._routes.requests
    assert result.transfers[0].mode == "DRIVE"
    assert result.transfers[0].provider_duration_seconds == 900
    assert result.transfers[0].reserve_seconds == 600
    assert result.route_diagnostics[0]["result"] == "PASS"


@pytest.mark.parametrize("fail", [False, True])
def test_hard_mode_set_prevents_drive_acquisition_and_cached_fallback(fail):
    svc = service(Provider(fail=fail))
    original = draft([activity(), activity("two", "b", "12:00", "13:00")])
    ctx = context()
    mode = TransportModeDecision(
        travel_mode="WALK", reason="hard_allowed_modes", allowed_modes=("WALK", "TRANSIT")
    )
    bundle = RouteEvidenceBundle(
        baseline=measured("WALK", 3600), alternatives=[measured("DRIVE", 900)]
    )
    final, _ = asyncio.run(svc.bind(original, ctx.contract, ctx.places, bundle, mode))
    assert all(r.travel_mode in ("WALK", "TRANSIT") for r in svc.acq._routes.requests)
    assert all(t.mode in ("WALK", "TRANSIT") and t.reserve_seconds == 0 for t in final.transfers)
    assert final.route_diagnostics[0]["considered_modes"] == ["WALK", "TRANSIT"]
    if fail:
        assert not final.transfers
        assert final.route_diagnostics[0]["result"] == "UNKNOWN"


def test_representative_transit_is_replaced_at_actual_departure():
    svc = service()
    representative = activity().end_time + timedelta(hours=4)
    result, _ = bind(svc, [measured("TRANSIT", 600, departure=representative)])
    assert result.transfers[0].mode == "TRANSIT"
    assert svc.acq._routes.requests[0].departure_time == activity().end_time
    assert len(svc.acq._routes.requests) == 1


def test_explicit_walk_conflict_and_default_unknown_are_distinct():
    svc = service(Provider(fail=True))
    result, _ = bind(svc, start="11:30")
    row = result.route_diagnostics[0]
    assert row["result"] == "UNKNOWN"
    assert row["mode_results"][0]["status"] == "CONFIRMED"
    assert not result.transfers
    result, _ = bind(service(), explicit=True, start="11:30")
    assert result.route_diagnostics[0]["result"] == "CONFIRMED"


def test_pre_reserves_all_three_dimensions_and_post_can_use_new_pair():
    svc = service()
    places = {f"p{i}": place(f"p{i}") for i in range(19)}

    async def exercise():
        with svc.work.active("pre"):
            for i in range(1, 18):
                await svc.fetch("p0", f"p{i}", "DRIVE", None, places)
        assert len(svc.pairs) == 16
        assert len(svc.acq._routes.requests) == 16
        with svc.work.active("post"):
            await svc.fetch("p0", "p18", "DRIVE", None, places)

    asyncio.run(exercise())
    assert len(svc.pairs) == 17
    assert svc.acq._budget.summary()[ToolBudgetKey.ALTERNATIVE_ROUTE_ELEMENTS.value]["used"] == 17


def test_same_pair_modes_charge_sends_not_duplicate_pairs_and_cache_survives_exhaustion():
    svc = service()
    places = {p.place_id: p for p in context().places}

    async def exercise():
        with svc.work.active("post"):
            await svc.fetch("a", "b", "DRIVE", None, places)
            await svc.fetch("a", "b", "WALK", None, places)
            for key in (
                ToolBudgetKey.ALTERNATIVE_ROUTE_ELEMENTS,
                ToolBudgetKey.ALTERNATIVE_ROUTE_MATRIX_CALLS,
                ToolBudgetKey.ALTERNATIVE_ROUTE_PAIRS,
            ):
                svc.acq._budget.consume(key, svc.acq._budget.remaining(key))
            cached = await svc.fetch("a", "b", "DRIVE", None, places)
            assert cached.availability == "available"

    asyncio.run(exercise())
    assert len(svc.pairs) == 1 and len(svc.acq._routes.requests) == 2


def test_no_send_failure_is_terminal_after_real_send():
    svc = service(Provider(fail=True))
    places = {p.place_id: p for p in context().places}

    async def exercise():
        with svc.work.active("post"):
            await svc.fetch("a", "b", "DRIVE", None, places)
            await svc.fetch("a", "b", "DRIVE", None, places)

    asyncio.run(exercise())
    assert len(svc.acq._routes.requests) == 1
    assert len(svc.pairs) == 1


def test_work_clock_pauses_and_nested_overlap_is_counted_once():
    now = [0.0]
    work = RouteWork(load_runtime_config().budget.routes, lambda: now[0])
    with work.active("pre"):
        now[0] = 20
        with work.active("pre"):
            now[0] = 30
        now[0] = 40
    now[0] = 100  # Primary time is outside active route work.
    with work.active("post"):
        now[0] = 110
    assert work.elapsed == 50 and work.remaining() == 70


def test_compact_projection_preserves_baseline_and_supplementary_directions():
    bundle = RouteEvidenceBundle(
        baseline=measured("WALK", 3600), alternatives=[measured("DRIVE", 900, "b", "c")]
    )
    first = compact_routes(bundle)
    assert {(r["origin"], r["destination"]) for r in first["directed_facts"]} == {
        ("a", "b"),
        ("b", "c"),
    }
    assert first["omissions"] == []
    assert first == compact_routes(bundle)


def test_supplied_places_only_and_pre_generation_drive_reaches_real_projection():
    svc = service(Provider(transit=4000))
    ctx = context()
    bundle = asyncio.run(
        svc.prepare(
            places=list(ctx.places), mode=decision(), requirements=ctx.contract.requirements
        )
    )
    projection = compact_routes(bundle)
    assert any(s["mode"] == "DRIVE" for s in projection["sources"].values())
    assert all(
        r["origin"] in {p.place_id for p in ctx.places} for r in projection["directed_facts"]
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("post_generation_reserved_pairs", 33),
        ("post_generation_reserved_requests", 33),
        ("post_generation_reserved_elements", 65),
        ("work_seconds", 0),
        ("post_generation_reserved_seconds", 121),
    ],
)
def test_invalid_route_config_rejected(field, value):
    data = load_runtime_config().model_dump()
    data["budget"]["routes"][field] = value
    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate(data)


def test_actual_v1_graph_receives_drive_and_binds_without_second_primary():
    from datetime import date

    from backend.app.versions.v1.runner import run_v1
    from backend.tests.request_fixtures import make_request
    from backend.tests.versions.v1.fakes import RevisedFakeLLM, make_revised_extraction
    from backend.tests.versions.v3.test_wiring import primary

    initial = primary()
    second = initial.days[0].activities[1]
    initial.days[0].activities[1] = second.model_copy(
        update={
            "start_time": second.start_time.replace(hour=12, minute=0),
            "end_time": second.end_time.replace(hour=13, minute=0),
        }
    )
    llm = RevisedFakeLLM([make_revised_extraction(), initial])
    _, places, weather, _, tracer, _ = _dependencies()
    provider = Provider(transit=4000)
    result = asyncio.run(
        run_v1(
            make_request(additional_preferences="Plan two days in Sydney."),
            llm,
            places,
            weather,
            provider,
            reference_date=date(2026, 9, 11),
            tracer=tracer,
        )
    )
    assert len(llm.calls) == 2  # One interpretation, one primary, no Repair.
    assert '"mode": "DRIVE"' in llm.calls[-1].user_prompt
    assert result.itinerary.transfers[0].mode == "DRIVE"
    assert result.itinerary.days == initial.days
    assert result.itinerary.route_diagnostics[0]["result"] == "PASS"


def test_cached_walk_suitable_does_not_send_fallback():
    svc = service()
    initial = draft([activity(), activity("two", "b", "12:00", "13:00")])
    ctx = context()
    bundle = RouteEvidenceBundle(baseline=measured("WALK", 600, distance=500))
    final, _ = asyncio.run(svc.bind(initial, ctx.contract, ctx.places, bundle, decision()))
    assert final.transfers[0].mode == "WALK" and not svc.acq._routes.requests


def test_unlocated_real_activity_is_not_silently_skipped():
    svc = service()
    unknown = activity("unknown", None, "11:10", "11:20").model_copy(
        update={"activity_kind": "generic_activity"}
    )
    initial = draft([activity(), unknown, activity("two", "b", "12:00", "13:00")])
    ctx = context()
    final, _ = asyncio.run(
        svc.bind(
            initial,
            ctx.contract,
            ctx.places,
            RouteEvidenceBundle(baseline=measured("WALK", 600, distance=500)),
            decision(),
        )
    )
    assert len(final.route_diagnostics) == 2
    assert all(r["reason"] == "not_evaluable_location_or_time" for r in final.route_diagnostics)
    assert not svc.acq._routes.requests


def test_explicit_drive_is_not_changed_to_walk():
    svc = service()
    ctx = context()
    initial = draft([activity(), activity("two", "b", "12:00", "13:00")])
    mode = TransportModeDecision(
        travel_mode="DRIVE", reason="explicit_mode_fixture", routing_preference="TRAFFIC_UNAWARE"
    )
    bundle = RouteEvidenceBundle(
        baseline=measured("WALK", 600, distance=500), alternatives=[measured("DRIVE", 900)]
    )
    final, _ = asyncio.run(svc.bind(initial, ctx.contract, ctx.places, bundle, mode))
    assert final.transfers[0].mode == "DRIVE"
    assert final.transfers[0].mode_source == "USER_EXPLICIT"


def test_cancellation_propagates_without_fallback():
    class Cancel(Provider):
        async def compute_route_matrix(self, request):
            self.requests.append(request)
            raise asyncio.CancelledError()

    svc = service(Cancel())
    with pytest.raises(asyncio.CancelledError):
        bind(svc)
    assert len(svc.acq._routes.requests) == 1
    assert svc.work.depth == 0


def test_work_reservation_and_request_deadline_both_limit_fetch():
    now = [0.0]
    work = RouteWork(load_runtime_config().budget.routes, lambda: now[0])
    with work.active("pre"):
        now[0] = 90
        assert work.remaining() == 0
    with work.active("post"):
        assert work.remaining() == 30
        work.request_deadline = 100
        work.nearby_reserve = 10
        assert work.remaining() == 0


def test_shared_yaml_policy_propagates_to_repair_projection():
    data = load_runtime_config().model_dump()
    data["transport"]["drive_max_minutes"] = 25
    changed = RuntimeConfig.model_validate(data)
    assert changed.transport.drive_max_minutes == 25
    assert changed.v3_repair.spatial.drive_max_minutes == 25
