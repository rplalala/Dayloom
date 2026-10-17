"""Offline requirement and schedule metrics over immutable independent preparation."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo

from ._schedule_preparation import (
    OBLIGATION_FIELDS,
    _clock,
    _days,
    _occupancy_reviews,
    _validate_spec,
    _validate_time_capacity,
    _window,
)
from .identity import SUBJECT_SCOPE_VERSION
from .occupancy import assess_occupancy, intersections, prepare_occupancy, read_span, stable_id
from .place_association import associated_place_id
from .preparation import identity_ready as _identity_ready
from .preparation import schedule_timezones as _context
from .records import MaterialError, freeze, require, thaw
from .schedule_time import expand_protection, normalize_interval

REPORT_VERSION = "rtpeval_requirement_schedule_report_1"
RULES_VERSION = "rtpeval_requirement_schedule_rules_3"
RULES = {
    "version": RULES_VERSION,
    "identity_scope": SUBJECT_SCOPE_VERSION,
    "occurrence_identity": "verified_place_association_else_historical_canonical",
    "target_identity": "version_owned_adopted_canonical",
    "intervals": "half_open",
    "time_tolerance_seconds": 0,
    "transport": "v0_activity_v1_v3_transfer",
    "unbound_v0_transport": "declared_activity_clock_establishes_occupancy_without_route_identity",
    "count_default": "explicit_reviewed_payload",
    "protection_units": False,
    "timestamp_fraction_digits": 6,
}


def _transport_component(projection, obligation):
    """One obligation result over independently projected mode claims, not route feasibility."""
    from ._route_inputs import policy_component

    review = {"status": "restricted", "policies": [obligation]}
    rows = []
    for leg in projection["legs"]:
        claims = leg["claims"]
        for claim in claims or [{"mode": None}]:
            rows.append(policy_component(review, claim["mode"], leg["declared_day"]))
    for claim in projection.get("unbound_transport", []):
        row = policy_component(review, claim["mode"], None)
        if row["state"] == "PASS":
            row = {**row, "state": "UNKNOWN", "reason": "transport_association_unresolved"}
        rows.append(row)
    return {
        "kind": "transport_modes",
        "state": _conjunction([r["state"] for r in rows]) if rows else "PASS",
        "claims": rows,
    }


@dataclass(frozen=True)
class RequirementScheduleResult:
    status: str
    data: Mapping

    def to_dict(self):
        return {"status": self.status, **thaw(self.data)}


def _value(value):
    return value.to_dict() if hasattr(value, "to_dict") else thaw(value)


def _conjunction(states):
    return "FAIL" if "FAIL" in states else "PASS" if all(s == "PASS" for s in states) else "UNKNOWN"


def _count_component(lower, upper, mode, target, kind="count"):
    if mode == "minimum":
        state = "PASS" if lower >= target else "FAIL" if upper < target else "UNKNOWN"
    else:
        state = (
            "PASS"
            if lower == upper == target
            else ("FAIL" if lower > target or upper < target else "UNKNOWN")
        )
    return {
        "kind": kind,
        "state": state,
        "bounds": {"lower": lower, "upper": upper},
        "mode": mode,
        "target": target,
    }


def _count_matches(confirmed, potential, mode, target, kind="count"):
    return {
        **_count_component(len(confirmed), len(confirmed) + len(potential), mode, target, kind),
        "confirmed_sources": [item["activity"]["source"] for item in confirmed],
        "potential_sources": [item["activity"]["source"] for item in potential],
    }


def _occurrences(projection, identity_index, timezone):
    result, seen = [], set()
    for activity in projection["activities"]:
        key = activity["source"]["record_id"]
        if key in seen or activity["evaluation_role"] not in ("primary_visit", "unresolved"):
            continue
        seen.add(key)
        raw = activity["original"]
        interval = normalize_interval(
            raw.get("start_time"), raw.get("end_time"), activity["declared_day"], timezone
        )
        record = identity_index.get(key, {})
        result.append(
            {
                "activity": activity,
                "interval": interval,
                "primary": activity["evaluation_role"] == "primary_visit",
                "identity": record,
                "associated_id": associated_place_id(record) if record else None,
                "canonical_id": record.get("canonical_place_id")
                if record.get("resolution") == "resolved"
                else None,
            }
        )
    return result


def _matches(occurrences, canonical, days):
    confirmed, potential = [], []
    for item in occurrences:
        activity = item["activity"]
        consistent = item["interval"].date_consistent
        if consistent and activity["declared_day"] not in days:
            continue
        associated = item["associated_id"]
        if item["primary"] and canonical and associated and canonical != associated:
            continue
        if item["primary"] and canonical and associated == canonical and consistent:
            confirmed.append(item)
        else:
            potential.append(item)
    return confirmed, potential


def _time_conditions(item, conditions, timezone):
    interval = item["interval"]
    components = []
    for kind, value in conditions.items():
        state, reason = "UNKNOWN", None
        if interval.span is None:
            reason = "time_unresolved"
        elif kind == "duration":
            seconds = interval.span.seconds
            ok = (
                seconds == value["seconds"]
                if value["mode"] == "exact"
                else seconds >= value["seconds"]
            )
            state = "PASS" if ok else "FAIL"
        elif not timezone:
            reason = "timezone_missing"
        else:
            local_start = interval.span.start.astimezone(ZoneInfo(timezone))
            local_end = interval.span.end.astimezone(ZoneInfo(timezone))
            start_seconds = (
                local_start.hour * 3600
                + local_start.minute * 60
                + local_start.second
                + local_start.microsecond / 1e6
            )
            end_seconds = (
                local_end.hour * 3600
                + local_end.minute * 60
                + local_end.second
                + local_end.microsecond / 1e6
            )
            if kind == "start_at":
                ok = start_seconds == _clock(value, "start_at")
            else:
                first, last = _window(value, "within")
                ok = first <= start_seconds and end_seconds <= last
            state = "PASS" if ok else "FAIL"
        components.append(
            {"kind": kind, "state": state, "reason": reason, "interval": interval.to_dict()}
        )
    return _conjunction([c["state"] for c in components]), components


def _fixed_components(obligation, occurrences, canonical, days, timezone):
    confirmed, potential = _matches(occurrences, canonical, [obligation["date"]])
    evaluated = []
    for item in confirmed:
        state, components = _time_conditions(item, obligation["conditions"], timezone)
        evaluated.append(
            {"source": item["activity"]["source"], "state": state, "components": components}
        )
    possible_compliant = [
        item
        for item in potential
        if _time_conditions(item, obligation["conditions"], timezone)[0] != "FAIL"
    ]
    state = (
        "PASS"
        if any(item["state"] == "PASS" for item in evaluated)
        else (
            "UNKNOWN"
            if possible_compliant or any(item["state"] == "UNKNOWN" for item in evaluated)
            else "FAIL"
        )
    )
    components = [
        {
            "kind": "dated_time_conjunction",
            "state": state,
            "date": obligation["date"],
            "visits": evaluated,
            "potential_sources": [p["activity"]["source"] for p in potential],
        }
    ]
    if obligation["match"] == "single_visit":
        all_confirmed, all_potential = _matches(occurrences, canonical, days)
        components.insert(
            0,
            _count_matches(all_confirmed, all_potential, "exact", 1),
        )
    return components


def _requirement_checks(group, projection, identity_index, timezone):
    days = _days(group["input"])
    occurrences = _occurrences(projection, identity_index, timezone)
    subjects = {
        item["source"].get("subject_id"): item.get("canonical_place_id")
        for item in identity_index.values()
        if item["kind"] == "requirement_subject"
        and item["group_id"] == group["group_id"]
        and item["version"] in (None, projection["planner_version"])
        and item["resolution"] == "resolved"
    }
    subject_failures = {
        item["source"].get("subject_id"): item
        for item in identity_index.values()
        if item["kind"] == "requirement_subject"
        and item["group_id"] == group["group_id"]
        and item["version"] in (None, projection["planner_version"])
        and ("programmatic_judgment" in item or "candidate_correspondence" in item)
        and item["grounding_verdict"] == "FAIL"
    }
    checks = []
    for obligation in group["requirement_spec"]["obligations"]:
        components = []
        kind = obligation["kind"]
        if kind not in OBLIGATION_FIELDS:
            continue
        if obligation["resolution"] != "resolved":
            components.append(
                {
                    "kind": kind,
                    "state": "UNKNOWN",
                    "reason": obligation.get("reason", "semantics_unresolved"),
                }
            )
        elif kind == "transport_modes":
            components.append(_transport_component(projection, obligation))
        elif kind == "daily_visit_count":
            confirmed, possible = [], []
            for item in occurrences:
                consistent = item["interval"].date_consistent
                if consistent and item["activity"]["declared_day"] != obligation["date"]:
                    continue
                (confirmed if item["primary"] and consistent else possible).append(item)
            count = obligation["count"]
            components.append(
                _count_matches(
                    confirmed, possible, count["mode"], count["value"], "daily_primary_count"
                )
            )
        elif kind == "required_visit":
            confirmed, possible = _matches(
                occurrences, subjects.get(obligation["subject_ref"]), days
            )
            count = obligation["count"]
            components.append(_count_matches(confirmed, possible, count["mode"], count["value"]))
            if obligation.get("distinct_dates"):
                lower = {item["activity"]["declared_day"] for item in confirmed}
                upper = lower | {
                    item["activity"]["declared_day"]
                    for item in possible
                    if item["interval"].date_consistent
                }
                if any(not item["interval"].date_consistent for item in possible):
                    upper |= set(days)
                # One uncertain occurrence cannot establish multiple distinct dates.
                upper_count = min(len(upper), len(confirmed) + len(possible))
                components.append(
                    _count_component(
                        len(lower), upper_count, "minimum", count["value"], "distinct_dates"
                    )
                )
            for dated in obligation.get("date_obligations", []):
                matches, uncertain = _matches(
                    occurrences, subjects.get(obligation["subject_ref"]), [dated["date"]]
                )
                component = _count_matches(
                    matches, uncertain, dated["count_mode"], dated["count"], "dated_count"
                )
                component["date"] = dated["date"]
                components.append(component)
        elif kind == "excluded_visit":
            scope = days if obligation["scope"] == "whole_trip" else obligation["dates"]
            confirmed, possible = _matches(
                occurrences, subjects.get(obligation["subject_ref"]), scope
            )
            components.append(
                {
                    "kind": "exclusion",
                    "state": "FAIL" if confirmed else "UNKNOWN" if possible else "PASS",
                    "bounds": {"lower": len(confirmed), "upper": len(confirmed) + len(possible)},
                    "confirmed_sources": [item["activity"]["source"] for item in confirmed],
                    "potential_sources": [item["activity"]["source"] for item in possible],
                }
            )
        elif kind == "fixed_visit_time":
            components = _fixed_components(
                obligation, occurrences, subjects.get(obligation["subject_ref"]), days, timezone
            )
        else:
            components.append({"kind": kind, "state": "UNKNOWN", "reason": "pending_check"})
        failure = subject_failures.get(obligation.get("subject_ref"))
        if failure:
            components.append({"kind": "subject_identity", "state": "FAIL", "identity": failure})
        checks.append(
            {
                "check_id": stable_id([projection["context"], obligation["obligation_id"]]),
                "obligation_id": obligation["obligation_id"],
                "kind": kind,
                "applicability": "applicable",
                "sources": obligation["source_refs"],
                "components": components,
                "state": _conjunction([c["state"] for c in components]),
                **(
                    {"aggregation_owner": "requirements"}
                    if kind == "transport_modes" and obligation["resolution"] == "resolved"
                    else {}
                ),
            }
        )
    return checks, occurrences


def _dimension(checks, denominator_unresolved=False, reasons=()):
    counts = {
        state: sum(item["state"] == state for item in checks)
        for state in ("PASS", "FAIL", "UNKNOWN")
    }
    denominator = len(checks)
    return {
        "checks": checks,
        "counts": counts,
        "known_unit_count": denominator,
        "denominator_unresolved": denominator_unresolved,
        "denominator": None if denominator_unresolved else denominator,
        "state": "UNKNOWN"
        if denominator_unresolved
        else (_conjunction([item["state"] for item in checks]) if checks else "N/A"),
        "verified_fraction": counts["PASS"] / denominator
        if denominator and not denominator_unresolved
        else None,
        "reasons": list(reasons),
    }


def _descriptive(group, projection, occurrences):
    days = _days(group["input"])
    density, known_days, unknown_days = [], set(), set()
    for day in days:
        known = [
            item
            for item in occurrences
            if item["primary"]
            and item["interval"].date_consistent
            and item["activity"]["declared_day"] == day
        ]
        possible = [
            item
            for item in occurrences
            if not item["interval"].date_consistent
            or not item["primary"]
            and item["activity"]["declared_day"] == day
        ]
        lower, upper = len(known), len(known) + len(possible)

        def category(count):
            return "<2" if count < 2 else "2..5" if count <= 5 else ">5"

        density.append(
            {
                "date": day,
                "known_primary_count": lower,
                "possible_primary_count": len(possible),
                "category": category(lower) if category(lower) == category(upper) else None,
            }
        )
        if known:
            known_days.add(day)
        elif possible:
            unknown_days.add(day)
    groups, unidentified = {}, 0
    for item in occurrences:
        if not item["interval"].date_consistent:
            unidentified += 1
            continue
        day = item["activity"]["declared_day"]
        if day not in days:
            continue
        if not item["primary"] or not item["canonical_id"]:
            unidentified += 1
            continue
        canonical = item["canonical_id"]
        groups.setdefault(canonical, {}).setdefault(day, []).append(item["activity"]["source"])
    venues = []
    for canonical, dates in sorted(groups.items()):
        count = sum(len(sources) for sources in dates.values())
        venues.append(
            {
                "canonical_place_id": canonical,
                "occurrence_count": count,
                "date_count": len(dates),
                "extra_occurrences": count - 1,
                "within_day_extras": sum(len(sources) - 1 for sources in dates.values()),
                "across_day_extras": len(dates) - 1,
                "dates": dates,
            }
        )
    coverage = {
        "requested_day_count": len(days),
        "declared_day_present_count": len(set(projection["declared_days"]) & set(days)),
        "any_activity_day_count": len(
            {a["declared_day"] for a in projection["activities"]} & set(days)
        ),
        "known_primary_day_count": len(known_days),
        "unknown_primary_day_count": len(unknown_days),
        "empty_primary_day_count": len(days) - len(known_days) - len(unknown_days),
        "extra_declared_days": sorted(set(projection["declared_days"]) - set(days)),
    }
    return {
        "coverage": coverage,
        **(
            {"identity_checks": [item["identity"] for item in occurrences]}
            if any("programmatic_judgment" in item["identity"] for item in occurrences)
            else {}
        ),
        "density": density,
        "repetition": {
            "venues": venues,
            "repeated_venue_count": sum(v["occurrence_count"] > 1 for v in venues),
            "known_identity_occurrences": sum(v["occurrence_count"] for v in venues),
            "unknown_identity_occurrences": unidentified,
            "extra_occurrences": sum(v["extra_occurrences"] for v in venues),
            "within_day_extras": sum(v["within_day_extras"] for v in venues),
            "across_day_extras": sum(v["across_day_extras"] for v in venues),
            "status": "lower_bound" if unidentified else "complete",
            "reviewed_revisit_obligations": [
                item
                for item in group["requirement_spec"]["obligations"]
                if item["kind"] == "required_visit"
            ],
        },
    }


def _daily_measures(measures, requested_days, timezone):
    if not timezone:
        measures["daily"] = None
        measures["daily_availability_reason"] = "timezone_missing"
        return
    keys = (
        "scheduled_occupied",
        "protected_reserved",
        "commitment_conflict",
        "protection_conflict",
        "combined_conflict",
    )
    days = set(requested_days)
    zone = ZoneInfo(timezone)
    for key in keys:
        for raw in measures[key]["intervals"]:
            span = read_span(raw)
            start, end = span.start.astimezone(zone).date(), span.end.astimezone(zone).date()
            days.update(
                (start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)
            )
    daily = {}
    for day in sorted(days):
        boundary = expand_protection({"date": day, "interval": {"kind": "full_day"}}, timezone)
        if boundary.span is None:
            daily[day] = {"availability_reason": "local_midnight_unresolved"}
            continue
        daily[day] = {}
        for key in keys:
            measure = measures[key]
            spans = intersections([read_span(raw) for raw in measure["intervals"]], [boundary.span])
            daily[day][key] = {
                "seconds": sum(span.seconds for span in spans)
                if spans or measure["status"] == "complete"
                else None,
                "status": measure["status"],
                "unknown_record_count": measure["unknown_record_count"],
                "intervals": [span.to_dict() for span in spans],
            }
    measures["daily"] = daily
    measures["daily_availability_reason"] = None


def score_requirement_schedule(
    intake, identity_report, schedule_context=None, occupancy_reviews=None, *, paired=False
):
    """Evaluate a whole accepted batch; material correction never returns a partial cohort."""
    prepared, identity = _value(intake), _value(identity_report)
    schedule_context, occupancy_reviews = _value(schedule_context), _value(occupancy_reviews)
    base = {
        "schema_version": REPORT_VERSION,
        "batch_id": prepared.get("batch_id"),
        "batch_revision": prepared.get("revision"),
        "rules_version": RULES_VERSION,
        "rules_hash": stable_id(RULES),
        "results": [],
        "diagnostics": [],
    }
    rules = RULES
    if any(
        o["kind"] == "transport_modes"
        for g in prepared.get("inventory", [])
        for o in g["requirement_spec"]["obligations"]
    ):
        rules = {
            **RULES,
            "version": "rtpeval_requirement_schedule_rules_4",
            "transport_modes": "source_bound_whole_trip_claims_1",
        }
        base.update(rules_version=rules["version"], rules_hash=stable_id(rules))
    if any(
        o["kind"] == "daily_visit_count"
        for g in prepared.get("inventory", [])
        for o in g["requirement_spec"]["obligations"]
    ):
        rules = {
            **rules,
            "version": "rtpeval_requirement_schedule_rules_5",
            "daily_visit_count": "source_distinct_primary_occurrences_with_date_role_bounds_1",
        }
        base.update(rules_version=rules["version"], rules_hash=stable_id(rules))
    try:
        require(prepared.get("status") == "accepted", "intake", "Accepted intake is required")
        completeness = {group["group_id"]: _validate_spec(group) for group in prepared["inventory"]}
        zones = _context(prepared, schedule_context)
        for group in prepared["inventory"]:
            _validate_time_capacity(group, zones.get(group["group_id"]))
        reviews = _occupancy_reviews(prepared, occupancy_reviews)
        if not _identity_ready(prepared, identity):
            base["diagnostics"] = [{"reason": "identity_replay_required"}]
            return RequirementScheduleResult("identity_replay_required", freeze(base))
        identity_index = {item["reference_id"]: item for item in identity["records"]}
        results = []
        for group in prepared["inventory"]:
            for version, run in group["runs"].items():
                projections = [("final", run["final"])]
                if paired and version == "v3":
                    projections.extend((label, p) for label, p in run["optional"].items() if p)
                for label, projection in projections:
                    zone = zones.get(group["group_id"])
                    checks, occurrences = _requirement_checks(
                        group, projection, identity_index, zone
                    )
                    occupancy = prepare_occupancy(
                        projection, group["requirement_spec"]["obligations"], zone, reviews
                    )
                    non_overlap, protections, measures = assess_occupancy(occupancy)
                    _daily_measures(measures, _days(group["input"]), zone)
                    for check in checks:
                        if check["kind"] == "protected_time":
                            state = protections[check["obligation_id"]]
                            check["state"] = state
                            check["components"] = [{"kind": "protected_conflict", "state": state}]
                    results.append(
                        {
                            "group_id": group["group_id"],
                            "version": version,
                            "projection": label,
                            "run_id": projection["context"]["run_id"],
                            "projection_id": stable_id(
                                [projection["context"], projection["projection"]]
                            ),
                            "source_hashes": {
                                "input": group["input_sha256"],
                                "requirement_spec": group["requirement_spec_sha256"],
                                "result": projection["context"]["artifact_sha256"],
                                "identity_report": stable_id(identity),
                                "identity_evidence": identity["evidence_hash"],
                                "identity_review": identity["review_hash"],
                                "identity_audit": identity["audit_plan_hash"],
                                "identity_references": identity["reference_set_digest"],
                                "schedule_context": stable_id(schedule_context)
                                if schedule_context
                                else None,
                                "occupancy_review": stable_id(occupancy_reviews)
                                if occupancy_reviews
                                else None,
                                "rules": base["rules_hash"],
                            },
                            "preparation_revisions": {
                                "context": schedule_context.get("revision")
                                if schedule_context
                                else None,
                                "occupancy_review": occupancy_reviews.get("revision")
                                if occupancy_reviews
                                else None,
                            },
                            "requirements": {
                                **_dimension(
                                    checks,
                                    completeness[group["group_id"]],
                                    ["requirement_completeness_unresolved"]
                                    if completeness[group["group_id"]]
                                    else [],
                                ),
                                "unclassified_obligations": [
                                    item
                                    for item in group["requirement_spec"]["obligations"]
                                    if item["kind"] not in OBLIGATION_FIELDS
                                ],
                            },
                            "requirement_identity": [
                                {
                                    "source": item["activity"]["source"],
                                    "associated_place_id": item["associated_id"],
                                    "canonical_place_id": item["canonical_id"],
                                    "grounding_verdict": item["identity"].get("grounding_verdict"),
                                    "basis": "verified_place_association"
                                    if item["associated_id"]
                                    and "place_association" in item["identity"]
                                    else "adopted_canonical_identity"
                                    if item["associated_id"]
                                    else "unresolved",
                                }
                                for item in occurrences
                            ],
                            "non_overlap": {
                                **_dimension(
                                    non_overlap,
                                    bool(occupancy.candidates),
                                    ["commitment_denominator_unresolved"]
                                    if occupancy.candidates
                                    else [],
                                ),
                                "candidate_unit_count": len(occupancy.candidates),
                            },
                            "schedule_measures": measures,
                            "descriptive": _descriptive(group, projection, occurrences),
                            "occupancy": occupancy.to_dict(),
                        }
                    )
        base["results"] = results
        return RequirementScheduleResult("complete", freeze(base))
    except MaterialError as exc:
        base["diagnostics"] = [exc.diagnostic]
        return RequirementScheduleResult("needs_material_correction", freeze(base))
