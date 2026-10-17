"""Application-owned time occupancy and location adjacency; no text interpretation."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field

from backend.app.policies.schedule_time import ScheduleTimeError, elapsed_seconds, local_datetime


class ValidationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TimeWindow(ValidationModel):
    root_activity_id: str
    start: datetime
    end: datetime
    source: str


class ScheduleState(ValidationModel):
    windows: tuple[TimeWindow, ...] = ()
    blank_windows: tuple[TimeWindow, ...] = ()
    day_windows: tuple[TimeWindow, ...] = ()
    # Historical IDs remain here so the stage-original spatial baseline uses the same view.
    lineage: dict[str, str] = Field(default_factory=dict)
    fixed: tuple[TimeWindow, ...] = ()
    unresolved_dates: tuple[str, ...] = ()
    classifications: tuple[dict, ...] = ()
    occupied_transfers: tuple[dict, ...] = ()


def subtract(start, end, intervals):
    pieces = [(start, end)]
    for left, right in sorted(intervals):
        updated = []
        for a, b in pieces:
            if right <= a or left >= b:
                updated.append((a, b))
            else:
                if a < left:
                    updated.append((a, left))
                if right < b:
                    updated.append((right, b))
        pieces = updated
    return pieces


def build_schedule(itinerary, contract, places=(), *, primary_generated=False):
    """None means historical/unassessed, never an assertion of no fixed requirements."""
    windows, lineage, classifications, fixed, unresolved = [], {}, [], [], set()
    scheduled_ids = {
        a.source_place_id for d in itinerary.days for a in d.activities if a.source_place_id
    }
    relevant_places = (
        [p for p in places if p.place_id in scheduled_ids] if scheduled_ids else list(places)
    )
    zones = {p.timezone_id for p in relevant_places if p.timezone_id}
    try:
        zone = ZoneInfo(next(iter(zones))) if len(zones) == 1 else None
    except (ValueError, KeyError):
        zone = None
    day_windows = []
    protections = contract.time_protections
    cost_links = {p.field_path: p for p in getattr(itinerary, "cost_projections", ())}
    from backend.app.schemas.itinerary import ItineraryDay

    schedule_days = list(itinerary.days)
    existing_dates = {d.date for d in schedule_days}
    date_cursor = itinerary.start_date
    while date_cursor <= itinerary.end_date:
        if date_cursor not in existing_dates:
            schedule_days.append(ItineraryDay(date=date_cursor, activities=[]))
        date_cursor += timedelta(days=1)
    for day_index, day in enumerate(schedule_days):
        local_ids = {a.source_place_id for a in day.activities if a.source_place_id}
        local_zones = {
            p.timezone_id for p in relevant_places if p.place_id in local_ids and p.timezone_id
        }
        try:
            day_zone = ZoneInfo(next(iter(local_zones))) if len(local_zones) == 1 else zone
        except (ValueError, KeyError):
            day_zone = None
        if day.activities and all(a.start_time.utcoffset() is not None for a in day.activities):
            try:
                if day_zone:
                    midnight = local_datetime(str(day.date), "00:00:00", day_zone.key)
                    next_midnight = local_datetime(
                        str(day.date + timedelta(days=1)), "00:00:00", day_zone.key
                    )
                else:
                    # Historical submitted offsets are retained without claiming IANA evidence.
                    midnight = datetime.combine(
                        day.date, time(), day.activities[0].start_time.tzinfo
                    )
                    next_midnight = midnight + timedelta(days=1)
                day_windows.append(
                    TimeWindow(
                        root_activity_id=f"calendar:{day.date}",
                        start=midnight,
                        end=next_midnight,
                        source="existing_day_calendar_gaps",
                    )
                )
            except ScheduleTimeError:
                unresolved.add(str(day.date))
        relevant = [p for p in protections or () if not p.dates or day.date in p.dates]
        for index, protection in enumerate(relevant):
            if protection.status == "unresolved" or day_zone is None:
                unresolved.add(str(day.date))
                continue
            try:
                fixed.append(
                    TimeWindow(
                        root_activity_id=f"requirement_time_{day.date}_{index}",
                        start=local_datetime(
                            str(day.date),
                            "00:00:00"
                            if protection.full_day
                            else protection.start_time.isoformat(),
                            day_zone.key,
                        ),
                        end=local_datetime(
                            str(day.date + timedelta(days=1)), "00:00:00", day_zone.key
                        )
                        if protection.full_day
                        else local_datetime(
                            str(day.date), protection.end_time.isoformat(), day_zone.key
                        ),
                        source=protection.model_dump_json(),
                    )
                )
            except ScheduleTimeError:
                unresolved.add(str(day.date))
        for activity_index, activity in enumerate(day.activities):
            explicit_free = (
                itinerary.output_version == "itinerary_3" and activity.time_use == "free_window"
            )
            if not explicit_free and activity.activity_kind != "free_time":
                continue
            reason = "generated_locationless_placeholder"
            if not primary_generated or protections is None:
                reason = "time_provenance_unassessed"
            elif str(day.date) in unresolved:
                reason = "scoped_time_requirement_unresolved"
            elif not explicit_free and (
                activity.source_place_id or activity.location or activity.place_name
            ):
                reason = "location_commitment"
            elif not explicit_free and (
                activity.estimated_cost is not None
                or (
                    (
                        projection := cost_links.get(
                            f"days[{day_index}].activities[{activity_index}].estimated_cost"
                        )
                    )
                    is not None
                    and projection.projection not in {"explicit_null", "invalid_set_null"}
                )
            ):
                reason = "cost_obligation"
            elif activity.start_time.utcoffset() is None:
                reason = "time_zone_unavailable"
            if reason == "generated_locationless_placeholder":
                windows.append(
                    TimeWindow(
                        root_activity_id=activity.activity_id,
                        start=activity.start_time,
                        end=activity.end_time,
                        source="primary_generation:activity:" + activity.activity_id,
                    )
                )
                lineage[activity.activity_id] = activity.activity_id
            classifications.append(
                dict(
                    activity_id=activity.activity_id,
                    reason=reason,
                    disposition="elastic_with_fixed_exclusions"
                    if activity.activity_id in lineage
                    else "protected_or_uncertain",
                )
            )
    return ScheduleState(
        windows=tuple(windows),
        day_windows=tuple(day_windows),
        lineage=lineage,
        fixed=tuple(fixed),
        unresolved_dates=tuple(sorted(unresolved)),
        classifications=tuple(classifications),
    )


def ordered_activities(day, schedule=None):
    elastic = schedule.lineage if schedule else {}
    return sorted(
        (a for a in day.activities if a.activity_id not in elastic and a.time_use != "free_window"),
        key=lambda a: a.start_time,
    )


def primary_journey_allowed(left, right):
    """New-wire non-primary activities are barriers, never primary journey endpoints."""
    return all(a.time_use is None for a in (left, right)) or all(
        a.activity_kind == "main_poi" for a in (left, right)
    )


def available_intervals(left, right, schedule=None):
    if left.end_time.utcoffset() is None or right.start_time.utcoffset() is None:
        return []
    blocked = [(w.start, w.end) for w in schedule.fixed] if schedule else []
    return (
        subtract(left.end_time, right.start_time, blocked)
        if right.start_time > left.end_time
        else []
    )


def available_minutes(left, right, schedule=None, *, at_departure=False):
    try:
        gaps = available_intervals(left, right, schedule)
        if at_departure:
            return next((elapsed_seconds(a, b) / 60 for a, b in gaps if a == left.end_time), 0)
        if gaps:
            return max(elapsed_seconds(a, b) / 60 for a, b in gaps)
        return min(0, elapsed_seconds(left.end_time, right.start_time) / 60)
    except (TypeError, ScheduleTimeError):
        return None


def prepare_blank_windows(itinerary, context, policy):
    state = context.schedule
    if state is None:
        return None
    zones = {p.timezone_id for p in context.places if p.timezone_id}
    try:
        zone = ZoneInfo(next(iter(zones))) if len(zones) == 1 else None
    except (ValueError, ZoneInfoNotFoundError):
        zone = None
    windows = []
    unresolved = set(state.unresolved_dates)
    existing = {d.date: d.activities for d in itinerary.days}
    day = itinerary.start_date
    while day <= itinerary.end_date:
        if (
            not existing.get(day)
            and zone
            and context.contract.time_protections is not None
            and str(day) not in state.unresolved_dates
        ):
            try:
                start = local_datetime(
                    str(day), time(policy.blank_day_start_hour).isoformat(), zone.key
                )
                civil_end = datetime.combine(day, time()) + timedelta(
                    hours=policy.blank_day_end_hour
                )
                end = local_datetime(str(civil_end.date()), civil_end.time().isoformat(), zone.key)
                windows.append(
                    TimeWindow(
                        root_activity_id=f"blank:{day}",
                        start=start,
                        end=end,
                        source="application_blank_day_policy",
                    )
                )
            except ScheduleTimeError:
                unresolved.add(str(day))
        day += timedelta(days=1)
    return state.model_copy(
        update={"blank_windows": tuple(windows), "unresolved_dates": tuple(sorted(unresolved))}
    )
