"""Independent Google/Responses HTTP transport with explicit sends and price context."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import httpx

from .cost_report import estimate
from .snapshot import Response, TransportFailure, _bytes, _decode

PLACE_FIELDS = "id,displayName,formattedAddress,addressComponents,businessStatus,location,timeZone"
SEARCH_MASK = ",".join("places." + field for field in PLACE_FIELDS.split(",")) + ",nextPageToken"
DETAILS_MASK = PLACE_FIELDS + ",currentOpeningHours,regularOpeningHours"
ROUTE_MASK = "originIndex,destinationIndex,status,condition,duration,distanceMeters"


def check_tokenizer():
    """Check the checksum-bound local vocabulary without downloading anything."""
    from backend.app.runtime.token_counting import count_tokens

    try:
        count_tokens("")
    except RuntimeError as exc:
        raise ValueError("Offline tokenizer unavailable") from exc


def usage_event(event):
    """Separate allowlisted billing metadata from the full HTTP evidence journal."""
    fields = {
        "event_id",
        "provider",
        "operation",
        "outcome",
        "send_status",
        "request_key",
        "billing_context",
        "element_count",
        "requested_at",
        "retrieved_at",
        "status_code",
        "reason",
        "model_event_id",
        "model_provider",
    }
    return {k: v for k, v in event.items() if k in fields}


def model_usage(raw, options):
    if not isinstance(raw, dict) or not isinstance(raw.get("usage", {}), dict):
        raise ValueError("Invalid model response usage")
    usage = raw.get("usage") or {}
    details = usage.get("input_tokens_details") or {}
    if not isinstance(details, dict):
        raise ValueError("Invalid model response usage details")
    value = {
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cached_input_tokens": details.get("cached_tokens"),
        "cache_write_input_tokens": details.get("cache_write_tokens"),
    }
    if any(count is not None and (type(count) is not int or count < 0) for count in value.values()):
        raise ValueError("Invalid model token usage")
    for field in ("input_tokens", "output_tokens"):
        if value[field] is not None and value[field] > options["max_" + field]:
            raise ValueError("Reported model usage exceeds allowance")
    return value


def verify_model_capture(execution, event, material, options, usage, *, reasoning_effort):
    """Bind a saved model judgment and usage to its exact captured HTTP attempt."""
    body = {
        **material["packet"]["request"],
        "max_output_tokens": options["max_output_tokens"],
        "store": False,
        "reasoning": {"effort": reasoning_effort},
    }
    if (
        event["request"]
        != {"method": "POST", "url": options["model_endpoint"] + "responses", "json": body}
        or event.get("status_code") != 200
        or _decode((Path(execution) / "http" / (event["event_id"] + ".bin")).read_bytes())
        != material["response"]
        or event["requested_at"] != material["requested_at"]
        or event["retrieved_at"] != material["retrieved_at"]
    ):
        raise ValueError("Model HTTP receipt differs from judgment material")
    if event.get("model_event_id") != usage.get("event_id") or any(
        usage[k] != v for k, v in model_usage(material["response"], options).items()
    ):
        raise ValueError("Model usage differs from captured HTTP response")


def google_wire(request):
    operation, params = request["operation"], request["parameters"]
    if operation == "places_search":
        return {
            "method": "POST",
            "url": "https://places.googleapis.com/v1/places:searchText",
            "field_mask": SEARCH_MASK,
            "json": {
                "textQuery": " ".join(
                    str(params[k]) for k in ("query", "destination", "location") if params[k]
                ),
                "pageSize": params["page_size"],
            },
            "endpoint": "searchText",
        }
    if operation == "places_details":
        return {
            "method": "GET",
            "url": "https://places.googleapis.com/v1/places/" + quote(params["place_id"], safe=""),
            "field_mask": DETAILS_MASK,
            "json": None,
            "endpoint": "details",
        }
    if operation != "route_matrix":
        raise ValueError("Unsupported independent acquisition operation")
    body = {
        "origins": [
            {
                "waypoint": {
                    "location": {
                        "latLng": {k: params["origin"][k] for k in ("latitude", "longitude")}
                    }
                }
            }
        ],
        "destinations": [
            {
                "waypoint": {
                    "location": {
                        "latLng": {k: params["destination"][k] for k in ("latitude", "longitude")}
                    }
                }
            }
        ],
        "travelMode": params["mode"],
    }
    if params["time_basis"] == "explicit_departure":
        body["departureTime"] = params["departure"]
    names = {
        "routing_preference": "routingPreference",
        "language_code": "languageCode",
        "region_code": "regionCode",
    }
    modifiers = {
        "avoid_tolls": "avoidTolls",
        "avoid_highways": "avoidHighways",
        "avoid_ferries": "avoidFerries",
    }
    for key, value in params["routing_options"].items():
        if key in names:
            body[names[key]] = value
        else:
            body["origins"][0]["routeModifiers"] = {
                **body["origins"][0].get("routeModifiers", {}),
                modifiers[key]: value,
            }
    return {
        "method": "POST",
        "url": "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
        "field_mask": ROUTE_MASK,
        "json": body,
        "endpoint": "computeRouteMatrix",
    }


class EvaluationTransport:
    """One run's isolated client, bounded counters and persisted HTTP receipts."""

    def __init__(self, preparation, root, client, google_key, model_key):
        self.preparation, self.root, self.client = preparation, Path(root), client
        self.google_key, self.model_key = google_key, model_key
        self.events, self.model_calls = [], []
        self.reserved = Decimal(0)
        self.started_at = datetime.now(UTC).isoformat()
        (self.root / "http").mkdir()

    def reserve(self, event, kind):
        value, _, reason = estimate(
            event, kind, {"timing": {"started_at": self.started_at}}, self.preparation["prices"]
        )
        if value is None:
            raise ValueError("Execution price unavailable: " + reason)
        if self.reserved + value > Decimal(self.preparation["options"]["max_cost_usd"]):
            raise ValueError("Execution reference cost allowance exhausted")
        self.reserved += value

    async def send(self, wire, event, headers):
        event.update(
            event_id=str(len(self.events) + 1),
            requested_at=datetime.now(UTC).isoformat(),
            send_status="transport_entered",
            outcome="incomplete",
            request=wire,
        )
        self.events.append(event)
        path = self.root / "http" / (event["event_id"] + ".json")
        path.write_bytes(_bytes(event))
        try:
            response = await self.client.request(
                wire["method"],
                wire["url"],
                headers=headers,
                json=wire["json"],
                timeout=self.preparation["options"]["timeout_seconds"],
                follow_redirects=False,
            )
            raw = await response.aread()
        except httpx.TransportError as exc:
            event.update(
                outcome="failed",
                reason="connection_failed",
                retrieved_at=datetime.now(UTC).isoformat(),
            )
            path.write_bytes(_bytes(event))
            raise TransportFailure("connection_failed") from exc
        event.update(
            status_code=response.status_code,
            outcome="completed" if 200 <= response.status_code < 300 else "failed",
            retrieved_at=datetime.now(UTC).isoformat(),
        )
        (self.root / "http" / (event["event_id"] + ".bin")).write_bytes(raw)
        path.write_bytes(_bytes(event))
        return Response(response.status_code, raw)

    async def google(self, request):
        count = sum(e["provider"] == "google" for e in self.events)
        if count >= self.preparation["options"]["max_google_sends"]:
            raise ValueError("Google send allowance exhausted")
        wire = google_wire(request)
        params = request["parameters"]
        event = {
            "provider": "google",
            "operation": "place_details"
            if request["operation"] == "places_details"
            else request["operation"],
            "outcome": "completed",
            "element_count": 1 if request["operation"] == "route_matrix" else None,
            "request_key": request["key"],
            "billing_context": {"endpoint": wire["endpoint"], "field_mask": wire["field_mask"]},
        }
        if request["operation"] == "route_matrix":
            event["billing_context"].update(
                travel_mode=params["mode"],
                routing_preference=params["routing_options"].get("routing_preference"),
            )
        self.reserve(event, "provider")
        return await self.send(
            wire, event, {"X-Goog-Api-Key": self.google_key, "X-Goog-FieldMask": wire["field_mask"]}
        )

    async def model(self, packet, *, operation="identity", reasoning_effort="low"):
        from backend.app.runtime.token_counting import count_tokens

        options = self.preparation["options"]
        body = {
            **packet["request"],
            "max_output_tokens": options["max_output_tokens"],
            "store": False,
            "reasoning": {"effort": reasoning_effort},
        }
        if count_tokens(json.dumps(body)) + 1024 > options["max_input_tokens"]:
            raise ValueError("Complete model packet exceeds input allowance: " + operation)
        if len(self.model_calls) >= self.preparation["max_model_sends"] or any(
            call["operation"] == operation for call in self.model_calls
        ):
            raise ValueError("Model send allowance consumed")
        event_id = "v0-identity" if operation == "identity" else "opening-access"
        event = {
            "event_id": event_id,
            "provider": "azure_foundry",
            "operation": operation,
            "model": options["model"],
            "outcome": "completed",
            "input_tokens": options["max_input_tokens"],
            "output_tokens": options["max_output_tokens"],
            "cached_input_tokens": 0,
            "cache_write_input_tokens": options["max_input_tokens"],
        }
        self.reserve(event, "model")
        model = {
            **event,
            "outcome": "incomplete",
            "input_tokens": None,
            "output_tokens": None,
            "cached_input_tokens": None,
            "cache_write_input_tokens": None,
            "total_tokens": None,
        }
        self.model_calls.append(model)
        response = await self.send(
            {"method": "POST", "url": options["model_endpoint"] + "responses", "json": body},
            {
                "provider": "azure_foundry",
                "operation": "model_http",
                "model_event_id": event_id,
                "model_provider": "azure_foundry",
            },
            {"Authorization": "Bearer " + self.model_key},
        )
        if response.status_code != 200:
            raise ValueError("Model HTTP request failed: " + operation)
        raw = _decode(response.body)
        model.update(outcome="completed", **model_usage(raw, options))
        return raw, self.events[-1]

    def usage(self):
        return {
            "schema_version": "rtpeval_usage_1",
            "namespace": "oracle",
            "group_id": self.preparation["intake"]["batch_id"],
            "run_id": str(self.root),
            "version": "shared",
            "result_sha256": self.preparation["content_sha256"],
            "collection_status": "available",
            "coverage": {"adapter_coverage": "default_adapters"},
            "model_calls": self.model_calls,
            "provider_events": [usage_event(e) for e in self.events],
            "cache_events": [],
            "repair_summary": {"model_event_ids": [], "provider_event_ids": []},
            "timing": {"started_at": self.started_at, "finished_at": datetime.now(UTC).isoformat()},
            "missing_fields": ["actual_account_billing"],
        }
