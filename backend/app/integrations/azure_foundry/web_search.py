"""Luna native Web Search adapter for application-bounded evidence tasks."""

import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from openai import AsyncOpenAI

from backend.app.integrations.web.models import (
    WebActionObservation,
    WebActionType,
    WebCitationObservation,
    WebEvidenceSearchRequest,
    WebSearchHit,
    WebSearchObservation,
    WebUsageObservation,
)
from backend.app.observability.usage import install_http_hooks, observe_sdk
from backend.app.runtime.config_models import WebEvidenceConfig


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _number(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _visible_url(value: object, allowed_domains: tuple[str, ...]) -> tuple[str, str, bool] | None:
    url = _text(value)
    if url is None:
        return None
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").encode("idna").decode("ascii").casefold()
    except (ValueError, UnicodeError):
        return None
    if not host:
        return None
    allowed = (
        parts.scheme.casefold() == "https"
        and parts.username is None
        and parts.password is None
        and any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)
    )
    return url, host, allowed


def _queries(action: Mapping[str, object]) -> tuple[str, ...]:
    values = action.get("queries")
    if values is None:
        values = action.get("query")
    if isinstance(values, str):
        return (values,)
    output: list[str] = []
    for item in _list(values):
        if isinstance(item, str) and item.strip():
            output.append(item)
        elif isinstance(item, Mapping):
            query = _text(item.get("search_term")) or _text(item.get("query"))
            if query:
                output.append(query)
    return tuple(output)


def normalize_luna_response(
    raw: object,
    request: WebEvidenceSearchRequest,
    *,
    latency_ms: int,
) -> WebSearchObservation:
    """Retain only application-visible provider facts; never infer hidden actions."""

    if hasattr(raw, "model_dump"):
        raw = raw.model_dump(mode="json")
    if not isinstance(raw, Mapping) or not isinstance(raw.get("output"), list):
        raise ValueError("Malformed Azure Responses output")
    actions: list[WebActionObservation] = []
    hits: list[WebSearchHit] = []
    citations: list[WebCitationObservation] = []
    partial = False
    for item in raw["output"]:
        if not isinstance(item, Mapping):
            partial = True
            continue
        if item.get("type") == "web_search_call":
            action = _mapping(item.get("action"))
            raw_type = _text(action.get("type")) or "other"
            action_type = (
                WebActionType(raw_type)
                if raw_type in WebActionType._value2member_map_
                else WebActionType.OTHER
            )
            status = _text(item.get("status")) or "unknown"
            if status != "completed":
                partial = True
            source_urls: list[str] = []
            for source in _list(action.get("sources")):
                source_map = _mapping(source)
                visible = _visible_url(source_map.get("url"), request.allowed_domains)
                if visible is not None:
                    source_urls.append(visible[0])
                else:
                    partial = True
            result_values = item.get("results", action.get("results", []))
            if not isinstance(result_values, list):
                partial = True
                result_values = []
            for result_index, result in enumerate(result_values):
                result_map = _mapping(result)
                visible = _visible_url(result_map.get("url"), request.allowed_domains)
                if visible is None:
                    partial = True
                    continue
                url, host, allowed = visible
                source_urls.append(url)
                hits.append(
                    WebSearchHit(
                        url=url,
                        source_domain=host,
                        title=_text(result_map.get("title")),
                        snippet=_text(result_map.get("snippet")),
                        action_index=len(actions),
                        result_index=result_index,
                        allowed_domain=allowed,
                    )
                )
            result_urls = {hit.url for hit in hits if hit.action_index == len(actions)}
            for source_index, source_url in enumerate(dict.fromkeys(source_urls)):
                if source_url in result_urls:
                    continue
                visible = _visible_url(source_url, request.allowed_domains)
                if visible is None:
                    continue
                hits.append(
                    WebSearchHit(
                        url=visible[0],
                        source_domain=visible[1],
                        action_index=len(actions),
                        result_index=-(source_index + 1),
                        allowed_domain=visible[2],
                    )
                )
            actions.append(
                WebActionObservation(
                    action_type=action_type,
                    status=status,
                    queries=_queries(action),
                    target_url=_text(action.get("url")),
                    source_urls=tuple(dict.fromkeys(source_urls)),
                )
            )
        elif item.get("type") == "message":
            for content in _list(item.get("content")):
                for annotation in _list(_mapping(content).get("annotations")):
                    annotation_map = _mapping(annotation)
                    if annotation_map.get("type") != "url_citation":
                        continue
                    visible = _visible_url(annotation_map.get("url"), request.allowed_domains)
                    if visible is None:
                        partial = True
                        continue
                    citations.append(
                        WebCitationObservation(
                            url=visible[0],
                            title=_text(annotation_map.get("title")),
                            start_index=_number(annotation_map.get("start_index")),
                            end_index=_number(annotation_map.get("end_index")),
                        )
                    )
                    if not any(hit.url == visible[0] for hit in hits):
                        hits.append(
                            WebSearchHit(
                                url=visible[0],
                                source_domain=visible[1],
                                title=_text(annotation_map.get("title")),
                                action_index=-1,
                                result_index=-1,
                                allowed_domain=visible[2],
                            )
                        )
    usage_raw = _mapping(raw.get("usage"))
    details = _mapping(usage_raw.get("output_tokens_details"))
    usage = (
        WebUsageObservation(
            input_tokens=_number(usage_raw.get("input_tokens")),
            output_tokens=_number(usage_raw.get("output_tokens")),
            total_tokens=_number(usage_raw.get("total_tokens")),
            reasoning_tokens=_number(details.get("reasoning_tokens")),
        )
        if usage_raw
        else None
    )
    return WebSearchObservation(
        response_id=_text(raw.get("id")),
        provider_status=_text(raw.get("status")),
        actions=tuple(actions),
        hits=tuple(hits),
        citations=tuple(citations),
        usage=usage,
        latency_ms=latency_ms,
        partial=partial or raw.get("status") not in (None, "completed"),
    )


class AzureFoundryWebEvidenceProvider:
    """Use the existing Foundry deployment without touching StructuredLLMClient."""

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
            install_http_hooks(self._owned_client._client, "azure_foundry", "official_search")
        self._responses = (
            responses_client if responses_client is not None else self._owned_client.responses
        )

    async def aclose(self):
        """Only close an SDK client created by this adapter."""
        if self._owned_client is not None:
            await self._owned_client.close()

    @property
    def cache_identity(self) -> str:
        return f"azure_foundry:{self._deployment}"

    async def search(self, request: WebEvidenceSearchRequest) -> WebSearchObservation:
        from backend.app.services.auxiliary_model_limits import bound_response_request

        started = time.monotonic()
        options = dict(
            model=self._deployment,
            input=request.task_instruction,
            tools=[
                {
                    "type": "web_search",
                    "filters": {"allowed_domains": list(request.allowed_domains)},
                    "search_context_size": self._config.search_context_size,
                }
            ],
            tool_choice="required",
            reasoning={"effort": self._config.reasoning_effort},
            max_tool_calls=self._config.max_tool_calls,
            include=["web_search_call.action.sources", "web_search_call.results"],
        )
        raw = await observe_sdk(
            self._responses.create,
            usage_operation="official_search",
            usage_provider="azure_foundry",
            **bound_response_request(options, self._auxiliary_limits),
        )
        return normalize_luna_response(
            raw, request, latency_ms=round((time.monotonic() - started) * 1000)
        )
