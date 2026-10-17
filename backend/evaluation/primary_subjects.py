"""One separately budgeted common-subject stage and its zero-network replay."""

from .evaluation_transport import verify_model_capture
from .identity_llm import RESULT_VERSION
from .intake import _read
from .records import canonical_digest
from .snapshot import _bytes
from .subject_correspondence import prepare_subject_judgment, resolve_subjects


async def assess_subjects(preparation, execution, evidence, transport):
    packet = prepare_subject_judgment(
        preparation["intake"], evidence, model=preparation["options"]["model"]
    )
    if packet is None:
        return None
    packet = packet.to_dict()
    (execution / "subject-packet.json").write_bytes(_bytes(packet))
    response, event = await transport.model(packet, operation="requirement_subject")
    material = {
        "schema_version": RESULT_VERSION,
        "packet": packet,
        "response": response,
        "response_sha256": canonical_digest(response),
        "requested_at": event["requested_at"],
        "retrieved_at": event["retrieved_at"],
    }
    (execution / "subject-model-result.json").write_bytes(_bytes(material))
    resolve_subjects(preparation["intake"], evidence, material)
    return material


def replay_subjects(preparation, execution, evidence, journal, usage):
    packet = prepare_subject_judgment(
        preparation["intake"], evidence, model=preparation["options"]["model"]
    )
    events = [e for e in journal if e.get("model_event_id") == "requirement-subject"]
    calls = [c for c in usage["model_calls"] if c["operation"] == "requirement_subject"]
    if packet is None:
        if (
            events
            or calls
            or any(
                (execution / name).exists()
                for name in ("subject-packet.json", "subject-model-result.json")
            )
        ):
            raise ValueError("Unselected subject stage has unexpected material")
        return None
    material = _read(execution / "subject-model-result.json")[0]
    if (
        len(events) != 1
        or len(calls) != 1
        or packet.to_dict() != _read(execution / "subject-packet.json")[0]
        or material["packet"] != packet.to_dict()
    ):
        raise ValueError("Subject stage inventory or packet replay differs")
    verify_model_capture(
        execution, events[0], material, preparation["options"], calls[0], reasoning_effort="low"
    )
    resolve_subjects(preparation["intake"], evidence, material)
    return material
