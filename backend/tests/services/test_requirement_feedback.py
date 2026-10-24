"""Product outcomes retain actionable, safe requirement failures."""

import asyncio
from datetime import date

import pytest

from backend.app.product.task_outcomes import failure_outcome
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.services.planning import PlanningNeedsClarificationError
from backend.app.services.preference_interpretation import interpret_preferences
from backend.tests.request_fixtures import make_request
from backend.tests.services.test_required_categories import category_draft
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient


@pytest.mark.parametrize(
    "kind,code",
    [
        ("resource", "planning_resource_limit"),
        ("timeout", "planning_timeout"),
        ("provider", "provider_unavailable"),
        ("evidence", "requirements_unmet"),
        ("unknown", "planning_failed"),
    ],
)
def test_infrastructure_failures_keep_original_requirements_without_requesting_rewording(
    kind, code
):
    from backend.app.integrations.http import ProviderHTTPError
    from backend.app.schemas.poi_semantics import SemanticPreparationLimit
    from backend.app.services.generation_resources import GenerationResourceError

    failures = {
        "resource": GenerationResourceError("private resource details"),
        "timeout": TimeoutError("private timeout details"),
        "provider": ProviderHTTPError("private provider details"),
        "evidence": SemanticPreparationLimit("required_primary_role_not_qualified"),
        "unknown": RuntimeError("private failure details"),
    }
    outer = RuntimeError("wrapper")
    outer.__cause__ = failures[kind]
    state, outcome = failure_outcome(outer)
    assert state == "failed" and outcome["code"] == code
    assert "original requirements have been kept" in outcome["action"]
    assert "Review your brief" not in outcome["action"]
    assert "private" not in str(outcome)


def test_unsupported_hard_requirement_retains_its_source_and_reason_in_product_outcome():
    text = "A local craft workshop is required."
    request = make_request(text)
    with pytest.raises(ClarificationRequired) as caught:
        asyncio.run(
            interpret_preferences(
                request,
                date(2026, 9, 11),
                FakeStructuredLLMClient([category_draft(text)]),
            )
        )
    state, outcome = failure_outcome(
        PlanningNeedsClarificationError(
            request.trip_requirements(),
            caught.value.as_dict(),
        )
    )
    assert state == "needs_clarification"
    assert outcome["issues"]["code"] == "unsupported_hard_requirements"
    assert outcome["issues"]["requirement_ids"] == ["semantic_1"]
    issue = outcome["issues"]["issues"][0]
    assert issue["source_refs"][0]["quote"] == text
    assert "cannot verify" in issue["reason"]
    assert "cannot verify" in outcome["message"]
    assert "clarify" not in outcome["message"].lower()
    assert "Review your brief" not in outcome["action"]


@pytest.mark.parametrize("code", ["no_eligible_candidates", "no_eligible_details"])
def test_acquisition_shortfalls_do_not_blame_the_users_wording(code):
    state, outcome = failure_outcome(
        PlanningNeedsClarificationError(
            make_request().trip_requirements(),
            ClarificationRequired(code).as_dict(),
        )
    )
    assert state == "failed"
    assert outcome["code"] == "requirements_unmet"
    assert outcome["issues"]["code"] == code
    assert outcome["issues"]["issues"][0]["reason"]
    assert "clarify" not in outcome["message"].lower()
