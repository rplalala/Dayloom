"""Owner-scoped explicit preview decisions and immutable saved detail."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from psycopg import Error
from pydantic import BaseModel, ConfigDict

from backend.app.product.auth import CurrentUser
from backend.app.product.saved_store import SavedStore

router = APIRouter(tags=["saved-trips"])


class SaveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiscardBody(SaveBody):
    confirmed: Literal[True]


def decide(user, preview_id, action, response):
    response.headers["Cache-Control"] = "no-store"
    try:
        decision = SavedStore().decision(user["id"], preview_id, action)
    except (Error, ValueError) as error:
        raise HTTPException(
            503,
            {
                "code": "preview_decision_failed",
                "message": "Could not confirm your decision. Check its status before retrying.",
            },
        ) from error
    if decision is None:
        raise HTTPException(404, {"code": "preview_not_found"})
    expected = "saved" if action == "save" else "discarded"
    if decision["state"] != expected or decision["outcome"] == "saved_result_deleted":
        raise HTTPException(409, {"code": "preview_already_decided", "decision": decision})
    return decision


@router.post("/api/previews/{preview_id}/save")
def save_preview(preview_id: UUID, body: SaveBody, user: CurrentUser, response: Response):
    return decide(user, preview_id, "save", response)


@router.post("/api/previews/{preview_id}/discard")
def discard_preview(preview_id: UUID, body: DiscardBody, user: CurrentUser, response: Response):
    return decide(user, preview_id, "discard", response)


@router.get("/api/trips/{trip_id}")
def read_saved(trip_id: UUID, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    detail = SavedStore().read(user["id"], trip_id)
    if detail is None:
        raise HTTPException(404, {"code": "trip_not_found"})
    return detail
