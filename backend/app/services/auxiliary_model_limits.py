"""Pre-send engineering limits; never truncate input or claim an invoice ceiling.

Hosted tools can introduce server-side tokens and separate charges. This guard
bounds caller-supplied input and output allowance, not a hosted tool's total cost.
"""

import json

from backend.app.runtime.token_counting import count_tokens
from backend.app.services.generation_resources import GenerationResourceError


def bound_response_request(request, limits):
    if limits is None:
        return request
    tokens = count_tokens(json.dumps(request, ensure_ascii=False)) + limits.framing_tokens
    if tokens > limits.input_tokens:
        raise GenerationResourceError(
            f"auxiliary_input_resource_overflow: {tokens} > {limits.input_tokens}"
        )
    return {
        **request,
        "max_output_tokens": min(
            request.get("max_output_tokens", limits.output_tokens), limits.output_tokens
        ),
    }


async def bounded_response(create, limits, **request):
    """Apply admission before entering either the SDK or an injected provider."""
    return await create(**bound_response_request(request, limits))
