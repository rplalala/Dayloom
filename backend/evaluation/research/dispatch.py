"""Traceable Planner invocation observations, separate from provider requests."""

from backend.cli.collection import _require

from .sources import Sources


def read_dispatch(sources: Sources, ref: dict, attempt: dict) -> dict:
    # Imported metadata is an explicit source declaration, never a filesystem inference.
    from .context import text_fields, timestamp

    value = sources.read_ref(ref, "rtpeval_planner_dispatch_1")
    text_fields(value, ("declared_by", "group_id", "run_id", "version"))
    _require(
        value.get("source_kind") in ("installed_generate", "historical_import"),
        "Unknown dispatch metadata source kind",
    )
    for field in ("group_id", "run_id", "version"):
        _require(value[field] == attempt.get(field), "Dispatch binding mismatch: " + field)
    _require(type(value.get("dispatched")) is bool, "Missing explicit dispatch observation")
    _require(
        type(value.get("planner_dispatches")) is int
        and value["planner_dispatches"] == int(value["dispatched"]),
        "Contradictory Planner dispatch count",
    )
    recorded = timestamp(value.get("recorded_at"))
    if value["dispatched"]:
        _require(
            timestamp(value.get("dispatched_at")) <= recorded,
            "Dispatch metadata recorded before invocation",
        )
    else:
        _require(value.get("dispatched_at") is None, "Non-dispatch observation has timestamp")
    _require(isinstance(value.get("execution_metadata"), dict), "Missing execution observations")
    for field in ("input_sha256", "configuration_sha256"):
        _require(
            value.get(field) == attempt.get(field), "Dispatch source binding mismatch: " + field
        )
    for field in ("dispatched", "dispatched_at", "execution_metadata"):
        if field in attempt:
            _require(value[field] == attempt[field], "Contradictory dispatch metadata: " + field)
    evidence = value.get("evidence_refs", [])
    _require(isinstance(evidence, list), "Invalid imported dispatch evidence")
    _require(
        value["source_kind"] != "historical_import" or bool(evidence),
        "Historical dispatch metadata requires explicit evidence references",
    )
    for source in evidence:
        sources.read_bytes(source)
    return value
