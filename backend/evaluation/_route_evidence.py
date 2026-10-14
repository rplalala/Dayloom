"""Raw matrix element interpretation and exact route component arithmetic."""

import re
from datetime import datetime

from ._route_rules import (
    CAPS,
    DISTANCE_TOLERANCE_METERS,
    DRIVE_RESERVE_SECONDS,
    DURATION_TOLERANCE_SECONDS,
    NANOSECOND,
    QUERY_TIMESTAMP_FRACTION_DIGITS,
    WALK_DISTANCE_CAP_METERS,
)


def seconds_exact(value, digits=9):
    if value is None:
        return None
    whole, fraction = divmod(value, 10**digits)
    return str(whole) + ("." + str(fraction).zfill(digits).rstrip("0") if fraction else "")


def duration_ns(value):
    match = re.fullmatch(r"([0-9]+)(?:\.([0-9]{1,9}))?s", value) if isinstance(value, str) else None
    try:
        return int(match[1]) * NANOSECOND + int((match[2] or "").ljust(9, "0")) if match else None
    except ValueError:
        return None


def context_reasons(actual, expected, requested_at):
    reasons = []
    if expected is None:
        return ["independent_route_context_unavailable"]
    for field in ("mode", "origin", "destination"):
        if actual[field] != expected[field]:
            reasons.append("query_" + field + "_mismatch")
    mode, options = actual["mode"], actual["routing_options"]
    preference = options.get("routing_preference")
    if preference is not None and (
        mode != "DRIVE"
        or preference
        not in (
            "TRAFFIC_UNAWARE",
            "TRAFFIC_AWARE",
            "TRAFFIC_AWARE_OPTIMAL",
        )
    ):
        reasons.append("routing_preference_unsupported")
    for key, value in options.items():
        if key.startswith("avoid_"):
            if mode != "DRIVE" or type(value) is not bool:
                reasons.append("routing_modifier_unsupported")
        elif key in ("language_code", "region_code") and (
            not isinstance(value, str) or not value.strip()
        ):
            reasons.append("routing_locale_invalid")
    if actual["routing_options"] != expected["routing_options"]:
        reasons.append("query_options_mismatch")
    if actual["time_basis"] == "time_independent":
        if mode != "WALK" and not (mode == "DRIVE" and preference == "TRAFFIC_UNAWARE"):
            reasons.append("time_independent_mode_unsupported")
        if actual["time_basis"] != expected["time_basis"]:
            reasons.append("query_time_basis_mismatch")
    else:
        target = expected["departure"]
        fraction = re.search(r"\.([0-9]+)", actual["departure"])
        if fraction and len(fraction[1]) > QUERY_TIMESTAMP_FRACTION_DIGITS:
            reasons.append("unsupported_query_timestamp_precision")
        query = datetime.fromisoformat(actual["departure"])
        if target is None or query != datetime.fromisoformat(target):
            reasons.append("query_departure_mismatch")
        if mode != "TRANSIT" and requested_at and query < datetime.fromisoformat(requested_at):
            reasons.append("historical_query_unsupported")
    return list(dict.fromkeys(reasons))


def observation(record):
    if record is None or record["summary"]["status"] != "available":
        return {
            "state": "UNKNOWN",
            "reason": record["summary"].get("reason") if record else "route_evidence_missing",
            "duration_nanoseconds": None,
            "distance_meters": None,
            "element": None,
        }
    element = record["summary"]["element"]
    status = element.get("status")
    code = status.get("code", 0) if isinstance(status, dict) else None
    condition = element.get("condition")
    reason = None
    if (
        type(code) is not int
        or code != 0
        or "message" in status
        and not isinstance(status["message"], str)
        or "details" in status
        and (
            not isinstance(status["details"], list)
            or not all(isinstance(detail, dict) for detail in status["details"])
        )
    ):
        reason = "route_status_invalid_or_error"
    elif condition not in ("ROUTE_EXISTS", "ROUTE_NOT_FOUND"):
        reason = "route_condition_invalid"
    elif condition == "ROUTE_NOT_FOUND" and any(
        k in element for k in ("duration", "distanceMeters", "staticDuration", "fallbackInfo")
    ):
        reason = "no_route_fields_contradictory"
    state = "UNKNOWN" if reason else "FAIL" if condition == "ROUTE_NOT_FOUND" else "PASS"
    duration = duration_ns(element.get("duration")) if state == "PASS" else None
    distance = element.get("distanceMeters") if state == "PASS" else None
    if type(distance) is not int or distance < 0:
        distance = None
    return {
        "state": state,
        "reason": reason or ("no_route" if state == "FAIL" else "route_exists"),
        "duration_nanoseconds": duration,
        "distance_meters": distance,
        "element": element,
    }


def conjunction(components):
    states = [c["state"] for c in components.values() if c["state"] != "N/A"]
    return (
        "FAIL"
        if "FAIL" in states
        else "PASS"
        if states and all(s == "PASS" for s in states)
        else "UNKNOWN"
    )


def components(leg, observed, applicable):
    components = {
        "mode_policy": leg.get("mode_policy_score", leg["mode_policy"]),
        "availability": {
            "state": observed["state"] if applicable else "UNKNOWN",
            "reason": observed["reason"] if applicable else "query_context_inapplicable",
        },
    }
    mode = leg["mode"]
    d = observed["duration_nanoseconds"] if applicable else None
    distance = observed["distance_meters"] if applicable else None
    reserve = DRIVE_RESERVE_SECONDS if mode == "DRIVE" else 0
    gap = leg["available_nanoseconds"]
    deficit = max(0, d + reserve * NANOSECOND - gap) if d is not None and gap is not None else None
    components["duration_cap"] = {
        "state": "PASS"
        if d is not None and d <= (CAPS[mode] + DURATION_TOLERANCE_SECONDS) * NANOSECOND
        else "FAIL"
        if d is not None
        else "UNKNOWN",
        "nominal_seconds": CAPS.get(mode),
        "tolerance_seconds": DURATION_TOLERANCE_SECONDS,
        "raw_overrun_nanoseconds": max(0, d - CAPS[mode] * NANOSECOND) if d is not None else None,
    }
    components["distance_cap"] = {
        "state": "N/A"
        if mode != "WALK"
        else "UNKNOWN"
        if distance is None
        else "PASS"
        if distance <= WALK_DISTANCE_CAP_METERS + DISTANCE_TOLERANCE_METERS
        else "FAIL",
        "nominal_meters": WALK_DISTANCE_CAP_METERS if mode == "WALK" else None,
        "tolerance_meters": DISTANCE_TOLERANCE_METERS,
        "raw_overrun_meters": max(0, distance - WALK_DISTANCE_CAP_METERS)
        if distance is not None and mode == "WALK"
        else None,
    }
    components["schedule"] = {
        "state": "UNKNOWN"
        if deficit is None
        else "PASS"
        if deficit <= leg["schedule_tolerance_seconds"] * NANOSECOND
        else "FAIL",
        "deadline_kind": leg["deadline_kind"],
        "tolerance_seconds": leg["schedule_tolerance_seconds"],
        "reserve_seconds": reserve,
        "raw_deficit_nanoseconds": deficit,
    }
    for name, magnitude in (
        ("duration_cap", components["duration_cap"]["raw_overrun_nanoseconds"]),
        ("schedule", deficit),
    ):
        check = components[name]
        check["classification"] = (
            "unavailable"
            if magnitude is None
            else "exceeded"
            if check["state"] == "FAIL"
            else "within_tolerance"
            if magnitude
            else "exact"
        )
        check["reason"] = (
            (
                "duration_unavailable"
                if name == "duration_cap"
                else "continuous_interval_or_duration_unavailable"
            )
            if check["state"] == "UNKNOWN"
            else None
        )
    components["distance_cap"]["reason"] = (
        "distance_unavailable" if mode == "WALK" and distance is None else None
    )
    if applicable and observed["state"] == "FAIL":
        for name in ("duration_cap", "distance_cap", "schedule"):
            components[name]["state"] = "N/A"
            components[name]["reason"] = "no_route"
    return components, deficit
