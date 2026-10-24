"""Direct bounded candidate supply; no model judgment, weights or subset search."""

from collections import Counter
from math import asin, ceil, cos, radians, sin, sqrt
from time import perf_counter, process_time

from pydantic import BaseModel, ConfigDict, Field

from backend.app.policies.category_visits import category_visit_target, required_category_visit
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.schemas.landmark_nomination import LandmarkIdentity


class SupplyCandidate(BaseModel):
    """Source-neutral facts and typed discovery links, without provider rank."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    place_id: str
    primary_type: str | None
    rating: float | None
    latitude: float
    longitude: float
    intent_ids: tuple[str, ...] = ()
    landmark_nomination: LandmarkIdentity | None = None


class ProfileRelation(BaseModel):
    requirement_id: str
    dimension: str
    relation: str
    value: str | None = None
    confidence: str | None = None
    evidence_refs: tuple[str, ...] = ()


class PlanningSupplyResult(BaseModel):
    landmarks: dict[str, LandmarkIdentity] = Field(default_factory=dict)
    nomination_diagnostics: dict = Field(default_factory=dict)
    acquisition_diagnostics: dict = Field(default_factory=dict)
    selected_place_ids: tuple[str, ...]
    required_canonical_ids: tuple[str, ...]
    optional_canonical_ids: tuple[str, ...]
    normal_capacity: int
    effective_capacity: int
    eligible_count: int
    shortfall: int
    selection_steps: tuple[dict, ...]
    profile_relations: dict[str, tuple[ProfileRelation, ...]]
    elapsed_seconds: float
    cpu_seconds: float
    evaluator_calls: int = 0
    subset_enumerator_calls: int = 0


def profile_relations(contract, profiles, place_id):
    """Only interpreted directional targets and validated review signals can relate."""
    profile = profiles.get(place_id)
    signals = (
        {s.dimension: s for s in profile.signals}
        if profile and profile.availability.value in {"available", "partial"}
        else {}
    )
    relations = []
    for request in sorted(
        contract.experience_evidence_requests, key=lambda r: (r.requirement_id, r.dimension)
    ):
        signal = signals.get(request.dimension)
        preferred = getattr(request, "preferred_values", ())
        avoided = getattr(request, "avoided_values", ())
        relation = "unknown"
        if signal is not None and (preferred or avoided):
            relation = (
                "conflict"
                if signal.value in avoided
                else "alignment"
                if signal.value in preferred
                else "neutral"
            )
        relations.append(
            ProfileRelation(
                requirement_id=request.requirement_id,
                dimension=request.dimension.value,
                relation=relation,
                value=signal.value.value if signal else None,
                confidence=signal.confidence.value if signal else None,
                evidence_refs=signal.review_refs if signal else (),
            )
        )
    return tuple(relations)


def _distance(candidate, destination):
    lat1, lon1 = map(radians, (candidate.latitude, candidate.longitude))
    lat2, lon2 = map(radians, destination)
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return round(12742000 * asin(sqrt(min(1.0, max(0.0, a)))))


def soft_opportunity_limits(contract):
    """Keep one replacement beyond each final soft target; never a category cap."""
    from backend.app.schemas.interpreted_requirements import soft_coverage_eligible

    return {
        r.requirement_id: (r.soft_coverage.target if r.soft_coverage else 1) + 1
        for r in contract.semantic_requirements
        if soft_coverage_eligible(r)
    }


def nomination_allowed(place, contract, judgment, required):
    """Optional nominations cannot expand explicit scopes or primary permissions."""
    if not place.landmark_nomination or place.candidate.place_id in required:
        return True
    exclusive = {
        r.requirement_id
        for r in contract.semantic_requirements
        if r.polarity == "favor"
        and r.experience_goal
        and r.experience_goal.trip_scope == "exclusive"
    }
    exclusions = {
        r.requirement_id
        for r in contract.semantic_requirements
        if r.polarity == "avoid" and r.kind == "constraint"
    }
    supported = (
        {m.requirement_id for m in judgment.matches if m.relation == "supported"}
        if judgment
        else set()
    )
    return not supported.intersection(exclusions) and (
        not exclusive or bool(exclusive.intersection(supported))
    )


def select_planning_supply(
    candidates,
    contract,
    *,
    required_ids,
    excluded_ids,
    capacity,
    hard_capacity,
    destination_coordinates,
    profiles=None,
    semantic_assessments=None,
    semantic_config=None,
):
    """Fill capacity after round-robin subject opportunity; soft signals never exclude.

    Inputs must already have passed the canonical factual gate. Missing ratings
    abstain: rating breaks a tied cohort only when every member has a rating.
    """
    wall, cpu = perf_counter(), process_time()
    if capacity < 0 or hard_capacity < capacity:
        raise ValueError("Invalid planning supply capacities")
    required, excluded = set(required_ids), set(excluded_ids)
    by_id = {c.place_id: c for c in candidates if c.place_id not in excluded}
    if required & excluded or not required <= set(by_id):
        raise ClarificationRequired("required_place_ineligible")
    if len(required) > hard_capacity:
        raise ClarificationRequired("required_capacity_conflict")
    effective = max(capacity, len(required))
    target = min(effective, len(by_id))
    chosen = sorted(required)
    profiles = profiles or {}
    relations = {pid: profile_relations(contract, profiles, pid) for pid in sorted(by_id)}
    requirements = {r.requirement_id: r for r in contract.semantic_requirements}
    # Subject first: several interests from one traveler must not consume a round.
    buckets = {}
    for intent in sorted(contract.discovery_intents, key=lambda d: d.intent_id):
        subjects = {
            s
            for ref in intent.requirement_refs
            if requirements[ref].polarity == "favor"
            for s in requirements[ref].subject_refs
        }
        members = {
            pid
            for pid, c in by_id.items()
            if (
                any(
                    m.requirement_id in intent.requirement_refs and m.relation == "supported"
                    for m in semantic_assessments[pid].matches
                )
                if semantic_assessments is not None
                else intent.intent_id in c.intent_ids
            )
        }
        for subject in subjects:
            buckets[(subject, intent.intent_id)] = members
    soft_limits = soft_opportunity_limits(contract)
    supported_by_requirement = {
        ref: {
            pid
            for pid, c in by_id.items()
            if (
                any(
                    m.requirement_id == ref and m.relation == "supported"
                    for m in semantic_assessments[pid].matches
                )
                if semantic_assessments is not None
                else any(
                    d.intent_id in c.intent_ids and ref in d.requirement_refs
                    for d in contract.discovery_intents
                )
            )
        }
        for ref in soft_limits
    }
    intent_refs = {d.intent_id: set(d.requirement_refs) for d in contract.discovery_intents}
    subject_turns = Counter()
    intent_turns = Counter()
    types = Counter(by_id[pid].primary_type for pid in chosen if by_id[pid].primary_type)
    steps = [{"place_id": pid, "reason": "required"} for pid in chosen]

    def priority(pid):
        rows = relations[pid]
        # One requirement cannot earn multiple rewards through several dimensions.
        conflicts = {r.requirement_id for r in rows if r.relation == "conflict"}
        aligned = {r.requirement_id for r in rows if r.relation == "alignment"}
        aligned -= conflicts | saturated
        category = by_id[pid].primary_type
        repeated = types[category] if category else 0
        landmark = by_id[pid].landmark_nomination
        return (
            len(conflicts),
            -len(aligned),
            0 if landmark else 1,
            repeated,
            landmark.rank if landmark else 0,
        )

    while len(chosen) < target:
        remaining = set(by_id) - set(chosen)
        if semantic_assessments is not None:
            exception_counts = Counter(
                ref for pid in chosen for ref in semantic_assessments[pid].exception_requirement_ids
            )
            remaining = {
                pid
                for pid in remaining
                if not semantic_assessments[pid].exception_requirement_ids
                or any(
                    exception_counts[ref]
                    < semantic_config.exception_alternatives
                    * (requirements[ref].experience_goal.count or 1)
                    if ref in requirements
                    else exception_counts[ref] < semantic_config.exception_alternatives
                    for ref in semantic_assessments[pid].exception_requirement_ids
                )
            }
        if not remaining:
            break
        saturated = {
            ref
            for ref, limit in soft_limits.items()
            if len(supported_by_requirement[ref] & set(chosen)) >= limit
        }
        active = {}
        for key, members in buckets.items():
            pending_refs = intent_refs[key[1]] - saturated
            options = members & remaining
            if semantic_assessments is not None:
                options = {
                    pid
                    for pid in options
                    if any(
                        m.requirement_id in pending_refs and m.relation == "supported"
                        for m in semantic_assessments[pid].matches
                    )
                }
            if pending_refs and options:
                active[key] = options
        saturated_members = set().union(*(supported_by_requirement[r] for r in saturated))
        independent = {pid for pid in remaining if by_id[pid].landmark_nomination}
        independent |= remaining - saturated_members
        if active:
            key = min(active, key=lambda k: (subject_turns[k[0]], k[0], intent_turns[k], k[1]))
            cohort = active[key]
        else:
            key, cohort = None, independent or remaining
        count_options = set()
        hard_count_options = set()
        if semantic_assessments is not None:
            for req in requirements.values():
                goal = req.experience_goal
                category_target = category_visit_target(req)
                if not goal or (category_target is None and (
                    req.polarity != "favor" or goal.frequency not in {"exact", "minimum"}
                )):
                    continue
                supported = {
                    pid
                    for pid in by_id
                    if any(
                        m.requirement_id == req.requirement_id and m.relation == "supported"
                        for m in semantic_assessments[pid].matches
                    )
                }
                needed = category_target if category_target is not None else 1
                if len(supported & set(chosen)) < needed:
                    count_options.update(supported & remaining)
                    if required_category_visit(req):
                        hard_count_options.update(supported & remaining)
        count_options = hard_count_options or count_options
        if count_options:
            if key and cohort & count_options:
                cohort &= count_options
            else:
                key, cohort = None, count_options
        elif semantic_assessments is not None and not any(
            r.experience_goal and r.experience_goal.trip_scope == "exclusive"
            for r in requirements.values()
        ):
            # Once a sourced one-off bucket has an option, diversify its remaining opportunities.
            fresh = {pid for pid in remaining if by_id[pid].primary_type not in types}
            favored = {r.requirement_id for r in requirements.values() if r.polarity == "favor"}
            general = {
                pid
                for pid in remaining
                if not any(
                    m.requirement_id in favored and m.relation == "supported"
                    for m in semantic_assessments[pid].matches
                )
            }
            general |= {pid for pid in remaining if by_id[pid].landmark_nomination}
            explored = len(chosen) - len(required)
            due = ceil((explored + 1) * semantic_config.exploration_fraction) > ceil(
                explored * semantic_config.exploration_fraction
            )
            if due and general:
                key, cohort = None, (general & fresh) or general
            elif fresh and (due or (key and intent_turns[key] > 0)):
                key, cohort = None, fresh
        best = min(priority(pid) for pid in cohort)
        tied = {pid for pid in cohort if priority(pid) == best}
        rated = all(by_id[pid].rating is not None for pid in tied)
        if rated:
            highest = max(by_id[pid].rating for pid in tied)
            tied = {pid for pid in tied if by_id[pid].rating == highest}
        pid = min(tied, key=lambda p: (_distance(by_id[p], destination_coordinates), p))
        chosen.append(pid)
        if by_id[pid].primary_type:
            types[by_id[pid].primary_type] += 1
        if key:
            subject_turns[key[0]] += 1
            intent_turns[key] += 1
        steps.append(
            {
                "place_id": pid,
                "reason": "discovery_opportunity" if key else "eligible_fill",
                "subject_intent": key,
                "priority": best,
                "rating_compared": rated,
                "destination_distance_metres": _distance(by_id[pid], destination_coordinates),
            }
        )
    return PlanningSupplyResult(
        selected_place_ids=tuple(chosen),
        required_canonical_ids=tuple(sorted(required)),
        optional_canonical_ids=tuple(pid for pid in chosen if pid not in required),
        normal_capacity=capacity,
        effective_capacity=effective,
        eligible_count=len(by_id),
        shortfall=max(0, effective - len(chosen)),
        selection_steps=tuple(steps),
        profile_relations=relations,
        elapsed_seconds=perf_counter() - wall,
        cpu_seconds=process_time() - cpu,
    )
