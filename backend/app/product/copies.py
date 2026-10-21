"""Explicit, atomic independent snapshots with durable owner-scoped receipts."""

import hashlib
import json
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Response
from psycopg import Error
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.product.auth import CurrentUser
from backend.app.product.database import connect
from backend.app.product.detail import ProductDetail
from backend.app.product.examples import COLLECTION, example_detail
from backend.app.product.saved_store import SavedStore

router = APIRouter(prefix="/api/copies", tags=["trip-copies"])
SourceKind = Literal["copied", "example"]


class CopyIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_kind: SourceKind
    source_id: str
    operation_key: str = Field(min_length=1, max_length=120, pattern=r"\S")

    @model_validator(mode="after")
    def canonical_source(self):
        if self.source_kind == "copied":
            self.source_id = str(UUID(self.source_id))
        elif self.source_id not in (*COLLECTION, "nearby-linking"):
            raise ValueError("Unknown example")
        return self


def receipt(connection, owner, row):
    exists = connection.execute(
        "SELECT id FROM app.trips WHERE owner_id=%s AND id=%s",
        (owner, row["saved_trip_id"]),
    ).fetchone()
    return {
        "id": str(row["id"]),
        "state": "saved",
        "saved_trip_id": str(row["saved_trip_id"]),
        "outcome": "saved" if exists else "saved_result_deleted",
    }


class CopyStore:
    def accept(self, owner, intent):
        fingerprint = hashlib.sha256(
            json.dumps(
                [str(owner), intent.source_kind, intent.source_id], separators=(",", ":")
            ).encode()
        ).hexdigest()
        with connect() as connection:
            # Same-owner intents serialize across application instances. Source row locking
            # then coordinates snapshot reads with independent title/delete mutations.
            connection.execute("SELECT id FROM app.users WHERE id=%s FOR NO KEY UPDATE", (owner,))
            row = connection.execute(
                "SELECT * FROM app.itinerary_previews WHERE owner_id=%s "
                "AND source_kind=%s AND operation_key=%s FOR UPDATE",
                (owner, intent.source_kind, intent.operation_key),
            ).fetchone()
            if row:
                if row["fingerprint"] != fingerprint:
                    raise HTTPException(409, {"code": "operation_key_conflict"})
                return receipt(connection, owner, row)
            bindings = {}
            if intent.source_kind == "example":
                detail = example_detail(intent.source_id)
            else:
                source = connection.execute(
                    "SELECT * FROM app.trips WHERE owner_id=%s AND id=%s FOR UPDATE",
                    (owner, intent.source_id),
                ).fetchone()
                if source is None:
                    raise HTTPException(404, {"code": "trip_not_found"})
                detail = ProductDetail.model_validate(
                    SavedStore().read_connection(connection, owner, intent.source_id)
                )
                bindings = source.get("media_bindings", {})
            detail.title += " (copy)"
            preview_id, trip_id = uuid4(), uuid4()
            row = connection.execute(
                "INSERT INTO app.itinerary_previews(id,owner_id,source_kind,source_id,"
                "operation_key,fingerprint,state,saved_trip_id,decided_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,'saved',%s,clock_timestamp()) RETURNING *",
                (
                    preview_id,
                    owner,
                    intent.source_kind,
                    intent.source_id,
                    intent.operation_key,
                    fingerprint,
                    trip_id,
                ),
            ).fetchone()
            # Bindings remain private to the normalized writer; decided receipts are empty.
            SavedStore()._write(connection, {**row, "media_bindings": bindings}, trip_id, detail)
            return receipt(connection, owner, row)

    def lookup(self, owner, kind, key):
        with connect() as connection:
            row = connection.execute(
                "SELECT * FROM app.itinerary_previews WHERE owner_id=%s "
                "AND source_kind=%s AND operation_key=%s",
                (owner, kind, key),
            ).fetchone()
            return receipt(connection, owner, row) if row else None


@router.post("")
def copy_trip(body: CopyIntent, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    try:
        return CopyStore().accept(user["id"], body)
    except (Error, ValueError) as error:
        raise HTTPException(
            503,
            {
                "code": "copy_unconfirmed",
                "message": "Check copy status before explicitly retrying with the same key.",
            },
        ) from error


@router.get("/{source_kind}/{operation_key}")
def lookup_copy(source_kind: SourceKind, operation_key: str, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    result = CopyStore().lookup(user["id"], source_kind, operation_key)
    if result is None:
        raise HTTPException(404, {"code": "copy_not_found"})
    return result
