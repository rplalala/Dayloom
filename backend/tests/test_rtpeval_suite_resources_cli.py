"""Default suite tracks through installed CLI and saved native reports."""

import json

import pytest

from backend.tests import test_rtpeval_cli as cli_tests
from backend.tests import test_rtpeval_suite_cli as suite_tests

installed_cli = cli_tests.installed_cli
suite_material = suite_tests.suite_material

pytest_plugins = ("backend.tests.evaluation.test_intake",)


def test_default_prepare_preserves_unavailable_usage_cost_and_trace(suite_material, installed_cli):
    source, directory, _ = suite_material
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    resources = json.loads((directory / "tracks/0001/resources.json").read_bytes())
    assert resources["schema_version"] == "rtpeval_resource_report_1"
    assert resources["groups"][0]["runs"]["v0"]["metrics"]["total_tokens"] is None
    cost = json.loads((directory / "tracks/0001/cost.json").read_bytes())
    assert cost["status"] == "unavailable"
    assert cost["reason"] == "generation_prices_not_supplied"
    assert cost["report"] is None
    mechanism = json.loads((directory / "tracks/0001/mechanism.json").read_bytes())
    assert mechanism["schema_version"] == "rtpeval_mechanism_report_1"
    assert [r["coverage"] for r in mechanism["runs"]] == ["not_applicable"] * 3 + ["unavailable"]
    assert mechanism["runs"][3]["trace_coverage"] == "unavailable"


def _replace_usage(source, version, updates):
    import hashlib

    folder = source.parent / "first"
    manifest = json.loads((folder / "manifest.json").read_bytes())
    ref = manifest["groups"][0]["selected_runs"][version]["usage_ref"]
    path = folder / ref["path"]
    usage = json.loads(path.read_bytes())
    usage.update(updates)
    raw = json.dumps(usage).encode()
    path.write_bytes(raw)
    ref["sha256"] = hashlib.sha256(raw).hexdigest()
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return usage, ref["sha256"]


def test_explicit_generation_prices_keep_partial_usage_and_unpriced_totals(
    suite_material, installed_cli
):
    from backend.tests.evaluation.test_cost_report import prices
    from backend.tests.evaluation.test_cost_report import source as usage_source

    source, directory, declaration = suite_material
    complete = usage_source()["usage"]
    for name in ("group_id", "run_id", "version", "result_sha256"):
        complete.pop(name)
    complete["model_calls"][0]["total_tokens"] = 1200
    _replace_usage(source, "v0", complete)
    partial = usage_source()["usage"]
    for name in ("group_id", "run_id", "version", "result_sha256"):
        partial.pop(name)
    partial["collection_status"] = "partial"
    partial["model_calls"][0]["output_tokens"] = None
    _replace_usage(source, "v1", partial)
    (source.parent / "generation-prices.json").write_text(json.dumps(prices()), encoding="utf-8")
    declaration["cases"][0]["tracks"] = {"resources": {"prices": "generation-prices.json"}}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    resources = json.loads((directory / "tracks/0001/resources.json").read_bytes())
    assert resources["groups"][0]["runs"]["v0"]["metrics"]["total_tokens"] == 1200
    assert resources["groups"][0]["runs"]["v1"]["metrics"]["total_tokens"] is None
    cost = json.loads((directory / "tracks/0001/cost.json").read_bytes())
    assert cost["schema_version"] == "rtpeval_cost_report_1"
    assert cost["runs"][0]["best_available_total"] == "0.0322"
    assert cost["runs"][1]["best_available_total"] is None
    assert cost["runs"][1]["events"][0]["status"] == "unpriced"


def _observation(source, *, content=None):
    from backend.evaluation.records import canonical_digest

    manifest = json.loads((source.parent / "first/manifest.json").read_bytes())
    group = manifest["groups"][0]
    run = group["selected_runs"]["v3"]
    content = content or {
        "events": [
            {
                "event": "v3_repair_round",
                "payload": {"round_index": 1, "status": "ACCEPTED_PARTIAL"},
            }
        ]
    }
    return {
        "group_id": group["group_id"],
        "run_id": run["run_id"],
        "version": "v3",
        "input_sha256": group["input_ref"]["sha256"],
        "result_sha256": run["result_ref"]["sha256"],
        "channel": "trace",
        "content": content,
        "content_sha256": canonical_digest(content),
    }


def test_saved_trace_keeps_partial_observations_without_inferred_denominator(
    suite_material, installed_cli
):
    source, directory, declaration = suite_material
    (source.parent / "observations.json").write_text(
        json.dumps({"records": [_observation(source)]}), encoding="utf-8"
    )
    declaration["cases"][0]["tracks"] = {"mechanism": {"observations": "observations.json"}}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    mechanism = json.loads((directory / "tracks/0001/mechanism.json").read_bytes())
    run = mechanism["runs"][3]
    assert run["trace_coverage"] == "partial"
    assert run["trace_observations"][0]["value"]["status"] == "ACCEPTED_PARTIAL"
    assert run["model_attempts"] is None


@pytest.mark.parametrize("fault", ["content_hash", "foreign_run", "trace_payload"])
def test_bad_optional_observation_rejects_complete_preflight(suite_material, installed_cli, fault):
    source, directory, declaration = suite_material
    observation = _observation(source)
    if fault == "content_hash":
        observation["content_sha256"] = "f" * 64
    elif fault == "foreign_run":
        observation["run_id"] = "another-run"
    else:
        observation = _observation(
            source, content={"events": [{"event": "v3_repair_round", "payload": {}}]}
        )
    (source.parent / "observations.json").write_text(
        json.dumps({"records": [observation]}), encoding="utf-8"
    )
    declaration["cases"][0]["tracks"] = {"mechanism": {"observations": "observations.json"}}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "mechanism" in json.loads(result.stdout)["reason"].lower()
    assert not directory.exists()


@pytest.mark.parametrize("excluded", ["oracle", "frozen_simulation"])
def test_non_generation_usage_is_excluded_from_resource_and_cost_metrics(
    suite_material, installed_cli, excluded
):
    from backend.tests.evaluation.test_cost_report import prices
    from backend.tests.evaluation.test_cost_report import source as usage_source

    source, directory, declaration = suite_material
    usage = usage_source()["usage"]
    for name in ("group_id", "run_id", "version", "result_sha256"):
        usage.pop(name)
    usage["model_calls"][0]["total_tokens"] = 1200
    if excluded == "oracle":
        usage["namespace"] = "oracle"
    else:
        usage["timing"]["scope"] = "frozen_simulation"
    _replace_usage(source, "v0", usage)
    (source.parent / "generation-prices.json").write_text(json.dumps(prices()), encoding="utf-8")
    declaration["cases"][0]["tracks"] = {"resources": {"prices": "generation-prices.json"}}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    resource = json.loads((directory / "tracks/0001/resources.json").read_bytes())
    run = resource["groups"][0]["runs"]["v0"]
    assert run["metrics"]["total_tokens"] is None
    assert run["observed_model_calls"] == 0
    assert run["missing_fields"] == ["generation_usage_excluded:" + excluded]
    cost = json.loads((directory / "tracks/0001/cost.json").read_bytes())
    assert all(run["version"] != "v0" for run in cost["runs"])


def _execute(source, directory, monkeypatch, capsys, *, stop=False):
    import asyncio

    import httpx

    from backend.cli.rtpeval import main
    from backend.tests.evaluation.test_evaluation_run import mock_provider

    assert main(["suite", "prepare", str(source), "--directory", str(directory)]) == 0
    prepared = json.loads(capsys.readouterr().out)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    models = []

    def respond(request):
        if request.url.host == "model.example.test":
            models.append(request)
            if stop and len(models) == 2:
                raise httpx.ConnectError("Synthetic stopped case", request=request)
        return mock_provider(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        status = main(
            [
                "suite",
                "execute",
                str(directory),
                "--approved-sha256",
                prepared["preparation_sha256"],
            ],
            http_client=client,
        )
        assert status == (2 if stop else 0)
    finally:
        asyncio.run(client.aclose())
    return json.loads(capsys.readouterr().out)


def test_default_tracks_survive_stopped_unstarted_primary_and_replay(
    suite_material, installed_cli, monkeypatch, capsys
):
    source, directory, _ = suite_material
    report = _execute(source, directory, monkeypatch, capsys, stop=True)
    assert [case["processing_status"] for case in report["cases"]] == [
        "complete",
        "stopped",
        "unstarted",
    ]
    for case in report["cases"]:
        assert case["tracks"]["resources"]["processing_status"] == "complete"
        assert case["tracks"]["resources"]["evidence_status"] == "unavailable"
        assert case["tracks"]["resources"]["cost_status"] == "unavailable"
        assert case["tracks"]["mechanism"]["processing_status"] == "complete"
        assert case["tracks"]["mechanism"]["evidence_status"] == "unavailable"
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == report


@pytest.mark.parametrize("artifact", ["resources", "cost", "mechanism_preparation", "mechanism"])
def test_corrupt_descriptive_track_cannot_pass_replay(
    suite_material, installed_cli, monkeypatch, capsys, artifact
):
    source, directory, _ = suite_material
    _execute(source, directory, monkeypatch, capsys)
    (directory / f"tracks/0001/{artifact}.json").write_text("{}", encoding="utf-8")
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2, replay.stdout + replay.stderr
    assert json.loads(replay.stdout)["processing_status"] == "needs_material_correction"


@pytest.mark.parametrize("material", ["prices", "observations"])
def test_extension_source_drift_blocks_execution_before_provider_send(
    suite_material, installed_cli, capsys, material
):
    from backend.cli.rtpeval import main
    from backend.tests.evaluation.test_cost_report import prices

    source, directory, declaration = suite_material
    path = source.parent / (material + ".json")
    value = prices() if material == "prices" else {"records": [_observation(source)]}
    path.write_text(json.dumps(value), encoding="utf-8")
    declaration["cases"][0]["tracks"] = {
        "resources" if material == "prices" else "mechanism": {material: path.name}
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    assert main(["suite", "prepare", str(source), "--directory", str(directory)]) == 0
    prepared = json.loads(capsys.readouterr().out)
    path.write_bytes(path.read_bytes() + b" ")
    result = installed_cli(
        "suite",
        "execute",
        directory,
        "--approved-sha256",
        prepared["preparation_sha256"],
        evaluation_offline=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "sources changed" in json.loads(result.stdout)["reason"]
    assert not (directory / "started.json").exists()


def test_report_refresh_preserves_closed_default_tracks(
    suite_material, installed_cli, monkeypatch, capsys
):
    source, directory, _ = suite_material
    report = _execute(source, directory, monkeypatch, capsys)
    originals = {p: p.read_bytes() for p in (directory / "tracks").rglob("*.json")}
    receipt = (directory / "receipt.json").read_bytes()
    refreshed = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert refreshed.returncode == 0, refreshed.stdout + refreshed.stderr
    assert json.loads(refreshed.stdout)["cases"] == report["cases"]
    assert (directory / "receipt.json").read_bytes() == receipt
    assert {p: p.read_bytes() for p in originals} == originals


def test_summary_keeps_observed_partial_usage_and_trace_available(
    suite_material, monkeypatch, capsys
):
    from backend.tests.evaluation.test_cost_report import source as usage_source

    source, directory, declaration = suite_material
    usage = usage_source()["usage"]
    for name in ("group_id", "run_id", "version", "result_sha256"):
        usage.pop(name)
    usage["collection_status"] = "partial"
    _replace_usage(source, "v0", usage)
    (source.parent / "observations.json").write_text(
        json.dumps({"records": [_observation(source)]}), encoding="utf-8"
    )
    declaration["cases"][0]["tracks"] = {"mechanism": {"observations": "observations.json"}}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    report = _execute(source, directory, monkeypatch, capsys)
    assert report["cases"][0]["tracks"]["resources"]["evidence_status"] == "partial"
    assert report["cases"][0]["tracks"]["mechanism"]["evidence_status"] == "partial"


@pytest.mark.parametrize("material", ["prices_array", "bills_object", "trace_event_null"])
def test_malformed_supplied_track_shapes_fail_with_cli_material_diagnostic(
    suite_material, installed_cli, material
):
    from backend.tests.evaluation.test_cost_report import prices

    source, directory, declaration = suite_material
    if material == "trace_event_null":
        value = {"records": [_observation(source, content={"events": [None]})]}
        tracks = {"mechanism": {"observations": "bad-material.json"}}
    else:
        (source.parent / "generation-prices.json").write_text(
            json.dumps(prices()), encoding="utf-8"
        )
        value = [] if material == "prices_array" else {"invalid": True}
        tracks = (
            {"resources": {"prices": "bad-material.json"}}
            if material == "prices_array"
            else {"resources": {"prices": "generation-prices.json", "bills": "bad-material.json"}}
        )
    (source.parent / "bad-material.json").write_text(json.dumps(value), encoding="utf-8")
    declaration["cases"][0]["tracks"] = tracks
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    assert not directory.exists()


@pytest.mark.parametrize("binding", ["valid", "foreign", "unverified"])
def test_generation_bills_require_selected_usage_and_invoice_binding(
    suite_material, installed_cli, binding
):
    from backend.tests.evaluation.test_cost_report import bill, prices
    from backend.tests.evaluation.test_cost_report import source as usage_source

    source, directory, declaration = suite_material
    usage = usage_source()["usage"]
    for name in ("group_id", "run_id", "version", "result_sha256"):
        usage.pop(name)
    saved, digest = _replace_usage(source, "v0", usage)
    invoice = bill(usage_sha256=digest, result_sha256=saved["result_sha256"])
    if binding == "foreign":
        invoice["usage_sha256"] = "f" * 64
    elif binding == "unverified":
        invoice["source"] = ""
    (source.parent / "generation-prices.json").write_text(json.dumps(prices()), encoding="utf-8")
    (source.parent / "bills.json").write_text(json.dumps([invoice]), encoding="utf-8")
    declaration["cases"][0]["tracks"] = {
        "resources": {"prices": "generation-prices.json", "bills": "bills.json"}
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == (0 if binding == "valid" else 2), result.stdout + result.stderr
    if binding == "valid":
        cost = json.loads((directory / "tracks/0001/cost.json").read_bytes())
        assert cost["runs"][0]["best_available_total"] == "0.13"
        assert cost["runs"][0]["actual_observed_subtotal"] == "0.1"
    else:
        assert not directory.exists()
