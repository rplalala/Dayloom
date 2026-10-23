"""Product HTTP/SSE adapters submit and observe durable account-owned tasks."""

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from backend.app.api.dependencies import get_date_provider
from backend.app.api.streaming import PlanningStreamingResponse
from backend.app.policies.trip_dates import MAX_TRIP_DAYS, DateProvider, create_trip_date_window
from backend.app.product.auth import CurrentUser
from backend.app.product.task_store import ACTIVE
from backend.app.product.tasks import Coordinator, Planner, TaskSubmission, submit_task
from backend.app.schemas.request import PlanningRequest

router = APIRouter(prefix="/api", tags=["product-planning"])


def submission(body, operation_key):
    if operation_key is None:
        raise HTTPException(422, {"code": "operation_key_required"})
    from pydantic import ValidationError

    try:
        return TaskSubmission(operation_key=operation_key, request=body)
    except ValidationError as error:
        raise HTTPException(422, {"code": "invalid_operation_key"}) from error


@router.post("/planning", status_code=202)
async def create_planning_result(
    body: PlanningRequest,
    user: CurrentUser,
    coordinator: Coordinator,
    planning_service: Planner,
    response: Response,
    operation_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    response.headers["Cache-Control"] = "no-store"
    task = await submit_task(submission(body, operation_key), user, coordinator, planning_service)
    if task["state"] == "completed":
        previews = await asyncio.to_thread(
            coordinator.store.previews, user["id"], task["preview_id"]
        )
        return {
            **task,
            "task_id": task["id"],
            "result": previews[0]["snapshot"] if previews else None,
            "preview_decision": preview_decision(previews),
        }
    return task


def preview_decision(previews):
    if not previews or previews[0]["state"] == "pending":
        return None
    return {key: previews[0].get(key) for key in ("id", "state", "saved_trip_id", "outcome")}


async def task_events(coordinator, owner, task_id, *, interval=1):
    revision = None
    while True:
        task = await asyncio.to_thread(coordinator.store.read, owner, task_id)
        if task is None:
            return
        if task["revision"] != revision:
            revision = task["revision"]
            yield f"event: task\ndata: {json.dumps(task, ensure_ascii=True)}\n\n"
        if task["state"] not in ACTIVE:
            if task["state"] == "completed":
                previews = await asyncio.to_thread(
                    coordinator.store.previews, owner, task["preview_id"]
                )
                payload = {
                    "type": "result",
                    "task_id": task["id"],
                    "preview_id": task["preview_id"],
                    "result": previews[0]["snapshot"] if previews else None,
                    "preview_decision": preview_decision(previews),
                }
                yield f"event: result\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"
            return
        await asyncio.sleep(interval)


@router.post("/planning/stream")
async def stream_planning_result(
    body: PlanningRequest,
    user: CurrentUser,
    coordinator: Coordinator,
    planning_service: Planner,
    operation_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    task = await submit_task(submission(body, operation_key), user, coordinator, planning_service)
    return PlanningStreamingResponse(
        task_events(coordinator, user["id"], task["id"]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store, no-transform", "X-Accel-Buffering": "no"},
    )


@router.get("/planning/date-window")
async def get_planning_date_window(
    date_provider: Annotated[DateProvider, Depends(get_date_provider)],
):
    window = create_trip_date_window(date_provider.today())
    return {
        "allowedStart": window.allowed_start.isoformat(),
        "allowedEnd": window.allowed_end.isoformat(),
        "maxTripDays": MAX_TRIP_DAYS,
    }
