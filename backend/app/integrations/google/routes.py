"""Google Routes API bounded Route Matrix adapter."""

from collections.abc import Mapping
from datetime import UTC, datetime

from backend.app.integrations.google.common import require_mapping, trace_exchange
from backend.app.integrations.http import AsyncJSONTransport
from backend.app.integrations.models import RouteMatrixDTO, RouteMatrixRequest
from backend.app.observability.run_trace import RunTracer

ROUTE_MATRIX_FIELDS = (
    "originIndex",
    "destinationIndex",
    "duration",
    "staticDuration",
    "fallbackInfo",
    "distanceMeters",
    "status",
    "condition",
)
ROUTE_MATRIX_FIELD_MASK = ",".join(ROUTE_MATRIX_FIELDS)


def _waypoint(latitude: float, longitude: float) -> dict[str, object]:
    return {
        "waypoint": {
            "location": {
                "latLng": {
                    "latitude": latitude,
                    "longitude": longitude,
                }
            }
        }
    }


class GoogleRoutesProvider:
    """Compute one mode-specific Route Matrix without automatic fan-out."""

    @property
    def observes_send_boundary(self):
        """Expose the existing transport send hook for opt-in repair accounting."""
        return getattr(self._transport, "observes_send_boundary", False)

    def __init__(
        self,
        *,
        api_key: str,
        transport: AsyncJSONTransport,
        tracer: RunTracer,
        base_url: str = "https://routes.googleapis.com",
    ) -> None:
        self._api_key = api_key
        self._transport = transport
        self._tracer = tracer
        self._base_url = base_url.rstrip("/")

    async def compute_route_matrix(self, request: RouteMatrixRequest) -> RouteMatrixDTO:
        body: dict[str, object] = {
            "origins": [
                _waypoint(item.location.latitude, item.location.longitude)
                for item in request.origins
            ],
            "destinations": [
                _waypoint(item.location.latitude, item.location.longitude)
                for item in request.destinations
            ],
            "travelMode": request.travel_mode,
        }
        if request.routing_preference is not None:
            body["routingPreference"] = request.routing_preference
        if request.departure_time is not None and not (
            request.travel_mode == "DRIVE"
            and request.routing_preference in (None, "TRAFFIC_UNAWARE")
        ):
            body["departureTime"] = (
                request.departure_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
            )
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": request.field_mask,
        }
        requested_at = datetime.now(UTC).isoformat()
        response = await self._transport.request_json(
            "POST",
            f"{self._base_url}/distanceMatrix/v2:computeRouteMatrix",
            headers=headers,
            json_body=body,
        )
        trace_exchange(
            self._tracer,
            name="google_routes_matrix",
            request={"headers": headers, "body": body},
            response=response,
        )
        if not isinstance(response, list):
            mapping = require_mapping(response, context="Route Matrix response")
            raw_elements = mapping.get("elements", [])
        else:
            raw_elements = response
        if not isinstance(raw_elements, list):
            raw_elements = []
        return RouteMatrixDTO(
            requested_at=requested_at,
            elements=[dict(item) for item in raw_elements if isinstance(item, Mapping)],
            retrieved_at=datetime.now(UTC).isoformat(),
        )
