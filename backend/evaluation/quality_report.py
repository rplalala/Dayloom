"""Replay final projections into a multimetric report and auxiliary verified scores."""

from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from pathlib import Path

from .daily_density import RULES as DENSITY_RULES
from .daily_density import (
    apply_density_penalty,
    density_rules,
    prepare_density_policies,
    score_daily_density,
)
from .intake import VERSIONS, _read
from .opening import score_opening
from .preparation import identity_ready
from .quality_aggregation import DIMENSIONS, _dimension, _fraction, _grounding, _index, _totals
from .records import MaterialError, canonical_digest, freeze, require, thaw
from .requirement_schedule import score_requirement_schedule
from .routes import score_routes
from .snapshot import load_snapshot

REPORT_VERSION = "rtpeval_quality_report_2"
RULES_PROFILE = {
    "profile_id": "rtpeval_verified_quality_2",
    "dimensions": list(DIMENSIONS),
    "verified_fraction": "PASS / (PASS + FAIL + UNKNOWN)",
    "total": "unrounded rational mean over the group common mask",
    "exclude": "all four established denominators equal zero",
    "included_no_checks": "raw N/A; contribution zero",
    "unresolved_denominator": "include; dimension and affected total unavailable",
    "empty_mask": "total unavailable",
    "scope": "final projections only; no optional track contributions",
    "daily_density": DENSITY_RULES,
}


@dataclass(frozen=True)
class QualityReportResult:
    """Immutable completed replay or whole-batch material diagnostics."""

    status: str
    data: object

    def to_dict(self):
        return {**thaw(self.data), "status": self.status}


def quality_content_hash(report):
    """Hash all report content except creation time and the hash itself."""
    return canonical_digest(
        {key: value for key, value in report.items() if key not in ("generated_at", "content_hash")}
    )


def _value(value):
    return value.to_dict() if hasattr(value, "to_dict") else value


def build_quality_report(
    intake,
    identity_report,
    snapshot_directory,
    schedule_context=None,
    occupancy_reviews=None,
    route_reviews=None,
    coordinate_evidence=None,
    *,
    expected_plan=None,
    identity_snapshot_directory=None,
    density_reviews=None,
    opening_judgment=None,
    quality_profile=None,
    generated_at,
):
    """Compose existing offline scorers without accepting caller-authored metric summaries."""
    prepared, identity = _value(intake), _value(identity_report)
    base = {
        "schema_version": REPORT_VERSION,
        "generated_at": generated_at,
        "rules_profile_id": RULES_PROFILE["profile_id"],
        "rules_profile": RULES_PROFILE,
        "rules_profile_hash": canonical_digest(RULES_PROFILE),
        "groups": [],
        "diagnostics": [],
    }
    status = "needs_material_correction"
    if opening_judgment is not None:
        profile = {
            **RULES_PROFILE,
            "profile_id": "rtpeval_access_quality_4",
            "public_landmark_intent": "ordinary_sightseeing_unless_restricted_activity",
            "opening_pass_basis": "api_hours_or_llm_access_reasonableness",
            "factual_hours_coverage": "separate_from_model_assessment",
        }
        base.update(
            rules_profile=profile,
            rules_profile_id=profile["profile_id"],
            rules_profile_hash=canonical_digest(profile),
        )
    try:
        profile = {**base["rules_profile"], "daily_density": density_rules(_value(density_reviews))}
        base.update(rules_profile=profile, rules_profile_hash=canonical_digest(profile))
        require(isinstance(generated_at, str), "generated_at", "Offset-aware timestamp required")
        stamp = datetime.fromisoformat(generated_at)
        require(stamp.utcoffset() is not None, "generated_at", "Offset-aware timestamp required")
        require(
            isinstance(prepared, dict) and prepared.get("status") == "accepted",
            "intake",
            "Accepted intake required",
        )
        base.update(batch_id=prepared["batch_id"], batch_revision=prepared["revision"])
        density_policies = prepare_density_policies(prepared, _value(density_reviews))
        from .declared_population import (
            PROFILE_ID,
            candidate_metrics,
            population_readiness,
            select_profile,
        )

        selected_profile = select_profile(prepared, quality_profile)
        population = None
        if selected_profile == PROFILE_ID:
            profile = {
                **base["rules_profile"],
                "profile_id": PROFILE_ID,
                "population": "frozen source-linked candidates minus verified N/A",
                "uncertain_applicability": "retained UNKNOWN candidate",
                "population_readiness": "required before acquisition",
                "projection_policy": "declared_or_source_labelled_legacy_1",
            }
            base.update(
                rules_profile=profile,
                rules_profile_id=PROFILE_ID,
                rules_profile_hash=canonical_digest(profile),
            )
            population = population_readiness(
                prepared,
                _value(schedule_context),
                _value(occupancy_reviews),
                _value(density_reviews),
            )
            base["population_readiness"] = population
            if population["status"] != "ready":
                status = "needs_population_resolution"
                base["diagnostics"] = population["diagnostics"]
                base["status"] = status
                base["content_hash"] = quality_content_hash(base)
                return QualityReportResult(status, freeze(base))
        if not identity_ready(prepared, identity):
            status = "identity_replay_required"
            raise MaterialError(
                status, "identity", "Identity policy/source/reference linkage is invalid"
            )
        snapshot = load_snapshot(snapshot_directory, expected_plan=_value(expected_plan))
        require(
            snapshot["plan"]["paired"] is False,
            "snapshot.plan.paired",
            "Final-only snapshot required; paired evidence aggregation is unsupported",
            reason="unsupported_snapshot_scope",
        )
        components = {
            "requirement_schedule": score_requirement_schedule(
                intake,
                identity_report,
                schedule_context,
                occupancy_reviews,
                paired=False,
            ).to_dict(),
            "opening": score_opening(
                intake,
                identity_report,
                snapshot_directory,
                schedule_context,
                paired=False,
                expected_plan=expected_plan,
                opening_judgment=opening_judgment,
            ).to_dict(),
            "routes": score_routes(
                intake,
                identity_report,
                snapshot_directory,
                schedule_context,
                occupancy_reviews,
                route_reviews,
                coordinate_evidence,
                paired=False,
                expected_plan=expected_plan,
                identity_snapshot_directory=identity_snapshot_directory,
            ).to_dict(),
        }
        failures = [
            component for component in components.values() if component["status"] != "complete"
        ]
        if failures:
            status = failures[0]["status"]
            base["diagnostics"] = [d for component in failures for d in component["diagnostics"]]
        else:
            _, manifest_hash = _read(Path(snapshot_directory) / "manifest.json")
            for name in ("opening", "routes"):
                require(
                    components[name]["source_hashes"]["snapshot_manifest"] == manifest_hash
                    and components[name]["source_hashes"]["snapshot_plan"] == snapshot["plan_hash"],
                    name,
                    "Incompatible snapshot linkage",
                )
            expected = {}
            for group in prepared["inventory"]:
                require(
                    set(group["runs"]) == set(VERSIONS), "runs", "Exactly four versions required"
                )
                for version, run in group["runs"].items():
                    expected[
                        (group["group_id"], version, run["final"]["context"]["run_id"], "final")
                    ] = {
                        "input": group["input_sha256"],
                        "requirement_spec": group["requirement_spec_sha256"],
                        "result": run["final"]["context"]["artifact_sha256"],
                    }
            indexed = {name: _index(component, expected) for name, component in components.items()}
            identities = {record["reference_id"]: record for record in identity["records"]}
            groups = []
            for group in prepared["inventory"]:
                versions = {}
                for version in VERSIONS:
                    run = group["runs"][version]
                    key = (group["group_id"], version, run["final"]["context"]["run_id"], "final")
                    schedule = indexed["requirement_schedule"][key]
                    metrics = {
                        "requirements": schedule["requirements"],
                        "grounding": _grounding(run["final"], identities),
                        "non_overlap": schedule["non_overlap"],
                        "opening": indexed["opening"][key]["opening"],
                        "routes": indexed["routes"][key]["routes"],
                    }
                    if population is not None:
                        row = next(
                            r
                            for r in population["rows"]
                            if r["group_id"] == group["group_id"] and r["version"] == version
                        )
                        metrics = candidate_metrics(metrics, row["inventory"])
                    dimensions = {
                        name: _dimension(
                            raw,
                            raw["denominator"]
                            if name in ("requirements", "non_overlap")
                            else raw["applicable_denominator"],
                        )
                        for name, raw in metrics.items()
                    }
                    versions[version] = {
                        "run_id": key[2],
                        "projection": "final",
                        "dimensions": dimensions,
                        "primary_metrics": metrics,
                        "schedule_measures": schedule["schedule_measures"],
                        "descriptive": schedule["descriptive"],
                        "daily_density": score_daily_density(
                            group,
                            schedule["descriptive"]["density"],
                            density_policies[group["group_id"]],
                        ),
                        "occupancy": schedule["occupancy"],
                        "component_source_hashes": {
                            name: indexed[name][key]["source_hashes"] for name in components
                        },
                        **(
                            {
                                "candidate_inventory": row["inventory"],
                                "activity_claims": row["activity_claims"],
                            }
                            if population is not None
                            else {}
                        ),
                    }
                mask = _totals(versions)
                for version in versions.values():
                    apply_density_penalty(version)
                groups.append(
                    {
                        "group_id": group["group_id"],
                        "included_dimensions": mask,
                        "total_included_dimensions": len(mask),
                        "dimension_weights": {
                            name: _fraction(Fraction(1, len(mask))) for name in mask
                        },
                        "diagnostics": [
                            {
                                "reason": "no_scorable_dimensions",
                                "explanation": "Reconcile applicability before interpreting totals",
                            }
                        ]
                        if not mask
                        else [],
                        "all_totals_available": all(
                            v["overall_total"]["score_0_100"] is not None for v in versions.values()
                        ),
                        "versions": versions,
                    }
                )
            base.update(
                groups=groups,
                components={
                    name: {k: v for k, v in component.items() if k != "results"}
                    for name, component in components.items()
                },
                source_hashes={
                    "artifacts": prepared["source_hashes"],
                    "intake": canonical_digest(prepared),
                    "identity_report": canonical_digest(identity),
                    "identity_evidence": identity["evidence_hash"],
                    "identity_review": identity["review_hash"],
                    "identity_audit": identity["audit_plan_hash"],
                    "identity_references": identity["reference_set_digest"],
                    "snapshot_manifest": manifest_hash,
                    "snapshot_plan": snapshot["plan_hash"],
                    "preparation": {
                        name: canonical_digest(_value(value)) if value is not None else None
                        for name, value in {
                            "schedule_context": schedule_context,
                            "occupancy_reviews": occupancy_reviews,
                            "route_reviews": route_reviews,
                            "coordinate_evidence": coordinate_evidence,
                            "expected_plan": expected_plan,
                            "density_reviews": density_reviews,
                        }.items()
                    },
                },
                stage_availability={
                    "resource": {"report_status": "not_integrated"},
                    "human": {"report_status": "not_integrated"},
                    "mechanism": {"report_status": "not_integrated"},
                    "source_runs": [
                        {
                            "group_id": group["group_id"],
                            "version": version,
                            "usage_available": run["usage_available"],
                            "usage_hash": run["usage_hash"],
                            "paired_available": run["paired_available"],
                            "optional_projections": {
                                name: value is not None for name, value in run["optional"].items()
                            },
                        }
                        for group in prepared["inventory"]
                        for version, run in group["runs"].items()
                    ],
                },
            )
            status = "complete"
    except (MaterialError, ValueError, KeyError, TypeError, OSError) as exc:
        base["groups"] = []
        base["diagnostics"] = [
            exc.diagnostic
            if isinstance(exc, MaterialError)
            else {"reason": "material_invalid", "explanation": str(exc)}
        ]
    base["status"] = status
    base["content_hash"] = quality_content_hash(base)
    return QualityReportResult(status, freeze(base))
