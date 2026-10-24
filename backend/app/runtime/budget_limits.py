"""One project-wide source of hard safety ceilings for tool usage."""

from dataclasses import dataclass
from enum import StrEnum


class ToolBudgetKey(StrEnum):
    """Provider operations and bounded result dimensions tracked per run."""

    CANDIDATES = "candidates"
    DESTINATION_SEARCH_CALLS = "destination_search_calls"
    CANDIDATE_SEARCH_CALLS = "candidate_search_calls"
    PLACE_DETAIL_CALLS = "place_detail_calls"
    REVIEW_DETAIL_CALLS = "review_detail_calls"
    REVIEW_ENRICHED_PLACES = "review_enriched_places"
    EXPERIENCE_PROFILE_LLM_CALLS = "experience_profile_llm_calls"
    FINAL_POIS = "final_pois"
    WEB_EVIDENCE_TASKS = "web_evidence_tasks"
    PAGE_FETCHES = "page_fetches"
    ROUTE_MATRIX_ELEMENTS = "route_matrix_elements"
    BASELINE_ROUTE_MATRIX_ELEMENTS = "baseline_route_matrix_elements"
    BASELINE_ROUTE_MATRIX_CALLS = "baseline_route_matrix_calls"
    ALTERNATIVE_ROUTE_ELEMENTS = "alternative_route_elements"
    ALTERNATIVE_ROUTE_PAIRS = "alternative_route_pairs"
    ALTERNATIVE_ROUTE_MATRIX_CALLS = "alternative_route_matrix_calls"
    WEATHER_CALLS = "weather_calls"


@dataclass(frozen=True)
class BudgetHardLimit:
    minimum: int
    maximum: int


BASELINE_ROUTE_MATRIX_PER_REQUEST_HARD_LIMIT = BudgetHardLimit(1, 64)


TOOL_BUDGET_HARD_LIMITS: dict[ToolBudgetKey, BudgetHardLimit] = {
    ToolBudgetKey.CANDIDATES: BudgetHardLimit(1, 128),
    ToolBudgetKey.DESTINATION_SEARCH_CALLS: BudgetHardLimit(1, 1),
    ToolBudgetKey.CANDIDATE_SEARCH_CALLS: BudgetHardLimit(1, 24),
    ToolBudgetKey.PLACE_DETAIL_CALLS: BudgetHardLimit(1, 120),
    ToolBudgetKey.REVIEW_DETAIL_CALLS: BudgetHardLimit(0, 8),
    ToolBudgetKey.REVIEW_ENRICHED_PLACES: BudgetHardLimit(0, 8),
    ToolBudgetKey.EXPERIENCE_PROFILE_LLM_CALLS: BudgetHardLimit(0, 8),
    ToolBudgetKey.FINAL_POIS: BudgetHardLimit(1, 40),
    ToolBudgetKey.WEB_EVIDENCE_TASKS: BudgetHardLimit(0, 20),
    ToolBudgetKey.PAGE_FETCHES: BudgetHardLimit(0, 20),
    # Transitional single-matrix counter used only by the current V1 graph.
    ToolBudgetKey.ROUTE_MATRIX_ELEMENTS: BudgetHardLimit(1, 100),
    ToolBudgetKey.BASELINE_ROUTE_MATRIX_ELEMENTS: BudgetHardLimit(1, 1600),
    ToolBudgetKey.BASELINE_ROUTE_MATRIX_CALLS: BudgetHardLimit(1, 32),
    ToolBudgetKey.ALTERNATIVE_ROUTE_ELEMENTS: BudgetHardLimit(0, 64),
    ToolBudgetKey.ALTERNATIVE_ROUTE_PAIRS: BudgetHardLimit(0, 32),
    ToolBudgetKey.ALTERNATIVE_ROUTE_MATRIX_CALLS: BudgetHardLimit(0, 32),
    ToolBudgetKey.WEATHER_CALLS: BudgetHardLimit(0, 3),
}


def validate_budget_values(values: dict[ToolBudgetKey, int]) -> None:
    """Reject runtime budgets outside the single project-wide safety envelope."""

    for key in ToolBudgetKey:
        value = values[key]
        limit = TOOL_BUDGET_HARD_LIMITS[key]
        if not limit.minimum <= value <= limit.maximum:
            raise ValueError(
                f"{key.value} must be between {limit.minimum} and {limit.maximum}; got {value}"
            )


def validate_baseline_per_request_elements(value: int) -> None:
    """Validate the separate per-request matrix bound without treating it as usage."""

    limit = BASELINE_ROUTE_MATRIX_PER_REQUEST_HARD_LIMIT
    if not limit.minimum <= value <= limit.maximum:
        raise ValueError(
            "baseline_route_matrix_elements_per_request must be between "
            f"{limit.minimum} and {limit.maximum}; got {value}"
        )
