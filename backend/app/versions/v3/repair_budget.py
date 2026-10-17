"""One repair ledger and monotonic deadline; local exhaustion is not global failure."""

import asyncio
import hashlib
from collections import Counter
from time import monotonic

from backend.app.runtime.cache import RequestCache


def configured_policy():
    from backend.app.runtime.config_loader import load_runtime_config

    policy = load_runtime_config().v3_repair
    if policy is None:
        raise ValueError("runtime.v3_repair is required for V3")
    return policy


class RepairLimit(RuntimeError):
    pass


class RepairBudget:
    def __init__(
        self,
        request_deadline,
        *,
        clock=monotonic,
        cache=None,
        policy=None,
        nearby_reserve=None,
        runtime_config=None,
    ):
        from backend.app.runtime.config_loader import load_runtime_config

        runtime_config = runtime_config if runtime_config is not None else load_runtime_config()
        self.rag_config = runtime_config.tripworld_discovery
        self.policy = policy if policy is not None else runtime_config.v3_repair
        if self.policy is None:
            raise ValueError("runtime.v3_repair is required for V3")
        if nearby_reserve is None:
            nearby_reserve = runtime_config.reference_discovery.deadline_seconds
        self.limits = self.policy.acquisition.model_dump(
            include={
                "google",
                "fallback",
                "embedding",
                "retrieval",
                "canonical",
                "details",
                "routes",
                "elements",
            }
        ) | {
            "model": self.policy.max_model_calls,
            "reason_compression": self.policy.reason_compression.max_calls,
            "deterministic_attempts": self.policy.max_deletion_attempts,
        }
        self.clock = clock
        self.started = clock()
        self.deadline = min(
            self.started + self.policy.timing.stage_seconds, request_deadline - nearby_reserve
        )
        self.io_deadline = self.deadline
        self.used = Counter()
        self.stops = []
        self.acquisition_audit = []
        self.round_index = 1
        self.route_phase = "post_proposal"
        self.limits["preparation_routes"] = (
            self.limits["routes"] - self.policy.acquisition.post_proposal_route_reserve
        )
        self.limits["ordinary_google"] = self.limits["google"] - self.limits["fallback"]
        self.cache = cache if cache is not None else RequestCache()
        # A new phase is not a retry opportunity, including failed pre-send attempts.
        # This does not relabel a reservation as a send or consume the new send budget.
        self.attempted = set(self.cache.attempts)

    def remaining(self):
        return max(0, self.deadline - self.clock())

    def charge(self, **charges):
        for key, amount in charges.items():
            if amount < 0 or self.used[key] + amount > self.limits[key]:
                raise RepairLimit(f"{key}_exhausted")
        self.used.update(charges)

    async def call(
        self, key, factory, *, charges, timeout=None, observed=False, unwrap=False, audit=None
    ):
        """Reuse compatible cache entries; charge failed sends, never retry a key.

        observed=True requires the provider's actual send notification. For fixture or
        non-observing ports, dispatch is conservatively counted as a send attempt.
        """
        # Reservation is checked before adapter entry and checked again at actual send.
        if "google" in charges and "fallback" not in charges:
            charges = {**charges, "ordinary_google": charges["google"]}
        if "routes" in charges and self.route_phase == "preparation":
            charges = {**charges, "preparation_routes": charges["routes"]}
        record = {
            "round": self.round_index,
            "route_phase": self.route_phase if "routes" in charges else None,
            "operation": str(key[0]),
            "key_sha256": hashlib.sha256(repr(key).encode()).hexdigest(),
            "purpose": "provider_acquisition"
            if "google" not in charges
            else "canonical_fallback"
            if "fallback" in charges
            else "feedback_target_discovery"
            if getattr(self, "feedback_kind", None) in ("no_op_patch", "no_measurable_improvement")
            else "ordinary_target_discovery",
            "budget_before": dict(self.used),
            "sent": False,
            **(audit or {}),
        }
        self.acquisition_audit.append(record)
        cached, hit = self.cache.lookup(key)
        if hit:
            self.used["cache_hits"] += 1
            record.update(outcome="cache_hit", budget_after=dict(self.used))
            return getattr(cached, "value", cached) if unwrap else cached
        if key in self.attempted or self.cache.terminal_attempt(key):
            record.update(outcome="previous_attempt", budget_after=dict(self.used))
            self.stops.append("previous_attempt")
            return None
        available = min(self.remaining(), self.io_deadline - self.clock())
        if available <= 0:
            record.update(outcome="phase_deadline", budget_after=dict(self.used))
            self.stops.append("phase_deadline")
            return None
        reasons = {
            "google": "google_search_budget_exhausted",
            "ordinary_google": "google_discovery_budget_exhausted",
            "fallback": "google_fallback_budget_exhausted",
            "details": "details_budget_exhausted",
            "routes": "routes_request_budget_exhausted",
            "elements": "routes_element_budget_exhausted",
        }
        exhausted = next((k for k, n in charges.items() if self.used[k] + n > self.limits[k]), None)
        if exhausted:
            reason = reasons.get(exhausted, f"{exhausted}_budget_exhausted")
            self.stops.append(reason)
            record.update(outcome=reason, budget_after=dict(self.used))
            return None
        self.attempted.add(key)
        try:

            async def load():
                async with asyncio.timeout(
                    min(timeout or self.policy.acquisition.provider_timeout_seconds, available)
                ):
                    value = await self.cache.dispatch(
                        key, factory, on_send=lambda: self.charge(**charges), observed=observed
                    )
                    if unwrap:
                        from backend.app.services.evidence_acquisition import _ProviderResult

                        return _ProviderResult(value=value)
                    return value

            value, _ = await self.cache.get_or_create(key, load)
            actual = getattr(value, "value", value)
            record.update(outcome="success", sent=True, budget_after=dict(self.used))
            if hasattr(actual, "candidates"):
                record["raw_hit_count"] = len(actual.candidates)
            return getattr(value, "value", value) if unwrap else value
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            from backend.app.integrations.dispatch import ProviderNotSentError

            cause = exc.__cause__ if isinstance(exc, ProviderNotSentError) else exc
            if isinstance(cause, RepairLimit):
                reason = reasons.get(str(cause).removesuffix("_exhausted"), str(cause))
            elif isinstance(exc, ProviderNotSentError):
                reason = "provider_pre_send_error"
            else:
                reason = f"{key[0]}:{type(exc).__name__}"
            record.update(
                outcome=reason, sent=self.cache.terminal_attempt(key), budget_after=dict(self.used)
            )
            self.stops.append(reason)
            return None
