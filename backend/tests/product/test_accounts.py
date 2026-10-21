"""Product acceptance uses only an explicitly isolated PostgreSQL database."""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from backend.tests.product.browser_harness import isolated_environment
from backend.tests.product.database_safety import require_test_database


@pytest.fixture
def client(monkeypatch):
    dsn = SecretStr(os.environ.get("PRODUCT_TEST_DATABASE_URL", ""))
    if not dsn.get_secret_value():
        pytest.skip("Set PRODUCT_TEST_DATABASE_URL to an isolated test database")
    require_test_database(dsn)
    monkeypatch.setenv("PRODUCT_DATABASE_URL", dsn.get_secret_value())
    monkeypatch.setenv("PRODUCT_JWT_SECRET", "test-signing-key-with-at-least-32-characters")
    monkeypatch.setenv("PRODUCT_ALLOW_INSECURE_LOOPBACK", "true")
    monkeypatch.setenv("PRODUCT_ORIGIN", "http://localhost:5120")
    migration_environment = isolated_environment(
        dsn, "8120", "5120", Path(".scratch/account-migration-tmp").resolve()
    )
    subprocess.run(
        [sys.executable, "scripts/migrate_product.py"], check=True, env=migration_environment
    )
    with psycopg.connect(dsn.get_secret_value()) as connection:
        connection.execute("TRUNCATE app.users CASCADE")
    from backend.app.main import app

    with TestClient(app, base_url="http://localhost:5120") as session:
        yield session


def test_register_returns_current_account_and_duplicate_is_normalized(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": " Alice@Example.COM ",
            "password": "a secure password",
            "display_name": "Alice Smith",
        },
        headers={"Origin": "http://localhost:5120"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["initials"] == "AS"
    assert response.json()["email"] == "alice@example.com"
    assert "password" not in response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    current = client.get("/api/auth/current")
    assert current.json()["id"] == response.json()["id"]
    duplicate = client.post(
        "/api/auth/register",
        json={
            "email": "ALICE@example.com",
            "password": "a secure password",
            "display_name": "Other",
        },
        headers={"Origin": "http://localhost:5120"},
    )
    assert duplicate.status_code == 409


def register(client, email="alice@example.com"):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "a secure password",
            "display_name": "Alice Smith",
        },
        headers={"Origin": "http://localhost:5120"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_cookie_csrf_origin_and_logout_revoke_all_tokens(client):
    account = register(client)
    old = client.cookies.get("dayloom_session")
    assert client.post("/api/auth/logout").status_code == 403
    assert (
        client.post("/api/auth/logout", headers={"Origin": "http://localhost:5120"}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/logout",
            headers={"Origin": "https://evil.example", "X-CSRF-Token": account["csrf_token"]},
        ).status_code
        == 403
    )
    response = client.post(
        "/api/auth/login",
        json={"email": account["email"], "password": "a secure password"},
        headers={"Origin": "http://localhost:5120"},
    )
    assert response.status_code == 200
    new = client.cookies.get("dayloom_session")
    assert (
        client.post(
            "/api/auth/logout",
            headers={
                "Origin": "http://localhost:5120",
                "X-CSRF-Token": response.json()["csrf_token"],
            },
        ).status_code
        == 204
    )
    assert client.get("/api/auth/current").status_code == 401
    for token in [old, new]:
        response = client.get("/api/auth/current", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "session_revoked"


def test_tokens_generic_login_errors_and_public_protection(client):
    account = register(client)
    token = client.cookies.get("dayloom_session")
    claims = jwt.decode(token, options={"verify_signature": False})
    client.cookies.clear()
    assert client.get("/api/auth/current").status_code == 401
    variants = [
        {**claims, "exp": datetime.now(UTC) - timedelta(seconds=1)},
        {**claims, "sub": str(uuid4())},
        {**claims, "ver": 99},
    ]
    for variant in variants:
        signed = jwt.encode(
            variant, "test-signing-key-with-at-least-32-characters", algorithm="HS256"
        )
        assert (
            client.get(
                "/api/auth/current", headers={"Authorization": f"Bearer {signed}"}
            ).status_code
            == 401
        )
    assert (
        client.get(
            "/api/auth/current", headers={"Authorization": f"Bearer {token}tampered"}
        ).status_code
        == 401
    )
    errors = []
    for email in [account["email"], "absent@example.com"]:
        errors.append(
            client.post(
                "/api/auth/login",
                json={"email": email, "password": "wrong password"},
                headers={"Origin": "http://localhost:5120"},
            ).json()
        )
    assert errors[0] == errors[1] == {"detail": {"code": "invalid_credentials"}}
    assert client.post("/api/planning", json={}).status_code == 401
    assert client.post("/api/planning/stream", json={}).status_code == 401


def test_registration_profile_failure_rolls_back_account(client):
    dsn = SecretStr(os.environ["PRODUCT_DATABASE_URL"])
    with psycopg.connect(dsn.get_secret_value()) as connection:
        connection.execute("""CREATE FUNCTION app.reject_profile()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'deliberate acceptance failure'; END; $$""")
        connection.execute("""CREATE TRIGGER reject_profile BEFORE INSERT ON app.user_profiles
            FOR EACH ROW EXECUTE FUNCTION app.reject_profile()""")
    try:
        with TestClient(
            client.app, base_url="http://localhost:5120", raise_server_exceptions=False
        ) as failing:
            response = failing.post(
                "/api/auth/register",
                json={
                    "email": "rollback@example.com",
                    "password": "a secure password",
                    "display_name": "Alice",
                },
                headers={"Origin": "http://localhost:5120"},
            )
            assert response.status_code == 500
        with psycopg.connect(dsn.get_secret_value()) as connection:
            assert (
                connection.execute(
                    "SELECT count(*) FROM app.users WHERE email='rollback@example.com'"
                ).fetchone()[0]
                == 0
            )
    finally:
        with psycopg.connect(dsn.get_secret_value()) as connection:
            connection.execute("DROP TRIGGER reject_profile ON app.user_profiles")
            connection.execute("DROP FUNCTION app.reject_profile()")
    register(client, "rollback@example.com")


def test_public_migration_rerun_checksum_and_tripworld_preservation(client, tmp_path):
    from backend.app.product.database import migrate

    dsn = SecretStr(os.environ["PRODUCT_DATABASE_URL"])
    with psycopg.connect(dsn.get_secret_value()) as connection:
        connection.execute("CREATE SCHEMA IF NOT EXISTS tripworld")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS tripworld.acceptance_seed"
            "(id integer PRIMARY KEY, text text)"
        )
        connection.execute(
            "INSERT INTO tripworld.acceptance_seed VALUES (1,'untouched') ON CONFLICT DO NOTHING"
        )
    assert migrate(dsn.get_secret_value()) == []
    source = Path("backend/app/product/migrations/001_accounts.sql")
    (tmp_path / source.name).write_bytes(source.read_bytes() + b"\n-- changed")
    with pytest.raises(ValueError, match="checksum"):
        migrate(dsn.get_secret_value(), tmp_path)
    with psycopg.connect(dsn.get_secret_value()) as connection:
        assert (
            connection.execute("SELECT text FROM tripworld.acceptance_seed WHERE id=1").fetchone()[
                0
            ]
            == "untouched"
        )
        assert [
            row[0]
            for row in connection.execute("SELECT name FROM app.schema_migrations ORDER BY name")
        ] == sorted(path.name for path in source.parent.glob("*.sql"))


def test_validation_errors_do_not_echo_passwords(client):
    password = "secret-material-" * 12
    response = client.post(
        "/api/auth/register",
        json={
            "email": "validation@example.com",
            "password": password,
            "display_name": "Alice",
        },
        headers={"Origin": "http://localhost:5120"},
    )
    assert response.status_code == 422
    assert password not in response.text
    assert response.json()["detail"][0]["loc"] == ["body", "password"]


def test_application_recreation_keeps_accounts_and_revocation(client):
    from backend.app.main import create_app

    account = register(client)
    token = client.cookies.get("dayloom_session")
    with TestClient(create_app(), base_url="http://localhost:5120") as recreated:
        response = recreated.get("/api/auth/current", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["id"] == account["id"]
        assert (
            recreated.post(
                "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == 204
        )
    assert client.get("/api/auth/current").json()["detail"]["code"] == "session_revoked"
