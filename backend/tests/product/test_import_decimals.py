"""JSON numeric admission through the actual import API and isolated PostgreSQL."""

# Imported pytest fixtures retain their public names.
# ruff: noqa: F811

import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_imports import source


@pytest.mark.parametrize("token", ["1e99999999999999999999", "1e-99999999999999999999"])
def test_unrepresentable_json_numeric_token_is_located_and_creates_no_import_receipt(client, token):
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "unrepresentable-token",
    }
    wrapper = {"itinerary": source(), "request": {"budget": {"amount": "TOKEN", "currency": "AUD"}}}
    content = json.dumps(wrapper).replace('"TOKEN"', token)
    # Observe the real safe HTTP boundary even if an unhandled server exception occurs.
    with TestClient(
        create_app(), base_url="http://localhost:5120", raise_server_exceptions=False
    ) as application:
        application.cookies.update(client.cookies)
        response = application.post("/api/imports", headers=headers, content=content)
        observation = {
            "status": response.status_code,
            "operation_status": application.get("/api/imports/unrepresentable-token").status_code,
            "pending_previews": len(application.get("/api/previews").json()),
        }
    assert observation == {"status": 422, "operation_status": 404, "pending_previews": 0}
    assert response.json()["detail"] == {
        "code": "invalid_import",
        "path": "$",
        "message": "Invalid JSON",
    }


@pytest.mark.parametrize("numeric", [False, True])
@pytest.mark.parametrize(
    "amount", ["1e100000", "1e-100000", "123456789012345678901234567890.1234567890123456789"]
)
def test_representable_original_budget_strings_and_numeric_tokens_remain_exact_through_save(
    client, amount, numeric
):
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "exact-request-budget",
    }
    wrapper = {"itinerary": source(), "request": {"budget": {"amount": amount, "currency": "AUD"}}}
    content = json.dumps(wrapper)
    if numeric:
        content = content.replace(json.dumps(amount), amount)
    imported = client.post("/api/imports", headers=headers, content=content)
    assert imported.status_code == 200, imported.text
    preview = imported.json()
    assert Decimal(preview["snapshot"]["request"]["budget"]["amount"]) == Decimal(amount)
    saved = client.post(f"/api/previews/{preview['id']}/save", headers=headers, json={})
    assert saved.status_code == 200, saved.text
    detail = client.get(f"/api/trips/{saved.json()['saved_trip_id']}").json()
    assert Decimal(detail["request"]["budget"]["amount"]) == Decimal(amount)
    assert detail["request"]["known_fields"] == ["budget"]
    replay = client.post("/api/imports", headers=headers, content=content)
    assert replay.status_code == 200
    assert replay.json()["saved_trip_id"] == saved.json()["saved_trip_id"]
