"""Short atomic Product task transitions. Database authority survives app instances."""

import hashlib
import json
from datetime import timedelta
from uuid import uuid4

from psycopg.types.json import Jsonb

from backend.app.product.database import connect

ACTIVE = ("pending", "running", "stopping")
INTERRUPTED = {
    "code": "planning_interrupted",
    "message": "Planning was interrupted. Your submitted brief is retained.",
    "action": "Review your brief and explicitly generate again.",
}
CANCELLED = {
    "code": "planning_cancelled",
    "message": "Planning stopped. Your submitted brief is retained.",
    "action": "Review your brief and explicitly generate again when you are ready.",
}
PUBLIC = (
    "id",
    "state",
    "revision",
    "progress",
    "outcome",
    "request",
    "editor_snapshot",
    "preview_id",
    "created_at",
    "updated_at",
)


def public_task(row):
    return {
        key: str(value)
        if key in {"id", "preview_id"} and value is not None
        else value.isoformat()
        if key in {"created_at", "updated_at"}
        else value
        for key in PUBLIC
        for value in [row[key]]
    }


def request_fingerprint(request):
    data = request.model_dump(mode="json")
    # Money semantics, rather than insignificant Decimal scale, identify the request.
    amount = request.budget.amount
    if amount:
        # Exact tuple arithmetic avoids context rounding and enormous fixed-point strings.
        _, digits, exponent = amount.as_tuple()
        end = len(digits)
        while digits[end - 1] == 0:
            end -= 1
        coefficient = "".join(str(digit) for digit in digits[:end])
        data["budget"]["amount"] = f"{coefficient}e{exponent + len(digits) - end}"
    else:
        data["budget"]["amount"] = "0"
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class TaskConflict(Exception):
    def __init__(self, code, task_id):
        self.code, self.task_id = code, str(task_id)


class TaskStore:
    def __init__(self, settings=None, *, clock=None, pending_seconds=30, lease_seconds=30):
        self.settings, self.clock = settings, clock
        self.pending_seconds, self.lease_seconds = pending_seconds, lease_seconds

    def now(self, connection):
        # Called after acquiring the row/account lock, never transaction-start now().
        return (
            self.clock()
            if self.clock
            else connection.execute("SELECT clock_timestamp() AS value").fetchone()["value"]
        )

    def reconcile(self, owner=None):
        with connect(self.settings) as connection:
            condition = "state IN ('pending','running','stopping')"
            args = ()
            if owner is not None:
                condition += " AND owner_id=%s"
                args = (owner,)
            rows = connection.execute(
                "SELECT * FROM app.planning_tasks WHERE " + condition + " FOR UPDATE", args
            ).fetchall()
            for row in rows:
                self._recover(connection, row)

    def _recover(self, connection, row):
        deadline = row["pending_deadline"] if row["state"] == "pending" else row["lease_deadline"]
        if row["state"] in ACTIVE and deadline <= self.now(connection):
            connection.execute(
                "UPDATE app.planning_tasks SET state='failed',outcome=%s,fence=fence+1,"
                "revision=revision+1,updated_at=%s WHERE id=%s",
                (Jsonb(INTERRUPTED), self.now(connection), row["id"]),
            )
            return True
        return False

    def accept(self, owner, key, request, editor, reference_date):
        fingerprint = request_fingerprint(request)
        with connect(self.settings) as connection:
            # Account row serializes first submissions, operation replays and slot recovery.
            # NO KEY UPDATE still serializes submissions, while remaining compatible
            # with the owner KEY SHARE needed by an independently completing preview.
            connection.execute("SELECT id FROM app.users WHERE id=%s FOR NO KEY UPDATE", (owner,))
            old = connection.execute(
                "SELECT * FROM app.planning_tasks WHERE owner_id=%s "
                "AND operation_key=%s FOR UPDATE",
                (owner, key),
            ).fetchone()
            if old:
                if old["fingerprint"] != fingerprint:
                    raise TaskConflict("operation_key_conflict", old["id"])
                if self._recover(connection, old):
                    old = connection.execute(
                        "SELECT * FROM app.planning_tasks WHERE id=%s", (old["id"],)
                    ).fetchone()
                return public_task(old), False
            active = connection.execute(
                "SELECT * FROM app.planning_tasks WHERE owner_id=%s AND state IN "
                "('pending','running','stopping') FOR UPDATE",
                (owner,),
            ).fetchone()
            if active and not self._recover(connection, active):
                raise TaskConflict("planning_task_active", active["id"])
            now = self.now(connection)
            row = connection.execute(
                "INSERT INTO app.planning_tasks(id,owner_id,operation_key,fingerprint,request,"
                "editor_snapshot,reference_date,state,pending_deadline,created_at,updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s,%s) RETURNING *",
                (
                    uuid4(),
                    owner,
                    key,
                    fingerprint,
                    Jsonb(request.model_dump(mode="json")),
                    Jsonb(editor.model_dump()) if editor else None,
                    reference_date,
                    now + timedelta(seconds=self.pending_seconds),
                    now,
                    now,
                ),
            ).fetchone()
            return public_task(row), True

    def read(self, owner, task_id=None, *, key=None):
        self.reconcile(owner)
        with connect(self.settings) as connection:
            column, value = ("operation_key", key) if key is not None else ("id", task_id)
            row = connection.execute(
                "SELECT * FROM app.planning_tasks WHERE owner_id=%s AND " + column + "=%s",
                (owner, value),
            ).fetchone()
            return public_task(row) if row else None

    def recent(self, owner, *, active=False, limit=20):
        self.reconcile(owner)
        with connect(self.settings) as connection:
            rows = connection.execute(
                "SELECT * FROM app.planning_tasks WHERE owner_id=%s"
                + (" AND state IN ('pending','running','stopping')" if active else "")
                + " ORDER BY created_at DESC,id LIMIT %s",
                (owner, limit),
            ).fetchall()
            return [public_task(row) for row in rows]

    def claim(self, task_id):
        with connect(self.settings) as connection:
            row = connection.execute(
                "SELECT * FROM app.planning_tasks WHERE id=%s FOR UPDATE", (task_id,)
            ).fetchone()
            if not row or row["state"] != "pending" or self._recover(connection, row):
                return None
            return connection.execute(
                "UPDATE app.planning_tasks SET state='running',execution_id=%s,fence=fence+1,"
                "lease_deadline=%s,revision=revision+1,updated_at=%s,progress=%s WHERE id=%s "
                "RETURNING *",
                (
                    uuid4(),
                    self.now(connection) + timedelta(seconds=self.lease_seconds),
                    self.now(connection),
                    Jsonb({"stage": "starting", "message": "Preparing your itinerary"}),
                    task_id,
                ),
            ).fetchone()

    def stop(self, owner, task_id):
        with connect(self.settings) as connection:
            row = connection.execute(
                "SELECT * FROM app.planning_tasks WHERE owner_id=%s AND id=%s FOR UPDATE",
                (owner, task_id),
            ).fetchone()
            if not row:
                return None
            recovered = self._recover(connection, row)
            if not recovered and row["state"] in {"pending", "running"}:
                pending = row["state"] == "pending"
                connection.execute(
                    "UPDATE app.planning_tasks SET state=%s,outcome=%s,progress=%s,"
                    "fence=fence+%s,revision=revision+1,updated_at=%s WHERE id=%s",
                    (
                        "cancelled" if pending else "stopping",
                        Jsonb(CANCELLED) if pending else None,
                        Jsonb(
                            {
                                "stage": "cancelled" if pending else "stopping",
                                "message": "Planning stopped" if pending else "Stopping planning…",
                            }
                        ),
                        1 if pending else 0,
                        self.now(connection),
                        task_id,
                    ),
                )
            return public_task(
                connection.execute(
                    "SELECT * FROM app.planning_tasks WHERE id=%s", (task_id,)
                ).fetchone()
            )

    def acknowledge_stop(self, claim):
        """Only the live execution owner can acknowledge its completed transport cleanup."""
        with connect(self.settings) as connection:
            row = connection.execute(
                "SELECT * FROM app.planning_tasks WHERE id=%s FOR UPDATE", (claim["id"],)
            ).fetchone()
            if not (
                row
                and row["state"] == "stopping"
                and row["execution_id"] == claim["execution_id"]
                and row["fence"] == claim["fence"]
                and row["lease_deadline"] > self.now(connection)
            ):
                return False
            connection.execute(
                "UPDATE app.planning_tasks SET state='cancelled',outcome=%s,progress=%s,"
                "fence=fence+1,revision=revision+1,updated_at=%s WHERE id=%s",
                (
                    Jsonb(CANCELLED),
                    Jsonb({"stage": "cancelled", "message": "Planning stopped"}),
                    self.now(connection),
                    claim["id"],
                ),
            )
            return True

    def _authorized(self, connection, claim):
        row = connection.execute(
            "SELECT * FROM app.planning_tasks WHERE id=%s FOR UPDATE", (claim["id"],)
        ).fetchone()
        return (
            row
            if (
                row
                and row["state"] == "running"
                and row["execution_id"] == claim["execution_id"]
                and row["fence"] == claim["fence"]
                and row["lease_deadline"] > self.now(connection)
            )
            else None
        )

    def renew(self, claim, progress=None):
        with connect(self.settings) as connection:
            if not self._authorized(connection, claim):
                return False
            connection.execute(
                "UPDATE app.planning_tasks SET lease_deadline=%s,updated_at=%s"
                + (",progress=%s,revision=revision+1" if progress else "")
                + " WHERE id=%s",
                (
                    self.now(connection) + timedelta(seconds=self.lease_seconds),
                    self.now(connection),
                    *([Jsonb(progress)] if progress else []),
                    claim["id"],
                ),
            )
            return True

    def finish(self, claim, state, outcome):
        with connect(self.settings) as connection:
            if not self._authorized(connection, claim):
                return False
            connection.execute(
                "UPDATE app.planning_tasks SET state=%s,outcome=%s,"
                "revision=revision+1,fence=fence+1,updated_at=%s WHERE id=%s",
                (state, Jsonb(outcome), self.now(connection), claim["id"]),
            )
            return True

    def complete(self, claim, detail):
        with connect(self.settings) as connection:
            if not self._authorized(connection, claim):
                return False
            connection.execute(
                "INSERT INTO app.itinerary_previews(id,owner_id,source_task_id,"
                "source_kind,operation_key,fingerprint,snapshot,original_request) "
                "VALUES (%s,%s,%s,'generated_v3',%s,%s,%s,%s)",
                (
                    detail.id,
                    claim["owner_id"],
                    claim["id"],
                    claim["operation_key"],
                    claim["fingerprint"],
                    Jsonb(detail.model_dump(mode="json")),
                    Jsonb(claim["request"]),
                ),
            )
            connection.execute(
                "UPDATE app.planning_tasks SET state='completed',preview_id=%s,"
                "revision=revision+1,fence=fence+1,updated_at=%s,progress=%s WHERE id=%s",
                (
                    detail.id,
                    self.now(connection),
                    Jsonb({"stage": "completed", "message": "Your itinerary preview is ready"}),
                    claim["id"],
                ),
            )
            return True

    def previews(self, owner, preview_id=None, *, limit=50, offset=0):
        with connect(self.settings) as connection:
            rows = connection.execute(
                "SELECT id,source_task_id,state,saved_trip_id,"
                + (
                    "snapshot,"
                    if preview_id
                    else "snapshot->>'title' AS title,snapshot->>'destination' AS destination,"
                )
                + "created_at FROM app.itinerary_previews WHERE owner_id=%s"
                + (" AND id=%s" if preview_id else " AND state='pending'")
                + " ORDER BY created_at DESC,id LIMIT %s OFFSET %s",
                (owner, preview_id, 1, 0) if preview_id else (owner, limit, offset),
            ).fetchall()
            return [
                {
                    **row,
                    "id": str(row["id"]),
                    "source_task_id": str(row["source_task_id"]) if row["source_task_id"] else None,
                    "saved_trip_id": str(row["saved_trip_id"]) if row["saved_trip_id"] else None,
                    "created_at": row["created_at"].isoformat(),
                }
                for row in rows
            ]
