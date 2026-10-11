"""Extension registration seam; unfinished tracks remain explicitly pending."""

TRACKS = ("resources", "mechanism", "pair", "human", "controlled_repair")


def prepare_tracks(declaration, cases, *, source_root):
    """Adapters return immutable configuration; reject unsupported supplied material."""
    supplied = [declaration, *(case for case, *_ in cases)]
    if any("tracks" in value and not isinstance(value["tracks"], dict) for value in supplied):
        raise ValueError("Extension track configuration must be an object")
    if declaration.get("tracks") or any(
        set(case.get("tracks", {})) - {"resources", "mechanism", "pair"} for case, *_ in cases
    ):
        raise ValueError("Supplied extension track material is not supported yet")
    from .suite_pair import prepare_pairs
    from .suite_resources import prepare_resources

    resources = prepare_resources(cases, source_root=source_root)
    pairs = prepare_pairs(cases, source_root=source_root)
    return {
        **resources,
        **pairs,
        "artifacts": {**resources["artifacts"], **pairs["artifacts"]},
        "source_bindings": {**resources["source_bindings"], **pairs["source_bindings"]},
    }


def compose_tracks(preparation, directory, cases):
    """Return case rows and separate suite-wide study tracks without changing scores."""
    from .suite_pair import compose_pairs
    from .suite_resources import compose_resources

    cases = compose_resources(preparation, directory, cases)
    for case in cases:
        for name in ("human", "controlled_repair"):
            case["tracks"][name] = {
                "processing_status": "pending",
                "evidence_status": "unavailable",
                "applicability": "pending",
                "reason": "extension_pending",
            }
    compose_pairs(preparation, directory, cases)
    return cases, {}
