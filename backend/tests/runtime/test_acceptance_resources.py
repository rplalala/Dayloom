"""Acceptance resources admit larger work while preserving finite provider bounds."""

import pytest
from pydantic import ValidationError

from backend.app.runtime.budget import ToolBudget, ToolBudgetExceededError, ToolBudgetKey
from backend.app.runtime.config_loader import load_runtime_profile, tool_limits
from backend.app.runtime.config_models import RuntimeConfig


def test_large_model_transport_loads_without_changing_development_defaults():
    development = load_runtime_profile("development")
    values = load_runtime_profile("acceptance").model_dump(mode="json")
    for group in (
        values["main_generation"], values["auxiliary_model_limits"], values["v3_repair"]["input"],
    ):
        group.update(input_tokens=900_000, output_tokens=32_768)

    config = RuntimeConfig.model_validate(values)

    assert config.v3_repair.input.input_tokens == 900_000
    assert development.v3_repair.input.input_tokens == 252_000
    for group in ("main_generation", "auxiliary_model_limits"):
        with pytest.raises(ValidationError):
            RuntimeConfig.model_validate(
                {**values, group: {**values[group], "input_tokens": 922_001}}
            )


def test_acceptance_admits_larger_evidence_work_but_still_stops_at_its_budget():
    budget = ToolBudget(tool_limits(load_runtime_profile("acceptance")))
    for key, amount in (
        (ToolBudgetKey.CANDIDATES, 200),
        (ToolBudgetKey.PLACE_DETAIL_CALLS, 160),
        (ToolBudgetKey.REVIEW_DETAIL_CALLS, 16),
        (ToolBudgetKey.REVIEW_ENRICHED_PLACES, 16),
        (ToolBudgetKey.EXPERIENCE_PROFILE_LLM_CALLS, 16),
        (ToolBudgetKey.FINAL_POIS, 50),
        (ToolBudgetKey.BASELINE_ROUTE_MATRIX_CALLS, 60),
        (ToolBudgetKey.BASELINE_ROUTE_MATRIX_ELEMENTS, 2500),
        (ToolBudgetKey.ALTERNATIVE_ROUTE_MATRIX_CALLS, 96),
    ):
        budget.consume(key, amount)
    before = budget.summary()
    with pytest.raises(ToolBudgetExceededError):
        budget.consume(ToolBudgetKey.CANDIDATES, budget.remaining(ToolBudgetKey.CANDIDATES) + 1)
    assert budget.summary() == before


def test_acceptance_repair_can_continue_beyond_the_old_stage_envelope():
    from backend.app.versions.v3.repair_budget import RepairBudget, RepairLimit

    config = load_runtime_profile("acceptance")
    assert config.v3_repair.input.input_tokens >= 500_000
    assert config.main_generation.output_tokens >= 32_768
    assert config.tripworld_discovery.max_queries >= 8
    budget = RepairBudget(
        100 + config.development_timeout_seconds, clock=lambda: 100, runtime_config=config,
    )
    assert budget.remaining() == 1800
    budget.charge(model=11, google=8, fallback=2, embedding=2, retrieval=2,
                  canonical=40, details=40, routes=40, elements=80)
    before = dict(budget.used)
    with pytest.raises(RepairLimit):
        budget.charge(model=config.v3_repair.max_model_calls)
    assert dict(budget.used) == before
