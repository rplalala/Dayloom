"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from backend.app.api.input_assistance import router as input_assistance_router
from backend.app.api.product.planning import router as product_planning_router
from backend.app.observability.product_http import ProductHTTPLogging
from backend.app.observability.product_http import router as diagnostics_router
from backend.app.product.auth import router as account_router
from backend.app.product.configuration_api import router as configuration_router
from backend.app.product.copies import router as copies_router
from backend.app.product.drafts import router as drafts_router
from backend.app.product.examples import router as examples_router
from backend.app.product.imports import router as imports_router
from backend.app.product.media import router as media_router
from backend.app.product.profiles import router as profile_router
from backend.app.product.saved import router as saved_router
from backend.app.product.tasks import router as tasks_router


class HealthResponse(BaseModel):
    """Response returned by the health endpoint."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]


def get_health() -> HealthResponse:
    """Report whether the API process is responsive."""

    return HealthResponse(status="ok")


def create_app() -> FastAPI:
    """Recreate the HTTP application without requiring Product/provider configuration."""

    @asynccontextmanager
    async def lifespan(application):
        from backend.app.observability.product_service_logs import configure_product_service_logs
        configure_product_service_logs()
        try:
            yield
        finally:
            coordinator = getattr(application.state, "product_coordinator", None)
            if coordinator:
                await coordinator.close()

    application = FastAPI(
        lifespan=lifespan,
        title="Reliable Trip Plan Agent",
        description="Backend API for reliable itinerary generation.",
        version="0.1.0",
    )
    application.include_router(product_planning_router)
    application.include_router(configuration_router)
    application.add_middleware(ProductHTTPLogging)
    application.include_router(diagnostics_router)
    application.include_router(input_assistance_router)
    application.include_router(account_router)
    application.include_router(copies_router)
    application.include_router(examples_router)
    application.include_router(profile_router)
    application.include_router(drafts_router)
    application.include_router(tasks_router)
    application.include_router(saved_router)
    application.include_router(imports_router)
    application.include_router(media_router)

    @application.exception_handler(RequestValidationError)
    async def safe_auth_validation(request: Request, exc: RequestValidationError):
        configuration_request = request.url.path.startswith("/api/config")
        if (
            request.url.path.startswith("/api/auth/") or configuration_request
            or request.url.path == "/api/profile"
        ):
            message = (
                "Invalid configuration field" if configuration_request else "Invalid account field"
            )
            return JSONResponse(
                status_code=422,
                content={
                    "detail": [
                        {"loc": error["loc"], "type": error["type"], "msg": message}
                        for error in exc.errors()
                    ]
                },
                headers={"Cache-Control": "no-store"},
            )
        return await request_validation_exception_handler(request, exc)

    application.get("/health", response_model=HealthResponse, tags=["system"])(get_health)
    return application


app = create_app()
