"""Source-linked mode restrictions at the shared interpretation boundary."""

import asyncio
from datetime import date

import pytest

from backend.app.policies.transport import select_transport_mode_from_intent
from backend.app.schemas.interpreted_requirements import ClarificationRequired, InterpretationDraft
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.initial_routes import permitted_modes
from backend.app.services.preference_interpretation import interpret_preferences
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient
from backend.tests.versions.v1.test_interpreted_requirements import draft_for

TEXT = "Use public transport and walking only."


@pytest.mark.parametrize("pattern", ["transport", "pace", "quote"])
def test_historical_failure_patterns_remain_explicit(pattern):
    value = constrained_draft().model_copy(update={"transport_constraint": None})
    if pattern == "pace":
        value = value.model_copy(update={"daily_pace": ()})
    if pattern == "quote":
        ref = (
            value.semantic_requirements[0]
            .source_refs[0]
            .model_copy(update={"quote": "I would like public transport and walking only."})
        )
        semantic = value.semantic_requirements[0].model_copy(update={"source_refs": (ref,)})
        value = value.model_copy(update={"semantic_requirements": (semantic,)})
    expected = {
        "transport": "unsupported_hard_requirements",
        "pace": "invalid_daily_pace_scope",
        "quote": "invalid_source_occurrence",
    }[pattern]
    with pytest.raises((ClarificationRequired, RequirementBoundaryError)) as error:
        asyncio.run(
            interpret_preferences(
                make_request(TEXT), date(2026, 9, 11), FakeStructuredLLMClient([value])
            )
        )
    assert error.value.code == expected


def constrained_draft(modes=("WALK", "TRANSIT")):
    data = draft_for(TEXT).model_dump(mode="json")
    semantic = data["semantic_requirements"][0]
    semantic.update(kind="constraint", scope="transport", strength="hard")
    data["transport_constraint"] = {
        "allowed_modes": modes,
        "requirement_refs": [semantic["local_key"]],
        "source_refs": [{"quote": TEXT, "occurrence": 0}],
    }
    return InterpretationDraft.model_validate(data)


def test_supported_hard_modes_pass_service_and_restrict_initial_routes():
    contract = asyncio.run(
        interpret_preferences(
            make_request(TEXT), date(2026, 9, 11), FakeStructuredLLMClient([constrained_draft()])
        )
    )
    decision = select_transport_mode_from_intent(None, contract.transport_constraint)
    assert permitted_modes(decision) == ("WALK", "TRANSIT")
    assert contract.semantic_requirements[0].strength == "hard"
    assert contract.transport_constraint.requirement_refs == ("semantic_1",)


def test_foreign_hard_constraint_link_fails_closed():
    draft = constrained_draft()
    bad = draft.model_copy(
        update={
            "transport_constraint": draft.transport_constraint.model_copy(
                update={"requirement_refs": ("foreign",)}
            )
        }
    )
    with pytest.raises(RequirementBoundaryError, match="invalid_transport_constraint_link"):
        asyncio.run(
            interpret_preferences(
                make_request(TEXT), date(2026, 9, 11), FakeStructuredLLMClient([bad])
            )
        )


def test_canonical_transport_links_follow_lossless_semantic_deduplication():
    from backend.app.policies.interpreted_requirements import canonicalize_requirements

    draft = constrained_draft()
    original = draft.semantic_requirements[0]
    draft = draft.model_copy(
        update={
            "semantic_requirements": (
                original,
                original.model_copy(update={"local_key": "duplicate"}),
            ),
            "transport_constraint": draft.transport_constraint.model_copy(
                update={
                    "requirement_refs": (original.local_key, "duplicate"),
                }
            ),
        }
    )
    result = canonicalize_requirements(draft, make_request(TEXT))
    assert result.transport_constraint.requirement_refs == ("semantic_1",)


@pytest.mark.parametrize("version", ["v1", "v2", "v3"])
def test_tool_version_entries_accept_typed_hard_modes_without_drive(version):
    from backend.app.versions.v1.runner import run_v1
    from backend.app.versions.v2.runner import run_v2
    from backend.app.versions.v3.runner import run_v3
    from backend.tests.services.test_tripworld_discovery import Retrieval
    from backend.tests.versions.v1.fakes import (
        FakeRoutesProvider,
        FakeWeatherProvider,
        make_itinerary,
    )
    from backend.tests.versions.v2.test_v2_runner import Places

    model = FakeStructuredLLMClient([constrained_draft(), make_itinerary()])
    routes = FakeRoutesProvider()
    kwargs = {"reference_date": date(2026, 9, 11)}
    if version != "v1":
        kwargs["retrieval_factory"] = lambda: Retrieval([])
    if version == "v3":
        kwargs["quantity_review_enabled"] = False
        kwargs["development_timeout_seconds"] = 600
    runner = {"v1": run_v1, "v2": run_v2, "v3": run_v3}[version]
    result = asyncio.run(
        runner(make_request(TEXT), model, Places(), FakeWeatherProvider(), routes, **kwargs)
    )
    assert result.system_version == version
    assert all(r.travel_mode in ("WALK", "TRANSIT") for r in routes.requests)
    assert all(t.mode in ("WALK", "TRANSIT") for t in result.itinerary.transfers)
