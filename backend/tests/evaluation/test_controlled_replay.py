"""Synthetic controlled cases through the real post-primary V3 seam."""

import asyncio
import copy

from backend.app.evidence.models import RouteEvidence, RouteEvidenceBundle
from backend.app.policies.transport import TransportModeDecision
from backend.app.runtime.config_loader import load_runtime_config
from backend.tests.versions.v3.test_b_targets import setup, visit
from backend.tests.versions.v3.test_validation import DAY, NOW


def case(rows=None, *, review=False):
    original, context, _, _ = setup(rows or [[visit("a", "a")]], reviews=())
    return {
        "schema_version": "rtpeval_controlled_case_1",
        "case_id": "synthetic-control",
        "revision": "one",
        "role": "control",
        "original_input": {
            "destination": "Fixture",
            "start_date": str(original.start_date),
            "end_date": str(original.end_date),
            "additional_preferences": "",
        },
        "primary": original.model_dump(mode="json"),
        "requirements": context.contract.model_dump(mode="json"),
        "reference_date": str(DAY),
        "supply_ids": list(context.original_supply_ids),
        "places": [p.model_dump(mode="json") for p in context.places],
        "transport": TransportModeDecision(travel_mode="WALK", reason="default").model_dump(
            mode="json"
        ),
        "routes": RouteEvidenceBundle(
            baseline=RouteEvidence(
                travel_mode="WALK",
                mode_reason="fixture",
                availability="available",
                retrieved_at=NOW,
                source_ref="synthetic:routes",
            )
        ).model_dump(mode="json"),
        "runtime": load_runtime_config().model_dump(mode="json"),
        "quantity_review": review,
        "request_remaining": 180,
        "calls": [],
    }


def replay(value):
    from backend.evaluation.controlled_replay import replay_controlled_case

    return asyncio.run(replay_controlled_case(value))


def test_valid_control_runs_real_finalization_without_model_or_provider_calls():
    value = case()
    original = copy.deepcopy(value)
    out = replay(value)
    assert out["status"] == "complete"
    assert out["outcome"]["reason"] == "no_authorized_targets"
    assert out["outcome"]["scope"] is None
    assert out["outcome"]["repair"] is None
    assert out["outcome"]["final_primary"]["days"][0]["activities"][0]["activity_id"] == "a"
    assert out["calls"] == []
    assert value == original
    assert out == replay(value)


def test_missing_route_script_cannot_be_swallowed_as_normal_repair_failure():
    value = case(
        [[visit("a", "a", start="10:00", end="11:00"), visit("b", "b", start="10:30", end="11:30")]]
    )
    out = replay(value)
    assert out["status"] == "execution_material_error"
    assert any(c["operation"] == "route_matrix" for c in out["calls"])
    assert any("route_matrix" in error for error in out["diagnostics"])


def scripted(value, patch, *, semantic_role="attraction"):
    """Record exact requests at external boundaries with independently chosen replies."""
    value = copy.deepcopy(value)
    for _ in range(64):
        out = replay(value)
        missing = [c for c in out["calls"] if c.get("status") == "unmatched"]
        if not missing:
            return value
        call = missing[0]
        if call["operation"] == "repair_model":
            response = patch
        elif call["operation"] == "poi_semantics":
            import json

            payload = json.loads(call["request"]["user_prompt"])
            response = {
                "assessments": [
                    {
                        "candidate_ref": p["candidate_ref"],
                        "visit_object": p["name"],
                        "role": semantic_role,
                        "categories": [],
                        "reason": "Synthetic attraction",
                        "evidence_refs": [p["source_ref"]],
                        "matches": [],
                        "exception_requirement_ids": [],
                    }
                    for p in payload["places"]
                ]
            }
        elif call["operation"] == "route_matrix":
            response = {
                "retrieved_at": NOW.isoformat(),
                "elements": [
                    {
                        "originIndex": 0,
                        "destinationIndex": 0,
                        "condition": "ROUTE_EXISTS",
                        "status": {"code": 0},
                        "duration": "600s",
                        "distanceMeters": 100,
                    }
                ],
            }
        else:
            raise AssertionError("Unexpected synthetic boundary: " + call["operation"])
        value["calls"].append(
            {"operation": call["operation"], "request": call["request"], "response": response}
        )
    raise AssertionError("Synthetic script did not converge")


def test_overlap_patch_is_revalidated_and_adopted_by_real_stage():
    value = case(
        [[visit("a", "a", start="10:00", end="11:00"), visit("b", "b", start="10:30", end="11:30")]]
    )
    value = scripted(
        value,
        {
            "edits": [
                {
                    "operation": "retime",
                    "activity_id": "b",
                    "date": str(DAY),
                    "place_id": None,
                    "start_time": f"{DAY}T11:30:00+00:00",
                    "end_time": f"{DAY}T12:30:00+00:00",
                }
            ]
        },
    )
    out = replay(value)
    assert out["status"] == "complete"
    assert out["outcome"]["repair"]["status"] == "ACCEPTED_COMPLETE", out["outcome"]["repair"][
        "reason"
    ]
    assert out["outcome"]["repair"]["rounds"][0]["adopted"]["days"][0]["activities"][1][
        "start_time"
    ].endswith("11:30:00Z")
    assert out["outcome"]["final_primary"]["transfers"][0]["provider_duration_seconds"] == 600
    assert out == replay(value)


def test_invalid_typed_provider_response_is_material_error_not_provider_outage():
    value = case([[visit("a", "a"), visit("b", "b", start="09:30", end="10:30")]])
    observed = replay(value)
    call = next(c for c in observed["calls"] if c["operation"] == "route_matrix")
    value["calls"] = [
        {
            "operation": "route_matrix",
            "request": call["request"],
            "response": {"invalid": "fixture"},
        }
    ]
    out = replay(value)
    assert any("invalid_frozen_response:route_matrix" in d for d in out["diagnostics"])


def overlap_case():
    return case(
        [[visit("a", "a", start="10:00", end="11:00"), visit("b", "b", start="10:30", end="11:30")]]
    )


def test_declared_model_outage_is_valid_replay_and_preserves_original():
    value = scripted(overlap_case(), {"edits": []})
    model = next(c for c in value["calls"] if c["operation"] == "repair_model")
    model.pop("response")
    model["error"] = "synthetic outage"
    out = replay(value)
    assert out["status"] == "complete", out["diagnostics"]
    assert out["outcome"]["repair"]["status"] == "REJECTED"
    assert out["outcome"]["repair"]["model_attempted"]
    assert out["outcome"]["final_primary"]["days"] == value["primary"]["days"]


def test_logical_route_duration_exhausts_real_budget_without_sleeping():
    value = scripted(overlap_case(), {"edits": []})
    first = next(c for c in value["calls"] if c["operation"] == "route_matrix")
    first["duration_seconds"] = 200
    out = replay(value)
    assert out["status"] == "complete", out["diagnostics"]
    assert not any(c["operation"] == "repair_model" for c in out["calls"])
    assert out["logical_elapsed_seconds"] == 200
    assert out == replay(value)


def test_case_rejects_injected_targets_and_permissions():
    import pytest
    from pydantic import ValidationError

    value = case()
    value["scope"] = {"target_ids": ["caller"]}
    with pytest.raises(ValidationError):
        replay(value)


def test_semantic_call_budget_uses_real_service_and_preserves_partial_material():
    from backend.tests.evaluation.test_controlled_report import addition_case

    value = addition_case()
    value["semantics"] = {"calls": value["runtime"]["poi_semantics"]["max_calls"]}
    out = replay(value)
    assert out["status"] == "complete", out["diagnostics"]
    assert not any(c["operation"] == "poi_semantics" for c in out["calls"])
    assert out["outcome"]["repair"]["status"] == "SKIPPED"
    assert out["outcome"]["repair"]["model_attempted"] is False


def test_frozen_typed_cache_value_avoids_a_real_route_send():
    from backend.app.integrations.models import RouteMatrixRequest
    from backend.app.services.evidence_acquisition import V1EvidenceAcquisitionService

    value = scripted(overlap_case(), {"edits": []})
    route = next(c for c in value["calls"] if c["operation"] == "route_matrix")
    key = V1EvidenceAcquisitionService._route_cache_key(
        RouteMatrixRequest.model_validate(route["request"])
    )
    value["cache"] = [
        {"key": key, "value_type": "routes", "value": route["response"], "provider_envelope": True}
    ]
    value["calls"] = [c for c in value["calls"] if c is not route]
    value = scripted(value, {"edits": []})
    out = replay(value)
    assert out["status"] == "complete"
    assert not any(
        c["operation"] == "route_matrix" and c["request"] == route["request"] for c in out["calls"]
    )
    assert any(a["outcome"] == "cache_hit" for a in out["outcome"]["repair"]["acquisition_audit"])


def test_semantic_model_uses_real_projection_and_returns_deterministic_adoption():
    from backend.tests.evaluation.test_controlled_report import addition_case
    from backend.tests.versions.v3.test_b_targets import edit

    value = addition_case()
    value["semantics"] = {}
    value = scripted(value, {"edits": [edit("add", pid="b", start="11:00", end="12:00")]})
    out = replay(value)
    assert out["status"] == "complete", out["diagnostics"]
    assert out["outcome"]["repair"]["status"] == "ACCEPTED_COMPLETE"
    assert any(c["operation"] == "poi_semantics" for c in out["calls"])
    assert out == replay(value)


def test_logical_model_duration_obeys_real_async_timeout_before_adoption():
    from backend.tests.versions.v3.test_b_targets import edit

    value = scripted(overlap_case(), {"edits": [edit("retime", "b", start="11:30", end="12:30")]})
    model = next(c for c in value["calls"] if c["operation"] == "repair_model")
    model["duration_seconds"] = 80
    out = replay(value)
    assert out["status"] == "complete", out["diagnostics"]
    assert out["outcome"]["repair"]["status"] == "REJECTED"
    assert not any(c["status"] == "accepted" for c in out["outcome"]["repair"]["components"])


def test_malformed_model_script_is_material_error_even_when_production_catches_it():
    value = scripted(overlap_case(), {"edits": []})
    model = next(c for c in value["calls"] if c["operation"] == "repair_model")
    model["response"] = {"not_a_patch": "invalid frozen material"}
    out = replay(value)
    assert out["status"] == "execution_material_error"
    assert "invalid_frozen_response:repair_model" in out["diagnostics"]


def test_finalization_restores_selected_semantics_after_unavailable_exploration():
    from backend.tests.versions.v3.test_repair_search import scenario

    original, ctx, _ = scenario((3,))
    value = case(review=True)
    value.update(
        primary=original.model_dump(mode="json"),
        requirements=ctx.contract.model_dump(mode="json"),
        supply_ids=list(ctx.original_supply_ids),
        places=[p.model_dump(mode="json") for p in ctx.places],
        semantics={},
    )
    value["runtime"]["v3_repair"].update(max_deletion_attempts=0, max_model_calls=1, max_rounds=1)
    value["original_input"]["additional_preferences"] = "relaxed"
    value["semantic_assessments"] = [
        dict(
            place_id=p.place_id,
            visit_object=p.name,
            role="attraction",
            categories=[],
            reason="Initial grounded role",
            evidence_refs=[p.source_ref],
            matches=[],
            exception_requirement_ids=[],
        )
        for p in ctx.places
    ]
    value = scripted(value, {"edits": []}, semantic_role="unresolved")
    execution = replay(value)
    assert execution["status"] == "complete", execution["diagnostics"]
    assert any(c["operation"] == "poi_semantics" for c in execution["calls"])
    outcome = execution["outcome"]
    repair = outcome["repair"]
    assert repair["selected_round_index"] is None
    assert repair["selected_semantic_assessments"] == value["semantic_assessments"]
    assert outcome["final_report"] == repair["adopted_report"]
    assert outcome["soft_pace"]["after"]["mean_penalty"] == 40
    assert outcome["soft_pace"]["target_state"] == "residual"
