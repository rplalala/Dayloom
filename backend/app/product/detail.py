"""Lossless Product detail contract, independent of generation input validation.

Dates and ISO clocks retain their supplied spelling and offset. Missing request
information stays absent; this representation never reconstructs a planning brief.
"""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from backend.app.schemas.generation_diagnostics import MinimumDailyCoverage
from backend.app.schemas.product import PreferenceCoverage
from backend.app.schemas.request import Money


def _date(value: str) -> str:
    date.fromisoformat(value)
    return value


def _clock(value: str) -> str:
    if "T" not in value:
        raise ValueError("An ISO date and time is required")
    datetime.fromisoformat(value)
    return value


ISODate = Annotated[str, AfterValidator(_date)]
ISOClock = Annotated[str, AfterValidator(_clock)]


class DetailModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DetailRequest(DetailModel):
    known_fields: list[str] | None = None
    destination: str | None = None
    start_date: ISODate | None = None
    end_date: ISODate | None = None
    traveler_count: int | None = None
    budget: Money | None = None
    additional_preferences: str | None = None


class DetailNearby(DetailModel):
    place_name: str
    anchor_activity_id: str | None = None
    associated_day: ISODate | None = None
    reason: str | None = None
    area: str | None = None
    uncertainty: str | None = None
    attribution: str | None = None


class DetailWeather(DetailModel):
    summary: str | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    precipitation_probability_percent: float | None = None
    max_wind_speed_kph: float | None = None
    attribution: str | None = None
    source_url: str | None = None


class DetailActivity(DetailModel):
    activity_id: str
    title: str
    time_use: Literal["scheduled", "free_window"] = "scheduled"
    place_name: str | None = None
    location: str | None = None
    category: str | None = None
    start_time: ISOClock
    end_time: ISOClock
    estimated_cost: Money | None = None
    notes: str | None = None
    introduction: str | None = None


class DetailDay(DetailModel):
    date: ISODate
    activities: list[DetailActivity] = Field(default_factory=list)
    weather: DetailWeather | None = None


class DetailTransfer(DetailModel):
    from_activity_id: str
    to_activity_id: str
    departure_time: ISOClock | None = None
    arrival_time: ISOClock | None = None
    preceding_end_time: ISOClock | None = None
    following_start_time: ISOClock | None = None
    mode: str | None = None
    provider_duration_seconds: float | None = None
    distance_meters: float | None = None
    reserve_seconds: float | None = None
    estimate_kind: Literal["provider", "derived", "unverified"] = "unverified"
    status: Literal["confirmed", "unknown", "source_claim"] = "unknown"
    validation_state: Literal["PASS", "CONFIRMED", "UNKNOWN"] | None = None
    source_status: str | None = None
    unknowns: list[str] = Field(default_factory=list)
    attribution: str | None = None


class DetailCompletion(DetailModel):
    source_claims: list[str] = Field(default_factory=list)
    policy_completion: Literal["complete", "incomplete", "unassessed"] = "unassessed"
    policy_reasons: list[str] = Field(default_factory=list)
    preference_coverage: list[PreferenceCoverage] = Field(default_factory=list)
    minimum_daily_coverage: list[MinimumDailyCoverage] = Field(default_factory=list)


class ProductDetail(DetailModel):
    schema_version: Literal["product_detail_1"] = "product_detail_1"
    id: str
    title: str
    destination: str
    start_date: ISODate | None = None
    end_date: ISODate | None = None
    description: str | None = None
    provenance: Literal["example", "generated", "imported"]
    trust: Literal["source_fixture", "generated_projection", "unverified_import"]
    request: DetailRequest | None = None
    days: list[DetailDay] = Field(default_factory=list)
    transfers: list[DetailTransfer] = Field(default_factory=list)
    nearby: list[DetailNearby] = Field(default_factory=list)
    completion: DetailCompletion | None = None


class ExampleCard(DetailModel):
    id: str
    title: str
    destination: str
    start_date: ISODate | None
    end_date: ISODate | None
    day_count: int
    description: str | None
