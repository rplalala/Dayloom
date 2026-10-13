"""Installed paired acquisition over immutable synthetic selected outputs."""

import copy
import json

import pytest

from backend.evaluation.intake import load_batch
from backend.tests.evaluation.test_daily_density import density_reviews
from backend.tests.evaluation.test_evaluation_run import run_prices
from backend.tests.evaluation.test_requirement_schedule import context
from backend.tests.evaluation.test_routes import no_departure, reviews
from backend.tests.test_rtpeval_cli import installed_cli as cli_fixture

pytest_plugins = ("backend.tests.evaluation.test_intake",)
installed_cli = cli_fixture


def save(root, name, value):
    (root / name).write_text(json.dumps(value), encoding="utf-8")
    return root / name


@pytest.fixture
def paired_material(batch):
    manifest, results, write, _, root = batch
    from backend.tests.research_native_fixtures import prepare_namespaced_usage

    prepare_namespaced_usage(batch)
    no_departure(results)
    for result in results.values():
        for row in result["itinerary"]["days"][0]["activities"]:
            row.update(
                source_place_id="pid-" + row["activity_id"],
                location="10 Main St, Example City, Country",
            )
    results["v3"]["v3"] = {
        name: copy.deepcopy(results["v3"]["itinerary"]) for name in ("draft", "final_primary")
    }
    for version in results:
        write(version)
    intake = load_batch(write())
    assert intake.status == "accepted", intake.to_dict()
    group = intake.to_dict()["inventory"][0]
    run = group["runs"]["v3"]["final"]["context"]
    selection = {
        "schema_version": "rtpeval_pair_selection_1",
        "batch_id": "batch",
        "batch_revision": "1",
        "runs": [
            {
                "group_id": "g",
                "run_id": run["run_id"],
                "input_sha256": group["input_sha256"],
                "requirement_spec_sha256": group["requirement_spec_sha256"],
                "result_sha256": run["artifact_sha256"],
                "stage_pointers": {"draft": "/v3/draft", "final_primary": "/v3/final_primary"},
            }
        ],
    }
    values = {
        "selection": selection,
        "options": {
            "max_google_sends": 30,
            "max_cost_usd": "10",
            "timeout_seconds": 5,
            "total_timeout_seconds": 30,
        },
        "prices": run_prices(),
        "context": context(intake),
        "route-reviews": reviews(intake),
        "density-reviews": density_reviews(intake),
    }
    args = [root / "manifest.json"]
    for name, value in values.items():
        args.extend(["--" + name, save(root, name + ".json", value)])
    return root, args, values, intake


def run(installed_cli, command, *args, **kwargs):
    if command == "import":
        filtered = []
        iterator = iter(args)
        for value in iterator:
            if value in ("--selection", "--options", "--prices"):
                next(iterator)
            else:
                filtered.append(value)
        args = filtered
    return installed_cli("pair", "acquire", command, *args, evaluation_offline=True, **kwargs)


def primary_run(
    paired_material, directory, monkeypatch, *, evidence_details_failure=False, failed_place_id=None
):
    import asyncio

    import httpx

    from backend.evaluation.evaluation_run import execute_run, prepare_run
    from backend.tests.evaluation.test_evaluation_run import mock_provider, options

    root, _, values, _ = paired_material
    prepared = prepare_run(
        root / "manifest.json",
        directory,
        options=options(),
        prices=run_prices(),
        schedule_context=values["context"],
        route_reviews=values["route-reviews"],
        density_reviews=values["density-reviews"],
    )
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")

    details_calls = {}

    def respond(request):
        if request.url.host == "places.googleapis.com" and request.method == "GET":
            if request.url.path.endswith("/" + str(failed_place_id)):
                return httpx.Response(503, json={"error": "synthetic provider failure"})
            details_calls[str(request.url)] = details_calls.get(str(request.url), 0) + 1
            if evidence_details_failure and details_calls[str(request.url)] > 1:
                return httpx.Response(503, json={"error": "synthetic provider failure"})
        response = mock_provider(request)
        if request.url.host == "model.example.test":
            body = response.json()
            text = body["output"][0]["content"][0]
            decisions = json.loads(text["text"])
            for row in decisions["decisions"].values():
                row["address_assessment"] = "equivalent"
                row["evidence_fields"].append("claim.location")
                row["evidence_fields"].append("claim.claimed_place_id")
            text["text"] = json.dumps(decisions)
            return httpx.Response(200, json=body)
        return response

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        result = asyncio.run(
            execute_run(
                prepared,
                approved_sha256=prepared["content_sha256"],
                google_api_key="synthetic-google",
                model_api_key="synthetic-model",
                http_client=client,
            )
        )
    finally:
        asyncio.run(client.aclose())
    assert result["processing_status"] == "complete", result
    return directory


def test_offline_import_reuses_primary_observations_and_exports_native_pair(
    installed_cli, paired_material, tmp_path, monkeypatch
):
    from backend.evaluation.snapshot import load_snapshot

    root, args, _, _ = paired_material
    primary = primary_run(paired_material, tmp_path / "primary", monkeypatch)
    imported = tmp_path / "v3-pair/import"
    result = run(installed_cli, "import", *args, "--primary-run", primary, "--directory", imported)
    assert result.returncode == 0, result.stdout + result.stderr
    handoff = json.loads(result.stdout)
    assert handoff["current_sends"] == 0
    identity = load_snapshot(imported / "identity-snapshot")
    evidence = load_snapshot(imported / "evidence-snapshot")
    assert identity["schema_version"] == evidence["schema_version"] == "rtpeval_imported_snapshot_1"
    assert all(row["origin"]["kind"] == "primary_evaluation" for row in identity["records"])
    original = load_snapshot(primary / "execution/identity-snapshot")
    assert (
        identity["records"][0]["attempts"][0]["retrieved_at"]
        == original["records"][0]["attempts"][0]["retrieved_at"]
    )
    assert identity["ledger"]["actual_sends"] == evidence["ledger"]["actual_sends"] == 0
    assert all(row["summary"]["status"] == "available" for row in evidence["records"])
    directory = tmp_path / "v3-pair/report"
    result = run(
        installed_cli,
        "prepare",
        *args,
        "--directory",
        directory,
        "--identity-snapshot",
        imported / "identity-snapshot",
        "--snapshot",
        imported / "evidence-snapshot",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        json.loads(result.stdout)["content_sha256"],
        bootstrap=LOOPBACK_FIXTURE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    saved = json.loads(result.stdout)
    assert saved["usage"]["actual_google_sends"] == 0
    assert saved["pair"]["groups"][0]["pair_status"] == "available"
    result = run(installed_cli, "replay", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == saved
    exported = tmp_path / "v3-pair/export"
    result = run(installed_cli, "export", directory, "--directory", exported)
    assert result.returncode == 0, result.stdout + result.stderr
    load_snapshot(exported / "execution/identity-snapshot")
    assert (root / "manifest.json").is_file()


@pytest.mark.parametrize("fault", [None, "native_hash", "original_field", "wrapper_drift"])
def test_generation_import_binds_finalized_producer_declaration(
    paired_material, installed_cli, tmp_path, fault
):
    import hashlib

    from backend.evaluation.snapshot import load_snapshot

    root, args, _, _ = paired_material
    generation = generation_source(paired_material, tmp_path / "generation")
    before = {
        p.relative_to(generation).as_posix(): p.read_bytes()
        for p in generation.rglob("*")
        if p.is_file()
    }
    manifest = json.loads((root / "manifest.json").read_bytes())
    selected = manifest["groups"][0]["selected_runs"]["v3"]
    native = json.loads((generation / "provenance.json").read_bytes())
    declaration = {
        **native,
        "declared_by": "rtpeval.generate/selected_workflow_1",
        "declared_at": "2026-06-01T00:02:00+00:00",
        "rationale": "Qualified selected producer declaration",
        "native_provenance_ref": {
            "path": "provenance.json",
            "sha256": hashlib.sha256((generation / "provenance.json").read_bytes()).hexdigest(),
            "availability": "available",
            "media_type": "application/json",
        },
    }
    if fault == "native_hash":
        declaration["native_provenance_ref"]["sha256"] = "0" * 64
    if fault == "original_field":
        declaration["configuration_ref"] = {**native["configuration_ref"], "sha256": "0" * 64}
    declaration_path = save(root, "producer-declaration.json", declaration)
    selected["provenance_ref"] = {
        "path": declaration_path.name,
        "sha256": hashlib.sha256(declaration_path.read_bytes()).hexdigest(),
        "availability": "available",
        "media_type": "application/json",
        "schema_version": "rtpeval_provenance_1",
    }
    save(root, "manifest.json", manifest)
    if fault == "wrapper_drift":
        declaration_path.write_bytes(declaration_path.read_bytes() + b" ")
    imported = tmp_path / "imported"
    result = run(
        installed_cli, "import", *args, "--generation", generation, "--directory", imported
    )
    if fault is None:
        assert result.returncode == 0, result.stdout + result.stderr
        snapshot = load_snapshot(imported / "identity-snapshot")
        details = [r for r in snapshot["records"] if r["summary"]["status"] == "available"]
        assert details
        assert all(r["origin"]["kind"] == "planner_generation" for r in details)
        assert snapshot["ledger"]["actual_sends"] == 0
        source = snapshot["sources"][0]
        assert source["selected_provenance"] in source["files"]
        copied = (
            imported
            / "identity-snapshot"
            / source["path"]
            / source["files"][source["selected_provenance"]]["path"]
        )
        assert copied.read_bytes() == declaration_path.read_bytes()
    else:
        assert result.returncode == 2
        assert not (imported / "handoff.json").exists()
    assert all((generation / name).read_bytes() == raw for name, raw in before.items())


def generation_source(
    paired_material, directory, *, mask=None, incomplete=False, language=None, route_body=None
):
    import httpx

    from backend.app.integrations.google.places import PLACES_DETAILS_FIELD_MASK
    from backend.app.observability.raw_capture import RawCapture
    from backend.evaluation.tools.generation_evidence import build_evidence_index

    root, _, _, _ = paired_material
    manifest = json.loads((root / "manifest.json").read_bytes())
    selected = manifest["groups"][0]["selected_runs"]["v3"]
    directory.mkdir()
    for name in ("result", "usage", "provenance"):
        (directory / (name + ".json")).write_bytes(
            (root / selected[name + "_ref"]["path"]).read_bytes()
        )
    usage = json.loads((directory / "usage.json").read_bytes())
    usage["timing"] = {
        "started_at": "2026-06-01T00:00:00+00:00",
        "finished_at": "2026-06-01T00:01:00+00:00",
    }
    usage["provider_events"] = []
    usage["outcome"] = "completed"
    raw = RawCapture(directory)
    for eid, pid in (("1", "pid-a"), ("2", "pid-b")):
        raw.request(
            httpx.Request(
                "GET",
                "https://places.googleapis.com/v1/places/" + pid,
                params={"languageCode": language} if language else None,
                headers={"X-Goog-FieldMask": mask or PLACES_DETAILS_FIELD_MASK},
            ),
            eid,
        )
        raw.response(
            httpx.Response(
                200,
                json={
                    "id": pid,
                    "displayName": {"text": "Museum " + pid[-1].upper()},
                    "formattedAddress": "10 Main St, Example City, Country",
                    "businessStatus": "OPERATIONAL",
                    "location": {"latitude": 10, "longitude": 20 if pid == "pid-a" else 21},
                    "timeZone": {"id": "Etc/UTC"},
                    "regularOpeningHours": {"periods": []},
                },
            ),
            eid,
        )
        usage["provider_events"].append(
            {
                "event_id": eid,
                "provider": "google",
                "operation": "place_details",
                "source": "http_request_hook",
                "outcome": "completed",
                "status_code": 200,
            }
        )
    if route_body is not None:
        from backend.evaluation.evaluation_transport import ROUTE_MASK

        raw.request(
            httpx.Request(
                "POST",
                "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
                headers={"X-Goog-FieldMask": ROUTE_MASK},
                json=route_body,
            ),
            "3",
        )
        raw.response(
            httpx.Response(
                200,
                json=[{"originIndex": 0, "destinationIndex": 0, "duration": "600s"}],
            ),
            "3",
        )
        usage["provider_events"].append(
            {
                "event_id": "3",
                "provider": "google",
                "operation": "route_matrix",
                "source": "http_request_hook",
                "outcome": "completed",
                "status_code": 200,
            }
        )
    raw.finish()
    if incomplete:
        for event in raw.events:
            event["response_body_status"] = "incomplete"
    save(directory, "usage.json", usage)
    provenance = json.loads((directory / "provenance.json").read_bytes())
    (directory / "input.json").write_bytes(
        (root / manifest["groups"][0]["input_ref"]["path"]).read_bytes()
    )
    policy = save(directory, "runtime-policy.json", {"sha256": "f" * 64, "configuration": {}})
    capture = {
        **provenance,
        "source_revision": "fixture-revision",
        "runtime_policy_sha256": "f" * 64,
        "status": "completed",
        "kind": "development_planner_usage_capture",
        "execution_requested": True,
        "evidence_requested": True,
    }
    save(directory, "manifest.json", capture)
    save(
        directory,
        "evidence-index.json",
        build_evidence_index(directory, capture, raw, usage, adapter_coverage="default_adapters"),
    )
    import hashlib

    provenance["configuration_ref"] = {
        "path": "runtime-policy.json",
        "sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
    }
    provenance["evidence_index_ref"] = {
        "path": "evidence-index.json",
        "sha256": hashlib.sha256((directory / "evidence-index.json").read_bytes()).hexdigest(),
    }
    save(directory, "provenance.json", provenance)
    for name in ("usage", "provenance"):
        ref = selected[name + "_ref"]
        (root / ref["path"]).write_bytes((directory / (name + ".json")).read_bytes())
        ref["sha256"] = hashlib.sha256((root / ref["path"]).read_bytes()).hexdigest()
    save(root, "manifest.json", manifest)
    return directory


@pytest.mark.parametrize(
    "departure, fault, expected_count",
    [
        ("2026-10-13T01:00:00Z", None, 1),
        ("2026-10-13T11:00:00+10:00", None, 1),
        ("2026-10-13T01:00:01Z", None, 0),
        ("2026-10-13T01:00:00", None, 0),
        ("invalid", None, 0),
        ("2026-10-13T01:00:00Z", "direction", 0),
        ("2026-10-13T01:00:00Z", "mode", 0),
        ("2026-10-13T01:00:00Z", "options", 0),
    ],
)
def test_generation_route_reuse_compares_explicit_departure_instants(
    paired_material, tmp_path, departure, fault, expected_count
):
    from backend.evaluation.evaluation_transport import google_wire
    from backend.evaluation.generation_import import generation_observations

    request = {
        "key": "route",
        "operation": "route_matrix",
        "parameters": {
            "origin": {"latitude": 10, "longitude": 20},
            "destination": {"latitude": 10, "longitude": 21},
            "mode": "DRIVE",
            "time_basis": "explicit_departure",
            "departure": "2026-10-13T01:00:00+00:00",
            "routing_options": {"routing_preference": "TRAFFIC_AWARE"},
        },
    }
    body = google_wire(request)["json"]
    body["departureTime"] = departure
    if fault == "direction":
        body["origins"], body["destinations"] = body["destinations"], body["origins"]
    elif fault == "mode":
        body["travelMode"] = "WALK"
    elif fault == "options":
        body["routingPreference"] = "TRAFFIC_AWARE_OPTIMAL"
    generation = generation_source(paired_material, tmp_path / "generation", route_body=body)
    originals = {
        p.relative_to(generation).as_posix(): p.read_bytes()
        for p in generation.rglob("*")
        if p.is_file()
    }
    source = {"files": {name: {"path": name} for name in originals}}
    observations, usage = generation_observations(
        originals.__getitem__,
        source,
        {"requests": [request]},
        load_batch(paired_material[0] / "manifest.json").to_dict(),
    )
    assert len(observations) == expected_count
    assert usage["charged_in_current_phase"] is False
    if observations:
        assert observations[0]["request"] == request
        assert observations[0]["origin"]["kind"] == "planner_generation"
        assert json.loads(originals["evidence/wire/0002-request.json"])["body"] == body
    assert all((generation / name).read_bytes() == raw for name, raw in originals.items())


def test_generation_observations_preserve_producer_origin_and_capture_window(
    installed_cli, paired_material, tmp_path
):
    from backend.evaluation.snapshot import load_snapshot

    _, args, _, _ = paired_material
    generation = generation_source(paired_material, tmp_path / "generation")
    imported = tmp_path / "import"
    result = run(
        installed_cli, "import", *args, "--generation", generation, "--directory", imported
    )
    assert result.returncode == 0, result.stdout + result.stderr
    snapshot = load_snapshot(imported / "identity-snapshot")
    details = [row for row in snapshot["records"] if row["origin"]]
    assert len(details) == 2
    assert all(row["origin"]["kind"] == "planner_generation" for row in details)
    assert all(row["origin"]["observation_time_basis"] == "run_capture_window" for row in details)
    assert all(row["attempts"][0]["retrieved_at"] == "2026-06-01T00:01:00+00:00" for row in details)
    assert snapshot["ledger"]["actual_sends"] == 0
    identity = json.loads((imported / "identity-report.json").read_bytes())
    assert any(
        row["resolution"] == "resolved" and row["version"] == "v3" for row in identity["records"]
    )
    assert snapshot["inherited_usage"][0]["charged_in_current_phase"] is False
    from backend.evaluation.snapshot_coordinates import prepare_snapshot_coordinates

    coordinates = prepare_snapshot_coordinates(
        load_batch(paired_material[0] / "manifest.json"),
        identity,
        imported / "identity-snapshot",
    ).to_dict()
    assert coordinates["records"]
    assert all(
        observation["pointer"] == "/body/location"
        for record in coordinates["records"]
        for observation in record["observations"]
    )


@pytest.mark.parametrize("fault", ["mask", "incomplete"])
def test_incompatible_generation_capture_remains_unknown_without_sends(
    installed_cli, paired_material, tmp_path, fault
):
    from backend.evaluation.snapshot import load_snapshot

    _, args, _, _ = paired_material
    generation = generation_source(
        paired_material,
        tmp_path / "generation",
        mask="id,displayName" if fault == "mask" else None,
        incomplete=fault == "incomplete",
    )
    imported = tmp_path / "import"
    result = run(
        installed_cli, "import", *args, "--generation", generation, "--directory", imported
    )
    assert result.returncode == 0, result.stdout + result.stderr
    snapshot = load_snapshot(imported / "identity-snapshot")
    assert all(
        row["origin"] is None and row["summary"]["status"] == "unavailable"
        for row in snapshot["records"]
    )
    assert snapshot["ledger"]["actual_sends"] == 0


def test_generation_source_drift_is_rejected_before_import_handoff(
    installed_cli, paired_material, tmp_path
):
    _, args, _, _ = paired_material
    generation = generation_source(paired_material, tmp_path / "generation")
    (generation / "evidence/wire/0000-response.json").write_text('{"body": {}}')
    imported = tmp_path / "import"
    result = run(
        installed_cli, "import", *args, "--generation", generation, "--directory", imported
    )
    assert result.returncode == 2
    assert "artifact hash mismatch" in result.stdout
    assert not (imported / "handoff.json").exists()


@pytest.mark.parametrize("artifact", ["index", "wire"])
def test_duplicate_generation_json_is_rejected_even_with_matching_hashes(
    installed_cli, paired_material, tmp_path, artifact
):
    import hashlib

    root, args, _, _ = paired_material
    generation = generation_source(paired_material, tmp_path / "generation")
    index_path = generation / "evidence-index.json"
    if artifact == "index":
        index_path.write_bytes(
            b'{"schema_version":"rtpeval_generation_evidence_1",' + index_path.read_bytes()[1:]
        )
    else:
        wire_path = generation / "evidence/wire/0000-response.json"
        wire_path.write_bytes(
            b'{"representation":"credential_filtered_utf8",' + wire_path.read_bytes()[1:]
        )
        index = json.loads(index_path.read_bytes())
        for ref in index["artifacts"]:
            if ref["path"] == wire_path.relative_to(generation).as_posix():
                ref["sha256"] = hashlib.sha256(wire_path.read_bytes()).hexdigest()
        save(generation, "evidence-index.json", index)
    provenance = json.loads((generation / "provenance.json").read_bytes())
    provenance["evidence_index_ref"]["sha256"] = hashlib.sha256(index_path.read_bytes()).hexdigest()
    save(generation, "provenance.json", provenance)
    manifest = json.loads((root / "manifest.json").read_bytes())
    ref = manifest["groups"][0]["selected_runs"]["v3"]["provenance_ref"]
    (root / ref["path"]).write_bytes((generation / "provenance.json").read_bytes())
    ref["sha256"] = hashlib.sha256((root / ref["path"]).read_bytes()).hexdigest()
    save(root, "manifest.json", manifest)
    imported = tmp_path / "import"
    result = run(
        installed_cli, "import", *args, "--generation", generation, "--directory", imported
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not (imported / "handoff.json").exists()


def test_import_can_reuse_primary_identity_details_for_evidence_gaps(
    installed_cli, paired_material, tmp_path, monkeypatch
):
    from backend.evaluation.snapshot import load_snapshot

    _, args, _, _ = paired_material
    primary = primary_run(
        paired_material, tmp_path / "primary", monkeypatch, evidence_details_failure=True
    )
    imported = tmp_path / "import"
    result = run(installed_cli, "import", *args, "--primary-run", primary, "--directory", imported)
    assert result.returncode == 0, result.stdout + result.stderr
    snapshot = load_snapshot(imported / "evidence-snapshot")
    details = {
        row["key"] for row in snapshot["plan"]["requests"] if row["operation"] == "places_details"
    }
    assert len(details) == 2
    assert all(
        row["summary"]["status"] == "available"
        for row in snapshot["records"]
        if row["key"] in details
    )
    assert snapshot["ledger"]["actual_sends"] == 0


def test_mixed_sources_preserve_per_request_origins_and_original_usage(
    installed_cli, paired_material, tmp_path, monkeypatch
):
    from backend.evaluation.snapshot import load_snapshot

    _, args, _, _ = paired_material
    generation = generation_source(paired_material, tmp_path / "generation", language="en")
    primary = primary_run(
        paired_material, tmp_path / "primary", monkeypatch, failed_place_id="pid-b"
    )
    imported = tmp_path / "import"
    result = run(
        installed_cli,
        "import",
        *args,
        "--primary-run",
        primary,
        "--generation",
        generation,
        "--directory",
        imported,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    snapshot = load_snapshot(imported / "identity-snapshot")
    requests = {row["key"]: row for row in snapshot["plan"]["requests"]}
    details = {
        requests[row["key"]]["parameters"]["place_id"]: row
        for row in snapshot["records"]
        if requests[row["key"]]["operation"] == "places_details"
    }
    assert details["pid-a"]["origin"]["kind"] == "primary_evaluation"
    assert details["pid-b"]["origin"]["kind"] == "planner_generation"
    assert all(row["summary"]["status"] == "available" for row in details.values())
    assert snapshot["ledger"]["actual_sends"] == 0
    assert len(snapshot["inherited_usage"]) == 2


def test_primary_route_reuse_checks_direction_ids_coordinates_mode_time_and_options(
    paired_material, tmp_path, monkeypatch
):
    from backend.evaluation.snapshot import _hash, load_snapshot
    from backend.evaluation.snapshot_import import import_pair, import_snapshot

    root, _, values, _ = paired_material
    primary = primary_run(paired_material, tmp_path / "primary", monkeypatch)
    baseline = tmp_path / "baseline"
    context_values = {
        "schedule_context": values["context"],
        "route_reviews": values["route-reviews"],
        "density_reviews": values["density-reviews"],
        "occupancy_reviews": None,
        "correspondence_reviews": None,
    }
    import_pair(root / "manifest.json", baseline, context=context_values, primary_runs=[primary])
    snapshot = load_snapshot(baseline / "evidence-snapshot")
    for fault in ("direction", "place_id", "coordinate", "mode", "time", "options"):
        plan = copy.deepcopy(snapshot["plan"])
        route = next(row for row in plan["requests"] if row["operation"] == "route_matrix")
        old_key, params = route["key"], route["parameters"]
        if fault == "direction":
            params["origin"], params["destination"] = params["destination"], params["origin"]
        elif fault == "place_id":
            params["origin"]["place_id"] = "different-id"
        elif fault == "coordinate":
            params["origin"]["latitude"] += 0.01
        elif fault == "mode":
            params["mode"] = "DRIVE"
        elif fault == "time":
            params.update(time_basis="explicit_departure", departure="2020-01-01T10:00:00Z")
        else:
            params["routing_options"] = {"avoid_ferries": True}
        route["key"] = _hash({"operation": route["operation"], "parameters": params})
        for leg in plan["legs"]:
            if leg["request_key"] == old_key:
                leg["request_key"] = route["key"]
        imported = import_snapshot(
            plan, tmp_path / fault, intake=snapshot["intake"], primary_runs=[primary]
        )
        observation = next(row for row in imported["records"] if row["key"] == route["key"])
        assert observation["attempts"] == []
        assert observation["summary"]["reason"] == "no_compatible_observation"
        assert imported["ledger"]["actual_sends"] == 0


def test_imported_snapshots_do_not_charge_inherited_provider_attempts(
    installed_cli, paired_material, tmp_path
):
    root, args, _, _ = paired_material
    generation = generation_source(paired_material, tmp_path / "generation")
    imported = tmp_path / "import"
    result = run(
        installed_cli, "import", *args, "--generation", generation, "--directory", imported
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output = tmp_path / "cost.json"
    result = installed_cli(
        "cost",
        "--snapshot",
        imported / "identity-snapshot",
        "--prices",
        root / "prices.json",
        "--output",
        output,
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    cost = json.loads(output.read_bytes())
    assert cost["runs"][0]["estimated_total"] == "0"
    assert cost["runs"][0]["events"] == []
    assert cost["runs"][0]["inherited_usage"][0]["actual_source_google_sends"] == 2


def test_imported_pair_accepts_explicit_zero_request_and_cost_limits(
    installed_cli, paired_material, tmp_path
):
    root, args, values, _ = paired_material
    imported = tmp_path / "import"
    result = run(installed_cli, "import", *args, "--directory", imported)
    assert result.returncode == 0, result.stdout + result.stderr
    save(root, "options.json", {**values["options"], "max_google_sends": 0, "max_cost_usd": "0"})
    directory = tmp_path / "paired"
    result = run(
        installed_cli,
        "prepare",
        *args,
        "--directory",
        directory,
        "--identity-snapshot",
        imported / "identity-snapshot",
        "--snapshot",
        imported / "evidence-snapshot",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    preparation = json.loads(result.stdout)
    assert preparation["execution_mode"] == "offline_reuse"
    assert preparation["request_inventory"]["estimated_cost_usd"] == "0"
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        preparation["content_sha256"],
        bootstrap=LOOPBACK_FIXTURE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["usage"]["actual_google_sends"] == 0
    assert run(installed_cli, "replay", directory).returncode == 0


@pytest.mark.parametrize("language, expected_count", [("en", 2), ("fr", 0)])
def test_generation_details_locale_is_explicitly_checked_and_preserved(
    installed_cli, paired_material, tmp_path, language, expected_count
):
    from backend.evaluation.snapshot import load_snapshot

    _, args, _, _ = paired_material
    generation = generation_source(paired_material, tmp_path / "generation", language=language)
    imported = tmp_path / "import"
    result = run(
        installed_cli, "import", *args, "--generation", generation, "--directory", imported
    )
    assert result.returncode == 0, result.stdout + result.stderr
    snapshot = load_snapshot(imported / "identity-snapshot")
    rows = [row for row in snapshot["records"] if row["origin"] is not None]
    assert len(rows) == expected_count
    if rows:
        assert all(row["origin"]["source_language_code"] == "en" for row in rows)
        assert all("languageCode=en" in row["origin"]["source_url"] for row in rows)


LOOPBACK_FIXTURE = """
original_socketpair = socket.socketpair
def local_socketpair(*args, **kwargs):
    guarded_connect = socket.socket.connect
    socket.socket.connect = original_connect
    try: return original_socketpair(*args, **kwargs)
    finally: socket.socket.connect = guarded_connect
socket.socketpair = local_socketpair
"""
HTTP_FIXTURE = (
    LOOPBACK_FIXTURE
    + """
import httpx
import json
from urllib.parse import unquote
original_environment = os._Environ.__getitem__
def fixture_environment(self, key):
    if key == 'GOOGLE_MAPS_API_KEY': return 'synthetic-secret-google'
    return original_environment(self, key)
os._Environ.__getitem__ = fixture_environment
class FixtureClient:
    def __init__(self, **kwargs): self.calls = 0
    async def request(self, method, url, **kwargs):
        self.calls += 1
        def place(pid):
            name = 'Museum ' + pid[-1].upper()
            return {'id': pid, 'displayName': {'text': name},
                    'formattedAddress': '10 Main St, Example City, Country',
                    'businessStatus': 'OPERATIONAL',
                    'location': {'latitude': 10, 'longitude': 20 + ord(pid[-1]) - ord('a')},
                    'timeZone': {'id': 'Etc/UTC'},
                    'regularOpeningHours': {
                        'periods': [{'open': {'day': 0, 'hour': 0, 'minute': 0}}]}}
        if 'searchText' in url:
            body = {'places': [place('pid-a'), place('pid-b')]}
        elif 'computeRouteMatrix' in url:
            body = [{'originIndex': 0, 'destinationIndex': 0, 'status': {},
                     'condition': 'ROUTE_EXISTS', 'duration': '1800s', 'distanceMeters': 2500}]
        else:
            body = place(unquote(url.rsplit('/', 1)[-1]))
        return httpx.Response(200, json=body)
    async def aclose(self): pass
httpx.AsyncClient = FixtureClient
"""
)


def test_offline_preparation_preserves_selected_stages_and_native_inventory(
    installed_cli, paired_material, tmp_path
):
    root, args, _, _ = paired_material
    originals = {p: p.read_bytes() for p in root.glob("*.json")}
    directory = tmp_path / "paired-preparation"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    preparation = json.loads((directory / "preparation.json").read_bytes())
    assert preparation["identity_plan"]["paired"] is True
    assert preparation["evidence_plan"]["paired"] is True
    assert preparation["scope"] == "selected_v3_paired_evidence"
    assert preparation["max_model_sends"] == preparation["max_retries"] == 0
    pointers = {
        r["source"]["pointer"]
        for r in preparation["identity_plan"]["references"]
        if r["source"].get("run_id") == "run-v3" and "pointer" in r["source"]
    }
    assert any(p.startswith("/v3/draft/") for p in pointers)
    assert any(p.startswith("/v3/final_primary/") for p in pointers)
    assert preparation["request_inventory"]["identity_request_count"] == 4
    assert preparation["request_inventory"]["evidence_status"] == "deferred_until_identity"
    assert not (directory / "execution").exists()
    assert {p: p.read_bytes() for p in originals} == originals
    rejected = run(installed_cli, "prepare", *args, "--directory", directory)
    assert rejected.returncode == 2


def test_injected_acquisition_reports_an_unchanged_pair_and_replays_without_sends(
    installed_cli, paired_material, tmp_path
):
    _, args, _, _ = paired_material
    directory = tmp_path / "acquisition"
    prepared = run(installed_cli, "prepare", *args, "--directory", directory)
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    digest = json.loads(prepared.stdout)["content_sha256"]
    result = run(
        installed_cli, "execute", directory, "--approved-sha256", digest, bootstrap=HTTP_FIXTURE
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    pair = report["pair"]["groups"][0]
    assert pair["pair_status"] == "available"
    assert pair["deltas"]["auxiliary_total"]["percentage_points"] == 0
    assert pair["deltas"]["overall_total"]["percentage_points"] == 0
    assert report["usage"]["actual_google_sends"] == 7
    assert report["usage"]["actual_model_sends"] == report["usage"]["retries"] == 0
    assert report["usage"]["raw"]["namespace"] == "oracle"
    assert (directory / "execution/evidence-snapshot/manifest.json").is_file()
    replayed = run(installed_cli, "replay", directory)
    assert replayed.returncode == 0, replayed.stdout + replayed.stderr
    assert json.loads(replayed.stdout) == report
    rejected = run(installed_cli, "execute", directory, "--approved-sha256", digest)
    assert rejected.returncode == 2


def test_export_is_fresh_and_accepted_by_native_pair_and_opt_in_suite(
    installed_cli, paired_material, tmp_path
):
    from backend.tests.evaluation.test_evaluation_run import options

    _, args, _, _ = paired_material
    directory, exported = tmp_path / "acquisition", tmp_path / "exported"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    digest = json.loads(result.stdout)["content_sha256"]
    result = run(
        installed_cli, "execute", directory, "--approved-sha256", digest, bootstrap=HTTP_FIXTURE
    )
    assert result.returncode == 0, result.stdout + result.stderr
    saved = json.loads(result.stdout)
    originals = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    result = run(installed_cli, "export", directory, "--directory", exported)
    assert result.returncode == 0, result.stdout + result.stderr
    handoff = json.loads(result.stdout)
    pair = handoff["suite_pair"]
    native_args = [
        "pair",
        "report",
        exported / handoff["manifest"],
        exported / pair["identity"],
        exported / pair["snapshot"],
    ]
    for field, flag in (
        ("context", "context"),
        ("route_reviews", "route-reviews"),
        ("density_reviews", "density-reviews"),
        ("expected_plan", "expected-plan"),
        ("edit_provenance", "edit-provenance"),
        ("identity_snapshot", "identity-snapshot"),
    ):
        native_args.extend(["--" + flag, exported / pair[field]])
    native_args.extend(["--generated-at", saved["generated_at"]])
    result = installed_cli(*native_args, evaluation_offline=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        json.loads(result.stdout) == saved["pair"]
        or json.loads(result.stdout)["groups"] == saved["pair"]["groups"]
    )
    save(exported, "suite-options.json", options())
    suite = {
        "schema_version": "rtpeval_suite_1",
        "suite_id": "paired-handoff",
        "max_cost_usd": "10",
        "cases": [
            {
                "case_id": "selected",
                "revision": "1",
                "manifest": handoff["manifest"],
                "options": "suite-options.json",
                "prices": "material/context/prices.json",
                "tracks": {"pair": pair},
            }
        ],
    }
    source = save(exported, "suite.json", suite)
    result = installed_cli(
        "suite", "prepare", source, "--directory", tmp_path / "suite", evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        json.loads((tmp_path / "suite/tracks/0001/pair.json").read_bytes())["groups"]
        == saved["pair"]["groups"]
    )
    assert {p: p.read_bytes() for p in originals} == originals
    assert run(installed_cli, "export", directory, "--directory", exported).returncode == 2


@pytest.mark.parametrize("fault", ["approval", "source", "copied_context", "copied_extra", "code"])
def test_execute_rejects_changed_preflight_before_credentials_or_transport(
    installed_cli, paired_material, tmp_path, fault
):
    root, args, _, _ = paired_material
    directory = tmp_path / "prepared"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    digest = json.loads(result.stdout)["content_sha256"]
    bootstrap = ""
    if fault == "approval":
        digest = "0" * 64
    elif fault == "source":
        (root / "v3.json").write_bytes(b"{}")
    elif fault == "copied_context":
        (directory / "material/context/context.json").write_bytes(b"{}")
    elif fault == "copied_extra":
        save(directory / "material", "extra.json", {})
    else:
        bootstrap = """
from pathlib import Path
original_read_bytes = Path.read_bytes
def changed_code(self):
    raw = original_read_bytes(self)
    return raw + b' ' if self.name == 'paired_execution.py' else raw
Path.read_bytes = changed_code
"""
    result = run(
        installed_cli, "execute", directory, "--approved-sha256", digest, bootstrap=bootstrap
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not (directory / "execution").exists()


@pytest.mark.parametrize(
    "stop", ["send_budget", "cost_budget", "cancel", "interrupt", "total_timeout"]
)
def test_stopped_acquisition_keeps_partial_journal_and_can_only_replay(
    installed_cli, paired_material, tmp_path, stop
):
    root, args, values, _ = paired_material
    fixture = HTTP_FIXTURE
    if stop == "send_budget":
        values["options"]["max_google_sends"] = 2
    elif stop == "cost_budget":
        values["options"]["max_cost_usd"] = "0.07"
    elif stop in ("cancel", "interrupt"):
        fixture += """
import asyncio
normal_request = FixtureClient.request
async def cancelling(self, *args, **kwargs):
    if self.calls == 1: raise asyncio.CancelledError()
    return await normal_request(self, *args, **kwargs)
FixtureClient.request = cancelling
"""
        if stop == "interrupt":
            fixture = fixture.replace("raise asyncio.CancelledError()", "raise KeyboardInterrupt()")
    else:
        values["options"]["total_timeout_seconds"] = 0.02
        fixture += """
import asyncio
async def slow(self, *args, **kwargs): await asyncio.sleep(10)
FixtureClient.request = slow
"""
    save(root, "options.json", values["options"])
    directory = tmp_path / "bounded"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    digest = json.loads(result.stdout)["content_sha256"]
    result = run(
        installed_cli, "execute", directory, "--approved-sha256", digest, bootstrap=fixture
    )
    assert result.returncode == 2, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["processing_status"] == "stopped"
    assert report["pair"] is None
    if stop == "interrupt":
        assert report["reason"] == "execution_interrupted"
    assert 0 < report["usage"]["actual_google_sends"] <= 2
    assert report["usage"]["actual_model_sends"] == report["usage"]["retries"] == 0
    assert (directory / "execution/receipt.json").is_file()
    replayed = run(installed_cli, "replay", directory)
    assert replayed.returncode == 2, replayed.stdout + replayed.stderr
    assert json.loads(replayed.stdout) == report
    assert run(installed_cli, "execute", directory, "--approved-sha256", digest).returncode == 2
    assert (
        run(installed_cli, "export", directory, "--directory", tmp_path / "export").returncode == 2
    )


def test_interruption_after_http_capture_retains_a_replayable_partial_response(
    installed_cli, paired_material, tmp_path
):
    _, args, _, _ = paired_material
    directory = tmp_path / "interrupt-after-response"
    prepared = run(installed_cli, "prepare", *args, "--directory", directory)
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    fixture = (
        HTTP_FIXTURE
        + """
from pathlib import Path
original_write = Path.write_bytes
def interrupted_write(self, data):
    result = original_write(self, data)
    if (self.name == '1.json' and self.parent.name == 'http'
            and json.loads(data).get('status_code') == 200):
        raise KeyboardInterrupt()
    return result
Path.write_bytes = interrupted_write
"""
    )
    executed = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        json.loads(prepared.stdout)["content_sha256"],
        bootstrap=fixture,
    )
    assert executed.returncode == 2, executed.stdout + executed.stderr
    report = json.loads(executed.stdout)
    assert report["reason"] == "execution_interrupted"
    assert report["usage"]["actual_google_sends"] == 1
    execution = directory / "execution"
    event = json.loads((execution / "http/1.json").read_bytes())
    assert event["status_code"] == 200
    replayed = run(installed_cli, "replay", directory)
    assert json.loads(replayed.stdout) == report
    partial = execution / "identity-snapshot/raw" / (event["request_key"] + "-1.bin")
    assert partial.read_bytes() == (execution / "http/1.bin").read_bytes()
    assert not (execution / "identity-snapshot/manifest.json").exists()


@pytest.mark.parametrize("fault", ["http_response", "snapshot_response", "missing_response"])
def test_stopped_replay_rejects_rehashed_partial_response_corruption(
    installed_cli, paired_material, tmp_path, fault
):
    import hashlib

    _, args, _, _ = paired_material
    directory = tmp_path / "cancelled"
    prepared = run(installed_cli, "prepare", *args, "--directory", directory)
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    fixture = (
        HTTP_FIXTURE
        + """
import asyncio
normal_request = FixtureClient.request
async def cancelling(self, *args, **kwargs):
    if self.calls == 1: raise asyncio.CancelledError()
    return await normal_request(self, *args, **kwargs)
FixtureClient.request = cancelling
"""
    )
    executed = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        json.loads(prepared.stdout)["content_sha256"],
        bootstrap=fixture,
    )
    assert executed.returncode == 2, executed.stdout + executed.stderr
    assert json.loads(executed.stdout)["reason"] == "execution_cancelled"
    intact = run(installed_cli, "replay", directory)
    assert json.loads(intact.stdout) == json.loads(executed.stdout)
    execution = directory / "execution"
    event = json.loads((execution / "http/1.json").read_bytes())
    partial = execution / "identity-snapshot/raw" / (event["request_key"] + "-1.bin")
    assert partial.read_bytes() == (execution / "http/1.bin").read_bytes()
    if fault == "missing_response":
        partial.unlink()
    else:
        corrupted = execution / "http/1.bin" if fault == "http_response" else partial
        corrupted.write_bytes(b'{"id":"foreign-place"}')
    receipt = json.loads((execution / "receipt.json").read_bytes())
    receipt["files"] = {
        str(p.relative_to(execution)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in execution.rglob("*")
        if p.is_file() and p != execution / "receipt.json"
    }
    save(execution, "receipt.json", receipt)
    replayed = run(installed_cli, "replay", directory)
    assert replayed.returncode == 2, replayed.stdout + replayed.stderr
    assert json.loads(replayed.stdout)["processing_status"] == "needs_material_correction"


def test_changed_visit_hours_produce_signed_native_deltas(
    installed_cli, paired_material, batch, tmp_path
):
    root, args, values, _ = paired_material
    final = batch[1]["v3"]["v3"]["final_primary"]["days"][0]["activities"][-1]
    final.update(start_time="2020-01-01T13:00:00+00:00", end_time="2020-01-01T14:00:00+00:00")
    batch[2]("v3")
    rebind_selection(root, values)
    directory = tmp_path / "changed-hours"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    digest = json.loads(result.stdout)["content_sha256"]
    fixture = HTTP_FIXTURE.replace("'1800s'", "'600s'").replace(
        "{'open': {'day': 0, 'hour': 0, 'minute': 0}}",
        "{'open': {'day': 3, 'hour': 9, 'minute': 0}, "
        "'close': {'day': 3, 'hour': 12, 'minute': 0}}",
    )
    result = run(
        installed_cli, "execute", directory, "--approved-sha256", digest, bootstrap=fixture
    )
    assert result.returncode == 0, result.stdout + result.stderr
    pair = json.loads(result.stdout)["pair"]["groups"][0]
    delta = pair["deltas"]["dimensions"]["opening"]["verified_score_percentage_points"]
    assert delta < 0
    assert pair["deltas"]["overall_total"]["percentage_points"] < 0
    assert pair["deltas"]["overall_total"]["exact_fraction"]["numerator"] < 0


@pytest.mark.parametrize("fault", ["http", "malformed", "transport", "redaction"])
def test_provider_failures_preserve_units_and_redact_captured_credentials(
    installed_cli, paired_material, tmp_path, fault
):
    _, args, _, _ = paired_material
    directory = tmp_path / "provider"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads(result.stdout)
    fixture = HTTP_FIXTURE
    if fault == "http":
        fixture = fixture.replace(
            "return httpx.Response(200, json=body)",
            "return httpx.Response(503, json={'error':'temporary'})",
        )
    elif fault == "malformed":
        fixture = fixture.replace(
            "return httpx.Response(200, json=body)",
            "return httpx.Response(200, content=b'not JSON')",
        )
    elif fault == "transport":
        fixture += """
async def disconnected(self, *args, **kwargs): raise httpx.ConnectError('offline fixture')
FixtureClient.request = disconnected
"""
    else:
        fixture = fixture.replace(
            "return httpx.Response(200, json=body)",
            "if isinstance(body, dict): body.update(api_key='synthetic-secret-google', "
            "authorization='unrelated-secret-token')\n"
            "        return httpx.Response(200, json=body)",
        )
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        prepared["content_sha256"],
        bootstrap=fixture,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    plan = json.loads((directory / "execution/evidence-plan.json").read_bytes())
    assert len(plan["references"]) == len(prepared["evidence_plan"]["references"])
    for path in directory.rglob("*"):
        if path.is_file():
            assert b"synthetic-secret-google" not in path.read_bytes()
            assert b"unrelated-secret-token" not in path.read_bytes()
    assert report["evidence_status"] == ("available" if fault == "redaction" else "partial")
    assert run(installed_cli, "replay", directory).returncode == 0


def rebind_selection(root, values):
    intake = load_batch(root / "manifest.json")
    assert intake.status == "accepted", intake.to_dict()
    group = intake.to_dict()["inventory"][0]
    row = values["selection"]["runs"][0]
    row.update(
        input_sha256=group["input_sha256"],
        requirement_spec_sha256=group["requirement_spec_sha256"],
        result_sha256=group["runs"]["v3"]["final"]["context"]["artifact_sha256"],
    )
    save(root, "selection.json", values["selection"])
    for name, value in (
        ("context", context(intake)),
        ("route-reviews", reviews(intake)),
        ("density-reviews", density_reviews(intake)),
    ):
        save(root, name + ".json", value)


def test_absent_original_pair_keeps_null_deltas_and_never_sends(
    installed_cli, paired_material, batch, tmp_path
):
    root, args, values, _ = paired_material
    del batch[1]["v3"]["v3"]
    batch[2]("v3")
    rebind_selection(root, values)
    directory = tmp_path / "missing"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads(result.stdout)
    assert prepared["request_inventory"]["identity_request_count"] == 0
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        prepared["content_sha256"],
        bootstrap=LOOPBACK_FIXTURE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["evidence_status"] == "pair_unavailable"
    assert report["usage"]["actual_google_sends"] == 0
    pair = report["pair"]["groups"][0]
    assert pair["pair_status"] == "pair_unavailable"
    assert pair["deltas"] is None
    assert not list((directory / "execution").glob("*-snapshot"))
    assert run(installed_cli, "replay", directory).returncode == 0


def test_second_input_and_changed_pair_keep_occurrences_and_signed_delta(
    installed_cli, paired_material, batch, tmp_path
):
    root, args, values, _ = paired_material
    manifest, results, write, saver, _ = batch
    original = json.loads((root / "input.json").read_bytes())
    original.update(
        destination="Other City",
        start_date="2021-02-02",
        end_date="2021-02-02",
        budget={"amount": 200, "currency": "USD"},
    )
    input_ref = saver("input.json", original)
    manifest["groups"][0]["input_ref"] = input_ref
    spec = json.loads((root / "requirements.json").read_bytes())
    spec["input_sha256"] = input_ref["sha256"]
    manifest["groups"][0]["requirement_spec_ref"] = saver(
        "requirements.json", spec, spec["schema_version"]
    )
    for version in results:
        results[version] = json.loads(
            json.dumps(results[version])
            .replace("Example City", "Other City")
            .replace("2020-01-01", "2021-02-02")
        )
        provenance = json.loads((root / (version + "-provenance.json")).read_bytes())
        provenance["input_sha256"] = input_ref["sha256"]
        manifest["groups"][0]["selected_runs"][version]["provenance_ref"] = saver(
            version + "-provenance.json", provenance, provenance["schema_version"]
        )
    final = results["v3"]["v3"]["final_primary"]["days"][0]["activities"]
    third = copy.deepcopy(final[-1])
    third.update(
        activity_id="c",
        title="Museum C",
        place_name="Museum C",
        source_place_id="pid-c",
        start_time="2021-02-02T09:30:00+00:00",
        end_time="2021-02-02T10:45:00+00:00",
    )
    final.append(third)
    for version in results:
        write(version)
    rebind_selection(root, values)
    directory = tmp_path / "second"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    preparation = json.loads(result.stdout)
    assert preparation["request_inventory"]["identity_request_count"] == 6
    fixture = HTTP_FIXTURE.replace("Example City", "Other City").replace(
        "[place('pid-a'), place('pid-b')]", "[place('pid-a'), place('pid-b'), place('pid-c')]"
    )
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        preparation["content_sha256"],
        bootstrap=fixture,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    pair = report["pair"]["groups"][0]
    assert pair["deltas"]["daily_density_penalty"] == 10
    assert pair["deltas"]["density"][0]["changes"]["known_primary_count"]["delta"] == 1
    # Changed eligibility remains null rather than inventing a comparable total.
    assert pair["deltas"]["overall_total"]["percentage_points"] is None
    assert pair["continuity"]["conflicts"][0]["transition"] == "unresolved_attribution"
    plan = json.loads((directory / "execution/evidence-plan.json").read_bytes())
    final_refs = [
        r for r in plan["references"] if r["source"]["pointer"].startswith("/v3/final_primary/")
    ]
    draft_refs = [r for r in plan["references"] if r["source"]["pointer"].startswith("/v3/draft/")]
    assert len(final_refs) == 3 and len(draft_refs) == 2
    assert len(plan["requests"]) < len(plan["references"]) + len(plan["legs"])
    assert run(installed_cli, "replay", directory).returncode == 0


@pytest.mark.parametrize(
    "fault",
    ["response", "journal", "report", "usage", "receipt", "rehashed_response", "rehashed_journal"],
)
def test_replay_rejects_corruption_including_rehashed_provider_evidence(
    installed_cli, paired_material, tmp_path, fault
):
    import hashlib

    root, args, _, _ = paired_material
    directory = tmp_path / "acquired"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    digest = json.loads(result.stdout)["content_sha256"]
    result = run(
        installed_cli, "execute", directory, "--approved-sha256", digest, bootstrap=HTTP_FIXTURE
    )
    assert result.returncode == 0, result.stdout + result.stderr
    execution = directory / "execution"
    if fault in ("response", "rehashed_response"):
        raw = execution / "http/1.bin"
        raw.write_bytes(b'{"id":"foreign-place"}')
    elif fault in ("journal", "rehashed_journal"):
        value = json.loads((execution / "http/1.json").read_bytes())
        value["request"]["url"] = "https://foreign.example/"
        save(execution / "http", "1.json", value)
    else:
        (execution / (fault + ".json")).write_bytes(b"{}")
    if fault.startswith("rehashed_"):
        receipt = json.loads((execution / "receipt.json").read_bytes())
        receipt["files"] = {
            str(p.relative_to(execution)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in execution.rglob("*")
            if p.is_file() and p != execution / "receipt.json"
        }
        save(execution, "receipt.json", receipt)
    result = run(installed_cli, "replay", directory)
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"


@pytest.mark.parametrize("imported", [False, True])
def test_export_research_descriptor_is_accepted_by_existing_repair_reader(
    installed_cli, paired_material, tmp_path, imported
):
    from backend.tests.research_native_fixtures import declare_native

    _, args, _, _ = paired_material
    directory, exported = tmp_path / "acquired", tmp_path / "exported"
    cached_args = []
    if imported:
        generation = generation_source(paired_material, tmp_path / "generation", language="en")
        snapshots = tmp_path / "import"
        result = run(
            installed_cli, "import", *args, "--generation", generation, "--directory", snapshots
        )
        assert result.returncode == 0, result.stdout + result.stderr
        cached_args = [
            "--identity-snapshot",
            snapshots / "identity-snapshot",
            "--snapshot",
            snapshots / "evidence-snapshot",
        ]
    result = run(installed_cli, "prepare", *args, "--directory", directory, *cached_args)
    assert result.returncode == 0, result.stdout + result.stderr
    digest = json.loads(result.stdout)["content_sha256"]
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        digest,
        bootstrap=LOOPBACK_FIXTURE if imported else HTTP_FIXTURE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    result = run(installed_cli, "export", directory, "--directory", exported)
    assert result.returncode == 0, result.stdout + result.stderr
    handoff = json.loads(result.stdout)
    manifest = json.loads((exported / handoff["manifest"]).read_bytes())
    prefix = "material/native/"
    for group in manifest["groups"]:
        for field in ("input_ref", "requirement_spec_ref"):
            group[field]["path"] = prefix + group[field]["path"]
        for selected in group["selected_runs"].values():
            for field in ("result_ref", "usage_ref", "provenance_ref"):
                selected[field]["path"] = prefix + selected[field]["path"]
    declaration = declare_native(exported, manifest, pairs=[handoff["research_pair"]])
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "repair",
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "repair/repair.json").read_bytes())
    assert report["same_run"]["summary"]["unchanged"] == 1


@pytest.mark.parametrize(
    "fault", ["selection", "stage", "review", "spec", "budget", "price", "credentials"]
)
def test_prepare_rejects_bad_local_material_with_zero_dispatch(
    installed_cli, paired_material, tmp_path, fault
):
    root, args, values, _ = paired_material
    if fault == "selection":
        values["selection"]["runs"][0]["run_id"] = "foreign-run"
    elif fault == "stage":
        values["selection"]["runs"][0]["stage_pointers"]["draft"] = "/itinerary"
    elif fault == "review":
        values["route-reviews"]["groups"] = []
    elif fault == "spec":
        (root / "requirements.json").write_bytes(b"{}")
    elif fault == "budget":
        values["options"]["max_cost_usd"] = "NaN"
    elif fault == "price":
        values["prices"]["rows"] = []
    else:
        values["options"]["google_api_key"] = "secret"
    for name, value in values.items():
        save(root, name + ".json", value)
    directory = tmp_path / "bad"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 2, result.stdout + result.stderr
    assert not directory.exists()


@pytest.mark.parametrize("command", [(), ("prepare",), ("execute",), ("replay",), ("export",)])
def test_acquire_help_is_lazy_and_offline(installed_cli, command):
    result = run(installed_cli, *command, "--help", block_intake=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("operation", ["prepare", "export"])
def test_existing_dangling_destination_is_rejected_before_resolution(
    installed_cli, paired_material, tmp_path, operation
):
    _, args, _, _ = paired_material
    source = tmp_path / "source"
    if operation == "export":
        result = run(installed_cli, "prepare", *args, "--directory", source)
        assert result.returncode == 0, result.stdout + result.stderr
        result = run(
            installed_cli,
            "execute",
            source,
            "--approved-sha256",
            json.loads(result.stdout)["content_sha256"],
            bootstrap=HTTP_FIXTURE,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    link, target = tmp_path / "existing-link", tmp_path / "missing-target"
    # Model the native filesystem's dangling-link result without Windows link privileges.
    bootstrap = f"""
from pathlib import Path
link, target = Path({json.dumps(str(link))}), Path({json.dumps(str(target))})
original_resolve, original_lexists = Path.resolve, os.path.lexists
def resolve(self, *args, **kwargs):
    return target if self == link else original_resolve(self, *args, **kwargs)
def lexists(path):
    return True if Path(path) == link else original_lexists(path)
Path.resolve, os.path.lexists = resolve, lexists
"""
    arguments = args if operation == "prepare" else [source]
    result = run(installed_cli, operation, *arguments, "--directory", link, bootstrap=bootstrap)
    assert result.returncode == 2, result.stdout + result.stderr
    assert not target.exists()


def test_rehashed_preparation_still_binds_original_options_before_dispatch(
    installed_cli, paired_material, tmp_path
):
    from backend.evaluation.records import canonical_digest

    _, args, _, _ = paired_material
    directory = tmp_path / "forged"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    value = json.loads(result.stdout)
    value["options"]["max_google_sends"] = 100
    value["content_sha256"] = canonical_digest(
        {k: v for k, v in value.items() if k != "content_sha256"}
    )
    save(directory, "preparation.json", value)
    result = run(installed_cli, "execute", directory, "--approved-sha256", value["content_sha256"])
    assert result.returncode == 2, result.stdout + result.stderr
    assert not (directory / "execution").exists()


def test_cleanup_deadline_keeps_a_stopped_receipt(installed_cli, paired_material, tmp_path):
    root, args, values, _ = paired_material
    values["options"]["total_timeout_seconds"] = 1
    save(root, "options.json", values["options"])
    directory = tmp_path / "slow-close"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    fixture = HTTP_FIXTURE.replace(
        "async def aclose(self): pass",
        "async def aclose(self):\n        import asyncio\n        await asyncio.sleep(1.5)",
    )
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        json.loads(result.stdout)["content_sha256"],
        bootstrap=fixture,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "stopped"
    assert (directory / "execution/receipt.json").is_file()


def test_native_mode_specific_route_prices_support_cold_preparation(
    installed_cli, paired_material, tmp_path
):
    from backend.evaluation.evaluation_transport import ROUTE_MASK

    root, args, values, _ = paired_material
    row = next(row for row in values["prices"]["rows"] if row["price_id"] == "route_matrix")
    row["match"]["billing_context"] = {
        "endpoint": "computeRouteMatrix",
        "field_mask": ROUTE_MASK,
        "travel_mode": "WALK",
        "routing_preference": None,
    }
    save(root, "prices.json", values["prices"])
    directory = tmp_path / "priced"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        json.loads(result.stdout)["content_sha256"],
        bootstrap=HTTP_FIXTURE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert run(installed_cli, "replay", directory).returncode == 0


def test_final_only_or_wrong_phase_cache_cannot_be_relabeled(
    installed_cli, paired_material, tmp_path
):
    _, args, _, _ = paired_material
    source = tmp_path / "acquired"
    result = run(installed_cli, "prepare", *args, "--directory", source)
    assert result.returncode == 0, result.stdout + result.stderr
    result = run(
        installed_cli,
        "execute",
        source,
        "--approved-sha256",
        json.loads(result.stdout)["content_sha256"],
        bootstrap=HTTP_FIXTURE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    identity = source / "execution/identity-snapshot"
    result = run(
        installed_cli,
        "prepare",
        *args,
        "--directory",
        tmp_path / "wrong",
        "--identity-snapshot",
        identity,
        "--snapshot",
        identity,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    native = json.loads((source / "execution/evidence-snapshot/manifest.json").read_bytes())
    native["plan"]["paired"] = False
    save(source / "execution/evidence-snapshot", "manifest.json", native)
    result = run(
        installed_cli,
        "prepare",
        *args,
        "--directory",
        tmp_path / "final-only",
        "--identity-snapshot",
        identity,
        "--snapshot",
        source / "execution/evidence-snapshot",
    )
    assert result.returncode == 2, result.stdout + result.stderr


def test_per_call_deadline_keeps_unknown_units_without_retry(
    installed_cli, paired_material, tmp_path
):
    root, args, values, _ = paired_material
    values["options"]["timeout_seconds"] = 0.02
    save(root, "options.json", values["options"])
    directory = tmp_path / "timeouts"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads(result.stdout)
    fixture = (
        HTTP_FIXTURE
        + """
import asyncio
async def slow(self, *args, **kwargs): await asyncio.sleep(1)
FixtureClient.request = slow
"""
    )
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        prepared["content_sha256"],
        bootstrap=fixture,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["usage"]["actual_google_sends"] == 4
    assert report["usage"]["retries"] == 0
    assert report["evidence_status"] == "partial"
    assert run(installed_cli, "replay", directory).returncode == 0


def test_final_report_deadline_cannot_claim_complete_after_synchronous_work(
    installed_cli, paired_material, tmp_path
):
    _, args, _, _ = paired_material
    directory = tmp_path / "late-report"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads(result.stdout)
    fixture = (
        HTTP_FIXTURE
        + """
from pathlib import Path
import time
original_monotonic, original_write = time.monotonic, Path.write_bytes
offset = 0
def monotonic(): return original_monotonic() + offset
def write_bytes(self, data):
    global offset
    result = original_write(self, data)
    if self.name == 'pair-report.json': offset = 120
    return result
time.monotonic, Path.write_bytes = monotonic, write_bytes
"""
    )
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        prepared["content_sha256"],
        bootstrap=fixture,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["processing_status"] == "stopped"
    assert report["reason"] == "execution_timeout"
    assert report["usage"]["actual_google_sends"] == 7
    assert (directory / "execution/receipt.json").is_file()


def test_client_cleanup_failure_retains_receipt_and_observed_usage(
    installed_cli, paired_material, tmp_path
):
    _, args, _, _ = paired_material
    directory = tmp_path / "close"
    result = run(installed_cli, "prepare", *args, "--directory", directory)
    assert result.returncode == 0, result.stdout + result.stderr
    fixture = HTTP_FIXTURE.replace(
        "async def aclose(self): pass",
        "async def aclose(self): raise OSError('fixture close failure')",
    )
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        json.loads(result.stdout)["content_sha256"],
        bootstrap=fixture,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert (directory / "execution/receipt.json").is_file()
    assert json.loads(result.stdout)["usage"]["actual_google_sends"] == 7


def test_exact_cached_pair_reuses_original_evidence_with_zero_current_sends(
    installed_cli, paired_material, tmp_path
):
    _, args, _, _ = paired_material
    source, directory = tmp_path / "acquired", tmp_path / "cached"
    result = run(installed_cli, "prepare", *args, "--directory", source)
    assert result.returncode == 0, result.stdout + result.stderr
    digest = json.loads(result.stdout)["content_sha256"]
    result = run(
        installed_cli, "execute", source, "--approved-sha256", digest, bootstrap=HTTP_FIXTURE
    )
    assert result.returncode == 0, result.stdout + result.stderr
    original = json.loads(result.stdout)
    result = run(
        installed_cli,
        "prepare",
        *args,
        "--directory",
        directory,
        "--identity-snapshot",
        source / "execution/identity-snapshot",
        "--snapshot",
        source / "execution/evidence-snapshot",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    preparation = json.loads(result.stdout)
    assert preparation["request_inventory"]["evidence_status"] == "exact"
    result = run(
        installed_cli,
        "execute",
        directory,
        "--approved-sha256",
        preparation["content_sha256"],
        bootstrap=LOOPBACK_FIXTURE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["usage"]["actual_google_sends"] == 0
    assert report["pair"]["groups"] == original["pair"]["groups"]
    assert run(installed_cli, "replay", directory).returncode == 0
