"""Common subject reuse at paired prepare/execute/import/replay boundaries."""

import asyncio
import json

import httpx
import pytest

from backend.evaluation.intake import load_batch
from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices
from backend.tests.test_rtpeval_pair_acquisition_cli import paired_material as paired_material
from backend.tests.test_rtpeval_pair_acquisition_cli import save

pytest_plugins = ("backend.tests.evaluation.test_intake",)


def named_material(batch, paired_material):
    root, args, values, _ = paired_material
    spec = json.loads((root / "requirements.json").read_bytes())
    spec["subjects"] = [{"subject_id": "museum", "place_name": "Museum A"}]
    spec["obligations"] = [
        {
            "obligation_id": "once",
            "kind": "required_visit",
            "resolution": "resolved",
            "subject_ref": "museum",
            "count": {"mode": "exact", "value": 1},
            "source_refs": [{"field_path": "additional_preferences", "quote": "architecture"}],
        }
    ]
    batch[0]["groups"][0]["requirement_spec_ref"] = batch[3](
        "requirements.json", spec, spec["schema_version"]
    )
    intake = load_batch(batch[2]()).to_dict()
    values["selection"]["runs"][0]["requirement_spec_sha256"] = intake["inventory"][0][
        "requirement_spec_sha256"
    ]
    save(root, "selection.json", values["selection"])
    return root, args, values, intake


def completed_primary(material, destination, provider=mock_provider):
    from backend.evaluation.evaluation_run import execute_run, prepare_run

    root, _, values, _ = material
    preparation = prepare_run(
        root / "manifest.json",
        destination,
        options=options(),
        prices=run_prices(),
        schedule_context=values["context"],
        route_reviews=values["route-reviews"],
        density_reviews=values["density-reviews"],
    )

    def respond(request):
        response = provider(request)
        if request.url.host == "model.example.test":
            claims = {
                c["reference_id"]: c["claim"]
                for c in json.loads(json.loads(request.content)["input"])["cases"]
            }
            body = response.json()
            text = body["output"][0]["content"][0]
            decisions = json.loads(text["text"])
            for rid, row in decisions["decisions"].items():
                if claims[rid]["location"]:
                    row["address_assessment"] = "equivalent"
                    row["evidence_fields"].append("claim.location")
                if claims[rid]["claimed_place_id"]:
                    row["evidence_fields"].append("claim.claimed_place_id")
            text["text"] = json.dumps(decisions)
            return httpx.Response(200, json=body)
        return response

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="fixture",
                model_api_key="fixture",
                http_client=client,
            )

    report = asyncio.run(execute())
    assert report["processing_status"] == "complete", report
    return destination


def prepare_pair(material, directory, primary):
    from backend.evaluation.paired_run import CONTEXT_FILES, prepare

    root, _, values, _ = material
    return prepare(
        root / "manifest.json",
        directory,
        selection=values["selection"],
        options=values["options"],
        prices=values["prices"],
        context={key: values.get(cli.replace("_", "-")) for key, cli in CONTEXT_FILES.items()},
        files={name: root / (name + ".json") for name in values},
        subject_primary_run=primary,
    )


def test_fresh_pair_freezes_common_target_source_without_model_fallback(
    batch, paired_material, tmp_path
):
    from backend.evaluation.paired_run import verify

    material = named_material(batch, paired_material)
    primary = completed_primary(material, tmp_path / "primary")
    prepared = prepare_pair(material, tmp_path / "pair", primary)
    assert prepared["schema_version"] == "rtpeval_pair_acquisition_preparation_2"
    assert prepared["identity_policy"] == "versioned_api_identity_6"
    assert prepared["subject_policy"] == "requirement_subject_correspondence_2"
    assert prepared["max_model_sends"] == 0
    assert verify(tmp_path / "pair") == prepared


def test_fresh_paired_visits_keep_common_source_and_replay_without_new_model(
    batch, paired_material, tmp_path, monkeypatch
):
    from backend.evaluation.paired_execution import execute
    from backend.evaluation.paired_run import replay

    material = named_material(batch, paired_material)
    primary = completed_primary(material, tmp_path / "primary")
    directory = tmp_path / "pair"
    prepared = prepare_pair(material, directory, primary)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fixture")

    def google_only(request):
        assert request.url.host != "model.example.test"
        return mock_provider(request)

    async def dispatch():
        async with httpx.AsyncClient(transport=httpx.MockTransport(google_only)) as client:
            return await execute(
                directory, approved_sha256=prepared["content_sha256"], http_client=client
            )

    report = asyncio.run(dispatch())
    assert report["processing_status"] == "complete", report
    identity = json.loads((directory / "execution/identity-report.json").read_bytes())
    assert identity["association_policy_version"] == "versioned_api_identity_6"
    assert {
        r["grounding_verdict"] for r in identity["records"] if r["kind"] == "requirement_subject"
    } == {"PASS"}
    assert report["usage"]["actual_model_sends"] == 0
    for stage in report["pair"]["groups"][0]["stages"].values():
        assert stage["dimensions"]["requirements"]["counts"] == {"PASS": 1, "FAIL": 0, "UNKNOWN": 0}
    assert replay(directory) == report


def test_closed_primary_import_keeps_subject_policy_without_current_sends(
    batch, paired_material, tmp_path
):
    from backend.evaluation.paired_run import CONTEXT_FILES
    from backend.evaluation.snapshot_import import import_pair

    material = named_material(batch, paired_material)
    root, _, values, _ = material
    primary = completed_primary(material, tmp_path / "primary")
    directory = tmp_path / "import"
    handoff = import_pair(
        root / "manifest.json",
        directory,
        context={k: values.get(v.replace("_", "-")) for k, v in CONTEXT_FILES.items()},
        primary_runs=[primary],
        subject_primary_run=primary,
    )
    assert handoff["current_sends"] == 0
    assert handoff["identity_policy"] == "versioned_api_identity_6"
    identity = json.loads((directory / "identity-report.json").read_bytes())
    assert {
        r["grounding_verdict"] for r in identity["records"] if r["kind"] == "requirement_subject"
    } == {"PASS"}


@pytest.mark.parametrize("fault", ["policy", "intake", "packet", "response", "receipt"])
def test_foreign_or_rebound_subject_source_is_rejected_before_pair_preparation(
    batch, paired_material, tmp_path, fault
):
    from backend.evaluation.records import canonical_digest

    material = named_material(batch, paired_material)
    primary = completed_primary(material, tmp_path / "primary")
    if fault in ("policy", "intake"):
        path = primary / "preparation.json"
        data = json.loads(path.read_bytes())
        if fault == "policy":
            data["subject_policy"] = "requirement_subject_correspondence_1"
        else:
            data["intake"]["inventory"][0]["input"]["destination"] = "Foreign City"
    elif fault in ("packet", "response"):
        path = primary / "execution/subject-model-result.json"
        data = json.loads(path.read_bytes())
        if fault == "packet":
            data["packet"]["source_cases_sha256"] = "0" * 64
        else:
            data["response"]["id"] = "foreign-response"
            data["response_sha256"] = canonical_digest(data["response"])
    else:
        path = primary / "execution/receipt.json"
        data = json.loads(path.read_bytes())
        data["preparation_sha256"] = "0" * 64
    path.write_text(json.dumps(data), encoding="utf-8")
    if fault in ("packet", "response"):
        import hashlib

        receipt_path = primary / "execution/receipt.json"
        receipt = json.loads(receipt_path.read_bytes())
        receipt["files"]["subject-model-result.json"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    directory = tmp_path / "pair"
    with pytest.raises(ValueError):
        prepare_pair(material, directory, primary)
    assert not directory.exists()


def test_cached_pair_and_portable_export_keep_common_targets(batch, paired_material, tmp_path):
    from backend.evaluation.paired_execution import execute
    from backend.evaluation.paired_run import CONTEXT_FILES, export, prepare, replay
    from backend.evaluation.snapshot_import import import_pair

    material = named_material(batch, paired_material)
    root, _, values, _ = material
    primary = completed_primary(material, tmp_path / "primary")
    context = {k: values.get(v.replace("_", "-")) for k, v in CONTEXT_FILES.items()}
    imported = tmp_path / "import"
    import_pair(
        root / "manifest.json",
        imported,
        context=context,
        primary_runs=[primary],
        subject_primary_run=primary,
    )
    values["options"].update(max_google_sends=0, max_cost_usd="0")
    save(root, "options.json", values["options"])
    directory = tmp_path / "pair"
    prepared = prepare(
        root / "manifest.json",
        directory,
        selection=values["selection"],
        options=values["options"],
        prices=values["prices"],
        context=context,
        files={name: root / (name + ".json") for name in values},
        subject_primary_run=primary,
        identity_snapshot=imported / "identity-snapshot",
        snapshot=imported / "evidence-snapshot",
    )
    report = asyncio.run(execute(directory, approved_sha256=prepared["content_sha256"]))
    assert report["processing_status"] == "complete", report
    assert report["usage"]["actual_google_sends"] == report["usage"]["actual_model_sends"] == 0
    assert replay(directory) == report
    handoff = export(directory, tmp_path / "export")
    assert handoff["processing_status"] == "complete"
    identity = json.loads((tmp_path / "export/execution/identity-report.json").read_bytes())
    assert identity["association_policy_version"] == "versioned_api_identity_6"


def test_paired_opening_freezes_common_subject_provenance(
    batch, paired_material, tmp_path, monkeypatch
):
    from backend.evaluation.opening_run import execute_opening_run, replay_opening_run
    from backend.evaluation.paired_execution import execute
    from backend.evaluation.paired_opening import prepare_pair_opening, verify_pair_opening
    from backend.tests.evaluation.test_opening_judgment import material as opening_material

    material = named_material(batch, paired_material)
    primary = completed_primary(material, tmp_path / "primary")
    directory = tmp_path / "pair"
    prepared = prepare_pair(material, directory, primary)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fixture")

    def missing_hours(request):
        response = mock_provider(request)
        if request.method == "GET":
            value = response.json()
            value.pop("regularOpeningHours", None)
            return httpx.Response(200, json=value)
        return response

    async def dispatch():
        async with httpx.AsyncClient(transport=httpx.MockTransport(missing_hours)) as client:
            return await execute(
                directory, approved_sha256=prepared["content_sha256"], http_client=client
            )

    assert asyncio.run(dispatch())["processing_status"] == "complete"
    config = {**options(), "max_google_sends": 0}
    prices = run_prices()
    prices["rows"][-1]["match"]["operation"] = "opening_access"
    opening = prepare_pair_opening(
        material[0] / "manifest.json",
        directory / "execution/identity-report.json",
        directory / "execution/evidence-snapshot",
        tmp_path / "access",
        options=config,
        prices=prices,
        schedule_context=material[2]["context"],
        expected_plan=json.loads((directory / "execution/evidence-plan.json").read_bytes()),
    )
    assert opening["schema_version"] == "rtpeval_pair_opening_preparation_2"
    assert opening["identity_policy"] == "versioned_api_identity_6"
    assert opening["subject_policy"] == "requirement_subject_correspondence_2"
    assert verify_pair_opening(opening)[1] == opening

    def access_only(request):
        assert request.url.host == "model.example.test"
        return httpx.Response(200, json=opening_material(opening["packet"])["response"])

    async def assess_access():
        async with httpx.AsyncClient(transport=httpx.MockTransport(access_only)) as client:
            return await execute_opening_run(
                opening,
                approved_sha256=opening["content_sha256"],
                model_api_key="fixture",
                http_client=client,
            )

    access = asyncio.run(assess_access())
    assert access["processing_status"] == "complete", access
    assert access["usage"]["actual_model_sends"] == 1
    assert access["usage"]["actual_google_sends"] == access["usage"]["retries"] == 0
    assert replay_opening_run(tmp_path / "access") == access
    from backend.evaluation.records import canonical_digest

    opening["identity_policy"] = "versioned_api_identity_4"
    opening["content_sha256"] = canonical_digest(
        {k: v for k, v in opening.items() if k != "content_sha256"}
    )
    save(tmp_path / "access", "preparation.json", opening)
    with pytest.raises(ValueError, match="provenance"):
        verify_pair_opening(opening)


@pytest.mark.parametrize("copy", [False, True])
def test_subject_files_changed_after_freeze_fail_preflight(batch, paired_material, tmp_path, copy):
    from backend.evaluation.paired_run import preflight

    material = named_material(batch, paired_material)
    primary = completed_primary(material, tmp_path / "primary")
    directory = tmp_path / "pair"
    prepared = prepare_pair(material, directory, primary)
    source = directory / "material/subjects" if copy else primary
    with (source / "execution/subject-model-result.json").open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="changed|inventory"):
        preflight(directory, prepared["content_sha256"])
    assert not (directory / "execution").exists()


def test_deleted_required_visit_is_still_a_confirmed_paired_violation(
    batch, paired_material, tmp_path, monkeypatch
):
    import copy

    from backend.evaluation.paired_execution import execute
    from backend.tests.evaluation.test_v3_pair_report import adopted_edit

    root, args, values, _ = named_material(batch, paired_material)
    result = batch[1]["v3"]
    draft = copy.deepcopy(result["itinerary"])
    final = copy.deepcopy(draft)
    final["days"][0]["activities"] = [
        a for a in final["days"][0]["activities"] if a["activity_id"] != "a"
    ]
    edits = [{"operation": "delete", "activity_id": "a", "date": "2020-01-01"}]
    result.update(
        itinerary=final,
        v3={"draft": draft, "final_primary": final, "repair": adopted_edit(draft, final, edits)},
    )
    batch[2]("v3")
    intake = load_batch(batch[2]()).to_dict()
    values["selection"]["runs"][0]["result_sha256"] = intake["inventory"][0]["runs"]["v3"]["final"][
        "context"
    ]["artifact_sha256"]
    save(root, "selection.json", values["selection"])
    material = root, args, values, intake
    primary = completed_primary(material, tmp_path / "primary")
    directory = tmp_path / "pair"
    prepared = prepare_pair(material, directory, primary)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fixture")

    async def dispatch():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
            return await execute(
                directory, approved_sha256=prepared["content_sha256"], http_client=client
            )

    report = asyncio.run(dispatch())
    assert report["processing_status"] == "complete", report
    stages = report["pair"]["groups"][0]["stages"]
    assert stages["draft"]["dimensions"]["requirements"]["counts"]["PASS"] == 1
    assert stages["final_primary"]["dimensions"]["requirements"]["counts"]["FAIL"] == 1


@pytest.mark.parametrize(
    "fault,expected",
    [
        (None, "PASS"),
        ("city", "UNKNOWN"),
        ("country", "UNKNOWN"),
        ("conflict", "UNKNOWN"),
        ("address", "UNKNOWN"),
    ],
)
def test_original_british_museum_postal_target_survives_paired_projection(
    batch, paired_material, tmp_path, monkeypatch, fault, expected
):
    import copy

    from backend.evaluation.paired_execution import execute
    from backend.tests.evaluation.test_daily_density import density_reviews
    from backend.tests.evaluation.test_requirement_schedule import context
    from backend.tests.evaluation.test_routes import reviews
    from backend.tests.evaluation.test_subject_postal_town import postal_batch

    postal_batch(
        batch, location="1 Wrong Road, London, United Kingdom" if fault == "address" else None
    )
    for version, result in batch[1].items():
        for activity in result["itinerary"]["days"][0]["activities"]:
            if activity.get("activity_id") == "a":
                activity["place_name"] = (
                    "British Museum" if version == "v0" else "The British Museum"
                )
            if activity.get("place_name"):
                activity["location"] = "Great Russell Street, London, United Kingdom"
        if version == "v3":
            result["v3"] = {
                k: copy.deepcopy(result["itinerary"]) for k in ["draft", "final_primary"]
            }
        batch[2](version)
    root, args, values, _ = paired_material
    loaded = load_batch(batch[2]())
    intake = loaded.to_dict()
    group = intake["inventory"][0]
    values["selection"]["runs"][0].update(
        input_sha256=group["input_sha256"],
        requirement_spec_sha256=group["requirement_spec_sha256"],
        result_sha256=group["runs"]["v3"]["final"]["context"]["artifact_sha256"],
    )
    values.update(
        context=context(loaded),
        **{"route-reviews": reviews(loaded), "density-reviews": density_reviews(loaded)},
    )
    for name, value in values.items():
        save(root, name + ".json", value)
    material = root, args, values, intake

    def postal_provider(request):
        response = mock_provider(request)
        if request.url.host != "places.googleapis.com":
            return response
        value = response.json()
        if (
            request.url.path.endswith("searchText")
            and "British Museum" in json.loads(request.content)["textQuery"]
        ):
            value = {
                "places": [
                    {
                        "id": "pid-a",
                        "displayName": {"text": "The British Museum"},
                        "location": {"latitude": 10, "longitude": 20},
                    }
                ]
            }
        for place in value.get("places", [value]):
            if place.get("id") == "pid-a":
                place["displayName"] = {"text": "The British Museum"}
            place["formattedAddress"] = "Great Russell Street, London, United Kingdom"
            place["addressComponents"] = [
                {"longText": "Oxford" if fault == "city" else "London", "types": ["postal_town"]},
                {
                    "longText": "France" if fault == "country" else "United Kingdom",
                    "shortText": "FR" if fault == "country" else "GB",
                    "types": ["country"],
                },
            ]
            if fault == "conflict":
                place["addressComponents"].append({"longText": "Oxford", "types": ["locality"]})
        return httpx.Response(200, json=value)

    primary = completed_primary(material, tmp_path / "primary", postal_provider)
    directory = tmp_path / "pair"
    prepared = prepare_pair(material, directory, primary)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fixture")

    async def dispatch():
        async with httpx.AsyncClient(transport=httpx.MockTransport(postal_provider)) as client:
            return await execute(
                directory, approved_sha256=prepared["content_sha256"], http_client=client
            )

    assert asyncio.run(dispatch())["processing_status"] == "complete"
    identity = json.loads((directory / "execution/identity-report.json").read_bytes())
    targets = [r for r in identity["records"] if r["kind"] == "requirement_subject"]
    assert {r["original_claim"]["place_name"] for r in targets} == {"British Museum"}
    assert {r["grounding_verdict"] for r in targets} == {expected}
    assert {r["version"] for r in targets} == {"v0", "v1", "v2", "v3"}
