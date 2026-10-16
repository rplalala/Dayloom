"""Evidence-bound named place correspondence, independent of lexical equality."""

import asyncio
import json

import pytest

from backend.app.schemas.interpreted_requirements import NamedRequirement, SourceReference
from backend.tests.candidate_fixtures import candidate_fixture


def binding_case(requested, provider_name):
    fixture = candidate_fixture(1, 0)
    requirement = NamedRequirement(
        requirement_id="named_1",
        place_text=requested,
        inclusion="REQUIRED",
        source_refs=(SourceReference(quote=requested, occurrence=0, start=0, end=len(requested)),),
    )
    place = fixture.canonical_places[0]
    place = place.model_copy(
        update={
            "candidate": place.candidate.model_copy(update={"name": provider_name}),
            "query_hits": [place.query_hits[0].model_copy(update={"intent_id": "named_1"})],
        }
    )
    return fixture.requirements.model_copy(update={"named_places": (requirement,)}), (place,)


class CorrespondenceModel:
    def __init__(self, relation="same_place", mutation=None):
        self.relation, self.mutation, self.calls = relation, mutation, []

    async def generate_named_place_binding_structured(self, **kwargs):
        payload = json.loads(kwargs["user_prompt"])
        self.calls.append(payload)
        result = {
            "decisions": [
                {
                    "requirement_ref": r["requirement_ref"],
                    "candidates": [
                        {
                            "candidate_ref": c["candidate_ref"],
                            "relation": self.relation,
                            "evidence_refs": [c["evidence_ref"]],
                            "reason": "Saved normalized venue evidence",
                        }
                        for c in r["candidates"]
                    ],
                }
                for r in payload["requirements"]
            ]
        }
        if self.mutation:
            self.mutation(result)
        return result


@pytest.mark.parametrize(
    "requested,provider",
    [
        ("Sagrada Família", "Basilica of the Sagrada Familia"),
        ("British Museum", "The British Museum"),
    ],
)
def test_supported_provider_name_variation_adopts_bound_identity(requested, provider):
    from backend.app.services.named_place_binding import NamedPlaceBinding

    contract, places = binding_case(requested, provider)
    model = CorrespondenceModel()
    result = asyncio.run(NamedPlaceBinding(model).resolve(contract, places))
    assert result[0].resolved_place_id == places[0].candidate.place_id
    assert result[0].search_intent_id == "named_1"
    assert model.calls[0]["requirements"][0]["place_text"] == requested


def test_single_search_hit_does_not_override_unresolved_judgment():
    from backend.app.services.named_place_binding import NamedPlaceBinding

    contract, places = binding_case("Museum", "Museum gift shop")
    result = asyncio.run(
        NamedPlaceBinding(CorrespondenceModel("unresolved")).resolve(contract, places)
    )
    assert result[0].resolved_place_id is None
    assert result[0].status == "insufficient_evidence"


def test_foreign_candidate_reference_is_a_system_failure_without_retry():
    from backend.app.services.named_place_binding import NamedPlaceBinding, NamedPlaceBindingError

    contract, places = binding_case("Museum", "Museum")
    model = CorrespondenceModel(
        mutation=lambda r: r["decisions"][0]["candidates"][0].update(candidate_ref="foreign")
    )
    with pytest.raises(NamedPlaceBindingError, match="invalid_named_binding_contract"):
        asyncio.run(NamedPlaceBinding(model).resolve(contract, places))
    assert len(model.calls) == 1


def test_two_supported_branches_remain_ambiguous_independent_of_order():
    from backend.app.services.named_place_binding import NamedPlaceBinding

    contract, (place,) = binding_case("Museum", "Museum")
    other = place.model_copy(
        update={"candidate": place.candidate.model_copy(update={"place_id": "branch-2"})}
    )
    for candidates in [(place, other), (other, place)]:
        result = asyncio.run(NamedPlaceBinding(CorrespondenceModel()).resolve(contract, candidates))
        assert result[0].resolved_place_id is None
        assert result[0].status == "ambiguous_candidates"
        assert set(result[0].considered_place_ids) == {"branch-2", place.candidate.place_id}


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(decisions=[]),
        lambda r: r["decisions"].append(r["decisions"][0]),
        lambda r: r["decisions"][0]["candidates"][0].update(evidence_refs=["e99"]),
        lambda r: r["decisions"][0]["candidates"][0].update(evidence_refs=[]),
    ],
)
def test_incomplete_or_foreign_evidence_never_authorizes_identity(mutation):
    from backend.app.services.named_place_binding import NamedPlaceBinding, NamedPlaceBindingError

    contract, places = binding_case("Museum", "Museum")
    with pytest.raises(NamedPlaceBindingError, match="invalid_named_binding_contract"):
        asyncio.run(
            NamedPlaceBinding(CorrespondenceModel(mutation=mutation)).resolve(contract, places)
        )


@pytest.mark.parametrize(
    "arguments,status",
    [
        ({"places": ()}, "empty_search"),
        ({"failures": ("named_1",)}, "search_failed"),
        ({"not_attempted": ("named_1",)}, "search_not_issued_budget"),
    ],
)
def test_unavailable_search_is_not_replaced_by_a_model_guess(arguments, status):
    from backend.app.services.named_place_binding import NamedPlaceBinding

    contract, places = binding_case("Museum", "Museum")
    model = CorrespondenceModel()
    result = asyncio.run(
        NamedPlaceBinding(model).resolve(contract, **{"places": places, **arguments})
    )
    assert result[0].status == status
    assert result[0].resolved_place_id is None
    assert not model.calls


def test_binding_uses_owned_query_id_when_two_surfaces_are_equal():
    from backend.app.services.named_place_binding import NamedPlaceBinding

    contract, (place,) = binding_case("Museum", "Museum")
    second = contract.named_places[0].model_copy(
        update={"requirement_id": "named_2", "inclusion": "EXCLUDED"}
    )
    contract = contract.model_copy(update={"named_places": (*contract.named_places, second)})
    other = place.model_copy(
        update={
            "candidate": place.candidate.model_copy(update={"place_id": "other-region"}),
            "query_hits": [place.query_hits[0].model_copy(update={"intent_id": "named_2"})],
        }
    )
    result = asyncio.run(NamedPlaceBinding(CorrespondenceModel()).resolve(contract, (other, place)))
    assert result[0].resolved_place_id == place.candidate.place_id
    assert result[1].resolved_place_id == "other-region"
