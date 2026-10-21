"""Product HTTP -> real V3 graph -> safe presentation with external boundaries faked."""

import asyncio
from contextlib import asynccontextmanager
from datetime import date

import pytest

from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
from backend.app.services.planning import DeveloperPlanningService, PlanningService
from backend.app.services.product_introductions import (
    Introduction,
    IntroductionBatch,
    ProductIntroductions,
)
from backend.tests.api.test_product_planning import post_product_planning
from backend.tests.fakes import FixedDateProvider
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
from backend.tests.versions.v2.test_v2_runner import Places
from backend.tests.versions.v3.test_wiring import Model, OwnedRetrieval


@pytest.mark.parametrize("introduction_failure", [False, True])
def test_product_v3_completed_and_developer_does_not_generate_introductions(
    monkeypatch,
    introduction_failure,
):
    from backend.app.versions.v3 import runner

    retrievals, models, calls = [], [], []

    def retrieval_factory(config):
        runtime = OwnedRetrieval()
        retrievals.append(runtime)
        return runtime

    monkeypatch.setattr(runner, "RuntimeRetrieval", retrieval_factory)

    @asynccontextmanager
    async def dependencies(*args):
        # An empty patch leaves findings unresolved: a valid final itinerary must still return.
        model = Model(behavior="empty")
        models.append(model)
        yield PlannerDependencies(model, Places(), FakeWeatherProvider(), FakeRoutesProvider())

    class Introductions:
        async def generate(self, places):
            calls.append(places)
            if introduction_failure:
                raise RuntimeError("PRIVATE provider failure")
            return IntroductionBatch(
                introductions=[
                    Introduction(activity_id=p["activity_id"], text="A place worth exploring.")
                    for p in places
                ]
            )

    @asynccontextmanager
    async def introductions():
        yield Introductions()

    runtime = RequestPlannerRuntime(dependency_factory=dependencies)
    date_provider = FixedDateProvider(date(2026, 9, 11))
    service = PlanningService(
        runtime, date_provider, introductions=ProductIntroductions(introductions)
    )
    status, body = post_product_planning(service, make_request().model_dump(mode="json"))
    assert status == 202 and body["state"] == "completed"
    body = body["preview"]["snapshot"]
    assert len(calls) == 1
    activities = [a for d in body["days"] for a in d["activities"]]
    assert any(a["introduction"] for a in activities) != introduction_failure
    assert all("weather" in d for d in body["days"])
    assert any(d["weather"] is not None for d in body["days"])
    assert all(r.closes == 1 for r in retrievals)
    forbidden = {
        "system_version",
        "v3",
        "rag_discovery",
        "route_diagnostics",
        "source_ref",
        "request_resources",
        "planning_supply",
        "provider_diagnostics",
        "output_version",
    }

    def check(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for item in value.values():
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)

    check(body)
    assert "PRIVATE" not in str(body)
    raw = asyncio.run(DeveloperPlanningService(runtime, date_provider).plan("v3", make_request()))
    assert raw.system_version == "v3" and raw.v3.final_report
    assert len(calls) == 1  # Research path did not add the presentation model call.
    assert len(models) == 2
