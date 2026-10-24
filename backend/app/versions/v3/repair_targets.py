"""B target dependencies and executable visit satisfaction, never text interpretation."""

from datetime import datetime

from backend.app.versions.v3.repair_models import RelatedTarget
from backend.app.versions.v3.repair_schedule import ordered_activities, subtract


def affected_activity_ids(itinerary, finding):
    """Use structured dependencies, never notes or a trip-wide date fallback."""
    return set(finding.activity_ids) | {
        a.activity_id
        for d in itinerary.days
        for a in d.activities
        if (
            finding.check in {"overfull", "soft_pace", "daily_visit_count"}
            and d.date in finding.dates
        )
        or (
            finding.reason == "excluded_identity_scheduled"
            and a.source_place_id in finding.place_ids
        )
    }


def localize_scope(
    itinerary,
    report,
    scope,
    active_ids,
    deferred=(),
    related=(),
    links=None,
    *,
    context=None,
    policy=None,
):
    """Intersect current target dependencies with the original operation authorization."""
    links = links or {}
    findings = [f for f in report.findings if f.finding_id in active_ids]
    activities = {a.activity_id: d.date for d in itinerary.days for a in d.activities}
    affected = set().union(*(affected_activity_ids(itinerary, f) for f in findings))
    permissions = tuple(p for p in scope.permissions if p.activity_id in affected)
    if deferred and context is not None:
        # Reuse the application operation policy: sharing an activity with a deferred
        # target must not lend that target's DELETE/REPLACE/MOVE permission.
        from backend.app.versions.v3.wiring import operation_scope

        active_report = report.model_copy(
            update={
                "improvement_targets": tuple(
                    t for t in report.improvement_targets if t.finding_id in active_ids
                )
            }
        )
        policy_scope = operation_scope(
            itinerary, active_report, context=context, policy=policy, mode=scope.travel_mode
        )
        allowed = {p.activity_id: p for p in policy_scope.permissions} if policy_scope else {}
        permissions = tuple(
            p.model_copy(
                update={
                    "operations": p.operations & allowed[p.activity_id].operations,
                    "move_dates": tuple(
                        d for d in p.move_dates if d in allowed[p.activity_id].move_dates
                    ),
                }
            )
            for p in permissions
            if p.activity_id in allowed and p.operations & allowed[p.activity_id].operations
        )
    original_active = {links.get(t, t) for t in active_ids}
    current_ids = {links.get(t, t): t for t in active_ids}
    removal_ids = {
        p.activity_id for p in permissions if p.operations & {"replace", "delete", "move"}
    }
    active_children = {r.permission.target_id for r in related if r.status != "resolved"}
    coverage = tuple(
        p.model_copy(update={"parent_id": current_ids.get(p.parent_id, p.parent_id)})
        for p in scope.coverage_permissions
        if (
            p.parent_id in original_active and any(a in removal_ids for a in p.trigger_activity_ids)
        )
        or p.target_id in active_children.intersection(active_ids)
    )
    direct = set()
    for f in findings:
        if f.check in {"coverage", "soft_pace", "daily_visit_count"}:
            direct.update(f.dates)
        elif f.reason in {
            "required_identity_omitted",
            "required_visit_obligation_unmet",
            "experience_goal_count_unmet",
        }:
            # Named omissions have explicit application authorization across these dates.
            direct.update(
                f.dates
                or (
                    scope.direct_add_dates
                    if scope.direct_add_dates is not None
                    else scope.add_dates
                )
            )
    direct.intersection_update(
        scope.direct_add_dates if scope.direct_add_dates is not None else scope.add_dates
    )
    addition_dates = direct | {p.date for p in coverage}
    dates = addition_dates | {
        activities[p.activity_id] for p in permissions if p.activity_id in activities
    }
    dates.update(d for p in permissions for d in p.move_dates)
    dates.update(d for f in findings for d in f.dates)
    roots = scope.window_roots
    if context is not None and context.schedule is not None:
        roots = tuple(
            r
            for r in roots
            if any(
                w.root_activity_id == r and w.start.date() in dates
                for w in context.schedule.windows
            )
        )
    return scope.model_copy(
        update={
            "window_roots": roots,
            "target_ids": tuple(active_ids),
            "deferred_review_target_ids": tuple(deferred),
            "active_related": tuple(related),
            "coverage_permissions": coverage,
            "permissions": permissions,
            "dates": tuple(d for d in scope.dates if d in dates),
            "add_dates": tuple(d for d in scope.add_dates if d in addition_dates),
            "direct_add_dates": tuple(d for d in scope.add_dates if d in direct),
            "revisits": tuple(r for r in scope.revisits if r.date in addition_dates),
        }
    )


def visit_rules(context):
    named = {r.requirement_id: r for r in context.contract.named_places}
    resolved = {}
    for binding in context.named_resolutions:
        n = named.get(binding.search_intent_id)
        if (
            n
            and binding.status == "resolved"
            and binding.resolved_place_id
            and sum(b.search_intent_id == n.requirement_id for b in context.named_resolutions) == 1
            and binding.matching_place_ids == (binding.resolved_place_id,)
            and binding.named_place_intent.place_text == n.place_text
            and binding.named_place_intent.source_text in {r.quote for r in n.source_refs}
        ):
            resolved[n.requirement_id] = binding.resolved_place_id
    rules = []
    for n in named.values():
        pid = resolved.get(n.requirement_id)
        if pid and n.inclusion == "REQUIRED":
            rules.append((pid, 1, (), context.contract.visit_requirements is None))
    for v in context.contract.visit_requirements or ():
        pid = resolved.get(v.requirement_id)
        if pid:
            rules.append((pid, v.minimum_visits, v.dates, v.status == "unresolved"))
    return rules


def main_visits(itinerary, pid, assessments=()):
    from backend.app.policies.visit_multiplicity import is_primary_visit

    return [
        (d.date, a)
        for d in itinerary.days
        for a in d.activities
        if is_primary_visit(a, assessments) and a.source_place_id == pid
    ]


def protect_visits(original, proposed, context, *, protect_daily=True):
    from backend.app.policies.category_visits import protect_required_categories

    protect_required_categories(original, proposed, context.contract, context.semantic_assessments)
    if protect_daily:
        from backend.app.policies.daily_visit_constraints import protect_daily_visits

        protect_daily_visits(original, proposed, context.contract, context.semantic_assessments)
    for pid, count, dates, uncertain in visit_rules(context):
        before = main_visits(original, pid, context.semantic_assessments)
        after = main_visits(proposed, pid, context.semantic_assessments)
        from backend.app.versions.v3.repair_obligations import bind_visits, visit_binding

        modes = {
            v.access_mode
            for v in context.contract.visit_requirements or ()
            if v.access_mode
            and any(
                n.requirement_id == v.requirement_id
                and b.search_intent_id == n.requirement_id
                and b.resolved_place_id == pid
                for n in context.contract.named_places
                for b in context.named_resolutions
            )
        }
        if modes:
            old_bindings, new_bindings = (
                bind_visits(original, context),
                bind_visits(proposed, context),
            )
            before = [
                (d, a)
                for d, a in before
                if (binding := visit_binding(a, old_bindings)) and binding.mode in modes
            ]
            after = [
                (d, a)
                for d, a in after
                if (binding := visit_binding(a, new_bindings)) and binding.mode in modes
            ]

        if uncertain:
            retained = {a.activity_id: (day, a) for day, a in after}
            if any(
                a.activity_id not in retained
                or retained[a.activity_id][0] != day
                or retained[a.activity_id][1].source_place_id != pid
                for day, a in before
            ):
                raise ValueError(
                    "REQUIRED or explicit visit requirement is unassessed or unresolved"
                )
            continue
        if min(len(after), count) < min(len(before), count):
            raise ValueError("REQUIRED visit satisfaction decreased")
        for day in dates:
            if any(d == day for d, _ in before) and not any(d == day for d, _ in after):
                raise ValueError("Required visit date satisfaction decreased")


def repeat_excess(itinerary, pid, context=None):
    if context:
        from backend.app.policies.visit_multiplicity import excess_visits

        return (
            excess_visits(
                [a for _, a in main_visits(itinerary, pid, context.semantic_assessments)],
                context.contract,
                context.named_resolutions,
                pid,
            )
            or 0
        )
    count = max((n for p, n, _, _ in visit_rules(context) if p == pid), default=1) if context else 1
    return max(0, len(main_visits(itinerary, pid)) - count)


def movable(activity, context):
    if context is None:
        return True
    if context.contract.visit_requirements is None:
        return False
    return not any(
        pid == activity.source_place_id and (activity.start_time.date() in dates or uncertain)
        for pid, _, dates, uncertain in visit_rules(context)
    )


def prepare_blank_windows(itinerary, context, policy):
    from backend.app.policies.itinerary_schedule import prepare_blank_windows as shared_windows

    return shared_windows(itinerary, context, policy)


def check_blank_windows(original, proposed, context):
    if context.schedule is None:
        return
    old = {a.activity_id: a for d in original.days for a in d.activities}
    blank = {
        w.start.date(): w for w in (*context.schedule.day_windows, *context.schedule.blank_windows)
    }
    original_days = {d.date: d for d in original.days}
    for day in proposed.days:
        needs_window = (
            day.date in blank
            or day.date not in original_days
            or not original_days[day.date].activities
        )
        if not needs_window:
            continue
        for a in day.activities:
            if a == old.get(a.activity_id):
                continue
            w = blank.get(day.date)
            if (
                w is None
                or a.start_time.utcoffset() is None
                or not w.start <= a.start_time < a.end_time <= w.end
            ):
                raise ValueError("Blank date lacks an applicable authorized local window")


def related_progress(original, proposed, scope, schedule=None, semantic_assessments=()):
    from backend.app.policies.visit_multiplicity import is_primary_visit

    old = {a.activity_id: (d.date, a) for d in original.days for a in d.activities}
    new = {a.activity_id: (d.date, a) for d in proposed.days for a in d.activities}
    active = {r.permission.target_id: r for r in scope.active_related}
    for permission in scope.coverage_permissions:
        triggers = tuple(
            aid
            for aid in permission.trigger_activity_ids
            if aid in old
            and (
                aid not in new
                or old[aid][0] != new[aid][0]
                or old[aid][1].source_place_id != new[aid][1].source_place_id
            )
        )
        if not triggers and permission.target_id not in active:
            continue
        activities = [a for d in proposed.days if d.date == permission.date for a in d.activities]
        before = len(
            {
                a.source_place_id
                for d in original.days
                if d.date == permission.date
                for a in d.activities
                if is_primary_visit(a, semantic_assessments) and a.source_place_id
            }
        )
        after = len(
            {
                a.source_place_id
                for a in activities
                if is_primary_visit(a, semantic_assessments) and a.source_place_id
            }
        )
        uncertain = any(
            (a.activity_kind == "unknown" and not is_primary_visit(a, semantic_assessments))
            or (a.activity_kind == "main_poi" and not a.source_place_id)
            for a in activities
        )
        ordered = [
            a
            for d in proposed.days
            if d.date == permission.date
            for a in ordered_activities(d, schedule)
        ]
        prior = active.get(permission.target_id)
        active[permission.target_id] = RelatedTarget(
            permission=permission,
            activated_by=prior.activated_by if prior else triggers,
            before=prior.before if prior else before,
            after=after,
            affected_adjacency=tuple(
                (a.activity_id, b.activity_id) for a, b in zip(ordered, ordered[1:], strict=False)
            ),
            status="unknown"
            if uncertain
            else "resolved"
            if after >= permission.minimum_count
            else "unresolved",
        )
    return tuple(active.values())


def insertion_windows(itinerary, schedule, scope):
    from backend.app.versions.v3.repair_schedule import window_projection

    rows = window_projection(itinerary, schedule, scope.window_roots)
    if schedule is None:
        return rows
    for w in schedule.day_windows:
        if w.start.date() not in scope.dates:
            continue
        occupied = [(a.start_time, a.end_time) for d in itinerary.days for a in d.activities]
        occupied.extend((f.start, f.end) for f in schedule.fixed)
        occupied.extend(
            (datetime.fromisoformat(t["start"]), datetime.fromisoformat(t["end"]))
            for t in schedule.occupied_transfers
        )
        for start, end in subtract(w.start, w.end, occupied):
            rows.append(
                dict(
                    root_activity_id=w.root_activity_id,
                    fragment_id=None,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    source=w.source,
                )
            )
    return [r for r in rows if datetime.fromisoformat(r["start"]).date() in scope.dates]


def dispensable_visit(itinerary, activity_id, context):
    """Conditional permission only; the complete atomic patch is checked again."""
    trial = itinerary.model_copy(deep=True)
    for day in trial.days:
        day.activities = [a for a in day.activities if a.activity_id != activity_id]
    try:
        protect_visits(itinerary, trial, context, protect_daily=False)
    except ValueError:
        return False
    return True
