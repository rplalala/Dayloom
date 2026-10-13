"""Current-round authorization must not borrow deferred review acquisition scope."""

import json
from datetime import timedelta
from pathlib import Path

from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_candidates import candidate_targets
from backend.app.versions.v3.repair_routes import bind_transitions
from backend.tests.versions.v3.test_b_targets import setup, visit
from backend.tests.versions.v3.test_c_obligations import execute
from backend.tests.versions.v3.test_repair import route
from backend.tests.versions.v3.test_validation import DAY


def test_confirmed_route_does_not_acquire_for_deferred_sparse_date():
    original, ctx, _, policy = setup(
        [
            [visit("a", "a", end="11:00"), visit("b", "b", start="11:10", end="12:10")],
            [visit("c", "c", day=1)],
        ]
    )
    ctx = ctx.model_copy(
        update={
            "route_evidence": (route(1800),),
            "transitions": bind_transitions(original, "TRANSIT", schedule=ctx.schedule),
        }
    )
    result, _ = execute((original, ctx, policy), [[]], mode="TRANSIT")
    first = result.rounds[0].result
    assert first.scope.deferred_review_target_ids
    targets = candidate_targets(original, ctx, first.scope)
    assert targets and {d for _, d, _, _ in targets} == {DAY}
    assert DAY + timedelta(days=1) not in first.scope.add_dates
    assert all(p.parent_id in first.scope.target_ids for p in first.scope.coverage_permissions)
    assert all(a.date == DAY for a in first.candidate_preparation.authorizations)


def test_retime_only_needs_no_candidate_identity():
    from backend.app.versions.v3.wiring import operation_scope
    from backend.tests.versions.v3.test_c_obligations import route_case

    original, ctx, policy = route_case()
    scope = operation_scope(original, assess(original, ctx), context=ctx, policy=policy)
    scope = scope.model_copy(
        update={
            "permissions": tuple(
                p.model_copy(update={"operations": frozenset({"retime"})})
                for p in scope.permissions
            ),
            "coverage_permissions": (),
        }
    )
    assert candidate_targets(original, ctx, scope) == ()


def test_deferred_review_promoted_only_after_confirmed_route_resolved():
    from backend.tests.versions.v3.test_b_targets import edit

    original, ctx, _, policy = setup(
        [
            [visit("a", "a", end="11:00"), visit("b", "b", start="11:10", end="12:10")],
            [visit("c", "c", day=1)],
        ]
    )
    ctx = ctx.model_copy(
        update={
            "route_evidence": (route(1800),),
            "transitions": bind_transitions(original, "TRANSIT", schedule=ctx.schedule),
        }
    )
    result, _ = execute(
        (original, ctx, policy),
        [[edit("retime", "b", start="11:40", end="12:40")], []],
        mode="TRANSIT",
    )
    first, second = result.rounds[:2]
    assert first.result.status.startswith("ACCEPTED")
    assert second.input_itinerary == first.adopted
    assert not second.result.scope.deferred_review_target_ids
    assert second.result.scope.direct_add_dates == (DAY + timedelta(days=1),)
    assert all(
        a.date == DAY + timedelta(days=1)
        for a in second.result.candidate_preparation.authorizations
    )


def test_unresolved_locality_does_not_expand_to_trip_dates():
    from backend.app.versions.v3.repair_targets import localize_scope
    from backend.app.versions.v3.wiring import operation_scope
    from backend.tests.versions.v3.test_c_obligations import route_case

    original, ctx, policy = route_case()
    report = assess(original, ctx)
    scope = operation_scope(original, report, context=ctx, policy=policy)
    report = report.model_copy(
        update={
            "findings": tuple(
                f.model_copy(update={"activity_ids": (), "dates": ()}) for f in report.findings
            )
        }
    )
    narrowed = localize_scope(original, report, scope, scope.target_ids)
    assert not narrowed.dates and not narrowed.add_dates and not narrowed.permissions


def test_current_mandatory_repeat_joins_confirmed_scope():
    original, ctx, _, policy = setup(
        [
            [visit("a", "a", end="11:00"), visit("b", "b", start="10:30", end="11:30")],
            [visit("a2", "a", day=1), visit("c", "c", day=1, start="12:00", end="13:00")],
        ]
    )
    result, _ = execute((original, ctx, policy), [[]])
    scope = result.rounds[0].result.scope
    assert not scope.deferred_review_target_ids
    assert any("delete" in p.operations for p in scope.permissions)
    assert any(
        f.check == "repetition" and f.status == "CONFIRMED" for f in result.original_report.findings
    )


def honolulu_fixture():
    from datetime import date

    from backend.app.evidence.models import PlaceEvidence, RouteEvidence
    from backend.app.policies.trip_dates import create_trip_date_window
    from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements
    from backend.app.schemas.itinerary import Itinerary
    from backend.app.versions.v3.models import ValidationPolicy
    from backend.app.versions.v3.repair_models import (
        RepairCandidate,
        RepairScope,
        ValidationContext,
    )
    from backend.app.versions.v3.repair_schedule import ScheduleState

    saved = json.loads(
        (Path(__file__).parents[2] / "fixtures/v3/honolulu_locality.json").read_text()
    )
    original = Itinerary.model_validate(saved["draft"])
    ctx = ValidationContext(
        contract=InterpretedTripRequirements.model_validate(saved["contract"]),
        window=create_trip_date_window(date(2026, 9, 25)),
        places=tuple(
            PlaceEvidence.model_validate(c["place"])
            for c in saved["ledger"]
            if c["place"]["place_id"] in saved["places"]
        ),
        original_supply_ids=tuple(saved["original_supply_ids"]),
        identity_ledger=tuple(RepairCandidate.model_validate(c) for c in saved["ledger"]),
        schedule=ScheduleState.model_validate(saved["schedule"]),
        route_evidence=tuple(RouteEvidence.model_validate(r) for r in saved["routes"]),
        policy=ValidationPolicy(review_targets={"coverage", "overfull"}),
    )
    ctx = ctx.model_copy(
        update={"transitions": bind_transitions(original, "WALK", schedule=ctx.schedule)}
    )
    return saved, original, ctx, RepairScope.model_validate(saved["scope"])


def test_honolulu_real_validation_scope_preparation_projection():
    from backend.app.versions.v3.repair_budget import configured_policy

    saved, original, ctx, _ = honolulu_fixture()
    result, model = execute(
        (
            original,
            ctx,
            configured_policy().model_copy(update={"max_model_calls": 2, "max_rounds": 2}),
        ),
        [[]],
        mode="WALK",
    )
    first = result.rounds[0].result
    assert len(first.scope.target_ids) == 2
    # Historical multiplicity has not been assessed under the new exact-count contract.
    assert len(first.scope.deferred_review_target_ids) == 5
    assert {str(a.date) for a in first.candidate_preparation.authorizations} == {
        "2026-09-27",
        "2026-10-03",
    }
    assert all(str(p.date) != "2026-10-01" for p in first.scope.coverage_permissions)
    assert first.sizing["total_tokens"] < 120000
    assert model.calls == 2 and result.final == original
    assert result.reason == "round_or_model_limit"
    assert (
        result.rounds[0].result.material_fingerprint != result.rounds[1].result.material_fingerprint
    )
    prep = first.candidate_preparation
    assert prep.identity_free_operations
    assert all("independent_identity_capacity" not in row for row in prep.target_opportunities)
    assert all(
        row["association_edges"] == row["unique_candidate_identities"]
        for row in prep.target_opportunities
    )
    assert (
        prep.identity_capacity_summary["independent_identity_capacity"]
        <= prep.identity_capacity_summary["unique_candidate_identities"]
    )
    assert any(a.opportunity_status == "UNRESOLVED" for a in prep.authorizations)
    assert saved["historical_sizing"]["total_tokens"] == 154653
