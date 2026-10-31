"""The admin API checks a frozen saved configuration using only mocked provider HTTP."""

import json

import httpx
import pytest

from backend.app.product.api_checks import ApiChecker
from backend.tests.product.test_api_checks import successful_provider
from backend.tests.product.test_configuration import connect_manager


@pytest.fixture
def checked_client(tmp_path, provider_values):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "".join(f"{key}={value}\n" for key, value in provider_values.items()), encoding="utf-8"
    )
    manager, client = connect_manager(tmp_path)
    requests = []

    def respond(request):
        requests.append(request)
        return successful_provider(request)

    manager.api_checker = ApiChecker(transport=httpx.MockTransport(respond))
    with client:
        yield manager, client, requests, dotenv


def test_checks_saved_configuration_without_saving_or_changing_runtime(checked_client, monkeypatch):
    manager, client, requests, dotenv = checked_client
    before = client.get("/api/config").json()
    original = dotenv.read_text("utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "different-running-private-key")
    response = client.post(
        "/api/config/check",
        json={
            "revision": before["revision"],
            "service": "all",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["revision"] == before["revision"]
    assert body["stale"] is False
    assert body["request_count"] == len(requests) == 8
    assert dotenv.read_text("utf-8") == original
    assert manager.initial["OPENAI_API_KEY"] == "synthetic-openai"
    openai_request = next(request for request in requests if request.url.host == "api.openai.com")
    assert openai_request.headers["Authorization"] == "Bearer synthetic-openai"
    assert "synthetic-" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_rejects_old_revision_before_any_external_request(checked_client):
    manager, client, requests, _ = checked_client
    old = manager.view()["revision"]
    manager.save(old, {"OPENAI_API_KEY": "saved-replacement"})
    response = client.post("/api/config/check", json={"revision": old, "service": "openai"})
    assert response.status_code == 409
    assert not requests


def test_check_requires_admin_session_and_csrf(checked_client):
    _, client, requests, _ = checked_client
    payload = {"revision": client.get("/api/config").json()["revision"], "service": "all"}
    assert (
        client.post(
            "/api/config/check", json=payload, headers={"X-CSRF-Token": "wrong"}
        ).status_code
        == 403
    )
    assert client.delete("/api/config/session").status_code == 204
    assert client.post("/api/config/check", json=payload).status_code == 401
    assert not requests


def test_deployment_defaults_are_part_of_the_checked_revision(tmp_path):
    (tmp_path / ".env").write_text("AZURE_OPENAI_API_KEY=synthetic-key\n", encoding="utf-8")
    yaml = tmp_path / "product.yaml"
    prefix = "foundry:\n  endpoint: https://example.services.ai.azure.com/openai/v1\n"
    yaml.write_text(prefix + "  deployment: first\n", encoding="utf-8")
    manager, client = connect_manager(tmp_path)
    manager.api_checker = ApiChecker(
        transport=httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(AssertionError("Stale settings must not send"))
        )
    )
    with client:
        old = client.get("/api/config").json()["revision"]
        yaml.write_text(prefix + "  deployment: second\n", encoding="utf-8")
        response = client.post("/api/config/check", json={"revision": old, "service": "foundry"})
        assert response.status_code == 409


def test_configuration_changed_during_a_check_marks_the_result_stale(checked_client):
    manager, client, requests, dotenv = checked_client

    def respond(request):
        dotenv.write_text("OPENAI_API_KEY=changed-during-check\n", encoding="utf-8")
        requests.append(request)
        return successful_provider(request)

    manager.api_checker = ApiChecker(transport=httpx.MockTransport(respond))
    old = client.get("/api/config").json()["revision"]
    response = client.post("/api/config/check", json={"revision": old, "service": "foundry"})
    assert response.status_code == 200
    assert response.json()["stale"] is True
    assert response.json()["revision"] == old
    assert "changed-during-check" not in json.dumps(response.json())


def test_new_saved_key_is_checked_while_runtime_keeps_the_old_key(checked_client, monkeypatch):
    manager, client, requests, _ = checked_client
    manager.save(manager.view()["revision"], {"OPENAI_API_KEY": "synthetic-replacement"})
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-openai")
    view = client.get("/api/config").json()
    assert view["restart_required"] is True
    response = client.post(
        "/api/config/check", json={"revision": view["revision"], "service": "openai"}
    )
    assert response.status_code == 200
    assert all(
        request.headers["Authorization"] == "Bearer synthetic-replacement" for request in requests
    )
    assert manager.initial["OPENAI_API_KEY"] == "synthetic-openai"


def test_request_cannot_supply_credentials_or_expand_the_service_list(checked_client):
    _, client, requests, _ = checked_client
    revision = client.get("/api/config").json()["revision"]
    for payload in (
        {"revision": revision, "service": "arbitrary"},
        {"revision": revision, "service": "foundry", "api_key": "private-sentinel"},
    ):
        response = client.post("/api/config/check", json=payload)
        assert response.status_code == 422
        assert "private-sentinel" not in response.text
    assert not requests


def test_simultaneous_admin_checks_return_busy_without_extra_sends(checked_client):
    import asyncio
    import threading
    from concurrent.futures import ThreadPoolExecutor

    manager, client, requests, _ = checked_client
    entered, release = threading.Event(), threading.Event()

    async def respond(request):
        requests.append(request)
        entered.set()
        while not release.is_set():
            await asyncio.sleep(0.01)
        return successful_provider(request)

    manager.api_checker = ApiChecker(transport=httpx.MockTransport(respond))
    payload = {"revision": client.get("/api/config").json()["revision"], "service": "foundry"}
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(client.post, "/api/config/check", json=payload)
        try:
            assert entered.wait(3)
            response = client.post("/api/config/check", json=payload)
            assert response.status_code == 409
            assert response.json()["detail"]["code"] == "api_check_in_progress"
        finally:
            release.set()
        assert first.result(timeout=3).status_code == 200
    assert len(requests) == 1
