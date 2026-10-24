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
