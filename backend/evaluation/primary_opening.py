"""Bound missing-hours assessment before composing a fresh run's final score."""

from .evaluation_transport import verify_model_capture
from .intake import _read
from .opening_judgment import MATERIAL_VERSION, prepare_packet, validate_material
from .snapshot import _bytes


def _packet(preparation, execution, identity, plan):
    return prepare_packet(
        preparation["intake"],
        identity,
        execution / "evidence-snapshot",
        preparation["context"]["schedule_context"],
        model=preparation["options"]["model"],
        expected_plan=plan,
    )


def _stage(packet):
    return {
        "status": "complete" if packet["cases"] else "skipped",
        "eligible_count": len(packet["cases"]),
        "reason": None if packet["cases"] else "no_eligible_missing_hours",
        "packet_sha256": packet["content_sha256"],
    }


def _disabled():
    return {"status": "disabled", "eligible_count": None, "reason": "explicit_api_only"}


async def assess_primary_opening(preparation, execution, identity, plan, transport):
    """Reuse collected evidence; send at most one medium-effort assessment, with no retries."""
    if not preparation["options"].get("assess_missing_hours", True):
        return _disabled(), None
    packet = _packet(preparation, execution, identity, plan)
    (execution / "opening-packet.json").write_bytes(_bytes(packet))
    stage = _stage(packet)
    if not packet["cases"]:
        return stage, None
    raw, event = await transport.model(
        packet, operation="opening_access", reasoning_effort="medium"
    )
    material = {
        "schema_version": MATERIAL_VERSION,
        "packet": packet,
        "provider": "azure_foundry",
        "request": event["request"]["json"],
        "response": raw,
        "requested_at": event["requested_at"],
        "retrieved_at": event["retrieved_at"],
    }
    (execution / "opening-model-result.json").write_bytes(_bytes(material))
    validate_material(material, packet)
    return stage, material


def replay_primary_opening(preparation, execution, identity, plan, journal, usage):
    """Reconstruct eligibility and bind the optional assessment to its captured model send."""
    events = [event for event in journal if event.get("model_event_id") == "opening-access"]
    calls = [call for call in usage["model_calls"] if call["operation"] == "opening_access"]
    if not preparation["options"].get("assess_missing_hours", True):
        if events or calls or (execution / "opening-packet.json").exists():
            raise ValueError("Disabled opening assessment has unexpected material")
        return _disabled(), None
    packet = _packet(preparation, execution, identity, plan)
    if packet != _read(execution / "opening-packet.json")[0]:
        raise ValueError("Opening eligibility/evidence replay differs")
    stage = _stage(packet)
    if not packet["cases"]:
        if events or calls or (execution / "opening-model-result.json").exists():
            raise ValueError("Ineligible opening assessment has unexpected material")
        return stage, None
    if len(events) != 1 or len(calls) != 1:
        raise ValueError("Exactly one opening assessment attempt required")
    material = _read(execution / "opening-model-result.json")[0]
    validate_material(material, packet)
    verify_model_capture(
        execution, events[0], material, preparation["options"], calls[0], reasoning_effort="medium"
    )
    return stage, material
