"""Source composition and route continuity across independently scored stages."""

import copy

import pytest

from backend.evaluation.v3_correspondence import prepare_v3_correspondence, read_v3_result_sources
from backend.tests.evaluation import test_v3_pair_report as pairs

pytest_plugins = ("backend.tests.evaluation.test_intake",)
pair_case = pairs.pair_case
route_case = pairs.route_case
prepared_scenario = pairs.prepared_scenario


def test_multiround_replacements_compose_slot_without_multiplying_visit_loss(pair_case, batch):
    def after(itinerary):
        itinerary["days"][0]["activities"][0].update(
            place_name="Gallery C", title="Gallery C", source_place_id="canonical-Gallery C"
        )

    def repair_change(repair):
        middle = copy.deepcopy(repair["original"])
        middle["days"][0]["activities"][0].update(
            place_name="Park D", title="Park D", source_place_id="canonical-Park D"
        )
        first = pairs.adopted_edit(
            repair["original"],
            middle,
            [
                pairs.edit(
                    "replace",
                    place_id="canonical-Park D",
                    start_time="2020-01-01T09:00:00Z",
                    end_time="2020-01-01T10:00:00Z",
                )
            ],
        )["rounds"][0]
        second = repair["rounds"][0]
        second["round_index"] = 2
        second["input_itinerary"] = copy.deepcopy(middle)
        second["result"]["original"] = copy.deepcopy(middle)
        repair["rounds"] = [first, second]

    case = pair_case(
        after=after,
        edits=[
            pairs.edit(
                "replace",
                place_id="canonical-Gallery C",
                start_time="2020-01-01T09:00:00Z",
                end_time="2020-01-01T10:00:00Z",
            )
        ],
        repair_change=repair_change,
    )
    pair = pairs.report(
        case, result_sources=read_v3_result_sources(case[0], batch[4] / "manifest.json")
    )["groups"][0]
    relation = next(r for r in pair["correspondence"]["relations"] if r["relation"] == "replaced")
    assert [event["round_index"] for event in relation["edit_sources"]] == [1, 2]
    assert pair["visit_changes"]["replaced_count"] == 1
    assert pair["visit_changes"]["confirmed_venue_loss_count"] == 1
    assert pair["visit_changes"]["removed_count"] == 0
    route = pair["continuity"]["routes"][0]
    assert route["before"] is not None and route["after"] is not None
    assert route["transition"] == "not_comparable"
    assert route["connection_lineage"] == "continued_endpoints"
    assert route["context_changed"] is True


def test_deleted_endpoint_is_structural_route_removal_not_a_repair(pair_case, batch):
    def after(itinerary):
        itinerary["days"][0]["activities"].pop(0)
        itinerary["transfers"] = []

    case = pair_case(after=after, edits=[pairs.edit("delete")])
    pair = pairs.report(
        case, result_sources=read_v3_result_sources(case[0], batch[4] / "manifest.json")
    )["groups"][0]
    assert pair["continuity"]["routes"][0]["transition"] == "structural_leg_removed"


def test_route_adjacency_insertion_records_old_direct_leg_and_two_new_legs(pair_case, batch):
    def after(itinerary):
        visit = copy.deepcopy(itinerary["days"][0]["activities"][0])
        visit.update(
            activity_id="repair_r1_1",
            title="Gallery C",
            place_name="Gallery C",
            source_place_id="canonical-Gallery C",
            start_time="2020-01-01T10:10:00Z",
            end_time="2020-01-01T10:40:00Z",
        )
        itinerary["days"][0]["activities"].insert(1, visit)
        itinerary["transfers"] = []

    case = pair_case(
        after=after,
        edits=[
            pairs.edit(
                "add",
                None,
                place_id="canonical-Gallery C",
                start_time="2020-01-01T10:10:00Z",
                end_time="2020-01-01T10:40:00Z",
            )
        ],
    )
    pair = pairs.report(
        case, result_sources=read_v3_result_sources(case[0], batch[4] / "manifest.json")
    )["groups"][0]
    transitions = [r["transition"] for r in pair["continuity"]["routes"]]
    assert transitions.count("structural_leg_removed") == 1
    assert transitions.count("structural_leg_added") == 2


@pytest.mark.parametrize("status", ["SKIPPED", "REJECTED"])
def test_unmodified_skipped_or_rejected_pairs_remain_eligible(pair_case, batch, status):
    def repair_change(repair):
        repair["rounds"][0]["result"]["status"] = status

    case = pair_case(edits=[], repair_change=repair_change)
    pair = pairs.report(
        case, result_sources=read_v3_result_sources(case[0], batch[4] / "manifest.json")
    )["groups"][0]
    assert pair["pair_status"] == "available"
    assert pair["deltas"]["auxiliary_total"]["percentage_points"] == 0
    assert pair["correspondence"]["unresolved"] == {"before": [], "after": []}


def test_source_snapshots_support_unchanged_repeated_occurrences_without_repair(pair_case, batch):
    def before(itinerary):
        duplicate = copy.deepcopy(itinerary["days"][0]["activities"][0])
        duplicate["activity_id"] = "a2"
        itinerary["days"][0]["activities"].append(duplicate)

    case = pair_case(before=before)
    sources = read_v3_result_sources(case[0], batch[4] / "manifest.json")
    prepared = prepare_v3_correspondence(case[0], case[1], sources).to_dict()
    assert prepared["groups"][0]["unresolved"] == {"before": [], "after": []}
    assert prepared["groups"][0]["coverage"]["before"]["unresolved_count"] == 0


def test_review_cannot_call_observed_time_change_unchanged(pair_case):
    case = pair_case(before=pairs.repeated_before, after=pairs.retimed_after)
    review = pairs.correspondence_review(case, relation="unchanged")
    out = pairs.report(case, correspondence_reviews=review)
    assert out["status"] == "needs_material_correction"
    assert out["groups"] == []


def test_review_cannot_override_validated_replacement(pair_case, batch):
    def after(itinerary):
        itinerary["days"][0]["activities"][0].update(
            title="Gallery C", place_name="Gallery C", source_place_id="canonical-Gallery C"
        )

    case = pair_case(
        after=after,
        edits=[
            pairs.edit(
                "replace",
                place_id="canonical-Gallery C",
                start_time="2020-01-01T09:00:00Z",
                end_time="2020-01-01T10:00:00Z",
            )
        ],
    )
    out = pairs.report(
        case,
        result_sources=read_v3_result_sources(case[0], batch[4] / "manifest.json"),
        correspondence_reviews=pairs.correspondence_review(case),
    )
    assert out["status"] == "needs_material_correction"
    assert out["groups"] == []


def test_empty_pair_mask_and_unresolved_population_do_not_impute_zero(pair_case):
    def empty(itinerary):
        itinerary["days"][0]["activities"] = []
        itinerary["transfers"] = []

    pair = pairs.report(pair_case(before=empty))["groups"][0]
    assert pair["included_dimensions"] == []
    assert pair["deltas"]["auxiliary_total"] == {
        "percentage_points": None,
        "exact_fraction": None,
    }
    for stage in pair["stages"].values():
        assert stage["auxiliary_total"]["score_0_100"] is None


def test_unresolved_identity_does_not_disable_lineage_or_valid_aggregate_differences(
    pair_case, batch
):
    case = pair_case(
        after=pairs.retimed_after,
        edits=[
            pairs.edit("retime", start_time="2020-01-01T08:00:00Z", end_time="2020-01-01T09:00:00Z")
        ],
        unresolved_names=["Museum A"],
    )
    out = pairs.report(
        case, result_sources=read_v3_result_sources(case[0], batch[4] / "manifest.json")
    )
    assert out["status"] == "complete", out["diagnostics"]
    pair = out["groups"][0]
    relation = next(r for r in pair["correspondence"]["relations"] if r["operations"])
    assert relation["basis"] == "validated_adopted_lineage"
    assert relation["identity_change"] == "unresolved"
    assert pair["correspondence"]["unresolved"] == {"before": [], "after": []}
    assert pair["deltas"]["dimensions"]["grounding"]["counts"]["UNKNOWN"] == 0
    opening = next(r for r in pair["continuity"]["opening"] if r.get("relation") == "modified")
    assert opening["transition"] == "not_comparable"


def test_absent_optional_final_is_not_replaced_by_selected_itinerary(pair_case):
    def change(results):
        pairs.no_departure(results)
        results["v3"]["v3"] = {"draft": copy.deepcopy(results["v3"]["itinerary"])}

    pair = pairs.report(pair_case(source_change=change))["groups"][0]
    assert pair["available_stages"] == {"draft": True, "final_primary": False}
    assert list(pair["stages"]) == ["draft"]
    assert pair["deltas"] is None


def test_changed_internal_findings_do_not_change_independent_metrics_or_matching(pair_case, batch):
    first_case = pair_case(edits=[])
    first = pairs.report(
        first_case, result_sources=read_v3_result_sources(first_case[0], batch[4] / "manifest.json")
    )

    def change(results):
        pairs.no_departure(results)
        draft = copy.deepcopy(results["v3"]["itinerary"])
        results["v3"]["v3"] = {
            "draft": draft,
            "final_primary": copy.deepcopy(draft),
            "repair": pairs.adopted_edit(draft, draft, []),
            "validation": {"findings": [{"state": "PASS", "target_id": "fabricated"}]},
        }
        results["v3"]["v3"]["repair"]["rounds"][0]["result"]["outcomes"] = [{"resolved": True}]

    second_case = pair_case(source_change=change)
    second = pairs.report(
        second_case,
        result_sources=read_v3_result_sources(second_case[0], batch[4] / "manifest.json"),
    )
    a, b = first["groups"][0], second["groups"][0]
    assert a["deltas"] == b["deltas"]
    for stage in ("draft", "final_primary"):
        assert a["stages"][stage]["dimensions"] == b["stages"][stage]["dimensions"]
    for left, right in zip(
        a["correspondence"]["relations"], b["correspondence"]["relations"], strict=True
    ):
        assert left["relation"] == right["relation"]
        assert left["operations"] == right["operations"]
        assert left["identity_change"] == right["identity_change"]
    assert first["content_hash"] != second["content_hash"]


@pytest.mark.parametrize("complete", [True, False])
def test_partial_route_improvement_requires_comparable_complete_failure_magnitudes(
    pair_case, batch, complete
):
    def after(itinerary):
        itinerary["days"][0]["activities"][0].update(
            start_time="2020-01-01T08:30:00Z",
            end_time="2020-01-01T09:30:00Z",
        )

    element = {"status": {}, "condition": "ROUTE_EXISTS", "duration": "7200s"}
    if complete:
        element["distanceMeters"] = 2500
    case = pair_case(
        after=after,
        edits=[
            pairs.edit(
                "retime",
                start_time="2020-01-01T08:30:00Z",
                end_time="2020-01-01T09:30:00Z",
            )
        ],
        element=element,
    )
    pair = pairs.report(
        case, result_sources=read_v3_result_sources(case[0], batch[4] / "manifest.json")
    )["groups"][0]
    route = pair["continuity"]["routes"][0]
    assert route["before"]["state"] == route["after"]["state"] == "FAIL"
    assert route["transition"] == ("partial_observed_improvement" if complete else "unchanged")
    assert (route["partial_observed_improvement"] is not None) == complete


def test_unknown_replacement_identity_cannot_certify_a_retained_protection_fix(pair_case, batch):
    def after(itinerary):
        itinerary["days"][0]["activities"][0].update(
            title="Gallery C",
            place_name="Gallery C",
            source_place_id="canonical-Gallery C",
            start_time="2020-01-01T08:00:00Z",
            end_time="2020-01-01T09:00:00Z",
        )

    case = pair_case(
        after=after,
        edits=[
            pairs.edit(
                "replace",
                place_id="canonical-Gallery C",
                start_time="2020-01-01T08:00:00Z",
                end_time="2020-01-01T09:00:00Z",
            )
        ],
        unresolved_names=["Gallery C"],
        obligations=[pairs.protection("09:30", "10:00")],
    )
    pair = pairs.report(
        case, result_sources=read_v3_result_sources(case[0], batch[4] / "manifest.json")
    )["groups"][0]
    conflict = pair["continuity"]["protection_conflicts"][0]
    assert conflict["transition"] == "unresolved_correspondence"
    assert conflict["continued_participant"] is None


def test_search_selection_keeps_intermediate_ancestors_and_discards_tail(pair_case, batch):
    def after(itinerary):
        itinerary["days"][0]["activities"][0].update(
            start_time="2020-01-01T08:00:00Z",
            end_time="2020-01-01T09:00:00Z",
        )

    def repair_change(repair):
        current = repair["original"]
        rows = []
        for index, (start, end) in enumerate(((10, 11), (8, 9), (11, 12)), 1):
            next_state = copy.deepcopy(current)
            next_state["days"][0]["activities"][0].update(
                start_time=f"2020-01-01T{start:02}:00:00Z",
                end_time=f"2020-01-01T{end:02}:00:00Z",
            )
            row = pairs.adopted_edit(
                current,
                next_state,
                [
                    pairs.edit(
                        "retime",
                        start_time=f"2020-01-01T{start:02}:00:00Z",
                        end_time=f"2020-01-01T{end:02}:00:00Z",
                    )
                ],
            )["rounds"][0]
            row.update(
                round_index=index,
                exploration_transition=True,
                best_promoted=index == 2,
                strategy="local",
            )
            rows.append(row)
            current = next_state
        repair.update(search_version=1, selected_round_index=2, rounds=rows)

    case = pair_case(
        after=after,
        edits=[
            pairs.edit("retime", start_time="2020-01-01T08:00:00Z", end_time="2020-01-01T09:00:00Z")
        ],
        repair_change=repair_change,
    )
    sources = read_v3_result_sources(case[0], batch[4] / "manifest.json")
    result = prepare_v3_correspondence(case[0], case[1], sources).to_dict()
    group = result["groups"][0]
    assert not group["diagnostics"]
    relation = next(r for r in group["relations"] if r["relation"] == "modified")
    assert [event["round_index"] for event in relation["edit_sources"]] == [1, 2]
    assert relation["basis"] == "validated_adopted_lineage"


@pytest.mark.parametrize("selection", [None, 1, "1"])
def test_original_selection_and_invalid_promotion_references(pair_case, batch, selection):
    def repair_change(repair):
        original = repair["original"]
        explored = copy.deepcopy(original)
        explored["days"][0]["activities"][0].update(
            start_time="2020-01-01T10:00:00Z", end_time="2020-01-01T11:00:00Z"
        )
        row = pairs.adopted_edit(
            original,
            explored,
            [
                pairs.edit(
                    "retime", start_time="2020-01-01T10:00:00Z", end_time="2020-01-01T11:00:00Z"
                )
            ],
        )["rounds"][0]
        row.update(strategy="local", exploration_transition=True, best_promoted=False)
        repair.update(search_version=1, selected_round_index=selection, rounds=[row])

    case = pair_case(after=lambda itinerary: None, edits=[], repair_change=repair_change)
    sources = read_v3_result_sources(case[0], batch[4] / "manifest.json")
    group = prepare_v3_correspondence(case[0], case[1], sources).to_dict()["groups"][0]
    if selection is None:
        assert not group["diagnostics"]
        assert all(not row["edit_sources"] for row in group["relations"])
    else:
        assert any(row["reason"] == "embedded_lineage_unavailable" for row in group["diagnostics"])
