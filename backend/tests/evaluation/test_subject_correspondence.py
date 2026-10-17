"""Independent requirement targets through source-bound public evaluator interfaces."""

import copy
import json

import pytest

from backend.evaluation.identity import identity_references
from backend.evaluation.identity_llm import RESULT_VERSION
from backend.evaluation.records import canonical_digest
from backend.tests.evaluation.test_identity import evidence, search
from backend.tests.evaluation.test_requirement_identity_versions import requirement_batch

pytest_plugins = ("backend.tests.evaluation.test_intake",)


@pytest.mark.parametrize(
    "provider_name", ["The Municipal Museum of Art", "Musée Municipal des Arts", "MMA Gallery"]
)
def test_destination_context_and_provider_name_are_one_common_target(batch, provider_name):
    from backend.evaluation.subject_correspondence import prepare_subject_judgment

    intake = requirement_batch(
        batch, bound=False, location="Example City, Country", destination="Example City, Country"
    )
    subject = next(r for r in identity_references(intake) if r["kind"] == "requirement_subject")
    observed = evidence(intake, [search(subject, provider_name)])
    packet = prepare_subject_judgment(intake, observed, model="fixture-model").to_dict()
    cases = json.loads(packet["request"]["input"])["cases"]
    assert len(cases) == 1
    assert cases[0]["claim"]["place_name"] == "Museum A"
    assert cases[0]["claim"]["location"] is None
    assert cases[0]["location_context"] == {
        "purpose": "destination_context",
        "original": "Example City, Country",
    }
    assert cases[0]["candidates"][0]["display_name"] == provider_name
    assert "version" not in cases[0]


def subject_material(intake, observed, change=None, *, policy_version=None):
    from backend.evaluation.subject_correspondence import prepare_subject_judgment

    options = {"policy_version": policy_version} if policy_version else {}
    packet = prepare_subject_judgment(intake, observed, model="fixture-model", **options).to_dict()
    cases = json.loads(packet["request"]["input"])["cases"]
    decisions = {}
    for case in cases:
        candidate = case["candidates"][0] if case["candidates"] else None
        row = {
            "reference_id": case["reference_id"],
            "decision": "match" if candidate else "unknown",
            "candidate_id": candidate["place_id"] if candidate else None,
            "rationale": "The independent candidate identifies the original requested venue.",
            "evidence_fields": [
                "claim.place_name",
                "claim.destination",
                "candidate.display_name",
                "candidate.formatted_address",
            ]
            if candidate
            else [],
            "address_assessment": "equivalent" if case["claim"]["location"] else "not_supplied",
            "destination_assessment": "consistent" if candidate else "unknown",
        }
        if candidate and case["claim"]["location"]:
            row["evidence_fields"].append("claim.location")
        decisions[case["reference_id"]] = row
    if change:
        change(decisions, cases)
    response = {
        "id": "subject-response",
        "model": "fixture-model",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": json.dumps({"decisions": decisions})}],
            }
        ],
    }
    return {
        "schema_version": RESULT_VERSION,
        "packet": packet,
        "requested_at": "2026-10-17T00:00:00Z",
        "retrieved_at": "2026-10-17T00:00:01Z",
        "response": response,
        "response_sha256": canonical_digest(response),
    }


def test_common_resolution_is_projected_to_all_versions_and_replays(batch):
    from backend.evaluation.identity_program import (
        resolve_versioned_identities,
        verify_versioned_report,
    )
    from backend.evaluation.preparation import identity_ready

    intake = requirement_batch(
        batch, bound=False, location="Example City, Country", destination="Example City, Country"
    )
    subject = next(r for r in identity_references(intake) if r["kind"] == "requirement_subject")
    record = search(
        subject, "The Municipal Museum of Art", address="Old District, 08000 Example City"
    )
    record["search"]["candidates"][0]["address_components"] = [
        {"longText": "Example City", "types": ["locality", "political"]},
        {"longText": "Country", "types": ["country", "political"]},
        {"longText": "Old District", "types": ["sublocality_level_1", "sublocality", "political"]},
    ]
    observed = evidence(intake, [record])
    report = resolve_versioned_identities(
        intake, observed, common_subjects=True, subject_result=subject_material(intake, observed)
    ).to_dict()
    targets = [r for r in report["records"] if r["kind"] == "requirement_subject"]
    assert {r["version"] for r in targets} == {"v0", "v1", "v2", "v3"}
    assert {r["canonical_place_id"] for r in targets} == {"place-a"}
    assert {r["grounding_verdict"] for r in targets} == {"PASS"}
    assert all(r["original_claim"]["location"] == "Example City, Country" for r in targets)
    assert len({r["reference_id"] for r in targets}) == 4
    assert identity_ready(intake.to_dict(), report)
    assert verify_versioned_report(intake, report)
    forged = copy.deepcopy(report)
    targets = [r for r in forged["records"] if r["kind"] == "requirement_subject"]
    targets[0]["canonical_place_id"] = "foreign-place"
    assert not verify_versioned_report(intake, forged)


def test_native_preparation_reserves_one_distinct_subject_stage(batch):
    from backend.evaluation.evaluation_run import prepare_run
    from backend.tests.evaluation.test_evaluation_run import options, run_prices

    requirement_batch(batch, bound=False)
    book = run_prices()
    preparation = prepare_run(batch[2](), batch[4] / "evaluation", options=options(), prices=book)
    assert preparation["schema_version"] == "rtpeval_execution_preparation_3"
    assert preparation["max_model_sends"] == 3
    assert preparation["subject_policy"] == "requirement_subject_correspondence_2"


@pytest.mark.parametrize(
    "fault",
    [
        "pagination",
        "empty_token",
        "truncated",
        "wrong_query",
        "wrong_size",
        "no_time",
        "malformed",
        "conflicting_id",
    ],
)
def test_incomplete_or_conflicting_search_cannot_supply_target(batch, fault):
    from backend.evaluation.subject_correspondence import resolve_subjects

    intake = requirement_batch(batch, bound=False)
    ref = next(r for r in identity_references(intake) if r["kind"] == "requirement_subject")
    record = search(ref, "Museum A")
    data = record["search"]
    if fault in ("pagination", "empty_token"):
        data["next_page_token"] = "next" if fault == "pagination" else ""
    elif fault == "truncated":
        data["actual_result_count"] = 2
    elif fault == "wrong_query":
        data["query"] = "Different Museum"
    elif fault == "wrong_size":
        data["requested_page_size"] = 1
    elif fault == "no_time":
        del data["retrieved_at"]
    elif fault == "malformed":
        data["candidates"][0]["display_name"] = None
    else:
        data["candidates"].append({**data["candidates"][0], "display_name": "Other branch"})
        data["actual_result_count"] = 2
    observed = evidence(intake, [record])
    targets, _ = resolve_subjects(intake, observed, subject_material(intake, observed))
    assert targets[ref["reference_id"]]["canonical_place_id"] is None


@pytest.mark.parametrize(
    "location,address,expected",
    [
        ("Example City, Country", "Example City", "place-a"),
        (None, "Different City", None),
        ("99 Main St, Example City, Country", "Example City", None),
        ("10 Main St, Example City, Country", "Example City", "place-a"),
        ("Unverified District", "Example City", None),
    ],
)
def test_location_purpose_preserves_explicit_precision(batch, location, address, expected):
    from backend.evaluation.subject_correspondence import resolve_subjects

    intake = requirement_batch(
        batch, bound=False, location=location, destination="Example City, Country"
    )
    ref = next(r for r in identity_references(intake) if r["kind"] == "requirement_subject")
    observed = evidence(intake, [search(ref, "Municipal Gallery", address=address)])
    targets, _ = resolve_subjects(intake, observed, subject_material(intake, observed))
    assert targets[ref["reference_id"]]["canonical_place_id"] == expected


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "foreign_candidate",
        "wrong_key",
        "empty_citation",
        "missing_support",
        "unknown",
        "ambiguity",
    ],
)
def test_decisions_enforce_coverage_ownership_and_uncertainty(batch, fault):
    from backend.evaluation.subject_correspondence import resolve_subjects

    intake = requirement_batch(batch, bound=False)
    ref = next(r for r in identity_references(intake) if r["kind"] == "requirement_subject")
    record = search(ref, "Museum A")
    record["search"]["candidates"].append(
        {
            **record["search"]["candidates"][0],
            "place_id": "other-branch",
            "display_name": "Museum A Shop",
        }
    )
    record["search"]["actual_result_count"] = 2
    observed = evidence(intake, [record])

    def change(rows, _cases):
        key = next(iter(rows))
        if fault == "missing":
            rows.clear()
            return
        row = rows[key]
        if fault == "foreign_candidate":
            row["candidate_id"] = "p999"
        elif fault == "wrong_key":
            rows["r999"] = rows.pop(key)
        elif fault == "empty_citation":
            row["evidence_fields"].append("claim.location")
        elif fault == "missing_support":
            row["evidence_fields"].remove("candidate.formatted_address")
        else:
            row.update(
                decision="unknown",
                candidate_id=None,
                evidence_fields=[],
                destination_assessment="unknown",
            )

    material = subject_material(intake, observed, change)
    if fault in ("unknown", "ambiguity"):
        targets, _ = resolve_subjects(intake, observed, material)
        assert targets[ref["reference_id"]]["canonical_place_id"] is None
    else:
        with pytest.raises(ValueError):
            resolve_subjects(intake, observed, material)


def test_unresolved_target_is_requirement_unknown_not_a_visit_failure(batch):
    from backend.evaluation.identity_program import resolve_versioned_identities
    from backend.evaluation.requirement_schedule import score_requirement_schedule
    from backend.tests.evaluation.test_requirement_schedule import context

    intake = requirement_batch(
        batch, bound=False, location="99 Main St, Example City, Country", kind="excluded_visit"
    )
    ref = next(r for r in identity_references(intake) if r["kind"] == "requirement_subject")
    observed = evidence(intake, [search(ref, "Museum A")])
    report = resolve_versioned_identities(
        intake, observed, common_subjects=True, subject_result=subject_material(intake, observed)
    ).to_dict()
    requirements = score_requirement_schedule(intake, report, context(intake)).to_dict()
    assert requirements["status"] == "complete"
    assert {row["requirements"]["state"] for row in requirements["results"]} == {"UNKNOWN"}


def test_subject_packet_is_independent_of_submitted_outputs_and_old_responses(batch):
    from backend.evaluation.identity_llm import prepare_identity_judgment
    from backend.evaluation.subject_correspondence import prepare_subject_judgment, resolve_subjects
    from backend.tests.evaluation.test_identity_llm import model_material

    intake = requirement_batch(batch, bound=False)
    observed = evidence(intake, [search(r, r["name"]) for r in identity_references(intake)])
    original = prepare_subject_judgment(intake, observed, model="fixture-model").to_dict()
    changed = intake.to_dict()
    changed["inventory"][0]["runs"]["v0"]["final"]["activities"][0]["original"]["place_name"] = (
        "Noise"
    )
    assert prepare_subject_judgment(changed, observed, model="fixture-model").to_dict() == original
    visits = prepare_identity_judgment(
        intake, observed, model="fixture-model", visits_only=True
    ).to_dict()
    assert all(
        c["kind"] == "primary_visit" for c in json.loads(visits["request"]["input"])["cases"]
    )
    with pytest.raises(ValueError, match="packet/source mismatch"):
        resolve_subjects(intake, observed, model_material(intake, observed, historical=False))


@pytest.mark.parametrize(
    "count,kind,expected",
    [
        (0, "required_visit", "FAIL"),
        (1, "required_visit", "PASS"),
        (2, "required_visit", "FAIL"),
        (0, "excluded_visit", "PASS"),
        (1, "excluded_visit", "FAIL"),
    ],
)
def test_common_targets_keep_actual_count_and_exclusion_violations(batch, count, kind, expected):
    from backend.evaluation.identity_program import resolve_versioned_identities
    from backend.evaluation.requirement_schedule import score_requirement_schedule
    from backend.tests.evaluation.test_identity import details, prepared
    from backend.tests.evaluation.test_requirement_schedule import context

    intake = requirement_batch(batch, bound=False, identified=True, kind=kind)
    visits = [
        a
        for a in batch[1]["v1"]["itinerary"]["days"][0]["activities"]
        if a["activity_kind"] == "main_poi"
    ]
    for index, activity in enumerate(visits):
        is_target = index < count
        activity.update(
            source_place_id="venue-a" if is_target else "venue-b",
            place_name="Museum A" if is_target else "Museum B",
        )
    batch[2]("v1")
    intake = prepared(batch)
    observed = evidence(
        intake,
        [
            search(r, "Municipal Gallery", place_id="venue-a")
            if r["kind"] == "requirement_subject"
            else details(r, r["name"], r["claimed_place_id"])
            for r in identity_references(intake)
            if r["kind"] == "requirement_subject" or r["version"] == "v1"
        ],
    )
    report = resolve_versioned_identities(
        intake, observed, common_subjects=True, subject_result=subject_material(intake, observed)
    ).to_dict()
    result = score_requirement_schedule(intake, report, context(intake)).to_dict()
    assert (
        next(row for row in result["results"] if row["version"] == "v1")["requirements"]["state"]
        == expected
    )


def test_old_native_preparation_retains_old_packets_and_policy(batch):
    import asyncio

    import httpx

    from backend.evaluation.evaluation_run import execute_run, prepare_run, replay_run
    from backend.evaluation.snapshot import _bytes
    from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices

    root = batch[4] / "legacy-evaluation"
    preparation = prepare_run(batch[2](), root, options=options(), prices=run_prices())
    preparation["schema_version"] = "rtpeval_execution_preparation_2"
    del preparation["subject_policy"]
    preparation["content_sha256"] = canonical_digest(
        {k: v for k, v in preparation.items() if k != "content_sha256"}
    )
    (root / "preparation.json").write_bytes(_bytes(preparation))

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic",
                model_api_key="synthetic",
                http_client=client,
            )

    result = asyncio.run(execute())
    assert result["processing_status"] == "complete"
    identity = json.loads((root / "execution" / "identity-report.json").read_bytes())
    assert identity["association_policy_version"] == "versioned_api_identity_4"
    assert replay_run(root) == result


def test_subject_preparation_needs_explicit_price_and_cannot_increase_budget(batch):
    from backend.evaluation.evaluation_run import prepare_run
    from backend.tests.evaluation.test_evaluation_run import options, run_prices

    requirement_batch(batch, bound=False)
    book = run_prices()
    book["rows"] = [r for r in book["rows"] if r["match"].get("operation") != "requirement_subject"]
    with pytest.raises(ValueError, match="Subject stage price unavailable"):
        prepare_run(batch[2](), batch[4] / "no-price", options=options(), prices=book)
    with pytest.raises(ValueError, match="reservation exceeds"):
        prepare_run(
            batch[2](),
            batch[4] / "low-budget",
            options={**options(), "max_cost_usd": "0.00001"},
            prices=run_prices(),
        )


def test_failed_subject_send_is_retained_without_visit_send_or_retry(batch):
    import asyncio

    import httpx

    from backend.evaluation.evaluation_run import execute_run, prepare_run, replay_run
    from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices

    requirement_batch(batch, bound=False)
    root = batch[4] / "failed-subject"
    preparation = prepare_run(batch[2](), root, options=options(), prices=run_prices())
    models = []

    def respond(request):
        if request.url.host == "model.example.test":
            models.append(json.loads(request.content)["text"]["format"]["name"])
            return httpx.Response(500, json={"error": "synthetic failure"})
        return mock_provider(request)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic",
                model_api_key="synthetic",
                http_client=client,
            )

    result = asyncio.run(execute())
    assert result["processing_status"] == "stopped"
    assert models == ["RequirementSubjects"]
    assert result["usage"]["actual_model_sends"] == 1
    assert replay_run(root) == result
    assert models == ["RequirementSubjects"]


def test_cli_prepares_and_imports_common_subjects_offline(batch, capsys):
    from backend.evaluation.identity_cli import main

    intake = requirement_batch(batch, bound=False)
    observed = evidence(intake, [search(r, r["name"]) for r in identity_references(intake)])
    path = batch[4] / "independent-evidence.json"
    path.write_text(json.dumps(observed), encoding="utf-8")
    base = [str(batch[2]()), str(path), "--common-subjects"]
    assert main([*base, "--prepare-subjects", "--model", "fixture-model"]) == 0
    assert (
        json.loads(capsys.readouterr().out)["association_policy_version"]
        == "requirement_subject_correspondence_2"
    )
    result_path = batch[4] / "subject-result.json"
    result_path.write_text(json.dumps(subject_material(intake, observed)), encoding="utf-8")
    assert main([*base, "--subject-result", str(result_path)]) == 3
    report = json.loads(capsys.readouterr().out)
    assert {
        r["canonical_place_id"] for r in report["records"] if r["kind"] == "requirement_subject"
    } == {"place-a"}


def test_unknown_target_keeps_proven_impossible_count_failure(batch):
    from backend.evaluation.identity_program import resolve_versioned_identities
    from backend.evaluation.requirement_schedule import score_requirement_schedule
    from backend.tests.evaluation.test_identity import prepared
    from backend.tests.evaluation.test_requirement_schedule import context

    requirement_batch(batch, bound=False)
    batch[1]["v1"]["itinerary"]["days"][0]["activities"] = []
    batch[2]("v1")
    intake = prepared(batch)
    identity = resolve_versioned_identities(
        intake, evidence(intake, []), common_subjects=True
    ).to_dict()
    report = score_requirement_schedule(intake, identity, context(intake)).to_dict()
    assert (
        next(r for r in report["results"] if r["version"] == "v1")["requirements"]["state"]
        == "FAIL"
    )


def test_native_empty_v0_visits_skip_the_model_and_replay(batch):
    import asyncio

    import httpx

    from backend.evaluation.evaluation_run import execute_run, prepare_run, replay_run
    from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices

    requirement_batch(batch, bound=False, kind="excluded_visit")
    batch[1]["v0"]["itinerary"]["days"][0]["activities"] = []
    batch[2]("v0")
    root = batch[4] / "empty-v0"
    preparation = prepare_run(batch[2](), root, options=options(), prices=run_prices())

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic",
                model_api_key="synthetic",
                http_client=client,
            )

    result = asyncio.run(execute())
    assert result["processing_status"] == "complete"
    assert preparation["max_model_sends"] == 2
    assert result["usage"]["actual_model_sends"] == 1
    assert {c["operation"] for c in result["usage"]["raw"]["model_calls"]} == {
        "requirement_subject"
    }
    assert not (root / "execution/model-result.json").exists()
    assert replay_run(root) == result
