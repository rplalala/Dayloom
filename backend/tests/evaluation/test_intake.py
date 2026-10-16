"""Batch-boundary acceptance tests using synthetic local artifacts only."""

import copy
import hashlib
import json

import pytest

from backend.evaluation.__main__ import main
from backend.evaluation.intake import load_batch


def activity(aid, title, start, end, role="main_poi", place=None):
    return {
        "activity_id": aid,
        "activity_kind": role,
        "title": title,
        "place_name": place,
        "source_place_id": None,
        "start_time": "2020-01-01T" + start + ":00+00:00",
        "end_time": "2020-01-01T" + end + ":00+00:00",
    }


@pytest.fixture
def batch(tmp_path):
    def save(name, value, schema=None):
        raw = json.dumps(value, ensure_ascii=False).encode()
        (tmp_path / name).write_bytes(raw)
        ref = {
            "path": name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "media_type": "application/json",
            "availability": "available",
        }
        if schema:
            ref["schema_version"] = schema
        return ref

    original = {
        "input_version": "planning_request_2",
        "destination": "Example City",
        "start_date": "2020-01-01",
        "end_date": "2020-01-01",
        "traveler_count": 1,
        "budget": {"amount": 100, "currency": "USD"},
        "additional_preferences": "Prefer architecture",
    }
    inp = save("input.json", original)
    spec = {
        "schema_version": "rtpeval_requirements_1",
        "spec_id": "spec-1",
        "revision": "1",
        "group_id": "g",
        "input_sha256": inp["sha256"],
        "review": {"status": "reviewed", "reviewer_ref": "reviewer", "reviewed_at": "now"},
        "subjects": [],
        "obligations": [],
        "soft_preferences": [],
        "unresolved_items": [],
    }
    spec_ref = save("requirements.json", spec, spec["schema_version"])
    itinerary = {
        "output_version": "itinerary_2",
        "destination": "Example City",
        "start_date": "2020-01-01",
        "end_date": "2020-01-01",
        "days": [
            {
                "date": "2020-01-01",
                "activities": [
                    activity("a", "Museum A", "09:00", "10:00", place="Museum A"),
                    activity("t", "Walking", "10:00", "10:20", "transport"),
                    activity("b", "Museum B", "10:30", "11:30", place="Museum B"),
                ],
            }
        ],
    }
    runs = {}
    results = {}
    for v in ("v0", "v1", "v2", "v3"):
        results[v] = {
            "system_version": v,
            "itinerary": copy.deepcopy(itinerary),
            "requirements": {"private": "never read"},
        }
        ref = save(v + ".json", results[v])
        usage = {
            "schema_version": "rtpeval_usage_1",
            "group_id": "g",
            "version": v,
            "run_id": "run-" + v,
            "result_sha256": ref["sha256"],
            "collection_status": "unavailable",
        }
        runs[v] = {
            "run_id": "run-" + v,
            "result_ref": ref,
            "usage_ref": save(v + "-usage.json", usage, usage["schema_version"]),
            "provenance_ref": save(
                v + "-provenance.json",
                {
                    "schema_version": "rtpeval_provenance_1",
                    "group_id": "g",
                    "run_id": "run-" + v,
                    "version": v,
                    "input_sha256": inp["sha256"],
                    "result_sha256": ref["sha256"],
                },
                "rtpeval_provenance_1",
            ),
        }
    manifest = {
        "schema_version": "rtpeval_batch_1",
        "batch_id": "batch",
        "revision": "1",
        "created_at": "now",
        "qualification_policy_ref": "producer-policy-1",
        "selected_group_ids": ["g"],
        "groups": [
            {
                "group_id": "g",
                "completion_attested": True,
                "input_ref": inp,
                "requirement_spec_ref": spec_ref,
                "selected_runs": runs,
            }
        ],
    }

    def write(version=None):
        if version:
            runs[version]["result_ref"] = save(version + ".json", results[version])
            name = version + "-usage.json"
            usage = json.loads((tmp_path / name).read_text())
            usage["result_sha256"] = runs[version]["result_ref"]["sha256"]
            runs[version]["usage_ref"] = save(name, usage, usage["schema_version"])
            name = version + "-provenance.json"
            provenance = json.loads((tmp_path / name).read_text(encoding="utf-8"))
            provenance["result_sha256"] = runs[version]["result_ref"]["sha256"]
            runs[version]["provenance_ref"] = save(name, provenance, "rtpeval_provenance_1")
        save("manifest.json", manifest)
        return tmp_path / "manifest.json"

    return manifest, results, write, save, tmp_path


def final(result, version="v0"):
    return result.to_dict()["inventory"][0]["runs"][version]["final"]


@pytest.mark.parametrize("mode", ["WALK", "TRANSIT", "DRIVE", None, "BICYCLE"])
@pytest.mark.parametrize("title", ["Walking", "Journey between visits", "Visit Museum C"])
def test_structured_v0_transport_overrides_prose_and_preserves_unknown_mode(batch, mode, title):
    _, results, write, _, _ = batch
    travel = results["v0"]["itinerary"]["days"][0]["activities"][1]
    travel.update(
        title=title,
        notes="Driving from Museum B to Museum A",
        transport={"mode": mode, "from_activity_id": "a", "to_activity_id": "b"},
    )
    out = final(load_batch(write("v0")))
    assert not out["unbound_transport"]
    claim = out["legs"][0]["claims"][0]
    assert claim["original"]["transport"] == travel["transport"]
    assert claim["mode"] == (mode if mode in ("WALK", "TRANSIT", "DRIVE") else None)
    assert out["legs"][0]["journey"]["agreement"] == (
        "consistent" if mode in ("WALK", "TRANSIT", "DRIVE") else "incomplete"
    )


@pytest.mark.parametrize(
    "declaration",
    [
        {"mode": "WALK", "from_activity_id": "b", "to_activity_id": "a"},
        {"mode": "WALK", "from_activity_id": "a", "to_activity_id": "a"},
        {"mode": "WALK", "from_activity_id": "a", "to_activity_id": "missing"},
        {"mode": "WALK", "from_activity_id": "a"},
        {"mode": "WALK", "from_activity_id": ["a"], "to_activity_id": "b"},
        "Walking from Museum A to Museum B",
        [],
        {},
    ],
)
def test_bad_structured_endpoints_never_fall_back_to_supported_prose(batch, declaration):
    _, results, write, _, _ = batch
    travel = results["v0"]["itinerary"]["days"][0]["activities"][1]
    travel["transport"] = declaration
    out = final(load_batch(write("v0")))
    assert len(out["unbound_transport"]) == 1
    assert out["unbound_transport"][0]["original"]["transport"] == declaration
    assert not out["legs"][0]["claims"]


@pytest.mark.parametrize(
    "fault", ["nonadjacent", "overlap", "cross_day", "outside_gap", "bad_clock"]
)
def test_structured_transport_requires_consecutive_same_day_resolved_gap(batch, fault):
    _, results, write, _, _ = batch
    itinerary = results["v0"]["itinerary"]
    acts = itinerary["days"][0]["activities"]
    acts[1]["transport"] = {"mode": "WALK", "from_activity_id": "a", "to_activity_id": "b"}
    if fault == "nonadjacent":
        acts.append(activity("c", "Museum C", "10:21", "10:25", place="Museum C"))
    elif fault == "overlap":
        acts[2]["start_time"] = "2020-01-01T09:30:00+00:00"
    elif fault == "cross_day":
        other = acts.pop()
        other["start_time"] = "2020-01-02T10:30:00+00:00"
        other["end_time"] = "2020-01-02T11:30:00+00:00"
        itinerary["end_date"] = "2020-01-02"
        itinerary["days"].append({"date": "2020-01-02", "activities": [other]})
    elif fault == "outside_gap":
        acts[1]["end_time"] = "2020-01-01T10:40:00+00:00"
    else:
        acts[1]["end_time"] = "invalid"
    out = final(load_batch(write("v0")))
    assert len(out["unbound_transport"]) == 1
    assert all(not leg["claims"] for leg in out["legs"])


@pytest.mark.parametrize(
    "fields",
    [
        {"mode": "DRIVE"},
        {"mode": None},
        {"from_activity_id": "a", "to_activity_id": "b"},
        {"mode": "DRIVE", "from_activity_id": "a", "to_activity_id": "b"},
    ],
)
def test_reviewed_transport_fields_take_precedence_independently(batch, fields):
    manifest, results, write, save, _ = batch
    travel = results["v0"]["itinerary"]["days"][0]["activities"][1]
    has_pair = "from_activity_id" in fields
    travel.update(
        title="Narrative journey",
        transport={
            "mode": "TRANSIT",
            "from_activity_id": "b" if has_pair else "a",
            "to_activity_id": "b",
        },
    )
    write("v0")
    ref = manifest["groups"][0]["selected_runs"]["v0"]["result_ref"]
    review = {
        "group_id": "g",
        "run_id": "run-v0",
        "artifact_sha256": ref["sha256"],
        "pointer": "/itinerary/days/0/activities/1",
        "reviewer_ref": "r",
        "reviewed_at": "now",
        "revision": "1",
        "rationale": "Independent transport review",
        **fields,
    }
    manifest["projection_reviews_ref"] = save(
        "reviews.json",
        {"schema_version": "rtpeval_reviews_1", "batch_id": "batch", "records": [review]},
        "rtpeval_reviews_1",
    )
    out = final(load_batch(write()))
    assert not out["unbound_transport"]
    assert out["legs"][0]["claims"][0]["mode"] == fields.get("mode", "TRANSIT")


def test_null_transport_retains_legacy_binding(batch):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"]["days"][0]["activities"][1]["transport"] = None
    out = final(load_batch(write("v0")))
    assert not out["unbound_transport"]
    assert out["legs"][0]["claims"][0]["mode"] == "WALK"


@pytest.mark.parametrize("version", ["v1", "v2", "v3"])
def test_structured_model_transport_cannot_replace_application_transfers(batch, version):
    _, results, write, _, _ = batch
    results[version]["itinerary"]["days"][0]["activities"][1]["transport"] = {
        "mode": "DRIVE",
        "from_activity_id": "a",
        "to_activity_id": "b",
    }
    results[version]["itinerary"]["transfers"] = [
        {
            "mode": "WALK",
            "from_activity_id": "a",
            "to_activity_id": "b",
            "departure_time": "2020-01-01T10:00:00+00:00",
            "arrival_time": "2020-01-01T10:20:00+00:00",
        }
    ]
    out = final(load_batch(write(version)), version)
    assert len(out["legs"][0]["claims"]) == 1
    assert out["legs"][0]["claims"][0]["kind"] == "transfer"
    assert out["legs"][0]["claims"][0]["mode"] == "WALK"
    assert len(out["ignored_transport"]) == 1


@pytest.mark.parametrize("in_notes", [False, True])
def test_explicit_v0_endpoints_bind_unique_occurrence_gap(batch, in_notes):
    _, results, write, _, _ = batch
    travel = results["v0"]["itinerary"]["days"][0]["activities"][1]
    travel["notes" if in_notes else "title"] = "Walking from Museum A to Museum B"
    out = final(load_batch(write("v0")))
    assert not out["unbound_transport"]
    assert len(out["legs"][0]["claims"]) == 1
    assert out["legs"][0]["claims"][0]["mode"] == "WALK"


@pytest.mark.parametrize("title", ["Walking", "Walking from Museum A to Museum B"])
@pytest.mark.parametrize(
    "notes",
    [
        "Model estimate",
        "Estimated travel time",
        "Bring water if it is sunny",
        "Pass the bus station",
        "Model estimate; prefer to wear comfortable shoes",
    ],
)
def test_v0_generic_notes_do_not_block_supported_transport_binding(batch, title, notes):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"]["days"][0]["activities"][1].update(title=title, notes=notes)
    out = final(load_batch(write("v0")))
    assert not out["unbound_transport"]
    assert len(out["legs"][0]["claims"]) == 1
    assert out["legs"][0]["claims"][0]["mode"] == "WALK"


@pytest.mark.parametrize(
    "title", ["Walking; Estimated travel time", "Walking ; Estimated travel time"]
)
def test_v0_mode_clause_whitespace_does_not_block_transport_binding(batch, title):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"]["days"][0]["activities"][1]["title"] = title
    out = final(load_batch(write("v0")))
    assert not out["unbound_transport"]
    assert len(out["legs"][0]["claims"]) == 1
    assert out["legs"][0]["claims"][0]["mode"] == "WALK"


@pytest.mark.parametrize(
    "title",
    [
        "Walking tour of Museum A",
        "A relaxing morning",
        "Rest",
        "Walk to Museum A",
        "Walk to Museum A and explore its exhibitions",
        "Walking from Museum A to Museum B",
    ],
)
def test_structured_visit_role_survives_descriptive_title(batch, title):
    _, results, write, _, _ = batch
    results["v1"]["itinerary"]["days"][0]["activities"][0]["title"] = title
    out = final(load_batch(write("v1")), "v1")
    assert out["activities"][0]["evaluation_role"] == "primary_visit"
    assert len(out["legs"]) == 1


@pytest.mark.parametrize("title", ["Visit Museum B", "Tour Museum B", "Explore museum district"])
def test_declared_transport_role_is_not_overridden_by_title(batch, title):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"]["days"][0]["activities"][1]["title"] = title
    out = final(load_batch(write("v0")))
    assert out["activities"][1]["evaluation_role"] == "transport"
    assert out["activities"][1]["transport_applicable"] is True
    assert len(out["legs"]) == 1


@pytest.mark.parametrize("title", ["Rest", "Explore the area"])
def test_declared_visit_without_place_is_not_erased_by_placeholder_title(batch, title):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"]["days"][0]["activities"][0].update(title=title, place_name=None)
    out = final(load_batch(write("v0")))
    assert out["activities"][0]["evaluation_role"] == "primary_visit"
    assert len(out["legs"]) == 1


@pytest.mark.parametrize(
    "title,notes,bound",
    [
        ("Walking from Museum A to Museum B", "Model estimate; not live verified", True),
        ("Walking from Museum B to Museum A", "Model estimate", False),
        ("Walking from Museum A to Museum B", "From Museum B to Museum A", False),
        ("Walking from Museum A to Museum B Annex", None, False),
        ("Walking between Museum A and Museum B", None, False),
    ],
)
def test_v0_endpoint_claims_respect_direction_complete_names_and_notes(batch, title, notes, bound):
    _, results, write, _, _ = batch
    acts = results["v0"]["itinerary"]["days"][0]["activities"]
    acts[1].update(title=title, notes=notes)
    acts.extend(
        [
            activity("a2", "Museum A", "12:00", "13:00", place="Museum A"),
            activity("b2", "Museum B", "13:30", "14:30", place="Museum B"),
        ]
    )
    out = final(load_batch(write("v0")))
    assert bool(out["legs"][0]["claims"]) is bound
    assert bool(out["unbound_transport"]) is not bound
    assert not out["legs"][-1]["claims"]


def test_complete_batch_preserves_sources_and_uncertainty(batch):
    _, _, write, _, _ = batch
    result = load_batch(write())
    assert result.status == "accepted"
    out = final(result)
    assert len(out["legs"]) == 1
    assert out["activities"][0]["source"]["pointer"] == "/itinerary/days/0/activities/0"
    assert out["activities"][0]["original"]["source_place_id"] is None
    assert out["legs"][0]["journey"]["representation"] == "single"
    assert not result.data["inventory"][0]["runs"]["v3"]["paired_available"]
    assert not result.data["inventory"][0]["runs"]["v0"]["usage_available"]
    with pytest.raises(TypeError):
        result.data["inventory"][0]["input"]["destination"] = "Changed"
    assert load_batch(write()).to_dict() == result.to_dict()


@pytest.mark.parametrize(
    "fault",
    [
        "hash",
        "version",
        "review",
        "membership",
        "escape",
        "missing_usage",
        "duplicate_id",
        "multi_poi",
        "schema",
    ],
)
def test_invalid_material_never_returns_partial_cohort(batch, fault):
    manifest, results, write, save, _ = batch
    group = manifest["groups"][0]
    if fault == "hash":
        group["input_ref"]["sha256"] = "bad"
    elif fault == "version":
        results["v3"]["system_version"] = "v0"
    elif fault == "review":
        group["requirement_spec_ref"] = save(
            "bad-spec.json", {"schema_version": "rtpeval_requirements_1"}, "rtpeval_requirements_1"
        )
    elif fault == "membership":
        del group["selected_runs"]["v1"]
    elif fault == "escape":
        group["input_ref"]["path"] = "../outside.json"
    elif fault == "missing_usage":
        group["selected_runs"]["v3"]["usage_ref"]["path"] = "absent.json"
    elif fault == "duplicate_id":
        results["v3"]["itinerary"]["days"][0]["activities"][1]["activity_id"] = "a"
    elif fault == "schema":
        results["v3"]["itinerary"]["output_version"] = "itinerary_99"
    else:
        path = write("v3")
        reviews = {
            "schema_version": "rtpeval_reviews_1",
            "batch_id": "batch",
            "records": [
                {
                    "group_id": "g",
                    "run_id": "run-v3",
                    "artifact_sha256": group["selected_runs"]["v3"]["result_ref"]["sha256"],
                    "pointer": "/itinerary/days/0/activities/0",
                    "reviewer_ref": "r",
                    "reviewed_at": "now",
                    "revision": "1",
                    "rationale": "two visits in one block",
                    "multi_poi": True,
                }
            ],
        }
        manifest["projection_reviews_ref"] = save("reviews.json", reviews, "rtpeval_reviews_1")
        result = load_batch(write())
        assert result.status == "needs_material_correction"
        assert result.data["inventory"] == ()
        return
    path = write("v3") if fault in {"version", "duplicate_id", "schema"} else write()
    result = load_batch(path)
    assert result.status == "needs_material_correction"
    assert result.data["inventory"] == ()


def transfer(start="10:00", end="10:20", mode="WALK"):
    return {
        "from_activity_id": "a",
        "to_activity_id": "b",
        "origin_place_id": "wrong-id",
        "destination_place_id": "id-b",
        "mode": mode,
        "departure_time": "2020-01-01T" + start + ":00+00:00",
        "arrival_time": None if end is None else "2020-01-01T" + end + ":00+00:00",
        "validation_state": "PASS",
        "evidence_refs": ["planner-private"],
    }


@pytest.mark.parametrize(
    "kind,agreement",
    [("same", "consistent"), ("conflict", "conflicting"), ("missing", "incomplete")],
)
def test_duplicate_and_conflicting_transport(batch, kind, agreement):
    _, results, write, _, _ = batch
    t = transfer() if kind == "same" else transfer("10:05", "10:25", "DRIVE")
    if kind == "missing":
        t = transfer(end=None)
    results["v1"]["itinerary"]["transfers"] = [transfer(), t]
    out = final(load_batch(write("v1")), "v1")
    journey = out["legs"][0]["journey"]
    assert journey["agreement"] == agreement
    assert len(out["legs"][0]["claims"]) == 2
    if kind == "same":
        assert len(journey["occupancy"]) == 1
        assert len(journey["occupancy"][0]["sources"]) == 2
    else:
        assert journey["occupancy"] == []
    assert "validation_state" not in json.dumps(out)
    assert "planner-private" not in json.dumps(out)
    assert out["legs"][0]["claims"][0]["original"]["origin_place_id"] == "wrong-id"


@pytest.mark.parametrize("version", ["v1", "v2", "v3"])
@pytest.mark.parametrize("has_transfer", [True, False])
def test_tool_versions_never_use_model_transport_fallback(batch, version, has_transfer):
    _, results, write, _, _ = batch
    if has_transfer:
        results[version]["itinerary"]["transfers"] = [transfer("10:05", "10:25", "DRIVE")]
    out = final(load_batch(write(version)), version)
    claims = out["legs"][0]["claims"]
    assert [c["kind"] for c in claims] == (["transfer"] if has_transfer else [])
    assert out["unbound_transport"] == []
    ignored = out["ignored_transport"]
    assert ignored[0]["original"]["activity_id"] == "t"
    assert ignored[0]["source"]["pointer"] == "/itinerary/days/0/activities/1"
    assert any(d["reason"] == "ignored_transport_source" for d in out["diagnostics"])
    assert out["activities"][1]["transport_applicable"] is False


def test_v0_ignores_transfer_and_preserves_model_transport(batch):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"]["transfers"] = [transfer("10:05", "10:25", "DRIVE")]
    out = final(load_batch(write("v0")))
    assert [c["kind"] for c in out["legs"][0]["claims"]] == ["activity"]
    assert out["legs"][0]["journey"]["occupancy"][0]["mode"] == "WALK"
    assert out["activities"][1]["transport_applicable"] is True
    assert out["ignored_transport"][0]["source"]["pointer"] == "/itinerary/transfers/0"


def test_v3_optional_projections_use_transfers_only(batch):
    _, results, write, _, _ = batch
    it = results["v3"]["itinerary"]
    it["transfers"] = [transfer("10:05", "10:25", "DRIVE")]
    results["v3"]["v3"] = {"draft": copy.deepcopy(it), "final_primary": copy.deepcopy(it)}
    result = load_batch(write("v3")).to_dict()
    run = result["inventory"][0]["runs"]["v3"]
    for key in ("draft", "final_primary"):
        out = run["optional"][key]
        assert [c["kind"] for c in out["legs"][0]["claims"]] == ["transfer"]
        assert out["ignored_transport"][0]["source"]["pointer"].startswith("/v3/" + key)


def test_repeated_actual_journeys_keep_distinct_occurrence_sources(batch):
    _, results, write, _, _ = batch
    it = results["v1"]["itinerary"]
    it["days"][0]["activities"].extend(
        [
            activity("a2", "Museum A", "12:00", "13:00", place="Museum A"),
            activity("b2", "Museum B", "13:30", "14:30", place="Museum B"),
        ]
    )
    later = transfer("13:00", "13:20")
    later.update(from_activity_id="a2", to_activity_id="b2")
    it["transfers"] = [transfer(), later]
    out = final(load_batch(write("v1")), "v1")
    assert len(out["legs"]) == 3
    assert [len(leg["claims"]) for leg in out["legs"]] == [1, 0, 1]
    assert out["legs"][0]["from_source"] != out["legs"][2]["from_source"]
    assert (
        out["legs"][0]["journey"]["occupancy"][0]["start"]
        != (out["legs"][2]["journey"]["occupancy"][0]["start"])
    )


def test_review_replay_and_source_order(batch):
    manifest, results, write, save, _ = batch
    acts = results["v0"]["itinerary"]["days"][0]["activities"]
    acts[1]["title"] = "A scenic walk between Museum A and Museum B"
    acts.reverse()
    write("v0")
    result = load_batch(write())
    assert final(result)["unbound_transport"]
    ref = manifest["groups"][0]["selected_runs"]["v0"]["result_ref"]
    review = {
        "group_id": "g",
        "run_id": "run-v0",
        "artifact_sha256": ref["sha256"],
        "pointer": "/itinerary/days/0/activities/1",
        "reviewer_ref": "r",
        "reviewed_at": "now",
        "revision": "1",
        "rationale": "explicit endpoints",
        "from_activity_id": "a",
        "to_activity_id": "b",
        "mode": "WALK",
    }
    manifest["projection_reviews_ref"] = save(
        "reviews.json",
        {"schema_version": "rtpeval_reviews_1", "batch_id": "batch", "records": [review]},
        "rtpeval_reviews_1",
    )
    out = final(load_batch(write()))
    assert out["legs"][0]["from_source"]["pointer"].endswith("/2")
    assert not out["unbound_transport"]
    assert load_batch(write()).to_dict() == load_batch(write()).to_dict()


def test_generic_place_and_protected_requirement(batch):
    manifest, results, write, save, root = batch
    acts = results["v0"]["itinerary"]["days"][0]["activities"]
    acts.append(activity("f", "Free time", "12:00", "13:00", "generic_activity"))
    acts[0]["activity_kind"] = "unknown"
    ref = manifest["groups"][0]["requirement_spec_ref"]
    spec = json.loads((root / ref["path"]).read_text())
    spec["obligations"] = [
        {
            "obligation_id": "protected",
            "kind": "protected_time",
            "resolution": "resolved",
            "source_refs": [{"field_path": "start_date"}],
            "start": "12:00",
            "end": "13:00",
        }
    ]
    manifest["groups"][0]["requirement_spec_ref"] = save(ref["path"], spec, spec["schema_version"])
    result = load_batch(write("v0"))
    assert final(result)["activities"][0]["evaluation_role"] == "primary_visit"
    assert final(result)["activities"][-1]["evaluation_role"] == "transition"
    assert (
        result.data["inventory"][0]["requirement_spec"]["obligations"][0]["obligation_id"]
        == "protected"
    )


def test_invalid_clock_is_not_material_rejection(batch):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"]["days"][0]["activities"][0]["end_time"] = "bad"
    result = load_batch(write("v0"))
    assert result.status == "accepted"
    assert "adjacency_unresolved" in [d["reason"] for d in final(result)["diagnostics"]]
    assert final(result)["legs"] == []


def test_dangling_transfer_is_not_retargeted(batch):
    _, results, write, _, _ = batch
    t = transfer()
    t["from_activity_id"] = "absent"
    results["v2"]["itinerary"]["transfers"] = [t]
    out = final(load_batch(write("v2")), "v2")
    assert out["unbound_transport"][0]["original"]["from_activity_id"] == "absent"
    assert out["legs"][0]["claims"] == []


def test_segments_remain_segments(batch):
    _, results, write, _, _ = batch
    acts = results["v0"]["itinerary"]["days"][0]["activities"]
    acts[1]["end_time"] = "2020-01-01T10:10:00+00:00"
    acts.append(activity("t2", "Public transit", "10:10", "10:20", "transport"))
    out = final(load_batch(write("v0")))
    assert out["legs"][0]["journey"]["representation"] == "segments"
    assert len(out["legs"][0]["journey"]["occupancy"]) == 2


def test_internal_findings_cannot_change_projection_except_source_hash(batch):
    _, results, write, _, _ = batch
    results["v3"]["v3"] = {
        "draft": copy.deepcopy(results["v3"]["itinerary"]),
        "final_primary": copy.deepcopy(results["v3"]["itinerary"]),
        "final_report": {"verdict": "PASS"},
    }
    before = final(load_batch(write("v3")), "v3")
    results["v3"]["v3"]["final_report"]["verdict"] = "FAIL"
    after = final(load_batch(write("v3")), "v3")

    def semantic(value):
        if isinstance(value, dict):
            return {
                k: semantic(v)
                for k, v in value.items()
                if k not in {"record_id", "artifact_sha256"}
            }
        if isinstance(value, list):
            return [semantic(v) for v in value]
        return value

    assert semantic(before) == semantic(after)
    assert "final_report" not in json.dumps(after)


def test_cli_and_duplicate_json_keys(batch, capsys):
    _, _, write, _, root = batch
    assert main([str(write())]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "accepted"
    (root / "manifest.json").write_text('{"schema_version": "x", "schema_version": "y"}')
    assert main([str(root / "manifest.json")]) == 2
    assert json.loads(capsys.readouterr().out)["inventory"] == []


@pytest.mark.parametrize(
    "field,value",
    [("days", None), ("days", [{}]), ("output_version", []), ("days", [{"date": []}])],
)
def test_malformed_wire_returns_diagnostic(batch, field, value):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"][field] = value
    result = load_batch(write("v0"))
    assert result.status == "needs_material_correction"
    assert not result.data["inventory"]


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1e999"])
def test_nonfinite_json_is_rejected(batch, value):
    _, _, write, _, root = batch
    write()
    (root / "manifest.json").write_text('{"value": ' + value + "}")
    assert load_batch(root / "manifest.json").status == "needs_material_correction"


def test_unknown_role_requires_review_without_denominator_deletion(batch):
    _, results, write, _, _ = batch
    acts = results["v0"]["itinerary"]["days"][0]["activities"]
    acts.append(activity("u", "A special experience", "10:00", "10:15", "unknown"))
    result = load_batch(write("v0"))
    assert result.status == "accepted"
    out = final(result)
    assert len(out["activities"]) == 4
    assert out["activities"][-1]["evaluation_role"] == "unresolved"
    assert out["legs"][0]["adjacency_status"] == "unresolved"


def test_no_interday_leg_and_no_claimed_id_shortcut(batch):
    _, results, write, _, _ = batch
    it = results["v0"]["itinerary"]
    acts = it["days"][0]["activities"]
    acts[0]["source_place_id"] = "same-claimed-id"
    acts[2]["source_place_id"] = "same-claimed-id"
    other = activity("c", "Museum C", "09:00", "10:00", place="Museum C")
    for k in ("start_time", "end_time"):
        other[k] = other[k].replace("2020-01-01", "2020-01-02")
    it["days"].append({"date": "2020-01-02", "activities": [other]})
    result = load_batch(write("v0"))
    assert len(final(result)["legs"]) == 1
    assert final(result)["legs"][0]["from_activity_id"] == "a"


def test_stale_review_hash_is_a_material_error(batch):
    manifest, _, write, save, _ = batch
    manifest["projection_reviews_ref"] = save(
        "reviews.json",
        {
            "schema_version": "rtpeval_reviews_1",
            "batch_id": "batch",
            "records": [
                {
                    "group_id": "g",
                    "run_id": "run-v0",
                    "artifact_sha256": "stale",
                    "pointer": "/itinerary/days/0/activities/1",
                    "reviewer_ref": "r",
                    "reviewed_at": "now",
                    "revision": "1",
                    "rationale": "reviewed",
                    "role": "transport",
                }
            ],
        },
        "rtpeval_reviews_1",
    )
    assert load_batch(write()).status == "needs_material_correction"


def test_missing_request_structure_is_not_accepted(batch):
    manifest, _, write, save, root = batch
    group = manifest["groups"][0]
    original = json.loads((root / "input.json").read_text())
    del original["start_date"]
    group["input_ref"] = save("input.json", original)
    result = load_batch(write())
    assert result.status == "needs_material_correction"


def test_source_quote_must_match_input(batch):
    manifest, _, write, save, root = batch
    group = manifest["groups"][0]
    spec = json.loads((root / "requirements.json").read_text())
    spec["obligations"] = [
        {
            "obligation_id": "x",
            "kind": "protected_time",
            "resolution": "unsupported",
            "source_refs": [
                {"field_path": "additional_preferences", "quote": "invented", "occurrence": 0}
            ],
        }
    ]
    group["requirement_spec_ref"] = save("requirements.json", spec, spec["schema_version"])
    assert load_batch(write()).status == "needs_material_correction"


def test_link_escape_resolves_before_read(batch, tmp_path):
    manifest, _, write, _, root = batch
    outside = tmp_path.parent / (tmp_path.name + "-outside.json")
    outside.write_text("{}")
    link = root / "linked.json"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Host does not grant symlink creation privileges")
    manifest["groups"][0]["input_ref"]["path"] = "linked.json"
    result = load_batch(write())
    assert result.status == "needs_material_correction"
    assert "escapes" in result.data["material_diagnostics"][0]["explanation"]


def test_no_planner_import_or_network_on_intake(batch, monkeypatch):
    import ast
    import socket
    from pathlib import Path

    def forbidden(*args, **kwargs):
        raise AssertionError("No network is permitted during intake")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert load_batch(batch[2]()).status == "accepted"
    allowed = {
        "statistics",
        "argparse",
        "json",
        "hashlib",
        "math",
        "re",
        "datetime",
        "pathlib",
        "collections",
        "dataclasses",
        "types",
        "unicodedata",
        "asyncio",
        "zoneinfo",
        "decimal",
        "fractions",
        "random",
        "importlib",
        "tzdata",
    }
    # Ticket 11 explicitly executes frozen V3 through its isolated controlled boundary.
    # Ordinary intake/scorers retain the planner-free import contract.
    controlled = {
        "_controlled_facts",
        "_controlled_goals",
        "_controlled_ports",
        "controlled_batch",
        "controlled_cli",
        "controlled_models",
        "controlled_preparation",
        "controlled_replay",
        "controlled_report",
    }
    # #87 isolates credential/HTTP access in the formal execution boundary.
    # Token counting is a pure offline helper, not a planner or evidence client.
    execution_imports = {
        "projection": {"backend.activity_semantics"},  # Pure declaration grammar only.
        "declared_population": {"backend.activity_semantics"},
        "activity_semantics": {"typing"},
        "daily_density": {"backend.pace_policy"},  # Numeric rules only; no planner state.
        "evaluation_run": {"httpx"},
        "opening_run": {"httpx"},  # #90 isolates one incremental model attempt here.
        "paired_execution": {"os", "shutil", "httpx", "dotenv"},  # Explicit acquire execute.
        "paired_run": {"os", "shutil"},  # Fresh-path checks and offline exact-byte copies.
        "snapshot_import": {"copy"},  # Offline source-labelled observation copies.
        "v3_correspondence": {"copy"},  # Offline adopted-itinerary lineage copies.
        "generation_import": {"urllib"},  # URL parsing only; no provider client.
        "evaluation_transport": {"httpx", "urllib", "backend.app.runtime.token_counting"},
        "evaluation_run_cli": {"os", "dotenv"},
        "suite": {"base64", "os", "dotenv"},  # Credential reads stay in explicit execute.
        "suite_external": {"base64", "copy"},  # Exact-byte offline attachment retention.
        "suite_research": {"base64", "copy"},  # Source-bound offline research retention.
        "suite_tracks": {"base64"},  # Frozen artifact inventory only.
    }
    for path in [*Path("backend/evaluation").glob("*.py"), Path("backend/activity_semantics.py")]:
        if path.stem in controlled:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        permitted = allowed | execution_imports.get(path.stem, set())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(n.name.split(".")[0] in permitted for n in node.names)
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                assert node.module in permitted or node.module.split(".")[0] in permitted


@pytest.mark.parametrize(
    "title,note,mode",
    [
        ("Walking", "Estimated, not live verified", "WALK"),
        ("Walking", "Bring water if it is sunny", "WALK"),
        ("Walking", "Pass the bus station", "WALK"),
        ("Walking from Museum A to Museum B", "Pass the bus station", "WALK"),
        ("Public transit", "Walk around after arrival", "TRANSIT"),
        ("Driving", "Train station nearby", "DRIVE"),
        ("Do not walk; use driving", None, None),
        ("Walk or drive", None, None),
        ("Walking; Driving", None, None),
        ("Transfer", "Walking might be possible", None),
    ],
)
def test_v0_explicit_title_mode_is_not_inferred_from_notes(batch, title, note, mode):
    _, results, write, _, _ = batch
    a = results["v0"]["itinerary"]["days"][0]["activities"][1]
    a.update(title=title, notes=note)
    out = final(load_batch(write("v0")))
    all_claims = out["unbound_transport"] + out["legs"][0]["claims"]
    assert all_claims[0]["mode"] == mode


def test_resolved_escape_is_rejected_without_opening(batch, monkeypatch):
    from pathlib import Path

    manifest, _, write, _, root = batch
    manifest["groups"][0]["input_ref"]["path"] = "resolved-link.json"
    path = write()
    original = Path.resolve

    def resolve(instance, *args, **kwargs):
        if instance.name == "resolved-link.json":
            return root.parent / "outside.json"
        return original(instance, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    result = load_batch(path)
    assert result.status == "needs_material_correction"
    assert "escapes" in result.data["material_diagnostics"][0]["explanation"]


def test_movement_title_preserves_visit_role_and_parsed_source(batch):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"]["days"][0]["activities"][0]["title"] = (
        "Walking from Museum A to Museum B"
    )
    activity = final(load_batch(write("v0")))["activities"][0]
    assert activity["evaluation_role"] == "primary_visit"
    assert activity["reason"] == "declared_visit"
    claim = activity["competing_claim"]
    assert claim["source"] == activity["source"]
    assert claim["field"] == "title"
    assert claim["original"] == "Walking from Museum A to Museum B"
    assert claim["parsed"] == {"kind": "movement", "origin": "museum a", "destination": "museum b"}


def test_optional_corrupt_draft_does_not_reject_final(batch):
    _, results, write, _, _ = batch
    results["v3"]["v3"] = {"draft": {"output_version": []}, "final_primary": None}
    result = load_batch(write("v3"))
    assert result.status == "accepted"
    assert not result.data["inventory"][0]["runs"]["v3"]["paired_available"]


def test_historical_wire_and_timezone_uncertainty_are_preserved(batch):
    _, results, write, _, _ = batch
    it = results["v0"]["itinerary"]
    del it["output_version"]
    for a in it["days"][0]["activities"]:
        for key in ("start_time", "end_time"):
            a[key] = a[key].removesuffix("+00:00")
    result = load_batch(write("v0"))
    assert result.status == "accepted"
    out = final(result)
    assert "output_version" in out["absent_fields"]
    assert any(d["reason"] == "timezone_unresolved" for d in out["diagnostics"])
    assert out["activities"][0]["original"]["start_time"] == "2020-01-01T09:00:00"


@pytest.mark.parametrize(
    "field", ["missing", "group_id", "run_id", "version", "input_sha256", "result_sha256"]
)
def test_selected_run_requires_full_input_provenance(batch, field):
    manifest, _, write, save, root = batch
    run = manifest["groups"][0]["selected_runs"]["v0"]
    if field == "missing":
        del run["provenance_ref"]
    else:
        value = json.loads((root / "v0-provenance.json").read_text(encoding="utf-8"))
        value[field] = "wrong"
        run["provenance_ref"] = save("v0-provenance.json", value, "rtpeval_provenance_1")
    result = load_batch(write()).to_dict()
    assert result["status"] == "needs_material_correction"
    assert result["inventory"] == []


@pytest.mark.parametrize("start", ["09:00", "09:30"])
def test_overlapping_visits_preserve_sources_and_uncertain_adjacency(batch, start):
    _, results, write, _, _ = batch
    results["v0"]["itinerary"]["days"][0]["activities"][2]["start_time"] = (
        "2020-01-01T" + start + ":00+00:00"
    )
    result = load_batch(write("v0"))
    assert result.status == "accepted"
    projection = final(result)
    assert projection["legs"][0]["adjacency_status"] == "unresolved"
    assert any(d["reason"] == "overlapping_visit_intervals" for d in projection["diagnostics"])
    assert len(projection["activities"]) == 3


def test_reviewed_transport_binding_survives_overlapping_visits(batch):
    manifest, results, write, save, _ = batch
    results["v0"]["itinerary"]["days"][0]["activities"][2]["start_time"] = (
        "2020-01-01T09:30:00+00:00"
    )
    write("v0")
    ref = manifest["groups"][0]["selected_runs"]["v0"]["result_ref"]
    review = {
        "group_id": "g",
        "run_id": "run-v0",
        "artifact_sha256": ref["sha256"],
        "pointer": "/itinerary/days/0/activities/1",
        "reviewer_ref": "r",
        "reviewed_at": "now",
        "revision": "1",
        "rationale": "explicit endpoints",
        "from_activity_id": "a",
        "to_activity_id": "b",
        "mode": "WALK",
    }
    manifest["projection_reviews_ref"] = save(
        "reviews.json",
        {
            "schema_version": "rtpeval_reviews_1",
            "batch_id": "batch",
            "records": [review],
        },
        "rtpeval_reviews_1",
    )
    out = final(load_batch(write()))
    assert out["legs"][0]["adjacency_status"] == "unresolved"
    assert out["legs"][0]["claims"][0]["association_status"] == "unique"
    assert not out["unbound_transport"]
