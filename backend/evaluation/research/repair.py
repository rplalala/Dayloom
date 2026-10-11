"""Independent Repair views over declared generation and controlled populations."""

from collections import Counter
from fractions import Fraction

from backend.cli.collection import _require

from .controlled import controlled_view
from .native import quality_rows, read_mechanism, read_pair, selected_groups
from .rendering import table_row
from .sources import digest


def summary(rows):
    return {
        "expected_slots": len(rows),
        "comparable": sum(r["classification"] != "unavailable" for r in rows),
        **{
            name: sum(r["classification"] == name for r in rows)
            for name in ("improved", "unchanged", "worse", "unavailable")
        },
    }


def classify(delta):
    value = delta.get("exact_fraction") if delta else None
    if value is None:
        return "unavailable"
    numerator = value["numerator"]
    return "improved" if numerator > 0 else "worse" if numerator < 0 else "unchanged"


def difference(before, after):
    a, b = before.get("exact_fraction"), after.get("exact_fraction")
    if a is None or b is None:
        return {"percentage_points": None, "exact_fraction": None}
    result = Fraction(b["numerator"], b["denominator"]) - Fraction(a["numerator"], a["denominator"])
    return {
        "percentage_points": float(result * 100),
        "exact_fraction": {"numerator": result.numerator, "denominator": result.denominator},
    }


def final_difference(group, baseline="v2", candidate="v3"):
    left, right = group["versions"][baseline], group["versions"][candidate]
    return {
        **{
            name: difference(left[name], right[name])
            for name in ("overall_total", "auxiliary_total")
        },
        "daily_density_penalty": (
            right["daily_density"]["mean_penalty_0_100"]
            - left["daily_density"]["mean_penalty_0_100"]
            if left["daily_density"]["mean_penalty_0_100"] is not None
            and right["daily_density"]["mean_penalty_0_100"] is not None
            else None
        ),
        "dimensions": {
            name: difference(
                {
                    "exact_fraction": left["dimensions"][name]["exact_fractions"][
                        "verified_fraction"
                    ]
                },
                {
                    "exact_fraction": right["dimensions"][name]["exact_fractions"][
                        "verified_fraction"
                    ]
                },
            )
            for name in left["dimensions"]
        },
    }


def material(context):
    ref = context.declaration.get("track_refs", {}).get("repair")
    if ref is None:
        return {}
    value = context.read_ref(ref, "rtpeval_research_repair_1")
    _require(
        (
            value.get("population_id"),
            value.get("population_revision"),
            value.get("profile_id"),
            value.get("profile_revision"),
        )
        == (
            context.population["population_id"],
            context.population["revision"],
            context.profile["profile_id"],
            context.profile["revision"],
        ),
        "Foreign or stale Repair population/profile binding",
    )
    for name in ("quality_reports", "pair_reports", "mechanism_reports"):
        _require(
            isinstance(value.get(name, []), list),
            "Explicit native report descriptor array required",
        )
    return value


def continuity_counts(pair):
    rows = [row for values in pair.get("continuity", {}).values() for row in values]
    counts = Counter(row["transition"] for row in rows)
    return {
        "unit": "native_continuity_checks",
        "transitions": dict(sorted(counts.items())),
        "residual_failures": sum(
            (row.get("before") or {}).get("state") == "FAIL"
            and (row.get("after") or {}).get("state") == "FAIL"
            for row in rows
        ),
        "unresolved_before": len(
            pair.get("correspondence", {}).get("unresolved", {}).get("before", [])
        ),
        "unresolved_after": len(
            pair.get("correspondence", {}).get("unresolved", {}).get("after", [])
        ),
    }


def repair_report(context):
    supplied = material(context)
    finals = quality_rows(context, supplied.get("quality_reports", []))
    pairs, mechanisms = {}, {}
    for descriptor in supplied.get("pair_reports", []):
        report = read_pair(context, descriptor)
        _, _, bindings = selected_groups(context, descriptor)
        by_group = {group["group_id"]: group for group in report["groups"]}
        for key, binding in bindings.items():
            _require(key not in pairs, "Duplicate same-run native pair")
            pairs[key] = {"report": report, "pair": by_group[binding["intake_group"]["group_id"]]}
    for descriptor in supplied.get("mechanism_reports", []):
        report = read_mechanism(context, descriptor)
        for run in report["runs"]:
            if run["version"] == "v3":
                _require(run["run_id"] not in mechanisms, "Duplicate selected mechanism run")
                mechanisms[run["run_id"]] = run
    rows, final_rows = [], []
    for slot in context.slots:
        if slot["version"] != "v3":
            continue
        key = tuple(slot[name] for name in ("case_id", "case_revision", "repetition_id"))
        attempt = slot["primary_attempt"]
        common = {
            **{
                name: slot[name] for name in ("case_id", "case_revision", "repetition_id", "status")
            },
            "version": "v3",
            "attempt_id": attempt["attempt_id"] if attempt else None,
            "run_id": attempt["run_id"] if attempt else None,
        }
        source = pairs.get(key)
        pair = source["pair"] if source else None
        mechanism = mechanisms.get(common["run_id"])
        attempted = (
            bool(mechanism["model_attempts"])
            if mechanism and mechanism["coverage"] == "available"
            else None
        )
        delta = pair["deltas"]["overall_total"] if pair and pair["deltas"] else None
        classification = classify(delta)
        rows.append(
            {
                **common,
                "classification": classification,
                "reason": None
                if classification != "unavailable"
                else "native_pair_or_score_unavailable",
                "native": pair,
                "native_profile": source["report"]["rules_profile"] if source else None,
                "native_report_sha256": source["report"]["content_hash"] if source else None,
                "continuity": continuity_counts(pair) if pair else None,
                "repair_attempted": attempted,
                "mechanism": mechanism,
            }
        )
        final = finals.get(key)
        delta = final_difference(final["group"]) if final else None
        classification = classify(delta["overall_total"] if delta else None)
        final_rows.append(
            {
                **common,
                "baseline": "v2",
                "candidate": "v3",
                "classification": classification,
                "deltas": delta,
                "native_group": final["group"] if final else None,
                "native_profile": final["report"]["rules_profile"] if final else None,
                "native_report_sha256": final["report"]["content_hash"] if final else None,
                "reason": None
                if classification != "unavailable"
                else "native_final_or_score_unavailable",
            }
        )
    conditional = [row for row in rows if row["repair_attempted"] is True]
    report = {
        "schema_version": "rtpeval_research_repair_report_1",
        "processing_status": "completed",
        "track": "repair",
        "applicability": "applicable" if rows or supplied.get("controlled") else "not_applicable",
        "same_run": {
            "rows": rows,
            "summary": summary(rows),
            "conditional_attempted_repair": {
                "rows": conditional,
                "summary": summary(conditional),
                "unknown_attempt_observations": sum(r["repair_attempted"] is None for r in rows),
            },
        },
        "four_final": {"rows": final_rows, "summary": summary(final_rows)},
        "controlled": controlled_view(context, supplied.get("controlled")),
        "measurement_coverage": {"native_pairs": len(pairs), "native_final_groups": len(finals)},
        "review_coverage": {"native_independent_reports": len(pairs) + len(finals)},
        "population_digest": digest(context.population),
        "selection_profile": context.profile,
        "source_bindings": context.sources.manifest(),
        "source_digest": digest(context.sources.manifest()),
        "diagnostics": [],
        "interpretation": "Descriptive independent outcomes; populations remain separate.",
    }
    report["semantic_sha256"] = digest(report)
    return report


def markdown(report):
    counts = report["same_run"]["summary"]
    lines = [
        "# Independent Repair summaries",
        "",
        f"Comparable same-run pairs: {counts['comparable']}/{counts['expected_slots']}.",
        "",
        "| Population | Improved | Unchanged | Worse | Unavailable |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, values in (
        ("V3 minus V2 finals", report["four_final"]["summary"]),
        ("Same-run V3 draft to final primary", counts),
    ):
        lines.append(
            table_row(
                label,
                values["improved"],
                values["unchanged"],
                values["worse"],
                values["unavailable"],
            )
        )
    controlled = report["controlled"]
    if controlled["applicability"] != "not_declared":
        resolved, joint = controlled["resolution"], controlled["case_joint_success"]
        coverage = controlled["verdict_coverage"]
        lines += [
            "",
            "## Declared controlled study",
            "",
            f"Independent target resolution: {resolved['numerator']}/{resolved['denominator']}.",
            f"Joint target-case success: {joint['numerator']}/{joint['denominator']}.",
            f"Independent target verdict coverage: {coverage['available']}/{coverage['expected']}.",
            "",
            "| Preservation | Targets |",
            "| --- | ---: |",
        ]
        lines += [table_row(name, count) for name, count in controlled["preservation"].items()]
        lines += ["", "| Control outcome | Cases |", "| --- | ---: |"]
        lines += [table_row(name, count) for name, count in controlled["control_outcomes"].items()]
    lines += [
        "",
        "Four-final masks and same-run pair masks retain their native definitions.",
        "Deletion and replacement do not prove resolution of the original condition.",
        "",
        f"Semantic SHA-256: `{report['semantic_sha256']}`",
        "",
    ]
    return "\n".join(lines)
