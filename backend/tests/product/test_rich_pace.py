"""Rich completion survives real Product tasks, PostgreSQL saves and replanning."""
# Imported pytest fixtures intentionally share the public client argument name.
# ruff: noqa: F811

import asyncio
from contextlib import asynccontextmanager
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_planning_service
from backend.app.main import create_app
from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
from backend.app.services.planning import PlanningService
from backend.app.services.product_introductions import IntroductionBatch, ProductIntroductions
from backend.tests.fakes import FixedDateProvider
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
from backend.tests.versions.v3.test_rich_pace_completion import OpenPlaces, rich_model
from backend.tests.versions.v3.test_wiring import OwnedRetrieval


@pytest.mark.parametrize("counts, status", [((2, 3), "partial"), ((4, 3), "complete")])
@pytest.mark.parametrize("reference_date", [date(2026, 9, 11), date(2026, 9, 12)])
def test_rich_task_preview_save_reopen_and_replan_keep_completion(
    client, monkeypatch, counts, status, reference_date
):  # noqa: F811, E501
    with TestClient(create_app(), base_url="http://localhost:5120") as planning_client:
        check_rich_lifecycle(planning_client, monkeypatch, counts, status, reference_date)


def check_rich_lifecycle(client, monkeypatch, counts, status, reference_date):
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    models = []
    monkeypatch.setattr(
        "backend.app.versions.v3.runner.RuntimeRetrieval", lambda _: OwnedRetrieval()
    )

    @asynccontextmanager
    async def dependencies(*_):
        model = rich_model(counts)
        models.append(model)
        yield PlannerDependencies(model, OpenPlaces(), FakeWeatherProvider(), FakeRoutesProvider())

    class Introductions:
        async def generate(self, places):
            return IntroductionBatch(introductions=[])

    @asynccontextmanager
    async def introductions():
        yield Introductions()

    service = PlanningService(
        RequestPlannerRuntime(dependency_factory=dependencies),
        FixedDateProvider(reference_date),
        introductions=ProductIntroductions(introductions),
    )
    client.app.dependency_overrides[get_planning_service] = lambda: service
    request = make_request("Travel pace: rich.").model_dump(mode="json")

    async def finish():
        await asyncio.gather(*client.app.state.product_coordinator.workers)

    try:
        accepted = client.post(
            "/api/planning/tasks",
            headers=headers,
            json={"operation_key": "rich-first", "request": request},
        )
        assert accepted.status_code == 202, accepted.text
        client.portal.call(finish)
        task = client.get(f"/api/planning/tasks/{accepted.json()['id']}").json()
        assert task["state"] == "completed", task
        preview_id = task["preview_id"]
        preview = client.get(f"/api/previews/{preview_id}").json()["snapshot"]
        completion = preview["completion"]["pace_review"]
        assert completion["status"] == status
        assert [d["count"] for d in completion["days"]] == (
            [2, 3] if status == "partial" else [3, 3]
        )
        saved = client.post(f"/api/previews/{preview_id}/save", headers=headers, json={}).json()
        saved_id = saved["saved_trip_id"]
        with TestClient(create_app(), base_url="http://localhost:5120") as reopened:
            reopened.cookies.update(client.cookies)
            trip = reopened.get(f"/api/trips/{saved_id}").json()
            assert trip["completion"]["pace_review"] == completion
            assert trip["request"]["additional_preferences"] == "Travel pace: rich."
        repeated = client.post(
            "/api/planning/tasks",
            headers=headers,
            json={
                "operation_key": "rich-replan",
                "request": {k: v for k, v in trip["request"].items() if k != "known_fields"},
            },
        )
        assert repeated.status_code == 202, repeated.text
        client.portal.call(finish)
        replanned = client.get(f"/api/planning/tasks/{repeated.json()['id']}").json()
        replanned_preview = client.get(f"/api/previews/{replanned['preview_id']}").json()
        assert replanned_preview["snapshot"]["completion"]["pace_review"] == completion
        assert len(models) == 2
        assert client.get(f"/api/trips/{saved_id}").json() == trip
    finally:
        client.app.dependency_overrides.clear()
