"""Read explicit Repair search selection without inventing historical observations."""

from .records import require


def selected_prefix(repair, rows=None):
    """Return selected prefix length for version 1, or None for historical records."""
    version = repair.get("search_version")
    if version is None:
        return None
    require(type(version) is int and version == 1, "repair_search", "Unsupported search version")
    rows = repair.get("rounds", []) if rows is None else rows
    promotions = []
    for index, row in enumerate(rows, 1):
        require(
            type(row["round_index"]) is int and row["round_index"] == index,
            "repair_search",
            "Broken search round order",
        )
        transition, promotion = row.get("exploration_transition"), row.get("best_promoted")
        require(
            type(transition) is bool and type(promotion) is bool,
            "repair_search",
            "Missing search transition observations",
        )
        require(
            row.get("strategy") in {"system_delete", "local", "replan"},
            "repair_search",
            "Unknown search strategy",
        )
        require(
            transition == row["result"]["status"].startswith("ACCEPTED_")
            and (not promotion or transition),
            "repair_search",
            "Inconsistent search transition/promotion",
        )
        if promotion:
            promotions.append(index)
    selected = repair.get("selected_round_index")
    require(
        selected is None or type(selected) is int, "repair_search", "Invalid selected round index"
    )
    require(
        selected == (promotions[-1] if promotions else None),
        "repair_search",
        "Selection must identify the last retained promotion",
    )
    return selected or 0
