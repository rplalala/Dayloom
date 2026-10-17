"""Versioned tools wire maps local clocks without changing historical explicit offsets."""

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from backend.app.llm.azure_foundry.dto import (
    FoundryDateTimeDTO,
    FoundryPrimaryActivityDTO,
    FoundryPrimaryItineraryDTO,
)
from backend.app.llm.azure_foundry.mapping import map_foundry_datetime
from backend.app.policies.schedule_time import (
    ScheduleTimeContext,
    local_datetime,
    validate_endpoint,
)
from backend.app.versions.v3.repair_models import Operation

TIME_WIRE_VERSION = "tools_civil_time_1"


class FoundryCivilDateTimeDTO(FoundryDateTimeDTO):
    utc_offset: str | None


class FoundryCivilActivityDTO(FoundryPrimaryActivityDTO):
    start_time: FoundryCivilDateTimeDTO
    end_time: FoundryCivilDateTimeDTO


class FoundryCivilDayDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    date: str
    activities: list[FoundryCivilActivityDTO]


class FoundryCivilItineraryDTO(FoundryPrimaryItineraryDTO):
    days: list[FoundryCivilDayDTO]


class FoundryCivilEditDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Operation
    activity_id: str | None
    date: str
    place_id: str | None
    start_time: str | None
    end_time: str | None


class FoundryCivilDispositionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    target_id: str
    disposition: Literal[
        "proposed", "unresolved", "needs_evidence", "competing_candidate", "not_attempted"
    ]
    reason: str


class FoundryCivilPatchDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    edits: list[FoundryCivilEditDTO]
    target_dispositions: list[FoundryCivilDispositionDTO]


def primary_transport_schema(system_prompt):
    return (
        FoundryCivilItineraryDTO
        if TIME_WIRE_VERSION in system_prompt
        else FoundryPrimaryItineraryDTO
    )


class ToolsTimeProjection:
    def __init__(self, context, activities=()):
        self.context = context
        self.activities = {a["activity_id"]: a.get("source_place_id") for a in activities}

    @classmethod
    def primary(cls, prompt):
        boundary = prompt.rfind("</travel_requirements>")
        start = prompt.rfind("<external_evidence>\n", max(0, boundary))
        if start < 0:
            raise ValueError("Missing application time context")
        data, _ = json.JSONDecoder().raw_decode(prompt[start + len("<external_evidence>\n") :])
        return cls(
            ScheduleTimeContext(
                data.get("places", []), default_zone=data.get("weather", {}).get("timezone")
            )
        )

    @classmethod
    def repair(cls, payload):
        context = payload.get("schedule_time_context")
        if not context or context.get("version") != TIME_WIRE_VERSION:
            return None
        return cls(
            ScheduleTimeContext(context["places"]),
            [*payload.get("editable_activities", []), *payload.get("protected_activities", [])],
        )

    def primary_result(self, payload):
        value = FoundryCivilItineraryDTO.model_validate(payload).model_dump(mode="json")
        for day in value["days"]:
            for activity in day["activities"]:
                zone = self.context.zone_for(activity["source_place_id"])
                for key in ("start_time", "end_time"):
                    endpoint = activity[key]
                    if endpoint["utc_offset"] is None:
                        mapped = local_datetime(endpoint["date"], endpoint["time"], zone)
                        offset = mapped.strftime("%z")
                        endpoint["utc_offset"] = offset[:3] + ":" + offset[3:]
                    else:
                        mapped = map_foundry_datetime(
                            FoundryDateTimeDTO.model_validate(endpoint), field_path=key
                        )
                        validate_endpoint(mapped, zone, activity_id=activity["activity_id"])
        return value

    def repair_result(self, payload):
        value = FoundryCivilPatchDTO.model_validate(payload).model_dump(mode="json")
        for edit in value["edits"]:
            pid = edit.get("place_id") or self.activities.get(edit.get("activity_id"))
            zone = self.context.zone_for(pid)
            for key in ("start_time", "end_time"):
                if edit.get(key) is None:
                    continue
                parsed = datetime.fromisoformat(edit[key])
                if parsed.utcoffset() is None:
                    parsed = local_datetime(
                        parsed.date().isoformat(), parsed.time().isoformat(), zone
                    )
                else:
                    validate_endpoint(parsed, zone, activity_id=edit.get("activity_id"))
                edit[key] = parsed.isoformat()
        return value
