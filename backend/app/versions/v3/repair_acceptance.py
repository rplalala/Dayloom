"""Atomic patch application and comparisons using the existing validator."""

from dataclasses import replace
from datetime import timedelta

from backend.app.observability.progress import observed
from backend.app.policies.visit_multiplicity import is_primary_visit
from backend.app.schemas.itinerary import Activity, ItineraryDay
from backend.app.versions.v3.repair_models import RepairComparison, TargetProgress
from backend.app.versions.v3.repair_obligations import (
    bind_visits,
    removed_obligation,
    route_chain_value,
)
from backend.app.versions.v3.soft_pace import pace_coverage_floor
from backend.app.versions.v3.validation import validate_draft


def coverage_unavailable(row):
    """Quantity applicability is independent of known primary identity and coverage."""
    return row.unclassified_activity_count > 0 or row.minimum_coverage == "unknown"


@observed("validation")
def assess(itinerary, context, whitelist=(), evidence=(), transitions=None):
    whitelist = (*context.identity_ledger, *whitelist)
    places = {p.place_id: p for p in context.places}
    places.update({c.place.place_id: c.place for c in whitelist})
    ids = tuple(
        dict.fromkeys((*context.original_supply_ids, *(c.place.place_id for c in whitelist)))
    )
    report = validate_draft(
        itinerary,
        context.contract,
        window=context.window,
        supplied_ids=ids,
        original_supply_ids=context.original_supply_ids,
        places=tuple(places.values()),
        named_resolutions=context.named_resolutions,
        effective_places=context.effective_places,
        policy=context.policy,
        schedule=context.schedule,
        visit_bindings=bind_visits(itinerary, context),
        semantic_assessments=context.semantic_assessments,
        route_evidence=(*context.route_evidence, *evidence),
        transitions=context.transitions if transitions is None else transitions,
    )

    from backend.app.versions.v3.models import Finding, ImprovementTarget

    findings = list(report.findings)
    targets = list(report.improvement_targets)
    for related in context.active_related:
        permission = related.permission
        row = next(r for r in report.diagnostics.days if r.date == permission.date)
        if row.distinct_main_poi_count < permission.minimum_count:
            status = "UNKNOWN" if coverage_unavailable(row) else "NEEDS_REVIEW"
            findings.append(
                Finding(
                    finding_id=permission.target_id,
                    check="coverage",
                    status=status,
                    reason="conditional_coverage_deficit",
                    dates=(permission.date,),
                    magnitude=permission.minimum_count,
                )
            )
            if status == "NEEDS_REVIEW":
                targets.append(
                    ImprovementTarget(finding_id=permission.target_id, basis="review_policy")
                )
    result = report.model_copy(
        update={"findings": tuple(findings), "improvement_targets": tuple(targets)}
    )
    from backend.app.observability.mechanism_observation import rule_selections

    rule_selections(result)
    return result


def validate_scope(original, report, scope):
    targets = {t.finding_id for t in report.improvement_targets}
    if not set(scope.target_ids) <= targets:
        raise ValueError("Target was not authorized by validation policy")
    if not set(scope.dates) <= {
        original.start_date + timedelta(days=i)
        for i in range((original.end_date - original.start_date).days + 1)
    }:
        raise ValueError("Scope date is outside the trip")
    activities = {a.activity_id: (d.date, a) for d in original.days for a in d.activities}
    scheduled_ids = {a.source_place_id for _, a in activities.values() if a.source_place_id}
    if not {r.place_id for r in scope.revisits} <= scheduled_ids:
        raise ValueError("Revisit authorization requires an existing scheduled identity")
    for permission in scope.permissions:
        if permission.activity_id not in activities:
            raise ValueError("Unknown permission identity")
        if activities[permission.activity_id][0] not in scope.dates:
            raise ValueError("Permission lies outside authorized dates")


def apply_patch(
    original,
    patch,
    scope,
    preparation,
    required_ids=(),
    excluded_ids=(),
    *,
    id_prefix="repair_new",
    context=None,
):
    """No free-form activity replacement: the application owns names, roles and IDs."""
    result = original.model_copy(deep=True)
    allowed = {c.place.place_id: c.place for c in preparation.ledger}
    presented = {c.place.place_id for c in preparation.input_candidates}
    authorized = {
        (a.operation, a.date, a.place_id)
        for a in preparation.authorizations
        if a.target_id in set(scope.target_ids) | {p.target_id for p in scope.coverage_permissions}
    }
    scheduled = {
        a.source_place_id for d in original.days for a in d.activities if a.source_place_id
    }
    revisits = {(r.place_id, r.date) for r in scope.revisits}
    added_ids = set()
    permissions = {p.activity_id: p for p in scope.permissions}
    originals = {a.activity_id: (d.date, a) for d in original.days for a in d.activities}
    changes, additions, touched, lost = {}, {}, set(), []
    for index, edit in enumerate(patch.edits):
        if edit.date not in scope.dates:
            raise ValueError("Unauthorized date")
        if edit.operation == "add":
            if edit.activity_id is not None or edit.date not in scope.add_dates:
                raise ValueError("Addition is not authorized")
            aid = f"{id_prefix}_{index + 1}"
            if aid in originals:
                raise ValueError("Allocated activity ID collision")
            if (
                "add",
                edit.date,
                edit.place_id,
            ) not in authorized or edit.place_id not in presented:
                raise ValueError(
                    "Addition identity is not a presented target/date option or is excluded"
                )
            if (
                edit.place_id in scheduled | added_ids
                and (edit.place_id, edit.date) not in revisits
            ):
                raise ValueError("Revisit is not authorized")
            added_ids.add(edit.place_id)
            previous = None
        else:
            if edit.activity_id not in originals or edit.activity_id in touched:
                raise ValueError("Unknown or repeated activity edit")
            day, previous = originals[edit.activity_id]
            permission = permissions.get(edit.activity_id)
            if (
                permission is None
                or edit.operation not in permission.operations
                or (day != edit.date and edit.operation != "move")
            ):
                raise ValueError("Unauthorized operation")
            if previous.activity_kind == "free_time" and not is_primary_visit(
                previous, context.semantic_assessments if context else ()
            ):
                raise ValueError("Placeholders may only be adjusted by the application")
            if edit.operation == "move" and (
                day != permission.source_date
                or edit.date not in permission.move_dates
                or abs((edit.date - day).days) != 1
            ):
                raise ValueError("Move exceeds original adjacent-date authorization")
            touched.add(edit.activity_id)
            aid = edit.activity_id
        if edit.operation == "delete":
            if any(v is not None for v in (edit.place_id, edit.start_time, edit.end_time)):
                raise ValueError("Deletion cannot carry replacement fields")
            if context is None and previous.source_place_id in required_ids:
                raise ValueError("Cannot delete a REQUIRED visit")
            changes[aid] = None
            if is_primary_visit(previous, context.semantic_assessments if context else ()):
                lost.append(aid)
            continue
        if edit.start_time is None or edit.end_time is None:
            raise ValueError("Scheduled edits require both timestamps")
        if edit.start_time.date() != edit.date or edit.end_time.date() != edit.date:
            raise ValueError("Cross-day edits are not supported")
        if previous is not None:
            if (previous.start_time.utcoffset() is None) != (edit.start_time.utcoffset() is None):
                raise ValueError("Cannot change timestamp awareness")
            if (
                not permission.allow_duration_change
                and edit.end_time - edit.start_time != previous.end_time - previous.start_time
            ):
                raise ValueError("Duration change is not authorized")
        if edit.operation in {"retime", "move"}:
            if edit.place_id is not None:
                raise ValueError("Retime cannot change identity")
            values = previous.model_dump()
        else:
            if (
                edit.place_id not in allowed
                or edit.place_id in excluded_ids
                or edit.place_id not in presented
                or (edit.operation, edit.date, edit.place_id) not in authorized
            ):
                raise ValueError("Identity is outside the repair whitelist or excluded")
            if previous is not None and (
                (context is None and previous.source_place_id in required_ids)
                or not is_primary_visit(previous, context.semantic_assessments if context else ())
            ):
                raise ValueError("Cannot replace a REQUIRED or non-main activity")
            if (
                previous is not None
                and edit.place_id != previous.source_place_id
                and edit.place_id in scheduled | added_ids
                and (edit.place_id, edit.date) not in revisits
            ):
                raise ValueError("Replacement revisit is not authorized")
            added_ids.add(edit.place_id)
            p = allowed[edit.place_id]
            values = dict(
                activity_id=aid,
                activity_kind="main_poi",
                title=p.name,
                place_name=p.name,
                source_place_id=p.place_id,
                location=p.formatted_address,
                estimated_cost=None,
                notes=None,
            )
            if previous is not None and previous.source_place_id != p.place_id:
                lost.append(aid)
        if (
            previous is not None
            and previous.notes
            and (
                edit.start_time != previous.start_time
                or edit.end_time != previous.end_time
                or (edit.place_id is not None and edit.place_id != previous.source_place_id)
            )
        ):
            prefix = (
                "Historical note from the pre-repair activity; "
                "not revalidated for this arrangement: "
            )
            values["notes"] = (
                previous.notes if previous.notes.startswith(prefix) else prefix + previous.notes
            )
        updated = Activity.model_validate(
            {**values, "start_time": edit.start_time, "end_time": edit.end_time}
        )
        if previous is None:
            additions.setdefault(edit.date, []).append(updated)
        elif edit.operation == "move":
            changes[aid] = None
            additions.setdefault(edit.date, []).append(updated)
        else:
            changes[aid] = updated
    days = {d.date: d.model_copy(deep=True) for d in result.days}
    for day in days.values():
        day.activities = [
            changes.get(a.activity_id, a)
            for a in day.activities
            if changes.get(a.activity_id, a) is not None
        ]
    for day, items in additions.items():
        if day not in days:
            days[day] = ItineraryDay(date=day)
        days[day].activities.extend(items)
    # Preserve protected array positions. Temporal order is represented by timestamps;
    # only sort days, whose ordering is already a shared invariant.
    result.days = [days[d] for d in sorted(days)]
    if hasattr(result, "set_cost_projections"):
        # Preserve path attribution for retained costs; removed/replaced observations
        # remain on the immutable original snapshot rather than pointing at another visit.
        old_paths = {
            f"days[{di}].activities[{ai}].estimated_cost": a
            for di, d in enumerate(original.days)
            for ai, a in enumerate(d.activities)
        }
        new_paths = {
            a.activity_id: f"days[{di}].activities[{ai}].estimated_cost"
            for di, d in enumerate(result.days)
            for ai, a in enumerate(d.activities)
        }
        current = {a.activity_id: a for d in result.days for a in d.activities}
        result.set_cost_projections(
            tuple(
                replace(p, field_path=new_paths[a.activity_id])
                for p in original.cost_projections
                if (a := old_paths.get(p.field_path)) is not None
                and a.activity_id in current
                and current[a.activity_id].source_place_id == a.source_place_id
                and current[a.activity_id].estimated_cost == a.estimated_cost
            )
        )
    type(result).model_validate(result.model_dump())
    if context is not None:
        from backend.app.versions.v3.repair_targets import check_blank_windows, protect_visits

        protect_visits(original, result, context)
        if scope.direct_add_dates is not None:
            from backend.app.versions.v3.repair_targets import related_progress

            active_dates = {
                r.permission.date
                for r in related_progress(
                    original, result, scope, context.schedule, context.semantic_assessments
                )
            }
            if any(
                e.operation == "add" and e.date not in set(scope.direct_add_dates) | active_dates
                for e in patch.edits
            ):
                raise ValueError("Conditional addition has no activating edit")
        check_blank_windows(original, result, context)
    if context and context.semantic_assessments:
        from backend.app.policies.poi_semantic_output import goal_progress, semantic_policy_issues

        before_goals = {
            r["requirement_id"]: r
            for r in goal_progress(original, context.contract, context.semantic_assessments)
        }
        for row in goal_progress(result, context.contract, context.semantic_assessments):
            requirement = next(
                r
                for r in context.contract.semantic_requirements
                if r.requirement_id == row["requirement_id"]
            )
            if row.get("soft") and requirement.experience_goal.frequency == "continuing":
                continue
            previous = before_goals[row["requirement_id"]]
            # Preserve the existing one-off safeguard without protecting a new focus target.
            expected = 1 if row.get("soft") else row["expected"]
            if min(row["matched"], expected) < min(previous["matched"], expected):
                raise ValueError("Sourced experience goal satisfaction decreased")

        old = semantic_policy_issues(
            original, context.contract, context.semantic_assessments, context.named_resolutions
        )
        new = semantic_policy_issues(
            result, context.contract, context.semantic_assessments, context.named_resolutions
        )

        def issue_key(row):
            return tuple(
                row.get(k) for k in ("reason", "requirement_id", "activity_id", "place_id")
            )

        prior = {issue_key(row): row for row in old}
        if any(
            row["reason"] not in {"unauthorized_repeat", "visit_multiplicity_unassessed"}
            and (
                issue_key(row) not in prior
                or row.get("excess", row.get("shortfall", 1))
                > prior[issue_key(row)].get("excess", prior[issue_key(row)].get("shortfall", 1))
            )
            for row in new
        ):
            raise ValueError("Patch violates primary role, exception or multiplicity authorization")
    return result, tuple(lost)


def finding_key(f):
    if f.check == "soft_pace":
        return f.check, f.dates
    if f.reason == "minimum_daily_coverage_missing":
        return "minimum_coverage", f.dates
    if f.reason == "conditional_coverage_deficit":
        return "related", f.finding_id
    if f.check == "opening":
        return f.check, f.activity_ids, f.place_ids
    if f.check == "repetition":
        return f.check, f.place_ids
    if f.check == "primary_policy" and f.requirement_ids:
        return f.check, f.reason, f.requirement_ids
    if f.reason == "experience_goal_count_unmet":
        return f.check, f.reason, f.requirement_ids
    return f.check, tuple(sorted(f.activity_ids)), f.dates, f.place_ids, f.requirement_ids


def severity(f, itinerary):
    if f.reason == "minimum_daily_coverage_missing":
        return f.magnitude
    if f.check == "overlap":
        items = {a.activity_id: a for d in itinerary.days for a in d.activities}
        if not set(f.activity_ids) <= items.keys():
            return 0.0
        a, b = (items[i] for i in f.activity_ids)
        try:
            return max(
                0, (min(a.end_time, b.end_time) - max(a.start_time, b.start_time)).total_seconds()
            )
        except TypeError:
            return None
    if f.check == "named_requirement":
        return 1.0 if f.status == "CONFIRMED" else 0.0 if f.status == "PASS" else None
    if f.check in {"route", "opening", "repetition", "primary_policy"}:
        return f.magnitude
    if f.reason == "experience_goal_count_unmet":
        return f.magnitude
    return None


def compare(
    original,
    proposed,
    initial_report,
    reassessed,
    after,
    scope,
    schedule=None,
    context=None,
    *,
    allow_soft_exploration=False,
):
    """Evidence-only gains cannot qualify as schedule improvement."""
    old = {finding_key(f): f for f in reassessed.findings}
    new = {finding_key(f): f for f in after.findings}
    from backend.app.versions.v3.repair_targets import related_progress, repeat_excess

    assessments = context.semantic_assessments if context else ()
    related = related_progress(original, proposed, scope, schedule, assessments)
    permitted = {
        r.permission.date
        for r in related
        if r.permission.allow_partial
        and r.permission.reason in {"excluded_removal", "confirmed_visit_removal"}
    }
    rejections = []
    for f in initial_report.findings:
        if f.status == "CONFIRMED":
            updated = old.get(finding_key(f))
            if updated is None or updated.status in {"UNKNOWN", "NEEDS_REVIEW"}:
                rejections.append("Original confirmed evidence weakened during reassessment")
    for key, f in new.items():
        if f.status != "CONFIRMED":
            continue
        before = old.get(key)
        if before is None or before.status != "CONFIRMED":
            # Scoped hard-obligation removal may leave a visible coverage debt.
            # The loss-specific regression check below still rejects other losses.
            if (
                f.reason == "minimum_daily_coverage_missing"
                and f.dates
                and set(f.dates) <= permitted
            ):
                continue
            rejections.append("New confirmed conflict")
            continue
        left, right = severity(before, original), severity(f, proposed)
        if left is None or right is None or right > left:
            rejections.append("Worsened or incomparable confirmed conflict")
    for key, f in old.items():
        if (
            f.status == "CONFIRMED"
            and key in new
            and new[key].status in {"UNKNOWN", "NEEDS_REVIEW"}
            and not (f.check in {"opening", "route"} and removed_obligation(f, original, proposed))
        ):
            rejections.append("Confirmed conflict downgraded to uncertainty")
    for finding in old.values():
        if finding.check != "route" or finding.status != "CONFIRMED":
            continue
        if removed_obligation(finding, original, proposed):
            continue
        if route_chain_value(finding, original, proposed, after, schedule) is None:
            rejections.append("Confirmed route dependency replaced by an unverified chain")
    before_days = {r.date: r for r in reassessed.diagnostics.days}
    regressions = tuple(
        r.date
        for r in after.diagnostics.days
        if r.distinct_main_poi_count < before_days[r.date].distinct_main_poi_count
    )
    for day in regressions:
        before = before_days[day]
        current = next(r for r in after.diagnostics.days if r.date == day)
        old_ids = {
            a.source_place_id
            for d in original.days
            if d.date == day
            for a in d.activities
            if is_primary_visit(a, assessments)
        }
        new_ids = {
            a.source_place_id
            for d in proposed.days
            if d.date == day
            for a in d.activities
            if is_primary_visit(a, assessments)
        }
        excluded = inclusion_ids(context)[1] if context else set()
        conflict_removals = {
            pid
            for r in related
            if r.permission.date == day
            and r.permission.reason == "confirmed_visit_removal"
            and r.permission.allow_partial
            for pid in r.permission.removable_place_ids
        }
        allowed_loss = (
            len((old_ids - new_ids) & (excluded | conflict_removals)) if day in permitted else 0
        )
        floor = min(scope.daily_main_min, before.distinct_main_poi_count - allowed_loss)
        for f in initial_report.findings:
            if f.check == "soft_pace" and f.finding_id in scope.target_ids and day in f.dates:
                floor = pace_coverage_floor(
                    floor,
                    before.distinct_main_poi_count - allowed_loss,
                    f.adopted_evidence.get("zero_counts", ()),
                )
        if coverage_unavailable(current) or current.distinct_main_poi_count < floor:
            rejections.append("Coverage regression is not authorized")
    if any(
        f.check in {"repetition", "overfull"} and f.finding_id in scope.target_ids
        for f in initial_report.findings
    ):
        if any(
            r.distinct_main_poi_count
            > max(scope.daily_main_max, before_days[r.date].distinct_main_poi_count)
            for r in after.diagnostics.days
        ):
            rejections.append("Review operation creates or worsens an overfull date")
    if any(r.status != "resolved" and not r.permission.allow_partial for r in related):
        rejections.append("Review compensation must succeed atomically")
    for pid in {
        a.source_place_id for d in proposed.days for a in d.activities if a.source_place_id
    }:
        if repeat_excess(proposed, pid, context) > repeat_excess(
            original, pid, context
        ) and not any(r.place_id == pid for r in scope.revisits):
            rejections.append("New or reintroduced excess repeat")
    progress = []
    business_values = []
    originals = {f.finding_id: f for f in initial_report.findings}
    comparable = {
        finding_key(f): f
        for f in initial_report.findings
        if f.check == "soft_pace" and f.magnitude is not None
    }
    comparable.update(
        {k: f for k, f in old.items() if f.check == "soft_pace" and f.magnitude is not None}
    )
    for key in comparable:
        if old.get(key) is None or old[key].magnitude is None:
            rejections.append("Lost comparable soft pace evidence")
        else:
            current = new.get(key)
            if current is None or current.magnitude is None:
                rejections.append("Lost comparable soft pace evidence")
    before_pace = [
        old[finding_key(f)]
        for f in initial_report.findings
        if f.check == "soft_pace" and f.magnitude is not None and finding_key(f) in old
    ]
    after_pace = [new.get(finding_key(f)) for f in before_pace]
    pace_improved = (
        bool(before_pace)
        and all(f.magnitude is not None for f in before_pace)
        and all(f is not None and f.magnitude is not None for f in after_pace)
        and sum(f.magnitude for f in after_pace) < sum(f.magnitude for f in before_pace)
    )
    for target in scope.target_ids:
        f = originals[target]
        key = finding_key(f)
        baseline = old.get(key)
        outcome, left, right = "unknown", None, None
        if f.check in {"coverage", "overfull"}:
            day = f.dates[0]
            a = before_days[day]
            b = next(r for r in after.diagnostics.days if r.date == day)
            coverage_target = f.reason in {
                "conditional_coverage_deficit",
                "minimum_daily_coverage_missing",
            }
            if (
                not coverage_unavailable(a) and not coverage_unavailable(b)
                if coverage_target
                else "not_assessable" not in (a.target_status, b.target_status)
            ):

                def distance(n, finding=f):
                    return max(
                        (
                            int(finding.magnitude)
                            if finding.reason
                            in {"conditional_coverage_deficit", "minimum_daily_coverage_missing"}
                            else scope.daily_main_min
                        )
                        - n,
                        n - scope.daily_main_max,
                        0,
                    )

                left, right = (
                    distance(a.distinct_main_poi_count),
                    distance(b.distinct_main_poi_count),
                )
        elif f.check == "soft_pace":
            current = new.get(key)
            left = baseline.magnitude if baseline else None
            right = current.magnitude if current else None
        elif f.check == "primary_policy" or f.reason == "experience_goal_count_unmet":
            left = f.magnitude
            right = max(
                (
                    r.magnitude or 0
                    for r in after.findings
                    if r.status == "CONFIRMED"
                    and r.check == f.check
                    and r.reason == f.reason
                    and (
                        r.requirement_ids == f.requirement_ids
                        if f.requirement_ids
                        else bool(set(r.activity_ids) & set(f.activity_ids))
                    )
                ),
                default=0,
            )
        elif f.check == "repetition":
            left = repeat_excess(original, f.place_ids[0], context)
            right = repeat_excess(proposed, f.place_ids[0], context)
        elif f.check in {"opening", "route"} and baseline is not None:
            left = severity(baseline, original)
            if removed_obligation(f, original, proposed):
                right = 0.0
            elif f.check == "route":
                right = route_chain_value(f, original, proposed, after, schedule)
            else:
                current = new.get(key)
                right = (
                    severity(current, proposed)
                    if current is not None and current.status in {"PASS", "CONFIRMED"}
                    else None
                )
        elif baseline is not None:
            left = severity(baseline, original)
            current = new.get(key)
            if current is not None:
                right = severity(current, proposed)
            elif f.check == "overlap":
                right = severity(f, proposed)
        if left is not None and right is not None:
            outcome = (
                "resolved"
                if left > 0 and right == 0
                else ("improved" if right < left else "unresolved")
            )
        business_values.append(
            {
                "finding_id": target,
                "check": f.check,
                "obligation_removed": removed_obligation(f, original, proposed)
                if f.check in {"opening", "route"}
                else False,
                "meaning": "conflict_obligation_removed_not_new_facts_verified"
                if f.check in {"opening", "route"} and removed_obligation(f, original, proposed)
                else "comparable_business_condition",
                "before": left,
                "after": right,
                "before_distinct_main": a.distinct_main_poi_count
                if f.check in {"coverage", "overfull"}
                else None,
                "after_distinct_main": b.distinct_main_poi_count
                if f.check in {"coverage", "overfull"}
                else None,
            }
        )
        progress.append(
            TargetProgress(
                finding_id=target, check=f.check, outcome=outcome, before=left, after=right
            )
        )
    exploring_pace = allow_soft_exploration and any(
        f.check == "soft_pace" and f.finding_id in scope.target_ids for f in initial_report.findings
    )
    if not exploring_pace and not any(
        p.outcome in {"resolved", "improved"} and (p.check != "soft_pace" or pace_improved)
        for p in progress
    ):
        rejections.append("No verifiable arrangement improvement")
    if original.model_dump() == proposed.model_dump():
        rejections.append("Evidence or binding changes alone are not arrangement improvement")
    return RepairComparison(
        accepted=not rejections,
        reason="; ".join(rejections) if rejections else "verifiable_arrangement_improvement",
        progress=tuple(progress),
        coverage_regressions=regressions,
        business_values=tuple(business_values),
    )


def inclusion_ids(context):
    required, excluded = set(), set()
    requirements = {r.requirement_id: r for r in context.contract.named_places}
    for binding in context.named_resolutions:
        r = requirements.get(binding.search_intent_id)
        if r and binding.resolved_place_id and binding.status == "resolved":
            if r.inclusion == "REQUIRED":
                required.add(binding.resolved_place_id)
            elif r.inclusion == "EXCLUDED":
                excluded.add(binding.resolved_place_id)
    return required, excluded
