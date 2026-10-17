"""Offline engineering preflight for main itinerary generation only."""

import json

from backend.app.llm.azure_foundry.civil_time import primary_transport_schema
from backend.app.llm.reference_transport import primary_references
from backend.app.runtime.token_counting import count_tokens
from backend.model_references import INSTRUCTION


class GenerationResourceError(ValueError):
    """Do not silently truncate evidence, preferences or candidate identities."""


def check_primary_input(system_prompt, user_prompt, config):
    references, user_prompt = primary_references(user_prompt)
    schema = primary_transport_schema(system_prompt).model_json_schema()
    if references is not None:
        system_prompt += "\n" + INSTRUCTION
        schema = references.constrain_schema(schema)
    parts = {
        "system_tokens": count_tokens(system_prompt),
        "user_tokens": count_tokens(user_prompt),
        "schema_tokens": count_tokens(json.dumps(schema)),
        "framing_tokens": config.framing_tokens,
    }
    parts["total_tokens"] = sum(parts.values())
    parts["ceiling"] = config.input_tokens
    parts["remaining"] = config.input_tokens - parts["total_tokens"]
    if parts["remaining"] < 0:
        raise GenerationResourceError(f"primary_input_resource_overflow: {parts}")
    return parts
