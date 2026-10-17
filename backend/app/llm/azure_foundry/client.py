"""Microsoft Foundry implementation of the structured LLM client interface."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from backend.app.evidence.experience_models import ExperienceProfileDraft
from backend.app.llm.azure_foundry.dto import (
    FoundryExperienceProfileDTO,
    FoundryInterpretationDTO,
    FoundryItineraryDTO,
    FoundryPrimaryItineraryDTO,
)
from backend.app.llm.azure_foundry.itinerary_cost_projection import map_foundry_v1_itinerary
from backend.app.llm.azure_foundry.mapping import (
    FoundryMappingError,
    map_foundry_itinerary,
)
from backend.app.llm.azure_foundry.provider_diagnostics import failure_category, normalize
from backend.app.llm.azure_foundry.requirement_profiles import (
    CURRENT_REQUIREMENT_PROFILE,
    requirement_profile,
)
from backend.app.llm.client import StructuredModelT, StructuredOutputError
from backend.app.llm.reference_transport import (
    primary_references,
    profile_references,
    repair_references,
)
from backend.app.observability.usage import install_http_hooks, staged
from backend.app.runtime.fingerprints import digest
from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.schemas.itinerary import Itinerary
from backend.app.schemas.itinerary_projection import V1Itinerary
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.model_references import INSTRUCTION


def requirement_wire_format(*, current=False, indexed=False, dated=False, profile=None):
    """Static DTO schema using the documented Azure Responses subset."""
    profile = profile or requirement_profile(
        "preference_draft_15"
        if dated
        else "preference_draft_14"
        if indexed
        else "preference_draft_13"
        if current
        else "preference_draft_12"
    )
    schema = profile.dto.model_json_schema()
    if profile.source_type is not None:
        from backend.app.llm.azure_foundry.requirement_wire import (
            IndexedSourceSpans,
            current_schema,
        )

        schema = current_schema(schema, indexed=profile.source_type is IndexedSourceSpans)

    def enums(node):
        if isinstance(node, dict):
            if "const" in node:
                node["enum"] = [node.pop("const")]
            for value in node.values():
                enums(value)
        elif isinstance(node, list):
            for value in node:
                enums(value)

    enums(schema)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": profile.schema_name,
            "strict": True,
            "schema": schema,
        },
    }


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RequirementBoundaryError("duplicate_json_key", stage="json")
        result[key] = value
    return result


@dataclass(frozen=True)
class _FoundryBinding:
    transport_schema: type[BaseModel]
    to_domain: Callable[[BaseModel], BaseModel]


def _map_itinerary(value: BaseModel) -> Itinerary:
    dto = FoundryItineraryDTO.model_validate(value)
    return map_foundry_itinerary(dto)


def _map_v1_itinerary(value: BaseModel) -> V1Itinerary:
    dto = FoundryPrimaryItineraryDTO.model_validate(value)
    return map_foundry_v1_itinerary(dto)


def _map_experience_profile(value: BaseModel) -> ExperienceProfileDraft:
    dto = FoundryExperienceProfileDTO.model_validate(value)
    return ExperienceProfileDraft.model_validate(dto.model_dump())


_FOUNDRY_BINDINGS: dict[type[BaseModel], _FoundryBinding] = {
    InterpretationDraft: _FoundryBinding(
        transport_schema=FoundryInterpretationDTO,
        to_domain=lambda dto: InterpretationDraft.model_validate(dto.model_dump()),
    ),
    Itinerary: _FoundryBinding(
        transport_schema=FoundryItineraryDTO,
        to_domain=_map_itinerary,
    ),
    V1Itinerary: _FoundryBinding(
        transport_schema=FoundryPrimaryItineraryDTO,
        to_domain=_map_v1_itinerary,
    ),
    ExperienceProfileDraft: _FoundryBinding(
        transport_schema=FoundryExperienceProfileDTO,
        to_domain=_map_experience_profile,
    ),
}


class AzureFoundryStructuredLLMClient:
    """Use strict transport DTOs through a Microsoft Foundry v1 endpoint."""

    def __init__(
        self,
        *,
        endpoint: str,
        deployment: str,
        api_key: str,
        requirement_capture=None,
        http_client: httpx.Client | None = None,
        http_async_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.requirement_capture = requirement_capture
        self._capture_secrets = (api_key,)
        self._requirement_config = {
            "version": "requirement_execution_1",
            "deployment": deployment,
            "api": "responses/v1",
            "max_retries": 0,
            "contract": CURRENT_REQUIREMENT_PROFILE,
        }
        transport_options = {}
        if http_client is not None:
            transport_options["http_client"] = http_client
        if http_async_client is not None:
            transport_options["http_async_client"] = http_async_client
        self._chat_model = ChatOpenAI(
            model=deployment,
            base_url=endpoint,
            api_key=api_key,
            use_responses_api=True,
            max_retries=0,
            **transport_options,
        )

        install_http_hooks(
            getattr(getattr(self._chat_model, "root_async_client", None), "_client", None),
            "azure_foundry",
            "model_http",
        )

    async def aclose(self):
        """Release SDK clients when the application owns this adapter."""
        try:
            await self._chat_model.root_async_client.close()
        finally:
            self._chat_model.root_client.close()

    def capture_requirement_outcome(self, draft, error=None):
        call_id = draft._diagnostic_call_id
        if self.requirement_capture and call_id:
            detail = (
                error.as_dict()
                if hasattr(error, "as_dict")
                else {
                    "status": "validated" if error is None else type(error).__name__,
                }
            )
            if error is not None and detail.get("status") == "clarification_required":
                detail["stage"] = "hard_requirements"
            try:
                saved = self.requirement_capture.record(
                    call_id,
                    detail.get("stage", "canonicalization"),
                    detail,
                    secrets=self._capture_secrets,
                )
                if saved is None:
                    self.last_call_metadata.setdefault("secondary_errors", []).append(
                        "capture_failure:unavailable"
                    )
            except Exception as exc:
                self.last_call_metadata.setdefault("secondary_errors", []).append(
                    "capture_failure:" + type(exc).__name__
                )

    @staged("requirements")
    async def _interpret(self, system_prompt, user_prompt):
        from backend.app.llm.azure_foundry.requirement_wire import (
            IndexedSourceSpans,
            planning_envelope,
            restore_current,
        )

        call_id = uuid4().hex
        envelope = planning_envelope(user_prompt)
        if self._requirement_config.get("contract") == "preference_draft_12":
            # Frozen response readers select the historical contract explicitly.
            envelope = None
        spans = None
        profile = requirement_profile(
            self._requirement_config.get("contract", CURRENT_REQUIREMENT_PROFILE)
            if envelope is not None
            else "preference_draft_12"
        )
        indexed = profile.source_type is IndexedSourceSpans
        source_request_sha256 = None
        if envelope is not None:
            spans = profile.source_type(user_prompt, envelope["additional_preferences"])
            if indexed:
                source_request_sha256 = spans.request_sha256
            source_payload = {**envelope, "source_spans": spans.inventory()}
            user_prompt = (
                json.dumps(source_payload, ensure_ascii=False, separators=(",", ":"))
                if profile.compact_json
                else json.dumps(source_payload)
            )
            system_prompt = profile.project_prompt(system_prompt)
        wire = requirement_wire_format(profile=profile)
        base = {
            "request_id": digest(user_prompt),
            "prompt_hash": digest(system_prompt),
            "schema_hash": digest(wire),
            "config_hash": digest(self._requirement_config),
            "prompt_version": profile.prompt_version,
            "schema_version": profile.schema_version,
            "config": self._requirement_config,
        }
        if indexed:
            base.update(
                source_request_sha256=source_request_sha256,
                source_mapping_sha256=spans.mapping_sha256,
            )
        self.last_call_metadata = {"call_id": call_id, **base, "secondary_errors": []}
        diagnostics = normalize(secrets=self._capture_secrets)

        def capture(stage, payload):
            if self.requirement_capture:
                try:
                    saved = self.requirement_capture.record(
                        call_id,
                        stage,
                        {**base, **payload, "provider_diagnostics": diagnostics},
                        secrets=self._capture_secrets,
                    )
                    if saved is None:
                        self.last_call_metadata["secondary_errors"].append(
                            "capture_failure:unavailable"
                        )
                except Exception as exc:
                    self.last_call_metadata["secondary_errors"].append(
                        "capture_failure:" + type(exc).__name__
                    )

        stage = "transport"
        try:
            # A dictionary schema selects SDK responses.create, not eager Pydantic parse.
            # Capture completed content BEFORE JSON/DTO/domain validation can discard it.
            raw = await self._chat_model.bind(response_format=wire).ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            metadata = getattr(raw, "response_metadata", {})
            content = raw.content
            usage = getattr(raw, "usage_metadata", None)
            self.last_call_metadata.update(
                usage=usage,
                model_name=metadata.get("model_name"),
                response_id=getattr(raw, "id", None),
            )
            diagnostics = normalize(
                metadata=metadata,
                content=content,
                usage=usage,
                response_id=getattr(raw, "id", None),
                secrets=self._capture_secrets,
            )
            self.last_call_metadata["provider_diagnostics"] = diagnostics
            blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content
            refusal = any(b.get("type") == "refusal" for b in blocks if isinstance(b, dict))
            capture(
                "response_received",
                {
                    "content": content,
                    "response_hash": digest(content),
                    "usage": usage,
                    "response_id": getattr(raw, "id", None),
                    "status": metadata.get("status"),
                    "finish_reason": metadata.get("finish_reason"),
                    "refusal": refusal,
                    "incomplete_details": metadata.get("incomplete_details"),
                },
            )
            if refusal:
                raise RequirementBoundaryError(
                    "requirement_refused", stage="provider", category="provider_refusal"
                )
            if metadata.get("status") != "completed" or metadata.get("incomplete_details"):
                raise RequirementBoundaryError(
                    "requirement_incomplete", stage="provider", category="provider_incomplete"
                )
            text = "".join(
                b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
            )
            if len(text) > 250000:
                raise RequirementBoundaryError("response_resource_overflow", stage="json")
            stage = "json"
            try:
                payload = json.loads(text, object_pairs_hook=_unique_object)
            except json.JSONDecodeError:
                # Non-JSON prose is not a Gate classification; never inspect its meaning.
                if text.strip() and not text.lstrip().startswith(("{", "[")):
                    raise RequirementBoundaryError(
                        "unstructured_requirement_response",
                        stage="provider",
                        category="provider_incomplete",
                    ) from None
                raise
            stage = "transport_dto"
            if envelope is not None:
                payload = restore_current(payload, spans, request_sha256=source_request_sha256)
            dto = profile.dto.model_validate(payload)
            stage = "draft_domain"
            draft = _FOUNDRY_BINDINGS[InterpretationDraft].to_domain(dto)
            draft._diagnostic_call_id = call_id
            capture("draft_validated", {"status": "validated"})
            return draft
        except RequirementBoundaryError as exc:
            exc.provider_diagnostics = diagnostics
            capture(exc.stage, exc.as_dict())
            raise
        except (ValidationError, FoundryMappingError, json.JSONDecodeError) as exc:
            errors = (
                tuple({"loc": e["loc"], "type": e["type"]} for e in exc.errors())
                if isinstance(exc, ValidationError)
                else ()
            )
            error = RequirementBoundaryError(
                "invalid_requirement_response",
                stage=stage,
                errors=errors,
                provider_diagnostics=diagnostics,
            )
            capture(stage, error.as_dict())
            raise error from exc
        except Exception as exc:
            diagnostics = normalize(error=exc, secrets=self._capture_secrets)
            self.last_call_metadata["provider_diagnostics"] = diagnostics
            error = RequirementBoundaryError(
                "requirement_provider_failed",
                stage=stage,
                category=failure_category(diagnostics),
                provider_diagnostics=diagnostics,
            )
            capture(stage, error.as_dict())
            raise error from exc

    @staged("structured_generation")
    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[StructuredModelT],
        _generation_config=None,
    ) -> StructuredModelT:
        """Make exactly one DTO-backed structured invocation for a domain schema."""

        if response_schema is InterpretationDraft:
            return await self._interpret(system_prompt, user_prompt)

        binding = _FOUNDRY_BINDINGS.get(response_schema)
        if binding is None:
            raise StructuredOutputError(
                f"Microsoft Foundry has no transport DTO for {response_schema.__name__}"
            )

        options = {"method": "json_schema", "strict": True}
        references = None
        time_projection = None
        transport_schema = binding.transport_schema
        if response_schema is V1Itinerary:
            from backend.app.llm.azure_foundry.civil_time import (
                TIME_WIRE_VERSION,
                ToolsTimeProjection,
                primary_transport_schema,
            )

            transport_schema = primary_transport_schema(system_prompt)
            if TIME_WIRE_VERSION in system_prompt:
                time_projection = ToolsTimeProjection.primary(user_prompt)
            references, user_prompt = primary_references(user_prompt)
        elif response_schema is ExperienceProfileDraft:
            references, user_prompt = profile_references(user_prompt)
        wire_schema = transport_schema
        if references is not None:
            system_prompt += "\n" + INSTRUCTION
            wire_schema = references.constrain_schema(transport_schema.model_json_schema())
        if _generation_config is not None:
            if response_schema is not V1Itinerary:
                raise ValueError("Primary generation limits apply only to V1/V2 main output")
            options["max_output_tokens"] = _generation_config.output_tokens
        structured_model = self._chat_model.with_structured_output(
            wire_schema,
            **options,
        )
        try:
            from backend.app.observability.mechanism_observation import model_submitted

            model_submitted()
            raw_result = await structured_model.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            if references is not None:
                raw_result = references.decode(
                    raw_result.model_dump(mode="json")
                    if isinstance(raw_result, BaseModel)
                    else raw_result
                )
            if time_projection is not None:
                raw_result = time_projection.primary_result(raw_result)
            transport_result = binding.transport_schema.model_validate(raw_result)
            domain_result = binding.to_domain(transport_result)
        except (FoundryMappingError, ValidationError, ValueError) as exc:
            raise StructuredOutputError(
                f"Microsoft Foundry response did not match {response_schema.__name__}: {exc}"
            ) from exc

        return cast(StructuredModelT, domain_result)

    async def generate_primary_structured(self, *, generation_config, **kwargs):
        """Per-call settings, without mutating a shared client or other tasks."""
        return await self.generate_structured(**kwargs, _generation_config=generation_config)

    @staged("semantics")
    async def generate_poi_semantics_structured(
        self, *, system_prompt, user_prompt, output_tokens, usage_callback=None
    ):
        from backend.app.schemas.poi_semantics import (
            FoundrySemanticAssessmentBatch,
        )

        model = self._chat_model.with_structured_output(
            FoundrySemanticAssessmentBatch,
            method="json_schema",
            strict=True,
            max_output_tokens=output_tokens,
        )
        raw = await model.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
            **({"config": {"callbacks": [usage_callback]}} if usage_callback else {}),
        )
        dto = FoundrySemanticAssessmentBatch.model_validate(raw)
        return dto

    @staged("landmark_nomination")
    async def generate_landmark_nomination_structured(
        self, *, system_prompt, user_prompt, output_tokens, usage_callback=None
    ):
        from backend.app.schemas.landmark_nomination import LandmarkNominationDraft

        model = self._chat_model.with_structured_output(
            LandmarkNominationDraft,
            method="json_schema",
            strict=True,
            max_output_tokens=output_tokens,
        )
        raw = await model.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
            **({"config": {"callbacks": [usage_callback]}} if usage_callback else {}),
        )
        return LandmarkNominationDraft.model_validate(raw)

    @staged("named_place_binding")
    async def generate_named_place_binding_structured(
        self, *, system_prompt, user_prompt, output_tokens, usage_callback=None
    ):
        from backend.app.schemas.named_place_binding import NamedBindingBatch

        model = self._chat_model.with_structured_output(
            NamedBindingBatch,
            method="json_schema",
            strict=True,
            max_output_tokens=output_tokens,
        )
        from backend.app.observability.mechanism_observation import model_submitted

        model_submitted()
        raw = await model.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
            **({"config": {"callbacks": [usage_callback]}} if usage_callback else {}),
        )
        return NamedBindingBatch.model_validate(raw)

    @staged("repair_reason_compression")
    async def compress_repair_reasons_structured(
        self, *, system_prompt, user_prompt, output_tokens, usage_callback=None
    ):
        """One text-only batch. The Repair service owns all budgets and validation."""
        from backend.app.observability.mechanism_observation import model_submitted
        from backend.app.versions.v3.repair_reason_compression import ReasonCompressionDTO

        model = self._chat_model.with_structured_output(
            ReasonCompressionDTO.model_json_schema(),
            method="json_schema",
            strict=True,
            max_output_tokens=output_tokens,
        )
        model_submitted()
        raw = await model.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
            **({"config": {"callbacks": [usage_callback]}} if usage_callback is not None else {}),
        )
        return ReasonCompressionDTO.model_validate(raw)

    @staged("repair_model")
    async def generate_repair_structured(
        self, *, system_prompt, user_prompt, output_tokens=None, usage_callback=None
    ):
        """Per-invocation V3 options and additive usage capture; primary stays unchanged."""
        from backend.app.llm.azure_foundry.civil_time import (
            FoundryCivilPatchDTO,
            ToolsTimeProjection,
        )
        from backend.app.versions.v3.repair_budget import configured_policy
        from backend.app.versions.v3.repair_models import RepairPatch
        from backend.app.versions.v3.repair_projection import FoundryRepairPatchDTO
        from backend.app.versions.v3.repair_reason_compression import validate_repair_patch

        if output_tokens is None:
            output_tokens = configured_policy().input.output_tokens
        time_projection = ToolsTimeProjection.repair(json.loads(user_prompt))
        references, user_prompt = repair_references(user_prompt)
        system_prompt += "\n" + INSTRUCTION
        model = self._chat_model.with_structured_output(
            references.constrain_schema(
                (
                    FoundryCivilPatchDTO if time_projection else FoundryRepairPatchDTO
                ).model_json_schema()
            ),
            method="json_schema",
            strict=True,
            max_output_tokens=output_tokens,
        )
        try:
            from backend.app.observability.mechanism_observation import model_submitted

            model_submitted()
            raw = await model.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
                **(
                    {"config": {"callbacks": [usage_callback]}}
                    if usage_callback is not None
                    else {}
                ),
            )
            restored = references.decode(
                raw.model_dump(mode="json") if isinstance(raw, BaseModel) else raw
            )
            if time_projection:
                restored = time_projection.repair_result(restored)
            dto = validate_repair_patch(restored, FoundryRepairPatchDTO)
            return RepairPatch.model_validate(dto.model_dump())
        except (ValidationError, ValueError) as exc:
            raise StructuredOutputError("Invalid Repair patch") from exc
