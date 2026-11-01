"""Unsplash uses one saved key while reading historical settings compatibly."""

import pytest
from dotenv import dotenv_values
from pydantic import SecretStr

from backend.app.product.configuration import LocalConfiguration
from backend.app.product.media import MediaSettings
from backend.tests.product.test_configuration import connect_manager


@pytest.fixture(autouse=True)
def isolated_unsplash_environment(monkeypatch):
    for key in ("UNSPLASH_API_KEY", "PRODUCT_UNSPLASH_ACCESS_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_save_and_clear_use_one_key_and_preserve_other_settings(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "# Retained settings\nDAYLOOM_DB_VOLUME=retained_test_volume\n"
        "PRODUCT_JWT_SECRET=synthetic-signing-key-at-least-32-characters\n"
        "product_unsplash_access_key=synthetic-old\n"
        "DEPENDENT=${product_unsplash_access_key}\nUNSPLASH_API_KEY=synthetic-current\n",
        encoding="utf-8",
    )
    manager, client = connect_manager(tmp_path)
    view = client.get("/api/config").json()
    assert "UNSPLASH_API_KEY" in view["fields"]
    assert "PRODUCT_UNSPLASH_ACCESS_KEY" not in view["fields"]
    response = client.put("/api/config", json={
        "revision": view["revision"], "changes": {"UNSPLASH_API_KEY": "synthetic-new"},
    })
    assert response.status_code == 200
    assert "synthetic-new" not in response.text
    saved = dotenv_values(path)
    assert "product_unsplash_access_key" not in saved
    assert SecretStr(saved["UNSPLASH_API_KEY"]) == SecretStr("synthetic-new")
    assert saved["DEPENDENT"] == "synthetic-old"
    assert saved["DAYLOOM_DB_VOLUME"] == "retained_test_volume"
    assert saved["PRODUCT_JWT_SECRET"] == "synthetic-signing-key-at-least-32-characters"
    restarted = LocalConfiguration(tmp_path, origin=manager.origin, environment={})
    assert restarted.initial["UNSPLASH_API_KEY"] == "synthetic-new"
    cleared = client.put("/api/config", json={
        "revision": response.json()["revision"], "changes": {"UNSPLASH_API_KEY": ""},
    })
    assert cleared.status_code == 200
    assert not MediaSettings(_env_file=path).unsplash_access_key.get_secret_value()
    assert "PRODUCT_UNSPLASH_ACCESS_KEY" not in path.read_text("utf-8").upper()


@pytest.mark.parametrize("environment,local,expected", [
    ({}, {"PRODUCT_UNSPLASH_ACCESS_KEY": "synthetic-file-old"}, "synthetic-file-old"),
    ({}, {"UNSPLASH_API_KEY": "synthetic-file-new",
          "PRODUCT_UNSPLASH_ACCESS_KEY": "synthetic-file-old"}, "synthetic-file-new"),
    ({"PRODUCT_UNSPLASH_ACCESS_KEY": "synthetic-env-old"},
     {"UNSPLASH_API_KEY": "synthetic-file-new"}, "synthetic-env-old"),
    ({"UNSPLASH_API_KEY": "synthetic-env-new"},
     {"PRODUCT_UNSPLASH_ACCESS_KEY": "synthetic-file-old"}, "synthetic-env-new"),
    ({"PRODUCT_UNSPLASH_ACCESS_KEY": ""}, {"UNSPLASH_API_KEY": "synthetic-file-new"}, ""),
    ({"UNSPLASH_API_KEY": ""}, {"PRODUCT_UNSPLASH_ACCESS_KEY": "synthetic-file-old"}, ""),
    ({}, {"UNSPLASH_API_KEY": None,
          "PRODUCT_UNSPLASH_ACCESS_KEY": "synthetic-file-old"}, "synthetic-file-old"),
])
def test_console_and_media_resolve_the_same_key(
    monkeypatch, tmp_path, environment, local, expected,
):
    path = tmp_path / ".env"
    path.write_text("".join(key + ("\n" if value is None else "=" + value + "\n")
                            for key, value in local.items()), encoding="utf-8")
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    manager, client = connect_manager(tmp_path, environment=environment)
    assert SecretStr(manager.initial["UNSPLASH_API_KEY"]) == SecretStr(expected)
    assert MediaSettings(_env_file=path).unsplash_access_key == SecretStr(expected)
    view = client.get("/api/config").json()
    assert view["fields"]["UNSPLASH_API_KEY"]["locked"] is bool(environment)
    if environment:
        response = client.put("/api/config", json={
            "revision": view["revision"], "changes": {"UNSPLASH_API_KEY": "synthetic-change"},
        })
        assert response.status_code == 409
