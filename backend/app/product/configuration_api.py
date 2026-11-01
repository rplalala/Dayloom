"""Loopback-only management access, independent of Product account authentication."""

from ipaddress import ip_address
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from starlette.responses import JSONResponse, RedirectResponse

from backend.app.product.api_checks import CheckBusy
from backend.app.product.configuration import (
    COOKIE,
    SESSION_SECONDS,
    ConfigurationError,
    LocalConfiguration,
)

router = APIRouter(prefix="/api/config", tags=["Local configuration"])


class ConfigurationGate:
    """Keep setup usable while incomplete resources cannot serve business requests."""

    def __init__(self, app, *, ready):
        self.app, self.ready = app, ready

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        config = path == "/api/config" or path.startswith("/api/config/")
        if config:
            original_send = send

            async def no_store(message):
                if message["type"] == "http.response.start":
                    message = {
                        **message,
                        "headers": [
                            (key, value)
                            for key, value in message.get("headers", [])
                            if key.lower() != b"cache-control"
                        ]
                        + [(b"cache-control", b"no-store")],
                    }
                await original_send(message)

            send = no_store
            if scope["method"] in {"POST", "PUT"}:
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > 32768:
                        return await JSONResponse(
                            {"detail": {"code": "configuration_payload_too_large"}}, 413
                        )(scope, receive, send)
                    if not message.get("more_body", False):
                        break
                original_receive = receive
                iterator = iter([{"type": "http.request", "body": bytes(body)}])

                async def replay():
                    return next(iterator, None) or await original_receive()

                receive = replay
        if not self.ready and not config:
            if path == "/" and scope["method"] == "GET":
                return await RedirectResponse("/config")(scope, receive, send)
            if path.startswith("/api/"):
                return await JSONResponse(
                    {"detail": {"code": "local_setup_required", "configuration_url": "/config"}},
                    503,
                    headers={"Cache-Control": "no-store"},
                )(scope, receive, send)
        await self.app(scope, receive, send)


def enable_local_configuration(application, manager, *, ready):
    manager.running_ready = ready
    application.state.local_configuration = manager
    application.add_middleware(ConfigurationGate, ready=ready)


def management(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    manager = getattr(request.app.state, "local_configuration", None)
    if manager is None:
        raise HTTPException(404, {"code": "local_configuration_unavailable"})
    try:
        local = request.client is not None and ip_address(request.client.host).is_loopback
    except ValueError:
        local = False
    if not local or request.headers.get("host") != urlsplit(manager.origin).netloc:
        raise HTTPException(403, {"code": "local_access_required"})
    if request.method not in {"GET", "HEAD"} and request.headers.get("origin") != manager.origin:
        raise HTTPException(403, {"code": "origin_rejected"})
    return manager


Management = Annotated[LocalConfiguration, Depends(management)]


def unlocked(request: Request, manager: Management):
    try:
        request.state.configuration_csrf = manager.authorize(
            request.cookies.get(COOKIE),
            request.headers.get("X-CSRF-Token"),
            write=request.method not in {"GET", "HEAD"},
        )
    except ConfigurationError as error:
        raise HTTPException(error.status, {"code": error.code}) from None
    return manager


Unlocked = Annotated[LocalConfiguration, Depends(unlocked)]


class UnlockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    password: SecretStr = Field(default=SecretStr(""), max_length=128)


class AccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: str = Field(min_length=64, max_length=64)
    enabled: bool
    current_password: SecretStr = Field(default=SecretStr(""), max_length=128)
    new_password: SecretStr | None = Field(default=None, min_length=10, max_length=128)
    confirmation: SecretStr | None = Field(default=None, max_length=128)


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: str = Field(min_length=64, max_length=64)
    changes: dict[str, str] = Field(max_length=6)


class ApiCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: str = Field(min_length=64, max_length=64)
    service: Literal["all", "foundry", "openai", "google", "unsplash"]


def configuration_operation(operation):
    try:
        return operation()
    except ConfigurationError as error:
        raise HTTPException(error.status, {"code": error.code}) from None
    except Exception:
        raise HTTPException(503, {"code": "configuration_unreadable"}) from None


@router.post("/session")
def unlock(body: UnlockRequest, response: Response, manager: Management):
    try:
        session, csrf = manager.unlock(body.password.get_secret_value())
    except ConfigurationError as error:
        raise HTTPException(error.status, {"code": error.code}) from None
    response.set_cookie(
        COOKIE,
        session,
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=manager.origin.startswith("https:"),
        path="/api/config",
    )
    return {"csrf_token": csrf}


@router.get("/access")
def access(manager: Management):
    return configuration_operation(manager.access_view)


@router.put("/access")
def change_access(body: AccessRequest, response: Response, manager: Unlocked):
    result = configuration_operation(lambda: manager.set_access(
        body.revision, enabled=body.enabled,
        current_password=body.current_password.get_secret_value(),
        new_password=body.new_password.get_secret_value() if body.new_password else "",
        confirmation=body.confirmation.get_secret_value() if body.confirmation else "",
    ))
    response.delete_cookie(COOKIE, path="/api/config")
    return result


@router.get("/session")
def session(request: Request, manager: Unlocked):
    return {"csrf_token": request.state.configuration_csrf}


@router.delete("/session", status_code=204)
def lock(request: Request, response: Response, manager: Unlocked):
    with manager.lock:
        manager.sessions.pop(request.cookies.get(COOKIE), None)
    response.delete_cookie(COOKIE, path="/api/config")


@router.get("")
def configuration(manager: Unlocked):
    return configuration_operation(manager.view)


@router.put("")
def save(body: SaveRequest, manager: Unlocked):
    return configuration_operation(lambda: manager.save(body.revision, body.changes))


@router.get("/readiness")
def readiness(manager: Unlocked):
    return configuration_operation(manager.readiness)


@router.post("/check")
async def check_apis(body: ApiCheckRequest, manager: Unlocked):
    values = configuration_operation(lambda: manager.values_for_check(body.revision))
    try:
        result = await manager.api_checker.check(body.service, values)
    except CheckBusy:
        raise HTTPException(409, {"code": "api_check_in_progress"}) from None
    except Exception:
        raise HTTPException(503, {"code": "api_check_failed"}) from None
    current = configuration_operation(manager.view)
    return {**result, "revision": body.revision, "stale": current["revision"] != body.revision}
