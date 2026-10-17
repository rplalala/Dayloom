"""Independent opening compliance over verified local evidence snapshots."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from importlib import resources
from pathlib import Path
from zoneinfo import TZPATH, ZoneInfo, ZoneInfoNotFoundError

from ._opening_hours import availability, seconds, subtract
from .identity import SUBJECT_SCOPE_VERSION
from .intake import _read
from .place_association import associated_place_id
from .preparation import identity_ready, schedule_timezones
from .records import MaterialError, canonical_digest, freeze, require, text, thaw
from .schedule_time import normalize_interval
from .snapshot import build_evidence_plan, load_snapshot

REPORT_VERSION = "rtpeval_opening_report_1"
RULES = {
    "version": "rtpeval_opening_rules_2",
    "intervals": "half_open",
    "grace_seconds": 0,
    "compliance_denominator": "PASS+FAIL",
    "identity_scope": SUBJECT_SCOPE_VERSION,
    "current_window_days": 7,
    "timestamp_fraction_digits": 6,
    "unknown_time_is_closed": False,
    "basis_order": ["applicable_current", "regular_for_unresolved_intervals"],
    "special_date_without_schedule": "diagnostic_only",
    "open_now": "query_instant_not_planned_visit",
    "timezone": "independent_place_or_reviewed_context",
}

ACCESS_RULES = {
    **RULES,
    "version": "rtpeval_opening_rules_4",
    "missing_hours_fallback": "llm_access_reasonableness_2",
    "public_landmark_intent": "ordinary_sightseeing_unless_restricted_activity",
    "model_pass_is_verified_hours": False,
}


@dataclass(frozen=True)
class OpeningResult:
    status: str
    data: Mapping

    def to_dict(self):
        return {"status": self.status, **thaw(self.data)}


def _value(value):
    return value.to_dict() if hasattr(value, "to_dict") else thaw(value)


def _verify_plan(actual, expected, prepared, identity):
    require(type(actual.get("paired")) is bool, "snapshot/plan", "Paired scope requires a boolean")
    for key in (
        "schema_version",
        "batch_id",
        "batch_revision",
        "intake_hash",
        "phase",
        "paired",
        "identity_report_hash",
        "references",
        "optional_availability",
    ):
        require(actual.get(key) == expected[key], "snapshot/plan", f"Opening plan mismatch: {key}")
    details = [r for r in actual["requests"] if r["operation"] == "places_details"]
    require(details == expected["requests"], "snapshot/plan", "Canonical details requests mismatch")
    requests = {r["key"]: r for r in actual["requests"]}
    contexts = [
        {"leg_id": leg["leg_id"], **requests[leg["request_key"]]["parameters"]}
        for leg in actual["legs"]
        if leg["request_key"] is not None
    ]
    # Retain supplied contexts without selecting or acquiring routes. Rebuilding checks
    # occurrence endpoints and rejects unused/foreign requests and stale leg linkage.
    linked_plan = build_evidence_plan(prepared, identity, contexts, paired=actual["paired"])
    require(actual == linked_plan, "snapshot/plan", "Snapshot route/reference linkage mismatch")


def _zone_basis(zone):
    """Identify the actual zone file selected by the installed Python zoneinfo search."""
    for root in TZPATH:
        path = Path(root).joinpath(*zone.split("/"))
        if path.is_file():
            return {
                "source": "system_zoneinfo",
                "zone_file_sha256": sha256(path.read_bytes()).hexdigest(),
            }
    import tzdata

    raw = resources.files("tzdata.zoneinfo").joinpath(*zone.split("/")).read_bytes()
    return {
        "source": "tzdata",
        "package_version": tzdata.__version__,
        "iana_version": tzdata.IANA_VERSION,
        "zone_file_sha256": sha256(raw).hexdigest(),
    }


def _timezone(payload, context_zone):
    raw = payload.get("timeZone")
    place_zone = raw.get("id") if isinstance(raw, dict) else None
    invalid = raw is not None and (
        not isinstance(raw, dict) or "id" in raw and not text(place_zone)
    )
    zone = place_zone or context_zone
    origin = "place_timeZone" if place_zone else "reviewed_group_context" if zone else None
    reasons = []
    if invalid:
        reasons.append("timezone_invalid")
    if place_zone and context_zone and place_zone != context_zone:
        reasons.append("timezone_evidence_conflict")
    if zone:
        try:
            ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            reasons.append("timezone_invalid")
            zone = None
    else:
        reasons.append("timezone_missing")
    provenance = {
        "id": zone,
        "origin": origin,
        "provider": raw,
        "reviewed_group_zone": context_zone,
        "zone_data": _zone_basis(zone) if zone else None,
    }
    return zone, provenance, list(dict.fromkeys(reasons))


def _check(activity, identity, reference, records, context_zone):
    raw = activity["original"]
    key = reference["requests"].get("details")
    record = records.get(key)
    payload = record["summary"].get("payload", {}) if record else {}
    zone, zone_provenance, zone_reasons = _timezone(payload, context_zone)
    interval = normalize_interval(
        raw.get("start_time"),
        raw.get("end_time"),
        activity["declared_day"],
        zone,
        allow_cross_date=True,
    )
    reasons = list(dict.fromkeys([*interval.reasons, *zone_reasons]))
    pid = associated_place_id(identity)
    if pid is None:
        reasons.append("identity_unresolved")
    elif not record or record["summary"]["status"] != "available":
        reasons.append("details_unavailable")
    elif payload.get("id") != pid:
        reasons.append("canonical_id_mismatch")
    opened, closed, segments = [], [], []
    if not reasons:
        attempt = record["attempts"][-1]
        opened, closed, segments, reasons = availability(
            payload, interval.span, zone, attempt["requested_at"], attempt["retrieved_at"]
        )
    known_open = seconds(opened)
    known_closed = seconds(closed)
    unknown = seconds(subtract([interval.span], opened + closed)) if interval.span else None
    state = "FAIL" if known_closed > 0 else ("PASS" if unknown == 0 else "UNKNOWN")
    bases = {s["basis"] for s in segments if s["basis"] != "unavailable"}
    basis = "mixed" if len(bases) > 1 else next(iter(bases), "unavailable")
    explanation = (
        "The full visit is covered by adopted opening evidence."
        if state == "PASS"
        else "A positive-duration portion of the visit is confirmed closed."
        if state == "FAIL"
        else "The visit cannot be decided from the retained evidence: " + ", ".join(reasons)
    )
    return {
        "source": activity["source"],
        **(
            {"identity_grounding_verdict": identity["grounding_verdict"]}
            if "programmatic_judgment" in identity or "candidate_correspondence" in identity
            else {}
        ),
        "declared_day": activity["declared_day"],
        "activity_id": raw.get("activity_id"),
        "reference_id": reference["reference_id"],
        "canonical_place_id": identity["canonical_place_id"],
        **({"associated_place_id": pid} if "place_association" in identity else {}),
        "state": state,
        "interval": interval.to_dict(),
        "structurally_evaluable": interval.span is not None,
        "identity_available": pid is not None,
        "timezone": zone_provenance,
        "evidence_reference": {
            "request_key": key,
            "summary": {k: v for k, v in record["summary"].items() if k != "payload"}
            if record
            else None,
            "attempts": record["attempts"] if record else [],
            "hours_fields_present": [
                field
                for field in ("currentOpeningHours", "regularOpeningHours")
                if field in payload
            ],
        },
        "basis": basis,
        "basis_segments": segments,
        "evidence_status": "complete"
        if unknown == 0
        else "partial"
        if opened or closed
        else "missing",
        "reasons": reasons,
        "explanation": explanation,
        "outside_seconds": known_closed if unknown == 0 else None,
        "confirmed_outside_lower_bound_seconds": known_closed if interval.span else None,
        "known_open_seconds": known_open if interval.span else None,
        "unknown_seconds": unknown,
    }


def _rate(numerator, denominator, unresolved):
    return {
        "numerator": numerator,
        "denominator": None if unresolved else denominator,
        "rate": numerator / denominator if denominator and not unresolved else None,
        "reason": "role_denominator_unresolved"
        if unresolved
        else "empty_denominator"
        if not denominator
        else None,
    }


def _subtotal(values):
    observed = [value for value in values if value is not None]
    return {
        "seconds": float(sum((Decimal(str(v)) for v in observed), Decimal(0)))
        if observed
        else None,
        "observed_visit_count": len(observed),
        "missing_visit_count": len(values) - len(observed),
        "aggregation": "per_visit_observed_subtotal",
    }


def _summary(checks, nonapplicable):
    counts = {
        state: sum(c["state"] == state for c in checks)
        for state in ("PASS", "FAIL", "UNKNOWN", "N/A")
    }
    decisive = counts["PASS"] + counts["FAIL"]
    unresolved = sum(c["role"] == "unresolved" for c in nonapplicable)
    complete = sum(c["evidence_status"] == "complete" for c in checks)
    structure = sum(c["structurally_evaluable"] for c in checks)
    summary = {
        "state": "FAIL"
        if counts["FAIL"]
        else "UNKNOWN"
        if counts["UNKNOWN"] or unresolved
        else "PASS"
        if checks
        else "N/A",
        "checks": checks,
        "counts": counts,
        "applicable_count": len(checks),
        "applicable_denominator": None if unresolved else len(checks),
        "unresolved_role_count": unresolved,
        "nonapplicable_records": nonapplicable,
        "structurally_evaluable_count": structure,
        "identity_available_count": sum(c["identity_available"] for c in checks),
        "complete_evidence_count": complete,
        "verdict_decidable_count": decisive,
        "evidence_counts": {
            kind: sum(c["evidence_status"] == kind for c in checks)
            for kind in ("complete", "partial", "missing")
        },
        "basis_counts": {
            kind: sum(c["basis"] == kind for c in checks)
            for kind in ("current", "regular", "mixed", "unavailable")
        },
        "structural_coverage": _rate(structure, len(checks), unresolved),
        "complete_evidence_coverage": _rate(complete, len(checks), unresolved),
        "verdict_decidable_coverage": _rate(decisive, len(checks), unresolved),
        "conditional_compliance": {
            "numerator": counts["PASS"],
            "denominator": decisive,
            "rate": counts["PASS"] / decisive if decisive and not unresolved else None,
        },
        "duration_subtotals": {
            key: _subtotal([c[key] for c in checks])
            for key in (
                "outside_seconds",
                "confirmed_outside_lower_bound_seconds",
                "known_open_seconds",
                "unknown_seconds",
            )
        },
    }
    if any("access_judgment" in c for c in checks):
        summary["llm_decidable_count"] = sum(
            c["basis"] == "llm_access_reasonableness" for c in checks
        )
        summary["llm_assessed_count"] = sum("access_judgment" in c for c in checks)
        summary["basis_counts"]["llm_access_reasonableness"] = summary["llm_decidable_count"]
    return summary


def score_opening(
    intake,
    identity_report,
    snapshot_directory,
    schedule_context=None,
    *,
    paired=False,
    expected_plan=None,
    opening_judgment=None,
):
    """Replay a whole batch; invalid preparation never reduces the scored cohort."""
    prepared, identity = _value(intake), _value(identity_report)
    context = _value(schedule_context)
    base = {
        "schema_version": REPORT_VERSION,
        "rules": RULES,
        "batch_id": prepared.get("batch_id"),
        "batch_revision": prepared.get("revision"),
        "rules_hash": canonical_digest(RULES),
        "results": [],
        "diagnostics": [],
    }
    try:
        require(prepared.get("status") == "accepted", "intake", "Accepted intake required")
        zones = schedule_timezones(prepared, context)
        if not identity_ready(prepared, identity):
            base["diagnostics"] = [
                {
                    "reason": "identity_replay_required",
                    "explanation": "Identity policy/source/reference linkage is stale or invalid.",
                }
            ]
            return OpeningResult("identity_replay_required", freeze(base))
        expected = build_evidence_plan(prepared, identity, [], paired=paired)
        snapshot = load_snapshot(snapshot_directory, expected_plan=_value(expected_plan))
        _verify_plan(snapshot["plan"], expected, prepared, identity)
        _, manifest_hash = _read(Path(snapshot_directory) / "manifest.json")
        base["source_hashes"] = {
            "intake": canonical_digest(prepared),
            "identity_report": canonical_digest(identity),
            "snapshot_manifest": manifest_hash,
            "expected_opening_plan": canonical_digest(expected),
            "snapshot_plan": snapshot["plan_hash"],
            "trusted_expected_plan": canonical_digest(_value(expected_plan))
            if expected_plan is not None
            else None,
            "schedule_context": canonical_digest(context) if context else None,
        }
        judgments = {}
        if opening_judgment is not None:
            from .opening_judgment import prepare_packet, validate_material

            material = _value(opening_judgment)
            packet = prepare_packet(
                prepared,
                identity,
                snapshot_directory,
                context,
                model=material["packet"]["model"],
                paired=paired,
                expected_plan=expected_plan,
                pair_only=material["packet"].get("pair_only", False),
            )
            judgments = validate_material(material, packet)
            base.update(rules=ACCESS_RULES, rules_hash=canonical_digest(ACCESS_RULES))
            base["source_hashes"]["opening_judgment"] = canonical_digest(material)
            base["model_provenance"] = {
                "packet_sha256": packet["content_sha256"],
                "requested_model": packet["model"],
                "reported_model": material["response"]["model"],
                "prompt_sha256": packet["prompt_sha256"],
                "requested_at": material["requested_at"],
                "retrieved_at": material["retrieved_at"],
                "usage": material["response"]["usage"],
            }
        identities = {i["reference_id"]: i for i in identity["records"]}
        refs = {r["reference_id"]: r for r in snapshot["plan"]["references"]}
        records = {r["key"]: r for r in snapshot["records"]}
        results = []
        for group in prepared["inventory"]:
            for version, run in group["runs"].items():
                projections = [("final", run["final"])]
                if paired and version == "v3":
                    projections.extend((label, p) for label, p in run["optional"].items() if p)
                for label, projection in projections:
                    checks = []
                    for activity in projection["activities"]:
                        if activity["evaluation_role"] == "primary_visit":
                            rid = activity["source"]["record_id"]
                            check = _check(
                                activity,
                                identities[rid],
                                refs[rid],
                                records,
                                zones.get(group["group_id"]),
                            )
                            if rid in judgments:
                                decision = judgments[rid]
                                check["access_judgment"] = decision
                                check["explanation"] = decision["rationale"]
                                if decision["state"] == "PASS":
                                    check.update(state="PASS", basis="llm_access_reasonableness")
                                    check["reasons"].append("llm_access_reasonableness_pass")
                                else:
                                    check["reasons"].append("llm_access_reasonableness_unknown")
                            checks.append(check)
                    nonapplicable = [
                        {
                            "source": a["source"],
                            "role": a["evaluation_role"],
                            "state": "UNKNOWN" if a["evaluation_role"] == "unresolved" else "N/A",
                            "reason": a["reason"],
                        }
                        for a in projection["activities"]
                        if a["evaluation_role"] != "primary_visit"
                    ]
                    results.append(
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
                            "opening": _summary(checks, nonapplicable),
                        }
                    )
        base["results"] = results
        return OpeningResult("complete", freeze(base))
    except (MaterialError, ValueError, KeyError, TypeError, OSError) as exc:
        base["diagnostics"] = [
            exc.diagnostic
            if isinstance(exc, MaterialError)
            else {"reason": "snapshot_invalid", "explanation": str(exc)}
        ]
        return OpeningResult("needs_material_correction", freeze(base))
