"""Authenticated owner defaults; planning requests never consult this boundary."""

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.product.auth import CurrentUser, can_delete_account, display_initials
from backend.app.product.database import connect
from backend.app.product.preferences import Currency, Interest, Pace, Transport

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=80)
    currency: Currency
    interests: list[Interest] = Field(max_length=64)
    pace: Pace | None
    transport: list[Transport] = Field(max_length=64)
    notes: str = Field(max_length=24000)

    @field_validator("display_name")
    @classmethod
    def name(cls, value):
        if not value.strip():
            raise ValueError("Enter a display name")
        return value.strip()

    @field_validator("interests", "transport")
    @classmethod
    def unique(cls, value):
        return list(dict.fromkeys(value))


def public_profile(row, user):
    return {
        "display_name": row["display_name"],
        "initials": display_initials(row["display_name"]),
        "can_delete_account": can_delete_account(user),
        **{key: row[key] for key in ("currency", "interests", "pace", "transport", "notes")},
    }


@router.get("")
def read_profile(response: Response, user: CurrentUser):
    response.headers["Cache-Control"] = "no-store"
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM app.user_profiles WHERE user_id=%s", (user["id"],)
        ).fetchone()
    return public_profile(row, user)


@router.put("")
def update_profile(body: ProfileUpdate, response: Response, user: CurrentUser):
    response.headers["Cache-Control"] = "no-store"
    with connect() as connection:
        row = connection.execute(
            """UPDATE app.user_profiles SET display_name=%s,currency=%s,interests=%s,
            pace=%s,transport=%s,notes=%s,updated_at=now() WHERE user_id=%s RETURNING *""",
            (
                body.display_name,
                body.currency,
                body.interests,
                body.pace,
                body.transport,
                body.notes,
                user["id"],
            ),
        ).fetchone()
    return public_profile(row, user)
