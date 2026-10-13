"""Selected Repair state through the complete V3 production graph."""

import asyncio
import json
from datetime import timedelta

import pytest

from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.schemas.itinerary import ItineraryDay
from backend.app.services.preference_interpretation import empty_preference_draft
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v3.test_multiround import policy
from backend.tests.versions.v3.test_wiring import ManyPlaces, Model, execute, primary


@pytest.mark.parametrize(
    "promote,terminal", [(False, "failure"), (True, "failure"), (False, "budget")]
)
def test_combined_search_returns_selected_primary_and_one_nearby_phase(promote, terminal):
    from uuid import uuid4

    from backend.app.observability.run_trace import NullRunTracer
    from backend.app.runtime.config_loader import load_runtime_config

    initial = primary(False)
    template = initial.days[0].activities[0]
    days = []
    for offset, count in enumerate((4, 2, 4)):
        date = initial.start_date + timedelta(days=offset)
        items = [
            template.model_copy(
                update={
                    "activity_id": f"d{offset}_{i}",
                    "start_time": template.start_time.replace(hour=9 + 2 * i)
                    + timedelta(days=offset),
                    "end_time": template.start_time.replace(hour=10 + 2 * i)
                    + timedelta(days=offset),
                }
            )
            for i in range(count)
        ]
        days.append(ItineraryDay(date=date, activities=items))
    initial = initial.model_copy(update={"days": days, "end_date": days[-1].date})

    class SearchModel(Model):
        async def generate_structured(self, **kwargs):
            if kwargs["response_schema"].__name__ == "V1Itinerary":
                supply = json.loads(
                    kwargs["user_prompt"].split("Planning candidate supply contract:\n", 1)[1]
                )
                ids = iter(supply["optional_canonical_ids"])
                for day in self.responses[0].days:
                    for a in day.activities:
                        a.source_place_id = next(ids)
                        a.place_name = f"Place {a.source_place_id}"
            return await super().generate_structured(**kwargs)

        async def generate_repair_structured(self, **kwargs):
            self.repair_calls += 1
            payload = json.loads(kwargs["user_prompt"])
            if self.repair_calls == 1:
                return {"edits": []}
            if self.repair_calls == 2:
                assert payload["proposal_strategy"] == "replan"
                date = days[1].date
                edits = [
                    {
                        "operation": "move",
                        "activity_id": "d2_3",
                        "date": str(date),
                        "place_id": None,
                        "start_time": f"{date}T15:00:00+10:00",
                        "end_time": f"{date}T16:00:00+10:00",
                    }
                ]
                if promote:
                    edits.append(
                        {
                            "operation": "delete",
                            "activity_id": "d0_2",
                            "date": str(days[0].date),
                            "place_id": None,
                            "start_time": None,
                            "end_time": None,
                        }
                    )
                return {"edits": edits}
            if terminal == "budget":
                return {"edits": []}
            raise RuntimeError("controlled terminal proposal failure")

    class Trace(NullRunTracer):
        def __init__(self):
            super().__init__(uuid4())
            self.rounds = []
            self.nearby_phases = 0

        def event(self, name, value=None):
            if name == "v3_repair_round":
                self.rounds.append(value)
            if name == "reference_discovery_completed":
                self.nearby_phases += 1

    fields = empty_preference_draft().model_dump()
    fields.update(
        visit_requirements=[],
        time_protections=[],
        daily_pace=[
            {
                "date": None,
                "profile": "relaxed",
                "exact_count": None,
                "source_refs": [{"quote": "relaxed", "occurrence": 0}],
            }
        ],
    )
    model = SearchModel(initial)
    model.responses.insert(0, InterpretationDraft.model_validate(fields))
    config = load_runtime_config().model_copy(update={"v3_repair": policy(max_deletion_attempts=1)})
    places, trace = ManyPlaces(), Trace()
    result, model, places, _ = asyncio.run(
        execute(
            model,
            places=places,
            request=make_request("relaxed", end_date=initial.end_date),
            runtime_config=config,
            quantity_review_enabled=True,
            tracer=trace,
            system_deletions=True,
        )
    )
    repair = result.v3.repair
    strategies = ["system_delete", "local", "replan", "local"] + (
        ["replan"] * 3 if terminal == "budget" else []
    )
    assert [r.strategy for r in repair.rounds] == strategies
    assert repair.selected_round_index == (3 if promote else 1)
    assert repair.rounds[2].exploration_transition and repair.rounds[2].best_promoted == promote
    assert [len(d.activities) for d in result.itinerary.days] == (
        [2, 3, 3] if promote else [3, 2, 4]
    )
    assert repair.reason == (
        "model_failed_no_retry" if terminal == "failure" else "round_or_model_limit"
    )
    assert repair.counters["model"] == model.repair_calls == (3 if terminal == "failure" else 6)
    assert repair.counters["deterministic_attempts"] == 1
    assert result.v3.final_report == repair.adopted_report
    assert result.itinerary.days == result.v3.final_primary.days
    assert result.v3.soft_pace["after"]["mean_penalty"] == (80 if promote else 110) / 3
    assert [len(d.activities) for d in result.v3.draft.days] == [4, 2, 4]
    assert [r["strategy"] for r in trace.rounds] == strategies
    assert [r["best_promoted"] for r in trace.rounds] == [True, False, promote] + [False] * (
        len(strategies) - 3
    )
    activities = {a.activity_id: a for d in result.itinerary.days for a in d.activities}
    assert activities["d2_3"].start_time.date() == days[1 if promote else 2].date
    assert all(
        t.from_activity_id in activities and t.to_activity_id in activities
        for t in result.itinerary.transfers
    )
    assert all(
        a.place_name
        == next(p.name for p in result.v3.final_places if p.place_id == a.source_place_id)
        for a in activities.values()
    )
    expected_legs = {
        (left.activity_id, right.activity_id)
        for day in result.itinerary.days
        for ordered in [sorted(day.activities, key=lambda a: a.start_time)]
        for left, right in zip(ordered, ordered[1:], strict=False)
    }
    assert {
        (r["from_activity_id"], r["to_activity_id"]) for r in result.itinerary.route_diagnostics
    } == expected_legs
    assert {
        (t.from_activity_id, t.to_activity_id) for t in result.itinerary.transfers
    } == expected_legs
    assert places.nearby
    assert trace.nearby_phases == 1
    assert repair.selected_semantic_assessments
    assert result.semantic_assessment["calls"] == len(model.semantic_calls)
    assert repair.usage_status == "partial_or_unavailable"
    assert repair.usage == {}
    if promote:
        assert repair.spatial["legs"]


def test_production_default_system_deletion_preserves_best_after_later_failure():
    model = Model(behavior="failure")
    result, model, places, _ = asyncio.run(execute(model, system_deletions=True))
    repair = result.v3.repair
    assert repair.effective_policy["max_deletion_attempts"] == 12
    assert repair.selected_round_index == 1
    assert [row.strategy for row in repair.rounds] == ["system_delete", "local"]
    assert model.repair_calls == repair.counters["model"] == 1
    assert repair.counters["deterministic_attempts"] == 1
    assert len(result.itinerary.days[0].activities) == 1
    assert result.v3.final_report == repair.adopted_report
    assert repair.selected_semantic_assessments
    assert places.nearby
