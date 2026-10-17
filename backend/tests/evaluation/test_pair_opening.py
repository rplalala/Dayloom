"""Source-bound paired access assessments through public evaluation interfaces."""

from backend.evaluation.opening_judgment import prepare_packet
from backend.tests.evaluation import test_v3_pair_report as pairs
from backend.tests.evaluation.test_opening_judgment import material

pytest_plugins = ("backend.tests.evaluation.test_intake",)
pair_case = pairs.pair_case
route_case = pairs.route_case
prepared_scenario = pairs.prepared_scenario


def missing_hours(request):
    return {"id": request["parameters"]["place_id"], "timeZone": {"id": "Etc/UTC"}}


def test_pair_assessment_shares_identical_context_without_scoring_other_finals(pair_case):
    case = pair_case(details_payload=missing_hours)
    packet = prepare_packet(
        case[0],
        case[1],
        case[2],
        case[3],
        model="fixture-model",
        paired=True,
        pair_only=True,
        expected_plan=case[6],
    )
    assert len(packet["cases"]) == 2
    assert {c["version"] for c in packet["cases"]} == {"v3"}
    assert all(c["projection"] == "draft" for c in packet["cases"])
    assert all(c["source_aliases"][0]["projection"] == "final_primary" for c in packet["cases"])
    result = pairs.report(case, opening_judgment=material(packet))
    assert result["status"] == "complete", result["diagnostics"]
    stages = result["groups"][0]["stages"]
    assert stages["draft"]["dimensions"]["opening"]["counts"]["PASS"] == 2
    assert stages["final_primary"]["dimensions"]["opening"]["counts"]["PASS"] == 2
    assert stages["draft"]["primary_metrics"]["opening"]["complete_evidence_coverage"]["rate"] == 0


def test_changed_visit_time_gets_a_distinct_assessment(pair_case):
    def after(itinerary):
        itinerary["days"][0]["activities"][0]["start_time"] = "2020-01-01T08:30:00Z"

    case = pair_case(after=after, details_payload=missing_hours)
    packet = prepare_packet(
        case[0],
        case[1],
        case[2],
        case[3],
        model="fixture-model",
        paired=True,
        pair_only=True,
        expected_plan=case[6],
    )
    assert len(packet["cases"]) == 3
    assert sum(len(c["source_aliases"]) + 1 for c in packet["cases"]) == 4


def test_cli_pair_report_imports_bound_access_material(pair_case, capsys):
    import json

    from backend.evaluation.v3_pair_cli import main

    case = pair_case(details_payload=missing_hours)
    root = case[2].parent
    packet = prepare_packet(
        case[0], case[1], case[2], case[3], model="fixture-model", paired=True, pair_only=True
    )
    for name, value in (
        ("identity", case[1].to_dict()),
        ("context", case[3]),
        ("access", material(packet)),
        ("routes", case[4]),
        ("coordinates", case[5]),
    ):
        (root / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
    assert (
        main(
            [
                "report",
                str(root / "manifest.json"),
                str(root / "identity.json"),
                str(case[2]),
                "--opening-judgment",
                str(root / "access.json"),
                "--context",
                str(root / "context.json"),
                "--route-reviews",
                str(root / "routes.json"),
                "--coordinates",
                str(root / "coordinates.json"),
                "--generated-at",
                pairs.STAMP,
            ]
        )
        == 0
    )
    saved = json.loads(capsys.readouterr().out)
    assert saved["preparation_file_sha256"]["opening_judgment"]
    assert saved["groups"][0]["stages"]["draft"]["dimensions"]["opening"]["counts"]["PASS"] == 2


def test_pair_access_one_send_and_offline_receipt_replay(pair_case, capsys, monkeypatch):
    import json
    import socket

    import httpx

    from backend.evaluation.evaluation_run_cli import main
    from backend.tests.evaluation.test_evaluation_run import options, run_prices

    case = pair_case(details_payload=missing_hours)
    root = case[2].parent
    config = options()
    config["max_google_sends"] = 0
    prices = run_prices()
    prices["rows"][-1]["match"]["operation"] = "opening_access"
    for name, value in (
        ("identity", case[1].to_dict()),
        ("context", case[3]),
        ("options", config),
        ("prices", prices),
    ):
        (root / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
    target = root / "paired-access"
    args = [
        "prepare-pair-opening",
        str(root / "manifest.json"),
        str(root / "identity.json"),
        str(case[2]),
        "--context",
        str(root / "context.json"),
        "--directory",
        str(target),
        "--options",
        str(root / "options.json"),
        "--prices",
        str(root / "prices.json"),
    ]
    assert main(args) == 0
    approved = json.loads(capsys.readouterr().out)["preparation_sha256"]
    packet = json.loads((target / "packet.json").read_bytes())
    sends = []

    def respond(request):
        sends.append(request)
        assert request.url.host == "model.example.test"
        return httpx.Response(200, json=material(packet)["response"])

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    execute = ["execute-opening", str(target), "--approved-sha256", approved]
    assert main(execute, http_client=client) == 0
    saved = json.loads(capsys.readouterr().out)
    assert len(sends) == 1
    assert saved["usage"]["actual_google_sends"] == 0
    assert main(execute, http_client=client) == 2
    capsys.readouterr()
    assert len(sends) == 1

    def deny(*args, **kwargs):
        raise AssertionError("Offline replay attempted network")

    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket, "socket", deny)
    assert main(["replay-opening", str(target)]) == 0
    assert json.loads(capsys.readouterr().out) == saved
