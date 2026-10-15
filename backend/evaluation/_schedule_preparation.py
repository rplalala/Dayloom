"""Neutral validation of reviewed source obligations and occupancy correspondence."""

import re
from datetime import date, timedelta

from .preparation import _review_provenance
from .records import require, text
from .schedule_time import expand_protection

OBLIGATION_FIELDS = {
    "transport_modes": {"allowed_modes", "scope"},
    "required_visit": {"subject_ref", "count", "distinct_dates", "date_obligations"},
    "excluded_visit": {"subject_ref", "scope", "dates"},
    "protected_time": {"date", "interval", "scope"},
    "fixed_visit_time": {"subject_ref", "date", "match", "conditions", "repeat_permission_refs"},
}


def _days(original):
    first = date.fromisoformat(original["start_date"])
    last = date.fromisoformat(original["end_date"])
    return [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]


def _positive(value):
    return type(value) is int and value > 0


def _sources(refs, original, pointer):
    require(isinstance(refs, list) and bool(refs), pointer, "Nonempty original sources required")
    for ref in refs:
        require(isinstance(ref, dict) and text(ref.get("field_path")), pointer, "Invalid source")
        field = ref["field_path"]
        require(field in original, pointer, "Unknown original field")
        if "quote" in ref:
            quote, value, occurrence = ref["quote"], original[field], ref.get("occurrence", 0)
            require(
                text(quote)
                and isinstance(value, str)
                and type(occurrence) is int
                and occurrence >= 0,
                pointer,
                "Invalid quote",
            )
            positions, offset = [], 0
            while (offset := value.find(quote, offset)) >= 0:
                positions.append(offset)
                offset += len(quote)
            require(occurrence < len(positions), pointer, "Absent quote occurrence")
            if "offset_start" in ref or "offset_end" in ref:
                require(
                    type(ref.get("offset_start")) is int
                    and type(ref.get("offset_end")) is int
                    and ref["offset_start"] == positions[occurrence]
                    and ref["offset_end"] == positions[occurrence] + len(quote),
                    pointer,
                    "Invalid Unicode quote offsets",
                )
        else:
            require(
                "offset_start" not in ref and "offset_end" not in ref,
                pointer,
                "Offsets require a quote",
            )


def _clock(value, pointer, *, end=False):
    require(
        isinstance(value, str) and re.fullmatch(r"[0-9]{2}:[0-9]{2}(?::[0-9]{2})?", value),
        pointer,
        "Expected HH:MM[:SS]",
    )
    parts = [int(part) for part in value.split(":")]
    hour, minute, second = *parts[:2], parts[2] if len(parts) == 3 else 0
    require(
        0 <= minute < 60
        and 0 <= second < 60
        and (0 <= hour < 24 or end and hour == 24 and minute == second == 0),
        pointer,
        "Invalid local clock",
    )
    return hour * 3600 + minute * 60 + second


def _window(value, pointer):
    require(isinstance(value, dict) and set(value) == {"start", "end"}, pointer, "Invalid window")
    start = _clock(value["start"], pointer)
    end = _clock(value["end"], pointer, end=True)
    require(start < end, pointer, "Clock window must increase within one day")
    return start, end


def _validate_spec(group):
    spec, original = group["requirement_spec"], group["input"]
    days = set(_days(original))
    subjects = {item["subject_id"] for item in spec["subjects"]}
    totals, dated, exclusions, distinct, single_times = {}, {}, {}, {}, {}
    incomplete = False
    ids = {item["obligation_id"] for item in spec["obligations"]}
    for item in spec["obligations"]:
        oid, kind = item["obligation_id"], item["kind"]
        _sources(item["source_refs"], original, oid)
        if item["resolution"] != "resolved":
            require(text(item.get("reason")), oid, "Unresolved semantics require a reason")
            incomplete |= kind not in OBLIGATION_FIELDS
            continue
        require(
            kind in OBLIGATION_FIELDS,
            oid,
            "Unsupported executable obligation kind",
        )
        require(
            set(item)
            <= {"obligation_id", "kind", "resolution", "source_refs", "reason"}
            | OBLIGATION_FIELDS[kind],
            oid,
            "Unknown executable fields",
        )
        if kind not in ("protected_time", "transport_modes"):
            require(
                text(item.get("subject_ref")) and item["subject_ref"] in subjects,
                oid,
                "Unknown requirement subject",
            )
        if kind in ("protected_time", "fixed_visit_time"):
            require(
                text(item.get("date")) and item["date"] in days,
                oid,
                "Obligation date outside requested dates",
            )
        if kind == "transport_modes":
            modes = item.get("allowed_modes")
            require(
                item.get("scope") == "whole_trip"
                and isinstance(modes, list)
                and bool(modes)
                and all(isinstance(m, str) and m in {"WALK", "TRANSIT", "DRIVE"} for m in modes)
                and len(set(modes)) == len(modes),
                oid,
                "Invalid transport mode restriction",
            )
            continue
        if kind == "required_visit":
            count = item.get("count")
            require(
                isinstance(count, dict)
                and set(count) == {"mode", "value"}
                and count["mode"] in ("minimum", "exact")
                and _positive(count["value"]),
                oid,
                "Invalid count",
            )
            require(type(item.get("distinct_dates", False)) is bool, oid, "Invalid distinct_dates")
            if item.get("distinct_dates"):
                require(count["value"] <= len(days), oid, "Impossible distinct-date count")
                distinct[item["subject_ref"]] = max(
                    distinct.get(item["subject_ref"], 0), count["value"]
                )
            total = (count["value"], count["value"] if count["mode"] == "exact" else None)
            totals.setdefault(item["subject_ref"], []).append(total)
            dates = item.get("date_obligations", [])
            require(isinstance(dates, list), oid, "Invalid date obligations")
            seen = set()
            for entry in dates:
                require(
                    isinstance(entry, dict)
                    and set(entry) == {"date", "count_mode", "count"}
                    and text(entry["date"])
                    and entry["date"] in days
                    and entry["date"] not in seen
                    and entry["count_mode"] in ("minimum", "exact")
                    and _positive(entry["count"]),
                    oid,
                    "Invalid/duplicate dated count",
                )
                seen.add(entry["date"])
                dated.setdefault((item["subject_ref"], entry["date"]), []).append(
                    (entry["count"], entry["count"] if entry["count_mode"] == "exact" else None)
                )
        elif kind == "excluded_visit":
            require(item.get("scope") in ("whole_trip", "specified_dates"), oid, "Invalid scope")
            if item["scope"] == "whole_trip":
                require("dates" not in item, oid, "Whole-trip exclusion cannot supply dates")
                excluded = days
            else:
                values = item.get("dates")
                require(
                    isinstance(values, list)
                    and bool(values)
                    and all(text(d) and d in days for d in values)
                    and len(set(values)) == len(values),
                    oid,
                    "Invalid excluded dates",
                )
                excluded = set(values)
            exclusions.setdefault(item["subject_ref"], set()).update(excluded)
        elif kind == "protected_time":
            require(
                item.get("scope") in ("primary_visits", "scheduled_commitments"),
                oid,
                "Invalid protected scope",
            )
            interval = item.get("interval")
            require(isinstance(interval, dict), oid, "Invalid protection interval")
            if interval.get("kind") == "full_day":
                require(set(interval) == {"kind"}, oid, "Unexpected full-day operators")
            else:
                require(
                    interval.get("kind") == "clock" and set(interval) == {"kind", "start", "end"},
                    oid,
                    "Invalid protection operator",
                )
                _window({key: interval[key] for key in ("start", "end")}, oid)
        else:
            require(
                item.get("match") in ("single_visit", "at_least_one"), oid, "Invalid time selector"
            )
            if item["match"] == "at_least_one":
                _sources(item.get("repeat_permission_refs"), original, oid)
                totals.setdefault(item["subject_ref"], []).append((1, None))
                dated.setdefault((item["subject_ref"], item["date"]), []).append((1, None))
            else:
                require(
                    "repeat_permission_refs" not in item,
                    oid,
                    "Single visit cannot permit repetition",
                )
                totals.setdefault(item["subject_ref"], []).append((1, 1))
                dated.setdefault((item["subject_ref"], item["date"]), []).append((1, None))
            conditions = item.get("conditions")
            require(
                isinstance(conditions, dict)
                and bool(conditions)
                and set(conditions) <= {"start_at", "within", "duration"},
                oid,
                "Invalid conditions",
            )
            start = _clock(conditions["start_at"], oid) if "start_at" in conditions else None
            window = _window(conditions["within"], oid) if "within" in conditions else None
            if "duration" in conditions:
                duration = conditions["duration"]
                require(
                    isinstance(duration, dict)
                    and set(duration) == {"mode", "seconds"}
                    and duration["mode"] in ("minimum", "exact")
                    and _positive(duration["seconds"]),
                    oid,
                    "Invalid duration",
                )
            require(
                start is None or window is None or window[0] <= start < window[1],
                oid,
                "Impossible time conjunction",
            )
            if item["match"] == "single_visit":
                single_times.setdefault((item["subject_ref"], item["date"]), []).append(conditions)
    for subject, ranges in totals.items():
        lower = max(low for low, _ in ranges)
        uppers = [high for _, high in ranges if high is not None]
        upper = min(uppers) if uppers else None
        minima, forced_dates, eligible_dates, date_maxima = 0, 0, 0, []
        for day in days:
            entries = dated.get((subject, day), [])
            lo = max((low for low, _ in entries), default=0)
            hi = [high for _, high in entries if high is not None]
            if day in exclusions.get(subject, set()):
                hi.append(0)
            require(not hi or lo <= min(hi), subject, "Contradictory dated requirements")
            minima += lo
            forced_dates += int(lo > 0)
            eligible_dates += int(not hi or min(hi) > 0)
            date_maxima.append(min(hi) if hi else None)
        require(upper is None or max(lower, minima) <= upper, subject, "Contradictory visit quotas")
        require(
            any(high is None for high in date_maxima) or lower <= sum(date_maxima),
            subject,
            "Dated exact counts cannot meet global minimum",
        )
        max_distinct = (
            eligible_dates if upper is None else min(eligible_dates, upper - minima + forced_dates)
        )
        require(
            distinct.get(subject, 0) <= max_distinct, subject, "Contradictory distinct-date quota"
        )
        require(
            exclusions.get(subject, set()) != days,
            subject,
            "Required visit excluded from whole trip",
        )
    for (subject, _), conditions in single_times.items():
        starts = {_clock(c["start_at"], subject) for c in conditions if "start_at" in c}
        windows = [_window(c["within"], subject) for c in conditions if "within" in c]
        exact = {
            c["duration"]["seconds"]
            for c in conditions
            if c.get("duration", {}).get("mode") == "exact"
        }
        minimum = max((c["duration"]["seconds"] for c in conditions if "duration" in c), default=0)
        require(
            len(starts) <= 1 and len(exact) <= 1 and (not exact or next(iter(exact)) >= minimum),
            subject,
            "Contradictory single-visit time conditions",
        )
        if windows:
            low, high = max(w[0] for w in windows), min(w[1] for w in windows)
            require(
                low < high and (not starts or low <= next(iter(starts)) < high),
                subject,
                "Disjoint single-visit time windows",
            )
    for item in spec["obligations"]:
        if (
            item["resolution"] == "resolved"
            and item["kind"] == "fixed_visit_time"
            and item["match"] == "at_least_one"
        ):
            require(
                not any(high == 1 for _, high in totals.get(item["subject_ref"], [])),
                item["obligation_id"],
                "Repeat selector conflicts with exact-one quota",
            )
    seen = set()
    for item in spec["unresolved_items"]:
        require(
            isinstance(item, dict)
            and text(item.get("item_id"))
            and item["item_id"] not in seen
            and text(item.get("reason")),
            "unresolved_items",
            "Invalid annotation",
        )
        seen.add(item["item_id"])
        _sources(item.get("source_refs"), original, item["item_id"])
        require(
            "classification" not in item or item["classification"] == "soft_preference",
            item["item_id"],
            "Unknown annotation classification",
        )
        require(
            "obligation_ref" not in item
            or text(item["obligation_ref"])
            and item["obligation_ref"] in ids,
            item["item_id"],
            "Unknown annotation parent",
        )
        require(
            not ("obligation_ref" in item and "classification" in item),
            item["item_id"],
            "Annotation has contradictory linkage",
        )
        incomplete |= "obligation_ref" not in item and "classification" not in item
    return incomplete


def _validate_time_capacity(group, timezone):
    if timezone is None:
        return
    combined = {}
    for item in group["requirement_spec"]["obligations"]:
        if item["resolution"] != "resolved" or item["kind"] != "fixed_visit_time":
            continue
        key = (
            (item["subject_ref"], item["date"])
            if item["match"] == "single_visit"
            else (item["obligation_id"], item["date"])
        )
        combined.setdefault(key, []).append(item["conditions"])
    for (subject, day), conditions in combined.items():
        windows = [condition["within"] for condition in conditions if "within" in condition]
        durations = [
            condition["duration"]["seconds"] for condition in conditions if "duration" in condition
        ]
        if not durations:
            continue
        if not windows:
            windows = [{"start": "00:00", "end": "24:00"}]
        low = max((_clock(w["start"], subject), w["start"]) for w in windows)[1]
        high = min((_clock(w["end"], subject, end=True), w["end"]) for w in windows)[1]
        starts = [condition["start_at"] for condition in conditions if "start_at" in condition]
        interval = expand_protection(
            {
                "date": day,
                "interval": {"kind": "clock", "start": starts[0] if starts else low, "end": high},
            },
            timezone,
        )
        if interval.span:
            require(
                max(durations) <= interval.span.seconds,
                subject,
                "Impossible elapsed duration within window",
            )


def _occupancy_reviews(intake, envelope):
    if envelope is None:
        return []
    require(
        isinstance(envelope, dict)
        and envelope.get("schema_version") == "rtpeval_occupancy_reviews_1"
        and envelope.get("batch_id") == intake["batch_id"]
        and text(envelope.get("revision"))
        and isinstance(envelope.get("records"), list),
        "occupancy_reviews",
        "Invalid review envelope",
    )
    sources = {}
    for group in intake["inventory"]:
        for run in group["runs"].values():
            projections = [run["final"], *(p for p in run.get("optional", {}).values() if p)]
            for projection in projections:
                for activity in projection["activities"]:
                    sources[activity["source"]["record_id"]] = (activity, group)
    seen = set()
    allowed = {
        "source",
        "revision",
        "reviewer_ref",
        "reviewed_at",
        "rationale",
        "occupancy",
        "protected_obligation_refs",
    }
    for item in envelope["records"]:
        require(
            isinstance(item, dict)
            and set(item) <= allowed
            and isinstance(item.get("source"), dict),
            "occupancy_reviews",
            "Review may only decide occupancy and correspondence",
        )
        source = item["source"]
        key = source.get("record_id")
        require(
            text(key)
            and key in sources
            and key not in seen
            and source == sources[key][0]["source"],
            "occupancy_reviews",
            "Stale/duplicate activity source",
        )
        seen.add(key)
        activity, group = sources[key]
        require(
            text(item.get("revision")) and text(item.get("rationale")),
            key,
            "Review identity/rationale missing",
        )
        _review_provenance(item, key)
        require(
            item.get("occupancy") in ("committed", "uncommitted", "unresolved"),
            key,
            "Invalid occupancy",
        )
        require(
            activity["evaluation_role"] != "transport",
            key,
            "Transport cannot receive occupancy reviews",
        )
        if activity["evaluation_role"] == "primary_visit":
            require(item["occupancy"] == "committed", key, "Primary visits remain commitments")
        refs = item.get("protected_obligation_refs", [])
        require(
            isinstance(refs, list)
            and all(text(ref) for ref in refs)
            and len(set(refs)) == len(refs),
            key,
            "Invalid protection links",
        )
        if refs:
            protections = {
                p["obligation_id"]: p
                for p in group["requirement_spec"]["obligations"]
                if p["kind"] == "protected_time"
            }
            require(
                activity["evaluation_role"] == "transition"
                and item["occupancy"] == "uncommitted"
                and all(ref in protections for ref in refs),
                key,
                "Contradictory protection correspondence",
            )
            linked = [protections[ref] for ref in refs]
            require(
                all(
                    p.get("date", activity["declared_day"]) == activity["declared_day"]
                    for p in linked
                )
                and len({p.get("scope") for p in linked}) == 1,
                key,
                "Protection links require same date/scope",
            )
    return envelope["records"]
