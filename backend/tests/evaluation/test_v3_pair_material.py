"""Supplied material integrity and read-only paired replay."""

import copy
import socket

import pytest

from backend.evaluation.v3_correspondence import prepare_v3_correspondence, read_v3_result_sources
from backend.evaluation.v3_pair_report import build_v3_pair_report
from backend.tests.evaluation import test_v3_pair_report as pair_tests

pytest_plugins = ("backend.tests.evaluation.test_intake",)
pair_case = pair_tests.pair_case
route_case = pair_tests.route_case
prepared_scenario = pair_tests.prepared_scenario


def test_reviewed_edit_preparation_replays_with_the_same_correspondence_reviews(pair_case, batch):
    case = pair_case(before=pair_tests.repeated_before, after=pair_tests.retimed_after)
    sources = read_v3_result_sources(case[0], batch[4] / "manifest.json")
    review = pair_tests.correspondence_review(case)
    provenance = prepare_v3_correspondence(case[0], case[1], sources, review).to_dict()
    assert provenance["status"] == "complete"
    report = pair_tests.report(
        case, result_sources=sources, correspondence_reviews=review, edit_provenance=provenance
    )
    assert report["status"] == "complete", report["diagnostics"]


@pytest.mark.parametrize(
    "fault",
    [
        "source_bytes",
        "source_link",
        "duplicate_source",
        "provenance",
        "review_revision",
        "review_pointer",
        "duplicate_review",
        "review_time",
        "review_cardinality",
        "snapshot",
        "identity",
    ],
)
def test_stale_or_corrupt_supplied_material_rejects_whole_batch(pair_case, batch, fault):
    case = pair_case(before=pair_tests.repeated_before, after=pair_tests.retimed_after)
    sources = read_v3_result_sources(case[0], batch[4] / "manifest.json")
    kwargs = {"result_sources": sources}
    if fault == "source_bytes":
        sources["records"][0]["raw_utf8"] += " "
    elif fault == "source_link":
        sources["records"][0]["input_sha256"] = "f" * 64
    elif fault == "duplicate_source":
        sources["records"].append(copy.deepcopy(sources["records"][0]))
    elif fault == "provenance":
        provenance = prepare_v3_correspondence(case[0], case[1], sources).to_dict()
        provenance["groups"][0]["relations"] = []
        kwargs["edit_provenance"] = provenance
    elif fault.startswith("review") or fault == "duplicate_review":
        review = pair_tests.correspondence_review(case)
        if fault == "review_revision":
            review["batch_revision"] = "stale"
        elif fault == "review_pointer":
            review["records"][0]["before"][0]["pointer"] = "/v3/draft/foreign"
        elif fault == "duplicate_review":
            review["records"].append(copy.deepcopy(review["records"][0]))
        elif fault == "review_time":
            review["records"][0]["reviewed_at"] = "2026-10-03T00:00:00"
        else:
            review["records"][0]["relation"] = "split"
        kwargs["correspondence_reviews"] = review
    elif fault == "snapshot":
        path = next((case[2] / "raw").glob("*"))
        path.write_bytes(b"corrupted")
    else:
        case = list(case)
        case[1] = case[1].to_dict()
        case[1]["source_hashes"] = {}
    out = pair_tests.report(case, **kwargs)
    assert out["status"] in ("needs_material_correction", "identity_replay_required")
    assert out["groups"] == []
    assert out["diagnostics"]


def test_replay_is_read_only_no_socket_and_time_is_not_semantic_hash(pair_case, batch, monkeypatch):
    case = pair_case()
    before = {p: p.read_bytes() for p in batch[4].rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("Replay attempted a network call")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    sources = read_v3_result_sources(case[0], batch[4] / "manifest.json")
    first = pair_tests.report(case, result_sources=sources)
    second = build_v3_pair_report(
        case[0],
        case[1],
        case[2],
        case[3],
        route_reviews=case[4],
        coordinate_evidence=case[5],
        expected_plan=case[6],
        result_sources=sources,
        generated_at="2026-10-04T00:00:00Z",
    ).to_dict()
    assert second["content_hash"] == first["content_hash"]
    assert {p: p.read_bytes() for p in batch[4].rglob("*") if p.is_file()} == before
