"""Declared controlled populations with native independent outcome replay."""

from collections import Counter

from backend.cli.collection import _require
from backend.evaluation.records import canonical_digest

from .native import snapshot_directory

OPTIONS = (
    "requirement_spec",
    "identity_report",
    "schedule_context",
    "occupancy_reviews",
    "route_reviews",
    "coordinate_evidence",
    "expected_plan",
    "correspondence_reviews",
    "factual_reviews",
)
FIELDS = {
    "case_ref",
    "execution_ref",
    "expectations_ref",
    "report_ref",
    "snapshot_ref",
    *(name + "_ref" for name in OPTIONS),
}


def identifiers(value, name):
    _require(
        isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value),
        name + " must be an explicit identifier array",
    )
    _require(len(value) == len(set(value)), "Duplicate " + name)
    return value


def read_controlled(context, entry):
    from backend.evaluation.controlled_report import build_controlled_report

    descriptor = entry["descriptor"]
    _require(
        isinstance(descriptor, dict) and set(descriptor) <= FIELDS,
        "Unknown controlled source descriptor",
    )
    case = context.read_ref(descriptor["case_ref"], "rtpeval_controlled_case_1")
    execution = context.read_ref(descriptor["execution_ref"], "rtpeval_controlled_replay_1")
    expectations = context.read_ref(
        descriptor["expectations_ref"], "rtpeval_controlled_expectations_1"
    )
    _require(
        (case.get("case_id"), case.get("revision"), case.get("role"))
        == (entry["case_id"], entry["revision"], entry["role"]),
        "Foreign/stale controlled case binding",
    )
    _require(
        entry["expectations_sha256"] == descriptor["expectations_ref"]["sha256"],
        "Controlled declaration expectations hash mismatch",
    )
    for name, declared in (("targets", "expected_goal_ids"), ("guards", "expected_guard_ids")):
        _require(
            [row["goal_id"] for row in expectations[name]] == entry[declared],
            "Undeclared or missing controlled goal/guard",
        )
    saved = context.read_ref(descriptor["report_ref"], "rtpeval_controlled_report_1")
    _require(saved.get("status") == "complete", "Complete controlled report required")
    _require(
        saved.get("content_hash")
        == canonical_digest(
            {k: v for k, v in saved.items() if k not in {"content_hash", "generated_at"}}
        ),
        "Controlled report content hash mismatch",
    )
    options = {
        name: context.read_ref(descriptor[name + "_ref"]) if descriptor.get(name + "_ref") else None
        for name in OPTIONS
    }
    options["snapshot_directory"] = snapshot_directory(context, descriptor["snapshot_ref"])
    rebuilt = build_controlled_report(
        case, execution, expectations, **options, generated_at=saved["generated_at"]
    )
    _require(
        rebuilt["status"] == "complete",
        "Controlled source replay requires material correction: " + str(rebuilt["diagnostics"]),
    )
    _require(saved == rebuilt, "Saved controlled report differs from source replay")
    return saved


def preservation(native):
    """Use reviewed independent continuity and every declared guard after resolution."""
    guards = native["guards"]
    continuity = native["reviewed_checks"]["continuity"]
    rows = [row for checks in continuity.values() for row in checks]
    problems = [
        row
        for row in rows
        if row["transition"] in {"regression", "introduced_conflict"}
        or (row.get("before") is None and (row.get("after") or {}).get("state") == "FAIL")
    ]
    if problems or any(guard["after"]["state"] == "FAIL" for guard in guards):
        return "violated"
    incomplete = any(guard["after"]["state"] != "PASS" for guard in guards)
    incomplete |= any(
        row["transition"]
        in {
            "lost_verification",
            "unresolved_correspondence",
            "unresolved_attribution",
            "unverified_change",
            "not_comparable",
        }
        for row in rows
    )
    unresolved = native["pair"]["correspondence"]["unresolved"]
    incomplete |= bool(unresolved["before"] or unresolved["after"])
    incomplete |= any(
        check["state"] == "UNKNOWN"
        for dimension in native["reviewed_checks"]["stages"]["final_primary"][
            "primary_metrics"
        ].values()
        for check in dimension["checks"]
    )
    incomplete |= any(
        dimension.get("unresolved_role_count")
        or dimension.get("unresolved_population_count")
        or dimension.get("denominator_unresolved")
        for dimension in native["pair"]["stages"]["final_primary"]["primary_metrics"].values()
    )
    return "unknown" if incomplete else "preserved"


def rate(numerator, denominator, unit):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "unit": unit,
        "fraction": numerator / denominator if denominator else None,
    }


def controlled_view(context, study):
    if study is None:
        return {"applicability": "not_declared"}
    _require(
        isinstance(study, dict) and set(study) == {"study_id", "revision", "cases"},
        "Explicit controlled study identity/inventory required",
    )
    _require(
        all(isinstance(study[k], str) and study[k].strip() for k in ("study_id", "revision")),
        "Controlled study identity/revision required",
    )
    _require(isinstance(study["cases"], list), "Controlled cases must be an array")
    cases, targets, controls, seen = [], [], [], set()
    for entry in study["cases"]:
        _require(
            isinstance(entry, dict)
            and set(entry)
            == {
                "case_id",
                "revision",
                "role",
                "expected_goal_ids",
                "expected_guard_ids",
                "expectations_sha256",
                "descriptor",
            },
            "Explicit controlled case/target/guard inventory required",
        )
        _require(
            all(isinstance(entry[k], str) and entry[k].strip() for k in ("case_id", "revision")),
            "Controlled case identity required",
        )
        _require(entry["role"] in {"target", "control"}, "Unknown controlled case role")
        key = (entry["case_id"], entry["revision"])
        _require(key not in seen, "Duplicate declared controlled case")
        seen.add(key)
        goals = identifiers(entry["expected_goal_ids"], "controlled targets")
        guards = identifiers(entry["expected_guard_ids"], "controlled guards")
        _require(not set(goals) & set(guards), "Controlled target/guard identifiers overlap")
        native = read_controlled(context, entry) if entry["descriptor"] is not None else None
        if native is None:
            _require(
                entry["expectations_sha256"] is None,
                "Missing controlled material must not claim a validated expectations hash",
            )
        row = {
            **{k: entry[k] for k in ("case_id", "revision", "role")},
            "expected_goal_ids": goals,
            "expected_guard_ids": guards,
            "availability": "available" if native else "unavailable",
            "native_report_sha256": native["content_hash"] if native else None,
            "native": native,
        }
        cases.append(row)
        by_goal = {target["goal_id"]: target for target in native["targets"]} if native else {}
        for goal in goals:
            outcome = by_goal.get(goal)
            targets.append(
                {
                    "case_id": entry["case_id"],
                    "case_revision": entry["revision"],
                    "role": entry["role"],
                    "goal_id": goal,
                    "native": outcome,
                    "independent_outcome": outcome["independent_outcome"]
                    if outcome
                    else "unavailable",
                    "preservation": preservation(native)
                    if outcome and outcome["independent_outcome"] == "resolved"
                    else "not_resolved"
                    if outcome
                    else "unknown",
                }
            )
        if entry["role"] == "control":
            controls.append(row)
    available = [row for row in targets if row["native"] is not None]
    target_cases = [row for row in cases if row["role"] == "target"]
    joint = 0
    for case in target_cases:
        members = [
            row
            for row in targets
            if row["case_id"] == case["case_id"] and row["case_revision"] == case["revision"]
        ]
        joint += bool(
            members
            and all(
                row["independent_outcome"] == "resolved" and row["preservation"] == "preserved"
                for row in members
            )
        )
    detected = [row for row in available if row["native"]["detection"] == "detected"]
    authorized = [row for row in detected if row["native"]["authorization"] == "authorized"]
    attempted = [row for row in authorized if row["native"]["model_attempted"]]
    channels = {}
    for name, field, positive, population, unit in (
        ("detection", "detection", "detected", available, "available_expected_targets"),
        ("authorization", "authorization", "authorized", detected, "detected_targets"),
        ("model_attempt", "model_attempted", True, authorized, "authorized_targets"),
        ("adoption", "adoption", "adopted_component", attempted, "model_attempted_targets"),
    ):
        channels[name] = {
            **rate(
                sum(row["native"][field] == positive for row in population), len(population), unit
            ),
            "expected_targets": len(targets),
            "available_expected_targets": len(available),
        }
    # Opportunities are native candidate/identity-free observations, not independent successes.
    opportunities = [
        opportunity for row in available for opportunity in row["native"]["opportunities"]
    ]
    return {
        "applicability": "applicable" if cases else "not_applicable",
        "study_id": study["study_id"],
        "revision": study["revision"],
        "cases": cases,
        "targets": targets,
        "controls": controls,
        "resolution": rate(
            sum(row["independent_outcome"] == "resolved" for row in targets),
            len(targets),
            "expected_targets",
        ),
        "verdict_coverage": {
            "available": len(available),
            "expected": len(targets),
            "unit": "expected_targets",
        },
        "outcomes": dict(sorted(Counter(row["independent_outcome"] for row in targets).items())),
        "preservation": dict(sorted(Counter(row["preservation"] for row in targets).items())),
        "preserved_resolution": rate(
            sum(
                row["independent_outcome"] == "resolved" and row["preservation"] == "preserved"
                for row in targets
            ),
            len(targets),
            "expected_targets",
        ),
        "case_joint_success": rate(joint, len(target_cases), "expected_target_cases"),
        "observational_channels": channels,
        "opportunities": {
            "unit": "native_opportunity_observations",
            "rows": opportunities,
            "observed": len(opportunities),
            "targets_with_observation": sum(
                bool(row["native"]["opportunities"]) for row in available
            ),
            "expected_targets": len(targets),
        },
        "control_outcomes": dict(
            sorted(
                Counter(
                    row["native"]["control"]["outcome"] if row["native"] else "unavailable"
                    for row in controls
                ).items()
            )
        ),
    }
