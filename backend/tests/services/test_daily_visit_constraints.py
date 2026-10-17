"""Dated all-primary counts stay executable and distinct from soft pace/rest days."""

import asyncio
from datetime import date

import pytest

from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.services.preference_interpretation import (
    empty_preference_draft,
    interpret_preferences,
)
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient

TEXT = "On 2026-09-12, plan exactly one sightseeing visit."


def counted_draft(count=1, *, day="2026-09-12", strength="hard", mode="exact"):
    text = TEXT.replace("2026-09-12", day)
    if count != 1:
        text = text.replace("one", str(count))
    if mode == "minimum":
        text = text.replace("exactly", "at least")
    data = empty_preference_draft().model_dump()
    data["semantic_requirements"] = [
        {
            "local_key": "daily",
            "normalized_text": text,
            "kind": "constraint",
            "polarity": "favor",
            "strength": strength,
            "scope": "itinerary_style",
            "subject_target": {"kind": "party"},
            "source_refs": [{"quote": text, "occurrence": 0}],
        }
    ]
    data["daily_visit_constraints"] = [
        {
            "date": day,
            "mode": mode,
            "count": count,
            "strength": strength,
            "requirement_refs": ["daily"],
            "source_refs": [{"quote": text, "occurrence": 0}],
        }
    ]
    return InterpretationDraft.model_validate(data)


def test_explicit_daily_total_survives_the_shared_hard_gate():
    from backend.app.policies.interpreted_requirements import assess_requirements

    contract = asyncio.run(
        interpret_preferences(
            make_request(TEXT), date(2026, 9, 11), FakeStructuredLLMClient([counted_draft()])
        )
    )
    rule = contract.daily_visit_constraints[0]
    assert (rule.date, rule.count, rule.strength) == (date(2026, 9, 12), 1, "hard")
    assert rule.requirement_refs == ("semantic_1",)
    assert assess_requirements(contract)[0].predicate_id == "daily_primary_visit_count"
    assert next(p for p in contract.daily_pace if p.date == rule.date).exact_count == 1


def test_unrelated_unsupported_hard_requirement_is_not_waived_by_daily_count():
    from backend.app.schemas.interpreted_requirements import ClarificationRequired

    text = TEXT + " Guarantee that I never queue."
    data = counted_draft().model_dump(mode="json")
    data["semantic_requirements"].append(
        {
            "local_key": "queue",
            "normalized_text": "Guarantee no queues.",
            "kind": "constraint",
            "polarity": "avoid",
            "strength": "hard",
            "scope": "whole_trip",
            "subject_target": {"kind": "party"},
            "source_refs": [{"quote": "Guarantee that I never queue.", "occurrence": 0}],
        }
    )
    with pytest.raises(ClarificationRequired, match="unsupported_hard_requirements"):
        asyncio.run(
            interpret_preferences(
                make_request(text),
                date(2026, 9, 11),
                FakeStructuredLLMClient([InterpretationDraft.model_validate(data)]),
            )
        )


def test_new_contract_rejects_a_separate_unbound_soft_count():
    from backend.app.schemas.requirement_boundary import RequirementBoundaryError

    data = empty_preference_draft().model_dump(mode="json")
    data["daily_visit_constraints"] = []
    data["daily_pace"].append(
        {
            "date": "2026-09-12",
            "profile": "ordinary",
            "exact_count": 1,
            "source_refs": [{"quote": TEXT, "occurrence": 0}],
        }
    )
    with pytest.raises(RequirementBoundaryError, match="unbound_daily_pace_count"):
        asyncio.run(
            interpret_preferences(
                make_request(TEXT),
                date(2026, 9, 11),
                FakeStructuredLLMClient([InterpretationDraft.model_validate(data)]),
            )
        )


def test_count_uses_occurrences_and_excludes_known_non_main_and_supporting_activities():
    from types import SimpleNamespace

    from backend.app.policies.daily_visit_constraints import daily_count_bounds
    from backend.tests.versions.v3.test_validation import DAY, activity, draft

    visits = [
        activity(),
        activity("repeat", "a", "12:00", "13:00"),
        activity("meal", "food", "14:00", "15:00"),
        activity(
            "support", "a", "15:00", "16:00", activity_kind="generic_activity", time_use="scheduled"
        ),
        activity(
            "free",
            None,
            "16:00",
            "17:00",
            place_name=None,
            activity_kind="free_time",
            time_use="free_window",
        ),
    ]
    roles = [
        SimpleNamespace(place_id="a", role="attraction", main_eligible=True),
        SimpleNamespace(place_id="food", role="non_main", main_eligible=False),
    ]
    confirmed, possible = daily_count_bounds(draft(visits), DAY, roles)
    assert confirmed == ("one", "repeat")
    assert possible == ()


def test_uncertain_role_and_date_cannot_be_counted_as_zero():
    from types import SimpleNamespace

    from backend.app.policies.daily_visit_constraints import daily_count_bounds
    from backend.tests.versions.v3.test_validation import DAY, activity, draft

    roles = [SimpleNamespace(place_id="a", role="unresolved", main_eligible=False)]
    confirmed, possible = daily_count_bounds(draft([activity()]), DAY, roles)
    assert confirmed == () and possible == ("one",)
    wrong_day = activity(
        start_time="2026-09-27T10:00:00+00:00", end_time="2026-09-27T11:00:00+00:00"
    )
    confirmed, possible = daily_count_bounds(draft([wrong_day]), DAY)
    assert confirmed == () and possible == ("one",)


def test_first_generation_carries_the_executable_dated_count():
    from backend.app.services.planning_supply_pipeline import planner_supply_projection
    from backend.tests.versions.v3.test_daily_visit_counts import counted_context

    class EmptySupply:
        selected_place_ids = required_canonical_ids = optional_canonical_ids = ()
        landmarks = profile_relations = {}
        shortfall = 0

    from types import SimpleNamespace

    contract = counted_context(1).contract
    selection = SimpleNamespace(policy_result=EmptySupply(), semantic_assessments=())
    projected = planner_supply_projection(selection, contract)
    assert projected["daily_visit_constraints"][0]["count"] == 1
    assert projected["daily_visit_constraints"][0]["requirement_refs"] == ("semantic_1",)


@pytest.mark.parametrize("fault", ["foreign_ref", "strength", "date", "bool", "negative"])
def test_invalid_daily_scope_or_binding_fails_before_generation(fault):
    from pydantic import ValidationError

    from backend.app.policies.interpreted_requirements import canonicalize_requirements
    from backend.app.schemas.requirement_boundary import RequirementBoundaryError

    data = counted_draft().model_dump(mode="json")
    rule = data["daily_visit_constraints"][0]
    field, value = {
        "foreign_ref": ("requirement_refs", ["foreign"]),
        "strength": ("strength", "soft"),
        "date": ("date", "2026-10-22"),
        "bool": ("count", True),
        "negative": ("count", -1),
    }[fault]
    rule[field] = value
    with pytest.raises((RequirementBoundaryError, ValidationError)):
        canonicalize_requirements(InterpretationDraft.model_validate(data), make_request(TEXT))


def test_positive_daily_count_conflicts_with_full_rest_day_but_zero_does_not():
    from backend.app.policies.interpreted_requirements import canonicalize_requirements
    from backend.app.schemas.interpreted_requirements import ClarificationRequired

    rest = " Leave 2026-09-12 completely free of planned activities and travel."
    for count in (0, 1):
        data = counted_draft(count).model_dump(mode="json")
        data["time_protections"] = [
            {
                "dates": ["2026-09-12"],
                "full_day": True,
                "start_time": None,
                "end_time": None,
                "status": "fixed",
                "reason": None,
                "source_refs": [{"quote": rest.strip(), "occurrence": 0}],
            }
        ]
        request = make_request(data["semantic_requirements"][0]["source_refs"][0]["quote"] + rest)
        if count:
            with pytest.raises(ClarificationRequired, match="daily_visit_protected_day_conflict"):
                canonicalize_requirements(InterpretationDraft.model_validate(data), request)
        else:
            assert (
                canonicalize_requirements(InterpretationDraft.model_validate(data), request)
                .time_protections[0]
                .full_day
            )


def test_incompatible_hard_daily_totals_remain_a_clarification():
    from backend.app.policies.interpreted_requirements import canonicalize_requirements
    from backend.app.schemas.interpreted_requirements import ClarificationRequired

    data = counted_draft().model_dump(mode="json")
    other = counted_draft(2).model_dump(mode="json")
    other["semantic_requirements"][0]["local_key"] = "other"
    other["daily_visit_constraints"][0]["requirement_refs"] = ["other"]
    data["semantic_requirements"] += other["semantic_requirements"]
    data["daily_visit_constraints"] += other["daily_visit_constraints"]
    request = make_request(
        TEXT + " " + other["semantic_requirements"][0]["source_refs"][0]["quote"]
    )
    with pytest.raises(ClarificationRequired, match="daily_visit_constraint_conflict"):
        canonicalize_requirements(InterpretationDraft.model_validate(data), request)
