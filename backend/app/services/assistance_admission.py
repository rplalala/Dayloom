"""Process-local user cooldowns and provider concurrency, without queued work."""

from threading import Lock
from time import monotonic

from backend.app.runtime.config_models import AssistanceAdmissionConfig


class AssistanceGate:
    def __init__(self, config: AssistanceAdmissionConfig, *, now=monotonic):
        self._config = config
        self._now = now
        self._lock = Lock()
        self._active: set[str] = set()
        self._until: dict[str, float] = {}

    def admit(self, actor: str) -> bool:
        with self._lock:
            now = self._now()
            self._until = {key: until for key, until in self._until.items() if until > now}
            if (
                actor in self._active
                or actor in self._until
                or len(self._active) >= self._config.max_concurrent
                or len(self._until) >= 10000
            ):
                return False
            self._active.add(actor)
            self._until[actor] = now + self._config.per_user_interval_seconds
            return True

    def release(self, actor: str) -> None:
        with self._lock:
            self._active.discard(actor)
