"""Descriptive selected-attempt comparisons with native final score preservation."""

from decimal import Decimal
from fractions import Fraction
from statistics import median

from backend.cli.collection import _require
from backend.evaluation.cost_report import money

from .context import VERSIONS
from .resources import METRICS


def difference(a, b, *, compatible=True, reason="scope_mismatch", decimal=False):
    valid = compatible and a is not None and b is not None
    left, right = (Decimal(a), Decimal(b)) if valid and decimal else (a, b)
    delta = right - left if valid else None
    ratio = right / left if valid and left > 0 else None
    return {
        "difference": money(delta) if decimal else delta,
        "ratio": money(ratio) if decimal else ratio,
        "reason": reason
        if not compatible
        else "missing_measurement"
        if not valid
        else "zero_baseline"
        if left == 0
        else None,
    }


def cost_deltas(left, right):
    a, b = left.get("cost") if left else None, right.get("cost") if right else None
    result = {}
    compatible = a is not None and b is not None
    reason = "missing_cost"
    if compatible:
        if a["currency"] != b["currency"]:
            compatible, reason = False, "currency_mismatch"
        elif (
            any(a[k] != b[k] for k in ("accounting_basis", "scope", "prices_sha256"))
            or a["billing_coverage"]["assumptions"] != b["billing_coverage"]["assumptions"]
        ):
            compatible, reason = False, "accounting_basis_mismatch"
    for mode in ("actual", "estimated", "best_available"):
        mode_compatible, mode_reason = compatible, reason
        if mode_compatible and mode == "best_available":

            def basis(cost):
                native = cost["native"]
                if native.get("run_bill"):
                    return ("complete_run_bill",)
                return tuple(
                    sorted(
                        {e["status"] for e in native["events"] if e["status"] != "transport_only"}
                    )
                )

            if basis(a) and basis(b) and basis(a) != basis(b):
                mode_compatible, mode_reason = False, "billing_basis_mismatch"
        result[mode] = difference(
            a["native"][mode + "_total"] if a else None,
            b["native"][mode + "_total"] if b else None,
            compatible=mode_compatible,
            reason=mode_reason,
            decimal=True,
        )
    return result


def quality_delta(native, baseline, candidate):
    if native is None:
        return {"availability": "missing_native_quality"}
    group, report = native["group"], native["report"]
    left, right = group["versions"][baseline], group["versions"][candidate]
    output = {
        "availability": "available",
        "native_content_hash": report["content_hash"],
        "rules_profile_id": report["rules_profile_id"],
        "rules_profile_hash": report["rules_profile_hash"],
        "included_dimensions": group["included_dimensions"],
        "baseline_native": left,
        "candidate_native": right,
        "totals": {},
        "dimensions": {},
    }
    for metric in ("auxiliary_total", "overall_total"):
        a, b = left[metric], right[metric]
        row = difference(a["score_0_100"], b["score_0_100"])
        x, y = a.get("exact_fraction"), b.get("exact_fraction")
        exact = (
            Fraction(y["numerator"], y["denominator"]) - Fraction(x["numerator"], x["denominator"])
            if x and y
            else None
        )
        row["exact_fraction"] = (
            {"numerator": exact.numerator, "denominator": exact.denominator}
            if exact is not None
            else None
        )
        output["totals"][metric] = row
    for dimension in group["included_dimensions"]:
        a, b = left["dimensions"][dimension], right["dimensions"][dimension]
        output["dimensions"][dimension] = difference(
            a["verified_score_0_100"], b["verified_score_0_100"]
        )
    return output


def pairs_report(context, population, ledger, native_rows, requested):
    _require(
        isinstance(requested, list) and requested, "Explicit nonempty comparison array required"
    )
    keys, pairs = set(), []
    for row in requested:
        _require(
            isinstance(row, dict) and set(row) == {"baseline", "candidate"},
            "Invalid version comparison",
        )
        pair = (row["baseline"], row["candidate"])
        _require(
            all(v in VERSIONS for v in pair) and pair[0] != pair[1] and pair not in keys,
            "Unknown or duplicate version comparison",
        )
        keys.add(pair)
        pairs.append(pair)
    slots = {}
    for slot in context.slots:
        key = tuple(slot[k] for k in ("case_id", "case_revision", "repetition_id"))
        slots.setdefault(key, {})[slot["version"]] = slot
    resources = {r["attempt_id"]: r for r in ledger["rows"]}
    output = []
    for baseline, candidate in pairs:
        rows = []
        not_applicable = 0
        for key, group in slots.items():
            if baseline not in group or candidate not in group:
                not_applicable += 1
                continue
            a, b = group[baseline]["primary_attempt"], group[candidate]["primary_attempt"]
            completed = (
                a is not None and b is not None and a["status"] == b["status"] == "completed"
            )
            left, right = (
                resources.get(a["attempt_id"]) if a else None,
                resources.get(b["attempt_id"]) if b else None,
            )
            row = {
                "case_id": key[0],
                "case_revision": key[1],
                "repetition_id": key[2],
                "baseline_attempt_id": a["attempt_id"] if a else None,
                "candidate_attempt_id": b["attempt_id"] if b else None,
                "completed_pair": completed,
                "reason": None if completed else "selected_attempt_not_completed",
                "resources": {},
                "costs": {},
                "quality": quality_delta(native_rows.get(key), baseline, candidate)
                if completed
                else {"availability": "selected_attempt_not_completed"},
                "caveats": [],
            }
            for metric in ("elapsed_seconds", *METRICS):
                compatible = completed
                if metric == "elapsed_seconds":
                    compatible = (
                        compatible
                        and left is not None
                        and right is not None
                        and left["elapsed_cohort"]
                        == right["elapsed_cohort"]
                        == "successful_invocation_through_cleanup"
                    )
                row["resources"][metric] = difference(
                    left["metrics"][metric] if left else None,
                    right["metrics"][metric] if right else None,
                    compatible=compatible,
                    reason="timing_or_completion_mismatch"
                    if metric == "elapsed_seconds"
                    else "selected_attempt_not_completed",
                )
            row["costs"] = (
                cost_deltas(left, right)
                if completed
                else {
                    mode: difference(
                        None, None, compatible=False, reason="selected_attempt_not_completed"
                    )
                    for mode in ("actual", "estimated", "best_available")
                }
            )
            if a and b:
                for field in ("cache", "order", "concurrency"):
                    x, y = a["execution_metadata"].get(field), b["execution_metadata"].get(field)
                    if x is None or y is None or x != y:
                        row["caveats"].append(
                            {
                                "field": field,
                                "baseline": x,
                                "candidate": y,
                                "reason": "unverified" if x is None or y is None else "unequal",
                            }
                        )
                if a["configuration_sha256"] != b["configuration_sha256"]:
                    row["caveats"].append(
                        {
                            "field": "configuration_sha256",
                            "baseline": a["configuration_sha256"],
                            "candidate": b["configuration_sha256"],
                            "reason": "unequal",
                        }
                    )
            if left and right:
                x, y = left.get("timing_scope"), right.get("timing_scope")
                if x != y or x != "selected_invocation_through_cleanup":
                    row["caveats"].append(
                        {
                            "field": "timing_scope",
                            "baseline": x,
                            "candidate": y,
                            "reason": "incompatible",
                        }
                    )
            row["cost_context"] = {}
            for side, resource in (("baseline", left), ("candidate", right)):
                cost = resource.get("cost") if resource else None
                row["cost_context"][side] = (
                    {k: cost[k] for k in ("currency", "accounting_basis", "prices_sha256")}
                    if cost
                    else None
                )
            rows.append(row)
        medians = {}
        for metric in ("elapsed_seconds", *METRICS):
            values = [
                r["resources"][metric]["difference"]
                for r in rows
                if r["resources"][metric]["difference"] is not None
            ]
            medians[metric] = {
                "comparable_pairs": len(values),
                "difference": median(values) if values else None,
            }
        quality_medians = {}
        for metric in ("auxiliary_total", "overall_total"):
            values = [
                r["quality"].get("totals", {}).get(metric, {}).get("difference") for r in rows
            ]
            values = [v for v in values if v is not None]
            quality_medians[metric] = {
                "comparable_pairs": len(values),
                "difference": median(values) if values else None,
            }
        a, b = (
            population["by_version"][baseline]["planned_completion"],
            population["by_version"][candidate]["planned_completion"],
        )
        compatible = not not_applicable and a["denominator"] == b["denominator"]
        completion = difference(
            a["fraction"],
            b["fraction"],
            compatible=compatible,
            reason="planned_population_mismatch",
        )
        completion.update(
            baseline=a,
            candidate=b,
            lower_bound=b["lower_bound"] - a["upper_bound"]
            if compatible and a["upper_bound"] is not None and b["lower_bound"] is not None
            else None,
            upper_bound=b["upper_bound"] - a["lower_bound"]
            if compatible and b["upper_bound"] is not None and a["lower_bound"] is not None
            else None,
        )
        output.append(
            {
                "baseline": baseline,
                "candidate": candidate,
                "eligible": len(rows),
                "completed": sum(r["completed_pair"] for r in rows),
                "excluded": sum(not r["completed_pair"] for r in rows),
                "not_applicable_groups": not_applicable,
                "native_quality_pairs": sum(
                    r["quality"]["availability"] == "available" for r in rows
                ),
                "rows": rows,
                "descriptive_medians": medians,
                "quality_medians": quality_medians,
                "cost_medians": cost_medians(rows),
                "completion_difference": completion,
            }
        )
    return output


def cost_medians(rows):
    cohorts = {}
    for row in rows:
        basis = row["cost_context"]["baseline"]
        if basis is None:
            continue
        for mode in ("actual", "estimated", "best_available"):
            value = row["costs"][mode]["difference"]
            if value is not None:
                key = (mode, basis["currency"], basis["accounting_basis"], basis["prices_sha256"])
                cohorts.setdefault(key, []).append(Decimal(value))
    return [
        {
            "mode": k[0],
            "currency": k[1],
            "accounting_basis": k[2],
            "prices_sha256": k[3],
            "comparable_pairs": len(values),
            "difference": money(median(values)),
        }
        for k, values in sorted(cohorts.items())
    ]
