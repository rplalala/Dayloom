"""Product JSON and SSE retain current V3 completion semantics through presentation."""

import json
from datetime import date

import pytest

from backend.app.schemas.generation_diagnostics import GenerationDiagnostics
from backend.app.schemas.planning import PlanningResult
from backend.app.services.planning import PlanningService
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.fakes import FixedDateProvider
from backend.tests.versions.v0.fakes import make_itinerary


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("completion", ["incomplete", "complete", "unassessed"])
def test_product_completion_survives_public_response(stream, completion):
    calls = []
    reasons = ["required_visit_obligation_unmet"] if completion == "incomplete" else []

    class Runtime:
        async def run(self, version, request, **kwargs):
            calls.append(version)
            return PlanningResult(
                system_version=version,
                requirements=request.trip_requirements(),
                itinerary=make_itinerary(),
                generation_diagnostics=GenerationDiagnostics(
                    goal_progress=(
                        {
                            "soft": True,
                            "preference": "Museums",
                            "expected": 2,
                            "matched": 1,
                            "remaining": 1,
                            "coverage_status": "gap",
                            "target_origin": "current_trip_focus",
                            "focus_source": "PRIVATE",
                            "basis": "model_semantic_judgment_not_operating_fact",
                        },
                    ),
                    policy_completion=completion,
                    policy_issues=tuple({"reason": r, "internal": "PRIVATE"} for r in reasons),
                    days=(),
                    days_meeting_default_target=0,
                    days_below_target=0,
                    days_above_target=0,
                    days_unassessable=0,
                    empty_days=0,
                    days_with_zero_main_pois=0,
                    scheduled_unique_supply=None,
                    unused_supply=None,
                    cross_day_repeated_visits=0,
                ),
            )

    class Introductions:
        async def generate(self, *args):
            return {}

    service = PlanningService(
        Runtime(), FixedDateProvider(date(2026, 9, 11)), introductions=Introductions()
    )

    from backend.tests.api.test_product_planning import post_product_planning

    status, payload = post_product_planning(service, make_product_payload(), stream=stream)
    if stream:
        assert status == 200
        event = next(e for e in payload if e.get("type") == "result")
        assert event["task_id"] and event["preview_id"]
        body = event["result"]
    else:
        assert status == 202 and payload["state"] == "completed"
        body = payload["preview"]["snapshot"]
    assert calls == ["v3"]
    completion_result = body["completion"]
    assert completion_result["policy_completion"] == completion
    assert completion_result["preference_coverage"] == [
        {
            "preference": "Museums",
            "target": 2,
            "scheduled": 1,
            "remaining": 1,
            "status": "gap",
            "target_origin": "current_trip_focus",
            "basis": "model_semantic_judgment_not_operating_fact",
        }
    ]
    assert completion_result["policy_reasons"] == reasons
    assert body["days"]
    assert "PRIVATE" not in json.dumps(payload) and "generation_diagnostics" not in body
