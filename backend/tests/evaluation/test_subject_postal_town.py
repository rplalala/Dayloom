"""Postal-town regression using supplied venue facts, not a case-specific identity rule."""

import copy
import json

import pytest

from backend.evaluation.identity import identity_references
from backend.evaluation.identity_program import (
    resolve_versioned_identities,
    verify_versioned_report,
)
from backend.evaluation.records import canonical_digest
from backend.tests.evaluation.test_identity import evidence, prepared, search
from backend.tests.evaluation.test_requirement_identity_versions import requirement_batch
from backend.tests.evaluation.test_subject_correspondence import subject_material

pytest_plugins = ("backend.tests.evaluation.test_intake",)
VENUE_ID = "ChIJB9OTMDIbdkgRp0JWbQGZsS8"


def postal_batch(
    batch, *, location=None, destination="London, United Kingdom", visits=None, same_date=False
):
    requirement_batch(batch, bound=False, destination=destination)

    def change(manifest, _results, save, root):
        original = json.loads((root / "input.json").read_bytes())
        original["additional_preferences"] = "Visit British Museum."
        if visits is not None:
            original.update(
                end_date="2020-01-02",
                additional_preferences="Visit British Museum exactly twice on different dates.",
            )
        manifest["groups"][0]["input_ref"] = save("input.json", original)
        sha = manifest["groups"][0]["input_ref"]["sha256"]
        spec = json.loads((root / "requirements.json").read_bytes())
        spec["input_sha256"] = sha
        spec["subjects"][0].update(place_name="British Museum", location=location)
        spec["obligations"][0]["source_refs"] = [
            {"field_path": "additional_preferences", "quote": "British Museum"}
        ]
        if visits is not None:
            spec["obligations"][0].update(count={"mode": "exact", "value": 2}, distinct_dates=True)
        manifest["groups"][0]["requirement_spec_ref"] = save(
            "requirements.json", spec, spec["schema_version"]
        )
        for version in _results:
            if visits is not None:
                itinerary = _results[version]["itinerary"]
                itinerary["end_date"] = "2020-01-02"
                template = copy.deepcopy(itinerary["days"][0]["activities"][0])
                days = [
                    {"date": "2020-01-01", "activities": []},
                    {"date": "2020-01-02", "activities": []},
                ]
                for index in range(visits):
                    day = 0 if same_date or index == 0 else 1
                    date = days[day]["date"]
                    hour = 9 + index * 2
                    activity = {
                        **template,
                        "activity_id": f"museum-{index}",
                        "title": "Visit British Museum",
                        "place_name": "British Museum" if version == "v0" else "The British Museum",
                        "start_time": f"{date}T{hour:02}:00:00+00:00",
                        "end_time": f"{date}T{hour + 1:02}:00:00+00:00",
                    }
                    if version != "v0":
                        activity.update(source_place_id=VENUE_ID, location="London, United Kingdom")
                    days[day]["activities"].append(activity)
                itinerary["days"] = days
                batch[2](version)
            provenance = json.loads((root / f"{version}-provenance.json").read_bytes())
            provenance["input_sha256"] = sha
            manifest["groups"][0]["selected_runs"][version]["provenance_ref"] = save(
                f"{version}-provenance.json", provenance, "rtpeval_provenance_1"
            )

    return prepared(batch, change)


def postal_evidence(intake):
    ref = next(r for r in identity_references(intake) if r["kind"] == "requirement_subject")
    record = search(ref, "The British Museum", place_id=VENUE_ID)
    candidate = record["search"]["candidates"][0]
    candidate["formatted_address"] = "London, United Kingdom"
    candidate["address_components"] = [
        {"longText": "London", "types": ["postal_town"]},
        {"longText": "United Kingdom", "shortText": "GB", "types": ["country", "political"]},
    ]
    return evidence(intake, [record])


def test_original_name_and_postal_town_resolve_one_target_for_all_versions(batch):
    intake = postal_batch(batch)
    observed = postal_evidence(intake)
    report = resolve_versioned_identities(
        intake, observed, common_subjects=True, subject_result=subject_material(intake, observed)
    ).to_dict()
    targets = [r for r in report["records"] if r["kind"] == "requirement_subject"]
    assert {r["canonical_place_id"] for r in targets} == {VENUE_ID}
    assert {r["version"] for r in targets} == {"v0", "v1", "v2", "v3"}
    assert {r["grounding_verdict"] for r in targets} == {"PASS"}
    assert all(r["original_claim"]["place_name"] == "British Museum" for r in targets)
    assert all(r["original_claim"]["location"] is None for r in targets)
    assert verify_versioned_report(intake, report)


def test_original_common_policy_keeps_its_packet_and_unresolved_postal_target(batch):
    from backend.evaluation.subject_correspondence import prepare_subject_judgment

    intake = postal_batch(batch)
    observed = postal_evidence(intake)
    old_policy = "requirement_subject_correspondence_1"
    packet = prepare_subject_judgment(
        intake, observed, model="fixture-model", policy_version=old_policy
    ).to_dict()
    # Captured from the fixed-base implementation before the postal-town change.
    assert (
        canonical_digest(packet)
        == "f412ccd818512c31ed007afbaa8c7976b7ead15d6c0ad8060575502d5f608add"
    )
    material = subject_material(intake, observed, policy_version=old_policy)
    report = resolve_versioned_identities(
        intake, observed, common_subjects=True, subject_policy=old_policy, subject_result=material
    ).to_dict()
    assert report["association_policy_version"] == "versioned_api_identity_5"
    assert {
        r["canonical_place_id"] for r in report["records"] if r["kind"] == "requirement_subject"
    } == {None}
    assert verify_versioned_report(intake, report)
    with pytest.raises(ValueError, match="packet/source mismatch"):
        resolve_versioned_identities(
            intake, observed, common_subjects=True, subject_result=material
        )


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_city",
        "wrong_country",
        "city_conflict",
        "duplicate_city",
        "country_conflict",
        "missing_country",
        "missing_city",
        "no_judgment",
        "ambiguous",
    ],
)
def test_postal_city_is_evidence_not_an_automatic_identity_match(batch, fault):
    intake = postal_batch(batch)
    observed = postal_evidence(intake)
    data = observed["records"][0]["search"]
    candidate = data["candidates"][0]
    parts = candidate["address_components"]
    if fault == "wrong_city":
        parts[0]["longText"] = "Oxford"
    elif fault == "wrong_country":
        parts[1].update(longText="France", shortText="FR")
    elif fault in ("city_conflict", "duplicate_city"):
        parts.append(
            {
                "longText": "Oxford",
                "types": ["locality" if fault == "city_conflict" else "postal_town"],
            }
        )
    elif fault == "country_conflict":
        parts.append({"longText": "France", "types": ["country"]})
    elif fault == "missing_country":
        parts.pop(1)
    elif fault == "missing_city":
        parts.pop(0)
    elif fault == "ambiguous":
        data["candidates"].append({**copy.deepcopy(candidate), "place_id": "another-branch"})
        data["actual_result_count"] = 2

    def unknown(rows, _cases):
        for row in rows.values():
            row.update(
                decision="unknown",
                candidate_id=None,
                evidence_fields=[],
                destination_assessment="unknown",
            )

    material = (
        None
        if fault == "no_judgment"
        else subject_material(intake, observed, unknown if fault == "ambiguous" else None)
    )
    report = resolve_versioned_identities(
        intake, observed, common_subjects=True, subject_result=material
    ).to_dict()
    assert {
        r["grounding_verdict"] for r in report["records"] if r["kind"] == "requirement_subject"
    } == {"UNKNOWN"}


@pytest.mark.parametrize("conflicting_city", [False, True])
@pytest.mark.parametrize("level", ["administrative_area_level_1", "administrative_area_level_2"])
def test_postal_town_preserves_administrative_destination_evidence(batch, conflicting_city, level):
    intake = postal_batch(batch, destination="England, United Kingdom")
    observed = postal_evidence(intake)
    parts = observed["records"][0]["search"]["candidates"][0]["address_components"]
    parts.append({"longText": "England", "types": [level]})
    if conflicting_city:
        parts.append({"longText": "Oxford", "types": ["locality"]})
    report = resolve_versioned_identities(
        intake, observed, common_subjects=True, subject_result=subject_material(intake, observed)
    ).to_dict()
    assert {
        r["canonical_place_id"] for r in report["records"] if r["kind"] == "requirement_subject"
    } == ({None} if conflicting_city else {VENUE_ID})


@pytest.mark.parametrize("destination", ["London, United Kingdom", "London, GB"])
def test_consistent_locality_and_postal_town_allow_google_country_aliases(batch, destination):
    intake = postal_batch(batch, destination=destination)
    observed = postal_evidence(intake)
    observed["records"][0]["search"]["candidates"][0]["address_components"].append(
        {"longText": "London", "types": ["locality", "political"]}
    )
    report = resolve_versioned_identities(
        intake, observed, common_subjects=True, subject_result=subject_material(intake, observed)
    ).to_dict()
    assert {
        r["canonical_place_id"] for r in report["records"] if r["kind"] == "requirement_subject"
    } == {VENUE_ID}


@pytest.mark.parametrize(
    "location", ["Oxford", "Another branch", "99 Example St, London, United Kingdom"]
)
def test_postal_town_does_not_drop_explicit_location_constraints(batch, location):
    intake = postal_batch(batch, location=location)
    observed = postal_evidence(intake)
    # A formatted token cannot override the typed city or prove an explicit branch.
    observed["records"][0]["search"]["candidates"][0]["formatted_address"] += ", Oxford"
    report = resolve_versioned_identities(
        intake, observed, common_subjects=True, subject_result=subject_material(intake, observed)
    ).to_dict()
    assert {
        r["canonical_place_id"] for r in report["records"] if r["kind"] == "requirement_subject"
    } == {None}


@pytest.mark.parametrize(
    "visits,same_date,resolved,expected",
    [
        (2, False, True, "PASS"),
        (1, False, True, "FAIL"),
        (3, False, True, "FAIL"),
        (2, True, True, "FAIL"),
        (2, False, False, "UNKNOWN"),
    ],
)
def test_postal_subject_exact_two_distinct_dates_preserves_real_violations(
    batch, visits, same_date, resolved, expected
):
    from backend.evaluation.requirement_schedule import score_requirement_schedule
    from backend.tests.evaluation.test_identity import details
    from backend.tests.evaluation.test_identity_llm import model_material
    from backend.tests.evaluation.test_requirement_schedule import context

    intake = postal_batch(batch, visits=visits, same_date=same_date)
    observed = postal_evidence(intake)
    facts = observed["records"][0]["search"]["candidates"][0]
    for ref in identity_references(intake):
        if ref["kind"] != "primary_visit":
            continue
        if ref["version"] == "v0":
            record = search(ref, "The British Museum", place_id=VENUE_ID)
            record["search"]["candidates"] = [copy.deepcopy(facts)]
        else:
            record = details(ref, "The British Museum", place_id=VENUE_ID)
            record["details"]["place"] = copy.deepcopy(facts)
        observed["records"].append(record)
    identity = resolve_versioned_identities(
        intake,
        observed,
        common_subjects=True,
        subject_result=subject_material(intake, observed) if resolved else None,
        model_result=model_material(intake, observed, historical=False, visits_only=True),
    ).to_dict()
    report = score_requirement_schedule(intake, identity, context(intake)).to_dict()
    assert report["status"] == "complete"
    assert {r["version"] for r in report["results"]} == {"v0", "v1", "v2", "v3"}
    assert {r["requirements"]["state"] for r in report["results"]} == {expected}


@pytest.mark.parametrize(
    "policy,expected_id,identity_policy",
    [
        ("requirement_subject_correspondence_1", None, "versioned_api_identity_5"),
        ("requirement_subject_correspondence_2", VENUE_ID, "versioned_api_identity_6"),
    ],
)
def test_prepared_policy_selects_native_postal_behavior_and_exact_replay(
    batch, policy, expected_id, identity_policy
):
    import asyncio

    import httpx

    from backend.evaluation.evaluation_run import execute_run, prepare_run, replay_run
    from backend.evaluation.snapshot import _bytes
    from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices

    intake = postal_batch(batch)
    facts = postal_evidence(intake)["records"][0]["search"]["candidates"][0]
    root = batch[4] / "postal-native"
    preparation = prepare_run(batch[2](), root, options=options(), prices=run_prices())
    assert preparation["subject_policy"] == "requirement_subject_correspondence_2"
    preparation["subject_policy"] = policy
    preparation["content_sha256"] = canonical_digest(
        {k: v for k, v in preparation.items() if k != "content_sha256"}
    )
    (root / "preparation.json").write_bytes(_bytes(preparation))

    def respond(request):
        if (
            request.url.path.endswith("searchText")
            and "British Museum" in json.loads(request.content)["textQuery"]
        ):
            return httpx.Response(
                200,
                json={
                    "places": [
                        {
                            "id": VENUE_ID,
                            "displayName": {"text": "The British Museum"},
                            "formattedAddress": facts["formatted_address"],
                            "addressComponents": facts["address_components"],
                            "location": {"latitude": 51.5194, "longitude": -0.1269},
                            "timeZone": {"id": "Europe/London"},
                        }
                    ]
                },
            )
        return mock_provider(request)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic",
                model_api_key="synthetic",
                http_client=client,
            )

    report = asyncio.run(execute())
    assert report["processing_status"] == "complete"
    identity = json.loads((root / "execution/identity-report.json").read_bytes())
    assert identity["association_policy_version"] == identity_policy
    assert {
        r["canonical_place_id"] for r in identity["records"] if r["kind"] == "requirement_subject"
    } == {expected_id}
    assert report["usage"]["actual_model_sends"] == 2
    assert report["usage"]["retries"] == 0
    assert replay_run(root) == report


@pytest.mark.parametrize("policy", ["", "unknown-policy"])
def test_unsupported_subject_policy_cannot_silently_upgrade_a_binding(batch, policy):
    intake = postal_batch(batch)
    with pytest.raises(ValueError, match="Unsupported requirement-subject policy"):
        resolve_versioned_identities(
            intake, postal_evidence(intake), common_subjects=True, subject_policy=policy
        )
