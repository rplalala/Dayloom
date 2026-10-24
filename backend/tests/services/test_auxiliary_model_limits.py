"""Offline admission preserves complete input and limits provider output."""

from copy import deepcopy

import pytest

from backend.app.runtime.config_models import AuxiliaryModelLimits
from backend.app.services.auxiliary_model_limits import bound_response_request
from backend.app.services.generation_resources import GenerationResourceError


def test_admission_preserves_requirements_and_existing_smaller_output_limit():
    request = {
        "input": "Must include a botanical garden. Absolutely no stairs.",
        "text": {"format": {"type": "json_schema", "schema": {"type": "object"}}},
        "max_output_tokens": 1200,
    }
    original = deepcopy(request)
    result = bound_response_request(request, AuxiliaryModelLimits())
    assert result == original and request == original
    assert bound_response_request({"input": request["input"]}, AuxiliaryModelLimits()) == {
        "input": original["input"], "max_output_tokens": 16384,
    }


def test_overflow_rejects_the_entire_request_without_truncation():
    request = {"input": "A very long source requirement. " * 100}
    original = deepcopy(request)
    with pytest.raises(GenerationResourceError, match="auxiliary_input_resource_overflow"):
        bound_response_request(
            request, AuxiliaryModelLimits(input_tokens=50, framing_tokens=10)
        )
    assert request == original


def test_legacy_policy_does_not_add_limits():
    request = {"input": "Existing independent runner input"}
    assert bound_response_request(request, None) == request
