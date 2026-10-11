"""Distinct completion denominators for the full original-input population."""

from collections import Counter

from .context import STATUSES, VERSIONS
from .rendering import cell, table_row
from .sources import digest


def fraction(completed, denominator, unresolved, unit):
    return {
        "numerator": completed,
        "denominator": denominator,
        "unit": unit,
        "confirmed_fraction": completed / denominator if denominator else None,
        "fraction": completed / denominator if denominator and not unresolved else None,
        "lower_bound": completed / denominator if denominator else None,
        "upper_bound": (completed + unresolved) / denominator if denominator else None,
        "unresolved": unresolved,
        "availability": "unavailable"
        if not denominator
        else "bounded"
        if unresolved
        else "available",
    }


def summarize(slots):
    counts = Counter(slot["status"] for slot in slots)
    first = [slot["primary_attempt"] for slot in slots if slot["primary_attempt"] is not None]
    conditional = fraction(
        sum(a["status"] == "completed" for a in first),
        len(first),
        sum(a["status"] == "unknown_pending" for a in first),
        "dispatched_first_attempts",
    )
    missing_dispatch = sum(not slot["attempts"] for slot in slots)
    conditional.update(
        unknown_dispatch_slots=missing_dispatch,
        denominator_lower_bound=len(first),
        denominator_upper_bound=len(first) + missing_dispatch,
    )
    if first and missing_dispatch:
        conditional.update(
            fraction=None,
            availability="bounded",
            lower_bound=conditional["numerator"] / (len(first) + missing_dispatch),
            upper_bound=(conditional["numerator"] + conditional["unresolved"] + missing_dispatch)
            / (len(first) + missing_dispatch),
        )
    return {
        "planned_completion": fraction(
            counts["completed"], len(slots), counts["unknown_pending"], "planned_slots"
        ),
        "conditional_completion": conditional,
        "status_counts": {status: counts[status] for status in STATUSES},
        "reason_counts": dict(sorted(Counter(slot["reason_type"] for slot in slots).items())),
        "attempt_census": {
            "records": sum(len(slot["attempts"]) for slot in slots),
            "dispatched": sum(a["dispatched"] for slot in slots for a in slot["attempts"]),
            "retry_dispatches": sum(
                max(0, sum(a["dispatched"] for a in slot["attempts"]) - 1) for slot in slots
            ),
        },
    }


def population_report(context):
    slots = context.slots
    groups = {}
    for slot in slots:
        key = (slot["case_id"], slot["case_revision"], slot["repetition_id"])
        groups.setdefault(key, []).append(slot)
    all_four = []
    for (case, revision, repetition), members in groups.items():
        applicable = {slot["version"] for slot in members} == set(VERSIONS)
        completed = applicable and all(slot["status"] == "completed" for slot in members)
        unresolved = (
            applicable
            and not completed
            and all(slot["status"] in ("completed", "unknown_pending") for slot in members)
        )
        all_four.append(
            {
                "case_id": case,
                "case_revision": revision,
                "repetition_id": repetition,
                "status": "not_applicable"
                if not applicable
                else "completed"
                if completed
                else "unknown_pending"
                if unresolved
                else "not_completed",
            }
        )
    report = {
        "schema_version": "rtpeval_research_population_report_1",
        "processing_status": "completed",
        "track": "population",
        "applicability": "applicable",
        "population": {
            "population_id": context.population["population_id"],
            "revision": context.population["revision"],
            "unique_requests": len(context.population["cases"]),
            "planned_slots": len(slots),
        },
        "selection_profile": context.profile,
        "measurement_coverage": {
            "census_slots": sum(bool(slot["attempts"]) for slot in slots),
            "planned_slots": len(slots),
            "missing_census_slots": sum(not slot["attempts"] for slot in slots),
            "completion_declarations": sum(
                a["producer_completion"] is not None for slot in slots for a in slot["attempts"]
            ),
            "census_records": sum(len(slot["attempts"]) for slot in slots),
        },
        "review_coverage": {"applicability": "not_applicable"},
        "summary": summarize(slots),
        "by_version": {v: summarize([s for s in slots if s["version"] == v]) for v in VERSIONS},
        "by_repetition": [
            {"repetition_id": rep, **summarize([s for s in slots if s["repetition_id"] == rep])}
            for rep in dict.fromkeys(s["repetition_id"] for s in slots)
        ],
        "by_version_repetition": [
            {
                "version": version,
                "repetition_id": repetition,
                "summary": summarize(
                    [
                        s
                        for s in slots
                        if s["version"] == version and s["repetition_id"] == repetition
                    ]
                ),
            }
            for repetition in dict.fromkeys(s["repetition_id"] for s in slots)
            for version in VERSIONS
            if any(s["version"] == version and s["repetition_id"] == repetition for s in slots)
        ],
        "by_request": [
            {
                "case_id": case["case_id"],
                "case_revision": case["revision"],
                "repetition_ids": case["repetition_ids"],
                "input_ref": case["input_ref"],
                "metadata": case["metadata"],
                "planned_versions": case["planned_versions"],
                "summary": summarize([s for s in slots if s["case_id"] == case["case_id"]]),
            }
            for case in context.population["cases"]
        ],
        "quality_candidate_material": {
            "completed_selected_attempts": sum(s["status"] == "completed" for s in slots),
            "with_result_refs": sum(
                s["status"] == "completed" and s["primary_attempt"].get("result_ref") is not None
                for s in slots
            ),
            "missing_result_refs": sum(
                s["status"] == "completed" and s["primary_attempt"].get("result_ref") is None
                for s in slots
            ),
            "non_completed_or_unresolved_slots": sum(s["status"] != "completed" for s in slots),
            "native_qualification": "not_performed",
        },
        "all_four": {
            "rows": all_four,
            "excluded_not_all_four": sum(r["status"] == "not_applicable" for r in all_four),
            "completion": fraction(
                sum(r["status"] == "completed" for r in all_four),
                sum(r["status"] != "not_applicable" for r in all_four),
                sum(r["status"] == "unknown_pending" for r in all_four),
                "request_repetitions",
            ),
        },
        "slots": slots,
        "source_bindings": context.sources.manifest(),
        "population_digest": digest(context.population),
        "source_digest": digest(context.sources.manifest()),
        "diagnostics": [],
        "quality_qualification": "unchanged_native_four_version_intake",
    }
    report["semantic_sha256"] = digest(report)
    return report


def markdown(report):
    summary = report["summary"]["planned_completion"]
    population = report["population"]
    lines = [
        "# Original-input population completion",
        "",
        f"Population: {cell(population['population_id'])}; "
        f"original requests: {population['unique_requests']}.",
        "",
        f"Confirmed completion: {summary['numerator']}/{summary['denominator']} "
        f"planned slots; unresolved: {summary['unresolved']}.",
        "",
        "| Version | Completed / planned | Unresolved | Dispatched first attempts |",
        "| --- | ---: | ---: | ---: |",
    ]
    for version, row in report["by_version"].items():
        completion = row["planned_completion"]
        lines.append(
            table_row(
                version,
                f"{completion['numerator']}/{completion['denominator']}",
                completion["unresolved"],
                row["conditional_completion"]["denominator"],
            )
        )
    conditional = report["summary"]["conditional_completion"]
    four = report["all_four"]["completion"]
    lines += [
        "",
        "Planned completion lower/upper bounds: "
        f"{summary['lower_bound']} / {summary['upper_bound']}.",
        f"Conditional completion: {conditional['numerator']}/{conditional['denominator']} "
        f"known dispatched first attempts; availability: {conditional['availability']}. "
        f"Lower/upper bounds: {conditional['lower_bound']} / {conditional['upper_bound']}; "
        f"slots with unknown dispatch: {conditional['unknown_dispatch_slots']}.",
        f"All-four completion: {four['numerator']}/{four['denominator']} "
        "request/repetition groups. "
        f"Lower/upper bounds: {four['lower_bound']} / {four['upper_bound']}.",
        "",
        "| State | Slots |",
        "| --- | ---: |",
        *(table_row(status, count) for status, count in report["summary"]["status_counts"].items()),
        "",
        f"Selection timing basis: {report['selection_profile']['timing_basis']}; "
        "retries are retained separately from primary selection.",
        "",
        "Missing attempt records remain unknown. "
        "Workflow completion is independent of quality scores.",
        "",
        f"Semantic SHA-256: `{report['semantic_sha256']}`",
        "",
    ]
    return "\n".join(lines)
