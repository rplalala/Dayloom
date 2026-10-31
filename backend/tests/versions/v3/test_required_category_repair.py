"""Required category completion and repair, independent of the category's vocabulary."""

import pytest

from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.wiring import operation_scope
from backend.tests.versions.v3.test_b_targets import edit, run, setup, visit
from backend.tests.versions.v3.test_semantic_repair import category_goal


def required_context(ctx, *, matched_ids=("c",), frequency="one_off", count=None):
    ctx = category_goal(ctx, frequency=frequency, count=count, matched_ids=matched_ids)
    requirement = ctx.contract.semantic_requirements[0].model_copy(update={"strength": "hard"})
    return ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(update={"semantic_requirements": (requirement,)}),
        }
    )


def known_matches(ctx, relation="mismatch"):
    from backend.app.schemas.poi_semantics import RequirementMatch

    return ctx.model_copy(
        update={
            "semantic_assessments": tuple(
                row.model_copy(
                    update={
                        "matches": row.matches
                        or [
                            RequirementMatch(
                                requirement_id="semantic_1",
                                relation=relation,
                                evidence_refs=row.evidence_refs,
                            )
                        ]
                    }
                )
                for row in ctx.semantic_assessments
            )
        }
    )


@pytest.mark.parametrize(
    "relation,status",
    [
        ("mismatch", "CONFIRMED"),
        ("related_alternative", "CONFIRMED"),
        ("unresolved", "UNKNOWN"),
    ],
)
def test_required_one_off_cannot_be_completed_without_supported_scheduled_visit(relation, status):
    original, ctx, _, _ = setup([[visit("a", "a")]], reviews=())
    ctx = known_matches(required_context(ctx), relation)
    report = assess(original, ctx)
    assert report.diagnostics.policy_completion == "incomplete"
    finding = next(f for f in report.findings if f.check == "semantic_requirements")
    assert finding.status == status
    assert report.diagnostics.goal_progress[0]["satisfied"] is False


def test_required_one_off_missing_from_draft_is_added_by_existing_repair():
    original, ctx, _, policy = setup([[visit("a", "a")]], reviews=())
    ctx = known_matches(required_context(ctx))
    scope = operation_scope(original, assess(original, ctx), context=ctx, policy=policy)
    result, _ = run(
        (original, ctx, scope, policy),
        [
            [
                edit(
                    "add",
                    pid="c",
                    start="12:00",
                    end="13:00",
                )
            ]
        ],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.adopted_report.diagnostics.goal_progress[0]["matched"] == 1
    assert result.adopted_report.diagnostics.goal_progress[0]["satisfied"] is True


def test_required_visit_is_not_dispensable_for_quantity_optimization():
    from backend.app.versions.v3.repair_targets import dispensable_visit

    original, ctx, _, _ = setup([[visit("a", "a")]], reviews=())
    ctx = known_matches(required_context(ctx, matched_ids=("a",)))
    assert not dispensable_visit(original, "a", ctx)


def test_required_exact_count_remains_unknown_when_another_visit_is_unresolved():
    original, ctx, _, _ = setup(
        [[visit("a", "a"), visit("b", "b", start="12:00", end="13:00")]],
        reviews=(),
    )
    ctx = known_matches(
        required_context(ctx, matched_ids=("a",), frequency="exact", count=1), "unresolved"
    )
    report = assess(original, ctx)
    assert report.diagnostics.policy_completion == "incomplete"
    assert report.diagnostics.goal_progress[0]["satisfied"] is False


def test_free_window_does_not_fulfill_required_visit_even_with_a_matching_place():
    original, ctx, _, _ = setup([[visit("a", "a")]], reviews=())
    ctx = known_matches(required_context(ctx, matched_ids=("a",)))
    original.days[0].activities[0].activity_kind = "free_time"
    original.days[0].activities[0].time_use = "free_window"
    report = assess(original, ctx)
    assert report.diagnostics.goal_progress[0]["matched"] == 0
    assert report.diagnostics.policy_completion == "incomplete"


def test_scheduled_supporting_walk_does_not_fulfill_required_principal_experience():
    original, ctx, _, _ = setup([[visit("a", "a")]], reviews=())
    ctx = known_matches(required_context(ctx, matched_ids=("a",)))
    original.days[0].activities[0].activity_kind = "generic_activity"
    original.days[0].activities[0].time_use = "scheduled"
    report = assess(original, ctx)
    assert report.diagnostics.goal_progress[0]["matched"] == 0
    assert report.diagnostics.policy_completion == "incomplete"


def test_supported_planned_place_association_survives_product_projection_without_photo():
    from types import SimpleNamespace

    from backend.app.product.preview_projection import generated_detail
    from backend.app.services.product_presentation import present_product
    from backend.tests.request_fixtures import make_request
    from backend.tests.services.test_product_presentation import example

    original, ctx, _, _ = setup([[visit("a", "a")]], reviews=())
    original.days[0].activities[0].activity_kind = "main_poi"
    original.days[0].activities[0].time_use = "scheduled"
    ctx = known_matches(required_context(ctx, matched_ids=("a",)))
    result, evidence = example()
    result.itinerary, result.requirements = original, ctx.contract.requirements
    result.generation_diagnostics = assess(original, ctx).diagnostics
    result.v3 = SimpleNamespace(
        final_identity_ids=ctx.original_supply_ids, final_places=ctx.places, repair=None
    )
    result.semantic_assessment = {
        "assessments": [r.model_dump(mode="json") for r in ctx.semantic_assessments]
    }
    public = present_product(result, evidence)
    visit_row = public.required_experiences[0].planned_visits[0]
    assert visit_row.activity_id == "a" and visit_row.date == original.days[0].date
    assert not public._media_bindings
    detail = generated_detail(public, make_request())
    assert detail.completion.required_experiences[0].planned_visits[0] == visit_row


@pytest.mark.parametrize("matching,status", [(True, "unmet"), (False, "unmet")])
def test_product_keeps_required_coverage_through_preview_serialization(matching, status):
    from backend.app.product.detail import ProductDetail
    from backend.app.product.preview_projection import generated_detail
    from backend.app.services.product_presentation import present_product
    from backend.tests.request_fixtures import make_request
    from backend.tests.services.test_product_presentation import example

    original, ctx, _, _ = setup([[visit("a", "a")]], reviews=())
    ctx = known_matches(required_context(ctx, matched_ids=("c",) if matching else ()))
    result, evidence = example()
    result.itinerary = original
    result.requirements = ctx.contract.requirements
    result.generation_diagnostics = assess(original, ctx).diagnostics
    public = present_product(result, evidence)
    row = public.required_experiences[0]
    assert row.status == status and row.scheduled == 0 and row.target == 1
    assert row.source_quotes == ["two zoos"]
    assert row.reason == ("required_visits_not_scheduled" if matching else "no_confirmed_match")
    detail = generated_detail(public, make_request())
    reopened = ProductDetail.model_validate_json(detail.model_dump_json())
    assert reopened.completion.required_experiences == list(public.required_experiences)
