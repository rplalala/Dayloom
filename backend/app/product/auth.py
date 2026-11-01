"""Cookie and API-token authentication with database-backed global revocation."""

import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg.errors import UniqueViolation
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.product.database import connect
from backend.app.product.settings import ProductSettings

router = APIRouter(prefix="/api/auth", tags=["accounts"])
password_hasher = PasswordHash.recommended()
# Equal password work for unknown accounts avoids an email-existence timing shortcut.
dummy_hash = password_hasher.hash("unusable-placeholder-password")
COOKIE = "dayloom_session"
PROTECTED_TEST_EMAIL = "admin@admin.com"


def can_delete_account(user):
    return user["email"] != PROTECTED_TEST_EMAIL


class AccountDeletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=128)
    confirmed: Literal[True]


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value):
        value = value.strip().lower()
        if value.count("@") != 1 or not all(value.split("@")) or any(c.isspace() for c in value):
            raise ValueError("Enter a valid email address")
        return value


class Registration(Credentials):
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def trim_name(cls, value):
        if not value.strip():
            raise ValueError("Enter a display name")
        return value.strip()


def display_initials(display_name: str) -> str:
    words = display_name.split()
    initials = "".join(word[0] for word in (words[:1] + words[-1:] if len(words) > 1 else words))
    return initials.upper()


def public_account(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "display_name": row["display_name"],
        "initials": display_initials(row["display_name"]),
    }


def origin_check(request: Request, settings: ProductSettings):
    if request.headers.get("origin") != settings.origin.rstrip("/"):
        raise HTTPException(403, {"code": "origin_rejected"})


def create_session(row: dict, response: Response, settings: ProductSettings) -> dict:
    now = datetime.now(UTC)
    csrf = secrets.token_urlsafe(32)
    token = jwt.encode(
        {
            "sub": str(row["id"]),
            "ver": row["token_version"],
            "csrf": csrf,
            "iat": now,
            "exp": now + timedelta(seconds=settings.session_seconds),
            "iss": "dayloom",
            "aud": "dayloom-product",
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings.secure_cookie,
        samesite="lax",
        max_age=settings.session_seconds,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {**public_account(row), "csrf_token": csrf}


def authenticated_account(request: Request) -> dict:
    """Validate account identity without granting permission for a mutation."""
    cookie = request.cookies.get(COOKIE)
    authorization = request.headers.get("authorization", "")
    bearer = authorization[7:] if authorization.startswith("Bearer ") else None
    if authorization and not bearer:
        raise HTTPException(401, {"code": "invalid_session"})
    if cookie and bearer and cookie != bearer:
        raise HTTPException(401, {"code": "conflicting_credentials"})
    token = bearer or cookie
    if not token:
        raise HTTPException(401, {"code": "login_required"})
    settings = ProductSettings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience="dayloom-product",
            issuer="dayloom",
            options={"require": ["sub", "ver", "csrf", "iat", "exp"]},
        )
        user_id = UUID(claims["sub"])
        if type(claims["ver"]) is not int or not isinstance(claims["csrf"], str):
            raise ValueError("Invalid session claims")
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(401, {"code": "session_expired"}) from exc
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise HTTPException(401, {"code": "invalid_session"}) from exc
    with connect(settings) as connection:
        row = connection.execute(
            """SELECT u.*, p.display_name FROM app.users u
            JOIN app.user_profiles p ON p.user_id = u.id WHERE u.id = %s""",
            (user_id,),
        ).fetchone()
    if not row or row["token_version"] != claims["ver"]:
        raise HTTPException(401, {"code": "session_revoked"})
    request.state.account = row
    request.state.csrf_token = claims["csrf"]
    return row


def current_user(request: Request) -> dict:
    row = authenticated_account(request)
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not request.headers.get(
        "authorization"
    ):
        origin_check(request, ProductSettings())
        supplied = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(supplied, request.state.csrf_token):
            raise HTTPException(403, {"code": "csrf_rejected"})
    return row


CurrentUser = Annotated[dict, Depends(current_user)]


@router.delete("/account", status_code=204)
def delete_account(body: AccountDeletion, response: Response, user: CurrentUser):
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM app.users WHERE id=%s FOR UPDATE", (user["id"],),
        ).fetchone()
        if row is None or row["token_version"] != user["token_version"]:
            raise HTTPException(401, {"code": "session_revoked"})
        if not can_delete_account(row):
            raise HTTPException(403, {"code": "protected_test_account"})
        if not password_hasher.verify(body.password, row["password_hash"]):
            raise HTTPException(403, {"code": "invalid_password"})
        # Task acceptance takes the same owner lock; deletion cannot race admission.
        if connection.execute(
            "SELECT 1 FROM app.planning_tasks WHERE owner_id=%s "
            "AND state IN ('pending','running','stopping') LIMIT 1", (user["id"],),
        ).fetchone():
            raise HTTPException(409, {"code": "account_tasks_active"})
        connection.execute("DELETE FROM app.users WHERE id=%s", (user["id"],))
    # The removed user invalidates its tokens. Do not expire a newer login's cookie
    # if this response reaches the browser after an account switch.
    response.headers["Cache-Control"] = "no-store"


@router.post("/register", status_code=201)
def register(body: Registration, request: Request, response: Response):
    settings = ProductSettings()
    origin_check(request, settings)
    user_id = uuid4()
    try:
        with connect(settings) as connection:
            row = connection.execute(
                """INSERT INTO app.users(id,email,password_hash)
                VALUES (%s,%s,%s) RETURNING *""",
                (user_id, body.email, password_hasher.hash(body.password)),
            ).fetchone()
            connection.execute(
                "INSERT INTO app.user_profiles(user_id,display_name) VALUES (%s,%s)",
                (user_id, body.display_name),
            )
            row["display_name"] = body.display_name
    except UniqueViolation as exc:
        raise HTTPException(409, {"code": "email_unavailable"}) from exc
    request.state.account = row
    return create_session(row, response, settings)


@router.post("/login")
def login(body: Credentials, request: Request, response: Response):
    settings = ProductSettings()
    origin_check(request, settings)
    with connect(settings) as connection:
        row = connection.execute(
            """SELECT u.*,p.display_name FROM app.users u
            JOIN app.user_profiles p ON p.user_id=u.id WHERE u.email=%s""",
            (body.email,),
        ).fetchone()
    valid = password_hasher.verify(body.password, row["password_hash"] if row else dummy_hash)
    if not row or not valid:
        raise HTTPException(401, {"code": "invalid_credentials"})
    request.state.account = row
    return create_session(row, response, settings)


@router.get("/current")
def current(request: Request, response: Response, user: CurrentUser):
    response.headers["Cache-Control"] = "no-store"
    return {**public_account(user), "csrf_token": request.state.csrf_token}


@router.post("/logout", status_code=204)
def logout(response: Response, user: CurrentUser):
    with connect() as connection:
        connection.execute(
            """UPDATE app.users SET token_version=token_version+1, updated_at=now()
            WHERE id=%s""",
            (user["id"],),
        )
    response.delete_cookie(
        COOKIE, path="/", httponly=True, samesite="lax", secure=ProductSettings().secure_cookie
    )
    response.headers["Cache-Control"] = "no-store"
