"""Diagnostics across real Product HTTP, task coordination and isolated PostgreSQL."""
# ruff: noqa: F811

import asyncio
from contextlib import asynccontextmanager
from datetime import date

import pytest

from backend.app.api.dependencies import get_planning_service
from backend.app.observability.product_logs import ProductLogs
from backend.app.product.task_coordinator import TaskCoordinator
from backend.app.product.task_store import TaskStore
from backend.app.product.tasks import get_coordinator
from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
from backend.app.services.planning import PlanningService
from backend.tests.fakes import FixedDateProvider
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_drafts import editor
from backend.tests.product.test_saved import pending
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
from backend.tests.versions.v2.test_v2_runner import Places
from backend.tests.versions.v3.test_wiring import Model, OwnedRetrieval


def test_account_draft_and_saved_operations_have_audit_results(client, monkeypatch, tmp_path):
    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    draft = client.post(
        "/api/drafts", headers=headers, json={"title": "PRIVATE TITLE", "editor": editor()}
    )
    assert draft.status_code == 201
    assert client.get("/api/profile").status_code == 200
    detail = pending(account["id"])
    saved = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={})
    assert saved.status_code == 200
    assert client.get(f"/api/trips/{saved.json()['saved_trip_id']}").status_code == 200
    assert (
        client.post(
            "/api/auth/login",
            headers=headers,
            json={"email": "alice@example.com", "password": "incorrect-private-password"},
        ).status_code
        == 401
    )
    rows = ProductLogs().read()
    http = [row["data"] for row in rows if row["event"] == "http_completed"]
    assert any(
        row["route"] == "/api/previews/{preview_id}/save" and row["status"] == 200 for row in http
    )
    assert any(row.get("code") == "invalid_credentials" for row in http)
    assert any(row.get("owner_id") == account["id"] for row in http)
    assert "PRIVATE TITLE" not in str(rows)
    assert "incorrect-private-password" not in str(rows)


@pytest.mark.parametrize("trace_limit", [512, 1_000_000])
def test_real_v3_task_records_repair_and_preserves_public_projection(
    client, monkeypatch, tmp_path, trace_limit
):
    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    monkeypatch.setattr(
        "backend.app.versions.v3.runner.RuntimeRetrieval", lambda _: OwnedRetrieval()
    )

    @asynccontextmanager
    async def dependencies(*args):
        yield PlannerDependencies(
            Model(behavior="empty"), Places(), FakeWeatherProvider(), FakeRoutesProvider()
        )

    class Introductions:
        async def generate(self, *args):
            return {}

    from backend.app.runtime.config_loader import load_runtime_config

    config = load_runtime_config()
    config = config.model_copy(
        update={"trace": config.trace.model_copy(update={"max_payload_bytes": trace_limit})}
    )
    service = PlanningService(
        RequestPlannerRuntime(config=config, dependency_factory=dependencies),
        FixedDateProvider(date(2026, 9, 11)),
        introductions=Introductions(),
    )
    client.app.dependency_overrides[get_planning_service] = lambda: service
    coordinator = TaskCoordinator(TaskStore())
    client.app.dependency_overrides[get_coordinator] = lambda: coordinator
    try:
        account = register(client)
        headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
        response = client.post(
            "/api/planning/tasks",
            headers=headers,
            json={
                "operation_key": "logged-real-v3",
                "request": make_request().model_dump(mode="json"),
            },
        )
        assert response.status_code == 202

        async def settle():
            await asyncio.gather(*coordinator.workers)

        client.portal.call(settle)
        task_id = response.json()["id"]
        task = client.get(f"/api/planning/tasks/{task_id}").json()
        assert task["state"] == "completed"
        preview = client.get(f"/api/previews/{task['preview_id']}").json()
        assert "v3_outcome" not in preview["snapshot"]
        rows = ProductLogs().read(task_id=task_id)
        summary = next(row for row in rows if "collection_status" in row)
        assert summary["run_id"] == summary["execution_id"]
        assert summary["request_id"] == response.headers["x-request-id"]
        assert summary["stop_reason"]
        assert summary["repair_status"]
        assert summary["validation_counts"]
        if trace_limit == 512:
            assert summary["upstream_details_truncated"]
        assert any(row.get("event") == "v3_finalized" for row in rows)
        assert any(row.get("event") == "task_completed" for row in rows)
    finally:
        client.portal.call(coordinator.close)
        client.app.dependency_overrides.clear()


def test_failed_task_records_the_committed_public_outcome(client, monkeypatch, tmp_path):
    from backend.tests.api.test_product_planning import make_planning_service, make_product_payload
    from backend.tests.versions.v0.fakes import FakeStructuredLLMClient

    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    coordinator = TaskCoordinator(TaskStore())
    model = FakeStructuredLLMClient([RuntimeError("private failure detail")])
    client.app.dependency_overrides[get_coordinator] = lambda: coordinator
    client.app.dependency_overrides[get_planning_service] = lambda: make_planning_service(model)
    try:
        account = register(client)
        headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
        response = client.post(
            "/api/planning/tasks",
            headers=headers,
            json={"operation_key": "logged-failure", "request": make_product_payload()},
        )
        assert response.status_code == 202

        async def settle():
            await asyncio.gather(*coordinator.workers)

        client.portal.call(settle)
        task_id = response.json()["id"]
        task = client.get("/api/planning/tasks/" + task_id).json()
        assert task["state"] == "failed"
        rows = ProductLogs().read(task_id=task_id)
        final = next(row for row in rows if row.get("event") == "task_finished")
        assert final["data"] == {"state": "failed", "code": task["outcome"]["code"]}
        assert "private failure detail" not in str(rows)
    finally:
        client.portal.call(coordinator.close)
        client.app.dependency_overrides.clear()
