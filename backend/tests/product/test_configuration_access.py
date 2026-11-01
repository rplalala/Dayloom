"""Configuration access is optional, persisted and independent of Product accounts."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.product.configuration import LocalConfiguration
from backend.app.product.configuration_api import enable_local_configuration


def local_client(root):
    manager = LocalConfiguration(root, origin="http://localhost:5173", environment={})
    app = create_app()
    enable_local_configuration(app, manager, ready=True)
    return TestClient(
        app,
        base_url=manager.origin,
        client=("127.0.0.1", 50000),
        headers={"Origin": manager.origin},
    )


def test_configuration_opens_without_password_and_retains_csrf_protection(tmp_path):
    with local_client(tmp_path) as client:
        access = client.get("/api/config/access")
        assert access.status_code == 200
        assert access.json()["password_required"] is False
        session = client.post("/api/config/session", json={})
        assert session.status_code == 200
        assert "HttpOnly" in session.headers["set-cookie"]
        view = client.get("/api/config")
        assert view.status_code == 200
        assert (
            client.put(
                "/api/config",
                json={
                    "revision": view.json()["revision"],
                    "changes": {},
                },
            ).status_code
            == 403
        )
        client.headers["X-CSRF-Token"] = session.json()["csrf_token"]
        assert (
            client.put(
                "/api/config",
                json={
                    "revision": view.json()["revision"],
                    "changes": {},
                },
            ).status_code
            == 200
        )


def test_password_protection_survives_restart_and_revokes_open_sessions(tmp_path):
    with local_client(tmp_path) as client:
        session = client.post("/api/config/session", json={}).json()
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        response = client.put(
            "/api/config/access",
            json={
                "revision": client.get("/api/config/access").json()["revision"],
                "enabled": True,
                "new_password": "private-config-password",
                "confirmation": "private-config-password",
            },
        )
        assert response.status_code == 200
        assert response.json()["password_required"] is True
        assert "private-config-password" not in response.text
        assert "password_hash" not in response.text
        assert client.get("/api/config").status_code == 401
    with local_client(tmp_path) as restarted:
        assert restarted.get("/api/config/access").json()["password_required"] is True
        assert restarted.post("/api/config/session", json={}).status_code == 401
        assert (
            restarted.post("/api/config/session", json={"password": "incorrect"}).status_code == 401
        )
        assert (
            restarted.post(
                "/api/config/session",
                json={
                    "password": "private-config-password",
                },
            ).status_code
            == 200
        )
        assert restarted.get("/api/config").status_code == 200
    stored = (tmp_path / ".config-access.json").read_text("utf-8")
    assert "private-config-password" not in stored
    assert "$argon2id$" in stored


def protect(client, password="private-config-password"):
    session = client.post("/api/config/session", json={}).json()
    client.headers["X-CSRF-Token"] = session["csrf_token"]
    response = client.put(
        "/api/config/access",
        json={
            "revision": client.get("/api/config/access").json()["revision"],
            "enabled": True,
            "new_password": password,
            "confirmation": password,
        },
    )
    assert response.status_code == 200
    session = client.post("/api/config/session", json={"password": password}).json()
    client.headers["X-CSRF-Token"] = session["csrf_token"]


def test_changing_and_disabling_protection_require_the_current_password(tmp_path):
    with local_client(tmp_path) as client:
        protect(client)
        revision = client.get("/api/config/access").json()["revision"]
        change = {
            "revision": revision,
            "enabled": True,
            "new_password": "replacement-private-password",
            "confirmation": "replacement-private-password",
        }
        assert client.put("/api/config/access", json=change).status_code == 401
        change["current_password"] = "private-config-password"
        assert client.put("/api/config/access", json=change).status_code == 200
        assert client.get("/api/config").status_code == 401
        assert (
            client.post(
                "/api/config/session", json={"password": "private-config-password"}
            ).status_code
            == 401
        )
        session = client.post(
            "/api/config/session",
            json={
                "password": "replacement-private-password",
            },
        ).json()
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        disable = {
            "revision": client.get("/api/config/access").json()["revision"],
            "enabled": False,
        }
        assert client.put("/api/config/access", json=disable).status_code == 401
        disable["current_password"] = "replacement-private-password"
        assert client.put("/api/config/access", json=disable).status_code == 200
    with local_client(tmp_path) as restarted:
        assert restarted.get("/api/config/access").json()["password_required"] is False
        assert restarted.post("/api/config/session", json={}).status_code == 200


def test_access_changes_revoke_other_process_sessions(tmp_path):
    with local_client(tmp_path) as first, local_client(tmp_path) as second:
        second.post("/api/config/session", json={})
        assert second.get("/api/config").status_code == 200
        protect(first)
        assert second.get("/api/config").status_code == 401
        assert second.get("/api/config/access").json()["password_required"] is True


@pytest.mark.parametrize("content", ["broken json", "{}", '{"password_hash": null}'])
def test_unreadable_access_settings_never_fall_back_to_open_access(tmp_path, content):
    (tmp_path / ".config-access.json").write_text(content, encoding="utf-8")
    with local_client(tmp_path) as client:
        for response in [
            client.get("/api/config/access"),
            client.post("/api/config/session", json={}),
        ]:
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "configuration_access_unreadable"


def test_password_attempts_are_bounded_and_errors_never_echo_credentials(tmp_path):
    with local_client(tmp_path) as client:
        protect(client)
        client.delete("/api/config/session")
        for _ in range(10):
            response = client.post(
                "/api/config/session", json={"password": "wrong-private-password"}
            )
            assert response.status_code == 401
            assert "wrong-private-password" not in response.text
        assert (
            client.post(
                "/api/config/session", json={"password": "private-config-password"}
            ).status_code
            == 429
        )


@pytest.mark.parametrize(
    "payload,status",
    [
        ({"enabled": True}, 400),
        ({"enabled": True, "new_password": "short", "confirmation": "short"}, 422),
        (
            {
                "enabled": True,
                "new_password": "valid-private-password",
                "confirmation": "different",
            },
            400,
        ),
    ],
)
def test_invalid_password_updates_leave_default_access_unchanged(tmp_path, payload, status):
    with local_client(tmp_path) as client:
        session = client.post("/api/config/session", json={}).json()
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        response = client.put(
            "/api/config/access",
            json={
                "revision": client.get("/api/config/access").json()["revision"],
                **payload,
            },
        )
        assert response.status_code == status
        assert "valid-private-password" not in response.text
        assert client.get("/api/config/access").json()["password_required"] is False


def test_default_access_still_rejects_remote_hosts_origins_and_forwarded_peers(tmp_path):
    with local_client(tmp_path) as client:
        assert (
            client.get("/api/config/access", headers={"Host": "untrusted.example"}).status_code
            == 403
        )
        assert (
            client.post(
                "/api/config/session", json={}, headers={"Origin": "https://untrusted.example"}
            ).status_code
            == 403
        )
        app = client.app
    with TestClient(app, base_url="http://localhost:5173", client=("192.0.2.5", 50000)) as remote:
        assert (
            remote.get("/api/config/access", headers={"X-Forwarded-For": "127.0.0.1"}).status_code
            == 403
        )


def test_access_metadata_is_unavailable_without_the_local_manager():
    with TestClient(create_app()) as client:
        assert client.get("/api/config/access").status_code == 404


def test_access_save_failure_retains_the_previous_password(tmp_path, monkeypatch):
    import os

    with local_client(tmp_path) as client:
        protect(client)
        monkeypatch.setattr(os, "replace", lambda *args: (_ for _ in ()).throw(OSError("private")))
        response = client.put(
            "/api/config/access",
            json={
                "revision": client.get("/api/config/access").json()["revision"],
                "enabled": False,
                "current_password": "private-config-password",
            },
        )
        assert response.status_code == 503
        assert "private" not in response.text
    with local_client(tmp_path) as restarted:
        assert restarted.get("/api/config/access").json()["password_required"] is True
        assert (
            restarted.post(
                "/api/config/session", json={"password": "private-config-password"}
            ).status_code
            == 200
        )
