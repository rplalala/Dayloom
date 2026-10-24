"""Current requirement wire contract, exercised through the complete service."""

import asyncio
import json
from datetime import date

import pytest
from langchain_core.messages import AIMessage

from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.preference_interpretation import (
    empty_preference_draft,
    interpret_preferences,
)
from backend.tests.request_fixtures import make_request


def run_wire(
    answer,
    text="I like parks.",
    *,
    contract="preference_draft_13",
    observe_prompt=None,
    observe_metadata=None,
):
    class SavedChat:
        def bind(self, **kwargs):
            self.schema = kwargs
            return self

        async def ainvoke(self, messages):
            if observe_prompt:
                observe_prompt(messages[-1].content)
            prompt = json.loads(messages[-1].content)
            payload = answer(prompt) if callable(answer) else answer
            return AIMessage(content=json.dumps(payload), response_metadata={"status": "completed"})

    client = AzureFoundryStructuredLLMClient.__new__(AzureFoundryStructuredLLMClient)
    client._chat_model = SavedChat()
    client._auxiliary_limits = None
    client._capture_secrets = ()
    client._requirement_config = {"contract": contract}
    client.requirement_capture = None
    result = asyncio.run(interpret_preferences(make_request(text), date(2026, 9, 11), client))
    if observe_metadata:
        observe_metadata(client.last_call_metadata)
    return result


def wire_empty():
    data = empty_preference_draft().model_dump(mode="json")
    data["transport_constraint"] = None
    data["daily_pace"] = {"trip_default": data["daily_pace"][0], "date_overrides": []}
    return data


def test_required_trip_default_passes_complete_service():
    result = run_wire(wire_empty())
    assert result.daily_pace[0].profile == "ordinary"
    assert result.daily_pace[0].date is None


def test_dated_count_wire_restores_sources_before_hard_capability_acceptance():
    from backend.tests.services.test_daily_visit_constraints import TEXT, counted_draft

    def answer(prompt):
        data = counted_draft().model_dump(mode="json")
        data.update(transport_constraint=None, daily_pace=wire_empty()["daily_pace"])
        selection = [{"first_ref": 0, "last_ref": len(prompt["source_spans"]) - 1}]
        data["semantic_requirements"][0]["source_refs"] = selection
        data["daily_visit_constraints"][0]["source_refs"] = selection
        return data

    result = run_wire(answer, TEXT, contract="preference_draft_15")
    assert result.contract_version == "interpreted_requirements_6"
    rule = result.daily_visit_constraints[0]
    assert rule.source_refs[0].quote == TEXT
    assert rule.requirement_refs == ("semantic_1",)


def test_dated_wire_requires_an_assessed_count_list_and_supported_schema():
    from backend.app.llm.azure_foundry.client import requirement_wire_format
    from backend.tests.llm.azure_foundry.test_dto import assert_foundry_schema_contract

    schema = requirement_wire_format(current=True, indexed=True, dated=True)["json_schema"][
        "schema"
    ]
    assert_foundry_schema_contract(schema)
    assert "daily_visit_constraints" in schema["required"]
    with pytest.raises(RequirementBoundaryError):
        run_wire(wire_empty(), contract="preference_draft_15")


def test_current_large_source_inventory_is_compact_without_rewriting_original_text():
    data = wire_empty()
    data["daily_visit_constraints"] = []
    original = "Café 😊.\n" * 400
    captured = []
    run_wire(data, original, contract="preference_draft_15", observe_prompt=captured.append)
    prompt = captured[0]
    assert '"source_spans":[' in prompt
    assert '"text":"é"' in prompt
    assert json.loads(prompt)["additional_preferences"] == original
    assert len(json.loads(prompt)["source_spans"]) == len(original)


def test_compact_source_selections_restore_through_complete_interpretation():
    from backend.tests.versions.v1.test_interpreted_requirements import draft_for

    text = "Café 😊. Café 😊."

    def answer(prompt):
        spans = prompt["source_spans"]
        assert spans[8] == {"id": 8, "text": "C"}
        data = draft_for(text).model_dump(mode="json")
        data.update(transport_constraint=None, daily_pace=wire_empty()["daily_pace"])
        data["semantic_requirements"][0]["source_refs"] = [{"first_ref": 8, "last_ref": 14}]
        return data

    result = run_wire(answer, text, contract="preference_draft_14")
    ref = result.semantic_requirements[0].source_refs[0]
    assert (ref.quote, ref.occurrence, ref.start, ref.end) == ("Café 😊.", 1, 8, 15)


@pytest.mark.parametrize("first,last", [(True, 5), (0, False), (-1, 5), (8, 2), (0, 999), ("0", 5)])
def test_compact_invalid_selections_fail_without_correction(first, last):
    from backend.tests.versions.v1.test_interpreted_requirements import draft_for

    data = draft_for("I like parks.").model_dump(mode="json")
    data.update(transport_constraint=None, daily_pace=wire_empty()["daily_pace"])
    data["semantic_requirements"][0]["source_refs"] = [{"first_ref": first, "last_ref": last}]
    with pytest.raises(RequirementBoundaryError) as error:
        run_wire(data, contract="preference_draft_14")
    assert error.value.code == "invalid_source_span"
    assert error.value.errors[0]["loc"] == ("semantic_requirements", 0, "source_refs", 0)


def test_compact_mapping_cannot_restore_against_a_foreign_request_binding():
    from backend.app.llm.azure_foundry.requirement_wire import IndexedSourceSpans, restore_current

    spans = IndexedSourceSpans("request A", "I like parks.")
    other = IndexedSourceSpans("request B", "I like parks.")
    with pytest.raises(RequirementBoundaryError, match="source_request_mismatch"):
        restore_current(wire_empty(), spans, request_sha256=other.request_sha256)


def test_compact_schema_has_integer_endpoints_without_large_enumerations():
    from backend.app.llm.azure_foundry.client import requirement_wire_format
    from backend.tests.llm.azure_foundry.test_dto import assert_foundry_schema_contract

    schema = requirement_wire_format(current=True, indexed=True)["json_schema"]["schema"]
    assert_foundry_schema_contract(schema)
    assert schema["$defs"]["FoundrySourceQuoteDTO"]["properties"] == {
        "first_ref": {"type": "integer"},
        "last_ref": {"type": "integer"},
    }


@pytest.mark.parametrize("pace", [[], None, {"date_overrides": []}])
def test_new_wire_rejects_missing_default_with_field_path(pace):
    data = wire_empty()
    data["daily_pace"] = pace
    with pytest.raises(RequirementBoundaryError) as error:
        run_wire(data)
    assert error.value.stage == "wire_mapping"
    assert error.value.errors[0]["loc"][:1] == ("daily_pace",)


def test_selected_spans_restore_repeated_unicode_source_and_offsets():
    from backend.tests.versions.v1.test_interpreted_requirements import draft_for

    text = "Café 😊. Café 😊."

    def answer(prompt):
        data = draft_for(text).model_dump(mode="json")
        data["transport_constraint"] = None
        data["daily_pace"] = wire_empty()["daily_pace"]
        spans = prompt["source_spans"]
        data["semantic_requirements"][0]["source_refs"] = [
            {"first_id": spans[8]["id"], "last_id": spans[14]["id"]}
        ]
        return data

    result = run_wire(answer, text)
    ref = result.semantic_requirements[0].source_refs[0]
    assert (ref.quote, ref.occurrence, ref.start, ref.end) == ("Café 😊.", 1, 8, 15)


def test_unknown_source_id_is_not_accepted_as_a_quote():
    from backend.tests.versions.v1.test_interpreted_requirements import draft_for

    data = draft_for("I like parks.").model_dump(mode="json")
    data["transport_constraint"] = None
    data["daily_pace"] = wire_empty()["daily_pace"]
    data["semantic_requirements"][0]["source_refs"] = [
        {"first_id": "foreign", "last_id": "foreign"}
    ]
    with pytest.raises(RequirementBoundaryError) as error:
        run_wire(data)
    assert error.value.code == "invalid_source_span"
    assert error.value.errors[0]["loc"] == ("semantic_requirements", 0, "source_refs", 0)


def test_current_wire_uses_only_supported_schema_keywords():
    from backend.app.llm.azure_foundry.client import requirement_wire_format
    from backend.tests.llm.azure_foundry.test_dto import assert_foundry_schema_contract

    schema = requirement_wire_format(current=True)["json_schema"]["schema"]
    assert_foundry_schema_contract(schema)
    assert schema["properties"]["daily_pace"]["required"] == ["trip_default", "date_overrides"]
    assert "quote" not in schema["$defs"]["FoundrySourceQuoteDTO"]["properties"]


def test_long_unbroken_unicode_input_still_has_bounded_source_granularity():
    from backend.tests.versions.v1.test_interpreted_requirements import draft_for

    text = "é" * 400

    def answer(prompt):
        data = draft_for(text[:64]).model_dump(mode="json")
        data.update(transport_constraint=None, daily_pace=wire_empty()["daily_pace"])
        spans = prompt["source_spans"]
        data["semantic_requirements"][0]["source_refs"] = [
            {"first_id": spans[0]["id"], "last_id": spans[63]["id"]}
        ]
        return data

    assert run_wire(answer, text).semantic_requirements[0].source_refs[0].quote == "é" * 64


@pytest.mark.parametrize("pace", [None, []])
def test_explicit_legacy_binding_reads_historical_pace_without_rewriting(pace):
    payload = empty_preference_draft().model_dump(mode="json")
    payload["daily_pace"] = pace
    if pace is None:
        assert run_wire(payload, contract="preference_draft_12").daily_pace is None
    else:
        with pytest.raises(RequirementBoundaryError) as error:
            run_wire(payload, contract="preference_draft_12")
        assert error.value.code == "invalid_daily_pace_scope"


def test_prompt_projection_drift_stops_before_any_model_send(monkeypatch):
    from backend.app.services import preference_interpretation as service

    monkeypatch.setattr(
        service,
        "PREFERENCE_INTERPRETATION_SYSTEM_PROMPT",
        service.PREFERENCE_INTERPRETATION_SYSTEM_PROMPT.replace(
            "Return one default record", "Return the default record"
        ),
    )
    sends = []

    def answer(prompt):
        sends.append(prompt)
        return wire_empty()

    with pytest.raises(RequirementBoundaryError) as error:
        run_wire(answer)
    assert error.value.code == "requirement_prompt_version_mismatch"
    assert error.value.category == "configuration_failure"
    assert sends == []


@pytest.mark.parametrize("body", ["x" * 150, "\u5c55" * 150, "\U0001f60a\u00e9" * 75])
def test_source_inventory_preserves_exact_scope_within_unbroken_text(body):
    from backend.app.llm.azure_foundry.requirement_wire import SourceSpans
    from backend.app.schemas.trip_intent import RequestedPlaceInformation

    spans = SourceSpans("request", "p" * 31 + body + "q" * 43)
    choices = [
        (first, last)
        for first, interval in spans.spans.items()
        if interval[0] == 31
        for last, end in spans.spans.items()
        if end[1] == 181
    ]
    assert choices
    restored = spans.restore({"scope_text": {"first_id": choices[0][0], "last_id": choices[0][1]}})
    assert restored["scope_text"] == body
    assert len(restored["scope_text"]) == 150
    question = RequestedPlaceInformation(
        target_surface="Museum",
        target_source_text="Museum",
        source_text=body,
        requested_facet="admission_fee",
        operational_need=None,
        subject_scope="exhibition",
        **restored,
    )
    assert question.scope_text == body


def test_reversed_and_cross_request_span_endpoints_fail_closed():
    from backend.app.llm.azure_foundry.requirement_wire import SourceSpans

    current, other = SourceSpans("one", "a b"), SourceSpans("two", "a b")
    ids, foreign = list(current.spans), list(other.spans)
    for first, last in [(ids[-1], ids[0]), (foreign[0], foreign[-1])]:
        with pytest.raises(RequirementBoundaryError) as error:
            current.source({"first_id": first, "last_id": last}, ("source_refs", 0))
        assert error.value.code == "invalid_source_span"
        assert error.value.errors[0]["loc"] == ("source_refs", 0)
