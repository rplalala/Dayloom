"""Repair time allocation through real stage execution and controlled local-work cost."""

import asyncio
from contextlib import contextmanager

import pytest

from backend.app.versions.v3 import repair_service
from backend.tests.versions.v3.test_multiround import SequenceModel
from backend.tests.versions.v3.test_repair import (
    Model,
    Routes,
    context,
    edit,
    overlap_draft,
    scope_for,
)


def stage_with_local_cost(monkeypatch, build_cost, responses=None):
    now = [100.0]

    class TimedModel(SequenceModel):
        async def generate_repair_structured(self, **kwargs):
            value = await super().generate_repair_structured(**kwargs)
            if self.calls == 1:
                now[0] += 11
            return value

    model = TimedModel(responses if responses is not None else [[], [edit()]])
    build = repair_service.build_repair_input

    def timed_build(*args, **kwargs):
        value = build(*args, **kwargs)
        if model.calls == 1:
            now[0] += build_cost
        return value

    monkeypatch.setattr(repair_service, "build_repair_input", timed_build)
    original, ctx = overlap_draft(), context()
    result = asyncio.run(
        repair_service.run_repair_stage(
            original,
            ctx,
            scope_for(original, ctx),
            model=model,
            routes_provider=Routes(),
            request_deadline=1000,
            clock=lambda: now[0],
        )
    )
    return result, model


@pytest.mark.parametrize("build_cost,remaining", [(30.5, 318.5), (70, 279)])
def test_local_input_work_can_use_stage_time_beyond_the_reference_window(
    monkeypatch, build_cost, remaining
):
    result, model = stage_with_local_cost(monkeypatch, build_cost)
    assert result.status == "ACCEPTED_COMPLETE" and model.calls == 2
    assert result.selected_round_index == 2
    assert result.original == overlap_draft()
    timing = result.rounds[1].result.timing
    assert timing["stage_remaining_seconds"] == pytest.approx(remaining)
    assert timing["input_build_elapsed_seconds"] == pytest.approx(build_cost)
    assert timing["preparation_elapsed_seconds"] == pytest.approx(build_cost)
    assert timing["round_reference_deadline"] < timing["round_deadline"]
    assert timing["round_deadline"] == timing["round_started"] + 120
    assert 30 <= timing["model_timeout_seconds"] <= 70
    assert result.effective_policy["timing"]["stage_seconds"] == 360
    assert result.effective_policy["timing"]["round_reference_seconds"] == 60


@pytest.mark.parametrize("build_cost", [70.1, 121])
def test_local_input_work_cannot_spend_the_hard_model_or_recheck_allowance(monkeypatch, build_cost):
    result, model = stage_with_local_cost(monkeypatch, build_cost)
    assert result.status == "REJECTED" and model.calls == 1
    assert result.final == result.original == overlap_draft()
    last = result.rounds[-1].result
    assert last.status == "SKIPPED" and not last.model_attempted
    assert last.reason == "insufficient_time_for_model_and_rechecks"
    assert last.timing["model_available_seconds"] < 30
    assert last.timing["limiting_deadline"] == "round"


def test_later_local_time_shortage_preserves_the_best_retained_result(monkeypatch):
    result, model = stage_with_local_cost(monkeypatch, 70.1, [[edit("10:50", "11:50")], [edit()]])
    assert result.status == "ACCEPTED_PARTIAL" and model.calls == 1
    assert result.selected_round_index == 1
    assert result.final == result.rounds[0].adopted != result.original
    assert result.rounds[-1].result.status == "SKIPPED"


@pytest.mark.parametrize("request_deadline,expected_calls", [(159.9, 0), (160, 1)])
def test_short_request_preserves_nearby_and_exact_minimum_model_and_recheck_time(
    request_deadline, expected_calls
):
    original, ctx = overlap_draft(), context()
    model = Model()
    result = asyncio.run(
        repair_service.run_repair_stage(
            original,
            ctx,
            scope_for(original, ctx),
            model=model,
            routes_provider=Routes(),
            request_deadline=request_deadline,
            clock=lambda: 100,
        )
    )
    assert model.calls == expected_calls
    if expected_calls:
        assert result.status == "ACCEPTED_COMPLETE"
        timing = result.rounds[0].result.timing
        assert timing["stage_deadline"] == timing["round_deadline"] == 150
        assert timing["model_timeout_seconds"] == 30
        assert timing["limiting_deadline"] == "stage"
    else:
        assert result.status == "SKIPPED" and result.reason == "insufficient_stage_time"
        assert result.final == result.original == original


@pytest.mark.parametrize(
    "elapsed,reason",
    [(101, "insufficient_time_for_rechecks"), (121, "phase_deadline")],
)
def test_single_round_rejects_late_model_results_without_spending_recheck_reserve(elapsed, reason):
    now = [100.0]

    class LateModel(Model):
        async def generate_repair_structured(self, **kwargs):
            value = await super().generate_repair_structured(**kwargs)
            now[0] += elapsed
            return value

    original, ctx = overlap_draft(), context()
    model = LateModel()
    result = asyncio.run(
        repair_service.run_repair_once(
            original,
            ctx,
            scope_for(original, ctx),
            model=model,
            routes_provider=Routes(),
            request_deadline=1000,
            clock=lambda: now[0],
        )
    )
    assert result.status == "REJECTED" and result.reason == reason
    assert result.final == result.original == original
    assert model.calls == 1


def test_local_projection_work_rechecks_time_before_charging_or_calling_the_model(monkeypatch):
    from backend.app.observability import mechanism_observation

    now = [100.0]
    projection = mechanism_observation.model_projection

    @contextmanager
    def slow_projection(*args, **kwargs):
        with projection(*args, **kwargs):
            now[0] += 71
            yield

    monkeypatch.setattr(mechanism_observation, "model_projection", slow_projection)
    original, ctx = overlap_draft(), context()
    model = Model()
    result = asyncio.run(
        repair_service.run_repair_once(
            original,
            ctx,
            scope_for(original, ctx),
            model=model,
            routes_provider=Routes(),
            request_deadline=1000,
            clock=lambda: now[0],
        )
    )
    assert result.status == "SKIPPED" and not result.model_attempted
    assert model.calls == result.counters.get("model", 0) == 0
    assert result.reason == "insufficient_time_for_model_and_rechecks"
    assert result.timing["preparation_elapsed_seconds"] == 71
    assert result.final == original


@pytest.mark.parametrize("stage", [False, True])
def test_final_synchronous_revalidation_cannot_adopt_after_the_hard_deadline(monkeypatch, stage):
    from backend.app.versions.v3 import repair_spatial

    now = [100.0]
    spatial = repair_spatial.check_addition_layout

    def slow_final_spatial(*args, **kwargs):
        value = spatial(*args, **kwargs)
        if "check_rearrangements" not in kwargs:
            now[0] += 121
        return value

    monkeypatch.setattr(repair_spatial, "check_addition_layout", slow_final_spatial)
    original, ctx = overlap_draft(), context()
    model = Model()
    run = repair_service.run_repair_stage if stage else repair_service.run_repair_once
    result = asyncio.run(
        run(
            original,
            ctx,
            scope_for(original, ctx),
            model=model,
            routes_provider=Routes(),
            request_deadline=1000,
            clock=lambda: now[0],
        )
    )
    assert result.status == "REJECTED" and result.reason == "phase_deadline"
    assert result.final == result.original == original
    assert model.calls == 1
    if stage:
        assert len(result.rounds) == 1 and result.selected_round_index is None


@pytest.mark.parametrize("retain_partial", [False, True])
def test_timeout_after_patch_parsing_stops_without_another_send(monkeypatch, retain_partial):
    from backend.app.versions.v3 import repair_components

    accept = repair_components.accept_components
    calls = 0

    async def timeout_revalidation(*args, **kwargs):
        nonlocal calls
        value = await accept(*args, **kwargs)
        calls += 1
        if calls == (2 if retain_partial else 1):
            raise TimeoutError("controlled_outer_round_timeout")
        return value

    monkeypatch.setattr(repair_components, "accept_components", timeout_revalidation)
    original, ctx = overlap_draft(), context()
    model = SequenceModel([[edit("10:50", "11:50")], [edit()]] if retain_partial else [[edit()]])
    result = asyncio.run(
        repair_service.run_repair_stage(
            original,
            ctx,
            scope_for(original, ctx),
            model=model,
            routes_provider=Routes(),
            request_deadline=1000,
            clock=lambda: 100,
        )
    )
    assert result.reason == "repair_timeout"
    assert model.calls == len(result.rounds) == (2 if retain_partial else 1)
    assert result.rounds[-1].result.parsed_patch is not None
    assert result.rounds[-1].continuation_reason == "repair_timeout"
    if retain_partial:
        assert result.status == "ACCEPTED_PARTIAL" and result.selected_round_index == 1
        assert result.final == result.rounds[0].adopted != original
    else:
        assert result.status == "REJECTED" and result.final == original
