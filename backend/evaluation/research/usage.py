"""Common structural validation for supplied native planner usage envelopes."""

from backend.cli.collection import _require
from backend.evaluation.usage_report import summarize


def validate_generation_usage(usage, *, dispatched, workflow_status):
    """Validate saved material without conflating capture outcome with workflow success."""
    _require(usage.get("namespace") == "planner", "Explicit planner namespace required")
    _require(
        all(usage.get(k) != "frozen_simulation" for k in ("outcome", "usage_scope", "scope")),
        "Frozen simulation is not generation usage",
    )
    _require(
        workflow_status != "completed"
        or usage.get("outcome") not in ("failed", "cancelled", "incomplete"),
        "Completed attempt usage outcome mismatch",
    )
    for field in ("coverage", "timing", "repair_summary"):
        _require(isinstance(usage.get(field, {}), dict), "Malformed native usage object: " + field)
    for field in ("model_calls", "provider_events", "cache_events", "stage_summaries"):
        members = usage.get(field, [])
        _require(
            isinstance(members, list) and all(isinstance(r, dict) for r in members),
            "Malformed native usage event array: " + field,
        )
    for field in ("model_event_ids", "provider_event_ids"):
        ids = usage.get("repair_summary", {}).get(field, [])
        _require(
            isinstance(ids, list)
            and all(isinstance(i, str) and i for i in ids)
            and len(ids) == len(set(ids)),
            "Malformed Repair usage subset: " + field,
        )
    native = summarize(usage)
    provider_ids = set(usage.get("repair_summary", {}).get("provider_event_ids", []))
    _require(
        provider_ids <= {p["event_id"] for p in usage.get("provider_events", [])},
        "Repair references absent provider events",
    )
    if not dispatched:
        _require(
            usage["collection_status"] == "unavailable"
            and usage.get("outcome") in (None, "unavailable", "not_started")
            and usage.get("result_sha256") is None
            and not any(
                usage.get(field, [])
                for field in ("model_calls", "provider_events", "cache_events", "stage_summaries")
            ),
            "Generation usage observations on undispatched attempt",
        )
        _require(
            all(value is None for key, value in usage.get("timing", {}).items() if key != "scope"),
            "Generation timing on undispatched attempt",
        )
        repair = usage.get("repair_summary", {})
        _require(
            not repair.get("model_event_ids", [])
            and not repair.get("provider_event_ids", [])
            and (
                repair.get("observed_rounds") is None
                or type(repair["observed_rounds"]) is int
                and repair["observed_rounds"] == 0
            )
            and all(
                value is None
                for key, value in repair.items()
                if key not in ("model_event_ids", "provider_event_ids", "observed_rounds")
            ),
            "Repair consumption on undispatched attempt",
        )
    return native
