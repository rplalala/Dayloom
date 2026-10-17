"""Fake drafts verify representation and policy, not model language understanding."""

import asyncio
from datetime import date

import pytest

from backend.app.policies.interpreted_requirements import canonicalize_requirements
from backend.app.schemas.interpreted_requirements import ClarificationRequired, InterpretationDraft
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.preference_interpretation import (
    empty_preference_draft,
    interpret_preferences,
)
from backend.app.services.preference_prompts import PREFERENCE_INTERPRETATION_SYSTEM_PROMPT
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient


def policy_draft(text, target, *, label=None, strength="hard", issues=()):
    data = empty_preference_draft().model_dump(mode="json")
    data["semantic_requirements"] = [
        {
            "local_key": "condition",
            "normalized_text": text,
            "kind": "constraint" if strength == "hard" else "preference",
            "polarity": "avoid",
            "strength": strength,
            "scope": "whole_trip",
            "subject_target": target,
            "source_refs": [{"quote": text, "occurrence": 0}],
        }
    ]
    if label:
        data["subjects"] = [
            {
                "local_key": "person",
                "label": label,
                "source_refs": [{"quote": text, "occurrence": 0}],
            }
        ]
    data["extraction_issues"] = issues
    return InterpretationDraft.model_validate(data)


@pytest.mark.parametrize(
    "text,label",
    [
        ("Absolutely no stairs.", None),
        ("My mother absolutely cannot use stairs.", "Mother"),
        ("My parents cannot use stairs; my friends may use them.", "Parents"),
    ],
)
def test_request_and_person_hard_targets_reach_existing_readiness(text, label):
    target = (
        {"kind": "specified", "first_ref": "person", "additional_refs": []}
        if label
        else {"kind": "party"}
    )
    draft = policy_draft(text, target, label=label)
    request = make_request(text)
    before = request.model_dump()
    contract = canonicalize_requirements(draft, request)
    item = contract.semantic_requirements[0]
    assert item.subject_refs == (("subject_1",) if label else ("party",))
    assert item.normalized_text == text  # Includes the explicit subgroup exception.
    assert [s.label for s in contract.subjects] == ([label] if label else [])
    assert contract.requirements == request.trip_requirements()
    client = FakeStructuredLLMClient([draft])
    with pytest.raises(ClarificationRequired) as error:
        asyncio.run(interpret_preferences(request, date(2026, 9, 11), client))
    assert error.value.code == "unsupported_hard_requirements"
    assert request.model_dump() == before and len(client.calls) == 1
    assert client.calls[0].system_prompt == PREFERENCE_INTERPRETATION_SYSTEM_PROMPT


def test_ambiguous_pronoun_is_not_overwritten_by_whole_trip_or_hard():
    text = "My mother and sister are coming. She absolutely cannot use stairs."
    draft = policy_draft(
        text,
        {"kind": "unresolved", "reason": "Two possible antecedents"},
        issues=("The pronoun could refer to either person.",),
    )
    with pytest.raises(ClarificationRequired) as error:
        canonicalize_requirements(draft, make_request(text))
    assert error.value.code == "extraction_ambiguity"


def test_soft_request_condition_stays_soft_and_preserves_form():
    text = "Prefer fewer transfers, but we can compromise."
    request = make_request(text)
    draft = policy_draft(text, {"kind": "party"}, strength="medium")
    result = asyncio.run(
        interpret_preferences(request, date(2026, 9, 11), FakeStructuredLLMClient([draft]))
    )
    assert result.semantic_requirements[0].strength == "medium"
    assert result.requirements == request.trip_requirements()


@pytest.mark.parametrize("invalid", ["reference", "source"])
def test_request_applicability_does_not_bypass_grounding(invalid):
    text = "Absolutely no stairs."
    target = (
        {"kind": "specified", "first_ref": "missing", "additional_refs": []}
        if invalid == "reference"
        else {"kind": "party"}
    )
    draft = policy_draft(text if invalid == "reference" else "Invented quote", target)
    with pytest.raises(RequirementBoundaryError):
        canonicalize_requirements(draft, make_request(text))


@pytest.mark.parametrize("draft,prompt", [(12, 19), (13, 20), (14, 21), (15, 22)])
def test_prompt_and_capture_version_wiring(draft, prompt):
    from backend.tests.llm.azure_foundry.test_requirement_wire import run_wire, wire_empty

    assert (
        "Request applicability does not assert personal attributes"
        in PREFERENCE_INTERPRETATION_SYSTEM_PROMPT
    )
    assert "missing personal attribution" in PREFERENCE_INTERPRETATION_SYSTEM_PROMPT
    payload = empty_preference_draft().model_dump(mode="json") if draft == 12 else wire_empty()
    if draft == 15:
        payload["daily_visit_constraints"] = []
    captured = []
    run_wire(payload, contract=f"preference_draft_{draft}", observe_metadata=captured.append)
    assert captured[0]["prompt_version"] == f"preference_prompt_{prompt}"
    assert captured[0]["schema_version"] == f"preference_draft_{draft}"


def test_mother_hard_and_father_soft_remain_separate():
    first = "My mother absolutely cannot use stairs."
    second = "My father prefers architecture."
    data = policy_draft(
        first,
        {"kind": "specified", "first_ref": "person", "additional_refs": []},
        label="Mother",
    ).model_dump(mode="json")
    other = policy_draft(
        second,
        {"kind": "specified", "first_ref": "father", "additional_refs": []},
        strength="medium",
    ).model_dump(mode="json")["semantic_requirements"][0]
    other.update(local_key="architecture", polarity="favor", scope="individual_poi")
    data["semantic_requirements"].append(other)
    data["subjects"].append(
        {
            "local_key": "father",
            "label": "Father",
            "source_refs": [{"quote": second, "occurrence": 0}],
        }
    )
    contract = canonicalize_requirements(
        InterpretationDraft.model_validate(data), make_request(first + " " + second)
    )
    assert [r.subject_refs for r in contract.semantic_requirements] == [
        ("subject_1",),
        ("subject_2",),
    ]
    assert [r.strength for r in contract.semantic_requirements] == ["hard", "medium"]
