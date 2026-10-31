"""Thin HTTP contracts for Product planning."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.product import ProductPlanResult
from backend.app.schemas.request import PlanningRequest, TravelRequirements

ProductPlanningRequest = PlanningRequest


class CompletedPlanningResponse(ProductPlanResult):
    """A completed product planning result without research metadata."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["completed"] = "completed"


class NeedsClarificationResponse(BaseModel):
    """Extracted requirements that need the user to revise their request."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["needs_clarification"] = "needs_clarification"
    requirements: TravelRequirements
    issues: dict[str, object] = Field(default_factory=dict)


class SafetyBlockedResponse(BaseModel):
    """Supportive, application-authored response; never echoes sensitive issue quotes."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["safety_blocked"] = "safety_blocked"
    requirements: TravelRequirements
    message: str
    action: str


class ProviderBlockedResponse(BaseModel):
    """Provider-filtered input; no domain assessment or sensitive provider details."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["provider_blocked"] = "provider_blocked"
    message: str
    action: str


ProductPlanningResponse = Annotated[
    CompletedPlanningResponse | NeedsClarificationResponse | SafetyBlockedResponse
    | ProviderBlockedResponse,
    Field(discriminator="status"),
]
