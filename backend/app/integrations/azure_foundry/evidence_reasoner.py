"""Bounded, source-only Azure Foundry EvidenceReasoner."""

import json
from typing import Any

from openai import AsyncOpenAI

from backend.app.evidence.models import PlaceEvidence
from backend.app.evidence.official_models import (
    DateRelevance,
    EvidenceReasonerAssessment,
    EvidenceSourceBlock,
    HoursScheduleScope,
    OfficialClaimKind,
    ReasonerConfidence,
    SourceKind,
    SubjectScope,
    TemporalBasis,
)
from backend.app.evidence.web_models import OfficialInformationNeed, WebEvidenceTask
from backend.app.integrations.azure_foundry.evidence_reasoner_prompt import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
)
from backend.app.observability.usage import install_http_hooks, observe_sdk
from backend.app.runtime.config_models import WebEvidenceConfig
from backend.model_references import INSTRUCTION, ShortReferences

_OPTIONAL_STRING = {"type": ["string", "null"]}
_CANDIDATE_FIELDS = {
    "source_key": {"type": "string"},
    "place_id": {"type": "string"},
    "place_name": {"type": "string"},
    "information_need": {
        "type": "string",
        "enum": [item.value for item in OfficialInformationNeed],
    },
    "claim_kind": {"type": "string", "enum": [item.value for item in OfficialClaimKind]},
    "value_text": {
        "type": "string",
        "description": "Exact source value span; need not occur within predicate_text.",
    },
    "source_kind": {"type": "string", "enum": [item.value for item in SourceKind]},
    "source_url": {"type": "string"},
    "final_url": _OPTIONAL_STRING,
    "supporting_excerpt": {
        "type": "string",
        "description": "One bounded continuous source excerpt supporting the overall claim.",
    },
    "subject_scope": {"type": "string", "enum": [item.value for item in SubjectScope]},
    "subject_text": {
        "type": "string",
        "description": "Exact source span identifying the subject of this claim.",
    },
    "predicate_text": {
        "type": "string",
        "description": "Exact source relation span, such as 'has'; need not contain value_text.",
    },
    "scope_text": {
        "type": ["string", "null"],
        "description": "Exact source span restricting venue or product scope; null if absent.",
    },
    "temporal_basis": {"type": "string", "enum": [item.value for item in TemporalBasis]},
    "date_text": _OPTIONAL_STRING,
    "applicable_start_date": _OPTIONAL_STRING,
    "applicable_end_date": _OPTIONAL_STRING,
    "time_text": _OPTIONAL_STRING,
    "schedule_scope": {
        "type": ["string", "null"],
        "enum": [*[item.value for item in HoursScheduleScope], None],
    },
    "schedule_text": _OPTIONAL_STRING,
    "opens_at": _OPTIONAL_STRING,
    "closes_at": _OPTIONAL_STRING,
    "amount_text": _OPTIONAL_STRING,
    "amount": _OPTIONAL_STRING,
    "currency": _OPTIONAL_STRING,
    "updated_at_text": _OPTIONAL_STRING,
    "updated_at": _OPTIONAL_STRING,
}
_ASSESSMENT_FIELDS = {
    "relevant": {"type": "boolean"},
    "supports_information_need": {"type": "boolean"},
    "relevant_to_requested_dates": {
        "type": "string",
        "enum": [item.value for item in DateRelevance],
    },
    "proposed_relation_to_baseline": {
        "type": ["string", "null"],
        "description": "Audit-only baseline comparison; not source evidence.",
    },
    "confidence": {
        "type": ["string", "null"],
        "enum": [*[item.value for item in ReasonerConfidence], None],
    },
    "brief_rationale": {
        "type": ["string", "null"],
        "description": "Concise audit explanation; not source evidence or an acceptance rule.",
    },
    "candidate": {
        "anyOf": [
            {
                "type": "object",
                "properties": _CANDIDATE_FIELDS,
                "required": list(_CANDIDATE_FIELDS),
                "additionalProperties": False,
            },
            {"type": "null"},
        ]
    },
}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "assessments": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": _ASSESSMENT_FIELDS,
                "required": list(_ASSESSMENT_FIELDS),
                "additionalProperties": False,
            },
        }
    },
    "required": ["assessments"],
    "additionalProperties": False,
}


def _response_text(raw: object) -> str:
    output_text = getattr(raw, "output_text", None)
    if isinstance(output_text, str) and output_text:
        return output_text
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump(mode="json")
    if isinstance(raw, dict):
        direct = raw.get("output_text")
        if isinstance(direct, str):
            return direct
        output = raw.get("output")
        for item in output if isinstance(output, list) else []:
            if isinstance(item, dict) and item.get("type") == "message":
                for content in item.get("content", []):
                    if isinstance(content, dict) and isinstance(content.get("text"), str):
                        return content["text"]
    raise ValueError("EvidenceReasoner returned no visible structured text")


def _response_parse_metadata(
    raw: object, text: str, exc: json.JSONDecodeError
) -> dict[str, object]:
    """Capture only bounded response shape and parser metadata, never response text."""

    if hasattr(raw, "model_dump"):
        raw = raw.model_dump(mode="json")
    response = raw if isinstance(raw, dict) else {}

    def token(value: object) -> str | None:
        return (
            value
            if isinstance(value, str)
            and 0 < len(value) <= 64
            and value.replace("_", "").replace("-", "").isalnum()
            else None
        )

    items = response.get("output")
    items = items if isinstance(items, list) else []
    details = response.get("incomplete_details")
    details = details if isinstance(details, dict) else {}
    status = token(response.get("status"))
    finish_reason = token(details.get("reason") or response.get("finish_reason"))
    return {
        "parser_stage": "json.loads",
        "response_item_types": [
            token(item.get("type")) if isinstance(item, dict) else None for item in items[:8]
        ],
        "response_item_statuses": [
            token(item.get("status")) if isinstance(item, dict) else None for item in items[:8]
        ],
        "response_item_count": len(items),
        "textual_content_existed": bool(text),
        "textual_content_length": len(text),
        "provider_status": status,
        "provider_finish_reason": finish_reason,
        "output_appeared_empty": not text,
        "output_appeared_truncated": (
            True
            if status == "incomplete" or finish_reason == "max_output_tokens"
            else False
            if status == "completed"
            else None
        ),
        "json_error_message": exc.msg[:120],
        "json_error_position": exc.pos,
        "json_error_line": exc.lineno,
        "json_error_column": exc.colno,
    }


def _baseline_context(place: PlaceEvidence, need: OfficialInformationNeed) -> dict[str, object]:
    context: dict[str, object] = {"source_ref": place.source_ref}
    if need in {
        OfficialInformationNeed.CURRENT_OPERATIONAL_STATUS,
        OfficialInformationNeed.DATE_SPECIFIC_OPERATIONAL_EXCEPTION,
    }:
        context["business_status"] = place.business_status
    if need is OfficialInformationNeed.SPECIAL_DATE_HOURS and place.opening_hours:
        context["opening_hours"] = place.opening_hours.model_dump(mode="json")
    return context


class AzureFoundryEvidenceReasoner:
    """One semantic call over supplied sources, with deterministic source alignment."""

    def __init__(
        self,
        *,
        endpoint: str,
        deployment: str,
        api_key: str,
        config: WebEvidenceConfig,
        responses_client: Any | None = None,
        auxiliary_limits=None,
    ) -> None:
        self._auxiliary_limits = auxiliary_limits
        self._deployment = deployment
        self._config = config
        self._owned_client = None
        if responses_client is None:
            self._owned_client = AsyncOpenAI(
                api_key=api_key,
                base_url=endpoint,
                max_retries=0,
                timeout=config.timeout_seconds,
            )
        if self._owned_client is not None:
            install_http_hooks(self._owned_client._client, "azure_foundry", "official_reasoning")
        self._responses = (
            responses_client if responses_client is not None else self._owned_client.responses
        )

    async def aclose(self):
        """Only close an SDK client created by this adapter."""
        if self._owned_client is not None:
            await self._owned_client.close()

    async def reason(
        self,
        task: WebEvidenceTask,
        sources: tuple[EvidenceSourceBlock, ...],
        baseline: PlaceEvidence,
    ) -> tuple[EvidenceReasonerAssessment, ...]:
        limit = self._config.claim_extraction.max_candidates_per_call
        if not sources or len(sources) > self._config.claim_extraction.max_native_sources:
            raise ValueError("EvidenceReasoner source count is outside the bound")
        if any(source.task_id != task.task_id for source in sources):
            raise ValueError("EvidenceReasoner sources must belong to the current task")
        if any(source.source_kind is SourceKind.FETCHED_HTML for source in sources):
            if (
                len(sources) != 1
                or len(sources[0].text) > self._config.page_retrieval.max_text_chars
            ):
                raise ValueError("EvidenceReasoner page source is outside the bound")
        elif any(
            len(source.text) > self._config.claim_extraction.max_native_snippet_chars
            for source in sources
        ):
            raise ValueError("EvidenceReasoner native snippet is outside the bound")
        input_data = {
            "QUERY_CONTEXT_NOT_EVIDENCE": {
                "place_id": task.place_id,
                "place_name": task.place_name,
                "information_need": task.information_need.value,
                "requested_facets": [item.value for item in task.requested_facets],
                "requested_subject_scope": task.requested_subject_scope.value,
                "requested_scope_text": task.requested_scope_text,
                "requested_start_date": task.applicable_start_date.isoformat(),
                "requested_end_date": task.applicable_end_date.isoformat(),
                "structured_baseline_not_source": _baseline_context(
                    baseline, task.information_need
                ),
            },
            "SOURCE_EVIDENCE": [
                {
                    "source_key": source.source_key,
                    **source.model_dump(mode="json", exclude={"content_blocks"}),
                }
                for source in sources
            ],
        }
        references = ShortReferences(
            input_data, {"place_id": "p", "source_key": "s", "task_id": "t"}
        )
        from backend.app.services.auxiliary_model_limits import bound_response_request

        options = dict(
            model=self._deployment,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT + "\n" + INSTRUCTION},
                {
                    "role": "user",
                    "content": json.dumps(references.encode(input_data), ensure_ascii=False),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": PROMPT_VERSION,
                    "schema": references.constrain_schema(OUTPUT_SCHEMA),
                    "strict": True,
                }
            },
            reasoning={"effort": self._config.reasoning_effort},
            max_output_tokens=self._config.claim_extraction.max_extraction_output_units,
        )
        raw = await observe_sdk(
            self._responses.create,
            usage_operation="official_reasoning",
            usage_provider="azure_foundry",
            **bound_response_request(options, self._auxiliary_limits),
        )
        response_text = _response_text(raw)
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as exc:
            try:
                exc._official_reasoner_parse_diagnostics = _response_parse_metadata(
                    raw, response_text, exc
                )
            except Exception:
                # Diagnostics cannot replace the original parse failure.
                pass
            raise
        if not isinstance(parsed, dict) or not isinstance(parsed.get("assessments"), list):
            raise ValueError("EvidenceReasoner output is not an assessment list")
        if len(parsed["assessments"]) > limit:
            raise ValueError("EvidenceReasoner exceeded assessment limit")
        aligned: list[EvidenceReasonerAssessment] = []
        by_key = {source.source_key: source for source in sources}
        for item in parsed["assessments"]:
            try:
                decoded = references.decode(item)
            except ValueError:
                continue
            assessment = EvidenceReasonerAssessment.model_validate(decoded)
            candidate = assessment.candidate
            if candidate is None:
                aligned.append(assessment)
                continue
            source = by_key.get(candidate.source_key or "")
            if source is None or (
                source.source_kind is not candidate.source_kind
                or source.source_url != candidate.source_url
                or source.final_url != candidate.final_url
                or source.task_id != task.task_id
            ):
                continue
            excerpt = candidate.supporting_excerpt
            if excerpt not in source.text or any(
                span is not None and span not in excerpt
                for span in (
                    candidate.subject_text,
                    candidate.predicate_text,
                    candidate.value_text,
                    candidate.scope_text,
                    candidate.date_text,
                    candidate.time_text,
                    candidate.schedule_text,
                    candidate.amount_text,
                    candidate.updated_at_text,
                )
            ):
                continue
            aligned.append(assessment)
        return tuple(aligned)
