"""Bounded presentation memory and evidence-scoped feedback, never a fact evaluator."""

import hashlib
import json
from datetime import datetime


def semantic_value(value):
    """Ignore observational metadata and collection order, not schedule or route direction."""
    if isinstance(value, dict):
        return {
            k: semantic_value(v)
            for k, v in sorted(value.items())
            if k
            not in {
                "retrieved_at",
                "requested_at",
                "round_index",
                "trace_id",
                "opportunity_signature",
                "reason",
                "opportunity_reason",
            }
        }
    if isinstance(value, (tuple, list)):
        rows = [semantic_value(v) for v in value]
        return sorted(rows, key=lambda v: json.dumps(v, sort_keys=True))
    return value


def digest(value):
    return hashlib.sha256(
        json.dumps(semantic_value(value), sort_keys=True, default=str).encode()
    ).hexdigest()


def material_fingerprint(user):
    payload = json.loads(user)
    # These fields describe decisions, not round commentary, counts or acquisition history.
    keys = (
        "semantic_assessments",
        "pending_dependency_groups",
        "candidate_catalog",
        "selected_opening_evidence",
        "time_windows",
        "time_protection",
        "spatial_policy",
        "scope",
        "visit_bindings",
        "requirements",
        "editable_activities",
        "protected_activities",
        "scheduled_coordinates",
        "addition_candidates",
        "other_operation_candidates",
        "effective_evidence",
        "routes",
        "transport_options",
        "adopted_transfers",
        "target_worksheet",
        "arrangement_constraints",
        "operation_guidance",
        "schedule_time_context",
        "affected_day_replan",
    )
    return digest({k: payload.get(k) for k in keys})


def opportunity(place, day, operation, view, original, context, scope, policy=None, required=False):
    """Only prove impossibility over known authorized windows; no invented visit duration."""
    from backend.app.versions.v3.repair_targets import insertion_windows

    windows = tuple(
        (w["start"], w["end"])
        for w in insertion_windows(original, context.schedule, scope)
        if datetime.fromisoformat(w["start"]).date() == day
    )
    if operation != "add" or scope.coverage_permissions:
        return "UNRESOLVED", "conditional_operation_windows", windows
    if context.schedule is None or str(day) in context.schedule.unresolved_dates:
        return "UNRESOLVED", "window_contract_incomplete", windows
    if not windows:
        return "BLOCKED", "no_authorized_insertion_window", windows
    if view["known"]:
        intersections = []
        for start, end in windows:
            a, b = datetime.fromisoformat(start), datetime.fromisoformat(end)
            # selected_hours uses venue-local naive intervals; only compare a known zone.
            from zoneinfo import ZoneInfo

            zone = view.get("timezone")
            if not zone:
                return "UNRESOLVED", "opening_timezone_missing", windows
            for opened, closed in view["intervals"]:
                left = max(a, datetime.fromisoformat(opened).replace(tzinfo=ZoneInfo(zone)))
                right = min(b, datetime.fromisoformat(closed).replace(tzinfo=ZoneInfo(zone)))
                if left < right:
                    intersections.append((left.isoformat(), right.isoformat()))
        if not intersections:
            return "BLOCKED", "opening_excludes_all_authorized_windows", windows
        windows = tuple(intersections)
    from backend.app.versions.v3.repair_transport import allowed_modes

    if policy is not None and len(allowed_modes(scope)) == 1:
        from backend.app.versions.v3.repair_routes import route_rows
        from backend.app.versions.v3.repair_schedule import ordered_activities

        ordered = [
            a
            for d in original.days
            if d.date == day
            for a in ordered_activities(d, context.schedule)
        ]
        retained = []
        for start, end in windows:
            a, b = datetime.fromisoformat(start), datetime.fromisoformat(end)
            left = [x for x in ordered if x.end_time <= a]
            right = [x for x in ordered if x.start_time >= b]
            pairs = []
            if left and left[-1].source_place_id:
                pairs.append((left[-1].source_place_id, place.place_id))
            if right and right[0].source_place_id:
                pairs.append((place.place_id, right[0].source_place_id))
            blocked = False
            for origin, destination in pairs:
                # No selected departure exists yet. Only the selector's time-independent
                # estimates can establish a whole-window application leg-policy obstacle.
                rows = route_rows(
                    origin,
                    destination,
                    scope.travel_mode or "WALK",
                    scope.routing_preference,
                    None,
                    context.route_evidence,
                )
                if (
                    rows
                    and not required
                    and all(r["duration_seconds"] > policy.max_leg_minutes * 60 for r in rows)
                ):
                    blocked = True
            if not blocked:
                retained.append((start, end))
        if not retained:
            return "BLOCKED", "leg_policy_excludes_all_authorized_windows", windows
        windows = tuple(retained)
    if not view["known"] or place.latitude is None or place.longitude is None:
        return "UNRESOLVED", "unverified_dimensions_remain_selectable", windows
    return "TRYABLE", "potential_window_not_full_feasibility", windows


def feedback_kind(result):
    if result.model_attempted and result.parsed_patch is None:
        return "provider_or_model_failure"
    if result.parsed_patch is not None and not result.parsed_patch.edits:
        return "no_op_patch"
    if result.status.startswith("ACCEPTED"):
        return "arrangement_improved"
    if result.proposed_report is not None and (
        any(f.status == "CONFIRMED" for f in result.proposed_report.findings)
        or result.spatial.get("reasons")
    ):
        return "candidate_specific_conflict"
    if result.comparison is not None:
        return "no_measurable_improvement"
    return "scope_or_operation_invalid" if result.parsed_patch else "not_evaluated"


def learn(result, budget, round_index):
    """Attribute only findings/legs identifying edited activities, never all patch members."""
    history = getattr(budget, "presentation_history", [])
    records = getattr(budget, "conflict_records", [])
    patch = result.parsed_patch
    proposed_ids = {e.place_id for e in patch.edits if e.place_id} if patch else set()
    accepted = result.status.startswith("ACCEPTED")
    adopted_ids = {a.source_place_id for d in result.final.days for a in d.activities}
    preparation = result.candidate_preparation
    if result.model_attempted and preparation:
        for row in preparation.authorizations:
            history.append(
                dict(
                    place_id=row.place_id,
                    target_id=row.target_id,
                    date=str(row.date),
                    operation=row.operation,
                    round_index=round_index,
                    windows=row.opportunity_windows,
                    signature=row.opportunity_signature,
                    evidence_refs=row.evidence_refs,
                    outcome="selected"
                    if accepted and row.place_id in proposed_ids and row.place_id in adopted_ids
                    else "proposed_not_adopted"
                    if row.place_id in proposed_ids
                    else "not_selected",
                )
            )
    if not accepted and result.proposed is not None and patch and not result.components:
        before = {a.activity_id: a for d in result.original.days for a in d.activities}
        changed = {
            a.activity_id: a
            for d in result.proposed.days
            for a in d.activities
            if a.activity_id not in before or a != before[a.activity_id]
        }
        facts = []
        if result.proposed_report:
            facts.extend(
                (f.activity_ids, f.check, f.evidence_refs)
                for f in result.proposed_report.findings
                if f.status == "CONFIRMED" and f.check in {"opening", "route", "overlap"}
            )
        facts.extend(
            (
                (leg["from_activity_id"], leg["to_activity_id"]),
                "spatial_policy",
                tuple(leg.get("evidence_refs", ())),
            )
            for leg in result.spatial.get("legs", ())
            if leg.get("reasons")
        )
        for ids, check, refs in facts:
            for aid in ids:
                if aid not in changed:
                    continue
                a = changed[aid]
                record = dict(
                    place_id=a.source_place_id,
                    date=str(a.start_time.date()),
                    start=a.start_time.isoformat(),
                    end=a.end_time.isoformat(),
                    activity_id=aid,
                    related_activity_ids=list(ids),
                    check=check,
                    mode=result.scope.travel_mode,
                    routing_preference=result.scope.routing_preference,
                    target_ids=sorted(
                        {
                            row.target_id
                            for row in preparation.authorizations
                            if row.place_id == a.source_place_id and row.date == a.start_time.date()
                        }
                    )
                    if preparation
                    else [],
                    evidence_refs=list(refs),
                )
                if record not in records:
                    records.append(record)
    for component in result.components:
        if component["status"] != "rejected" or not component.get("proposal"):
            continue
        changed = {
            a["activity_id"]: a
            for d in component["proposal"]["days"]
            for a in d["activities"]
            if a["activity_id"] in component.get("changed_activity_ids", ())
        }
        facts = [
            (f["activity_ids"], f["check"], f["evidence_refs"])
            for f in (component.get("report") or {}).get("findings", [])
            if f["status"] == "CONFIRMED" and f["check"] in {"opening", "route", "overlap"}
        ]
        facts += [
            (
                [leg["from_activity_id"], leg["to_activity_id"]],
                "spatial_policy",
                leg.get("evidence_refs", []),
            )
            for leg in (component.get("spatial") or {}).get("legs", [])
            if leg.get("reasons")
        ]
        for ids, check, refs in facts:
            for aid in ids:
                if aid not in changed:
                    continue
                a = changed[aid]
                transfer = next(
                    (
                        t
                        for t in component["proposal"].get("transfers", [])
                        if t["from_activity_id"] in ids and t["to_activity_id"] in ids
                    ),
                    {},
                )
                record = dict(
                    place_id=a["source_place_id"],
                    date=a["start_time"][:10],
                    start=datetime.fromisoformat(a["start_time"]).isoformat(),
                    end=datetime.fromisoformat(a["end_time"]).isoformat(),
                    activity_id=aid,
                    related_activity_ids=list(ids),
                    check=check,
                    evidence_refs=list(refs),
                    mode=transfer.get("mode", result.scope.travel_mode or "WALK"),
                    routing_preference=transfer.get(
                        "routing_preference", result.scope.routing_preference
                    ),
                    target_ids=sorted(
                        {
                            row.target_id
                            for row in preparation.authorizations
                            if row.place_id == a["source_place_id"]
                            and str(row.date) == a["start_time"][:10]
                        }
                    )
                    if preparation
                    else [],
                )
                if record not in records:
                    records.append(record)
    budget.presentation_history, budget.conflict_records = history, records
    return result.model_copy(
        update=dict(
            feedback_kind=feedback_kind(result),
            presentation_history=tuple(history),
            conflict_records=tuple(records),
        )
    )
