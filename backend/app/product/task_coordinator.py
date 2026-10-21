"""Application-owned execution; observation never owns a planner or its cancellation."""

import asyncio
from contextlib import suppress
from datetime import date

from backend.app.observability.progress import MESSAGES, ProgressObserver, progress_scope
from backend.app.product.preview_projection import generated_detail
from backend.app.product.task_outcomes import failure_outcome
from backend.app.product.task_store import INTERRUPTED, TaskConflict, request_fingerprint
from backend.app.schemas.request import PlanningRequest


class TaskCoordinator:
    def __init__(self, store, *, schedule=None, heartbeat_seconds=5, reconcile_seconds=10):
        self.store, self.schedule = store, schedule
        self.heartbeat_seconds, self.reconcile_seconds = heartbeat_seconds, reconcile_seconds
        self.workers = set()
        self.submissions = set()
        self.reconciler = None
        self.closed = False

    async def submit(self, owner, key, request, editor, service):
        if self.closed:
            raise RuntimeError("The application is shutting down")
        operation = asyncio.create_task(
            self._accept_and_launch(owner, key, request, editor, service)
        )
        self.submissions.add(operation)

        def settled(task):
            self.submissions.discard(task)
            if not task.cancelled():
                task.exception()  # Observe detached failures without logging private details.

        operation.add_done_callback(settled)
        return await asyncio.shield(operation)

    async def _accept_and_launch(self, owner, key, request, editor, service):
        # Validate without constructing external dependencies; only confirmed request executes.
        original = await asyncio.to_thread(self.store.read, owner, key=key)
        if original:
            if request_fingerprint(
                PlanningRequest.model_validate(original["request"])
            ) != request_fingerprint(request):
                raise TaskConflict("operation_key_conflict", original["id"])
            return original
        reference_date = service.reference_date()
        service.validate(request, reference_date=reference_date)
        task, created = await asyncio.to_thread(
            self.store.accept, owner, key, request, editor, reference_date
        )
        self.start()
        if created:
            if self.schedule:
                self.schedule(lambda: self.launch(task["id"], service))
            else:
                self.launch(task["id"], service)
        return task

    def start(self):
        if self.reconciler is None and not self.closed:
            self.reconciler = asyncio.create_task(self._reconcile())

    def launch(self, task_id, service):
        if self.closed:
            return
        task = asyncio.create_task(self._run(task_id, service))
        self.workers.add(task)
        task.add_done_callback(self.workers.discard)

    async def _reconcile(self):
        while True:
            try:
                await asyncio.to_thread(self.store.reconcile)
            except Exception:
                # A temporary storage failure cannot grant execution authority.
                pass
            await asyncio.sleep(self.reconcile_seconds)

    async def _heartbeat(self, claim, observer):
        while True:
            await asyncio.sleep(self.heartbeat_seconds)
            # Coalesce bounded public observations; browsers each read durable snapshots.
            progress = None
            while observer.buffer:
                event = observer.buffer.popleft()
                if event["type"] == "stage":
                    progress = {
                        "stage": event["stage"] if event["stage"] in MESSAGES else "planning",
                        "message": event["message"],
                        "status": event["status"],
                    }
            try:
                if not await asyncio.to_thread(self.store.renew, claim, progress):
                    return
            except Exception:
                # No renewal was granted. A later attempt still checks the existing deadline.
                continue

    async def _run(self, task_id, service):
        claim, heartbeat = None, None
        try:
            claim = await asyncio.to_thread(self.store.claim, task_id)
            if claim is None:
                return
            observer = ProgressObserver(developer=False)
            heartbeat = asyncio.create_task(self._heartbeat(claim, observer))
            with progress_scope(observer):
                result = await service.plan(
                    PlanningRequest.model_validate(claim["request"]),
                    reference_date=claim["reference_date"]
                    if isinstance(claim["reference_date"], date)
                    else date.fromisoformat(claim["reference_date"]),
                )
            detail = generated_detail(result, PlanningRequest.model_validate(claim["request"]))
            await asyncio.to_thread(self.store.complete, claim, detail)
        except asyncio.CancelledError:
            if claim:
                with suppress(Exception):
                    await asyncio.to_thread(self.store.finish, claim, "failed", INTERRUPTED)
            raise
        except Exception as error:
            if claim:
                state, outcome = failure_outcome(error)
                with suppress(Exception):
                    await asyncio.to_thread(self.store.finish, claim, state, outcome)
        finally:
            if heartbeat:
                heartbeat.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await heartbeat

    async def close(self):
        self.closed = True
        tasks = (
            list(self.workers)
            + list(self.submissions)
            + ([self.reconciler] if self.reconciler else [])
        )
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
