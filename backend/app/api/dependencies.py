"""FastAPI dependencies for planning services."""

from functools import lru_cache

from fastapi import Request

from backend.app.policies.trip_dates import DateProvider, SystemDateProvider
from backend.app.runtime.config_loader import load_product_runtime_config, load_runtime_config
from backend.app.runtime.logging_config import configure_logging
from backend.app.services.planner_runtime import RequestPlannerRuntime
from backend.app.services.planning import PlanningService
from backend.app.services.product_language import create_product_planner_dependencies


@lru_cache
def get_date_provider() -> DateProvider:
    """Provide the trusted configured-zone date source for production requests."""

    runtime_config = load_runtime_config()
    configure_logging(runtime_config.logging)
    return SystemDateProvider(runtime_config.app.time_zone)


def get_planning_service(request: Request) -> PlanningService:
    """Provide the version-agnostic product planning service."""

    existing = getattr(request.app.state, "product_planning_service", None)
    if existing is not None:
        return existing
    from backend.app.runtime.deployment import ProductPolicySettings

    rag_enabled = getattr(request.app.state, "rag_enabled", None)
    if rag_enabled is None:
        rag_enabled = ProductPolicySettings().rag_enabled
        request.app.state.rag_enabled = rag_enabled
    service = PlanningService(
        RequestPlannerRuntime(
            config=load_product_runtime_config(),
            dependency_factory=create_product_planner_dependencies,
            rag_enabled=rag_enabled,
        ),
        get_date_provider(),
        spend_limit_usd=load_product_runtime_config().generation_spend_usd,
    )
    request.app.state.product_planning_service = service
    return service
