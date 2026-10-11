"""Extension registration seam; unfinished tracks remain explicitly pending."""

TRACKS = ("resources", "mechanism", "pair", "human", "controlled_repair")


def prepare_tracks(declaration, cases, *, source_root):
    """Adapters return immutable configuration; reject unsupported supplied material."""
    supplied = [declaration, *(case for case, *_ in cases)]
    if any("tracks" in value and not isinstance(value["tracks"], dict) for value in supplied):
        raise ValueError("Extension track configuration must be an object")
    if set(declaration.get("tracks", {})) - {"human", "controlled_repair"} or any(
        case.get("tracks") for case, *_ in cases
    ):
        raise ValueError("Supplied extension track material is not supported yet")
    from .suite_external import prepare_external

    return prepare_external(declaration.get("tracks", {}), cases, source_root=source_root)


def compose_tracks(preparation, directory, cases):
    """Return case rows and separate suite-wide study tracks without changing scores."""
    for case in cases:
        for name in TRACKS:
            case["tracks"][name] = {
                "processing_status": "pending",
                "evidence_status": "unavailable",
                "applicability": "pending",
                "reason": "extension_pending",
            }
    for case in cases:
        for name in ("human", "controlled_repair"):
            case["tracks"][name] = {
                "processing_status": "complete",
                "evidence_status": "unavailable",
                "applicability": "not_applicable",
                "reason": "suite_wide_study",
            }
    from .suite_external import compose_external

    return cases, compose_external(preparation["track_configuration"])
