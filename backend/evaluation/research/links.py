"""Descriptive links between independently rebuilt benefits and planner resources."""

from .resources import METRICS
from .sources import digest

IDENTITY = ("case_id", "case_revision", "repetition_id")


def _key(row):
    return tuple(row[name] for name in IDENTITY)


def _attempt(slot):
    attempt = slot["primary_attempt"]
    return {
        **{
            name: slot[name]
            for name in (*IDENTITY, "version", "input_sha256", "configuration_sha256", "status")
        },
        "attempt_id": attempt["attempt_id"] if attempt else None,
        "run_id": attempt["run_id"] if attempt else None,
        "group_id": attempt.get("group_id") if attempt else None,
        **{
            field + "_sha256": (attempt.get(field + "_ref") or {}).get("sha256")
            if attempt
            else None
            for field in ("result", "usage", "provenance")
        },
    }


def _binding(report, track, pointer):
    if report is None:
        return None
    return {
        "track": track,
        "pointer": pointer,
        **{
            field: report[field]
            for field in ("population_digest", "source_digest", "semantic_sha256")
        },
    }


def _row_at(rows, key):
    return next(((row, i) for i, row in enumerate(rows) if _key(row) == key), (None, None))


def _resource_measurements(matches, expected):
    coverage = {
        metric: {
            "known_attempts": sum(row["metrics"][metric] is not None for row in matches),
            "missing_attempts": expected
            - sum(row["metrics"][metric] is not None for row in matches),
            "observed_subtotal_attempts": sum(
                row.get("observed_subtotals", {}).get(metric) is not None for row in matches
            ),
        }
        for metric in ("elapsed_seconds", *METRICS)
    }
    complete = all(value["missing_attempts"] == 0 for value in coverage.values())
    observed = any(
        value["known_attempts"] or value["observed_subtotal_attempts"]
        for value in coverage.values()
    )
    costs = [row["cost"]["native"] for row in matches if row.get("cost")]
    observed_costs = sum(
        any(
            cost.get(mode + suffix) is not None
            for mode in ("actual", "estimated", "best_available")
            for suffix in ("_total", "_observed_subtotal")
        )
        or cost.get("run_bill") is not None
        for cost in costs
    )
    coverage["cost"] = {
        "observed_attempts": observed_costs,
        "missing_attempts": expected - observed_costs,
        "by_mode": {
            mode: {
                "known_total_attempts": sum(
                    cost.get(mode + "_total") is not None for cost in costs
                ),
                "missing_total_attempts": expected
                - sum(cost.get(mode + "_total") is not None for cost in costs),
                "observed_subtotal_attempts": sum(
                    cost.get(mode + "_observed_subtotal") is not None for cost in costs
                ),
            }
            for mode in ("actual", "estimated", "best_available")
        },
    }
    status = "available" if complete else "partial" if observed or observed_costs else "unavailable"
    return status, coverage


def benefit_resource_links(context, reports):
    """Keep unmatched planned units; same-run V3 never becomes an independent V2 pair."""
    groups = {}
    for slot in context.slots:
        groups.setdefault(_key(slot), {})[slot["version"]] = slot
    resources = reports.get("tradeoffs")
    ledger = (
        {row["attempt_id"]: row for row in resources["all_attempts"]["rows"]} if resources else {}
    )
    result = []
    for key, versions in groups.items():
        for kind, required, view in (
            ("rag_v2_minus_v1", ("v1", "v2"), "selected_version_pair"),
            ("repair_v3_minus_v2_finals", ("v2", "v3"), "selected_version_pair"),
            ("repair_same_run_v3", ("v3",), "selected_v3_invocation"),
        ):
            selected = [_attempt(versions[v]) for v in required if v in versions]
            row = {
                **dict(zip(IDENTITY, key, strict=True)),
                "kind": kind,
                "resource_view": view,
                "selected_attempts": selected,
                "status": "unavailable",
                "benefit_status": "unavailable",
                "resource_status": "unavailable",
                "source_compatible": False,
                "benefit": None,
                "resources": None,
                "reasons": [],
            }
            if len(selected) != len(required):
                row["reasons"].append("missing_planned_version")
            benefit_report, benefit_track, benefit_row, pointer = None, None, None, None
            if kind == "rag_v2_minus_v1":
                benefit_track = "relevance" if "relevance" in reports else "opportunities"
                benefit_report = reports.get(benefit_track)
                if benefit_report:
                    family = "comparisons" if benefit_track == "relevance" else "cross_version"
                    benefit_row, i = _row_at(benefit_report[family], key)
                    pointer = f"/{family}/{i}" if i is not None else None
                    if benefit_row and benefit_track == "relevance":
                        available = benefit_row["end_to_end"]["status"] == "complete"
                    else:
                        available = bool(
                            benefit_row
                            and any(
                                benefit_row.get(name, {}).get("status") == "complete"
                                for name in ("discovered", "admitted", "supplied", "scheduled")
                            )
                        )
                    run_ids = {
                        run["version"]: run["attempt_id"]
                        for run in benefit_report["runs"]
                        if _key(run) == key
                    }
                    if any(run_ids.get(a["version"]) != a["attempt_id"] for a in selected):
                        raise ValueError("Research RAG benefit selected-attempt mismatch")
                    row["benefit_status"] = "available" if available else "unavailable"
            else:
                benefit_track, benefit_report = "repair", reports.get("repair")
                if benefit_report:
                    family = "same_run" if kind == "repair_same_run_v3" else "four_final"
                    benefit_row, i = _row_at(benefit_report[family]["rows"], key)
                    pointer = f"/{family}/rows/{i}" if i is not None else None
                    if benefit_row:
                        attempt = next((a for a in selected if a["version"] == "v3"), None)
                        if attempt and (benefit_row["attempt_id"], benefit_row["run_id"]) != (
                            attempt["attempt_id"],
                            attempt["run_id"],
                        ):
                            raise ValueError("Research Repair benefit selected-attempt mismatch")
                        row["benefit_status"] = (
                            "available"
                            if benefit_row["classification"] != "unavailable"
                            else "unavailable"
                        )
                        row["native_report_sha256"] = benefit_row["native_report_sha256"]
            row["benefit"] = _binding(benefit_report, benefit_track, pointer)
            if benefit_report is None:
                row["reasons"].append("benefit_track_not_selected")
            elif row["benefit_status"] == "unavailable":
                row["reasons"].append("benefit_measurement_unavailable")
            matches = []
            for attempt in selected:
                measured = ledger.get(attempt["attempt_id"])
                if measured is None:
                    continue
                if (
                    not measured["selected_primary"]
                    or any(
                        measured[field] != attempt[field]
                        for field in (*IDENTITY, "version", "run_id")
                    )
                    or measured.get("usage_sha256") != attempt["usage_sha256"]
                ):
                    raise ValueError("Research resource selected-attempt/source mismatch")
                matches.append(measured)
            compatible = (
                len(selected) == len(required)
                and len(matches) == len(required)
                and all(a["attempt_id"] is not None for a in selected)
            )
            if compatible and benefit_report:
                if benefit_report["population_digest"] != resources[
                    "population_digest"
                ] or resources["population_digest"] != digest(context.population):
                    raise ValueError("Research benefit/resource population mismatch")
            if resources:
                if view == "selected_v3_invocation":
                    i = next(
                        (
                            i
                            for i, r in enumerate(resources["all_attempts"]["rows"])
                            if selected and r["attempt_id"] == selected[0]["attempt_id"]
                        ),
                        None,
                    )
                    resource_pointer = f"/all_attempts/rows/{i}" if i is not None else None
                else:
                    resource_pointer = None
                    for p, pair in enumerate(resources["paired_comparisons"]):
                        if (pair["baseline"], pair["candidate"]) != required:
                            continue
                        resource_row, i = _row_at(pair["rows"], key)
                        if resource_row is not None:
                            if len(selected) == 2 and (
                                resource_row["baseline_attempt_id"],
                                resource_row["candidate_attempt_id"],
                            ) != tuple(a["attempt_id"] for a in selected):
                                raise ValueError("Research resource pair selected-attempt mismatch")
                            resource_pointer = f"/paired_comparisons/{p}/rows/{i}"
                    compatible = compatible and resource_pointer is not None
                row["resources"] = _binding(resources, "tradeoffs", resource_pointer)
                if compatible:
                    row["source_compatible"] = benefit_report is not None
                    row["resource_status"], row["resource_measurement_coverage"] = (
                        _resource_measurements(matches, len(required))
                    )
            if row["resource_status"] == "unavailable":
                row["reasons"].append(
                    "resource_track_not_selected"
                    if resources is None
                    else "selected_usage_unavailable"
                )
            elif row["resource_status"] == "partial":
                row["reasons"].append("partial_resource_measurement")
            if (
                row["source_compatible"]
                and row["benefit_status"] == "available"
                and row["resource_status"] != "unavailable"
            ):
                row["status"] = "matched" if row["resource_status"] == "available" else "partial"
            result.append(row)
    return result
