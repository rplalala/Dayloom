"""Bounded deterministic dependency partition, never a subset optimizer."""

from backend.app.versions.v3.repair_models import RepairPatch


def partition_patch(original, patch, report, scope):
    """Same-day edits share adjacency, windows and cumulative burden and stay atomic.

    New-candidate competition across dates is sequential, not a co-acceptance dependency.
    Existing visit obligations, moves and parent compensation connect affected dates.
    """
    items = {a.activity_id: a for d in original.days for a in d.activities}
    units = []
    for index, edit in enumerate(patch.edits):
        old = items.get(edit.activity_id)
        dates = {edit.date} | ({old.start_time.date()} if old else set())
        resources = {("date", str(d)) for d in dates}
        if old:
            resources.add(("activity", old.activity_id))
            if old.source_place_id:
                resources.add(("obligation", old.source_place_id))
            if old.estimated_cost is not None and edit.operation in {"delete", "replace"}:
                resources.add(("cost", "protected_associations"))
        for permission in scope.coverage_permissions:
            if edit.activity_id in permission.trigger_activity_ids or edit.date == permission.date:
                resources.add(("compensation", permission.parent_id))
        for f in report.findings:
            if f.finding_id in scope.target_ids and (
                edit.activity_id in f.activity_ids
                or set(f.dates) & dates
                or (old and old.source_place_id in f.place_ids)
            ):
                resources.add(("target", f.finding_id))
        units.append(({index}, resources))
    # At most 50 edits; transitive union is bounded and conservative.
    merged = []
    for indices, resources in units:
        again = True
        while again:
            again = False
            retained = []
            for prior, keys in merged:
                if resources & keys:
                    indices |= prior
                    resources |= keys
                    again = True
                else:
                    retained.append((prior, keys))
            merged = retained
        merged.append((indices, resources))
    priorities = {
        f.finding_id: 0
        if f.status == "CONFIRMED"
        else 1
        if f.reason == "conditional_coverage_deficit"
        else 2
        for f in report.findings
    }
    merged.sort(
        key=lambda row: (
            min((priorities.get(v, 2) for k, v in row[1] if k == "target"), default=2),
            min(row[0]),
        )
    )
    return tuple(
        (
            RepairPatch(edits=tuple(patch.edits[i] for i in sorted(indices))),
            tuple(sorted(indices)),
            tuple(sorted(resources)),
        )
        for indices, resources in merged
    )


async def accept_components(
    original,
    patch,
    initial,
    context,
    scope,
    preparation,
    evidence,
    places,
    provider,
    budget,
    stage_original,
    prefix,
    *,
    proposal_strategy="local",
):
    """Sequential acceptance with complete working-state checks and immutable evidence history."""
    import asyncio

    from backend.app.versions.v3.repair_acceptance import (
        apply_patch,
        assess,
        compare,
        finding_key,
        inclusion_ids,
    )
    from backend.app.versions.v3.repair_feedback import digest
    from backend.app.versions.v3.repair_routes import bind_transitions
    from backend.app.versions.v3.repair_schedule import check_time_permissions, consume_windows
    from backend.app.versions.v3.repair_spatial import check_addition_layout
    from backend.app.versions.v3.repair_transport import resolve_transfers

    required, excluded = inclusion_ids(context)
    working, schedule = original, context.schedule
    acquired, audits, adjustments, losses = [], [], [], []
    keys = {finding_key(f) for f in initial.findings if f.finding_id in scope.target_ids}
    original_bindings = bind_transitions(
        original, scope.travel_mode or "WALK", scope.routing_preference, context.schedule
    )
    latest_spatial = {}
    partitions = partition_patch(original, patch, initial, scope)
    for number, (component, indices, dependencies) in enumerate(partitions, 1):
        audit = dict(
            component_id=f"component_{number}",
            edit_indices=indices,
            dependencies=dependencies,
            status="not_attempted",
            proposal=None,
            comparison=None,
            report=None,
            spatial=None,
        )
        audit.update(
            input_state_sha256=digest(working.model_dump(mode="json")),
            budget_before=dict(budget.used),
        )
        component_started = budget.clock()
        audits.append(audit)
        if budget.remaining() <= 0 or budget.clock() >= budget.io_deadline:
            audit.update(
                reason="component_deadline", budget_after=dict(budget.used), elapsed_seconds=0
            )
            continue
        ctx = context.model_copy(update={"schedule": schedule})
        before = assess(
            working,
            ctx,
            preparation.ledger,
            (*evidence, *acquired),
            bind_transitions(
                working, scope.travel_mode or "WALK", scope.routing_preference, schedule
            ),
        )
        active_ids = tuple(f.finding_id for f in before.findings if finding_key(f) in keys)
        local_scope = scope.model_copy(update={"target_ids": active_ids})
        # Candidate authorizations refer to round-stable IDs, not renumbered reports.
        mapped = {
            f.finding_id: next(
                (g.finding_id for g in before.findings if finding_key(g) == finding_key(f)),
                f.finding_id,
            )
            for f in initial.findings
        }
        local_preparation = preparation.model_copy(
            update={
                "authorizations": tuple(
                    a.model_copy(update={"target_id": mapped.get(a.target_id, a.target_id)})
                    for a in preparation.authorizations
                )
            }
        )
        try:
            async with asyncio.timeout(
                max(0, min(budget.remaining(), budget.io_deadline - budget.clock()))
            ):
                proposal, removed = apply_patch(
                    working,
                    component,
                    local_scope,
                    local_preparation,
                    required,
                    excluded,
                    id_prefix=prefix if len(partitions) == 1 else f"{prefix}_c{number}",
                    context=ctx,
                )
                audit.update(
                    proposal=proposal.model_dump(mode="json"),
                    main_visits_lost=removed,
                    changed_activity_ids=[
                        a.activity_id
                        for d in proposal.days
                        for a in d.activities
                        if a not in [v for day in working.days for v in day.activities]
                    ],
                )
                if scope.unsupported_explicit_mode and any(
                    e.operation in {"add", "replace"} for e in component.edits
                ):
                    raise ValueError("explicit_transport_mode_not_supported")
                check_time_permissions(working, proposal, schedule)
                proposal, extra = await resolve_transfers(
                    working,
                    proposal,
                    scope,
                    (*context.route_evidence, *evidence, *acquired),
                    places,
                    provider,
                    budget,
                    schedule,
                )
                acquired.extend(extra)
                proposal, proposed_schedule, changes = consume_windows(
                    working,
                    proposal,
                    local_scope,
                    schedule,
                    places,
                    (*context.route_evidence, *evidence, *acquired),
                    budget.policy.spatial,
                    prefix=f"{prefix}_c{number}",
                )
                if (
                    sum(len(d.activities) for d in proposal.days)
                    > budget.policy.input.activity_capacity
                ):
                    raise ValueError("repair_activity_capacity_after_window_split")
                audit["proposal"] = proposal.model_dump(mode="json")
                reevaluated = assess(
                    working,
                    ctx,
                    preparation.ledger,
                    (*evidence, *acquired),
                    bind_transitions(
                        working, scope.travel_mode or "WALK", scope.routing_preference, schedule
                    ),
                )
                after = assess(
                    proposal,
                    ctx.model_copy(update={"schedule": proposed_schedule}),
                    preparation.ledger,
                    (*evidence, *acquired),
                    bind_transitions(
                        proposal,
                        scope.travel_mode or "WALK",
                        scope.routing_preference,
                        proposed_schedule,
                    ),
                )
                comparison = compare(
                    working,
                    proposal,
                    before,
                    reevaluated,
                    after,
                    local_scope,
                    proposed_schedule,
                    ctx,
                    allow_soft_exploration=getattr(budget, "allow_soft_exploration", False),
                )
                spatial = check_addition_layout(
                    stage_original,
                    proposal,
                    places,
                    (*context.route_evidence, *evidence, *acquired),
                    scope.travel_mode,
                    budget.policy.spatial,
                    required,
                    routing_preference=scope.routing_preference,
                    schedule=proposed_schedule,
                    check_rearrangements=proposal_strategy == "replan",
                )
                audit.update(
                    report=after.model_dump(mode="json"),
                    comparison=comparison.model_dump(mode="json"),
                    spatial=spatial,
                )
                if not comparison.accepted or not spatial["accepted"]:
                    from backend.app.versions.v3.repair_pending import retain_pending

                    deduplication = any(
                        f.check == "repetition" and ("target", f.finding_id) in dependencies
                        for f in initial.findings
                    )
                    pending = deduplication and retain_pending(
                        budget,
                        working,
                        proposal,
                        component,
                        dependencies,
                        after,
                        comparison,
                        spatial,
                    )
                    audit.update(
                        status="pending" if pending else "rejected",
                        reason=comparison.reason + "; " + "; ".join(spatial["reasons"]),
                    )
                    continue
                # Check all original obligations too, not just this component's improvements.
                base = assess(
                    original, context, preparation.ledger, (*evidence, *acquired), original_bindings
                )
                global_check = compare(
                    original,
                    proposal,
                    initial,
                    base,
                    after,
                    scope,
                    proposed_schedule,
                    context,
                    allow_soft_exploration=getattr(budget, "allow_soft_exploration", False),
                )
                if not global_check.accepted:
                    audit.update(status="rejected", reason=global_check.reason)
                    continue
                working, schedule = proposal, proposed_schedule
                from backend.app.versions.v3.repair_pending import complete_pending

                complete_pending(budget, dependencies)
                losses.extend(removed)
                adjustments.extend(changes)
                latest_spatial = spatial
                audit.update(status="accepted", reason="verifiable_component_improvement")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            audit.update(status="rejected", reason=f"{type(exc).__name__}:{exc}")
        finally:
            audit.update(
                budget_after=dict(budget.used),
                elapsed_seconds=max(0, budget.clock() - component_started),
            )
    reassessed = assess(
        original, context, preparation.ledger, (*evidence, *acquired), original_bindings
    )
    after = assess(
        working,
        context.model_copy(update={"schedule": schedule}),
        preparation.ledger,
        (*evidence, *acquired),
        bind_transitions(working, scope.travel_mode or "WALK", scope.routing_preference, schedule),
    )
    comparison = compare(
        original,
        working,
        initial,
        reassessed,
        after,
        scope,
        schedule,
        context,
        allow_soft_exploration=getattr(budget, "allow_soft_exploration", False),
    )
    final_spatial = check_addition_layout(
        stage_original,
        working,
        places,
        (*context.route_evidence, *evidence, *acquired),
        scope.travel_mode,
        budget.policy.spatial,
        required,
        routing_preference=scope.routing_preference,
        schedule=schedule,
    )
    if comparison.accepted and not final_spatial["accepted"]:
        comparison = comparison.model_copy(
            update={
                "accepted": False,
                "reason": "Final component spatial revalidation: "
                + "; ".join(final_spatial["reasons"]),
            }
        )
    if not comparison.accepted:
        # The safe fallback is the round input; actual sends and obtained evidence remain.
        for audit in audits:
            if audit["status"] == "accepted":
                audit.update(status="rolled_back", reason="final_global_revalidation")
        working, schedule, adjustments, losses = original, context.schedule, [], []
    return dict(
        final=working,
        schedule=schedule,
        adjustments=tuple(adjustments),
        losses=tuple(losses),
        extra=tuple(acquired),
        components=tuple(audits),
        reassessed=reassessed,
        after=after,
        comparison=comparison,
        spatial=latest_spatial,
    )
