"""Persistent display URLs and per-image PostgreSQL acquisition coordination."""

import asyncio
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from backend.app.product.database import connect

_workers = ThreadPoolExecutor(max_workers=12, thread_name_prefix="product-media-cache")


def cached_entry(resource, key):
    value = (resource or {}).get("media_cache", {}).get(key)
    if isinstance(value, dict):
        try:
            UUID(value.get("revision", ""))
            return value
        except (ValueError, TypeError, AttributeError):
            pass
    return {}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def display_metadata(value):
    """Whitelist the provider display DTO, validating persisted records on every read."""
    from backend.app.product.media import safe_url

    if not isinstance(value, dict) or value.get("status") != "available":
        return None
    provider = value.get("provider")
    google = provider == "Google Maps" and value.get("kind") == "verified_place"
    unsplash = provider == "Unsplash" and value.get("kind") == "atmosphere"
    if not (google or unsplash):
        return None
    if not safe_url(
        value.get("image_url"),
        "googleusercontent.com" if google else "images.unsplash.com", subdomains=google,
    ):
        return None
    source = value.get("source_url")
    hosts = ("www.google.com", "maps.google.com") if google else ("unsplash.com",)
    if source and not any(safe_url(source, host) for host in hosts):
        return None
    authors = value.get("authors")
    if not isinstance(authors, list) or len(authors) > 100 or (unsplash and not authors):
        return None
    cleaned = []
    for author in authors:
        if not isinstance(author, dict):
            return None
        name, url = author.get("name"), author.get("url")
        if not isinstance(name, str) or not name.strip() or len(name) > 2000:
            return None
        if (url and not any(safe_url(url, host) for host in hosts)) or (unsplash and not url):
            return None
        cleaned.append({"name": name, "url": url})
    result = {"status": "available", "provider": provider, "kind": value["kind"],
              "image_url": value["image_url"], "source_url": source, "authors": cleaned}
    for key in ("theme", "fallback", "alt"):
        if key in value:
            if not isinstance(value[key], str) or len(value[key]) > 2000:
                return None
            result[key] = value[key]
    if unsplash:
        if not source or result.get("theme", "general") not in {
            "meal", "rest", "explore", "walk", "general",
        }:
            return None
        result.setdefault("theme", "general")
        if "fallback" in result and (
            result["fallback"] != "google_no_photos" or result["theme"] != "general"
        ):
            return None
    elif "fallback" in result:
        return None
    return result


@dataclass(frozen=True)
class MediaScope:
    owner: str
    kind: str
    resource: str
    version: str


def resource_version(row):
    return fingerprint({key: value for key, value in row.items() if key != "media_cache"})


def _resource(connection, kind, resource, owner, *, lock=False):
    if kind == "trips":
        query = ("SELECT media_bindings,destination,media_cache FROM app.trips "
                 "WHERE owner_id=%s AND id=%s")
    else:
        query = ("SELECT snapshot,media_bindings,media_cache FROM app.itinerary_previews "
                 "WHERE owner_id=%s AND id=%s AND state='pending'")
    return connection.execute(query + (" FOR UPDATE" if lock else ""), (owner, resource)).fetchone()


def owned_context(kind, resource, owner):
    """Read authorization, bindings and detail from one repeatable-read snapshot."""
    from backend.app.product.saved_store import SavedStore

    original_kind = kind
    with connect() as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        if kind == "previews":
            preview = connection.execute(
                "SELECT state,saved_trip_id FROM app.itinerary_previews "
                "WHERE owner_id=%s AND id=%s",
                (owner, resource),
            ).fetchone()
            if preview is None:
                raise HTTPException(404, {"code": "media_resource_not_found"})
            if preview and preview["state"] == "saved" and preview["saved_trip_id"]:
                kind, resource = "trips", preview["saved_trip_id"]
        row = _resource(connection, kind, resource, owner)
        if row is None:
            if original_kind == "previews":
                return None, None, {}
            raise HTTPException(404, {"code": "media_resource_not_found"})
        scope = MediaScope(str(owner), kind, str(resource), resource_version(row))
        detail = (row["snapshot"] if kind == "previews"
                  else SavedStore().read_connection(connection, owner, resource))
        return scope, detail, row["media_bindings"]


class MediaCache:
    def __init__(self, settings=None):
        self.settings = settings

    async def resolve(self, scope, identity, acquire, refresh=None):
        """Coalesce across workers; refresh only the version actually seen by the client.

        SQL runs in one worker thread; the bounded async provider remains on its API
        loop. Session advisory locks serialize only the same image across workers.
        Row locks cover publication only; no transaction waits on a provider call.
        Empty metadata is a coordination revision, not a reusable negative result.
        """
        key = fingerprint(identity)
        sharing_key = (fingerprint([identity[0], *identity[2:]])
                       if identity[0] == "supporting" else None)
        lock_key = fingerprint([scope.owner, scope.kind, scope.resource, sharing_key or key])
        loop = asyncio.get_running_loop()
        cancelled = threading.Event()
        futures = []

        def execute():
            with connect(self.settings) as connection:
                connection.autocommit = True
                connection.execute("SET lock_timeout = '10000ms'")
                initial_row = _resource(connection, scope.kind, scope.resource, scope.owner)
                initial = cached_entry(initial_row, key)
                connection.execute("SELECT pg_advisory_lock(%s)", (
                    int.from_bytes(bytes.fromhex(lock_key[:16]), signed=True),
                ))
                if cancelled.is_set():
                    return {"status": "unavailable"}
                resource = _resource(connection, scope.kind, scope.resource, scope.owner)
                if resource is None or resource_version(resource) != scope.version:
                    raise HTTPException(404, {"code": "media_resource_not_found"})
                row = cached_entry(resource, key)
                media = display_metadata(row.get("media"))
                revision = row.get("revision")
                if row and refresh and revision != str(refresh):
                    return {**(media or {"status": "unavailable"}), "cache_revision": revision}
                if media and not refresh:
                    return {**media, "cache_revision": revision}
                if row and not media and initial.get("revision") != revision:
                    return {"status": "unavailable", "cache_revision": revision}
                acquired_at = None
                media = None
                if sharing_key and not refresh:
                    candidates = sorted((entry for entry in resource["media_cache"].values()
                        if isinstance(entry, dict) and entry.get("sharing_key") == sharing_key
                        and isinstance(entry.get("acquired_at"), str)),
                        key=lambda entry: entry["acquired_at"])
                    for entry in candidates:
                        media = display_metadata(entry.get("media"))
                        if media:
                            acquired_at = entry["acquired_at"]
                            break
                if media is None:
                    future = asyncio.run_coroutine_threadsafe(acquire(), loop)
                    futures.append(future)
                    if cancelled.is_set():
                        future.cancel()
                    try:
                        media = display_metadata(future.result(timeout=32))
                    finally:
                        if not future.done():
                            future.cancel()
                revision = str(uuid4())
                with connection.transaction():
                    resource = _resource(
                        connection, scope.kind, scope.resource, scope.owner, lock=True,
                    )
                    if resource is None or resource_version(resource) != scope.version:
                        raise HTTPException(404, {"code": "media_resource_not_found"})
                    entries = {name: entry for name, entry in resource["media_cache"].items()
                               if isinstance(entry, dict)}
                    entries[key] = {"revision": revision, "media": media,
                                    "sharing_key": sharing_key,
                                    "acquired_at": (acquired_at or datetime.now(UTC).isoformat())
                                    if media else None}
                    entries = dict(sorted(entries.items(), key=lambda item:
                        item[1].get("acquired_at") or "", reverse=True)[:1000])
                    while entries and len(json.dumps(entries).encode()) > 5 * 1024 * 1024:
                        entries.pop(next(reversed(entries)))
                    table = "trips" if scope.kind == "trips" else "itinerary_previews"
                    connection.execute(
                        f"UPDATE app.{table} SET media_cache=%s WHERE owner_id=%s AND id=%s",
                        (Jsonb(entries), scope.owner, scope.resource),
                    )
                return {**(media or {"status": "unavailable"}), "cache_revision": revision}

        try:
            # Blocking advisory-lock waiters must not occupy asyncio's DNS executor.
            return await loop.run_in_executor(_workers, copy_context().run, execute)
        except asyncio.CancelledError:
            cancelled.set()
            for future in futures:
                future.cancel()
            raise


def get_media_cache():
    return MediaCache()
