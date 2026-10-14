"""One-use opening model execution and complete report replay through real CLI."""

import json
import socket

import httpx
import pytest

from backend.evaluation.evaluation_run_cli import main
from backend.evaluation.quality_report_cli import main as quality_cli
from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices
from backend.tests.evaluation.test_opening_judgment import landmarks, material, walks

pytest_plugins = ("backend.tests.evaluation.test_intake",)


def prepare_base(batch, capsys, *, public_landmarks=False):
    _, results, write, _, root = batch
    (landmarks if public_landmarks else walks)(results)
    for version in ("v1", "v2", "v3"):
        visits = results[version]["itinerary"]["days"][0]["activities"]
        visits[0]["source_place_id"] = "pid-a"
        visits[2]["source_place_id"] = "pid-b"
    for version in results:
        write(version)
    directory = root / "evaluation"
    option_path, price_path = root / "options.json", root / "prices.json"
    option_path.write_text(
        json.dumps({**options(), "assess_missing_hours": False}), encoding="utf-8"
    )
    price_path.write_text(json.dumps(run_prices()), encoding="utf-8")
    assert (
        main(
            [
                "prepare",
                str(write()),
                "--directory",
                str(directory),
                "--options",
                str(option_path),
                "--prices",
                str(price_path),
            ]
        )
        == 0
    )
    approved = json.loads(capsys.readouterr().out)["preparation_sha256"]

    def respond(request):
        if public_landmarks and request.url.path.endswith("searchText"):
            query = json.loads(request.content)
            query["textQuery"] = (
                query["textQuery"]
                .replace("City Harbour Bridge", "Museum A")
                .replace("Old Waterfront", "Museum B")
            )
            request = httpx.Request(
                request.method, request.url, headers=request.headers, json=query
            )
        response = mock_provider(request)
        if public_landmarks and request.url.host == "places.googleapis.com":
            payload = response.json()
            for venue in payload.get("places", [payload]):
                venue["displayName"]["text"] = (
                    "City Harbour Bridge" if venue["id"] == "pid-a" else "Old Waterfront"
                )
            response = httpx.Response(200, json=payload)
        if request.url.host == "places.googleapis.com" and not request.url.path.endswith(
            "searchText"
        ):
            payload = response.json()
            payload.pop("regularOpeningHours")
            return httpx.Response(200, json=payload)
        return response

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    assert main(["execute", str(directory), "--approved-sha256", approved], http_client=client) == 0
    capsys.readouterr()
    config = options()
    config["max_google_sends"] = 0
    option_path.write_text(json.dumps(config), encoding="utf-8")
    price = run_prices()
    price["rows"][-1]["match"]["operation"] = "opening_access"
    price_path.write_text(json.dumps(price), encoding="utf-8")
    target = root / "opening"
    assert (
        main(
            [
                "prepare-opening",
                str(directory),
                "--directory",
                str(target),
                "--options",
                str(option_path),
                "--prices",
                str(price_path),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["eligible_count"] == 8
    return root, directory, target, result["preparation_sha256"]


@pytest.mark.parametrize("public_landmarks", [False, True])
def test_opening_execution_reuses_api_evidence_and_replays_full_report(
    batch, capsys, monkeypatch, public_landmarks
):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    root, parent, directory, approved = prepare_base(
        batch, capsys, public_landmarks=public_landmarks
    )
    originals = {str(p): p.read_bytes() for p in parent.rglob("*") if p.is_file()}
    calls = []

    def respond(request):
        assert request.url.host == "model.example.test"
        calls.append(request)
        packet = json.loads((directory / "preparation.json").read_bytes())["packet"]
        assessment = (
            material(
                packet, intent_basis="public_landmark_default", venue_category="public_landmark"
            )
            if public_landmarks
            else material(packet)
        )
        assert json.loads(request.content) == assessment["request"]
        return httpx.Response(200, json=assessment["response"])

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    assert (
        main(["execute-opening", str(directory), "--approved-sha256", approved], http_client=client)
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["processing_status"] == "complete"
    assert report["quality"]["rules_profile_id"] == "rtpeval_access_quality_4"
    assert report["usage"]["actual_google_sends"] == 0
    assert report["usage"]["actual_model_sends"] == 1
    assert report["usage"]["raw"]["model_calls"][0]["total_tokens"] == 120
    assert len(calls) == 1
    assert all(
        row["opening"]["counts"]["UNKNOWN"] == 0 for row in report["reports"]["opening"]["results"]
    )
    assert all(
        g["versions"][v]["dimensions"]["opening"]["counts"]["PASS"] == 2
        for g in report["quality"]["groups"]
        for v in g["versions"]
    )
    assert (
        main(["execute-opening", str(directory), "--approved-sha256", approved], http_client=client)
        == 2
    )
    capsys.readouterr()
    assert len(calls) == 1
    opening_originals = {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("Replay attempted network"))
    assert main(["replay-opening", str(directory)]) == 0
    assert json.loads(capsys.readouterr().out) == report
    preparation = json.loads((parent / "preparation.json").read_bytes())
    quality_args = [
        preparation["manifest"],
        str(parent / "execution" / "identity-report.json"),
        str(parent / "execution" / "evidence-snapshot"),
        "--identity-snapshot",
        str(parent / "execution" / "identity-snapshot"),
        "--expected-plan",
        str(parent / "execution" / "evidence-plan.json"),
        "--opening-judgment",
        str(directory / "execution" / "model-result.json"),
        "--generated-at",
        report["generated_at"],
    ]
    assert quality_cli(quality_args) == 0
    quality = json.loads(capsys.readouterr().out)
    assert quality["status"] == "complete"
    assert quality["groups"] == report["quality"]["groups"]
    assert quality_cli(quality_args) == 0
    assert json.loads(capsys.readouterr().out) == quality
    assert {str(p): p.read_bytes() for p in parent.rglob("*") if p.is_file()} == originals
    assert {
        str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    } == opening_originals


@pytest.mark.parametrize("fault", ["http_error", "partial_decisions", "missing_usage", "unknown"])
def test_failed_or_unknown_model_attempt_is_saved_without_retry(batch, capsys, monkeypatch, fault):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    _, _, directory, approved = prepare_base(batch, capsys)
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.host == "model.example.test"
        if fault == "http_error":
            return httpx.Response(503, json={"error": "synthetic failure"})
        packet = json.loads((directory / "preparation.json").read_bytes())["packet"]
        raw = material(packet, "UNKNOWN" if fault == "unknown" else "PASS")["response"]
        if fault == "partial_decisions":
            raw["output"][0]["content"][0]["text"] = json.dumps({"decisions": []})
        elif fault == "missing_usage":
            raw.pop("usage")
        return httpx.Response(200, json=raw)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    assert (
        main(["execute-opening", str(directory), "--approved-sha256", "wrong"], http_client=client)
        == 2
    )
    capsys.readouterr()
    assert calls == []
    assert not (directory / "execution").exists()
    expected_exit = 0 if fault == "unknown" else 2
    assert (
        main(["execute-opening", str(directory), "--approved-sha256", approved], http_client=client)
        == expected_exit
    )
    report = json.loads(capsys.readouterr().out)
    assert len(calls) == 1
    assert report["usage"]["actual_model_sends"] == 1
    assert report["usage"]["retries"] == 0
    monkeypatch.setattr(
        socket, "socket", lambda *a, **k: pytest.fail("Offline replay used network")
    )
    assert main(["replay-opening", str(directory)]) == expected_exit
    assert json.loads(capsys.readouterr().out) == report
    if fault == "unknown":
        assert (
            sum(
                row["opening"]["counts"]["UNKNOWN"]
                for row in report["reports"]["opening"]["results"]
            )
            == 8
        )


def test_changed_original_receipt_blocks_new_model_dispatch(batch, capsys, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    _, parent, directory, approved = prepare_base(batch, capsys)
    (parent / "execution" / "usage.json").write_text("{}", encoding="utf-8")
    calls = []
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: calls.append(request)))
    assert (
        main(["execute-opening", str(directory), "--approved-sha256", approved], http_client=client)
        == 2
    )
    assert calls == []
    assert not (directory / "execution").exists()
