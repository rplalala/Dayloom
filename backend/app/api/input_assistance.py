"""Separate application endpoints for optional planning input assistance."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from backend.app.integrations.geodb.client import (
    DestinationSuggestion,
    GeoDBClient,
    GeoDBInvalidResponse,
    GeoDBThrottled,
    GeoDBTimeout,
    GeoDBUnavailable,
)
from backend.app.llm.azure_foundry.polishing import (
    PolishProviderBlocked,
    PolishProviderInvalidResponse,
    PolishProviderThrottled,
    PolishProviderUnavailable,
    create_foundry_polisher,
)
from backend.app.product.auth import COOKIE, authenticated_account
from backend.app.runtime.config_loader import load_product_runtime_config
from backend.app.schemas.input_assistance import PolishRequest, PolishResponse
from backend.app.services.destination_suggestions import (
    DestinationRateLimited,
    DestinationSuggestionService,
)
from backend.app.services.preference_polishing import (
    PolishingDeadline,
    PolishingInputLimit,
    PolishingInvalidResponse,
    PolishingRateLimited,
    PolishingUnavailable,
    PreferencePolishingService,
)

router = APIRouter(prefix="/api/input-assistance", tags=["input-assistance"])


def assistance_actor(request: Request) -> str:
    """Use verified accounts, or the direct client address for public guest assistance."""
    if request.cookies.get(COOKIE) or request.headers.get("authorization"):
        try:
            return f"user:{authenticated_account(request)['id']}"
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
    return f"guest:{request.client.host if request.client else 'unknown'}"


AssistanceActor = Annotated[str, Depends(assistance_actor)]


class DestinationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = "geodb"
    suggestions: list[DestinationSuggestion]


def assistance_error(
    status_code: int,
    code: str,
    message: str,
    *,
    retry_after: int | None = None,
    client_revision: str | None = None,
):
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    content = {"error": {"code": code, "message": message}}
    if client_revision is not None:
        content["client_revision"] = client_revision
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers,
    )


@lru_cache
def get_destination_service() -> DestinationSuggestionService:
    config = load_product_runtime_config().input_assistance.destination
    return DestinationSuggestionService(GeoDBClient(), config)


@router.get("/destinations", response_model=DestinationResponse)
async def get_destinations(
    service: Annotated[DestinationSuggestionService, Depends(get_destination_service)],
    actor: AssistanceActor,
    q: Annotated[str | None, Query()] = None,
):
    prefix = q.strip() if q is not None else ""
    if not service.accepts(prefix):
        return assistance_error(422, "invalid_prefix", "Enter 2 to 100 destination characters.")
    try:
        choices = await service.suggest(prefix, actor=actor)
    except DestinationRateLimited:
        return assistance_error(
            429,
            "destination_rate_limited",
            "Destination suggestions are temporarily limited.",
            retry_after=2,
        )
    except GeoDBThrottled:
        return assistance_error(
            429, "destination_provider_limited", "Destination suggestions are temporarily limited."
        )
    except GeoDBTimeout:
        return assistance_error(504, "destination_timeout", "Destination suggestions timed out.")
    except GeoDBInvalidResponse:
        return assistance_error(
            502, "destination_invalid_response", "Destination suggestions are unavailable."
        )
    except GeoDBUnavailable:
        return assistance_error(
            503, "destination_unavailable", "Destination suggestions are unavailable."
        )
    return DestinationResponse(suggestions=choices)


@lru_cache
def get_polishing_service() -> PreferencePolishingService:
    config = load_product_runtime_config().input_assistance.polishing
    return PreferencePolishingService(create_foundry_polisher, config)


@router.post("/preferences/polish", response_model=PolishResponse)
async def polish_preferences(
    body: dict,
    service: Annotated[PreferencePolishingService, Depends(get_polishing_service)],
    actor: AssistanceActor,
):
    revision = body.get("client_revision")
    revision = revision if isinstance(revision, str) and len(revision) <= 100 else None
    try:
        request = PolishRequest.model_validate(body)
        return await service.polish(request, actor=actor)
    except PydanticValidationError:
        return assistance_error(
            422, "invalid_polish_input", "Review the preference input.", client_revision=revision
        )
    except PolishingInputLimit:
        return assistance_error(
            422,
            "polish_input_limit",
            "Preference text exceeds the polish limit.",
            client_revision=revision,
        )
    except PolishingRateLimited:
        return assistance_error(
            429,
            "polish_rate_limited",
            "Preference polishing is temporarily limited.",
            retry_after=2,
            client_revision=revision,
        )
    except PolishProviderThrottled:
        return assistance_error(
            429,
            "polish_provider_limited",
            "Preference polishing is temporarily limited.",
            client_revision=revision,
        )
    except PolishProviderBlocked:
        return assistance_error(
            422,
            "polishing_blocked",
            "The provider could not process this text.",
            client_revision=revision,
        )
    except PolishingDeadline:
        return assistance_error(
            504, "polish_timeout", "Preference polishing timed out.", client_revision=revision
        )
    except (PolishingInvalidResponse, PolishProviderInvalidResponse):
        return assistance_error(
            502, "polish_invalid_response", "Preference polishing returned an invalid result.",
            client_revision=revision,
        )
    except (PolishingUnavailable, PolishProviderUnavailable):
        return assistance_error(
            503,
            "polish_unavailable",
            "Preference polishing is unavailable.",
            client_revision=revision,
        )
