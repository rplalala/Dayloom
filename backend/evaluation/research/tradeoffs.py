"""Source-bound generation benefit/resource comparisons, without new scoring."""

from backend.cli.collection import _require

from .comparisons import pairs_report
from .costs import attach_costs
from .population import population_report
from .resources import all_attempts
from .sources import digest


def tradeoffs_report(context):
    population = population_report(context)
    track = {}
    if context.declaration.get("track_refs", {}).get("tradeoffs") is not None:
        track = context.read_ref(
            context.declaration["track_refs"]["tradeoffs"], "rtpeval_research_tradeoffs_1"
        )
    _require(
        set(track) <= {"schema_version", "quality_reports", "cost_ledgers", "comparisons"},
        "Unknown tradeoff material fields",
    )
    _require(
        isinstance(track.get("quality_reports", []), list),
        "Explicit native quality descriptor array required",
    )
    ledger = all_attempts(context)
    attach_costs(context, ledger, track.get("cost_ledgers", []))
    native_rows = {}
    if track.get("quality_reports"):
        from .native import quality_rows

        native_rows = quality_rows(context, track["quality_reports"])
    pairs = pairs_report(
        context,
        population,
        ledger,
        native_rows,
        track.get(
            "comparisons",
            [{"baseline": "v1", "candidate": "v2"}, {"baseline": "v2", "candidate": "v3"}],
        ),
    )
    output = {
        "schema_version": "rtpeval_research_tradeoffs_report_1",
        "track": "tradeoffs",
        "processing_status": "completed",
        "applicability": "applicable",
        "profile_ids": {
            "selection": context.profile["profile_id"],
            "selection_revision": context.profile["revision"],
        },
        "population_digest": population["population_digest"],
        "measurement_coverage": {
            "planned_slots": len(context.slots),
            "dispatched_attempts": ledger["dispatched_attempts"],
            "missing_usage_attempts": ledger["missing_usage_attempts"],
            "unknown_or_pending_slots": ledger["unknown_or_pending_slots"],
        },
        "review_coverage": {
            "native_quality_groups": len(native_rows),
            "reviewer_execution": "not_performed",
        },
        "diagnostics": [],
        "interpretation": "descriptive_observations_only",
        "generation_scope": (
            "planner_only; repair_is_a_subset; evaluator_and_frozen_simulation_excluded"
        ),
        "population_completion": population,
        "all_attempts": ledger,
        "paired_comparisons": pairs,
        "source_bindings": context.sources.manifest(),
        "source_digest": digest(context.sources.manifest()),
    }
    output["semantic_sha256"] = digest(output)
    return output


def markdown(report):
    population = report["population_completion"]
    fraction = population["summary"]["planned_completion"]
    ledger = report["all_attempts"]
    lines = [
        "# Generation benefit and resources",
        "",
        f"Confirmed workflow completion: "
        f"{fraction['numerator']}/{fraction['denominator']} planned slots; "
        f"unresolved: {fraction['unresolved']}. Bounds: {fraction['lower_bound']} to "
        f"{fraction['upper_bound']}.",
        "",
        "Generation uses the planner namespace. Repair is a subset counted once. "
        "Selected successful resources and all-attempt consumption have separate "
        "populations. HTTP sends are transport observations, not confirmed charges.",
        "",
        "## Selected first-attempt comparisons",
        "",
    ]
    for pair in report["paired_comparisons"]:
        lines += [
            f"### {pair['candidate']} minus {pair['baseline']}",
            "",
            f"Completed pairs: {pair['completed']}/{pair['eligible']}; excluded: "
            f"{pair['excluded']}; native quality pairs: {pair['native_quality_pairs']}.",
            "",
            "| Case / repetition | Completed | Token difference | Elapsed "
            "difference (s) | Estimated cost difference | Native overall difference |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
        for row in pair["rows"]:
            quality = row["quality"].get("totals", {}).get("overall_total", {}).get("difference")
            lines.append(
                f"| {row['case_id']} / {row['repetition_id']} | "
                f"{row['completed_pair']} | "
                f"{row['resources']['total_tokens']['difference']} | "
                f"{row['resources']['elapsed_seconds']['difference']} | "
                f"{row['costs']['estimated']['difference']} | {quality} |"
            )
        lines += [
            "",
            "Medians of comparable resource differences:",
            "",
            "| Metric | Comparable pairs | Median difference |",
            "| --- | ---: | ---: |",
        ]
        for metric, summary in pair["descriptive_medians"].items():
            lines.append(f"| {metric} | {summary['comparable_pairs']} | {summary['difference']} |")
        completion = pair["completion_difference"]
        lines += [
            "",
            f"Full-population completion difference: {completion['difference']}; "
            f"bounds: {completion['lower_bound']} to {completion['upper_bound']}.",
            "",
        ]
    lines += [
        "## All-attempt generation consumption",
        "",
        f"Dispatched attempts: {ledger['dispatched_attempts']}; missing usage: "
        f"{ledger['missing_usage_attempts']}; complete ledger: {ledger['ledger_complete']}.",
        "",
        "| Version | Dispatched | Complete ledger | Observed token subtotal | "
        "Complete token total |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for version, row in ledger["by_version"].items():
        tokens = row["totals"]["total_tokens"]
        lines.append(
            f"| {version} | {row['dispatched_attempts']} | {row['ledger_complete']} "
            f"| {tokens['observed_subtotal']} | {tokens['total']} |"
        )
    lines += [
        "",
        "Successful elapsed cohorts remain separate from failed/censored observations:",
        "",
        "| Version | Workflow status | Timing cohort | Observed attempts | Median seconds |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for row in ledger["elapsed_cohorts"]:
        lines.append(
            f"| {row['version']} | {row['workflow_status']} | {row['cohort']} | "
            f"{row['observed_attempts']} | {row['median']} |"
        )
    lines += [
        "",
        "Null totals retain unavailable coverage. Unequal or unverified cache, "
        "order, concurrency, configuration and timing appear in per-case caveats. "
        "Compatible medians are descriptive; they establish no efficiency score or "
        "causal/significance conclusion.",
        "",
        f"Semantic SHA-256: `{report['semantic_sha256']}`",
        "",
    ]
    return "\n".join(lines)
