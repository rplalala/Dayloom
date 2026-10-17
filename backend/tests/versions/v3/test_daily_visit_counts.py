"""Hard dated occurrence counts are repaired without aggregate tradeoffs."""

import asyncio
from datetime import timedelta
from time import monotonic

import pytest

from backend.app.policies.interpreted_requirements import canonicalize_requirements
from backend.app.schemas.request import PlanningRequest
from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_service import run_repair_once
from backend.app.versions.v3.wiring import operation_scope
from backend.tests.services.test_daily_visit_constraints import counted_draft
from backend.tests.versions.v3.test_repair import Model, Routes, context, edit
from backend.tests.versions.v3.test_validation import DAY, activity, draft


def counted_context(count, *, mode="exact"):
    interpretation = counted_draft(count, day=str(DAY), mode=mode)
    text = interpretation.semantic_requirements[0].source_refs[0].quote
    request = PlanningRequest(
        destination="Fixture",
        start_date=DAY,
        end_date=DAY,
        traveler_count=2,
        budget={"amount": 100, "currency": "GBP"},
        additional_preferences=text,
    )
    contract = canonicalize_requirements(interpretation, request)
    return context(contract)


def test_satisfied_one_visit_is_not_a_default_two_visit_repair_target():
    ctx = counted_context(1)
    report = assess(draft([activity()]), ctx)
    assert next(f for f in report.findings if f.check == "daily_visit_count").status == "PASS"
    assert not any(f.check == "coverage" and f.status == "NEEDS_REVIEW" for f in report.findings)


@pytest.mark.parametrize("count,penalty", [(3, 0), (4, 40)])
def test_hard_minimum_limits_the_soft_objective_without_becoming_a_maximum(count, penalty):
    ctx = counted_context(3, mode="minimum")
    items = [
        activity(str(i), str(i), f"{9 + i * 2:02}:00", f"{10 + i * 2:02}:00") for i in range(count)
    ]
    report = assess(
        draft(items),
        ctx.model_copy(
            update={
                "original_supply_ids": tuple(str(i) for i in range(count)),
                "places": tuple(
                    ctx.places[0].model_copy(update={"place_id": str(i)}) for i in range(count)
                ),
            }
        ),
    )
    assert next(f for f in report.findings if f.check == "daily_visit_count").status == "PASS"
    pace = next(f for f in report.findings if f.check == "soft_pace")
    assert pace.magnitude == penalty
    assert pace.adopted_evidence["zero_counts"] == (3,)


def test_surplus_visit_can_be_deleted_to_satisfy_exact_one():
    original = draft([activity(), activity("two", "b", "12:00", "13:00")])
    ctx = counted_context(1)
    report = assess(original, ctx)
    scope = operation_scope(original, report, context=ctx)
    target = next(f for f in report.findings if f.check == "daily_visit_count")
    assert target.status == "CONFIRMED" and target.finding_id in scope.target_ids
    model = Model(
        edits=[
            {
                "operation": "delete",
                "activity_id": "two",
                "date": str(DAY),
                "place_id": None,
                "start_time": None,
                "end_time": None,
            }
        ]
    )
    result = asyncio.run(
        run_repair_once(original, ctx, scope, model=model, request_deadline=monotonic() + 300)
    )
    assert result.status.startswith("ACCEPTED"), result.reason
    assert (
        next(f for f in result.proposed_report.findings if f.check == "daily_visit_count").status
        == "PASS"
    )


@pytest.mark.parametrize("strategy", ["local", "replan"])
def test_shortfall_can_be_filled_through_authorized_repair(strategy):
    original, ctx = draft([activity()]), counted_context(2)
    scope = operation_scope(original, assess(original, ctx), context=ctx)
    result = asyncio.run(
        run_repair_once(
            original,
            ctx,
            scope,
            model=Model([edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")]),
            routes_provider=Routes(duration=300),
            request_deadline=monotonic() + 300,
            proposal_strategy=strategy,
        )
    )
    assert result.status.startswith("ACCEPTED"), result.reason
    assert (
        next(f for f in result.proposed_report.findings if f.check == "daily_visit_count").status
        == "PASS"
    )


def test_complete_patch_cannot_remove_the_only_visit_on_a_satisfied_date():
    from backend.app.versions.v3.repair_acceptance import apply_patch
    from backend.app.versions.v3.repair_models import CandidatePreparation, RepairPatch, RepairScope

    original = draft([activity()])
    ctx = counted_context(1)
    scope = RepairScope(
        dates=(DAY,),
        permissions=({"activity_id": "one", "operations": {"delete"}},),
        target_ids=("other",),
    )
    patch = RepairPatch(
        edits=(
            {
                "operation": "delete",
                "activity_id": "one",
                "date": DAY,
                "place_id": None,
                "start_time": None,
                "end_time": None,
            },
        )
    )
    with pytest.raises(ValueError, match="daily visit constraint regressed"):
        apply_patch(original, patch, scope, CandidatePreparation(), context=ctx)


def test_zero_sightseeing_is_exempt_from_coverage_but_allows_a_supporting_meal():
    ctx = counted_context(0)
    original = draft([activity(activity_kind="generic_activity", time_use="scheduled")])
    report = assess(original, ctx)
    assert next(f for f in report.findings if f.check == "daily_visit_count").status == "PASS"
    assert report.diagnostics.days[0].minimum_coverage == "exempt"
    assert not any(f.status == "CONFIRMED" for f in report.findings)


def test_move_cannot_break_either_satisfied_date_despite_other_improvements():
    from backend.app.policies.daily_visit_constraints import protect_daily_visits

    first = counted_context(1).contract
    tomorrow = DAY + timedelta(days=1)
    data = first.model_dump(mode="json")
    # A second date is allowed to have visits; the first date's exact total still binds.
    data["requirements"]["end_date"] = str(tomorrow)
    contract = type(first).model_validate(data)
    one = activity()
    two = activity("two", "b", "12:00", "13:00").model_copy(
        update={
            "start_time": one.start_time + timedelta(days=1, hours=2),
            "end_time": one.end_time + timedelta(days=1, hours=2),
        }
    )
    original = draft([one]).model_copy(
        update={
            "end_date": tomorrow,
            "days": [
                draft([one]).days[0],
                draft([two]).days[0].model_copy(update={"date": tomorrow}),
            ],
        }
    )
    for moved in ("out", "in"):
        proposed = original.model_copy(
            update={
                "days": [
                    original.days[0].model_copy(
                        update={
                            "activities": []
                            if moved == "out"
                            else [
                                one,
                                two.model_copy(
                                    update={
                                        "start_time": two.start_time - timedelta(days=1),
                                        "end_time": two.end_time - timedelta(days=1),
                                    }
                                ),
                            ]
                        }
                    ),
                    original.days[1].model_copy(
                        update={
                            "activities": [
                                two,
                                one.model_copy(
                                    update={
                                        "start_time": one.start_time + timedelta(days=1),
                                        "end_time": one.end_time + timedelta(days=1),
                                    }
                                ),
                            ]
                            if moved == "out"
                            else []
                        }
                    ),
                ]
            }
        )
        with pytest.raises(ValueError, match="daily visit constraint regressed"):
            protect_daily_visits(original, proposed, contract)
