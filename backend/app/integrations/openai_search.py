"""Bounded OpenAI web search with the existing official-evidence contract."""

import time

from openai import AsyncOpenAI
from pydantic import Field, SecretStr

from backend.app.integrations.azure_foundry.web_search import normalize_luna_response
from backend.app.integrations.spending import install_spend_hooks
from backend.app.observability.usage import observe_sdk
from backend.app.runtime.config_models import AuxiliaryModelLimits
from backend.app.runtime.model_limits import OPENAI_SEARCH_MAX_OUTPUT_TOKENS
from backend.app.runtime.settings import RuntimeSettings

MODEL = "gpt-4.1-mini-2025-04-14"


class SearchSettings(RuntimeSettings):
    openai_api_key: SecretStr = Field(validation_alias="OPENAI_API_KEY", min_length=1)


class OpenAIWebEvidenceProvider:
    def __init__(self, *, api_key, config, auxiliary_limits=None, http_client=None):
        self._config = config
        self._limits = auxiliary_limits or AuxiliaryModelLimits()
        self._client = AsyncOpenAI(
            api_key=api_key,
            max_retries=0,
            timeout=config.timeout_seconds,
            http_client=http_client,
        )
        install_spend_hooks(self._client._client)

    @property
    def cache_identity(self):
        return f"openai:{MODEL}:web_search"

    async def aclose(self):
        await self._client.close()

    async def search(self, request):
        from backend.app.services.auxiliary_model_limits import bound_response_request

        started = time.monotonic()
        options = bound_response_request(
            {
                "model": MODEL,
                "max_output_tokens": min(
                    self._limits.output_tokens, OPENAI_SEARCH_MAX_OUTPUT_TOKENS
                ),
                "input": request.task_instruction,
                "tools": [
                    {
                        "type": "web_search",
                        "filters": {
                            "allowed_domains": list(request.allowed_domains),
                        },
                        "search_context_size": self._config.search_context_size,
                    }
                ],
                "tool_choice": "required",
                "max_tool_calls": self._config.max_tool_calls,
                "include": ["web_search_call.action.sources"],
                "store": False,
                "service_tier": "default",
            },
            self._limits,
        )
        raw = await observe_sdk(
            self._client.responses.create,
            usage_operation="official_search",
            usage_provider="openai",
            **options,
        )
        return normalize_luna_response(
            raw,
            request,
            latency_ms=round((time.monotonic() - started) * 1000),
        )
