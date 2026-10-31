"""Application-owned execution; observation never owns a planner or its cancellation."""

import asyncio
from contextlib import ExitStack, suppress
from datetime import date

from backend.app.observability.product_logs import log_context, operation, safe_error
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
            with log_context(task_id=original["id"], owner_id=owner):
                operation("task_replayed", {"state": original["state"]})
            return original
        reference_date = service.reference_date()
        service.validate(request, reference_date=reference_date)
        task, created = await asyncio.to_thread(
            self.store.accept, owner, key, request, editor, reference_date
        )
        with log_context(task_id=task["id"], owner_id=owner):
            operation("task_accepted" if created else "task_replayed", {"state": task["state"]})
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
        with log_context(reset=True):
            await self._reconcile_loop()

    async def _reconcile_loop(self):
        while True:
            try:
                await asyncio.to_thread(self.store.reconcile)
            except Exception as error:
                # A temporary storage failure cannot grant execution authority.
                operation("task_reconcile_failed", {"error": safe_error(error)})
            await asyncio.sleep(self.reconcile_seconds)

    async def _heartbeat(self, claim, observer, worker):
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
                    # Stop may arrive through another app instance. Lost durable authority
                    # also stops this owner's transport; fencing alone only rejects writes.
                    operation("task_lease_lost")
                    worker.cancel()
                    return
            except Exception as error:
                # No renewal was granted. A later attempt still checks the existing deadline.
                operation("task_heartbeat_failed", {"error": safe_error(error)})
                continue

    async def _run(self, task_id, service):
        claim, heartbeat = None, None
        diagnostics = ExitStack()
        try:
            claim = await asyncio.to_thread(self.store.claim, task_id)
            if claim is None:
                return
            diagnostics.enter_context(log_context(
                task_id=claim["id"], execution_id=claim["execution_id"],
                run_id=claim["execution_id"], owner_id=claim["owner_id"], fence=claim["fence"]
            ))
            operation("task_claimed")
            observer = ProgressObserver(developer=False, run_id=claim["execution_id"])
            heartbeat = asyncio.create_task(
                self._heartbeat(claim, observer, asyncio.current_task())
            )
            with progress_scope(observer):
                result = await service.plan(
                    PlanningRequest.model_validate(claim["request"]),
                    reference_date=claim["reference_date"]
                    if isinstance(claim["reference_date"], date)
                    else date.fromisoformat(claim["reference_date"]),
                )
            detail = generated_detail(result, PlanningRequest.model_validate(claim["request"]))
            committed = await asyncio.to_thread(self.store.complete, claim, detail)
            operation(
                "task_completed" if committed else "task_result_not_committed",
                {"preview_id": detail.id},
            )
        except asyncio.CancelledError:
            operation("task_execution_cancelled")
            if claim:
                await self._persist_failure(claim, "failed", INTERRUPTED)
            raise
        except Exception as error:
            operation("task_execution_failed", {"error": safe_error(error)})
            if claim:
                state, outcome = failure_outcome(error)
                await self._persist_failure(claim, state, outcome)
        finally:
            if heartbeat:
                heartbeat.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await heartbeat
            if claim:
                # service.plan unwinds its owned transport stack before this acknowledgement.
                # This narrow transition cannot alter completion or another execution's fence.
                with suppress(Exception):
                    acknowledged = await asyncio.to_thread(self.store.acknowledge_stop, claim)
                    if acknowledged:
                        operation("task_stop_acknowledged")
            diagnostics.close()

    async def _persist_failure(self, claim, state, outcome):
        data = {"state": state, "code": outcome.get("code")}
        try:
            committed = await asyncio.to_thread(self.store.finish, claim, state, outcome)
            operation("task_finished" if committed else "task_finish_not_committed", data)
        except Exception as error:
            operation("task_terminal_write_failed", {**data, "error": safe_error(error)})

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
