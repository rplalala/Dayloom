"""Current semantic policy over the real stage, including unpublished compensation."""

import pytest

from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.wiring import operation_scope
from backend.tests.versions.v3.test_b_targets import edit, repeated, run, setup, visit


def semantic_rows(ctx):
    from backend.app.schemas.poi_semantics import POISemanticAssessment

    return tuple(
        POISemanticAssessment(
            place_id=p.place_id,
            visit_object=p.name,
            role="attraction",
            categories=["fixture"],
            reason="Synthetic semantic assessment",
            evidence_refs=[p.source_ref],
            matches=[],
            exception_requirement_ids=[],
        )
        for p in ctx.places
    )


def category_goal(ctx, *, frequency="exact", count=2, matched_ids=("a", "b", "c")):
    from backend.app.schemas.interpreted_requirements import ExperienceGoal, SemanticRequirement
    from backend.app.schemas.poi_semantics import RequirementMatch

    requirement = SemanticRequirement(
        requirement_id="semantic_1",
        normalized_text="Visit two different zoos",
        kind="goal",
        polarity="favor",
        strength="high",
        scope="selected_poi_set",
        subject_refs=("party",),
        source_refs=({"quote": "two zoos", "start": 0, "end": 8, "occurrence": 0},),
        experience_goal=ExperienceGoal(
            frequency=frequency,
            count=count,
            target="category",
            distinct_dates=False,
            explicit_primary_exception=False,
            trip_scope="ordinary",
        ),
    )
    rows = tuple(
        row.model_copy(
            update={
                "matches": [
                    RequirementMatch(
                        requirement_id="semantic_1",
                        relation="supported",
                        evidence_refs=row.evidence_refs,
                    )
                ]
                if row.place_id in matched_ids
                else []
            }
        )
        for row in semantic_rows(ctx)
    )
    return ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(update={"semantic_requirements": (requirement,)}),
            "semantic_assessments": rows,
        }
    )


def test_exact_category_excess_is_incomplete_and_repaired():
    original, ctx, _, policy = setup(
        [
            [
                visit("a", "a"),
                visit("b", "b", start="12:00", end="13:00"),
                visit("c", "c", start="15:00", end="16:00"),
            ]
        ],
        reviews=(),
    )
    ctx = category_goal(ctx)
    report = assess(original, ctx)
    assert report.diagnostics.goal_progress[0]["satisfied"] is False
    assert report.diagnostics.policy_completion == "incomplete"
    scope = operation_scope(original, report, context=ctx, policy=policy)
    result, _ = run((original, ctx, scope, policy), [[edit("delete", "c")]])
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.adopted_report.diagnostics.goal_progress[0]["matched"] == 2
    assert result.adopted_report.diagnostics.policy_completion == "complete"


@pytest.mark.parametrize("role", ["generic_activity", "unknown", "free_time"])
def test_canonical_visit_relabeling_cannot_bypass_deduplication(role):
    original, ctx, _, policy = setup(
        [
            [
                visit("a1", "a"),
                visit("a2", "a", start="12:00", end="13:00").model_copy(
                    update={"activity_kind": role}
                ),
            ]
        ],
        reviews=(),
    )
    ctx = ctx.model_copy(update={"semantic_assessments": semantic_rows(ctx)})
    report = assess(original, ctx)
    assert report.diagnostics.policy_completion == "incomplete"
    scope = operation_scope(original, report, context=ctx, policy=policy)
    result, _ = run((original, ctx, scope, policy), [[edit("delete", "a2")]])
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert [a.activity_id for a in result.final.days[0].activities] == ["a1"]
    assert result.adopted_report.diagnostics.policy_completion == "complete"


def test_exact_category_can_reduce_excess_over_multiple_rounds():
    original, ctx, _, policy = setup(
        [
            [
                visit(pid, pid, start=f"{9 + 2 * i:02d}:00", end=f"{10 + 2 * i:02d}:00")
                for i, pid in enumerate("abcd")
            ]
        ],
        reviews=(),
    )
    ctx = category_goal(ctx, matched_ids=tuple("abcd"))
    scope = operation_scope(original, assess(original, ctx), context=ctx, policy=policy)
    result, _ = run((original, ctx, scope, policy), [[edit("delete", "d")], [edit("delete", "c")]])
    assert len(result.rounds[0].adopted.days[0].activities) == 3
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.adopted_report.diagnostics.policy_completion == "complete"


@pytest.mark.parametrize("frequency", ["exact", "minimum"])
def test_explicit_category_shortfall_uses_supported_addition(frequency):
    original, ctx, _, policy = setup(
        [[visit("a", "a"), visit("b", "b", start="12:00", end="13:00")]],
        reviews=(),
    )
    ctx = category_goal(ctx, frequency=frequency, matched_ids=("a", "c"))
    report = assess(original, ctx)
    assert report.diagnostics.policy_completion == "incomplete"
    scope = operation_scope(original, report, context=ctx, policy=policy)
    result, _ = run(
        (original, ctx, scope, policy),
        [
            [
                edit("add", pid="c", start="15:00", end="16:00"),
            ]
        ],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.adopted_report.diagnostics.policy_completion == "complete"
    presented = result.rounds[0].result.candidate_preparation.input_candidates
    assert {c.place.place_id for c in presented} == {"c"}


def test_v0_without_semantic_evidence_does_not_assert_category_shortfall():
    from backend.app.policies.generation_diagnostics import observe_generation
    from backend.tests.versions.v3.test_validation import DAY, WINDOW

    original, ctx, _, _ = setup([[visit("a", "a")]], reviews=())
    ctx = category_goal(ctx)
    original.days[0].activities[0].source_place_id = None
    diagnostics = observe_generation(
        original,
        ctx.contract.requirements,
        reference_date=WINDOW.reference_date,
        contract=ctx.contract,
    )
    assert original.start_date == DAY
    assert diagnostics.policy_completion == "unassessed"
    assert not diagnostics.policy_issues


def test_minimum_category_count_does_not_cap_additional_distinct_visits():
    original, ctx, _, _ = setup(
        [
            [
                visit("a", "a"),
                visit("b", "b", start="12:00", end="13:00"),
                visit("c", "c", start="15:00", end="16:00"),
            ]
        ],
        reviews=(),
    )
    ctx = category_goal(ctx, frequency="minimum")
    report = assess(original, ctx)
    assert report.diagnostics.goal_progress[0]["satisfied"] is True
    assert report.diagnostics.policy_completion == "complete"


def test_distinct_date_goal_cannot_hide_excess_category_identities():
    original, ctx, _, _ = setup(
        [
            [visit("a", "a"), visit("b", "b", start="12:00", end="13:00")],
            [visit("c", "c", day=1)],
        ],
        reviews=(),
    )
    ctx = category_goal(ctx)
    requirement = ctx.contract.semantic_requirements[0]
    requirement = requirement.model_copy(
        update={
            "experience_goal": requirement.experience_goal.model_copy(
                update={"distinct_dates": True}
            ),
        }
    )
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(update={"semantic_requirements": (requirement,)}),
        }
    )
    report = assess(original, ctx)
    assert report.diagnostics.goal_progress[0]["satisfied"] is False
    assert any(
        i["reason"] == "experience_goal_count_exceeded" for i in report.diagnostics.policy_issues
    )


def test_exact_category_date_shortfall_moves_a_visit_without_adding_an_extra():
    original, ctx, _, policy = setup(
        [
            [
                visit("a", "a"),
                visit("b", "b", start="12:00", end="13:00"),
                visit("d", "d", start="15:00", end="16:00"),
            ],
            [visit("c", "c", day=1)],
        ],
        reviews=(),
    )
    ctx = category_goal(ctx, matched_ids=("a", "b"))
    requirement = ctx.contract.semantic_requirements[0]
    requirement = requirement.model_copy(
        update={
            "experience_goal": requirement.experience_goal.model_copy(
                update={"distinct_dates": True}
            ),
        }
    )
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(update={"semantic_requirements": (requirement,)}),
        }
    )
    report = assess(original, ctx)
    assert report.diagnostics.policy_completion == "incomplete"
    scope = operation_scope(original, report, context=ctx, policy=policy)
    result, _ = run(
        (original, ctx, scope, policy),
        [
            [
                edit("move", "b", day=1, start="12:00", end="13:00"),
            ]
        ],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.adopted_report.diagnostics.goal_progress[0]["matched"] == 2
    assert result.adopted_report.diagnostics.goal_progress[0]["satisfied"] is True


def test_unmet_named_count_remains_incomplete_in_product_after_failed_repair():
    from backend.app.schemas.interpreted_requirements import VisitRequirement
    from backend.app.services.product_presentation import present_product
    from backend.tests.services.test_product_presentation import example

    original, ctx, _, policy = setup(
        [[visit("a", "a"), visit("b", "b", start="12:00", end="13:00")]],
        reviews=(),
        required="REQUIRED",
    )
    named = ctx.contract.named_places[0]
    rule = VisitRequirement(
        requirement_id=named.requirement_id,
        place_text=named.place_text,
        minimum_visits=2,
        exact_visits=2,
        distinct_dates=False,
        dates=(),
        status="executable",
        reason=None,
        source_refs=named.source_refs,
    )
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(update={"visit_requirements": (rule,)}),
            "semantic_assessments": semantic_rows(ctx),
        }
    )
    scope = operation_scope(original, assess(original, ctx), context=ctx, policy=policy)
    repair, _ = run((original, ctx, scope, policy), [RuntimeError("Synthetic patch failure")])
    result, evidence = example()
    result.itinerary = repair.final
    result.requirements = ctx.contract.requirements
    result.generation_diagnostics = repair.adopted_report.diagnostics
    result.interpreted_requirements = ctx.contract
    public = present_product(result, evidence)
    assert public.policy_completion == "incomplete"
    assert "required_visit_obligation_unmet" in public.policy_reasons
    assert public.attention_items[0].title == named.place_text
    assert "not fully arranged" in public.attention_items[0].description


def test_model_transport_endpoint_is_rejected_before_canonical_visit_checks():
    with pytest.raises(ValueError, match="transport activities"):
        setup(
            [
                [
                    visit("a1", "a"),
                    visit("transfer", "a", start="12:00", end="13:00").model_copy(
                        update={"activity_kind": "transport"}
                    ),
                ]
            ],
            reviews=(),
        )


def test_assessed_generic_visit_counts_toward_atomic_deduplication_compensation():
    original, ctx, _, policy = repeated()
    original.days[1].activities[1].activity_kind = "generic_activity"
    ctx = ctx.model_copy(update={"semantic_assessments": semantic_rows(ctx)})
    scope = operation_scope(original, assess(original, ctx), context=ctx, policy=policy)
    result, _ = run(
        (original, ctx, scope, policy),
        [
            [
                edit("delete", "a2", day=1),
                edit("add", pid="d", day=1, start="09:00", end="10:00"),
            ]
        ],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert {a.source_place_id for a in result.final.days[1].activities} == {"c", "d"}


def test_repetition_is_automatic_with_all_reviews_off_same_day():
    original, ctx, _, policy = setup(
        [[visit("a1", "a"), visit("a2", "a", start="12:00", end="13:00")]], reviews=()
    )
    report = assess(original, ctx)
    finding = next(f for f in report.findings if f.check == "repetition")
    assert finding.status == "CONFIRMED"
    scope = operation_scope(original, report, context=ctx, policy=policy)
    assert scope is not None and finding.finding_id in scope.target_ids
    result, _ = run((original, ctx, scope, policy), [[edit("delete", "a2")]])
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert len(result.final.days[0].activities) == 1


def test_pending_deduplication_completed_by_second_round_compensation():
    args = repeated()
    result, model = run(
        args,
        [
            [edit("delete", "a2", day=1)],
            [edit("add", pid="d", day=1, start="09:00", end="10:00")],
        ],
    )
    assert model.calls == 2, result.reason
    assert result.rounds[0].adopted == args[0]
    assert result.rounds[0].result.pending_groups
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert not result.pending_groups
    assert {a.source_place_id for a in result.final.days[1].activities} == {"c", "d"}
    assert len(result.rounds[1].result.parsed_patch.edits) == 1
    assert len(result.rounds[1].result.effective_patch.edits) == 2


def test_pending_group_rollback_does_not_publish_empty_slot():
    args = repeated()
    result, _ = run(args, [[edit("delete", "a2", day=1)], RuntimeError("fixture failure")])
    assert result.final == args[0]
    assert result.pending_groups[0]["status"] == "rolled_back"
    assert result.adopted_report.diagnostics.policy_completion == "incomplete"


def test_primary_role_policy_replacement_uses_real_validator_scope_and_stage():
    from backend.app.schemas.poi_semantics import POISemanticAssessment

    original, ctx, _, policy = setup(
        [[visit("a", "a"), visit("b", "b", start="12:00", end="13:00")]], reviews=()
    )
    rows = tuple(
        POISemanticAssessment(
            place_id=p.place_id,
            visit_object=p.name,
            role="non_main" if p.place_id == "a" else "attraction",
            categories=["fixture"],
            reason="Synthetic semantic assessment",
            evidence_refs=[p.source_ref],
            matches=[],
            exception_requirement_ids=[],
        )
        for p in ctx.places
    )
    ctx = ctx.model_copy(update={"semantic_assessments": rows})
    report = assess(original, ctx)
    scope = operation_scope(original, report, context=ctx, policy=policy)
    assert any(f.check == "primary_policy" and f.status == "CONFIRMED" for f in report.findings)
    result, _ = run(
        (original, ctx, scope, policy),
        [[edit("replace", "a", pid="c", start="09:00", end="10:00")]],
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert not result.adopted_report.diagnostics.policy_issues


def test_pending_failure_preserves_independent_adopted_retime():
    args = setup(
        [
            [visit("a1", "a"), visit("b", "b", start="12:00", end="13:00")],
            [visit("a2", "a", 1), visit("c", "c", 1, "12:00", "13:00")],
            [visit("f", "f", 2), visit("g", "g", 2, "09:30", "10:30")],
        ],
        reviews=(),
    )
    result, _ = run(
        args,
        [
            [edit("delete", "a2", day=1), edit("retime", "g", day=2, start="11:00", end="12:00")],
            RuntimeError("fixture failure"),
        ],
    )
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert result.final.days[1] == args[0].days[1]
    assert result.final.days[2].activities[1].start_time.hour == 11
    assert result.pending_groups[0]["status"] == "rolled_back"


def test_graph_semantic_failure_stops_primary_and_nearby():
    import asyncio

    from backend.tests.versions.v3.test_wiring import Model, OwnedRetrieval, Places, execute

    class Broken(Model):
        async def generate_poi_semantics_structured(self, **kwargs):
            raise RuntimeError("fixture semantic provider failure")

    model, places, resource = Broken(), Places(), OwnedRetrieval()
    with pytest.raises(RuntimeError):
        asyncio.run(execute(model, places=places, runtime=resource))
    assert not model.calls and not model.repair_calls and not places.nearby
    assert resource.closes == 1


@pytest.mark.parametrize("exact", [None, 2])
def test_minimum_revisit_does_not_invent_upper_bound(exact):
    from backend.app.policies.visit_multiplicity import excess_visits
    from backend.app.schemas.interpreted_requirements import VisitRequirement

    _, ctx, _, _ = repeated("REQUIRED")
    named = ctx.contract.named_places[0]
    rule = VisitRequirement(
        requirement_id=named.requirement_id,
        place_text=named.place_text,
        minimum_visits=2,
        exact_visits=exact,
        distinct_dates=True,
        dates=(),
        status="executable",
        reason=None,
        source_refs=named.source_refs,
    )
    contract = ctx.contract.model_copy(update={"visit_requirements": (rule,)})
    items = [visit(str(i), "a", day=i) for i in range(3)]
    assert excess_visits(items, contract, ctx.named_resolutions, "a") == (1 if exact else 0)


def test_required_named_model_transport_is_rejected_before_requirement_checks():
    original, ctx, _, _ = repeated("REQUIRED")
    ctx = ctx.model_copy(
        update={
            "contract": ctx.contract.model_copy(update={"visit_requirements": ()}),
            "semantic_assessments": semantic_rows(ctx),
        }
    )
    for day in original.days:
        for activity in day.activities:
            if activity.source_place_id == "a":
                activity.activity_kind = "transport"
    with pytest.raises(ValueError, match="transport activities"):
        assess(original, ctx)
