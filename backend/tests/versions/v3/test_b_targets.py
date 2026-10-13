"""B actual repair service fixtures; external boundaries never execute."""

import asyncio
from datetime import timedelta
from time import monotonic

import pytest

from backend.app.schemas.itinerary import ItineraryDay
from backend.app.versions.v3.models import ValidationPolicy
from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_budget import configured_policy
from backend.app.versions.v3.repair_schedule import build_schedule
from backend.app.versions.v3.repair_service import run_repair_stage
from backend.app.versions.v3.repair_targets import prepare_blank_windows
from backend.app.versions.v3.wiring import operation_scope
from backend.tests.versions.v3.test_repair import Model, context
from backend.tests.versions.v3.test_validation import DAY, activity, binding, contract, draft, place


def visit(aid, pid, day=0, start="09:00", end="10:00"):
    a = activity(aid, pid, start, end)
    return a.model_copy(
        update={
            "start_time": a.start_time + timedelta(days=day),
            "end_time": a.end_time + timedelta(days=day),
        }
    )


def setup(
    rows,
    *,
    reviews=("coverage", "overfull"),
    required=None,
    extra_days=0,
    protections=(),
):
    original = draft(rows[0])
    original.end_date = DAY + timedelta(days=len(rows) - 1 + extra_days)
    original.days = [
        ItineraryDay(date=DAY + timedelta(days=i), activities=items) for i, items in enumerate(rows)
    ]
    c = contract(required) if required else contract()
    c = c.model_copy(
        update={
            "visit_requirements": (),
            "time_protections": protections,
            "requirements": c.requirements.model_copy(update={"end_date": original.end_date}),
        }
    )
    places = tuple(place(pid) for pid in "abcdefghijk")
    ctx = context(
        c,
        places=places,
        original_supply_ids=tuple(p.place_id for p in places),
        named_resolutions=(binding(),) if required else (),
        policy=ValidationPolicy(review_targets=set(reviews)),
    )
    ctx = ctx.model_copy(
        update={"schedule": build_schedule(original, c, places, primary_generated=True)}
    )
    policy = configured_policy().model_copy(update={"overfull_review_enabled": True})
    ctx = ctx.model_copy(update={"schedule": prepare_blank_windows(original, ctx, policy)})
    scope = operation_scope(
        original, assess(original, ctx), mode="WALK", context=ctx, policy=policy
    )
    if scope:
        scope = scope.model_copy(
            update={
                "window_roots": tuple(
                    w.root_activity_id
                    for w in ctx.schedule.windows
                    if w.start.date() in scope.dates
                )
            }
        )
    return original, ctx, scope, policy


def edit(operation, aid=None, pid=None, day=0, start=None, end=None):
    date = DAY + timedelta(days=day)
    return dict(
        operation=operation,
        activity_id=aid,
        place_id=pid,
        date=str(date),
        start_time=f"{date}T{start}:00+00:00" if start else None,
        end_time=f"{date}T{end}:00+00:00" if end else None,
    )


def run(args, patches):
    original, ctx, scope, policy = args
    # Exercise these explicit model patches independently of application proposals.
    policy = policy.model_copy(update={"max_deletion_attempts": 0})

    class Sequence(Model):
        async def generate_repair_structured(self, **kwargs):
            self.calls += 1
            data = patches[min(self.calls - 1, len(patches) - 1)]
            if isinstance(data, Exception):
                raise data
            return {"edits": data}

    model = Sequence()
    result = asyncio.run(
        run_repair_stage(
            original, ctx, scope, policy=policy, model=model, request_deadline=monotonic() + 600
        )
    )
    return result, model


@pytest.mark.parametrize("missing", [False, True])
def test_blank_and_missing_date_get_real_visits(missing):
    rows = [[visit("a", "a"), visit("b", "b", start="12:00", end="13:00")]]
    if not missing:
        rows.append([])
    args = setup(rows, extra_days=int(missing))
    result, model = run(
        args,
        [
            [
                edit("add", pid="c", day=1, start="10:00", end="11:00"),
                edit("add", pid="d", day=1, start="12:00", end="13:00"),
            ]
        ],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert len(result.final.days[1].activities) == 2 and model.calls == 1
    assert result.original == args[0]


def repeated(required=None):
    return setup(
        [
            [visit("a1", "a"), visit("b", "b", start="12:00", end="13:00")],
            [visit("a2", "a", 1), visit("c", "c", 1, "12:00", "13:00")],
        ],
        reviews=(),
        required=required,
    )


def test_deduplicate_and_compensate_without_global_quantity_policy():
    result, _ = run(
        repeated(),
        [[edit("delete", "a2", day=1), edit("add", pid="d", day=1, start="09:00", end="10:00")]],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.related_targets and all(t.status == "resolved" for t in result.related_targets)
    assert result.related_targets[0].activated_by == ("a2",)


def test_deduplication_without_compensation_is_atomic_rejection():
    args = repeated()
    result, _ = run(args, [[edit("delete", "a2", day=1)]])
    assert result.status == "REJECTED" and result.final == args[0]
    assert result.reason == "round_or_model_limit"
    assert "compensation" in result.rounds[0].result.reason
    assert result.rounds[0].result.comparison is not None


def test_required_extra_copy_can_be_removed_but_last_satisfaction_cannot():
    args = repeated("REQUIRED")
    result, _ = run(
        args,
        [[edit("delete", "a2", day=1), edit("add", pid="d", day=1, start="09:00", end="10:00")]],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    bad, _ = run(args, [[edit("delete", "a1"), edit("delete", "a2", day=1)]])
    assert bad.status == "REJECTED" and bad.final == args[0]


def crowded():
    rows = [
        [
            visit(pid, pid, start=f"{9 + i:02d}:00", end=f"{9 + i:02d}:30")
            for i, pid in enumerate("abcdef")
        ],
        [visit("g", "g", 1)],
    ]
    return setup(rows, reviews=("overfull",))


def test_overfull_can_end_at_five():
    result, _ = run(crowded(), [[edit("delete", "f")]])
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert len(result.final.days[0].activities) == 5


def test_adjacent_move_preserves_id_duration_and_checks_destination():
    args = crowded()
    result, _ = run(args, [[edit("move", "f", day=1, start="12:00", end="12:30")]])
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    moved = next(a for a in result.final.days[1].activities if a.activity_id == "f")
    assert moved.source_place_id == "f" and moved.end_time - moved.start_time == timedelta(
        minutes=30
    )
    assert result.rounds[0].result.spatial["legs"]
    rejected, _ = run(args, [[edit("move", "f", day=1, start="09:15", end="09:45")]])
    assert rejected.final == args[0]


def test_excluded_removal_activates_child_and_next_round_fills_it():
    args = setup(
        [[visit("a", "a"), visit("b", "b", start="12:00", end="13:00")]],
        reviews=(),
        required="EXCLUDED",
    )
    result, model = run(
        args, [[edit("delete", "a")], [edit("add", pid="c", start="09:00", end="10:00")]]
    )
    assert model.calls == 2, result.reason
    assert result.rounds[0].result.status == "ACCEPTED_PARTIAL"
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert all(t.status == "resolved" for t in result.related_targets)


def test_later_failure_keeps_excluded_removal_and_reports_child():
    args = setup(
        [[visit("a", "a"), visit("b", "b", start="12:00", end="13:00")]],
        reviews=(),
        required="EXCLUDED",
    )
    result, _ = run(args, [[edit("delete", "a")], RuntimeError("fixture failure")])
    assert result.status == "ACCEPTED_PARTIAL"
    assert result.final == result.rounds[0].adopted
    assert any(t.status == "unresolved" for t in result.related_targets)


def test_conditional_addition_cannot_activate_itself():
    args = repeated()
    result, _ = run(args, [[edit("add", pid="d", day=1, start="15:00", end="16:00")]])
    assert result.status == "REJECTED" and result.final == args[0]


def test_unassessed_visit_contract_does_not_grant_destructive_review():
    original, ctx, _, policy = repeated()
    ctx = ctx.model_copy(
        update={"contract": ctx.contract.model_copy(update={"visit_requirements": None})}
    )
    assert operation_scope(original, assess(original, ctx), context=ctx, policy=policy) is None


def test_explicit_count_and_date_obligations_protect_visits():
    from backend.app.schemas.interpreted_requirements import VisitRequirement

    original, ctx, scope, policy = repeated("REQUIRED")
    n = ctx.contract.named_places[0]
    rule = VisitRequirement(
        place_text=n.place_text,
        requirement_id=n.requirement_id,
        minimum_visits=2,
        dates=(DAY, DAY + timedelta(days=1)),
        status="executable",
        reason=None,
        source_refs=n.source_refs,
    )
    ctx = ctx.model_copy(
        update={"contract": ctx.contract.model_copy(update={"visit_requirements": (rule,)})}
    )
    assert operation_scope(original, assess(original, ctx), context=ctx, policy=policy) is None
    result, _ = run(
        (original, ctx, scope, policy),
        [[edit("delete", "a2", day=1), edit("add", pid="d", day=1, start="09:00", end="10:00")]],
    )
    assert result.status in {"REJECTED", "SKIPPED"} and result.final == original


def test_default_window_rejects_outside_hours_and_unknown_timezone():
    args = setup([[]])
    result, _ = run(args, [[edit("add", pid="a", start="08:00", end="09:00")]])
    assert result.status == "REJECTED" and result.final == args[0]
    original, ctx, _, policy = args
    ctx = ctx.model_copy(
        update={"places": tuple(p.model_copy(update={"timezone_id": None}) for p in ctx.places)}
    )
    ctx = ctx.model_copy(update={"schedule": prepare_blank_windows(original, ctx, policy)})
    assert operation_scope(original, assess(original, ctx), context=ctx, policy=policy) is None


def test_fixed_rest_overrides_blank_window():
    from backend.tests.versions.v3.test_schedule import protection

    rest = protection().model_copy(
        update={
            "start_time": __import__("datetime").time(9),
            "end_time": __import__("datetime").time(18),
        }
    )
    original, ctx, scope, _ = setup([[]], protections=(rest,))
    assert scope is None
    assert assess(original, ctx).diagnostics.days[0].distinct_main_poi_count == 0


def test_move_cannot_chain_beyond_original_source_permission():
    from backend.app.versions.v3.repair_acceptance import apply_patch
    from backend.app.versions.v3.repair_models import CandidatePreparation, RepairPatch

    args = crowded()
    result, _ = run(args, [[edit("move", "f", day=1, start="12:00", end="12:30")]])
    with pytest.raises(ValueError, match="original adjacent"):
        apply_patch(
            result.final,
            RepairPatch(edits=(edit("move", "f", day=0, start="15:00", end="15:30"),)),
            args[2],
            CandidatePreparation(),
            context=args[1],
        )


def test_repeat_moved_to_same_day_is_not_deduplication():
    args = repeated()
    result, _ = run(
        args,
        [
            [
                edit("move", "a2", day=0, start="15:00", end="16:00"),
                edit("add", pid="d", day=1, start="09:00", end="10:00"),
            ]
        ],
    )
    assert result.status == "REJECTED" and result.final == args[0]
    assert result.rounds[0].result.target_progress[0].outcome == "unresolved"


def test_unauthorized_repeat_repairs_automatically_without_optional_review():
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.tests.versions.v3.test_wiring import Model as GraphModel
    from backend.tests.versions.v3.test_wiring import execute, primary

    config = load_runtime_config()
    original = primary(False)
    a = original.days[0].activities[0]
    original.days[0].activities.append(
        a.model_copy(
            update={
                "activity_id": "b",
                "source_place_id": "poi-0-1",
                "start_time": a.start_time + timedelta(hours=3),
                "end_time": a.end_time + timedelta(hours=3),
            }
        )
    )
    second = a.model_copy(
        update={
            "activity_id": "repeat",
            "start_time": a.start_time + timedelta(days=1),
            "end_time": a.end_time + timedelta(days=1),
        }
    )
    other = second.model_copy(
        update={
            "activity_id": "c",
            "source_place_id": "poi-0-2",
            "start_time": second.start_time + timedelta(hours=3),
            "end_time": second.end_time + timedelta(hours=3),
        }
    )
    original.days = [
        original.days[0],
        ItineraryDay(date=second.start_time.date(), activities=[second, other]),
    ]

    class Model(GraphModel):
        async def generate_repair_structured(self, **kwargs):
            import json

            self.repair_calls += 1
            payload = json.loads(kwargs["user_prompt"])
            candidate = payload["addition_candidates"][0]["place_id"]
            return {
                "edits": [
                    dict(
                        operation="delete",
                        activity_id="repeat",
                        date=str(second.start_time.date()),
                        place_id=None,
                        start_time=None,
                        end_time=None,
                    ),
                    dict(
                        operation="add",
                        activity_id=None,
                        date=str(second.start_time.date()),
                        place_id=candidate,
                        start_time=second.start_time.isoformat(),
                        end_time=second.end_time.isoformat(),
                    ),
                ]
            }

    model = Model(original)
    result, model, places, runtime = asyncio.run(execute(model, runtime_config=config))
    assert result.v3.repair.status == "ACCEPTED_COMPLETE", result.v3.repair.reason
    assert result.v3.review_policy == {"quantity": False, "overfull": False, "soft_pace": False}
    assert model.repair_calls == 1 and places.nearby and runtime.closes == 1
    assert result.generation_diagnostics == result.v3.final_report.diagnostics


def test_multiple_targets_receive_their_own_geographic_discovery_opportunity():
    from backend.app.versions.v3.repair_budget import RepairBudget
    from backend.app.versions.v3.repair_candidates import prepare_candidates
    from backend.tests.versions.v3.test_repair import CandidateSearch, discovery_context

    original, ctx, scope, policy = setup(
        [[visit("a", "a")], [visit("b", "b", day=1)]], reviews=("coverage",)
    )
    discoveries = discovery_context().contract.discovery_intents
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(update={"discovery_intents": discoveries}),
            "places": (
                place("a"),
                place("b").model_copy(update={"latitude": 1.0, "longitude": 1.0}),
            ),
            "original_supply_ids": ("a", "b"),
        }
    )

    class Search(CandidateSearch):
        def __init__(self):
            super().__init__(ids=())
            self.biases = []

        async def search_text(self, request):
            self.biases.append((request.location_bias.latitude, request.location_bias.longitude))
            return await super().search_text(request)

    provider = Search()
    budget = RepairBudget(monotonic() + 600, policy=policy)
    prepared = asyncio.run(
        prepare_candidates(
            ctx,
            scope,
            budget,
            original=original,
            provider=provider,
            intent_ids=(discoveries[0].intent_id,),
        )
    )
    assert set(provider.biases) == {(0.0, 0.0), (1.0, 1.0)}
    assert budget.used["google"] == 2
    assert {r["date"] for r in prepared.discovery_opportunities if r["kind"] == "google"} == {
        str(DAY),
        str(DAY + timedelta(days=1)),
    }


def test_repeat_group_is_not_truncated_to_two_dates():
    args = setup(
        [
            [visit("a0", "a"), visit("b", "b", start="12:00", end="13:00")],
            [visit("a1", "a", day=1), visit("c", "c", day=1, start="12:00", end="13:00")],
            [visit("a2", "a", day=2), visit("d", "d", day=2, start="12:00", end="13:00")],
        ],
        reviews=(),
    )
    assert {p.activity_id for p in args[2].permissions} == {"a0", "a1", "a2"}
    result, _ = run(
        args,
        [
            [
                edit("replace", "a1", "e", 1, "09:00", "10:00"),
                edit("replace", "a2", "f", 2, "09:00", "10:00"),
            ]
        ],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason


@pytest.mark.parametrize(
    "change",
    [
        {"move_max_days": 2},
        {"daily_main_min": 0},
        {"daily_main_max": 1},
        {"blank_day_start_hour": 18},
        {"blank_day_end_hour": 0},
    ],
)
def test_b_invalid_configuration_is_rejected(change):
    from pydantic import ValidationError

    from backend.app.runtime.config_models import V3RepairConfig

    data = configured_policy().model_dump()
    data.update(change)
    with pytest.raises(ValidationError):
        V3RepairConfig.model_validate(data)


def test_move_disable_and_blank_hours_are_effective_configuration():
    original, ctx, _, policy = crowded()
    policy = policy.model_copy(update={"move_max_days": 0})
    scope = operation_scope(original, assess(original, ctx), context=ctx, policy=policy)
    assert all("move" not in p.operations for p in scope.permissions)
    original, ctx, _, policy = setup([[]], reviews=("coverage",))
    policy = policy.model_copy(update={"blank_day_start_hour": 11, "blank_day_end_hour": 16})
    state = prepare_blank_windows(original, ctx, policy)
    assert state.blank_windows[0].start.hour == 11 and state.blank_windows[0].end.hour == 16


def test_overfull_enabled_in_real_graph_and_keeps_cost_association():
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.tests.versions.v3.test_wiring import Model as GraphModel
    from backend.tests.versions.v3.test_wiring import execute, primary

    original = primary(False)
    original.days = original.days[:1]
    original.end_date = original.start_date
    a = original.days[0].activities[0]
    original.days[0].activities = [
        a.model_copy(
            update={
                "activity_id": f"item_{i}",
                "source_place_id": f"poi-0-{i}",
                "start_time": a.start_time + timedelta(hours=i),
                "end_time": a.start_time + timedelta(hours=i, minutes=30),
            }
        )
        for i in range(6)
    ]

    class Model(GraphModel):
        async def generate_structured(self, **kwargs):
            if kwargs["response_schema"].__name__ == "V1Itinerary":
                import json

                supply = json.loads(
                    kwargs["user_prompt"].split("Planning candidate supply contract:\n", 1)[1]
                )
                ids = supply["optional_canonical_ids"]
                assert len(ids) >= 6
                for item, pid in zip(self.responses[0].days[0].activities, ids, strict=False):
                    item.source_place_id = pid
            return await super().generate_structured(**kwargs)

        async def generate_repair_structured(self, **kwargs):
            self.repair_calls += 1
            return {
                "edits": [
                    dict(
                        operation="delete",
                        activity_id="item_5",
                        date=str(a.start_time.date()),
                        place_id=None,
                        start_time=None,
                        end_time=None,
                    )
                ]
            }

    cfg = load_runtime_config()
    cfg = cfg.model_copy(
        update={"v3_repair": cfg.v3_repair.model_copy(update={"overfull_review_enabled": True})}
    )
    result, model, places, runtime = asyncio.run(
        execute(
            Model(original),
            request=__import__(
                "backend.tests.request_fixtures", fromlist=["make_request"]
            ).make_request(end_date=original.end_date),
            places=__import__(
                "backend.tests.versions.v3.test_wiring", fromlist=["ManyPlaces"]
            ).ManyPlaces(),
            runtime_config=cfg,
        )
    )
    assert result.v3.repair.status == "ACCEPTED_COMPLETE", result.v3.repair.reason
    assert len(result.itinerary.days[0].activities) == 5 and model.repair_calls == 1
    assert result.itinerary.cost_projections == result.v3.draft.cost_projections
    assert result.v3.review_policy["overfull"] and places.nearby and runtime.closes == 1


def test_dedup_consumes_a_elastic_window_atomically():
    args = repeated()
    original, ctx, scope, policy = args
    placeholder = activity(
        "rest", None, "14:00", "18:00", activity_kind="free_time", place_name=None, location=None
    )
    placeholder = placeholder.model_copy(
        update={
            "start_time": placeholder.start_time + timedelta(days=1),
            "end_time": placeholder.end_time + timedelta(days=1),
        }
    )
    original.days[1].activities.append(placeholder)
    ctx = ctx.model_copy(
        update={
            "schedule": build_schedule(original, ctx.contract, ctx.places, primary_generated=True)
        }
    )
    scope = scope.model_copy(update={"window_roots": ("rest",)})
    result, _ = run(
        (original, ctx, scope, policy),
        [[edit("delete", "a2", day=1), edit("add", pid="d", day=1, start="15:00", end="16:00")]],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.window_adjustments
    times = sorted((a.start_time, a.end_time) for a in result.final.days[1].activities)
    assert all(left[1] <= right[0] for left, right in zip(times, times[1:], strict=False))


def test_move_must_not_export_overfull_problem_to_neighbor():
    rows = [
        [
            visit(p, p, start=f"{9 + i:02d}:00", end=f"{9 + i:02d}:30")
            for i, p in enumerate("abcdef")
        ],
        [
            visit(p, p, 1, start=f"{9 + i:02d}:00", end=f"{9 + i:02d}:30")
            for i, p in enumerate("ghijk")
        ],
    ]
    original, ctx, scope, policy = setup(rows, reviews=("overfull",))
    result, _ = run(
        (original, ctx, scope, policy), [[edit("move", "f", day=1, start="16:00", end="16:30")]]
    )
    assert result.status == "REJECTED" and result.final == original
    assert "overfull" in result.rounds[0].result.reason


def test_missing_date_fixed_rest_is_not_lost_by_schedule_construction():
    from datetime import time

    from backend.tests.versions.v3.test_schedule import protection

    rest = protection().model_copy(
        update={"dates": (DAY + timedelta(days=1),), "start_time": time(9), "end_time": time(18)}
    )
    original, ctx, scope, _ = setup(
        [[visit("a", "a"), visit("b", "b", start="12:00", end="13:00")]],
        reviews=("coverage",),
        extra_days=1,
        protections=(rest,),
    )
    assert scope is None
    assert any(w.start.date() == DAY + timedelta(days=1) for w in ctx.schedule.fixed)
