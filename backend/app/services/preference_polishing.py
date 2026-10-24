"""Bounded single-call rewrite presented for user review."""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Lock
from time import monotonic

from pydantic import ValidationError

from backend.app.runtime.config_models import PreferencePolishingConfig
from backend.app.runtime.token_counting import count_tokens
from backend.app.schemas.input_assistance import (
    PolishDraft,
    PolishRequest,
    PolishResponse,
)
from backend.app.services.assistance_admission import AssistanceGate
from backend.app.services.preference_polishing_prompts import (
    DRAFT_SYSTEM_PROMPT,
)


class PolishingInputLimit(RuntimeError):
    """The optional assistance envelope is smaller than normal planning input."""


class PolishingRateLimited(RuntimeError):
    """An optional model operation is already running or the daily allowance is spent."""


class PolishingDeadline(RuntimeError):
    """The optional single-call operation exceeded its bounded deadline."""


class PolishingUnavailable(RuntimeError):
    """A model or configuration problem prevented a safe suggestion."""


class PolishingInvalidResponse(RuntimeError):
    """The model produced output that violates the assistance contract."""


def _prompt_payload(request: PolishRequest) -> str:
    data = {
        "original_text": request.original_text,
        "read_only_context": request.context.model_dump(mode="json", exclude_none=True),
    }
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


class PreferencePolishingService:
    def __init__(
        self,
        client_factory: Callable,
        config: PreferencePolishingConfig | None = None,
        *,
        utc_now=lambda: datetime.now(UTC),
        now=monotonic,
    ) -> None:
        self._client_factory = client_factory
        self._config = config or PreferencePolishingConfig()
        self._utc_now = utc_now
        self._lock = Lock()
        self._day = None
        self._count = 0
        self._inflight = False
        self._gate = (
            AssistanceGate(self._config.admission, now=now) if self._config.admission else None
        )

    def _admit(self, actor: str) -> None:
        if self._gate and not self._gate.admit(actor):
            raise PolishingRateLimited()
        with self._lock:
            day = self._utc_now().date()
            if day != self._day:
                self._day, self._count = day, 0
            limit = self._config.daily_operations_per_process
            if (not self._gate and self._inflight) or (limit is not None and self._count >= limit):
                if self._gate:
                    self._gate.release(actor)
                raise PolishingRateLimited()
            self._inflight = True
            self._count += 1

    def _release(self, actor: str) -> None:
        if self._gate:
            self._gate.release(actor)
        with self._lock:
            self._inflight = False

    def _fits_model_input(self, system: str, user: str, schema) -> bool:
        total = count_tokens(system) + count_tokens(user)
        total += count_tokens(json.dumps(schema.model_json_schema(), sort_keys=True))
        return total <= self._config.model_input_tokens_per_call

    async def polish(self, request: PolishRequest, *, actor: str = "anonymous") -> PolishResponse:
        original = request.original_text
        if (
            len(original) > self._config.source_max_chars
            or count_tokens(original) > self._config.source_max_tokens
        ):
            raise PolishingInputLimit()
        draft_user = _prompt_payload(request)
        if not self._fits_model_input(DRAFT_SYSTEM_PROMPT, draft_user, PolishDraft):
            raise PolishingInputLimit()
        self._admit(actor)
        client = None
        try:
            try:
                client = self._client_factory()
            except Exception as exc:
                raise PolishingUnavailable() from exc
            try:
                async with asyncio.timeout(self._config.total_timeout_seconds):
                    draft = await asyncio.wait_for(
                        client.draft(
                            DRAFT_SYSTEM_PROMPT, draft_user, self._config.draft_output_tokens
                        ),
                        timeout=self._config.call_timeout_seconds,
                    )
                    draft = PolishDraft.model_validate(draft)
                    if draft.status != "suggested":
                        return PolishResponse(
                            status=draft.status,
                            original_text=original,
                            suggested_text=None,
                            explanation=draft.explanation,
                            questions=draft.questions,
                            client_revision=request.client_revision,
                        )
                    candidate = draft.suggested_text or ""
                    return PolishResponse(
                        status="suggested",
                        original_text=original,
                        suggested_text=candidate,
                        explanation=draft.explanation,
                        questions=[],
                        client_revision=request.client_revision,
                    )
            except TimeoutError as exc:
                raise PolishingDeadline() from exc
            except ValidationError as exc:
                raise PolishingInvalidResponse() from exc
            except ValueError as exc:
                raise PolishingUnavailable() from exc
        finally:
            try:
                if client is not None and hasattr(client, "aclose"):
                    try:
                        await client.aclose()
                    except Exception:
                        pass
            finally:
                self._release(actor)
