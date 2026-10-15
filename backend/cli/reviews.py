"""Offline post-generation review queues for native manifests and producer staging."""

from pathlib import Path

from .collection import _json, _require, read_staging


def preflight(source):
    """Return coverage; no reviewer, provider, quality scorer or Planner is invoked."""
    from backend.evaluation.intake import _artifact, _read, _reviews, load_batch
    from backend.evaluation.projection import project
    from backend.evaluation.records import MaterialError
    from backend.evaluation.review_artifacts import review_inputs
    from backend.evaluation.semantic_readiness import review_readiness

    source = Path(source).resolve()
    declaration = _json(source.read_bytes())
    if declaration.get("schema_version") == "rtpeval_staging_1":
        declaration = read_staging(source)
        roles = _reviews(source.parent, declaration, {})
        inventory = []
        for group in declaration["groups"]:
            original, input_hash = _artifact(source.parent, group["input_ref"])
            runs = {}
            for version, run in group["selected_runs"].items():
                _require(
                    run.get("result_ref"), "Post-generation preflight requires selected results"
                )
                result, result_hash = _artifact(source.parent, run["result_ref"])
                context = {
                    "batch_id": declaration["batch_id"],
                    "group_id": group["group_id"],
                    "run_id": run["run_id"],
                    "artifact_sha256": result_hash,
                }
                relevant = [
                    r
                    for r in roles
                    if all(r[k] == context[k] for k in ("group_id", "run_id", "artifact_sha256"))
                ]
                runs[version] = {
                    "final": project(
                        result["itinerary"],
                        context,
                        reviews=[r for r in relevant if r["pointer"].startswith("/itinerary/")],
                        version=version,
                    ),
                    "optional": {},
                }
                for key in ("draft", "final_primary") if version == "v3" else ():
                    prefix = "/v3/" + key
                    extension = result.get("v3")
                    try:
                        runs[version]["optional"][key] = project(
                            extension.get(key) if isinstance(extension, dict) else None,
                            context,
                            prefix,
                            [r for r in relevant if r["pointer"].startswith(prefix + "/")],
                            version=version,
                        )
                    except (MaterialError, TypeError, KeyError, ValueError):
                        runs[version]["optional"][key] = None
            inventory.append(
                {
                    "group_id": group["group_id"],
                    "input": original,
                    "input_sha256": input_hash,
                    "requirement_spec": {"obligations": []},
                    "runs": runs,
                }
            )
        intake = {
            "batch_id": declaration["batch_id"],
            "revision": declaration["revision"],
            "inventory": inventory,
            "source_hashes": {"staging": _read(source)[1]},
        }
    else:
        intake = load_batch(source).to_dict()
        _require(intake["status"] == "accepted", "Native intake rejected preflight: " + str(intake))
    occupancy = review_inputs(source, declaration, intake)
    result = review_readiness(intake, occupancy)
    result["inputs"] = [
        {"group_id": g["group_id"], "input_sha256": g["input_sha256"], "original": g["input"]}
        for g in intake["inventory"]
    ]
    return result
