"""Source-preserving declarations establish populations without semantic model review."""

import copy

import pytest

from backend.activity_semantics import read_activity_claim
from backend.evaluation.occupancy import prepare_occupancy
from backend.evaluation.projection import project
from backend.evaluation.semantic_readiness import review_readiness
from backend.tests.schemas.test_activity_semantics import itinerary


@pytest.mark.parametrize("time_use,count", [("scheduled", 1), ("free_window", 0)])
def test_named_nonprimary_walk_retains_role_and_explicit_time_use(time_use, count):
    raw = itinerary(time_use=time_use, place_name="Left Bank", notes="Relaxed and movable")
    original = copy.deepcopy(raw)
    projection = project(raw, {}, version="v1")
    assert projection["activities"][0]["evaluation_role"] == "transition"
    occupancy = prepare_occupancy(projection, []).to_dict()
    assert len(occupancy["commitments"]) == count
    assert not occupancy["candidates"]
    intake = {
        "batch_id": "synthetic",
        "revision": "1",
        "inventory": [
            {
                "input_sha256": "a" * 64,
                "requirement_spec": {"obligations": []},
                "runs": {"v1": {"final": projection}},
            }
        ],
    }
    assert review_readiness(intake)["status"] == "ready"
    assert raw == original


def test_legacy_adapter_labels_derived_meaning_without_altering_the_wire():
    raw = {"activity_kind": "main_poi"}
    claim = read_activity_claim(raw, "itinerary_2")
    assert (claim.time_use, claim.provenance) == ("scheduled", "legacy_policy_derived")
    assert raw == {"activity_kind": "main_poi"}
    assert (
        read_activity_claim({"activity_kind": "generic_activity"}, "itinerary_2").time_use is None
    )
