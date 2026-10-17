"""Uniform identity judgment through offline public interfaces and synthetic facts."""

import copy
import json
import socket

import pytest

from backend.evaluation.controlled_cli import main as controlled_main
from backend.evaluation.identity import identity_references
from backend.evaluation.identity_adoption import resolve_v0_identities
from backend.evaluation.identity_adoption_cli import main as v0_main
from backend.evaluation.identity_cli import main as identity_main
from backend.evaluation.identity_llm import prepare_identity_judgment as _prepare_identity_judgment
from backend.evaluation.identity_llm import resolve_llm_identities as resolve_identities
from backend.evaluation.preparation import identity_ready
from backend.evaluation.records import canonical_digest
from backend.evaluation.routes import prepare_routes
from backend.evaluation.snapshot import build_evidence_plan
from backend.evaluation.snapshot_coordinates import prepare_snapshot_coordinates
from backend.evaluation.tools.route_requests import prepare_v0_route_requests
from backend.tests.evaluation.test_identity import evidence, prepared, search
from backend.tests.evaluation.test_requirement_schedule import context

pytest_plugins = (
    "backend.tests.evaluation.test_intake",
    "backend.tests.evaluation.test_identity_adoption",
)


def prepare_identity_judgment(intake, evidence, *, model):
    return _prepare_identity_judgment(intake, evidence, model=model, historical=True)


def test_packet_covers_protected_subjects_and_all_versions(batch):
    def protect(manifest, _results, save, root):
        spec = json.loads((root / "requirements.json").read_text())
        spec["subjects"] = [{"subject_id": "required-museum", "place_name": "Museum A"}]
        spec["obligations"] = [
            {
                "obligation_id": "required-visit",
                "kind": "required_visit",
                "resolution": "resolved",
                "subject_ref": "required-museum",
                "count": {"mode": "exact", "value": 1},
                "source_refs": [{"field_path": "additional_preferences", "quote": "architecture"}],
            }
        ]
        manifest["groups"][0]["requirement_spec_ref"] = save(
            "requirements.json", spec, spec["schema_version"]
        )

    intake = prepared(batch, protect)
    refs = identity_references(intake)
    observed = evidence(intake, [search(r, r["name"]) for r in refs])
    packet = prepare_identity_judgment(intake, observed, model="fixture-model").to_dict()
    cases = json.loads(packet["request"]["input"])["cases"]
    assert len(cases) == 9
    assert {c["version"] for c in cases} == {None, "v0", "v1", "v2", "v3"}
    assert any(c["kind"] == "requirement_subject" for c in cases)
    assert all(c["reference_id"].startswith("r") for c in cases)
    assert all(c["claim"]["location"] is None for c in cases)
    assert packet["request"]["tools"] == []
    report = resolve_identities(intake, observed).to_dict()
    assert all(r["reason"] == "model_judgment_missing" for r in report["records"])
    assert report["review_queue"] == []
    judged = resolve_identities(
        intake, observed, model_result=model_material(intake, observed)
    ).to_dict()
    assert all(r["resolution"] == "resolved" for r in judged["records"])
    assert any(r["high_impact"] for r in judged["records"])
    assert all(r["review_history"] == [] for r in judged["records"])


def model_material(
    intake, observed, *, decisions=None, historical=True, legacy_v0=False, visits_only=False
):
    packet = _prepare_identity_judgment(
        intake,
        observed,
        model="fixture-model",
        historical=historical,
        legacy_v0=legacy_v0,
        visits_only=visits_only,
    ).to_dict()
    cases = json.loads(packet["request"]["input"])["cases"]
    rows = []
    for case in cases:
        candidate = case["candidates"][0] if case["candidates"] else None
        row = {
            "reference_id": case["reference_id"],
            "decision": "match" if candidate else "unknown",
            "candidate_id": candidate["place_id"] if candidate else None,
            "rationale": "Independent name and address identify the intended venue.",
            "evidence_fields": [
                "claim.place_name",
                "claim.destination",
                "candidate.display_name",
                "candidate.formatted_address",
            ]
            if candidate
            else [],
            "address_assessment": "not_supplied",
            "destination_assessment": "consistent" if candidate else "unknown",
        }
        if not historical and case["kind"] == "requirement_subject" and candidate:
            if case["claim"]["claimed_place_id"]:
                row["evidence_fields"].append("claim.claimed_place_id")
            if case["claim"]["location"]:
                row["address_assessment"] = "equivalent"
                row["evidence_fields"].append("claim.location")
        if decisions:
            decisions(row, case)
        rows.append(row)
    response = {
        "id": "fixture-response",
        "model": "fixture-model",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "decisions": rows
                                if historical or legacy_v0
                                else {row["reference_id"]: row for row in rows}
                            }
                        ),
                    }
                ],
            }
        ],
    }
    return {
        "schema_version": "rtpeval_identity_model_result_1",
        "packet": packet,
        "requested_at": "2026-10-05T10:00:00Z",
        "retrieved_at": "2026-10-05T10:00:01Z",
        "response": response,
        "response_sha256": canonical_digest(response),
    }


def test_model_matches_all_versions_without_human_or_audit_gate(batch):
    intake = prepared(batch)
    refs = identity_references(intake)
    observed = evidence(intake, [search(r, r["name"], place_id="venue-" + r["name"]) for r in refs])
    result = model_material(intake, observed)
    report = resolve_identities(intake, observed, model_result=result).to_dict()
    assert all(r["resolution"] == "resolved" for r in report["records"])
    assert {r["decision_route"] for r in report["records"]} == {"llm_judgment"}
    assert report["judgment_queue"] == []
    assert report["audit_plan_hash"] is None
    assert report["review_hash"] is None
    assert report["groups"][0]["versions"]["v3"]["final"]["grounding_fraction"] == 1


def test_consumers_replay_llm_report_and_reject_tampering(batch):
    intake = prepared(batch)
    observed = evidence(intake, [search(r, r["name"]) for r in identity_references(intake)])
    report = resolve_identities(
        intake, observed, model_result=model_material(intake, observed)
    ).to_dict()
    assert identity_ready(intake.to_dict(), report)
    assert len(build_evidence_plan(intake, report, [])["requests"]) == 1
    for tamper in (
        "canonical_place_id",
        "policy",
        "prior_policy",
        "provenance",
        "original_claim",
        "grounding_verdict",
    ):
        forged = copy.deepcopy(report)
        if tamper == "policy":
            forged["association_policy_version"] = "structural_claims_typed_addresses_3"
        elif tamper == "prior_policy":
            forged["association_policy_version"] = "llm_identity_judgment_1"
        elif tamper == "provenance":
            forged["model_judgment_provenance"]["response_id"] = "forged"
        elif tamper == "original_claim":
            forged["records"][0]["original_claim"]["location"] = "silently repaired"
        elif tamper == "grounding_verdict":
            forged["records"][0][tamper] = "FAIL"
        else:
            forged["records"][0][tamper] = "foreign-id"
        assert not identity_ready(intake.to_dict(), forged)
        with pytest.raises(ValueError):
            build_evidence_plan(intake, forged, [])


@pytest.mark.parametrize(
    "assessment,decision,destination,resolved",
    [
        ("equivalent", "match", "consistent", True),
        ("different_precision", "match", "consistent", True),
        ("incorrect_claim", "match", "consistent", False),
        ("different_place", "match", "consistent", False),
        ("unknown", "match", "consistent", False),
        ("equivalent", "match", "contradictory", False),
        ("unknown", "unknown", "unknown", False),
        ("different_place", "no_supported_match", "contradictory", False),
    ],
)
def test_address_identity_and_uncertainty_are_separate(
    batch, assessment, decision, destination, resolved
):
    def location(_, results, _save, _root):
        results["v0"]["itinerary"]["days"][0]["activities"][0]["location"] = (
            "Original declared address"
        )
        return "v0"

    intake = prepared(batch, location)
    ref = next(r for r in identity_references(intake) if r["version"] == "v0")
    observed = evidence(intake, [search(ref, ref["name"])])
    original = intake.to_dict()

    def choose(row, case):
        if case["claim"]["location"]:
            row.update(
                decision=decision, address_assessment=assessment, destination_assessment=destination
            )
            if decision == "match":
                row["evidence_fields"].append("claim.location")
            else:
                row.update(candidate_id=None, evidence_fields=[])
                if assessment in ("incorrect_claim", "different_place"):
                    row["evidence_fields"] = [
                        "claim.place_name",
                        "claim.destination",
                        "claim.location",
                        "case.candidates",
                    ]

    report = resolve_identities(
        intake, observed, model_result=model_material(intake, observed, decisions=choose)
    ).to_dict()
    record = next(r for r in report["records"] if r["reference_id"] == ref["reference_id"])
    assert (record["resolution"] == "resolved") == resolved
    if assessment in ("incorrect_claim", "different_place"):
        assert record["grounding_verdict"] == "FAIL"
        assert record["canonical_place_id"] is None
    elif not resolved:
        assert record["grounding_verdict"] == "UNKNOWN"
    else:
        assert record["grounding_verdict"] == "PASS"
    assert record["model_judgment"]["address_assessment"] == assessment
    assert record["original_claim"]["location"] == "Original declared address"
    assert intake.to_dict() == original
    assert len(report["judgment_queue"]) == 7 + (
        not resolved and assessment not in ("incorrect_claim", "different_place")
    )


@pytest.mark.parametrize("assessment", ["incorrect_claim", "different_place"])
def test_address_failure_requires_a_supplied_location_and_independent_citations(batch, assessment):
    def location(_, results, _save, _root):
        results["v0"]["itinerary"]["days"][0]["activities"][0]["location"] = "Wrong address"
        return "v0"

    intake = prepared(batch, location)
    observed = evidence(intake, [search(r, r["name"]) for r in identity_references(intake)])

    def unsupported(row, case):
        row.update(decision="unknown", candidate_id=None, address_assessment=assessment)
        row["evidence_fields"] = ["claim.location"] if case["claim"]["location"] else []

    with pytest.raises(ValueError):
        resolve_identities(
            intake, observed, model_result=model_material(intake, observed, decisions=unsupported)
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "foreign",
        "partial",
        "duplicate",
        "stale",
        "hash",
        "model",
        "tool",
        "timestamp",
        "citation",
        "missing_address",
        "bad_components",
        "malformed_content",
        "bad_short_text",
    ],
)
def test_invalid_model_material_is_not_adopted(batch, mutation):
    intake = prepared(batch)
    observed = evidence(intake, [search(r, r["name"]) for r in identity_references(intake)])
    result = model_material(intake, observed)
    response = result["response"]
    content = response["output"][0]["content"][0]
    rows = json.loads(content["text"])
    if mutation == "foreign":
        rows["decisions"][0]["candidate_id"] = "p99"
    elif mutation == "partial":
        rows["decisions"].pop()
    elif mutation == "duplicate":
        rows["decisions"][1] = rows["decisions"][0]
    elif mutation == "stale":
        result["packet"]["evidence_sha256"] = "a" * 64
    elif mutation == "hash":
        result["response_sha256"] = "b" * 64
    elif mutation == "model":
        response["model"] = "other-model"
    elif mutation == "tool":
        response["output"].append({"type": "function_call"})
    elif mutation == "timestamp":
        result["retrieved_at"] = "2026-10-05T09:00:00Z"
    elif mutation == "citation":
        rows["decisions"][0]["evidence_fields"] = ["candidate.rating"]
    elif mutation == "missing_address":
        del rows["decisions"][0]["address_assessment"]
    elif mutation == "malformed_content":
        response["output"][0]["content"] = ["invalid content"]
    else:
        observed["records"][0]["search"]["candidates"][0]["address_components"] = (
            [{"longText": "Example City", "shortText": 42, "types": ["locality"]}]
            if mutation == "bad_short_text"
            else "not-components"
        )
        result = model_material(
            intake,
            observed,
            decisions=lambda r, c: (
                r["evidence_fields"].append("candidate.address_components")
                if c["candidates"] and c["candidates"][0].get("address_components")
                else None
            ),
        )
        response = result["response"]
        content = response["output"][0]["content"][0]
        rows = json.loads(content["text"])
    content["text"] = json.dumps(rows)
    if mutation != "hash":
        result["response_sha256"] = canonical_digest(response)
    with pytest.raises(ValueError):
        resolve_identities(intake, observed, model_result=result)
    pending = resolve_identities(intake, observed).to_dict()
    pending["identity_llm_replay"]["model_result"] = result
    assert not identity_ready(intake.to_dict(), pending)


def test_default_cli_prepares_and_imports_model_result_without_audit(batch, capsys):
    manifest, _, write, save, root = batch
    intake = prepared(batch)
    observed = evidence(intake, [search(r, r["name"]) for r in identity_references(intake)])
    save("observed.json", observed)
    args = [str(write()), str(root / "observed.json")]
    assert identity_main(args + ["--prepare", "--model", "fixture-model"]) == 0
    packet = json.loads(capsys.readouterr().out)
    assert packet["request"]["model"] == "fixture-model"
    assert identity_main(args) == 3
    pending = json.loads(capsys.readouterr().out)
    assert pending["review_queue"] == []
    save("model.json", model_material(intake, observed, historical=False))
    assert identity_main(args + ["--model-result", str(root / "model.json")]) == 0
    report = json.loads(capsys.readouterr().out)
    assert identity_ready(intake.to_dict(), report)


def test_v3_optional_projections_are_judged_independently(batch):
    _, results, write, _, _ = batch
    results["v3"]["v3"] = {
        "draft": copy.deepcopy(results["v3"]["itinerary"]),
        "final_primary": copy.deepcopy(results["v3"]["itinerary"]),
    }
    from backend.evaluation.intake import load_batch

    intake = load_batch(write("v3"))
    refs = identity_references(intake)
    observed = evidence(intake, [search(r, r["name"]) for r in refs])
    report = resolve_identities(
        intake, observed, model_result=model_material(intake, observed)
    ).to_dict()
    assert len(report["records"]) == 12
    assert {r["projection"] for r in report["records"] if r["version"] == "v3"} == {
        "final",
        "draft",
        "final_primary",
    }
    assert all(v["grounding_fraction"] == 1 for v in report["groups"][0]["versions"]["v3"].values())


@pytest.mark.parametrize("adoption_case", [{"high_impact": True}], indirect=True)
def test_v0_material_cli_coordinates_and_routes_use_model_policy(
    adoption_case, monkeypatch, capsys
):
    intake, observed, bundle, _, _, _, _, _ = adoption_case

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Offline identity work must not contact a model or provider")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    assert v0_main([str(bundle), "--prepare", "--model", "fixture-model"]) == 0
    assert (
        json.loads(capsys.readouterr().out)["schema_version"]
        == "rtpeval_identity_judgment_packet_1"
    )
    assert v0_main([str(bundle)]) == 3
    pending = json.loads(capsys.readouterr().out)
    assert pending["audit_selected_reference_ids"] == []
    assert pending["review_queue"] == []
    material = model_material(intake, observed, historical=False)
    path = bundle.parent / "new-model.json"
    path.write_text(json.dumps(material), encoding="utf-8")
    assert v0_main([str(bundle), "--model-result", str(path)]) == 3
    report = json.loads(capsys.readouterr().out)
    assert report == resolve_v0_identities(intake, bundle, model_result=material).to_dict()
    coords = prepare_snapshot_coordinates(
        intake, report, bundle.parent / "identity-snapshot"
    ).to_dict()
    assert coords["status"] == "complete"
    assert len(coords["records"]) == 2
    routes = prepare_routes(
        intake,
        report,
        schedule_context=context(intake),
        identity_snapshot_directory=bundle.parent / "identity-snapshot",
    ).to_dict()
    assert routes["status"] == "complete", routes["diagnostics"]
    package = prepare_v0_route_requests(
        bundle, report, prepared_at="2026-10-06T10:00:00Z", schedule_context=context(intake)
    ).to_dict()
    assert package["status"] == "complete"
    assert package["counts"]["identity_eligible_legs"] == 1
    assert package["counts"]["actual_sends"] == 0


@pytest.mark.parametrize("adoption_case", [{"claimed_location": "Wrong address"}], indirect=True)
@pytest.mark.parametrize("assessment", ["incorrect_claim", "different_place", "unknown"])
def test_v0_address_failure_and_trusted_physical_association_remain_separate(
    adoption_case, assessment, monkeypatch
):
    intake, observed, bundle, _, _, _, _, _ = adoption_case

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Address evaluation must remain offline")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    original = copy.deepcopy(intake.to_dict())

    def choose(row, case):
        if case["claim"]["location"]:
            row["address_assessment"] = assessment
            row["evidence_fields"].append("claim.location")

    report = resolve_v0_identities(
        intake,
        bundle,
        model_result=model_material(intake, observed, decisions=choose, historical=False),
    ).to_dict()
    assert identity_ready(intake.to_dict(), report)
    coordinates = prepare_snapshot_coordinates(
        intake, report, bundle.parent / "identity-snapshot"
    ).to_dict()
    assert coordinates["status"] == "complete", coordinates["diagnostics"]
    associated = assessment == "incorrect_claim"
    assert {r["place_id"] for r in coordinates["records"]} == (
        {"canonical-Museum A", "canonical-Museum B"} if associated else {"canonical-Museum B"}
    )
    routes = prepare_routes(
        intake,
        report,
        schedule_context=context(intake),
        identity_snapshot_directory=bundle.parent / "identity-snapshot",
    ).to_dict()
    assert routes["status"] == "complete", routes["diagnostics"]
    v0 = next(r for r in routes["results"] if r["version"] == "v0")
    assert v0["legs"][0]["canonical_endpoints"] == [
        "canonical-Museum A" if associated else None,
        "canonical-Museum B",
    ]
    assert (v0["legs"][0]["expected_context"] is not None) == associated
    package = prepare_v0_route_requests(
        bundle, report, prepared_at="2026-10-06T10:00:00Z", schedule_context=context(intake)
    ).to_dict()
    assert package["status"] == "complete", package["diagnostics"]
    assert package["counts"]["identity_eligible_legs"] == int(associated)
    assert package["counts"]["actual_sends"] == 0
    assert intake.to_dict() == original


def test_controlled_identity_cli_has_the_same_offline_judgment_policy(batch, capsys):
    _, _, _, save, root = batch
    intake = prepared(batch)
    observed = evidence(intake, [search(r, r["name"]) for r in identity_references(intake)])
    save("preparation.json", intake.to_dict())
    save("observed.json", observed)
    args = ["identity", str(root / "preparation.json"), str(root / "observed.json")]
    assert controlled_main(args) == 3
    assert json.loads(capsys.readouterr().out)["review_queue"] == []
    assert controlled_main(args + ["--prepare", "--model", "fixture-model"]) == 0
    assert "request_sha256" in json.loads(capsys.readouterr().out)
    save("model.json", model_material(intake, observed, historical=False))
    assert controlled_main(args + ["--model-result", str(root / "model.json")]) == 0
    assert identity_ready(intake.to_dict(), json.loads(capsys.readouterr().out))


def test_claimed_wrong_id_and_conflicting_observations_remain_visible_to_model(batch):
    def supplied(_, results, _save, _root):
        results["v1"]["itinerary"]["days"][0]["activities"][0].update(
            source_place_id="wrong-venue", location="Declared address"
        )
        return "v1"

    from backend.tests.evaluation.test_identity import details

    intake = prepared(batch, supplied)
    refs = identity_references(intake)
    observations = [search(r, r["name"], place_id="right-venue") for r in refs]
    ref = next(r for r in refs if r["version"] == "v1")
    observation = next(o for o in observations if o["reference_id"] == ref["reference_id"])
    observation.update(details(ref, "Different venue", place_id="wrong-venue"))
    observed = evidence(intake, observations)
    packet = prepare_identity_judgment(intake, observed, model="fixture-model").to_dict()
    wire_case = next(
        c for c in json.loads(packet["request"]["input"])["cases"] if c["claim"]["claimed_place_id"]
    )
    assert wire_case["claim"]["claimed_place_id"].startswith("p")
    assert wire_case["observation"]["details"]["requested_place_id"].startswith("p")
    assert {c["display_name"] for c in wire_case["candidates"]} == {"Museum A", "Different venue"}

    def choose(row, case):
        if case["claim"]["claimed_place_id"]:
            row.update(
                candidate_id=next(
                    c["place_id"] for c in case["candidates"] if c["display_name"] == "Museum A"
                ),
                address_assessment="incorrect_claim",
            )
            row["evidence_fields"].extend(["claim.location", "claim.claimed_place_id"])

    report = resolve_identities(
        intake, observed, model_result=model_material(intake, observed, decisions=choose)
    ).to_dict()
    record = next(r for r in report["records"] if r["reference_id"] == ref["reference_id"])
    assert record["canonical_place_id"] is None
    assert record["grounding_verdict"] == "FAIL"
    assert record["claimed_id_association"] == "conflicting"
    assert record["original_claim"]["location"] == "Declared address"


def test_valid_raw_address_components_leave_semantic_judgment_with_model(batch):
    intake = prepared(batch)
    refs = identity_references(intake)
    observed = evidence(intake, [search(r, r["name"]) for r in refs])
    observed["records"][0]["search"]["candidates"][0]["address_components"] = [
        {"longText": "District", "shortText": "Dist", "types": ["sublocality"]},
        {"longText": "Neighborhood", "types": ["sublocality"]},
    ]

    def cite(row, case):
        if case["candidates"][0].get("address_components"):
            row["evidence_fields"].append("candidate.address_components")

    report = resolve_identities(
        intake, observed, model_result=model_material(intake, observed, decisions=cite)
    ).to_dict()
    assert report["status"] == "complete"
    assert identity_ready(intake.to_dict(), report)
