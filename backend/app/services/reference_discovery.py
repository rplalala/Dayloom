"""Optional post-itinerary nearby discovery; never replans the primary itinerary."""

import asyncio
import math
from dataclasses import dataclass, field
from datetime import date
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from backend.app.integrations.google.places import PLACES_NEARBY_FIELD_MASK
from backend.app.integrations.models import LatLng, PlaceCandidateDTO, PlaceNearbySearchRequest
from backend.app.integrations.protocols import NearbyPlacesProvider
from backend.app.runtime.cache import RequestCache
from backend.app.runtime.config_models import ReferenceDiscoveryConfig
from backend.app.schemas.itinerary import Itinerary, ReferenceRecommendation


def distance_metres(a: LatLng, b: LatLng) -> float:
    """Great-circle distance; not a walking route or travel-time estimate."""
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat, dlon = lat2 - lat1, math.radians(b.longitude - a.longitude)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


class ReferenceAnchor(BaseModel):
    model_config = ConfigDict(frozen=True)
    place_id: str
    activity_id: str
    day: date
    name: str
    location: LatLng


class NearbyReferenceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    place: PlaceCandidateDTO
    anchor: ReferenceAnchor
    representative: ReferenceAnchor
    distance_metres: float
    call_id: str
    source_ref: str
    retrieved_at: str


@dataclass
class ReferenceDiscoveryResult:
    itinerary: Itinerary
    ledger: dict[str, NearbyReferenceEvidence] = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)


def attach_references(primary, references, ledger, anchors):
    """Validate separate nearby and scheduled-anchor identities before attachment."""
    scheduled = {
        a.source_place_id for day in primary.days for a in day.activities if a.source_place_id
    }
    for reference in references:
        entry = ledger.get(reference.source_place_id)
        if entry is None:
            raise ValueError("Reference identity is outside the nearby ledger")
        anchor = entry.anchor
        if anchor.place_id not in scheduled or anchor not in anchors:
            raise ValueError("Reference anchor is not a resolved scheduled activity")
        address = entry.place.formatted_address
        area = address.strip() if address and len(address) <= 160 else None
        if entry.place.place_id != reference.source_place_id:
            raise ValueError("Reference ledger key does not match its place identity")
        if (
            reference.place_name,
            reference.source_ref,
            reference.associated_day,
            reference.area,
        ) != (entry.place.display_name.strip(), entry.source_ref, anchor.day, area):
            raise ValueError("Reference projection disagrees with nearby evidence")
    result = primary.model_copy(update={"reference_recommendations": references})
    type(result).model_validate(result.model_dump())
    if result.model_dump(exclude={"reference_recommendations"}) != primary.model_dump(
        exclude={"reference_recommendations"}
    ):
        raise ValueError("Reference attachment changed the primary itinerary")
    return result


class ReferenceDiscoveryService:
    """One request-local phase with its own attempt budget and cancellable awaits."""

    def __init__(
        self,
        provider: NearbyPlacesProvider | None,
        cache: RequestCache,
        config: ReferenceDiscoveryConfig,
    ):
        self.provider, self.cache, self.config = provider, cache, config
        self._failed_keys: set[tuple] = set()

    async def discover(
        self,
        primary,
        places,
        supplied_ids,
        excluded_ids=(),
        known_places=(),
        *,
        request_deadline=None,
    ):
        diagnostics = {
            "policy_version": self.config.policy_version,
            "status": "empty",
            "primary_succeeded": True,
            "reference_succeeded": False,
            "requests_sent": 0,
            "cache_hits": 0,
            "calls": [],
            "skipped_anchors": [],
            "uncovered_anchor_ids": [],
            "rejections": {},
            "anchors": [],
        }
        result = ReferenceDiscoveryResult(primary, diagnostics=diagnostics)
        started = asyncio.get_running_loop().time()
        deadline = started + self.config.deadline_seconds
        if request_deadline is not None:
            deadline = min(deadline, request_deadline)
        if deadline <= started:
            diagnostics.update(status="request_deadline", elapsed_seconds=0, reference_count=0)
            return result
        try:
            await self._discover(
                result,
                places,
                supplied_ids,
                excluded_ids,
                known_places,
                deadline,
            )
        except Exception as exc:
            # Cancellation is a BaseException and deliberately propagates to the caller.
            result.itinerary = primary
            diagnostics.update(status="attachment_error", error_type=type(exc).__name__)
        diagnostics["elapsed_seconds"] = asyncio.get_running_loop().time() - started
        diagnostics["reference_count"] = len(result.itinerary.reference_recommendations)
        return result

    async def _discover(self, result, places, supplied_ids, excluded_ids, known_places, deadline):
        primary, info, cfg = result.itinerary, result.diagnostics, self.config
        if cfg.scale_by_duration:
            days = (primary.end_date - primary.start_date).days + 1
            cfg = cfg.model_copy(update={
                "max_requests": min(cfg.max_requests, days),
                "max_references": min(cfg.max_references, 2 * days),
            })
        info["effective_limits"] = {
            "requests": cfg.max_requests, "references": cfg.max_references,
        }
        by_id = {p.place_id: p for p in places if p.place_id in supplied_ids}
        activities = sorted(
            ((d.date, a) for d in primary.days for a in d.activities),
            key=lambda pair: (pair[0], pair[1].start_time, pair[1].activity_id),
        )
        scheduled_ids = {a.source_place_id for _, a in activities if a.source_place_id}
        scheduled_names = {a.place_name.strip().casefold() for _, a in activities if a.place_name}
        anchors, groups, seen = [], [], set()
        for day, activity in activities:
            pid = activity.source_place_id
            if pid in seen:
                info["skipped_anchors"].append(
                    {"activity_id": activity.activity_id, "reason": "duplicate_place"}
                )
                continue
            place = by_id.get(pid)
            try:
                if place is None:
                    raise ValueError("No supplied identity")
                location = LatLng(latitude=place.latitude, longitude=place.longitude)
            except (ValueError, AttributeError):
                info["skipped_anchors"].append(
                    {
                        "activity_id": activity.activity_id,
                        "reason": "unresolved_identity_or_coordinates",
                    }
                )
                continue
            seen.add(pid)
            anchor = ReferenceAnchor(
                place_id=pid,
                activity_id=activity.activity_id,
                day=day,
                name=place.name,
                location=location,
            )
            anchors.append(anchor)
            group = next(
                (
                    g
                    for g in groups
                    if distance_metres(g[0].location, location) <= cfg.anchor_reuse_metres
                ),
                None,
            )
            if group is not None:
                group.append(anchor)
            # Cached groups remain usable even when the external send allowance is zero.
            elif len(groups) < max(cfg.max_requests, cfg.max_references):
                groups.append([anchor])
            else:
                info["uncovered_anchor_ids"].append(pid)
        info["anchors"] = [a.model_dump(mode="json") for a in anchors]
        info["representative_groups"] = [[a.place_id for a in g] for g in groups]
        if not anchors:
            info["status"] = "no_anchors"
            return
        if self.provider is None:
            info["status"] = "provider_unavailable"
            return
        blocked = set(excluded_ids) | scheduled_ids
        closed = {"CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"}
        blocked |= {p.place_id for p in (*places, *known_places) if p.business_status in closed}
        pools, fetched_ids, outcomes = [], set(), []

        def reject(reason):
            info["rejections"][reason] = info["rejections"].get(reason, 0) + 1

        for group in groups:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                outcomes.append("deadline_exceeded")
                break
            representative = group[0]
            request = PlaceNearbySearchRequest(
                center=representative.location,
                radius_metres=cfg.radius_metres,
                max_result_count=cfg.max_result_count,
                included_types=cfg.included_types,
                rank_preference=cfg.rank_preference,
                field_mask=PLACES_NEARBY_FIELD_MASK,
            )
            key = ("reference_nearby", request.model_dump_json())
            record = {
                "representative_id": representative.place_id,
                "request": request.model_dump(mode="json"),
                "status": "pending",
            }
            info["calls"].append(record)

            async def fetch(request=request, key=key, record=record):
                if key in self._failed_keys:
                    raise _ReferenceLimit("previous_attempt_failed")
                if info["requests_sent"] >= cfg.max_requests:
                    raise _ReferenceLimit("budget_exhausted")
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise _ReferenceLimit("deadline_exceeded")
                call_id = f"nearby-{uuid4()}"
                record["call_id"] = call_id
                record["deadline_limited"] = remaining <= cfg.request_timeout_seconds
                record["timeout_seconds"] = min(cfg.request_timeout_seconds, remaining)
                info["requests_sent"] += 1
                try:
                    async with asyncio.timeout(min(cfg.request_timeout_seconds, remaining)):
                        response = await self.provider.search_nearby(request)
                    return response, call_id
                except BaseException:
                    self._failed_keys.add(key)
                    raise

            try:
                (response, call_id), cached = await self.cache.get_or_create(key, fetch)
            except _ReferenceLimit as exc:
                record["status"] = str(exc)
                outcomes.append(str(exc))
                continue
            except Exception as exc:
                status = "provider_error"
                if isinstance(exc, TimeoutError):
                    status = (
                        "deadline_exceeded"
                        if (
                            record.get("deadline_limited")
                            or asyncio.get_running_loop().time() >= deadline
                        )
                        else "timeout"
                    )
                record.update(status=status, error_type=type(exc).__name__)
                outcomes.append(record["status"])
                if record["status"] == "deadline_exceeded":
                    break
                continue
            record.update(status="cache_hit" if cached else "success", call_id=call_id)
            info["cache_hits"] += int(cached)
            record["raw_result_count"] = response.actual_result_count
            record["normalized_candidate_count"] = len(response.candidates)
            if asyncio.get_running_loop().time() >= deadline:
                record["status"] = "deadline_exceeded"
                outcomes.append("deadline_exceeded")
                break
            outcomes.append("success")
            pool = []
            for candidate in response.candidates[: cfg.max_result_count]:
                try:
                    candidate = PlaceCandidateDTO.model_validate(candidate.model_dump())
                    if not candidate.place_id.strip() or not candidate.display_name.strip():
                        raise ValueError("Blank identity")
                except (ValueError, AttributeError):
                    reject("invalid_candidate")
                    continue
                if candidate.place_id in fetched_ids:
                    reject("duplicate_id")
                    continue
                fetched_ids.add(candidate.place_id)
                if candidate.place_id in blocked or candidate.business_status in closed:
                    reject("scheduled_excluded_or_closed")
                    continue
                if not (set(candidate.types) | {candidate.primary_type}) & set(cfg.included_types):
                    reject("unsupported_type")
                    continue
                distance, _, anchor = min(
                    (distance_metres(candidate.location, a.location), i, a)
                    for i, a in enumerate(group)
                )
                if distance > cfg.radius_metres:
                    reject("outside_radius")
                    continue
                entry = NearbyReferenceEvidence(
                    place=candidate,
                    anchor=anchor,
                    representative=representative,
                    distance_metres=distance,
                    call_id=call_id,
                    source_ref=f"google_places_nearby:{call_id}:{candidate.provider_rank}",
                    retrieved_at=response.retrieved_at,
                )
                pool.append(entry)
                result.ledger[candidate.place_id] = entry
            pools.append(sorted(pool, key=lambda e: (e.distance_metres, e.place.place_id)))

        selected, names = [], set(scheduled_names)
        while any(pools) and len(selected) < cfg.max_references:
            for pool in pools:
                while pool and len(selected) < cfg.max_references:
                    entry = pool.pop(0)
                    name = entry.place.display_name.strip().casefold()
                    if name in names:
                        reject("duplicate_name")
                        continue
                    try:
                        category = next(
                            t
                            for t in cfg.included_types
                            if t in (*entry.place.types, entry.place.primary_type)
                        )
                        address = entry.place.formatted_address
                        reference = ReferenceRecommendation(
                            place_name=entry.place.display_name,
                            source_place_id=entry.place.place_id,
                            reason=f"{category.capitalize()} near {entry.anchor.name[:100]} "
                            f"(approximately {round(entry.distance_metres)} m straight-line).",
                            associated_day=entry.anchor.day,
                            area=address if address and len(address) <= 160 else None,
                            uncertainty="Availability, prices and accessibility are unverified; "
                            "straight-line distance is not a walking route.",
                            source_ref=entry.source_ref,
                        )
                    except ValueError:
                        reject("invalid_reference")
                        continue
                    selected.append(reference)
                    names.add(name)
                    break
        result.itinerary = attach_references(primary, selected, result.ledger, anchors)
        failures = any(o != "success" for o in outcomes)
        info["status"] = (
            ("partial" if failures else "completed")
            if selected
            else (next((o for o in reversed(outcomes) if o != "success"), "empty"))
        )
        info["reference_succeeded"] = not failures
        info["outcomes"] = outcomes


class _ReferenceLimit(Exception):
    """Local scheduling limit; not a provider request or primary planning failure."""
