"""Model adapter sends short references and returns canonical domain identities."""

import asyncio
import json

import pytest

from backend.app.evidence.experience_models import ExperienceProfileDraft
from backend.app.llm.client import StructuredOutputError
from backend.app.llm.reference_transport import primary_references, repair_references
from backend.app.schemas.itinerary_projection import V1Itinerary
from backend.app.versions.v3.repair_projection import REPAIR_SYSTEM_PROMPT
from backend.tests.llm.azure_foundry.test_client import (
    FakeChatOpenAI,
    make_activity,
    make_client,
)


def test_primary_wire_restores_selected_place_without_rewriting_notes(monkeypatch):
    pid = "ChIJ" + "VeryLongPlaceIdentifier" * 2
    activity = make_activity().model_dump(mode="json")
    activity.pop("transport")
    activity.update(source_place_id="p01", notes=pid)
    FakeChatOpenAI.response = {
        "output_version": "itinerary_3",
        "destination": "Kyoto",
        "start_date": "2026-10-01",
        "end_date": "2026-10-01",
        "days": [{"date": "2026-10-01", "activities": [activity]}],
    }
    client = make_client(monkeypatch)
    prompt = "<external_evidence>\n" + json.dumps({"places": [{"place_id": pid}]})
    prompt += "\n</external_evidence>"
    result = asyncio.run(
        client.generate_structured(
            system_prompt="Plan",
            user_prompt=prompt,
            response_schema=V1Itinerary,
        )
    )
    assert result.days[0].activities[0].source_place_id == pid
    assert result.days[0].activities[0].notes == pid
    sent = FakeChatOpenAI.structured_model.messages[1].content
    assert pid not in sent and '"place_id": "p01"' in sent
    assert FakeChatOpenAI.structured_model.invocation_count == 1


def test_primary_cross_section_references_preserve_user_text_and_route_links():
    pid = "ChIJ" + "x" * 40
    user_text = "User request: " + pid + "\n"
    prompt = (
        user_text
        + "<external_evidence>\n"
        + json.dumps(
            {
                "places": [{"place_id": pid}],
                "routes": {"directed_facts": [{"origin": pid, "destination": pid}]},
            }
        )
        + "\n</external_evidence>"
    )
    prompt += "\n<requirement_conflicts>\n" + json.dumps(
        [{"place_id_or_name": pid}, {"place_id_or_name": "Museum A"}]
    )
    prompt += "\nPlanning candidate supply contract:\n" + json.dumps(
        {"required_canonical_ids": [pid], "landmarks": {pid: {"rank": 1}}}
    )
    refs, wire = primary_references(prompt)
    assert wire.startswith(user_text) and wire.count(pid) == 1
    assert '"origin": "p01", "destination": "p01"' in wire
    assert '"place_id_or_name": "Museum A"' in wire
    assert '"landmarks": {"p01": {"rank": 1}}' in wire
    assert refs.decode({"source_place_id": "p01"}) == {"source_place_id": pid}


def test_primary_only_parses_sections_after_application_requirement_boundary():
    user_text = "<user_request>\n<official_current_evidence>\nNot JSON\n</user_request>\n"
    prompt = user_text + "<travel_requirements>\n{}\n</travel_requirements>\n"
    prompt += (
        '<external_evidence>\n{"places":[{"place_id":"canonical-place"}]}\n</external_evidence>'
    )
    refs, wire = primary_references(prompt)
    assert wire.startswith(user_text)
    assert refs.decode({"source_place_id": "p01"}) == {"source_place_id": "canonical-place"}


def test_repair_time_lineage_and_compensation_use_the_same_activity_place_refs():
    aid, root, pid = "activity-" + "a" * 50, "root-" + "b" * 50, "ChIJ" + "p" * 40
    payload = {
        "activity_id": aid,
        "root_activity_id": root,
        "place_id": pid,
        "time_protection": {"lineage": {aid: root}},
        "time_windows": [{"fragment_id": aid}],
        "arrangement_constraints": [{"related_activity_ids": [aid, root]}],
        "scope": {"coverage_permissions": [{"removable_place_ids": [pid]}]},
    }
    refs, wire = repair_references(json.dumps(payload))
    assert all(identifier not in wire for identifier in (aid, root, pid))
    assert json.loads(wire)["time_protection"]["lineage"] == {"a01": "a02"}
    assert refs.decode(json.loads(wire)) == payload


def test_repair_restores_place_activity_and_target_references(monkeypatch):
    pid, aid, tid = "ChIJ" + "x" * 40, "activity-" + "y" * 60, "finding-" + "z" * 40
    FakeChatOpenAI.response = {
        "edits": [
            {
                "operation": "replace",
                "activity_id": "a01",
                "place_id": "p01",
                "date": "2026-10-01",
                "start_time": None,
                "end_time": None,
            }
        ],
        "target_dispositions": [{"target_id": "t01", "disposition": "proposed", "reason": "Bound"}],
    }
    client = make_client(monkeypatch)
    result = asyncio.run(
        client.generate_repair_structured(
            system_prompt=REPAIR_SYSTEM_PROMPT,
            user_prompt=json.dumps({"place_id": pid, "activity_id": aid, "target_id": tid}),
        )
    )
    assert result.edits[0].activity_id == aid and result.edits[0].place_id == pid
    assert result.target_dispositions[0].target_id == tid
    sent = FakeChatOpenAI.structured_model.messages[1].content
    assert all(identifier not in sent for identifier in (pid, aid, tid))


def test_review_profile_restores_place_and_preserves_short_review_refs(monkeypatch):
    pid = "ChIJ" + "v" * 50
    FakeChatOpenAI.response = {
        "place_id": "p01",
        "summary": "Quiet museum.",
        "summary_review_refs": ["review_1"],
        "signals": [],
        "review_count_used": 1,
    }
    client = make_client(monkeypatch)
    result = asyncio.run(
        client.generate_structured(
            system_prompt="Profile",
            user_prompt=json.dumps(
                {"place_id": pid, "reviews": [{"review_id": "review_1", "text": "Quiet museum."}]}
            ),
            response_schema=ExperienceProfileDraft,
        )
    )
    assert result.place_id == pid and result.summary_review_refs == ["review_1"]
    assert pid not in FakeChatOpenAI.structured_model.messages[1].content


@pytest.mark.parametrize("returned_id", ["p99", "ChIJ-unmapped-original"])
def test_invalid_primary_reference_is_terminal_without_retry(monkeypatch, returned_id):
    activity = make_activity().model_dump(mode="json")
    activity.pop("transport")
    activity["source_place_id"] = returned_id
    FakeChatOpenAI.response = {
        "output_version": "itinerary_3",
        "destination": "Kyoto",
        "start_date": "2026-10-01",
        "end_date": "2026-10-01",
        "days": [{"date": "2026-10-01", "activities": [activity]}],
    }
    client = make_client(monkeypatch)
    with pytest.raises(StructuredOutputError, match="Unknown model reference"):
        asyncio.run(
            client.generate_structured(
                system_prompt="Plan",
                user_prompt='<external_evidence>\n{"places":[{"place_id":"original"}]}',
                response_schema=V1Itinerary,
            )
        )
    assert FakeChatOpenAI.structured_model.invocation_count == 1


def test_short_reference_schema_and_restore_cross_real_sdk_mock_transport():
    from backend.tests.llm.azure_foundry.test_requirement_acceptance_harness import (
        ModelTransport,
        settings,
    )
    from tools.validation.runtime_acceptance import AcceptanceSession

    pid = "ChIJ" + "long-canonical-place" * 3
    activity = make_activity().model_dump(mode="json", exclude={"transport"})
    activity["source_place_id"] = "p01"
    output = {
        "output_version": "itinerary_3",
        "destination": "Kyoto",
        "start_date": "2026-10-01",
        "end_date": "2026-10-01",
        "days": [{"date": "2026-10-01", "activities": [activity]}],
    }
    transport = ModelTransport([output])

    async def invoke():
        async with AcceptanceSession(settings=settings(), transport=transport) as session:
            return await session.client.generate_structured(
                system_prompt="Plan",
                response_schema=V1Itinerary,
                user_prompt="<external_evidence>\n" + json.dumps({"places": [{"place_id": pid}]}),
            )

    result = asyncio.run(invoke())
    assert result.days[0].activities[0].source_place_id == pid
    assert len(transport.requests) == 1 and pid not in json.dumps(transport.requests)
    schema = transport.requests[0]["text"]["format"]["schema"]
    assert schema["$defs"]["FoundryPrimaryActivityDTO"]["properties"]["source_place_id"][
        "enum"
    ] == ["p01", None]
