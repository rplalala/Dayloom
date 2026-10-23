"""Public migration execution and saved-domain constraints in isolated PostgreSQL."""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from psycopg import IntegrityError
from pydantic import SecretStr

from backend.app.product.database import connect
from backend.tests.product.browser_harness import isolated_environment
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_saved import historical_content, pending


def test_public_fresh_migration_rerun_checksum_and_tripworld_marker(client):  # noqa: F811
    with connect() as connection:
        connection.execute("CREATE SCHEMA IF NOT EXISTS tripworld")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS tripworld.saved_acceptance_marker "
            "(id integer PRIMARY KEY, value text)"
        )
        connection.execute(
            "INSERT INTO tripworld.saved_acceptance_marker VALUES (1,'untouched') "
            "ON CONFLICT DO NOTHING"
        )
        # The fixture has already proved this explicitly isolated test database.
        connection.execute("DROP SCHEMA app CASCADE")
    environment = isolated_environment(
        SecretStr(os.environ["DAYLOOM_DB_URL"]),
        "8122",
        "5122",
        Path(".scratch/saved-migration-tmp").resolve(),
    )
    command = [sys.executable, "scripts/migrate_product.py"]
    first = subprocess.run(command, env=environment, capture_output=True, text=True)
    migration_count = len(list(Path("backend/app/product/migrations").glob("*.sql")))
    assert first.returncode == 0 and f"{migration_count} applied" in first.stdout
    repeated = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert repeated.returncode == 0 and "0 applied" in repeated.stdout
    with connect() as connection:
        row = connection.execute(
            "UPDATE app.schema_migrations SET sha256='changed' "
            "WHERE name='005_saved_trips.sql' RETURNING name"
        ).fetchone()
        assert row is not None
    try:
        failed = subprocess.run(command, env=environment, capture_output=True, text=True)
        assert failed.returncode != 0
        assert "Migration checksum mismatch: 005_saved_trips.sql" in failed.stderr
    finally:
        import hashlib

        digest = hashlib.sha256(
            Path("backend/app/product/migrations/005_saved_trips.sql").read_bytes()
        ).hexdigest()
        with connect() as connection:
            connection.execute(
                "UPDATE app.schema_migrations SET sha256=%s WHERE name='005_saved_trips.sql'",
                (digest,),
            )
    with connect() as connection:
        assert (
            connection.execute(
                "SELECT value FROM tripworld.saved_acceptance_marker WHERE id=1"
            ).fetchone()["value"]
            == "untouched"
        )
        tables = connection.execute(
            "SELECT count(*) AS n FROM information_schema.tables "
            "WHERE table_schema='app' AND table_name <> 'schema_migrations'"
        ).fetchone()["n"]
        assert tables == 10


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE app.trip_activities SET position=-1 WHERE trip_id=%s",
        "UPDATE app.trip_activities SET time_use='invented' WHERE trip_id=%s",
        "UPDATE app.trip_activities SET activity_id=' ' WHERE trip_id=%s",
        "UPDATE app.trip_activities SET title='' WHERE trip_id=%s",
        "UPDATE app.trip_activities SET cost_amount=-1,cost_currency='AUD' WHERE trip_id=%s",
        "UPDATE app.trip_activities SET cost_amount='NaN',cost_currency='AUD' WHERE trip_id=%s",
        "UPDATE app.trip_activities SET cost_amount=0,cost_currency=NULL WHERE trip_id=%s",
        "UPDATE app.trip_weather SET temperature_min_c='Infinity' WHERE trip_id=%s",
        "UPDATE app.trip_weather SET max_wind_speed_kph=-1 WHERE trip_id=%s",
        "UPDATE app.trip_weather SET precipitation_probability_percent=101 WHERE trip_id=%s",
        "UPDATE app.trip_transfers SET distance_meters='NaN' WHERE trip_id=%s",
        "UPDATE app.trip_transfers SET reserve_seconds=-1 WHERE trip_id=%s",
        "UPDATE app.trip_transfers SET estimate_kind='invented' WHERE trip_id=%s",
        "UPDATE app.trip_transfers SET validation_state='SUCCESS' WHERE trip_id=%s",
        "UPDATE app.trip_transfers SET to_activity_id=from_activity_id WHERE trip_id=%s",
        "UPDATE app.trip_transfers SET day_position=1 WHERE trip_id=%s",
        "UPDATE app.trip_nearby SET resolved_day_position=1 WHERE trip_id=%s AND position=0",
        "UPDATE app.trip_nearby SET resolved_activity_id=NULL WHERE trip_id=%s AND position=0",
        "UPDATE app.trips SET source_kind='forged' WHERE id=%s",
        "UPDATE app.trips SET title=' ' WHERE id=%s",
    ],
)
def test_saved_domain_rejects_illegal_values_and_cross_day_endpoints(client, mutation):  # noqa: F811
    account = register(client)
    detail = pending(account["id"], **historical_content())
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    saved_id = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={}).json()[
        "saved_trip_id"
    ]
    with pytest.raises(IntegrityError), connect() as connection:
        connection.execute(mutation, (saved_id,))
    assert client.get(f"/api/trips/{saved_id}").status_code == 200


def test_saved_same_owner_cross_trip_keys_and_account_cascade(client):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    detail = pending(account["id"], **historical_content())
    saved_id = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={}).json()[
        "saved_trip_id"
    ]
    another = pending(
        account["id"],
        days=[
            {
                "date": "2020-01-04",
                "activities": [
                    {
                        "activity_id": "other-trip",
                        "title": "Only in another trip",
                        "start_time": "2020-01-04T09:00:00",
                        "end_time": "2020-01-04T10:00:00",
                    }
                ],
            }
        ],
    )
    client.post(f"/api/previews/{another.id}/save", headers=headers, json={})
    with pytest.raises(IntegrityError), connect() as connection:
        connection.execute(
            "UPDATE app.trip_transfers SET to_activity_id='other-trip' WHERE trip_id=%s",
            (saved_id,),
        )
    client.cookies.clear()
    other = register(client, "other@example.com")
    for mutation in [
        ("UPDATE app.trips SET owner_id=%s WHERE id=%s", (other["id"], saved_id)),
        ("UPDATE app.trips SET source_preview_id=%s WHERE id=%s", (uuid4(), saved_id)),
    ]:
        with pytest.raises(IntegrityError), connect() as connection:
            connection.execute(*mutation)
    with connect() as connection:
        connection.execute("DELETE FROM app.users WHERE id=%s", (account["id"],))
        for table in (
            "trips",
            "trip_weather",
            "trip_activities",
            "trip_nearby",
            "trip_transfers",
            "itinerary_previews",
            "planning_tasks",
        ):
            assert connection.execute(f"SELECT count(*) AS n FROM app.{table}").fetchone()["n"] == 0


def test_display_migration_upgrades_existing_rows_without_changing_public_detail(client):  # noqa: F811
    import hashlib

    account = register(client)
    detail = pending(account["id"])
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    decision = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={}).json()
    trip_id = decision["saved_trip_id"]
    before = client.get(f"/api/trips/{trip_id}").json()
    with connect() as connection:
        # Simulate a genuine pre-007 saved row inside this isolated test database.
        connection.execute("ALTER TABLE app.trips DROP COLUMN display_metadata")
        connection.execute(
            "DELETE FROM app.schema_migrations WHERE name='007_display_metadata.sql'"
        )
    environment = isolated_environment(
        SecretStr(os.environ["DAYLOOM_DB_URL"]),
        "8122",
        "5122",
        Path(".scratch/display-migration-tmp").resolve(),
    )
    command = [sys.executable, "scripts/migrate_product.py"]
    applied = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert applied.returncode == 0 and "1 applied" in applied.stdout
    assert client.get(f"/api/trips/{trip_id}").json() == before
    with connect() as connection:
        assert (
            connection.execute(
                "SELECT display_metadata FROM app.trips WHERE id=%s", (trip_id,)
            ).fetchone()["display_metadata"]
            == {}
        )
    repeated = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert repeated.returncode == 0 and "0 applied" in repeated.stdout
    migration = Path("backend/app/product/migrations/007_display_metadata.sql")
    try:
        with connect() as connection:
            connection.execute(
                "UPDATE app.schema_migrations SET sha256='changed' WHERE name=%s", (migration.name,)
            )
        failed = subprocess.run(command, env=environment, capture_output=True, text=True)
        assert (
            failed.returncode != 0
            and "Migration checksum mismatch: 007_display_metadata.sql" in failed.stderr
        )
    finally:
        with connect() as connection:
            connection.execute(
                "UPDATE app.schema_migrations SET sha256=%s WHERE name=%s",
                (hashlib.sha256(migration.read_bytes()).hexdigest(), migration.name),
            )
