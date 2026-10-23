"""Public validation and repair behavior for the soft pace objective."""

import asyncio
from datetime import timedelta
from time import monotonic

import pytest

from backend.app.policies.itinerary_schedule import build_schedule
from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements
from backend.app.versions.v3.models import ValidationPolicy
from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_service import run_repair_stage
from backend.app.versions.v3.validation import validate_draft
from backend.app.versions.v3.wiring import operation_scope
from backend.tests.versions.v3.test_repair import Model, Routes, context, edit
from backend.tests.versions.v3.test_validation import DAY, WINDOW, activity, contract, draft, place


def pace_contract(profile="relaxed", exact_count=None):
    data = contract(preferences=profile).model_dump()
    data["visit_requirements"] = ()
    data["daily_pace"] = [
        {
            "date": None,
            "profile": profile,
            "exact_count": exact_count,
            "source_refs": [{"quote": profile, "start": 0, "end": len(profile), "occurrence": 0}],
        }
    ]
    return InterpretedTripRequirements.model_validate(data)


def three_visits():
    return draft(
        [
            activity("one", "a", "09:00", "10:00"),
            activity("two", "b", "12:00", "13:00"),
            activity("three", "c", "15:00", "16:00"),
        ]
    )


def protected_pace_contract(**changes):
    data = pace_contract().model_dump()
    protection = {
        "dates": (DAY,),
        "full_day": True,
        "start_time": None,
        "end_time": None,
        "status": "fixed",
        "reason": None,
        "source_refs": [{"quote": "Rest all day", "start": 8, "end": 20, "occurrence": 0}],
    }
    protection.update(changes)
    data["time_protections"] = [protection]
    return InterpretedTripRequirements.model_validate(data)


@pytest.mark.parametrize("dates", [(DAY,), ()])
def test_fixed_full_day_rest_has_zero_pace_penalty_and_no_repair_scope(dates):
    req = protected_pace_contract(dates=dates)
    ctx = context(
        req, policy=ValidationPolicy(review_targets={"soft_pace", "coverage", "overfull"})
    )
    original = draft([])
    report = assess(original, ctx)
    pace = next(f for f in report.findings if f.check == "soft_pace")
    assert pace.status == "PASS" and pace.magnitude == 0
    assert pace.adopted_evidence["count"] == 0
    assert pace.adopted_evidence["zero_counts"] == (0,)
    assert pace.adopted_evidence["time_protection_projection"]["protections"] == [
        p.model_dump(mode="json") for p in req.time_protections
    ]
    assert req.daily_pace[0].exact_count is None
    assert not report.improvement_targets
    assert operation_scope(original, report, context=ctx) is None
    assert not original.days[0].activities


@pytest.mark.parametrize(
    "changes",
    [
        None,
        {"dates": (DAY + timedelta(days=1),)},
        {"full_day": False, "start_time": "12:00", "end_time": "14:00"},
        {"status": "unresolved", "reason": "Protection scope is not executable"},
    ],
    ids=["ordinary-blank", "other-date", "partial-day", "unresolved"],
)
def test_blank_day_without_fixed_full_day_protection_keeps_pace_target(changes):
    req = (
        pace_contract().model_copy(update={"time_protections": ()})
        if changes is None
        else protected_pace_contract(**changes)
    )
    ctx = context(req, policy=ValidationPolicy(review_targets={"soft_pace", "coverage"}))
    original = draft([])
    report = assess(original, ctx)
    pace = next(f for f in report.findings if f.check == "soft_pace")
    assert pace.magnitude == 100 and pace.status == "NEEDS_REVIEW"
    assert pace.adopted_evidence["zero_counts"] == (2,)
    assert "time_protection_projection" not in pace.adopted_evidence
    assert pace.finding_id in {t.finding_id for t in report.improvement_targets}
    scope = operation_scope(original, report, context=ctx)
    assert scope is not None and DAY in scope.add_dates
    if changes is None:
        assert report.diagnostics.days[0].minimum_coverage == "missing"


@pytest.mark.parametrize("kind", ["main_poi", "generic_activity"])
def test_full_day_pace_projection_preserves_actual_counts_and_hard_time_conflicts(kind):
    ctx = context(protected_pace_contract(), policy=ValidationPolicy(review_targets={"soft_pace"}))
    original = draft([activity(activity_kind=kind, time_use="scheduled")])
    ctx = ctx.model_copy(update={"schedule": build_schedule(original, ctx.contract, ctx.places)})
    report = assess(original, ctx)
    assert any(
        f.reason == "fixed_user_time_overlap" and f.status == "CONFIRMED" for f in report.findings
    )
    pace = next(f for f in report.findings if f.check == "soft_pace")
    assert pace.adopted_evidence["count"] == (1 if kind == "main_poi" else 0)
    assert pace.magnitude == (100 if kind == "main_poi" else 0)
    assert pace.adopted_evidence["zero_counts"] == (0,)


def test_full_day_projection_does_not_turn_unknown_activity_roles_into_zero_visits():
    ctx = context(protected_pace_contract(), policy=ValidationPolicy(review_targets={"soft_pace"}))
    report = assess(draft([activity(activity_kind="unknown")]), ctx)
    pace = next(f for f in report.findings if f.check == "soft_pace")
    assert pace.status == "UNKNOWN" and pace.magnitude is None
    assert pace.finding_id not in {t.finding_id for t in report.improvement_targets}


@pytest.mark.parametrize("first_count", [0, 1, 2])
def test_rest_day_projection_keeps_first_day_exact_one_and_ordinary_blank_day(first_count):
    from backend.tests.versions.v3.test_daily_visit_counts import counted_context
    from backend.tests.versions.v3.test_repair_search import scenario

    original, ctx, _ = scenario((first_count, 0, 0))
    req = counted_context(1).contract
    req = req.model_copy(
        update={
            "requirements": req.requirements.model_copy(update={"end_date": original.end_date}),
            "time_protections": protected_pace_contract(
                dates=(DAY + timedelta(days=1),)
            ).time_protections,
        }
    )
    report = assess(original, ctx.model_copy(update={"contract": req}))
    daily = next(f for f in report.findings if f.check == "daily_visit_count")
    assert daily.status == ("PASS" if first_count == 1 else "CONFIRMED")
    pace = {f.dates[0]: f for f in report.findings if f.check == "soft_pace"}
    assert [pace[DAY + timedelta(days=i)].magnitude for i in range(3)] == [
        0 if first_count == 1 else 100,
        0,
        100,
    ]
    targets = {t.finding_id for t in report.improvement_targets}
    assert pace[DAY + timedelta(days=1)].finding_id not in targets
    assert pace[DAY + timedelta(days=2)].finding_id in targets


def test_repair_can_complete_other_pace_goals_while_preserving_exact_one_and_rest_day():
    from backend.tests.versions.v3.test_daily_visit_counts import counted_context
    from backend.tests.versions.v3.test_repair_search import scenario

    original, ctx, _ = scenario((1, 3, 0))
    req = counted_context(1).contract
    req = req.model_copy(
        update={
            "requirements": req.requirements.model_copy(update={"end_date": original.end_date}),
            "time_protections": protected_pace_contract(
                dates=(DAY + timedelta(days=2),)
            ).time_protections,
        }
    )
    ctx = ctx.model_copy(
        update={"contract": req, "schedule": build_schedule(original, req, ctx.places)}
    )
    report = assess(original, ctx)
    scope = operation_scope(original, report, context=ctx)
    assert scope is not None
    assert all(
        f.dates == (DAY + timedelta(days=1),)
        for f in report.findings
        if f.finding_id in scope.target_ids
    )
    assert DAY + timedelta(days=2) not in scope.direct_add_dates
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=Model(),
            routes_provider=Routes(),
            request_deadline=monotonic() + 600,
        )
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert [len(d.activities) for d in result.final.days] == [1, 2, 0]
    assert result.soft_pace["target_state"] == "reached"
    assert all(p.outcome == "resolved" for p in result.target_progress)
    assert not result.adopted_report.improvement_targets
    assert [len(d.activities) for d in original.days] == [1, 3, 0]


def test_relaxed_three_visit_draft_has_soft_repair_target_not_violation():
    original = three_visits()
    report = validate_draft(
        original,
        pace_contract(),
        window=WINDOW,
        supplied_ids=("a", "b", "c"),
        places=(place(), place("b"), place("c")),
        policy=ValidationPolicy(review_targets={"soft_pace"}),
    )
    pace = next(f for f in report.findings if f.check == "soft_pace")
    assert pace.magnitude == 40
    assert pace.dates == (DAY,)
    assert pace.status == "NEEDS_REVIEW" and not pace.is_violation
    assert pace.finding_id in {t.finding_id for t in report.improvement_targets}
    assert len(original.days[0].activities) == 3


def test_repair_adopts_zero_pace_without_changing_original_draft():
    original = three_visits()
    ctx = context(pace_contract(), policy=ValidationPolicy(review_targets={"soft_pace"}))
    report = validate_draft(
        original,
        ctx.contract,
        window=WINDOW,
        supplied_ids=ctx.original_supply_ids,
        places=ctx.places,
        policy=ctx.policy,
    )
    scope = operation_scope(original, report, context=ctx)
    assert scope is not None
    model = Model([edit(operation="delete", start=None, end=None)])
    routes = Routes()
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=model,
            routes_provider=routes,
            request_deadline=monotonic() + 600,
        )
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert len(result.final.days[0].activities) == 2
    assert len(original.days[0].activities) == 3
    pace = next(p for p in result.target_progress if p.check == "soft_pace")
    assert (pace.before, pace.after, pace.outcome) == (40, 0, "resolved")
    assert result.soft_pace["target_state"] == "reached"
    assert model.calls == result.counters.get("model", 0) == 0
    assert result.counters["deterministic_attempts"] == 1


def test_actual_v3_runner_carries_pace_from_existing_interpretation_call():
    from backend.app.schemas.interpreted_requirements import InterpretationDraft
    from backend.app.services.preference_interpretation import empty_preference_draft
    from backend.tests.request_fixtures import make_request
    from backend.tests.versions.v3.test_wiring import ManyPlaces, execute, primary
    from backend.tests.versions.v3.test_wiring import Model as RunnerModel

    initial = primary(overlap=False)
    a = initial.days[0].activities[0]
    for index in (1, 3):
        from datetime import timedelta

        initial.days[0].activities.append(
            a.model_copy(
                update={
                    "activity_id": "two" if index == 1 else "three",
                    "source_place_id": f"poi-0-{index}",
                    "place_name": f"Place poi-0-{index}",
                    "start_time": a.start_time + timedelta(hours=3 if index == 1 else 6),
                    "end_time": a.end_time + timedelta(hours=3 if index == 1 else 6),
                }
            )
        )
    fields = empty_preference_draft().model_dump()
    fields["daily_pace"] = [
        {
            "date": None,
            "profile": "relaxed",
            "exact_count": None,
            "source_refs": [{"quote": "relaxed", "occurrence": 0}],
        }
    ]

    class PaceModel(RunnerModel):
        async def generate_structured(self, **kwargs):
            if kwargs["response_schema"].__name__ == "V1Itinerary":
                import json

                supply = json.loads(
                    kwargs["user_prompt"].split("Planning candidate supply contract:\n", 1)[1]
                )
                ids = iter(supply["optional_canonical_ids"])
                for day in self.responses[0].days:
                    for a in day.activities:
                        a.source_place_id = next(ids)
                        a.place_name = f"Place {a.source_place_id}"
            return await super().generate_structured(**kwargs)

    model = PaceModel(initial, behavior="delete")
    model.responses.insert(0, InterpretationDraft.model_validate(fields))
    result, model, _, _ = asyncio.run(
        execute(
            model,
            places=ManyPlaces(),
            request=make_request("relaxed"),
            quantity_review_enabled=True,
            system_deletions=True,
        )
    )
    pace = next(
        f
        for f in result.v3.original_report.findings
        if f.check == "soft_pace" and str(f.dates[0]) == "2026-09-12"
    )
    assert pace.magnitude == 40
    assert result.v3.repair.soft_pace["after"]["days"][0]["penalty"] == 0
    assert len([c for c in model.calls if c.response_schema is InterpretationDraft]) == 1
    assert len(result.v3.draft.days[0].activities) == 3
    assert result.v3.repair.rounds[0].strategy == "system_delete"
    assert result.v3.repair.counters["deterministic_attempts"] >= 1


def test_incremental_pace_improvement_is_kept_at_model_limit():
    from backend.tests.versions.v3.test_multiround import policy

    original = three_visits()
    original.days[0].activities.append(activity("four", "d", "18:00", "19:00"))
    ctx = context(
        pace_contract(),
        original_supply_ids=("a", "b", "c", "d"),
        places=(place(), place("b"), place("c"), place("d")),
        policy=ValidationPolicy(review_targets={"soft_pace"}),
    )
    report = validate_draft(
        original,
        ctx.contract,
        window=WINDOW,
        supplied_ids=ctx.original_supply_ids,
        places=ctx.places,
        policy=ctx.policy,
    )
    scope = operation_scope(original, report, context=ctx)
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=Model([edit(operation="delete", start=None, end=None)]),
            routes_provider=Routes(),
            policy=policy(max_model_calls=1, max_rounds=1, max_deletion_attempts=0),
            request_deadline=monotonic() + 600,
        )
    )
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert result.soft_pace["before"]["mean_penalty"] == 70
    assert result.soft_pace["after"]["mean_penalty"] == 40
    assert result.soft_pace["target_state"] == "residual"
    assert result.reason == "round_or_model_limit"
    assert len(result.final.days[0].activities) == 3


@pytest.mark.parametrize(
    "profile,exact,expected",
    [
        ("ordinary", None, 10),
        ("rich", None, 0),
        ("relaxed", 3, 0),
        ("unresolved", None, None),
        ("relaxed", 1, 100),
    ],
)
def test_pace_profiles_and_explicit_counts_keep_numeric_meaning(profile, exact, expected):
    report = validate_draft(
        three_visits(),
        pace_contract(profile, exact),
        window=WINDOW,
        supplied_ids=("a", "b", "c"),
        places=(place(), place("b"), place("c")),
        policy=ValidationPolicy(review_targets={"soft_pace", "coverage"}),
    )
    f = next(f for f in report.findings if f.check == "soft_pace")
    assert f.magnitude == expected
    assert not f.is_violation
    assert bool(f.finding_id in {t.finding_id for t in report.improvement_targets}) == (
        expected not in (0, None)
    )


def test_date_override_and_disabled_optimization_are_read_only():
    data = pace_contract().model_dump()
    data["daily_pace"] += (
        {
            "date": DAY,
            "profile": "rich",
            "exact_count": None,
            "source_refs": data["daily_pace"][0]["source_refs"],
        },
    )
    report = validate_draft(
        three_visits(),
        InterpretedTripRequirements.model_validate(data),
        window=WINDOW,
        supplied_ids=("a", "b", "c"),
        places=(place(), place("b"), place("c")),
    )
    assert next(f for f in report.findings if f.check == "soft_pace").magnitude == 0
    assert not report.improvement_targets


def test_required_visit_cannot_be_deleted_to_improve_pace():
    from backend.tests.versions.v3.test_multiround import policy
    from backend.tests.versions.v3.test_validation import binding

    req = pace_contract().model_copy(
        update={
            "named_places": contract("REQUIRED").named_places,
            "visit_requirements": (),
            "daily_pace": pace_contract().daily_pace,
        }
    )
    ctx = context(
        req, named_resolutions=(binding(),), policy=ValidationPolicy(review_targets={"soft_pace"})
    )
    original = three_visits()
    report = validate_draft(
        original,
        req,
        window=WINDOW,
        supplied_ids=ctx.original_supply_ids,
        places=ctx.places,
        named_resolutions=ctx.named_resolutions,
        policy=ctx.policy,
    )
    scope = operation_scope(original, report, context=ctx)
    assert "one" not in {p.activity_id for p in scope.permissions if "delete" in p.operations}
    model = Model([edit(operation="delete", activity_id="one", start=None, end=None)])
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=model,
            routes_provider=Routes(),
            policy=policy(max_deletion_attempts=0),
            request_deadline=monotonic() + 600,
        )
    )
    assert result.final == original
    assert result.soft_pace["after"]["mean_penalty"] == 40
    assert result.status in {"REJECTED", "SKIPPED"}


@pytest.mark.parametrize("fault", ["quote", "foreign_date", "duplicate_date"])
def test_actual_runner_rejects_unsourced_or_foreign_pace_before_generation(fault):
    from backend.app.schemas.interpreted_requirements import InterpretationDraft
    from backend.app.services.preference_interpretation import empty_preference_draft
    from backend.tests.request_fixtures import make_request
    from backend.tests.versions.v3.test_wiring import Model as RunnerModel
    from backend.tests.versions.v3.test_wiring import execute

    fields = empty_preference_draft().model_dump()
    fields["daily_pace"] = [
        {
            "date": None,
            "profile": "relaxed",
            "exact_count": None,
            "source_refs": [{"quote": "relaxed", "occurrence": 0}],
        }
    ]
    if fault == "quote":
        fields["daily_pace"][0]["source_refs"][0]["quote"] = "foreign text"
    elif fault == "foreign_date":
        fields["daily_pace"].append({**fields["daily_pace"][0], "date": "2099-01-01"})
    else:
        fields["daily_pace"].append(dict(fields["daily_pace"][0]))
    model = RunnerModel()
    model.responses.insert(0, InterpretationDraft.model_validate(fields))
    from backend.app.schemas.requirement_boundary import RequirementBoundaryError

    with pytest.raises(RequirementBoundaryError):
        asyncio.run(execute(model, request=make_request("relaxed")))
    assert len(model.calls) == 1
    assert model.repair_calls == 0


def test_exhausted_stage_keeps_draft_with_residual_goal_and_no_model_send():
    original = three_visits()
    ctx = context(pace_contract(), policy=ValidationPolicy(review_targets={"soft_pace"}))
    report = validate_draft(
        original,
        ctx.contract,
        window=WINDOW,
        supplied_ids=ctx.original_supply_ids,
        places=ctx.places,
        policy=ctx.policy,
    )
    scope = operation_scope(original, report, context=ctx)
    model = Model()
    result = asyncio.run(
        run_repair_stage(original, ctx, scope, model=model, request_deadline=monotonic() + 0.001)
    )
    assert result.final == original
    assert not result.model_attempted and model.calls == 0
    assert result.status == "SKIPPED"
    assert result.soft_pace["target_state"] == "residual"
    assert result.soft_pace["is_failure_constraint"] is False
