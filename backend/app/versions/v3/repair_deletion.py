"""Finite application proposals, never an independent deletion authorization."""

from backend.app.policies.visit_multiplicity import is_primary_visit
from backend.app.versions.v3.repair_models import RepairEdit, RepairPatch
from backend.app.versions.v3.repair_search import state_key
from backend.app.versions.v3.repair_targets import dispensable_visit


def next_deletion(itinerary, context, scope, budget):
    """Attempt each authorized visit once per exploration state under a stage ceiling."""
    if budget.used["deterministic_attempts"] >= budget.policy.max_deletion_attempts:
        return None
    allowed = {p.activity_id for p in scope.permissions if "delete" in p.operations}
    tried = getattr(budget, "deletion_attempts", set())
    base = state_key(itinerary, context.schedule)
    for day in itinerary.days:
        for activity in day.activities:
            key = (base, activity.activity_id)
            if (
                activity.activity_id not in allowed
                or key in tried
                or not is_primary_visit(activity, context.semantic_assessments)
                or not dispensable_visit(itinerary, activity.activity_id, context)
            ):
                continue
            budget.deletion_attempts = tried | {key}
            return RepairPatch(
                edits=(
                    RepairEdit(
                        operation="delete",
                        activity_id=activity.activity_id,
                        date=day.date,
                        place_id=None,
                        start_time=None,
                        end_time=None,
                    ),
                )
            )
    return None
