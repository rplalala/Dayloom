"""Offline coverage of independent activity reviews, separate from score decidability."""

from ._schedule_preparation import _occupancy_reviews
from .occupancy import prepare_occupancy
from .projection import classify
from .records import canonical_digest


class MissingSemanticReviews(ValueError):
    """Required independent work is absent; completed UNKNOWN is not this error."""

    def __init__(self, report):
        super().__init__("missing_semantic_reviews: run rtpeval batch preflight for exact sources")
        self.report = report


def review_readiness(intake, occupancy_reviews=None):
    """Inspect selected finals using native projection/occupancy rules, without scoring."""
    decisions = {r["source"]["record_id"]: r for r in _occupancy_reviews(intake, occupancy_reviews)}
    rows = []
    for group in intake["inventory"]:
        for version, run in group["runs"].items():
            projection = run["final"]
            pending = {
                ref["record_id"]
                for c in prepare_occupancy(
                    projection, group["requirement_spec"]["obligations"], reviews=decisions.values()
                ).to_dict()["candidates"]
                if c["reason"] == "occupancy_unresolved"
                for ref in c["sources"]
            }
            for activity in projection["activities"]:
                source = activity["source"]
                role = activity["evaluation_role"]
                review = activity.get("review") or {}
                role_status = (
                    ("reviewed_unresolved" if "role" in review else "missing")
                    if role == "unresolved"
                    else ("reviewed" if "role" in review else "not_required")
                )
                decision = decisions.get(source["record_id"])
                if role == "unresolved":
                    occupancy_status = (
                        "awaiting_role" if role_status == "missing" else "unresolved_role"
                    )
                elif decision:
                    occupancy_status = (
                        "reviewed_unresolved"
                        if decision["occupancy"] == "unresolved"
                        else "reviewed"
                    )
                elif source["record_id"] in pending or (
                    role == "transition" and classify(activity["original"], None)[0] == "unresolved"
                ):
                    occupancy_status = "missing"
                else:
                    occupancy_status = "not_required"
                missing = []
                if role_status == "missing":
                    missing.append("missing_role_review")
                if occupancy_status == "missing":
                    missing.append("missing_occupancy_review")
                rows.append(
                    {
                        "version": version,
                        "input_sha256": group["input_sha256"],
                        "source": source,
                        "original": activity["original"],
                        "declared_day": activity["declared_day"],
                        "evaluation_role": role,
                        "role_basis": activity["reason"],
                        "role_review": role_status,
                        "occupancy_review": occupancy_status,
                        "missing": missing,
                    }
                )
    missing = [r for r in rows if r["missing"]]
    unresolved = [
        r
        for r in rows
        if r["role_review"] == "reviewed_unresolved"
        or r["occupancy_review"] == "reviewed_unresolved"
    ]
    return {
        "schema_version": "rtpeval_semantic_readiness_1",
        "scope": "selected_final_activities",
        "batch_id": intake["batch_id"],
        "revision": intake["revision"],
        "status": "needs_semantic_review" if missing else "ready",
        "source_hashes": intake.get("source_hashes", {}),
        "occupancy_reviews_content_sha256": canonical_digest(occupancy_reviews)
        if occupancy_reviews
        else None,
        "missing_role_count": sum(r["role_review"] == "missing" for r in rows),
        "missing_occupancy_count": sum(r["occupancy_review"] == "missing" for r in rows),
        "awaiting_role_count": sum(r["occupancy_review"] == "awaiting_role" for r in rows),
        "reviewed_unresolved_count": len(unresolved),
        "queue": missing,
        "reviewed_unresolved": unresolved,
        "activities": rows,
        "score_decidability": "not_assessed",
        "provider_calls": 0,
    }
