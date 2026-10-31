"""Pure trip-duration capacities for the revised V1-A candidate funnel."""

from dataclasses import dataclass
from datetime import date, timedelta

from backend.app.policies.trip_dates import (
    MAX_TRIP_DAYS,
    TripDateWindow,
    validate_requested_trip_dates,
)
from backend.app.runtime.budget import ToolBudgetLimits


@dataclass(frozen=True)
class POICapacities:
    trip_days: int
    c_raw: int
    r_pool: int
    k_final: int
    review_pool_cap: int


@dataclass(frozen=True)
class EffectivePOICapacities:
    """Preserve algorithmic maxima alongside explicit operating-budget reductions."""

    algorithmic: POICapacities
    c_raw: int
    r_pool: int
    k_final: int
    review_pool_cap: int
    limiting_budgets: tuple[str, ...]


def derive_poi_capacities(
    start_date: date, end_date: date, window: TripDateWindow
) -> POICapacities:
    """Derive maximum pool sizes only after shared date validation."""

    validate_requested_trip_dates(start_date, end_date, window)
    days = (end_date - start_date).days + 1
    if not 1 <= days <= MAX_TRIP_DAYS:
        raise ValueError("trip duration must be inside the supported 1-10 day horizon")
    k_final = min(16, 2 * days + 2)
    r_pool = max(10, k_final + 2)
    return POICapacities(
        trip_days=days,
        c_raw=max(20, 2 * r_pool),
        r_pool=r_pool,
        k_final=k_final,
        review_pool_cap=min(6, (k_final + 2) // 3),
    )


def apply_poi_operating_budgets(
    capacities: POICapacities, limits: ToolBudgetLimits
) -> EffectivePOICapacities:
    """Make deliberate runtime reductions visible without rewriting the formula."""

    c_raw = min(capacities.c_raw, limits.max_candidates)
    r_pool = min(capacities.r_pool, limits.max_place_detail_calls, c_raw)
    k_final = min(capacities.k_final, limits.max_final_pois, r_pool)
    review_pool_cap = min(
        capacities.review_pool_cap,
        limits.max_review_enriched_places,
        limits.max_review_detail_calls,
        limits.max_experience_profile_llm_calls,
        r_pool,
    )
    reductions = (
        ("c_raw", c_raw, capacities.c_raw),
        ("r_pool", r_pool, capacities.r_pool),
        ("k_final", k_final, capacities.k_final),
        ("review_pool_cap", review_pool_cap, capacities.review_pool_cap),
    )
    return EffectivePOICapacities(
        algorithmic=capacities,
        c_raw=c_raw,
        r_pool=r_pool,
        k_final=k_final,
        review_pool_cap=review_pool_cap,
        limiting_budgets=tuple(name for name, actual, maximum in reductions if actual < maximum),
    )


def quality_capacities(start_date, end_date, window, required=0):
    """Quality-first effective goals, independently of the user's monetary budget."""
    validate_requested_trip_dates(start_date, end_date, window)
    if required > 16:
        from backend.app.schemas.interpreted_requirements import ClarificationRequired

        raise ClarificationRequired("required_capacity_conflict")
    days = (end_date - start_date).days + 1
    normal = min(16, max(8, 2 * days + 6))
    acquisition_k = max(normal, required)
    k = max(acquisition_k, 2 * days)
    values = POICapacities(
        days, max(48, 4 * acquisition_k), 2 * acquisition_k, k,
        min(8, (acquisition_k + 1) // 2),
    )
    return EffectivePOICapacities(
        values, values.c_raw, values.r_pool, k, values.review_pool_cap, ()
    )


def acceptance_capacities(contract, window, limits, required=0):
    """Reserve alternatives for sourced visit demand; supply is never a visit quota."""
    from backend.app.policies.category_visits import required_category_visit
    from backend.app.policies.daily_visit_constraints import hard_count_floor, hard_exact_count
    from backend.app.services.generation_resources import GenerationResourceError
    from backend.pace_policy import zero_penalty_counts

    request = contract.requirements
    validate_requested_trip_dates(request.start_date, request.end_date, window)
    days = (request.end_date - request.start_date).days + 1
    if required > limits.max_final_pois:
        raise GenerationResourceError("required_identity_supply_limit")
    pace = {row.date: row for row in contract.daily_pace or ()}
    demand = 0
    for index in range(days):
        day = request.start_date + timedelta(days=index)
        if any(
            row.status == "fixed" and row.full_day is True and (not row.dates or day in row.dates)
            for row in contract.time_protections or ()
        ):
            continue
        policy = pace.get(day, pace.get(None))
        exact = hard_exact_count(contract, day)
        target = exact if exact is not None else min(
            zero_penalty_counts(policy.profile, policy.exact_count) if policy else (), default=2
        )
        demand += max(target, hard_count_floor(contract, day))
    obligations = sum(
        row.experience_goal.count or 1
        for row in contract.semantic_requirements if required_category_visit(row)
    )
    # Named identities and category obligations may be disjoint until evidence proves otherwise.
    demand = max(demand, obligations + required)
    target = min(limits.max_final_pois, max(8, demand + max(6, (demand + 2) // 3)))
    values = POICapacities(
        days, min(limits.max_candidates, max(48, 4 * target)),
        min(limits.max_place_detail_calls, 2 * target), target,
        min(limits.max_review_enriched_places, (target + 1) // 2),
    )
    return apply_poi_operating_budgets(values, limits)
