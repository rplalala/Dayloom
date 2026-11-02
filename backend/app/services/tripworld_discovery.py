"""V2-only bounded discovery extension, before common factual admission."""

import asyncio
from time import perf_counter

from backend.app.evidence.models import PlaceCandidate
from backend.app.evidence.selection_models import PlaceSelectionInput
from backend.app.integrations.dispatch import ProviderNotSentError
from backend.app.integrations.google.places import (
    PLACES_CANDIDATE_FIELD_MASK,
    PLACES_DETAILS_FIELD_MASK,
)
from backend.app.integrations.models import LatLng, PlaceDetailsRequest, PlaceSearchRequest
from backend.app.observability.progress import observed
from backend.app.policies.poi_funnel import MergedSearchObservations, normalize_exact_name
from backend.app.policies.tripworld_query_plan import query_plan
from backend.app.schemas.tripworld_discovery import TripWorldOrigin
from backend.app.services.evidence_acquisition import _ProviderResult
from backend.app.tripworld.database.policy import POLICY_VERSION, exclusion_reasons
from backend.app.tripworld.database.vectors import SPACE_ID
from backend.app.tripworld.retrieval.entities import RetrievalEntity
from backend.app.tripworld.retrieval.geography import GeographicScope, haversine_km, in_radius
from backend.app.tripworld.retrieval.runtime import RuntimeRetrieval
from backend.app.versions.v2.config import RAGConfig


class RAGStop(Exception):
    """Local limit, not provider failure and never a negative Details cache entry."""


class TripWorldDiscovery:
    def __init__(self, acquisition, *, config=None, runtime_factory=None, enabled=True):
        self.acq = acquisition
        self.enabled = enabled
        self.config = config or RAGConfig()
        self.runtime_factory = runtime_factory or (lambda: RuntimeRetrieval(self.config))
        self.report = {
            "version": self.config.version,
            "status": "not_started",
            "queries": [],
            "omitted_queries": [],
            "returned_positions": 0,
            "unique_entities": 0,
            "resolution_attempts": 0,
            "details_sends": 0,
            "fallback_sends": 0,
            "embedding_sends": 0,
            "retrieval_queries": 0,
            "cache_hits": 0,
            "entities": [],
            "origins": {},
            "stops": [],
            "phase_seconds": {},
        }
        self.incomplete_keys = set()

    def remaining(self):
        remaining = self.ends - perf_counter()
        if remaining <= 0:
            raise RAGStop("deadline")
        return remaining

    async def provider(self, key, kind, factory):
        self.remaining()
        cached, hit = self.acq._cache.lookup(key)
        if not hit and self.acq._cache.terminal_attempt(key):
            return _ProviderResult(error_type="previous_sent_request")
        if key in self.incomplete_keys:
            raise RAGStop("previous_incomplete_request")

        async def load():
            self.remaining()
            limit = self.config.details_calls if kind == "details" else self.config.fallback_calls
            counter = f"{kind}_sends"
            if self.report[counter] >= limit:
                raise RAGStop(f"{kind}_budget")
            timeout = min(self.config.google_timeout, self.remaining())
            self.acq._cache.attempts[key] = "reserved_not_sent"
            self.remaining()

            def sent():
                self.remaining()
                if self.report[counter] >= limit:
                    raise RAGStop(f"{kind}_budget")
                self.report[counter] += 1

            timer = asyncio.timeout(timeout)
            try:
                async with timer:
                    try:
                        if self.acq._places is None:
                            raise ProviderNotSentError("Places dependency is not ready")
                        return _ProviderResult(
                            value=await self.acq._cache.dispatch(
                                key,
                                factory,
                                on_send=sent,
                                observed=getattr(self.acq._places, "observes_send_boundary", False),
                            )
                        )
                    except ProviderNotSentError as exc:
                        raise RAGStop("pre_send_unavailable") from exc
                    except RAGStop:
                        raise
                    except TimeoutError:
                        raise
                    except Exception as exc:
                        return _ProviderResult(error_type=type(exc).__name__)
            except TimeoutError:
                if timer.expired():
                    if self.acq._cache.terminal_attempt(key):
                        self.incomplete_keys.add(key)
                    raise RAGStop("request_timeout") from None
                return _ProviderResult(error_type="TimeoutError")

        result, hit = await self.acq._cache.get_or_create(key, load)
        self.report["cache_hits"] += int(hit)
        self.acq._tracer.event(
            "rag_provider_result",
            {
                "operation": kind,
                "key": key,
                "cache_hit": hit,
                "error": result.error_type,
                "sent_counts": {
                    "details": self.report["details_sends"],
                    "fallback": self.report["fallback_sends"],
                },
            },
        )
        return result

    async def details(self, pid):
        request = PlaceDetailsRequest(place_id=pid, field_mask=PLACES_DETAILS_FIELD_MASK)
        result = await self.provider(
            self.acq._place_details_cache_key(request),
            "details",
            lambda: self.acq._places.get_place_details(request),
        )
        return result.value if result.value is not None and result.value.place_id == pid else None

    def near_entity(self, value, entity):
        return in_radius(value.location.latitude, value.location.longitude, self.scope) and (
            haversine_km(
                entity.latitude, entity.longitude, value.location.latitude, value.location.longitude
            )
            <= self.config.identity_radius_km
        )

    async def resolve(self, entity):
        if entity.google_place_id:
            value = await self.details(entity.google_place_id)
            if value is not None and self.near_entity(value, entity):
                return value, "direct_id"
        if not entity.preferred_name:
            return None, "missing_name"
        request = PlaceSearchRequest(
            text_query=" ".join((entity.preferred_name, *entity.localities[:1])),
            page_size=3,
            location_bias=LatLng(latitude=entity.latitude, longitude=entity.longitude),
            field_mask=PLACES_CANDIDATE_FIELD_MASK,
        )
        key = (
            "places_search",
            request.text_query.casefold(),
            request.page_size,
            request.field_mask,
            request.include_future_opening_businesses,
            (request.location_bias.latitude, request.location_bias.longitude),
            request.language_code,
        )
        response = await self.provider(
            key, "fallback", lambda: self.acq._places.search_text(request)
        )
        if response.value is None:
            return None, "fallback_failed"
        aliases = {normalize_exact_name(n) for n in (entity.preferred_name, *entity.aliases) if n}
        matches = {
            c.place_id: c
            for c in response.value.candidates[:3]
            if normalize_exact_name(c.display_name) in aliases and self.near_entity(c, entity)
        }
        if len(matches) != 1:
            return None, "fallback_not_unique"
        value = await self.details(next(iter(matches)))
        if value is None or not self.near_entity(value, entity):
            return None, "fallback_details_unusable"
        return value, "fallback"

    def attach(self, by_id, pid, entity, hits, method, value=None):
        origins = tuple(
            TripWorldOrigin(
                entity_id=entity.retrieval_entity_id,
                query=query,
                rank=row["rank"],
                cosine=row["similarity_score"],
                distance_km=row["distance_km"],
                artifact_hash=row["retrieval_entity_artifact_hash"],
                text_hash=row["embedding_text_hash"],
                space_id=SPACE_ID,
                policy_version=POLICY_VERSION,
                resolution=method,
                evidence_ref=f"google_places:{pid}",
            )
            for query, row in hits
        )
        current = by_id.get(pid)
        if current is None:
            current = PlaceSelectionInput(
                candidate=PlaceCandidate(
                    place_id=pid,
                    name=value.display_name,
                    formatted_address=value.formatted_address,
                    latitude=value.location.latitude,
                    longitude=value.location.longitude,
                    primary_type=value.primary_type,
                    business_status=value.business_status,
                    source_query=hits[0][0].text,
                    category=hits[0][0].query_id,
                    provider_rank=None,
                ),
                discovery_origins=origins,
            )
        else:
            union = {o.model_dump_json(): o for o in (*current.discovery_origins, *origins)}
            current = current.model_copy(update={"discovery_origins": tuple(union.values())})
        by_id[pid] = current

    @observed("retrieval")
    async def extend(self, contract, destination, merged, excluded):
        phase_timer = None
        started = perf_counter()
        self.ends = started + self.config.deadline_seconds
        self.google_ids = {p.candidate.place_id for p in merged.places}
        by_id = {p.candidate.place_id: p for p in merged.places}
        self.report["config"] = self.config.model_dump()
        try:
            self.scope = GeographicScope(
                latitude=destination.latitude,
                longitude=destination.longitude,
                radius_km=self.config.radius_km,
                country=None,
            )
            self.report["scope"] = self.scope.model_dump()
            if not self.enabled:
                self.report.update(status="disabled", reason="disabled_by_deployment",
                                   elapsed_seconds=perf_counter() - started)
                self.acq._tracer.event("rag_discovery_disabled", self.report)
                return merged
            queries, omitted = query_plan(contract, self.config)
            self.report["queries"] = [q.model_dump() for q in queries]
            self.report["omitted_queries"] = omitted
            phase_timer = asyncio.timeout(self.remaining())
            async with phase_timer:
                async with self.runtime_factory() as runtime:
                    self.report["runtime_diagnostics"] = getattr(runtime, "diagnostics", [])
                    self.report["embedding_http_attempts"] = getattr(runtime, "http_attempts", [])
                    await runtime.prepare()
                    self.remaining()
                    t = perf_counter()
                    vectors = {}
                    missing = []
                    for q in queries:
                        v, hit = self.acq._cache.lookup(("rag_embedding", SPACE_ID, q.text))
                        if hit:
                            vectors[q.query_id] = v
                            self.report["cache_hits"] += 1
                        else:
                            missing.append(q)
                    if missing:
                        try:
                            encoded = await runtime.embed([q.text for q in missing])
                        finally:
                            self.report["embedding_sends"] = runtime.embedding_sends
                            self.report["embedding_usage"] = runtime.usage
                        for q, v in zip(missing, encoded, strict=True):

                            async def completed(value=v):
                                return value

                            vectors[q.query_id], _ = await self.acq._cache.get_or_create(
                                ("rag_embedding", SPACE_ID, q.text), completed
                            )
                    self.report["embedding_usage"] = runtime.usage
                    self.report["phase_seconds"]["embedding"] = perf_counter() - t
                    t, streams = perf_counter(), []
                    for q in queries:
                        self.remaining()
                        key = (
                            "rag_retrieval",
                            SPACE_ID,
                            runtime.artifact_hash,
                            POLICY_VERSION,
                            self.scope.model_dump_json(),
                            self.config.top_k,
                            q.text,
                        )

                        async def retrieve(query=q):
                            self.report["retrieval_queries"] += 1
                            return await runtime.search(
                                vectors[query.query_id], self.scope, self.config.top_k
                            )

                        rows, hit = await self.acq._cache.get_or_create(key, retrieve)
                        self.report["cache_hits"] += int(hit)
                        streams.append((q, rows[: self.config.top_k]))
                    self.report["phase_seconds"]["retrieval"] = perf_counter() - t
                    entities = {}
                    for pos in range(self.config.top_k):
                        for q, rows in streams:
                            if pos >= len(rows):
                                continue
                            row = rows[pos]
                            self.report["returned_positions"] += 1
                            try:
                                entity = RetrievalEntity.model_validate(row["entity"])
                                if exclusion_reasons(entity) or not in_radius(
                                    entity.latitude, entity.longitude, self.scope
                                ):
                                    raise ValueError("Ineligible retrieval entity")
                            except (ValueError, KeyError):
                                self.report["entities"].append({"status": "invalid_entity"})
                                continue
                            entry = entities.setdefault(entity.retrieval_entity_id, (entity, []))
                            entry[1].append((q, row))
                    self.report["unique_entities"] = len(entities)
                    t = perf_counter()
                    for entity, hits in entities.values():
                        self.remaining()
                        record = {"entity_id": entity.retrieval_entity_id, "status": "resolving"}
                        self.report["entities"].append(record)
                        pid = entity.google_place_id
                        if pid in excluded:
                            record["status"] = "excluded"
                            continue
                        if pid in by_id:
                            method = (
                                "google_observation"
                                if pid in self.google_ids
                                else "request_resolved"
                            )
                            self.attach(by_id, pid, entity, hits, method)
                            record.update(status=method, canonical_id=pid)
                            continue
                        if pid:
                            request = PlaceDetailsRequest(
                                place_id=pid, field_mask=PLACES_DETAILS_FIELD_MASK
                            )
                            cached, hit = self.acq._cache.lookup(
                                self.acq._place_details_cache_key(request)
                            )
                            if (
                                hit
                                and cached.value is not None
                                and cached.value.place_id == pid
                                and self.near_entity(cached.value, entity)
                            ):
                                self.report["cache_hits"] += 1
                                self.attach(
                                    by_id, pid, entity, hits, "request_resolved", cached.value
                                )
                                record.update(status="request_resolved", canonical_id=pid)
                                continue
                        if self.report["resolution_attempts"] >= self.config.resolution_entities:
                            record["status"] = "entity_budget"
                            continue
                        self.report["resolution_attempts"] += 1
                        try:
                            value, method = await self.resolve(entity)
                            if value is None:
                                record["status"] = method
                                continue
                            if value.place_id in excluded:
                                record["status"] = "excluded"
                                continue
                            self.attach(by_id, value.place_id, entity, hits, method, value)
                            record.update(
                                status="resolved", method=method, canonical_id=value.place_id
                            )
                        except RAGStop as exc:
                            record["status"] = str(exc)
                            self.report["stops"].append(str(exc))
                        except Exception as exc:
                            record.update(status="invalid_resolution", error=type(exc).__name__)
                    self.report["phase_seconds"]["resolution"] = perf_counter() - t
            incomplete = any(
                r["status"]
                not in {"resolved", "google_observation", "request_resolved", "excluded"}
                for r in self.report["entities"]
            )
            self.report["status"] = "partial" if incomplete else "complete"
        except asyncio.CancelledError:
            self.report["cancellation"] = "caller_cancelled"
            self.acq._tracer.event("rag_cancelled", self.report)
            raise
        except (TimeoutError, RAGStop) as exc:
            self.report.update(status="deadline_limited", stop=type(exc).__name__)
            self.report["phase_deadline_expired"] = bool(phase_timer and phase_timer.expired())
            self.report["timeout_scope"] = (
                "phase"
                if self.report["phase_deadline_expired"]
                or (isinstance(exc, RAGStop) and str(exc) == "deadline")
                else "sql"
                if any(
                    r.get("sql_timeout_expired") for r in self.report.get("runtime_diagnostics", [])
                )
                else "other_suboperation_or_limit"
            )
            for record in self.report["entities"]:
                if record["status"] == "resolving":
                    record["status"] = "stage_interrupted"
        except Exception as exc:
            self.report.update(status="unavailable", stop=type(exc).__name__)
        self.report["elapsed_seconds"] = perf_counter() - started
        self.report["origins"] = {
            pid: [o.model_dump(mode="json") for o in p.discovery_origins]
            for pid, p in by_id.items()
            if p.discovery_origins
        }
        self.report["new_canonical_ids"] = sorted(set(by_id) - self.google_ids)
        self.report["mixed_source_ids"] = sorted(set(self.report["origins"]) & self.google_ids)
        self.report["google_overlap_entities"] = sum(
            r["status"] == "google_observation" for r in self.report["entities"]
        )
        self.report["origin_associations"] = {
            pid: {
                "intent_ids": list(p.discovery_intent_ids),
                "requirement_refs": sorted(
                    {r for o in p.discovery_origins for r in o.query.requirement_refs}
                ),
            }
            for pid, p in by_id.items()
            if p.discovery_origins
        }
        if self.report["status"] == "complete" and not self.report["origins"]:
            self.report["status"] = "empty"
        self.acq._tracer.event("rag_discovery_completed", self.report)
        return MergedSearchObservations(
            tuple(by_id[k] for k in sorted(by_id)), merged.raw_observation_count
        )

    def record_admission(self, eligible, admitted):
        self.report["admission"] = {
            pid: "admitted" if pid in admitted else "capacity" if pid in eligible else "ineligible"
            for pid in self.report["origins"]
        }

    def finalize(self, state):
        funnel, selection, itinerary = (
            state["candidate_funnel"],
            state["review_selection"],
            state["itinerary"],
        )
        from backend.app.policies.itinerary_output import output_role_summary

        roles = output_role_summary(itinerary, selection.policy_result)
        origins = set(self.report["origins"])
        self.report["fate"] = {
            "admitted": sorted(
                origins & {p.candidate.place_id for p in funnel.admitted_candidates}
            ),
            "enriched": sorted(
                origins & {p.candidate.place_id for p in funnel.enriched_candidates}
            ),
            "supplied": sorted(origins & set(selection.selected_place_ids)),
            "scheduled": sorted(origins & set(roles.scheduled_place_ids)),
            "nearby_only": sorted(
                (origins & set(roles.reference_place_ids)) - set(roles.scheduled_place_ids)
            ),
        }
        self.report["canonical_outcomes"] = {
            pid: (
                "scheduled"
                if pid in self.report["fate"]["scheduled"]
                else "supplied_not_scheduled"
                if pid in self.report["fate"]["supplied"]
                else "not_selected_by_supply"
                if pid in self.report["fate"]["enriched"]
                else dict(funnel.details_failures).get(pid, "enrichment_capacity_not_attempted")
                if pid in self.report["fate"]["admitted"]
                else self.report.get("admission", {}).get(pid, "not_admitted")
            )
            for pid in sorted(origins)
        }
        self.acq._tracer.event("rag_final_fate", self.report)
        return self.report
