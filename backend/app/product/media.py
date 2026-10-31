"""Fresh fixed-provider display metadata; no photo archive or URL fetch proxy."""

import asyncio
import re
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AliasChoices, Field, SecretStr, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.observability.product_logs import operation
from backend.app.observability.usage import install_http_hooks
from backend.app.product.auth import CurrentUser
from backend.app.product.database import connect
from backend.app.product.examples import example_detail
from backend.app.runtime.database import PROJECT_ROOT

router = APIRouter(tags=["Product media"])
MAX_PLACE_PHOTOS = 12
CURATED = {
    "sydney": ("7Zb7kUyQg1E", "Daylight view across Sydney Harbour toward the Opera House"),
    "nature": ("78A265wPiO4", "Sunlight crossing green mountain ridges"),
}
ATMOSPHERE_QUERIES = {
    "meal": "relaxed meal",
    "rest": "peaceful rest",
    "explore": "neighborhood exploration",
    "walk": "scenic walk",
    "general": "travel moments",
}


class MediaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRODUCT_",
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )
    google_places_media_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="GOOGLE_MAPS_API_KEY",
    )
    unsplash_access_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("PRODUCT_UNSPLASH_ACCESS_KEY", "UNSPLASH_API_KEY"),
    )


def safe_url(value, host, *, subdomains=False):
    if not isinstance(value, str) or len(value) > 4096:
        return None
    try:
        parsed = urlsplit(value)
        matches = parsed.hostname == host or (
            subdomains and (parsed.hostname or "").endswith("." + host)
        )
        if (
            parsed.scheme == "https"
            and matches
            and parsed.port in {None, 443}
            and not parsed.username
            and not parsed.password
            and not parsed.fragment
        ):
            return value
    except ValueError:
        pass
    return None


def unavailable(*, provider=None, reason=None):
    if reason:
        operation("media_unavailable", {"provider": provider, "reason": reason})
    return {"status": "unavailable"}


def unsplash_photo(data, width, height, alt):
    image = safe_url(data["urls"]["raw"], "images.unsplash.com")
    user = data["user"]
    profile = safe_url(user["links"]["html"], "unsplash.com")
    page = safe_url(data["links"]["html"], "unsplash.com")
    author = user["name"]
    if not image or not profile or not page or not isinstance(author, str) or not author.strip():
        raise ValueError("Invalid Unsplash metadata")
    parsed = urlsplit(image)
    parameters = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"w", "h", "dpr", "fit", "auto"}
    ]
    parameters.extend([("w", str(width)), ("h", str(height)), ("fit", "max"), ("auto", "format")])
    referral = "utm_source=dayloom&utm_medium=referral"
    return {
        "status": "available",
        "kind": "atmosphere",
        "provider": "Unsplash",
        "image_url": urlunsplit(parsed._replace(query=urlencode(parameters))),
        "authors": [
            {"name": author[:500], "url": profile + ("&" if "?" in profile else "?") + referral}
        ],
        "source_url": page + ("&" if "?" in page else "?") + referral,
        "alt": alt,
    }


class MediaProviders:
    """Google lookup, fixed covers and first-result search; no retries or server cache.

    HTTP transport is the external acceptance seam. Redirects are never followed and
    response bodies, dimensions, parallelism and the total display batch are bounded.
    """

    def __init__(self, *, google_key="", unsplash_key="", transport=None):
        self.google_key, self.unsplash_key = google_key, unsplash_key
        self.transport = transport

    async def _json(self, client, url, **kwargs):
        install_http_hooks(client, "media", "media_metadata")
        async with client.stream("GET", url, **kwargs) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 256 * 1024:
                    raise ValueError("Media metadata exceeds the display limit")
            import json

            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError("Media metadata must be an object")
            return data

    async def google(self, place_id, width, height, *, fallback_query=None):
        if not self.google_key:
            return unavailable(provider="google", reason="credentials_missing")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", place_id):
            return unavailable(provider="google", reason="invalid_place_id")
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=8, follow_redirects=False, trust_env=False
            ) as client:
                data = await self._json(
                    client,
                    f"https://places.googleapis.com/v1/places/{place_id}",
                    headers={"X-Goog-Api-Key": self.google_key, "X-Goog-FieldMask": "photos"},
                )
                photos = data.get("photos")
                if photos is None or photos == []:
                    missing = unavailable(provider="google", reason="no_photos")
                    if fallback_query:
                        fallback = await self._unsplash_search(
                            fallback_query, width, height, purpose="place_fallback"
                        )
                        if fallback["status"] == "available":
                            return {**fallback, "theme": "general", "fallback": "google_no_photos"}
                    return missing
                if not isinstance(photos, list):
                    return unavailable(provider="google", reason="invalid_photo_metadata")
                photo = photos[0]
                resource = photo.get("name", "")
                if not re.fullmatch(
                    r"places/" + re.escape(place_id) + r"/photos/[A-Za-z0-9_-]{1,2048}", resource
                ):
                    return unavailable(provider="google", reason="invalid_photo_reference")
                media = await self._json(
                    client,
                    f"https://places.googleapis.com/v1/{resource}/media",
                    headers={"X-Goog-Api-Key": self.google_key},
                    params={"maxWidthPx": width, "maxHeightPx": height, "skipHttpRedirect": "true"},
                )
                image = safe_url(media.get("photoUri"), "googleusercontent.com", subdomains=True)
                if not image:
                    return unavailable(provider="google", reason="invalid_photo_url")
                authors = []
                supplied = photo.get("authorAttributions", [])
                if not isinstance(supplied, list) or len(supplied) > 20:
                    return unavailable(provider="google", reason="invalid_attribution")
                for author in supplied:
                    name = author.get("displayName")
                    if not isinstance(name, str) or not name.strip() or len(name) > 500:
                        return unavailable(provider="google", reason="invalid_attribution")
                    uri = author.get("uri")
                    profile = safe_url(uri, "www.google.com") or safe_url(uri, "maps.google.com")
                    if uri and not profile:
                        return unavailable(provider="google", reason="invalid_attribution_url")
                    authors.append({"name": name, "url": profile})
                source = photo.get("googleMapsUri")
                source_url = safe_url(source, "www.google.com") or safe_url(
                    source, "maps.google.com"
                )
                if source and not source_url:
                    return unavailable(provider="google", reason="invalid_source_url")
                return {
                    "status": "available",
                    "image_url": image,
                    "provider": "Google Maps",
                    "authors": authors,
                    "kind": "verified_place",
                    "source_url": source_url,
                }
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as error:
            operation(
                "media_provider_failed", {"provider": "google", "error_type": type(error).__name__}
            )
            return unavailable()

    async def supporting(self, theme, width, height):
        if theme not in ATMOSPHERE_QUERIES or not self.unsplash_key:
            return unavailable(provider="unsplash", reason="supporting_search_unavailable")
        media = await self._unsplash_search(ATMOSPHERE_QUERIES[theme], width, height, theme=theme)
        return {**media, "theme": theme} if media["status"] == "available" else media

    async def _unsplash_search(self, query, width, height, *, theme=None, purpose=None):
        if not self.unsplash_key:
            return unavailable(provider="unsplash", reason="credentials_missing")
        headers = {"Authorization": f"Client-ID {self.unsplash_key}", "Accept-Version": "v1"}
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=8, follow_redirects=False, trust_env=False
            ) as client:
                data = await self._json(
                    client,
                    "https://api.unsplash.com/search/photos",
                    headers=headers,
                    params={
                        "query": query,
                        "page": 1,
                        "per_page": 1,
                        "order_by": "relevant",
                        "orientation": "landscape",
                        "content_filter": "high",
                    },
                )
                results = data.get("results")
                if not isinstance(results, list) or not results:
                    return unavailable()
                first = results[0]
                identity = first["id"]
                if not isinstance(identity, str) or not re.fullmatch(
                    r"[A-Za-z0-9_-]{1,128}", identity
                ):
                    return unavailable()
                media = unsplash_photo(first, width, height, "Travel atmosphere")
                tracking = safe_url(first["links"]["download_location"], "api.unsplash.com")
                if not tracking or urlsplit(tracking).path != f"/photos/{identity}/download":
                    return unavailable()
                # Automatic first-result selection is adoption, distinct from cached display.
                await self._json(client, tracking, headers=headers)
                operation(
                    "media_photo_adopted",
                    {
                        "provider": "unsplash",
                        **({"theme": theme} if theme else {}),
                        **({"purpose": purpose} if purpose else {}),
                    },
                )
            return media
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError) as error:
            operation(
                "media_provider_failed",
                {"provider": "unsplash", "error_type": type(error).__name__},
            )
            return unavailable()

    async def curated(self, key, width):
        photo_id, alt = CURATED[key]
        if not self.unsplash_key:
            return unavailable(provider="unsplash", reason="credentials_missing")
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=8, follow_redirects=False, trust_env=False
            ) as client:
                data = await self._json(
                    client,
                    f"https://api.unsplash.com/photos/{photo_id}",
                    headers={
                        "Authorization": f"Client-ID {self.unsplash_key}",
                        "Accept-Version": "v1",
                    },
                )
            if data.get("id") != photo_id:
                return unavailable(provider="unsplash", reason="invalid_photo_reference")
            return unsplash_photo(data, width, 1280, alt)
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError) as error:
            operation(
                "media_provider_failed",
                {"provider": "unsplash", "error_type": type(error).__name__},
            )
            return unavailable()


def get_media_providers():
    settings = MediaSettings()
    return MediaProviders(
        google_key=settings.google_places_media_key.get_secret_value(),
        unsplash_key=settings.unsplash_access_key.get_secret_value(),
    )


Providers = Annotated[MediaProviders, Depends(get_media_providers)]
Dimension = Annotated[int, Query(ge=200, le=1280)]
Slot = Annotated[str, StringConstraints(min_length=1, max_length=300)]
RequestedSlots = Annotated[list[Slot] | None, Query(max_length=MAX_PLACE_PHOTOS)]


def owned_bindings(kind, resource_id, owner):
    table = "itinerary_previews" if kind == "previews" else "trips"
    with connect() as connection:
        row = connection.execute(
            f"SELECT media_bindings FROM app.{table} WHERE owner_id=%s AND id=%s",
            (owner, resource_id),
        ).fetchone()
        if row is None:
            raise HTTPException(404, {"code": "media_resource_not_found"})
        # A decided preview delegates to the owner's saved trip; discarded/deleted stays empty.
        if kind == "previews":
            decision = connection.execute(
                "SELECT state,saved_trip_id FROM app.itinerary_previews WHERE id=%s", (resource_id,)
            ).fetchone()
            if decision["state"] != "pending":
                row = connection.execute(
                    "SELECT media_bindings FROM app.trips WHERE owner_id=%s AND id=%s",
                    (owner, decision["saved_trip_id"]),
                ).fetchone()
    return sorted((row["media_bindings"] if row else {}).items())


async def resolve_photos(
    bindings,
    providers,
    width,
    height,
    response,
    *,
    offset=0,
    slots=None,
    batch_timeout_seconds=30,
    provider_timeout_seconds=8,
    lookup=None,
    share_values=False,
    source_provider="google",
    fallback_queries=None,
):
    response.headers["Cache-Control"] = "no-store"
    all_bindings = list(bindings)
    if slots is not None:
        if len(slots) > MAX_PLACE_PHOTOS:
            raise ValueError("Media batch exceeds the slot limit")
        authorized = dict(all_bindings)
        all_bindings = [(slot, authorized.get(slot)) for slot in dict.fromkeys(slots)]
        offset = 0
    bindings = all_bindings[offset : offset + MAX_PLACE_PHOTOS]
    semaphore = asyncio.Semaphore(3)
    items = {slot: unavailable() for slot, _ in bindings}
    lookup = lookup or providers.google
    pending = {}

    async def fetch(value, query=None):
        async with semaphore:
            async with asyncio.timeout(provider_timeout_seconds):
                options = {"fallback_query": query} if query else {}
                return await lookup(value, width, height, **options)

    async def resolve(slot, place):
        if place is None:
            operation(
                "media_unavailable", {"provider": source_provider, "reason": "binding_unavailable"}
            )
            return
        try:
            if share_values:
                if place not in pending:
                    pending[place] = asyncio.create_task(fetch(place))
                items[slot] = await pending[place]
            else:
                items[slot] = await fetch(place, (fallback_queries or {}).get(slot))
        except Exception as error:
            # One display failure must not erase completed slots; cancellation propagates.
            operation("media_slot_failed", {"error_type": type(error).__name__})

    try:
        async with asyncio.timeout(batch_timeout_seconds):
            await asyncio.gather(*(resolve(slot, place) for slot, place in bindings))
    except TimeoutError:
        operation("media_batch_timeout")
    next_offset = offset + len(bindings)
    return {
        "items": items,
        "limit": MAX_PLACE_PHOTOS,
        "next_offset": next_offset if next_offset < len(all_bindings) else None,
    }


def place_fallback_queries(detail):
    """Only structured place/destination labels enter search, never notes or preferences."""

    def query(name):
        parts = [
            " ".join(value.split())[:120]
            for value in (name, detail.get("destination"))
            if isinstance(value, str) and value.strip()
        ]
        return " ".join(parts)[:200] or ATMOSPHERE_QUERIES["general"]

    return {
        **{
            f"activity:{activity['activity_id']}": query(activity.get("place_name"))
            for day in detail["days"]
            for activity in day["activities"]
        },
        **{
            f"nearby:{index}": query(item["place_name"])
            for index, item in enumerate(detail.get("nearby", []))
        },
    }


@router.get("/api/examples/{example_id}/media")
async def example_media(
    example_id: str,
    providers: Providers,
    response: Response,
    width: Dimension = 960,
    height: Dimension = 640,
    offset: Annotated[int, Query(ge=0)] = 0,
    slot: RequestedSlots = None,
):
    detail = example_detail(example_id)
    return await resolve_photos(
        detail._media_bindings.items(),
        providers,
        width,
        height,
        response,
        offset=offset,
        slots=slot,
        fallback_queries=place_fallback_queries(detail.model_dump(mode="json")),
    )


def owned_detail(kind, resource_id, owner):
    from backend.app.product.saved_store import SavedStore
    from backend.app.product.task_store import TaskStore

    if kind == "trips":
        detail = SavedStore().read(owner, resource_id)
    else:
        previews = TaskStore().previews(owner, resource_id)
        detail = previews[0].get("snapshot") if previews else None
    if detail is None:
        raise HTTPException(404, {"code": "media_resource_not_found"})
    return detail


def owned_supporting_slots(kind, resource_id, owner):
    detail = owned_detail(kind, resource_id, owner)
    return [
        (f"activity:{activity['activity_id']}", activity.get("atmosphere_theme") or "general")
        for day in detail["days"]
        for activity in day["activities"]
        if activity.get("activity_kind") == "generic_activity"
        and activity.get("time_use") == "scheduled"
    ]


@router.get("/api/{kind}/{resource_id}/supporting-media")
async def supporting_media(
    kind: Literal["previews", "trips"],
    resource_id: UUID,
    user: CurrentUser,
    providers: Providers,
    response: Response,
    width: Dimension = 960,
    height: Dimension = 640,
    offset: Annotated[int, Query(ge=0)] = 0,
    slot: RequestedSlots = None,
):
    slots = await asyncio.to_thread(owned_supporting_slots, kind, resource_id, user["id"])
    return await resolve_photos(
        slots,
        providers,
        width,
        height,
        response,
        offset=offset,
        slots=slot,
        lookup=providers.supporting,
        share_values=True,
        source_provider="unsplash",
    )


@router.get("/api/{kind}/{resource_id}/media")
async def owned_media(
    kind: Literal["previews", "trips"],
    resource_id: UUID,
    user: CurrentUser,
    providers: Providers,
    response: Response,
    width: Dimension = 960,
    height: Dimension = 640,
    offset: Annotated[int, Query(ge=0)] = 0,
    slot: RequestedSlots = None,
):
    # Storage is synchronous; slow reads must not block the task/lease event loop.
    bindings = await asyncio.to_thread(owned_bindings, kind, resource_id, user["id"])
    queries = {}
    if bindings:
        detail = await asyncio.to_thread(owned_detail, kind, resource_id, user["id"])
        queries = place_fallback_queries(detail)
    return await resolve_photos(
        bindings,
        providers,
        width,
        height,
        response,
        offset=offset,
        slots=slot,
        fallback_queries=queries,
    )


@router.get("/api/media/curated/{key}")
async def curated_media(
    key: Literal["sydney", "london", "nature"],
    providers: Providers,
    response: Response,
    width: Dimension = 960,
):
    response.headers["Cache-Control"] = "no-store"
    if key == "london":
        # This adopted landmark belongs to the allowlisted historical London example.
        bindings = example_detail("london-example")._media_bindings
        photo = await providers.google(
            bindings["activity:london-20261015-tower-bridge"],
            width,
            640,
            fallback_query="Tower Bridge London",
        )
        return {**photo, "alt": "Tower Bridge, London"}
    return await providers.curated(key, width)
