"""Real database lock interleavings and exact canonical operation identity."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from time import monotonic
from uuid import uuid4

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr

from backend.app.api.dependencies import get_planning_service
from backend.app.product.detail import ProductDetail
from backend.app.product.settings import ProductSettings
from backend.app.product.task_coordinator import TaskCoordinator
from backend.app.product.task_store import TaskStore
from backend.app.product.tasks import get_coordinator
from backend.app.schemas.request import PlanningRequest
from backend.tests.api.test_product_planning import make_planning_service, make_product_payload
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient


def wait_for_lock(dsn: SecretStr, application_name):
    deadline = monotonic() + 5
    with psycopg.connect(dsn.get_secret_value(), autocommit=True) as connection:
        while monotonic() < deadline:
            if connection.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE application_name=%s "
                "AND wait_event_type='Lock'",
                (application_name,),
            ).fetchone()[0]:
                return
    raise AssertionError("The controlled database operation did not reach its lock gate")


def named_store(dsn: SecretStr, name, clock):
    settings = ProductSettings().model_copy(
        update={
            "database_url": SecretStr(
                make_conninfo(
                    dsn.get_secret_value(),
                    application_name=name,
                    options="-c statement_timeout=8000",
                )
            )
        }
    )
    return TaskStore(settings, clock=clock, pending_seconds=10, lease_seconds=10)


@pytest.mark.parametrize("transition", ["claim", "renew", "complete", "complete-new-operation"])
def test_replay_waits_for_current_claim_lease_or_completion(client, transition):  # noqa: F811
    new_operation = transition == "complete-new-operation"
    if new_operation:
        transition = "complete"
    account = register(client)
    dsn = SecretStr(os.environ["DAYLOOM_DB_URL"])
    instant = [datetime(2026, 9, 11, tzinfo=UTC)]
    store = named_store(dsn, "replay-regression", lambda: instant[0])
    worker = named_store(dsn, "worker-regression", lambda: instant[0])
    request = PlanningRequest.model_validate(make_product_payload())
    task, _ = store.accept(account["id"], "racing-replay", request, None, date(2026, 9, 11))
    claim = None if transition == "claim" else worker.claim(task["id"])
    instant[0] += timedelta(seconds=5)
    detail = ProductDetail(
        id=str(uuid4()),
        title="Retained completion",
        destination="Sydney",
        provenance="generated",
        trust="generated_projection",
    )
    # The trigger gates a real transition after it owns its task row. Another connection
    # can observe the old committed row, but must not recover it without waiting/re-reading.
    condition = {
        "claim": "OLD.state='pending' AND NEW.state='running'",
        "renew": "OLD.state='running' AND NEW.lease_deadline>OLD.lease_deadline",
        "complete": "true",
    }[transition]
    table = "itinerary_previews" if transition == "complete" else "planning_tasks"
    event = "INSERT" if transition == "complete" else "UPDATE"
    with psycopg.connect(dsn.get_secret_value()) as connection:
        connection.execute(
            "CREATE FUNCTION app.gate_task_transition() RETURNS trigger "
            "LANGUAGE plpgsql AS $$ BEGIN IF "
            + condition
            + " THEN PERFORM pg_advisory_xact_lock(202661); END IF; RETURN NEW; END; $$"
        )
        connection.execute(
            "CREATE TRIGGER gate_task_transition BEFORE "
            + event
            + " ON app."
            + table
            + " FOR EACH ROW EXECUTE FUNCTION app.gate_task_transition()"
        )
    try:
        with psycopg.connect(dsn.get_secret_value(), autocommit=True) as gate:
            gate.execute("SELECT pg_advisory_lock(202661)")
            with ThreadPoolExecutor(2) as pool:
                try:
                    operation = {
                        "claim": lambda: worker.claim(task["id"]),
                        "renew": lambda: worker.renew(claim),
                        "complete": lambda: worker.complete(claim, detail),
                    }[transition]
                    execution = pool.submit(operation)
                    wait_for_lock(dsn, "worker-regression")
                    instant[0] += timedelta(
                        seconds=6
                    )  # Old deadline elapsed; new lease stays live.
                    replay = pool.submit(
                        store.accept,
                        account["id"],
                        "new-operation" if new_operation else "racing-replay",
                        request,
                        None,
                        date(2026, 9, 11),
                    )
                    wait_for_lock(dsn, "replay-regression")
                    gate.execute("SELECT pg_advisory_unlock(202661)")
                    assert execution.result(timeout=8)
                    observed, created = replay.result(timeout=8)
                    if new_operation:
                        assert created and observed["id"] != task["id"]
                        assert observed["state"] == "pending"
                        observed = store.read(account["id"], task["id"])
                    else:
                        assert not created and observed["id"] == task["id"]
                    assert observed["state"] == (
                        "completed" if transition == "complete" else "running"
                    )
                    if transition == "complete":
                        assert observed["preview_id"] == detail.id
                        assert store.previews(account["id"], detail.id)[0]["state"] == "pending"
                finally:
                    gate.execute("SELECT pg_advisory_unlock_all()")
    finally:
        with psycopg.connect(dsn.get_secret_value()) as connection:
            connection.execute("DROP TRIGGER gate_task_transition ON app." + table)
            connection.execute("DROP FUNCTION app.gate_task_transition()")


@pytest.mark.parametrize(
    "original,changed,equivalent",
    [
        (
            "1.00000000000000000000000000001",
            "1.00000000000000000000000000002",
            "1.0000000000000000000000000000100",
        ),
        ("1E+1000000", "1E+999999", "10E+999999"),
        ("0E+9000", "1E-9000", "-0.00"),
    ],
)
def test_canonical_api_distinguishes_exact_amounts_without_expanding_exponents(
    client,  # noqa: F811
    original,
    changed,
    equivalent,  # noqa: F811
):
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    external = FakeStructuredLLMClient([])
    coordinator = TaskCoordinator(TaskStore(), schedule=lambda work: None)
    client.app.dependency_overrides[get_coordinator] = lambda: coordinator
    client.app.dependency_overrides[get_planning_service] = lambda: make_planning_service(external)
    payload = {"operation_key": "exact-amount", "request": make_product_payload()}

    def submit(amount):
        return client.post(
            "/api/planning/tasks",
            headers=headers,
            json={
                **payload,
                "request": {**payload["request"], "budget": {"amount": amount, "currency": "AUD"}},
            },
        )

    try:
        accepted = submit(original)
        assert accepted.status_code == 202, accepted.text
        conflict = submit(changed)
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "operation_key_conflict"
        replay = submit(equivalent)
        assert replay.status_code == 202 and replay.json()["id"] == accepted.json()["id"]
        assert external.calls == []
    finally:
        client.app.dependency_overrides.clear()


@pytest.mark.parametrize("winner", ["stop", "completion"])
def test_stop_and_completion_serialize_and_stale_execution_cannot_replace_winner(client, winner):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    dsn = SecretStr(os.environ["DAYLOOM_DB_URL"])
    instant = [datetime(2026, 9, 11, tzinfo=UTC)]
    stop_store = named_store(dsn, "stop-race", lambda: instant[0])
    worker = named_store(dsn, "completion-race", lambda: instant[0])
    coordinator = TaskCoordinator(stop_store, schedule=lambda work: None)
    client.app.dependency_overrides[get_coordinator] = lambda: coordinator
    external = FakeStructuredLLMClient([])
    client.app.dependency_overrides[get_planning_service] = lambda: make_planning_service(external)
    try:
        task = client.post(
            "/api/planning/tasks",
            json={"operation_key": "stop-completion-race", "request": make_product_payload()},
            headers=headers,
        ).json()
        claim = worker.claim(task["id"])
        detail = ProductDetail(
            id=str(uuid4()),
            title="Race survivor",
            destination="Sydney",
            provenance="generated",
            trust="generated_projection",
        )
        table = "planning_tasks" if winner == "stop" else "itinerary_previews"
        event = "UPDATE" if winner == "stop" else "INSERT"
        condition = "NEW.state='stopping'" if winner == "stop" else "true"
        with psycopg.connect(dsn.get_secret_value()) as connection:
            connection.execute(
                "CREATE FUNCTION app.gate_stop_race() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN IF "
                + condition
                + " THEN PERFORM pg_advisory_xact_lock(203661); END IF; RETURN NEW; END; $$"
            )
            connection.execute(
                "CREATE TRIGGER gate_stop_race BEFORE "
                + event
                + " ON app."
                + table
                + " FOR EACH ROW EXECUTE FUNCTION app.gate_stop_race()"
            )
        try:
            with (
                psycopg.connect(dsn.get_secret_value(), autocommit=True) as gate,
                ThreadPoolExecutor(2) as pool,
            ):
                gate.execute("SELECT pg_advisory_lock(203661)")

                def stop():
                    return client.post(f"/api/planning/tasks/{task['id']}/stop", headers=headers)

                def complete():
                    return worker.complete(claim, detail)

                try:
                    first = pool.submit(stop if winner == "stop" else complete)
                    wait_for_lock(dsn, "stop-race" if winner == "stop" else "completion-race")
                    second = pool.submit(complete if winner == "stop" else stop)
                    wait_for_lock(dsn, "completion-race" if winner == "stop" else "stop-race")
                finally:
                    gate.execute("SELECT pg_advisory_unlock_all()")
                first_reply, second_reply = first.result(timeout=8), second.result(timeout=8)
                reply = first_reply if winner == "stop" else second_reply
                assert reply.status_code == 200
                assert (second_reply if winner == "stop" else first_reply) is (
                    winner == "completion"
                )
        finally:
            with psycopg.connect(dsn.get_secret_value()) as connection:
                connection.execute("DROP TRIGGER gate_stop_race ON app." + table)
                connection.execute("DROP FUNCTION app.gate_stop_race()")
        url = f"/api/planning/tasks/{task['id']}"
        if winner == "stop":
            assert worker.acknowledge_stop(claim)
            assert not worker.acknowledge_stop(claim)
            assert client.get(url).json()["state"] == "cancelled"
            assert client.get("/api/previews").json() == []
        else:
            retained = client.get(f"/api/previews/{detail.id}").json()
            assert reply.json()["state"] == "completed" and reply.json()["preview_id"] == detail.id
            assert not worker.acknowledge_stop(claim)
            assert client.get(f"/api/previews/{detail.id}").json() == retained
        finished = client.get(url).json()
        assert client.post(url + "/stop", headers=headers).json() == finished
        assert not worker.complete(claim, detail)
        assert not worker.finish(claim, "failed", {"code": "stale"})
        assert not worker.renew(claim)
        assert client.get(url).json() == finished
        assert external.calls == []
    finally:
        client.app.dependency_overrides.clear()
