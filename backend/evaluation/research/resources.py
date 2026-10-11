"""Planner-only native usage views and separate all-attempt consumption."""

from statistics import median

from backend.cli.collection import _require
from backend.evaluation.usage_report import number, summarize

METRICS = (
    "model_calls",
    "http_sends",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "embedding_calls",
    "embedding_input_tokens",
    "embedding_total_tokens",
)


def token_view(models, field, covered):
    values = [m.get(field) for m in models if number(m.get(field))]
    return {
        "total": sum(values) if covered and len(values) == len(models) else None,
        "observed_subtotal": sum(values) if values else 0 if covered and not models else None,
        "known_calls": len(values),
        "missing_calls": len(models) - len(values),
    }


def resource_row(context, slot, attempt):
    row = {
        field: attempt[field]
        for field in (
            "case_id",
            "case_revision",
            "version",
            "repetition_id",
            "attempt_id",
            "run_id",
            "status",
            "execution_metadata",
            "order",
            "prior_attempt_id",
        )
    }
    row.update(
        selected_primary=attempt is slot["primary_attempt"],
        usage_ref=attempt.get("usage_ref"),
        metrics={k: None for k in ("elapsed_seconds", *METRICS)},
        observed_subtotals={k: None for k in METRICS},
        repair=None,
        native_usage=None,
        token_coverage={},
        elapsed_cohort="failed_or_censored",
        cost=None,
    )
    if attempt.get("usage_ref") is None:
        row["availability"] = "missing_usage"
        return row
    usage = context.read_ref(attempt["usage_ref"], "rtpeval_usage_1")
    _require(usage.get("namespace") == "planner", "Explicit planner namespace required")
    _require(attempt["dispatched"], "Generation usage on undispatched attempt")
    _require(
        all(usage.get(k) != "frozen_simulation" for k in ("outcome", "usage_scope", "scope")),
        "Frozen simulation is not generation usage",
    )
    _require(
        attempt["status"] != "completed"
        or usage.get("outcome") not in ("failed", "cancelled", "incomplete"),
        "Completed attempt usage outcome mismatch",
    )
    for field in ("coverage", "timing", "repair_summary"):
        _require(isinstance(usage.get(field, {}), dict), "Malformed native usage object: " + field)
    for field in ("model_calls", "provider_events", "cache_events"):
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
    covered = native["adapter_coverage"] == "declared_default_adapters"
    models = usage.get("model_calls", [])
    embeddings = [m for m in models if m.get("operation") == "embedding"]
    nonembeddings = [m for m in models if m.get("operation") != "embedding"]
    row.update(
        availability="available",
        native_usage=native,
        timing_scope=native["timing_scope"],
        usage_sha256=attempt["usage_ref"]["sha256"],
        raw_usage=usage,
    )
    row["metrics"].update(native["metrics"])
    # Embeddings retain input/total; no invented output-token observation.
    for key, members, field in (
        ("input_tokens", models, "input_tokens"),
        ("output_tokens", nonembeddings, "output_tokens"),
        ("total_tokens", models, "total_tokens"),
        ("embedding_input_tokens", embeddings, "input_tokens"),
        ("embedding_total_tokens", embeddings, "total_tokens"),
    ):
        view = token_view(members, field, covered)
        row["token_coverage"][key] = view
        row["metrics"][key] = view["total"]
        row["observed_subtotals"][key] = view["observed_subtotal"]
    row["metrics"]["embedding_calls"] = len(embeddings) if covered else None
    row["observed_subtotals"].update(
        model_calls=native["observed_model_calls"],
        http_sends=native["observed_http_sends"],
        embedding_calls=len(embeddings),
    )
    repair_ids = set(usage.get("repair_summary", {}).get("model_event_ids", []))
    providers = [
        p for p in usage.get("provider_events", []) if p.get("source") != "sdk_output_tool_calls"
    ]
    provider_ids = set(usage.get("repair_summary", {}).get("provider_event_ids", []))
    _require(
        provider_ids <= {p["event_id"] for p in usage.get("provider_events", [])},
        "Repair references absent provider events",
    )
    repaired = [m for m in models if m["event_id"] in repair_ids]
    row["repair"] = {
        "model_calls": len(repaired) if covered else None,
        "http_sends": sum(p["event_id"] in provider_ids for p in providers) if covered else None,
        "total_tokens": token_view(repaired, "total_tokens", covered)["total"],
        "observed_token_subtotal": token_view(repaired, "total_tokens", covered)[
            "observed_subtotal"
        ],
        "scope": "subset_counted_once",
    }
    if (
        attempt["status"] == "completed"
        and native["outcome"] == "completed"
        and native["timing_scope"] == "selected_invocation_through_cleanup"
    ):
        row["elapsed_cohort"] = "successful_invocation_through_cleanup"
    return row


def covered_ledger(row):
    return (
        row["availability"] == "available"
        and row["native_usage"]["adapter_coverage"] == "declared_default_adapters"
    )


def all_attempts(context):
    for slot in context.slots:
        for attempt in slot["attempts"]:
            _require(
                attempt["dispatched"] or attempt.get("usage_ref") is None,
                "Generation usage on undispatched attempt",
            )
    rows = [
        resource_row(context, slot, attempt)
        for slot in context.slots
        for attempt in slot["attempts"]
        if attempt["dispatched"]
    ]
    unknown_slots = sum(
        not s["attempts"] or any(a["status"] == "unknown_pending" for a in s["attempts"])
        for s in context.slots
    )
    ledger_complete = not unknown_slots and all(covered_ledger(r) for r in rows)
    output = {
        "planned_slots": len(context.slots),
        "dispatched_attempts": len(rows),
        "unknown_or_pending_slots": unknown_slots,
        "missing_usage_attempts": sum(r["availability"] == "missing_usage" for r in rows),
        "ledger_complete": ledger_complete,
        "totals": ledger_totals(rows, ledger_complete),
        "rows": rows,
    }
    output["by_version"] = {}
    for version in ("v0", "v1", "v2", "v3"):
        selected = [r for r in rows if r["version"] == version]
        slots = [s for s in context.slots if s["version"] == version]
        complete = all(
            s["attempts"] and all(a["status"] != "unknown_pending" for a in s["attempts"])
            for s in slots
        ) and all(covered_ledger(r) for r in selected)
        output["by_version"][version] = {
            "dispatched_attempts": len(selected),
            "ledger_complete": complete,
            "totals": ledger_totals(selected, complete),
        }
    cohorts = {}
    for row in rows:
        elapsed = row["metrics"]["elapsed_seconds"]
        if elapsed is not None:
            key = (
                row["version"],
                row["status"],
                row["elapsed_cohort"],
                row.get("timing_scope"),
                row["selected_primary"],
            )
            cohorts.setdefault(key, []).append(elapsed)
    output["elapsed_cohorts"] = [
        {
            "version": k[0],
            "workflow_status": k[1],
            "cohort": k[2],
            "timing_scope": k[3],
            "selected_primary": k[4],
            "observed_attempts": len(values),
            "median": median(values),
        }
        for k, values in sorted(cohorts.items(), key=lambda item: str(item[0]))
    ]
    return output


def ledger_totals(rows, ledger_complete):
    totals = {}
    for metric in METRICS:
        known = [r["metrics"][metric] for r in rows if r["metrics"][metric] is not None]
        observed = [
            r["observed_subtotals"][metric]
            for r in rows
            if r["observed_subtotals"][metric] is not None
        ]
        totals[metric] = {
            "total": sum(known) if ledger_complete and len(known) == len(rows) else None,
            "observed_subtotal": sum(observed)
            if observed
            else 0
            if ledger_complete and not rows
            else None,
            "known_attempts": len(known),
            "missing_attempts": len(rows) - len(known),
        }
    return totals
