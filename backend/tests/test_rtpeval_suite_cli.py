"""Suite lifecycle acceptance at the installed command and external HTTP boundary."""

import asyncio
import hashlib
import json
import shutil

import httpx
import pytest

from backend.cli.rtpeval import main
from backend.tests import test_rtpeval_cli as cli_tests
from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices

installed_cli = cli_tests.installed_cli


@pytest.mark.parametrize("leaf", [None, "prepare", "execute", "replay", "report"])
def test_suite_help_is_lazy_and_describes_operations(installed_cli, leaf):
    args = ["suite", *([leaf] if leaf else []), "--help"]
    result = installed_cli(*args, block_intake=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "offline" in result.stdout.lower() or "online" in result.stdout.lower()


pytest_plugins = ("backend.tests.evaluation.test_intake",)


@pytest.fixture
def suite_material(batch):
    _, _, write, _, root = batch
    write()
    cases = []
    for name in ("first", "second", "third"):
        folder = root / name
        folder.mkdir()
        for path in root.glob("*.json"):
            shutil.copyfile(path, folder / path.name)
        manifest = json.loads((folder / "manifest.json").read_bytes())
        manifest["batch_id"] = name
        for version, run in manifest["groups"][0]["selected_runs"].items():
            run["run_id"] = name + "-" + version
            for key in ("usage_ref", "provenance_ref"):
                path = folder / run[key]["path"]
                value = json.loads(path.read_bytes())
                value["run_id"] = run["run_id"]
                raw = json.dumps(value).encode()
                path.write_bytes(raw)
                run[key]["sha256"] = hashlib.sha256(raw).hexdigest()
        (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (folder / "options.json").write_text(json.dumps(options()), encoding="utf-8")
        (folder / "prices.json").write_text(json.dumps(run_prices()), encoding="utf-8")
        cases.append(
            {
                "case_id": name,
                "revision": "1",
                "manifest": name + "/manifest.json",
                "options": name + "/options.json",
                "prices": name + "/prices.json",
            }
        )
    declaration = {
        "schema_version": "rtpeval_suite_1",
        "suite_id": "synthetic",
        "max_cost_usd": "30",
        "cases": cases,
    }
    path = root / "suite.json"
    path.write_text(json.dumps(declaration), encoding="utf-8")
    return path, root / "suite-run", declaration


def test_complete_offline_preflight_preserves_order_and_native_limits(
    suite_material, installed_cli
):
    source, directory, _ = suite_material
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "prepared"
    preparation = json.loads((directory / "preparation.json").read_bytes())
    assert [row["case_id"] for row in preparation["cases"]] == ["first", "second", "third"]
    assert preparation["reserved_cost_usd"] == "30"
    assert all(row["primary"]["options"]["max_google_sends"] == 50 for row in preparation["cases"])
    assert not list(directory.rglob("started.json"))


def test_multi_case_execution_replays_offline_and_report_refresh_preserves_receipts(
    suite_material, installed_cli, monkeypatch, capsys
):
    source, directory, _ = suite_material
    originals = {p: p.read_bytes() for p in source.parent.rglob("*.json")}
    assert main(["suite", "prepare", str(source), "--directory", str(directory)]) == 0
    prepared = json.loads(capsys.readouterr().out)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    calls = []

    def respond(request):
        calls.append(request)
        return mock_provider(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    prepared["preparation_sha256"],
                ],
                http_client=client,
            )
            == 0
        )
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert report["processing_status"] == "complete"
    assert [r["processing_status"] for r in report["cases"]] == ["complete"] * 3
    assert len(calls) == 18
    assert all(row["primary_report"]["unknowns"] for row in report["cases"])
    assert all('"FAIL"' in json.dumps(row["primary_report"]["quality"]) for row in report["cases"])
    assert report["cases"][0]["tracks"]["pair"]["processing_status"] == "pending"
    receipt = (directory / "receipt.json").read_bytes()
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == report
    refresh = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert refresh.returncode == 0, refresh.stdout + refresh.stderr
    assert json.loads(refresh.stdout)["cases"] == report["cases"]
    assert (directory / "reports/0001/summary.json").is_file()
    assert (directory / "receipt.json").read_bytes() == receipt
    assert {p: p.read_bytes() for p in originals} == originals
    assert (
        main(
            [
                "suite",
                "execute",
                str(directory),
                "--approved-sha256",
                prepared["preparation_sha256"],
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["error_type"] == "FileExistsError"


@pytest.mark.parametrize(
    "fault",
    [
        "allowance",
        "duplicate_case",
        "duplicate_runs",
        "revision",
        "escape",
        "malformed_late",
        "unsupported_track",
    ],
)
def test_full_preflight_rejects_all_invalid_selection_before_execution(
    suite_material, installed_cli, fault
):
    source, directory, declaration = suite_material
    if fault == "allowance":
        declaration["max_cost_usd"] = "20"
    elif fault == "duplicate_case":
        declaration["cases"][1]["case_id"] = "first"
    elif fault == "duplicate_runs":
        declaration["cases"][1]["manifest"] = "first/manifest.json"
    elif fault == "revision":
        declaration["cases"][2]["revision"] = "2"
    elif fault == "escape":
        declaration["cases"][2]["options"] = "../options.json"
    elif fault == "malformed_late":
        (source.parent / "third/options.json").write_text("{", encoding="utf-8")
    else:
        declaration["cases"][2]["tracks"] = {"pair": {"unexpected": True}}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    assert not directory.exists()


@pytest.mark.parametrize("changed", ["options", "result", "manifest", "declaration"])
def test_source_configuration_drift_blocks_every_provider_send(
    suite_material, monkeypatch, capsys, changed
):
    source, directory, _ = suite_material
    assert main(["suite", "prepare", str(source), "--directory", str(directory)]) == 0
    prepared = json.loads(capsys.readouterr().out)
    changed_path = {
        "options": source.parent / "third/options.json",
        "result": source.parent / "third/v0.json",
        "manifest": source.parent / "third/manifest.json",
        "declaration": source,
    }[changed]
    changed_path.write_bytes(changed_path.read_bytes() + b" ")

    def forbidden(request):
        pytest.fail("Changed late-case configuration must block the first provider send")

    client = httpx.AsyncClient(transport=httpx.MockTransport(forbidden))
    try:
        assert (
            main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    prepared["preparation_sha256"],
                ],
                http_client=client,
            )
            == 2
        )
    finally:
        asyncio.run(client.aclose())
    assert "sources changed" in json.loads(capsys.readouterr().out)["reason"]
    assert not list(directory.rglob("started.json"))


def test_stopped_middle_case_preserves_completed_and_unstarted_states(
    suite_material, installed_cli, monkeypatch, capsys
):
    source, directory, _ = suite_material
    assert main(["suite", "prepare", str(source), "--directory", str(directory)]) == 0
    prepared = json.loads(capsys.readouterr().out)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    calls = []
    models = []

    def respond(request):
        calls.append(request)
        if request.url.host == "model.example.test":
            models.append(request)
            if len(models) == 2:
                raise httpx.ConnectError("Synthetic middle-case failure", request=request)
        return mock_provider(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    prepared["preparation_sha256"],
                ],
                http_client=client,
            )
            == 2
        )
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert [row["processing_status"] for row in report["cases"]] == [
        "complete",
        "stopped",
        "unstarted",
    ]
    assert len(calls) == 9
    assert (directory / "cases/0001/primary/execution/receipt.json").is_file()
    assert (directory / "cases/0002/primary/execution/receipt.json").is_file()
    assert not (directory / "cases/0003/primary/execution").exists()
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == report
    (directory / "cases/0001/primary/execution/report.json").write_text("{}", encoding="utf-8")
    corrupt = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert corrupt.returncode == 2
    assert json.loads(corrupt.stdout)["processing_status"] == "needs_material_correction"
