"""Repair time allocation through real stage execution and controlled local-work cost."""

import asyncio
from contextlib import asynccontextmanager, contextmanager

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


def test_approved_timing_policy_retains_model_and_recheck_reserves():
    from backend.app.runtime.config_loader import load_runtime_config

    runtime = load_runtime_config()
    timing = runtime.v3_repair.timing
    assert (timing.stage_seconds, timing.round_seconds) == (420, 150)
    assert (timing.round_reference_seconds, timing.preparation_seconds) == (120, 60)
    assert (timing.model_seconds, timing.minimum_model_seconds) == (70, 30)
    assert timing.recheck_reserve_seconds == 20
    assert runtime.development_timeout_seconds == 600
    assert runtime.poi_semantics.call_timeout_seconds == 45
    assert runtime.poi_semantics.total_seconds == 120


@pytest.mark.parametrize("legacy,model_elapsed", [(True, 22), (False, 22), (False, 44)])
def test_semantic_preparation_window_through_real_repair_stage(monkeypatch, legacy, model_elapsed):
    from backend.app.services import poi_semantics
    from backend.tests.services.test_poi_semantics import Model as SemanticModel
    from backend.tests.services.test_poi_semantics import service
    from backend.tests.versions.v3.test_multiround import policy

    now = [100.0]

    @asynccontextmanager
    async def controlled_timeout(seconds):
        deadline = now[0] + seconds
        yield
        if now[0] > deadline:
            raise TimeoutError("Controlled deadline elapsed")

    count_input = poi_semantics.semantic_input_tokens

    def local_input_work(*args):
        tokens = count_input(*args)
        now[0] += 8
        return tokens

    class TimedSemanticModel(SemanticModel):
        async def generate_poi_semantics_structured(self, **kwargs):
            now[0] += model_elapsed
            return await super().generate_poi_semantics_structured(**kwargs)

    monkeypatch.setattr(asyncio, "timeout", controlled_timeout)
    monkeypatch.setattr(poi_semantics, "semantic_input_tokens", local_input_work)
    semantic_service = service(TimedSemanticModel())
    semantic_service.clock = lambda: now[0]
    timing = (
        dict(
            stage_seconds=360, round_seconds=120, round_reference_seconds=60, preparation_seconds=45
        )
        if legacy
        else {}
    )
    original, ctx = overlap_draft(), context()
    model = Model()
    call = repair_service.run_repair_stage(
        original,
        ctx,
        scope_for(original, ctx),
        model=model,
        routes_provider=Routes(),
        request_deadline=1000,
        clock=lambda: now[0],
        policy=policy(timing=timing),
        semantic_service=semantic_service,
    )
    if legacy:
        with pytest.raises(poi_semantics.SemanticAssessmentError):
            asyncio.run(call)
        assert model.calls == 0 and not semantic_service.ledger
        assert semantic_service.records[0]["timeout_seconds"] == 2
        assert semantic_service.records[0]["limiting_deadline"] == "caller"
    else:
        result = asyncio.run(call)
        assert result.status == "ACCEPTED_COMPLETE", result.reason
        assert model.calls == 1
        assert semantic_service.records[0]["timeout_seconds"] == 45
        assert semantic_service.records[0]["limiting_deadline"] == "call"
        assert result.rounds[0].result.timing["model_timeout_seconds"] <= 70


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


@pytest.mark.parametrize("build_cost,remaining", [(30.5, 378.5), (70, 339)])
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
    assert timing["round_deadline"] == timing["round_started"] + 150
    assert 30 <= timing["model_timeout_seconds"] <= 70
    assert result.effective_policy["timing"]["stage_seconds"] == 420
    assert result.effective_policy["timing"]["round_reference_seconds"] == 120


@pytest.mark.parametrize("build_cost", [100.1, 151])
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
    result, model = stage_with_local_cost(monkeypatch, 100.1, [[edit("10:50", "11:50")], [edit()]])
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
    [(131, "insufficient_time_for_rechecks"), (151, "phase_deadline")],
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
            now[0] += 101
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
    assert result.timing["preparation_elapsed_seconds"] == 101
    assert result.final == original


@pytest.mark.parametrize("stage", [False, True])
@pytest.mark.parametrize("accepted_patch", [False, True])
def test_final_synchronous_revalidation_stops_after_the_hard_deadline(
    monkeypatch, stage, accepted_patch
):
    from backend.app.versions.v3 import repair_spatial

    now = [100.0]
    spatial = repair_spatial.check_addition_layout

    def slow_final_spatial(*args, **kwargs):
        value = spatial(*args, **kwargs)
        if "check_rearrangements" not in kwargs:
            now[0] += 151
        return value

    monkeypatch.setattr(repair_spatial, "check_addition_layout", slow_final_spatial)
    original, ctx = overlap_draft(), context()
    model = SequenceModel([[edit()] if accepted_patch else [], [edit()]])
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


@pytest.mark.parametrize("retain_partial", [False, True])
def test_component_deadline_stops_the_stage_and_preserves_the_best_result(
    monkeypatch, retain_partial
):
    from backend.app.versions.v3 import repair_transport

    now = [100.0]
    resolve = repair_transport.resolve_transfers
    calls = 0

    async def late_transfer(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == (2 if retain_partial else 1):
            now[0] += 149.1
            raise TimeoutError("component_deadline")
        return await resolve(*args, **kwargs)

    monkeypatch.setattr(repair_transport, "resolve_transfers", late_transfer)
    original, ctx = overlap_draft(), context()
    responses = (
        [[edit("10:50", "11:50")], [edit()], [edit()]] if retain_partial else [[edit()], [edit()]]
    )
    model = SequenceModel(responses)
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
    assert result.reason == "repair_timeout"
    assert model.calls == len(result.rounds) == (2 if retain_partial else 1)
    assert result.rounds[-1].continuation_reason == "repair_timeout"
    assert result.rounds[-1].result.components[0]["reason"] == "TimeoutError:component_deadline"
    if retain_partial:
        assert result.status == "ACCEPTED_PARTIAL" and result.selected_round_index == 1
        assert result.final == result.rounds[0].adopted != original
    else:
        assert result.status == "REJECTED" and result.final == original
