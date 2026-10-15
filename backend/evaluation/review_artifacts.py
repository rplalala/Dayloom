"""Validate existing review envelopes at fresh workflow boundaries, without adoption."""

from pathlib import Path

from .intake import _artifact, _reviews
from .preparation import _review_provenance
from .records import require


def review_inputs(manifest_path, declaration, intake, supplied_occupancy=None):
    """Resolve bound reviews and reject conflicting explicit/manifest decisions."""
    root = Path(manifest_path).resolve().parent
    records = _reviews(root, declaration, {})
    sources = {}
    for group in intake["inventory"]:
        for version, run in group["runs"].items():
            for projection in [run["final"], *run.get("optional", {}).values()]:
                if projection:
                    for activity in projection["activities"]:
                        ref = activity["source"]
                        key = tuple(
                            ref[k] for k in ("group_id", "run_id", "artifact_sha256", "pointer")
                        )
                        sources[key] = version
    for record in records:
        key = tuple(record[k] for k in ("group_id", "run_id", "artifact_sha256", "pointer"))
        require(key in sources, "projection_reviews", "Stale/unlinked review activity")
        require(
            "version" not in record or record["version"] == sources[key],
            "projection_reviews",
            "Review version mismatch",
        )
        _review_provenance(record, "projection_reviews")
    bound = None
    if "occupancy_reviews_ref" in declaration:
        bound, _ = _artifact(
            root, declaration["occupancy_reviews_ref"], "rtpeval_occupancy_reviews_1"
        )
    require(
        bound is None or supplied_occupancy is None or bound == supplied_occupancy,
        "occupancy_reviews",
        "Conflicting supplied and manifest occupancy reviews",
    )
    return bound if bound is not None else supplied_occupancy
