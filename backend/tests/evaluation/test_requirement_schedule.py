"""Requirement and schedule public-boundary checks with frozen synthetic artifacts."""

import copy
import json

import pytest

from backend.evaluation.identity import identity_references
from backend.evaluation.identity import resolve_legacy_identities as resolve_identities
from backend.evaluation.intake import load_batch
from backend.evaluation.requirement_schedule import score_requirement_schedule
from backend.tests.evaluation.test_identity import evidence, plan, review_envelope, search

pytest_plugins = ("backend.tests.evaluation.test_intake",)
SOURCE = [{"field_path": "additional_preferences", "quote": "architecture"}]


@pytest.fixture
def scenario(batch):
    manifest, results, write, save, root = batch

    def build(obligations=(), change=None, unresolved=(), end_date=None, unresolved_names=()):
        spec = json.loads((root / "requirements.json").read_text(encoding="utf-8"))
        spec["subjects"] = [{"subject_id": "a", "place_name": "Museum A"}]
        spec["obligations"] = copy.deepcopy(list(obligations))
        spec["unresolved_items"] = copy.deepcopy(list(unresolved))
        if end_date:
            original = json.loads((root / "input.json").read_text(encoding="utf-8"))
            original["end_date"] = end_date
            ref = save("input.json", original)
            manifest["groups"][0]["input_ref"] = ref
            spec["input_sha256"] = ref["sha256"]
            for version in results:
                name = version + "-provenance.json"
                provenance = json.loads((root / name).read_text(encoding="utf-8"))
                provenance["input_sha256"] = ref["sha256"]
                manifest["groups"][0]["selected_runs"][version]["provenance_ref"] = save(
                    name, provenance, "rtpeval_provenance_1"
                )
        manifest["groups"][0]["requirement_spec_ref"] = save(
            "requirements.json", spec, spec["schema_version"]
        )
        if change:
            change(results)
        for version in results:
            write(version)
        intake = load_batch(write())
        assert intake.status == "accepted", intake.to_dict()
        observations, reviews = [], []
        for reference in identity_references(intake):
            if reference["name"] in unresolved_names:
                continue
            canonical = "canonical-" + reference["name"]
            observation = search(reference, reference["name"], place_id=canonical)
            observations.append(observation)
            reviews.extend(
                review_envelope(intake, observation, reference["reference_id"], canonical)[
                    "records"
                ]
            )
        envelope = {
            "schema_version": "rtpeval_identity_reviews_1",
            "batch_id": "batch",
            "batch_revision": "1",
            "records": reviews,
        }
        identity = resolve_identities(
            intake, evidence(intake, observations), envelope, plan(intake)
        )
        assert identity.status in ("complete", "needs_adjudication"), identity.to_dict()
        return intake, identity, root

    return build


def required(mode="exact", count=1, **fields):
    return {
        "obligation_id": "require-a",
        "kind": "required_visit",
        "resolution": "resolved",
        "subject_ref": "a",
        "source_refs": SOURCE,
        "count": {"mode": mode, "value": count},
        **fields,
    }


def first(report, version="v0"):
    return next(item for item in report["results"] if item["version"] == version)


@pytest.mark.parametrize("mode,state", [("WALK", "PASS"), ("DRIVE", "FAIL"), (None, "UNKNOWN")])
def test_transport_obligation_is_executable_with_independent_sources(scenario, mode, state):
    obligation = {
        "obligation_id": "mode-policy",
        "kind": "transport_modes",
        "resolution": "resolved",
        "scope": "whole_trip",
        "allowed_modes": ["WALK", "TRANSIT"],
        "source_refs": SOURCE,
    }

    def change(results):
        for version, result in results.items():
            itinerary = result["itinerary"]
            if version == "v0":
                activity = itinerary["days"][0]["activities"][1]
                activity["title"] = "Transfer"
                activity["transport"] = {
                    "mode": mode,
                    "from_activity_id": "a",
                    "to_activity_id": "b",
                }
            else:
                itinerary["transfers"] = [
                    {
                        "from_activity_id": "a",
                        "to_activity_id": "b",
                        "mode": mode,
                        "departure_time": "2020-01-01T10:00:00+00:00",
                        "arrival_time": "2020-01-01T10:20:00+00:00",
                    }
                ]

    intake, identity, _ = scenario([obligation], change=change)
    report = score_requirement_schedule(intake, identity).to_dict()
    assert report["status"] == "complete", report
    assert report["rules_version"] == "rtpeval_requirement_schedule_rules_4"
    for version in ("v0", "v1", "v2", "v3"):
        check = first(report, version)["requirements"]["checks"][0]
        assert check["state"] == state
        assert check["sources"] == SOURCE
        assert check["aggregation_owner"] == "requirements"
        assert first(report, version)["requirements"]["denominator"] == 1
        assert first(report, version)["requirements"]["unclassified_obligations"] == []
    from backend.evaluation.routes import prepare_routes

    routes = prepare_routes(intake, identity).to_dict()
    assert routes["status"] == "complete", routes
    assert routes["rules"]["version"] == "rtpeval_route_rules_3"
    assert all(
        leg["mode_policy"]["state"] == state for row in routes["results"] for leg in row["legs"]
    )
    assert all(
        leg["mode_policy_score"]["state"] == ("UNKNOWN" if mode is None else "PASS")
        for row in routes["results"]
        for leg in row["legs"]
    )


def test_identity_report_requires_current_association_policy(scenario):
    intake, identity, _ = scenario()
    stale = identity.to_dict()
    stale.pop("association_policy_version", None)
    assert score_requirement_schedule(intake, stale).status == "identity_replay_required"


def test_empty_reviewed_requirements_are_na_and_identity_replay_is_explicit(scenario):
    intake, identity, _ = scenario()
    report = score_requirement_schedule(intake, identity).to_dict()
    assert report["status"] == "complete"
    assert first(report)["requirements"]["state"] == "N/A"
    old = identity.to_dict()
    old.pop("subject_scope_version")
    replay = score_requirement_schedule(intake, old).to_dict()
    assert replay["status"] == "identity_replay_required"
    assert replay["results"] == []


def test_exact_and_minimum_count_use_canonical_occurrences(scenario):
    intake, identity, _ = scenario([required()])
    report = score_requirement_schedule(intake, identity).to_dict()
    check = first(report)["requirements"]["checks"][0]
    assert check["state"] == "PASS"
    assert check["components"][0]["bounds"] == {"lower": 1, "upper": 1}


@pytest.mark.parametrize(
    "payload",
    [
        required(count=True),
        required(count=0),
        required(mode="maximum"),
        required(distinct_dates="yes"),
        required(
            count=1, date_obligations=[{"date": "2020-01-01", "count_mode": "minimum", "count": 2}]
        ),
        {
            "obligation_id": "unknown",
            "kind": "unknown_operator",
            "resolution": "resolved",
            "source_refs": SOURCE,
        },
        {
            "obligation_id": "fixed",
            "kind": "fixed_visit_time",
            "resolution": "resolved",
            "subject_ref": "a",
            "date": "2020-01-01",
            "match": "at_least_one",
            "conditions": {"start_at": "09:00"},
            "source_refs": SOURCE,
        },
    ],
)
def test_malformed_or_contradictory_executable_spec_returns_whole_batch(scenario, payload):
    intake, identity, _ = scenario([payload])
    report = score_requirement_schedule(intake, identity).to_dict()
    assert report["status"] == "needs_material_correction"
    assert report["results"] == []


def test_unclassified_annotations_make_empty_dimension_unavailable(scenario):
    intake, identity, _ = scenario(
        unresolved=[
            {"item_id": "unclear", "source_refs": SOURCE, "reason": "Unclear hard applicability"}
        ]
    )
    dimension = first(score_requirement_schedule(intake, identity).to_dict())["requirements"]
    assert dimension["state"] == "UNKNOWN"
    assert dimension["denominator"] is None
    assert dimension["reasons"] == ["requirement_completeness_unresolved"]


def context(intake, zone="Etc/UTC"):
    group = intake.to_dict()["inventory"][0]
    return {
        "schema_version": "rtpeval_schedule_context_1",
        "batch_id": "batch",
        "revision": "1",
        "groups": [
            {
                "group_id": "g",
                "input_sha256": group["input_sha256"],
                "timezone": zone,
                "source_ref": "independent-fixture",
                "reviewer_ref": "reviewer",
                "reviewed_at": "2026-10-02T00:00:00Z",
            }
        ],
    }


def fixed(match="single_visit", **fields):
    return {
        "obligation_id": "fixed-a",
        "kind": "fixed_visit_time",
        "resolution": "resolved",
        "subject_ref": "a",
        "source_refs": SOURCE,
        "date": "2020-01-01",
        "match": match,
        "conditions": {"start_at": "09:00", "duration": {"mode": "minimum", "seconds": 3600}},
        **fields,
    }


def duplicate_a(results):
    for value in results.values():
        visits = value["itinerary"]["days"][0]["activities"]
        second = copy.deepcopy(visits[0])
        second.update(
            activity_id="a2",
            start_time="2020-01-01T12:00:00+00:00",
            end_time="2020-01-01T13:00:00+00:00",
        )
        visits.append(second)


@pytest.mark.parametrize(
    "mode,target,expected",
    [("exact", 1, "FAIL"), ("exact", 2, "PASS"), ("minimum", 1, "PASS"), ("minimum", 3, "FAIL")],
)
def test_repeated_source_occurrences_are_distinct_counts(scenario, mode, target, expected):
    intake, identity, _ = scenario([required(mode, target)], duplicate_a)
    dimension = first(score_requirement_schedule(intake, identity).to_dict())["requirements"]
    assert dimension["checks"][0]["state"] == expected
    assert dimension["checks"][0]["components"][0]["bounds"] == {"lower": 2, "upper": 2}


def test_dates_and_distinct_dates_stay_components_of_one_obligation(scenario):
    intake, identity, _ = scenario(
        [
            required(
                "minimum",
                2,
                distinct_dates=True,
                date_obligations=[{"date": "2020-01-02", "count_mode": "minimum", "count": 1}],
            )
        ],
        duplicate_a,
        end_date="2020-01-02",
    )
    dimension = first(score_requirement_schedule(intake, identity).to_dict())["requirements"]
    assert dimension["known_unit_count"] == 1
    assert dimension["checks"][0]["state"] == "FAIL"
    assert [c["state"] for c in dimension["checks"][0]["components"]] == ["PASS", "FAIL", "FAIL"]


def test_unknown_identity_prevents_exact_pass_but_not_proven_minimum(scenario):
    intake, identity, _ = scenario([required()], unresolved_names=["Museum B"])
    dimension = first(score_requirement_schedule(intake, identity).to_dict())["requirements"]
    assert dimension["checks"][0]["state"] == "UNKNOWN"
    assert dimension["checks"][0]["components"][0]["bounds"] == {"lower": 1, "upper": 2}


@pytest.mark.parametrize(
    "duplicate,match,expected",
    [
        (False, "single_visit", "PASS"),
        (True, "single_visit", "FAIL"),
        (True, "at_least_one", "PASS"),
    ],
)
def test_fixed_selector_and_single_visit_default(scenario, duplicate, match, expected):
    obligation = fixed(
        match, **({"repeat_permission_refs": SOURCE} if match == "at_least_one" else {})
    )
    intake, identity, _ = scenario([obligation], duplicate_a if duplicate else None)
    report = score_requirement_schedule(intake, identity, context(intake)).to_dict()
    assert first(report)["requirements"]["checks"][0]["state"] == expected
    assert first(report)["requirements"]["known_unit_count"] == 1


def test_local_clock_requires_context_but_duration_alone_uses_instants(scenario):
    intake, identity, _ = scenario([fixed()])
    assert (
        first(score_requirement_schedule(intake, identity).to_dict())["requirements"]["state"]
        == "UNKNOWN"
    )
    intake, identity, _ = scenario(
        [fixed(conditions={"duration": {"mode": "exact", "seconds": 3600}})]
    )
    assert (
        first(score_requirement_schedule(intake, identity).to_dict())["requirements"]["state"]
        == "PASS"
    )


def test_protection_fails_original_obligations_without_adding_schedule_units(scenario):
    protections = [
        {
            "obligation_id": oid,
            "kind": "protected_time",
            "resolution": "resolved",
            "source_refs": SOURCE,
            "date": "2020-01-01",
            "scope": "primary_visits",
            "interval": {"kind": "clock", "start": start, "end": end},
        }
        for oid, start, end in [("p1", "09:30", "09:45"), ("p2", "09:40", "10:00")]
    ]
    intake, identity, _ = scenario(protections)
    report = first(score_requirement_schedule(intake, identity, context(intake)).to_dict())
    assert [c["state"] for c in report["requirements"]["checks"]] == ["FAIL", "FAIL"]
    assert report["non_overlap"]["known_unit_count"] == 3
    assert report["non_overlap"]["counts"] == {"PASS": 2, "FAIL": 1, "UNKNOWN": 0}
    assert report["schedule_measures"]["protection_conflict"]["seconds"] == 1800
    assert report["schedule_measures"]["scheduled_occupied"]["seconds"] == 8400


def test_triple_overlap_pair_seconds_differ_from_union_seconds(scenario):
    def triple(results):
        for value in results.values():
            activities = value["itinerary"]["days"][0]["activities"]
            activities[:] = [copy.deepcopy(activities[0]) for _ in range(3)]
            for index, activity in enumerate(activities):
                activity["activity_id"] = "visit-" + str(index)

    intake, identity, _ = scenario(change=triple)
    report = first(score_requirement_schedule(intake, identity, context(intake)).to_dict())
    assert report["non_overlap"]["counts"] == {"PASS": 0, "FAIL": 3, "UNKNOWN": 0}
    assert len(report["schedule_measures"]["commitment_pairs"]) == 3
    assert report["schedule_measures"]["pair_intersection_sum"]["seconds"] == 10800
    assert report["schedule_measures"]["commitment_conflict"]["seconds"] == 3600


def occupancy_review(intake, occupancy="committed", **fields):
    projection = intake.to_dict()["inventory"][0]["runs"]["v0"]["final"]
    return {
        "schema_version": "rtpeval_occupancy_reviews_1",
        "batch_id": "batch",
        "revision": "1",
        "records": [
            {
                "source": projection["activities"][-1]["source"],
                "revision": "1",
                "occupancy": occupancy,
                "reviewer_ref": "reviewer",
                "reviewed_at": "2026-10-02T00:00:00Z",
                "rationale": "Independent decision",
                **fields,
            }
        ],
    }


def add_rest(results):
    for value in results.values():
        item = copy.deepcopy(value["itinerary"]["days"][0]["activities"][0])
        item.update(
            activity_id="rest",
            title="Rest",
            place_name=None,
            activity_kind="free_time",
            notes="Reserved rest",
            start_time="2020-01-01T12:00:00+00:00",
            end_time="2020-01-01T13:00:00+00:00",
        )
        value["itinerary"]["days"][0]["activities"].append(item)


def test_fixed_generic_review_and_linked_protection_placeholder(
    scenario,
):
    protection = {
        "obligation_id": "p",
        "kind": "protected_time",
        "resolution": "resolved",
        "source_refs": SOURCE,
        "date": "2020-01-01",
        "scope": "scheduled_commitments",
        "interval": {"kind": "clock", "start": "12:00", "end": "13:00"},
    }
    intake, identity, _ = scenario([protection], add_rest)
    report = first(score_requirement_schedule(intake, identity, context(intake)).to_dict())
    assert report["non_overlap"]["denominator"] is None
    committed = first(
        score_requirement_schedule(
            intake, identity, context(intake), occupancy_review(intake)
        ).to_dict()
    )
    assert committed["non_overlap"]["known_unit_count"] == 4
    assert committed["requirements"]["state"] == "FAIL"
    duplicate = first(
        score_requirement_schedule(
            intake,
            identity,
            context(intake),
            occupancy_review(intake, "uncommitted", protected_obligation_refs=["p"]),
        ).to_dict()
    )
    assert duplicate["non_overlap"]["known_unit_count"] == 3
    assert duplicate["non_overlap"]["denominator_unresolved"] is False
    assert duplicate["requirements"]["state"] == "PASS"


@pytest.mark.parametrize(
    "fault", ["stale", "duplicate", "primary_uncommitted", "unknown_protection", "role_edit"]
)
def test_occupancy_reviews_cannot_change_roles_or_bypass_source_links(scenario, fault):
    intake, identity, _ = scenario(change=add_rest)
    review = occupancy_review(intake)
    item = review["records"][0]
    if fault == "stale":
        item["source"]["artifact_sha256"] = "0" * 64
    elif fault == "duplicate":
        review["records"].append(copy.deepcopy(item))
    elif fault == "primary_uncommitted":
        item["source"] = intake.to_dict()["inventory"][0]["runs"]["v0"]["final"]["activities"][0][
            "source"
        ]
        item["occupancy"] = "uncommitted"
    elif fault == "unknown_protection":
        item.update(occupancy="uncommitted", protected_obligation_refs=["absent"])
    else:
        item["role"] = "transition"
    report = score_requirement_schedule(intake, identity, occupancy_reviews=review).to_dict()
    assert report["status"] == "needs_material_correction"
    assert report["results"] == []


def test_requested_days_include_empty_days_and_extra_days_do_not_change_counts(scenario):
    def extra(results):
        for value in results.values():
            day = copy.deepcopy(value["itinerary"]["days"][0])
            day["date"] = "2020-01-03"
            for item in day["activities"]:
                item["activity_id"] += "-extra"
                item["start_time"] = item["start_time"].replace("2020-01-01", day["date"])
                item["end_time"] = item["end_time"].replace("2020-01-01", day["date"])
            value["itinerary"]["days"].append(day)

    intake, identity, _ = scenario([required()], extra, end_date="2020-01-02")
    report = first(score_requirement_schedule(intake, identity, context(intake)).to_dict())
    assert report["requirements"]["state"] == "PASS"
    assert report["descriptive"]["coverage"] == {
        "requested_day_count": 2,
        "declared_day_present_count": 1,
        "any_activity_day_count": 1,
        "known_primary_day_count": 1,
        "empty_primary_day_count": 1,
        "unknown_primary_day_count": 0,
        "extra_declared_days": ["2020-01-03"],
    }
    assert [item["known_primary_count"] for item in report["descriptive"]["density"]] == [2, 0]
    assert (
        report["schedule_measures"]["daily"]["2020-01-01"]["scheduled_occupied"]["seconds"] == 8400
    )
    assert report["source_hashes"]["input"] == intake.to_dict()["inventory"][0]["input_sha256"]


def test_canonical_repetition_is_descriptive_and_unknown_ids_make_it_a_lower_bound(scenario):
    intake, identity, _ = scenario(
        [required("minimum", 1)], duplicate_a, unresolved_names=["Museum B"]
    )
    report = first(score_requirement_schedule(intake, identity).to_dict())
    repeat = report["descriptive"]["repetition"]
    assert report["requirements"]["state"] == "PASS"
    assert repeat["extra_occurrences"] == 1
    assert repeat["within_day_extras"] == 1
    assert repeat["across_day_extras"] == 0
    assert repeat["status"] == "lower_bound"
    assert repeat["unknown_identity_occurrences"] == 1
    assert repeat["reviewed_revisit_obligations"][0]["count"] == {"mode": "minimum", "value": 1}
    assert report["schedule_measures"]["daily"] is None


def test_fixed_time_components_cannot_be_satisfied_by_different_visits(scenario):
    def visits(results):
        duplicate_a(results)
        for result in results.values():
            result["itinerary"]["days"][0]["activities"][0]["end_time"] = (
                "2020-01-01T09:30:00+00:00"
            )

    intake, identity, _ = scenario([fixed("at_least_one", repeat_permission_refs=SOURCE)], visits)
    assert (
        first(score_requirement_schedule(intake, identity, context(intake)).to_dict())[
            "requirements"
        ]["state"]
        == "FAIL"
    )


def test_unknown_identity_with_proven_wrong_time_cannot_satisfy_fixed_time(scenario):
    intake, identity, _ = scenario(
        [fixed(conditions={"start_at": "08:00"})], unresolved_names=["Museum B"]
    )
    assert (
        first(score_requirement_schedule(intake, identity, context(intake)).to_dict())[
            "requirements"
        ]["state"]
        == "FAIL"
    )


def test_known_flexible_candidate_outside_protection_does_not_create_possible_conflict(scenario):
    protection = {
        "obligation_id": "p",
        "kind": "protected_time",
        "resolution": "resolved",
        "source_refs": SOURCE,
        "date": "2020-01-01",
        "scope": "scheduled_commitments",
        "interval": {"kind": "clock", "start": "14:00", "end": "15:00"},
    }
    intake, identity, _ = scenario([protection], add_rest)
    report = first(score_requirement_schedule(intake, identity, context(intake)).to_dict())
    assert report["requirements"]["state"] == "PASS"
    assert report["non_overlap"]["counts"] == {"PASS": 3, "FAIL": 0, "UNKNOWN": 0}
    assert report["non_overlap"]["denominator"] is None


def test_date_disagreement_is_potential_in_trip_even_on_extra_declared_day(scenario):
    def mismatch(results):
        for result in results.values():
            result["itinerary"]["days"][0]["date"] = "2020-01-03"

    intake, identity, _ = scenario([required()], mismatch)
    report = first(score_requirement_schedule(intake, identity, context(intake)).to_dict())
    component = report["requirements"]["checks"][0]["components"][0]
    assert component["bounds"] == {"lower": 0, "upper": 1}
    assert component["state"] == "UNKNOWN"
    assert report["descriptive"]["coverage"]["unknown_primary_day_count"] == 1


def test_missing_clocks_preserve_declared_count_and_unknown_non_overlap(scenario):
    def missing(results):
        for result in results.values():
            result["itinerary"]["days"][0]["activities"][0].pop("start_time")

    intake, identity, _ = scenario([required()], missing)
    report = first(score_requirement_schedule(intake, identity).to_dict())
    assert report["requirements"]["state"] == "PASS"
    assert report["non_overlap"]["counts"]["UNKNOWN"] > 0


@pytest.mark.parametrize(
    "fields",
    [
        {"subject_ref": []},
        {"date": []},
        {"conditions": {"within": []}},
        {"repeat_permission_refs": ["invalid"], "match": "at_least_one"},
        {"conditions": {"duration": {"mode": "minimum", "seconds": True}}},
        {"conditions": {"start_at": "25:00"}},
        {"all_occurrences": True},
    ],
)
def test_malformed_fixed_payload_is_correction_before_identity_preflight(batch, fields):
    manifest, _, write, save, root = batch
    spec = json.loads((root / "requirements.json").read_text(encoding="utf-8"))
    spec["subjects"] = [{"subject_id": "a", "place_name": "Museum A"}]
    spec["obligations"] = [fixed(**fields)]
    manifest["groups"][0]["requirement_spec_ref"] = save(
        "requirements.json", spec, spec["schema_version"]
    )
    intake = load_batch(write())
    assert intake.status == "accepted"
    report = score_requirement_schedule(intake, {}).to_dict()
    assert report["status"] == "needs_material_correction"
    assert report["results"] == []


@pytest.mark.parametrize("fault", ["zone", "duplicate", "hash", "timestamp", "source"])
def test_independent_context_integrity_is_material_not_quality(scenario, fault):
    intake, identity, _ = scenario()
    value = context(intake)
    record = value["groups"][0]
    if fault == "zone":
        record["timezone"] = "Invalid/Zone"
    elif fault == "duplicate":
        value["groups"].append(copy.deepcopy(record))
    elif fault == "hash":
        record["input_sha256"] = "0" * 64
    elif fault == "timestamp":
        record["reviewed_at"] = "2026-10-02T00:00:00"
    else:
        record.pop("source_ref")
    report = score_requirement_schedule(intake, identity, value).to_dict()
    assert report["status"] == "needs_material_correction"


@pytest.mark.parametrize(
    "obligations,end",
    [
        (
            [
                required(
                    "minimum",
                    2,
                    date_obligations=[{"date": "2020-01-01", "count_mode": "exact", "count": 1}],
                )
            ],
            None,
        ),
        (
            [
                required(
                    "exact",
                    2,
                    distinct_dates=True,
                    date_obligations=[{"date": "2020-01-01", "count_mode": "exact", "count": 2}],
                )
            ],
            "2020-01-02",
        ),
        ([fixed(), fixed(obligation_id="another", conditions={"start_at": "10:00"})], None),
        (
            [
                fixed("at_least_one", repeat_permission_refs=SOURCE),
                {
                    "obligation_id": "exclude",
                    "kind": "excluded_visit",
                    "resolution": "resolved",
                    "source_refs": SOURCE,
                    "subject_ref": "a",
                    "scope": "whole_trip",
                },
            ],
            None,
        ),
    ],
)
def test_detectable_cross_component_contradictions_are_not_planner_failures(
    scenario, obligations, end
):
    intake, identity, _ = scenario(obligations, end_date=end)
    assert score_requirement_schedule(intake, identity).status == "needs_material_correction"


@pytest.mark.parametrize("resolution", ["unresolved", "unsupported"])
def test_unresolved_parent_and_linked_or_soft_annotations_do_not_multiply_units(
    scenario, resolution
):
    obligation = {
        "obligation_id": "unknown",
        "kind": "fixed_visit_time",
        "resolution": resolution,
        "reason": "Original afternoon meaning retained",
        "source_refs": SOURCE,
    }
    intake, identity, _ = scenario(
        [obligation],
        unresolved=[
            {
                "item_id": "linked",
                "obligation_ref": "unknown",
                "source_refs": SOURCE,
                "reason": "Clarify clock",
            },
            {
                "item_id": "soft",
                "classification": "soft_preference",
                "source_refs": SOURCE,
                "reason": "A preference",
            },
        ],
    )
    report = first(score_requirement_schedule(intake, identity).to_dict())["requirements"]
    assert report["known_unit_count"] == 1
    assert report["counts"] == {"PASS": 0, "FAIL": 0, "UNKNOWN": 1}
    assert report["denominator"] == 1


@pytest.mark.parametrize("scope,expected", [("whole_trip", "FAIL"), ("specified_dates", "PASS")])
def test_exclusion_uses_reviewed_subject_and_requested_date_scope(scenario, scope, expected):
    obligation = {
        "obligation_id": "exclude",
        "kind": "excluded_visit",
        "resolution": "resolved",
        "subject_ref": "a",
        "source_refs": SOURCE,
        "scope": scope,
    }
    if scope == "specified_dates":
        obligation["dates"] = ["2020-01-02"]
    intake, identity, _ = scenario([obligation], end_date="2020-01-02")
    assert (
        first(score_requirement_schedule(intake, identity).to_dict())["requirements"]["state"]
        == expected
    )


def test_planner_findings_metadata_and_nearby_are_not_verdict_inputs(scenario):
    intake, identity, _ = scenario([required()])
    baseline = first(score_requirement_schedule(intake, identity).to_dict())

    def private(results):
        for result in results.values():
            result["requirements"] = {"required": ["Museum B"], "violation": True}
            result["validation"] = {"non_overlap": "FAIL"}
            result["mechanisms"] = {"repair_success": False}
            result["itinerary"]["reference_recommendations"] = [{"place_name": "Museum A"}]

    intake, identity, _ = scenario([required()], private)
    report = first(score_requirement_schedule(intake, identity).to_dict())
    assert report["requirements"]["counts"] == baseline["requirements"]["counts"]
    assert report["non_overlap"]["counts"] == baseline["non_overlap"]["counts"]
    assert report["schedule_measures"] == baseline["schedule_measures"]
    assert report["descriptive"]["coverage"] == baseline["descriptive"]["coverage"]


def test_independent_zone_can_prove_impossible_duration_window_is_material(scenario):
    intake, identity, _ = scenario(
        [
            fixed(
                conditions={
                    "within": {"start": "09:00", "end": "10:00"},
                    "duration": {"mode": "minimum", "seconds": 7200},
                }
            )
        ]
    )
    report = score_requirement_schedule(intake, identity, context(intake)).to_dict()
    assert report["status"] == "needs_material_correction"


@pytest.mark.parametrize(
    "fault", ["omitted_record", "stale_source", "bad_resolution", "automatic_high_impact"]
)
def test_identity_preflight_checks_complete_source_linkage_and_adoption_policy(scenario, fault):
    intake, identity, _ = scenario([required()])
    report = identity.to_dict()
    item = report["records"][0]
    if fault == "omitted_record":
        report["records"].pop()
    elif fault == "stale_source":
        item["source"]["requirement_spec_sha256"] = "0" * 64
    elif fault == "bad_resolution":
        item["resolution"] = "invented"
    else:
        item["decision_route"] = "name_search"
    assert score_requirement_schedule(intake, report).status == "identity_replay_required"


def test_unknown_unresolved_kind_preserves_applicability_availability(scenario):
    intake, identity, _ = scenario(
        [
            {
                "obligation_id": "unclassified",
                "kind": "not_classified",
                "resolution": "unresolved",
                "source_refs": SOURCE,
                "reason": "Applicability cannot be established",
            }
        ]
    )
    report = first(score_requirement_schedule(intake, identity).to_dict())["requirements"]
    assert report["denominator"] is None
    assert report["known_unit_count"] == 0
    assert report["unclassified_obligations"][0]["obligation_id"] == "unclassified"


def test_known_contradictory_placeholder_correspondence_requires_review_correction(scenario):
    protection = {
        "obligation_id": "p",
        "kind": "protected_time",
        "resolution": "resolved",
        "source_refs": SOURCE,
        "date": "2020-01-01",
        "scope": "scheduled_commitments",
        "interval": {"kind": "clock", "start": "14:00", "end": "15:00"},
    }
    intake, identity, _ = scenario([protection], add_rest)
    review = occupancy_review(intake, "uncommitted", protected_obligation_refs=["p"])
    assert (
        score_requirement_schedule(intake, identity, context(intake), review).status
        == "needs_material_correction"
    )


def test_start_and_duration_without_window_cannot_require_an_overnight_visit(scenario):
    intake, identity, _ = scenario(
        [fixed(conditions={"start_at": "23:00", "duration": {"mode": "minimum", "seconds": 7200}})]
    )
    assert (
        score_requirement_schedule(intake, identity, context(intake)).status
        == "needs_material_correction"
    )
