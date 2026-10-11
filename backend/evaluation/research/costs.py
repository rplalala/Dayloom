"""Offline native cost reconstruction bound to census usage bytes."""

from decimal import Decimal

from backend.cli.collection import _require
from backend.evaluation.cost_report import build_cost_report, money

from .context import text_fields
from .sources import digest


def attach_costs(context, ledger, descriptors):
    _require(isinstance(descriptors, list), "Explicit cost ledger array required")
    attempts = {r["attempt_id"]: r for r in ledger["rows"]}
    assigned, rebuilt = set(), []
    for descriptor in descriptors:
        text_fields(descriptor, ("accounting_basis",))
        ids = descriptor.get("attempt_ids")
        _require(
            isinstance(ids, list) and ids and len(ids) == len(set(ids)),
            "Unique cost attempt inventory required",
        )
        _require(
            all(a in attempts and a not in assigned for a in ids),
            "Foreign or duplicate cost attempt binding",
        )
        assigned.update(ids)
        selected = [attempts[a] for a in ids]
        _require(
            all(r["usage_ref"] is not None for r in selected),
            "Cost requires exact bound native usage",
        )
        prices = context.read_ref(descriptor.get("prices_ref"), "rtpeval_prices_1")
        _require(
            isinstance(prices.get("rows"), list)
            and all(isinstance(r, dict) for r in prices["rows"]),
            "Malformed native price rows",
        )
        for price in prices["rows"]:
            _require(
                isinstance(price.get("match"), dict) and isinstance(price.get("rates"), dict),
                "Malformed native price match/rates",
            )
        bills = (
            context.read_ref(descriptor["bills_ref"])["bills"]
            if descriptor.get("bills_ref") is not None
            else None
        )
        annotations = (
            context.read_ref(descriptor["annotations_ref"])["annotations"]
            if descriptor.get("annotations_ref") is not None
            else None
        )
        for field, rows in (("bills", bills), ("annotations", annotations)):
            _require(
                rows is None or isinstance(rows, list) and all(isinstance(r, dict) for r in rows),
                "Malformed native accounting array: " + field,
            )
        for annotation in annotations or []:
            _require(
                isinstance(annotation.get("fields"), dict),
                "Malformed native accounting annotation fields",
            )
            _billing_context(annotation["fields"])
        for row in selected:
            for field in ("model_calls", "provider_events"):
                for event in row["raw_usage"].get(field, []):
                    _billing_context(event)
        report = build_cost_report(
            [{"sha256": r["usage_sha256"], "usage": r["raw_usage"]} for r in selected],
            prices,
            bills=bills,
            annotations=annotations,
        )
        if descriptor.get("report_ref") is not None:
            saved = context.read_ref(descriptor["report_ref"], "rtpeval_cost_report_1")
            _require(saved == report, "Native saved cost report differs from source reconstruction")
        by_sha = {r["usage_sha256"]: r for r in report["runs"]}
        for row in selected:
            native = by_sha[row["usage_sha256"]]
            row["cost"] = {
                "native": native,
                "currency": report["currency"],
                "accounting_basis": descriptor["accounting_basis"],
                "scope": report["scope"],
                "prices_sha256": descriptor["prices_ref"]["sha256"],
                "prices": prices,
                "limitations": report["limitations"],
                "report_ref": descriptor.get("report_ref"),
                "billing_coverage": {
                    "run_bill": native.get("run_bill"),
                    "unpriced_event_count": native["unpriced_event_count"],
                    "assumptions": sorted(
                        {
                            a
                            for e in native["events"]
                            for a in (e.get("pricing") or {}).get("assumptions", [])
                        }
                    ),
                },
            }
        rebuilt.append({"attempt_ids": ids, "native": report, "semantic_sha256": digest(report)})
    ledger["native_cost_ledgers"] = rebuilt
    ledger["cost_coverage"] = {
        "known_cost_attempts": len(assigned),
        "missing_cost_attempts": len(attempts) - len(assigned),
    }
    cohorts = {}
    for row in ledger["rows"]:
        cost = row["cost"]
        if cost:
            key = (
                row["version"],
                cost["currency"],
                cost["accounting_basis"],
                cost["prices_sha256"],
            )
            cohorts.setdefault(key, []).append(cost["native"])
    consumption = []
    for key, runs in sorted(cohorts.items()):
        row = {
            "version": key[0],
            "currency": key[1],
            "accounting_basis": key[2],
            "prices_sha256": key[3],
            "known_cost_attempts": len(runs),
        }
        complete = (
            ledger["by_version"][key[0]]["ledger_complete"]
            and len(runs) == ledger["by_version"][key[0]]["dispatched_attempts"]
        )
        for mode in ("actual", "estimated", "best_available"):
            known = [r[mode + "_total"] for r in runs if r[mode + "_total"] is not None]
            observed = [
                r[mode + "_observed_subtotal"]
                for r in runs
                if r[mode + "_observed_subtotal"] is not None
            ]
            row[mode + "_known_run_total_subtotal"] = (
                money(sum((Decimal(v) for v in known), Decimal(0))) if known else None
            )
            row[mode + "_total"] = (
                money(sum((Decimal(v) for v in known), Decimal(0)))
                if complete and len(known) == len(runs)
                else None
            )
            row[mode + "_observed_subtotal"] = (
                money(sum((Decimal(v) for v in observed), Decimal(0))) if observed else None
            )
        consumption.append(row)
    ledger["cost_consumption"] = consumption


def _billing_context(event):
    _require(
        "billing_context" not in event or isinstance(event["billing_context"], dict),
        "Malformed native billing_context",
    )
