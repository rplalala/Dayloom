"""Feedback rounds, policy wiring and spatial evidence without external services."""

import asyncio
import json
from time import monotonic

import pytest
from pydantic import ValidationError

from backend.app.runtime.config_loader import load_runtime_config
from backend.app.runtime.config_models import RuntimeConfig, V3RepairConfig
from backend.app.versions.v3.repair_service import run_repair_stage
from backend.app.versions.v3.repair_spatial import check_addition_layout
from backend.tests.versions.v3.test_repair import (
    DAY,
    Model,
    Routes,
    activity,
    context,
    draft,
    edit,
    overlap_draft,
    place,
    scope_for,
)


def policy(**changes):
    data = load_runtime_config().v3_repair.model_dump()
    for key, value in changes.items():
        if isinstance(value, dict):
            data[key].update(value)
        else:
            data[key] = value
    return V3RepairConfig.model_validate(data)


class SequenceModel(Model):
    def __init__(self, responses):
        super().__init__()
        self.responses = responses
        self.inputs = []

    async def generate_repair_structured(self, **kwargs):
        self.inputs.append(json.loads(kwargs["user_prompt"]))
        value = self.responses[self.calls]
        self.calls += 1
        if isinstance(value, BaseException):
            raise value
        return {"edits": value}


def stage(model, original=None, ctx=None, scope=None, **kwargs):
    original = original if original is not None else overlap_draft()
    ctx = ctx if ctx is not None else context()
    return asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope or scope_for(original, ctx),
            model=model,
            request_deadline=monotonic() + 600,
            **kwargs,
        )
    )


def test_rejection_feedback_allows_another_proposal_with_unchanged_materials():
    model = SequenceModel([[], [edit()]])
    result = stage(model, routes_provider=Routes())
    assert result.status == "ACCEPTED_COMPLETE"
    assert len(result.rounds) == 2 and model.calls == 2
    assert model.inputs[0]["feedback"] is None
    assert result.reason == "authorized_targets_complete"
    assert result.counters.get("details", 0) == 0
    assert result.original == overlap_draft()
    assert result.rounds[0].result.status == "REJECTED"


def test_later_provider_failure_preserves_partial_improvement():
    model = SequenceModel([[edit("10:50", "11:50")], RuntimeError("offline failure")])
    result = stage(model)
    assert result.status == "ACCEPTED_PARTIAL"
    assert result.final == result.rounds[0].adopted
    assert result.final != result.original
    assert result.target_progress[0].outcome == "improved"
    assert result.rounds[1].result.status == "REJECTED"
    assert result.reason == "model_failed_no_retry"
    assert result.adopted_report is not result.rounds[1].result.proposed_report


def test_repeated_failed_patch_does_not_exhaust_other_operations():
    unchanged = [edit("10:30", "11:30")]
    model = SequenceModel([unchanged, unchanged, unchanged, [edit()]])
    result = stage(model, routes_provider=Routes())
    assert model.calls == 4
    assert result.rounds[2].result.reason == "equivalent_proposal_suppressed"
    assert result.status == "ACCEPTED_COMPLETE"
    assert result.final != result.original


def test_configured_model_round_limit_changes_real_execution():
    model = SequenceModel([[], [edit()]])
    result = stage(model, policy=policy(max_rounds=1, max_model_calls=1))
    assert model.calls == 1 and result.status == "REJECTED"
    disabled = stage(SequenceModel([]), policy=policy(max_model_calls=0))
    assert disabled.status == "SKIPPED" and not disabled.model_attempted


def test_cancel_propagates_after_partial_adoption():
    model = SequenceModel([[edit("10:50", "11:50")], asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        stage(model)
    assert model.calls == 2


def test_unknown_candidate_addition_keeps_unknown_facts():
    original, ctx = draft(), context()
    scope = scope_for(original, ctx, check="coverage", add_dates=(DAY,))
    model = SequenceModel(
        [[edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")]]
    )
    result = stage(model, original, ctx, scope)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert any(f.status == "UNKNOWN" and "b" in f.place_ids for f in result.adopted_report.findings)
    assert result.rounds[0].result.spatial["legs"][0]["basis"] == "policy_reserve_route_unknown"
    assert not result.rounds[0].result.spatial["legs"][0]["time_verified"]


def layout(original, proposed, places=None, evidence=(), mode=None, spatial=None):
    return check_addition_layout(
        original,
        proposed,
        places or (place(), place("b"), place("c"), place("d")),
        evidence,
        mode,
        spatial or policy().spatial,
    )


def test_untimed_walk_measurement_is_used_but_not_future_verified():
    from backend.app.versions.v3.repair_budget import RepairBudget
    from backend.app.versions.v3.repair_routes import acquire_transitions, bind_transitions

    original = draft()
    proposed = draft([activity(), activity("new", "b", "11:20", "12:20")])
    provider = Routes(duration=600)
    evidence = asyncio.run(
        acquire_transitions(
            proposed,
            bind_transitions(proposed, "WALK"),
            (),
            (place(), place("b")),
            provider,
            RepairBudget(monotonic() + 600),
        )
    )
    assert len(provider.calls) == 1 and provider.calls[0].departure_time is None
    checked = layout(original, proposed, evidence=evidence, mode="WALK")
    assert checked["accepted"]
    assert checked["legs"][0]["basis"] == "walk_provider_estimate"
    assert not checked["legs"][0]["time_verified"]
    missing = layout(original, proposed)
    assert not missing["accepted"]
    assert missing["legs"][0]["basis"] == "policy_reserve_route_unknown"


def test_geographic_policy_rejects_far_addition_even_with_large_time_gap():
    original = draft()
    proposed = draft([activity(), activity("new", "b", "15:00", "16:00")])
    checked = layout(original, proposed, (place(), place("b", latitude=1)))
    assert not checked["accepted"]
    assert "automatic_geographic_range" in checked["reasons"]


def test_blank_day_group_cannot_be_far_apart():
    original = draft([])
    proposed = draft([activity(), activity("new", "b", "15:00", "16:00")])
    checked = layout(original, proposed, (place(), place("b", latitude=1)))
    assert "blank_day_group_range" in checked["reasons"]


def test_daily_burden_is_stage_cumulative_not_current_round():
    original = draft()
    first = draft([activity(), activity("r1", "b", "12:00", "13:00")])
    final = draft(
        [
            *first.days[0].activities,
            activity("r2", "c", "14:00", "15:00"),
            activity("r3", "d", "16:00", "17:00"),
        ]
    )
    assert layout(original, first)["accepted"]
    checked = layout(original, final)
    assert checked["daily"][0]["added_minutes"] == 135
    assert "stage_cumulative_daily_added_burden" in checked["reasons"]


def test_unknown_baseline_does_not_earn_fictional_credit():
    original = draft([activity(), activity("last", "c", "15:00", "16:00")])
    proposed = draft(
        [
            original.days[0].activities[0],
            activity("new", "b", "12:00", "13:00"),
            original.days[0].activities[1],
        ]
    )
    checked = layout(original, proposed)
    assert checked["accepted"]
    assert checked["daily"][0]["added_minutes"] == 90
    assert checked["daily"][0]["baseline_credits"][0]["minutes"] is None


def test_runtime_spatial_value_changes_actual_policy_result():
    proposed = draft([activity(), activity("new", "b", "12:00", "13:00")])
    assert layout(draft(), proposed)["accepted"]
    assert not layout(
        draft(), proposed, spatial=policy(spatial={"daily_added_minutes": 30}).spatial
    )["accepted"]


@pytest.mark.parametrize(
    "change",
    [
        {"max_rounds": 7},
        {"acquisition": {"canonical": 31}},
        {"timing": {"stage_seconds": 421}},
        {"timing": {"round_seconds": 151}},
        {"timing": {"preparation_seconds": 61}},
        {"max_rounds": True},
        {"max_model_calls": -1},
        {"timing": {"model_seconds": 0}},
        {"timing": {"round_seconds": 20}},
        {"input": {"identity_capacity": 33}},
        {"input": {"input_tokens": 10}},
        {"input": {"input_tokens": 252001}},
        {"acquisition": {"google": 0}},
        {"acquisition": {"routes": 0}},
        {"spatial": {"fallback_distance_km": 3}},
        {"spatial": {"max_leg_minutes": float("inf")}},
    ],
)
def test_invalid_policy_fails_explicitly(change):
    with pytest.raises(ValidationError):
        policy(**change)


def test_runtime_yaml_snapshot_round_trips_and_v0_defaults_remain():
    config = load_runtime_config()
    assert RuntimeConfig.model_validate(config.model_dump()) == config
    assert config.v3_repair.quantity_review_enabled is True
    assert config.main_generation.input_tokens == 252000
    assert config.budget.final_pois == 20


def test_blank_day_two_rounds_use_unique_ids_and_current_candidate_groups():
    original, ctx = draft([]), context()
    ctx = ctx.model_copy(
        update={"contract": ctx.contract.model_copy(update={"time_protections": ()})}
    )
    scope = scope_for(original, ctx, check="coverage", add_dates=(DAY,))
    model = SequenceModel(
        [
            [edit("10:00", "11:00", operation="add", activity_id=None, place_id="a")],
            [edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")],
        ]
    )
    result = stage(model, original, ctx, scope)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert len(result.rounds) == 2
    assert {a.activity_id for d in result.final.days for a in d.activities} == {
        "repair_r1_new_1",
        "repair_r2_new_1",
    }
    assert "a" not in {c["place_id"] for c in model.inputs[1]["addition_candidates"]}
    assert result.rounds[1].target_links


def test_budget_settings_control_sends_and_nearby_reserve_without_round_reset():
    from backend.app.versions.v3.repair_budget import RepairBudget

    async def scenario():
        p = policy(acquisition={"routes": 1, "elements": 1, "post_proposal_route_reserve": 0})
        budget = RepairBudget(500, clock=lambda: 100, policy=p, nearby_reserve=7)
        assert budget.deadline == 493
        shorter = policy(timing={"stage_seconds": 150})
        assert RepairBudget(500, clock=lambda: 100, policy=shorter).deadline == 250
        sends = []

        async def send():
            sends.append(1)
            return "value"

        for _ in range(3):
            assert (
                await budget.call(("leg", 1), send, charges={"routes": 1, "elements": 1}) == "value"
            )
        assert await budget.call(("leg", 2), send, charges={"routes": 1, "elements": 1}) is None
        assert len(sends) == 1 and budget.used["cache_hits"] == 2
        assert budget.used["routes"] == budget.used["elements"] == 1
        assert RepairBudget(150, clock=lambda: 100, policy=p, nearby_reserve=7).deadline == 143

    asyncio.run(scenario())


def test_insertion_checks_two_sides_and_detour_increment():
    ps = (place(), place("b", longitude=0.008), place("c", latitude=0.008, longitude=0.004))
    original = draft([activity(), activity("last", "b", "15:00", "16:00")])
    proposed = draft(
        [
            original.days[0].activities[0],
            activity("new", "c", "12:00", "13:00"),
            original.days[0].activities[1],
        ]
    )
    checked = layout(original, proposed, ps)
    assert len(checked["legs"]) == 2
    assert "automatic_insertion_detour" in checked["reasons"]


def test_required_remote_addition_is_not_deleted_by_default_compactness():
    original = draft()
    proposed = draft([activity(), activity("required", "b", "15:00", "16:00")])
    checked = check_addition_layout(
        original,
        proposed,
        (place(), place("b", latitude=1)),
        (),
        None,
        policy().spatial,
        required={"b"},
    )
    assert checked["accepted"]
    assert len(proposed.days[0].activities) == 2


def test_actual_graph_feedback_rounds_then_nearby_once(monkeypatch):
    from backend.app.services.reference_discovery import ReferenceDiscoveryService
    from backend.tests.versions.v3.test_wiring import Model as GraphModel
    from backend.tests.versions.v3.test_wiring import execute

    calls = []
    real = ReferenceDiscoveryService.discover

    async def observed(*args, **kwargs):
        calls.append(1)
        return await real(*args, **kwargs)

    monkeypatch.setattr(ReferenceDiscoveryService, "discover", observed)

    class FeedbackGraphModel(GraphModel):
        async def generate_repair_structured(self, **kwargs):
            if self.repair_calls == 0:
                self.repair_calls += 1
                return {"edits": []}
            assert json.loads(kwargs["user_prompt"])["feedback"]["previous_status"] == "REJECTED"
            return await super().generate_repair_structured(**kwargs)

    result, model, _, owner = asyncio.run(execute(FeedbackGraphModel()))
    assert result.v3.repair.status == "ACCEPTED_COMPLETE"
    assert result.v3.repair.reason == "authorized_targets_complete"
    assert model.repair_calls == 2 and len(model.calls) == 1
    assert len(calls) == 1 and owner.closes == 1


def test_yaml_round_limit_reaches_actual_runner(tmp_path):
    import yaml

    from backend.app.runtime.config_loader import load_runtime_config_file
    from backend.tests.versions.v3.test_wiring import Model as GraphModel
    from backend.tests.versions.v3.test_wiring import execute

    data = load_runtime_config().model_dump(mode="json")
    data["v3_repair"].update(max_rounds=1, max_model_calls=1, quantity_review_enabled=True)
    path = tmp_path / "runtime.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    result, model, _, _ = asyncio.run(
        execute(
            GraphModel(behavior="empty"),
            runtime_config=load_runtime_config_file(path),
            quantity_review_enabled=None,
        )
    )
    assert model.repair_calls == 1 and result.v3.quantity_review_enabled


def test_cli_review_override_precedence_is_explicit(monkeypatch):
    from backend.app.versions.v1 import runner
    from backend.app.versions.v3.runner import main

    observed = []

    def fake_main(argv, **kwargs):
        observed.append(kwargs["planner_runner"].keywords["quantity_review_enabled"])
        return 0

    monkeypatch.setattr(runner, "main", fake_main)
    assert (
        main([]) == main(["--repair-quantity-review"]) == main(["--no-repair-quantity-review"]) == 0
    )
    assert observed == [None, True, False]


def test_config_documentation_lists_every_yaml_leaf_and_value():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[4]
    data = yaml.safe_load((root / "config/runtime.yaml").read_text(encoding="utf-8"))
    documentation = (root / "config/README.md").read_text(encoding="utf-8")

    def check(value, path=""):
        for key, item in value.items():
            full = f"{path}.{key}" if path else key
            if isinstance(item, dict):
                check(item, full)
            else:
                assert f"| `{full}` | `{json.dumps(item)}` |" in documentation

    check(data)


def test_actual_usage_is_cumulative_and_missing_values_remain_explicit():
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, LLMResult

    class UsageModel(SequenceModel):
        async def generate_repair_structured(self, **kwargs):
            kwargs["usage_callback"].on_llm_end(
                LLMResult(
                    generations=[
                        [
                            ChatGeneration(
                                message=AIMessage(
                                    content="",
                                    response_metadata={"model_name": "fixture-model"},
                                    usage_metadata={
                                        "input_tokens": 10,
                                        "output_tokens": 3,
                                        "total_tokens": 13,
                                    },
                                )
                            )
                        ]
                    ]
                )
            )
            return await super().generate_repair_structured(**kwargs)

    result = stage(UsageModel([[edit("10:50", "11:50")], [edit()]]))
    assert result.usage["fixture-model"]["total_tokens"] == 26
    assert [r.usage["fixture-model"]["total_tokens"] for r in result.rounds] == [13, 13]
    assert result.usage_status == "reported"
    assert all(r.result.timing["model_timeout_seconds"] <= 70 for r in result.rounds)


def test_configured_routes_stage_allowance_does_not_reset_between_rounds():
    original, ctx = overlap_draft(), context()
    scope = scope_for(original, ctx, travel_mode="TRANSIT")
    provider = Routes(duration=1)
    result = stage(
        SequenceModel([[], [edit("12:00", "13:00")]]),
        original,
        ctx,
        scope,
        routes_provider=provider,
        policy=policy(acquisition={"routes": 1, "elements": 1, "post_proposal_route_reserve": 0}),
    )
    assert len(result.rounds) == 2
    assert len(provider.calls) == result.counters["routes"] == result.counters["elements"] == 1


def test_explicit_unsupported_transport_is_not_replaced_by_walk_fallback():
    original, ctx = draft(), context()
    scope = scope_for(original, ctx, check="coverage", add_dates=(DAY,)).model_copy(
        update={"unsupported_explicit_mode": "BICYCLE"}
    )
    model = SequenceModel(
        [[edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")]] * 2
    )
    result = stage(model, original, ctx, scope)
    assert result.status == "SKIPPED"
    assert result.reason == "explicit_transport_mode_not_supported"
    assert model.calls == 0


def test_splitting_confirmed_route_cannot_hide_it_in_unknown_new_legs():
    from backend.app.versions.v3.repair_acceptance import assess, compare
    from backend.app.versions.v3.repair_routes import bind_transitions
    from backend.tests.versions.v3.test_repair import route

    original = overlap_draft()
    ctx = context(
        route_evidence=(route(duration=14400),), transitions=bind_transitions(original, "TRANSIT")
    )
    initial = assess(original, ctx)
    scope = scope_for(original, ctx)
    proposed = draft(
        [
            activity(),
            activity("inserted", "c", "12:00", "13:00"),
            activity("two", "b", "15:00", "16:00"),
        ]
    )
    after = assess(proposed, ctx, transitions=bind_transitions(proposed, "TRANSIT"))
    comparison = compare(original, proposed, initial, initial, after, scope)
    assert not comparison.accepted
    assert "unverified chain" in comparison.reason
