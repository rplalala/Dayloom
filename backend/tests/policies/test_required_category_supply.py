"""A required category retains an opportunity when optional goals compete for capacity."""

from backend.app.policies.interpreted_requirements import canonicalize_requirements
from backend.app.runtime.config_loader import load_runtime_config
from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.schemas.poi_semantics import POISemanticAssessment, RequirementMatch
from backend.tests.policies.test_planning_supply import candidate, select
from backend.tests.request_fixtures import make_request
from backend.tests.services.test_required_categories import category_draft


def test_required_category_precedes_optional_count_goal_at_capacity():
    optional = "A garden is preferred twice."
    required = "Visit a workshop; it is essential."
    data = category_draft(optional, frequency="exact", count=2, strength="high").model_dump(
        mode="json"
    )
    data["semantic_requirements"][0]["local_key"] = "optional"
    data["semantic_requirements"].append(
        category_draft(required).model_dump()["semantic_requirements"][0]
    )
    data["discovery_intents"] = [
        {"requirement_refs": [key], "query_text": text, "purpose": "activity_or_category"}
        for key, text in (("optional", optional), ("visit", required))
    ]
    contract = canonicalize_requirements(
        InterpretationDraft.model_validate(data),
        make_request(optional + " " + required),
    )
    ids = {r.normalized_text: r.requirement_id for r in contract.semantic_requirements}
    intents = {d.requirement_refs[0]: d.intent_id for d in contract.discovery_intents}
    judgments = {
        pid: POISemanticAssessment(
            place_id=pid,
            visit_object=pid,
            role="attraction",
            categories=[],
            reason="Fixture",
            evidence_refs=[f"google_places:{pid}"],
            exception_requirement_ids=[],
            matches=[
                RequirementMatch(
                    requirement_id=rid,
                    relation="supported" if rid == ids[text] else "mismatch",
                    evidence_refs=[f"google_places:{pid}"],
                )
                for rid in ids.values()
            ],
        )
        for pid, text in (("a", optional), ("z", required))
    }
    result = select(
        [
            candidate(pid, intents=(intents[ids[text]],))
            for pid, text in (("a", optional), ("z", required))
        ],
        contract,
        capacity=1,
        semantic_assessments=judgments,
        semantic_config=load_runtime_config().poi_semantics,
    )
    assert result.selected_place_ids == ("z",)
