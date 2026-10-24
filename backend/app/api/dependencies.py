"""FastAPI dependencies for planning services."""

from functools import lru_cache

from backend.app.policies.trip_dates import DateProvider, SystemDateProvider
from backend.app.runtime.config_loader import load_product_runtime_config, load_runtime_config
from backend.app.runtime.logging_config import configure_logging
from backend.app.services.planner_runtime import RequestPlannerRuntime
from backend.app.services.planning import DeveloperPlanningService, PlanningService
from backend.app.services.product_language import create_product_planner_dependencies


@lru_cache
def get_date_provider() -> DateProvider:
    """Provide the trusted configured-zone date source for production requests."""

    runtime_config = load_runtime_config()
    configure_logging(runtime_config.logging)
    return SystemDateProvider(runtime_config.app.time_zone)


@lru_cache
def get_planning_service() -> PlanningService:
    """Provide the version-agnostic product planning service."""

    return PlanningService(
        RequestPlannerRuntime(
            config=load_product_runtime_config(),
            dependency_factory=create_product_planner_dependencies,
        ),
        get_date_provider(),
        spend_limit_usd=load_product_runtime_config().generation_spend_usd,
    )


@lru_cache
def get_developer_planning_service() -> DeveloperPlanningService:
    """Provide the locally exposed developer planning service."""

    return DeveloperPlanningService(RequestPlannerRuntime(), get_date_provider())
