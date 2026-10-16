"""Read-only first-draft measurements; no feasibility or repair decisions."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_serializer


class DayGenerationDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    date: date
    day_present: bool
    applicability: Literal["default_full_day", "same_day_remaining_hours_unsupported"]
    count_basis: Literal["canonical_id", "name_proxy"]
    main_activity_count: int
    distinct_main_poi_count: int
    repeated_main_poi_count: int
    generic_activity_count: int
    transport_activity_count: int
    free_time_activity_count: int
    unclassified_activity_count: int
    target_status: Literal["within_target", "below_target", "above_target", "not_assessable"]
    minimum_coverage: Literal["satisfied", "missing", "exempt", "unknown"] = "unknown"
    minimum_coverage_reason: str = "historical_unassessed"
    minimum_coverage_evidence: tuple[str, ...] = ()
    empty_day: bool


class GenerationDiagnostics(BaseModel):
    daily_visit_counts: tuple[dict, ...] | None = None

    @model_serializer(mode="wrap")
    def serialize_assessed_counts(self, handler):
        result = handler(self)
        if self.daily_visit_counts is None:
            result.pop("daily_visit_counts", None)
        return result

    policy_completion: Literal["complete", "incomplete", "unassessed"] = "unassessed"
    policy_issues: tuple[dict, ...] = ()
    goal_progress: tuple[dict, ...] = ()
    model_config = ConfigDict(extra="forbid", frozen=True)

    days: tuple[DayGenerationDiagnostics, ...]
    days_meeting_default_target: int
    days_below_target: int
    days_above_target: int
    days_unassessable: int
    empty_days: int
    days_with_zero_main_pois: int
    scheduled_unique_supply: int | None
    unused_supply: int | None
    cross_day_repeated_visits: int
    related_requirement_ids: tuple[str, ...] = ()
    assessment_basis: Literal["default_target_observation_not_feasibility"] = (
        "default_target_observation_not_feasibility"
    )


class MinimumDailyCoverage(BaseModel):
    """Public product status, without research metadata or user source quotations."""

    date: date
    countable_primary_activities: int
    status: Literal["satisfied", "missing", "exempt", "unknown"]
    reason: str


def public_minimum_coverage(diagnostics):
    return (
        tuple(
            MinimumDailyCoverage(
                date=row.date,
                countable_primary_activities=row.main_activity_count,
                status=row.minimum_coverage,
                reason=row.minimum_coverage_reason,
            )
            for row in diagnostics.days
        )
        if diagnostics
        else ()
    )
