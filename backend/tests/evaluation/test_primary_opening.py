"""Opening assessment precedes the only final score, with synthetic provider responses."""

import asyncio
import hashlib
import json
import socket

import httpx
import pytest

from backend.evaluation.evaluation_run_cli import main
from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices
from backend.tests.evaluation.test_opening_judgment import material, walks

pytest_plugins = ("backend.tests.evaluation.test_intake",)


def prepare(batch, capsys, **overrides):
    _, results, write, _, root = batch
    walks(results)
    for version in ("v1", "v2", "v3"):
        visits = results[version]["itinerary"]["days"][0]["activities"]
        visits[0]["source_place_id"] = "pid-a"
        visits[2]["source_place_id"] = "pid-b"
    for version in results:
        write(version)
    configured = {**options(), **overrides}
    book = run_prices()
    opening_price = json.loads(json.dumps(book["rows"][-1]))
    opening_price["price_id"] = "opening"
    opening_price["match"]["operation"] = "opening_access"
    book["rows"].append(opening_price)
    (root / "options.json").write_text(json.dumps(configured), encoding="utf-8")
    (root / "prices.json").write_text(json.dumps(book), encoding="utf-8")
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
    digest = json.loads(capsys.readouterr().out)["preparation_sha256"]
    return directory, digest


def test_primary_assesses_missing_hours_before_emitting_one_final_report(
    batch, capsys, monkeypatch
):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    directory, digest = prepare(batch, capsys)
    calls = []

    def respond(request):
        calls.append(request)
        if request.url.host == "model.example.test":
            wire = json.loads(request.content)
            if wire["text"]["format"]["name"] == "access_assessments":
                assert not (directory / "execution/report.json").exists()
                packet = json.loads((directory / "execution/opening-packet.json").read_bytes())
                assert {case["version"] for case in packet["cases"]} == {"v0", "v1", "v2", "v3"}
                assessment = material(packet)
                assert wire == assessment["request"]
                return httpx.Response(200, json=assessment["response"])
        response = mock_provider(request)
        if request.url.host == "places.googleapis.com" and not request.url.path.endswith(
            "searchText"
        ):
            payload = response.json()
            payload.pop("regularOpeningHours")
            return httpx.Response(200, json=payload)
        return response

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(["execute", str(directory), "--approved-sha256", digest], http_client=client) == 0
        )
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert report["opening_assessment"]["status"] == "complete"
    assert report["opening_assessment"]["eligible_count"] == 8
    assert report["quality"]["rules_profile_id"] == "rtpeval_access_quality_4"
    assert all(
        value["primary_metrics"]["opening"]["counts"]["PASS"] == 2
        for value in report["quality"]["groups"][0]["versions"].values()
    )
    assert report["usage"]["actual_model_sends"] == 2
    assert {call["operation"] for call in report["usage"]["raw"]["model_calls"]} == {
        "identity",
        "opening_access",
    }
    before = len(calls)
    monkeypatch.setattr(socket.socket, "connect", lambda *args: pytest.fail("replay used network"))
    assert main(["replay", str(directory)]) == 0
    assert json.loads(capsys.readouterr().out) == report
    assert len(calls) == before
    execution = directory / "execution"
    for path in (execution / "http").glob("*.json"):
        event = json.loads(path.read_bytes())
        if event.get("model_event_id") == "opening-access":
            event["request"]["json"]["reasoning"] = {"effort": "low"}
            path.write_text(json.dumps(event), encoding="utf-8")
            receipt_path = execution / "receipt.json"
            receipt = json.loads(receipt_path.read_bytes())
            receipt["files"][str(path.relative_to(execution))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            break
    assert main(["replay", str(directory)]) == 2
    assert "Model HTTP receipt differs" in capsys.readouterr().out


@pytest.mark.parametrize("assess", [True, False])
def test_primary_skips_opening_call_when_not_needed_or_explicitly_disabled(
    batch, capsys, monkeypatch, assess
):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    directory, digest = prepare(batch, capsys, assess_missing_hours=assess)
    seen = []

    def respond(request):
        if request.url.host == "model.example.test":
            seen.append(json.loads(request.content)["text"]["format"]["name"])
        response = mock_provider(request)
        if not assess and request.url.host == "places.googleapis.com" and request.method == "GET":
            payload = response.json()
            payload.pop("regularOpeningHours")
            return httpx.Response(200, json=payload)
        return response

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(["execute", str(directory), "--approved-sha256", digest], http_client=client) == 0
        )
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert report["opening_assessment"]["status"] == ("skipped" if assess else "disabled")
    assert report["usage"]["actual_model_sends"] == 1
    assert len(seen) == 1
    assert report["quality"]["rules_profile_id"] == "rtpeval_verified_quality_2"
    assert not (directory / "execution/opening-model-result.json").exists()
    if not assess:
        assert all(
            value["primary_metrics"]["opening"]["counts"]["UNKNOWN"] == 2
            for value in report["quality"]["groups"][0]["versions"].values()
        )
    assert main(["replay", str(directory)]) == 0
    assert json.loads(capsys.readouterr().out) == report


@pytest.mark.parametrize("failure", ["http", "invalid_quote", "price", "budget"])
def test_opening_failure_stops_without_publishing_a_preliminary_score(
    batch, capsys, monkeypatch, failure
):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    # Seven Google reservations (0.21) plus identity's maximum-token reservation
    # (0.021) fit 0.24; reserving opening's 0.021 exceeds the same shared allowance.
    directory, digest = prepare(
        batch, capsys, **({"max_cost_usd": "0.24"} if failure == "budget" else {})
    )
    if failure == "price":
        # Prepare a genuinely new package with a price book lacking the conditional operation.
        from backend.evaluation.evaluation_run import prepare_run

        _, _, write, _, root = batch
        directory = root / "unpriced-evaluation"
        prepared = prepare_run(write(), directory, options=options(), prices=run_prices())
        digest = prepared["content_sha256"]
    opening_sends = []

    def respond(request):
        if request.url.host == "model.example.test":
            wire = json.loads(request.content)
            if wire["text"]["format"]["name"] == "access_assessments":
                opening_sends.append(request)
                assert not (directory / "execution/report.json").exists()
                if failure == "http":
                    return httpx.Response(503, json={"error": "fixture unavailability"})
                packet = json.loads((directory / "execution/opening-packet.json").read_bytes())
                assessment = material(packet, activity_quote="a quote absent from the source")
                return httpx.Response(200, json=assessment["response"])
        response = mock_provider(request)
        if request.url.host == "places.googleapis.com" and not request.url.path.endswith(
            "searchText"
        ):
            payload = response.json()
            payload.pop("regularOpeningHours")
            return httpx.Response(200, json=payload)
        return response

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(["execute", str(directory), "--approved-sha256", digest], http_client=client) == 2
        )
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert report["processing_status"] == "stopped"
    assert "quality" not in report
    assert (directory / "execution/opening-packet.json").exists()
    assert len(opening_sends) == (1 if failure in ("http", "invalid_quote") else 0)
    assert report["usage"]["actual_model_sends"] == 1 + len(opening_sends)
    assert report["usage"]["retries"] == 0
    assert main(["replay", str(directory)]) == 2
    assert json.loads(capsys.readouterr().out) == report


@pytest.mark.parametrize("flag", [None, 0, "false"])
def test_primary_rejects_ambiguous_assessment_switch_before_preparation(batch, flag):
    from backend.evaluation.evaluation_run import prepare_run

    _, _, write, _, root = batch
    with pytest.raises(ValueError, match="assess_missing_hours must be a boolean"):
        prepare_run(
            write(),
            root / "evaluation",
            options={**options(), "assess_missing_hours": flag},
            prices=run_prices(),
        )
    assert not (root / "evaluation").exists()
