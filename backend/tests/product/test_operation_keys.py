"""Operation identities are admitted only when durable recovery can address them."""

import json
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_imports import source


@pytest.mark.parametrize("key", ["a\x00b", "a\nb", "a\x7fb", " ", "", "x" * 121])
def test_copy_import_task_reject_unrecoverable_keys_before_database_mutation(client, key):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    # Observe real HTTP/database encoding failures without replacing persistence.
    with TestClient(
        create_app(), base_url="http://localhost:5120", raise_server_exceptions=False
    ) as http:
        http.cookies.update(client.cookies)
        replies = {
            "copy": http.post(
                "/api/copies",
                headers=headers,
                json={
                    "source_kind": "example",
                    "source_id": "sydney-example",
                    "operation_key": key,
                },
            ).status_code,
            "import": http.post(
                "/api/imports",
                headers=headers | {"X-Import-Key": key},
                content=json.dumps(source()),
            ).status_code,
            "task": http.post(
                "/api/planning/tasks",
                headers=headers,
                json={"operation_key": key, "request": make_product_payload()},
            ).status_code,
            "legacy": http.post(
                "/api/planning",
                headers=headers | {"Idempotency-Key": key},
                json=make_product_payload(),
            ).status_code,
            "task_lookup": http.get(
                "/api/planning/tasks", params={"operation_key": key}
            ).status_code,
        }
        assert replies == dict.fromkeys(replies, 422)
        assert http.get("/api/library").json()["total"] == 0
        assert http.get("/api/previews").json() == []
        assert http.get("/api/planning/tasks").json() == []


@pytest.mark.parametrize(
    "key", ["a", "A_1.:9-", "x" * 120, "a/b", ".", "..", "a?b", "a#b", "a%b", "a b"]
)
def test_accepted_copy_and_import_keys_recover_their_durable_identity(client, key):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    copied = client.post(
        "/api/copies",
        headers=headers,
        json={"source_kind": "example", "source_id": "sydney-example", "operation_key": key},
    )
    imported = client.post(
        "/api/imports", headers=headers | {"X-Import-Key": key}, content=json.dumps(source())
    )
    assert copied.status_code == imported.status_code == 200
    assert (
        client.get("/api/copies", params={"source_kind": "example", "operation_key": key}).json()
        == copied.json()
    )
    assert client.get("/api/imports", params={"operation_key": key}).json() == imported.json()
    if key not in (".", "..") and "/" not in key:
        assert client.get(f"/api/copies/example/{quote(key, safe='')}").json() == copied.json()
        assert client.get(f"/api/imports/{quote(key, safe='')}").json() == imported.json()
