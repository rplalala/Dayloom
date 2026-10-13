"""Offline, explicit-price money accounting; no planner dependencies or network calls."""

import argparse
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .cost_snapshot import snapshot_usage
from .usage_report import summarize

UNITS = {
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "requests",
    "element_count",
    "tool_calls",
}
TRANSPORT_ONLY = {"model_http", "embedding", "official_reasoning", "official_search"}


def backing_transport(event, models):
    """A successful, source-bound dispatch is not another model charge."""
    if event["operation"] not in TRANSPORT_ONLY:
        return False, None
    if event.get("outcome") != "completed":
        return False, "charge_uncertain"
    model = next((m for m in models if m["event_id"] == event.get("model_event_id")), None)
    if model is None or event.get("model_provider") != model["provider"]:
        return False, "unlinked_model_transport"
    if model["provider"] != "langchain" and model["provider"] != event["provider"]:
        return False, "transport_provider_mismatch"
    if event["operation"] != "model_http" and event["operation"] != model["operation"]:
        return False, "transport_operation_mismatch"
    if model.get("outcome") != "completed":
        return False, "charge_uncertain"
    return True, None


def amount(value):
    """Money and divisors are decimal strings, never binary floats or implicit currencies."""
    if not isinstance(value, str):
        raise ValueError("Amounts and divisors require decimal strings")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal amount") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Amounts must be finite and nonnegative")
    return result


def money(value):
    return format(value.normalize(), "f") if value is not None else None


def digest(value):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        raise ValueError("Artifact binding requires a SHA-256 digest")
    return value


def validate_prices(prices):
    if prices.get("schema_version") != "rtpeval_prices_1":
        raise ValueError("Unsupported price snapshot")
    if not re.fullmatch("[A-Z]{3}", prices.get("currency", "")):
        raise ValueError("Price snapshot requires explicit currency")
    ids = set()
    for row in prices["rows"]:
        if not row.get("price_id") or row["price_id"] in ids:
            raise ValueError("Price IDs must be unique")
        ids.add(row["price_id"])
        if not row.get("source"):
            raise ValueError("Price source required")
        date.fromisoformat(row["as_of"])
        start, end = date.fromisoformat(row["valid_from"]), date.fromisoformat(row["valid_until"])
        if start >= end:
            raise ValueError("Price validity interval must be nonempty")
        selector = row["match"]
        if (
            selector.get("kind") not in ("model", "provider")
            or not selector.get("provider")
            or not selector.get("operation")
        ):
            raise ValueError("Explicit price event identity required")
        if selector["kind"] == "model" and not selector.get("model"):
            raise ValueError("Model price requires exact deployment/model identity")
        if not row["rates"] or not set(row["rates"]) <= UNITS or amount(row["per"]) == 0:
            raise ValueError("Unsupported billing unit or divisor")
        for rate in row["rates"].values():
            amount(rate)
        if row.get("unreported_cache_policy") is not None:
            if row["unreported_cache_policy"] != "uncached_write_rate" or not {
                "input_tokens",
                "cached_input_tokens",
                "cache_write_input_tokens",
            } <= set(row["rates"]):
                raise ValueError("Unsupported unreported-cache price policy")
            if amount(row["rates"]["cache_write_input_tokens"]) < amount(
                row["rates"]["input_tokens"]
            ):
                raise ValueError("Conservative cache-write rate cannot be below ordinary input")


def estimate(event, kind, usage, prices):
    if event.get("outcome") != "completed":
        return None, None, "charge_uncertain"
    stamp = usage.get("timing", {}).get("started_at")
    try:
        observed_date = date.fromisoformat(stamp[:10])
    except (TypeError, ValueError):
        return None, None, "missing_usage_date"
    matches = []
    for row in prices["rows"]:
        fields = {"kind": kind, **event}
        if all(fields.get(k) == v for k, v in row["match"].items()) and (
            date.fromisoformat(row["valid_from"])
            <= observed_date
            < date.fromisoformat(row["valid_until"])
        ):
            matches.append(row)
    if len(matches) != 1:
        return None, None, "ambiguous_price" if matches else "missing_price_or_billing_context"
    row = matches[0]
    if event.get("cache_write_input_tokens", 0) and "cache_write_input_tokens" not in row["rates"]:
        return None, row, "missing_cache_write_price"
    if (
        kind == "model"
        and event["operation"] != "embedding"
        and not {"input_tokens", "output_tokens", "cached_input_tokens"} <= set(row["rates"])
    ):
        return None, row, "incomplete_model_price"
    if row.get("max_input_tokens") is not None and (
        type(event.get("input_tokens")) is not int
        or event["input_tokens"] > row["max_input_tokens"]
    ):
        return None, row, "unsupported_context_price"
    assumptions = []
    event = dict(event)
    if row.get("unreported_cache_policy") == "uncached_write_rate":
        if event.get("cached_input_tokens") is None:
            event["cached_input_tokens"] = 0
            assumptions.append("Unreported cache reads: no cache-read discount assumed.")
        if event.get("cache_write_input_tokens") is None:
            inputs, reads = event.get("input_tokens"), event.get("cached_input_tokens")
            if type(inputs) is int and type(reads) is int and 0 <= reads <= inputs:
                event["cache_write_input_tokens"] = inputs - reads
                assumptions.append(
                    "Unreported cache writes: all non-read input priced at the cache-write rate."
                )
    units = {}
    for unit in row["rates"]:
        count = 1 if unit == "requests" else event.get(unit)
        if type(count) is not int or count < 0:
            return None, row, "missing_" + unit
        units[unit] = count
    partitions = sum(
        units.get(key, 0) for key in ("cached_input_tokens", "cache_write_input_tokens")
    )
    if "cached_input_tokens" in units or "cache_write_input_tokens" in units:
        if "input_tokens" not in units or partitions > units["input_tokens"]:
            return None, row, "invalid_cache_partition"
        units["input_tokens"] -= partitions
    value = sum(
        (
            Decimal(count) * amount(row["rates"][unit]) / amount(row["per"])
            for unit, count in units.items()
        ),
        Decimal(0),
    )
    pricing = {**row, "billable_units": units}
    if assumptions:
        pricing["assumptions"] = assumptions
    return value, pricing, None


def totals(events, *, covered=True):
    billable = [e for e in events if e["status"] != "transport_only"]
    output = {}
    for name in ("actual", "estimated", "best_available"):
        values = [amount(e[name]) for e in billable if e.get(name) is not None]
        subtotal = sum(values, Decimal(0)) if values else Decimal(0) if not billable else None
        output[name + "_observed_subtotal"] = money(subtotal)
        output[name + "_total"] = (
            money(subtotal) if covered and len(values) == len(billable) else None
        )
    output["unpriced_event_count"] = sum(e["status"] == "unpriced" for e in events)
    return output


def bind_bills(sources, bills, currency):
    by_hash = {s["sha256"]: s["usage"] for s in sources}
    bound, unallocated, ids = {}, [], set()
    for bill in bills:
        if not bill.get("bill_id") or bill["bill_id"] in ids:
            raise ValueError("Duplicate or missing bill ID")
        ids.add(bill["bill_id"])
        amount(bill["amount"])
        if not bill.get("source") or not re.fullmatch("[A-Z]{3}", bill.get("currency", "")):
            raise ValueError("Bill requires source and currency")
        scope = bill.get("scope")
        if scope == "aggregate":
            if any(k in bill for k in ("usage_sha256", "result_sha256", "event_id", "kind")):
                raise ValueError("Aggregate bills must not claim event attribution")
            unallocated.append(bill)
            continue
        if scope not in ("event", "run") or bill["currency"] != currency:
            raise ValueError("Unsupported bill scope or currency; no implicit FX")
        sha = digest(bill.get("usage_sha256"))
        usage = by_hash.get(sha)
        if usage is None or bill.get("result_sha256") != usage.get("result_sha256"):
            raise ValueError("Foreign bill artifact binding")
        if scope == "run":
            if bill.get("complete") is not True or "event_id" in bill or "kind" in bill:
                raise ValueError("Run bill requires complete attribution without event IDs")
            key = (sha, "run", None)
        else:
            kind = bill.get("kind")
            field = {"model": "model_calls", "provider": "provider_events"}.get(kind)
            if field is None or bill.get("event_id") not in {r["event_id"] for r in usage[field]}:
                raise ValueError("Bill references an absent event")
            key = (sha, kind, bill["event_id"])
        if key in bound:
            raise ValueError("Ambiguous bill binding")
        bound[key] = bill
    for sha in by_hash:
        if (sha, "run", None) in bound and any(k[0] == sha and k[1] != "run" for k in bound):
            raise ValueError("Run and event bills overlap")
    return bound, unallocated


def bind_annotations(sources, annotations):
    events = {
        (s["sha256"], kind, row["event_id"])
        for s in sources
        for kind, field in (("model", "model_calls"), ("provider", "provider_events"))
        for row in s["usage"].get(field, [])
    }
    bound = {}
    for item in annotations:
        key = (digest(item.get("usage_sha256")), item.get("kind"), item.get("event_id"))
        if key not in events or key in bound:
            raise ValueError("Foreign or duplicate event annotation")
        if not item.get("source") or not item.get("note"):
            raise ValueError("Historical annotations require source and explanation")
        digest(item.get("source_sha256"))
        if not item.get("fields") or not set(item["fields"]) <= {
            "billing_context",
            "cached_input_tokens",
        }:
            raise ValueError("Annotations cannot replace observed tokens, status or identity")
        bound[key] = item
    return bound


def build_cost_report(sources, prices, *, bills=None, annotations=None):
    """Account selected saved envelopes; caller supplies hashes of the original file bytes.

    The CLI hashes bytes itself. Report totals cover declared instrumented adapters only;
    credits, taxes, account tiers and unobserved services require actual imported bills.
    """
    validate_prices(prices)
    hashes, identities, captures = set(), set(), set()
    for source in sources:
        sha, usage = digest(source["sha256"]), source["usage"]
        summarize(usage)
        for kind, field in (("model", "model_calls"), ("provider", "provider_events")):
            refs = usage.get("repair_summary", {}).get(kind + "_event_ids", [])
            if not set(refs) <= {r["event_id"] for r in usage.get(field, [])}:
                raise ValueError("Repair references absent events")
        identity = tuple(usage.get(k) for k in ("namespace", "group_id", "run_id", "version"))
        if not all(identity) or identity[0] not in ("planner", "oracle"):
            raise ValueError("Explicit namespaced run identity required")
        if sha in hashes or identity in identities:
            raise ValueError("Duplicate usage artifact or run identity")
        hashes.add(sha)
        identities.add(identity)
        for event in usage.get("provider_events", []):
            capture = event.get("capture_id")
            if capture is not None:
                if capture in captures:
                    raise ValueError("Duplicate captured send across usage artifacts")
                captures.add(capture)
    bound, unallocated = bind_bills(sources, bills or [], prices["currency"])
    annotated = bind_annotations(sources, annotations or [])
    runs = []
    for source in sources:
        sha, usage = source["sha256"], source["usage"]
        covered = usage.get("coverage", {}).get("adapter_coverage") == "default_adapters" and usage[
            "collection_status"
        ] in ("available", "partial")
        events = []
        repair = usage.get("repair_summary", {})
        for kind, field in (("model", "model_calls"), ("provider", "provider_events")):
            for original in usage.get(field, []):
                key = (sha, kind, original["event_id"])
                annotation = annotated.get(key)
                event = dict(original)
                for k, v in annotation["fields"].items() if annotation else ():
                    if k == "billing_context" and isinstance(v, dict):
                        old = original.get(k, {})
                        if any(name in old and old[name] != value for name, value in v.items()):
                            raise ValueError(
                                "Annotations must not override observed billing fields"
                            )
                        event[k] = {**old, **v}
                    elif k in original and original[k] != v:
                        raise ValueError("Annotations must not override observed billing fields")
                    else:
                        event[k] = v
                transport, transport_reason = (
                    backing_transport(event, usage.get("model_calls", []))
                    if kind == "provider"
                    else (False, None)
                )
                value, pricing, reason = (
                    (None, None, transport_reason)
                    if transport or transport_reason
                    else estimate(event, kind, usage, prices)
                )
                bill = bound.get(key)
                if bill and transport:
                    raise ValueError("Bind a backing HTTP bill to its model event or complete run")
                actual = amount(bill["amount"]) if bill else None
                best = actual if actual is not None else value
                category = (
                    "embeddings"
                    if kind == "model" and event["operation"] == "embedding"
                    else "models"
                    if kind == "model"
                    else event["operation"]
                )
                events.append(
                    {
                        "event_id": event["event_id"],
                        "kind": kind,
                        "category": category,
                        "provider": event["provider"],
                        "operation": event["operation"],
                        "model": event.get("model"),
                        "status": "actual"
                        if bill
                        else "transport_only"
                        if transport
                        else "estimated"
                        if value is not None
                        else "unpriced",
                        "actual": money(actual),
                        "estimated": money(value),
                        "best_available": money(best),
                        "missing_reason": reason if best is None and not transport else None,
                        "pricing": pricing,
                        "bill": bill,
                        "annotation": annotation,
                    }
                )
        # Repair references both model and provider event IDs, never an additional charge.
        for row in events:
            row["repair"] = row["event_id"] in repair.get(row["kind"] + "_event_ids", [])
        run = {
            k: usage.get(k) for k in ("namespace", "group_id", "run_id", "version", "result_sha256")
        }
        run.update(usage_sha256=sha, events=events, **totals(events, covered=covered))
        run["categories"] = {
            category: totals([e for e in events if e["category"] == category], covered=covered)
            for category in sorted({e["category"] for e in events})
        }
        run["repair"] = totals([e for e in events if e["repair"]], covered=covered)
        run["missing_fields"] = usage.get("missing_fields", [])
        if "inherited_usage" in usage:
            run["inherited_usage"] = usage["inherited_usage"]
        run_bill = bound.get((sha, "run", None))
        if run_bill:
            run.update(
                actual_total=run_bill["amount"],
                best_available_total=run_bill["amount"],
                run_bill=run_bill,
            )
            for subset in [run["repair"], *run["categories"].values()]:
                subset["actual_total"] = subset["best_available_total"] = None
                subset["actual_allocation"] = "unavailable_run_bill"
        runs.append(run)
    return {
        "schema_version": "rtpeval_cost_report_1",
        "currency": prices["currency"],
        "scope": "observed_instrumented_adapters_only",
        "runs": runs,
        "unallocated_bills": unallocated,
        "prices": prices,
        "limitations": [
            "Retail estimates exclude credits, free tiers, volume discounts and tax.",
            "Unobserved services are not inferred; partial subtotals are not totals.",
            "Repair is a subset. Oracle runs are not allocated to planner versions.",
        ],
    }


def read_source(path):
    raw = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "usage": json.loads(raw)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usage", action="append", default=[])
    parser.add_argument("--snapshot", action="append", default=[])
    parser.add_argument("--prices", required=True)
    parser.add_argument("--bills")
    parser.add_argument("--annotations")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not args.usage and not args.snapshot:
        parser.error("At least one usage envelope or oracle snapshot is required")
    inputs = args.usage + [str(Path(p) / "manifest.json") for p in args.snapshot]
    inputs += [p for p in (args.prices, args.bills, args.annotations) if p]
    output = Path(args.output).resolve()
    if any(output == Path(p).resolve() for p in inputs) or any(
        output.is_relative_to(Path(p).resolve()) for p in args.snapshot
    ):
        parser.error("Output must not overwrite source usage, prices, bills or snapshot material")
    report = build_cost_report(
        [read_source(p) for p in args.usage] + [snapshot_usage(p) for p in args.snapshot],
        json.loads(Path(args.prices).read_bytes()),
        bills=json.loads(Path(args.bills).read_bytes()) if args.bills else None,
        annotations=json.loads(Path(args.annotations).read_bytes()) if args.annotations else None,
    )
    Path(args.output).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
