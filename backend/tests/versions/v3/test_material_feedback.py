"""Material progress gates through actual preparation, projection and Repair stage."""

import asyncio
import json
from datetime import timedelta
from time import monotonic

import pytest

from backend.app.versions.v3.repair_budget import RepairBudget
from backend.app.versions.v3.repair_candidates import matched_capacity, prepare_candidates
from backend.app.versions.v3.repair_feedback import material_fingerprint, opportunity
from backend.app.versions.v3.repair_models import CandidateDecision
from backend.tests.versions.v3.test_multiround import SequenceModel, policy, stage
from backend.tests.versions.v3.test_repair import (
    DAY,
    CandidateSearch,
    Routes,
    addition_scope,
    context,
    discovery_context,
    draft,
    edit,
    place,
)
from backend.tests.versions.v3.test_schedule import setup


def test_noop_rotates_unpresented_old_options_without_acquisition():
    places = tuple(place(pid) for pid in ("a", "b", "c", "d", "e"))
    ctx = discovery_context(places=places, original_supply_ids=tuple(p.place_id for p in places))
    model, provider = SequenceModel([[], []]), CandidateSearch()
    result = stage(
        model,
        draft(),
        ctx,
        addition_scope(draft(), ctx),
        policy=policy(max_rounds=2, max_model_calls=2, input={"identity_capacity": 3}),
        places_provider=provider,
        intent_ids=("discovery_1",),
    )
    groups = [{c["place_id"] for c in i["addition_candidates"]} for i in model.inputs]
    assert model.calls == 2 and groups[0].isdisjoint(groups[1])
    assert provider.calls == provider.searches == 0
    assert result.rounds[0].result.feedback_kind == "no_op_patch"
    assert all(r["outcome"] == "not_selected" for r in result.presentation_history)
    assert not result.conflict_records


def test_noop_bounded_discovery_changes_real_input_and_accepts():
    ctx, original = discovery_context(), draft()
    provider = CandidateSearch()
    model = SequenceModel(
        [[], [edit("12:00", "13:00", operation="add", activity_id=None, place_id="fresh")]]
    )
    result = stage(
        model,
        original,
        ctx,
        addition_scope(original, ctx),
        places_provider=provider,
        intent_ids=("discovery_1",),
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert provider.searches == 1 and provider.calls == 1
    assert "fresh" not in {c["place_id"] for c in model.inputs[0]["addition_candidates"]}
    assert "fresh" in {c["place_id"] for c in model.inputs[1]["addition_candidates"]}
    assert result.counters["google"] == result.counters["details"] == 1


@pytest.mark.parametrize("role", ["non_main", "unresolved"])
def test_semantically_rejected_new_option_does_not_stop_replenishment(role):
    from backend.tests.services.test_poi_semantics import Model as SemanticModel
    from backend.tests.services.test_poi_semantics import service
    from backend.tests.versions.v3.test_repair import selection

    def reject_pending(rows):
        for row in rows:
            if row["visit_object"] == "pending":
                row["role"] = role

    semantic = service(SemanticModel(reject_pending))
    ctx, original = discovery_context(), draft()
    budget = RepairBudget(monotonic() + 600)
    scope = addition_scope(original, ctx)
    first = asyncio.run(
        prepare_candidates(ctx, scope, budget, original=original, semantic_service=semantic)
    )
    budget.presentation_history = [
        {"signature": a.opportunity_signature} for a in first.authorizations
    ]
    budget.feedback_kind = "no_op_patch"
    provider = CandidateSearch()
    prep = asyncio.run(
        prepare_candidates(
            ctx,
            scope,
            budget,
            original=original,
            pool=(selection("pending"),),
            provider=provider,
            intent_ids=("discovery_1",),
            semantic_service=semantic,
        )
    )
    assert provider.searches == 1
    assert "pending" not in {r.place_id for r in prep.authorizations}
    assert "fresh" in {r.place_id for r in prep.authorizations}
    assert budget.used["details"] == budget.used["canonical"] == 2
    assert any(r.reason == "semantic_role_not_main" for r in prep.decisions)


def test_repeated_empty_replan_stops_before_another_send_and_keeps_authority_explicit():
    original, ctx = draft(), context()
    model = SequenceModel([[], [], [], [], [], []])
    result = stage(model, original, ctx, addition_scope(original, ctx))
    assert model.calls == result.counters["model"] == 2
    assert result.reason == "no_new_material_after_empty_proposal"
    assert result.final == original
    assert not result.rounds[-1].result.model_attempted
    assert result.rounds[-1].result.empty_proposal_guard["action"] == "stop_unchanged_input"
    assert model.inputs[1]["scope"]["permissions"] == []
    assert model.inputs[1]["addition_candidates"]
    assert "independent" in model.inputs[1]["operation_guidance"]["authority_rule"]


def test_unpresented_place_and_semantic_changes_do_not_bypass_empty_input_guard():
    from backend.app.schemas.poi_semantics import POISemanticAssessment
    from backend.tests.versions.v3.test_repair import Model, overlap_draft, run, scope_for
    from backend.tests.versions.v3.test_semantic_repair import semantic_rows

    original, ctx = overlap_draft(), context()
    ctx = ctx.model_copy(update={"semantic_assessments": semantic_rows(ctx)})
    scope = scope_for(original, ctx)
    budget = RepairBudget(monotonic() + 600)
    model = Model([])
    first = run(original, ctx, scope, model, budget=budget, proposal_strategy="replan")
    foreign = place("unpresented")
    ctx = ctx.model_copy(
        update={
            "places": (*ctx.places, foreign),
            "semantic_assessments": (
                *ctx.semantic_assessments,
                POISemanticAssessment(
                    place_id=foreign.place_id,
                    visit_object="Restaurant",
                    role="non_main",
                    categories=[],
                    reason="Fixture role",
                    evidence_refs=[foreign.source_ref],
                    matches=[],
                    exception_requirement_ids=[],
                ),
            ),
        }
    )
    second = run(original, ctx, scope, model, budget=budget, proposal_strategy="replan")
    assert first.material_fingerprint == second.material_fingerprint
    assert model.calls == budget.used["model"] == 1
    assert second.status == "SKIPPED" and second.reason == "no_new_material_after_empty_proposal"


def test_semantic_limit_stops_replenishment_without_authorizing_unassessed_candidates():
    from backend.tests.services.test_poi_semantics import Model as SemanticModel
    from backend.tests.services.test_poi_semantics import service
    from backend.tests.versions.v3.test_repair import selection

    semantic = service(SemanticModel(), max_calls=1)
    ctx = discovery_context(original_supply_ids=("a",), places=(place(),))
    original, provider = draft(), CandidateSearch()
    budget = RepairBudget(monotonic() + 600)
    prep = asyncio.run(
        prepare_candidates(
            ctx,
            addition_scope(original, ctx),
            budget,
            original=original,
            pool=(selection("pending"),),
            provider=provider,
            intent_ids=("discovery_1",),
            semantic_service=semantic,
        )
    )
    assert not prep.authorizations and not prep.input_candidates
    assert provider.calls == provider.searches == 0
    assert "semantic_assessment_preparation_limit" in budget.stops


@pytest.mark.parametrize("boundary", ["query", "capacity", "deadline"])
def test_budget_alone_does_not_authorize_discovery(boundary):
    ctx, original, provider = discovery_context(), draft(), CandidateSearch()
    scope = addition_scope(original, ctx)
    budget = RepairBudget(monotonic() + 600)
    first = asyncio.run(prepare_candidates(ctx, scope, budget, original=original))
    budget.presentation_history = [
        {"signature": a.opportunity_signature} for a in first.authorizations
    ]
    budget.feedback_kind = "no_op_patch"
    if boundary == "capacity":
        budget.policy = policy(exploration_positions=0, input={"identity_capacity": 1})
    if boundary == "deadline":
        budget.io_deadline = budget.clock() - 1
    asyncio.run(
        prepare_candidates(
            ctx,
            scope,
            budget,
            original=original,
            provider=provider,
            intent_ids=() if boundary == "query" else ("discovery_1",),
        )
    )
    assert provider.searches == provider.calls == 0


def test_independent_matching_counts_unknown_identity_once():
    rows = [
        CandidateDecision(
            place_id="b",
            target_id=t,
            date=DAY,
            operation="add",
            disposition="eligible",
            reason="fixture",
        )
        for t in ("t1", "t2")
    ]
    targets = (("t1", DAY, "add", 1), ("t2", DAY, "add", 1))
    assert matched_capacity(rows, targets) == 1
    rows[0] = rows[0].model_copy(update={"opportunity_status": "BLOCKED"})
    assert matched_capacity(rows, targets) == 1
    rows[1] = rows[1].model_copy(update={"opportunity_status": "BLOCKED"})
    assert matched_capacity(rows, targets) == 0


def test_hours_window_opportunity_has_no_minimum_duration_and_keeps_unknown():
    original, ctx, scope = setup()
    base = dict(known=True, timezone="UTC", intervals=[(f"{DAY}T10:00:00", f"{DAY}T10:00:01")])
    status, _, windows = opportunity(place("b"), DAY, "add", base, original, ctx, scope)
    assert status == "TRYABLE" and windows
    base["intervals"] = [(f"{DAY}T09:00:00", f"{DAY}T10:00:00")]
    assert opportunity(place("b"), DAY, "add", base, original, ctx, scope)[0] == "BLOCKED"
    base["known"] = False
    assert opportunity(place("b"), DAY, "add", base, original, ctx, scope)[0] == "UNRESOLVED"


def test_preparation_blocked_edges_do_not_meet_reference():
    from backend.tests.versions.v3.test_repair import selection, with_hours

    original, ctx, scope = setup()
    # Only the occupied 09:00-10:00 period is open; generated free time starts at 10:00.
    places = (place(), with_hours("b"), with_hours("c"))
    ctx = ctx.model_copy(update={"places": places})
    # An explicitly fixed whole calendar, including the elastic interval, admits no insertion.
    from backend.app.versions.v3.repair_schedule import TimeWindow

    w = TimeWindow(
        root_activity_id="fixed",
        start=f"{DAY}T00:00:00+00:00",
        end=f"{DAY + timedelta(days=1)}T00:00:00+00:00",
        source="user_fixed",
    )
    ctx = ctx.model_copy(
        update={
            "schedule": ctx.schedule.model_copy(
                update={
                    "fixed": (w,),
                    "windows": (),
                    "lineage": {},
                }
            )
        }
    )
    provider = CandidateSearch()
    prep = asyncio.run(
        prepare_candidates(
            ctx,
            scope,
            RepairBudget(monotonic() + 600),
            original=original,
            pool=(selection("pending"),),
            provider=provider,
        )
    )
    assert not prep.authorizations
    assert all(not row["preparation_reference_met"] for row in prep.target_opportunities)
    assert any(d.opportunity_status == "BLOCKED" for d in prep.decisions)
    assert provider.calls == provider.searches == 0


def test_fingerprint_ignores_commentary_order_and_observation_time_but_not_constraints():
    a = dict(
        candidate_catalog=[{"place_id": "b", "retrieved_at": "old"}, {"place_id": "c"}],
        feedback={"round": 1},
        time_windows=[{"start": "13:00", "end": "16:00"}],
    )
    b = dict(a, candidate_catalog=list(reversed(a["candidate_catalog"])), feedback={"round": 2})
    b["candidate_catalog"][1] = {"place_id": "b", "retrieved_at": "new"}
    assert material_fingerprint(json.dumps(a)) == material_fingerprint(json.dumps(b))
    b["arrangement_constraints"] = [{"place_id": "b", "start": "13:00", "end": "14:00"}]
    assert material_fingerprint(json.dumps(a)) != material_fingerprint(json.dumps(b))
    b = dict(a, time_windows=[{"start": "14:30", "end": "16:00"}])
    assert material_fingerprint(json.dumps(a)) != material_fingerprint(json.dumps(b))


def test_applicable_leg_policy_can_block_all_positions_without_blocking_unknown_routes():
    from backend.app.evidence.models import RouteEvidence
    from backend.tests.versions.v3.test_validation import NOW

    original, ctx, scope = setup()
    route = RouteEvidence(
        travel_mode="WALK",
        mode_reason="fixture",
        availability="available",
        retrieved_at=NOW,
        source_ref="fixture:long_walk",
        elements=[
            dict(
                origin_place_id=a,
                destination_place_id=b,
                status="OK",
                status_state="success",
                condition="ROUTE_EXISTS",
                duration_seconds=3600,
                distance_meters=4000,
                availability="available",
            )
            for a, b in (("a", "b"), ("b", "a"))
        ],
    )
    view = dict(known=False, intervals=[], timezone="UTC")
    with_routes = ctx.model_copy(update={"route_evidence": (route,)})
    args = (place("b"), DAY, "add", view, original)
    assert opportunity(*args, with_routes, scope, policy().spatial)[0] == "UNRESOLVED"
    scope = scope.model_copy(update={"mode_source": "USER_EXPLICIT"})
    assert opportunity(*args, with_routes, scope, policy().spatial)[0] == "BLOCKED"
    assert opportunity(*args, ctx, scope, policy().spatial)[0] == "UNRESOLVED"
    assert (
        opportunity(*args, with_routes, scope, policy().spatial, required=True)[0] == "UNRESOLVED"
    )
    # A dated TRANSIT observation cannot prove all departures in the window impossible.
    transit = route.model_copy(
        update={"travel_mode": "TRANSIT", "representative_departure_time": NOW}
    )
    assert (
        opportunity(
            *args,
            ctx.model_copy(update={"route_evidence": (transit,)}),
            scope.model_copy(update={"travel_mode": "TRANSIT"}),
            policy().spatial,
        )[0]
        == "UNRESOLVED"
    )


def test_specific_failed_time_changes_next_input_without_search():
    # First retime preserves the overlap. Its concrete failed interval is visible next round.
    model = SequenceModel([[edit("10:20", "11:20")], [edit("11:00", "12:00")]])
    result = stage(model, routes_provider=Routes())
    assert model.calls == 2 and result.status == "ACCEPTED_COMPLETE", result.reason
    constraints = model.inputs[1]["arrangement_constraints"]
    assert constraints and constraints[0]["check"] == "overlap"
    assert constraints[0]["start"].endswith("10:20:00+00:00")
    assert result.counters.get("google", 0) == 0


def test_candidate_conflict_reuses_different_time_before_discovery():
    original, ctx, provider = draft(), discovery_context(), CandidateSearch()
    model = SequenceModel(
        [
            [edit("10:30", "11:30", operation="add", activity_id=None, place_id="b")],
            [edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")],
        ]
    )
    result = stage(
        model,
        original,
        ctx,
        addition_scope(original, ctx),
        places_provider=provider,
        intent_ids=("discovery_1",),
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert model.calls == 2 and provider.searches == provider.calls == 0
    constraint = model.inputs[1]["arrangement_constraints"][0]
    assert constraint["place_id"] == "b" and constraint["target_ids"]
    assert constraint["start"].endswith("10:30:00+00:00")


def test_conflict_attribution_does_not_blacklist_other_patch_candidates():
    from backend.app.versions.v3.repair_feedback import learn
    from backend.tests.versions.v3.test_repair import Model, run

    original, ctx = draft(), context(places=(place(), place("b"), place("c")))
    scope = addition_scope(original, ctx)
    result = run(
        original=original,
        ctx=ctx,
        scope=scope,
        model=Model(
            [
                edit("10:30", "11:30", operation="add", activity_id=None, place_id="b"),
                edit("14:00", "15:00", operation="add", activity_id=None, place_id="c"),
            ]
        ),
    )
    learned = learn(result, RepairBudget(monotonic() + 600), 1)
    assert learned.status == "REJECTED"
    assert {r["place_id"] for r in learned.conflict_records} == {"b"}
    assert any(
        r["place_id"] == "c" and r["outcome"] == "proposed_not_adopted"
        for r in learned.presentation_history
    )


def test_changed_window_reintroduces_presented_candidate_without_ineligibility():
    original, ctx, scope = setup()
    budget = RepairBudget(monotonic() + 600)
    first = asyncio.run(prepare_candidates(ctx, scope, budget, original=original))
    budget.presentation_history = [
        {"signature": a.opportunity_signature} for a in first.authorizations
    ]
    budget.feedback_kind = "no_op_patch"
    altered = original.model_copy(deep=True)
    altered.days[0].activities[0].end_time += timedelta(minutes=15)
    next_preparation = asyncio.run(prepare_candidates(ctx, scope, budget, original=altered))
    assert any(r["unpresented"] for r in next_preparation.target_opportunities)
    assert {a.place_id for a in first.authorizations} == {
        a.place_id for a in next_preparation.authorizations
    }


def tokyo_fixture():
    from datetime import date
    from pathlib import Path

    from backend.app.evidence.models import PlaceEvidence, RouteEvidence
    from backend.app.policies.trip_dates import create_trip_date_window
    from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements
    from backend.app.schemas.itinerary import Itinerary
    from backend.app.versions.v3.models import ValidationPolicy
    from backend.app.versions.v3.repair_models import (
        RepairCandidate,
        RepairScope,
        ValidationContext,
    )
    from backend.app.versions.v3.repair_schedule import ScheduleState

    saved = json.loads(
        (Path(__file__).parents[2] / "fixtures/v3/tokyo_api_feedback.json").read_text()
    )
    places = tuple(PlaceEvidence.model_validate(x) for x in saved["places"])
    # The saved acquired Odaiba details/route are supplied as already available evidence,
    # not a replayed provider call. Other historical business data remains unchanged.
    ctx = ValidationContext(
        contract=InterpretedTripRequirements.model_validate(saved["contract"]),
        window=create_trip_date_window(date(2026, 9, 24)),
        places=places,
        original_supply_ids=tuple(saved["original_supply_ids"]),
        identity_ledger=tuple(
            RepairCandidate(place=p, origin="discovered", provenance=(p.source_ref,))
            for p in places
            if p.place_id not in saved["original_supply_ids"]
        ),
        schedule=ScheduleState.model_validate(saved["schedule"]),
        route_evidence=tuple(RouteEvidence.model_validate(x) for x in saved["routes"]),
        policy=ValidationPolicy(review_targets={"coverage", "overfull"}),
    )
    # Candidate-anchor matrices were not retained in the CLI record. Synthetic support
    # preserves the observed five selectable identities solely for control-flow replay.
    # It is not historical Google evidence and none of these routes is adopted by the patches.
    scheduled = {a["source_place_id"] for d in saved["draft"]["days"] for a in d["activities"]}
    unused = set(saved["original_supply_ids"]) - scheduled
    template = ctx.route_evidence[0]
    synthetic = template.model_copy(
        update={
            "source_ref": "fixture:synthetic_candidate_route_context",
            "elements": [
                template.elements[0].model_copy(
                    update={
                        "origin_place_id": anchor,
                        "destination_place_id": candidate,
                    }
                )
                for anchor in scheduled
                for candidate in unused
            ],
        }
    )
    ctx = ctx.model_copy(update={"route_evidence": (*ctx.route_evidence, synthetic)})
    return (
        saved,
        Itinerary.model_validate(saved["draft"]),
        ctx,
        RepairScope.model_validate(saved["scope"]),
    )


def test_tokyo_partial_then_noop_retains_best_at_bounded_stop():
    saved, original, ctx, scope = tokyo_fixture()
    model = SequenceModel([p["edits"] for p in saved["patches"]] + [[]])
    result = stage(model, original, ctx, scope, policy=policy(max_model_calls=3, max_rounds=3))
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert model.calls == 3
    assert result.reason == "round_or_model_limit"
    assert result.rounds[0].result.status == "ACCEPTED_PARTIAL"
    assert result.rounds[1].result.feedback_kind == "no_op_patch"
    assert result.final == result.rounds[0].adopted
    assert result.rounds[-1].result.model_attempted is True
    assert not result.conflict_records
    assert len(result.rounds[1].result.candidate_preparation.input_candidates) == 5


def test_tokyo_third_round_gets_unpresented_legal_candidate_and_keeps_adoption():
    saved, original, ctx, scope = tokyo_fixture()
    model = SequenceModel([p["edits"] for p in saved["patches"]])
    # Synthetic pending Details response, explicitly not historical Google evidence.
    from backend.tests.versions.v3.test_repair import Places, selection

    class NearbyDetails(Places):
        async def get_place_details(self, request):
            from backend.app.integrations.models import LatLng

            dto = await super().get_place_details(request)
            return dto.model_copy(
                update={"location": LatLng(latitude=35.68948, longitude=139.69168)}
            )

    item = selection("synthetic_new")
    item = item.model_copy(
        update={
            "candidate": item.candidate.model_copy(
                update={
                    "latitude": 35.68948,
                    "longitude": 139.69168,
                }
            )
        }
    )
    provider = NearbyDetails()
    result = stage(model, original, ctx, scope, pool=(item,), places_provider=provider)
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert model.calls == 3
    assert "synthetic_new" in {c["place_id"] for c in model.inputs[2]["addition_candidates"]}
    assert "synthetic_new" not in {c["place_id"] for c in model.inputs[1]["addition_candidates"]}
    assert result.final == result.rounds[0].adopted


def test_multi_target_exploration_uses_both_dates_and_records_no_results():
    from backend.tests.versions.v3.test_repair import two_day_case

    original, _, _ = two_day_case((place(), place("b"), place("c")))
    ctx = discovery_context()
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(
                update={
                    "requirements": ctx.contract.requirements.model_copy(
                        update={"end_date": DAY + timedelta(days=1)}
                    )
                }
            )
        }
    )
    scope = addition_scope(original, ctx)
    budget = RepairBudget(monotonic() + 600)
    first = asyncio.run(prepare_candidates(ctx, scope, budget, original=original))
    budget.presentation_history = [
        {"signature": a.opportunity_signature} for a in first.authorizations
    ]
    budget.feedback_kind = "no_op_patch"
    provider = CandidateSearch(ids=())
    prep = asyncio.run(
        prepare_candidates(
            ctx, scope, budget, original=original, provider=provider, intent_ids=("discovery_1",)
        )
    )
    assert provider.searches == 2
    assert (
        len(
            {
                r["date"]
                for r in prep.discovery_opportunities
                if r["status"] == "attempted_or_cached"
            }
        )
        == 2
    )
    assert all(r["presented"] > 0 for r in prep.target_opportunities)
