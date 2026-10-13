"""Controlled outcomes composed from independent same-run V3 checks."""

from copy import deepcopy
from datetime import datetime

from ._controlled_facts import supplement_pair
from ._controlled_goals import Expectations, detection, target_outcome, verdict
from .controlled_models import ControlledCase
from .controlled_preparation import prepare_controlled_case
from .preparation import _review_provenance
from .records import MaterialError, canonical_digest, require, text
from .v3_pair_report import build_v3_pair_report


def build_controlled_report(
    case,
    execution,
    expectations,
    requirement_spec,
    identity_report,
    snapshot_directory,
    schedule_context=None,
    occupancy_reviews=None,
    route_reviews=None,
    coordinate_evidence=None,
    *,
    expected_plan=None,
    correspondence_reviews=None,
    factual_reviews=None,
    generated_at,
):
    """Keep internal execution decisions and independent compliance in separate channels."""
    inventory = expectations.get("targets", []) if isinstance(expectations, dict) else []
    inventory = inventory if isinstance(inventory, list) else []
    base = {
        "schema_version": "rtpeval_controlled_report_1",
        "generated_at": generated_at,
        "case_id": case.get("case_id"),
        "role": case.get("role"),
        "status": "needs_material_correction",
        "targets": [
            {
                "goal_id": row.get("goal_id"),
                "independent_outcome": "unavailable",
                "detection": "unavailable",
                "authorization": "unavailable",
            }
            for row in inventory
            if isinstance(row, dict)
        ],
        "control": None,
        "target_counts": {"expected": len(inventory), "detected": None, "authorized": None},
        "diagnostics": [],
    }
    try:
        saved = ControlledCase.model_validate(deepcopy(case))
        stamp = datetime.fromisoformat(generated_at)
        require(stamp.utcoffset() is not None, "generated_at", "Offset-aware timestamp required")
        prepared = prepare_controlled_case(case, execution, requirement_spec).to_dict()
        expectations = deepcopy(expectations)
        require(
            expectations.get("schema_version") == "rtpeval_controlled_expectations_1"
            and expectations.get("case_id") == saved.case_id
            and expectations.get("case_hash") == prepared["case_hash"],
            "expectations",
            "Foreign/stale controlled expectations",
        )
        _review_provenance(expectations, "expectations")
        require(
            text(expectations.get("revision"))
            and text(expectations.get("rationale"))
            and isinstance(expectations.get("supporting_refs"), list)
            and bool(expectations["supporting_refs"]),
            "expectations",
            "Reviewed goal basis required",
        )
        require(
            isinstance(expectations.get("targets"), list)
            and isinstance(expectations.get("guards"), list),
            "expectations",
            "Expected target and guard inventories required",
        )
        goals = Expectations.model_validate(expectations)
        original_activities = {a.activity_id for d in saved.primary.days for a in d.activities}
        for goal in (*goals.targets, *goals.guards):
            require(
                set(goal.condition.activity_ids) <= original_activities,
                "expectations.subjects",
                "Unknown draft occurrence selector",
            )
            if goal.basis == "explicit_requirement":
                source = goal.source or {}
                original = saved.original_input.get(source.get("field"))
                quote = source.get("quote")
                require(
                    isinstance(original, str)
                    and isinstance(quote, str)
                    and quote.strip()
                    and quote in original,
                    "expectations.source",
                    "Explicit controlled requirement must cite the original input",
                )
        pair_report = build_v3_pair_report(
            prepared,
            identity_report,
            snapshot_directory,
            schedule_context,
            occupancy_reviews,
            route_reviews,
            coordinate_evidence,
            expected_plan=expected_plan,
            result_sources=prepared["result_sources"],
            correspondence_reviews=correspondence_reviews,
            generated_at=generated_at,
        ).to_dict()
        require(pair_report["status"] == "complete", "pair", str(pair_report["diagnostics"]))
        pair = pair_report["groups"][0]
        require(pair["pair_status"] == "available", "pair", "Both controlled stages required")
        raw_pair = deepcopy(pair)
        pair, factual_provenance = supplement_pair(pair, factual_reviews, execution)
        stages = pair["stages"]
        for label, stage in stages.items():
            stage["controlled_projection"] = prepared["inventory"][0]["runs"]["v3"]["optional"][
                label
            ]
        problems, unknown, baseline = [], [], []
        for name, dimension in stages["draft"]["primary_metrics"].items():
            baseline.extend(
                {"dimension": name, "check": c} for c in dimension["checks"] if c["state"] == "FAIL"
            )
        for name, dimension in stages["final_primary"]["primary_metrics"].items():
            if (
                dimension.get("unresolved_role_count")
                or dimension.get("unresolved_population_count")
                or dimension.get("denominator_unresolved")
            ):
                unknown.append({"dimension": name, "reason": "population_unresolved"})
            for check in dimension["checks"]:
                if check["state"] == "UNKNOWN":
                    unknown.append({"dimension": name, "check": check})
        for name, rows in pair["continuity"].items():
            for row in rows:
                if row["transition"] in {"regression", "introduced_conflict"} or (
                    row.get("before") is None and (row.get("after") or {}).get("state") == "FAIL"
                ):
                    problems.append({"dimension": name, "transition": row})
                elif row["transition"] in {
                    "lost_verification",
                    "unresolved_correspondence",
                    "unresolved_attribution",
                }:
                    unknown.append({"dimension": name, "transition": row})
        if (
            pair["correspondence"]["unresolved"]["before"]
            or pair["correspondence"]["unresolved"]["after"]
        ):
            unknown.append(
                {"dimension": "correspondence", "subjects": pair["correspondence"]["unresolved"]}
            )
        changed = any(r["relation"] != "unchanged" for r in pair["correspondence"]["relations"])
        base.update(
            status="complete",
            pair=raw_pair,
            source_hashes={
                "preparation": canonical_digest(prepared),
                "expectations": canonical_digest(expectations),
                "pair": pair_report["content_hash"],
                "factual_reviews": canonical_digest(factual_reviews) if factual_reviews else None,
            },
            execution={
                "scope": execution["outcome"]["scope"],
                "repair_status": execution["outcome"]["repair"]["status"]
                if execution["outcome"]["repair"]
                else "not_executed",
                "calls": execution["calls"],
                "usage_scope": "frozen_simulation",
            },
        )
        base["reviewed_checks"] = {
            "provenance": factual_provenance,
            "stages": {
                label: {
                    "primary_metrics": {
                        name: {"checks": d["checks"]}
                        for name, d in stage["primary_metrics"].items()
                    }
                }
                for label, stage in stages.items()
            },
            "continuity": pair["continuity"],
        }
        base["targets"] = [
            {**target_outcome(g, pair), **detection(g, execution["outcome"])} for g in goals.targets
        ]
        base["target_counts"] = {
            "expected": len(goals.targets),
            "detected": sum(r["detection"] == "detected" for r in base["targets"]),
            "authorized": sum(r["authorization"] == "authorized" for r in base["targets"]),
        }
        if (execution["outcome"].get("repair") or {}).get("search_version") == 1:
            base["target_counts"].update(
                operation_attempted=sum(r["operation_attempted"] for r in base["targets"]),
                deterministic_attempted=sum(r["deterministic_attempted"] for r in base["targets"]),
            )
        base["target_counts"].update(
            model_attempted=sum(r["model_attempted"] for r in base["targets"]),
            adopted=sum(r["adoption"] == "adopted_component" for r in base["targets"]),
            outcomes={
                name: sum(r["independent_outcome"] == name for r in base["targets"])
                for name in (
                    "resolved",
                    "partial_improvement",
                    "residual",
                    "regressed",
                    "unresolved",
                    "structural_change",
                    "valid_no_change",
                )
            },
        )
        base["guards"] = [
            {
                "goal_id": g.goal_id,
                "basis": g.basis,
                "before": verdict(stages["draft"], g.condition),
                "after": verdict(stages["final_primary"], g.condition),
            }
            for g in goals.guards
        ]
        for guard in base["guards"]:
            if guard["after"]["state"] == "FAIL":
                problems.append({"dimension": "guard", "guard": guard})
            elif guard["after"]["state"] == "UNKNOWN":
                unknown.append({"dimension": "guard", "guard": guard})
        if saved.role == "control":
            require(
                not baseline and all(g["before"]["state"] != "FAIL" for g in base["guards"]),
                "control",
                "Control baseline has an independently confirmed violation",
            )
            baseline_unknown = any(
                c["state"] == "UNKNOWN"
                for d in stages["draft"]["primary_metrics"].values()
                for c in d["checks"]
            ) or any(g["before"]["state"] == "UNKNOWN" for g in base["guards"])
            baseline_unknown |= any(
                d.get("unresolved_role_count")
                or d.get("unresolved_population_count")
                or d.get("denominator_unresolved")
                for d in stages["draft"]["primary_metrics"].values()
            )
            if baseline_unknown:
                unknown.append({"dimension": "baseline", "reason": "initial_compliance_unresolved"})
            base["control"] = {
                "outcome": "regressed"
                if problems
                else "unresolved"
                if unknown
                else "lawful_change"
                if changed
                else "valid_no_change",
                "changed": changed,
                "confirmed_problems": problems,
                "unresolved": unknown,
            }
    except (MaterialError, ValueError, TypeError, KeyError, OSError) as exc:
        base["status"] = "needs_material_correction"
        base["control"] = None
        base["targets"] = [
            {
                "goal_id": row.get("goal_id"),
                "independent_outcome": "unavailable",
                "detection": "unavailable",
                "authorization": "unavailable",
            }
            for row in inventory
            if isinstance(row, dict)
        ]
        base["target_counts"] = {"expected": len(inventory), "detected": None, "authorized": None}
        base["diagnostics"] = [
            exc.diagnostic
            if isinstance(exc, MaterialError)
            else {"reason": "material_invalid", "explanation": str(exc)}
        ]
    base["content_hash"] = canonical_digest({k: v for k, v in base.items() if k != "generated_at"})
    return base
