"""Opt-in independent V3 diagnostics through installed suite command boundaries."""

import json

import pytest

from backend.tests import test_rtpeval_cli as cli_tests
from backend.tests.evaluation import test_v3_pair_report as pair_tests
from backend.tests.evaluation.test_evaluation_run import options, run_prices

pytest_plugins = ("backend.tests.evaluation.test_intake",)
installed_cli = cli_tests.installed_cli
pair_case = pair_tests.pair_case
route_case = pair_tests.route_case
prepared_scenario = pair_tests.prepared_scenario


@pytest.fixture
def pair_suite(pair_case, batch):
    def build(**kwargs):
        case = pair_case(**kwargs)
        root = batch[4]
        files = {
            "identity": case[1].to_dict(),
            "context": case[3],
            "route_reviews": case[4],
            "coordinates": case[5],
            "expected_plan": case[6],
            "options": options(),
            "prices": run_prices(),
        }
        for name, value in files.items():
            (root / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
        pair = {name: name + ".json" for name in files if name not in ("options", "prices")}
        pair["snapshot"] = case[2].relative_to(root).as_posix()
        declaration = {
            "schema_version": "rtpeval_suite_1",
            "suite_id": "pairs",
            "max_cost_usd": "10",
            "cases": [
                {
                    "case_id": "selected",
                    "revision": "1",
                    "manifest": "manifest.json",
                    "options": "options.json",
                    "prices": "prices.json",
                    "tracks": {"pair": pair},
                }
            ],
        }
        source = root / "suite.json"
        source.write_text(json.dumps(declaration), encoding="utf-8")
        return source, root / "suite-run", declaration, case

    return build


def test_explicit_unchanged_no_repair_pair_preserves_native_zero_deltas(pair_suite, installed_cli):
    source, directory, _, _ = pair_suite()
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads((directory / "preparation.json").read_bytes())
    report = next(
        value
        for value in prepared["track_configuration"]["artifacts"].values()
        if value["schema_version"] == "rtpeval_v3_pair_report_2"
    )
    pair = report["groups"][0]
    assert pair["pair_status"] == "available"
    assert pair["deltas"]["auxiliary_total"]["percentage_points"] == 0
    assert pair["deltas"]["auxiliary_total"]["exact_fraction"] == {"numerator": 0, "denominator": 1}
    assert pair["included_dimensions"] == ["grounding", "non_overlap", "opening", "routes"]
    assert not list(directory.rglob("started.json"))


def test_changed_pair_reports_native_signed_loss_and_regression(pair_suite, installed_cli):
    def overlap(itinerary):
        itinerary["days"][0]["activities"][1].update(
            start_time="2020-01-01T09:30:00Z", end_time="2020-01-01T10:30:00Z"
        )

    source, directory, declaration, _ = pair_suite(
        after=overlap,
        edits=[
            pair_tests.edit(
                "retime", "b", start_time="2020-01-01T09:30:00Z", end_time="2020-01-01T10:30:00Z"
            )
        ],
    )
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((directory / "tracks/0001/pair.json").read_bytes())
    native = installed_cli(
        "pair",
        "report",
        source.parent / "manifest.json",
        source.parent / "identity.json",
        source.parent / declaration["cases"][0]["tracks"]["pair"]["snapshot"],
        "--context",
        source.parent / "context.json",
        "--route-reviews",
        source.parent / "route_reviews.json",
        "--coordinates",
        source.parent / "coordinates.json",
        "--expected-plan",
        source.parent / "expected_plan.json",
        "--generated-at",
        report["generated_at"],
        evaluation_offline=True,
    )
    assert native.returncode == 0, native.stdout + native.stderr
    assert json.loads(native.stdout)["groups"] == report["groups"]
    pair = report["groups"][0]
    assert pair["deltas"]["dimensions"]["routes"]["counts"] == {"FAIL": 0, "PASS": -1, "UNKNOWN": 1}
    assert pair["deltas"]["auxiliary_total"]["percentage_points"] is None
    assert any(
        row["transition"] == "introduced_conflict" for row in pair["continuity"]["conflicts"]
    )


def test_explicit_pair_with_missing_evidence_stays_unavailable(pair_suite, installed_cli):
    source, directory, declaration, _ = pair_suite()
    declaration["cases"][0]["tracks"]["pair"] = {}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    preparation = json.loads((directory / "preparation.json").read_bytes())
    row = preparation["track_configuration"]["pair_cases"]["selected"]
    assert row["processing_status"] == "complete"
    assert row["evidence_status"] == "unavailable"
    assert row["reason"] == "pair_material_missing"
    assert row["report"] is None
    assert not any(
        value["schema_version"] == "rtpeval_v3_pair_report_2"
        for value in preparation["track_configuration"]["artifacts"].values()
    )


def test_missing_snapshot_keeps_bound_identity_unavailable(pair_suite, installed_cli):
    source, directory, declaration, _ = pair_suite()
    declaration["cases"][0]["tracks"]["pair"].pop("snapshot")
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    preparation = json.loads((directory / "preparation.json").read_bytes())
    row = preparation["track_configuration"]["pair_cases"]["selected"]
    assert row["evidence_status"] == "unavailable"
    assert row["reason"] == "pair_material_missing"
    assert str(source.parent / "identity.json") in preparation["source_bindings"]
    assert row["report"] is None


@pytest.mark.parametrize(
    "fault", ["identity", "context", "snapshot", "provenance", "expected_plan_missing_snapshot"]
)
def test_supplied_stale_pair_material_rejects_full_preflight(pair_suite, installed_cli, fault):
    source, directory, declaration, case = pair_suite()
    root = source.parent
    if fault == "snapshot":
        next((case[2] / "raw").glob("*")).write_bytes(b"corrupted")
    elif fault == "provenance":
        declaration["cases"][0]["tracks"]["pair"]["edit_provenance"] = "provenance.json"
        (root / "provenance.json").write_text(
            json.dumps({"schema_version": "rtpeval_v3_edit_provenance_1"}), encoding="utf-8"
        )
    else:
        name = "expected_plan" if fault == "expected_plan_missing_snapshot" else fault
        path = root / (name + ".json")
        value = json.loads(path.read_bytes())
        if fault == "identity":
            value["source_hashes"] = {}
        elif fault == "context":
            value["batch_id"] = "foreign"
        else:
            value["intake_hash"] = "f" * 64
            declaration["cases"][0]["tracks"]["pair"].pop("snapshot")
        path.write_text(json.dumps(value), encoding="utf-8")
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    assert not directory.exists()


@pytest.mark.parametrize("mode", ["complete", "missing", "not_requested", "final_only"])
def test_pair_summary_preserves_four_final_scores_and_offline_replay(
    pair_suite, installed_cli, monkeypatch, capsys, mode
):
    import asyncio

    import httpx

    from backend.cli.rtpeval import main
    from backend.tests.evaluation.test_evaluation_run import mock_provider

    kwargs = {"source_change": pair_tests.no_departure} if mode == "final_only" else {}
    source, directory, declaration, _ = pair_suite(**kwargs)
    if mode == "missing":
        declaration["cases"][0]["tracks"]["pair"] = {}
    elif mode == "not_requested":
        declaration["cases"][0].pop("tracks")
    source.write_text(json.dumps(declaration), encoding="utf-8")
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_provider))
    try:
        assert (
            main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    json.loads(prepared.stdout)["preparation_sha256"],
                ],
                http_client=client,
            )
            == 0
        )
    finally:
        asyncio.run(client.aclose())
    summary = json.loads(capsys.readouterr().out)
    row = summary["cases"][0]
    native_primary = json.loads(
        (directory / "cases/0001/primary/execution/report.json").read_bytes()
    )
    assert row["primary_report"] == native_primary
    assert set(native_primary["quality"]["groups"][0]["versions"]) == {"v0", "v1", "v2", "v3"}
    pair = row["tracks"]["pair"]
    assert pair["processing_status"] == ("not_requested" if mode == "not_requested" else "complete")
    assert pair["evidence_status"] == ("available" if mode == "complete" else "unavailable")
    if mode == "final_only":
        assert pair["native_report"]["groups"][0]["pair_status"] == "pair_unavailable"
        assert pair["native_report"]["groups"][0]["available_stages"] == {
            "draft": False,
            "final_primary": False,
        }
        assert pair["native_report"]["groups"][0]["deltas"] is None
    originals = {p: p.read_bytes() for p in source.parent.rglob("*") if p.is_file()}
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == summary
    assert {p: p.read_bytes() for p in originals} == originals
    if mode == "complete":
        (directory / pair["report"]).write_text("{}", encoding="utf-8")
        corrupt = installed_cli("suite", "replay", directory, evaluation_offline=True)
        assert corrupt.returncode == 2, corrupt.stdout + corrupt.stderr
        assert json.loads(corrupt.stdout)["processing_status"] == "needs_material_correction"


def test_supplied_null_pair_configuration_is_not_implicit_opt_out(pair_suite, installed_cli):
    source, directory, declaration, _ = pair_suite()
    declaration["cases"][0]["tracks"]["pair"] = None
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not directory.exists()


@pytest.mark.parametrize("changed", ["identity", "snapshot_raw"])
def test_pair_original_source_drift_blocks_before_first_provider_send(
    pair_suite, installed_cli, changed
):
    source, directory, _, case = pair_suite()
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    path = (
        source.parent / "identity.json"
        if changed == "identity"
        else next((case[2] / "raw").glob("*"))
    )
    path.write_bytes(path.read_bytes() + b" ")
    result = installed_cli(
        "suite",
        "execute",
        directory,
        "--approved-sha256",
        json.loads(prepared.stdout)["preparation_sha256"],
        evaluation_offline=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "sources changed" in json.loads(result.stdout)["reason"]
    assert not list(directory.rglob("started.json"))


@pytest.mark.parametrize("fault", ["context", "expected_plan"])
def test_final_only_unavailable_pair_still_rejects_supplied_stale_context(
    pair_suite, installed_cli, fault
):
    source, directory, declaration, _ = pair_suite(source_change=pair_tests.no_departure)
    declaration["cases"][0]["tracks"]["pair"].pop("snapshot")
    source.write_text(json.dumps(declaration), encoding="utf-8")
    path = source.parent / (fault + ".json")
    value = json.loads(path.read_bytes())
    value["batch_id" if fault == "context" else "intake_hash"] = "foreign"
    path.write_text(json.dumps(value), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not directory.exists()
