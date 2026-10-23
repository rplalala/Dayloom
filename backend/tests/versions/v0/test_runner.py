"""Tests for V0 configuration and independent CLI behavior."""

import io
import json
import sys
from datetime import date

import pytest
from pydantic_settings import SettingsConfigDict

from backend.app.llm.azure_foundry import AzureFoundryStructuredLLMClient
from backend.app.services.preference_interpretation import empty_preference_draft
from backend.app.versions.v0.config import V0Settings
from backend.app.versions.v0.runner import (
    create_foundry_client,
    main,
    parse_reference_date,
)
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import (
    FakeStructuredLLMClient,
    make_itinerary,
    make_requirements,
)


@pytest.fixture(autouse=True)
def input_json_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    request = make_request("Plan a trip.", requirements=make_requirements())
    (tmp_path / "request.json").write_text(request.model_dump_json(), encoding="utf-8")


def test_v0_settings_use_deployment_for_foundry(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://example.services.ai.azure.com/openai/v1",
    )
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "configured-deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")

    settings = V0Settings(_env_file=None)

    assert str(settings.azure_openai_endpoint) == (
        "https://example.services.ai.azure.com/openai/v1"
    )
    assert settings.azure_openai_deployment == "configured-deployment"
    assert settings.azure_openai_api_key.get_secret_value() == "test-key"


def test_independent_planner_loads_foundry_yaml_with_environment_override(monkeypatch, tmp_path):
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    path = tmp_path / "deployment.yaml"
    path.write_text(
        "foundry:\n  endpoint: https://yaml.invalid/openai/v1\n  deployment: yaml-model\n",
        encoding="utf-8",
    )

    class Settings(V0Settings):
        model_config = SettingsConfigDict(yaml_file=path)

    settings = Settings(_env_file=None, azure_openai_api_key="synthetic-key")
    assert settings.azure_openai_deployment == "yaml-model"
    assert str(settings.azure_openai_endpoint) == "https://yaml.invalid/openai/v1"
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "process-model")
    overridden = Settings(_env_file=None, azure_openai_api_key="synthetic-key")
    assert overridden.azure_openai_deployment == "process-model"


def test_v0_foundry_client_uses_deployment_for_api_model(monkeypatch) -> None:
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://example.services.ai.azure.com/openai/v1",
    )
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "configured-deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    settings = V0Settings(_env_file=None)

    client = create_foundry_client(settings)

    assert isinstance(client, AzureFoundryStructuredLLMClient)
    assert client._chat_model.model_name == "configured-deployment"
    assert client._chat_model.openai_api_base == (
        "https://example.services.ai.azure.com/openai/v1"
    )
    assert client._chat_model.use_responses_api is True
    assert client._chat_model.max_retries == 0


def test_reference_date_parser_accepts_iso_date() -> None:
    assert parse_reference_date("2026-09-11") == date(2026, 9, 11)


def test_v0_cli_outputs_planning_result_json(capsys) -> None:
    client = FakeStructuredLLMClient([empty_preference_draft(), make_itinerary()])

    exit_code = main(
        [
            "--input-json", "request.json",
            "--reference-date",
            "2026-09-11",
        ],
        llm_client=client,
    )

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert output["system_version"] == "v0"
    assert set(output) == {"system_version", "requirements", "itinerary", "generation_diagnostics"}


def test_v0_cli_preserves_unicode_through_cp936_safe_json(
    monkeypatch,
) -> None:
    itinerary = make_itinerary()
    activity = itinerary.days[0].activities[0].model_copy(
        update={"title": "Visit shrine 😀"}
    )
    day = itinerary.days[0].model_copy(update={"activities": [activity]})
    itinerary = itinerary.model_copy(update={"days": [day]})
    client = FakeStructuredLLMClient([empty_preference_draft(), itinerary])

    output_buffer = io.BytesIO()
    cp936_stdout = io.TextIOWrapper(output_buffer, encoding="cp936", errors="strict")
    monkeypatch.setattr(sys, "stdout", cp936_stdout)

    exit_code = main(
        [
            "--input-json", "request.json",
            "--reference-date",
            "2026-09-11",
        ],
        llm_client=client,
    )
    cp936_stdout.flush()
    serialized = output_buffer.getvalue().decode("cp936")
    parsed = json.loads(serialized)

    assert exit_code == 0
    assert "\\ud83d\\ude00" in serialized
    assert parsed["itinerary"]["days"][0]["activities"][0]["title"] == (
        "Visit shrine 😀"
    )


def test_v0_cli_reports_invalid_input_without_model(capsys, tmp_path):
    (tmp_path / "request.json").write_text('{"destination":"Kyoto"}', encoding="utf-8")
    client = FakeStructuredLLMClient([])
    assert main(["--input-json", "request.json"], llm_client=client) == 2
    assert json.loads(capsys.readouterr().err)["error"] == "invalid_planning_input"
    assert not client.calls


def test_v0_cli_reports_provider_failure_without_retry(capsys) -> None:
    client = FakeStructuredLLMClient([RuntimeError("provider unavailable")])

    exit_code = main(
        ["--input-json", "request.json", "--reference-date", "2026-09-11"],
        llm_client=client,
    )

    captured = capsys.readouterr()
    error = json.loads(captured.err)
    assert exit_code == 1
    assert captured.out == ""
    assert error == {
        "error": "v0_stage_failed",
        "stage": "extract_requirements",
        "message": "provider unavailable",
    }
    assert len(client.calls) == 1
