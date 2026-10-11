"""Register native case tracks and separately operated suite-wide studies."""

TRACKS = ("resources", "mechanism", "pair", "human", "controlled_repair")


def prepare_tracks(declaration, cases, *, source_root):
    """Adapters return immutable configuration; reject unsupported supplied material."""
    supplied = [declaration, *(case for case, *_ in cases)]
    if any("tracks" in value and not isinstance(value["tracks"], dict) for value in supplied):
        raise ValueError("Extension track configuration must be an object")
    if set(declaration.get("tracks", {})) - {"human", "controlled_repair"} or any(
        set(case.get("tracks", {})) - {"resources", "mechanism"} for case, *_ in cases
    ):
        raise ValueError("Unsupported suite or case track configuration")
    from .suite_external import prepare_external
    from .suite_resources import prepare_resources

    configuration = prepare_resources(cases, source_root=source_root)
    external = prepare_external(declaration.get("tracks", {}), cases, source_root=source_root)
    for key, value in external.items():
        if key in {"artifacts", "source_bindings"}:
            configuration[key].update(value)
        else:
            configuration[key] = value
    return configuration


def compose_tracks(preparation, directory, cases):
    """Return case rows and separate suite-wide study tracks without changing scores."""
    from .suite_external import compose_external
    from .suite_resources import compose_resources

    cases = compose_resources(preparation, directory, cases)
    for case in cases:
        case["tracks"]["pair"] = {
            "processing_status": "pending",
            "evidence_status": "unavailable",
            "applicability": "pending",
            "reason": "extension_pending",
        }
        for name in ("human", "controlled_repair"):
            case["tracks"][name] = {
                "processing_status": "complete",
                "evidence_status": "unavailable",
                "applicability": "not_applicable",
                "reason": "suite_wide_study",
            }
    return cases, compose_external(preparation["track_configuration"])
