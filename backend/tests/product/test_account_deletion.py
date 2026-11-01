"""Account self-deletion, protection and revocation use an isolated Product database."""
# ruff: noqa: F811

import pytest

from backend.tests.product.test_accounts import client, register  # noqa: F401


def test_confirmed_self_deletion_revokes_current_and_existing_sessions(client):
    account = register(client)
    token = client.cookies.get("dayloom_session")
    response = client.request(
        "DELETE",
        "/api/auth/account",
        json={
            "password": "a secure password",
            "confirmed": True,
        },
        headers={"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]},
    )
    assert response.status_code == 204, response.text
    assert response.headers["cache-control"] == "no-store"
    # A delayed response must not expire a cookie issued by a newer account login.
    assert "set-cookie" not in response.headers
    assert client.get("/api/auth/current").status_code == 401
    client.cookies.clear()
    assert (
        client.get("/api/profile", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    )


@pytest.mark.parametrize("email", ["admin@admin.com", "  ADMIN@ADMIN.COM  "])
def test_default_test_admin_is_protected_by_the_server(client, email):
    account = register(client, email)
    assert client.get("/api/profile").json()["can_delete_account"] is False
    response = client.request(
        "DELETE",
        "/api/auth/account",
        json={
            "password": "a secure password",
            "confirmed": True,
        },
        headers={"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "protected_test_account"
    assert client.get("/api/auth/current").json()["id"] == account["id"]


def test_deletion_requires_password_confirmation_and_existing_csrf_rules(client):
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    valid = {"password": "a secure password", "confirmed": True}
    assert client.request("DELETE", "/api/auth/account", json=valid).status_code == 403
    wrong = client.request(
        "DELETE", "/api/auth/account", headers=headers, json={**valid, "password": "wrong password"}
    )
    assert wrong.status_code == 403 and wrong.json()["detail"]["code"] == "invalid_password"
    for body in (
        {"password": "a secure password"},
        {**valid, "confirmed": False},
        {**valid, "user_id": account["id"]},
    ):
        assert (
            client.request("DELETE", "/api/auth/account", headers=headers, json=body).status_code
            == 422
        )
    assert client.get("/api/auth/current").json()["id"] == account["id"]
    client.cookies.clear()
    assert client.request("DELETE", "/api/auth/account", json=valid).status_code == 401


def test_self_deletion_cascades_only_the_owners_travel_data(client):
    from backend.app.product.database import connect
    from backend.tests.product.test_drafts import editor
    from backend.tests.product.test_saved import pending

    other = register(client, "other@example.com")
    other_token = client.cookies.get("dayloom_session")
    owner = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": owner["csrf_token"]}
    draft = client.post(
        "/api/drafts",
        headers=headers,
        json={
            "title": "Private brief",
            "editor": editor(destination="Sydney"),
        },
    )
    assert draft.status_code == 201
    preview = pending(owner["id"])
    saved = client.post(f"/api/previews/{preview.id}/save", json={}, headers=headers)
    assert saved.status_code == 200
    response = client.request(
        "DELETE",
        "/api/auth/account",
        headers=headers,
        json={
            "password": "a secure password",
            "confirmed": True,
        },
    )
    assert response.status_code == 204
    with connect() as connection:
        assert (
            connection.execute("SELECT id FROM app.users WHERE id=%s", (owner["id"],)).fetchone()
            is None
        )
        assert connection.execute("SELECT id FROM app.users WHERE id=%s", (other["id"],)).fetchone()
        for table, column in (
            ("user_profiles", "user_id"),
            ("planning_drafts", "owner_id"),
            ("planning_tasks", "owner_id"),
            ("itinerary_previews", "owner_id"),
            ("trips", "owner_id"),
        ):
            assert (
                connection.execute(
                    f"SELECT count(*) AS n FROM app.{table} WHERE {column}=%s",
                    (owner["id"],),
                ).fetchone()["n"]
                == 0
            )
    client.cookies.clear()
    assert (
        client.get(
            "/api/auth/current", headers={"Authorization": f"Bearer {other_token}"}
        ).status_code
        == 200
    )


def test_active_planning_must_stop_before_account_deletion(client):
    from datetime import date
    from uuid import uuid4

    from backend.app.product.task_store import TaskStore
    from backend.app.schemas.request import PlanningRequest
    from backend.tests.api.test_product_planning import make_product_payload

    account = register(client)
    store = TaskStore()
    task, _ = store.accept(
        account["id"],
        str(uuid4()),
        PlanningRequest.model_validate(make_product_payload()),
        None,
        date(2026, 9, 11),
    )
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    body = {"password": "a secure password", "confirmed": True}
    blocked = client.request("DELETE", "/api/auth/account", headers=headers, json=body)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "account_tasks_active"
    assert client.get("/api/auth/current").status_code == 200
    store.stop(account["id"], task["id"])
    assert (
        client.request("DELETE", "/api/auth/account", headers=headers, json=body).status_code == 204
    )
