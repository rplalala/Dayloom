"""Atomic preview decisions and normalized saved detail, without planner dependencies."""

from uuid import uuid4

from psycopg.types.json import Jsonb

from backend.app.product.database import connect
from backend.app.product.detail import DetailDisplay, ProductDetail


class SavedRevisionConflict(Exception):
    def __init__(self, revision):
        self.revision = revision


def insert(connection, table, values):
    """Column names are application constants; all content uses bound parameters."""
    connection.execute(
        f"INSERT INTO app.{table} ({','.join(values)}) VALUES ({','.join(['%s'] * len(values))})",
        tuple(values.values()),
    )


class SavedStore:
    def __init__(self, settings=None):
        self.settings = settings

    def rename(self, owner, trip_id, title, revision):
        with connect(self.settings) as connection:
            row = connection.execute(
                "SELECT id,revision FROM app.trips WHERE owner_id=%s AND id=%s FOR UPDATE",
                (owner, trip_id),
            ).fetchone()
            if row is None:
                return None
            if row["revision"] != revision:
                raise SavedRevisionConflict(row["revision"])
            row = connection.execute(
                "UPDATE app.trips SET title=%s,revision=revision+1,updated_at=clock_timestamp() "
                "WHERE id=%s RETURNING id,title,revision",
                (title, trip_id),
            ).fetchone()
            return {**row, "id": str(row["id"])}

    def delete(self, owner, trip_id, revision):
        with connect(self.settings) as connection:
            row = connection.execute(
                "SELECT revision FROM app.trips WHERE owner_id=%s AND id=%s FOR UPDATE",
                (owner, trip_id),
            ).fetchone()
            if row is None:
                return False
            if row["revision"] != revision:
                raise SavedRevisionConflict(row["revision"])
            # Child rows cascade; the decided preview retains its original saved ID.
            connection.execute("DELETE FROM app.trips WHERE id=%s", (trip_id,))
            return True

    def decision(self, owner, preview_id, action):
        with connect(self.settings) as connection:
            row = connection.execute(
                "SELECT * FROM app.itinerary_previews WHERE owner_id=%s AND id=%s FOR UPDATE",
                (owner, preview_id),
            ).fetchone()
            if not row:
                return None
            if row["state"] == "pending":
                saved_id = None
                if action == "save":
                    detail = ProductDetail.model_validate(row["snapshot"])
                    saved_id = uuid4()
                    self._write(connection, row, saved_id, detail)
                row = connection.execute(
                    "UPDATE app.itinerary_previews SET state=%s,saved_trip_id=%s,"
                    "snapshot=NULL,original_request=NULL,media_bindings='{}',"
                    "decided_at=clock_timestamp() "
                    "WHERE id=%s RETURNING *",
                    ("saved" if action == "save" else "discarded", saved_id, preview_id),
                ).fetchone()
            exists = (
                row["saved_trip_id"]
                and connection.execute(
                    "SELECT id FROM app.trips WHERE owner_id=%s AND id=%s",
                    (owner, row["saved_trip_id"]),
                ).fetchone()
            )
            return {
                "id": str(row["id"]),
                "state": row["state"],
                "saved_trip_id": str(row["saved_trip_id"]) if row["saved_trip_id"] else None,
                "outcome": "saved_result_deleted"
                if row["state"] == "saved" and not exists
                else row["state"],
            }

    def _write(self, connection, preview, trip_id, detail):
        header = detail.model_dump(
            mode="json",
            exclude={
                "id",
                "schema_version",
                "days",
                "transfers",
                "nearby",
                "illustration_key",
                "display_tags",
            },
        )
        # Trust is server-owned. No public save body can supply itinerary or origin.
        if preview["source_kind"] == "generated_v3":
            header.update(provenance="generated", trust="generated_projection")
        for key in ("request", "completion"):
            header[key] = Jsonb(header[key]) if header[key] is not None else None
        insert(
            connection,
            "trips",
            dict(
                id=trip_id,
                owner_id=preview["owner_id"],
                source_preview_id=preview["id"],
                source_kind=preview["source_kind"],
                source_id=preview["source_id"],
                media_bindings=Jsonb(preview.get("media_bindings", {})),
                display_metadata=Jsonb(DetailDisplay.from_detail(detail).model_dump(mode="json")),
                generated_at=preview["created_at"]
                if preview["source_kind"] == "generated_v3"
                else None,
                **header,
            ),
        )
        anchors = {}
        for day_position, day in enumerate(detail.days):
            weather = (
                day.weather.model_dump(exclude={"attribution", "source_url"}) if day.weather else {}
            )
            insert(
                connection,
                "trip_weather",
                dict(
                    trip_id=trip_id,
                    position=day_position,
                    day_date=day.date,
                    has_weather=day.weather is not None,
                    **weather,
                ),
            )
            for position, activity in enumerate(day.activities):
                values = activity.model_dump(
                    mode="json", exclude={"estimated_cost", "illustration_key"}
                )
                values["cost_amount"] = (
                    activity.estimated_cost.amount if activity.estimated_cost else None
                )
                values["cost_currency"] = (
                    activity.estimated_cost.currency if activity.estimated_cost else None
                )
                insert(
                    connection,
                    "trip_activities",
                    dict(trip_id=trip_id, day_position=day_position, position=position, **values),
                )
                anchors[activity.activity_id] = (day_position, day.date, activity.time_use)
        for position, nearby in enumerate(detail.nearby):
            anchor = anchors.get(nearby.anchor_activity_id)
            resolved = (
                anchor
                and anchor[2] == "scheduled"
                and (nearby.associated_day is None or nearby.associated_day == anchor[1])
            )
            values = nearby.model_dump(
                exclude={"anchor_activity_id", "associated_day", "illustration_key"}
            )
            insert(
                connection,
                "trip_nearby",
                dict(
                    trip_id=trip_id,
                    position=position,
                    supplied_anchor_id=nearby.anchor_activity_id,
                    supplied_day=nearby.associated_day,
                    resolved_day_position=anchor[0] if resolved else None,
                    resolved_activity_id=nearby.anchor_activity_id if resolved else None,
                    **values,
                ),
            )
        for position, transfer in enumerate(detail.transfers):
            origin = anchors.get(transfer.from_activity_id)
            target = anchors.get(transfer.to_activity_id)
            if not origin or not target or origin[0] != target[0]:
                raise ValueError("Transfer endpoints must belong to one actual day")
            insert(
                connection,
                "trip_transfers",
                dict(
                    trip_id=trip_id,
                    position=position,
                    day_position=origin[0],
                    **transfer.model_dump(),
                ),
            )

    def read(self, owner, trip_id):
        with connect(self.settings) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            return self.read_connection(connection, owner, trip_id)

    def read_connection(self, connection, owner, trip_id):
        # The reader transaction keeps the header and all children in one snapshot.
        row = connection.execute(
            "SELECT * FROM app.trips WHERE owner_id=%s AND id=%s", (owner, trip_id)
        ).fetchone()
        if not row:
            return None
        detail = {
            key: row[key]
            for key in (
                "title",
                "destination",
                "start_date",
                "end_date",
                "description",
                "provenance",
                "trust",
                "request",
                "completion",
            )
        }
        display = DetailDisplay.model_validate(row.get("display_metadata", {}))
        detail.update(
            id=str(row["id"]),
            days=[],
            nearby=[],
            transfers=[],
            illustration_key=display.illustration_key,
            display_tags=display.display_tags,
        )
        days = connection.execute(
            "SELECT * FROM app.trip_weather WHERE trip_id=%s ORDER BY position", (trip_id,)
        ).fetchall()
        activities = connection.execute(
            "SELECT * FROM app.trip_activities WHERE trip_id=%s ORDER BY day_position,position",
            (trip_id,),
        ).fetchall()
        for day in days:
            weather = {
                key: day[key]
                for key in (
                    "summary",
                    "temperature_min_c",
                    "temperature_max_c",
                    "precipitation_probability_percent",
                    "max_wind_speed_kph",
                )
            }
            content = []
            for activity in activities:
                if activity["day_position"] != day["position"]:
                    continue
                value = {
                    key: activity[key]
                    for key in (
                        "activity_id",
                        "title",
                        "time_use",
                        "place_name",
                        "location",
                        "category",
                        "start_time",
                        "end_time",
                        "notes",
                        "introduction",
                    )
                }
                value["illustration_key"] = display.activities.get(activity["activity_id"])
                value["estimated_cost"] = (
                    None
                    if activity["cost_amount"] is None
                    else {"amount": activity["cost_amount"], "currency": activity["cost_currency"]}
                )
                content.append(value)
            detail["days"].append(
                {
                    "date": day["day_date"],
                    "weather": weather if day["has_weather"] else None,
                    "activities": content,
                }
            )
        for nearby in connection.execute(
            "SELECT * FROM app.trip_nearby WHERE trip_id=%s ORDER BY position", (trip_id,)
        ).fetchall():
            detail["nearby"].append(
                {
                    **{
                        key: nearby[key]
                        for key in ("place_name", "reason", "area", "uncertainty", "attribution")
                    },
                    "illustration_key": display.nearby.get(nearby["position"]),
                    "anchor_activity_id": nearby["supplied_anchor_id"],
                    "associated_day": nearby["supplied_day"],
                }
            )
        for transfer in connection.execute(
            "SELECT * FROM app.trip_transfers WHERE trip_id=%s ORDER BY position", (trip_id,)
        ).fetchall():
            detail["transfers"].append(
                {
                    key: value
                    for key, value in transfer.items()
                    if key not in {"trip_id", "position", "day_position"}
                }
            )
        return ProductDetail.model_validate(detail).model_dump(mode="json")
