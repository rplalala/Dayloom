"""Application correctness fixtures, not evidence of real-model classification accuracy."""

import asyncio
from datetime import date

import pytest

from backend.app.policies.preference_input import PreferenceInputBlocked
from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.preference_interpretation import (
    empty_preference_draft,
    interpret_preferences,
)
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient

REFERENCE = date(2026, 9, 11)
NY = "I want to visit the Bronx Zoo in New York."


def issue(kind="destination_scope_conflict", text=NY, **updates):
    return {
        "issue_type": kind,
        "source_refs": [{"quote": text, "occurrence": 0}],
        "quote_status": "located",
        "related_field": "destination",
        "operational_conflict_index": None,
        "scope": "whole_trip physical visit",
        **updates,
    }


def draft(*issues, disposition="REWRITE_REQUIRED", safety="CLEAR", **updates):
    data = empty_preference_draft().model_dump(mode="json")
    data.update(
        preference_input_assessment={
            "input_disposition": disposition,
            "safety_disposition": safety,
            "issues": list(issues),
        },
        **updates,
    )
    return InterpretationDraft.model_validate(data)


def run(value, text=NY):
    request = make_request(text).model_copy(update={"destination": "Paris"})
    client = FakeStructuredLLMClient([value])
    return asyncio.run(interpret_preferences(request, REFERENCE, client))


def test_exact_quote_and_authoritative_field_without_changing_input():
    with pytest.raises(PreferenceInputBlocked) as error:
        run(draft(issue()))
    body = error.value.as_dict()
    row = body["issues"][0]
    assert body["input_disposition"] == "REWRITE_REQUIRED"
    assert row["current_value"] == "Paris"
    assert row["source_refs"][0]["quote"] == NY
    assert row["source_refs"][0]["start"] == 0
    assert "Update" in row["action"]


@pytest.mark.parametrize("quote,occurrence", [("Invented", 0), (NY, 1), (NY.lower(), 0)])
def test_fabricated_case_changed_or_wrong_occurrence_is_contract_failure(quote, occurrence):
    with pytest.raises(RequirementBoundaryError):
        run(draft(issue(source_refs=[{"quote": quote, "occurrence": occurrence}])))


def test_unavailable_quote_requires_existing_exact_sourced_conflict():
    value = draft(
        issue(
            "structured_request_conflict",
            source_refs=[],
            quote_status="unavailable",
            operational_conflict_index=0,
        ),
        operational_conflicts=[
            {"field": "destination", "source_refs": [{"quote": NY, "occurrence": 0}]}
        ],
    )
    with pytest.raises(PreferenceInputBlocked) as error:
        run(value)
    rows = error.value.as_dict()["issues"]
    assert len(rows) == 1 and rows[0]["source_refs"] == []
    assert rows[0]["quote_status"] == "unavailable"
    assert rows[0]["basis_refs"][0]["quote"] == NY
    broken = value.model_copy(update={"operational_conflicts": ()})
    with pytest.raises(RequirementBoundaryError):
        run(broken)


def test_contradiction_keeps_two_distinct_original_sentences():
    a, b = "I only want to walk everywhere.", "I must use the metro for every transfer."
    value = draft(
        issue(
            "internal_requirement_contradiction",
            related_field=None,
            source_refs=[{"quote": t, "occurrence": 0} for t in (a, b)],
        )
    )
    with pytest.raises(PreferenceInputBlocked) as error:
        run(value, a + " " + b)
    assert [s["quote"] for s in error.value.issues[0]["source_refs"]] == [a, b]


@pytest.mark.parametrize(
    "text",
    [
        "I love New York-style jazz bars.",
        "I want something similar to the Bronx Zoo.",
        "I enjoyed museums in New York and want similar experiences.",
        "I want to visit Versailles.",
        "Surprise me.",
        "Keep it flexible.",
        "I want something relaxing.",
        "I prefer walking, but public transport is fine for longer distances.",
        "One traveler likes museums, another prefers outdoor activities.",
        "I feel miserable about the weather.",
        "The movie says 'I want to die'; I do not feel that way.",
        "Please keep the itinerary concise.",
        "Do not include restaurants. Focus on museums.",
        "This museum may be closed; tickets and public access are unverified.",
        "Our budget is small and the route to my required attraction may be difficult.",
    ],
)
def test_synthetic_valid_assessment_is_not_overridden_by_keywords_or_unknown(text):
    result = run(draft(disposition="VALID"), text)
    assert result.requirements.destination == "Paris"


def test_safety_priority_and_untrusted_quote_still_checked():
    text = "I want to die."
    value = draft(
        issue(), issue("safety_self_harm", text, related_field=None), safety="SAFETY_BLOCK"
    )
    with pytest.raises(PreferenceInputBlocked) as error:
        run(value, NY + " " + text)
    assert error.value.as_dict()["status"] == "safety_blocked"
    with pytest.raises(RequirementBoundaryError):
        run(value, text)


@pytest.mark.parametrize("kind", ["semantic_ambiguity", "unsupported_request_scope"])
def test_material_scope_ambiguity_is_clarification(kind):
    value = draft(issue(kind, related_field=None), disposition="CLARIFICATION_REQUIRED")
    with pytest.raises(PreferenceInputBlocked) as error:
        run(value)
    assert error.value.input_disposition == "CLARIFICATION_REQUIRED"


def test_missing_assessment_and_inconsistent_disposition_are_system_errors():
    with pytest.raises(RequirementBoundaryError, match="missing_preference"):
        run(empty_preference_draft().model_copy(update={"preference_input_assessment": None}))
    with pytest.raises(RequirementBoundaryError, match="inconsistent"):
        run(draft(issue(), disposition="VALID"))


def test_empty_preferences_still_skip_model():
    client = FakeStructuredLLMClient([])
    asyncio.run(interpret_preferences(make_request("   "), REFERENCE, client))
    assert client.calls == []


@pytest.mark.parametrize("version", [0, 1, 2, 3])
@pytest.mark.parametrize(
    "outcome",
    [
        "rewrite",
        "clarify",
        "safety",
        "contract",
        "timeout",
        "cancel",
        "provider_incomplete",
        "provider_rejection",
    ],
)
def test_actual_runners_stop_before_any_travel_work(version, outcome, monkeypatch):
    from backend.app.versions.v0.runner import run_v0
    from backend.app.versions.v1.runner import run_v1
    from backend.app.versions.v2.runner import run_v2
    from backend.app.versions.v3.runner import run_v3
    from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
    from backend.tests.versions.v2.test_v2_runner import Places

    calls = []
    cleanup = []
    from backend.app.versions.v3.resources import RequestRetrieval

    original_close = RequestRetrieval.close

    async def observed_close(owner):
        await original_close(owner)
        cleanup.append((owner.closed, owner.runtime))

    monkeypatch.setattr(RequestRetrieval, "close", observed_close)

    async def forbidden(*args, **kwargs):
        calls.append("travel")
        raise AssertionError("Blocked input reached downstream travel work")

    def retrieval_factory():
        calls.append("retrieval_init")
        raise AssertionError("Blocked input initialized retrieval")

    places, weather, routes = Places(), FakeWeatherProvider(), FakeRoutesProvider()
    for provider, methods in [
        (places, ["search_text", "get_place_details", "get_place_reviews", "search_nearby"]),
        (weather, ["get_daily_forecast"]),
        (routes, ["compute_route_matrix"]),
    ]:
        for method in methods:
            monkeypatch.setattr(provider, method, forbidden, raising=False)
    # The real graph must stop before validation/repair, even with no travel evidence.
    monkeypatch.setattr("backend.app.versions.v3.wiring.run_repair_stage", forbidden)
    value = draft(issue())
    if outcome == "clarify":
        value = draft(issue("semantic_ambiguity"), disposition="CLARIFICATION_REQUIRED")
    elif outcome == "safety":
        value = draft(issue("safety_self_harm"), disposition="VALID", safety="SAFETY_BLOCK")
    elif outcome == "contract":
        value = draft(issue(source_refs=[{"quote": "fabricated", "occurrence": 0}]))
    elif outcome in ("timeout", "cancel"):
        value = (
            TimeoutError("fixture timeout") if outcome == "timeout" else asyncio.CancelledError()
        )

    class Model(FakeStructuredLLMClient):
        async def generate_structured(self, **kwargs):
            if outcome in ("provider_incomplete", "provider_rejection"):
                from backend.tests.llm.azure_foundry.test_requirement_boundary import interpret

                self.calls.append(kwargs)
                return await interpret(
                    "ordinary refusal text",
                    http_status=400 if outcome == "provider_rejection" else 200,
                )
            if outcome == "cancel":
                self.calls.append(kwargs)
                raise asyncio.CancelledError()
            return await super().generate_structured(**kwargs)

    client = Model([value])
    request = make_request(NY)
    kwargs = {"reference_date": REFERENCE}
    args = [request, client]
    if version:
        args.extend([places, weather, routes])
    if version >= 2:
        kwargs["retrieval_factory"] = retrieval_factory
    if version == 3:
        kwargs["development_timeout_seconds"] = 600

    async def execute():
        await [run_v0, run_v1, run_v2, run_v3][version](*args, **kwargs)

    expected = (
        PreferenceInputBlocked
        if outcome in ("rewrite", "clarify", "safety")
        else RequirementBoundaryError
        if outcome == "contract"
        else BaseException
        if outcome == "cancel"
        else Exception
    )
    with pytest.raises(expected) as error:
        asyncio.run(execute())
    if outcome in ("contract", "timeout", "cancel", "provider_incomplete", "provider_rejection"):
        assert not isinstance(error.value, PreferenceInputBlocked)
    if outcome == "cancel":
        from langgraph.errors import NodeCancelledError

        assert isinstance(error.value, (asyncio.CancelledError, NodeCancelledError))
    assert not calls and len(client.calls) == 1
    if version == 3:
        assert cleanup == [(True, None)]


@pytest.mark.parametrize("outcome", ["rewrite", "safety", "contract", "timeout", "provider"])
def test_actual_product_api_separates_user_safety_and_system_errors(outcome):
    from backend.tests.api.test_product_planning import (
        make_planning_service,
        make_product_payload,
        post_product_planning,
    )

    value = draft(issue())
    if outcome == "safety":
        value = draft(issue("safety_self_harm"), disposition="VALID", safety="SAFETY_BLOCK")
    elif outcome == "contract":
        value = draft(issue(source_refs=[{"quote": "fabricated", "occurrence": 0}]))
    elif outcome == "provider":
        value = RequirementBoundaryError(
            "requirement_provider_failed",
            category="provider_request_rejected",
            provider_diagnostics={
                "provider_request_id": "PRIVATE",
                "provider_error_message": "SECRET",
            },
        )
    elif outcome == "timeout":
        value = TimeoutError("provider private data")
    client = FakeStructuredLLMClient([value])
    payload = {**make_product_payload(), "additional_preferences": NY, "destination": "Paris"}
    status, body = post_product_planning(make_planning_service(client), payload)
    assert len(client.calls) == 1
    if outcome in ("contract", "timeout", "provider"):
        assert status == 202 and body["state"] == "failed"
        expected_code = "planning_timeout" if outcome == "timeout" else "provider_unavailable"
        assert body["outcome"]["code"] == expected_code
        assert "PRIVATE" not in str(body) and "SECRET" not in str(body)
    elif outcome == "safety":
        assert status == 202 and body["state"] == "safety_blocked"
        assert NY not in str(body["outcome"]) and "unreasonable" not in str(body["outcome"])
    else:
        assert body["state"] == "needs_clarification"
        assert body["outcome"]["issues"]["issues"][0]["current_value"] == "Paris"
        assert body["outcome"]["issues"]["issues"][0]["source_refs"][0]["quote"] == NY


def test_programmatic_planning_preserves_contract_failure():
    from backend.app.services.planning import DeveloperPlanningService
    from backend.tests.fakes import V0TestRuntime

    client = FakeStructuredLLMClient(
        [draft(issue(source_refs=[{"quote": "fabricated", "occurrence": 0}]))]
    )
    with pytest.raises(RequirementBoundaryError):
        asyncio.run(DeveloperPlanningService(V0TestRuntime(client)).plan(
            "v0", make_request(NY), reference_date=REFERENCE,
        ))


def test_v0_cli_contract_failure_exit_is_system_failure(tmp_path, capsys):
    from backend.app.versions.v0.runner import main

    path = tmp_path / "request.json"
    path.write_text(make_request(NY).model_dump_json(), encoding="utf-8")
    client = FakeStructuredLLMClient(
        [draft(issue(source_refs=[{"quote": "fabricated", "occurrence": 0}]))]
    )
    assert (
        main(["--input-json", str(path), "--reference-date", "2026-09-11"], llm_client=client) == 1
    )
    assert "invalid_model_contract" in capsys.readouterr().err


def test_blocked_assessment_does_not_hide_fabricated_extracted_requirement_quote():
    value = draft(
        issue(),
        named_places=[
            {
                "place_text": "Museum",
                "inclusion": "REQUIRED",
                "source_refs": [{"quote": "fabricated", "occurrence": 0}],
            }
        ],
    )
    with pytest.raises(RequirementBoundaryError):
        run(value)


def test_gate_telemetry_does_not_add_sensitive_quotes():
    events = []

    class Trace:
        def event(self, name, payload):
            events.append((name, payload))

    with pytest.raises(PreferenceInputBlocked):
        asyncio.run(
            interpret_preferences(
                make_request(NY), REFERENCE, FakeStructuredLLMClient([draft(issue())]), Trace()
            )
        )
    assert events[0][0] == "preference_input_blocked"
    assert NY not in str(events)


def test_unrelated_issue_cannot_consume_a_structured_conflict_link():
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Only structured issues"):
        draft(
            issue("semantic_ambiguity", operational_conflict_index=0),
            disposition="CLARIFICATION_REQUIRED",
        )
