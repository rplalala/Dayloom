"""Application-owned deletion through the public bounded Repair stage."""

import asyncio
from time import monotonic

import pytest

from backend.app.policies.trip_dates import create_trip_date_window
from backend.app.versions.v3.models import ValidationPolicy
from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_models import ActivityPermission
from backend.app.versions.v3.repair_service import run_repair_stage
from backend.app.versions.v3.wiring import operation_scope
from backend.tests.versions.v3.test_multiround import policy
from backend.tests.versions.v3.test_repair import Model, Routes, context
from backend.tests.versions.v3.test_soft_pace import pace_contract, three_visits
from backend.tests.versions.v3.test_validation import DAY, activity, binding, contract


def execute(original=None, ctx=None, scope=None, **kwargs):
    original = original or three_visits()
    ctx = ctx or context(pace_contract(), policy=ValidationPolicy(review_targets={"soft_pace"}))
    scope = scope or operation_scope(original, assess(original, ctx), context=ctx)
    model = Model(error=AssertionError("Deletion must not send a proposal model request"))
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=model,
            policy=kwargs.pop("policy", policy(max_model_calls=0)),
            request_deadline=monotonic() + 600,
            **kwargs,
        )
    )
    assert model.calls == 0
    return result


def test_authorized_deletion_improves_without_any_model_allowance():
    original = three_visits()
    result = execute(original)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert len(result.final.days[0].activities) == 2
    assert len(original.days[0].activities) == len(result.original.days[0].activities) == 3
    assert result.soft_pace["target_state"] == "reached"
    assert result.counters.get("model", 0) == 0
    assert result.counters["deterministic_attempts"] == 1
    assert result.usage_status == "not_called"
    assert result.rounds[0].strategy == "system_delete"
    assert result.rounds[0].best_promoted


def test_rejected_adjacency_continues_to_another_deletion_without_discovery():
    original = three_visits()
    ctx = context(pace_contract(), policy=ValidationPolicy(review_targets={"soft_pace"}))
    scope = operation_scope(original, assess(original, ctx), context=ctx)
    scope = scope.model_copy(
        update={
            "travel_mode": "TRANSIT",
            "permissions": tuple(p for p in scope.permissions if p.activity_id != "one"),
        }
    )
    routes = Routes(duration=86400)
    result = execute(original, ctx, scope, routes_provider=routes)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert [a.activity_id for a in result.final.days[0].activities] == ["one", "two"]
    assert result.counters["deterministic_attempts"] == 2
    assert result.counters["routes"] == len(routes.calls) == 1
    assert result.counters.get("details", 0) == result.counters.get("google", 0) == 0
    assert not result.rounds[0].exploration_transition
    assert result.rounds[1].best_promoted
    assert result.rounds[0].result.parsed_patch.edits[0].activity_id == "two"


@pytest.mark.parametrize("duration,fail", [(86400, False), (0, True)])
def test_infeasible_or_unavailable_required_adjacency_preserves_original(duration, fail):
    original = three_visits()
    ctx = context(pace_contract(), policy=ValidationPolicy(review_targets={"soft_pace"}))
    scope = operation_scope(original, assess(original, ctx), context=ctx)
    scope = scope.model_copy(
        update={
            "travel_mode": "TRANSIT",
            "permissions": tuple(p for p in scope.permissions if p.activity_id == "two"),
        }
    )
    routes = Routes(duration=duration, fail=fail)
    result = execute(original, ctx, scope, routes_provider=routes)
    assert result.final == original
    assert result.counters["deterministic_attempts"] == 1
    assert result.counters["routes"] == len(routes.calls) == 1
    assert not any(r.exploration_transition for r in result.rounds)


def test_same_day_quantity_unavailability_does_not_block_confirmed_coverage_deletion():
    original = three_visits()
    requirements = contract("EXCLUDED").model_copy(
        update={"visit_requirements": (), "time_protections": ()}
    )
    ctx = context(requirements, named_resolutions=(binding(),), window=create_trip_date_window(DAY))
    assert assess(original, ctx).diagnostics.days[0].target_status == "not_assessable"
    result = execute(original, ctx)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert [a.source_place_id for a in result.final.days[0].activities] == ["b", "c"]
    assert result.adopted_report.diagnostics.days[0].minimum_coverage == "satisfied"
    assert result.adopted_report.diagnostics.days[0].target_status == "not_assessable"


def test_actual_unknown_coverage_still_blocks_count_reduction():
    original = three_visits()
    original.days[0].activities.append(
        activity("unknown", None, "18:00", "19:00", activity_kind="unknown")
    )
    requirements = contract("EXCLUDED").model_copy(
        update={"visit_requirements": (), "time_protections": ()}
    )
    ctx = context(requirements, named_resolutions=(binding(),))
    result = execute(original, ctx)
    assert result.final == original
    assert result.counters["deterministic_attempts"] == 1
    assert not result.rounds[0].exploration_transition


def test_required_visit_is_protected_even_when_delete_permission_is_present():
    original = three_visits()
    requirements = pace_contract().model_copy(
        update={"named_places": contract("REQUIRED").named_places}
    )
    ctx = context(
        requirements,
        named_resolutions=(binding(),),
        policy=ValidationPolicy(review_targets={"soft_pace"}),
    )
    scope = operation_scope(original, assess(original, ctx), context=ctx)
    scope = scope.model_copy(
        update={"permissions": (ActivityPermission(activity_id="one", operations={"delete"}),)}
    )
    result = execute(original, ctx, scope)
    assert result.final == original
    assert result.counters.get("deterministic_attempts", 0) == 0
    assert not result.rounds


def test_deterministic_attempt_limit_returns_earlier_partial_improvement():
    original = three_visits()
    original.days[0].activities.append(activity("four", "d", "18:00", "19:00"))
    from backend.tests.versions.v3.test_validation import place

    ctx = context(
        pace_contract(),
        places=tuple(place(pid) for pid in "abcd"),
        original_supply_ids=tuple("abcd"),
        policy=ValidationPolicy(review_targets={"soft_pace"}),
    )
    result = execute(original, ctx, policy=policy(max_model_calls=0, max_deletion_attempts=1))
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert len(result.final.days[0].activities) == 3
    assert result.counters["deterministic_attempts"] == 1
    assert result.soft_pace["target_state"] == "residual"


def test_deterministic_deduplication_cannot_publish_uncompensated_removal():
    from backend.tests.versions.v3.test_b_targets import repeated

    original, ctx, scope, _ = repeated()
    result = execute(original, ctx, scope)
    assert result.final == original
    assert result.counters["deterministic_attempts"] > 0
    assert not any(r.exploration_transition for r in result.rounds)
    assert all(g["status"] == "rolled_back" for g in result.pending_groups)


def test_confirmed_optional_removal_keeps_authorized_coverage_debt_visible():
    from backend.tests.versions.v3.test_c_obligations import opening_case

    original, ctx, _ = opening_case(closed=True)
    result = execute(original, ctx)
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert not result.final.days[0].activities
    assert result.adopted_report.diagnostics.days[0].minimum_coverage == "missing"
    assert any(r.status == "unresolved" for r in result.related_targets)


def test_failed_deletion_alternatives_do_not_force_extra_model_compensation():
    from backend.tests.versions.v3.test_b_targets import edit, repeated

    original, ctx, scope, config = repeated()
    model = Model(
        [edit("delete", "a2", day=1), edit("add", pid="d", day=1, start="09:00", end="10:00")]
    )
    result = asyncio.run(
        run_repair_stage(
            original, ctx, scope, policy=config, model=model, request_deadline=monotonic() + 600
        )
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert model.calls == result.counters["model"] == 1
    assert result.counters["deterministic_attempts"] == 2
    assert [a.source_place_id for a in result.final.days[0].activities] == ["a", "b"]
    assert {a.source_place_id for a in result.final.days[1].activities} == {"c", "d"}


def test_system_attempts_leave_all_six_model_sends_available_and_do_not_repeat():
    from backend.tests.versions.v3.test_b_targets import edit, repeated
    from backend.tests.versions.v3.test_multiround import SequenceModel

    original, ctx, scope, config = repeated()
    model = SequenceModel(
        [
            [],
            [],
            [],
            [],
            [],
            [edit("delete", "a2", day=1), edit("add", pid="d", day=1, start="09:00", end="10:00")],
        ]
    )
    result = asyncio.run(
        run_repair_stage(
            original, ctx, scope, policy=config, model=model, request_deadline=monotonic() + 600
        )
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert model.calls == result.counters["model"] == 6
    assert result.counters["deterministic_attempts"] == 2
    assert len(result.rounds) == 8


def test_model_pending_compensation_survives_prior_system_alternatives():
    from backend.tests.versions.v3.test_b_targets import edit, repeated
    from backend.tests.versions.v3.test_multiround import SequenceModel

    original, ctx, scope, config = repeated()
    # The model starts a different atomic group, not an equivalent failed deletion.
    config = config.model_copy(update={"max_deletion_attempts": 1})
    model = SequenceModel(
        [[edit("delete", "a2", day=1)], [edit("add", pid="d", day=1, start="09:00", end="10:00")]]
    )
    result = asyncio.run(
        run_repair_stage(
            original, ctx, scope, policy=config, model=model, request_deadline=monotonic() + 600
        )
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert model.calls == result.counters["model"] == 2
    assert result.counters["deterministic_attempts"] == 1
    assert result.rounds[1].result.pending_groups
    assert result.rounds[1].adopted == original
    assert len(result.rounds[2].result.effective_patch.edits) == 2
    assert not result.pending_groups


def test_shared_deadline_during_later_deletion_keeps_prior_best():
    from backend.tests.versions.v3.test_validation import place

    original = three_visits()
    one, two, three = original.days[0].activities
    original.days[0].activities = [two, three, one, activity("four", "d", "18:00", "19:00")]
    ctx = context(
        pace_contract(),
        places=tuple(place(pid) for pid in "abcd"),
        original_supply_ids=tuple("abcd"),
        policy=ValidationPolicy(review_targets={"soft_pace"}),
    )
    scope = operation_scope(original, assess(original, ctx), context=ctx)
    scope = scope.model_copy(update={"travel_mode": "TRANSIT"})
    now = [100.0]

    class ExpiringRoutes(Routes):
        async def compute_route_matrix(self, request):
            response = await super().compute_route_matrix(request)
            now[0] = 110.0 if len(self.calls) == 1 else 500.0
            return response

    result = execute(original, ctx, scope, routes_provider=ExpiringRoutes(), clock=lambda: now[0])
    assert len(result.final.days[0].activities) == 3
    assert result.final == result.rounds[0].adopted
    assert result.counters["routes"] == 2
    assert not result.rounds[1].exploration_transition
