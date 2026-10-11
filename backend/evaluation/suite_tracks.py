"""Extension registration seam; unfinished tracks remain explicitly pending."""

TRACKS = ("resources", "mechanism", "pair", "human", "controlled_repair")


def prepare_tracks(declaration, cases, *, source_root):
    """Adapters return immutable configuration; reject unsupported supplied material."""
    supplied = [declaration, *(case for case, *_ in cases)]
    if any("tracks" in value and not isinstance(value["tracks"], dict) for value in supplied):
        raise ValueError("Extension track configuration must be an object")
    if declaration.get("tracks") or any(case.get("tracks") for case, *_ in cases):
        raise ValueError("Supplied extension track material is not supported yet")
    return {"artifacts": {}, "source_bindings": {}}


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
    return cases, {}
