"""Application civil-time conversion, separate from independent evaluation."""

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ScheduleTimeError(ValueError):
    def __init__(self, code, *, activity_id=None):
        self.code, self.activity_id = code, activity_id
        super().__init__(code)

    def as_dict(self):
        return {
            "status": "invalid_model_contract",
            "stage": "schedule_time",
            "code": self.code,
            "activity_ids": [self.activity_id] if self.activity_id else [],
        }


def _zone(name):
    if not name:
        raise ScheduleTimeError("timezone_missing")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ScheduleTimeError("timezone_invalid") from exc


def validate_endpoint(value, zone_name, *, activity_id=None):
    """A known zone must agree with both the civil clock and explicit offset."""
    if value.utcoffset() is None:
        raise ScheduleTimeError("timezone_offset_missing", activity_id=activity_id)
    if zone_name is None:
        return  # Unassessed evidence is not a fabricated destination zone.
    local = value.astimezone(_zone(zone_name))
    if (
        local.replace(tzinfo=None) != value.replace(tzinfo=None)
        or local.utcoffset() != value.utcoffset()
    ):
        raise ScheduleTimeError("timezone_offset_conflict", activity_id=activity_id)


def local_datetime(day, clock, zone_name):
    """Resolve one unambiguous clock; never choose a fold or shift through a gap."""
    try:
        value = datetime.fromisoformat(f"{day}T{clock}")
        if (
            value.tzinfo is not None
            or value.date().isoformat() != day
            or value.time().isoformat() != clock
        ):
            raise ValueError("Non-civil wire timestamp")
    except (ValueError, TypeError) as exc:
        raise ScheduleTimeError("invalid_local_timestamp") from exc
    zone = _zone(zone_name)
    instants = {}
    for fold in (0, 1):
        local = value.replace(tzinfo=zone, fold=fold)
        instant = local.astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None) == value:
            instants[instant] = local
    if len(instants) != 1:
        raise ScheduleTimeError("dst_fold" if instants else "dst_gap")
    selected = next(iter(instants.values()))
    # Domain values use fixed offsets, avoiding same-ZoneInfo wall-clock subtraction.
    return selected.astimezone(timezone(selected.utcoffset()))


def elapsed_seconds(start, end):
    validate_endpoint(start, None)
    validate_endpoint(end, None)
    return (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds()


def elapsed_add(value, seconds, zone_name=None):
    validate_endpoint(value, None)
    instant = value.astimezone(UTC) + timedelta(seconds=seconds)
    local = instant.astimezone(_zone(zone_name) if zone_name else value.tzinfo)
    return local.astimezone(timezone(local.utcoffset()))


class ScheduleTimeContext:
    def __init__(self, places, *, default_zone=None):
        self.zones = {}
        for place in places:
            pid = place.place_id if hasattr(place, "place_id") else place["place_id"]
            zone = (
                place.get("timezone_id")
                if isinstance(place, dict)
                else getattr(place, "timezone_id", None)
            )
            self.zones.setdefault(pid, set()).add(zone)
        known = {z for zs in self.zones.values() for z in zs if z}
        if default_zone:
            known.add(default_zone)
        self.default = next(iter(known)) if len(known) == 1 else None

    def zone_for(self, place_id):
        zones = {z for z in self.zones.get(place_id, ()) if z}
        if len(zones) > 1:
            raise ScheduleTimeError("timezone_evidence_conflict")
        return next(iter(zones)) if zones else self.default
