"""Offline independent route preparation and frozen-evidence evaluation."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ._route_evidence import (
    components,
    conjunction,
    context_reasons,
    observation,
    seconds_exact,
)
from ._route_inputs import coordinates, policy_component, requirement_mode_review, route_context
from ._route_inputs import route_reviews as read_route_reviews
from ._route_preparation import prepare_leg
from ._route_rules import DEFAULT_OPTIONS, DRIVE_RESERVE_SECONDS, RULES
from ._schedule_preparation import _occupancy_reviews, _validate_spec, _validate_time_capacity
from .intake import _read
from .occupancy import prepare_occupancy
from .preparation import identity_ready, schedule_timezones
from .records import MaterialError, canonical_digest, freeze, require, thaw
from .snapshot import build_evidence_plan, load_snapshot
from .snapshot_coordinates import prepare_snapshot_coordinates

PREPARATION_VERSION = "rtpeval_route_preparation_1"
REPORT_VERSION = "rtpeval_route_report_1"


@dataclass(frozen=True)
class RoutePreparation:
    status: str
    data: Mapping

    def to_dict(self):
        return {"status": self.status, **thaw(self.data)}


@dataclass(frozen=True)
class RouteResult:
    status: str
    data: Mapping

    def to_dict(self):
        return {"status": self.status, **thaw(self.data)}


def _value(value):
    return value.to_dict() if hasattr(value, "to_dict") else thaw(value)


def prepare_routes(
    intake,
    identity_report,
    schedule_context=None,
    occupancy_reviews=None,
    route_reviews=None,
    coordinate_evidence=None,
    *,
    paired=False,
    identity_snapshot_directory=None,
):
    """Prepare source-selected routes without reading route observations."""
    prepared, identity = _value(intake), _value(identity_report)
    base = {
        "schema_version": PREPARATION_VERSION,
        "results": [],
        "route_contexts": [],
        "diagnostics": [],
        "paired": paired,
    }
    try:
        require(
            isinstance(prepared, dict) and prepared.get("status") == "accepted",
            "intake",
            "Accepted intake required",
        )
        require(type(paired) is bool, "paired", "Paired scope requires a boolean")
        zones = schedule_timezones(prepared, _value(schedule_context))
        reviews = _occupancy_reviews(prepared, _value(occupancy_reviews))
        for group in prepared["inventory"]:
            _validate_spec(group)
            _validate_time_capacity(group, zones.get(group["group_id"]))
        if not identity_ready(prepared, identity):
            base["diagnostics"] = [{"reason": "identity_replay_required"}]
            return RoutePreparation("identity_replay_required", freeze(base))
        identities = {r["reference_id"]: r for r in identity["records"]}
        policies = read_route_reviews(prepared, _value(route_reviews))
        require(
            identity_snapshot_directory is None or coordinate_evidence is None,
            "coordinates",
            "Choose one coordinate source",
        )
        if identity_snapshot_directory is not None:
            coordinate_preparation = prepare_snapshot_coordinates(
                prepared, identity, identity_snapshot_directory
            ).to_dict()
            require(
                coordinate_preparation["status"] == "complete",
                "coordinates",
                str(coordinate_preparation["diagnostics"]),
            )
            base["coordinate_preparation"] = coordinate_preparation
            points = {
                r["place_id"]: {
                    k: r[k] for k in ("place_id", "latitude", "longitude", "evidence_sha256")
                }
                for r in coordinate_preparation["records"]
            }
            options = DEFAULT_OPTIONS
        else:
            points, options = coordinates(prepared, identity, _value(coordinate_evidence))
        base.update(batch_id=prepared["batch_id"], batch_revision=prepared["revision"])
        base["source_hashes"] = {
            "intake": canonical_digest(prepared),
            "identity_report": canonical_digest(identity),
        }
        for name, value in (
            ("schedule_context", schedule_context),
            ("occupancy_reviews", occupancy_reviews),
            ("route_reviews", route_reviews),
            ("coordinate_evidence", coordinate_evidence),
        ):
            base["source_hashes"][name] = (
                canonical_digest(_value(value)) if value is not None else None
            )
        base["rules"], base["rules_hash"] = RULES, canonical_digest(RULES)
        if any(
            o["kind"] == "transport_modes"
            for g in prepared["inventory"]
            for o in g["requirement_spec"]["obligations"]
        ):
            rules = {
                **RULES,
                "version": "rtpeval_route_rules_3",
                "transport_requirement_bridge": "whole_trip_1",
            }
            base["rules"], base["rules_hash"] = rules, canonical_digest(rules)
        if identity_snapshot_directory is not None:
            base["source_hashes"]["snapshot_coordinates"] = canonical_digest(coordinate_preparation)
        for group in prepared["inventory"]:
            zone = zones.get(group["group_id"])
            for version, run in group["runs"].items():
                projections = [("final", run["final"])]
                if paired and version == "v3":
                    projections.extend((label, p) for label, p in run["optional"].items() if p)
                for label, projection in projections:
                    occupancy = prepare_occupancy(
                        projection, group["requirement_spec"]["obligations"], zone, reviews
                    )
                    legs = [
                        prepare_leg(leg, occupancy, zone, identities) for leg in projection["legs"]
                    ]
                    for leg in legs:
                        endpoint_records = [
                            identities[s["record_id"]]
                            for s in (leg["from_source"], leg["to_source"])
                        ]
                        if any(
                            "programmatic_judgment" in r or "candidate_correspondence" in r
                            for r in endpoint_records
                        ):
                            leg["identity_grounding_verdicts"] = [
                                r.get("grounding_verdict") for r in endpoint_records
                            ]
                    review = requirement_mode_review(group, policies.get(group["group_id"]))
                    for leg in legs:
                        if (
                            leg["mode"] is None
                            and review
                            and review.get("stated_mode")
                            and not any(
                                r == "transport_claims_conflicting_or_segmented"
                                for r in leg["reasons"]
                            )
                        ):
                            leg["mode"], leg["mode_basis"] = (
                                review["stated_mode"]["mode"],
                                "original_input_review",
                            )
                        leg["mode_policy"] = policy_component(
                            review, leg["mode"], leg["declared_day"]
                        )
                        if review and "scoring_review" in review:
                            leg["mode_policy_score"] = policy_component(
                                review["scoring_review"], leg["mode"], leg["declared_day"]
                            )
                        leg["mode_review"] = review
                        if leg["mode"] is None:
                            leg["reasons"].append("route_mode_unresolved")
                        if None in leg["canonical_endpoints"]:
                            leg["reasons"].append("identity_unresolved")
                        leg["expected_context"] = route_context(leg, points, options)
                        if leg["expected_context"]:
                            base["route_contexts"].append(leg["expected_context"])
                    base["results"].append(
                        {
                            "group_id": group["group_id"],
                            "version": version,
                            "projection": label,
                            "run_id": projection["context"]["run_id"],
                            "source_hashes": {
                                "input": group["input_sha256"],
                                "requirement_spec": group["requirement_spec_sha256"],
                                "result": projection["context"]["artifact_sha256"],
                            },
                            "unresolved_population_records": [
                                {
                                    "source": a["source"],
                                    "declared_day": a["declared_day"],
                                    "reason": "role_unresolved",
                                }
                                for a in projection["activities"]
                                if a["evaluation_role"] == "unresolved"
                            ]
                            + [
                                {
                                    "sources": [leg["from_source"], leg["to_source"]],
                                    "declared_day": leg["declared_day"],
                                    "reason": "adjacency_unresolved",
                                }
                                for leg in legs
                                if "adjacency_unresolved" in leg["reasons"]
                            ],
                            "ignored_transport": projection["ignored_transport"],
                            "unbound_transport": projection["unbound_transport"],
                            "legs": legs,
                        }
                    )
        base["evidence_plan"] = build_evidence_plan(
            prepared, identity, base["route_contexts"], paired=paired
        )
        return RoutePreparation("complete", freeze(base))
    except (MaterialError, ValueError, TypeError, KeyError, OSError) as exc:
        base["results"], base["route_contexts"] = [], []
        base["diagnostics"] = [
            exc.diagnostic
            if isinstance(exc, MaterialError)
            else {"reason": "preparation_invalid", "explanation": str(exc)}
        ]
        return RoutePreparation("needs_material_correction", freeze(base))


def _rate(numerator, denominator, unresolved=False):
    return {
        "numerator": numerator,
        "denominator": None if unresolved else denominator,
        "rate": numerator / denominator if denominator and not unresolved else None,
        "reason": "population_unresolved"
        if unresolved
        else "empty_denominator"
        if not denominator
        else None,
    }


def _burden(checks, unresolved=()):
    observed = sorted(
        c["duration_nanoseconds"] for c in checks if c["duration_nanoseconds"] is not None
    )
    length = len(observed)
    # The median of integer nanoseconds can contain half a nanosecond; serialize exactly.
    median_twice = observed[length // 2] + observed[(length - 1) // 2] if length else None
    return {
        "aggregation": "per_occurrence_observed_subtotal",
        "observed_leg_count": length,
        "missing_leg_count": len(checks) - length,
        "unresolved_population_count": len(unresolved),
        "duration_nanoseconds": sum(observed) if observed else None,
        "duration_seconds_exact": seconds_exact(sum(observed)) if observed else None,
        "maximum_duration_seconds_exact": seconds_exact(observed[-1]) if observed else None,
        "median_duration_seconds_exact": seconds_exact(median_twice * 5, 10) if length else None,
        "product_reserve_seconds_subtotal": sum(
            c["reserve_seconds"] for c in checks if c["duration_nanoseconds"] is not None
        )
        if observed
        else None,
        "full_scope_complete": bool(checks) and length == len(checks) and not unresolved,
    }


def _summary(checks, unresolved):
    applicable = [c for c in checks if c["state"] != "N/A"]
    counts = {s: sum(c["state"] == s for c in checks) for s in ("PASS", "FAIL", "UNKNOWN", "N/A")}
    size, decisive = len(applicable), counts["PASS"] + counts["FAIL"]
    structure = sum(c["structurally_evaluable"] for c in applicable)
    response = sum(c["response_applicable"] for c in applicable)
    complete = sum(c["complete_evidence"] for c in applicable)
    durations = sum(c["duration_nanoseconds"] is not None for c in applicable)
    return {
        "state": "FAIL"
        if counts["FAIL"]
        else "UNKNOWN"
        if counts["UNKNOWN"] or unresolved
        else "PASS"
        if applicable
        else "N/A",
        "checks": checks,
        "counts": counts,
        "applicable_count": size,
        "applicable_denominator": None if unresolved else size,
        "unresolved_population_count": len(unresolved),
        "unresolved_population_records": unresolved,
        "structurally_evaluable_count": structure,
        "applicable_response_count": response,
        "complete_evidence_count": complete,
        "verdict_decidable_count": decisive,
        "duration_available_count": durations,
        "structural_coverage": _rate(structure, size, unresolved),
        "applicable_response_coverage": _rate(response, size, unresolved),
        "complete_evidence_coverage": _rate(complete, size, unresolved),
        "verdict_decidable_coverage": _rate(decisive, size, unresolved),
        "duration_available_coverage": _rate(durations, size, unresolved),
        "conditional_compliance": _rate(counts["PASS"], decisive, unresolved),
        "observed_transfer_burden": _burden(applicable, unresolved),
        "daily_observed_transfer_burden": [
            {
                "date": day,
                **_burden(
                    [c for c in applicable if c["declared_day"] == day],
                    [u for u in unresolved if u["declared_day"] == day],
                ),
            }
            for day in sorted(
                {c["declared_day"] for c in applicable} | {u["declared_day"] for u in unresolved}
            )
        ],
    }


def _check(leg, snapshot_leg, requests, records):
    request = requests.get(snapshot_leg["request_key"])
    record = records.get(snapshot_leg["request_key"])
    requested_at = record["attempts"][-1]["requested_at"] if record and record["attempts"] else None
    reasons = (
        context_reasons(request["parameters"], leg["expected_context"], requested_at)
        if request
        else ["route_context_missing"]
    )
    observed = observation(record)
    applicable = not reasons and observed["state"] != "UNKNOWN"
    evaluated, deficit = components(leg, observed, applicable)
    state = "N/A" if leg["applicability"] == "N/A" else conjunction(evaluated)
    if state == "N/A":
        evaluated, applicable, deficit = {}, False, None
    duration = observed["duration_nanoseconds"] if applicable else None
    return {
        **leg,
        "state": state,
        "components": evaluated,
        "structurally_evaluable": leg["selected_interval"] is not None
        and leg["mode"] is not None
        and None not in leg["canonical_endpoints"]
        and not leg["reasons"],
        "response_applicable": applicable,
        "context_reasons": reasons,
        "complete_evidence": bool(evaluated)
        and all(c["state"] != "UNKNOWN" for c in evaluated.values()),
        "duration_nanoseconds": duration,
        "duration_seconds_exact": seconds_exact(duration),
        "distance_meters": observed["distance_meters"] if applicable else None,
        "reserve_seconds": DRIVE_RESERVE_SECONDS if leg["mode"] == "DRIVE" else 0,
        "raw_deficit_nanoseconds": deficit,
        "raw_deficit_seconds_exact": seconds_exact(deficit),
        "evidence_reference": {
            "request_key": snapshot_leg["request_key"],
            "query": request["parameters"] if request else None,
            "attempts": record["attempts"] if record else [],
            "summary": record["summary"] if record else None,
        },
        "observation": observed,
        "reason": "same_canonical_venue" if state == "N/A" else None,
    }


def score_routes(
    intake,
    identity_report,
    snapshot_directory,
    schedule_context=None,
    occupancy_reviews=None,
    route_reviews=None,
    coordinate_evidence=None,
    *,
    paired=False,
    expected_plan=None,
    identity_snapshot_directory=None,
):
    """Replay a whole frozen batch; unavailable evidence never reduces its candidate population."""
    prepared = prepare_routes(
        intake,
        identity_report,
        schedule_context,
        occupancy_reviews,
        route_reviews,
        coordinate_evidence,
        paired=paired,
        identity_snapshot_directory=identity_snapshot_directory,
    ).to_dict()
    base = {
        "schema_version": REPORT_VERSION,
        "rules": RULES,
        "rules_hash": canonical_digest(RULES),
        "results": [],
        "diagnostics": prepared["diagnostics"],
    }
    if prepared["status"] != "complete":
        return RouteResult(prepared["status"], freeze(base))
    base["rules"], base["rules_hash"] = prepared["rules"], prepared["rules_hash"]
    if "coordinate_preparation" in prepared:
        base["coordinate_preparation"] = prepared["coordinate_preparation"]
    try:
        snapshot = load_snapshot(snapshot_directory, expected_plan=_value(expected_plan))
        requests = {r["key"]: r for r in snapshot["plan"]["requests"]}
        contexts = [
            {"leg_id": leg["leg_id"], **requests[leg["request_key"]]["parameters"]}
            for leg in snapshot["plan"]["legs"]
            if leg["request_key"] is not None
        ]
        linked = build_evidence_plan(
            _value(intake), _value(identity_report), contexts, paired=paired
        )
        require(
            snapshot["plan"] == linked,
            "snapshot/plan",
            "Snapshot identity/occurrence/request linkage mismatch",
        )
        legs = {leg["leg_id"]: leg for leg in snapshot["plan"]["legs"]}
        records = {r["key"]: r for r in snapshot["records"]}
        _, manifest_hash = _read(Path(snapshot_directory) / "manifest.json")
        base.update(
            batch_id=prepared["batch_id"], batch_revision=prepared["batch_revision"], paired=paired
        )
        base["source_hashes"] = {
            **prepared["source_hashes"],
            "preparation": canonical_digest(prepared),
            "snapshot_manifest": manifest_hash,
            "snapshot_plan": snapshot["plan_hash"],
            "trusted_expected_plan": canonical_digest(_value(expected_plan))
            if expected_plan
            else None,
        }
        for result in prepared["results"]:
            checks = [_check(leg, legs[leg["leg_id"]], requests, records) for leg in result["legs"]]
            base["results"].append(
                {k: v for k, v in result.items() if k != "legs"}
                | {
                    "routes": _summary(checks, result["unresolved_population_records"]),
                }
            )
        return RouteResult("complete", freeze(base))
    except (MaterialError, ValueError, KeyError, TypeError, OSError) as exc:
        base["results"] = []
        base["diagnostics"] = [
            exc.diagnostic
            if isinstance(exc, MaterialError)
            else {"reason": "snapshot_invalid", "explanation": str(exc)}
        ]
        return RouteResult("needs_material_correction", freeze(base))
