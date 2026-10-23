"""Rich completion through the production Repair stage and V3 runner."""

import asyncio
import json
from datetime import timedelta
from time import monotonic

import pytest

from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.services.preference_interpretation import empty_preference_draft
from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_service import run_repair_stage
from backend.app.versions.v3.wiring import operation_scope
from backend.tests.versions.v3.test_repair import Model, Routes
from backend.tests.versions.v3.test_repair_search import scenario
from backend.tests.versions.v3.test_soft_pace import pace_contract
from backend.tests.versions.v3.test_wiring import ManyPlaces, execute, primary
from backend.tests.versions.v3.test_wiring import Model as RunnerModel


def rich_scenario(counts):
    original, ctx, _ = scenario(counts)
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(
                update={"daily_pace": pace_contract("rich").daily_pace}
            )
        }
    )
    return original, ctx


def repair(original, ctx, **kwargs):
    scope = operation_scope(original, assess(original, ctx), context=ctx)
    assert scope is not None
    return asyncio.run(
        run_repair_stage(
            original,
            ctx,
            scope,
            model=kwargs.pop("model", Model()),
            routes_provider=Routes(),
            request_deadline=kwargs.pop("request_deadline", monotonic() + 600),
            **kwargs,
        )
    )


def test_three_visits_with_unverified_opening_are_not_full_repair_success():
    original, ctx = rich_scenario((4,))
    result = repair(original, ctx)
    assert len(result.final.days[0].activities) == 3
    assert result.soft_pace["target_state"] == "reached"
    assert result.status == "ACCEPTED_PARTIAL"
    assert result.soft_pace["completion"]["status"] == "unavailable"
    assert "opening" in result.soft_pace["completion"]["unverified_checks"]


class OpenPlaces(ManyPlaces):
    async def get_place_details(self, request):
        response = await super().get_place_details(request)
        return response.model_copy(
            update={
                "current_opening_hours": None,
                "regular_opening_hours": {
                    "periods": [
                        {"open": {"day": day, "hour": 7}, "close": {"day": day, "hour": 23}}
                        for day in range(7)
                    ]
                },
            }
        )


def rich_model(
    counts=(3, 3),
    *,
    overlap=False,
    unknown=False,
    missing_day=False,
    behavior="failure",
    fields=None,
):
    initial = primary(overlap=False)
    for offset, (day, count) in enumerate(zip(initial.days, counts, strict=True)):
        sample = day.activities[0]
        day.activities = [
            sample.model_copy(
                update={
                    "activity_id": f"d{offset}_{index}",
                    "start_time": sample.start_time + timedelta(hours=3 * index),
                    "end_time": sample.end_time + timedelta(hours=3 * index),
                }
            )
            for index in range(count)
        ]
    if overlap:
        first, second = initial.days[0].activities[:2]
        second.start_time = first.end_time - timedelta(minutes=30)
    if unknown:
        initial.days[0].activities[0].activity_kind = "unknown"
    if missing_day:
        initial.days.pop()

    class RichModel(RunnerModel):
        async def generate_structured(self, **kwargs):
            if kwargs["response_schema"].__name__ == "V1Itinerary":
                supply = json.loads(
                    kwargs["user_prompt"].split("Planning candidate supply contract:\n", 1)[1]
                )
                ids = iter(supply["optional_canonical_ids"])
                for day in self.responses[0].days:
                    for activity in day.activities:
                        activity.source_place_id = next(ids)
                        activity.place_name = f"Place {activity.source_place_id}"
            return await super().generate_structured(**kwargs)

        async def generate_repair_structured(self, **kwargs):
            if self.behavior != "rich_add":
                return await super().generate_repair_structured(**kwargs)
            self.repair_calls += 1
            self.payload = json.loads(kwargs["user_prompt"])
            candidate = next(
                c
                for c in self.payload["addition_candidates"]
                if c["place_id"] not in self.payload["scheduled_coordinates"]
            )
            return {
                "edits": [
                    {
                        "operation": "add",
                        "activity_id": None,
                        "date": "2026-09-12",
                        "place_id": candidate["place_id"],
                        "start_time": "2026-09-12T16:00:00+10:00",
                        "end_time": "2026-09-12T17:00:00+10:00",
                    }
                ]
            }

    fields = dict(fields or empty_preference_draft().model_dump())
    fields["daily_pace"] = [
        {
            "date": None,
            "profile": "rich",
            "exact_count": None,
            "source_refs": [{"quote": "rich", "occurrence": 0}],
        }
    ] + [p for p in fields.get("daily_pace", ()) if p["date"] is not None]
    model = RichModel(initial, behavior=behavior)
    model.responses.insert(0, InterpretationDraft.model_validate(fields))
    return model


def run_rich(counts=(3, 3), *, review=True, text="rich", runtime_config=None, **kwargs):
    from backend.tests.request_fixtures import make_request

    model = rich_model(counts, **kwargs)
    result, model, _, _ = asyncio.run(
        execute(
            model,
            places=OpenPlaces(),
            request=make_request(text),
            quantity_review_enabled=review,
            system_deletions=True,
            runtime_config=runtime_config,
        )
    )
    return result, model


def test_runner_already_three_is_verified_without_inventing_repair_work():
    result, model = run_rich()
    assert result.v3.soft_pace["completion"]["status"] == "already_satisfied"
    assert result.v3.repair is None and model.repair_calls == 0


def test_runner_reduces_four_to_three_and_revalidates_each_day():
    result, _ = run_rich((4, 3))
    assert [len(day.activities) for day in result.itinerary.days] == [3, 3]
    assert result.v3.repair.status == "ACCEPTED_COMPLETE"
    assert result.v3.soft_pace["completion"]["status"] == "complete"
    assert result.v3.repair.soft_pace == result.v3.soft_pace


def test_runner_can_legally_add_the_third_visit_and_revalidate_every_day():
    result, _ = run_rich((2, 3), behavior="rich_add")
    assert [len(day.activities) for day in result.itinerary.days] == [3, 3]
    assert result.v3.repair.status == "ACCEPTED_COMPLETE"
    assert result.v3.soft_pace["completion"]["status"] == "complete"
    assert not result.v3.soft_pace["completion"]["blocking_findings"]


@pytest.mark.parametrize("mode,count", [("exact", 2), ("exact", 4), ("minimum", 4)])
def test_runner_records_a_sourced_count_without_calling_it_the_default_rich_target(mode, count):
    from backend.tests.services.test_daily_visit_constraints import counted_draft

    fields = counted_draft(count, mode=mode).model_dump()
    text = "rich. " + fields["semantic_requirements"][0]["source_refs"][0]["quote"]
    result, _ = run_rich((count, 3), fields=fields, text=text)
    completion = result.v3.soft_pace["completion"]
    assert completion["days"][0]["state"] == "source_overridden"
    assert completion["days"][0]["target_count"] == count
    assert completion["days"][0]["count"] == count
    assert completion["days"][1]["state"] == "satisfied"
    assert result.v3.repair is None


def test_runner_unmet_sourced_soft_count_stays_residual():
    from backend.tests.services.test_daily_visit_constraints import counted_draft

    fields = counted_draft(2).model_dump()
    fields["semantic_requirements"][0]["strength"] = "medium"
    fields["daily_visit_constraints"][0]["strength"] = "soft"
    text = "rich. " + fields["semantic_requirements"][0]["source_refs"][0]["quote"]
    result, _ = run_rich((1, 3), fields=fields, text=text)
    completion = result.v3.soft_pace["completion"]
    assert completion["status"] == "partial"
    assert completion["days"][0]["state"] == "residual"
    assert completion["days"][0]["target_count"] == 2


def test_runner_sourced_full_day_rest_retains_zero_without_default_rich_success():
    fields = empty_preference_draft().model_dump()
    fields["time_protections"] = [
        {
            "dates": ["2026-09-12"],
            "full_day": True,
            "start_time": None,
            "end_time": None,
            "status": "fixed",
            "reason": None,
            "source_refs": [{"quote": "Rest all day on 2026-09-12", "occurrence": 0}],
        }
    ]
    result, _ = run_rich((0, 3), fields=fields, text="rich. Rest all day on 2026-09-12")
    day = result.v3.soft_pace["completion"]["days"][0]
    assert (day["count"], day["target_count"], day["state"]) == (0, 0, "source_overridden")


@pytest.mark.parametrize("limit", ["deadline", "rounds"])
def test_repair_limits_preserve_the_retained_itinerary_and_unmet_daily_target(limit):
    from backend.tests.versions.v3.test_multiround import policy

    original, ctx = rich_scenario((2, 4))
    result = repair(
        original,
        ctx,
        model=Model([]),
        policy=policy(max_rounds=1, max_model_calls=1, max_deletion_attempts=0),
        request_deadline=monotonic() - 1 if limit == "deadline" else monotonic() + 600,
    )
    assert result.final == original
    assert result.status in {"SKIPPED", "REJECTED"}
    assert result.soft_pace["completion"]["status"] == "partial"


def test_runner_keeps_an_unresolved_dated_pace_in_rich_completion():
    fields = empty_preference_draft().model_dump()
    fields["daily_pace"] = [
        {
            "date": "2026-09-12",
            "profile": "unresolved",
            "exact_count": None,
            "source_refs": [{"quote": "unclear first-day pace", "occurrence": 0}],
        }
    ]
    result, _ = run_rich(fields=fields, text="rich. unclear first-day pace")
    completion = result.v3.soft_pace["completion"]
    assert completion["status"] == "unavailable"
    assert len(completion["days"]) == 2
    assert completion["days"][0]["state"] == "unavailable"


def test_runner_keeps_a_missing_requested_date_in_completion():
    result, _ = run_rich(missing_day=True)
    completion = result.v3.soft_pace["completion"]
    assert completion["status"] == "partial"
    assert len(completion["days"]) == 2
    assert completion["days"][1]["state"] == "residual"
    assert completion["days"][1]["count"] == 0
    assert result.v3.repair.status != "ACCEPTED_COMPLETE"


@pytest.mark.parametrize("counts", [(2, 3), (2, 4)])
def test_runner_residual_day_cannot_be_hidden_by_an_average_or_another_improvement(counts):
    result, _ = run_rich(counts)
    assert result.v3.soft_pace["completion"]["status"] == "partial"
    assert result.v3.soft_pace["completion"]["days"][0]["state"] == "residual"
    assert result.v3.repair.status != "ACCEPTED_COMPLETE"


@pytest.mark.parametrize(
    "kwargs, status",
    [
        ({"review": False}, "not_attempted"),
        ({"overlap": True}, "partial"),
        ({"unknown": True}, "unavailable"),
    ],
)
def test_runner_does_not_report_success_when_review_or_required_checks_are_missing(kwargs, status):
    result, _ = run_rich(**kwargs)
    assert result.v3.soft_pace["completion"]["status"] == status
    assert result.v3.repair is None or result.v3.repair.status != "ACCEPTED_COMPLETE"
