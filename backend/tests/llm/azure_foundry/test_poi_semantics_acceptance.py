"""One-shot development CLI capture over the real V3 requirement gate and mock HTTP."""

import asyncio
import json
import logging
from datetime import date

import httpx2 as httpx
import pytest
import yaml

from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.schemas.request import PlanningRequest
from backend.app.services.preference_interpretation import interpret_preferences
from backend.app.versions.v1 import runner
from backend.app.versions.v1.config import V1Settings
from backend.tests.llm.azure_foundry.requirement_fixtures import current_response
from backend.tests.llm.azure_foundry.test_requirement_acceptance_harness import response
from backend.tests.versions.v1.test_interpreted_requirements import draft_for
from tools.validation.poi_semantics_acceptance import run_case

QUOTE = "Visit the British Museum exactly twice, on two different days"


def visit_payload(*, hard=False):
    value = draft_for(QUOTE).model_dump(mode="json")
    value["visit_requirements"] = [
        dict(
            place_text="British Museum",
            minimum_visits=2,
            exact_visits=2,
            distinct_dates=True,
            dates=[],
            status="executable",
            reason=None,
            access_mode=None,
            source_refs=[dict(quote=QUOTE, occurrence=0)],
        )
    ]
    value["time_protections"] = []
    value["named_places"] = [
        dict(
            place_text="British Museum",
            inclusion="REQUIRED",
            source_refs=[dict(quote=QUOTE, occurrence=0)],
        )
    ]
    if hard:
        value["semantic_requirements"][0].update(strength="hard", kind="goal")
    else:
        value["semantic_requirements"] = []
    return value


def setup_case(tmp_path, monkeypatch, payload=None):
    request = PlanningRequest(
        destination="London",
        start_date="2026-10-05",
        end_date="2026-10-07",
        traveler_count=1,
        budget={"amount": "900", "currency": "GBP"},
        additional_preferences=QUOTE,
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(request.model_dump_json(), encoding="utf-8")
    settings = V1Settings(
        _env_file=None,
        azure_openai_endpoint="https://fixture.invalid/openai/v1",
        azure_openai_api_key="fixture-secret",
        azure_openai_deployment="fixture-model",
        google_maps_api_key="fixture-google-secret",
    )
    sends, clients = [], []

    def handler(request):
        sends.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=response(
                json.dumps(current_response(payload or visit_payload(hard=True), request)), 1
            ),
        )

    def create(settings):
        client = AzureFoundryStructuredLLMClient(
            endpoint=str(settings.azure_openai_endpoint),
            deployment=settings.azure_openai_deployment,
            api_key=settings.azure_openai_api_key.get_secret_value(),
            http_async_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        clients.append(client)
        return client

    monkeypatch.setattr(runner, "V1Settings", lambda: settings)
    monkeypatch.setattr(runner, "create_foundry_client", create)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    return request_path, sends, clients


@pytest.mark.parametrize("version", ["v1", "v3"])
def test_http_success_then_hard_gate_failure_retains_linked_draft(tmp_path, monkeypatch, version):
    request, sends, clients = setup_case(tmp_path, monkeypatch)
    output = tmp_path / "case"
    result = run_case(
        request,
        output,
        capture_requirements=True,
        reference_date="2026-09-26",
        version=version,
    )
    assert result["application_exit_code"] == 2
    assert result["version"] == version
    assert result["capture_status"] == "complete"
    assert len(sends) == 1
    assert clients[0]._chat_model.root_async_client.is_closed()
    records = [json.loads(p.read_text()) for p in (output / "requirements").glob("*.json")]
    draft = next(r for r in records if r["validation_stage"] == "draft_validated")
    outcome = next(r for r in records if r["validation_stage"] == "canonicalization")
    assert draft["call_id"] == outcome["call_id"]
    assert draft["draft"]["visit_requirements"][0]["exact_visits"] == 2
    assert draft["draft"]["semantic_requirements"][0]["strength"] == "hard"
    assert outcome["outcome"]["code"] == "unsupported_hard_requirements"
    assert outcome["outcome"]["requirement_ids"] == ["semantic_1"]
    assert draft["prompt_sha256"] and draft["runtime_config_sha256"]
    assert not (output / "product.json").exists()


@pytest.mark.parametrize("version", ["v1", "v3"])
def test_independent_runner_wraps_linked_semantic_calls(tmp_path, monkeypatch, version):
    import tools.validation.poi_semantics_acceptance as entry

    request, sends, _ = setup_case(tmp_path, monkeypatch)
    call_ids = ("rejected", "corrected")

    def fake_main(argv):
        assert argv[argv.index("--reference-date") + 1] == "2026-09-26"
        client = runner.create_foundry_client(runner.V1Settings())
        for call_id, correction_of in zip(call_ids, (None, call_ids[0]), strict=True):
            identity = {"call_id": call_id, "correction_of": correction_of}
            client.capture_poi_semantics("input", identity | {"input": "fixture-secret"})
            client.capture_poi_semantics("output", identity | {"output": "normalized"})
            client.capture_poi_semantics("outcome", identity | {"status": "accepted"})
        asyncio.run(client.aclose())
        return 1

    monkeypatch.setattr(
        entry.runner if version == "v1" else entry,
        "main" if version == "v1" else "v3_main",
        fake_main,
    )
    output = tmp_path / "captured"
    result = run_case(
        request,
        output,
        capture_semantics=True,
        reference_date="2026-09-26",
        version=version,
    )
    assert result["application_exit_code"] == 1
    assert result["semantic_capture_status"] == "complete"
    assert not sends
    records = [json.loads(path.read_text()) for path in (output / "semantics").glob("*.json")]
    assert len(records) == 6
    assert {record["validation_stage"] for record in records} == {
        "semantic_input",
        "semantic_output",
        "semantic_outcome",
    }
    assert {record["call_id"] for record in records} == set(call_ids)
    assert {record["correction_of"] for record in records} == {None, "rejected"}
    assert "fixture-secret" not in json.dumps(records)


def test_cli_forwards_v1_and_reference_date_without_running_providers(monkeypatch, tmp_path):
    import sys

    import tools.validation.poi_semantics_acceptance as entry

    received = {}

    def fake_run_case(*args, **kwargs):
        received.update(kwargs)
        return {
            "application_exit_code": 1,
            "capture_errors": [],
            "semantic_capture_errors": [],
            "repair_capture_errors": [],
        }

    monkeypatch.setattr(entry, "run_case", fake_run_case)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "poi_semantics_acceptance",
            "--input-json",
            str(tmp_path / "input.json"),
            "--output",
            str(tmp_path / "case"),
            "--version",
            "v1",
            "--reference-date",
            "2026-09-27",
            "--capture-semantics",
            "--execute",
        ],
    )
    assert entry.main() == 1
    assert received["version"] == "v1"
    assert received["reference_date"] == "2026-09-27"
    assert received["capture_semantics"]


@pytest.mark.parametrize("failure", ["return_none", "raise"])
def test_capture_failure_keeps_gate_result_and_never_retries(tmp_path, monkeypatch, failure):
    from tools.validation.requirement_capture import DevelopmentRequirementCapture

    request, sends, _ = setup_case(tmp_path, monkeypatch)

    def failed_record(*args, **kwargs):
        if failure == "raise":
            raise OSError("Synthetic capture failure")
        return None

    monkeypatch.setattr(DevelopmentRequirementCapture, "record", failed_record)
    result = run_case(
        request, tmp_path / "case", capture_requirements=True, reference_date="2026-09-26"
    )
    assert result["application_exit_code"] == 2
    assert result["capture_status"] == "incomplete"
    assert result["acceptance_status"] == "evidence_incomplete"
    assert len(sends) == 1


def test_default_capture_is_disabled_and_existing_case_cannot_run_again(tmp_path, monkeypatch):
    request, sends, _ = setup_case(tmp_path, monkeypatch)
    output = tmp_path / "case"
    result = run_case(request, output, reference_date="2026-09-26")
    assert result["application_exit_code"] == 2
    assert result["capture_status"] == "disabled"
    assert not (output / "requirements").exists()
    with pytest.raises(FileExistsError):
        run_case(request, output, reference_date="2026-09-26")
    assert len(sends) == 1


def test_saved_draft_identifies_the_prompt_revision(tmp_path, monkeypatch):
    request, _, _ = setup_case(tmp_path, monkeypatch)
    output = tmp_path / "case"
    run_case(request, output, capture_requirements=True, reference_date="2026-09-26")
    records = [json.loads(p.read_text()) for p in (output / "requirements").glob("*.json")]
    draft = next(r for r in records if r["validation_stage"] == "draft_validated")
    assert draft["prompt_version"] == "preference_prompt_23"


def test_case_logging_does_not_leave_a_handler_bound_to_closed_output(tmp_path, monkeypatch):
    request, _, _ = setup_case(tmp_path, monkeypatch)
    logger = logging.getLogger()
    handlers = [h for h in logger.handlers if h.name != "reliable-trip-plan-console"]
    monkeypatch.setattr(logger, "handlers", handlers.copy())
    level = logger.level
    run_case(request, tmp_path / "case", reference_date="2026-09-26")
    assert logger.handlers == handlers
    assert logger.level == level


def test_capture_redacts_client_secret_from_failed_model_draft(tmp_path, monkeypatch):
    payload = visit_payload(hard=True)
    payload["semantic_requirements"][0]["normalized_text"] += " fixture-secret"
    request, sends, _ = setup_case(tmp_path, monkeypatch, payload)
    output = tmp_path / "case"
    result = run_case(request, output, capture_requirements=True, reference_date="2026-09-26")
    assert result["application_exit_code"] == 2 and len(sends) == 1
    saved = "".join(p.read_text() for p in (output / "requirements").glob("*.json"))
    assert "fixture-secret" not in saved
    assert "[REDACTED]" in saved


@pytest.mark.parametrize("enabled", [False, True])
def test_missing_file_trace_preserves_business_result(tmp_path, monkeypatch, enabled):
    from backend.app.observability.run_trace import NullRunTracer
    from backend.app.runtime.config_loader import load_runtime_config

    request, sends, _ = setup_case(tmp_path, monkeypatch)
    config = load_runtime_config().model_dump(mode="json")
    config["trace"]["enabled"] = enabled
    config_path = tmp_path / "runtime.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(
        runner, "create_run_tracer", lambda context, **kwargs: NullRunTracer(context.run_id)
    )
    output = tmp_path / "case"
    result = run_case(
        request,
        output,
        runtime_config=config_path,
        capture_requirements=True,
        reference_date="2026-09-26",
    )
    assert result["application_exit_code"] == 2 and len(sends) == 1
    assert result["trace_directories"] == []
    assert result["trace_status"] == ("unavailable" if enabled else "disabled")
    assert result["acceptance_status"] == ("evidence_incomplete" if enabled else "execution_failed")
    assert json.loads((output / "execution.json").read_text()) == result


@pytest.mark.parametrize("extra_hard", [False, True])
def test_real_sdk_named_count_routing_preserves_independent_hard_condition(extra_hard):
    text = QUOTE
    payload = visit_payload()
    if extra_hard:
        condition = "I require a guarantee that I will never queue on either visit"
        text += ". " + condition
        hard = draft_for(condition).model_dump(mode="json")["semantic_requirements"][0]
        hard["strength"] = "hard"
        payload["semantic_requirements"] = [hard]
    request = PlanningRequest(
        destination="London",
        start_date="2026-10-05",
        end_date="2026-10-07",
        traveler_count=1,
        budget={"amount": "900", "currency": "GBP"},
        additional_preferences=text,
    )
    sends = []

    def handler(request):
        sends.append(request)
        return httpx.Response(200, json=response(json.dumps(current_response(payload, request)), 1))

    async def exercise():
        client = AzureFoundryStructuredLLMClient(
            endpoint="https://fixture.invalid/openai/v1",
            deployment="fixture-model",
            api_key="fixture-secret",
            http_async_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        try:
            if extra_hard:
                with pytest.raises(ClarificationRequired) as caught:
                    await interpret_preferences(request, date(2026, 9, 26), client)
                assert caught.value.as_dict()["requirement_ids"] == ("semantic_1",)
            else:
                contract = await interpret_preferences(request, date(2026, 9, 26), client)
                assert contract.named_places[0].inclusion == "REQUIRED"
                visit = contract.visit_requirements[0]
                assert visit.requirement_id == contract.named_places[0].requirement_id
                assert visit.exact_visits == visit.minimum_visits == 2
                assert visit.distinct_dates and visit.dates == ()
                assert contract.semantic_requirements == ()
        finally:
            await client.aclose()

    asyncio.run(exercise())
    assert len(sends) == 1
