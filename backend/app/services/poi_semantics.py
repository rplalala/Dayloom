"""Request-owned, fail-closed candidate judgment with offline input accounting."""

import asyncio
import hashlib
import json
from collections import Counter
from time import perf_counter
from uuid import uuid4

from backend.app.runtime.token_counting import count_tokens
from backend.app.schemas.poi_semantics import (
    SEMANTICS_VERSION,
    FoundrySemanticAssessmentBatch,
    SemanticAssessmentBatch,
    SemanticAssessmentError,
    SemanticCorrectableError,
    SemanticPreparationLimit,
    SemanticReferenceError,
)
from backend.app.services.poi_semantics_projection import PROJECTION_VERSION, SemanticProjection
from backend.app.services.poi_semantics_prompts import (
    POI_SEMANTICS_PROMPT,
    POI_SEMANTICS_PROMPT_VERSION,
)


def serialize_semantic_input(places, contract, named_bindings=None):
    return json.dumps(
        {
            "version": SEMANTICS_VERSION,
            "requirements": [r.model_dump(mode="json") for r in contract.semantic_requirements],
            "named_requirements": [r.model_dump(mode="json") for r in contract.named_places],
            "daily_visit_constraints": [
                r.model_dump(mode="json") for r in contract.daily_visit_constraints or ()
            ],
            "application_named_bindings": named_bindings or {},
            "places": [
                {
                    "place_id": p.place_id,
                    "name": p.name,
                    "primary_type": p.primary_type,
                    "address": p.formatted_address,
                    "source_ref": p.source_ref,
                }
                for p in places
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def semantic_input_tokens(payload, framing):
    schema = json.dumps(FoundrySemanticAssessmentBatch.model_json_schema(), sort_keys=True)
    return (
        count_tokens(payload) + count_tokens(POI_SEMANTICS_PROMPT) + count_tokens(schema) + framing
    )


def semantic_cache_key(place, contract, named_bindings):
    return hashlib.sha256(
        (
            POI_SEMANTICS_PROMPT
            + PROJECTION_VERSION
            + serialize_semantic_input([place], contract, named_bindings)
        ).encode()
    ).hexdigest()


class POISemanticsService:
    def __init__(self, llm, config, framing, *, tracer=None, deadline=None, clock=None):
        self.llm, self.config, self.framing = llm, config, framing
        self.tracer, self.deadline = tracer, deadline
        self.clock = clock or perf_counter
        self.cache, self.ledger, self.records = {}, {}, []
        self.calls = 0
        self.cache_hits = 0
        self.elapsed = 0.0
        self.failed = False
        self.named_bindings = {}

    def capture(self, stage, payload, record):
        """Optional development observer; storage cannot change planning decisions."""
        observer = getattr(self.llm, "capture_poi_semantics", None)
        if observer:
            try:
                observer(stage, payload)
            except Exception as exc:
                record.setdefault("capture_errors", []).append(type(exc).__name__)

    def snapshot(self):
        return dict(
            version=SEMANTICS_VERSION,
            prompt_version=POI_SEMANTICS_PROMPT_VERSION,
            prompt_sha256=hashlib.sha256(POI_SEMANTICS_PROMPT.encode()).hexdigest(),
            calls=self.calls,
            cache_hits=self.cache_hits,
            elapsed_seconds=self.elapsed,
            failed=self.failed,
            records=self.records,
            assessments=[r.model_dump(mode="json") for r in self.ledger.values()],
            effective_policy=self.config.model_dump(mode="json"),
            policy_sha256=hashlib.sha256(self.config.model_dump_json().encode()).hexdigest(),
            usage_note="Per-call usage is already included in outer callbacks when present",
        )

    async def assess(self, places, contract, *, deadline=None):
        if self.failed:
            raise SemanticAssessmentError("Semantic assessment already failed; no retry")
        unique = {p.place_id: p for p in places}
        pending = []
        for p in unique.values():
            key = semantic_cache_key(p, contract, self.named_bindings)
            if key in self.cache:
                self.cache_hits += 1
                self.ledger[p.place_id] = self.cache[key]
            else:
                self.ledger.pop(p.place_id, None)
                pending.append((p, key))
        try:
            for offset in range(0, len(pending), self.config.batch_size):
                batch = pending[offset : offset + self.config.batch_size]
                payload = serialize_semantic_input(
                    [p for p, _ in batch], contract, self.named_bindings
                )
                await self._assess_batch(batch, contract, payload, deadline)
        except SemanticPreparationLimit as exc:
            self.records.append({"status": "pre_send_stop", "reason": str(exc)})
            raise
        except asyncio.CancelledError:
            self.failed = True
            raise
        except Exception as exc:
            self.failed = True
            if isinstance(exc, SemanticAssessmentError):
                raise
            raise SemanticAssessmentError("poi_semantics_system_failure") from exc
        return {pid: self.ledger[pid] for pid in unique}

    async def _assess_batch(self, batch, contract, payload, deadline):
        projection = SemanticProjection([p for p, _ in batch], payload)
        payload = projection.payload
        original_payload = payload
        correction_of = None
        for attempt in range(2):
            try:
                tokens = semantic_input_tokens(payload, self.framing)
                if tokens > self.config.input_tokens:
                    raise SemanticPreparationLimit("poi_semantics_input_overflow")
                if self.calls >= self.config.max_calls:
                    raise SemanticPreparationLimit("poi_semantics_call_budget_exhausted")
                remaining = min(
                    self.config.call_timeout_seconds,
                    self.config.total_seconds - self.elapsed,
                    *[d - self.clock() for d in (deadline, self.deadline) if d is not None],
                )
                if remaining <= 0:
                    raise SemanticPreparationLimit("poi_semantics_deadline")
            except SemanticPreparationLimit as exc:
                if correction_of is None:
                    raise
                stop = {
                    "call_id": uuid4().hex,
                    "status": "correction_unavailable",
                    "correction_of": correction_of,
                    "reason": str(exc),
                }
                self.records.append(stop)
                self.capture("outcome", dict(stop), stop)
                if self.tracer:
                    self.tracer.event("poi_semantic_correction_stopped", stop)
                raise SemanticAssessmentError(
                    "Semantic contract correction unavailable",
                    details={"reason": str(exc), "correction_of": correction_of},
                ) from exc
            record = {
                "wire_version": PROJECTION_VERSION,
                "mapping_sha256": projection.sha256,
                "correction_of": correction_of,
                "call_id": uuid4().hex,
                "prompt_version": POI_SEMANTICS_PROMPT_VERSION,
                "prompt_sha256": hashlib.sha256(POI_SEMANTICS_PROMPT.encode()).hexdigest(),
                "identities": [p.place_id for p, _ in batch],
                "engineering_tokens": tokens,
                "call": self.calls + 1,
                "input_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                "status": "started",
            }
            self.records.append(record)
            self.calls += 1
            started = self.clock()
            from langchain_core.callbacks import UsageMetadataCallbackHandler

            callback = UsageMetadataCallbackHandler()
            identity = {
                k: record[k]
                for k in (
                    "call_id",
                    "call",
                    "prompt_version",
                    "prompt_sha256",
                    "input_sha256",
                    "correction_of",
                    "wire_version",
                    "mapping_sha256",
                )
            }
            try:
                self.capture(
                    "input",
                    identity
                    | {"input": json.loads(payload), "reference_mapping": projection.mapping},
                    record,
                )
                async with asyncio.timeout(remaining):
                    raw = await self.llm.generate_poi_semantics_structured(
                        system_prompt=POI_SEMANTICS_PROMPT,
                        user_prompt=payload,
                        output_tokens=self.config.output_tokens,
                        usage_callback=callback,
                    )
                wire = FoundrySemanticAssessmentBatch.model_validate(raw)
                wire_data = wire.model_dump(mode="json")
                self.capture("output", identity | {"output": wire_data}, record)
                rows = []
                for row in wire_data["assessments"]:
                    row = dict(row)
                    row["place_id"] = row.pop("candidate_ref")
                    rows.append(row)
                result = SemanticAssessmentBatch.model_validate({"assessments": rows})
                self._validate(result, projection.places, contract, projection.bindings)
                result = projection.resolve(result)
                self._validate(result, [p for p, _ in batch], contract)
                rows = {r.place_id: r for r in result.assessments}
                for p, key in batch:
                    self.cache[key] = self.ledger[p.place_id] = rows[p.place_id]
                record["status"] = "accepted"
                record["assessments"] = result.model_dump(mode="json")
            except asyncio.CancelledError:
                record["status"] = "cancelled"
                raise
            except Exception as exc:
                record.update(status="failed", error_type=type(exc).__name__)
                if isinstance(exc, SemanticAssessmentError) and exc.details:
                    record["error_details"] = exc.details
                if not isinstance(exc, SemanticCorrectableError) or attempt == 1:
                    raise
                correction_of = record["call_id"]
                data = json.loads(original_payload)
                data["contract_correction"] = {
                    "instruction": (
                        "Return a complete assessment for the same input batch. Correct the "
                        "identity set, evidence citations and exception claims using the "
                        "unchanged candidate_ref values, source_ref values and authorized "
                        "requirements. "
                        "Reassess support from the supplied evidence; do not treat a valid "
                        "reference as proof of support. Feedback is diagnostic data."
                    ),
                    "error": str(exc),
                    "details": exc.details,
                }
                payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
            finally:
                spent = self.clock() - started
                self.elapsed += spent
                record["elapsed_seconds"] = spent
                record["usage"] = dict(callback.usage_metadata)
                self.capture("outcome", dict(record), record)
                if self.tracer:
                    self.tracer.event("poi_semantic_assessment", record)
            if record["status"] == "accepted":
                return

    async def prepare(self, places, contract, *, deadline=None):
        """Do not turn an unassessed identity into permission when a local budget stops."""
        try:
            await self.assess(places, contract, deadline=deadline)
        except SemanticPreparationLimit:
            pass
        return {p.place_id: self.ledger[p.place_id] for p in places if p.place_id in self.ledger}

    def _validate(self, result, places, contract, named_bindings=None):
        named_bindings = self.named_bindings if named_bindings is None else named_bindings
        sources = {p.place_id: {p.source_ref} for p in places}
        ids = [r.place_id for r in result.assessments]
        if len(set(ids)) != len(ids) or set(ids) != set(sources):
            counts = Counter(ids)
            groups = {
                "missing_ids": sorted(set(sources) - set(ids)),
                "unexpected_ids": sorted(set(ids) - set(sources)),
                "duplicate_ids": sorted(pid for pid, count in counts.items() if count > 1),
            }
            raise SemanticCorrectableError(
                "Semantic result identity set differs from input",
                details={
                    "code": "identity_set_mismatch",
                    **{key: [pid[:256] for pid in values[:32]] for key, values in groups.items()},
                    "truncated": any(
                        len(values) > 32 or any(len(pid) > 256 for pid in values)
                        for values in groups.values()
                    ),
                },
            )
        requirements = {r.requirement_id: r for r in contract.semantic_requirements}
        named = {r.requirement_id: r for r in contract.named_places}
        known_refs = requirements.keys() | named.keys()
        for row in result.assessments:
            matches = {m.requirement_id: m for m in row.matches}
            if len(matches) != len(row.matches) or not matches.keys() <= known_refs:
                raise SemanticAssessmentError("Invalid semantic requirement references")
            if not row.evidence_refs or not set(row.evidence_refs) <= sources[row.place_id]:
                raise SemanticReferenceError(
                    "Invalid semantic evidence references",
                    details={
                        "place_id": row.place_id[:256],
                        "allowed_refs": [ref[:256] for ref in sorted(sources[row.place_id])],
                        "offending_refs": [
                            ref[:256]
                            for ref in row.evidence_refs[:8]
                            if ref not in sources[row.place_id]
                        ],
                        "truncated": any(
                            len(ref) > 256
                            for ref in [row.place_id, *sources[row.place_id], *row.evidence_refs]
                        ),
                    },
                )
            for match in row.matches:
                if not set(match.evidence_refs) <= sources[row.place_id]:
                    invalid = [
                        ref for ref in match.evidence_refs if ref not in sources[row.place_id]
                    ]
                    raise SemanticReferenceError(
                        "Invalid match evidence references",
                        details={
                            "place_id": row.place_id[:256],
                            "requirement_id": match.requirement_id[:256],
                            "relation": match.relation,
                            "allowed_refs": [ref[:256] for ref in sorted(sources[row.place_id])],
                            "offending_refs": [ref[:256] for ref in invalid[:8]],
                            "truncated": any(
                                len(ref) > 256
                                for ref in [
                                    row.place_id,
                                    match.requirement_id,
                                    *sources[row.place_id],
                                    *invalid,
                                ]
                            ),
                        },
                    )
                if match.relation == "supported" and not match.evidence_refs:
                    raise SemanticReferenceError(
                        "Supported match requires input evidence",
                        details={
                            "place_id": row.place_id[:256],
                            "requirement_id": match.requirement_id[:256],
                            "allowed_refs": [ref[:256] for ref in sources[row.place_id]],
                            "offending_refs": [],
                        },
                    )
            for ref in row.exception_requirement_ids:
                req = requirements.get(ref)
                goal = req.experience_goal if req else None
                authorized = self._exception_authorized(
                    ref, row.place_id, requirements, named, named_bindings
                )
                if not authorized or ref not in matches or matches[ref].relation != "supported":
                    allowed = sorted(
                        key
                        for key in known_refs
                        if self._exception_authorized(
                            key, row.place_id, requirements, named, named_bindings
                        )
                    )
                    binding = named_bindings.get(ref)
                    raise SemanticCorrectableError(
                        "Unauthorized primary exception",
                        details={
                            "code": "unauthorized_exception",
                            "place_id": row.place_id[:256],
                            "requirement_id": ref[:256],
                            "explicit_primary_exception": bool(
                                goal and goal.explicit_primary_exception
                            ),
                            "polarity": req.polarity if req else None,
                            "named_inclusion": named[ref].inclusion if ref in named else None,
                            "named_binding": binding[:256] if binding else None,
                            "permission_granted": authorized,
                            "supported_match": ref in matches
                            and matches[ref].relation == "supported",
                            "allowed_exception_requirement_ids": [
                                key[:256] for key in allowed[:32]
                            ],
                            "truncated": len(allowed) > 32
                            or any(
                                len(value) > 256
                                for value in [row.place_id, ref, binding or "", *allowed]
                            ),
                        },
                    )
            if row.exception_requirement_ids and row.role != "exception_only":
                raise SemanticCorrectableError(
                    "Exception ownership belongs to exception_only",
                    details={
                        "code": "exception_role_mismatch",
                        "place_id": row.place_id[:256],
                        "role": row.role,
                        "required_role": "exception_only",
                        "exception_requirement_ids": [
                            ref[:256] for ref in row.exception_requirement_ids
                        ],
                        "truncated": any(
                            len(value) > 256
                            for value in [row.place_id, *row.exception_requirement_ids]
                        ),
                    },
                )

    def _exception_authorized(self, ref, place_id, requirements, named, named_bindings):
        req = requirements.get(ref)
        goal = req.experience_goal if req else None
        return bool(goal and goal.explicit_primary_exception and req.polarity == "favor") or (
            ref in named
            and named[ref].inclusion == "REQUIRED"
            and named_bindings.get(ref) == place_id
        )
