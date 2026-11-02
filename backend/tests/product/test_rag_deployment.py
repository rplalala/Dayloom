"""Instance RAG policy preserves keys but removes retrieval prerequisites and sends."""

import asyncio
import os
from unittest.mock import patch

import httpx
import pytest

from backend.app.product.api_checks import ApiChecker
from backend.app.product.configuration import LocalConfiguration
from backend.app.runtime.deployment import ProductOptions, ProductPolicySettings
from backend.tests.product.test_accounts import client  # noqa: F401


def test_api_startup_pins_rag_before_the_first_request_and_restart_applies_changes(
    tmp_path, monkeypatch,
):
    from contextlib import asynccontextmanager
    from datetime import date

    from fastapi.testclient import TestClient
    from starlette.requests import Request

    from backend.app.api import dependencies
    from backend.app.main import create_app
    from backend.app.services import planner_runtime
    from backend.app.services.planning import PlanningFailedError
    from backend.tests.request_fixtures import make_request

    deployment = tmp_path / "product.yaml"
    deployment.write_text("rag_enabled: false\n", encoding="utf-8")
    monkeypatch.setenv("DAYLOOM_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("PRODUCT_RAG_ENABLED", raising=False)
    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path / "logs"))
    calls = []

    @asynccontextmanager
    async def providers(*args):
        yield planner_runtime.PlannerDependencies(llm=object())

    async def observe_policy(*args, **kwargs):
        calls.append(kwargs["rag_enabled"])
        raise RuntimeError("Stop before provider execution")

    monkeypatch.setattr(dependencies, "create_product_planner_dependencies", providers)
    monkeypatch.setattr(planner_runtime, "run_v3", observe_policy)
    for index in range(2):
        with TestClient(create_app()) as session:
            if index == 0:
                deployment.write_text("rag_enabled: true\n", encoding="utf-8")
            request = Request({"type": "http", "app": session.app})
            service = dependencies.get_planning_service(request)
            with pytest.raises(PlanningFailedError):
                asyncio.run(service.plan(make_request(), reference_date=date(2026, 9, 11)))
    assert calls == [False, True]


def test_app_only_database_passes_disabled_readiness(client, monkeypatch, provider_values):  # noqa: F811
    from backend.app.product.local_readiness import check_local_resources
    from backend.app.tripworld.retrieval import query_tokens, runtime
    from scripts.run_product import check_runtime

    for key, value in provider_values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("PRODUCT_RAG_ENABLED", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    def forbidden(*args, **kwargs):
        pytest.fail("App-only readiness attempted retrieval initialization")

    monkeypatch.setattr(query_tokens, "tokenizer", forbidden)
    monkeypatch.setattr(runtime, "RuntimeRetrieval", forbidden)
    check_runtime()
    resources = check_local_resources(remote_database=True, rag_enabled=False)
    assert all(row["ready"] or row.get("status") == "skipped" for row in resources)
    assert {row["id"] for row in resources if row.get("status") == "skipped"} == {
        "tripworld", "embedding_tokenizer",
    }


def test_disabled_startup_skips_retrieval_prerequisites_but_keeps_app_checks(
    tmp_path, monkeypatch, provider_values,
):
    from contextlib import contextmanager

    import psycopg

    from backend.app.product.local_readiness import check_local_resources
    from backend.app.tripworld.retrieval import query_tokens, runtime
    from scripts.run_product import check_runtime

    (tmp_path / "product.yaml").write_text(
        "rag_enabled: false\nfoundry:\n  endpoint: https://example.services.ai.azure.com/openai/v1\n"
        "  deployment: gpt-6-luna\n", encoding="utf-8",
    )
    queries = []

    class Connection:
        def execute(self, query):
            queries.append(query)

    @contextmanager
    def connect(*args, **kwargs):
        yield Connection()

    def forbidden(*args, **kwargs):
        pytest.fail("Disabled startup attempted retrieval initialization")

    monkeypatch.setattr(psycopg, "connect", connect)
    monkeypatch.setattr(query_tokens, "tokenizer", forbidden)
    monkeypatch.setattr(runtime, "RuntimeRetrieval", forbidden)
    environment = {**provider_values, "DAYLOOM_CONFIG_DIR": str(tmp_path), "OPENAI_API_KEY": "",
                   "DAYLOOM_DB_URL": "postgresql://test:test@localhost/dayloom_rag_test",
                   "PRODUCT_JWT_SECRET": "test-signing-key-with-at-least-32-characters"}
    with patch.dict(os.environ, environment, clear=True):
        check_runtime()
        results = check_local_resources(rag_enabled=False)
    assert {row["id"] for row in results if row.get("status") == "skipped"} == {
        "tripworld", "embedding_tokenizer",
    }
    assert all(row["ready"] for row in results if row.get("status") != "skipped")
    assert queries and all("app.schema_migrations" in q or q == "SELECT 1" for q in queries)


def test_disabled_rag_rejects_legacy_openai_evidence_instead_of_switching_provider():
    from backend.app.runtime.deployment import check_rag_provider

    check_rag_provider(True, "openai")
    check_rag_provider(False, "azure_foundry")
    with pytest.raises(ValueError, match="Foundry evidence provider"):
        check_rag_provider(False, "openai")


def test_disabled_runtime_rejects_openai_evidence_before_creating_provider_clients():
    from contextlib import asynccontextmanager
    from datetime import date

    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.schemas.planning import SystemVersion
    from backend.app.services.planner_runtime import RequestPlannerRuntime
    from backend.tests.request_fixtures import make_request

    @asynccontextmanager
    async def forbidden(*args):
        pytest.fail("Invalid deployment constructed provider clients")
        yield  # pragma: no cover

    base = load_runtime_config()
    config = base.model_copy(update={
        "web_evidence": base.web_evidence.model_copy(update={"provider": "openai"}),
    })
    runtime = RequestPlannerRuntime(config=config, dependency_factory=forbidden, rag_enabled=False)
    with pytest.raises(ValueError, match="Foundry evidence provider"):
        asyncio.run(runtime.run(SystemVersion.V3, make_request(), reference_date=date(2026, 9, 11)))


def test_default_and_instance_overrides_are_explicit_and_restart_bound(tmp_path):
    assert ProductOptions().rag_enabled is True
    (tmp_path / "product.yaml").write_text("rag_enabled: false\n", encoding="utf-8")
    with patch.dict(os.environ, {"DAYLOOM_CONFIG_DIR": str(tmp_path)}, clear=True):
        assert ProductPolicySettings().rag_enabled is False
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
    assert manager.view()["rag_enabled"] is False
    assert manager.view()["restart_required"] is False
    (tmp_path / "product.yaml").write_text("rag_enabled: true\n", encoding="utf-8")
    assert manager.view()["rag_enabled"] is False
    assert manager.view()["restart_required"] is True
    override = LocalConfiguration(tmp_path, origin="http://localhost:5173",
                                  environment={"PRODUCT_RAG_ENABLED": "false"})
    assert override.view()["rag_enabled"] is False
    assert override.view()["restart_required"] is False


def test_disabled_rag_does_not_require_or_delete_an_openai_key(tmp_path):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=retained-private-key\n", encoding="utf-8")
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173",
                                 environment={"PRODUCT_RAG_ENABLED": "false"})
    manager.resource_probe = lambda: [{"id": "tripworld", "ready": False, "status": "skipped"}]
    assert "OPENAI_API_KEY" not in manager.readiness()["missing"]
    assert manager.initial["OPENAI_API_KEY"] == "retained-private-key"
    manager.save(manager.view()["revision"], {"OPENAI_API_KEY": ""})
    assert "OPENAI_API_KEY" not in manager.readiness()["missing"]


def test_disabled_openai_diagnostic_never_sends_even_with_a_saved_key():
    def forbidden(_):
        pytest.fail("Disabled RAG must not send an OpenAI probe")

    checker = ApiChecker(transport=httpx.MockTransport(forbidden), embedding_enabled=False)
    result = asyncio.run(checker.check("openai", {"OPENAI_API_KEY": "saved-key"}))
    assert result["request_count"] == 0
    assert result["results"][0]["status"] == "disabled"
