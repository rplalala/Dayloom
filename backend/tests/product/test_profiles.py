"""Owner profile API and database acceptance on isolated PostgreSQL."""
# Imported pytest fixtures are intentionally named by their public fixture names.
# ruff: noqa: F811

import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from backend.tests.product.test_accounts import client, register  # noqa: F401


def test_profile_defaults_persist_after_application_recreation(client):
    from backend.app.main import create_app

    account = register(client)
    initial = client.get("/api/profile")
    assert initial.status_code == 200
    assert initial.json() == {
        "display_name": "Alice Smith",
        "initials": "AS",
        "currency": "AUD",
        "interests": [],
        "pace": None,
        "transport": [],
        "notes": "",
    }
    desired = {
        "display_name": "  Ada Lovelace  ",
        "currency": "JPY",
        "interests": ["Nature", "Nature", "Art & museums"],
        "pace": "relaxed",
        "transport": ["walk", "transit", "walk"],
        "notes": "  Keep quiet mornings.\n ",
    }
    result = client.put(
        "/api/profile",
        json=desired,
        headers={
            "Origin": "http://localhost:5120",
            "X-CSRF-Token": account["csrf_token"],
        },
    )
    assert result.status_code == 200, result.text
    expected = {
        **desired,
        "display_name": "Ada Lovelace",
        "initials": "AL",
        "interests": ["Nature", "Art & museums"],
        "transport": ["walk", "transit"],
    }
    assert result.json() == expected
    token = client.cookies.get("dayloom_session")
    with TestClient(create_app()) as recreated:
        restored = recreated.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
        assert restored.json() == expected
        assert restored.headers["cache-control"] == "no-store"
    assert client.get("/api/auth/current").json()["initials"] == "AL"


def test_profile_is_owner_only_and_rejects_unsupported_fields(client):
    first = register(client)
    token = client.cookies.get("dayloom_session")
    register(client, "bob@example.com")
    assert client.get("/api/profile").json()["display_name"] == "Alice Smith"
    profile = {
        "display_name": "Bob",
        "currency": "USD",
        "interests": [],
        "pace": None,
        "transport": [],
        "notes": "Bob only",
    }
    second = client.get("/api/auth/current").json()
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": second["csrf_token"]}
    assert client.put("/api/profile", json=profile).status_code == 403
    assert client.put("/api/profile", json=profile, headers=headers).status_code == 200
    client.cookies.clear()
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/profile/" + first["id"]).status_code == 404
    bearer = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/profile", headers=bearer).json()["notes"] == ""
    for change in [
        {"currency": "XXX"},
        {"interests": ["invented"]},
        {"pace": "fast"},
        {"transport": ["flying"]},
        {"display_name": " "},
        {"avatar_url": "https://example.com/image.jpg"},
        {"notes": "x" * 24001},
    ]:
        response = client.put("/api/profile", json={**profile, **change}, headers=bearer)
        assert response.status_code == 422
    assert client.get("/api/profile", headers=bearer).json()["notes"] == ""


def test_profile_database_domains_deduplication_and_owner_cascade(client):
    account = register(client)
    dsn = SecretStr(os.environ["PRODUCT_DATABASE_URL"])
    for assignment in [
        "currency='XXX'",
        "pace='fast'",
        "transport=ARRAY['flying']",
        "interests=ARRAY['Nature','Nature']",
        "transport=ARRAY['walk','walk']",
        "interests=ARRAY['invented']",
        "notes=repeat('x',24001)",
    ]:
        with psycopg.connect(dsn.get_secret_value()) as connection:
            with pytest.raises(psycopg.errors.CheckViolation):
                connection.execute(f"UPDATE app.user_profiles SET {assignment}")
            connection.rollback()
    with psycopg.connect(dsn.get_secret_value()) as connection:
        connection.execute("DELETE FROM app.users WHERE id=%s", (account["id"],))
        assert connection.execute("SELECT count(*) FROM app.user_profiles").fetchone()[0] == 0
    assert client.get("/api/profile").status_code == 401
