"""Offline V3 scope, uncertainty, provenance and side-effect regression tests."""

import asyncio
import socket
from dataclasses import replace
from datetime import date, datetime, time, timedelta

import httpx
import pytest
from pydantic import ValidationError

from backend.app.evidence.models import PlaceEvidence, RouteEvidenceBundle
from backend.app.evidence.official_models import OfficialCurrentEvidence
from backend.app.policies.official_evidence_resolver import resolve_effective_evidence
from backend.app.policies.poi_funnel import NamedPlaceResolution, NamedPlaceResolutionStatus
from backend.app.policies.trip_dates import create_trip_date_window
from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements
from backend.app.schemas.itinerary import Activity
from backend.app.schemas.itinerary_projection import EstimatedCostProjectionDiagnostic, V1Itinerary
from backend.app.schemas.named_place_intent import NamedPlaceIntent
from backend.app.schemas.request import PlanningRequest
from backend.app.versions.v3.models import Finding, ValidationPolicy
from backend.app.versions.v3.validation import validate_draft

DAY = date(2026, 9, 26)
NOW = datetime.fromisoformat("2026-09-25T12:00:00+00:00")
WINDOW = create_trip_date_window(DAY - timedelta(days=1))


def place(pid="a", **changes):
    return PlaceEvidence(
        **{
            "place_id": pid,
            "name": pid,
            "latitude": 0,
            "longitude": 0,
            "timezone_id": "UTC",
            "availability": "available",
            "source_ref": f"places:{pid}",
            "retrieved_at": NOW,
            **changes,
        }
    )


def activity(aid="one", pid="a", start="10:00", end="11:00", **changes):
    return Activity(
        **{
            "activity_id": aid,
            "source_place_id": pid,
            "place_name": pid,
            "activity_kind": "main_poi",
            "title": "Visit",
            "start_time": f"{DAY}T{start}:00+00:00",
            "end_time": f"{DAY}T{end}:00+00:00",
            **changes,
        }
    )


def contract(inclusion=None, preferences=""):
    request = PlanningRequest(
        destination="Fixture",
        start_date=DAY,
        end_date=DAY,
        traveler_count=2,
        budget={"amount": 100, "currency": "GBP"},
    )
    return InterpretedTripRequirements(
        request_sha256="offline",
        structured_input_sha256=request.structured_hash(),
        interpretation_origin="skipped_empty",
        requirements=request.trip_requirements().model_copy(update={"preferences": [preferences]}),
        named_places=()
        if inclusion is None
        else (
            {
                "requirement_id": "named_1",
                "place_text": "a",
                "inclusion": inclusion,
                "source_refs": ({"quote": "a", "start": 0, "end": 1, "occurrence": 0},),
            },
        ),
        requested_place_information=(),
        transport_preference=None,
        semantic_requirements=(),
        subjects=(),
        discovery_intents=(),
        experience_evidence_requests=(),
        extraction_issues=(),
    )


def binding(pid="a"):
    return NamedPlaceResolution(
        named_place_intent=NamedPlaceIntent(place_text="a", inclusion="OPTIONAL", source_text="a"),
        search_intent_id="named_1",
        status=NamedPlaceResolutionStatus.RESOLVED,
        matching_place_ids=(pid,),
        resolved_place_id=pid,
    )


def draft(items=None, references=()):
    return V1Itinerary(
        output_version="itinerary_2",
        destination="Fixture",
        start_date=DAY,
        end_date=DAY,
        days=[{"date": DAY, "activities": items if items is not None else [activity()]}],
        reference_recommendations=list(references),
    )


def run(items=None, *, itinerary=None, requirements=None, places=None, **kwargs):
    return validate_draft(
        itinerary or draft(items),
        requirements or contract(),
        window=WINDOW,
        supplied_ids=("a", "b", "c"),
        places=places or (place(), place("b"), place("c")),
        **kwargs,
    )


def findings(report, check):
    return [f for f in report.findings if f.check == check]


def effective(*, closure=False, **changes):
    values = dict(
        place_id="a",
        place_name="a",
        information_need="special_date_hours",
        claim_kind="special_hours",
        value_text="Date-specific hours",
        source_kind="fetched_html",
        source_url="https://venue.example/hours",
        supporting_excerpt="Date-specific hours",
        subject_scope="whole_venue",
        temporal_basis="explicit_date_or_range",
        applicable_start_date=DAY,
        applicable_end_date=DAY,
        schedule_scope="daily",
        opens_at=time(9),
        closes_at=time(17),
        authority_basis="places_first_party_website",
        retrieved_at=NOW,
        source_ref="official:a",
    )
    if closure:
        values.update(
            information_need="date_specific_operational_exception",
            claim_kind="temporary_closure",
            opens_at=None,
            closes_at=None,
        )
    values.update(changes)
    return resolve_effective_evidence(
        place(), (OfficialCurrentEvidence(**values),), trip_start=DAY, trip_end=DAY
    )


def test_diagnostics_review_and_targets_are_separate():
    result = run()
    assert result.diagnostics.days[0].target_status == "below_target"
    assert findings(result, "coverage")[0].status == "NEEDS_REVIEW"
    assert not result.improvement_targets
    reviewed = run(policy=ValidationPolicy(review_targets={"coverage"}))
    assert reviewed.findings == result.findings
    assert reviewed.improvement_targets[0].basis == "review_policy"
    assert not any(f.is_violation for f in reviewed.findings)


@pytest.mark.parametrize(
    "text",
    [
        "Rest day",
        "Revisit intentionally",
        "Architecture firm",
        "Spend all day inside the theme park",
        "",
    ],
)
def test_natural_language_never_changes_verdict_or_manufactures_exception(text):
    report = run(
        [activity(end="18:00", notes=text or None)], requirements=contract(preferences=text)
    )
    assert report == run([activity(end="18:00")])
    assert not any(f.is_violation for f in report.findings)


def test_repetition_does_not_prove_unreasonable_repeat():
    report = run([activity(), activity("two", start="12:00", end="13:00")])
    assert findings(report, "repetition")[0].status == "UNKNOWN"
    assert report.diagnostics.days[0].distinct_main_poi_count == 1
    assert not any(f.is_violation for f in report.findings)


@pytest.mark.parametrize("kind", ["transport", "free_time", "generic_activity", "unknown"])
def test_other_roles_are_uncounted_or_transport_rejected(kind):
    itinerary = draft(
        [activity(activity_kind=kind)],
        [{"place_name": "b", "source_place_id": "b", "reason": "Optional nearby"}],
    )
    if kind == "transport":
        with pytest.raises(ValueError, match="transport activities"):
            run(itinerary=itinerary)
        return
    report = run(itinerary=itinerary)
    assert report.diagnostics.days[0].distinct_main_poi_count == 0
    assert report.diagnostics.unused_supply == 3


@pytest.mark.parametrize("primary_type", ["corporate_office", "consultant", "museum", None])
def test_provider_use_classification_is_never_access_prohibition(primary_type):
    result = run(places=(place(primary_type=primary_type), place("b"), place("c")))
    assert result.place_use_observations[0].primary_type == primary_type
    assert findings(result, "visitor_suitability")[0].status == "UNKNOWN"
    assert not any(f.is_violation for f in result.findings)


def test_all_nested_overlaps_are_confirmed_without_mutating_order():
    itinerary = draft(
        [
            activity("outer", end="16:00"),
            activity("late", "b", "14:00", "15:00"),
            activity("early", "c", "11:00", "12:00"),
        ]
    )
    before = itinerary.model_dump_json()
    report = run(itinerary=itinerary)
    overlaps = findings(report, "overlap")
    assert len(overlaps) == 2
    assert all(f.status == "CONFIRMED" and f.evidence_refs for f in overlaps)
    assert len(report.improvement_targets) == 2
    assert itinerary.model_dump_json() == before


def test_touching_windows_do_not_overlap_and_naive_endpoints_are_rejected():
    assert not findings(run([activity(), activity("two", "b", "11:00", "12:00")]), "overlap")
    naive = activity(
        "two", "b", start_time=datetime(2026, 9, 26, 10), end_time=datetime(2026, 9, 26, 11)
    )
    with pytest.raises(ValueError, match="timezone_offset_missing"):
        run([activity(), naive])


@pytest.mark.parametrize(
    "inclusion,present,status",
    [
        ("REQUIRED", False, "CONFIRMED"),
        ("REQUIRED", True, "PASS"),
        ("EXCLUDED", True, "CONFIRMED"),
        ("EXCLUDED", False, "PASS"),
    ],
)
def test_named_requirements_use_canonical_inclusion_not_resolver_optional(
    inclusion, present, status
):
    report = run(
        [activity(pid="a" if present else "b")],
        requirements=contract(inclusion),
        named_resolutions=(binding(),),
    )
    assert findings(report, "named_requirement")[0].status == status


def test_reference_does_not_satisfy_required_identity():
    report = run(
        itinerary=draft(
            [activity(pid="b")],
            [
                {
                    "place_name": "a",
                    "source_place_id": "a",
                    "reason": "Optional",
                }
            ],
        ),
        requirements=contract("REQUIRED"),
        named_resolutions=(binding(),),
    )
    assert findings(report, "named_requirement")[0].status == "CONFIRMED"


@pytest.mark.parametrize(
    "resolutions",
    [
        (),
        (binding(), binding()),
        (replace(binding(), matching_place_ids=("a", "b")),),
        (replace(binding(), resolved_place_id=None),),
        (
            replace(
                binding(),
                named_place_intent=NamedPlaceIntent(
                    place_text="a", inclusion="OPTIONAL", source_text="unrelated"
                ),
            ),
        ),
    ],
)
def test_missing_ambiguous_or_unprovenanced_bindings_are_unknown(resolutions):
    result = run(requirements=contract("REQUIRED"), named_resolutions=resolutions)
    assert findings(result, "named_requirement")[0].status == "UNKNOWN"


def test_foreign_requirement_and_outside_supply_use_boundary_errors():
    with pytest.raises(ValueError, match="provenance"):
        run(named_resolutions=(binding(),))
    with pytest.raises(ValueError, match="outside"):
        run([activity(pid="invented")])


@pytest.mark.parametrize("changes", [{}, {"closure": True}, {"closes_at": time(10, 30)}])
def test_opening_uses_existing_resolver_without_inventing_visit_mode(changes):
    result = run(effective_places=(effective(**changes),))
    finding = findings(result, "opening")[0]
    assert finding.status == ("PASS" if not changes else "CONFIRMED")
    assert finding.evidence_refs == ("official:a",)
    assert finding.is_violation == bool(changes)


@pytest.mark.parametrize(
    "changes",
    [
        {
            "applicable_start_date": DAY + timedelta(days=1),
            "applicable_end_date": DAY + timedelta(days=1),
        },
        {"subject_scope": "sub_area"},
        {"schedule_scope": "weekly_pattern"},
        {"temporal_basis": "current_general_policy"},
        {"opens_at": None},
        {"opens_at": time(20), "closes_at": time(5)},
    ],
)
def test_inapplicable_or_incomplete_hours_stay_unknown(changes):
    assert findings(run(effective_places=(effective(**changes),)), "opening")[0].status == "UNKNOWN"


@pytest.mark.parametrize("timezone", [None, "Invalid/Zone"])
def test_missing_timezone_does_not_confirm_hours(timezone):
    if timezone == "Invalid/Zone":
        with pytest.raises(ValueError, match="timezone_invalid"):
            run(places=(place(timezone_id=timezone),), effective_places=(effective(closure=True),))
        return
    result = run(
        places=(place(timezone_id=timezone), place("b"), place("c")),
        effective_places=(effective(closure=True),),
    )
    assert findings(result, "opening")[0].status == "UNKNOWN"


def test_conflicting_hours_are_not_upgraded_to_pass():
    evidence = effective()
    conflict = evidence.model_copy(
        update={
            "facts": tuple(f.model_copy(update={"relation": "conflict"}) for f in evidence.facts)
        }
    )
    assert findings(run(effective_places=(conflict,)), "opening")[0].status == "UNKNOWN"


@pytest.mark.parametrize(
    "mode,evidence_type",
    [
        ("WALK", "provider_observed"),
        ("TRANSIT", "provider_observed"),
        ("DRIVE", "mirrored_reverse_estimate"),
    ],
)
def test_route_mode_direction_and_departure_are_not_assumed(mode, evidence_type):
    routes = RouteEvidenceBundle(
        baseline={
            "travel_mode": mode,
            "mode_reason": "fixture",
            "availability": "available",
            "retrieved_at": NOW,
            "source_ref": "routes:fixture",
            "elements": [
                {
                    "origin_place_id": "b",
                    "destination_place_id": "a",
                    "duration_seconds": 90000,
                    "availability": "available",
                    "evidence_type": evidence_type,
                }
            ],
        }
    )
    result = run([activity(), activity("two", "b", "12:00", "13:00")], routes=routes)
    assert findings(result, "route")[0].status == "UNKNOWN"


@pytest.mark.parametrize(
    "cost", [None, {"amount": 10000, "currency": "GBP"}, {"amount": 0, "currency": "USD"}]
)
def test_model_costs_do_not_verify_budget(cost):
    assert findings(run([activity(estimated_cost=cost)]), "budget")[0].status == "UNKNOWN"


def test_zero_external_calls_and_complete_snapshot_unchanged(monkeypatch):
    import openai.resources.chat.completions
    import openai.resources.embeddings
    import psycopg

    def forbidden(*args, **kwargs):
        pytest.fail("Validator attempted external work")

    for target, name in [
        (socket.socket, "connect"),
        (socket.socket, "connect_ex"),
        (socket, "create_connection"),
        (httpx.Client, "send"),
        (httpx.AsyncClient, "send"),
        (openai.resources.chat.completions.Completions, "create"),
        (openai.resources.chat.completions.AsyncCompletions, "create"),
        (openai.resources.embeddings.Embeddings, "create"),
        (openai.resources.embeddings.AsyncEmbeddings, "create"),
        (psycopg, "connect"),
        (psycopg.Connection, "connect"),
        (psycopg.AsyncConnection, "connect"),
    ]:
        monkeypatch.setattr(target, name, forbidden)
    itinerary = draft([activity("two", "b", "12:00", "13:00"), activity()])
    itinerary.set_cost_projections((EstimatedCostProjectionDiagnostic("field", "explicit_null"),))
    evidence = (effective(),)
    places = (place(), place("b"), place("c"))
    requirements = contract("REQUIRED")
    before = (
        itinerary.model_dump_json(),
        itinerary.cost_projections,
        tuple(p.model_dump_json() for p in places),
        evidence,
        requirements.model_dump_json(),
    )
    run(
        itinerary=itinerary,
        places=places,
        effective_places=evidence,
        requirements=requirements,
        named_resolutions=(binding(),),
    )
    assert before == (
        itinerary.model_dump_json(),
        itinerary.cost_projections,
        tuple(p.model_dump_json() for p in places),
        evidence,
        requirements.model_dump_json(),
    )


def test_cancellation_is_not_reclassified(monkeypatch):
    def cancelled(*args):
        raise asyncio.CancelledError

    monkeypatch.setattr("backend.app.evidence.opening_hours.ZoneInfo", cancelled)
    with pytest.raises(asyncio.CancelledError):
        run(effective_places=(effective(),))


def test_finding_contract_rejects_unknown_violation_and_unsourced_confirmation():
    with pytest.raises(ValidationError):
        Finding(
            finding_id="one", check="budget", status="UNKNOWN", reason="missing", is_violation=True
        )
    with pytest.raises(ValidationError):
        Finding(
            finding_id="one",
            check="overlap",
            status="CONFIRMED",
            reason="overlap",
            is_violation=True,
        )


def test_long_required_visit_is_not_a_density_violation():
    result = run(
        [activity(end="18:00")], requirements=contract("REQUIRED"), named_resolutions=(binding(),)
    )
    assert findings(result, "named_requirement")[0].status == "PASS"
    assert findings(result, "coverage")[0].status == "NEEDS_REVIEW"
    assert not result.improvement_targets


def test_semantic_rest_requirement_remains_open_not_keyword_executable():
    data = contract().model_dump()
    data["semantic_requirements"] = [
        {
            "requirement_id": "semantic_1",
            "normalized_text": "Rest throughout the day",
            "kind": "preference",
            "polarity": "favor",
            "strength": "high",
            "scope": "itinerary_style",
            "subject_refs": ("party",),
            "source_refs": ({"quote": "rest", "start": 0, "end": 4, "occurrence": 0},),
        }
    ]
    result = run([], requirements=InterpretedTripRequirements.model_validate(data))
    assert not any(f.is_violation for f in result.findings)
    assert findings(result, "semantic_requirements")[0].status == "UNKNOWN"


def test_cross_day_overlap_and_mixed_awareness():
    next_day = DAY + timedelta(days=1)
    itinerary = draft([activity(end_time=f"{next_day}T02:00:00+00:00")])
    data = itinerary.model_dump()
    data["end_date"] = next_day
    data["days"].append(
        {
            "date": next_day,
            "activities": [
                activity(
                    "two",
                    "b",
                    start_time=f"{next_day}T01:00:00+00:00",
                    end_time=f"{next_day}T03:00:00+00:00",
                )
            ],
        }
    )
    itinerary = V1Itinerary.model_validate(data)
    requirements = contract().model_copy(
        update={"requirements": contract().requirements.model_copy(update={"end_date": next_day})}
    )
    assert (
        findings(run(itinerary=itinerary, requirements=requirements), "overlap")[0].status
        == "CONFIRMED"
    )
    second = itinerary.days[1].activities[0]
    second.start_time = second.start_time.replace(tzinfo=None)
    second.end_time = second.end_time.replace(tzinfo=None)
    with pytest.raises(ValueError, match="timezone_offset_missing"):
        run(itinerary=itinerary, requirements=requirements)


def test_shared_date_and_schema_checks_remain_preconditions():
    itinerary = draft()
    itinerary.days[0].activities[0].start_time = datetime(2026, 9, 24, 10)
    itinerary.days[0].activities[0].end_time = datetime(2026, 9, 24, 11)
    with pytest.raises(ValueError):
        run(itinerary=itinerary)
    itinerary = draft()
    itinerary.days[0].activities.append(itinerary.days[0].activities[0].model_copy())
    with pytest.raises(ValidationError, match="activity_id"):
        run(itinerary=itinerary)


def test_timezone_conflict_is_rejected_and_unparsed_places_hours_remain_unknown():
    with pytest.raises(ValueError, match="timezone_offset_conflict"):
        run(
            [activity(start_time=f"{DAY}T19:00:00+10:00", end_time=f"{DAY}T20:00:00+10:00")],
            effective_places=(effective(),),
        )
    p = place(
        opening_hours={
            "applicability": "regular",
            "weekday_descriptions": [
                "Saturday: Closed",
                "The venue is never accessible to the public",
            ],
        }
    )
    assert findings(run(places=(p,)), "opening")[0].status == "UNKNOWN"


def test_unknown_cannot_become_improvement_target():
    from backend.app.versions.v3.models import ValidationReport

    data = run().model_dump()
    unknown = next(f for f in data["findings"] if f["status"] == "UNKNOWN")
    data["improvement_targets"] = [{"finding_id": unknown["finding_id"], "basis": "review_policy"}]
    with pytest.raises(ValidationError, match="preserve"):
        ValidationReport.model_validate(data)
