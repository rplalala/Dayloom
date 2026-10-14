"""Real application route/component paths with fixture-only provider boundaries."""

import asyncio
from datetime import timedelta
from time import monotonic

from backend.app.schemas.itinerary import ItineraryDay
from backend.app.versions.v3.repair_budget import RepairBudget
from backend.app.versions.v3.repair_transport import allowed_modes, route_option
from backend.tests.versions.v3.test_multiround import policy
from backend.tests.versions.v3.test_repair import (
    DAY,
    Model,
    activity,
    context,
    draft,
    edit,
    place,
    route,
    run,
    scope_for,
)


def measured(mode, seconds, origin="a", destination="b", distance=4000, departure=None):
    return route(
        seconds,
        travel_mode=mode,
        representative_departure_time=departure,
        routing_preference="TRAFFIC_UNAWARE" if mode == "DRIVE" else None,
        elements=[
            dict(
                origin_place_id=origin,
                destination_place_id=destination,
                condition="ROUTE_EXISTS",
                status="OK",
                duration_seconds=seconds,
                distance_meters=distance,
                availability="available",
            )
        ],
    )


def test_existing_drive_enters_real_repair_beyond_walk_prefilter_without_fetch():
    original = draft()
    ctx = context(
        places=(place(), place("b", longitude=0.03)),
        route_evidence=(measured("WALK", 4200), measured("DRIVE", 1080)),
    )
    result = run(
        original=original,
        ctx=ctx,
        scope=scope_for(original, ctx, check="coverage", add_dates=(DAY,)),
        model=Model([edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")]),
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert len(result.final.transfers) == 1
    transfer = result.final.transfers[0]
    assert transfer.mode == "DRIVE" and transfer.provider_duration_seconds == 1080
    assert transfer.reserve_seconds == 600
    assert (transfer.arrival_time - transfer.departure_time).total_seconds() == 1680
    assert result.counters.get("routes", 0) == 0
    assert next(f for f in result.proposed_report.findings if f.check == "route").status == "PASS"


def test_drive_reserve_must_fit_actual_gap_and_explicit_walk_is_restrictive():
    left, right = activity(), activity("two", "b", "11:35", "12:35")
    assert route_option(left, right, "DRIVE", (measured("DRIVE", 1680),), policy().spatial) is None
    original, ctx = draft(), context()
    scope = scope_for(
        original,
        ctx,
        check="coverage",
        add_dates=(DAY,),
        travel_mode="WALK",
        mode_source="explicit_mode_in_user_request",
    )
    assert allowed_modes(scope) == ("WALK",)


def test_hard_modes_exclude_cached_drive_from_repair_candidates():
    original = draft()
    ctx = context(
        places=(place(), place("b", longitude=0.03)),
        route_evidence=(measured("WALK", 4200), measured("DRIVE", 1080)),
    )
    scope = scope_for(original, ctx, check="coverage", add_dates=(DAY,)).model_copy(
        update={"allowed_transport_modes": ("WALK", "TRANSIT")}
    )
    assert allowed_modes(scope) == ("WALK", "TRANSIT")
    result = run(
        original=original,
        ctx=ctx,
        scope=scope,
        model=Model([edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")]),
    )
    assert all(t.mode != "DRIVE" for t in result.final.transfers)


def test_transit_time_mismatch_and_unknown_drive_do_not_become_options():
    left, right = activity(), activity("two", "b", "12:00", "13:00")
    assert (
        route_option(
            left,
            right,
            "TRANSIT",
            (measured("TRANSIT", 600, departure=left.start_time),),
            policy().spatial,
        )
        is None
    )
    assert route_option(left, right, "DRIVE", (), policy().spatial) is None


def test_independent_date_rejection_keeps_legal_other_component():
    day2 = DAY + timedelta(days=1)
    original = draft()
    original = original.model_copy(
        update={
            "end_date": day2,
            "days": [
                original.days[0],
                ItineraryDay(
                    date=day2,
                    activities=[
                        activity("next", "c").model_copy(
                            update={
                                "start_time": activity().start_time + timedelta(days=1),
                                "end_time": activity().end_time + timedelta(days=1),
                            }
                        )
                    ],
                ),
            ],
        }
    )
    ctx = context(
        places=(place(), place("b", longitude=0.03), place("c"), place("d")),
        original_supply_ids=("a", "b", "c", "d"),
        route_evidence=(measured("WALK", 6000), measured("DRIVE", 6000)),
    )
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(
                update={
                    "requirements": ctx.contract.requirements.model_copy(update={"end_date": day2})
                }
            )
        }
    )
    scope = scope_for(original, ctx, check="coverage", dates=(DAY, day2), add_dates=(DAY, day2))
    bad = edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")
    good = edit(
        "12:00",
        "13:00",
        operation="add",
        activity_id=None,
        place_id="d",
        date=str(day2),
        start_time=f"{day2}T12:00:00+00:00",
        end_time=f"{day2}T13:00:00+00:00",
    )
    result = run(original=original, ctx=ctx, scope=scope, model=Model([bad, good]))
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert [c["status"] for c in result.components] == ["rejected", "accepted"]
    assert len(result.final.days[0].activities) == 1
    assert len(result.final.days[1].activities) == 2
    assert len(original.days[1].activities) == 1
    from backend.app.versions.v3.repair_feedback import learn

    learned = learn(result, RepairBudget(monotonic() + 600), 1)
    assert all(r["place_id"] != "d" for r in learned.conflict_records)
    assert any(r["place_id"] == "b" for r in learned.conflict_records)
    assert all(c["input_state_sha256"] and "budget_after" in c for c in result.components)


def test_preparation_reserve_is_cumulative_and_cache_does_not_charge():
    async def scenario():
        budget = RepairBudget(monotonic() + 600)

        async def send():
            return "route"

        budget.route_phase = "preparation"
        for i in range(16):
            budget.round_index = i % 5 + 1
            assert (
                await budget.call(("route", i), send, charges={"routes": 1, "elements": 1})
                == "route"
            )
        assert await budget.call(("route", 16), send, charges={"routes": 1, "elements": 1}) is None
        assert (
            await budget.call(("route", 0), send, charges={"routes": 1, "elements": 1}) == "route"
        )
        budget.route_phase = "post_proposal"
        for i in range(16, 24):
            assert (
                await budget.call(("route", i), send, charges={"routes": 1, "elements": 1})
                == "route"
            )
        assert budget.used["routes"] == 24 and budget.used["preparation_routes"] == 16
        assert await budget.call(("route", 24), send, charges={"routes": 1, "elements": 1}) is None

    asyncio.run(scenario())


def test_provider_transit_failure_falls_back_to_drive_without_retry():
    from backend.app.integrations.dispatch import mark_provider_send
    from backend.app.integrations.models import RouteMatrixDTO
    from backend.app.versions.v3.repair_transport import resolve_transfers

    class Provider:
        observes_send_boundary = True

        def __init__(self):
            self.calls = []

        async def compute_route_matrix(self, request):
            mark_provider_send()
            self.calls.append(request.travel_mode)
            if request.travel_mode == "TRANSIT":
                raise RuntimeError("fixture transit unavailable")
            return RouteMatrixDTO(
                retrieved_at="2026-09-25T00:00:00Z",
                elements=[
                    {
                        "originIndex": 0,
                        "destinationIndex": 0,
                        "condition": "ROUTE_EXISTS",
                        "status": {},
                        "duration": "1080s",
                        "distanceMeters": 4000,
                    }
                ],
            )

    async def scenario():
        original, ctx, provider = draft(), context(), Provider()
        proposal = draft([activity(), activity("new", "b", "12:00", "13:00")])
        scope = scope_for(original, ctx, check="coverage", add_dates=(DAY,))
        budget = RepairBudget(monotonic() + 600)
        final, extra = await resolve_transfers(
            original, proposal, scope, (measured("WALK", 4000),), ctx.places, provider, budget
        )
        assert provider.calls == ["TRANSIT", "DRIVE"]
        assert final.transfers[0].mode == "DRIVE"
        assert budget.used["routes"] == 2
        again, _ = await resolve_transfers(
            original,
            proposal,
            scope,
            (measured("WALK", 4000), *extra),
            ctx.places,
            provider,
            budget,
        )
        assert again.transfers == final.transfers and len(provider.calls) == 2

    asyncio.run(scenario())


def test_two_sided_modes_and_cumulative_reserve_burden():
    from backend.app.versions.v3.repair_spatial import check_addition_layout

    original, ctx = draft(), context(places=tuple(place(p) for p in "abcd"))
    visits = [
        activity(),
        activity("b", "b", "12:00", "13:00"),
        activity("c", "c", "14:00", "15:00"),
        activity("d", "d", "16:00", "17:00"),
    ]
    evidence = tuple(
        measured("DRIVE", 1500, a.source_place_id, b.source_place_id)
        for a, b in zip(visits, visits[1:], strict=False)
    )
    proposal = draft(visits)
    proposal.transfers = [
        route_option(a, b, "DRIVE", evidence, policy().spatial)
        for a, b in zip(visits, visits[1:], strict=False)
    ]
    layout = check_addition_layout(original, proposal, ctx.places, evidence, None, policy().spatial)
    assert layout["daily"][0]["added_minutes"] == 105
    assert "stage_cumulative_daily_added_burden" in layout["reasons"]
    evidence = (measured("DRIVE", 1080), measured("WALK", 600, "b", "c", distance=800))
    proposal = draft(visits[:3])
    proposal.transfers = [
        route_option(visits[0], visits[1], "DRIVE", evidence, policy().spatial),
        route_option(visits[1], visits[2], "WALK", evidence, policy().spatial),
    ]
    layout = check_addition_layout(original, proposal, ctx.places, evidence, None, policy().spatial)
    assert layout["accepted"] and [r["mode"] for r in layout["legs"]] == ["DRIVE", "WALK"]
    assert layout["daily"][0]["added_minutes"] == 38


def test_continuous_window_does_not_sum_fragments():
    from backend.app.versions.v3.repair_schedule import ScheduleState, TimeWindow

    left, right = activity(), activity("right", "b", "12:00", "13:00")
    fixed = TimeWindow(
        root_activity_id="rest",
        source="explicit_user",
        start=left.end_time + timedelta(minutes=20),
        end=left.end_time + timedelta(minutes=40),
    )
    schedule = ScheduleState(fixed=(fixed,))
    assert (
        route_option(left, right, "DRIVE", (measured("DRIVE", 1080),), policy().spatial, schedule)
        is None
    )
    assert (
        route_option(left, right, "DRIVE", (measured("DRIVE", 1080),), policy().spatial) is not None
    )


def test_independent_components_both_adopt_and_share_one_model_call():
    from backend.tests.versions.v3.test_repair import two_day_case

    original, ctx, scope = two_day_case((place(), place("b"), place("c"), place("d")))
    tomorrow = DAY + timedelta(days=1)
    model = Model(
        [
            edit("12:00", "13:00", operation="add", activity_id=None, place_id="b"),
            edit(
                "12:00",
                "13:00",
                operation="add",
                activity_id=None,
                place_id="c",
                date=str(tomorrow),
                start_time=f"{tomorrow}T12:00:00+00:00",
                end_time=f"{tomorrow}T13:00:00+00:00",
            ),
            edit(
                "14:00",
                "15:00",
                operation="add",
                activity_id=None,
                place_id="d",
                date=str(tomorrow),
                start_time=f"{tomorrow}T14:00:00+00:00",
                end_time=f"{tomorrow}T15:00:00+00:00",
            ),
        ]
    )
    result = run(original=original, ctx=ctx, scope=scope, model=model)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert model.calls == 1 and len(result.components) == 2
    assert all(c["status"] == "accepted" for c in result.components)


def test_same_day_invalid_member_keeps_component_atomic():
    original, ctx = draft(), context()
    model = Model(
        [
            edit("12:00", "13:00", operation="add", activity_id=None, place_id="b"),
            edit("14:00", "15:00", operation="add", activity_id=None, place_id="invented"),
        ]
    )
    result = run(
        original=original,
        ctx=ctx,
        scope=scope_for(original, ctx, check="coverage", add_dates=(DAY,)),
        model=model,
    )
    assert result.status == "REJECTED" and result.final == original
    assert len(result.components) == 1 and result.components[0]["status"] == "rejected"


def test_malformed_model_output_is_not_salvaged():
    model = Model(
        [
            edit("12:00", "13:00", operation="add", activity_id=None, place_id="b"),
            {"operation": "invented"},
        ]
    )
    original, ctx = draft(), context()
    result = run(
        original=original,
        ctx=ctx,
        scope=scope_for(original, ctx, check="coverage", add_dates=(DAY,)),
        model=model,
    )
    assert result.status == "REJECTED" and not result.components and result.parsed_patch is None
    assert result.final == original


def test_explicit_drive_preference_and_reserve_survive_revalidation():
    from backend.app.versions.v3.repair_routes import bind_transitions, check_transitions
    from backend.app.versions.v3.repair_transport import resolve_transfers

    async def scenario():
        original, ctx = draft(), context()
        proposal = draft([activity(), activity("new", "b", "11:35", "12:35")])
        scope = scope_for(
            original,
            ctx,
            check="coverage",
            add_dates=(DAY,),
            travel_mode="DRIVE",
            mode_source="USER_EXPLICIT",
            routing_preference="TRAFFIC_AWARE",
        )
        evidence = measured("DRIVE", 1680, departure=activity().end_time).model_copy(
            update={"routing_preference": "TRAFFIC_AWARE"}
        )
        final, _ = await resolve_transfers(
            original,
            proposal,
            scope,
            (evidence,),
            ctx.places,
            None,
            RepairBudget(monotonic() + 600),
        )
        binding = bind_transitions(final, "DRIVE", "TRAFFIC_AWARE")[0]
        assert binding.application_reserve_seconds == 600
        assert binding.routing_preference == "TRAFFIC_AWARE"
        check = list(check_transitions(final, (binding,), (evidence,)))[0]
        assert check["status"] == "CONFIRMED" and check["magnitude"] == 180
        assert (
            route_option(
                activity(), proposal.days[0].activities[1], "DRIVE", (evidence,), policy().spatial
            )
            is None
        )

    asyncio.run(scenario())


def test_policy_overrides_change_actual_route_window_without_relaxing_contract():
    import pytest
    from pydantic import ValidationError

    left, right = activity(), activity("b", "b", "11:35", "12:35")
    evidence = (measured("DRIVE", 1680),)
    assert route_option(left, right, "DRIVE", evidence, policy().spatial) is None
    assert (
        route_option(
            left, right, "DRIVE", evidence, policy(spatial={"drive_reserve_minutes": 0}).spatial
        )
        is not None
    )
    with pytest.raises(ValidationError):
        policy(acquisition={"routes": 3, "post_proposal_route_reserve": 4})
    with pytest.raises(ValidationError):
        policy(spatial={"drive_max_minutes": 0})
