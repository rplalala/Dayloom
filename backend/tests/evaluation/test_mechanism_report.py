"""Independent mechanism counts from exact saved sources, never rescored itineraries."""

import copy
import hashlib
import json

import pytest

from backend.evaluation.mechanism_preparation import prepare_sources, read_batch_sources
from backend.evaluation.mechanism_report import report_mechanism
from backend.tests.evaluation.test_intake import batch as selected_batch
from backend.tests.versions.v3.test_multiround import SequenceModel, stage
from backend.tests.versions.v3.test_repair import edit

batch = selected_batch


def selected(outcome=None, version="v3", observations=()):
    result = {"system_version": version}
    if outcome is not None:
        result["v3"] = outcome
    raw = json.dumps(result)
    sha = hashlib.sha256(raw.encode()).hexdigest()
    selection = {
        "status": "accepted",
        "batch_id": "b",
        "revision": "1",
        "inventory": [
            {
                "group_id": "g",
                "input_sha256": "a" * 64,
                "runs": {
                    version: {
                        "final": {
                            "context": {
                                "run_id": "r",
                                "artifact_sha256": sha,
                            }
                        }
                    }
                },
            }
        ],
    }
    sources = {
        "records": [
            {
                "group_id": "g",
                "run_id": "r",
                "version": version,
                "input_sha256": "a" * 64,
                "result_sha256": sha,
                "raw_utf8": raw,
            }
        ]
    }
    return prepare_sources(selection, sources, observations=observations)


def actual_outcome():
    repair = stage(SequenceModel([[edit("10:50", "11:50")], RuntimeError("offline failure")]))
    return {
        "original_report": repair.original_report.model_dump(mode="json"),
        "scope": repair.scope.model_dump(mode="json"),
        "repair": repair.model_dump(mode="json"),
    }


def test_missing_v3_is_unavailable_and_earlier_versions_are_not_applicable():
    for version, status in [("v3", "unavailable"), ("v1", "not_applicable")]:
        run = report_mechanism(selected(version=version))["runs"][0]
        assert run["coverage"] == status
        assert run["model_attempts"] is None


def test_actual_multiround_has_two_attempts_without_counting_cumulative_summary():
    report = report_mechanism(selected(actual_outcome()))
    run = report["runs"][0]
    assert run["model_attempts"] == 2
    assert len(run["rounds"]) == 2
    assert run["accepted_rounds"] == 1
    assert report["fractions"]["run_acceptance"]["denominator"] == 1
    assert report["fractions"]["round_acceptance"]["denominator"] == 2
    assert run["internal_progress"][0]["outcome"] == "improved"
    assert "independently_verified" not in run


def test_exact_round_duplicates_keep_references_but_conflicts_invalidate_channel():
    outcome = actual_outcome()
    outcome["repair"]["rounds"].append(copy.deepcopy(outcome["repair"]["rounds"][0]))
    run = report_mechanism(selected(outcome))["runs"][0]
    assert run["model_attempts"] == 2
    assert len(run["rounds"][0]["source_refs"]) == 2
    outcome["repair"]["rounds"][-1]["result"]["status"] = "REJECTED"
    run = report_mechanism(selected(outcome))["runs"][0]
    assert run["coverage"] == "needs_material_correction"
    assert run["model_attempts"] is None


def test_four_version_reader_keeps_real_selection_and_missing_metadata(batch):
    *_, write, _, _ = batch
    preparation = read_batch_sources(write())
    assert len(preparation.to_dict()["runs"]) == 4
    assert [r["coverage"] for r in report_mechanism(preparation)["runs"]] == [
        "not_applicable",
        "not_applicable",
        "not_applicable",
        "unavailable",
    ]


def observed(base, channel, content):
    from backend.evaluation.records import canonical_digest

    run = base["runs"][0]
    link = {k: run[k] for k in ("group_id", "run_id", "version", "input_sha256", "result_sha256")}
    return {
        **link,
        "channel": channel,
        "content": content,
        "content_sha256": canonical_digest(content),
    }


def test_partial_trace_preserves_cells_without_inventing_model_attempt_denominator():
    base = selected().to_dict()
    content = {
        "events": [
            {
                "event": "v3_repair_round",
                "payload": {
                    "round_index": 1,
                    "status": "ACCEPTED_PARTIAL",
                    "cumulative_counters": {"model": 1},
                },
            }
        ]
    }
    row = observed(base, "trace", content)
    base["runs"][0]["channels"]["trace"].update(
        status="available", records=[row, copy.deepcopy(row)]
    )
    run = report_mechanism(base)["runs"][0]
    assert run["model_attempts"] is None
    assert run["trace_coverage"] == "partial"
    assert len(run["trace_observations"]) == 1


@pytest.mark.parametrize("field", ["result_sha256", "content_sha256"])
def test_foreign_optional_hash_does_not_remove_valid_mechanism_counts(field):
    base = selected(actual_outcome()).to_dict()
    row = observed(base, "trace", {"events": []})
    row[field] = "f" * 64
    base["runs"][0]["channels"]["trace"].update(status="available", records=[row])
    run = report_mechanism(base)["runs"][0]
    assert run["model_attempts"] == 2
    assert run["trace_coverage"] == "needs_material_correction"


def test_tampered_preparation_cannot_keep_old_result_hash_and_mechanism_counts():
    base = selected(actual_outcome()).to_dict()
    base["runs"][0]["result"]["v3"]["repair"]["rounds"] = []
    run = report_mechanism(base)["runs"][0]
    assert run["model_attempts"] is None
    assert run["coverage"] == "needs_material_correction"


def test_components_pending_and_unattempted_are_separate_from_evaluated_acceptance():
    outcome = actual_outcome()
    components = outcome["repair"]["rounds"][0]["result"]["components"]
    components.extend(
        [
            {"component_id": "not-attempted", "status": "not_attempted", "comparison": None},
            {"component_id": "pending", "status": "pending", "comparison": {"accepted": False}},
        ]
    )
    report = report_mechanism(selected(outcome))
    run = report["runs"][0]
    assert run["pending_components"] == 1
    assert run["unevaluated_components"] == 1
    assert run["evaluated_components"] == 2
    assert report["fractions"]["component_acceptance"]["numerator"] == 1


def test_original_and_related_targets_are_distinct_round_inventories():
    outcome = actual_outcome()
    repair = outcome["repair"]
    repair["related_targets"] = [{"permission": {"target_id": "related:coverage"}}]
    repair["rounds"][1]["target_links"]["related:coverage"] = "related:coverage"
    run = report_mechanism(selected(outcome))["runs"][0]
    assert run["coverage"] == "available"
    assert "related:coverage" not in run["authorized_targets"]
    assert run["rounds"][1]["related_target_links"] == {"related:coverage": "related:coverage"}


def test_missing_multiround_children_cannot_be_inferred_as_one_attempt():
    outcome = actual_outcome()
    outcome["repair"]["rounds"] = []
    run = report_mechanism(selected(outcome))["runs"][0]
    assert run["coverage"] == "needs_material_correction"
    assert run["model_attempts"] is None


def test_trace_copy_of_saved_round_is_not_an_extra_attempt():
    base = selected(actual_outcome()).to_dict()
    row = observed(
        base,
        "trace",
        {
            "events": [
                {
                    "event": "v3_repair_round",
                    "payload": {
                        "round_index": 1,
                        "status": "ACCEPTED_PARTIAL",
                        "cumulative_counters": {"model": 1},
                    },
                }
            ]
        },
    )
    base["runs"][0]["channels"]["trace"].update(status="available", records=[row])
    run = report_mechanism(base)["runs"][0]
    assert run["model_attempts"] == 2
    assert len(run["rounds"]) == 2 and len(run["trace_observations"]) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("continuation_reason", "wrong_stop_reason"),
        ("cumulative_counters", {"model": 999}),
        ("usage", {"foreign-model": {"total_tokens": 999}}),
        ("strategy", "replan"),
        ("exploration_transition", False),
        ("best_promoted", False),
    ],
)
def test_trace_conflicting_shared_round_cells_are_local_material_errors(field, value):
    base = selected(actual_outcome()).to_dict()
    saved = base["runs"][0]["result"]["v3"]["repair"]["rounds"][0]
    payload = {
        "round_index": saved["round_index"],
        "status": saved["result"]["status"],
        "continuation_reason": saved["continuation_reason"],
        "cumulative_counters": saved["result"]["counters"],
        "usage": saved["usage"],
    }
    payload[field] = value
    row = observed(base, "trace", {"events": [{"event": "v3_repair_round", "payload": payload}]})
    base["runs"][0]["channels"]["trace"].update(status="available", records=[row])
    report = report_mechanism(base)
    run = report["runs"][0]
    assert run["model_attempts"] == 2 and run["coverage"] == "available"
    assert run["trace_coverage"] == "needs_material_correction"
    assert report["status"] == "needs_material_correction"


def test_separate_usage_does_not_add_to_cumulative_or_round_token_observations():
    base = selected(actual_outcome()).to_dict()
    run = base["runs"][0]
    link = {k: run[k] for k in ("group_id", "run_id", "version", "result_sha256")}
    content = {
        **link,
        "schema_version": "rtpeval_usage_1",
        "collection_status": "available",
        "coverage": {"adapter_coverage": "default_adapters"},
        "model_calls": [
            {"event_id": "one", "input_tokens": 7, "output_tokens": 3, "total_tokens": 10}
        ],
        "provider_events": [],
        "cache_events": [],
    }
    row = observed(base, "usage", content)
    run["channels"]["usage"].update(status="available", records=[row, copy.deepcopy(row)])
    report = report_mechanism(base)["runs"][0]
    assert report["usage"]["report"]["metrics"]["total_tokens"] == 10
    assert report["model_attempts"] == 2


def test_search_mechanism_keeps_derived_pace_targets_and_separate_promotions():
    from backend.tests.versions.v3.test_repair_search import deletion, execute, move

    repair, _ = execute([[move("d0_2", 1)], [deletion("d0_2", 1)], [deletion("d2_2", 2)]])
    outcome = {
        "original_report": repair.original_report.model_dump(mode="json"),
        "scope": repair.scope.model_dump(mode="json"),
        "repair": repair.model_dump(mode="json"),
    }
    report = report_mechanism(selected(outcome))
    run = report["runs"][0]
    assert run["coverage"] == "available", run["diagnostics"]
    assert run["model_attempts"] == 3
    assert run["exploration_transitions"] == 3
    assert run["best_promotions"] == 2
    assert run["selected_lineage_rounds"] == 3
    assert run["rounds"][1]["derived_target_links"]
    assert run["rounds"][0]["best_promoted"] is False
    assert run["rounds"][0]["strategy"] == "local"


def test_legacy_mechanism_does_not_invent_search_fields_or_change_sources():
    outcome = actual_outcome()
    repair = outcome["repair"]
    for name in ("search_version", "selected_round_index", "selected_semantic_assessments"):
        repair.pop(name, None)
    for row in repair["rounds"]:
        for name in (
            "strategy",
            "base_state",
            "best_state",
            "exploration_transition",
            "best_promoted",
        ):
            row.pop(name, None)
    before = copy.deepcopy(outcome)
    run = report_mechanism(selected(outcome))["runs"][0]
    assert run["coverage"] == "available"
    assert run["model_attempts"] == 2 and run["accepted_rounds"] == 1
    assert "exploration_transitions" not in run
    assert "strategy" not in run["rounds"][0]
    assert outcome == before
