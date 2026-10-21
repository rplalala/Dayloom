"""Canonical authenticated task submission and durable observation API."""

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from backend.app.api.dependencies import get_planning_service
from backend.app.policies.trip_dates import TripDatePolicyError
from backend.app.product.auth import CurrentUser
from backend.app.product.editor import EditorSnapshot
from backend.app.product.preferences import Currency
from backend.app.product.task_coordinator import TaskCoordinator
from backend.app.product.task_store import TaskConflict, TaskStore
from backend.app.schemas.request import PlanningRequest
from backend.app.services.planning import PlanningService

router = APIRouter(tags=["planning-tasks"])


class TaskSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_key: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")
    request: PlanningRequest
    editor_snapshot: EditorSnapshot | None = None


async def get_coordinator(request: Request):
    coordinator = getattr(request.app.state, "product_coordinator", None)
    if coordinator is None:
        coordinator = TaskCoordinator(TaskStore())
        request.app.state.product_coordinator = coordinator
    coordinator.start()
    return coordinator


Coordinator = Annotated[TaskCoordinator, Depends(get_coordinator)]
Planner = Annotated[PlanningService, Depends(get_planning_service)]


async def submit_task(body, user, coordinator, service):
    try:
        TypeAdapter(Currency).validate_python(body.request.budget.currency)
    except ValidationError as error:
        raise HTTPException(
            422, {"code": "unsupported_currency", "loc": ["body", "request", "budget", "currency"]}
        ) from error
    try:
        return await coordinator.submit(
            user["id"], body.operation_key, body.request, body.editor_snapshot, service
        )
    except TaskConflict as error:
        raise HTTPException(409, {"code": error.code, "task_id": error.task_id}) from error
    except TripDatePolicyError as error:
        raise HTTPException(422, error.as_detail()) from error


@router.post("/api/planning/tasks", status_code=202)
async def create_task(
    body: TaskSubmission,
    user: CurrentUser,
    coordinator: Coordinator,
    service: Planner,
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    return await submit_task(body, user, coordinator, service)


@router.get("/api/planning/tasks")
@router.get("/api/planning/tasks/recent")
async def recent_tasks(
    user: CurrentUser,
    coordinator: Coordinator,
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    operation_key: str | None = Query(None, max_length=120),
):
    response.headers["Cache-Control"] = "no-store"
    if operation_key is not None:
        task = await asyncio.to_thread(coordinator.store.read, user["id"], key=operation_key)
        return task
    return await asyncio.to_thread(coordinator.store.recent, user["id"], limit=limit)


@router.get("/api/planning/tasks/active")
async def active_task(user: CurrentUser, coordinator: Coordinator, response: Response):
    response.headers["Cache-Control"] = "no-store"
    tasks = await asyncio.to_thread(coordinator.store.recent, user["id"], active=True, limit=1)
    return tasks[0] if tasks else None


@router.get("/api/planning/tasks/{task_id}")
async def read_task(task_id: UUID, user: CurrentUser, coordinator: Coordinator, response: Response):
    response.headers["Cache-Control"] = "no-store"
    task = await asyncio.to_thread(coordinator.store.read, user["id"], task_id)
    if not task:
        raise HTTPException(404, {"code": "planning_task_not_found"})
    return task


@router.get("/api/previews")
async def pending_previews(
    user: CurrentUser,
    coordinator: Coordinator,
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    response.headers["Cache-Control"] = "no-store"
    return await asyncio.to_thread(
        coordinator.store.previews, user["id"], limit=limit, offset=offset
    )


@router.get("/api/previews/{preview_id}")
async def read_preview(
    preview_id: UUID, user: CurrentUser, coordinator: Coordinator, response: Response
):
    response.headers["Cache-Control"] = "no-store"
    previews = await asyncio.to_thread(coordinator.store.previews, user["id"], preview_id)
    if not previews:
        raise HTTPException(404, {"code": "preview_not_found"})
    return previews[0]
