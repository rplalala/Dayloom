"""Selectable Product resources do not change the independent development policy."""

import pytest

from backend.app.runtime.budget import ToolBudget, ToolBudgetExceededError, ToolBudgetKey
from backend.app.runtime.config_loader import (
    load_runtime_config,
    runtime_config_snapshot,
    tool_limits,
)


def test_acceptance_profile_supports_larger_work_while_development_remains_selectable():
    from backend.app.runtime.config_loader import load_runtime_profile

    config = load_runtime_profile("acceptance")
    budget = ToolBudget(tool_limits(config))
    for key, quantity in [
        (ToolBudgetKey.CANDIDATES, 256),
        (ToolBudgetKey.CANDIDATE_SEARCH_CALLS, 48),
        (ToolBudgetKey.PLACE_DETAIL_CALLS, 240),
        (ToolBudgetKey.FINAL_POIS, 60),
        (ToolBudgetKey.BASELINE_ROUTE_MATRIX_ELEMENTS, 3600),
        (ToolBudgetKey.BASELINE_ROUTE_MATRIX_CALLS, 128),
    ]:
        budget.consume(key, quantity)
        with pytest.raises(ToolBudgetExceededError):
            budget.consume(key)
    assert config.v3_repair.input.identity_capacity == 128
    assert config.v3_repair.max_rounds == config.v3_repair.max_model_calls == 20
    assert config.v3_repair.timing.stage_seconds == 1800
    assert config.v3_repair.timing.model_seconds == 240
    assert config.development_timeout_seconds == 2700
    assert config.poi_semantics.max_calls == 24
    assert config.poi_semantics.total_seconds == 600
    assert config.generation_spend_usd == 25
    assert load_runtime_profile("development") == load_runtime_config()
    development = ToolBudget(tool_limits(load_runtime_config()))
    with pytest.raises(ToolBudgetExceededError):
        development.consume(ToolBudgetKey.FINAL_POIS, 21)
    assert runtime_config_snapshot(config) == runtime_config_snapshot(
        load_runtime_profile("acceptance")
    )
    assert runtime_config_snapshot(config)[1] != runtime_config_snapshot(load_runtime_config())[1]


def test_product_defaults_to_acceptance_and_supports_explicit_development(monkeypatch):
    from backend.app.runtime.config_loader import load_product_runtime_config

    monkeypatch.delenv("PRODUCT_RUNTIME_PROFILE", raising=False)
    assert load_product_runtime_config().resource_profile == "acceptance"
    monkeypatch.setenv("PRODUCT_RUNTIME_PROFILE", "development")
    assert load_product_runtime_config() == load_runtime_config()


def test_legacy_configuration_snapshot_round_trip_keeps_its_digest():
    from backend.app.runtime.config_models import RuntimeConfig

    snapshot, digest = runtime_config_snapshot(load_runtime_config())
    assert "resource_profile" not in snapshot
    assert runtime_config_snapshot(RuntimeConfig.model_validate(snapshot)) == (snapshot, digest)
