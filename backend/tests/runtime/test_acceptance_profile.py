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
        (ToolBudgetKey.CANDIDATES, 128),
        (ToolBudgetKey.CANDIDATE_SEARCH_CALLS, 24),
        (ToolBudgetKey.PLACE_DETAIL_CALLS, 120),
        (ToolBudgetKey.FINAL_POIS, 40),
        (ToolBudgetKey.BASELINE_ROUTE_MATRIX_ELEMENTS, 1600),
        (ToolBudgetKey.BASELINE_ROUTE_MATRIX_CALLS, 32),
    ]:
        budget.consume(key, quantity)
        with pytest.raises(ToolBudgetExceededError):
            budget.consume(key)
    assert config.v3_repair.input.identity_capacity == 64
    assert config.v3_repair.max_rounds == config.v3_repair.max_model_calls == 10
    assert config.v3_repair.timing.stage_seconds == 720
    assert config.v3_repair.timing.model_seconds == 120
    assert config.development_timeout_seconds == 1200
    assert config.poi_semantics.max_calls == 12
    assert config.poi_semantics.total_seconds == 240
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
