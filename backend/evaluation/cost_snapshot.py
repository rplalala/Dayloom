"""Normalize verified native oracle attempts for offline cost accounting."""

import hashlib
import json
from pathlib import Path

from .snapshot import load_snapshot


def snapshot_usage(directory):
    """Preserve every send, including retries; do not infer missing Places field masks."""
    snapshot = load_snapshot(directory)
    sha = hashlib.sha256((Path(directory) / "manifest.json").read_bytes()).hexdigest()
    requests = {r["key"]: r for r in snapshot["plan"]["requests"]}
    events = []
    imported = snapshot["schema_version"] == "rtpeval_imported_snapshot_1"
    for record in () if imported else snapshot["records"]:
        request = requests[record["key"]]
        operation = request["operation"]
        for attempt in record["attempts"]:
            # A copied/rebound snapshot cannot invent another send with the same captured attempt.
            capture_id = hashlib.sha256(
                json.dumps(
                    {
                        k: attempt.get(k)
                        for k in ("requested_at", "retrieved_at", "status_code", "raw")
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            context = {}
            if operation == "route_matrix":
                params = request["parameters"]
                context["travel_mode"] = params["mode"]
                options = params.get("routing_options", {})
                if "routing_preference" in options:
                    context["routing_preference"] = options["routing_preference"]
            status = attempt.get("status_code")
            events.append(
                {
                    "event_id": record["key"] + ":" + str(attempt["attempt"]),
                    "capture_id": capture_id,
                    "provider": "google",
                    "operation": "place_details" if operation == "places_details" else operation,
                    "outcome": "completed"
                    if type(status) is int and 200 <= status < 400
                    else "failed",
                    "send_status": "transport_entered",
                    "status_code": status,
                    "element_count": 1 if operation == "route_matrix" else None,
                    "billing_context": context,
                    "source": "verified_native_snapshot_attempt",
                    "requested_at": attempt["requested_at"],
                }
            )
    return {
        "sha256": sha,
        "usage": {
            "schema_version": "rtpeval_usage_1",
            "namespace": "oracle",
            "group_id": snapshot["plan"]["batch_id"],
            "run_id": sha,
            "version": "shared",
            "result_sha256": snapshot["plan_hash"],
            "collection_status": "available",
            "model_calls": [],
            "provider_events": events,
            "cache_events": [],
            "repair_summary": {"model_event_ids": [], "provider_event_ids": []},
            "coverage": {"adapter_coverage": "default_adapters"},
            "timing": {
                "started_at": snapshot["imported_at"] if imported else snapshot["started_at"],
                "finished_at": snapshot["imported_at"] if imported else snapshot["finished_at"],
            },
            "missing_fields": ["places_billing_context"]
            if any(e["operation"] != "route_matrix" for e in events)
            else [],
            **({"inherited_usage": snapshot["inherited_usage"]} if imported else {}),
        },
    }
