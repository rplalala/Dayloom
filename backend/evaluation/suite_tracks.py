"""Extension registration seam; unfinished tracks remain explicitly pending."""

TRACKS = ("resources", "mechanism", "pair", "human", "controlled_repair")


def prepare_tracks(declaration, cases, *, source_root):
    """Adapters return immutable configuration; reject unsupported supplied material."""
    supplied = [declaration, *(case for case, *_ in cases)]
    if any("tracks" in value and not isinstance(value["tracks"], dict) for value in supplied):
        raise ValueError("Extension track configuration must be an object")
    if declaration.get("tracks") or any(
        set(case.get("tracks", {})) - {"resources", "mechanism"} for case, *_ in cases
    ):
        raise ValueError("Supplied extension track material is not supported yet")
    from .suite_resources import prepare_resources

    return prepare_resources(cases, source_root=source_root)


def compose_tracks(preparation, directory, cases):
    """Return case rows and separate suite-wide study tracks without changing scores."""
    from .suite_resources import compose_resources

    cases = compose_resources(preparation, directory, cases)
    for case in cases:
        for name in ("pair", "human", "controlled_repair"):
            case["tracks"][name] = {
                "processing_status": "pending",
                "evidence_status": "unavailable",
                "applicability": "pending",
                "reason": "extension_pending",
            }
    return cases, {}
