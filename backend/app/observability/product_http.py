"""ASGI request audit and bounded, untrusted browser error reports."""

import json
import re
import threading
from collections import OrderedDict
from contextlib import nullcontext
from time import monotonic
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.observability.model_usage import observe_usage
from backend.app.observability.product_logs import log_context, operation, safe_error

router = APIRouter(tags=["diagnostics"])
_buckets = OrderedDict()
_bucket_lock = threading.Lock()


def route_path(path):
    """Keep route structure, stripping queries, UUIDs and arbitrary user text."""
    path = path.split("?", 1)[0].split("#", 1)[0]
    if not path.startswith("/") or len(path) > 256:
        return "/unknown"
    return "/".join(
        part if re.fullmatch(r"[a-zA-Z][a-zA-Z_-]{0,40}", part) else ":id"
        for part in path.split("/")
    )


def resource_identifiers(source):
    values = {}
    for key in (
        "id",
        "preview_id",
        "saved_trip_id",
        "source_task_id",
        "task_id",
        "trip_id",
        "draft_id",
        "resource_id",
    ):
        if source.get(key) is None:
            continue
        try:
            values[key] = str(UUID(str(source[key])))
        except ValueError:
            pass
    return values


class ProductHTTPLogging:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = monotonic()
        request_id = str(uuid4())  # Never trust client-chosen correlation identifiers.
        scope.setdefault("state", {})["request_id"] = request_id
        status, body_size, body = 500, 0, bytearray()
        error = None

        async def observe(message):
            nonlocal status, body_size
            if message["type"] == "http.response.start":
                status = message["status"]
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        (b"x-request-id", request_id.encode()),
                    ],
                }
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                body_size += len(chunk)
                if len(body) + len(chunk) <= 65536:
                    body.extend(chunk)
            await send(message)

        observe_calls = (
            scope["path"].startswith("/api/input-assistance/")
            or scope["path"].endswith("/media")
            or scope["path"].startswith("/api/media/")
        )
        with (
            log_context(request_id=request_id),
            observe_usage(lambda data: operation("http_usage", data))
            if observe_calls
            else nullcontext(),
        ):
            try:
                await self.app(scope, receive, observe)
            except BaseException as exc:
                error = safe_error(exc)
                raise
            finally:
                account = scope.get("state", {}).get("account") or {}
                route = getattr(scope.get("route"), "path", None) or "/unmatched"
                data = {
                    "method": scope["method"],
                    "route": route,
                    "status": status,
                    "duration_ms": round((monotonic() - started) * 1000, 2),
                    "response_bytes": body_size,
                    "owner_id": str(account["id"]) if account.get("id") else None,
                }
                data.update(resource_identifiers(scope.get("path_params", {})))
                if scope.get("path_params", {}).get("kind") in {"trips", "previews"}:
                    data["resource_kind"] = scope["path_params"]["kind"]
                # Extract IDs/status codes only. Never persist response/request bodies.
                try:
                    value = json.loads(body)
                    if isinstance(value, dict):
                        if value.get("status") in {"available", "unavailable"}:
                            data["result_status"] = value["status"]
                        if isinstance(value.get("suggestions"), list):
                            data["suggestion_count"] = len(value["suggestions"])
                        if isinstance(value.get("items"), dict):
                            statuses = [
                                item.get("status")
                                for item in value["items"].values()
                                if isinstance(item, dict)
                            ]
                            data["media_available"] = statuses.count("available")
                            data["media_unavailable"] = statuses.count("unavailable")
                        data.update(resource_identifiers(value))
                        if route.startswith("/api/planning") and data.get("id"):
                            data["task_id"] = data["id"]
                        detail = value.get("detail", value.get("error", {}))
                        if isinstance(detail, dict) and re.fullmatch(
                            r"[a-z_]{1,80}", str(detail.get("code", ""))
                        ):
                            data["code"] = detail["code"]
                        if value.get("state") in {
                            "pending",
                            "running",
                            "stopping",
                            "completed",
                            "failed",
                            "cancelled",
                            "needs_clarification",
                            "safety_blocked",
                            "provider_blocked",
                        }:
                            data["task_state"] = value["state"]
                except (ValueError, UnicodeError, TypeError):
                    pass
                if error:
                    data["error"] = error
                operation("http_failed" if error else "http_completed", data)


class ClientError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "global_error", "unhandled_rejection", "render_error", "request_failed", "product_action"
    ]
    error_type: Literal[
        "Error",
        "TypeError",
        "RangeError",
        "ReferenceError",
        "SyntaxError",
        "URIError",
        "NetworkError",
        "Unknown",
    ] = "Unknown"
    path: str = Field(default="/unknown", max_length=256)
    source: str | None = Field(default=None, max_length=160)
    line: int | None = Field(default=None, ge=0, le=10_000_000)
    column: int | None = Field(default=None, ge=0, le=10_000_000)
    request_id: UUID | None = None
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"] | None = None
    status: int | None = Field(default=None, ge=0, le=599)
    action: (
        Literal[
            "json_download_requested",
            "text_download_requested",
            "summary_copied",
            "summary_copy_fallback",
        ]
        | None
    ) = None
    resource_id: UUID | None = None


@router.post("/api/diagnostics/client-errors", status_code=202)
async def client_error(request: Request):
    from backend.app.runtime.deployment import ProductPolicySettings

    if request.headers.get("origin") != ProductPolicySettings().origin.rstrip("/"):
        raise HTTPException(403, {"code": "origin_rejected"})
    now = monotonic()
    peer = request.client.host if request.client else "unknown"
    with _bucket_lock:
        stamp, count = _buckets.pop(peer, (now, 0))
        if now - stamp >= 60:
            stamp, count = now, 0
        _buckets[peer] = (stamp, count + 1)
        while len(_buckets) > 1024:
            _buckets.popitem(last=False)
        if count >= 20:
            raise HTTPException(429, {"code": "diagnostics_rate_limited"})
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 4096:
            raise HTTPException(413, {"code": "diagnostics_size_limit"})
    try:
        report = ClientError.model_validate_json(bytes(body))
    except (ValidationError, ValueError):
        raise HTTPException(422, {"code": "invalid_diagnostic_report"}) from None
    data = report.model_dump(mode="json")
    data["path"] = route_path(report.path)
    if report.source:
        source = report.source.split("?", 1)[0].rsplit("/", 1)[-1]
        data["source"] = (
            source if re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}\.(?:js|tsx?|jsx)", source) else None
        )
    operation("client_reported", data)
    return Response(status_code=202)
