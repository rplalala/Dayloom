"""Independent controlled outcomes, not internal acceptance labels."""

import asyncio
import json

import pytest

from backend.evaluation.records import canonical_digest
from backend.tests.evaluation.controlled_fixtures import expectations, material
from backend.tests.evaluation.test_controlled_replay import case, replay, scripted
from backend.tests.versions.v3.test_b_targets import edit, visit
from backend.tests.versions.v3.test_validation import DAY


@pytest.mark.parametrize("reviewed", [False, True])
def test_opening_venue_selector_and_human_facts_use_verified_association(tmp_path, reviewed):
    from backend.evaluation.controlled_preparation import prepare_controlled_case
    from backend.evaluation.controlled_report import build_controlled_report
    from backend.evaluation.identity import identity_references, resolve_identities
    from backend.evaluation.routes import prepare_routes
    from backend.evaluation.snapshot import AcquisitionPolicy, Response, acquire_snapshot
    from backend.tests.evaluation.test_identity import details

    value = case()
    value["role"] = "target"
    execution = replay(value)
    original_hash = canonical_digest(execution)
    package = material(value, execution, tmp_path / "legacy")
    prepared = prepare_controlled_case(value, execution, package["requirement_spec"]).to_dict()
    observed = {
        "schema_version": "rtpeval_identity_evidence_1",
        "batch_id": prepared["batch_id"],
        "batch_revision": prepared["revision"],
        "records": [
            details(r, r["name"], r["claimed_place_id"], address="Fixture")
            for r in identity_references(prepared)
        ],
    }
    identity = resolve_identities(prepared, observed).to_dict()
    assert all(
        r["grounding_verdict"] == "FAIL"
        and r["canonical_place_id"] is None
        and r["place_association"]["place_id"] == "a"
        for r in identity["records"]
    )
    routes = prepare_routes(
        prepared,
        identity,
        package["schedule_context"],
        route_reviews=package["route_reviews"],
        coordinate_evidence=package["coordinate_evidence"],
        paired=True,
    ).to_dict()
    assert routes["status"] == "complete", routes["diagnostics"]
    package.update(
        identity_report=identity,
        expected_plan=routes["evidence_plan"],
        snapshot_directory=tmp_path / "current",
    )

    async def transport(request):
        return Response(
            200,
            json.dumps(
                {
                    "id": request["parameters"]["place_id"],
                    "timeZone": {"id": "UTC"},
                    "regularOpeningHours": {}
                    if reviewed
                    else {
                        "periods": [
                            {
                                "open": {"day": DAY.isoweekday() % 7, "hour": 8, "minute": 0},
                                "close": {"day": DAY.isoweekday() % 7, "hour": 18, "minute": 0},
                            }
                        ]
                    },
                }
            ).encode(),
        )

    asyncio.run(
        acquire_snapshot(
            routes["evidence_plan"],
            package["snapshot_directory"],
            transport,
            AcquisitionPolicy(100),
        )
    )
    goals = expectations(
        value,
        execution,
        guards=[
            {
                "goal_id": "opening-place",
                "basis": "product_policy",
                "condition": {
                    "kind": "check",
                    "dimension": "opening",
                    "activity_ids": ["a"],
                    "canonical_place_id": "a",
                },
            }
        ],
    )
    report = build_controlled_report(
        value,
        execution,
        goals,
        **package,
        factual_reviews=opening_review(value, execution) if reviewed else None,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert report["status"] == "complete", report["diagnostics"]
    assert report["pair"]["stages"]["draft"]["primary_metrics"]["opening"]["checks"][0][
        "state"
    ] == ("UNKNOWN" if reviewed else "PASS")
    assert report["guards"][0]["before"]["state"] == "PASS"
    assert report["guards"][0]["after"]["state"] == "PASS"
    checks = report["reviewed_checks"]["stages"]["draft"]["primary_metrics"]
    assert checks["grounding"]["checks"][0]["state"] == "FAIL"
    assert checks["opening"]["checks"][0]["canonical_place_id"] is None
    assert checks["opening"]["checks"][0]["associated_place_id"] == "a"
    assert canonical_digest(execution) == original_hash


def opening_review(value, execution):
    return {
        "schema_version": "rtpeval_controlled_facts_1",
        "case_id": value["case_id"],
        "case_hash": execution["case_hash"],
        "replay_hash": execution["replay_hash"],
        "revision": "1",
        "reviewer_ref": "independent-human",
        "reviewed_at": "2026-10-04T00:00:00Z",
        "rationale": "Verified venue timetable",
        "supporting_refs": ["synthetic:verified-timetable"],
        "opening": [
            {
                "canonical_place_id": "a",
                "date": str(DAY),
                "timezone": "UTC",
                "open_intervals": [{"start": f"{DAY}T08:00:00Z", "end": f"{DAY}T18:00:00Z"}],
                "closed_intervals": [],
            }
        ],
        "routes": [],
    }


def test_separately_reviewed_hours_resolve_unknown_without_changing_replay(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report

    value = case()
    execution = replay(value)
    original_hash = canonical_digest(execution)
    package = material(value, execution, tmp_path / "snapshot", hours={"regularOpeningHours": {}})
    initial = build_controlled_report(
        value,
        execution,
        expectations(value, execution),
        **package,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert initial["control"]["outcome"] == "unresolved"
    reviewed = build_controlled_report(
        value,
        execution,
        expectations(value, execution),
        **package,
        factual_reviews=opening_review(value, execution),
        generated_at="2026-10-04T00:00:00Z",
    )
    assert reviewed["status"] == "complete", reviewed["diagnostics"]
    assert reviewed["control"]["outcome"] == "valid_no_change"
    assert (
        reviewed["pair"]["stages"]["draft"]["primary_metrics"]["opening"]["checks"][0]["state"]
        == "UNKNOWN"
    )
    assert (
        reviewed["reviewed_checks"]["stages"]["draft"]["primary_metrics"]["opening"]["checks"][0][
            "state"
        ]
        == "PASS"
    )
    assert canonical_digest(execution) == original_hash


def test_human_hours_cannot_override_independently_confirmed_closed_visit(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report

    value = case()
    execution = replay(value)
    package = material(
        value, execution, tmp_path / "snapshot", hours={"regularOpeningHours": {"periods": []}}
    )
    out = build_controlled_report(
        value,
        execution,
        expectations(value, execution),
        **package,
        factual_reviews=opening_review(value, execution),
        generated_at="2026-10-04T00:00:00Z",
    )
    assert out["status"] == "needs_material_correction"
    assert "contradict" in str(out["diagnostics"])


def addition_case(*, exclusive=False):
    from datetime import timedelta

    value = case(review=True)
    value["reference_date"] = str(DAY - timedelta(days=1))
    value["semantic_assessments"] = [
        {
            "place_id": p["place_id"],
            "visit_object": p["name"],
            "role": "attraction",
            "categories": [],
            "reason": "Synthetic attraction",
            "evidence_refs": [p["source_ref"]],
            "matches": [],
            "exception_requirement_ids": [],
        }
        for p in value["places"]
    ]
    if exclusive:
        value["original_input"]["additional_preferences"] = "Exactly one primary visit on this day."
    return scripted(value, {"edits": [edit("add", pid="b", start="11:00", end="12:00")]})


def test_review_addition_is_lawful_control_change_when_independently_feasible(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report

    value = addition_case()
    execution = replay(value)
    assert execution["outcome"]["repair"] is not None, execution["outcome"]["original_report"][
        "findings"
    ]
    assert execution["outcome"]["repair"]["status"] == "ACCEPTED_COMPLETE", execution["outcome"][
        "repair"
    ]["reason"]
    package = material(value, execution, tmp_path / "snapshot")
    out = build_controlled_report(
        value,
        execution,
        expectations(value, execution),
        **package,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert out["status"] == "complete", out["diagnostics"]
    assert out["control"]["outcome"] == "lawful_change"
    assert out["execution"]["repair_status"] == "ACCEPTED_COMPLETE"


def test_explicit_one_visit_guard_catches_internally_accepted_addition(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report

    value = addition_case(exclusive=True)
    execution = replay(value)
    assert execution["outcome"]["repair"]["status"] == "ACCEPTED_COMPLETE"
    package = material(value, execution, tmp_path / "snapshot")
    goals = expectations(
        value,
        execution,
        guards=[
            {
                "goal_id": "one-visit",
                "basis": "explicit_requirement",
                "condition": {"kind": "daily_count", "date": str(DAY), "minimum": 1, "maximum": 1},
                "source": {
                    "field": "additional_preferences",
                    "quote": "Exactly one primary visit on this day.",
                },
            }
        ],
    )
    out = build_controlled_report(
        value, execution, goals, **package, generated_at="2026-10-04T00:00:00Z"
    )
    assert out["status"] == "complete", out["diagnostics"]
    assert out["guards"][0]["before"]["state"] == "PASS"
    assert out["guards"][0]["after"]["state"] == "FAIL"
    assert out["control"]["outcome"] == "regressed"


def test_invalid_replay_retains_expected_target_inventory_without_quality_verdict(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report

    value = case()
    execution = replay(value)
    package = material(value, execution, tmp_path / "snapshot")
    goals = expectations(
        value,
        execution,
        targets=[
            {
                "goal_id": "opening",
                "basis": "confirmed_conflict",
                "detector": {"check": "opening", "activity_ids": ["a"]},
                "condition": {"kind": "check", "dimension": "opening", "activity_ids": ["a"]},
            }
        ],
    )
    execution["outcome"]["reason"] = "tampered"
    out = build_controlled_report(
        value, execution, goals, **package, generated_at="2026-10-04T00:00:00Z"
    )
    assert out["status"] == "needs_material_correction"
    assert out["target_counts"]["expected"] == 1
    assert out["targets"][0]["independent_outcome"] == "unavailable"


def test_real_overlap_resolution_is_independent_of_internal_progress_label(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report

    value = case(
        [[visit("a", "a", start="10:00", end="11:00"), visit("b", "b", start="10:30", end="11:30")]]
    )
    value["role"] = "target"
    value = scripted(value, {"edits": [edit("retime", "b", start="11:30", end="12:30")]})
    execution = replay(value)
    package = material(value, execution, tmp_path / "snapshot")
    goals = expectations(
        value,
        execution,
        targets=[
            {
                "goal_id": "overlap",
                "basis": "confirmed_conflict",
                "detector": {"check": "overlap", "activity_ids": ["a", "b"]},
                "condition": {
                    "kind": "check",
                    "dimension": "conflicts",
                    "activity_ids": ["a", "b"],
                },
            }
        ],
    )
    out = build_controlled_report(
        value, execution, goals, **package, generated_at="2026-10-04T00:00:00Z"
    )
    assert out["status"] == "complete", out["diagnostics"]
    row = out["targets"][0]
    assert row["detection"] == "detected"
    assert row["authorization"] == "authorized"
    assert row["model_attempted"]
    assert row["independent_outcome"] == "resolved"
    assert row["before"]["state"] == "FAIL" and row["after"]["state"] == "PASS"
    assert row["adoption"] == "adopted_component"


def test_new_closed_visit_is_a_control_regression_despite_internal_adoption(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report

    value = addition_case()
    execution = replay(value)
    package = material(
        value,
        execution,
        tmp_path / "snapshot",
        hours_by_place={"b": {"regularOpeningHours": {"periods": []}}},
    )
    out = build_controlled_report(
        value,
        execution,
        expectations(value, execution),
        **package,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert out["status"] == "complete", out["diagnostics"]
    assert out["control"]["outcome"] == "regressed"
    assert any(p["dimension"] == "opening" for p in out["control"]["confirmed_problems"])


def test_route_review_fills_only_exact_query_and_retains_other_unknown_units(tmp_path):
    from backend.app.schemas.itinerary import Transfer
    from backend.evaluation.controlled_report import build_controlled_report

    value = case([[visit("a", "a"), visit("b", "b", start="11:00", end="12:00")]])
    value["primary"]["transfers"] = [
        Transfer(
            from_activity_id="a",
            to_activity_id="b",
            origin_place_id="a",
            destination_place_id="b",
            mode="WALK",
            mode_source="synthetic",
            departure_time=f"{DAY}T10:00:00Z",
            calculation_basis="synthetic",
            validation_state="UNKNOWN",
        ).model_dump(mode="json")
    ]
    execution = replay(value)
    package = material(value, execution, tmp_path / "snapshot", route_fields={"duration": None})
    out = build_controlled_report(
        value,
        execution,
        expectations(value, execution),
        **package,
        generated_at="2026-10-04T00:00:00Z",
    )
    checks = out["pair"]["stages"]["draft"]["primary_metrics"]["routes"]["checks"]
    assert checks[0]["state"] == "UNKNOWN"
    facts = opening_review(value, execution)
    facts["opening"] = []
    facts["routes"] = [
        {
            "expected_context_hash": canonical_digest(checks[0]["expected_context"]),
            "availability": "route_exists",
            "duration_nanoseconds": 600_000_000_000,
            "distance_meters": 100,
        }
    ]
    reviewed = build_controlled_report(
        value,
        execution,
        expectations(value, execution),
        **package,
        factual_reviews=facts,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert reviewed["status"] == "complete", reviewed["diagnostics"]
    assert (
        reviewed["reviewed_checks"]["stages"]["draft"]["primary_metrics"]["routes"]["checks"][0][
            "state"
        ]
        == "PASS"
    )
    assert reviewed["control"]["outcome"] == "unresolved"
    facts["routes"][0]["expected_context_hash"] = "0" * 64
    invalid = build_controlled_report(
        value,
        execution,
        expectations(value, execution),
        **package,
        factual_reviews=facts,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert invalid["status"] == "needs_material_correction"


def test_valid_control_is_independently_verified_without_four_version_outputs(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report

    value = case()
    execution = replay(value)
    package = material(value, execution, tmp_path / "snapshot")
    out = build_controlled_report(
        value,
        execution,
        expectations(value, execution),
        **package,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert out["status"] == "complete", out["diagnostics"]
    assert out["control"]["outcome"] == "valid_no_change"
    assert out["control"]["confirmed_problems"] == []
    assert out["targets"] == []
    assert set(out["pair"]["stages"]) == {"draft", "final_primary"}


def test_independent_opening_conflict_detection_miss_stays_in_denominator(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report

    value = case()
    value["role"] = "target"
    execution = replay(value)
    package = material(
        value, execution, tmp_path / "snapshot", hours={"regularOpeningHours": {"periods": []}}
    )
    goals = expectations(
        value,
        execution,
        targets=[
            {
                "goal_id": "closed-visit",
                "basis": "confirmed_conflict",
                "detector": {"check": "opening", "activity_ids": ["a"]},
                "condition": {"kind": "check", "dimension": "opening", "activity_ids": ["a"]},
            }
        ],
    )
    out = build_controlled_report(
        value, execution, goals, **package, generated_at="2026-10-04T00:00:00Z"
    )
    assert out["status"] == "complete", out["diagnostics"]
    assert out["target_counts"]["expected"] == 1
    assert out["target_counts"]["detected"] == 0
    assert out["targets"][0]["detection"] == "missed"
    assert out["targets"][0]["independent_outcome"] == "residual"
    assert out["targets"][0]["before"]["state"] == "FAIL"


def test_discarded_exploration_is_not_controlled_final_adoption(tmp_path):
    from backend.evaluation.controlled_report import build_controlled_report
    from backend.tests.versions.v3.test_repair_search import move, scenario

    original, ctx, _ = scenario((4, 2, 3))
    value = case(review=True)
    value.update(
        role="target",
        primary=original.model_dump(mode="json"),
        requirements=ctx.contract.model_dump(mode="json"),
        supply_ids=list(ctx.original_supply_ids),
        places=[p.model_dump(mode="json") for p in ctx.places],
    )
    value["original_input"].update(
        end_date=str(original.end_date), additional_preferences="relaxed"
    )
    value["runtime"]["v3_repair"].update(max_deletion_attempts=0, max_model_calls=2, max_rounds=2)
    value = scripted(value, {"edits": [move("d0_3", 1)]})
    execution = replay(value)
    assert execution["status"] == "complete", execution["diagnostics"]
    assert execution["outcome"]["repair"]["rounds"][0]["exploration_transition"]
    assert execution["outcome"]["repair"]["selected_round_index"] is None
    package = material(value, execution, tmp_path / "snapshot")
    goals = expectations(
        value,
        execution,
        targets=[
            {
                "goal_id": "pace",
                "basis": "review_opportunity",
                "detector": {"check": "soft_pace", "dates": [str(DAY)]},
                "condition": {"kind": "daily_count", "date": str(DAY), "maximum": 2},
            }
        ],
    )
    result = build_controlled_report(
        value, execution, goals, **package, generated_at="2026-10-04T00:00:00Z"
    )
    assert result["status"] == "complete", result["diagnostics"]
    row = result["targets"][0]
    assert row["model_attempted"]
    assert row["adoption"] == "not_adopted"
    assert row["exploration_transitions"] == 1
    assert row["best_promotions"] == 0


@pytest.mark.parametrize("remaining", [180, 0])
def test_system_only_adoption_has_no_model_attempt_denominator(tmp_path, remaining):
    from backend.evaluation.controlled_report import build_controlled_report
    from backend.tests.versions.v3.test_repair_search import scenario

    original, ctx, _ = scenario((3,))
    value = case(review=True)
    value["request_remaining"] = remaining
    value.update(
        role="target",
        primary=original.model_dump(mode="json"),
        requirements=ctx.contract.model_dump(mode="json"),
        supply_ids=list(ctx.original_supply_ids),
        places=[p.model_dump(mode="json") for p in ctx.places],
    )
    value["original_input"]["additional_preferences"] = "relaxed"
    assert value["runtime"]["v3_repair"]["max_deletion_attempts"] == 12
    value = scripted(value, {"edits": []})
    execution = replay(value)
    assert execution["status"] == "complete", execution["diagnostics"]
    repair = execution["outcome"]["repair"]
    assert repair["selected_round_index"] == (1 if remaining else None)
    assert repair["counters"].get("model", 0) == 0
    assert repair["counters"].get("deterministic_attempts", 0) == bool(remaining)
    package = material(value, execution, tmp_path / "snapshot")
    goals = expectations(
        value,
        execution,
        targets=[
            {
                "goal_id": "pace",
                "basis": "review_opportunity",
                "detector": {"check": "soft_pace", "dates": [str(DAY)]},
                "condition": {"kind": "daily_count", "date": str(DAY), "maximum": 2},
            }
        ],
    )
    result = build_controlled_report(
        value, execution, goals, **package, generated_at="2026-10-04T00:00:00Z"
    )
    assert result["status"] == "complete", result["diagnostics"]
    row = result["targets"][0]
    assert not row["model_attempted"]
    assert row["operation_attempted"] == bool(remaining)
    assert row["deterministic_attempted"] == bool(remaining)
    assert row["adoption"] == ("adopted_component" if remaining else "not_adopted")
    assert row["independent_outcome"] == ("resolved" if remaining else "residual")
    assert result["target_counts"]["operation_attempted"] == bool(remaining)
    assert result["target_counts"]["deterministic_attempted"] == bool(remaining)
