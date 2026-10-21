"""Owner-scoped incomplete drafts and the unified library read boundary."""

from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from backend.app.product.auth import CurrentUser
from backend.app.product.database import connect
from backend.app.product.editor import EditorSnapshot

router = APIRouter(tags=["drafts"])


class DraftWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    editor: EditorSnapshot

    @field_validator("title")
    @classmethod
    def title_required(cls, value):
        if not value.strip() or "\x00" in value or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("Enter a title")
        return value.strip()


class DraftUpdate(DraftWrite):
    revision: StrictInt = Field(gt=0)


class DraftRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: StrictInt = Field(gt=0)


class DraftRename(DraftRevision):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def title_required(cls, value):
        return DraftWrite.title_required(value)


def public_draft(row):
    return {
        **row,
        "id": str(row["id"]),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def owned(connection, user, draft_id, *, lock=False):
    row = connection.execute(
        "SELECT id, title, editor, revision, created_at, updated_at FROM app.planning_drafts "
        "WHERE owner_id = %s AND id = %s" + (" FOR UPDATE" if lock else ""),
        (user["id"], draft_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, {"code": "draft_not_found"})
    return row


def check_revision(row, revision):
    if row["revision"] != revision:
        raise HTTPException(409, {"code": "draft_revision_conflict", "revision": row["revision"]})


@router.post("/api/drafts", status_code=201)
def create_draft(body: DraftWrite, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    with connect() as connection:
        row = connection.execute(
            "INSERT INTO app.planning_drafts(id, owner_id, title, editor) VALUES (%s,%s,%s,%s) "
            "RETURNING id, title, editor, revision, created_at, updated_at",
            (uuid4(), user["id"], body.title, Jsonb(body.editor.model_dump())),
        ).fetchone()
    return public_draft(row)


@router.get("/api/drafts/{draft_id}")
def get_draft(draft_id: UUID, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    with connect() as connection:
        return public_draft(owned(connection, user, draft_id))


@router.put("/api/drafts/{draft_id}")
def update_draft(draft_id: UUID, body: DraftUpdate, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    with connect() as connection:
        row = owned(connection, user, draft_id, lock=True)
        check_revision(row, body.revision)
        row = connection.execute(
            "UPDATE app.planning_drafts SET title=%s, editor=%s, "
            "revision=revision+1, updated_at=now() "
            "WHERE id=%s RETURNING id, title, editor, revision, created_at, updated_at",
            (body.title, Jsonb(body.editor.model_dump()), draft_id),
        ).fetchone()
    return public_draft(row)


@router.patch("/api/drafts/{draft_id}")
def rename_draft(draft_id: UUID, body: DraftRename, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    with connect() as connection:
        row = owned(connection, user, draft_id, lock=True)
        check_revision(row, body.revision)
        row = connection.execute(
            "UPDATE app.planning_drafts SET title=%s, revision=revision+1, updated_at=now() "
            "WHERE id=%s RETURNING id, title, editor, revision, created_at, updated_at",
            (body.title, draft_id),
        ).fetchone()
    return public_draft(row)


@router.post("/api/drafts/{draft_id}/copy", status_code=201)
def copy_draft(draft_id: UUID, body: DraftRevision, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    with connect() as connection:
        source = owned(connection, user, draft_id, lock=True)
        check_revision(source, body.revision)
        row = connection.execute(
            "INSERT INTO app.planning_drafts(id, owner_id, title, editor) VALUES (%s,%s,%s,%s) "
            "RETURNING id, title, editor, revision, created_at, updated_at",
            (uuid4(), user["id"], source["title"][:113] + " (copy)", Jsonb(source["editor"])),
        ).fetchone()
    return public_draft(row)


@router.delete("/api/drafts/{draft_id}", status_code=204)
def delete_draft(draft_id: UUID, user: CurrentUser, revision: int = Query(gt=0)):
    with connect() as connection:
        row = owned(connection, user, draft_id, lock=True)
        check_revision(row, revision)
        connection.execute("DELETE FROM app.planning_drafts WHERE id=%s", (draft_id,))
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/api/library")
def library(
    user: CurrentUser,
    response: Response,
    q: str = Query(default="", max_length=100),
    sort: Literal["newest", "oldest", "name"] = "newest",
    limit: int = Query(default=24, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=10000),
):
    response.headers["Cache-Control"] = "no-store"
    ordering = {
        "newest": "updated_at DESC, id ASC",
        "oldest": "updated_at ASC, id ASC",
        "name": "lower(title) ASC, id ASC",
    }[sort]
    # Literal substring search: user '%' and '_' are characters, not wildcards.
    condition = (
        "owner_id=%s AND (strpos(lower(title),lower(%s))>0 "
        "OR strpos(lower(editor->>'destination'),lower(%s))>0)"
    )
    with connect() as connection:
        total = connection.execute(
            "SELECT count(*) AS n FROM app.planning_drafts WHERE " + condition, (user["id"], q, q)
        ).fetchone()["n"]
        rows = connection.execute(
            "SELECT id, title, editor->>'destination' AS destination, "
            "editor->>'start_date' AS start_date, editor->>'end_date' AS end_date, "
            "revision, created_at, updated_at FROM app.planning_drafts WHERE "
            + condition
            + " ORDER BY "
            + ordering
            + " LIMIT %s OFFSET %s",
            (user["id"], q, q, limit, offset),
        ).fetchall()
    return {
        "items": [
            {**public_draft(row), "kind": "draft", "source": "draft", "draft_id": str(row["id"])}
            for row in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
