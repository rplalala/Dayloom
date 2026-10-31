"""Persist standard service diagnostics without logging exception payloads or locals."""

import json
import logging
import re
import threading

from backend.app.observability.product_logs import ProductLogs, safe_error

_lock = threading.Lock()


class ServiceRedaction(logging.Filter):
    def filter(self, record):
        try:
            logs = ProductLogs()
            record.msg = logs.sanitize(record.getMessage())
            record.msg = re.sub(r"(https?://[^\s?\"]+)\?[^\s\"]+", r"\1?[REDACTED]", record.msg)
            record.msg = re.sub(r"(/[^\s?\"]+)\?[^\s\"]+", r"\1?[REDACTED]", record.msg)
            record.args = ()
            if record.exc_info:
                record.product_error = safe_error(record.exc_info[1])
                record.exc_info = None
                record.exc_text = json.dumps(record.product_error)
        except Exception:
            record.msg, record.args, record.exc_info, record.exc_text = (
                "Service diagnostic unavailable",
                (),
                None,
                None,
            )
        return True


class ProductServiceHandler(logging.Handler):
    def emit(self, record):
        if record.name.startswith("backend.app.observability.product_logs"):
            return  # Storage warnings must not recursively attempt a failing write.
        if getattr(record, "product_persisted", False):
            return
        record.product_persisted = True
        try:
            ProductLogs().event(
                "service_log",
                {
                    "logger": record.name,
                    "severity": record.levelname,
                    "message": record.getMessage(),
                    "error": getattr(record, "product_error", None),
                },
            )
        except Exception:
            pass


def configure_product_service_logs():
    """Idempotently attach after the host configures its handlers."""
    with _lock:
        for logger in (
            logging.getLogger(),
            logging.getLogger("uvicorn"),
            logging.getLogger("uvicorn.access"),
        ):
            for handler in logger.handlers:
                if not any(isinstance(f, ServiceRedaction) for f in handler.filters):
                    handler.addFilter(ServiceRedaction())
            if not any(isinstance(handler, ProductServiceHandler) for handler in logger.handlers):
                handler = ProductServiceHandler()
                handler.addFilter(ServiceRedaction())
                logger.addHandler(handler)
