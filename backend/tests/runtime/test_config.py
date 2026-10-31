"""Tests for global YAML policy, hard limits, and deterministic configuration."""

import copy
import json
import logging
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from backend.app.runtime.budget import ToolBudget, ToolBudgetLimits
from backend.app.runtime.budget_limits import (
    BASELINE_ROUTE_MATRIX_PER_REQUEST_HARD_LIMIT,
    TOOL_BUDGET_HARD_LIMITS,
    ToolBudgetKey,
)
from backend.app.runtime.config_loader import (
    PROJECT_ROOT,
    load_runtime_config,
    load_runtime_config_file,
    resolve_trace_directory,
    runtime_config_snapshot,
)
from backend.app.runtime.logging_config import _RedactingLogFilter, configure_logging


def _write_config(path: Path, data: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_committed_yaml_selects_quality_first_budget_and_trace_defaults() -> None:
    config = load_runtime_config()
    limits = ToolBudgetLimits()

    assert config.app.time_zone == "Australia/Sydney"
    assert limits.max_candidates == 64
    assert limits.max_final_pois == 20
    assert limits.max_destination_search_calls == 1
    assert limits.max_candidate_search_calls == 12
    assert limits.max_place_detail_calls == 60
    assert limits.max_review_detail_calls == 8
    assert limits.max_review_enriched_places == 8
    assert limits.max_experience_profile_llm_calls == 8
    assert limits.max_route_matrix_elements == 64
    assert limits.max_baseline_route_matrix_elements_per_request == 64
    assert limits.max_baseline_route_matrix_elements == 400
    assert limits.max_baseline_route_matrix_calls == 7
    assert limits.max_alternative_route_pairs == 32
    assert limits.max_alternative_route_matrix_calls == 32
    assert limits.max_weather_calls == 2
    assert config.acquisition.policy_id == "quality_first_1"
    assert config.tripworld_discovery.sql_timeout == 60
    assert config.tripworld_discovery.deadline_seconds == 360
    assert config.main_generation.input_tokens == 252000
    assert config.main_generation.output_tokens == 16384
    assert config.schema_version == 6
    assert limits.max_web_evidence_tasks == 8
    assert config.web_evidence.max_tool_calls == 2
    assert config.web_evidence.page_retrieval.timeout_seconds == 10
    assert config.web_evidence.page_retrieval.max_response_bytes == 262144
    assert config.trace.enabled is True
    assert config.trace.payload_level.value == "metadata"
    assert config.trace.raw_provider_payloads is False


def test_removed_repetition_review_key_is_rejected(tmp_path) -> None:
    data = load_runtime_config().model_dump(mode="json")
    assert data["v3_repair"]["quantity_review_enabled"] is True
    assert "repetition_review_enabled" not in data["v3_repair"]
    data["v3_repair"]["repetition_review_enabled"] = False
    path = tmp_path / "old-policy.yaml"
    _write_config(path, data)
    with pytest.raises(ValidationError, match="repetition_review_enabled"):
        load_runtime_config_file(path)


def test_config_path_and_trace_directory_ignore_working_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert load_runtime_config().app.time_zone == "Australia/Sydney"
    assert resolve_trace_directory(Path("logs")) == PROJECT_ROOT / "logs"
    assert resolve_trace_directory(tmp_path / "trace") == tmp_path / "trace"


def test_yaml_rejects_unknown_keys_bad_types_and_malformed_syntax(tmp_path) -> None:
    data = load_runtime_config().model_dump(mode="json")
    data["unexpected"] = "ignored if validation is lax"
    path = tmp_path / "runtime.yaml"
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)

    del data["unexpected"]
    data["budget"]["places"]["candidate_search_calls"] = "12"
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)

    path.write_text("budget: [unfinished", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_runtime_config_file(path)

    path.write_text("schema_version: 1\nschema_version: 2\n", encoding="utf-8")
    with pytest.raises(yaml.YAMLError, match="Duplicate YAML key"):
        load_runtime_config_file(path)


def test_web_budget_migration_rejects_old_schema_old_key_and_dual_keys(tmp_path) -> None:
    data = load_runtime_config().model_dump(mode="json")
    path = tmp_path / "runtime.yaml"
    data["schema_version"] = 1
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)

    data["schema_version"] = 2
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)

    data["schema_version"] = 6
    data["budget"]["web"]["search_queries"] = data["budget"]["web"].pop("evidence_tasks")
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)

    data["budget"]["web"]["evidence_tasks"] = 6
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)


def test_search_budget_migration_rejects_old_shared_key_and_schema(tmp_path) -> None:
    data = load_runtime_config().model_dump(mode="json")
    path = tmp_path / "runtime.yaml"
    data["schema_version"] = 4
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)

    data["schema_version"] = 6
    places = data["budget"]["places"]
    places["search_calls"] = places.pop("candidate_search_calls")
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)

    places["candidate_search_calls"] = 12
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)


def test_invalid_authority_domain_override_fails_config_validation(tmp_path) -> None:
    data = load_runtime_config().model_dump(mode="json")
    data["web_evidence"]["authority_domain_overrides"] = [
        {
            "place_id": "alpha",
            "information_needs": ["date_specific_operational_exception"],
            "domains": ["localhost"],
        }
    ]
    path = tmp_path / "runtime.yaml"
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)


def test_page_retrieval_safety_defaults_are_strict(tmp_path) -> None:
    data = load_runtime_config().model_dump(mode="json")
    data["web_evidence"]["page_retrieval"]["max_response_bytes"] = 524288
    path = tmp_path / "runtime.yaml"
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)


_BUDGET_PATHS = {
    ToolBudgetKey.ALTERNATIVE_ROUTE_ELEMENTS: ("routes", "alternative_elements"),
    ToolBudgetKey.CANDIDATES: ("candidates",),
    ToolBudgetKey.FINAL_POIS: ("final_pois",),
    ToolBudgetKey.DESTINATION_SEARCH_CALLS: ("places", "destination_search_calls"),
    ToolBudgetKey.CANDIDATE_SEARCH_CALLS: ("places", "candidate_search_calls"),
    ToolBudgetKey.PLACE_DETAIL_CALLS: ("places", "detail_calls"),
    ToolBudgetKey.REVIEW_DETAIL_CALLS: ("places", "review_detail_calls"),
    ToolBudgetKey.REVIEW_ENRICHED_PLACES: ("experience", "review_enriched_places"),
    ToolBudgetKey.EXPERIENCE_PROFILE_LLM_CALLS: ("experience", "profile_llm_calls"),
    ToolBudgetKey.WEB_EVIDENCE_TASKS: ("web", "evidence_tasks"),
    ToolBudgetKey.PAGE_FETCHES: ("web", "page_fetches"),
    ToolBudgetKey.ROUTE_MATRIX_ELEMENTS: ("routes", "matrix_elements"),
    ToolBudgetKey.BASELINE_ROUTE_MATRIX_ELEMENTS: ("routes", "baseline_elements_per_run"),
    ToolBudgetKey.BASELINE_ROUTE_MATRIX_CALLS: ("routes", "baseline_calls"),
    ToolBudgetKey.ALTERNATIVE_ROUTE_PAIRS: ("routes", "alternative_pairs"),
    ToolBudgetKey.ALTERNATIVE_ROUTE_MATRIX_CALLS: ("routes", "alternative_matrix_calls"),
    ToolBudgetKey.WEATHER_CALLS: ("weather", "calls"),
}


@pytest.mark.parametrize("key", list(ToolBudgetKey))
def test_every_yaml_budget_has_one_enforced_hard_limit(tmp_path, key) -> None:
    limit = TOOL_BUDGET_HARD_LIMITS[key]
    data = copy.deepcopy(load_runtime_config().model_dump(mode="json"))
    target = data["budget"]
    path = _BUDGET_PATHS[key]
    for segment in path[:-1]:
        target = target[segment]
    config_path = tmp_path / "runtime.yaml"
    if key is ToolBudgetKey.REVIEW_ENRICHED_PLACES:
        data["budget"]["places"]["review_detail_calls"] = limit.maximum
        data["budget"]["experience"]["profile_llm_calls"] = limit.maximum
    if key is ToolBudgetKey.FINAL_POIS:
        data["budget"]["routes"]["baseline_elements_per_run"] = 3600
        data["budget"]["routes"]["baseline_calls"] = 128
    if key is ToolBudgetKey.ALTERNATIVE_ROUTE_PAIRS:
        data["budget"]["routes"]["alternative_elements"] = 128
    target[path[-1]] = limit.maximum
    _write_config(config_path, data)
    assert load_runtime_config_file(config_path).budget.as_key_limits()[key] == limit.maximum

    target[path[-1]] = limit.maximum + 1
    _write_config(config_path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(config_path)


def test_baseline_route_request_run_and_call_limits_are_independent(tmp_path) -> None:
    data = load_runtime_config().model_dump(mode="json")
    routes = data["budget"]["routes"]
    assert routes["matrix_elements"] == 64  # Current V1 graph compatibility bridge.
    assert routes["baseline_elements_per_request"] == 64
    assert routes["baseline_elements_per_run"] == 400
    assert routes["baseline_calls"] == 7
    assert BASELINE_ROUTE_MATRIX_PER_REQUEST_HARD_LIMIT.maximum == 64

    path = tmp_path / "runtime.yaml"
    routes["baseline_elements_per_request"] = 65
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)

    with pytest.raises(ValidationError):
        ToolBudgetLimits(max_baseline_route_matrix_elements_per_request=65)

    budget = ToolBudget()
    budget.consume(ToolBudgetKey.BASELINE_ROUTE_MATRIX_ELEMENTS, 36)
    budget.consume(ToolBudgetKey.BASELINE_ROUTE_MATRIX_CALLS)
    summary = budget.summary()
    assert summary["baseline_route_matrix_elements"]["used"] == 36
    assert summary["baseline_route_matrix_calls"]["used"] == 1
    assert summary["route_matrix_elements"]["used"] == 0

    routes["baseline_elements_per_request"] = 32
    routes["baseline_elements_per_run"] = 31
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)


@pytest.mark.parametrize(
    ("section", "field"),
    [("places", "review_detail_calls"), ("experience", "profile_llm_calls")],
)
def test_review_attempt_budget_cannot_be_lower_than_review_poi_budget(
    tmp_path, section: str, field: str
) -> None:
    data = load_runtime_config().model_dump(mode="json")
    data["budget"][section][field] = 5
    path = tmp_path / "runtime.yaml"
    _write_config(path, data)
    with pytest.raises(ValidationError):
        load_runtime_config_file(path)


def test_env_cannot_override_yaml_policy(monkeypatch) -> None:
    monkeypatch.setenv("V1_MAX_ALTERNATIVE_ROUTE_PAIRS", "16")
    monkeypatch.setenv("V1_TRACE_ENABLED", "false")
    monkeypatch.setenv("APP_TIME_ZONE", "Pacific/Auckland")

    assert ToolBudgetLimits().max_alternative_route_pairs == 32
    assert load_runtime_config().trace.enabled is True
    assert load_runtime_config().app.time_zone == "Australia/Sydney"


def test_runtime_budget_can_increase_within_global_hard_limits() -> None:
    limits = ToolBudgetLimits(
        max_alternative_route_pairs=12,
        max_alternative_route_matrix_calls=6,
    )

    assert limits.max_alternative_route_pairs == 12
    assert limits.max_alternative_route_matrix_calls == 6


def test_config_snapshot_is_stable_and_contains_only_policy() -> None:
    config = load_runtime_config()
    snapshot, digest = runtime_config_snapshot(
        config,
        effective_budget={key.value: value for key, value in config.budget.as_key_limits().items()},
    )

    assert snapshot["trace"]["directory"] == "logs"
    assert snapshot["effective_tool_budget"]["alternative_route_pairs"] == 32
    assert snapshot["effective_tool_budget"]["web_evidence_tasks"] == 8
    assert "web_search_queries" not in json.dumps(snapshot)
    assert (snapshot, digest) == runtime_config_snapshot(
        config,
        effective_budget={key.value: value for key, value in config.budget.as_key_limits().items()},
    )
    assert len(digest) == 64
    assert "API_KEY" not in json.dumps(snapshot)


def test_logging_policy_controls_owned_console_handler() -> None:
    root = logging.getLogger()
    original_level = root.level
    try:
        config = load_runtime_config().logging
        configure_logging(config.model_copy(update={"level": "WARNING", "console": True}))
        assert root.level == logging.WARNING
        assert any(h.get_name() == "reliable-trip-plan-console" for h in root.handlers)
        configure_logging(config.model_copy(update={"console": False}))
        assert not any(h.get_name() == "reliable-trip-plan-console" for h in root.handlers)
    finally:
        root.setLevel(original_level)


def test_console_log_filter_redacts_provider_query_credentials() -> None:
    record = logging.LogRecord(
        "httpx",
        logging.INFO,
        __file__,
        1,
        "HTTP Request: GET https://weather.example.test/forecast?key=live-secret&days=10",
        (),
        None,
    )

    assert _RedactingLogFilter().filter(record) is True
    assert "live-secret" not in record.getMessage()
    assert "key=%5BREDACTED%5D" in record.getMessage()







def test_repair_input_ceiling_accepts_authorized_capacity_and_rejects_overflow():
    from backend.app.runtime.config_models import RepairInputConfig

    values = load_runtime_config().v3_repair.input.model_dump()
    assert values["input_tokens"] == 252000
    assert RepairInputConfig.model_validate(values).input_tokens == 252000
    with pytest.raises(ValidationError):
        RepairInputConfig.model_validate({**values, "input_tokens": 922001})


def test_rag_time_and_work_bounds_remain_finite():
    from backend.app.versions.v2.config import RAGConfig

    effective = load_runtime_config().tripworld_discovery
    for values in (
        {"sql_timeout": 0}, {"sql_timeout": 121}, {"deadline_seconds": 601},
        {"top_k": 31}, {"max_queries": 9}, {"retries": 1},
    ):
        with pytest.raises(ValidationError):
            RAGConfig.model_validate({**effective.model_dump(), **values})
