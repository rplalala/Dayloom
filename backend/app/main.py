"""FastAPI application entry point."""

from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from backend.app.api.developer.planning import router as developer_planning_router
from backend.app.api.input_assistance import router as input_assistance_router
from backend.app.api.product.planning import router as product_planning_router
from backend.app.product.auth import router as account_router
from backend.app.product.drafts import router as drafts_router
from backend.app.product.examples import router as examples_router
from backend.app.product.profiles import router as profile_router


class HealthResponse(BaseModel):
    """Response returned by the health endpoint."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]


def get_health() -> HealthResponse:
    """Report whether the API process is responsive."""

    return HealthResponse(status="ok")


def create_app() -> FastAPI:
    """Recreate the HTTP application without requiring Product/provider configuration."""
    application = FastAPI(
        title="Reliable Trip Plan Agent",
        description="Backend API for reliable itinerary generation.",
        version="0.1.0",
    )
    application.include_router(product_planning_router)
    application.include_router(developer_planning_router)
    application.include_router(input_assistance_router)
    application.include_router(account_router)
    application.include_router(examples_router)
    application.include_router(profile_router)
    application.include_router(drafts_router)

    @application.exception_handler(RequestValidationError)
    async def safe_auth_validation(request: Request, exc: RequestValidationError):
        if request.url.path.startswith("/api/auth/") or request.url.path == "/api/profile":
            return JSONResponse(
                status_code=422,
                content={
                    "detail": [
                        {"loc": error["loc"], "type": error["type"], "msg": "Invalid account field"}
                        for error in exc.errors()
                    ]
                },
                headers={"Cache-Control": "no-store"},
            )
        return await request_validation_exception_handler(request, exc)

    application.get("/health", response_model=HealthResponse, tags=["system"])(get_health)
    return application


app = create_app()
