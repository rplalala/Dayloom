"""Comparable priorities for bounded Repair exploration and final retention."""

from typing import NamedTuple

from backend.app.versions.v3.repair_acceptance import severity
from backend.app.versions.v3.repair_feedback import digest


class RepairObjective(NamedTuple):
    hard_severity: float
    coverage_deficit: int
    review_magnitude: float
    pace_deduction: float | None

    @property
    def priorities(self) -> tuple[float, int, float]:
        return self.hard_severity, self.coverage_deficit, self.review_magnitude


def state_key(itinerary, schedule=None):
    return digest(
        {
            "days": [
                {
                    "date": str(d.date),
                    "activities": [
                        {
                            k: v
                            for k, v in a.model_dump(mode="json").items()
                            if k not in {"notes", "title", "place_name", "location"}
                        }
                        for a in d.activities
                    ],
                }
                for d in itinerary.days
            ],
            "schedule": schedule.model_dump(mode="json") if schedule else None,
        }
    )


def objective(itinerary, report, pace_dates, scope):
    """Hard findings and minimum coverage precede a fixed-date aggregate pace score."""
    hard = sum(
        severity(f, itinerary) if severity(f, itinerary) is not None else 1
        for f in report.findings
        if f.status == "CONFIRMED" and f.reason != "minimum_daily_coverage_missing"
    )
    coverage = sum(
        max(0, int(f.magnitude or 0) - row.distinct_main_poi_count)
        for f in report.findings
        if f.reason == "minimum_daily_coverage_missing"
        for row in report.diagnostics.days
        if row.date in f.dates
    )
    rows = {f.dates[0]: f.magnitude for f in report.findings if f.check == "soft_pace"}
    pace = (
        sum(rows[d] for d in pace_dates)
        if pace_dates and all(rows.get(d) is not None for d in pace_dates)
        else None
    )
    review = sum(
        (
            max(
                0,
                scope.daily_main_min - row.distinct_main_poi_count,
                row.distinct_main_poi_count - scope.daily_main_max,
            )
            if f.check in {"coverage", "overfull"}
            else f.magnitude or 1
        )
        for f in report.findings
        if f.status == "NEEDS_REVIEW" and f.check != "soft_pace"
        for row in (next((r for r in report.diagnostics.days if r.date in f.dates), None),)
    )
    return RepairObjective(hard, coverage, review, pace)


def improves(candidate: RepairObjective, best: RepairObjective):
    if candidate.priorities != best.priorities:
        return candidate.priorities < best.priorities
    return (
        candidate.pace_deduction is not None
        and best.pace_deduction is not None
        and candidate.pace_deduction < best.pace_deduction
    )


def proposal_key(patch, itinerary, context, scope, evidence):
    """Explanations are not operations; permissions and directed evidence are dependencies."""
    return digest(
        {
            "base": state_key(itinerary, context.schedule),
            "edits": [e.model_dump(mode="json") for e in patch.edits],
            "scope": scope.model_dump(mode="json"),
            "evidence": [r.model_dump(mode="json") for r in (*context.route_evidence, *evidence)],
            "places": [p.model_dump(mode="json") for p in context.places],
            "effective_places": [p.model_dump(mode="json") for p in context.effective_places],
            "semantics": [p.model_dump(mode="json") for p in context.semantic_assessments],
        }
    )
