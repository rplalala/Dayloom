"""Long Product trips exercise the real graphs with external service doubles."""

import asyncio
import json
from datetime import date, timedelta

import pytest

from backend.app.runtime.config_loader import load_runtime_profile
from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.services.preference_interpretation import empty_preference_draft
from backend.app.versions.v1.runner import run_v1
from backend.app.versions.v2.runner import run_v2
from backend.app.versions.v3.runner import run_v3
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
from backend.tests.versions.v3.test_wiring import ManyPlaces, Model, OwnedRetrieval, primary


@pytest.mark.parametrize("version", ["v1", "v2", "v3"])
@pytest.mark.parametrize("days,expected", [(1, 9), (9, 36), (10, 40)])
def test_rich_trip_uses_demand_sized_initial_supply(version, days, expected):
    text = "Travel pace: rich."
    request = make_request(text, end_date=date(2026, 9, 12) + timedelta(days=days - 1))
    before = request.model_dump()
    data = empty_preference_draft().model_dump()
    data["daily_pace"] = [
        {
            "date": None,
            "profile": "rich",
            "exact_count": None,
            "source_refs": [{"quote": text, "occurrence": 0}],
        }
    ]

    class LongTripModel(Model):
        def __init__(self):
            super().__init__(primary(False), behavior="empty")
            self.responses.insert(0, InterpretationDraft.model_validate(data))
            self.supply = None

        async def generate_structured(self, **kwargs):
            if kwargs["response_schema"].__name__ == "V1Itinerary":
                self.supply = json.loads(
                    kwargs["user_prompt"].split("Planning candidate supply contract:\n", 1)[1]
                )
                ids = self.supply["optional_canonical_ids"]
                draft = self.responses[0]
                draft.end_date = request.end_date
                template = draft.days[0]
                activity = template.activities[0]
                draft.days = []
                for index in range(days):
                    activities = []
                    for visit in range(3):
                        pid = ids[index * 3 + visit]
                        activities.append(
                            activity.model_copy(
                                update={
                                    "activity_id": f"day-{index}-visit-{visit}",
                                    "source_place_id": pid,
                                    "place_name": f"Place {pid}",
                                    "location": f"{pid.split('-')[-1]} Sydney NSW, Australia",
                                    "start_time": activity.start_time
                                    + timedelta(days=index, hours=visit * 3),
                                    "end_time": activity.end_time
                                    + timedelta(days=index, hours=visit * 3),
                                }
                            )
                        )
                    draft.days.append(
                        template.model_copy(
                            update={
                                "date": request.start_date + timedelta(days=index),
                                "activities": activities,
                            }
                        )
                    )
            return await super().generate_structured(**kwargs)

    class FullSearchPlaces(ManyPlaces):
        async def search_text(self, request):
            from backend.tests.versions.v1.fakes import _candidate

            response = await super().search_text(request)
            if request.location_bias is not None:
                group = self._candidate_call - 1
                response = response.model_copy(
                    update={
                        "candidates": [
                            _candidate(f"poi-{group}-{i}", i, -33.86, 151.2) for i in range(20)
                        ],
                        "actual_result_count": 20,
                    }
                )
            return response

    model, places, routes = LongTripModel(), FullSearchPlaces(), FakeRoutesProvider()
    config = load_runtime_profile("acceptance")
    options = {
        "runtime_config": config,
        "development_timeout_seconds": config.development_timeout_seconds,
    }
    if version != "v1":
        options["retrieval_factory"] = OwnedRetrieval
    result = asyncio.run(
        {"v1": run_v1, "v2": run_v2, "v3": run_v3}[version](
            request,
            model,
            places,
            FakeWeatherProvider(),
            routes,
            reference_date=date(2026, 9, 11),
            **options,
        )
    )
    assert len(result.planning_supply.selected_place_ids) == expected
    assert len(result.itinerary.days) == days
    assert all(len(day.activities) == 3 for day in result.itinerary.days)
    assert request.model_dump() == before
    assert model.repair_calls == 0
    assert all(len(item.origins) * len(item.destinations) <= 64 for item in routes.requests)
    # Initial baseline and mixed-mode alternatives have separate finite envelopes.
    assert sum(len(item.origins) * len(item.destinations) for item in routes.requests) <= 4112
