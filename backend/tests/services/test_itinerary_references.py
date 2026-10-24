"""Offline output-role contracts and identity ownership across both engines."""

import asyncio
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.app.api.schemas.planning import CompletedPlanningResponse
from backend.app.llm.azure_foundry.dto import FoundryItineraryDTO, FoundryPrimaryItineraryDTO
from backend.app.llm.azure_foundry.itinerary_cost_projection import map_foundry_v1_itinerary
from backend.app.llm.azure_foundry.mapping import map_foundry_itinerary
from backend.app.policies.itinerary_output import output_role_summary, validate_output_sources
from backend.app.schemas.itinerary import Activity, Itinerary
from backend.app.services import preference_interpretation as _bootstrap  # noqa: F401
from backend.app.services.product_presentation import present_product
from backend.app.versions.v0.runner import run_v0
from backend.tests.llm.azure_foundry.test_mapping import make_itinerary as make_dto
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient, make_itinerary


def reference(index=1, **changes):
    return {
        "place_name": f"Venue {index}",
        "source_place_id": None,
        "reason": "An extra option if interested.",
        "associated_day": None,
        "area": None,
        "uncertainty": None,
        **changes,
    }


def itinerary(references=()):
    data = make_itinerary().model_dump()
    data.update(output_version="itinerary_2", reference_recommendations=list(references))
    return Itinerary.model_validate(data)


def evidence(pid="cafe"):
    return SimpleNamespace(
        place_id=pid,
        name=f"Source {pid}",
        formatted_address="Known district",
        source_ref=f"google_places:{pid}",
    )


@pytest.mark.parametrize("count", [0, 1, 3, 20])
def test_shared_reference_bounds_and_no_times_or_costs(count):
    result = itinerary([reference(i) for i in range(count)])
    assert len(result.reference_recommendations) == count
    for item in result.reference_recommendations:
        assert (
            not {"start_time", "end_time", "estimated_cost", "booking_status"}
            & item.model_dump().keys()
        )
    with pytest.raises(ValidationError):
        itinerary([reference(i) for i in range(21)])


def test_activity_times_required_and_historical_defaults():
    data = make_itinerary().model_dump()
    data.pop("output_version")
    data.pop("reference_recommendations")
    data["days"][0]["activities"][0].pop("source_place_id")
    old = Itinerary.model_validate(data)
    assert old.output_version == "itinerary_1" and old.reference_recommendations == []
    assert old.days[0].activities[0].source_place_id is None
    activity = old.days[0].activities[0].model_dump()
    del activity["start_time"]
    with pytest.raises(ValidationError):
        Activity.model_validate(activity)


@pytest.mark.parametrize("day", [None, "2026-09-12"])
def test_associated_day(day):
    assert itinerary([reference(associated_day=day)])
    with pytest.raises(ValidationError):
        itinerary([reference(associated_day="2026-09-13")])


def test_duplicates_and_overlap_are_invalid():
    with pytest.raises(ValidationError):
        itinerary([reference(), reference()])
    data = itinerary().model_dump()
    data["days"][0]["activities"][0].update(source_place_id="cafe", place_name="Cafe")
    data["reference_recommendations"] = [reference(source_place_id="cafe")]
    with pytest.raises(ValidationError):
        Itinerary.model_validate(data)


def test_v0_source_ownership_and_single_generation():
    with pytest.raises(ValueError, match="at most three"):
        validate_output_sources(itinerary([reference(i) for i in range(4)]))
    request = make_request()
    request = request.model_copy(update={"destination": "Kyoto", "end_date": date(2026, 9, 12)})
    client = FakeStructuredLLMClient([itinerary([reference()])])
    result = asyncio.run(run_v0(request, client, reference_date=date(2026, 9, 11)))
    assert len(client.calls) == 1
    assert result.itinerary.reference_recommendations[0].source_ref is None
    assert result.itinerary.reference_recommendations[0].source_place_id is None
    for change in ({"source_ref": "forged"}, {"source_place_id": "google-fake"}):
        with pytest.raises(ValueError):
            validate_output_sources(itinerary([reference(**change)]))


def test_v0_preserves_model_estimated_transport_and_nearby_without_extra_generation():
    request = make_request().model_copy(
        update={"destination": "Kyoto", "end_date": date(2026, 9, 12)}
    )
    planned = itinerary([reference(associated_day="2026-09-12", area="Planned district")])
    first = (
        planned.days[0]
        .activities[0]
        .model_copy(update={"activity_kind": "main_poi", "place_name": "Fushimi Inari Shrine"})
    )
    journey = first.model_copy(
        update={
            "activity_id": "journey-1",
            "activity_kind": "transport",
            "title": "Walk to the next visit",
            "place_name": None,
            "source_place_id": None,
            "estimated_cost": None,
            "start_time": first.end_time,
            "end_time": first.end_time + timedelta(minutes=20),
            "notes": "Model estimate; route and duration have not been checked.",
        }
    )
    second = first.model_copy(
        update={
            "activity_id": "visit-2",
            "title": "Second visit",
            "place_name": "Second venue",
            "start_time": journey.end_time,
            "end_time": journey.end_time + timedelta(hours=1),
        }
    )
    planned.days[0].activities = [first, journey, second]
    client = FakeStructuredLLMClient([planned])

    result = asyncio.run(run_v0(request, client, reference_date=date(2026, 9, 11)))

    assert len(client.calls) == 1
    assert result.itinerary.days[0].activities == [first, journey, second]
    assert result.itinerary.reference_recommendations == planned.reference_recommendations
    assert result.itinerary.transfers == []
    assert result.generation_diagnostics.days[0].transport_activity_count == 1
    assert result.generation_diagnostics.days[0].main_activity_count == 2


def test_v1_model_references_rejected_even_for_supplied_ids():
    for pid in (None, "unknown", "cafe"):
        with pytest.raises(ValueError, match="V1 model references"):
            validate_output_sources(
                itinerary([reference(source_place_id=pid)]),
                places=[evidence()],
                supplied_ids=["cafe"],
            )


def test_required_reference_is_not_scheduled_and_outside_supply_is_separate():
    result = itinerary([reference(source_place_id="new"), reference(2, source_place_id="cafe")])
    summary = output_role_summary(
        result,
        SimpleNamespace(selected_place_ids=("cafe", "unused"), required_canonical_ids=("cafe",)),
    )
    assert summary.scheduled_place_ids == ()
    assert summary.reference_place_ids == ("cafe", "new")
    assert summary.unscheduled_required_ids == ("cafe",)
    assert summary.unused_candidate_ids == ("unused",)


@pytest.mark.parametrize(
    ("kind", "time_use", "scheduled", "missing"),
    [
        ("generic_activity", "free_window", (), ("park",)),
        ("generic_activity", "scheduled", ("park",), ("park",)),
        ("main_poi", "scheduled", ("park",), ()),
    ],
)
def test_declared_output_roles_distinguish_suggestions_and_required_visits(
    kind, time_use, scheduled, missing
):
    data = itinerary().model_dump()
    data["output_version"] = "itinerary_3"
    activity = data["days"][0]["activities"][0]
    activity.update(
        activity_kind=kind, time_use=time_use, source_place_id="park", place_name="Park"
    )
    data["days"][0]["activities"] = [activity]
    result = Itinerary.model_validate(data)

    summary = output_role_summary(
        result, SimpleNamespace(selected_place_ids=("park",), required_canonical_ids=("park",))
    )

    assert summary.scheduled_place_ids == scheduled
    assert summary.unscheduled_required_ids == missing
    assert summary.supply_not_scheduled_ids == (() if scheduled else ("park",))


def test_new_wire_requires_fields_and_rejects_authoritative_source_ref():
    data = make_dto().model_dump()
    del data["reference_recommendations"]
    with pytest.raises(ValidationError):
        FoundryItineraryDTO.model_validate(data)
    data = make_dto().model_dump()
    data["reference_recommendations"] = [reference(source_ref="fabricated")]
    with pytest.raises(ValidationError):
        FoundryItineraryDTO.model_validate(data)


def test_primary_cost_projection_and_final_api_contract():
    data = make_dto().model_dump(exclude={"reference_recommendations"})
    for day in data["days"]:
        for activity in day["activities"]:
            activity.pop("transport")  # V1 provider output excludes V0's declaration field.
    data["days"][0]["activities"][0]["source_place_id"] = "museum"
    data["days"][0]["activities"][0]["estimated_cost"]["amount"] = "10-20"
    result = map_foundry_v1_itinerary(FoundryPrimaryItineraryDTO.model_validate(data))
    result = validate_output_sources(result, places=[evidence("museum")], supplied_ids=["museum"])
    assert str(result.days[0].activities[0].estimated_cost.amount) == "15"
    assert result.cost_projections and result.reference_recommendations == []
    public = present_product(
        SimpleNamespace(
            requirements=make_request().trip_requirements(),
            itinerary=result,
            generation_diagnostics=None,
        ),
        SimpleNamespace(weather=None),
    )
    response = CompletedPlanningResponse(**public.model_dump())
    assert str(response.itinerary.days[0].activities[0].estimated_cost.amount) == "15"
    assert "output_version" not in response.itinerary.model_dump()
    assert "cost_projections" not in response.itinerary.model_dump()
    with pytest.raises(ValidationError):
        FoundryPrimaryItineraryDTO.model_validate({**data, "reference_recommendations": []})
    plain = make_dto().model_dump()
    plain["reference_recommendations"] = [reference()]
    assert (
        len(
            map_foundry_itinerary(
                FoundryItineraryDTO.model_validate(plain)
            ).reference_recommendations
        )
        == 1
    )


@pytest.mark.parametrize("identifier", [None, "excluded"])
def test_named_v1_activity_needs_supplied_identity(identifier):
    data = itinerary().model_dump()
    data["days"][0]["activities"][0].update(place_name="Venue", source_place_id=identifier)
    with pytest.raises(ValueError):
        validate_output_sources(
            Itinerary.model_validate(data), places=[evidence()], supplied_ids=["cafe"]
        )


def test_model_transport_is_v0_only_at_output_acceptance():
    data = itinerary().model_dump()
    data["days"][0]["activities"][0].update(
        activity_kind="transport", title="Walking", place_name=None, source_place_id=None
    )
    value = Itinerary.model_validate(data)
    assert validate_output_sources(value).days[0].activities[0].activity_kind == "transport"
    with pytest.raises(ValueError, match="transport activities"):
        validate_output_sources(value, places=[], supplied_ids=[])


def test_model_transport_is_v0_only_in_generation_schema():
    data = make_dto().model_dump()
    data["days"][0]["activities"][0]["activity_kind"] = "transport"
    value = FoundryItineraryDTO.model_validate(data)
    assert value.days[0].activities[0].activity_kind == "transport"
    del data["reference_recommendations"]
    with pytest.raises(ValidationError):
        FoundryPrimaryItineraryDTO.model_validate(data)


def test_scheduled_required_cafe_counts_by_id_without_name_guessing():
    data = itinerary().model_dump()
    data["days"][0]["activities"][0].update(place_name="Model spelling", source_place_id="cafe")
    result = validate_output_sources(
        Itinerary.model_validate(data), places=[evidence()], supplied_ids=["cafe"]
    )
    assert result.days[0].activities[0].place_name == "Source cafe"
    summary = output_role_summary(
        result, SimpleNamespace(selected_place_ids=("cafe",), required_canonical_ids=("cafe",))
    )
    assert summary.scheduled_place_ids == ("cafe",)
    assert summary.unscheduled_required_ids == ()


def test_unlinked_v0_reference_cannot_repeat_a_scheduled_name():
    data = itinerary([reference(place_name="Cafe")]).model_dump()
    data["days"][0]["activities"][0]["place_name"] = "Cafe"
    with pytest.raises(ValidationError, match="Scheduled venues"):
        Itinerary.model_validate(data)
