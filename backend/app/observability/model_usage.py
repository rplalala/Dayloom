"""Shared LangChain usage callbacks and request-local numeric observation."""

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tracers.context import register_configure_hook

from backend.app.observability.usage import UsageLedger, current_usage, finish_attempt

_callback = ContextVar("rtpeval_model_callback", default=None)
register_configure_hook(_callback, inheritable=True)


class ModelUsageCallback(BaseCallbackHandler):
    run_inline = True

    def __init__(self, ledger):
        self.ledger = ledger

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        params = kwargs.get("invocation_params") or {}
        self.ledger.begin(
            "model",
            "langchain",
            "chat_model",
            event_id=str(run_id),
            model=params.get("model") or params.get("model_name"),
            source="langchain_message_usage",
        )

    def on_llm_end(self, response, *, run_id, **kwargs):
        usage = None
        for group in response.generations:
            for generation in group:
                message = getattr(generation, "message", None)
                if getattr(message, "usage_metadata", None) is not None:
                    usage = message.usage_metadata
                    break
        self.ledger.finish("model", str(run_id), usage=usage)

    def on_llm_error(self, error, *, run_id, **kwargs):
        self.ledger.finish(
            "model",
            str(run_id),
            outcome="cancelled" if isinstance(error, asyncio.CancelledError) else "failed",
            error_type=type(error).__name__,
        )


@contextmanager
def observe_usage(sink):
    """Borrow existing capture or install one; always restore callbacks and hooks."""
    if current_usage.get() is not None:
        yield
        return
    ledger = UsageLedger()
    token = current_usage.set(ledger)
    callback_token = _callback.set(ModelUsageCallback(ledger))
    started, started_at = ledger.clock(), datetime.now(UTC).isoformat()
    outcome = "completed"
    try:
        yield
    except BaseException as error:
        outcome = "cancelled" if isinstance(error, asyncio.CancelledError) else "failed"
        raise
    finally:
        try:
            sink(finish_attempt(ledger, started, started_at, outcome))
        except Exception:
            from backend.app.observability.product_logs import operation

            operation("usage_collection_failed")
        finally:
            current_usage.reset(token)
            _callback.reset(callback_token)
