"""Production tools transport delegates offsets to sourced application time context."""

import asyncio
import copy
import json

import pytest

from backend.app.llm.client import StructuredOutputError
from backend.app.schemas.itinerary_projection import V1Itinerary
from backend.tests.llm.azure_foundry.test_client import FakeChatOpenAI, make_activity, make_client


def test_primary_civil_wire_maps_null_offsets_after_reference_restoration(monkeypatch):
    activity = make_activity().model_dump(mode="json")
    activity.pop("transport")
    activity["source_place_id"] = "p01"
    for key, clock in [("start_time", "10:00:00"), ("end_time", "11:00:00")]:
        activity[key] = {"date": "2026-10-25", "time": clock, "utc_offset": None}
    raw = {
        "output_version": "itinerary_3",
        "destination": "Paris",
        "start_date": "2026-10-25",
        "end_date": "2026-10-25",
        "days": [{"date": "2026-10-25", "activities": [activity]}],
    }
    original = copy.deepcopy(raw)
    FakeChatOpenAI.response = raw
    client = make_client(monkeypatch)
    prompt = "<external_evidence>\n" + json.dumps(
        {"places": [{"place_id": "canonical", "timezone_id": "Europe/Paris"}]}
    )
    result = asyncio.run(
        client.generate_structured(
            system_prompt="tools_civil_time_1", user_prompt=prompt, response_schema=V1Itinerary
        )
    )
    assert result.days[0].activities[0].start_time.isoformat() == "2026-10-25T10:00:00+01:00"
    assert result.days[0].activities[0].source_place_id == "canonical"
    assert raw == original


def test_repair_civil_wire_uses_same_time_context_after_identity_restoration(monkeypatch):
    raw = {
        "edits": [
            {
                "operation": "retime",
                "activity_id": "a01",
                "place_id": None,
                "date": "2026-10-25",
                "start_time": "2026-10-25T10:00:00",
                "end_time": "2026-10-25T11:00:00",
            }
        ],
        "target_dispositions": [],
    }
    original = copy.deepcopy(raw)
    FakeChatOpenAI.response = raw
    client = make_client(monkeypatch)
    context = {
        "schedule_time_context": {
            "version": "tools_civil_time_1",
            "places": [{"place_id": "canonical", "timezone_id": "Europe/Paris"}],
        },
        "editable_activities": [{"activity_id": "activity", "source_place_id": "canonical"}],
    }
    result = asyncio.run(
        client.generate_repair_structured(
            system_prompt="tools_civil_time_1", user_prompt=json.dumps(context)
        )
    )
    assert result.edits[0].start_time.isoformat() == "2026-10-25T10:00:00+01:00"
    assert result.edits[0].activity_id == "activity"
    assert raw == original


def test_civil_wire_schema_is_foundry_compatible():
    from backend.app.llm.azure_foundry.civil_time import (
        FoundryCivilItineraryDTO,
        FoundryCivilPatchDTO,
    )
    from backend.tests.llm.azure_foundry.test_dto import assert_foundry_schema_contract

    assert_foundry_schema_contract(FoundryCivilItineraryDTO.model_json_schema())
    assert_foundry_schema_contract(FoundryCivilPatchDTO.model_json_schema())


def test_overlong_repair_reason_preserves_the_mapped_patch_for_caller_owned_compression(
    monkeypatch,
):
    reason = "Route support is unavailable. " * 9
    raw = {
        "edits": [],
        "target_dispositions": [
            {"target_id": "t01", "disposition": "unresolved", "reason": reason}
        ],
    }
    FakeChatOpenAI.response = raw
    client = make_client(monkeypatch)
    payload = {
        "schedule_time_context": {"version": "tools_civil_time_1", "places": []},
        "target_worksheet": [{"target_id": "canonical-target"}],
    }
    with pytest.raises(StructuredOutputError) as caught:
        asyncio.run(
            client.generate_repair_structured(
                system_prompt="Repair", user_prompt=json.dumps(payload)
            )
        )
    assert caught.value.candidate["target_dispositions"] == [
        {"target_id": "canonical-target", "disposition": "unresolved", "reason": reason}
    ]
    assert FakeChatOpenAI.structured_output_count == 1
    assert raw["target_dispositions"][0]["reason"] == reason


def test_reason_compression_uses_a_compatible_text_only_schema_and_per_call_options(monkeypatch):
    from backend.tests.llm.azure_foundry.test_dto import assert_foundry_schema_contract

    raw = {"reasons": [{"reason_ref": "r01", "reason": "No supported route."}]}
    FakeChatOpenAI.response = raw
    client = make_client(monkeypatch)
    result = asyncio.run(
        client.compress_repair_reasons_structured(
            system_prompt="Compress", user_prompt='{"reasons": []}', output_tokens=8192
        )
    )
    assert result.model_dump() == raw
    assert_foundry_schema_contract(FakeChatOpenAI.schema)
    assert FakeChatOpenAI.structured_kwargs["max_output_tokens"] == 8192
    assert FakeChatOpenAI.init_kwargs["max_retries"] == 0
    assert FakeChatOpenAI.structured_output_count == 1
