"""Formal evaluation entry points use immutable synthetic inputs and mocked HTTP."""

import asyncio
import copy
import hashlib
import io
import json
import subprocess
import sys

import httpx
import pytest

from backend.tests.evaluation.test_cost_report import prices

pytest_plugins = ("backend.tests.evaluation.test_intake",)


def options():
    return {
        "max_google_sends": 50,
        "max_cost_usd": "10",
        "timeout_seconds": 5,
        "total_timeout_seconds": 60,
        "model": "fixture-model",
        "model_endpoint": "https://model.example.test/openai/v1/",
        "max_input_tokens": 18000,
        "max_output_tokens": 3000,
    }


@pytest.mark.parametrize("effort", [None, "low", "medium"])
def test_cli_freezes_sends_and_replays_identity_effort(batch, capsys, effort):
    from backend.evaluation.evaluation_run_cli import main

    _, _, write, _, root = batch
    configured = options()
    if effort is not None:
        configured["reasoning_effort"] = effort
    (root / "options.json").write_text(json.dumps(configured), encoding="utf-8")
    (root / "prices.json").write_text(json.dumps(run_prices()), encoding="utf-8")
    directory = root / "evaluation"
    assert (
        main(
            [
                "prepare",
                str(write()),
                "--directory",
                str(directory),
                "--options",
                str(root / "options.json"),
                "--prices",
                str(root / "prices.json"),
            ]
        )
        == 0
    )
    preparation = json.loads((directory / "preparation.json").read_bytes())
    seen = []

    def respond(request):
        if request.url.host == "model.example.test":
            seen.append(json.loads(request.content)["reasoning"])
        return mock_provider(request)

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
        patch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        try:
            assert (
                main(
                    ["execute", str(directory), "--approved-sha256", preparation["content_sha256"]],
                    http_client=client,
                )
                == 0
            )
        finally:
            asyncio.run(client.aclose())
    assert seen == [{"effort": effort or "low"}]
    assert main(["replay", str(directory)]) == 0
    if effort is None:
        assert "reasoning_effort" not in preparation["options"]
    else:
        assert preparation["options"]["reasoning_effort"] == effort
    capsys.readouterr()
    if effort == "medium":
        execution = directory / "execution"
        journal_path = next(
            path
            for path in (execution / "http").glob("*.json")
            if json.loads(path.read_bytes())["provider"] == "azure_foundry"
        )
        journal = json.loads(journal_path.read_bytes())
        journal["request"]["json"]["reasoning"] = {"effort": "low"}
        journal_path.write_text(json.dumps(journal), encoding="utf-8")
        receipt_path = execution / "receipt.json"
        receipt = json.loads(receipt_path.read_bytes())
        receipt["files"][str(journal_path.relative_to(execution))] = hashlib.sha256(
            journal_path.read_bytes()
        ).hexdigest()
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        assert main(["replay", str(directory)]) == 2
        assert "Model HTTP receipt differs" in capsys.readouterr().out


@pytest.mark.parametrize("effort", ["", "unexpected", None, 1, {"effort": "medium"}])
def test_prepare_rejects_invalid_identity_effort_without_execution(batch, effort):
    from backend.evaluation.evaluation_run import prepare_run

    _, _, write, _, root = batch
    with pytest.raises(ValueError, match="Identity reasoning effort"):
        prepare_run(
            write(),
            root / "evaluation",
            options={**options(), "reasoning_effort": effort},
            prices=run_prices(),
        )
    assert not (root / "evaluation").exists()


def test_prepare_is_offline_and_binds_original_sources(batch):
    from backend.evaluation.evaluation_run import prepare_run

    _, _, write, _, root = batch
    prepared = prepare_run(write(), root / "evaluation", options=options(), prices=prices())
    assert prepared["status"] == "prepared"
    assert prepared["intake"]["status"] == "accepted"
    assert prepared["identity_plan"]["phase"] == "identity"
    assert not (root / "evaluation" / "execution").exists()
    saved = json.loads((root / "evaluation" / "preparation.json").read_bytes())
    assert saved == prepared


def run_prices():
    book = prices()
    book["rows"] = [
        {
            "price_id": operation,
            "source": "https://example.test/official",
            "as_of": "2026-10-08",
            "valid_from": "2020-01-01",
            "valid_until": "2030-01-01",
            "match": {"kind": "provider", "provider": "google", "operation": operation},
            "rates": {"requests": "0.03"},
            "per": "1",
        }
        for operation in ("places_search", "place_details", "route_matrix")
    ]
    book["rows"].append(
        {
            "price_id": "model",
            "source": "https://example.test/official",
            "as_of": "2026-10-08",
            "valid_from": "2020-01-01",
            "valid_until": "2030-01-01",
            "match": {
                "kind": "model",
                "provider": "azure_foundry",
                "operation": "identity",
                "model": "fixture-model",
            },
            "rates": {
                "input_tokens": "1",
                "cached_input_tokens": "1",
                "cache_write_input_tokens": "1",
                "output_tokens": "1",
            },
            "per": "1000000",
        }
    )
    subject_row = copy.deepcopy(book["rows"][-1])
    subject_row["price_id"] = "requirement-subject"
    subject_row["match"]["operation"] = "requirement_subject"
    book["rows"].append(subject_row)
    return book


def mock_provider(request):
    def place(name):
        return {
            "id": "pid-" + name[-1].lower(),
            "displayName": {"text": name},
            "formattedAddress": "10 Main St, Example City, Country",
            "businessStatus": "OPERATIONAL",
            "location": {"latitude": 10, "longitude": 20 if name.endswith("A") else 21},
            "timeZone": {"id": "Etc/UTC"},
            "regularOpeningHours": {"periods": [{"open": {"day": 0, "hour": 0, "minute": 0}}]},
        }

    if request.url.host == "model.example.test":
        wire = json.loads(request.content)
        cases = json.loads(wire["input"])["cases"]
        if wire["text"]["format"]["name"] == "RequirementSubjects":
            assert all("version" not in c for c in cases)
        else:
            assert {c["version"] for c in cases} == {"v0"}
            assert all(c["kind"] == "primary_visit" for c in cases)
        rows = [
            {
                "reference_id": c["reference_id"],
                "decision": "match" if c["candidates"] else "unknown",
                "candidate_id": c["candidates"][0]["place_id"] if c["candidates"] else None,
                "rationale": "Supplied independent name and address identify the venue.",
                "evidence_fields": [
                    "claim.place_name",
                    "claim.destination",
                    "candidate.display_name",
                    "candidate.formatted_address",
                ]
                if c["candidates"]
                else [],
                "address_assessment": "not_supplied",
                "destination_assessment": "consistent",
            }
            for c in cases
        ]
        return httpx.Response(
            200,
            json={
                "id": "model-response",
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
                                    {"decisions": {row["reference_id"]: row for row in rows}}
                                ),
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "total_tokens": 120,
                    "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                },
            },
        )
    if request.url.path.endswith("searchText"):
        name = "Museum A" if "Museum A" in json.loads(request.content)["textQuery"] else "Museum B"
        return httpx.Response(200, json={"places": [place(name)]})
    if request.url.host == "places.googleapis.com":
        mask = request.headers["X-Goog-FieldMask"]
        assert "displayName" in mask and "timeZone" in mask and "regularOpeningHours" in mask
        return httpx.Response(
            200, json=place("Museum A" if request.url.path.endswith("pid-a") else "Museum B")
        )
    assert request.url.host == "routes.googleapis.com"
    wire = json.loads(request.content)
    assert wire["travelMode"] == "WALK" and "departureTime" not in wire
    return httpx.Response(
        200,
        json=[
            {
                "originIndex": 0,
                "destinationIndex": 0,
                "status": {},
                "condition": "ROUTE_EXISTS",
                "duration": "600s",
                "distanceMeters": 600,
            }
        ],
    )


@pytest.mark.parametrize("dated_total", [False, True])
def test_execute_and_replay_complete_native_flow_without_regenerating(batch, dated_total):
    from backend.evaluation.evaluation_run import execute_run, prepare_run, replay_run

    manifest, results, write, save, root = batch
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
    if dated_total:
        spec["obligations"] = [
            {
                "obligation_id": "daily-total",
                "kind": "daily_visit_count",
                "resolution": "resolved",
                "date": "2020-01-01",
                "scope": "primary_visits",
                "count": {"mode": "exact", "value": 1},
                "source_refs": [{"field_path": "additional_preferences", "quote": "architecture"}],
            }
        ]
    manifest["groups"][0]["requirement_spec_ref"] = save(
        "requirements.json", spec, spec["schema_version"]
    )
    results["v0"]["itinerary"]["days"][0]["activities"][1]["transport"] = {
        "mode": "WALK",
        "from_activity_id": "a",
        "to_activity_id": "b",
    }
    write("v0")
    preparation = prepare_run(write(), root / "evaluation", options=options(), prices=run_prices())
    originals = {p: p.read_bytes() for p in root.glob("v*.json")}
    calls = []

    def respond(request):
        calls.append(request)
        return mock_provider(request)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic-google",
                model_api_key="synthetic-model",
                http_client=client,
            )

    report = asyncio.run(execute())
    assert (
        report["reports"]["requirement_schedule"]["rules_version"]
        == "rtpeval_requirement_schedule_rules_6"
    )
    assert report["processing_status"] == "complete"
    assert report["acquisition_status"] == "complete"
    assert {u["version"] for u in report["unknowns"] if u["stage"] == "daily_density"} == {
        "v0",
        "v1",
        "v2",
        "v3",
    }
    assert all("request" not in event for event in report["usage"]["raw"]["provider_events"])
    assert report["usage"]["actual_google_sends"] == 5
    assert report["usage"]["actual_model_sends"] == (1 if dated_total else 2)
    assert len(report["quality"]["groups"][0]["versions"]) == 4
    assert report[
        "unknowns"
    ]  # Missing declared API IDs are FAIL; unavailable routes remain UNKNOWN.
    assert replay_run(root / "evaluation") == report
    assert len(calls) == (6 if dated_total else 7)
    assert all(p.read_bytes() == raw for p, raw in originals.items())
    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.evaluation.evaluation_run_cli",
            "replay",
            str(root / "evaluation"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert cli.returncode == 0, cli.stderr
    assert json.loads(cli.stdout) == report


def test_actual_cli_prepares_executes_and_replays(batch, capsys, monkeypatch):
    from backend.evaluation.evaluation_run_cli import main

    _, _, write, _, root = batch
    (root / "options.json").write_text(json.dumps(options()), encoding="utf-8")
    (root / "prices.json").write_text(json.dumps(run_prices()), encoding="utf-8")
    directory = root / "evaluation"
    assert (
        main(
            [
                "prepare",
                str(write()),
                "--directory",
                str(directory),
                "--options",
                str(root / "options.json"),
                "--prices",
                str(root / "prices.json"),
            ]
        )
        == 0
    )
    capsys.readouterr()
    preparation = json.loads((directory / "preparation.json").read_bytes())
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_provider))
    assert (
        main(
            ["execute", str(directory), "--approved-sha256", preparation["content_sha256"]],
            http_client=client,
        )
        == 0
    )
    capsys.readouterr()
    assert main(["replay", str(directory)]) == 0
    assert json.loads(capsys.readouterr().out)["processing_status"] == "complete"
    asyncio.run(client.aclose())


def test_completed_cli_report_survives_gbk_stdout(batch, monkeypatch):
    from backend.evaluation.evaluation_run import prepare_run, verify_receipt
    from backend.evaluation.evaluation_run_cli import main

    _, _, write, _, root = batch
    directory = root / "evaluation"
    preparation = prepare_run(write(), directory, options=options(), prices=run_prices())
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")

    def respond(request):
        response = mock_provider(request)
        if request.url.host == "model.example.test":
            raw = response.json()
            content = raw["output"][0]["content"][0]
            wire = json.loads(content["text"])
            for row in wire["decisions"].values():
                row["rationale"] = "Independent match at Montju\u00efc."
            content["text"] = json.dumps(wire)
            return httpx.Response(200, json=raw)
        return response

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    buffer = io.BytesIO()
    output = io.TextIOWrapper(buffer, encoding="gbk", errors="strict")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(sys, "stdout", output)
            exit_code = main(
                ["execute", str(directory), "--approved-sha256", preparation["content_sha256"]],
                http_client=client,
            )
            output.flush()
        emitted = json.loads(buffer.getvalue().decode("gbk"))
        saved = json.loads((directory / "execution" / "report.json").read_bytes())
        assert exit_code == 0 and emitted == saved
        assert emitted["processing_status"] == "complete"
        assert "Montju\u00efc" in json.dumps(emitted, ensure_ascii=False)
        verify_receipt(directory / "execution", preparation["content_sha256"])
    finally:
        output.close()
        asyncio.run(client.aclose())


def test_missing_activity_review_remains_blocked_with_gbk_stdout(batch, monkeypatch):
    from backend.evaluation.evaluation_run_cli import main

    _, results, write, _, root = batch
    activity = results["v1"]["itinerary"]["days"][0]["activities"][0]
    activity.update(
        activity_kind="generic_activity",
        title="Montju\u00efc pause",
        place_name=None,
        notes="Independent role and occupancy decisions are missing.",
    )
    manifest = write("v1")
    (root / "options.json").write_text(json.dumps(options()), encoding="utf-8")
    (root / "prices.json").write_text(json.dumps(run_prices()), encoding="utf-8")
    directory = root / "blocked"

    def forbidden_client(*args, **kwargs):
        pytest.fail("Missing reviews must stop before HTTP client construction")

    buffer = io.BytesIO()
    output = io.TextIOWrapper(buffer, encoding="gbk", errors="strict")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(sys, "stdout", output)
            patch.setattr(httpx, "AsyncClient", forbidden_client)
            code = main(
                [
                    "prepare",
                    str(manifest),
                    "--directory",
                    str(directory),
                    "--options",
                    str(root / "options.json"),
                    "--prices",
                    str(root / "prices.json"),
                ]
            )
            output.flush()
        emitted = json.loads(buffer.getvalue().decode("gbk"))
        assert code == 2 and emitted["processing_status"] == "needs_semantic_review"
        assert emitted["semantic_readiness"]["status"] == "needs_semantic_review"
        assert "Montju\u00efc" in json.dumps(emitted, ensure_ascii=False)
        assert not directory.exists()
    finally:
        output.close()


def test_population_resolution_remains_blocked_with_gbk_stdout(batch, monkeypatch):
    from backend.evaluation import evaluation_run_cli
    from backend.evaluation.declared_population import UnreadyPopulation

    _, _, write, _, root = batch
    manifest = write()
    (root / "options.json").write_text(json.dumps(options()), encoding="utf-8")
    (root / "prices.json").write_text(json.dumps(run_prices()), encoding="utf-8")
    directory = root / "unready-population"
    readiness = {
        "status": "needs_population_resolution",
        "diagnostics": [{"claim": "Montju\u00efc interval", "reason": "activity_date_unresolved"}],
    }

    def unready(*args, **kwargs):
        raise UnreadyPopulation(readiness)

    def forbidden_client(*args, **kwargs):
        pytest.fail("Unresolved population must stop before HTTP client construction")

    buffer = io.BytesIO()
    output = io.TextIOWrapper(buffer, encoding="gbk", errors="strict")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(sys, "stdout", output)
            patch.setattr(evaluation_run_cli, "prepare_run", unready)
            patch.setattr(httpx, "AsyncClient", forbidden_client)
            code = evaluation_run_cli.main(
                [
                    "prepare",
                    str(manifest),
                    "--directory",
                    str(directory),
                    "--options",
                    str(root / "options.json"),
                    "--prices",
                    str(root / "prices.json"),
                    "--quality-profile",
                    "rtpeval_declared_population_1",
                ]
            )
            output.flush()
        emitted = json.loads(buffer.getvalue().decode("gbk"))
        assert code == 2 and emitted["processing_status"] == "needs_population_resolution"
        assert emitted["population_readiness"] == readiness
        assert not directory.exists()
    finally:
        output.close()


def test_cli_requests_each_owned_identity_once_and_replays_exact_material(
    batch, capsys, monkeypatch
):
    from backend.evaluation.evaluation_run_cli import main

    _, results, write, _, root = batch
    results["v0"]["itinerary"]["days"][0]["activities"][0]["location"] = (
        "10 Main St, Example City, Country"
    )
    write("v0")
    (root / "options.json").write_text(json.dumps(options()), encoding="utf-8")
    (root / "prices.json").write_text(json.dumps(run_prices()), encoding="utf-8")
    directory = root / "evaluation"
    assert (
        main(
            [
                "prepare",
                str(write()),
                "--directory",
                str(directory),
                "--options",
                str(root / "options.json"),
                "--prices",
                str(root / "prices.json"),
            ]
        )
        == 0
    )
    capsys.readouterr()
    preparation = json.loads((directory / "preparation.json").read_bytes())
    sent = []

    def respond(request):
        response = mock_provider(request)
        if request.url.host != "model.example.test":
            return response
        wire = json.loads(request.content)
        sent.append(wire)
        schema = wire["text"]["format"]["schema"]
        coverage = schema["properties"]["decisions"]
        assert coverage["type"] == "object"
        assert coverage["required"] == ["r01", "r02"]
        assert set(coverage["properties"]) == {"r01", "r02"}
        assert coverage["additionalProperties"] is False
        assert schema["$defs"]["WithAddress"]["properties"]["reference_id"]["enum"] == ["r01"]
        assert schema["$defs"]["WithoutAddress"]["properties"]["address_assessment"]["enum"] == [
            "not_supplied"
        ]
        raw = response.json()
        rows = list(json.loads(raw["output"][0]["content"][0]["text"])["decisions"].values())
        rows[0]["address_assessment"] = "equivalent"
        rows[0]["evidence_fields"].append("claim.location")
        raw["output"][0]["content"][0]["text"] = json.dumps(
            {"decisions": {row["reference_id"]: row for row in rows}}
        )
        return httpx.Response(200, json=raw)

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(
                ["execute", str(directory), "--approved-sha256", preparation["content_sha256"]],
                http_client=client,
            )
            == 0
        )
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert report["processing_status"] == "complete"
    assert len(sent) == 1
    saved = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    monkeypatch.setattr(
        "socket.create_connection", lambda *a, **k: pytest.fail("Network in replay")
    )
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: pytest.fail("DNS in replay"))
    assert main(["replay", str(directory)]) == 0
    assert json.loads(capsys.readouterr().out) == report
    assert all(p.read_bytes() == raw for p, raw in saved.items())


@pytest.mark.parametrize(
    "fault",
    ["missing", "duplicate_reference", "foreign_key", "duplicate_key", "array", "candidate"],
)
def test_cli_stops_invalid_identity_coverage_without_retry_and_replays_raw_response(
    batch, fault, capsys, monkeypatch
):
    from backend.evaluation.evaluation_run import prepare_run
    from backend.evaluation.evaluation_run_cli import main

    _, _, write, _, root = batch
    directory = root / "evaluation"
    preparation = prepare_run(write(), directory, options=options(), prices=run_prices())
    sent, received = [], []

    def respond(request):
        response = mock_provider(request)
        if request.url.host != "model.example.test":
            return response
        sent.append(json.loads(request.content))
        raw = response.json()
        content = raw["output"][0]["content"][0]
        wire = json.loads(content["text"])
        rows = wire["decisions"]
        if fault == "missing":
            rows.pop("r02")
        elif fault == "duplicate_reference":
            rows["r02"]["reference_id"] = "r01"
        elif fault == "foreign_key":
            rows["r99"] = rows.pop("r02")
            rows["r99"]["reference_id"] = "r99"
        elif fault == "array":
            wire["decisions"] = list(rows.values())
        elif fault == "candidate":
            rows["r01"]["candidate_id"] = rows["r02"]["candidate_id"]
        content["text"] = json.dumps(wire)
        if fault == "duplicate_key":
            content["text"] = (
                '{"decisions":{"r01":'
                + json.dumps(rows["r01"])
                + (',"r01":' + json.dumps(rows["r02"]) + "}}")
            )
        response = httpx.Response(200, json=raw)
        received.append(response.content)
        return response

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(
                ["execute", str(directory), "--approved-sha256", preparation["content_sha256"]],
                http_client=client,
            )
            == 2
        )
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert report["processing_status"] == "stopped"
    assert report["usage"]["actual_model_sends"] == len(sent) == 1
    assert report["usage"]["retries"] == 0
    execution = directory / "execution"
    assert not (execution / "identity-report.json").exists()
    journal_path = next(
        p
        for p in (execution / "http").glob("*.json")
        if json.loads(p.read_bytes())["provider"] == "azure_foundry"
    )
    journal = json.loads(journal_path.read_bytes())
    assert journal["request"]["json"] == sent[0]
    assert journal_path.with_suffix(".bin").read_bytes() == received[0]
    saved = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: pytest.fail("DNS in replay"))
    monkeypatch.setattr(
        "socket.create_connection", lambda *a, **k: pytest.fail("Network in replay")
    )
    assert main(["replay", str(directory)]) == 2
    assert json.loads(capsys.readouterr().out) == report
    assert all(p.read_bytes() == raw for p, raw in saved.items())


@pytest.mark.parametrize("mode", ["WALK", "DRIVE", "TRANSIT"])
def test_independent_program_versions_keep_directed_original_route_context(batch, mode):
    from backend.evaluation.evaluation_run import execute_run, prepare_run, replay_run

    _, results, write, _, root = batch
    results["v0"]["itinerary"]["days"][0]["activities"][1]["transport"] = {
        "mode": mode,
        "from_activity_id": "a",
        "to_activity_id": "b",
    }
    write("v0")
    for version in ("v1", "v2", "v3"):
        itinerary = results[version]["itinerary"]
        activities = itinerary["days"][0]["activities"]
        itinerary["days"][0]["activities"] = [activities[0], activities[2]]
        activities[0]["source_place_id"] = "pid-a"
        activities[2]["source_place_id"] = "pid-b"
        activities[0]["location"] = "10 Main St, Example City, Country"
        activities[2]["location"] = "10 Main St, Example City, Country"
        itinerary["transfers"] = [
            {
                "from_activity_id": "a",
                "to_activity_id": "b",
                "mode": mode,
                "departure_time": "2020-01-01T10:00:00Z",
                "arrival_time": "2020-01-01T10:20:00Z",
            }
        ]
        write(version)
    preparation = prepare_run(write(), root / "evaluation", options=options(), prices=run_prices())
    routes = []

    def respond(request):
        if request.url.host != "routes.googleapis.com":
            return mock_provider(request)
        body = json.loads(request.content)
        routes.append(body)
        assert body["travelMode"] == mode
        assert body["origins"][0]["waypoint"]["location"]["latLng"]["longitude"] == 20
        assert body["destinations"][0]["waypoint"]["location"]["latLng"]["longitude"] == 21
        if mode == "TRANSIT":
            assert body["departureTime"] == "2020-01-01T10:00:00+00:00"
        else:
            assert "departureTime" not in body
        if mode == "DRIVE":
            assert body["routingPreference"] == "TRAFFIC_UNAWARE"
        return httpx.Response(
            200,
            json=[
                {
                    "originIndex": 0,
                    "destinationIndex": 0,
                    "status": {},
                    "condition": "ROUTE_EXISTS",
                    "duration": "600s",
                    "distanceMeters": 600,
                }
            ],
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic-google",
                model_api_key="synthetic-model",
                http_client=client,
            )

    report = asyncio.run(execute())
    assert report["processing_status"] == "complete"
    assert len(routes) == 1  # One request, four independently retained directed verdicts.
    assert report["usage"]["actual_google_sends"] == 9
    assert all(
        row["grounding_verdict"] == "PASS"
        for row in report["reports"]["identity"]["records"]
        if row["projection"] == "final"
    )
    assert len(report["reports"]["routes"]["results"]) == 4
    assert replay_run(root / "evaluation") == report


@pytest.mark.parametrize(
    "failure", ["google_http", "model_connection", "cost_limit", "source_drift", "runtime_failure"]
)
def test_failures_remain_recorded_and_never_retry_or_reuse_attempt(batch, failure):
    from backend.evaluation.evaluation_run import execute_run, prepare_run, replay_run

    _, _, write, _, root = batch
    configured = options()
    if failure == "cost_limit":
        configured["max_cost_usd"] = "0.0001"
    preparation = prepare_run(write(), root / "evaluation", options=configured, prices=run_prices())
    calls = []
    if failure == "source_drift":
        (root / "v0.json").write_text("{}", encoding="utf-8")

    def respond(request):
        calls.append(request)
        if failure == "google_http" and request.url.host == "places.googleapis.com":
            return httpx.Response(500, json={"error": "synthetic"})
        if failure == "model_connection" and request.url.host == "model.example.test":
            raise httpx.ConnectError("synthetic", request=request)
        if failure == "runtime_failure" and request.url.host == "model.example.test":
            raise RuntimeError("Synthetic dependency failure")
        return mock_provider(request)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic-google",
                model_api_key="synthetic-model",
                http_client=client,
            )

    if failure == "source_drift":
        with pytest.raises(ValueError, match="sources changed"):
            asyncio.run(execute())
        assert not calls and not (root / "evaluation" / "execution").exists()
        return
    report = asyncio.run(execute())
    assert report["acquisition_status"] == "partial"
    assert replay_run(root / "evaluation") == report
    with pytest.raises(FileExistsError):
        asyncio.run(execute())
    if failure == "google_http":
        assert report["processing_status"] == "complete" and report["unknowns"]
        assert len(calls) == 3  # Two distinct searches and exactly one V0 model call.
        unknown = next(
            u for u in report["unknowns"] if u["stage"] == "identity" and u["version"] == "v0"
        )
        assert any(e["reason"] == "http_error" for e in unknown["acquisition"])
        assert all(e["request_key"] for e in unknown["acquisition"])
    else:
        assert report["processing_status"] == "stopped"
        assert len(calls) == (3 if failure in ("model_connection", "runtime_failure") else 0)
        assert report["usage"]["actual_billing"] is None
        cost = report["usage"]["cost"]["runs"][0]
        if failure in ("model_connection", "runtime_failure"):
            assert cost["estimated_total"] is None and cost["unpriced_event_count"] > 0
        else:
            assert cost["estimated_total"] == "0"


def test_total_deadline_preserves_started_attempt_with_zero_retry(batch):
    from backend.evaluation.evaluation_run import execute_run, prepare_run, replay_run

    _, _, write, _, root = batch
    configured = options()
    configured["total_timeout_seconds"] = 0.02
    preparation = prepare_run(write(), root / "evaluation", options=configured, prices=run_prices())
    calls = []

    async def respond(request):
        calls.append(request)
        await asyncio.sleep(1)
        return mock_provider(request)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic-google",
                model_api_key="synthetic-model",
                http_client=client,
            )

    report = asyncio.run(execute())
    assert report["processing_status"] == "stopped"
    assert report["error_type"] == "TimeoutError"
    assert len(calls) == 1
    assert report["usage"]["actual_google_sends"] == 1
    assert report["usage"]["actual_model_sends"] == 0
    assert replay_run(root / "evaluation") == report


def test_replay_rejects_model_material_detached_from_captured_http_bytes(batch):
    from backend.evaluation.evaluation_run import execute_run, prepare_run, replay_run

    _, _, write, _, root = batch
    preparation = prepare_run(write(), root / "evaluation", options=options(), prices=run_prices())

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic-google",
                model_api_key="synthetic-model",
                http_client=client,
            )

    assert asyncio.run(execute())["processing_status"] == "complete"
    execution = root / "evaluation" / "execution"
    receipt = json.loads((execution / "receipt.json").read_bytes())
    event = next(
        json.loads(p.read_bytes())
        for p in (execution / "http").glob("*.json")
        if json.loads(p.read_bytes())["provider"] == "azure_foundry"
    )
    raw_path = execution / "http" / (event["event_id"] + ".bin")
    raw_path.write_bytes(b'{"status":"failed","output":[]}')
    receipt["files"][str(raw_path.relative_to(execution))] = hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()
    (execution / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="Model HTTP receipt"):
        replay_run(root / "evaluation")
