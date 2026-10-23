"""Owner-scoped Stop through real APIs, PostgreSQL and planner transport cleanup."""
# Imported fixture names remain their public pytest names.
# ruff: noqa: F811

import pytest

from backend.app.api.dependencies import get_planning_service
from backend.app.product.task_coordinator import TaskCoordinator
from backend.app.product.task_store import TaskStore
from backend.app.product.tasks import get_coordinator
from backend.tests.api.test_product_planning import make_planning_service, make_product_payload
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient


def test_stop_pending_is_idempotent_and_never_enters_external_work(client):
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    schedules = []
    external = FakeStructuredLLMClient([])
    coordinator = TaskCoordinator(TaskStore(), schedule=schedules.append)
    client.app.dependency_overrides[get_coordinator] = lambda: coordinator
    client.app.dependency_overrides[get_planning_service] = lambda: make_planning_service(external)
    try:
        payload = {"operation_key": "stop-before-launch", "request": make_product_payload()}
        task = client.post("/api/planning/tasks", headers=headers, json=payload).json()
        url = f"/api/planning/tasks/{task['id']}/stop"
        assert client.post(url).status_code == 403
        stopped = client.post(url, headers=headers)
        assert stopped.status_code == 200
        assert stopped.json()["state"] == "cancelled"
        assert stopped.json()["outcome"]["code"] == "planning_cancelled"
        assert client.post(url, headers=headers).json() == stopped.json()
        # An already scheduled callback must not claim after the committed Stop.
        import asyncio

        async def launch_late():
            schedules[0]()
            await asyncio.gather(*coordinator.workers)

        client.portal.call(launch_late)
        assert external.calls == []
        assert client.get("/api/previews").json() == []
        replay = client.post("/api/planning/tasks", headers=headers, json=payload).json()
        assert replay == stopped.json()
        assert client.get("/api/planning/tasks/active").json() is None
        client.cookies.clear()
        other = register(client, "different-stop-owner@example.com")
        assert (
            client.post(url, headers={**headers, "X-CSRF-Token": other["csrf_token"]}).status_code
            == 404
        )
    finally:
        client.app.dependency_overrides.clear()


@pytest.mark.parametrize("cleanup_race", ["normal", "shutdown", "expired"])
def test_other_app_stop_cleans_running_transport_before_cancelled_and_keeps_input(
    client, monkeypatch, cleanup_race
):
    import asyncio
    from contextlib import asynccontextmanager
    from datetime import date

    from httpx import ASGITransport, AsyncClient

    from backend.app.main import create_app
    from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
    from backend.app.services.planning import PlanningService
    from backend.tests.fakes import FixedDateProvider
    from backend.tests.product.test_drafts import editor
    from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
    from backend.tests.versions.v2.test_v2_runner import Places
    from backend.tests.versions.v3.test_wiring import Model, OwnedRetrieval
    from scripts.run_api import create_api_loop

    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    retrievals = []

    def retrieval_factory(config):
        retrieval = OwnedRetrieval()
        retrievals.append(retrieval)
        return retrieval

    monkeypatch.setattr("backend.app.versions.v3.runner.RuntimeRetrieval", retrieval_factory)

    async def scenario():
        entered, cancelled, closing, cleanup_release = [asyncio.Event() for _ in range(4)]
        calls = []

        class GatedModel(Model):
            async def generate_structured(self, **kwargs):
                calls.append(kwargs["response_schema"].__name__)
                entered.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cancelled.set()
                    raise

        @asynccontextmanager
        async def dependencies(*args):
            try:
                yield PlannerDependencies(
                    GatedModel(behavior="empty"),
                    Places(),
                    FakeWeatherProvider(),
                    FakeRoutesProvider(),
                )
            finally:
                closing.set()
                await cleanup_release.wait()

        service = PlanningService(
            RequestPlannerRuntime(dependency_factory=dependencies),
            FixedDateProvider(date(2026, 9, 11)),
        )
        first, second = create_app(), create_app()
        coordinator = TaskCoordinator(TaskStore(), heartbeat_seconds=0.02)
        first.state.product_coordinator = coordinator
        first.dependency_overrides[get_planning_service] = lambda: service
        async with first.router.lifespan_context(first), second.router.lifespan_context(second):
            async with (
                AsyncClient(
                    transport=ASGITransport(app=first),
                    base_url="http://localhost:5120",
                    cookies=dict(client.cookies),
                ) as owner,
                AsyncClient(
                    transport=ASGITransport(app=second),
                    base_url="http://localhost:5120",
                    cookies=dict(client.cookies),
                ) as other,
            ):
                payload = {
                    "operation_key": "cross-app-stop",
                    "request": make_product_payload(),
                    "editor_snapshot": editor(destination="Sydney"),
                }
                accepted = await owner.post("/api/planning/tasks", json=payload, headers=headers)
                assert accepted.status_code == 202
                task_id = accepted.json()["id"]
                url = f"/api/planning/tasks/{task_id}"
                await asyncio.wait_for(entered.wait(), 20)
                stopping = await other.post(url + "/stop", headers=headers)
                assert stopping.status_code == 200 and stopping.json()["state"] == "stopping"
                assert (await other.post(url + "/stop", headers=headers)).json() == stopping.json()
                shutdown = None
                try:
                    await asyncio.wait_for(cancelled.wait(), 3)
                    await asyncio.wait_for(closing.wait(), 3)
                    assert (await other.get(url)).json()["state"] == "stopping"
                    if cleanup_race == "shutdown":
                        shutdown = asyncio.create_task(coordinator.close())
                        await asyncio.sleep(0)  # Deliver shutdown while owned cleanup is gated.
                        assert not shutdown.done()
                    elif cleanup_race == "expired":
                        from datetime import UTC, datetime, timedelta

                        second.state.product_coordinator.store.clock = lambda: (
                            datetime.now(UTC) + timedelta(hours=1)
                        )
                        assert (await other.get(url)).json()["outcome"][
                            "code"
                        ] == "planning_interrupted"
                finally:
                    cleanup_release.set()
                await asyncio.wait_for(
                    asyncio.gather(*coordinator.workers, return_exceptions=True), 5
                )
                if shutdown:
                    await asyncio.wait_for(shutdown, 5)
                stopped = (await other.get(url)).json()
                assert stopped["state"] == ("failed" if cleanup_race == "expired" else "cancelled")
                assert stopped["outcome"]["code"] == (
                    "planning_interrupted" if cleanup_race == "expired" else "planning_cancelled"
                )
                assert stopped["request"] == accepted.json()["request"]
                assert stopped["editor_snapshot"] == accepted.json()["editor_snapshot"]
                assert (await other.post(url + "/stop", headers=headers)).json() == stopped
                assert (await other.get("/api/previews")).json() == []
                assert (await other.get("/api/planning/tasks/active")).json() is None
                assert calls == ["V1Itinerary"]
                assert len(retrievals) == 1 and retrievals[0].enters == retrievals[0].closes == 1

    asyncio.run(scenario(), loop_factory=create_api_loop)
