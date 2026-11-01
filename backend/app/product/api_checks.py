"""Explicit, bounded provider probes. No planner runs, retries or credential persistence."""

import asyncio
import json
import math
import re
import threading
from datetime import UTC, datetime
from time import monotonic
from urllib.parse import urlsplit

import httpx

from backend.app.product.configuration_validation import supported_foundry_endpoint

MAX_REQUESTS = 8
RUN_TIMEOUT_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 15
WEB_TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 131072

MESSAGES = {
    "passed": "The requested API capability responded successfully.",
    "missing_credentials": "Required settings are missing.",
    "invalid_configuration": "Check the saved endpoint, deployment and credential format.",
    "authentication_failed": "The service rejected the credential.",
    "permission_denied": "Check API enablement, key restrictions and service permissions.",
    "billing_required": "Check the service account's billing setup.",
    "quota_exceeded": "The service reported an exhausted quota.",
    "rate_limited": "The service is rate limiting requests. Try again later.",
    "not_found": "The requested deployment or API resource was not found.",
    "provider_error": "The service could not process this check.",
    "network_error": "The service could not be reached. Check network and proxy settings.",
    "timeout": "The check timed out. This does not establish invalid credentials.",
    "invalid_response": "The response did not confirm the required API capability.",
    "response_too_large": "The response exceeded this check's size limit.",
    "run_limit": "The check's time or request limit was reached.",
    "dependency_failed": "Places lookup did not supply a sample for the photo check.",
    "no_sample_photo": "The sample has no photos; photo permission could not be verified.",
}
REQUIRED_SETTINGS = {
    "foundry": ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
    "google": ("GOOGLE_MAPS_API_KEY",),
    "unsplash": ("UNSPLASH_API_KEY",),
}


class CheckBusy(Exception):
    """Another explicit check is already using this local instance."""


class ProbeFailure(Exception):
    def __init__(self, code, *, status=None, http_status=None):
        self.code = code
        self.status = status or code
        self.http_status = http_status


class ApiChecker:
    def __init__(self, *, transport=None, clock=monotonic):
        self.transport, self.clock = transport, clock
        self.lock = threading.Lock()

    async def check(self, service, values):
        if service != "all" and service not in REQUIRED_SETTINGS:
            raise ValueError("Unknown API check service")
        if not self.lock.acquire(blocking=False):
            raise CheckBusy()
        try:
            async with httpx.AsyncClient(
                transport=self.transport,
                timeout=REQUEST_TIMEOUT_SECONDS,
                follow_redirects=False,
            ) as client:
                run = _CheckRun(client, values, self.clock)
                for group, name, operation in (
                    ("foundry", "foundry", run.foundry),
                    ("foundry", "foundry_search", run.search),
                    ("openai", "openai_embeddings", run.embeddings),
                    ("google", "google_places", run.places),
                    ("google", "google_routes", run.routes),
                    ("google", "google_photos", run.photos),
                    ("unsplash", "unsplash", run.unsplash),
                ):
                    if service in {"all", group}:
                        await run.probe(name, REQUIRED_SETTINGS[group], operation, service=group)
                return {
                    "service": service,
                    "checked_at": datetime.now(UTC).isoformat(),
                    "request_count": run.request_count,
                    "results": run.results,
                }
        finally:
            self.lock.release()


class _CheckRun:
    def __init__(self, client, values, clock):
        self.client, self.values, self.clock = client, values, clock
        self.deadline = clock() + RUN_TIMEOUT_SECONDS
        self.request_count = 0
        self.results = []
        self.place_id = None

    async def probe(self, name, required, operation, *, service):
        started = self.clock()
        result = {"id": name, "service": service}
        try:
            if any(not self.values.get(key) for key in required):
                raise ProbeFailure("missing_credentials", status="not_configured")
            if any(
                len(self.values[key]) > 4096
                or not self.values[key].isascii()
                or any(ord(char) < 32 or ord(char) == 127 for char in self.values[key])
                for key in required
            ):
                raise ProbeFailure("invalid_configuration")
            await operation()
            result.update(status="passed", message=MESSAGES["passed"])
        except ProbeFailure as error:
            result.update(status=error.status, message=MESSAGES[error.code])
            if error.http_status is not None:
                result["http_status"] = error.http_status
        except (httpx.TimeoutException, TimeoutError):
            result.update(status="timeout", message=MESSAGES["timeout"])
        except httpx.RequestError:
            result.update(status="network_error", message=MESSAGES["network_error"])
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            AttributeError,
            OverflowError,
            RecursionError,
        ):
            result.update(status="invalid_response", message=MESSAGES["invalid_response"])
        result["latency_ms"] = max(0, round((self.clock() - started) * 1000))
        self.results.append(result)

    async def request(self, method, url, *, timeout=None, **kwargs):
        # Provider-supplied IDs must not reflect a credential into URL/access logs.
        if any(
            value and value in url
            for key, value in self.values.items()
            if key.endswith(("_API_KEY", "_ACCESS_KEY"))
        ):
            raise ProbeFailure("invalid_response")
        timeout = REQUEST_TIMEOUT_SECONDS if timeout is None else timeout
        remaining = self.deadline - self.clock()
        if self.request_count >= MAX_REQUESTS or remaining <= 0:
            raise ProbeFailure("run_limit", status="not_checked")
        self.request_count += 1
        async with asyncio.timeout(min(timeout, remaining)):
            async with self.client.stream(method, url, **kwargs) as response:
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(content) + len(chunk) > MAX_RESPONSE_BYTES:
                        if response.status_code >= 300:
                            break
                        raise ProbeFailure("response_too_large", status="invalid_response")
                    content.extend(chunk)
                if response.status_code >= 300:
                    try:
                        body = json.loads(content)
                    except (ValueError, RecursionError):
                        body = {}
                    raise ProbeFailure(
                        error_code(response.status_code, body), http_status=response.status_code
                    )
                return json.loads(content)

    def foundry_url(self):
        endpoint = self.values["AZURE_OPENAI_ENDPOINT"]
        if not supported_foundry_endpoint(endpoint):
            raise ProbeFailure("invalid_configuration")
        return endpoint.rstrip("/") + "/responses"

    async def foundry(self):
        data = await self.request(
            "POST",
            self.foundry_url(),
            headers={"Authorization": "Bearer " + self.values["AZURE_OPENAI_API_KEY"]},
            json={
                "model": self.values["AZURE_OPENAI_DEPLOYMENT"],
                "input": 'Return JSON with exactly {"ok": true}.',
                "max_output_tokens": 1024,
                "store": False,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "ConfigurationCheck",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {"ok": {"type": "boolean"}},
                            "required": ["ok"],
                            "additionalProperties": False,
                        },
                    }
                },
            },
        )
        text = "".join(
            content["text"]
            for item in data.get("output", [])
            if item.get("type") == "message"
            for content in item.get("content", [])
            if content.get("type") == "output_text"
        )
        parsed = json.loads(text)
        if (
            data.get("status") != "completed"
            or not isinstance(parsed, dict)
            or set(parsed) != {"ok"}
            or parsed["ok"] is not True
        ):
            raise ProbeFailure("invalid_response")

    def openai_headers(self):
        return {"Authorization": "Bearer " + self.values["OPENAI_API_KEY"]}

    def google_headers(self, mask):
        return {"X-Goog-Api-Key": self.values["GOOGLE_MAPS_API_KEY"], "X-Goog-FieldMask": mask}

    async def embeddings(self):
        data = await self.request(
            "POST",
            "https://api.openai.com/v1/embeddings",
            headers=self.openai_headers(),
            json={
                "model": "text-embedding-3-small",
                "input": "Local configuration check.",
                "encoding_format": "float",
            },
        )
        vector = data["data"][0]["embedding"]
        if (
            data.get("model") != "text-embedding-3-small"
            or len(data["data"]) != 1
            or len(vector) != 1536
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in vector
            )
        ):
            raise ProbeFailure("invalid_response")

    async def search(self):
        data = await self.request(
            "POST",
            self.foundry_url(),
            timeout=WEB_TIMEOUT_SECONDS,
            headers={"Authorization": "Bearer " + self.values["AZURE_OPENAI_API_KEY"]},
            json={
                "model": self.values["AZURE_OPENAI_DEPLOYMENT"],
                "store": False,
                "max_output_tokens": 512,
                "reasoning": {"effort": "low"},
                "input": "Search for the official Sydney Opera House website. Reply briefly.",
                "tools": [
                    {
                        "type": "web_search",
                        "search_context_size": "low",
                        "filters": {"allowed_domains": ["sydneyoperahouse.com"]},
                    }
                ],
                "max_tool_calls": 1,
                "tool_choice": "required",
                "service_tier": "default",
            },
        )
        if data.get("status") != "completed" or not any(
            item.get("type") == "web_search_call" and item.get("status") == "completed"
            for item in data.get("output", [])
        ):
            raise ProbeFailure("invalid_response")

    async def places(self):
        data = await self.request(
            "POST",
            "https://places.googleapis.com/v1/places:searchText",
            headers=self.google_headers("places.id"),
            json={
                "textQuery": "Sydney Opera House, Sydney, Australia",
                "pageSize": 1,
                "languageCode": "en",
            },
        )
        place_id = data["places"][0]["id"]
        if not isinstance(place_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", place_id):
            raise ProbeFailure("invalid_response")
        self.place_id = place_id

    async def routes(self):
        def point(latitude, longitude):
            return {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": latitude,
                            "longitude": longitude,
                        }
                    }
                }
            }

        data = await self.request(
            "POST",
            "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
            headers=self.google_headers(
                "originIndex,destinationIndex,status,condition,duration,distanceMeters"
            ),
            json={
                "origins": [point(-33.8568, 151.2153)],
                "destinations": [point(-33.8612, 151.2103)],
                "travelMode": "WALK",
            },
        )
        item = data[0]
        status = item.get("status", {}).get("code", 0)
        if status:
            code = {7: "permission_denied", 8: "quota_exceeded", 16: "authentication_failed"}.get(
                status, "provider_error"
            )
            raise ProbeFailure(code)
        if (
            len(data) != 1
            or item.get("condition") != "ROUTE_EXISTS"
            or not re.fullmatch(r"\d+(?:\.\d+)?s", item.get("duration", ""))
        ):
            raise ProbeFailure("invalid_response")

    async def photos(self):
        if self.place_id is None:
            raise ProbeFailure("dependency_failed", status="not_checked")
        data = await self.request(
            "GET",
            f"https://places.googleapis.com/v1/places/{self.place_id}",
            headers=self.google_headers("photos"),
        )
        if data.get("photos") is None or data.get("photos") == []:
            raise ProbeFailure("no_sample_photo", status="inconclusive")
        name = data["photos"][0]["name"]
        if not isinstance(name, str) or not re.fullmatch(
            r"places/" + re.escape(self.place_id) + r"/photos/[A-Za-z0-9_-]{1,2048}", name
        ):
            raise ProbeFailure("invalid_response")
        media = await self.request(
            "GET",
            f"https://places.googleapis.com/v1/{name}/media",
            headers={"X-Goog-Api-Key": self.values["GOOGLE_MAPS_API_KEY"]},
            params={"maxWidthPx": 100, "maxHeightPx": 100, "skipHttpRedirect": "true"},
        )
        if not image_url(media["photoUri"], "googleusercontent.com", subdomains=True):
            raise ProbeFailure("invalid_response")

    async def unsplash(self):
        data = await self.request(
            "GET",
            "https://api.unsplash.com/photos/7Zb7kUyQg1E",
            headers={
                "Authorization": "Client-ID " + self.values["UNSPLASH_API_KEY"],
                "Accept-Version": "v1",
            },
        )
        if data.get("id") != "7Zb7kUyQg1E" or not image_url(
            data["urls"]["raw"], "images.unsplash.com"
        ):
            raise ProbeFailure("invalid_response")


def image_url(value, host, *, subdomains=False):
    if not isinstance(value, str) or len(value) > 4096:
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and not parsed.username
        and not parsed.password
        and parsed.port in (None, 443)
        and not parsed.fragment
        and (parsed.hostname == host or subdomains and (parsed.hostname or "").endswith("." + host))
    )


def error_code(status, body):
    error = body.get("error", {}) if isinstance(body, dict) else {}
    values = []
    if isinstance(error, dict):
        values = [error.get(key) for key in ("code", "type", "status")]
        details = error.get("details", [])
        if isinstance(details, list):
            values.extend(item.get("reason") for item in details[:20] if isinstance(item, dict))
    codes = {value.casefold() for value in values if isinstance(value, str) and len(value) < 128}
    for reasons, code in (
        ({"invalid_api_key", "api_key_invalid", "unauthenticated"}, "authentication_failed"),
        ({"billing_disabled", "billing_not_active", "billing_required"}, "billing_required"),
        (
            {
                "insufficient_quota",
                "quota_exceeded",
                "billing_hard_limit_reached",
            },
            "quota_exceeded",
        ),
        ({"rate_limit_exceeded"}, "rate_limited"),
        ({"resource_exhausted"}, "quota_exceeded"),
        ({"service_disabled", "api_key_service_blocked", "permission_denied"}, "permission_denied"),
        ({"deploymentnotfound", "model_not_found"}, "not_found"),
    ):
        if codes & reasons:
            return code
    return {
        401: "authentication_failed",
        403: "permission_denied",
        404: "not_found",
        429: "rate_limited",
    }.get(status, "provider_error")
