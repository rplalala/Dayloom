"""Offline snapshot acquisition/replay acceptance at public seams."""

import asyncio
import json

import pytest

from backend.evaluation.intake import load_batch
from backend.evaluation.snapshot import build_identity_plan


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("Snapshot tests must not access network")

    # Windows creates a loopback socket pair when constructing an asyncio loop.
    connect = socket.socket.connect

    def guarded(sock, address):
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return connect(sock, address)
        return forbidden(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(socket, "create_connection", forbidden)


pytest_plugins = ("backend.tests.evaluation.test_intake",)


def test_identity_plan_deduplicates_queries_but_retains_occurrences(batch):
    _, _, write, _, _ = batch
    plan = build_identity_plan(load_batch(write()))
    assert len(plan["references"]) == 8
    assert len(plan["requests"]) == 2
    assert all(r["operation"] == "places_search" for r in plan["requests"])
    assert all(r["parameters"]["page_size"] == 20 for r in plan["requests"])
    assert plan == build_identity_plan(load_batch(write()))


def test_offline_import_records_missing_observations_without_new_sends(batch, tmp_path):
    from backend.evaluation.snapshot import load_snapshot
    from backend.evaluation.snapshot_import import import_snapshot

    intake = load_batch(batch[2]()).to_dict()
    plan = build_identity_plan(intake, paired=True)
    directory = tmp_path / "derived"
    imported = import_snapshot(plan, directory, intake=intake)
    assert imported == load_snapshot(directory, expected_plan=plan)
    assert imported["schema_version"] == "rtpeval_imported_snapshot_1"
    assert imported["ledger"]["actual_sends"] == 0
    assert imported["inherited_usage"] == []
    assert all(row["attempts"] == [] for row in imported["records"])
    assert all(
        row["summary"] == {"status": "unavailable", "reason": "no_compatible_observation"}
        for row in imported["records"]
    )


def test_acquire_and_replay_preserves_raw_bytes_and_reference_coverage(batch, tmp_path):
    from backend.evaluation.snapshot import (
        AcquisitionPolicy,
        Response,
        acquire_snapshot,
        load_snapshot,
    )

    _, _, write, _, _ = batch
    plan = build_identity_plan(load_batch(write()))
    calls = []

    async def transport(request):
        calls.append(request)
        return Response(200, b'{ "places": [] }')

    path = tmp_path / "snapshot"
    acquired = asyncio.run(acquire_snapshot(plan, path, transport, AcquisitionPolicy(max_sends=5)))
    replay = load_snapshot(path, expected_plan=plan)
    assert acquired == replay == load_snapshot(path)
    assert len(calls) == 2
    assert replay["ledger"]["actual_sends"] == 2
    assert len(replay["plan"]["references"]) == 8
    raw = replay["records"][0]["attempts"][0]["raw"]
    assert (path / raw["path"]).read_bytes() == b'{ "places": [] }'
    with pytest.raises(FileExistsError):
        asyncio.run(acquire_snapshot(plan, path, transport, AcquisitionPolicy(max_sends=5)))


@pytest.mark.parametrize("failure", ["http", "timeout", "transport"])
def test_bounded_retry_preserves_failures_and_budget_coverage(batch, tmp_path, failure):
    from backend.evaluation.snapshot import (
        AcquisitionPolicy,
        Response,
        TransportFailure,
        acquire_snapshot,
    )

    plan = build_identity_plan(load_batch(batch[2]()))
    calls = []

    async def transport(request):
        calls.append(request)
        if len(calls) == 1:
            if failure == "timeout":
                raise TimeoutError()
            if failure == "transport":
                raise TransportFailure("connection_failed")
            return Response(503, b'{"error":"unavailable"}')
        return Response(200, b'{"places":[]}')

    report = asyncio.run(
        acquire_snapshot(
            plan,
            tmp_path / "retry",
            transport,
            AcquisitionPolicy(max_sends=2, retry_delay_seconds=0),
        )
    )
    assert report["ledger"]["actual_sends"] == 2
    assert report["ledger"]["retry_sends"] == 1
    assert len(report["records"][0]["attempts"]) == 2
    assert report["records"][0]["summary"]["status"] == "available"
    assert report["records"][1]["summary"]["reason"] == "send_budget_exhausted"
    assert len(report["plan"]["references"]) == 8


def test_identity_snapshot_handoff_uses_real_resolver(batch, tmp_path):
    from backend.evaluation.identity import resolve_legacy_identities as resolve_identities
    from backend.evaluation.snapshot import (
        AcquisitionPolicy,
        Response,
        acquire_snapshot,
        identity_evidence,
    )
    from backend.tests.evaluation.test_identity import plan as audit_plan

    intake = load_batch(batch[2]())
    request_plan = build_identity_plan(intake)

    async def transport(request):
        name = request["parameters"]["query"]
        return Response(
            200,
            json.dumps(
                {
                    "places": [
                        {
                            "id": name,
                            "displayName": {"text": name},
                            "formattedAddress": "10 Main St, Example City, Country",
                        }
                    ]
                }
            ).encode(),
        )

    snapshot = asyncio.run(
        acquire_snapshot(
            request_plan, tmp_path / "identity", transport, AcquisitionPolicy(max_sends=2)
        )
    )
    evidence = identity_evidence(snapshot)
    report = resolve_identities(intake, evidence, audit_plan=audit_plan(intake)).to_dict()
    assert len(evidence["records"]) == 8
    assert sum(r["resolution"] == "resolved" for r in report["records"]) == 7
    assert len(report["audit_selected_reference_ids"]) == 1


def resolved_batch(batch):
    from backend.evaluation.identity import identity_references
    from backend.evaluation.identity import resolve_legacy_identities as resolve_identities
    from backend.tests.evaluation.test_identity import evidence, plan, review_envelope, search

    intake = load_batch(batch[2]())
    refs = identity_references(intake)
    observations = [search(r, r["name"], place_id=r["name"]) for r in refs]
    envelope = evidence(intake, observations)
    initial = resolve_identities(intake, envelope, audit_plan=plan(intake)).to_dict()
    rid = initial["audit_selected_reference_ids"][0]
    observation = next(o for o in observations if o["reference_id"] == rid)
    reviews = review_envelope(
        intake, observation, rid, observation["search"]["candidates"][0]["place_id"]
    )
    return intake, resolve_identities(intake, envelope, reviews, plan(intake)).to_dict()


@pytest.mark.parametrize("component_state", ["available", "absent", "malformed"])
def test_address_snapshot_replay_never_backfills_or_adds_requests(batch, tmp_path, component_state):
    from backend.evaluation.identity import resolve_legacy_identities as resolve_identities
    from backend.evaluation.snapshot import (
        AcquisitionPolicy,
        Response,
        acquire_snapshot,
        identity_evidence,
        load_snapshot,
    )
    from backend.tests.evaluation.test_identity import address_components
    from backend.tests.evaluation.test_identity import plan as audit_plan

    intake = load_batch(batch[2]())
    request_plan = build_identity_plan(intake)
    assert len(request_plan["requests"]) == 2
    sends = []

    async def transport(request):
        sends.append(request)
        name = request["parameters"]["query"]
        place = {
            "id": name,
            "displayName": {"text": name},
            "formattedAddress": "10 Main St, Example City ST 2000, Country",
        }
        if component_state != "absent":
            place["addressComponents"] = (
                address_components() if component_state == "available" else None
            )
        return Response(200, json.dumps({"places": [place]}).encode())

    path = tmp_path / "addresses"
    asyncio.run(acquire_snapshot(request_plan, path, transport, AcquisitionPolicy(max_sends=2)))
    before = {p.name: p.read_bytes() for p in (path / "raw").iterdir()}
    snapshot = load_snapshot(path, expected_plan=request_plan)
    report = resolve_identities(
        intake, identity_evidence(snapshot), audit_plan=audit_plan(intake)
    ).to_dict()
    reasons = {r["reason"] for r in report["records"]}
    if component_state == "available":
        assert sum(r["resolution"] == "resolved" for r in report["records"]) == 7
        assert reasons == {"strict_association", "audit_pending"}
    else:
        assert reasons == {
            "destination_unverified"
            if component_state == "absent"
            else "malformed_address_components"
        }
    assert len(sends) == snapshot["ledger"]["actual_sends"] == 2
    assert before == {p.name: p.read_bytes() for p in (path / "raw").iterdir()}


def test_evidence_planning_requires_current_identity_policy(batch):
    from backend.evaluation.snapshot import build_evidence_plan

    intake, identity = resolved_batch(batch)
    identity.pop("association_policy_version")
    with pytest.raises(ValueError, match="Identity report"):
        build_evidence_plan(intake, identity, [])


def test_evidence_union_retains_legs_without_departure_guessing(batch):
    from backend.evaluation.snapshot import build_evidence_plan

    intake, report = resolved_batch(batch)
    plan = build_evidence_plan(intake, report, [])
    assert len(plan["requests"]) == 2
    assert len(plan["references"]) == 8
    assert len(plan["legs"]) == 4
    assert all(leg["reason"] == "route_context_missing" for leg in plan["legs"])
    assert all(r["operation"] == "places_details" for r in plan["requests"])


def route_context(leg):
    return {
        "leg_id": leg["leg_id"],
        "mode": "TRANSIT",
        "departure": "2020-01-01T10:00:00+00:00",
        "time_basis": "explicit_departure",
        "origin": {
            "place_id": "Museum A",
            "latitude": 10.0,
            "longitude": 20.0,
            "evidence_sha256": "a" * 64,
        },
        "destination": {
            "place_id": "Museum B",
            "latitude": 10.1,
            "longitude": 20.1,
            "evidence_sha256": "b" * 64,
        },
        "routing_options": {},
        "source_kind": "independent_evaluation_context",
    }


def test_route_keys_preserve_context_and_missing_elements(batch, tmp_path):
    from backend.evaluation.snapshot import (
        AcquisitionPolicy,
        Response,
        acquire_snapshot,
        build_evidence_plan,
    )

    intake, report = resolved_batch(batch)
    initial = build_evidence_plan(intake, report, [])
    contexts = [route_context(leg) for leg in initial["legs"]]
    contexts[1]["departure"] = "2020-01-01T10:10:00+00:00"
    contexts[2]["mode"] = "DRIVE"
    contexts[3]["origin"]["latitude"] = 11.0
    plan = build_evidence_plan(intake, report, contexts)
    assert len({leg["request_key"] for leg in plan["legs"]}) == 4

    async def transport(request):
        return Response(200, b"[]" if request["operation"] == "route_matrix" else b"{}")

    snapshot = asyncio.run(
        acquire_snapshot(plan, tmp_path / "routes", transport, AcquisitionPolicy(max_sends=10))
    )
    assert snapshot["ledger"]["requested_matrix_elements"] == 4
    assert sum(r["summary"]["status"] == "incomplete" for r in snapshot["records"]) == 4
    assert len(snapshot["plan"]["legs"]) == 4


@pytest.mark.parametrize("mutation", ["raw", "path", "coverage", "summary", "ledger", "no_attempt"])
def test_snapshot_replay_rejects_corruption(batch, tmp_path, mutation):
    from backend.evaluation.snapshot import (
        AcquisitionPolicy,
        Response,
        acquire_snapshot,
        load_snapshot,
    )

    plan = build_identity_plan(load_batch(batch[2]()))

    async def transport(request):
        return Response(200, b'{"places":[]}')

    path = tmp_path / "corruption"
    snapshot = asyncio.run(acquire_snapshot(plan, path, transport, AcquisitionPolicy(max_sends=2)))
    record = snapshot["records"][0]
    if mutation == "raw":
        (path / record["attempts"][0]["raw"]["path"]).write_bytes(b"corrupt")
    elif mutation == "path":
        record["attempts"][0]["raw"]["path"] = "../outside.bin"
    elif mutation == "coverage":
        snapshot["records"].pop()
    elif mutation == "summary":
        record["summary"]["status"] = "unavailable"
    elif mutation == "ledger":
        snapshot["ledger"]["actual_sends"] = 0
    else:
        record["attempts"] = []
    (path / "manifest.json").write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(ValueError):
        load_snapshot(path, expected_plan=plan)


def test_paired_union_includes_available_drafts_without_merging_occurrences(batch):
    import copy

    _, results, write, _, _ = batch
    results["v3"]["v3"] = {"draft": copy.deepcopy(results["v3"]["itinerary"])}
    intake = load_batch(write("v3"))
    base = build_identity_plan(intake)
    paired = build_identity_plan(intake, paired=True)
    assert len(base["references"]) == 8
    assert len(paired["references"]) == 10
    assert len(paired["requests"]) == 2
    assert {r["projection"]: r["available"] for r in paired["optional_availability"]} == {
        "draft": True,
        "final_primary": False,
    }


@pytest.mark.parametrize(
    "mutation", ["identity", "naive", "foreign_leg", "duplicate", "planner_source"]
)
def test_invalid_route_context_is_rejected(batch, mutation):
    from backend.evaluation.snapshot import build_evidence_plan

    intake, report = resolved_batch(batch)
    leg = build_evidence_plan(intake, report, [])["legs"][0]
    context = route_context(leg)
    contexts = [context]
    if mutation == "identity":
        context["origin"]["place_id"] = "wrong"
    elif mutation == "naive":
        context["departure"] = "2020-01-01T10:00:00"
    elif mutation == "foreign_leg":
        context["leg_id"] = "foreign"
    elif mutation == "duplicate":
        contexts.append(context)
    else:
        context["source_kind"] = "planner_cache"
    with pytest.raises(ValueError):
        build_evidence_plan(intake, report, contexts)


@pytest.mark.parametrize(
    "payload,status",
    [
        ([], "incomplete"),
        ([{"originIndex": 0, "destinationIndex": 0}] * 2, "incomplete"),
        ([{"originIndex": 1, "destinationIndex": 0}], "incomplete"),
        (
            [
                {
                    "originIndex": 0,
                    "destinationIndex": 0,
                    "status": {},
                    "condition": "ROUTE_EXISTS",
                    "duration": "300.123s",
                }
            ],
            "available",
        ),
    ],
)
def test_matrix_replay_keeps_precision_and_incomplete_elements(batch, tmp_path, payload, status):
    from backend.evaluation.snapshot import (
        AcquisitionPolicy,
        Response,
        acquire_snapshot,
        build_evidence_plan,
    )

    intake, report = resolved_batch(batch)
    leg = build_evidence_plan(intake, report, [])["legs"][0]
    plan = build_evidence_plan(intake, report, [route_context(leg)])

    async def transport(request):
        return Response(
            200, json.dumps(payload if request["operation"] == "route_matrix" else {}).encode()
        )

    snapshot = asyncio.run(
        acquire_snapshot(plan, tmp_path / "matrix", transport, AcquisitionPolicy(max_sends=10))
    )
    key = plan["legs"][0]["request_key"]
    summary = next(r["summary"] for r in snapshot["records"] if r["key"] == key)
    assert summary["status"] == status
    if status == "available":
        assert summary["element"]["duration"] == "300.123s"


@pytest.mark.parametrize("code,body", [(400, b"{}"), (200, b"not json")])
def test_permanent_or_malformed_observation_is_not_retried(batch, tmp_path, code, body):
    from backend.evaluation.snapshot import AcquisitionPolicy, Response, acquire_snapshot

    async def transport(request):
        return Response(code, body)

    snapshot = asyncio.run(
        acquire_snapshot(
            build_identity_plan(load_batch(batch[2]())),
            tmp_path / "permanent",
            transport,
            AcquisitionPolicy(max_sends=10, retry_delay_seconds=0),
        )
    )
    assert snapshot["ledger"]["actual_sends"] == 2
    assert snapshot["ledger"]["retry_sends"] == 0
    assert all(r["summary"]["status"] != "available" for r in snapshot["records"])


def test_snapshot_cli_prepares_and_replays_without_transport(batch, tmp_path, capsys):
    from backend.evaluation.snapshot import AcquisitionPolicy, Response, acquire_snapshot
    from backend.evaluation.snapshot_cli import main

    manifest = batch[2]()
    assert main(["identity-plan", str(manifest)]) == 0
    plan = json.loads(capsys.readouterr().out)

    async def transport(request):
        return Response(200, b'{"places": []}')

    root = tmp_path / "cli-snapshot"
    asyncio.run(acquire_snapshot(plan, root, transport, AcquisitionPolicy(max_sends=2)))
    assert main(["replay", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["plan"] == plan
    assert main(["identity-evidence", str(root)]) == 0
    assert len(json.loads(capsys.readouterr().out)["records"]) == 8
    (root / "manifest.json").write_text("broken", encoding="utf-8")
    assert main(["replay", str(root)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "needs_snapshot_correction"


def test_acquisition_rejects_unapproved_request_parameters_before_transport(batch, tmp_path):
    import hashlib

    from backend.evaluation.snapshot import AcquisitionPolicy, Response, acquire_snapshot

    plan = build_identity_plan(load_batch(batch[2]()))
    request = plan["requests"][0]
    old = request["key"]
    request["parameters"]["authorization"] = "must-not-persist"
    body = {k: request[k] for k in ("operation", "parameters")}
    request["key"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    for ref in plan["references"]:
        for kind, key in ref["requests"].items():
            if key == old:
                ref["requests"][kind] = request["key"]

    async def transport(request):
        return Response(200, b"{}")

    with pytest.raises(ValueError, match="parameters"):
        asyncio.run(
            acquire_snapshot(plan, tmp_path / "invalid", transport, AcquisitionPolicy(max_sends=2))
        )
    assert not (tmp_path / "invalid").exists()


@pytest.mark.parametrize("mutation", ["missing", "naive", "reversed", "outside"])
def test_replay_rejects_invalid_collection_times(batch, tmp_path, mutation):
    from backend.evaluation.snapshot import (
        AcquisitionPolicy,
        Response,
        acquire_snapshot,
        load_snapshot,
    )

    async def transport(request):
        return Response(200, b'{"places": []}')

    root = tmp_path / "times"
    plan = build_identity_plan(load_batch(batch[2]()))
    snapshot = asyncio.run(acquire_snapshot(plan, root, transport, AcquisitionPolicy(max_sends=2)))
    attempt = snapshot["records"][0]["attempts"][0]
    if mutation == "missing":
        del attempt["retrieved_at"]
    elif mutation == "naive":
        attempt["retrieved_at"] = "2026-09-30T10:00:00"
    elif mutation == "reversed":
        attempt["retrieved_at"] = "2000-01-01T00:00:00+00:00"
    else:
        snapshot["finished_at"] = "2000-01-01T00:00:00+00:00"
    (root / "manifest.json").write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(ValueError, match="time"):
        load_snapshot(root)


def test_supplied_id_and_malformed_optional_location_handoff(batch, tmp_path):
    from backend.evaluation.identity import resolve_legacy_identities as resolve_identities
    from backend.evaluation.snapshot import (
        AcquisitionPolicy,
        Response,
        acquire_snapshot,
        identity_evidence,
    )
    from backend.tests.evaluation.test_identity import plan as audit_plan

    _, results, write, _, _ = batch
    activity = results["v1"]["itinerary"]["days"][0]["activities"][0]
    activity.update(source_place_id="Museum A", location={"invalid": "location"})
    intake = load_batch(write("v1"))
    plan = build_identity_plan(intake)

    async def transport(request):
        parameters = request["parameters"]
        name = parameters.get("query", parameters.get("place_id"))
        place = {
            "id": name,
            "displayName": {"text": name},
            "formattedAddress": "10 Main St, Example City, Country",
        }
        payload = {"places": [place]} if request["operation"] == "places_search" else place
        return Response(200, json.dumps(payload).encode())

    snapshot = asyncio.run(
        acquire_snapshot(plan, tmp_path / "supplied", transport, AcquisitionPolicy(max_sends=10))
    )
    report = resolve_identities(
        intake, identity_evidence(snapshot), audit_plan=audit_plan(intake)
    ).to_dict()
    record = next(
        r for r in report["records"] if r["version"] == "v1" and r["candidate_ids"] == ["Museum A"]
    )
    assert record["reason"] in ("strict_association", "audit_pending")
    assert any("details" in r["requests"] for r in plan["references"])


def test_reverse_leg_has_distinct_key_even_with_shared_context(batch):
    from backend.evaluation.snapshot import build_evidence_plan

    _, results, write, _, _ = batch
    activities = results["v1"]["itinerary"]["days"][0]["activities"]
    activities[0]["start_time"], activities[2]["start_time"] = (
        activities[2]["start_time"],
        activities[0]["start_time"],
    )
    activities[0]["end_time"], activities[2]["end_time"] = (
        activities[2]["end_time"],
        activities[0]["end_time"],
    )
    write("v1")
    intake, report = resolved_batch(batch)
    initial = build_evidence_plan(intake, report, [])
    contexts = [route_context(leg) for leg in initial["legs"]]
    contexts[1]["origin"], contexts[1]["destination"] = (
        contexts[1]["destination"],
        contexts[1]["origin"],
    )
    plan = build_evidence_plan(intake, report, contexts)
    assert plan["legs"][0]["request_key"] != plan["legs"][1]["request_key"]
    assert plan["legs"][0]["request_key"] == plan["legs"][2]["request_key"]


def test_stale_identity_report_cannot_seed_evidence_plan(batch):
    from backend.evaluation.snapshot import build_evidence_plan

    intake, report = resolved_batch(batch)
    report["source_hashes"] = {"manifest": "stale"}
    with pytest.raises(ValueError, match="source mismatch"):
        build_evidence_plan(intake, report, [])
