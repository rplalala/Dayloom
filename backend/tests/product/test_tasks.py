"""Durable task acceptance through real HTTP and isolated PostgreSQL."""

import pytest

from backend.tests.api.test_product_planning import make_planning_service, make_product_payload
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient


def test_accepted_pending_has_identity_and_survives_app_recreation(client):  # noqa: F811
    from backend.app.api.dependencies import get_planning_service
    from backend.app.product.task_coordinator import TaskCoordinator
    from backend.app.product.task_store import TaskStore
    from backend.app.product.tasks import get_coordinator

    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    coordinator = TaskCoordinator(TaskStore(), schedule=lambda work: None)
    client.app.dependency_overrides[get_coordinator] = lambda: coordinator
    service = make_planning_service(FakeStructuredLLMClient([]))
    client.app.dependency_overrides[get_planning_service] = lambda: service
    try:
        payload = {"operation_key": "acceptance-one", "request": make_product_payload()}
        accepted = client.post("/api/planning/tasks", json=payload, headers=headers)
        assert accepted.status_code == 202, accepted.text
        task = accepted.json()
        assert task["state"] == "pending" and task["revision"] == 1
        replay = client.post("/api/planning/tasks", json=payload, headers=headers)
        assert replay.json()["id"] == task["id"]
        changed = {**payload, "request": {**payload["request"], "additional_preferences": "Quiet"}}
        assert client.post("/api/planning/tasks", json=changed, headers=headers).status_code == 409
        conflict = client.post(
            "/api/planning/tasks", json={**payload, "operation_key": "other"}, headers=headers
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["task_id"] == task["id"]
        assert client.get("/api/planning/tasks/active").json()["id"] == task["id"]
        from fastapi.testclient import TestClient

        from backend.app.main import create_app

        with TestClient(create_app(), base_url="http://localhost:5120") as recreated:
            recreated.cookies.update(client.cookies)
            assert recreated.get(f"/api/planning/tasks/{task['id']}").json() == task
            assert recreated.get("/api/previews").json() == []
    finally:
        client.app.dependency_overrides.clear()


@pytest.mark.parametrize("expire_running_lease", [False, True])
def test_real_v3_runs_once_while_other_brief_changes_and_preview_is_durable(
    client,  # noqa: F811
    monkeypatch,
    expire_running_lease,
):  # noqa: F811
    import asyncio
    from contextlib import asynccontextmanager
    from datetime import date

    from httpx import ASGITransport, AsyncClient

    from backend.app.api.dependencies import get_planning_service
    from backend.app.main import create_app
    from backend.app.product.task_coordinator import TaskCoordinator
    from backend.app.product.task_store import TaskStore
    from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
    from backend.app.services.planning import PlanningService
    from backend.app.services.product_introductions import IntroductionBatch, ProductIntroductions
    from backend.tests.fakes import FixedDateProvider
    from backend.tests.product.test_drafts import editor
    from backend.tests.request_fixtures import make_request
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
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []

        class GatedModel(Model):
            async def generate_structured(self, **kwargs):
                calls.append(kwargs["response_schema"].__name__)
                entered.set()
                await release.wait()
                return await super().generate_structured(**kwargs)

        @asynccontextmanager
        async def dependencies(*args):
            yield PlannerDependencies(
                GatedModel(behavior="empty"), Places(), FakeWeatherProvider(), FakeRoutesProvider()
            )

        class Introductions:
            async def generate(self, places):
                return IntroductionBatch(introductions=[])

        @asynccontextmanager
        async def introductions():
            yield Introductions()

        service = PlanningService(
            RequestPlannerRuntime(dependency_factory=dependencies),
            FixedDateProvider(date(2026, 9, 11)),
            introductions=ProductIntroductions(introductions),
        )
        first, second = create_app(), create_app()
        coordinator = TaskCoordinator(TaskStore())
        first.state.product_coordinator = coordinator
        first.dependency_overrides[get_planning_service] = lambda: service
        second.dependency_overrides[get_planning_service] = lambda: service
        async with first.router.lifespan_context(first), second.router.lifespan_context(second):
            async with AsyncClient(
                transport=ASGITransport(app=first),
                base_url="http://localhost:5120",
                cookies=dict(client.cookies),
            ) as http:
                payload = {
                    "operation_key": "real-graph",
                    "request": make_request().model_dump(mode="json"),
                    "editor_snapshot": editor(destination="Sydney"),
                }
                accepted = await http.post("/api/planning/tasks", json=payload, headers=headers)
                assert accepted.status_code == 202, accepted.text
                task_id = accepted.json()["id"]
                await asyncio.wait_for(entered.wait(), 20)
                # Real ASGI stream disconnect detaches the observer, keeping the same worker.
                import json

                observed = asyncio.Event()
                received = False

                async def receive():
                    nonlocal received
                    if not received:
                        received = True
                        return {
                            "type": "http.request",
                            "body": json.dumps(payload["request"]).encode(),
                        }
                    await observed.wait()
                    return {"type": "http.disconnect"}

                async def send(message):
                    if message["type"] == "http.response.body" and b"event: task" in message.get(
                        "body", b""
                    ):
                        observed.set()

                raw_headers = {
                    **headers,
                    "Idempotency-Key": "real-graph",
                    "Content-Type": "application/json",
                    "Cookie": "; ".join(
                        f"{key}={value}" for key, value in dict(client.cookies).items()
                    ),
                }
                scope = {
                    "type": "http",
                    "asgi": {"version": "3.0", "spec_version": "2.0"},
                    "http_version": "1.1",
                    "method": "POST",
                    "scheme": "http",
                    "path": "/api/planning/stream",
                    "raw_path": b"/api/planning/stream",
                    "query_string": b"",
                    "root_path": "",
                    "server": ("localhost", 5120),
                    "client": ("127.0.0.1", 1),
                    "headers": [
                        (key.lower().encode(), value.encode()) for key, value in raw_headers.items()
                    ],
                }
                await asyncio.wait_for(first(scope, receive, send), 5)
                assert observed.is_set()
                async with AsyncClient(
                    transport=ASGITransport(app=second),
                    base_url="http://localhost:5120",
                    cookies=dict(client.cookies),
                ) as other:
                    conflict = await other.post(
                        "/api/planning/tasks",
                        json={**payload, "operation_key": "second-app"},
                        headers=headers,
                    )
                    assert conflict.status_code == 409
                    assert conflict.json()["detail"]["task_id"] == task_id
                    draft = await other.post(
                        "/api/drafts",
                        json={"title": "Different brief", "editor": editor(destination="Kyoto")},
                        headers=headers,
                    )
                    assert draft.status_code == 201
                    retained = (await other.get(f"/api/planning/tasks/{task_id}")).json()
                    assert retained["request"]["destination"] == "Sydney"
                    assert retained["editor_snapshot"]["destination"] == "Sydney"
                if expire_running_lease:
                    from datetime import UTC, datetime, timedelta

                    coordinator.store.clock = lambda: datetime.now(UTC) + timedelta(hours=1)
                    await asyncio.to_thread(coordinator.store.reconcile)
                release.set()
                await asyncio.wait_for(asyncio.gather(*coordinator.workers), 30)
                finished = (await http.get(f"/api/planning/tasks/{task_id}")).json()
                if expire_running_lease:
                    assert finished["state"] == "failed" and finished["preview_id"] is None
                    assert finished["outcome"]["code"] == "planning_interrupted"
                    assert (await http.get("/api/previews")).json() == []
                    assert calls.count("V1Itinerary") == 1
                    assert (
                        len(retrievals) == 1 and retrievals[0].enters == retrievals[0].closes == 1
                    )
                    return
                assert finished["state"] == "completed", finished
                preview_id = finished["preview_id"]
                preview = (await http.get(f"/api/previews/{preview_id}")).json()
                assert preview["state"] == "pending"
                assert preview["snapshot"]["trust"] == "generated_projection"
                replay = await http.post(
                    "/api/planning",
                    json=payload["request"],
                    headers={**headers, "Idempotency-Key": payload["operation_key"]},
                )
                assert replay.status_code == 202
                assert replay.json()["task_id"] == task_id
                assert replay.json()["preview_id"] == preview_id
                assert replay.json()["result"] == preview["snapshot"]
                assert preview["snapshot"]["completion"]["policy_completion"] in {
                    "complete",
                    "incomplete",
                    "unassessed",
                }
                assert "fence" not in finished and "execution_id" not in finished
                assert [
                    item["kind"] for item in (await http.get("/api/library")).json()["items"]
                ] == ["draft"]
                saved = await http.post(
                    f"/api/previews/{preview_id}/save", json={}, headers=headers
                )
                assert saved.status_code == 200, saved.text
                saved_id = saved.json()["saved_trip_id"]
                from copy import deepcopy

                expected_saved = deepcopy(preview["snapshot"])
                expected_saved["id"] = saved_id
                for day in expected_saved["days"]:
                    if day["weather"] is not None:
                        day["weather"].update(attribution=None, source_url=None)
                assert (await http.get(f"/api/trips/{saved_id}")).json() == expected_saved
                assert (await http.get("/api/previews")).json() == []
                preview = (await http.get(f"/api/previews/{preview_id}")).json()
                assert calls.count("V1Itinerary") == 1
                assert (
                    len(retrievals) == 1 and retrievals[0].enters == 1 and retrievals[0].closes == 1
                )
        recreated = create_app()
        async with recreated.router.lifespan_context(recreated):
            async with AsyncClient(
                transport=ASGITransport(app=recreated),
                base_url="http://localhost:5120",
                cookies=dict(client.cookies),
            ) as http:
                assert (await http.get(f"/api/previews/{preview_id}")).json() == preview
                assert (await http.get(f"/api/trips/{saved_id}")).json() == expected_saved
                assert (await http.get(f"/api/planning/tasks/{task_id}")).json()[
                    "state"
                ] == "completed"

    asyncio.run(scenario(), loop_factory=create_api_loop)


def test_finite_acceptance_deadline_reconciles_once_and_fences_stale_claims(client):  # noqa: F811
    from concurrent.futures import ThreadPoolExecutor
    from datetime import UTC, date, datetime, timedelta

    from backend.app.product.task_store import TaskStore
    from backend.app.schemas.request import PlanningRequest

    account = register(client)
    instant = [datetime(2026, 9, 11, tzinfo=UTC)]
    first = TaskStore(clock=lambda: instant[0], pending_seconds=10, lease_seconds=10)
    second = TaskStore(clock=lambda: instant[0], pending_seconds=10, lease_seconds=10)
    request = PlanningRequest.model_validate(make_product_payload())
    pending, _ = first.accept(account["id"], "before-claim-crash", request, None, date(2026, 9, 11))
    instant[0] += timedelta(seconds=11)
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda store: store.reconcile(), [first, second]))
    interrupted = first.read(account["id"], pending["id"])
    assert interrupted["state"] == "failed"
    assert interrupted["outcome"]["code"] == "planning_interrupted"
    assert interrupted["revision"] == 2
    assert first.claim(pending["id"]) is None
    next_task, _ = first.accept(
        account["id"], "new-explicit-action", request, None, date(2026, 9, 11)
    )
    with ThreadPoolExecutor(2) as pool:
        claims = list(pool.map(lambda store: store.claim(next_task["id"]), [first, second]))
    claim = next(value for value in claims if value)
    assert sum(value is not None for value in claims) == 1
    second.reconcile()
    assert first.read(account["id"], next_task["id"])["state"] == "running"
    assert first.renew(claim, {"stage": "generation", "message": "Planning your days"})
    observed = first.read(account["id"], next_task["id"])
    assert observed["progress"]["message"] == "Planning your days"
    from backend.app.product.database import connect

    with connect() as connection:
        connection.execute(
            "UPDATE app.planning_tasks SET state='stopping' WHERE id=%s", (next_task["id"],)
        )
    assert first.read(account["id"], next_task["id"])["state"] == "stopping"
    instant[0] += timedelta(seconds=11)
    assert not first.renew(claim)
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda store: store.reconcile(), [first, second]))
    assert not first.finish(claim, "cancelled", {"code": "late"})
    assert first.read(account["id"], next_task["id"])["state"] == "failed"


def test_request_identity_includes_preferences_and_normalizes_decimal_and_null(client):  # noqa: F811
    from datetime import date

    import pytest

    from backend.app.product.task_store import TaskConflict, TaskStore
    from backend.app.schemas.request import PlanningRequest

    account = register(client)
    store = TaskStore()
    payload = make_product_payload()
    task, _ = store.accept(
        account["id"], "identity", PlanningRequest.model_validate(payload), None, date(2026, 9, 11)
    )
    same = {**payload, "request_id": None, "budget": {"amount": "1800.00", "currency": "AUD"}}
    replay, created = store.accept(
        account["id"], "identity", PlanningRequest.model_validate(same), None, date(2026, 9, 11)
    )
    assert replay["id"] == task["id"] and not created
    with pytest.raises(TaskConflict) as error:
        store.accept(
            account["id"],
            "identity",
            PlanningRequest.model_validate(
                {**same, "additional_preferences": "Literal changed preference"}
            ),
            None,
            date(2026, 9, 11),
        )
    assert error.value.code == "operation_key_conflict"


def test_other_owner_cannot_read_task_preview_and_invalid_currency_never_starts(client):  # noqa: F811
    from backend.app.api.dependencies import get_planning_service
    from backend.app.product.task_coordinator import TaskCoordinator
    from backend.app.product.task_store import TaskStore
    from backend.app.product.tasks import get_coordinator

    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    external = FakeStructuredLLMClient([])
    coordinator = TaskCoordinator(TaskStore(), schedule=lambda work: None)
    client.app.dependency_overrides[get_coordinator] = lambda: coordinator
    client.app.dependency_overrides[get_planning_service] = lambda: make_planning_service(external)
    try:
        payload = {"operation_key": "valid", "request": make_product_payload()}
        rejected = client.post(
            "/api/planning/tasks",
            headers=headers,
            json={
                **payload,
                "request": {**payload["request"], "budget": {"amount": "1", "currency": "XXX"}},
            },
        )
        assert rejected.status_code == 422 and external.calls == []
        task = client.post("/api/planning/tasks", headers=headers, json=payload).json()
        client.cookies.clear()
        register(client, "second@example.com")
        assert client.get(f"/api/planning/tasks/{task['id']}").status_code == 404
        assert client.get("/api/planning/tasks?operation_key=valid").json() is None
        assert client.get("/api/planning/tasks/active").json() is None
    finally:
        client.app.dependency_overrides.clear()


def test_preview_write_failure_rolls_back_terminal_task_and_cross_owner_links(client):  # noqa: F811
    from datetime import date
    from uuid import uuid4

    from psycopg.errors import UniqueViolation

    from backend.app.product.detail import ProductDetail
    from backend.app.product.task_store import TaskStore
    from backend.app.schemas.request import PlanningRequest

    account = register(client)
    store = TaskStore()
    request = PlanningRequest.model_validate(make_product_payload())
    first, _ = store.accept(account["id"], "first-completion", request, None, date(2026, 9, 11))
    first_claim = store.claim(first["id"])
    detail = ProductDetail(
        id=str(uuid4()),
        title="Sydney journey",
        destination="Sydney",
        provenance="generated",
        trust="generated_projection",
    )
    assert store.complete(first_claim, detail)
    assert not store.finish(first_claim, "cancelled", {"code": "late"})
    assert not store.renew(first_claim)
    store.reconcile()
    assert store.read(account["id"], first["id"])["state"] == "completed"
    second, _ = store.accept(account["id"], "second-completion", request, None, date(2026, 9, 11))
    second_claim = store.claim(second["id"])
    with pytest.raises(UniqueViolation):
        store.complete(second_claim, detail)
    retained = store.read(account["id"], second["id"])
    assert retained["state"] == "running" and retained["preview_id"] is None
    assert len(store.previews(account["id"])) == 1
    client.cookies.clear()
    register(client, "different-preview-owner@example.com")
    assert client.get(f"/api/previews/{detail.id}").status_code == 404


def test_terminal_update_failure_rolls_back_inserted_preview(client):  # noqa: F811
    import os
    from datetime import date
    from uuid import uuid4

    import psycopg
    from pydantic import SecretStr

    from backend.app.product.detail import ProductDetail
    from backend.app.product.task_store import TaskStore
    from backend.app.schemas.request import PlanningRequest

    account = register(client)
    store = TaskStore()
    accepted, _ = store.accept(
        account["id"],
        "atomic-update-failure",
        PlanningRequest.model_validate(make_product_payload()),
        None,
        date(2026, 9, 11),
    )
    claim = store.claim(accepted["id"])
    dsn = SecretStr(os.environ["PRODUCT_DATABASE_URL"])
    with psycopg.connect(dsn.get_secret_value()) as connection:
        connection.execute(
            "CREATE FUNCTION app.reject_completed_task() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN IF NEW.state='completed' THEN RAISE EXCEPTION "
            "'deliberate completion update failure'; END IF; RETURN NEW; END; $$"
        )
        connection.execute(
            "CREATE TRIGGER reject_completed_task BEFORE UPDATE ON app.planning_tasks "
            "FOR EACH ROW EXECUTE FUNCTION app.reject_completed_task()"
        )
    try:
        detail = ProductDetail(
            id=str(uuid4()),
            title="Atomic itinerary",
            destination="Sydney",
            provenance="generated",
            trust="generated_projection",
        )
        with pytest.raises(psycopg.errors.RaiseException):
            store.complete(claim, detail)
        assert store.previews(account["id"]) == []
        retained = store.read(account["id"], accepted["id"])
        assert retained["state"] == "running" and retained["preview_id"] is None
    finally:
        with psycopg.connect(dsn.get_secret_value()) as connection:
            connection.execute("DROP TRIGGER reject_completed_task ON app.planning_tasks")
            connection.execute("DROP FUNCTION app.reject_completed_task()")


def test_two_http_app_instances_accept_only_one_concurrent_submission(client):  # noqa: F811
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from backend.app.api.dependencies import get_planning_service
    from backend.app.main import create_app
    from backend.app.product.task_coordinator import TaskCoordinator
    from backend.app.product.task_store import TaskStore

    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    schedules = []
    apps = [create_app(), create_app()]
    service = make_planning_service(FakeStructuredLLMClient([]))
    for app in apps:
        app.state.product_coordinator = TaskCoordinator(
            TaskStore(), schedule=lambda work: schedules.append("scheduled")
        )
        app.dependency_overrides[get_planning_service] = lambda: service
    with (
        TestClient(apps[0], base_url="http://localhost:5120") as first,
        TestClient(apps[1], base_url="http://localhost:5120") as second,
    ):
        first.cookies.update(client.cookies)
        second.cookies.update(client.cookies)

        def submit(item):
            http, key = item
            return http.post(
                "/api/planning/tasks",
                headers=headers,
                json={"operation_key": key, "request": make_product_payload()},
            )

        with ThreadPoolExecutor(2) as pool:
            replies = list(pool.map(submit, [(first, "concurrent-a"), (second, "concurrent-b")]))
        assert sorted(reply.status_code for reply in replies) == [202, 409]
        accepted = next(reply.json() for reply in replies if reply.status_code == 202)
        rejected = next(reply.json() for reply in replies if reply.status_code == 409)
        assert rejected["detail"] == {"code": "planning_task_active", "task_id": accepted["id"]}
        assert schedules == ["scheduled"]


def test_submission_observer_cancellation_cannot_drop_committed_scheduling(client):  # noqa: F811
    import asyncio
    import os

    import psycopg
    from pydantic import SecretStr

    from backend.app.product.task_coordinator import TaskCoordinator
    from backend.app.product.task_store import TaskStore
    from backend.app.schemas.request import PlanningRequest

    account = register(client)
    dsn = SecretStr(os.environ["PRODUCT_DATABASE_URL"])

    async def scenario():
        scheduled = asyncio.Event()
        coordinator = TaskCoordinator(TaskStore(), schedule=lambda work: scheduled.set())
        service = make_planning_service(FakeStructuredLLMClient([]))
        with psycopg.connect(dsn.get_secret_value()) as holder:
            holder.execute("SELECT id FROM app.users WHERE id=%s FOR UPDATE", (account["id"],))
            observation = asyncio.create_task(
                coordinator.submit(
                    account["id"],
                    "detached-acceptance",
                    PlanningRequest.model_validate(make_product_payload()),
                    None,
                    service,
                )
            )

            def is_waiting():
                with psycopg.connect(dsn.get_secret_value()) as connection:
                    return (
                        connection.execute(
                            "SELECT count(*) FROM pg_stat_activity "
                            "WHERE datname=current_database() AND wait_event_type='Lock'"
                        ).fetchone()[0]
                        > 0
                    )

            async with asyncio.timeout(5):
                while not await asyncio.to_thread(is_waiting):
                    await asyncio.sleep(0)
            observation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await observation
            holder.commit()
        await asyncio.wait_for(scheduled.wait(), 5)
        task = await asyncio.to_thread(
            coordinator.store.read, account["id"], key="detached-acceptance"
        )
        assert task["state"] == "pending"
        await coordinator.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "kind", ["needs_clarification", "safety_blocked", "provider_blocked", "failed"]
)
def test_real_v3_typed_terminal_outcomes_retain_input_without_a_preview(monkeypatch, kind):
    from contextlib import asynccontextmanager
    from datetime import date

    from backend.app.schemas.requirement_boundary import RequirementBoundaryError
    from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
    from backend.app.services.planning import PlanningService
    from backend.tests.api.test_product_planning import post_product_planning
    from backend.tests.fakes import FixedDateProvider
    from backend.tests.request_fixtures import make_request
    from backend.tests.services.test_preference_input_gate import draft, issue
    from backend.tests.versions.v3.test_wiring import OwnedRetrieval

    source = "A supplied private travel preference."
    if kind == "needs_clarification":
        response = draft(issue(text=source))
    elif kind == "safety_blocked":
        response = draft(
            issue("safety_self_harm", text=source, related_field=None),
            disposition="VALID",
            safety="SAFETY_BLOCK",
        )
    elif kind == "provider_blocked":
        response = RequirementBoundaryError(
            "private rejection",
            category="provider_request_rejected",
            provider_diagnostics={"provider_error_code": "content_filter", "private": source},
        )
    else:
        response = RuntimeError("PRIVATE external failure")
    external = FakeStructuredLLMClient([response])

    @asynccontextmanager
    async def dependencies(*args):
        yield PlannerDependencies(external)

    monkeypatch.setattr(
        "backend.app.versions.v3.runner.RuntimeRetrieval", lambda config: OwnedRetrieval()
    )
    service = PlanningService(
        RequestPlannerRuntime(dependency_factory=dependencies), FixedDateProvider(date(2026, 9, 11))
    )
    request = make_request(source)
    status, task = post_product_planning(service, request.model_dump(mode="json"))
    assert status == 202 and task["state"] == kind, task
    assert task["request"]["additional_preferences"] == source
    assert task["preview_id"] is None
    assert task["outcome"]["message"] and task["outcome"]["action"]
    if kind != "needs_clarification":
        assert source not in str(task["outcome"])
    assert "PRIVATE" not in str(task["outcome"])
    assert len(external.calls) == 1
