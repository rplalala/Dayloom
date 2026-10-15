"""Enforce sourced multiplicity without interpreting names or raw preferences."""


def is_primary_visit(activity, assessments=()):
    """Count assessed venue visits independently of model-authored role labels.

    Transport endpoints remain transit uses, and unlinked placeholders/references
    cannot acquire a canonical visit merely from their title.
    """
    return activity.activity_kind == "main_poi" or (
        activity.activity_kind != "transport"
        and any(
            row.place_id == activity.source_place_id and row.main_eligible for row in assessments
        )
    )


def visit_specs(contract, resolutions, place_id):
    refs = {
        b.search_intent_id
        for b in resolutions
        if b.status == "resolved"
        and b.resolved_place_id == place_id
        and b.matching_place_ids == (place_id,)
        and any(
            n.requirement_id == b.search_intent_id
            and n.place_text == b.named_place_intent.place_text
            and b.named_place_intent.source_text in {s.quote for s in n.source_refs}
            for n in contract.named_places
        )
    }
    return [v for v in contract.visit_requirements or () if v.requirement_id in refs]


def named_visit_issues(itinerary, contract, resolutions, assessments=()):
    """Expose sourced count/date obligations in shared output, including V1/V2."""
    if (
        contract.contract_version
        not in ("interpreted_requirements_4", "interpreted_requirements_5")
        or contract.visit_requirements is None
    ):
        return ()
    issues = []
    for named in contract.named_places:
        specs = [v for v in contract.visit_requirements if v.requirement_id == named.requirement_id]
        if named.inclusion == "EXCLUDED" or (named.inclusion != "REQUIRED" and not specs):
            continue
        bindings = [b for b in resolutions if b.search_intent_id == named.requirement_id]
        binding = bindings[0] if len(bindings) == 1 else None
        valid = (
            binding is not None
            and binding.status == "resolved"
            and binding.resolved_place_id
            and binding.matching_place_ids == (binding.resolved_place_id,)
            and binding.named_place_intent.place_text == named.place_text
            and binding.named_place_intent.source_text in {s.quote for s in named.source_refs}
        )
        reason = None
        if not valid:
            reason = "visit_requirement_unresolved"
        else:
            visits = [
                a
                for d in itinerary.days
                for a in d.activities
                if a.source_place_id == binding.resolved_place_id
                and is_primary_visit(a, assessments)
            ]
            dates = {a.start_time.date() for a in visits}
            if (named.inclusion == "REQUIRED" and not visits) or any(
                v.status == "executable"
                and (
                    len(visits) < v.minimum_visits
                    or (v.exact_visits is not None and len(visits) != v.exact_visits)
                    or (v.distinct_dates and len(dates) < v.minimum_visits)
                    or not set(v.dates) <= dates
                )
                for v in specs
            ):
                reason = "required_visit_obligation_unmet"
            elif any(v.status != "executable" for v in specs):
                reason = "visit_requirement_unresolved"
        if reason:
            issues.append({"reason": reason, "requirement_id": named.requirement_id})
    return tuple(issues)


def excess_visits(items, contract, resolutions, place_id):
    """None means unassessed intent; an explicit minimum is not an upper bound."""
    if (
        contract.contract_version
        not in ("interpreted_requirements_4", "interpreted_requirements_5")
        or contract.visit_requirements is None
    ):
        return None
    specs = visit_specs(contract, resolutions, place_id)
    if any(v.status != "executable" for v in specs):
        return None
    exact = [v.exact_visits for v in specs if v.exact_visits is not None]
    if exact:
        excess = max(0, len(items) - min(exact))
    elif any(v.minimum_visits > 1 for v in specs):
        excess = 0
    else:
        excess = max(0, len(items) - 1)
    if any(v.distinct_dates for v in specs):
        excess = max(excess, len(items) - len({a.start_time.date() for a in items}))
    return excess
