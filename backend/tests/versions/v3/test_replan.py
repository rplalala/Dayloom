"""Affected-day replanning through the production Repair stage and strict wire."""

import asyncio
import json
from datetime import timedelta
from time import monotonic

import pytest

from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_models import RepairScope
from backend.app.versions.v3.repair_service import run_repair_stage
from backend.tests.versions.v3.test_multiround import SequenceModel, policy
from backend.tests.versions.v3.test_repair import Routes, edit
from backend.tests.versions.v3.test_repair_search import move, scenario
from backend.tests.versions.v3.test_validation import DAY


class StrategyModel(SequenceModel):
    def __init__(self, responses):
        super().__init__(responses)
        self.systems = []

    async def generate_repair_structured(self, **kwargs):
        self.systems.append(kwargs["system_prompt"])
        return await super().generate_repair_structured(**kwargs)


def linked_scenario():
    original, ctx, _ = scenario((3, 2, 2))
    a = original.days[0].activities[2]
    a.start_time = a.start_time.replace(hour=9, minute=30)
    a.end_time = a.end_time.replace(hour=10, minute=30)
    report = assess(original, ctx)
    scope = RepairScope(
        dates=tuple(d.date for d in original.days),
        target_ids=tuple(f.finding_id for f in report.findings if f.check == "overlap"),
        permissions=(
            dict(
                activity_id="d0_2",
                operations={"move"},
                source_date=DAY,
                move_dates=(DAY + timedelta(days=1),),
            ),
            dict(activity_id="d1_0", operations={"retime"}),
            dict(activity_id="d2_0", operations={"retime"}),
        ),
    )
    return original, ctx, scope


def linked_patch():
    return [
        move("d0_2", 1, "09:30", "10:30"),
        edit(
            activity_id="d1_0",
            date=str(DAY + timedelta(days=1)),
            start_time=f"{DAY + timedelta(days=1)}T07:00:00+00:00",
            end_time=f"{DAY + timedelta(days=1)}T08:00:00+00:00",
        ),
    ]


def run(model, *, settings=None, routes=None, inputs=None, **kwargs):
    original, ctx, scope = inputs or linked_scenario()
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=model,
            routes_provider=routes or Routes(),
            request_deadline=monotonic() + 600,
            policy=settings or policy(max_model_calls=2),
            **kwargs,
        )
    )
    return result, original


def test_local_nonprogress_replans_linked_dates_and_preserves_unaffected_day():
    model = StrategyModel([[], linked_patch()])
    result, original = run(model)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert [r.strategy for r in result.rounds] == ["local", "replan"]
    assert [len(d.activities) for d in result.final.days] == [2, 3, 2]
    assert result.final.days[2] == original.days[2]
    assert result.original == original
    assert result.counters["model"] == model.calls == 2
    assert model.systems[1] != model.systems[0]
    arrangement = model.inputs[1]["affected_day_replan"]
    assert arrangement["affected_dates"] == [str(DAY), str(DAY + timedelta(days=1))]
    assert arrangement["unaffected_dates"] == [str(DAY + timedelta(days=2))]
    assert len(arrangement["days"]) == 2
    assert {p["activity_id"] for p in model.inputs[1]["scope"]["permissions"]} == {
        "d0_2",
        "d1_0",
    }
    before = {a.activity_id: a for d in original.days for a in d.activities}
    after = {a.activity_id: a for d in result.final.days for a in d.activities}
    assert before.keys() == after.keys()
    assert all(before[i].source_place_id == after[i].source_place_id for i in before)
    assert all(
        before[i].end_time - before[i].start_time == after[i].end_time - after[i].start_time
        for i in before
    )


@pytest.mark.parametrize("change", ["unaffected", "protected", "identity", "duration"])
def test_replan_preserves_scope_identity_and_duration(change):
    patch = linked_patch()
    if change == "unaffected":
        patch = [
            edit(
                activity_id="d2_0",
                date=str(DAY + timedelta(days=2)),
                start_time=f"{DAY + timedelta(days=2)}T07:00:00+00:00",
                end_time=f"{DAY + timedelta(days=2)}T08:00:00+00:00",
            )
        ]
    elif change == "protected":
        patch[1]["activity_id"] = "d1_1"
    elif change == "identity":
        patch[0]["place_id"] = "fabricated"
    else:
        patch[0]["end_time"] = f"{DAY + timedelta(days=1)}T11:30:00+00:00"
    result, original = run(StrategyModel([[], patch]))
    assert result.rounds[-1].strategy == "replan"
    assert result.final == original
    assert not result.rounds[-1].exploration_transition


def test_replan_checks_new_route_and_reuses_preparation_evidence():
    routes = Routes()
    result, _ = run(StrategyModel([[], linked_patch()]), routes=routes)
    assert result.status == "ACCEPTED_COMPLETE"
    assert result.counters["routes"] == len(routes.calls)
    keys = [
        (tuple(r.origins), tuple(r.destinations), r.travel_mode, r.departure_time)
        for r in routes.calls
    ]
    assert len(keys) == len(set(keys))
    assert any(
        r.origins[0].place_id == "d1_0" and r.destinations[0].place_id == "d0_2"
        for r in routes.calls
    )
    assert any(
        r.origins[0].place_id == "d0_2" and r.destinations[0].place_id == "d1_1"
        for r in routes.calls
    )


def test_unsupported_new_route_cannot_adopt_linked_replan():
    original, ctx, scope = linked_scenario()
    scope = scope.model_copy(update={"travel_mode": "TRANSIT"})
    result, original = run(
        StrategyModel([[], linked_patch()]), routes=Routes(fail=True), inputs=(original, ctx, scope)
    )
    assert result.final == original
    assert result.rounds[-1].strategy == "replan"
    assert not result.rounds[-1].exploration_transition


def test_six_shared_sends_include_real_replan_and_do_not_reset_budget():
    model = StrategyModel([[], [], [], [], [], linked_patch()])
    result, _ = run(model, settings=policy())
    assert result.status == "ACCEPTED_COMPLETE"
    assert result.counters["model"] == model.calls == 6
    assert [r.strategy for r in result.rounds] == ["local"] + ["replan"] * 5
    assert all("affected_day_replan" in p for p in model.inputs[1:])


@pytest.mark.parametrize("failure", [RuntimeError("offline model failure"), {"days": []}])
def test_replan_terminal_failure_retains_earlier_publishable_improvement(failure):
    from backend.tests.versions.v3.test_repair import context, overlap_draft, scope_for

    class Terminal(StrategyModel):
        async def generate_repair_structured(self, **kwargs):
            if self.calls == 2 and isinstance(failure, dict):
                self.inputs.append(json.loads(kwargs["user_prompt"]))
                self.calls += 1
                return failure
            return await super().generate_repair_structured(**kwargs)

    original, ctx = overlap_draft(), context()
    model = Terminal([[edit("10:50", "11:50")], [], failure])
    result, _ = run(model, settings=policy(), inputs=(original, ctx, scope_for(original, ctx)))
    assert result.final == result.rounds[0].adopted != original
    assert [r.strategy for r in result.rounds] == ["local", "local", "replan"]
    assert result.reason == "model_failed_no_retry"
    assert result.selected_round_index == 1
    assert model.calls == result.counters["model"] == 3


def test_replan_strict_wire_uses_short_references_and_rejects_replacement_itinerary():
    from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
    from backend.app.llm.client import StructuredOutputError

    model = StrategyModel([[], linked_patch()])
    run(model)
    calls = []

    class Chat:
        def with_structured_output(self, schema, **options):
            calls.append((schema, options))
            return self

        async def ainvoke(self, messages):
            payload = json.loads(messages[1].content)
            assert "Replan the affected date group" in messages[0].content
            assert payload["affected_day_replan"]["days"][0]["activities"][0][
                "activity_id"
            ].startswith("a")
            assert all(
                a["source_place_id"].startswith("p")
                for day in payload["affected_day_replan"]["days"]
                for a in day["activities"]
            )
            return {"days": []}

    client = object.__new__(AzureFoundryStructuredLLMClient)
    client._chat_model = Chat()
    with pytest.raises(StructuredOutputError):
        asyncio.run(
            client.generate_repair_structured(
                system_prompt=model.systems[1],
                user_prompt=json.dumps(model.inputs[1]),
            )
        )
    assert calls[0][1]["strict"] is True
    assert calls[0][0]["additionalProperties"] is False


def test_replan_qualifies_bounded_new_alternative_after_old_options_do_not_advance():
    from backend.tests.services.test_poi_semantics import service
    from backend.tests.versions.v3.test_repair import (
        CandidateSearch,
        addition_scope,
        discovery_context,
        draft,
        place,
        with_hours,
    )

    original = draft()
    ctx = discovery_context(places=(place(), with_hours("b"), with_hours("c")))
    provider = CandidateSearch()
    semantics = service()
    model = StrategyModel(
        [[], [], [edit("12:00", "13:00", operation="add", activity_id=None, place_id="fresh")]]
    )
    result, _ = run(
        model,
        settings=policy(max_model_calls=3),
        inputs=(original, ctx, addition_scope(original, ctx)),
        places_provider=provider,
        intent_ids=("discovery_1",),
        semantic_service=semantics,
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.rounds[0].result.counters.get("google", 0) == 0
    assert result.rounds[1].strategy == "replan"
    assert provider.searches == result.counters["google"] == 1
    assert provider.calls == result.counters["details"] == 1
    assert semantics.ledger["fresh"].main_eligible
    assert result.final_place_ids == ("a", "fresh")
    assert result.original_supply_ids == ("a", "b", "c")


def test_replan_preserves_existing_conservative_walk_policy_and_unknown_status():
    result, _ = run(StrategyModel([[], linked_patch()]), routes=Routes(fail=True))
    assert result.status == "ACCEPTED_COMPLETE"
    assert any(
        row["basis"] == "policy_reserve_route_unknown"
        for row in result.rounds[-1].result.spatial["legs"]
    )
    assert any(f.check == "route" and f.status == "UNKNOWN" for f in result.adopted_report.findings)


def test_replan_retiming_requires_supported_motor_route_at_actual_departure():
    from backend.tests.versions.v3.test_repair import context, overlap_draft, scope_for

    original, ctx = overlap_draft(), context()
    scope = scope_for(original, ctx, travel_mode="TRANSIT")
    result, _ = run(
        StrategyModel([[], [edit()]]), routes=Routes(fail=True), inputs=(original, ctx, scope)
    )
    assert result.final == original
    assert "explicit_motor_mode_requires_route_evidence" in result.rounds[-1].result.reason


def test_replan_cannot_chain_moves_beyond_original_date_permission():
    original, ctx, scope = scenario()
    scope = scope.model_copy(
        update={
            "permissions": tuple(
                p.model_copy(update={"operations": p.operations - {"delete"}})
                for p in scope.permissions
            )
        }
    )
    model = StrategyModel([[move("d0_2", 1)], [], [move("d0_2", 2)]])
    result, _ = run(model, settings=policy(max_model_calls=3), inputs=(original, ctx, scope))
    assert result.rounds[0].exploration_transition
    assert result.rounds[-1].strategy == "replan"
    assert not result.rounds[-1].exploration_transition
    assert result.final == original
    assert "original adjacent-date" in result.rounds[-1].result.reason


def test_new_replan_identity_without_semantic_admission_is_not_publishable():
    from backend.tests.services.test_poi_semantics import Model, service
    from backend.tests.versions.v3.test_repair import (
        CandidateSearch,
        addition_scope,
        discovery_context,
        draft,
        place,
        with_hours,
    )

    def uncertain_new_roles(rows):
        for row in rows:
            if row["visit_object"].startswith("fresh"):
                row["role"] = "unresolved"

    original = draft()
    ctx = discovery_context(places=(place(), with_hours("b"), with_hours("c")))
    semantics = service(Model(uncertain_new_roles))
    model = StrategyModel(
        [[], [], [edit("12:00", "13:00", operation="add", activity_id=None, place_id="fresh")]]
    )
    result, _ = run(
        model,
        settings=policy(max_model_calls=3),
        inputs=(original, ctx, addition_scope(original, ctx)),
        places_provider=CandidateSearch(),
        intent_ids=("discovery_1",),
        semantic_service=semantics,
    )
    assert result.final == original
    assert not semantics.ledger["fresh"].main_eligible
    assert result.rounds[-1].strategy == "replan"
    assert "not a presented" in result.rounds[-1].result.reason


def test_replan_cancellation_propagates_and_deadline_does_not_allow_extra_send():
    model = StrategyModel([[], asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        run(model)
    assert model.calls == 2

    now = [0.0]

    class Expiring(StrategyModel):
        async def generate_repair_structured(self, **kwargs):
            reply = await super().generate_repair_structured(**kwargs)
            if self.calls == 2:
                now[0] = 359.0
            return reply

    model = Expiring([[], linked_patch(), linked_patch()])
    result, original = run(model, settings=policy(), clock=lambda: now[0])
    assert result.final == original
    assert result.counters["model"] == model.calls == 2
    assert result.rounds[-1].strategy == "replan"
    assert result.reason == result.rounds[-1].result.reason == "phase_deadline"
    assert result.rounds[-1].result.timing["round_remaining_seconds"] == 0
