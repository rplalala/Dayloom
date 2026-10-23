"""Bounded provider recovery, budget-scope contracts and clean CLI process regressions."""

import asyncio
import subprocess
import sys

import pytest

from backend.app.policies.preference_input import PreferenceInputBlocked
from backend.app.schemas.request import Money
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.preference_interpretation import interpret_preferences
from backend.tests.api.test_product_planning import (
    make_planning_service,
    make_product_payload,
    post_product_planning,
)
from backend.tests.llm.azure_foundry.test_requirement_boundary import interpret
from backend.tests.request_fixtures import make_request
from backend.tests.services.test_preference_input_gate import REFERENCE, draft, issue
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient
from backend.tests.versions.v1.test_interpreted_requirements import draft_for


@pytest.mark.parametrize("version", [0, 1, 2, 3])
def test_clean_process_cli_help(version):
    result = subprocess.run(
        [sys.executable, "-B", f"scripts/run_v{version}.py", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--input-json" in result.stdout


@pytest.mark.parametrize("code", ["content_filter", None, "invalid_json_schema"])
def test_provider_filter_user_action_is_evidence_scoped(code):
    error = RequirementBoundaryError(
        "requirement_provider_failed",
        category="provider_request_rejected",
        provider_diagnostics={"provider_error_code": code, "provider_request_id": "PRIVATE"},
    )
    client = FakeStructuredLLMClient([error])
    payload = {**make_product_payload(), "additional_preferences": "Travel input"}
    status, body = post_product_planning(make_planning_service(client), payload)
    assert len(client.calls) == 1
    if code == "content_filter":
        assert status == 202 and body["state"] == "provider_blocked"
        assert "rewrite" in body["outcome"]["action"].lower()
        assert "content filter" in body["outcome"]["message"]
        assert "action" in error.as_dict()
    else:
        assert status == 202 and body["state"] == "failed"
        assert "action" not in error.as_dict()
    assert "PRIVATE" not in str(body) and "SAFETY_BLOCK" not in str(body)


@pytest.mark.parametrize(
    "text",
    [
        "exclude flights and accommodation from our budget.",
        "exclude accommodation from our budget.",
        "exclude flights from our budget.",
    ],
)
def test_budget_scope_survives_wire_and_does_not_change_amount(text):
    value = draft_for(text)
    parsed, _ = asyncio.run(interpret(value.model_dump(mode="json"), text=text, canonical=False))
    request = make_request(text).model_copy(update={"budget": Money(amount=1600, currency="AUD")})
    before = request.model_dump()
    contract = asyncio.run(
        interpret_preferences(request, REFERENCE, FakeStructuredLLMClient([parsed]))
    )
    assert contract.requirements.budget == request.budget
    assert contract.semantic_requirements[0].source_refs[0].quote == text
    assert request.model_dump() == before


@pytest.mark.parametrize(
    "text,field",
    [
        ("Use 800 AUD instead.", "budget.amount"),
        ("The budget is 1600 AUD per person.", "budget.amount"),
        ("Use USD instead.", "budget.currency"),
    ],
)
def test_true_budget_conflicts_remain_blocked(text, field):
    value = draft(
        issue(
            "structured_request_conflict",
            text=text,
            related_field=field,
            operational_conflict_index=0,
        ),
        operational_conflicts=[{"field": field, "source_refs": [{"quote": text, "occurrence": 0}]}],
    )
    parsed, _ = asyncio.run(interpret(value.model_dump(mode="json"), text=text, canonical=False))
    request = make_request(text).model_copy(update={"budget": Money(amount=1600, currency="AUD")})
    with pytest.raises(PreferenceInputBlocked):
        asyncio.run(interpret_preferences(request, REFERENCE, FakeStructuredLLMClient([parsed])))


def test_public_service_exports_remain_available():
    from backend.app.services import PlanningService
    from backend.app.services.planning import PlanningService as Direct

    assert PlanningService is Direct
