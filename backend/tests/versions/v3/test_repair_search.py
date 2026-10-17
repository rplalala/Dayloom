"""Bounded Repair search behavior through its production stage."""

import asyncio
from datetime import timedelta
from time import monotonic

from backend.app.schemas.itinerary import ItineraryDay
from backend.app.versions.v3.models import ValidationPolicy
from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_service import run_repair_stage
from backend.app.versions.v3.wiring import operation_scope
from backend.tests.versions.v3.test_multiround import SequenceModel, policy
from backend.tests.versions.v3.test_repair import Routes, context, edit
from backend.tests.versions.v3.test_soft_pace import pace_contract
from backend.tests.versions.v3.test_validation import DAY, activity, draft, place


def scenario(counts=(3, 2, 3)):
    days = []
    ids = []
    for offset, count in enumerate(counts):
        items = []
        for index in range(count):
            aid = f"d{offset}_{index}"
            ids.append(aid)
            a = activity(aid, aid, f"{9 + index * 3:02d}:00", f"{10 + index * 3:02d}:00")
            items.append(
                a.model_copy(
                    update={
                        "start_time": a.start_time + timedelta(days=offset),
                        "end_time": a.end_time + timedelta(days=offset),
                    }
                )
            )
        days.append(ItineraryDay(date=DAY + timedelta(days=offset), activities=items))
    original = draft().model_copy(update={"days": days, "end_date": days[-1].date})
    req = pace_contract()
    req = req.model_copy(
        update={
            "requirements": req.requirements.model_copy(
                update={
                    "end_date": days[-1].date,
                }
            )
        }
    )
    ctx = context(
        req,
        places=tuple(place(i) for i in ids),
        original_supply_ids=tuple(ids),
        policy=ValidationPolicy(review_targets={"soft_pace"}),
    )
    return original, ctx, operation_scope(original, assess(original, ctx), context=ctx)


def deletion(aid, day):
    return edit(
        operation="delete",
        activity_id=aid,
        date=str(DAY + timedelta(days=day)),
        start=None,
        end=None,
    )


def move(aid, day, start="18:00", end="19:00"):
    date = DAY + timedelta(days=day)
    return edit(
        operation="move",
        activity_id=aid,
        date=str(date),
        start_time=f"{date}T{start}:00+00:00",
        end_time=f"{date}T{end}:00+00:00",
    )


def execute(responses, *, counts=(3, 2, 3), **kwargs):
    original, ctx, scope = scenario(counts)
    # Isolate model-authored intermediate paths from independently tested system deletions.
    kwargs["policy"] = kwargs.get("policy", policy()).model_copy(
        update={"max_deletion_attempts": 0}
    )
    model = SequenceModel(responses)
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=model,
            routes_provider=Routes(),
            request_deadline=monotonic() + 600,
            **kwargs,
        )
    )
    return result, model


def test_equal_aggregate_move_can_lead_to_best_delivery():
    result, model = execute(
        [
            [move("d0_2", 1)],
            [deletion("d0_2", 1)],
            [deletion("d2_2", 2)],
        ]
    )
    assert [len(d.activities) for d in result.final.days] == [2, 2, 2], result.reason
    assert model.calls == 3
    assert [len(d.activities) for d in result.rounds[0].adopted.days] == [2, 3, 3]
    assert not result.rounds[0].best_promoted
    assert result.rounds[0].exploration_transition
    assert result.soft_pace["target_state"] == "reached"
    assert result.search_version == 1
    assert result.selected_round_index == 3
    assert [len(d.activities) for d in result.original.days] == [3, 2, 3]


def test_worse_exploration_can_later_improve():
    result, model = execute(
        [
            [move("d0_3", 1)],
            [deletion("d0_3", 1)],
        ],
        counts=(4, 2, 3),
        policy=policy(max_rounds=2, max_model_calls=2),
    )
    assert model.calls == 2
    assert [len(d.activities) for d in result.rounds[0].adopted.days] == [3, 3, 3]
    assert not result.rounds[0].best_promoted
    assert [len(d.activities) for d in result.final.days] == [3, 2, 3]
    assert result.soft_pace["before"]["mean_penalty"] == 110 / 3
    assert result.soft_pace["after"]["mean_penalty"] == 80 / 3


def test_worse_terminal_state_returns_best_complete_context():
    result, _ = execute(
        [
            [deletion("d2_3", 2)],
            [move("d0_3", 1)],
        ],
        counts=(4, 2, 4),
        policy=policy(max_rounds=2, max_model_calls=2),
    )
    assert result.rounds[1].exploration_transition
    assert not result.rounds[1].best_promoted
    assert result.final == result.rounds[0].adopted
    assert result.final != result.rounds[1].adopted
    assert result.schedule == result.rounds[0].result.schedule
    assert result.selected_round_index == 1
    delivered_ids = {a.activity_id for d in result.final.days for a in d.activities}
    assert all(
        t.from_activity_id in delivered_ids and t.to_activity_id in delivered_ids
        for t in result.final.transfers
    )
    assert result.soft_pace["after"]["mean_penalty"] == 110 / 3


def test_sixth_eligible_proposal_and_equivalent_failure_suppression():
    from backend.tests.versions.v3.test_repair import overlap_draft, scope_for

    class Explanations(SequenceModel):
        async def generate_repair_structured(self, **kwargs):
            value = await super().generate_repair_structured(**kwargs)
            value["target_dispositions"] = [
                {
                    "target_id": self.inputs[-1]["scope"]["target_ids"][0],
                    "disposition": "unresolved",
                    "reason": f"Different words {self.calls}",
                }
            ]
            return value

    original, ctx = overlap_draft(), context()
    unchanged = [edit("10:30", "11:30")]
    model = Explanations([unchanged] * 5 + [[edit()]])
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope_for(original, ctx),
            model=model,
            routes_provider=Routes(),
            request_deadline=monotonic() + 600,
        )
    )
    assert model.calls == result.counters["model"] == 6
    assert result.status == "ACCEPTED_COMPLETE"
    assert result.rounds[2].result.reason == "equivalent_proposal_suppressed"
    assert not result.rounds[2].result.components
    assert model.inputs[1]["feedback"]["previous_status"] == "REJECTED"
    assert model.inputs[5]["feedback"]["tried_operations"]


def test_repeated_exploration_state_is_suppressed_without_stopping_next_alternative():
    original, ctx, scope = scenario((3,))
    scope = scope.model_copy(
        update={
            "permissions": tuple(
                p.model_copy(update={"operations": p.operations | {"retime"}})
                for p in scope.permissions
            )
        }
    )
    model = SequenceModel(
        [
            [edit("18:00", "19:00", activity_id="d0_2")],
            [edit("15:00", "16:00", activity_id="d0_2")],
            [deletion("d0_2", 0)],
        ]
    )
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=model,
            routes_provider=Routes(),
            request_deadline=monotonic() + 600,
            policy=policy(max_deletion_attempts=0),
        )
    )
    assert result.rounds[0].exploration_transition
    assert not result.rounds[1].exploration_transition
    assert result.rounds[1].result.reason == "repeated_exploration_state_suppressed"
    assert model.calls == 3 and len(result.final.days[0].activities) == 2


def test_deadline_after_exploration_keeps_best_and_counts_failed_send():
    original, ctx, scope = scenario((4, 2, 4))
    now = [100.0]

    class Expiring(SequenceModel):
        async def generate_repair_structured(self, **kwargs):
            if self.calls == 2:
                self.calls += 1
                now[0] = 500.0
                raise TimeoutError("controlled stage expiry")
            return await super().generate_repair_structured(**kwargs)

    model = Expiring([[deletion("d2_3", 2)], [move("d0_3", 1)]])
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=model,
            routes_provider=Routes(),
            request_deadline=1000,
            clock=lambda: now[0],
            policy=policy(max_deletion_attempts=0),
        )
    )
    assert result.final == result.rounds[0].adopted
    assert result.rounds[1].exploration_transition and not result.rounds[1].best_promoted
    assert model.calls == result.counters["model"] == 3
    assert result.timing["stage_deadline"] == 520
    assert result.reason == "model_failed_no_retry"
    assert result.rounds[-1].result.reason == "repair_timeout"
    assert result.counters["final_main_visits"] == 9


def test_known_date_improvement_survives_unrelated_unavailable_pace():
    original, ctx, _ = scenario((3, 2))
    unknown = ctx.contract.daily_pace[0].model_copy(
        update={
            "date": DAY + timedelta(days=1),
            "profile": "unresolved",
        }
    )
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(
                update={
                    "daily_pace": (*ctx.contract.daily_pace, unknown),
                }
            )
        }
    )
    scope = operation_scope(original, assess(original, ctx), context=ctx)
    model = SequenceModel([])
    result = asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=model,
            routes_provider=Routes(),
            request_deadline=monotonic() + 600,
        )
    )
    assert [len(d.activities) for d in result.final.days] == [2, 2]
    assert model.calls == 0
    assert result.soft_pace["target_state"] == "unavailable"
    assert result.soft_pace["comparable"]["dates"] == [str(DAY)]
    assert result.soft_pace["comparable"]["before_total"] == 40
    assert result.soft_pace["comparable"]["after_total"] == 0
