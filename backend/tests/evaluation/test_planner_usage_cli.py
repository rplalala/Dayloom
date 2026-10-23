"""Development usage CLI with simulated provider HTTP and literal price examples."""

import asyncio
import hashlib
import json
from datetime import date
from types import SimpleNamespace

import httpx
import pytest

from backend.app.observability.usage import install_http_hooks, observe_sdk
from backend.app.runtime.cache import RequestCache
from backend.app.schemas.itinerary import Itinerary, ItineraryDay
from backend.app.schemas.planning import PlanningResult

REFERENCE = SimpleNamespace(today=lambda: date(2026, 10, 8))


def result(version, request):
    return PlanningResult(
        system_version=version,
        requirements=request.trip_requirements(),
        itinerary=Itinerary(
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            days=[ItineraryDay(date=request.start_date, activities=[])],
        ),
    )


def test_cli_saves_usage_prices_and_estimate_without_double_charging(tmp_path):
    from backend.evaluation.tools.planner_usage_cli import main

    original = {
        "input_version": "planning_request_2",
        "destination": "Sydney, Australia",
        "start_date": "2026-10-14",
        "end_date": "2026-10-17",
        "traveler_count": 2,
        "budget": {"amount": "1600", "currency": "AUD"},
        "additional_preferences": "Relaxed trip.",
    }
    input_path = tmp_path / "original.json"
    input_path.write_text(json.dumps(original), encoding="utf-8")
    output = tmp_path / "capture"
    sent = []

    class ProviderRuntime:
        async def run(self, version, request, *, reference_date, tracer=None):
            def response(wire):
                sent.append(wire)
                return httpx.Response(
                    200,
                    json={
                        "usage": {
                            "input_tokens": 1000,
                            "output_tokens": 200,
                            "input_tokens_details": {
                                "cached_tokens": 400,
                                "cache_write_tokens": 300,
                            },
                        },
                        "output": [{"type": "web_search_call"}, {"type": "web_search_call"}],
                    },
                )

            async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
                install_http_hooks(client, "azure_foundry", "official_search")

                async def search(**kwargs):
                    return (await client.post("https://fixture.invalid/responses", json={})).json()

                await observe_sdk(
                    search,
                    usage_provider="azure_foundry",
                    usage_operation="official_search",
                    model="gpt-6-luna",
                    tools=[{"type": "web_search"}],
                )
            async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
                install_http_hooks(client)
                cache = RequestCache()

                async def places():
                    return await client.post(
                        "https://places.googleapis.com/v1/places:searchText",
                        headers={"X-Goog-FieldMask": "places.id,places.displayName"},
                        json={"textQuery": "PRIVATE", "key": "SECRET"},
                    )

                await cache.get_or_create(("search",), places)
                await cache.get_or_create(("search",), places)
                await client.post(
                    "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
                    json={"origins": [1, 2], "destinations": [3, 4, 5], "travelMode": "WALK"},
                )
            return result(version, request)

    assert (
        main(
            [
                "--version",
                "v1",
                "--input-json",
                str(input_path),
                "--output-directory",
                str(output),
                "--group-id",
                "g",
                "--run-id",
                "r",
                "--execute",
                "--env-file",
                str(tmp_path / ".env"),
            ],
            runtime=ProviderRuntime(),
            date_provider=REFERENCE,
        )
        == 0
    )
    usage = json.loads((output / "usage.json").read_text())
    report = json.loads((output / "cost-report.json").read_text())
    assert len(sent) == 3
    assert len(usage["model_calls"]) == 1
    assert len(usage["cache_events"]) == 1
    assert usage["coverage"]["adapter_coverage"] == "unverified"
    assert (
        usage["result_sha256"] == hashlib.sha256((output / "result.json").read_bytes()).hexdigest()
    )
    assert (output / "input.json").read_bytes() == input_path.read_bytes()
    assert report["runs"][0]["estimated_observed_subtotal"] == "0.0821715"
    assert (
        report["runs"][0]["estimated_total"] is None
    )  # Injected coverage is not asserted complete.
    assert "SECRET" not in (output / "usage.json").read_text()


def arguments(tmp_path, *, execute=True):
    input_path = tmp_path / "original.json"
    input_path.write_text(
        json.dumps(
            {
                "destination": "Sydney, Australia",
                "start_date": "2026-10-14",
                "end_date": "2026-10-17",
                "traveler_count": 2,
                "budget": {"amount": "1600", "currency": "AUD"},
            }
        ),
        encoding="utf-8",
    )
    return [
        "--version",
        "v2",
        "--input-json",
        str(input_path),
        "--output-directory",
        str(tmp_path / "capture"),
        "--group-id",
        "offline-fixture",
        "--run-id",
        "fixture-run",
        "--env-file",
        str(tmp_path / ".env"),
    ] + (["--execute"] if execute else [])


def test_preparation_does_not_construct_or_invoke_provider_runtime(tmp_path, monkeypatch):
    from backend.evaluation.tools import planner_usage_cli

    def forbidden(**kwargs):
        raise AssertionError("Offline preparation must not construct provider dependencies")

    monkeypatch.setattr(planner_usage_cli, "RequestPlannerRuntime", forbidden)
    monkeypatch.setattr(planner_usage_cli, "load_dotenv", forbidden)
    argv = arguments(tmp_path, execute=False)
    assert planner_usage_cli.main(argv, date_provider=REFERENCE) == 0
    manifest = json.loads((tmp_path / "capture/manifest.json").read_bytes())
    assert manifest["status"] == "prepared" and not manifest["execution_requested"]
    assert not (tmp_path / "capture/usage.json").exists()
    assert not (tmp_path / "capture/result.json").exists()
    before = (tmp_path / "capture/manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        planner_usage_cli.main(argv, date_provider=REFERENCE)
    assert (tmp_path / "capture/manifest.json").read_bytes() == before


def test_failed_execution_keeps_observed_usage_without_fabricating_result(tmp_path):
    from backend.evaluation.tools.planner_usage_cli import main

    class FailedRuntime:
        async def run(self, version, request, **kwargs):
            async def embedding(**kwargs):
                return {"usage": {"input_tokens": 1000, "total_tokens": 1000}}

            await observe_sdk(
                embedding,
                usage_provider="openai",
                usage_operation="embedding",
                model="text-embedding-3-small",
            )
            raise RuntimeError("PRIVATE credential failure")

    assert main(arguments(tmp_path), runtime=FailedRuntime(), date_provider=REFERENCE) == 1
    output = tmp_path / "capture"
    usage = json.loads((output / "usage.json").read_bytes())
    report = json.loads((output / "cost-report.json").read_bytes())
    assert usage["outcome"] == "failed"
    assert usage["result_sha256"] is None
    assert report["runs"][0]["estimated_observed_subtotal"] == "0.00002"
    assert not (output / "provenance.json").exists()
    assert not (output / "result.json").exists()
    assert "PRIVATE" not in "".join(p.read_text() for p in output.iterdir())


def test_native_failure_retains_requirement_code_stage_and_path(tmp_path):
    from backend.app.schemas.requirement_boundary import RequirementBoundaryError
    from backend.evaluation.tools.planner_usage_cli import main

    class FailedRuntime:
        async def run(self, *args, **kwargs):
            raise RequirementBoundaryError(
                "invalid_source_span",
                stage="wire_mapping",
                errors=(
                    {
                        "loc": ("semantic_requirements", 0, "source_refs", 0),
                        "type": "invalid_source_span",
                    },
                ),
            )

    assert main(arguments(tmp_path), runtime=FailedRuntime(), date_provider=REFERENCE) == 1
    failure = json.loads((tmp_path / "capture/failure.json").read_bytes())
    assert failure["detail"]["code"] == "invalid_source_span"
    assert failure["detail"]["stage"] == "wire_mapping"
    assert failure["detail"]["errors"][0]["loc"] == ["semantic_requirements", 0, "source_refs", 0]


def test_result_from_different_input_is_not_bound_to_this_request(tmp_path):
    from backend.evaluation.tools.planner_usage_cli import main

    class WrongInputRuntime:
        async def run(self, version, request, **kwargs):
            value = result(version, request)
            value.requirements.destination = "Kyoto, Japan"
            return value

    assert main(arguments(tmp_path), runtime=WrongInputRuntime(), date_provider=REFERENCE) == 1
    output = tmp_path / "capture"
    assert not (output / "result.json").exists()
    assert not (output / "provenance.json").exists()
    usage = json.loads((output / "usage.json").read_bytes())
    assert usage["result_sha256"] is None
    assert usage["outcome"] == "failed"


def test_text_search_ids_only_uses_free_sku_without_assuming_account_quota(tmp_path):
    from backend.evaluation.tools.planner_usage_cli import main

    class IdsRuntime:
        async def run(self, version, request, **kwargs):
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(lambda wire: httpx.Response(200, json={"places": []}))
            ) as client:
                install_http_hooks(client)
                await client.post(
                    "https://places.googleapis.com/v1/places:searchText",
                    headers={"X-Goog-FieldMask": "places.id,nextPageToken"},
                    json={"textQuery": "PRIVATE"},
                )
            return result(version, request)

    assert main(arguments(tmp_path), runtime=IdsRuntime(), date_provider=REFERENCE) == 0
    report = json.loads((tmp_path / "capture/cost-report.json").read_bytes())
    assert report["runs"][0]["estimated_observed_subtotal"] == "0"
    assert report["runs"][0]["events"][0]["pricing"]["sku_reference"] == "Text Search IDs Only"


@pytest.mark.parametrize(
    "model,tokens,expected",
    [
        ("gpt-6-luna", {"input_tokens": 272000, "output_tokens": 100}, "0.03405"),
        ("gpt-6-luna", {"input_tokens": 272001, "output_tokens": 100}, "0.06807525"),
        ("text-embedding-3-small", {"input_tokens": 1000, "total_tokens": 1000}, "0.00002"),
        ("unknown-deployment", {"input_tokens": 1000, "output_tokens": 100}, None),
        ("gpt-6-luna", None, None),
    ],
)
def test_cli_prices_only_known_observed_model_units(tmp_path, model, tokens, expected):
    from backend.evaluation.tools.planner_usage_cli import main

    class ModelRuntime:
        async def run(self, version, request, **kwargs):
            async def sdk(**kwargs):
                return {"usage": tokens}

            await observe_sdk(
                sdk,
                usage_provider="openai",
                usage_operation="embedding" if "embedding" in model else "chat_model",
                model=model,
            )
            return result(version, request)

    assert main(arguments(tmp_path), runtime=ModelRuntime(), date_provider=REFERENCE) == 0
    report = json.loads((tmp_path / "capture/cost-report.json").read_bytes())
    usage = json.loads((tmp_path / "capture/usage.json").read_bytes())
    assert report["runs"][0]["estimated_observed_subtotal"] == expected
    assert report["runs"][0]["actual_total"] is None
    assert "cache_write_input_tokens" not in usage["model_calls"][0]
    if model == "gpt-6-luna" and tokens:
        assert len(report["runs"][0]["events"][0]["pricing"]["assumptions"]) == 2


def test_unknown_places_field_mask_stays_unpriced(tmp_path):
    from backend.evaluation.tools.planner_usage_cli import main

    class UnknownMaskRuntime:
        async def run(self, version, request, **kwargs):
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(lambda wire: httpx.Response(200, json={}))
            ) as client:
                install_http_hooks(client)
                await client.get(
                    "https://places.googleapis.com/v1/places/fixture",
                    headers={"X-Goog-FieldMask": "*"},
                )
            return result(version, request)

    assert main(arguments(tmp_path), runtime=UnknownMaskRuntime(), date_provider=REFERENCE) == 0
    report = json.loads((tmp_path / "capture/cost-report.json").read_bytes())
    assert report["runs"][0]["estimated_observed_subtotal"] is None
    assert report["runs"][0]["events"][0]["missing_reason"] == "missing_price_or_billing_context"


def test_cancelled_execution_still_emits_cost_report_for_observed_attempts(tmp_path):
    from backend.evaluation.tools.planner_usage_cli import main

    class CancelledRuntime:
        async def run(self, version, request, **kwargs):
            async def embedding(**kwargs):
                return {"usage": {"input_tokens": 1000, "total_tokens": 1000}}

            await observe_sdk(
                embedding,
                usage_provider="openai",
                usage_operation="embedding",
                model="text-embedding-3-small",
            )
            raise asyncio.CancelledError()

    assert main(arguments(tmp_path), runtime=CancelledRuntime(), date_provider=REFERENCE) == 1
    output = tmp_path / "capture"
    assert json.loads((output / "usage.json").read_bytes())["outcome"] == "cancelled"
    report = json.loads((output / "cost-report.json").read_bytes())
    assert report["runs"][0]["estimated_observed_subtotal"] == "0.00002"
    assert not (output / "result.json").exists()


@pytest.mark.parametrize("existing_key", [None, "fixture-existing-key"])
def test_cli_loads_declared_base_and_rag_environment_only_for_execution(
    tmp_path, monkeypatch, existing_key
):
    import os

    from backend.evaluation.tools.planner_usage_cli import main

    base = tmp_path / ".env"
    base.write_text("OPENAI_API_KEY=fixture-base-key\n", encoding="utf-8")
    rag = tmp_path / "rag.env"
    rag.write_text("DAYLOOM_DB_TEST_MARKER=fixture-db\n", encoding="utf-8")
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DAYLOOM_DB_TEST_MARKER", raising=False)
    if existing_key:
        monkeypatch.setenv("OPENAI_API_KEY", existing_key)

    class EnvironmentRuntime:
        async def run(self, version, request, **kwargs):
            assert os.environ["OPENAI_API_KEY"] == (existing_key or "fixture-base-key")
            assert os.environ["DAYLOOM_DB_TEST_MARKER"] == "fixture-db"
            return result(version, request)

    argv = arguments(tmp_path) + ["--env-file", str(base), "--rag-env-file", str(rag)]
    assert main(argv, runtime=EnvironmentRuntime(), date_provider=REFERENCE) == 0
    output = tmp_path / "capture"
    assert "fixture-base-key" not in "".join(p.read_text() for p in output.iterdir())
