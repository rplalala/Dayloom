"""Assembled writer prompts must not retain superseded activity declarations."""

import pytest


@pytest.mark.parametrize("version", ["v0", "v1"])
def test_current_writer_prompts_have_one_consistent_activity_contract(version):
    from backend.activity_semantics import GENERATION_ACTIVITY_CONTRACT
    from backend.app.versions.v0.prompts import ITINERARY_GENERATION_SYSTEM_PROMPT as v0
    from backend.app.versions.v1.prompts import ITINERARY_GENERATION_SYSTEM_PROMPT as v1

    prompt = {"v0": v0, "v1": v1}[version]
    assert GENERATION_ACTIVITY_CONTRACT in prompt
    assert "unknown when the role cannot be assigned" not in prompt
    assert "generic_activity for a non-specific activity" not in prompt
    assert "free_time for unallocated/rest time" not in prompt
