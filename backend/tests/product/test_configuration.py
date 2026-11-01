"""Local configuration is independent of traveler accounts and never returns secrets."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from backend.app.main import create_app
from backend.app.product.configuration import DEFAULT_TEST_PASSWORD, FIELDS, LocalConfiguration
from backend.app.product.configuration_api import enable_local_configuration


def connect_manager(tmp_path, *, environment=None):
    manager = LocalConfiguration(
        tmp_path, origin="http://localhost:5173", environment=environment or {}
    )
    manager.set_access(manager.access_view()["revision"], enabled=False,
                       current_password=DEFAULT_TEST_PASSWORD, new_password="", confirmation="")
    app = create_app()
    enable_local_configuration(app, manager, ready=True)
    client = TestClient(app, base_url=manager.origin, client=("127.0.0.1", 50000))
    response = client.post(
        "/api/config/session", headers={"Origin": manager.origin}, json={}
    )
    client.headers.update({"Origin": manager.origin, "X-CSRF-Token": response.json()["csrf_token"]})
    return manager, client


def test_local_manager_unlocks_without_database_and_redacts_credentials(tmp_path):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=synthetic-private-key\n", encoding="utf-8")
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
    app = create_app()
    app.state.local_configuration = manager
    with TestClient(app, base_url=manager.origin, client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/config").status_code == 401
        response = client.post(
            "/api/config/session", headers={"Origin": manager.origin},
            json={"password": DEFAULT_TEST_PASSWORD},
        )
        assert response.status_code == 200
        assert "HttpOnly" in response.headers["set-cookie"]
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        response = client.get("/api/config")
        assert response.status_code == 200
        assert response.json()["fields"]["OPENAI_API_KEY"]["configured"] is True
        assert "synthetic-private-key" not in response.text
        assert response.headers["cache-control"] == "no-store"


def test_save_preserves_unrelated_settings_and_only_applies_after_restart(tmp_path):
    (tmp_path / ".env").write_text(
        "# Retained settings\nDAYLOOM_DB_PASSWORD='unchanged'\n"
        "OPENAI_API_KEY='old-synthetic-key'\n",
        encoding="utf-8",
    )
    manager, client = connect_manager(tmp_path)
    with client:
        before = client.get("/api/config").json()
        response = client.put(
            "/api/config",
            json={
                "revision": before["revision"],
                "changes": {"OPENAI_API_KEY": "new-synthetic-key"},
            },
        )
        assert response.status_code == 200
        assert response.json()["restart_required"] is True
        assert "new-synthetic-key" not in response.text
        assert manager.initial["OPENAI_API_KEY"] == "old-synthetic-key"
        assert "DAYLOOM_DB_PASSWORD='unchanged'" in (tmp_path / ".env").read_text("utf-8")
        restarted = LocalConfiguration(tmp_path, origin=manager.origin, environment={})
        assert restarted.initial["OPENAI_API_KEY"] == "new-synthetic-key"
        assert restarted.view()["restart_required"] is False
        assert (
            client.put(
                "/api/config",
                json={
                    "revision": before["revision"],
                    "changes": {"OPENAI_API_KEY": "stale-key"},
                },
            ).status_code
            == 409
        )


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"UNKNOWN_SETTING": "out-of-scope"}, "unsupported_setting"),
        ({"OPENAI_API_KEY": "bad\nPRODUCT_JWT_SECRET=injected"}, "invalid_setting_value"),
        (
            {"AZURE_OPENAI_ENDPOINT": "https://untrusted.example/openai/v1"},
            "invalid_foundry_endpoint",
        ),
    ],
)
def test_rejects_unsafe_or_unapproved_changes_without_disclosing_values(tmp_path, changes, code):
    _, client = connect_manager(tmp_path)
    with client:
        revision = client.get("/api/config").json()["revision"]
        response = client.put("/api/config", json={"revision": revision, "changes": changes})
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == code
        assert not (tmp_path / ".env").exists()


def test_environment_overrides_are_visible_but_not_editable(tmp_path):
    _, client = connect_manager(tmp_path, environment={"OPENAI_API_KEY": "external-private"})
    with client:
        view = client.get("/api/config").json()
        assert view["fields"]["OPENAI_API_KEY"]["locked"] is True
        response = client.put(
            "/api/config",
            json={
                "revision": view["revision"],
                "changes": {"OPENAI_API_KEY": "replacement"},
            },
        )
        assert response.status_code == 409
        assert "external-private" not in response.text


@pytest.mark.parametrize("source", ["environment", "dotenv"])
@pytest.mark.parametrize("key", [*FIELDS, "PRODUCT_UNSPLASH_ACCESS_KEY"])
def test_managed_names_keep_existing_case_insensitive_resolution(tmp_path, source, key):
    value = (
        "https://example.services.ai.azure.com/openai/v1"
        if key == "AZURE_OPENAI_ENDPOINT" else "synthetic-case-value"
    )
    supplied = {key.lower(): value}
    if source == "dotenv":
        (tmp_path / ".env").write_text(f"{key.lower()}={value}\n", encoding="utf-8")
    manager, client = connect_manager(
        tmp_path, environment=supplied if source == "environment" else {},
    )
    canonical = "UNSPLASH_API_KEY" if key == "PRODUCT_UNSPLASH_ACCESS_KEY" else key
    with client:
        view = client.get("/api/config").json()
        assert manager.initial[canonical] == value
        assert view["fields"][canonical]["configured"] is True
        assert view["fields"][canonical]["locked"] is (source == "environment")
        assert manager.values_for_check(view["revision"])[canonical] == value
        if source == "environment":
            response = client.put("/api/config", json={
                "revision": view["revision"], "changes": {canonical: ""},
            })
            assert response.status_code == 409


def test_save_preserves_binding_order_case_variants_and_dependent_interpolation(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "openai_api_key=synthetic-first\nLOWER_COPY=${openai_api_key}\n"
        "OPENAI_API_KEY=synthetic-last\nUPPER_COPY=${OPENAI_API_KEY}\n"
        "# Retained comment\nUNRELATED=retained\n", encoding="utf-8",
    )
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
    manager.save(manager.view()["revision"], {"OPENAI_API_KEY": "synthetic-new"})
    assert path.read_text("utf-8") == (
        "openai_api_key='synthetic-new'\nLOWER_COPY=${openai_api_key}\n"
        "OPENAI_API_KEY='synthetic-new'\nUPPER_COPY=${OPENAI_API_KEY}\n"
        "# Retained comment\nUNRELATED=retained\n"
    )
    restarted = LocalConfiguration(tmp_path, origin=manager.origin, environment={})
    assert restarted.initial["OPENAI_API_KEY"] == "synthetic-new"
    assert restarted.read()[1]["LOWER_COPY"] == "synthetic-new"
    assert restarted.read()[1]["UPPER_COPY"] == "synthetic-new"


def test_alias_clear_replaces_mixed_case_bindings_and_keeps_interpolation_case_sensitive(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "TOKEN_SOURCE=synthetic-upper\ntoken_source=synthetic-lower\n"
        "openai_api_key=${token_source}\nGOOGLE_MAPS_API_KEY=${TOKEN_SOURCE}\n"
        "UnSplash_Api_Key=synthetic-alias\nproduct_unsplash_access_key=synthetic-primary\n",
        encoding="utf-8",
    )
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
    assert manager.initial["OPENAI_API_KEY"] == "synthetic-lower"
    assert manager.initial["GOOGLE_MAPS_API_KEY"] == "synthetic-upper"
    manager.save(manager.view()["revision"], {"UNSPLASH_API_KEY": ""})
    assert "synthetic-alias" not in path.read_text("utf-8")
    assert "synthetic-primary" not in path.read_text("utf-8")
    assert LocalConfiguration(tmp_path, origin=manager.origin, environment={}).initial[
        "UNSPLASH_API_KEY"
    ] == ""


def test_session_requires_local_host_origin_and_csrf_and_can_be_revoked(tmp_path):
    manager, client = connect_manager(tmp_path)
    with client:
        body = {"revision": client.get("/api/config").json()["revision"], "changes": {}}
        assert (
            client.put("/api/config", json=body, headers={"X-CSRF-Token": "wrong"}).status_code
            == 403
        )
        assert (
            client.put(
                "/api/config", json=body, headers={"Origin": "https://elsewhere.example"}
            ).status_code
            == 403
        )
        assert client.get("/api/config", headers={"Host": "elsewhere.example"}).status_code == 403
        assert client.delete("/api/config/session").status_code == 204
        assert client.get("/api/config").status_code == 401
    remote = TestClient(client.app, base_url=manager.origin, client=("192.0.2.5", 50000))
    assert (
        remote.post(
            "/api/config/session", headers={"Origin": manager.origin}, json={}
        ).status_code
        == 403
    )


def test_readiness_does_not_call_providers_or_claim_credentials_are_verified(tmp_path):
    manager, client = connect_manager(tmp_path)
    manager.resource_probe = lambda: [{"id": "database", "ready": False}]
    with client:
        response = client.get("/api/config/readiness")
        assert response.status_code == 200
        assert response.json()["ready"] is False
        assert response.json()["credentials_verified"] is False
        assert response.json()["resources"] == [{"id": "database", "ready": False}]


def test_setup_mode_serves_configuration_but_blocks_business_operations(tmp_path):
    from backend.app.product.application import create_product_application

    (tmp_path / "index.html").write_text("Dayloom shell", encoding="utf-8")
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
    app = create_product_application(tmp_path)
    enable_local_configuration(app, manager, ready=False)
    with TestClient(app, base_url=manager.origin, client=("127.0.0.1", 50000)) as client:
        assert client.get("/", follow_redirects=False).headers["location"] == "/config"
        assert client.get("/config").text == "Dayloom shell"
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post("/api/planning/tasks", json={})
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "local_setup_required"
        assert client.get("/api/config").status_code == 401
        assert client.get("/api/config").headers["cache-control"] == "no-store"


def test_configuration_payload_is_bounded_before_validation(tmp_path):
    _, client = connect_manager(tmp_path)
    with client:
        response = client.put("/api/config", content=b"x" * 40000)
        assert response.status_code == 413
        assert "x" * 100 not in response.text


def test_unsplash_alias_can_be_cleared_and_quoted_keys_round_trip(tmp_path):
    (tmp_path / ".env").write_text("PRODUCT_UNSPLASH_ACCESS_KEY=legacy-private\n", encoding="utf-8")
    _, client = connect_manager(tmp_path)
    with client:
        before = client.get("/api/config").json()
        assert before["fields"]["UNSPLASH_API_KEY"]["configured"] is True
        result = client.put(
            "/api/config",
            json={
                "revision": before["revision"],
                "changes": {
                    "UNSPLASH_API_KEY": "",
                    "OPENAI_API_KEY": "synthetic'key\\suffix",
                },
            },
        )
        assert result.status_code == 200
        restarted = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
        assert restarted.initial["UNSPLASH_API_KEY"] == ""
        assert restarted.initial["OPENAI_API_KEY"] == "synthetic'key\\suffix"


def test_failed_atomic_save_leaves_original_configuration_intact(tmp_path, monkeypatch):
    import os

    path = tmp_path / ".env"
    path.write_text("OPENAI_API_KEY=retained-private\n", encoding="utf-8")
    _, client = connect_manager(tmp_path)
    with client:
        revision = client.get("/api/config").json()["revision"]
        monkeypatch.setattr(os, "replace", lambda *args: (_ for _ in ()).throw(OSError("private")))
        response = client.put(
            "/api/config",
            json={
                "revision": revision,
                "changes": {"OPENAI_API_KEY": "replacement-private"},
            },
        )
        assert response.status_code == 503
        assert "private" not in response.text
        assert path.read_text("utf-8") == "OPENAI_API_KEY=retained-private\n"


def test_invalid_config_request_never_echoes_supplied_secrets(tmp_path):
    _, client = connect_manager(tmp_path)
    with client:
        response = client.put("/api/config", json={"revision": "secret-sentinel", "changes": {}})
        assert response.status_code == 422
        assert "secret-sentinel" not in response.text
        assert response.headers["cache-control"] == "no-store"


def test_unchanged_application_does_not_expose_configuration_management():
    with TestClient(create_app()) as client:
        assert client.get("/api/config").status_code == 404


def test_expired_management_session_is_rejected(tmp_path, monkeypatch):
    from backend.app.product import configuration

    _, client = connect_manager(tmp_path)
    with client:
        monkeypatch.setattr(configuration, "monotonic", lambda: 10**20)
        assert client.get("/api/config/session").status_code == 401
        assert client.get("/api/config").status_code == 401


def test_external_unsplash_alias_precedes_dotenv_canonical_key(tmp_path):
    (tmp_path / ".env").write_text("UNSPLASH_API_KEY=dotenv-private\n", encoding="utf-8")
    manager = LocalConfiguration(
        tmp_path,
        origin="http://localhost:5173",
        environment={"PRODUCT_UNSPLASH_ACCESS_KEY": "external-private"},
    )
    assert manager.initial["UNSPLASH_API_KEY"] == "external-private"
    assert manager.view()["fields"]["UNSPLASH_API_KEY"]["locked"] is True


def test_dotenv_interpolation_preserves_external_environment_precedence(tmp_path):
    (tmp_path / ".env").write_text(
        "CREDENTIAL_SOURCE=dotenv-private\nOPENAI_API_KEY=${CREDENTIAL_SOURCE}\n",
        encoding="utf-8",
    )
    manager = LocalConfiguration(
        tmp_path,
        origin="http://localhost:5173",
        environment={"CREDENTIAL_SOURCE": "external-private"},
    )
    assert manager.initial["OPENAI_API_KEY"] == "external-private"


def test_empty_yaml_retains_environment_only_configuration_support(tmp_path):
    (tmp_path / "product.yaml").write_text("", encoding="utf-8")
    manager = LocalConfiguration(
        tmp_path,
        origin="http://localhost:5173",
        environment={"AZURE_OPENAI_DEPLOYMENT": "gpt-6-luna"},
    )
    assert manager.view()["fields"]["AZURE_OPENAI_DEPLOYMENT"]["value"] == "gpt-6-luna"


def test_unassigned_dotenv_bindings_allow_existing_defaults_and_aliases(tmp_path):
    (tmp_path / "product.yaml").write_text(
        "foundry:\n  endpoint: https://example.services.ai.azure.com/openai/v1\n"
        "  deployment: gpt-6-luna\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "AZURE_OPENAI_ENDPOINT\nUNSPLASH_API_KEY\nPRODUCT_UNSPLASH_ACCESS_KEY=synthetic-legacy\n",
        encoding="utf-8",
    )
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
    assert manager.initial["AZURE_OPENAI_ENDPOINT"] == (
        "https://example.services.ai.azure.com/openai/v1"
    )
    assert manager.initial["UNSPLASH_API_KEY"] == "synthetic-legacy"


def test_concurrent_file_replacement_cannot_tag_old_fields_with_new_revision(tmp_path, monkeypatch):
    from pathlib import Path

    path = tmp_path / ".env"
    path.write_text("AZURE_OPENAI_DEPLOYMENT=original\n", encoding="utf-8")
    _, client = connect_manager(tmp_path)
    with client:
        original = client.get("/api/config").json()
        read_text = Path.read_text
        replaced = False

        def replace_after_read(source, *args, **kwargs):
            nonlocal replaced
            text = read_text(source, *args, **kwargs)
            if source == path and not replaced:
                replaced = True
                path.write_text("AZURE_OPENAI_DEPLOYMENT=concurrent\n", encoding="utf-8")
            return text

        monkeypatch.setattr(Path, "read_text", replace_after_read)
        response = client.get("/api/config").json()
        assert response["fields"]["AZURE_OPENAI_DEPLOYMENT"]["value"] == "original"
        assert response["revision"] == original["revision"]
        assert (
            client.put(
                "/api/config",
                json={
                    "revision": response["revision"],
                    "changes": {
                        "AZURE_OPENAI_DEPLOYMENT": "stale-edit",
                    },
                },
            ).status_code
            == 409
        )


def test_database_and_custom_signing_key_can_be_saved_without_exposing_secrets(
    tmp_path, monkeypatch,
):
    from psycopg.conninfo import conninfo_to_dict

    from backend.app.runtime.database import DatabaseSettings

    for key in ("URL", "HOST", "PORT", "NAME", "USER", "PASSWORD"):
        monkeypatch.delenv("DAYLOOM_DB_" + key, raising=False)
    manager, client = connect_manager(tmp_path)
    fields = {
        "DAYLOOM_DB_HOST": "localhost", "DAYLOOM_DB_PORT": "55620",
        "DAYLOOM_DB_NAME": "configuration_test", "DAYLOOM_DB_USER": "reader",
        "DAYLOOM_DB_PASSWORD": "synthetic-db-secret",
        "PRODUCT_JWT_SECRET": "synthetic-custom-signing-key-at-least-32-characters",
    }
    response = client.put("/api/config", json={
        "revision": manager.view()["revision"], "changes": fields,
    })
    assert response.status_code == 200
    assert response.json()["restart_required"] is True
    assert fields["DAYLOOM_DB_PASSWORD"] not in response.text
    assert fields["PRODUCT_JWT_SECRET"] not in response.text
    settings = DatabaseSettings(_env_file=tmp_path / ".env")
    connection = conninfo_to_dict(settings.connection_string.get_secret_value())
    assert connection["dbname"] == "configuration_test"
    assert connection["port"] == "55620"
    assert SecretStr(connection["password"]) == SecretStr("synthetic-db-secret")
    assert LocalConfiguration(tmp_path, origin=manager.origin, environment={}).initial[
        "PRODUCT_JWT_SECRET"
    ] == fields["PRODUCT_JWT_SECRET"]


@pytest.mark.parametrize("changes", [
    {"DAYLOOM_DB_PORT": "65536"}, {"DAYLOOM_DB_PORT": "invalid"},
    {"DAYLOOM_DB_NAME": ""}, {"DAYLOOM_DB_URL": "postgresql://[invalid"},
    {"PRODUCT_JWT_SECRET": "short"}, {"PRODUCT_JWT_SECRET": ""},
])
def test_invalid_database_or_signing_configuration_does_not_write_files(tmp_path, changes):
    manager, client = connect_manager(tmp_path)
    response = client.put("/api/config", json={
        "revision": manager.view()["revision"], "changes": changes,
    })
    assert response.status_code == 400
    assert not (tmp_path / ".env").exists()


def test_generate_signing_key_respects_revision_and_environment_lock(tmp_path):
    from dotenv import dotenv_values
    manager, client = connect_manager(tmp_path)
    revision = manager.view()["revision"]
    response = client.post("/api/config/signing-key", json={"revision": revision})
    assert response.status_code == 200
    saved = dotenv_values(tmp_path / ".env")["PRODUCT_JWT_SECRET"]
    assert len(saved) >= 32
    assert saved not in response.text
    assert response.json()["fields"]["PRODUCT_JWT_SECRET"]["configured"] is True
    assert response.json()["restart_required"] is True
    assert client.post("/api/config/signing-key", json={"revision": revision}).status_code == 409
    assert dotenv_values(tmp_path / ".env")["PRODUCT_JWT_SECRET"] == saved
    locked_dir = tmp_path / "locked"
    locked_dir.mkdir()
    locked, locked_client = connect_manager(locked_dir, environment={"PRODUCT_JWT_SECRET": saved})
    assert locked_client.post("/api/config/signing-key", json={
        "revision": locked.view()["revision"],
    }).status_code == 409
    assert not (locked_dir / ".env").exists()
