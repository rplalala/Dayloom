"""Offline instruction and controlled-output tests, not model accuracy evidence."""

import asyncio
import copy
import json
from datetime import date
from pathlib import Path

import httpx2 as httpx
import pytest

from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
from backend.app.policies.preference_input import PreferenceInputBlocked
from backend.app.schemas.request import PlanningRequest
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.preference_interpretation import interpret_preferences
from backend.app.services.preference_prompts import PREFERENCE_INTERPRETATION_SYSTEM_PROMPT
from backend.tests.llm.azure_foundry.requirement_fixtures import current_response
from backend.tests.llm.azure_foundry.test_requirement_acceptance_harness import response

FIXTURE = Path(__file__).parents[1] / "fixtures/preference_gate/historical_rich_trip_ambiguity.json"


def historical():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def positive():
    saved = historical()
    payload = saved["draft"]
    payload["preference_input_assessment"] = {
        "input_disposition": "VALID",
        "safety_disposition": "CLEAR",
        "issues": [],
    }
    payload["semantic_requirements"].append(
        {
            "local_key": "quality",
            "normalized_text": "The requester prefers a rich and varied trip.",
            "kind": "preference",
            "polarity": "favor",
            "strength": "medium",
            "scope": "itinerary_style",
            "subject_target": {"kind": "party"},
            "experience_goal": None,
            "source_refs": [{"quote": "I also want to enjoy a rich trip", "occurrence": 0}],
        }
    )
    return payload, PlanningRequest.model_validate(saved["request"])


async def interpret(payload, request):
    payload = copy.deepcopy(payload)
    payload["daily_pace"] = None  # Historical style evidence has no structured pace.
    for row in payload["semantic_requirements"]:
        row.setdefault("trip_focus_source", None)  # Synthetic current-wire migration.
    sends = []

    def handler(http_request):
        sends.append(json.loads(http_request.content))
        projected = current_response(payload, http_request)
        return httpx.Response(200, json=response(json.dumps(projected), 1))

    client = AzureFoundryStructuredLLMClient(
        endpoint="https://fixture.invalid/openai/v1",
        deployment="fixture-model",
        api_key="fixture-key",
        http_async_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    try:
        return await interpret_preferences(request, date(2026, 9, 26), client)
    finally:
        await client.aclose()
        assert len(sends) == 1
        assert "Ordinary soft quality/style wishes" in json.dumps(sends[0])


def test_quality_wishes_have_an_explicit_nonblocking_instruction_boundary():
    prompt = PREFERENCE_INTERPRETATION_SYSTEM_PROMPT
    assert "preference_prompt_19" in prompt
    assert "Ordinary soft quality/style wishes do not require a precise definition" in prompt
    assert (
        "I like climbing mountain, I want to visit zoo, I also want to enjoy a rich trip" in prompt
    )
    assert "Do not invent exact counts, exclusive themes, luxury spending" in prompt
    assert "A soft quality wish never cancels a separate genuine input issue" in prompt


def test_historical_quality_misclassification_remains_a_blocked_model_output():
    saved = historical()
    assert saved["prompt_version"] == "preference_prompt_15"
    with pytest.raises(PreferenceInputBlocked) as error:
        asyncio.run(interpret(saved["draft"], PlanningRequest.model_validate(saved["request"])))
    assert error.value.code == "preference_input_blocked"
    assert error.value.issues[0]["source_refs"][0]["quote"] == "I also want to enjoy a rich trip"


@pytest.mark.parametrize(
    "quality",
    [
        "I also want to enjoy a rich trip",
        "I want a varied and enjoyable trip",
        "I want a memorable trip",
    ],
)
def test_synthetic_soft_quality_preserves_goals_sources_and_structured_facts(quality):
    payload, request = positive()
    original = "I also want to enjoy a rich trip"
    request = request.model_copy(
        update={"additional_preferences": request.additional_preferences.replace(original, quality)}
    )
    payload["semantic_requirements"][-1]["source_refs"][0]["quote"] = quality
    payload["semantic_requirements"][-1]["normalized_text"] = quality
    contract = asyncio.run(interpret(payload, request))
    mountain, zoo, style = contract.semantic_requirements
    assert mountain.experience_goal.frequency == "continuing"
    assert zoo.experience_goal.frequency == "one_off"
    for goal in (mountain.experience_goal, zoo.experience_goal):
        assert goal.count is None and goal.trip_scope == "ordinary"
        assert not goal.explicit_primary_exception
    assert style.experience_goal is None and style.strength == "medium"
    assert style.source_refs[0].quote == quality
    assert not contract.visit_requirements and not contract.named_places
    assert contract.requirements == request.trip_requirements()


@pytest.mark.parametrize(
    "kind,disposition,sentences",
    [
        (
            "semantic_ambiguity",
            "CLARIFICATION_REQUIRED",
            ["Apply the mandatory transport restriction I mentioned earlier."],
        ),
        (
            "internal_requirement_contradiction",
            "REWRITE_REQUIRED",
            ["I only want to walk everywhere.", "I must use the metro for every transfer."],
        ),
        (
            "unsupported_request_scope",
            "CLARIFICATION_REQUIRED",
            ["I also want to spend a full day sightseeing in Paris."],
        ),
    ],
)
def test_soft_quality_does_not_cancel_a_separate_real_issue(kind, disposition, sentences):
    payload, request = positive()
    request = request.model_copy(
        update={
            "additional_preferences": request.additional_preferences + ". " + " ".join(sentences)
        }
    )
    issue = copy.deepcopy(historical()["draft"]["preference_input_assessment"]["issues"][0])
    issue.update(
        issue_type=kind,
        source_refs=[{"quote": s, "occurrence": 0} for s in sentences],
        scope="Separate mandatory requirement or scope extension",
    )
    payload["preference_input_assessment"].update(input_disposition=disposition, issues=[issue])
    with pytest.raises(PreferenceInputBlocked) as error:
        asyncio.run(interpret(payload, request))
    assert error.value.input_disposition == disposition
    assert [s["quote"] for s in error.value.issues[0]["source_refs"]] == sentences


def test_soft_quality_does_not_hide_fabricated_provenance():
    payload, request = positive()
    payload["semantic_requirements"][-1]["source_refs"][0]["quote"] = "A fabricated wish."
    with pytest.raises(RequirementBoundaryError):
        asyncio.run(interpret(payload, request))
