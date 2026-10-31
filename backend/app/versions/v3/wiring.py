"""Application scope policy and finalization over the Step 1/2 contracts."""

import json
from collections import Counter, defaultdict
from copy import deepcopy
from time import monotonic

from backend.app.observability.run_trace import redact_secrets
from backend.app.policies.itinerary_output import validate_output_sources
from backend.app.policies.trip_dates import create_trip_date_window, validate_itinerary_dates
from backend.app.services.reference_discovery import attach_references
from backend.app.versions.v3.models import ValidationPolicy
from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_models import ActivityPermission, RepairScope, ValidationContext
from backend.app.versions.v3.repair_routes import bind_transitions
from backend.app.versions.v3.repair_service import run_repair_stage
from backend.app.versions.v3.soft_pace import pace_coverage_floor
from backend.app.versions.v3.state import V3Outcome


def operation_scope(draft, report, *, mode=None, context=None, policy=None):
    """Application-owned B operations and conditional local coverage permissions."""
    from backend.app.versions.v3.repair_budget import configured_policy
    from backend.app.versions.v3.repair_models import CoveragePermission
    from backend.app.versions.v3.repair_targets import movable, repeat_excess

    policy = policy or configured_policy()
    permissions = defaultdict(set)
    dates, additions, targets = set(), set(), []
    all_dates = {r.date for r in report.diagnostics.days}
    activities = {a.activity_id: (d.date, a) for d in draft.days for a in d.activities}
    rows = {r.date: r for r in report.diagnostics.days}
    eligible = {t.finding_id for t in report.improvement_targets}

    def uncertain_binding(aid):
        if context is None:
            return False
        day, activity = activities[aid]
        for finding in report.findings:
            if (
                finding.check != "named_requirement"
                or finding.reason != "missing_or_inconsistent_identity_binding"
            ):
                continue
            for rid in finding.requirement_ids:
                specs = [
                    v for v in context.contract.visit_requirements or () if v.requirement_id == rid
                ]
                if specs and all(v.dates and day not in v.dates for v in specs):
                    continue
                named = next(
                    (n for n in context.contract.named_places if n.requirement_id == rid), None
                )
                matches = [r for r in context.named_resolutions if r.search_intent_id == rid]
                if (
                    named is None
                    or len(matches) != 1
                    or matches[0].named_place_intent.place_text != named.place_text
                    or matches[0].named_place_intent.source_text
                    not in {r.quote for r in named.source_refs}
                    or not matches[0].matching_place_ids
                ):
                    return True  # No trustworthy scope: retain protection.
                if activity.source_place_id in matches[0].matching_place_ids:
                    return True
        return False

    dependent = []
    move_destinations = defaultdict(set)
    direct_additions = set()
    revisits = []
    for f in sorted(
        report.findings,
        key=lambda row: (row.status != "CONFIRMED", row.check != "named_requirement"),
    ):
        if f.finding_id not in eligible:
            continue
        selected = []
        if f.check == "daily_visit_count" and f.status == "CONFIRMED":
            from backend.app.versions.v3.repair_targets import dispensable_visit

            dates.update(f.dates)
            if f.adopted_evidence["upper"] < f.adopted_evidence["count"]:
                additions.update(f.dates)
                direct_additions.update(f.dates)
            else:
                selected = [
                    aid
                    for aid in f.activity_ids
                    if aid in activities
                    and not uncertain_binding(aid)
                    and (context is None or dispensable_visit(draft, aid, context))
                ]
                for aid in selected:
                    permissions[aid].add("delete")
        elif f.check == "overlap" and f.status == "CONFIRMED":
            for aid in f.activity_ids:
                if (
                    activities[aid][1].activity_kind != "free_time"
                    and activities[aid][1].time_use != "free_window"
                ):
                    permissions[aid].add("retime")
                dates.add(activities[aid][0])
        elif f.reason in {
            "required_identity_omitted",
            "required_visit_obligation_unmet",
            "experience_goal_count_unmet",
        }:
            additions.update(all_dates)
            direct_additions.update(all_dates)
            dates.update(all_dates)
            if f.reason == "required_visit_obligation_unmet":
                from backend.app.versions.v3.repair_models import RevisitPermission

                revisits.extend(
                    RevisitPermission(place_id=pid, date=day)
                    for pid in f.place_ids
                    for day in all_dates
                )
        elif f.reason == "excluded_identity_scheduled":
            selected = [
                aid for aid, (_, a) in activities.items() if a.source_place_id in f.place_ids
            ]
            for aid in selected:
                permissions[aid].add("delete")
        elif f.check in {"opening", "route"} and f.status == "CONFIRMED":
            from backend.app.versions.v3.repair_targets import dispensable_visit

            selected = [
                aid
                for aid in f.activity_ids
                if aid in activities and activities[aid][1].activity_kind == "main_poi"
            ]
            for aid in selected:
                permissions[aid].add("retime")
                if (
                    context
                    and context.contract.visit_requirements is not None
                    and not uncertain_binding(aid)
                    and dispensable_visit(draft, aid, context)
                ):
                    permissions[aid].update({"replace", "delete"})
        elif f.check == "soft_pace" and f.status == "NEEDS_REVIEW":
            from backend.app.versions.v3.repair_targets import dispensable_visit

            zero_counts = f.adopted_evidence.get("zero_counts", ())
            count = f.adopted_evidence.get("count")
            if not zero_counts or count is None:
                continue
            if count < min(zero_counts):
                additions.update(f.dates)
                direct_additions.update(f.dates)
                dates.update(f.dates)
            elif count > max(zero_counts):
                if context is None or context.contract.visit_requirements is None:
                    continue
                selected = [
                    aid
                    for aid in f.activity_ids
                    if aid in activities
                    and not uncertain_binding(aid)
                    and dispensable_visit(draft, aid, context)
                ]
                if not selected:
                    continue
                for aid in selected:
                    permissions[aid].add("delete")
            else:
                continue
        elif f.check == "coverage" and (
            f.status == "NEEDS_REVIEW" or f.reason == "minimum_daily_coverage_missing"
        ):
            applicable = set(f.dates)
            if context and context.schedule:
                from backend.app.versions.v3.repair_schedule import subtract

                existing = {d.date for d in draft.days if d.activities}
                blank = {w.start.date(): w for w in context.schedule.blank_windows}
                applicable = {
                    d
                    for d in applicable
                    if d in existing
                    or (
                        d in blank
                        and subtract(
                            blank[d].start,
                            blank[d].end,
                            [(w.start, w.end) for w in context.schedule.fixed],
                        )
                    )
                }
            if not applicable:
                continue
            additions.update(applicable)
            direct_additions.update(applicable)
            dates.update(applicable)
        elif f.check == "primary_policy" and f.status == "CONFIRMED":
            selected = [aid for aid in f.activity_ids if not uncertain_binding(aid)]
            for aid in selected:
                if f.reason != "experience_goal_dates_unmet":
                    permissions[aid].update({"delete", "replace"})
        elif f.check == "repetition":
            if context and (
                context.contract.visit_requirements is None
                or not repeat_excess(draft, f.place_ids[0], context)
            ):
                continue
            selected = [aid for aid in f.activity_ids if not uncertain_binding(aid)]
            for aid in selected:
                permissions[aid].update({"delete", "replace"})
        elif f.check == "overfull":
            selected = [
                aid
                for aid, (day, a) in activities.items()
                if day in f.dates and a.activity_kind == "main_poi"
            ]
            if context and context.contract.visit_requirements is None:
                continue
            selected = [aid for aid in selected if not uncertain_binding(aid)]
            for aid in selected:
                permissions[aid].add("delete")
        else:
            continue
        for aid in selected:
            day, a = activities[aid]
            dates.add(day)
            if (
                (
                    f.check
                    in {
                        "repetition",
                        "overfull",
                        "opening",
                        "route",
                        "soft_pace",
                        "daily_visit_count",
                    }
                    or f.reason == "experience_goal_dates_unmet"
                )
                and not uncertain_binding(aid)
                and movable(a, context)
            ):
                destinations = {
                    d for d in all_dates if 0 < abs((d - day).days) <= policy.move_max_days
                }
                if destinations:
                    permissions[aid].add("move")
                    move_destinations[aid].update(destinations)
                    dates.update(destinations)
        for day in {activities[aid][0] for aid in selected}:
            ids = tuple(aid for aid in selected if activities[aid][0] == day)
            removable = tuple(
                activities[aid][1].source_place_id for aid in ids if "delete" in permissions[aid]
            )
            c_removal = (
                f.check in {"opening", "route"} and f.status == "CONFIRMED" and bool(removable)
            )
            partial = f.reason == "excluded_identity_scheduled" or c_removal
            dependent.append(
                CoveragePermission(
                    target_id=f"related:{f.finding_id}:{day}",
                    parent_id=f.finding_id,
                    date=day,
                    trigger_activity_ids=ids,
                    minimum_count=(0 if f.adopted_evidence["count"] == 0 else 1)
                    if f.check == "daily_visit_count"
                    else pace_coverage_floor(
                        policy.daily_main_min,
                        rows[day].distinct_main_poi_count,
                        f.adopted_evidence.get("zero_counts", ()) if f.check == "soft_pace" else (),
                    ),
                    allow_partial=partial,
                    reason="confirmed_visit_removal"
                    if c_removal
                    else "excluded_removal"
                    if partial
                    else "review_compensation",
                    removable_place_ids=removable if c_removal else (),
                )
            )
            additions.add(day)
        targets.append(f.finding_id)
    if not targets:
        return None
    return RepairScope(
        dates=tuple(sorted(dates)),
        add_dates=tuple(sorted(additions)),
        direct_add_dates=tuple(sorted(direct_additions)),
        target_ids=tuple(targets),
        permissions=tuple(
            ActivityPermission(
                activity_id=aid,
                operations=frozenset(ops),
                source_date=activities[aid][0],
                move_dates=tuple(sorted(move_destinations[aid])),
            )
            for aid, ops in sorted(permissions.items())
        ),
        coverage_permissions=tuple(dependent),
        revisits=tuple(revisits),
        travel_mode=mode,
        daily_main_min=policy.daily_main_min,
        daily_main_max=policy.daily_main_max,
    )


def cost_records(itinerary):
    return tuple(p.as_trace_payload() for p in getattr(itinerary, "cost_projections", ()))


class V3PostPrimary:
    def __init__(
        self,
        model,
        acquisition,
        tracer,
        discovery,
        owner,
        deadline,
        quantity_review,
        *,
        clock=monotonic,
    ):
        self.model, self.acq, self.tracer = model, acquisition, tracer
        self.discovery, self.owner = discovery, owner
        self.deadline, self.quantity_review = deadline, quantity_review
        self.clock = clock

    async def __call__(self, state):
        draft = state["itinerary"].model_copy(deep=True)
        initial_rag = deepcopy(self.discovery.finalize(state))
        # Detach initial-phase aliased runtime diagnostics before the borrowed next phase.
        self.discovery.report = deepcopy(self.discovery.report)
        routes, official = state["route_evidence"], state.get("official_web_result")
        mode = state["transport_mode"].travel_mode.value
        mode = mode if mode in {"WALK", "TRANSIT", "DRIVE"} else None
        context = ValidationContext(
            semantic_assessments=state["review_selection"].semantic_assessments,
            contract=state["interpreted_requirements"],
            window=create_trip_date_window(state["reference_date"]),
            original_supply_ids=state["review_selection"].policy_result.selected_place_ids,
            places=tuple(state["place_evidence"]),
            named_resolutions=state["candidate_funnel"].named_place_resolutions,
            effective_places=official.effective_places if official else (),
            route_evidence=(routes.baseline, *routes.alternatives),
            transitions=bind_transitions(draft, mode),
            policy=ValidationPolicy(
                daily_main_min=self.acq.runtime_config.v3_repair.daily_main_min,
                daily_main_max=self.acq.runtime_config.v3_repair.daily_main_max,
                review_targets=frozenset(
                    (["coverage", "soft_pace"] if self.quantity_review else [])
                    + (
                        ["overfull"]
                        if self.acq.runtime_config.v3_repair.overfull_review_enabled
                        else []
                    )
                ),
            ),
        )
        from backend.app.versions.v3.repair_schedule import build_schedule

        context = context.model_copy(
            update={
                "schedule": build_schedule(
                    draft, context.contract, context.places, primary_generated=True
                )
            }
        )
        context = context.model_copy(
            update={
                "transitions": bind_transitions(
                    draft, mode, state["transport_mode"].routing_preference, context.schedule
                )
            }
        )
        from backend.app.versions.v3.repair_targets import prepare_blank_windows

        context = context.model_copy(
            update={
                "schedule": prepare_blank_windows(draft, context, self.acq.runtime_config.v3_repair)
            }
        )
        from backend.app.versions.v3.repair_obligations import bind_visits

        context = context.model_copy(update={"visit_bindings": bind_visits(draft, context)})
        original_report = assess(draft, context)
        scope = operation_scope(
            draft,
            original_report,
            mode=mode,
            context=context,
            policy=self.acq.runtime_config.v3_repair,
        )
        if scope is not None:
            decision = state["transport_mode"]
            scope = scope.model_copy(
                update={
                    "window_roots": tuple(
                        w.root_activity_id
                        for w in context.schedule.windows
                        if w.start.date() in scope.dates
                    ),
                    "routing_preference": decision.routing_preference,
                    "mode_source": decision.reason,
                    "allowed_transport_modes": None
                    if decision.allowed_modes is None
                    else tuple(m.value for m in decision.allowed_modes),
                    "unsupported_explicit_mode": decision.travel_mode.value
                    if decision.is_explicit and mode is None
                    else None,
                }
            )
        self.owner.phase = "repair"
        # Reuse existing intents only when a shortage authorizes additions.
        coverage_target = scope is not None and any(
            f.check in {"coverage", "soft_pace", "daily_visit_count"}
            and f.finding_id in scope.target_ids
            for f in original_report.findings
        )
        intent_ids = (
            tuple(
                i.intent_id
                for i in context.contract.discovery_intents[
                    : max(
                        self.acq.runtime_config.v3_repair.acquisition.google,
                        self.acq.runtime_config.v3_repair.acquisition.retrieval,
                    )
                ]
            )
            if scope and (coverage_target or scope.coverage_permissions)
            else ()
        )
        # An opt-in development observer cannot change planning or trigger retries.
        observer = getattr(self.model, "capture_repair_snapshot", None)
        if observer is not None:
            try:
                observer(
                    original=draft,
                    context=context,
                    scope=scope,
                    enriched=state["candidate_funnel"].enriched_candidates,
                    admitted=state["candidate_funnel"].admitted_candidates,
                    runtime=self.acq.runtime_config,
                    request_remaining=max(0, self.deadline - self.clock()),
                    cache=self.acq._cache,
                    semantic_service=getattr(self.acq, "poi_semantics", None),
                    geographic_scope=getattr(self.discovery, "scope", None),
                    intent_ids=intent_ids,
                )
            except Exception:
                pass
        repair = None
        if scope is None:
            from backend.app.observability.progress import skipped

            skipped("repair")
        if scope is not None:
            rich = state["candidate_funnel"].enriched_candidates
            rich_ids = {c.candidate.place_id for c in rich}
            pool = (
                *rich,
                *(
                    c
                    for c in state["candidate_funnel"].admitted_candidates
                    if c.candidate.place_id not in rich_ids
                ),
            )
            repair = await run_repair_stage(
                draft,
                context,
                scope,
                model=self.model,
                request_deadline=self.deadline,
                clock=self.clock,
                pool=pool,
                places_provider=self.acq._places,
                routes_provider=self.acq._routes,
                intent_ids=intent_ids,
                rag=self.owner,
                geographic_scope=getattr(self.discovery, "scope", None),
                cache=self.acq._cache,
                tracer=self.tracer,
                audit_max_bytes=self.acq.runtime_config.trace.max_payload_bytes,
                policy=self.acq.runtime_config.v3_repair,
                runtime_config=self.acq.runtime_config,
                semantic_service=getattr(self.acq, "poi_semantics", None),
                nearby_reserve=self.acq.runtime_config.reference_discovery.deadline_seconds,
            )
        chosen = repair.final if repair else draft
        whitelist = repair.repair_whitelist if repair else ()
        places = {p.place_id: p for p in context.places}
        places.update({c.place.place_id: c.place for c in whitelist})
        ids = tuple(
            dict.fromkeys((*context.original_supply_ids, *(c.place.place_id for c in whitelist)))
        )
        final = validate_output_sources(chosen, places=tuple(places.values()), supplied_ids=ids)
        validate_itinerary_dates(context.contract.requirements, final, context.window)
        final_context = context.model_copy(
            update={
                "places": tuple(places.values()),
                "semantic_assessments": repair.selected_semantic_assessments
                if repair is not None and repair.selected_semantic_assessments is not None
                else context.semantic_assessments,
                "schedule": repair.schedule if repair else context.schedule,
                "active_related": repair.related_targets if repair else (),
            }
        )
        final_report = assess(
            final,
            final_context,
            whitelist,
            repair.acquired_routes if repair else (),
            bind_transitions(
                final, mode, state["transport_mode"].routing_preference, final_context.schedule
            ),
        )
        from backend.app.versions.v3.repair_transport import present_transfers

        final = present_transfers(
            final,
            bind_transitions(
                final, mode, state["transport_mode"].routing_preference, final_context.schedule
            ),
            (*context.route_evidence, *(repair.acquired_routes if repair else ())),
            final_context.schedule,
            default_source="USER_EXPLICIT"
            if state["transport_mode"].is_explicit
            else "APPLICATION_DEFAULT_WALK",
            places=final_context.places,
        )
        from backend.app.policies.itinerary_schedule import ordered_activities
        from backend.app.services.initial_routes import leg_diagnostic, permitted_modes

        selected = {(t.from_activity_id, t.to_activity_id): t for t in final.transfers}
        route_diagnostics = [
            leg_diagnostic(
                left,
                right,
                permitted_modes(state["transport_mode"]),
                (*context.route_evidence, *(repair.acquired_routes if repair else ())),
                self.acq.runtime_config.transport or self.acq.runtime_config.v3_repair.spatial,
                final_context.schedule,
                state["transport_mode"],
                selected.get((left.activity_id, right.activity_id)),
            )
            for day in final.days
            for ordered in [ordered_activities(day, final_context.schedule)]
            for left, right in zip(ordered, ordered[1:], strict=False)
        ]
        final = final.model_copy(update={"route_diagnostics": route_diagnostics})
        from backend.app.versions.v3.soft_pace import pace_summary

        soft_pace = pace_summary(
            original_report,
            final_report,
            contract=final_context.contract,
            review_enabled=self.quantity_review,
            changed=repair is not None and repair.selected_round_index is not None,
        )
        completion = soft_pace["completion"]
        if repair and completion:
            repair = repair.model_copy(
                update={
                    "soft_pace": soft_pace,
                    "status": "ACCEPTED_PARTIAL"
                    if repair.status == "ACCEPTED_COMPLETE" and completion["status"] != "complete"
                    else repair.status,
                }
            )
        outcome = V3Outcome(
            soft_pace=soft_pace,
            review_policy={
                "quantity": self.quantity_review,
                "soft_pace": self.quantity_review,
                "overfull": self.acq.runtime_config.v3_repair.overfull_review_enabled,
            },
            quantity_review_enabled=self.quantity_review,
            draft=draft,
            original_report=original_report,
            scope=scope,
            repair=repair,
            final_primary=final.model_copy(deep=True),
            final_report=final_report,
            final_identity_ids=ids,
            final_places=tuple(places.values()),
            draft_cost_projections=cost_records(draft),
            final_cost_projections=cost_records(final),
            original_rag_discovery=initial_rag,
            reason=repair.reason if repair else "no_authorized_targets",
        )
        self.tracer.event("v3_completion_summary", {
            "reason": outcome.reason,
            "repair_status": repair.status if repair else "not_executed",
            "selected_round_index": repair.selected_round_index if repair else None,
            "pace_completion": completion,
            "validation_counts": dict(Counter(finding.status for finding in final_report.findings)),
            "unresolved_findings": [
                {"id": finding.finding_id, "check": finding.check, "status": finding.status,
                 "reason": finding.reason, "dates": finding.dates}
                for finding in final_report.findings if finding.status != "PASS"
            ][:50],
            "policy_completion": final_report.diagnostics.policy_completion,
            "policy_reasons": list(dict.fromkeys(
                row["reason"] for row in final_report.diagnostics.policy_issues
            )),
        })
        trace_outcome = redact_secrets(outcome.model_dump(mode="json"))
        trace_bytes = len(json.dumps(trace_outcome, ensure_ascii=True).encode("utf-8"))
        if trace_bytes > self.acq.runtime_config.trace.max_payload_bytes:
            trace_outcome = {
                "truncated": True,
                "original_bytes": trace_bytes,
                "reason": outcome.reason,
                "repair_status": repair.status if repair else "not_executed",
                "artifact_events": [
                    f"v3_repair_{name}"
                    for name in (
                        "scope",
                        "candidates",
                        "patch",
                        "proposal",
                        "comparison",
                        "decision",
                    )
                ]
                if repair
                else [],
            }
        self.tracer.event("v3_finalized", trace_outcome)
        return {
            "itinerary": final,
            "generation_diagnostics": final_report.diagnostics,
            "v3_outcome": outcome,
        }


def reference_node(service, tracer, deadline):
    async def discover(state):
        outcome = state["v3_outcome"]
        primary = state["itinerary"]
        result = await service.discover(
            primary,
            outcome.final_places,
            outcome.final_identity_ids,
            state["candidate_funnel"].excluded_place_ids,
            tuple(
                c.structured_evidence
                for c in state["candidate_funnel"].enriched_candidates
                if c.structured_evidence is not None
            ),
            request_deadline=deadline,
        )
        # Recheck only the attachment boundary; never apply primary source normalization here.
        checked = attach_references(
            primary,
            result.itinerary.reference_recommendations,
            result.ledger,
            [entry.anchor for entry in result.ledger.values()],
        )
        if checked.model_dump() != result.itinerary.model_dump() or (
            cost_records(result.itinerary) != outcome.final_cost_projections
        ):
            raise ValueError("Nearby changed adopted primary or cost associations")
        tracer.event("reference_discovery_completed", result.diagnostics)
        return {"itinerary": result.itinerary, "reference_discovery": result}

    return discover


def project_result(state):
    references = state.get("reference_discovery")
    return {
        "v3": state["v3_outcome"],
        "nearby_ledger": {k: v.model_dump(mode="json") for k, v in references.ledger.items()}
        if references
        else {},
        "nearby_diagnostics": references.diagnostics if references else {},
    }
