"""Required category visits use sourced goals, never venue-name special cases."""

import asyncio
from datetime import date

import pytest

from backend.app.schemas.interpreted_requirements import ClarificationRequired, InterpretationDraft
from backend.app.services.preference_interpretation import (
    empty_preference_draft,
    interpret_preferences,
)
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient


def category_draft(text, *, frequency="one_off", count=None, **changes):
    data = empty_preference_draft().model_dump()
    data["semantic_requirements"] = [
        {
            "local_key": "visit",
            "normalized_text": text,
            "kind": "goal",
            "polarity": "favor",
            "strength": "hard",
            "scope": "selected_poi_set",
            "subject_target": {"kind": "party"},
            "source_refs": [{"quote": text, "occurrence": 0}],
            "experience_goal": {
                "frequency": frequency,
                "count": count,
                "target": "category",
                "distinct_dates": False,
                "explicit_primary_exception": False,
                "trip_scope": "ordinary",
            },
            **changes,
        }
    ]
    data["discovery_intents"] = [
        {
            "requirement_refs": ["visit"],
            "purpose": "activity_or_category",
            "query_text": text,
        }
    ]
    return InterpretationDraft.model_validate(data)


@pytest.mark.parametrize(
    "text",
    [
        "Must include: An art museum.",
        "We must visit a botanical garden.",
        "Include a science centre; this is essential.",
        "A local craft workshop is required.",
    ],
)
def test_tools_admit_required_categories_without_changing_the_request(text):
    request = make_request(text)
    before = request.model_dump()
    contract = asyncio.run(
        interpret_preferences(
            request,
            date(2026, 9, 11),
            FakeStructuredLLMClient([category_draft(text)]),
            category_visits=True,
        )
    )
    assert request.model_dump() == before
    requirement = contract.semantic_requirements[0]
    assert requirement.strength == "hard"
    assert requirement.source_refs[0].quote == text
    assert requirement.experience_goal.frequency == "one_off"
    assert requirement.soft_coverage is None


def test_v0_does_not_claim_evidence_based_category_enforcement():
    text = "A botanical garden is required."
    with pytest.raises(ClarificationRequired, match="unsupported_hard_requirements"):
        asyncio.run(
            interpret_preferences(
                make_request(text),
                date(2026, 9, 11),
                FakeStructuredLLMClient([category_draft(text)]),
            )
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"experience_goal": None},
        {"polarity": "avoid"},
        {"scope": "itinerary_style"},
    ],
)
def test_tools_do_not_waive_other_hard_semantics(changes):
    text = "A non-negotiable travel condition."
    with pytest.raises(ClarificationRequired, match="unsupported_hard_requirements"):
        asyncio.run(
            interpret_preferences(
                make_request(text),
                date(2026, 9, 11),
                FakeStructuredLLMClient([category_draft(text, **changes)]),
                category_visits=True,
            )
        )


@pytest.mark.parametrize("frequency,count", [("exact", 2), ("minimum", 3)])
def test_explicit_category_counts_retain_operator_and_number(frequency, count):
    text = "An explicitly counted category visit request."
    contract = asyncio.run(
        interpret_preferences(
            make_request(text),
            date(2026, 9, 11),
            FakeStructuredLLMClient([category_draft(text, frequency=frequency, count=count)]),
            category_visits=True,
        )
    )
    goal = contract.semantic_requirements[0].experience_goal
    assert (goal.frequency, goal.count) == (frequency, count)


@pytest.mark.parametrize("version", ["v1", "v2", "v3"])
@pytest.mark.parametrize("qualified", [True, False])
@pytest.mark.parametrize(
    "text", ["Must include: An art museum.", "A botanical garden is required."]
)
def test_real_tools_graphs_acquire_and_report_required_categories(version, qualified, text):
    import json

    from backend.app.versions.v1.runner import run_v1
    from backend.app.versions.v2.runner import run_v2
    from backend.app.versions.v3.runner import run_v3
    from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
    from backend.tests.versions.v3.test_wiring import Model, OwnedRetrieval, Places, primary

    class CategoryModel(Model):
        def __init__(self):
            super().__init__(primary(False), behavior="empty")
            self.responses.insert(0, category_draft(text))

        async def generate_poi_semantics_structured(self, **kwargs):
            payload = json.loads(kwargs["user_prompt"])
            result = await super().generate_poi_semantics_structured(**kwargs)
            for row in result["assessments"]:
                if not qualified:
                    row["role"] = "unresolved"
                row["matches"] = [
                    {
                        "requirement_id": req["requirement_id"],
                        "relation": "supported" if qualified else "unresolved",
                        "evidence_refs": row["evidence_refs"],
                    }
                    for req in payload["requirements"]
                ]
            return result

    options = {}
    if version in {"v2", "v3"}:
        options["retrieval_factory"] = OwnedRetrieval
    if version == "v3":
        options.update(development_timeout_seconds=600, quantity_review_enabled=False)
    request = make_request(text)
    operation = {"v1": run_v1, "v2": run_v2, "v3": run_v3}[version](
        request,
        CategoryModel(),
        Places(),
        FakeWeatherProvider(),
        FakeRoutesProvider(),
        reference_date=date(2026, 9, 11),
        **options,
    )
    if not qualified:
        from backend.app.product.task_outcomes import failure_outcome
        from backend.app.services.planning import PlanningNeedsClarificationError

        with pytest.raises(ClarificationRequired) as caught:
            asyncio.run(operation)
        assert caught.value.code == "no_qualified_candidates"
        state, outcome = failure_outcome(
            PlanningNeedsClarificationError(request.trip_requirements(), caught.value.as_dict())
        )
        assert state == "failed" and outcome["code"] == "requirements_unmet"
        assert outcome["issues"]["issues"][0]["source_refs"][0]["quote"] == text
        assert "Review your brief" not in outcome["action"]
        return
    result = asyncio.run(operation)
    assert result.interpreted_requirements.semantic_requirements[0].strength == "hard"
    assert result.generation_diagnostics.goal_progress[0]["satisfied"] is True
    assert request.additional_preferences == text


def test_original_paris_brief_keeps_hard_visit_and_soft_crowding_preference():
    from backend.app.schemas.request import PlanningRequest

    museum = "Must include: An art museum."
    crowds = "Please avoid: very crowded places."
    text = "\n".join(
        [
            museum,
            crowds,
            "Enjoy parks, waterfronts and gentle outdoor experiences.",
            "Discover local food, with optional places to eat along the way.",
            "Explore historic districts, cultural landmarks and museums.",
            "Travel pace: rich. Include more experiences where time and connections allow.",
            "Prefer walking and public transit and driving where practical.",
        ]
    )
    request = PlanningRequest(
        destination="Paris, Île-de-France, France",
        start_date="2026-10-25",
        end_date="2026-11-02",
        traveler_count=3,
        budget={"amount": "7000", "currency": "EUR"},
        additional_preferences=text,
    )
    data = category_draft(museum).model_dump(mode="json")
    data["semantic_requirements"].append(
        {
            "local_key": "crowds",
            "normalized_text": "Prefer to avoid very crowded places.",
            "kind": "preference",
            "polarity": "avoid",
            "strength": "high",
            "scope": "selected_poi_set",
            "subject_target": {"kind": "party"},
            "source_refs": [{"quote": crowds, "occurrence": 0}],
        }
    )
    before = request.model_dump()
    contract = asyncio.run(
        interpret_preferences(
            request,
            date(2026, 10, 24),
            FakeStructuredLLMClient([InterpretationDraft.model_validate(data)]),
            category_visits=True,
        )
    )
    assert request.model_dump() == before
    assert [r.strength for r in contract.semantic_requirements] == ["hard", "high"]
    assert [r.source_refs[0].quote for r in contract.semantic_requirements] == [museum, crowds]


def test_supported_category_does_not_hide_a_separate_hard_access_requirement():
    text = "A garden is required. Absolutely no stairs."
    data = category_draft("A garden is required.").model_dump(mode="json")
    data["semantic_requirements"].append(
        {
            "local_key": "access",
            "normalized_text": "Absolutely no stairs.",
            "kind": "constraint",
            "polarity": "avoid",
            "strength": "hard",
            "scope": "whole_trip",
            "subject_target": {"kind": "party"},
            "source_refs": [{"quote": "Absolutely no stairs.", "occurrence": 0}],
        }
    )
    with pytest.raises(ClarificationRequired) as caught:
        asyncio.run(
            interpret_preferences(
                make_request(text),
                date(2026, 9, 11),
                FakeStructuredLLMClient([InterpretationDraft.model_validate(data)]),
                category_visits=True,
            )
        )
    assert caught.value.requirement_ids == ("semantic_2",)
    assert caught.value.as_dict()["issues"][0]["source_refs"][0]["quote"] == "Absolutely no stairs."
