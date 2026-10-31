"""New tools output requires an acquired, semantically eligible principal place."""

from types import SimpleNamespace

import pytest

from backend.app.policies.itinerary_output import validate_output_sources
from backend.tests.policies.test_itinerary_ordering import make_itinerary


@pytest.mark.parametrize("eligible", [True, False, None])
def test_new_output_accepts_only_assessed_principals_independent_of_photos(eligible):
    itinerary = make_itinerary("v1", ordered=True)
    itinerary.output_version = "itinerary_3"
    places, rows = [], []
    for day in itinerary.days:
        for activity in day.activities:
            activity.activity_kind, activity.time_use = "main_poi", "scheduled"
            places.append(
                SimpleNamespace(
                    place_id=activity.source_place_id,
                    name=activity.place_name,
                    formatted_address=None,
                )
            )
            if eligible is not None:
                rows.append(
                    SimpleNamespace(place_id=activity.source_place_id, main_eligible=eligible)
                )
    kwargs = dict(
        places=places, supplied_ids=[p.place_id for p in places], semantic_assessments=rows
    )
    if eligible:
        assert (
            validate_output_sources(itinerary, **kwargs).days[0].activities[0].activity_kind
            == "main_poi"
        )
    else:
        with pytest.raises(ValueError, match="Principal visit requires an eligible acquired place"):
            validate_output_sources(itinerary, **kwargs)
