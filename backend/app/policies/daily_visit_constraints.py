"""Source-bound daily occurrence counts; no parsing of user prose or provider calls."""

from backend.app.policies.visit_multiplicity import is_primary_visit
from backend.app.schemas.interpreted_requirements import (
    ClarificationRequired,
    DailyPace,
    DailyVisitConstraint,
)
from backend.app.schemas.requirement_boundary import RequirementBoundaryError


def canonical_daily_constraints(draft, aliases, text, locate):
    if draft.daily_visit_constraints is None:
        return None
    result = []
    for rule in draft.daily_visit_constraints:
        if not set(rule.requirement_refs) <= aliases.keys():
            raise RequirementBoundaryError("unknown_daily_visit_reference")
        refs = tuple(sorted({aliases[r] for r in rule.requirement_refs}))
        result.append(
            DailyVisitConstraint(
                **rule.model_dump(exclude={"source_refs", "requirement_refs"}),
                constraint_id=f"daily_visit_{len(result) + 1}",
                requirement_refs=refs,
                source_refs=locate(rule.source_refs, text),
            )
        )
    return tuple(result)


def derived_pace(pace, constraints):
    """The numeric value has one owner; pace is only its optimization projection."""
    policies = {p.date: p for p in pace or ()}
    for p in policies.values():
        if p.exact_count is not None and not any(
            r.date == p.date
            and r.mode == "exact"
            and r.count == p.exact_count
            and set(r.source_refs) <= set(p.source_refs)
            for r in constraints
        ):
            raise RequirementBoundaryError("unbound_daily_pace_count")
    if None not in policies:
        policies[None] = DailyPace(date=None, profile="ordinary", exact_count=None, source_refs=())
    dates = {r.date for r in constraints if r.mode == "exact"}
    for day in sorted(dates):
        rules = [r for r in constraints if r.date == day and r.mode == "exact"]
        selected = next((r for r in rules if r.strength == "hard"), None)
        if selected is None and len({r.count for r in rules}) == 1:
            selected = rules[0]
        if selected is None:
            if day in policies:
                policies[day] = policies[day].model_copy(update={"exact_count": None})
            continue  # Conflicting soft wishes do not arbitrarily elect one numeric target.
        base = policies.get(day, policies[None])
        policies[day] = DailyPace(
            date=day,
            profile=base.profile,
            exact_count=selected.count,
            source_refs=tuple(
                sorted(
                    set(base.source_refs) | set(selected.source_refs),
                    key=lambda s: (s.start, s.end),
                )
            ),
        )
    return (policies[None], *[policies[d] for d in sorted(d for d in policies if d is not None)])


def validate_daily_contract(contract, request):
    semantics = {r.requirement_id: r for r in contract.semantic_requirements}
    rules = contract.daily_visit_constraints
    if rules is None:
        return
    if derived_pace(contract.daily_pace, rules) != contract.daily_pace:
        raise RequirementBoundaryError("invalid_daily_pace_projection")
    for index, rule in enumerate(rules, 1):
        if (
            rule.constraint_id != f"daily_visit_{index}"
            or not request.start_date <= rule.date <= request.end_date
        ):
            raise RequirementBoundaryError("invalid_daily_visit_scope")
        if len(set(rule.requirement_refs)) != len(rule.requirement_refs):
            raise RequirementBoundaryError("duplicate_daily_visit_reference")
        for ref in rule.requirement_refs:
            semantic = semantics.get(ref)
            if (
                semantic is None
                or semantic.subject_refs != ("party",)
                or semantic.kind not in {"constraint", "goal"}
                or semantic.polarity != "favor"
                or semantic.scope not in {"selected_poi_set", "whole_trip", "itinerary_style"}
                or (semantic.strength == "hard") != (rule.strength == "hard")
                or not set(semantic.source_refs) <= set(rule.source_refs)
            ):
                raise RequirementBoundaryError("invalid_daily_visit_binding")
    for day in {r.date for r in rules}:
        hard = [r for r in rules if r.date == day and r.strength == "hard"]
        lower = max((r.count for r in hard), default=0)
        exact = [r.count for r in hard if r.mode == "exact"]
        if exact and (len(set(exact)) != 1 or lower > exact[0]):
            raise ClarificationRequired(
                "daily_visit_constraint_conflict",
                tuple(sorted({ref for r in hard for ref in r.requirement_refs})),
            )
        if lower and any(
            p.status == "fixed" and p.full_day is True and (not p.dates or day in p.dates)
            for p in contract.time_protections or ()
        ):
            raise ClarificationRequired(
                "daily_visit_protected_day_conflict",
                tuple(sorted({ref for r in hard for ref in r.requirement_refs})),
            )


def daily_count_bounds(itinerary, day, assessments=()):
    states = {r.place_id: r for r in assessments}
    confirmed, potential = [], []
    for submitted in itinerary.days:
        for activity in submitted.activities:
            if activity.time_use == "free_window" or activity.activity_kind == "transport":
                continue
            state = states.get(activity.source_place_id)
            if state is not None and state.role == "non_main":
                continue
            primary = is_primary_visit(activity, assessments)
            unresolved = activity.time_use is None and (
                activity.activity_kind == "unknown"
                or (state is not None and state.role == "unresolved")
            )
            if not primary and not unresolved:
                continue
            consistent = (
                activity.start_time.date() == submitted.date
                and activity.end_time.date() == submitted.date
            )
            if consistent and submitted.date != day:
                continue
            uncertain = (
                not consistent
                or not primary
                or (bool(states) and (state is None or not state.main_eligible))
            )
            (potential if uncertain else confirmed).append(activity.activity_id)
    return tuple(confirmed), tuple(potential)


def assess_daily_visits(itinerary, contract, assessments=()):
    rows = []
    for rule in contract.daily_visit_constraints or ():
        confirmed, potential = daily_count_bounds(itinerary, rule.date, assessments)
        lower, upper = len(confirmed), len(confirmed) + len(potential)
        status = (
            ("PASS" if lower >= rule.count else "FAIL" if upper < rule.count else "UNKNOWN")
            if rule.mode == "minimum"
            else (
                "PASS"
                if lower == upper == rule.count
                else "FAIL"
                if lower > rule.count or upper < rule.count
                else "UNKNOWN"
            )
        )
        rows.append(
            {
                "constraint_id": rule.constraint_id,
                "date": rule.date,
                "count": rule.count,
                "mode": rule.mode,
                "strength": rule.strength,
                "lower": lower,
                "upper": upper,
                "status": status,
                "activity_ids": confirmed,
                "potential_activity_ids": potential,
                "requirement_ids": rule.requirement_refs,
                "source_refs": tuple(s.model_dump_json() for s in rule.source_refs),
            }
        )
    return tuple(rows)


def protect_daily_visits(original, proposed, contract, assessments=()):
    before = {r["constraint_id"]: r for r in assess_daily_visits(original, contract, assessments)}
    for after in assess_daily_visits(proposed, contract, assessments):
        old = before[after["constraint_id"]]
        if after["strength"] != "hard":
            continue
        if old["status"] == "PASS" and after["status"] != "PASS":
            raise ValueError("Satisfied daily visit constraint regressed")
        if old["status"] == "UNKNOWN" and after["status"] == "FAIL":
            raise ValueError("Uncertain daily visit constraint became violated")
        if old["status"] == "FAIL":

            def debt(row):
                return max(
                    0,
                    row["lower"] - row["count"] if row["mode"] == "exact" else 0,
                    row["count"] - row["upper"],
                )

            if after["status"] == "UNKNOWN" or debt(after) > debt(old):
                raise ValueError("Daily visit constraint worsened or became uncertain")


def hard_exact_count(contract, day):
    return next(
        (
            r.count
            for r in getattr(contract, "daily_visit_constraints", None) or ()
            if r.date == day and r.mode == "exact" and r.strength == "hard"
        ),
        None,
    )
