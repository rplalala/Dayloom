"""Descriptive V3 mechanism units, separate from independently verified outcomes."""

from .mechanism_preparation import diagnostic, linkage, unique_rows, validated_preparation
from .records import canonical_digest, require
from .usage_report import summarize

STATUSES = ("SKIPPED", "REJECTED", "ACCEPTED_PARTIAL", "ACCEPTED_COMPLETE")


def _targets(report):
    require(isinstance(report, dict), "original_report", "Saved validation report required")
    findings = {f["finding_id"]: f for f in report["findings"]}
    require(len(findings) == len(report["findings"]), "findings", "Duplicate finding IDs")
    ids = [t["finding_id"] for t in report["improvement_targets"]]
    require(
        len(ids) == len(set(ids)) and set(ids) <= set(findings),
        "targets",
        "Invalid improvement target links",
    )
    return ids


def _derived_targets(outcome):
    repair, scope = outcome["repair"], outcome["scope"]
    if repair.get("search_version") != 1 or not scope:
        return {}
    findings = outcome["original_report"]["findings"]
    if not any(
        f["check"] == "soft_pace" and f["finding_id"] in scope["target_ids"] for f in findings
    ):
        return {}
    move_dates = {d for p in scope.get("permissions", []) for d in p.get("move_dates", [])}
    return {
        f["finding_id"]: f
        for f in findings
        if f["check"] == "soft_pace"
        and f["dates"]
        and set(f["dates"]) <= set(scope["dates"]) & move_dates
        and f["finding_id"] not in scope["target_ids"]
    }


def _rounds(repair, original_targets, derived=None):
    require(
        repair["status"] in STATUSES and isinstance(repair["model_attempted"], bool),
        "repair",
        "Invalid Repair summary",
    )
    rows = repair["rounds"]
    # Legacy complete single-call results have no multiround children. The saved result
    # describes that one call; a multiround cumulative summary is never an additional round.
    if not rows and repair["model_attempted"]:
        require(
            repair["counters"].get("model") == 1,
            "rounds",
            "Missing multiround children do not establish one model attempt",
        )
        rows = [
            {"round_index": 1, "result": repair, "target_links": {t: t for t in original_targets}}
        ]
    from .repair_selection import selected_prefix

    items = sorted(
        unique_rows(rows, lambda r: r["round_index"], "/v3/repair/rounds"),
        key=lambda item: item["value"]["round_index"],
    )
    prefix = selected_prefix(repair, [item["value"] for item in items])
    derived = derived or {}
    output = []
    for item in items:
        row, refs = item["value"], item["source_refs"]
        index = row["round_index"]
        require(type(index) is int and index >= 1, "round", "Invalid round index")
        result = row["result"]
        require(
            result["status"] in STATUSES and isinstance(result["model_attempted"], bool),
            "round",
            "Invalid round status/attempt observation",
        )
        links = row["target_links"]
        related = {t["permission"]["target_id"] for t in repair.get("related_targets", [])}
        related.update(t["permission"]["target_id"] for t in result.get("related_targets", []))
        require(
            isinstance(links, dict)
            and set(links.values()) <= set(original_targets) | related | set(derived),
            "round",
            "Round-local targets do not map to original authorized targets",
        )
        for local, source in links.items():
            if source in derived:
                matches = [
                    f for f in result["original_report"]["findings"] if f["finding_id"] == local
                ]
                require(
                    len(matches) == 1
                    and matches[0]["check"] == "soft_pace"
                    and matches[0]["dates"] == derived[source]["dates"],
                    "round",
                    "Invalid derived pace target",
                )
        component_rows = unique_rows(
            result["components"],
            lambda c: c["component_id"],
            f"/v3/repair/rounds/{index}/components",
        )
        components = [r["value"] for r in component_rows]
        evaluated, accepted, pending, unevaluated = [], [], [], []
        for component in components:
            require(
                component["status"]
                in ("accepted", "rejected", "pending", "not_attempted", "rolled_back"),
                "components",
                "Unknown component status",
            )
            if component["status"] == "pending":
                pending.append(component)
            if component.get("comparison") is not None:
                evaluated.append(component)
                if component["status"] == "accepted":
                    accepted.append(component)
            else:
                unevaluated.append(component)
        output.append(
            {
                "round_index": index,
                **(
                    {
                        "strategy": row["strategy"],
                        "exploration_transition": row["exploration_transition"],
                        "best_promoted": row["best_promoted"],
                        "selected_lineage": index <= prefix and row["exploration_transition"],
                        "derived_target_links": {k: v for k, v in links.items() if v in derived},
                    }
                    if prefix is not None
                    else {}
                ),
                "source_refs": refs,
                "status": result["status"],
                "model_attempted": result["model_attempted"],
                "accepted": result["status"].startswith("ACCEPTED_"),
                "target_links": {k: v for k, v in links.items() if v in original_targets},
                "related_target_links": {k: v for k, v in links.items() if v in related},
                "internal_progress": result["target_progress"],
                "related_targets": result.get("related_targets", []),
                "components": components,
                "component_source_refs": [r["source_refs"] for r in component_rows],
                "evaluated_components": len(evaluated),
                "accepted_components": len(accepted),
                "pending_components": len(pending),
                "unevaluated_components": len(unevaluated),
                "counters_snapshot": result["counters"],
                "usage_observation": row.get("usage", result.get("usage")),
                "continuation_reason": row.get("continuation_reason"),
            }
        )
    return sorted(output, key=lambda r: r["round_index"])


def _trace(run, rounds):
    channel = run["channels"]["trace"]
    if channel["status"] != "available":
        return [], channel["status"], channel["diagnostics"]
    observations = []
    try:
        for record in channel["records"]:
            for event in record["content"]["events"]:
                if event.get("event") == "v3_repair_round":
                    payload = event["payload"]
                    require(
                        payload["status"] in STATUSES and type(payload["round_index"]) is int,
                        "trace",
                        "Malformed round trace",
                    )
                    observations.append(payload)
        rows = unique_rows(observations, lambda r: r["round_index"], "trace/rounds")
        embedded = {r["round_index"]: r for r in rounds}
        for item in rows:
            row = item["value"]
            if row["round_index"] in embedded:
                saved = embedded[row["round_index"]]
                require(
                    row["status"] == saved["status"],
                    "trace",
                    "Trace contradicts saved round",
                )
                for trace_field, saved_field in (
                    ("continuation_reason", "continuation_reason"),
                    ("usage", "usage_observation"),
                    ("strategy", "strategy"),
                    ("exploration_transition", "exploration_transition"),
                    ("best_promoted", "best_promoted"),
                ):
                    if trace_field in row and saved.get(saved_field) is not None:
                        require(
                            row[trace_field] == saved[saved_field],
                            "trace",
                            f"Trace {trace_field} contradicts saved round",
                        )
                if "cumulative_counters" in row:
                    counters = row["cumulative_counters"]
                    require(
                        isinstance(counters, dict), "trace", "Counter snapshot must be an object"
                    )
                    require(
                        all(saved["counters_snapshot"].get(k) == v for k, v in counters.items()),
                        "trace",
                        "Trace cumulative counters contradict saved round",
                    )
        return rows, "partial", []  # Current trace cells do not establish a complete denominator.
    except (ValueError, KeyError, TypeError) as exc:
        return [], "needs_material_correction", [diagnostic(exc)]


def _run(run):
    output = {
        **linkage(run),
        "coverage": "unavailable",
        "diagnostics": list(run["diagnostics"]),
        "triggered": None,
        "initial_improvement_targets": None,
        "authorized_targets": None,
        "model_attempts": None,
        "accepted_rounds": None,
        "accepted_run": None,
        "rounds": [],
        "internal_progress": None,
        "related_targets": None,
        "evaluated_components": None,
        "accepted_components": None,
        "pending_components": None,
        "unevaluated_components": None,
    }
    if run["version"] != "v3":
        output["coverage"] = "not_applicable"
    elif run["result"] is not None and isinstance(run["result"].get("v3"), dict):
        try:
            outcome = run["result"]["v3"]
            targets = _targets(outcome["original_report"])
            scope = outcome["scope"]
            authorized = scope["target_ids"] if scope is not None else []
            require(
                len(authorized) == len(set(authorized)) and set(authorized) <= set(targets),
                "scope",
                "Scope must preserve original improvement target IDs",
            )
            repair = outcome["repair"]
            rounds = (
                _rounds(repair, authorized, _derived_targets(outcome)) if repair is not None else []
            )
            output.update(
                coverage="available",
                triggered=bool(authorized),
                initial_improvement_targets=targets,
                authorized_targets=authorized,
                model_attempts=sum(r["model_attempted"] for r in rounds),
                accepted_rounds=sum(r["accepted"] for r in rounds),
                rounds=rounds,
                accepted_run=repair["status"].startswith("ACCEPTED_") if repair else False,
                internal_progress=repair["target_progress"] if repair else [],
                related_targets=repair.get("related_targets", []) if repair else [],
            )
            if repair and repair.get("search_version") == 1:
                output.update(
                    exploration_transitions=sum(r["exploration_transition"] for r in rounds),
                    best_promotions=sum(r["best_promoted"] for r in rounds),
                    selected_lineage_rounds=sum(r["selected_lineage"] for r in rounds),
                    deterministic_attempts=repair["counters"].get("deterministic_attempts", 0),
                )
            for field in (
                "evaluated_components",
                "accepted_components",
                "pending_components",
                "unevaluated_components",
            ):
                output[field] = sum(r[field] for r in rounds)
            output["cumulative_counters_snapshot"] = repair["counters"] if repair else {}
            output["cumulative_usage_observation"] = repair["usage"] if repair else {}
        except (ValueError, KeyError, TypeError) as exc:
            output["coverage"] = "needs_material_correction"
            output["diagnostics"].append(diagnostic(exc))
    output["trace_observations"], output["trace_coverage"], output["trace_diagnostics"] = _trace(
        run, output["rounds"]
    )
    usage = run["channels"]["usage"]
    output["usage"] = {
        "status": usage["status"],
        "diagnostics": usage["diagnostics"],
        "report": None,
    }
    if usage["status"] == "available":
        try:
            rows = unique_rows(
                [r["content"] for r in usage["records"]], lambda r: r["run_id"], "usage"
            )
            output["usage"]["report"] = summarize(rows[0]["value"])
        except (ValueError, KeyError, TypeError) as exc:
            output["usage"].update(
                status="needs_material_correction", diagnostics=[diagnostic(exc)]
            )
    # Independently supplied outcomes are attachments, never internal-success evidence.
    output["independent_outcomes"] = run["channels"]["independent"]
    if output["diagnostics"] and output["coverage"] == "unavailable":
        output["coverage"] = "needs_material_correction"
    return output


def _fraction(runs, numerator, denominator, unit):
    applicable = [r for r in runs if r["version"] == "v3"]
    covered = [r for r in applicable if r["coverage"] == "available"]
    missing = len(applicable) - len(covered)
    num = sum(numerator(r) for r in covered)
    den = sum(denominator(r) for r in covered)
    complete = missing == 0 and bool(applicable)
    return {
        "numerator": num if complete else None,
        "denominator": den if complete else None,
        "observed_numerator": num,
        "observed_denominator": den,
        "unit": unit,
        "covered_runs": len(covered),
        "missing_runs": missing,
        "fraction": num / den if complete and den else None,
    }


def report_mechanism(preparation):
    prepared = validated_preparation(preparation)
    runs = [_run(run) for run in prepared["runs"]]
    output = {
        "schema_version": "rtpeval_mechanism_report_1",
        "preparation_sha256": canonical_digest(prepared),
        "batch_id": prepared["batch_id"],
        "optional_diagnostics": prepared.get("optional_diagnostics", []),
        "revision": prepared["revision"],
        "runs": runs,
        "interpretation": "Internal acceptance/progress is not independently verified resolution.",
        "fractions": {
            "run_acceptance": _fraction(
                runs,
                lambda r: r["triggered"] and r["accepted_run"],
                lambda r: r["triggered"],
                "triggered_run",
            ),
            "round_acceptance": _fraction(
                runs,
                lambda r: sum(x["accepted"] and x["model_attempted"] for x in r["rounds"]),
                lambda r: r["model_attempts"],
                "model_attempted_round",
            ),
            "component_acceptance": _fraction(
                runs,
                lambda r: r["accepted_components"],
                lambda r: r["evaluated_components"],
                "evaluated_component",
            ),
        },
    }
    output["status"] = (
        "needs_material_correction"
        if any(
            r["coverage"] == "needs_material_correction"
            or r["trace_coverage"] == "needs_material_correction"
            or r["usage"]["status"] == "needs_material_correction"
            or r["independent_outcomes"]["status"] == "needs_material_correction"
            for r in runs
        )
        else "complete"
    )
    output["content_hash"] = canonical_digest(output)
    return output
