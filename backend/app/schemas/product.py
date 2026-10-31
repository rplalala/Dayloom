"""Allowlisted user-facing presentation, separate from research result serialization."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from backend.app.evidence.models import WeatherDayEvidence
from backend.app.schemas.generation_diagnostics import MinimumDailyCoverage
from backend.app.schemas.itinerary import ActivityKind, AtmosphereTheme
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
    activity_kind: ActivityKind = "unknown"
    atmosphere_theme: AtmosphereTheme | None = None
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


class PaceReviewDay(ProductModel):
    date: date
    count: int | None = Field(ge=0)
    target_count: int = Field(ge=0)
    state: Literal["satisfied", "residual", "unavailable", "source_overridden"]


class ExperienceVisit(ProductModel):
    activity_id: str
    date: date
    place_name: str


class RequiredExperienceCoverage(ProductModel):
    planned_visits: tuple[ExperienceVisit, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    requirement: str
    source_quotes: list[str]
    target: int = Field(ge=1)
    scheduled: int = Field(ge=0)
    frequency: Literal["one_off", "minimum", "exact"]
    status: Literal["satisfied", "unmet", "unverified"]
    reason: Literal[
        "supported_visit_coverage", "matching_evidence_incomplete",
        "required_visits_not_scheduled", "no_confirmed_match",
    ]
    basis: Literal["model_semantic_judgment_not_operating_fact"] = (
        "model_semantic_judgment_not_operating_fact"
    )


class AttentionItem(ProductModel):
    title: str
    description: str
    planned_visits: tuple[ExperienceVisit, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )


class PaceReview(ProductModel):
    status: Literal[
        "complete",
        "already_satisfied",
        "partial",
        "unavailable",
        "not_attempted",
        "source_overridden",
    ]
    days: tuple[PaceReviewDay, ...]


class ProductPlanResult(ProductModel):
    _media_bindings: dict[str, str] = PrivateAttr(default_factory=dict)
    attention_items: tuple[AttentionItem, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    preference_coverage: tuple[PreferenceCoverage, ...] = ()
    required_experiences: tuple[RequiredExperienceCoverage, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    policy_completion: Literal["complete", "incomplete", "unassessed"] = "unassessed"
    policy_reasons: tuple[str, ...] = ()
    requirements: TravelRequirements
    itinerary: ProductItinerary
    minimum_daily_coverage: tuple[MinimumDailyCoverage, ...] = ()
    pace_review: PaceReview | None = Field(default=None, exclude_if=lambda value: value is None)
