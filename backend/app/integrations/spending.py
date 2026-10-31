"""Request-local, conservative USD reservations at the HTTP send boundary.

Rates deliberately exceed list prices for model tokens and Places. Failed or
unaccounted sends retain their full reservation. Web search is explicitly excluded
from dollar admission and totals. No estimate truncates user input.
"""

import json
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal

from backend.app.runtime.model_limits import (
    FOUNDRY_LUNA_CONTEXT_TOKENS,
    FOUNDRY_LUNA_MAX_OUTPUT_TOKENS,
)

_active = ContextVar("generation_spending", default=None)
D = Decimal


class SpendingLimitError(RuntimeError):
    """The next request has no affordable, recognized charge envelope."""


class SpendingBudget:
    def __init__(self, limit_usd):
        self.limit_usd = D(str(limit_usd))
        if not self.limit_usd.is_finite() or self.limit_usd <= 0:
            raise ValueError("A positive finite USD allowance is required")
        self.reserved_usd = D(0)
        self.events = []
        self.excluded_operations = set()
        self.blocked = False

    @contextmanager
    def activate(self):
        if _active.get() is not None:
            raise ValueError("Nested spending budgets would split the allowance")
        token = _active.set(self)
        try:
            yield self
        finally:
            _active.reset(token)

    def reserve(self, amount, operation):
        if self.blocked or self.reserved_usd + amount > self.limit_usd:
            self.blocked = True
            raise SpendingLimitError("generation_spending_limit: request not sent")
        self.reserved_usd += amount
        event = {
            "operation": operation,
            "reserved_usd": str(amount),
            "charged_upper_usd": str(amount),
        }
        self.events.append(event)
        return event

    def settle(self, event, upper):
        reserved = D(event["reserved_usd"])
        if upper > reserved:
            self.blocked = True
            raise SpendingLimitError("provider_usage_exceeded_reserved_envelope")
        self.reserved_usd -= reserved - upper
        event["charged_upper_usd"] = str(upper)
        event["usage_accounted"] = True

    def snapshot(self):
        return {
            "limit_usd": str(self.limit_usd),
            "charged_upper_usd": str(self.reserved_usd),
            "blocked": self.blocked,
            "events": self.events,
            "excluded_operations": sorted(self.excluded_operations),
        }


def current_spending_budget():
    return _active.get()


def _quote(request):
    host, path = request.url.host, request.url.path
    body = json.loads(request.content) if request.content else {}
    if host == "places.googleapis.com" and path.startswith("/v1/places"):
        if "/media" in path:
            raise SpendingLimitError("Media is outside the generation allowance")
        return D(".04"), "places", None
    if host == "routes.googleapis.com" and path == "/distanceMatrix/v2:computeRouteMatrix":
        # Only the existing Essentials matrix shape is admitted at this tariff.
        if body.get("routingPreference", "TRAFFIC_UNAWARE") != "TRAFFIC_UNAWARE" or (
            set(body)
            - {"origins", "destinations", "travelMode", "departureTime", "routingPreference"}
        ):
            raise SpendingLimitError("Unpriced route options")
        elements = len(body["origins"]) * len(body["destinations"])
        return D(elements) * D(".005"), "routes", None
    if host.endswith(".open-meteo.com") and request.method == "GET":
        return D(0), "weather", None
    if host == "api.openai.com" and path == "/v1/embeddings":
        if body.get("model") != "text-embedding-3-small":
            raise SpendingLimitError("Unpriced embedding model")
        # The endpoint permits at most 300,000 input tokens per request.
        return D(".006"), "embedding", None
    azure = host.endswith(
        (".openai.azure.com", ".services.ai.azure.com", ".cognitiveservices.azure.com")
    )
    if path.endswith("/responses") and (azure or host == "api.openai.com"):
        tools = body.get("tools", [])
        if (
            request.method == "POST"
            and isinstance(tools, list)
            and len(tools) == 1
            and isinstance(tools[0], dict)
            and tools[0].get("type") == "web_search"
        ):
            # Exclusion is not a zero-dollar quote. Adapter time/call bounds remain.
            return None
        outputs = body.get("max_output_tokens")
        if not isinstance(outputs, int) or isinstance(outputs, bool) or outputs < 1:
            raise SpendingLimitError("An explicit supported output ceiling is required")
        if body.get("stream") or body.get("background") or body.get("previous_response_id"):
            raise SpendingLimitError("Unpriced response execution mode")
        if body.get("service_tier", "default") not in ("default", "auto"):
            raise SpendingLimitError("Unpriced service tier")
        if azure and body.get("model") == "gpt-6-luna" and not body.get("tools"):
            if outputs > FOUNDRY_LUNA_MAX_OUTPUT_TOKENS:
                raise SpendingLimitError("Output exceeds the supported Foundry model ceiling")
            # Full published context, not a local tokenizer estimate. $1/$2 per
            # million exceeds verified Global Standard long-context/cache rates.
            rates = (D("1"), D("2"), D(0))
            amount = (D(FOUNDRY_LUNA_CONTEXT_TOKENS) + D(outputs) * 2) / 1000000
            return amount, "foundry_model", rates
    raise SpendingLimitError("No verified tariff for this external request")


def install_spend_hooks(client):
    """Install once; hooks are inert outside an explicitly activated budget."""
    if not isinstance(getattr(client, "event_hooks", None), dict):
        return
    if getattr(client, "_dayloom_spend_hooks", False):
        return
    client._dayloom_spend_hooks = True

    async def sent(request):
        budget = _active.get()
        if budget is None:
            return
        try:
            quote = _quote(request)
            if quote is None:
                budget.excluded_operations.add("web_search")
                return
            amount, operation, rates = quote
            event = budget.reserve(amount, operation)
        except Exception:
            budget.blocked = True
            raise
        request.extensions["dayloom_spending"] = (budget, event, rates)

    async def received(response):
        reservation = response.request.extensions.pop("dayloom_spending", None)
        if not reservation or response.status_code != 200 or reservation[2] is None:
            return
        budget, event, (input_rate, output_rate, fixed) = reservation
        await response.aread()
        try:
            data = response.json()
            usage = data["usage"]
            inputs, outputs = usage["input_tokens"], usage["output_tokens"]
            if data.get("status") != "completed" or any(
                not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in (inputs, outputs)
            ):
                return
        except (ValueError, KeyError, TypeError):
            return
        upper = (D(inputs) * input_rate + D(outputs) * output_rate) / 1000000 + fixed
        budget.settle(event, upper)

    client.event_hooks["request"].append(sent)
    client.event_hooks["response"].append(received)
