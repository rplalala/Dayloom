"""Actual interpreter and strict SDK parsing over MockTransport, never real services."""

import asyncio
import copy
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import httpx
import pytest
from openai import AsyncOpenAI

from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
from backend.tests.llm.azure_foundry.test_requirement_acceptance_harness import response
from backend.tests.request_fixtures import make_request
from backend.tests.services.test_preference_input_gate import NY, draft, issue
from tools.validation import preference_gate_smoke as smoke

REFERENCE = date(2026, 9, 11)


@pytest.fixture(autouse=True)
def no_downstream(monkeypatch):
    from backend.app.versions.v0 import runner as v0
    from backend.app.versions.v1 import runner as v1
    from backend.app.versions.v2 import runner as v2
    from backend.app.versions.v3 import runner as v3

    def forbidden(*args, **kwargs):
        raise AssertionError("Travel runner must not be entered")

    for module, name in ((v0, "run_v0"), (v1, "run_v1"), (v2, "run_v2"), (v3, "run_v3")):
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")


def matrix(tmp_path, values):
    source = tmp_path / "source.txt"
    source.write_text("frozen fixture", encoding="utf-8")
    cases = []
    for index, value in enumerate(values):
        a = value.preference_input_assessment
        cases.append(
            {
                "case_id": f"case_{index}",
                "request": make_request(NY, destination="Paris").model_dump(mode="json"),
                "expected_input": a.input_disposition,
                "expected_safety": a.safety_disposition,
                "expected_issue_types": [i.issue_type for i in a.issues],
                "expected_source_quotes": [r.quote for i in a.issues for r in i.source_refs],
            }
        )
    return {
        "deployment": "fixture-model",
        "cases": cases,
        "source_hashes": {str(source): smoke.digest(source)},
        "historical_hashes": {str(source): smoke.digest(source)},
    }


def execute(
    tmp_path,
    values,
    *,
    manifest=None,
    handler_override=None,
    close_failure=False,
    reference=REFERENCE,
    **kwargs,
):
    manifest = manifest or matrix(tmp_path, values)
    sends = []
    clients = []

    def handler(request):
        sends.append(request)
        if handler_override:
            return handler_override(request)
        value = values[len(sends) - 1]
        payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
        from backend.tests.llm.azure_foundry.requirement_fixtures import current_response

        payload = current_response(payload, request)
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return httpx.Response(200, json=response(text, len(sends)))

    def factory():
        client = AzureFoundryStructuredLLMClient(
            endpoint="https://fixture.invalid/openai/v1",
            deployment="fixture-model",
            api_key="fixture-secret",
        )
        # Close the unused default async SDK without ever sending a request.
        original = client._chat_model.root_async_client
        sdk = AsyncOpenAI(
            api_key="fixture-secret",
            base_url="https://fixture.invalid/openai/v1",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        client._chat_model.root_async_client = sdk
        close = client.aclose

        async def cleanup():
            await original.close()
            await close()
            if close_failure:
                raise RuntimeError("fixture cleanup failure")

        client.aclose = cleanup
        clients.append(client)
        return client

    result = asyncio.run(
        smoke.run_smoke(
            manifest,
            tmp_path / "run",
            deployment="fixture-model",
            reference=reference,
            client_factory=factory,
            **kwargs,
        )
    )
    return result, sends, clients


def test_ten_cases_reach_real_interpreter_without_capture_leak(tmp_path):
    values = [draft(issue()), draft(disposition="VALID")] * 5
    result, sends, clients = execute(tmp_path, values)
    assert result["stop_reason"] is None
    assert result["model_calls"] == result["http_sends"] == len(sends) == 10
    for index, row in enumerate(result["cases"]):
        assert row["frozen_expectation_match"]
        assert row["strict_parsed_dto"] and row["domain_parsed_dto"]
        assert len(row["raw_model_response"]) == 1
        assert row["raw_model_response"][0]["response_id"] == f"resp_{index + 1}"
        assert row["callback_cumulative"]["fixture-model"]["input_tokens"] == 30 * (index + 1)
    assert result["callback_total"]["fixture-model"]["input_tokens"] == 300
    assert clients[0]._chat_model.root_async_client.is_closed()
    assert clients[0]._chat_model.root_client.is_closed()


@pytest.mark.parametrize("failure", ["index", "quote", "occurrence", "malformed", "missing"])
def test_first_contract_failure_stops_remaining_and_keeps_response(tmp_path, failure):
    good = draft(issue())
    manifest = matrix(tmp_path, [good] * 10)
    payload = good.model_dump(mode="json")
    row = payload["preference_input_assessment"]["issues"][0]
    if failure == "index":
        row["operational_conflict_index"] = 0
    elif failure == "quote":
        row["source_refs"][0]["quote"] = "Invented quotation."
    elif failure == "occurrence":
        row["source_refs"][0]["occurrence"] = 1
    elif failure == "missing":
        payload["preference_input_assessment"] = None
    else:
        payload = '{"broken":'
    result, sends, _ = execute(tmp_path, [payload], manifest=manifest)
    assert result["stop_reason"] == "contract_failure:case_0"
    assert len(sends) == 1
    assert result["cases"][0]["raw_model_response"]
    assert all(r["state"] == "NOT_ATTEMPTED" for r in result["cases"][1:])
    assert result["callback_total"]["fixture-model"]["input_tokens"] == 30


def test_provider_error_no_retry_or_fake_usage(tmp_path):
    result, sends, _ = execute(
        tmp_path,
        [draft(disposition="VALID")] * 10,
        handler_override=lambda _: httpx.Response(503, json={"error": {"message": "fixture"}}),
    )
    assert len(sends) == 1
    assert result["stop_reason"] == "provider_failure:case_0"
    assert result["callback_total"] == {}
    assert result["cases"][0]["http_responses"] == [{"status_code": 503}]


def test_capture_failure_retains_attempt_usage_and_first_reason(tmp_path):
    def broken(row):
        raise RuntimeError("capture failed")

    result, sends, _ = execute(
        tmp_path, [draft(disposition="VALID")] * 3, capture=broken, close_failure=True
    )
    assert len(sends) == 1
    assert result["stop_reason"] == "capture_failure:case_0"
    assert result["secondary_errors"] == ["cleanup_failure:RuntimeError"]
    assert result["cases"][0]["state"] == "completed"
    assert result["callback_total"]["fixture-model"]["input_tokens"] == 30


def test_record_write_failure_does_not_relabel_attempt(tmp_path):
    def writer(path, value):
        if path.name == "case_0.json":
            raise OSError("fixture write error")
        smoke.write_once(path, value)

    result, sends, _ = execute(tmp_path, [draft(disposition="VALID")] * 2, writer=writer)
    assert len(sends) == 1
    assert result["cases"][0]["record_complete"] is False
    assert result["cases"][0]["model_calls"] == 1
    assert result["cases"][1]["state"] == "NOT_ATTEMPTED"


def test_false_positive_stops_and_expected_clarification_and_safety_can_complete(tmp_path):
    valid = draft(disposition="VALID")
    manifest = matrix(tmp_path, [valid, valid])
    result, sends, _ = execute(tmp_path, [draft(issue())], manifest=manifest)
    assert result["stop_reason"] == "expectation_mismatch:case_0"
    assert len(sends) == 1


@pytest.mark.parametrize(
    "kind,disposition,safety",
    [
        ("unsupported_request_scope", "CLARIFICATION_REQUIRED", "CLEAR"),
        ("safety_self_harm", "VALID", "SAFETY_BLOCK"),
    ],
)
def test_expected_clarification_and_safety(tmp_path, kind, disposition, safety):
    value = draft(issue(kind, related_field=None), disposition=disposition, safety=safety)
    result, _, _ = execute(tmp_path, [value])
    assert result["stop_reason"] is None
    assert result["cases"][0]["state"] == "input_blocked"


def test_cancellation_propagates_after_summary_and_close(tmp_path):
    class CancelledModel:
        closed = False

        async def generate_structured(self, **kwargs):
            raise asyncio.CancelledError()

        async def aclose(self):
            self.closed = True

    client = CancelledModel()
    manifest = matrix(tmp_path, [draft(disposition="VALID")] * 2)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            smoke.run_smoke(
                manifest,
                tmp_path / "run",
                deployment="fixture-model",
                reference=REFERENCE,
                client_factory=lambda: client,
                attach=lambda *_: None,
            )
        )
    saved = json.loads((tmp_path / "run/summary.json").read_text())
    assert saved["cases"][0]["state"] == "cancelled"
    assert saved["cases"][1]["state"] == "NOT_ATTEMPTED"
    assert saved["resources"]["adapter_aclose_returned"]
    assert client.closed


@pytest.mark.parametrize("problem", ["directory", "hash", "deployment", "date"])
def test_preflight_refuses_before_client_creation(tmp_path, problem):
    manifest = matrix(tmp_path, [draft(disposition="VALID")])
    output = tmp_path / "run"
    deployment = "fixture-model"
    reference = REFERENCE
    if problem == "directory":
        output.mkdir()
    elif problem == "hash":
        manifest["source_hashes"] = {__file__: "wrong"}
    elif problem == "deployment":
        deployment = "other"
    else:
        reference = date(2026, 9, 13)

    def forbidden():
        pytest.fail("Client created during rejected preflight")

    with pytest.raises(ValueError):
        asyncio.run(
            smoke.run_smoke(
                manifest,
                output,
                deployment=deployment,
                reference=reference,
                client_factory=forbidden,
            )
        )


def test_expectations_and_history_are_not_mutated(tmp_path):
    value = draft(issue())
    manifest = matrix(tmp_path, [value])
    frozen = copy.deepcopy(manifest)
    execute(tmp_path, [value], manifest=manifest)
    assert manifest == frozen
    assert all(smoke.digest(p) == h for p, h in manifest["historical_hashes"].items())


def test_original_ten_frozen_contexts_with_synthetic_model_outputs(tmp_path):
    fixture = Path(__file__).parents[2] / "fixtures/preference_gate/frozen_smoke_cases.json"
    cases = json.loads(fixture.read_text())["cases"]
    values = []
    for case in cases:
        issues = [
            issue(
                kind,
                related_field=case["expected_related_field"],
                operational_conflict_index=case["expected_operational_conflict_index"],
                source_refs=[{"quote": q, "occurrence": 0} for q in case["expected_source_quotes"]],
            )
            for kind in case["expected_issue_types"]
        ]
        values.append(
            draft(*issues, disposition=case["expected_input"], safety=case["expected_safety"])
        )
    manifest = matrix(tmp_path, values)
    manifest["cases"] = copy.deepcopy(cases)
    result, sends, _ = execute(tmp_path, values, manifest=manifest, reference=date(2026, 9, 25))
    assert result["stop_reason"] is None
    assert len(sends) == 10
    assert all(r["frozen_expectation_match"] for r in result["cases"])
    contradiction = result["cases"][1]["application_outcome"]["issues"][0]
    assert [r["quote"] for r in contradiction["source_refs"]] == cases[1]["expected_source_quotes"]
    assert result["cases"][3]["application_outcome"]["category"] == "SAFETY_BLOCK"


def test_cli_requires_explicit_execution_before_settings(tmp_path, monkeypatch):
    import sys

    def forbidden():
        pytest.fail("Settings/client construction must not occur")

    monkeypatch.setattr(smoke, "V0Settings", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke",
            "--manifest",
            "unused",
            "--manifest-sha256",
            "unused",
            "--output",
            str(tmp_path / "run"),
        ],
    )
    with pytest.raises(SystemExit) as error:
        smoke.main()
    assert error.value.code == 2


def test_persisted_capture_redacts_credentials(tmp_path):
    value = draft(disposition="VALID")

    def capture(row):
        smoke.capture_wire(row)
        row["fixture_sensitive_text"] = "fixture-secret"

    execute(tmp_path, [value], capture=capture)
    assert "fixture-secret" not in (tmp_path / "run/summary.json").read_text()
    assert "[REDACTED]" in (tmp_path / "run/case_0.json").read_text()


def test_powershell_propagates_preflight_error_without_loading_settings(tmp_path):
    shell = shutil.which("pwsh")
    if not shell:
        pytest.skip("PowerShell wrapper is Windows-specific")
    fixture = Path(__file__).parents[2] / "fixtures/preference_gate/frozen_smoke_cases.json"
    # Deliberately wrong hash guarantees rejection BEFORE settings/client construction.
    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-File",
            "tools/validation/run_preference_gate_smoke.ps1",
            "-Manifest",
            str(fixture),
            "-ManifestSha256",
            "invalid",
            "-Output",
            str(tmp_path / "run"),
            "-ExecuteLive",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "Manifest hash mismatch" in result.stderr
    assert not (tmp_path / "run").exists()
