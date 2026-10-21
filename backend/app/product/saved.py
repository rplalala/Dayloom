"""Owner-scoped explicit preview decisions and immutable saved detail."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from psycopg import Error
from pydantic import BaseModel, ConfigDict

from backend.app.product.auth import CurrentUser
from backend.app.product.drafts import DraftRename, DraftRevision
from backend.app.product.saved_store import SavedRevisionConflict, SavedStore

router = APIRouter(tags=["saved-trips"])


class SaveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiscardBody(SaveBody):
    confirmed: Literal[True]


class DeleteBody(DraftRevision):
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


def read_saved_view(trip_id, view, user, response):
    detail = read_saved(trip_id, user, response)
    items = (
        [{"date": day["date"], "weather": day["weather"]} for day in detail["days"]]
        if view == "weather"
        else detail[view]
    )
    return {"trip_id": str(trip_id), "items": items}


@router.get("/api/trips/{trip_id}/weather")
def read_saved_weather(trip_id: UUID, user: CurrentUser, response: Response):
    return read_saved_view(trip_id, "weather", user, response)


@router.get("/api/trips/{trip_id}/nearby")
def read_saved_nearby(trip_id: UUID, user: CurrentUser, response: Response):
    return read_saved_view(trip_id, "nearby", user, response)


@router.get("/api/trips/{trip_id}/transfers")
def read_saved_transfers(trip_id: UUID, user: CurrentUser, response: Response):
    return read_saved_view(trip_id, "transfers", user, response)


@router.patch("/api/trips/{trip_id}")
def rename_saved(trip_id: UUID, body: DraftRename, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    try:
        result = SavedStore().rename(user["id"], trip_id, body.title, body.revision)
    except SavedRevisionConflict as conflict:
        raise HTTPException(
            409, {"code": "trip_revision_conflict", "revision": conflict.revision}
        ) from conflict
    if result is None:
        raise HTTPException(404, {"code": "trip_not_found"})
    return result


@router.delete("/api/trips/{trip_id}", status_code=204)
def delete_saved(trip_id: UUID, body: DeleteBody, user: CurrentUser):
    try:
        deleted = SavedStore().delete(user["id"], trip_id, body.revision)
    except SavedRevisionConflict as conflict:
        raise HTTPException(
            409, {"code": "trip_revision_conflict", "revision": conflict.revision}
        ) from conflict
    if not deleted:
        raise HTTPException(404, {"code": "trip_not_found"})
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
