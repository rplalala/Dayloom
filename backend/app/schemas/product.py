"""Allowlisted user-facing presentation, separate from research result serialization."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.evidence.models import WeatherDayEvidence
from backend.app.schemas.generation_diagnostics import MinimumDailyCoverage
from backend.app.schemas.request import Money, TravelRequirements


class ProductModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductWeather(ProductModel):
    status: Literal["available", "unavailable"]
    forecast: WeatherDayEvidence | None = None
    attribution: str | None = None
    source_url: str | None = None


class ProductNearby(ProductModel):
    place_name: str
    reason: str
    associated_day: date
    anchor_activity_id: str
    area: str | None = None
    uncertainty: str | None = None
    attribution: str | None = None


class ProductActivity(ProductModel):
    activity_id: str
    time_use: Literal["scheduled", "free_window"] | None = None
    title: str
    place_name: str | None
    location: str | None
    start_time: datetime
    end_time: datetime
    estimated_cost: Money | None
    notes: str | None
    introduction: str | None = None
    nearby: list[ProductNearby] = Field(default_factory=list)


class ProductDay(ProductModel):
    date: date
    activities: list[ProductActivity]
    weather: ProductWeather


class ProductTransfer(ProductModel):
    from_activity_id: str
    to_activity_id: str
    preceding_end_time: datetime
    following_start_time: datetime
    mode: Literal["WALK", "TRANSIT", "DRIVE"] | None
    provider_duration_seconds: float | None
    distance_meters: int | None
    reserve_seconds: float
    validation_state: Literal["PASS", "CONFIRMED", "UNKNOWN"]
    unknowns: list[str]
    estimate_kind: Literal["provider", "derived", "unverified"]
    attribution: str | None = None


class ProductItinerary(ProductModel):
    destination: str
    start_date: date
    end_date: date
    days: list[ProductDay]
    transfers: list[ProductTransfer] = Field(default_factory=list)


class PreferenceCoverage(ProductModel):
    preference: str
    target: Literal[1, 2]
    scheduled: int
    remaining: int
    status: Literal["covered", "gap", "unassessed"]
    target_origin: Literal["ordinary_preference", "current_trip_focus"]
    basis: Literal["model_semantic_judgment_not_operating_fact"] = (
        "model_semantic_judgment_not_operating_fact"
    )


class ProductPlanResult(ProductModel):
    preference_coverage: tuple[PreferenceCoverage, ...] = ()
    policy_completion: Literal["complete", "incomplete", "unassessed"] = "unassessed"
    policy_reasons: tuple[str, ...] = ()
    requirements: TravelRequirements
    itinerary: ProductItinerary
    minimum_daily_coverage: tuple[MinimumDailyCoverage, ...] = ()
