"""Bounded historical JSON import. Source facts never acquire server authority."""

import asyncio
import hashlib
import json
import math
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from psycopg import Error
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from backend.app.product.auth import CurrentUser
from backend.app.product.database import connect
from backend.app.product.detail import (
    DetailActivity,
    DetailNearby,
    DetailTransfer,
    DetailWeather,
    ProductDetail,
)
from backend.app.product.task_store import TaskStore

MAX_BYTES = 5 * 1024 * 1024
router = APIRouter(prefix="/api/imports", tags=["historical imports"])


class ImportError(ValueError):
    def __init__(self, path, message):
        self.path, self.message = path, message
        super().__init__(f"{path}: {message}")


def fail(path, message):
    raise ImportError(path, message)


def object_at(value, path):
    if not isinstance(value, dict):
        fail(path, "Expected one JSON object")
    return value


def list_at(value, path):
    if not isinstance(value, list):
        fail(path, "Expected an array")
    return value


def text(value, path):
    if not isinstance(value, str) or not value.strip():
        fail(path, "Expected nonblank text")
    return value


def calendar(value, path):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        fail(path, "Expected YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError:
        fail(path, "Invalid calendar date")
    return value


def instant(value, path):
    """Integer nanoseconds; retain original ISO spelling in the detail."""
    if not isinstance(value, str):
        fail(path, "Expected an ISO date and time")
    match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,9}))?)?(Z|[+-]\d{2}:\d{2})?",
        value,
    )
    if not match:
        fail(path, "Expected ISO time with at most nine fractional digits")
    day, hour, minute, second, fraction, zone = match.groups()
    calendar(day, path)
    hour, minute, second = int(hour), int(minute), int(second or 0)
    if hour > 23 or minute > 59 or second > 59:
        fail(path, "Invalid clock time")
    offset = 0
    if zone and zone != "Z":
        zh, zm = int(zone[1:3]), int(zone[4:6])
        if zh > 23 or zm > 59:
            fail(path, "Invalid UTC offset")
        offset = (zh * 60 + zm) * 60 * (1 if zone[0] == "+" else -1)
    seconds = (
        date.fromisoformat(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset
    )
    return seconds * 10**9 + int((fraction or "").ljust(9, "0")), bool(zone)


def interval(start, end, path):
    a, aware_a = instant(start, path + ".start")
    b, aware_b = instant(end, path + ".end")
    if aware_a != aware_b:
        fail(path, "Both endpoints must have the same timezone awareness")
    if b <= a:
        fail(path, "End must be later than start in actual time")


AUTHORITY = {
    "owner",
    "owner_id",
    "user_id",
    "account_id",
    "task_id",
    "source_task_id",
    "operation_key",
    "operation_id",
    "save_key",
    "fingerprint",
    "saved_trip_id",
    "source_preview_id",
    "media_binding",
    "photo_binding",
    "verified_binding",
    "signed_url",
    "photo_token",
    "verified_media",
}


def guard(value, path="$"):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in AUTHORITY:
                fail(
                    path + "." + key,
                    "Artifact cannot declare ownership, operation or media authority",
                )
            guard(item, path + "." + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            guard(item, f"{path}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        fail(path, "Numbers must be finite")
    elif isinstance(value, Decimal) and not value.is_finite():
        fail(path, "Numbers must be finite")
    elif isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            fail(path, "Text must contain valid Unicode characters")


def fields(source, model, exclude=()):
    return {
        key: value
        for key, value in source.items()
        if key in model.model_fields and key not in exclude
    }


def finite_measurement(value, path, *, nonnegative=False):
    """Public measurements must fit the detail/SQL floating-point boundary."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        fail(path, "Expected a finite numeric measurement")
    try:
        representable = math.isfinite(float(value))
    except (OverflowError, ValueError):
        representable = False
    if not representable or (nonnegative and value < 0):
        fail(
            path,
            "Expected a representable finite nonnegative measurement"
            if nonnegative
            else "Expected a representable finite measurement",
        )


def normalize_import(content: str) -> ProductDetail:
    if len(content.encode("utf-8")) > MAX_BYTES:
        fail("$", "JSON must be at most 5 MiB")
    try:
        raw = json.loads(
            content.lstrip("\ufeff"),
            parse_float=Decimal,
            parse_constant=lambda value: fail("$", "Numbers must be finite"),
        )
    except (ValueError, RecursionError) as error:
        if isinstance(error, ImportError):
            raise
        fail("$", "Invalid JSON")
    object_at(raw, "$")
    try:
        guard(raw)
    except RecursionError:
        fail("$", "JSON nesting is too deep")
    if "schema_version" in raw and raw["schema_version"] != "dayloom_export_1":
        fail("$.schema_version", "Unsupported import schema version")
    source = object_at(raw.get("itinerary", raw), "$.itinerary")
    path = "$.itinerary" if "itinerary" in raw else "$"
    if source.get("output_version") not in (None, "itinerary_1", "itinerary_2", "itinerary_3"):
        fail(path + ".output_version", "Unsupported itinerary version")
    destination = text(source.get("destination"), path + ".destination")
    source_days = list_at(source.get("days"), path + ".days")
    if not 1 <= len(source_days) <= 400:
        fail(path + ".days", "Expected 1 to 400 actual days")
    days, nearby, ids, dates = [], [], {}, set()
    for di, day in enumerate(source_days):
        dp = f"{path}.days[{di}]"
        object_at(day, dp)
        day_date = calendar(day.get("date"), dp + ".date")
        if day_date in dates:
            fail(dp + ".date", "Duplicate day")
        dates.add(day_date)
        activities = []
        for ai, activity in enumerate(list_at(day.get("activities"), dp + ".activities")):
            ap = f"{dp}.activities[{ai}]"
            object_at(activity, ap)
            aid = (
                text(activity["activity_id"], ap + ".activity_id")
                if "activity_id" in activity
                else f"import-day-{di}-activity-{ai}"
            )
            if aid in ids:
                fail(ap + ".activity_id", "Duplicate activity ID")
            ids[aid] = day_date
            interval(activity.get("start_time"), activity.get("end_time"), ap)
            if activity["start_time"][:10] != day_date:
                fail(ap + ".start_time", "Start must belong to its actual day")
            values = fields(activity, DetailActivity)
            values.update(
                activity_id=aid,
                title=text(activity.get("title", activity.get("place_name")), ap + ".title"),
            )
            activities.append(values)
            for ni, item in enumerate(list_at(activity.get("nearby", []), ap + ".nearby")):
                item = object_at(item, f"{ap}.nearby[{ni}]")
                nearby.append(
                    {
                        "anchor_activity_id": aid,
                        "associated_day": day_date,
                        **fields(item, DetailNearby),
                    }
                )
        weather = day.get("weather")
        if weather is None and day.get("weather_note") is not None:
            weather = {"summary": day["weather_note"]}
        if weather is not None:
            weather = fields(
                object_at(weather, dp + ".weather"), DetailWeather, ("attribution", "source_url")
            )
            for key, value in weather.items():
                if key != "summary" and value is not None:
                    finite_measurement(value, dp + ".weather." + key)
        days.append({"date": day_date, "activities": activities, "weather": weather})
    start = calendar(
        source["start_date"] if source.get("start_date") is not None else min(dates),
        path + ".start_date",
    )
    end = calendar(
        source["end_date"] if source.get("end_date") is not None else max(dates), path + ".end_date"
    )
    if start > min(dates) or end < max(dates) or start > end:
        fail(path + ".days", "Actual days must lie within the supplied span")
    for key in ("nearby", "reference_recommendations"):
        for ni, item in enumerate(list_at(source.get(key, []), path + "." + key)):
            nearby.append(fields(object_at(item, f"{path}.{key}[{ni}]"), DetailNearby))
    for ni, item in enumerate(nearby):
        text(item.get("place_name"), f"{path}.nearby[{ni}].place_name")
        if item.get("associated_day") is not None:
            calendar(item["associated_day"], f"{path}.nearby[{ni}].associated_day")
    transfers = []
    for ti, transfer in enumerate(list_at(source.get("transfers", []), path + ".transfers")):
        tp = f"{path}.transfers[{ti}]"
        object_at(transfer, tp)
        origin, target = transfer.get("from_activity_id"), transfer.get("to_activity_id")
        if (
            not isinstance(origin, str)
            or not isinstance(target, str)
            or origin == target
            or origin not in ids
            or target not in ids
            or ids[origin] != ids[target]
        ):
            fail(tp, "Transfer endpoints must be distinct existing activities on one day")
        values = fields(
            transfer,
            DetailTransfer,
            ("status", "validation_state", "estimate_kind", "source_status"),
        )
        for key in ("provider_duration_seconds", "distance_meters", "reserve_seconds"):
            value = values.get(key)
            if value is not None:
                finite_measurement(value, tp + "." + key, nonnegative=True)
        for first, last in (
            ("departure_time", "arrival_time"),
            ("preceding_end_time", "following_start_time"),
        ):
            a, b = values.get(first), values.get(last)
            if a is not None:
                instant(a, tp + "." + first)
            if b is not None:
                instant(b, tp + "." + last)
            if a is not None and b is not None:
                interval(a, b, tp)
        values.update(
            status="source_claim",
            estimate_kind=transfer.get("estimate_kind", "unverified"),
            source_status=transfer.get("source_status")
            or transfer.get("validation_state")
            or transfer.get("status"),
        )
        transfers.append(values)
    prototype = object_at(raw["_prototype"], "$._prototype") if "_prototype" in raw else {}
    request = raw.get("request", raw.get("input", prototype.get("input")))
    if request is not None:
        request = object_at(request, "$.request")
        known = {
            key: request[key]
            for key in (
                "destination",
                "start_date",
                "end_date",
                "traveler_count",
                "budget",
                "additional_preferences",
            )
            if key in request
        }
        for alias, canonical in (("people", "traveler_count"), ("activity_budget", "budget")):
            if alias in request and canonical not in known:
                known[canonical] = request[alias]
        if (
            "budget" in known
            and known["budget"] is not None
            and not isinstance(known["budget"], dict)
        ):
            known["budget"] = {"amount": known["budget"], "currency": request.get("currency")}
        for key in ("start_date", "end_date"):
            if known.get(key) is not None:
                calendar(known[key], "$.request." + key)
        if (
            known.get("start_date")
            and known.get("end_date")
            and known["start_date"] > known["end_date"]
        ):
            fail("$.request.end_date", "Request end precedes start")
        count = known.get("traveler_count")
        if count is not None and (type(count) is not int or count < 1):
            fail("$.request.traveler_count", "Expected a positive integer")
        if known.get("destination") is not None:
            text(known["destination"], "$.request.destination")
        original_known = request.get("known_fields")
        if original_known is not None:
            if not isinstance(original_known, list) or any(
                not isinstance(key, str) or key not in known for key in original_known
            ):
                fail("$.request.known_fields", "Invalid known request fields")
            if len(original_known) != len(set(original_known)) or any(
                key not in original_known and value is not None for key, value in known.items()
            ):
                fail("$.request.known_fields", "Known fields cannot hide supplied nonnull facts")
            known = {key: known[key] for key in original_known}
        request = {**known, "known_fields": sorted(known)}
    claims = []
    claim_containers = [("$", raw)]
    for container_path, parent in (("$", raw), (path, source)):
        if parent.get("completion") is not None:
            claim_containers.append(
                (
                    container_path + ".completion",
                    object_at(parent["completion"], container_path + ".completion"),
                )
            )
    for container_path, container in claim_containers:
        if "source_claims" in container:
            supplied = list_at(container["source_claims"], container_path + ".source_claims")
            for index, claim in enumerate(supplied):
                if not isinstance(claim, str):
                    fail(
                        f"{container_path}.source_claims[{index}]", "Expected a source claim string"
                    )
            claims.extend(supplied)
        if isinstance(container, dict):
            for key in (
                "origin",
                "policy_completion",
                "policy_reasons",
                "preference_coverage",
                "minimum_daily_coverage",
            ):
                if key in container:
                    claims.append(
                        key + ": " + json.dumps(container[key], ensure_ascii=False, default=str)
                    )
    try:
        return ProductDetail.model_validate(
            dict(
                id="import",
                title=text(
                    raw.get("title", source.get("title", destination + " journey")), "$.title"
                ),
                destination=destination,
                start_date=start,
                end_date=end,
                description=source.get("description"),
                provenance="imported",
                trust="unverified_import",
                request=request,
                days=days,
                transfers=transfers,
                nearby=nearby,
                completion={"source_claims": list(dict.fromkeys(claims))} if claims else None,
            )
        )
    except ValidationError as error:
        first = error.errors()[0]
        fail("$." + ".".join(map(str, first["loc"])), first["msg"])


class ImportStore:
    def accept(self, owner, key, detail):
        normalized = detail.model_dump(mode="json", exclude={"id"})

        def canonical_money(value):
            if isinstance(value, dict):
                if set(value) == {"amount", "currency"}:
                    number = Decimal(value["amount"])
                    _, digits, exponent = number.as_tuple()
                    coefficient = "".join(map(str, digits)).rstrip("0")
                    value["amount"] = (
                        f"{coefficient}e{exponent + len(digits) - len(coefficient)}"
                        if coefficient
                        else "0"
                    )
                for item in value.values():
                    canonical_money(item)
            elif isinstance(value, list):
                for item in value:
                    canonical_money(item)

        canonical_money(normalized)
        fingerprint = hashlib.sha256(
            json.dumps(
                normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ).hexdigest()
        with connect() as connection:
            connection.execute("SELECT id FROM app.users WHERE id=%s FOR NO KEY UPDATE", (owner,))
            row = connection.execute(
                "SELECT id,fingerprint FROM app.itinerary_previews WHERE owner_id=%s "
                "AND source_kind='imported' AND operation_key=%s FOR UPDATE",
                (owner, key),
            ).fetchone()
            if row:
                if row["fingerprint"] != fingerprint:
                    raise HTTPException(409, {"code": "operation_key_conflict"})
                preview_id = row["id"]
            else:
                preview_id = uuid4()
                detail.id = str(preview_id)
                connection.execute(
                    "INSERT INTO app.itinerary_previews(id,owner_id,source_kind,operation_key,"
                    "fingerprint,snapshot,original_request) "
                    "VALUES (%s,%s,'imported',%s,%s,%s,%s)",
                    (
                        preview_id,
                        owner,
                        key,
                        fingerprint,
                        Jsonb(detail.model_dump(mode="json")),
                        Jsonb(detail.request.model_dump(mode="json")) if detail.request else None,
                    ),
                )
        return TaskStore().previews(owner, preview_id)[0]

    def lookup(self, owner, key):
        with connect() as connection:
            row = connection.execute(
                "SELECT id FROM app.itinerary_previews WHERE owner_id=%s "
                "AND source_kind='imported' AND operation_key=%s",
                (owner, key),
            ).fetchone()
        return TaskStore().previews(owner, row["id"])[0] if row else None


@router.post("")
async def import_preview(request: Request, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    key = request.headers.get("X-Import-Key", "")
    if not 1 <= len(key) <= 120 or not key.strip():
        raise HTTPException(
            422,
            {"code": "invalid_import_key", "message": "Supply X-Import-Key outside the artifact"},
        )
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(
                413,
                {"code": "import_too_large", "path": "$", "message": "JSON must be at most 5 MiB"},
            )
        chunks.append(chunk)
    try:
        detail = await asyncio.to_thread(normalize_import, b"".join(chunks).decode("utf-8-sig"))
        return await asyncio.to_thread(ImportStore().accept, user["id"], key, detail)
    except (ImportError, UnicodeDecodeError) as error:
        raise HTTPException(
            422,
            {
                "code": "invalid_import",
                "path": getattr(error, "path", "$"),
                "message": getattr(error, "message", "Expected UTF-8 JSON"),
            },
        ) from error
    except Error as error:
        raise HTTPException(
            503,
            {
                "code": "import_unconfirmed",
                "message": "Check import status before explicitly retrying with the same key.",
            },
        ) from error


@router.get("/{operation_key}")
def lookup_import(operation_key: str, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    result = ImportStore().lookup(user["id"], operation_key)
    if result is None:
        raise HTTPException(404, {"code": "import_not_found"})
    return result
