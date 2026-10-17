"""Save a native generation completion without treating unknown cost as zero."""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


def complete_generation_receipt(
    receipt_path: Path,
    capture_directory: Path,
    *,
    completed_at: str,
    exit_code: int,
    spent_before_usd: Decimal,
) -> dict:
    """Finalize an existing start receipt; never execute or retry its command."""
    record = json.loads(receipt_path.read_text(encoding="utf-8"))
    record.update(
        completed_at=completed_at,
        exit_code=exit_code,
        estimated_usd=None,
        observed_subtotal_usd=None,
        unpriced_event_count=None,
        cumulative_usd=None,
        cumulative_known_subtotal_usd=str(spent_before_usd),
    )
    for name in (
        "usage-summary.json",
        "failure.json",
        "producer-completion.json",
        "cost-report.json",
    ):
        path = capture_directory / name
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if name != "cost-report.json":
                record[name] = value
                continue
            run = value["runs"][0]
            total = run["best_available_total"]
            subtotal = run.get("best_available_observed_subtotal")
            unpriced = run["unpriced_event_count"]
            fields = dict(unpriced_event_count=unpriced)
            if subtotal is not None:
                fields.update(
                    observed_subtotal_usd=subtotal,
                    cumulative_known_subtotal_usd=str(spent_before_usd + Decimal(subtotal)),
                )
            if total is not None and unpriced == 0:
                fields.update(
                    estimated_usd=total,
                    cumulative_usd=str(spent_before_usd + Decimal(total)),
                )
            record.update(fields)
        except (OSError, ValueError, TypeError, KeyError, IndexError, InvalidOperation) as exc:
            record.setdefault("receipt_errors", []).append(f"{name}:{type(exc).__name__}")
    receipt_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record
