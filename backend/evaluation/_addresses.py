"""Typed independent address comparisons with strict legacy fallback."""

import re
from collections import deque

from ._claims import normalized
from .records import text


def compare_address_claim(value, candidate):
    """Binary whole-address equivalence using only this observation's alias pairs."""
    provider = candidate["formatted_address"]
    result = {
        "schema_version": "rtpeval_address_comparison_1",
        "original": value,
        "provider_address": provider,
        "verdict": "FAIL",
        "basis": "unexplained_address_difference",
        "aliases": [],
    }
    if value == provider:
        return {**result, "verdict": "PASS", "basis": "exact"}
    if normalized(value) == normalized(provider):
        return {**result, "verdict": "PASS", "basis": "normalized_format"}

    def tokens(s):
        return tuple(re.findall(r"\w+|[^\w\s]", normalized(s) or ""))

    left, right = tokens(value), tokens(provider)
    pairs = []
    raw = candidate.get("address_components")
    for component in raw if isinstance(raw, list) else []:
        if not isinstance(component, dict):
            continue
        long, short = component.get("longText"), component.get("shortText")
        if not text(long) or not text(short) or normalized(long) == normalized(short):
            continue
        # An alias cannot excuse changed house/unit/postal numbers.
        if re.findall(r"\d+", long) != re.findall(r"\d+", short):
            continue
        pairs.append((tokens(long), tokens(short), {"longText": long, "shortText": short}))
    destinations = {}
    for long, short, _ in pairs:
        destinations.setdefault(short, set()).add(long)
        destinations.setdefault(long, set()).add(short)
    if any(len(values) > 1 for values in destinations.values()):
        return {**result, "basis": "conflicting_component_aliases"}
    pending = deque([(0, 0, [])])
    visited = set()
    while pending:
        i, j, used = pending.popleft()
        if (i, j) in visited:
            continue
        visited.add((i, j))
        if i == len(left) and j == len(right):
            return {
                **result,
                "verdict": "PASS",
                "basis": "google_component_aliases" if used else "normalized_format",
                "aliases": used,
            }
        if i < len(left) and j < len(right) and left[i] == right[j]:
            pending.append((i + 1, j + 1, used))
        for a, b, proof in pairs:
            for first, second in ((a, b), (b, a)):
                if left[i : i + len(first)] == first and right[j : j + len(second)] == second:
                    pending.append((i + len(first), j + len(second), [*used, proof]))
    return result


def components(candidate, *, literal=False, hierarchical=False):
    raw = candidate.get("address_components")
    if "address_components" not in candidate:
        return {}
    if not isinstance(raw, list):
        raise ValueError("Address components must be an array")
    result = {}
    for item in raw:
        if not isinstance(item, dict) or not text(item.get("longText")):
            raise ValueError("Address component requires longText")
        kinds = item.get("types")
        if not isinstance(kinds, list) or not kinds or not all(text(k) for k in kinds):
            raise ValueError("Address component requires types")
        values = {item["longText"] if literal else normalized(item["longText"])}
        if "shortText" in item:
            if not text(item["shortText"]):
                raise ValueError("Invalid shortText")
            values.add(item["shortText"] if literal else normalized(item["shortText"]))
        for kind in kinds:
            if kind == "political" or (
                hierarchical
                and kind == "sublocality"
                and any(k.startswith("sublocality_level_") for k in kinds)
            ):
                continue
            if kind in result and result[kind] != values:
                raise ValueError("Conflicting address components")
            result[kind] = values
    return result


def legacy_match(value, candidate):
    target = normalized(value)
    return target is not None and target in {
        normalized(piece) for piece in re.split(r"[,;]", candidate["formatted_address"])
    }


def destination_matches(value, candidate):
    typed = components(candidate)
    if "locality" not in typed:
        return legacy_match(value, candidate)
    parts = [normalized(p) for p in re.split(r"[,;]", value)]
    qualifiers = set().union(
        *(
            typed.get(k, set())
            for k in ("country", "administrative_area_level_1", "administrative_area_level_2")
        )
    )
    return parts[0] in typed["locality"] and all(p in qualifiers for p in parts[1:])


def strict_destination_matches(value, candidate, *, postal_town=False):
    """Verify every literal destination token without legacy semantic normalization."""
    parts = [piece.strip() for piece in re.split(r"[,;]", value)]
    if not parts or any(not part for part in parts):
        return False
    typed = components(candidate, literal=True, hierarchical=True)
    if typed:
        if postal_town and "postal_town" in typed:
            cities = typed["postal_town"]
            locality = typed.get("locality", set())
            if locality and not cities & locality:
                return False
            destinations = cities | locality
        else:
            destinations = set().union(
                *(
                    typed.get(kind, set())
                    for kind in (
                        "locality",
                        "administrative_area_level_1",
                        "administrative_area_level_2",
                    )
                )
            )
        qualifiers = set().union(
            *(
                typed.get(kind, set())
                for kind in (
                    "country",
                    "administrative_area_level_1",
                    "administrative_area_level_2",
                )
            )
        )
        return parts[0] in destinations and all(part in qualifiers for part in parts[1:])
    address = {piece.strip() for piece in re.split(r"[,;]", candidate["formatted_address"])}
    return all(part in address for part in parts)


def street_forms(typed):
    return {
        f"{number} {route}"
        for number in typed.get("street_number", ())
        for route in typed.get("route", ())
    }


def location_matches(value, candidate, *, postal_town=False):
    typed = components(candidate)
    target = normalized(value)
    if numbered_street(value) and street_forms(typed):
        return target in street_forms(typed)
    if target in street_forms(typed) or any(target in values for values in typed.values()):
        return True
    if "locality" in typed or postal_town and "postal_town" in typed:
        # Typed city evidence cannot be overridden by an untyped address token.
        return False
    return legacy_match(value, candidate)


def numbered_street(value):
    return bool(
        re.fullmatch(
            r"\d+[a-z]?(?:[-/]\d+[a-z]?)?\s+.+\s+"
            r"(?:street|st|road|rd|avenue|ave|lane|ln|drive|dr|boulevard|blvd|way|court|ct)\.?",
            normalized(value) or "",
        )
    )


def addresses_agree(left, right):
    a, b = components(left), components(right)
    if any(not a[k] & b[k] for k in a.keys() & b.keys()):
        return False
    if normalized(left["formatted_address"]) == normalized(right["formatted_address"]):
        return True
    required = {"street_number", "route", "locality", "country"}
    return required <= a.keys() and a.keys() == b.keys() and all(a[k] & b[k] for k in a)
