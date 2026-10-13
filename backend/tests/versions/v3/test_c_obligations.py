"""C evidence-to-automatic-scope-to-adoption tests; external boundaries are fixtures."""

import asyncio
from datetime import time, timedelta
from time import monotonic

import pytest

from backend.app.versions.v3.models import ValidationPolicy
from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_models import VisitBinding
from backend.app.versions.v3.repair_routes import bind_transitions
from backend.app.versions.v3.repair_service import run_repair_stage
from backend.app.versions.v3.wiring import operation_scope
from backend.tests.versions.v3.test_b_targets import edit, setup, visit
from backend.tests.versions.v3.test_repair import Model, Routes, route
from backend.tests.versions.v3.test_validation import DAY, effective


def opening_case(*, closed=False, bound=True, required=None):
    original, ctx, _, policy = setup(
        [[visit("a", "a", start="17:00", end="18:00")]], reviews=(), required=required
    )
    ctx = ctx.model_copy(
        update={
            "effective_places": (effective(closure=closed),),
            "visit_bindings": (
                VisitBinding(
                    activity_id="a",
                    place_id="a",
                    mode="venue_entry",
                    source_refs=("application:explicit_fixture_intent",),
                ),
            )
            if bound
            else (),
        }
    )
    return original, ctx, policy


def execute(case, patches, *, mode="WALK", routes=None):
    original, ctx, policy = case
    # Keep the supplied model strategy observable; system deletion has separate stage tests.
    policy = policy.model_copy(update={"max_deletion_attempts": 0})
    scope = operation_scope(original, assess(original, ctx), context=ctx, policy=policy, mode=mode)

    class Sequence(Model):
        async def generate_repair_structured(self, **kwargs):
            self.calls += 1
            value = patches[min(self.calls - 1, len(patches) - 1)]
            if isinstance(value, Exception):
                raise value
            return {"edits": value}

    model = Sequence()
    assert scope is not None
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            policy=policy,
            model=model,
            routes_provider=routes,
            request_deadline=monotonic() + 600,
        )
    )
    return result, model


def test_entry_hours_confirmed_and_retime_without_any_review():
    case = opening_case()
    before = assess(case[0], case[1])
    assert not case[1].policy.review_targets
    assert any(f.check == "opening" and f.status == "CONFIRMED" for f in before.findings)
    result, model = execute(case, [[edit("retime", "a", start="15:00", end="16:00")]])
    assert result.status == "ACCEPTED_COMPLETE", [
        (r.result.reason, r.result.spatial) for r in result.rounds
    ]
    assert model.calls == 1 and result.original == case[0]
    assert any(f.check == "opening" and f.status == "PASS" for f in result.adopted_report.findings)
    assert any(
        f.check == "visitor_suitability" and f.status == "UNKNOWN"
        for f in result.adopted_report.findings
    )


def test_closed_optional_replace_with_unknown_retains_new_unknowns():
    case = opening_case(closed=True)
    result, _ = execute(case, [[edit("replace", "a", "b", start="17:00", end="18:00")]])
    assert result.status == "ACCEPTED_COMPLETE", [
        (r.result.reason, r.result.spatial) for r in result.rounds
    ]
    assert result.final.days[0].activities[0].source_place_id == "b"
    assert any(
        f.check == "opening" and f.status == "UNKNOWN" for f in result.adopted_report.findings
    )
    assert result.rounds[0].result.comparison.business_values[0]["obligation_removed"]


def test_closed_deletion_child_partial_survives_later_failure():
    result, model = execute(
        opening_case(closed=True), [[edit("delete", "a")], RuntimeError("offline failure")]
    )
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert not result.final.days[0].activities
    assert any(r.status == "unresolved" for r in result.related_targets)
    assert model.calls == 2


def test_required_closed_visit_cannot_be_deleted_or_replaced():
    case = opening_case(closed=True, required="REQUIRED")
    result, _ = execute(case, [[edit("delete", "a")]])
    assert result.status == "REJECTED" and result.final == case[0]


@pytest.mark.parametrize("change", ["zone", "date", "conflict", "exterior"])
def test_insufficient_opening_scope_never_confirms(change):
    original, ctx, policy = opening_case()
    if change == "unbound":
        ctx = ctx.model_copy(update={"visit_bindings": ()})
    if change == "exterior":
        ctx = ctx.model_copy(
            update={
                "visit_bindings": (ctx.visit_bindings[0].model_copy(update={"mode": "exterior"}),)
            }
        )
    if change == "zone":
        ctx = ctx.model_copy(
            update={"places": tuple(p.model_copy(update={"timezone_id": None}) for p in ctx.places)}
        )
    if change == "date":
        ctx = ctx.model_copy(
            update={
                "effective_places": (
                    effective(
                        applicable_start_date=DAY + timedelta(days=1),
                        applicable_end_date=DAY + timedelta(days=1),
                    ),
                )
            }
        )
    if change == "conflict":
        e = ctx.effective_places[0]
        ctx = ctx.model_copy(
            update={
                "effective_places": (
                    e.model_copy(
                        update={
                            "facts": tuple(
                                f.model_copy(update={"relation": "conflict"}) for f in e.facts
                            )
                        }
                    ),
                )
            }
        )
    assert not any(
        f.check == "opening" and f.status == "CONFIRMED" for f in assess(original, ctx).findings
    )
    assert operation_scope(original, assess(original, ctx), context=ctx, policy=policy) is None


def route_case():
    original, ctx, _, policy = setup(
        [[visit("a", "a", end="11:00"), visit("b", "b", start="11:10", end="12:10")]], reviews=()
    )
    ctx = ctx.model_copy(
        update={
            "route_evidence": (route(1800),),
            "transitions": bind_transitions(original, "TRANSIT", schedule=ctx.schedule),
        }
    )
    return original, ctx, policy


def test_timed_transfer_automatically_repaired_by_retime():
    result, _ = execute(
        route_case(), [[edit("retime", "b", start="11:40", end="12:40")]], mode="TRANSIT"
    )
    assert result.status == "ACCEPTED_COMPLETE", [
        (r.result.reason, r.result.spatial) for r in result.rounds
    ]
    assert result.target_progress[0].after == 0


def test_changed_departure_needs_new_route_and_failure_does_not_pass():
    patch = [edit("retime", "a", start="08:30", end="10:30")]
    failed, _ = execute(route_case(), [patch], mode="TRANSIT", routes=Routes(fail=True))
    assert failed.status == "REJECTED" and failed.final == route_case()[0]
    provider = Routes(duration=1800)
    accepted, _ = execute(route_case(), [patch], mode="TRANSIT", routes=provider)
    assert accepted.status == "ACCEPTED_COMPLETE", accepted.reason
    assert accepted.counters["routes"] == accepted.counters["elements"] == 1


def test_timed_transfer_partial_improvement_remains_confirmed():
    result, _ = execute(
        route_case(),
        [[edit("retime", "b", start="11:20", end="12:20")], RuntimeError("offline")],
        mode="TRANSIT",
    )
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert any(
        f.check == "route" and f.status == "CONFIRMED" and f.magnitude == 600
        for f in result.adopted_report.findings
    )


def test_removed_optional_route_obligation_does_not_require_nonexistent_leg():
    result, _ = execute(
        route_case(),
        [[edit("replace", "b", "c", start="12:00", end="13:00")]],
        mode="TRANSIT",
        routes=Routes(duration=300),
    )
    assert result.status == "ACCEPTED_COMPLETE", [
        (r.result.reason, r.result.spatial) for r in result.rounds
    ]
    assert any(
        f.check == "opening" and f.status == "UNKNOWN" for f in result.adopted_report.findings
    )


def test_real_runner_graph_auto_route_with_reviews_off():
    from backend.tests.request_fixtures import make_request
    from backend.tests.versions.v1.test_interpreted_requirements import draft_for
    from backend.tests.versions.v3.test_wiring import Model as GraphModel
    from backend.tests.versions.v3.test_wiring import execute as graph_run
    from backend.tests.versions.v3.test_wiring import primary

    original = primary(False)
    a = original.days[0].activities[0]
    a.end_time = a.end_time.replace(hour=12)
    b = a.model_copy(
        update={
            "activity_id": "b",
            "source_place_id": "poi-0-1",
            "start_time": a.end_time + timedelta(minutes=1),
            "end_time": a.end_time + timedelta(minutes=61),
        }
    )
    original.days[0].activities.append(b)

    class Graph(GraphModel):
        async def generate_structured(self, **kwargs):
            if kwargs["response_schema"].__name__ == "InterpretationDraft":
                return draft_for(
                    "Use transit",
                    semantic_requirements=(),
                    time_protections=(),
                    visit_requirements=(),
                    transport_preference={"mode": "TRANSIT", "source_text": "Use transit"},
                )
            return await super().generate_structured(**kwargs)

        async def generate_repair_structured(self, **kwargs):
            self.repair_calls += 1
            return {
                "edits": [
                    dict(
                        operation="retime",
                        activity_id="b",
                        place_id=None,
                        date=str(b.start_time.date()),
                        start_time=(a.end_time + timedelta(minutes=30)).isoformat(),
                        end_time=(a.end_time + timedelta(minutes=90)).isoformat(),
                    )
                ]
            }

    result, model, places, runtime = asyncio.run(
        graph_run(Graph(original), request=make_request("Use transit"))
    )
    assert not any(result.v3.review_policy.values())
    assert result.v3.repair.status == "ACCEPTED_COMPLETE", result.v3.repair.reason
    assert model.repair_calls == 1 and places.nearby and runtime.closes == 1
    assert result.generation_diagnostics == result.v3.final_report.diagnostics
    assert result.itinerary.cost_projections == result.v3.draft.cost_projections
    assert any(
        f.check == "route" and f.status == "CONFIRMED" for f in result.v3.original_report.findings
    )


def test_notes_only_rejected_and_retime_preserves_warning_as_historical():
    original, ctx, policy = opening_case()
    original.days[0].activities[0].notes = "Original timing summary. Keep the reservation warning."
    result, _ = execute(
        (original, ctx, policy), [[edit("retime", "a", start="15:00", end="16:00")]]
    )
    assert result.status == "ACCEPTED_COMPLETE"
    assert result.final.days[0].activities[0].notes.startswith("Historical note")
    assert original.days[0].activities[0].notes in result.final.days[0].activities[0].notes
    patch = edit("retime", "a", start="17:00", end="18:00")
    patch["notes"] = "Open now"
    rejected, _ = execute((original, ctx, policy), [[patch]])
    assert rejected.status == "REJECTED" and rejected.final == original


def test_route_order_change_checks_new_directed_chain():
    provider = Routes(duration=1800)
    result, _ = execute(
        route_case(),
        [
            [
                edit("retime", "b", start="08:00", end="09:00"),
                edit("retime", "a", start="09:40", end="11:40"),
            ]
        ],
        mode="TRANSIT",
        routes=provider,
    )
    assert result.status == "ACCEPTED_COMPLETE", [r.result.reason for r in result.rounds]
    assert provider.calls[0].origins[0].place_id == "b"
    assert provider.calls[0].destinations[0].place_id == "a"
    assert any(
        f.check == "route" and f.activity_ids == ("b", "a") and f.status == "PASS"
        for f in result.adopted_report.findings
    )


def test_opening_partial_remains_confirmed_and_required_duration_unchanged():
    result, _ = execute(
        opening_case(required="REQUIRED"),
        [[edit("retime", "a", start="16:30", end="17:30")], RuntimeError("offline")],
    )
    assert result.status == "ACCEPTED_PARTIAL"
    assert any(
        f.check == "opening" and f.status == "CONFIRMED" and f.magnitude == 1800
        for f in result.adopted_report.findings
    )
    failed, _ = execute(
        opening_case(required="REQUIRED"), [[edit("retime", "a", start="16:30", end="17:00")]]
    )
    assert failed.status == "REJECTED"


def test_opening_adjacent_move_plus_local_compensation():
    original, ctx, _, policy = setup(
        [[visit("a", "a", start="17:00", end="18:00")]], reviews=(), extra_days=1
    )
    ctx = ctx.model_copy(
        update={
            "effective_places": (effective(applicable_end_date=DAY + timedelta(days=1)),),
            "visit_bindings": (
                VisitBinding(
                    activity_id="a",
                    place_id="a",
                    mode="venue_entry",
                    source_refs=("application:explicit_intent",),
                ),
            ),
        }
    )
    result, _ = execute(
        (original, ctx, policy),
        [
            [
                edit("move", "a", day=1, start="15:00", end="16:00"),
                edit("add", pid="b", start="17:00", end="18:00"),
            ]
        ],
    )
    assert result.status == "ACCEPTED_COMPLETE", [r.result.reason for r in result.rounds]
    assert result.final.days[1].activities[0].activity_id == "a"
    assert result.final.days[0].activities[0].source_place_id == "b"


def test_fixed_time_blocks_opening_retime():
    from backend.app.versions.v3.repair_schedule import build_schedule
    from backend.tests.versions.v3.test_schedule import protection

    original, ctx, policy = opening_case()
    c = ctx.contract.model_copy(
        update={
            "time_protections": (
                protection().model_copy(update={"start_time": time(14), "end_time": time(16)}),
            )
        }
    )
    ctx = ctx.model_copy(
        update={
            "contract": c,
            "schedule": build_schedule(original, c, ctx.places, primary_generated=True),
        }
    )
    result, _ = execute(
        (original, ctx, policy), [[edit("retime", "a", start="15:00", end="16:00")]]
    )
    assert result.status == "REJECTED" and result.final == original


def test_shared_access_intent_binding_does_not_manufacture_operating_facts():
    from backend.app.schemas.interpreted_requirements import VisitRequirement
    from backend.app.versions.v3.repair_obligations import bind_visits

    original, ctx, policy = opening_case(required="REQUIRED", bound=False)
    named = ctx.contract.named_places[0]
    rule = VisitRequirement(
        place_text="a",
        requirement_id=named.requirement_id,
        minimum_visits=1,
        dates=(),
        status="executable",
        reason=None,
        source_refs=named.source_refs,
        access_mode="venue_entry",
    )
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(update={"visit_requirements": (rule,)}),
            "effective_places": (),
        }
    )
    assert bind_visits(original, ctx)[0].mode == "venue_entry"
    assert not any(
        f.check == "opening" and f.status == "CONFIRMED" for f in assess(original, ctx).findings
    )
    ctx = ctx.model_copy(update={"effective_places": (effective(),)})
    result, _ = execute(
        (original, ctx, policy), [[edit("retime", "a", start="15:00", end="16:00")]]
    )
    assert result.status == "ACCEPTED_COMPLETE"


def test_review_targets_deferred_while_confirmed_conflict_remains():
    original, ctx, policy = opening_case()
    ctx = ctx.model_copy(update={"policy": ValidationPolicy(review_targets={"coverage"})})
    result, _ = execute(
        (original, ctx, policy),
        [[edit("retime", "a", start="16:30", end="17:30")], RuntimeError("offline")],
    )
    assert result.status == "ACCEPTED_PARTIAL"
    assert result.rounds[0].result.scope.deferred_review_target_ids
    assert all(p.check == "opening" for p in result.rounds[0].result.target_progress)


def test_actual_deletion_removes_leg_but_keeps_coverage_child():
    provider = Routes(fail=True)
    result, _ = execute(
        route_case(),
        [[edit("delete", "b")], RuntimeError("offline")],
        mode="TRANSIT",
        routes=provider,
    )
    assert result.status == "ACCEPTED_PARTIAL"
    assert result.rounds[0].result.comparison.business_values[0]["obligation_removed"]
    assert result.rounds[0].result.counters.get("routes", 0) == 0
    # A later activated coverage child may prepare replacement route options.
    assert any(r.status == "unresolved" for r in result.related_targets)


def test_explicit_entry_requirement_cannot_be_satisfied_by_exterior_copy():
    from backend.app.schemas.interpreted_requirements import VisitRequirement
    from backend.app.versions.v3.repair_targets import protect_visits

    original, ctx, policy = opening_case(required="REQUIRED")
    other = (
        original.days[0]
        .activities[0]
        .model_copy(
            update={
                "activity_id": "outside",
                "start_time": original.days[0].activities[0].start_time - timedelta(hours=3),
                "end_time": original.days[0].activities[0].end_time - timedelta(hours=3),
            }
        )
    )
    original.days[0].activities.append(other)
    n = ctx.contract.named_places[0]
    rule = VisitRequirement(
        place_text="a",
        requirement_id=n.requirement_id,
        minimum_visits=1,
        dates=(),
        status="executable",
        reason=None,
        source_refs=n.source_refs,
        access_mode="venue_entry",
    )
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(update={"visit_requirements": (rule,)}),
            "visit_bindings": (
                *ctx.visit_bindings,
                VisitBinding(
                    activity_id="outside",
                    place_id="a",
                    mode="exterior",
                    source_refs=("application:exterior",),
                ),
            ),
        }
    )
    trial = original.model_copy(deep=True)
    trial.days[0].activities = [other]
    with pytest.raises(ValueError, match="satisfaction"):
        protect_visits(original, trial, ctx)
    assert any(
        f.check == "named_requirement" and f.status == "UNKNOWN"
        for f in assess(trial, ctx).findings
    )


def test_exhausted_route_budget_retains_old_confirmed_limit():
    original, ctx, policy = route_case()
    policy = policy.model_copy(
        update={"acquisition": policy.acquisition.model_copy(update={"routes": 0})}
    )
    provider = Routes(duration=1800)
    result, _ = execute(
        (original, ctx, policy),
        [[edit("retime", "a", start="08:30", end="10:30")]],
        mode="TRANSIT",
        routes=provider,
    )
    assert result.status == "REJECTED" and result.final == original
    assert not provider.calls
    assert any(
        f.check == "route" and f.status == "CONFIRMED" for f in result.adopted_report.findings
    )


def test_conflicting_closure_authority_and_wrong_scope_never_confirm():
    original, ctx, policy = opening_case(closed=True)
    e = ctx.effective_places[0]
    for update in ({"authority_bases": ()}, {"subject_scope": "sub_area"}):
        facts = tuple(f.model_copy(update=update) for f in e.facts)
        altered = ctx.model_copy(
            update={"effective_places": (e.model_copy(update={"facts": facts}),)}
        )
        assert not any(
            f.check == "opening" and f.status == "CONFIRMED"
            for f in assess(original, altered).findings
        )


def test_opening_magnitude_uses_same_date_specific_fact_as_confirmation():
    original, ctx, policy = opening_case()
    e = ctx.effective_places[0]
    baseline = e.facts[0].model_copy(
        update={"temporal_basis": "current_general_policy", "closes_at": time(20)}
    )
    ctx = ctx.model_copy(
        update={"effective_places": (e.model_copy(update={"facts": (baseline, *e.facts)}),)}
    )
    row = next(f for f in assess(original, ctx).findings if f.check == "opening")
    assert row.status == "CONFIRMED" and row.magnitude == 3600
