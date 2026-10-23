"""Fresh fixed-provider display metadata; no photo archive or URL fetch proxy."""

import asyncio
import re
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

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


class MediaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRODUCT_", env_file=PROJECT_ROOT / ".env", extra="ignore",
        hide_input_in_errors=True,
    )
    google_places_media_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="GOOGLE_MAPS_API_KEY",
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


def unavailable():
    return {"status": "unavailable"}


class MediaProviders:
    """Two metadata requests per Google photo, one per fixed curated photo; no retries/cache.

    HTTP transport is the external acceptance seam. Redirects are never followed and
    response bodies, dimensions, parallelism and the total display batch are bounded.
    """

    def __init__(self, *, google_key="", unsplash_key="", transport=None):
        self.google_key, self.unsplash_key = google_key, unsplash_key
        self.transport = transport

    async def _json(self, client, url, **kwargs):
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

    async def google(self, place_id, width, height):
        if not self.google_key or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", place_id):
            return unavailable()
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=3, follow_redirects=False, trust_env=False
            ) as client:
                data = await self._json(
                    client,
                    f"https://places.googleapis.com/v1/places/{place_id}",
                    headers={"X-Goog-Api-Key": self.google_key, "X-Goog-FieldMask": "photos"},
                )
                photos = data.get("photos")
                if not isinstance(photos, list) or not photos:
                    return unavailable()
                photo = photos[0]
                resource = photo.get("name", "")
                if not re.fullmatch(
                    r"places/" + re.escape(place_id) + r"/photos/[A-Za-z0-9_-]{1,2048}", resource
                ):
                    return unavailable()
                media = await self._json(
                    client,
                    f"https://places.googleapis.com/v1/{resource}/media",
                    headers={"X-Goog-Api-Key": self.google_key},
                    params={"maxWidthPx": width, "maxHeightPx": height, "skipHttpRedirect": "true"},
                )
                image = safe_url(media.get("photoUri"), "googleusercontent.com", subdomains=True)
                if not image:
                    return unavailable()
                authors = []
                supplied = photo.get("authorAttributions", [])
                if not isinstance(supplied, list) or len(supplied) > 20:
                    return unavailable()
                for author in supplied:
                    name = author.get("displayName")
                    if not isinstance(name, str) or not name.strip() or len(name) > 500:
                        return unavailable()
                    uri = author.get("uri")
                    profile = safe_url(uri, "www.google.com") or safe_url(uri, "maps.google.com")
                    if uri and not profile:
                        return unavailable()
                    authors.append({"name": name, "url": profile})
                source = photo.get("googleMapsUri")
                source_url = safe_url(source, "www.google.com") or safe_url(
                    source, "maps.google.com"
                )
                if source and not source_url:
                    return unavailable()
                return {
                    "status": "available",
                    "image_url": image,
                    "provider": "Google Maps",
                    "authors": authors,
                    "kind": "verified_place",
                    "source_url": source_url,
                }
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return unavailable()

    async def curated(self, key, width):
        photo_id, alt = CURATED[key]
        if not self.unsplash_key:
            return unavailable()
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=3, follow_redirects=False, trust_env=False
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
                return unavailable()
            image = safe_url(data["urls"]["raw"], "images.unsplash.com")
            user = data["user"]
            profile = safe_url(user["links"]["html"], "unsplash.com")
            page = safe_url(data["links"]["html"], "unsplash.com")
            author = user["name"]
            if (
                not image
                or not profile
                or not page
                or not isinstance(author, str)
                or not author.strip()
            ):
                return unavailable()
            parsed = urlsplit(image)
            parameters = [
                (key, value)
                for key, value in parse_qsl(parsed.query, keep_blank_values=True)
                if key not in {"w", "h", "dpr", "fit", "auto"}
            ]
            parameters.extend(
                [("w", str(width)), ("h", "1280"), ("fit", "max"), ("auto", "format")]
            )
            image = urlunsplit(parsed._replace(query=urlencode(parameters)))
            referral = "utm_source=dayloom&utm_medium=referral"
            # Retain returned hotlink tracking parameters; no selection/download action exists.
            return {
                "status": "available",
                "image_url": image,
                "provider": "Unsplash",
                "authors": [
                    {
                        "name": author[:500],
                        "url": profile + ("&" if "?" in profile else "?") + referral,
                    }
                ],
                "source_url": page + ("&" if "?" in page else "?") + referral,
                "alt": alt,
                "kind": "atmosphere",
            }
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
            return unavailable()


def get_media_providers():
    settings = MediaSettings()
    return MediaProviders(
        google_key=settings.google_places_media_key.get_secret_value(),
        unsplash_key=settings.unsplash_access_key.get_secret_value(),
    )


Providers = Annotated[MediaProviders, Depends(get_media_providers)]
Dimension = Annotated[int, Query(ge=200, le=1280)]


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
    return list((row["media_bindings"] if row else {}).items())[:MAX_PLACE_PHOTOS]


async def resolve_photos(bindings, providers, width, height, response):
    response.headers["Cache-Control"] = "no-store"
    bindings = list(bindings)[:MAX_PLACE_PHOTOS]
    semaphore = asyncio.Semaphore(3)

    async def resolve(slot, place):
        async with semaphore:
            return slot, await providers.google(place, width, height)

    try:
        async with asyncio.timeout(12):
            items = dict(await asyncio.gather(*(resolve(slot, place) for slot, place in bindings)))
    except TimeoutError:
        items = {slot: unavailable() for slot, _ in bindings}
    return {"items": items, "limit": MAX_PLACE_PHOTOS}


@router.get("/api/examples/{example_id}/media")
async def example_media(
    example_id: str,
    providers: Providers,
    response: Response,
    width: Dimension = 960,
    height: Dimension = 640,
):
    detail = example_detail(example_id)
    return await resolve_photos(detail._media_bindings.items(), providers, width, height, response)


@router.get("/api/{kind}/{resource_id}/media")
async def owned_media(
    kind: Literal["previews", "trips"],
    resource_id: UUID,
    user: CurrentUser,
    providers: Providers,
    response: Response,
    width: Dimension = 960,
    height: Dimension = 640,
):
    # Storage is synchronous; slow reads must not block the task/lease event loop.
    bindings = await asyncio.to_thread(owned_bindings, kind, resource_id, user["id"])
    return await resolve_photos(bindings, providers, width, height, response)


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
            bindings["activity:london-20261015-tower-bridge"], width, 640
        )
        return {**photo, "alt": "Tower Bridge, London"}
    return await providers.curated(key, width)
