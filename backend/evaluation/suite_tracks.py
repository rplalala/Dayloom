"""Register native case tracks and separately operated suite-wide studies."""

import base64

from .snapshot import _bytes

TRACKS = ("resources", "mechanism", "pair", "human", "controlled_repair")


def prepare_tracks(declaration, cases, *, source_root):
    """Adapters return immutable configuration; reject unsupported supplied material."""
    supplied = [declaration, *(selection.declaration for selection in cases)]
    if any("tracks" in value and not isinstance(value["tracks"], dict) for value in supplied):
        raise ValueError("Extension track configuration must be an object")
    if set(declaration.get("tracks", {})) - {"human", "controlled_repair"} or any(
        set(selection.declaration.get("tracks", {})) - {"resources", "mechanism", "pair"}
        for selection in cases
    ):
        raise ValueError("Unsupported suite or case track configuration")
    from .suite_external import prepare_external
    from .suite_pair import prepare_pairs
    from .suite_resources import prepare_resources

    configuration = prepare_resources(cases, source_root=source_root)
    pairs = prepare_pairs(cases, source_root=source_root)
    external = prepare_external(declaration.get("tracks", {}), cases, source_root=source_root)
    for additional in (pairs, external):
        for key, value in additional.items():
            if key in {"artifacts", "source_bindings", "raw_artifacts"}:
                configuration.setdefault(key, {}).update(value)
            else:
                configuration[key] = value
    return configuration


def _invalid_artifacts(preparation, directory):
    expected = {
        name: _bytes(value)
        for name, value in preparation["track_configuration"].get("artifacts", {}).items()
    }
    expected.update(
        {
            name: base64.b64decode(raw, validate=True)
            for name, raw in preparation["track_configuration"].get("raw_artifacts", {}).items()
        }
    )
    invalid = set()
    for name, raw in expected.items():
        try:
            if (directory / name).read_bytes() != raw:
                invalid.add(name)
        except OSError:
            invalid.add(name)
    return invalid


def compose_tracks(preparation, directory, cases, *, allow_material_correction=False):
    """Return case rows and separate suite-wide study tracks without changing scores."""
    from .suite_external import compose_external
    from .suite_pair import compose_pairs
    from .suite_resources import compose_resources

    invalid = _invalid_artifacts(preparation, directory) if allow_material_correction else set()
    cases = compose_resources(preparation, directory, cases, invalid_artifacts=invalid)
    compose_pairs(preparation, directory, cases, invalid_artifacts=invalid)
    for case in cases:
        for name in ("human", "controlled_repair"):
            case["tracks"][name] = {
                "processing_status": "complete",
                "evidence_status": "unavailable",
                "applicability": "not_applicable",
                "reason": "suite_wide_study",
            }
    external = compose_external(preparation["track_configuration"])
    for kind, track in external.items():
        # Keep the prepared configuration immutable while marking only affected studies.
        track["studies"] = [dict(study) for study in track["studies"]]
        changed = []
        for index, study in enumerate(track["studies"], 1):
            prefix = f"tracks/{kind}/{index:04d}/"
            artifacts = sorted(name for name in invalid if name.startswith(prefix))
            if artifacts:
                study.update(
                    processing_status="needs_material_correction",
                    evidence_status="unavailable",
                    report=None,
                    reason="prepared_track_artifact_changed",
                    invalid_artifacts=artifacts,
                )
                changed.extend(artifacts)
        if changed:
            track.update(
                processing_status="needs_material_correction",
                invalid_artifacts=changed,
                reason="prepared_track_artifact_changed",
                evidence_status="partial"
                if any(study["evidence_status"] != "unavailable" for study in track["studies"])
                else "unavailable",
            )
    return cases, external
