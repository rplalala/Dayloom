"""Public API responsiveness during an actual isolated PostgreSQL import lock wait."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
from pydantic import SecretStr

from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_imports import source


def test_import_row_lock_does_not_block_health_or_stop_api(client):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "lock-wait",
    }
    database = SecretStr(os.environ["PRODUCT_TEST_DATABASE_URL"])
    with (
        psycopg.connect(database.get_secret_value()) as locker,
        psycopg.connect(database.get_secret_value(), autocommit=True) as observer,
        ThreadPoolExecutor(max_workers=2) as workers,
    ):
        # Deliberately hold the owner's real database row. The observer only synchronizes
        # the lock wait; acceptance assertions use the public HTTP interfaces.
        locker.execute("SELECT id FROM app.users WHERE id=%s FOR UPDATE", (account["id"],))
        importing = workers.submit(
            client.post, "/api/imports", headers=headers, content=json.dumps(source())
        )
        try:
            deadline = time.monotonic() + 5
            while not observer.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                    "WHERE datname=current_database() AND wait_event_type='Lock' "
                    "AND query LIKE 'SELECT id FROM app.users%')"
            ).fetchone()[0]:
                assert time.monotonic() < deadline, "Import never reached the controlled row lock"
                time.sleep(0.02)
            assert not importing.done()
            health = workers.submit(client.get, "/health").result(timeout=2)
            assert health.status_code == 200 and health.json() == {"status": "ok"}
            stopped = workers.submit(
                client.post, f"/api/planning/tasks/{uuid4()}/stop", headers=headers
            ).result(timeout=2)
            assert stopped.status_code == 404
            assert not importing.done()
        finally:
            locker.rollback()
        result = importing.result(timeout=5)
        assert result.status_code == 200, result.text
        assert client.get("/api/imports/lock-wait").json()["id"] == result.json()["id"]
