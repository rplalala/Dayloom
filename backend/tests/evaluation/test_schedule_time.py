"""Independent instant normalization at the public time preparation interface."""

import pytest

from backend.evaluation.schedule_time import expand_protection, normalize_interval


def test_aware_intervals_preserve_precision_and_half_open_endpoints_without_a_zone():
    first = normalize_interval(
        "2020-01-01T09:00:00.000001+00:00",
        "2020-01-01T10:00:00+00:00",
        "2020-01-01",
    )
    second = normalize_interval(
        "2020-01-01T10:00:00+00:00", "2020-01-01T11:00:00+00:00", "2020-01-01"
    )
    assert first.status == second.status == "known"
    assert first.span.end == second.span.start
    assert first.span.seconds == 3599.999999


@pytest.mark.parametrize(
    ("start", "end", "day", "status", "reason"),
    [
        ("2020-01-01T09:00", "2020-01-01T10:00", "2020-01-01", "known", None),
        ("2020-03-29T02:15", "2020-03-29T03:30", "2020-03-29", "unknown", "dst_gap"),
        ("2020-10-25T02:15", "2020-10-25T03:30", "2020-10-25", "unknown", "dst_fold"),
        (
            "2020-01-01T09:00+00:00",
            "2020-01-01T10:00+00:00",
            "2020-01-01",
            "unknown",
            "timezone_offset_conflict",
        ),
    ],
)
def test_localization_uses_independent_zone_and_requires_unique_valid_wall_time(
    start, end, day, status, reason
):
    result = normalize_interval(start, end, day, timezone="Europe/Berlin")
    assert result.status == status
    if reason:
        assert reason in result.reasons
    else:
        assert result.span.start.isoformat() == "2020-01-01T08:00:00+00:00"


@pytest.mark.parametrize(("day", "seconds"), [("2020-03-29", 82800), ("2020-10-25", 90000)])
def test_full_day_protection_uses_next_local_midnight_on_dst_days(day, seconds):
    result = expand_protection(
        {"date": day, "interval": {"kind": "full_day"}}, timezone="Europe/Berlin"
    )
    assert result.status == "known"
    assert result.span.seconds == seconds


@pytest.mark.parametrize(
    ("start", "end", "reason", "consistent"),
    [
        (None, "2020-01-01T10:00Z", "invalid_timestamp", True),
        (
            "2020-01-01T09:00:00.1234567Z",
            "2020-01-01T10:00Z",
            "unsupported_timestamp_precision",
            True,
        ),
        ("2020-01-01T10:00Z", "2020-01-01T09:00Z", "nonpositive_interval", True),
        ("2020-01-01T23:30Z", "2020-01-02T00:30Z", "declared_date_mismatch", False),
        ("2020-01-01T09:00", "2020-01-01T10:00", "timezone_missing", True),
    ],
)
def test_time_missingness_precision_and_overnight_are_explicit(start, end, reason, consistent):
    result = normalize_interval(start, end, "2020-01-01")
    assert result.span is None
    assert result.reasons == (reason,)
    assert result.date_consistent is consistent
    assert result.original_start == start


def test_dst_duration_uses_elapsed_instants():
    result = normalize_interval(
        "2020-03-29T01:30:00+01:00", "2020-03-29T03:30:00+02:00", "2020-03-29", "Europe/Berlin"
    )
    assert result.span.seconds == 3600


@pytest.mark.parametrize(
    ("day", "offset", "status", "reasons"),
    [
        ("2026-10-24", "+01:00", "known", ()),
        ("2026-10-25", "+01:00", "unknown", ("timezone_offset_conflict",)),
        ("2026-10-25", "+00:00", "known", ()),
    ],
)
def test_london_fall_back_keeps_date_membership_without_repairing_offsets(
    day, offset, status, reasons
):
    start, end = f"{day}T10:00:00{offset}", f"{day}T11:30:00{offset}"
    interval = normalize_interval(start, end, day, "Europe/London")
    assert interval.status == status
    assert interval.reasons == reasons
    assert interval.date_consistent is True
    assert interval.original_start == start
    assert interval.original_end == end


def test_cross_date_is_opt_in_and_never_repairs_a_reversed_same_date():
    args = ("2020-01-01T23:30Z", "2020-01-02T00:30Z", "2020-01-01")
    assert normalize_interval(*args).reasons == ("declared_date_mismatch",)
    assert normalize_interval(*args, allow_cross_date=True).span.seconds == 3600
    reversed_clock = normalize_interval(
        "2020-01-01T23:30Z", "2020-01-01T00:30Z", "2020-01-01", allow_cross_date=True
    )
    assert reversed_clock.reasons == ("nonpositive_interval",)
