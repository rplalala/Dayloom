"""Source-preserving schedule projection, independent of planner judgments."""

from datetime import date, datetime

from backend.activity_semantics import read_activity_claim

from ._claims import (
    claim_evidence,
    movement_claim,
    normalized,
    transport_endpoints,
)
from .records import require, source, text

ACTIVITY_FIELDS = (
    "activity_id",
    "activity_kind",
    "time_use",
    "title",
    "place_name",
    "source_place_id",
    "location",
    "start_time",
    "end_time",
    "estimated_cost",
    "notes",
    "transport",
)
TRANSFER_FIELDS = (
    "from_activity_id",
    "to_activity_id",
    "origin_place_id",
    "destination_place_id",
    "mode",
    "departure_time",
    "arrival_time",
    "provider_duration_seconds",
    "distance_meters",
    "reserve_seconds",
)
MODES = ("WALK", "TRANSIT", "DRIVE")
MODE_TITLES = {
    "walk": "WALK",
    "walking": "WALK",
    "on foot": "WALK",
    "public transit": "TRANSIT",
    "public transport": "TRANSIT",
    "bus": "TRANSIT",
    "train": "TRANSIT",
    "metro": "TRANSIT",
    "subway": "TRANSIT",
    "tram": "TRANSIT",
    "drive": "DRIVE",
    "driving": "DRIVE",
    "by car": "DRIVE",
}
PLACEHOLDERS = {"free time", "break", "rest", "relax", "explore", "explore the area"}


def clock(value):
    try:
        return (
            datetime.fromisoformat(value)
            if isinstance(value, str) and ("T" in value or " " in value)
            else None
        )
    except ValueError:
        return None


def interval(start, end):
    a, b = clock(start), clock(end)
    try:
        return (a, b) if a is not None and b is not None and a < b else None
    except TypeError:
        return None


def mode_claim(raw, review):
    """Prefer reviewed mode, then structured declaration, then legacy title."""
    if review and "mode" in review:
        return review["mode"]
    if raw.get("transport") is not None:
        declaration = raw["transport"]
        mode = declaration.get("mode") if isinstance(declaration, dict) else None
        return mode if mode in MODES else None
    declared = []
    for clause in (normalized(raw.get("title")) or "").split(";"):
        title = clause.strip().removesuffix(".")
        mode = MODE_TITLES.get(title)
        if mode is None and movement_claim(title):
            mode = MODE_TITLES.get(title.split(" from ", 1)[0].split(" to ", 1)[0])
        declared.append(mode)
    return declared[0] if all(mode in (None, declared[0]) for mode in declared) else None


def classify(raw, review, wire="itinerary_2"):
    if review and "role" in review:
        return review["role"], "independently_reviewed", "reviewed_role"
    if wire == "itinerary_3":
        claim = read_activity_claim(raw, wire)
        role = {"main_poi": "primary_visit", "transport": "transport"}.get(claim.kind, "transition")
        return role, "declared_consistent", "declared_itinerary_3"
    role = raw.get("activity_kind", "unknown")
    place = text(raw.get("place_name")) or text(raw.get("source_place_id"))
    title = raw["title"].strip().casefold()
    if role == "transport" and not place:
        return "transport", "declared_consistent", "declared_transport"
    if role == "main_poi":
        return "primary_visit", "declared_consistent", "declared_visit"
    if role == "free_time":
        return "transition", "declared_consistent", "declared_free_time"
    if place and role not in ("transport", "free_time"):
        return "primary_visit", "declared_consistent", "named_visit"
    if not place and title in PLACEHOLDERS and role != "transport":
        return "transition", "declared_consistent", "generic_placeholder"
    return "unresolved", "unresolved", "role_review_required"


def project(itinerary, context, prefix="/itinerary", reviews=(), *, version):
    """Return inventory and uncertainties; never compute metric verdicts."""
    require(isinstance(itinerary, dict), prefix, "Expected an itinerary object")
    require(version in ("v0", "v1", "v2", "v3"), prefix, "Unknown planner version")
    wire = itinerary.get("output_version", "itinerary_1")
    require(
        wire in ("itinerary_1", "itinerary_2", "itinerary_3"),
        prefix,
        "Unknown itinerary version",
        "unsupported_wire_version",
    )
    days = itinerary.get("days")
    require(isinstance(days, list), prefix, "days must be an array")
    review_map = {r["pointer"]: r for r in reviews}
    consumed = set()
    records, legs, claims, diagnostics = [], [], [], []
    ignored_transport = []
    ids, dates = set(), set()

    def report(reason, refs, explanation):
        diagnostics.append({"reason": reason, "sources": refs, "explanation": explanation})

    for di, day in enumerate(days):
        dp = f"{prefix}/days/{di}"
        require(isinstance(day, dict), dp, "Expected a day object")
        try:
            day_date = date.fromisoformat(day.get("date", ""))
        except (ValueError, TypeError):
            require(False, dp, "Missing or invalid declared day date")
        require(day_date not in dates, dp, "Duplicate declared day date", "duplicate_source_id")
        dates.add(day_date)
        activities = day.get("activities")
        require(isinstance(activities, list), dp, "activities must be an array")
        day_records = []
        for ai, raw in enumerate(activities):
            ap = f"{dp}/activities/{ai}"
            require(isinstance(raw, dict), ap, "Expected an activity object")
            require(
                text(raw.get("activity_id")) and text(raw.get("title")),
                ap,
                "Activity ID and title must be nonempty strings",
            )
            require(
                raw["activity_id"] not in ids, ap, "Duplicate activity ID", "duplicate_source_id"
            )
            ids.add(raw["activity_id"])
            review = review_map.get(ap)
            if review:
                consumed.add(ap)
                require(
                    not review.get("multi_poi"), ap, "Reviewed multi-POI block", "multi_poi_block"
                )
            if wire == "itinerary_3":
                read_activity_claim(raw, wire)
                span = interval(raw.get("start_time"), raw.get("end_time"))
                require(
                    span is not None
                    and all(t.utcoffset() is not None for t in span)
                    and all(t.date() == day_date for t in span),
                    ap,
                    "New-wire times require positive offset-aware declared-day intervals",
                )
                require(
                    raw.get("activity_kind") != "transport" or version == "v0",
                    ap,
                    "Only V0 declares transport activities",
                )
                require(
                    raw.get("activity_kind") != "main_poi" or text(raw.get("place_name")),
                    ap,
                    "Primary visits require an explicit place name",
                )
                if raw["activity_kind"] == "transport":
                    declaration = raw.get("transport")
                    require(
                        isinstance(declaration, dict)
                        and set(declaration) == {"mode", "from_activity_id", "to_activity_id"}
                        and declaration["mode"] in (*MODES, None)
                        and text(declaration["from_activity_id"])
                        and text(declaration["to_activity_id"]),
                        ap,
                        "New-wire transport requires structured directed endpoints",
                    )
            role, status, reason = classify(raw, review, wire)
            movement = movement_claim(raw["title"])
            rec = {
                "source": source(context, ap),
                **(
                    {"competing_claim": claim_evidence(raw["title"], movement, source(context, ap))}
                    if movement and raw.get("activity_kind") == "main_poi"
                    else {}
                ),
                "declared_day": day["date"],
                "original": {k: raw[k] for k in ACTIVITY_FIELDS if k in raw},
                "evaluation_role": role,
                "role_status": status,
                "reason": reason,
                "review": review,
                "transport_applicable": role == "transport" and version == "v0",
            }
            records.append(rec)
            day_records.append(rec)
            times = [clock(raw.get(k)) for k in ("start_time", "end_time")]
            if any(t is not None and t.utcoffset() is None for t in times):
                report(
                    "timezone_unresolved",
                    [rec["source"]],
                    "Wall time retained; no machine timezone is inferred",
                )
            if role == "unresolved":
                report(reason, [rec["source"]], "Independent activity-role review required")
            if interval(raw.get("start_time"), raw.get("end_time")) is None:
                report("invalid_clock", [rec["source"]], "Invalid or incomparable interval")
        visits = [r for r in day_records if r["evaluation_role"] == "primary_visit"]
        spans = [
            interval(r["original"].get("start_time"), r["original"].get("end_time")) for r in visits
        ]
        ordered = []
        try:
            if any(span is None for span in spans):
                raise ValueError("Invalid visit time")
            ordered = (
                visits
                if wire == "itinerary_3"
                else sorted(
                    visits,
                    key=lambda r: (
                        clock(r["original"]["start_time"]),
                        clock(r["original"]["end_time"]),
                        r["source"]["pointer"],
                    ),
                )
            )
        except (TypeError, ValueError):
            report(
                "adjacency_unresolved",
                [r["source"] for r in visits],
                "Cannot establish chronological adjacency",
            )
        overlapping_ids = set()
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                if not (
                    clock(right["original"]["start_time"]) < clock(left["original"]["end_time"])
                    and clock(left["original"]["start_time"]) < clock(right["original"]["end_time"])
                ):
                    continue
                overlapping_ids.update(
                    (left["original"]["activity_id"], right["original"]["activity_id"])
                )
                report(
                    "overlapping_visit_intervals",
                    [left["source"], right["source"]],
                    "Visit intervals overlap; display ordering does not establish chronology",
                )
        uncertain_roles = any(r["evaluation_role"] == "unresolved" for r in day_records)
        for left, right in zip(ordered, ordered[1:], strict=False):
            leg = {
                "from_source": left["source"],
                "to_source": right["source"],
                "from_activity_id": left["original"]["activity_id"],
                "to_activity_id": right["original"]["activity_id"],
                "declared_day": day["date"],
                "claims": [],
                "gap_start": left["original"]["end_time"],
                "gap_end": right["original"]["start_time"],
                "adjacency_status": "unresolved"
                if uncertain_roles
                or (
                    wire != "itinerary_3"
                    and (
                        left["original"]["activity_id"] in overlapping_ids
                        or right["original"]["activity_id"] in overlapping_ids
                    )
                )
                else "ordered_candidates",
            }
            legs.append(leg)
    transfers = itinerary.get("transfers", [])
    if wire == "itinerary_3":
        require(
            isinstance(transfers, list) and all(isinstance(t, dict) for t in transfers),
            prefix + "/transfers",
            "New-wire transfers must be an object array",
        )
    if not isinstance(transfers, list):
        report(
            "invalid_transfer_collection",
            [source(context, prefix + "/transfers")],
            "Preserved as unavailable transfer representation",
        )
        transfers = []
    for ti, raw in enumerate(transfers):
        ref = source(context, f"{prefix}/transfers/{ti}")
        if not isinstance(raw, dict):
            report("invalid_transfer", [ref], "Expected a transfer object")
            continue
        claim = {
            "source": ref,
            "kind": "transfer",
            "original": {k: raw[k] for k in TRANSFER_FIELDS if k in raw},
            "mode": raw.get("mode") if raw.get("mode") in MODES else None,
            "start": raw.get("departure_time"),
            "end": raw.get("arrival_time"),
        }
        if version == "v0":
            ignored_transport.append(claim)
            report("ignored_transport_source", [ref], "V0 transport uses model activities only")
            continue
        matches = [
            leg
            for leg in legs
            if (leg["from_activity_id"], leg["to_activity_id"])
            == (raw.get("from_activity_id"), raw.get("to_activity_id"))
        ]
        if not matches:
            dangling = (
                not text(raw.get("from_activity_id"))
                or not text(raw.get("to_activity_id"))
                or raw.get("from_activity_id") not in ids
                or raw.get("to_activity_id") not in ids
            )
            report(
                "dangling_transfer_endpoint" if dangling else "nonadjacent_transfer",
                [ref],
                "Transfer cannot be retargeted to another visit pair",
            )
        if raw.get("arrival_time") is None:
            report("missing_claimed_arrival", [ref], "Arrival is not synthesized from duration")
        attach(claim, matches, claims)
    for rec in records:
        if rec["evaluation_role"] != "transport":
            continue
        raw, review = rec["original"], rec["review"]
        claim = {
            "source": rec["source"],
            "kind": "activity",
            "original": raw,
            "mode": mode_claim(raw, review),
            "start": raw.get("start_time"),
            "end": raw.get("end_time"),
        }
        if version != "v0":
            ignored_transport.append(claim)
            report(
                "ignored_transport_source",
                [rec["source"]],
                "V1-V3 transport uses application transfers only; no activity fallback",
            )
            continue
        candidates = [leg for leg in legs if leg["declared_day"] == rec["declared_day"]]
        if review and "from_activity_id" in review:
            matches = [
                leg
                for leg in candidates
                if (leg["from_activity_id"], leg["to_activity_id"])
                == (review["from_activity_id"], review["to_activity_id"])
            ]
        elif raw.get("transport") is not None:
            declaration = raw["transport"]
            pair = (
                (declaration.get("from_activity_id"), declaration.get("to_activity_id"))
                if isinstance(declaration, dict)
                else (None, None)
            )
            matches = [
                leg
                for leg in candidates
                if (wire == "itinerary_3" or leg["adjacency_status"] != "unresolved")
                and (leg["from_activity_id"], leg["to_activity_id"]) == pair
                and (
                    wire == "itinerary_3"
                    or contains(leg["gap_start"], leg["gap_end"], claim["start"], claim["end"])
                )
            ]
        else:
            endpoints = transport_endpoints(raw)
            title = (normalized(raw.get("title")) or "").split(";", 1)[0].strip().removesuffix(".")
            plain_title = title in MODE_TITLES or title in {"transport", "transfer"}
            matches = (
                []
                if endpoints["declared"] or not plain_title
                else [
                    leg
                    for leg in candidates
                    if leg["adjacency_status"] != "unresolved"
                    and contains(leg["gap_start"], leg["gap_end"], claim["start"], claim["end"])
                ]
            )
            if endpoints["pair"]:
                names = {
                    r["original"]["activity_id"]: normalized(
                        r["original"].get("place_name") or r["original"]["title"]
                    )
                    for r in records
                }
                matches = [
                    leg
                    for leg in candidates
                    if leg["adjacency_status"] != "unresolved"
                    and (names[leg["from_activity_id"]], names[leg["to_activity_id"]])
                    == endpoints["pair"]
                    and contains(leg["gap_start"], leg["gap_end"], claim["start"], claim["end"])
                ]
        attach(claim, matches, claims)
        if len(matches) != 1:
            report(
                "ambiguous_transport_association",
                [rec["source"]],
                "Endpoint/position association requires independent review",
            )
    for leg in legs:
        if wire == "itinerary_3":
            require(
                len(leg["claims"]) <= 1,
                prefix,
                "New-wire journeys require a unique selected declaration",
            )
        leg["journey"] = reconcile(leg["claims"])
        if leg["journey"]["agreement"] == "conflicting":
            report(
                "conflicting_transport_claims",
                [c["source"] for c in leg["claims"]],
                "No claim takes precedence",
            )
    require(consumed == set(review_map), prefix, "Review points to no activity in this projection")
    if wire == "itinerary_3":
        require(
            not any(c["association_status"] != "unique" for c in claims),
            prefix,
            "New-wire journeys must identify consecutive primary occurrences",
        )
    return {
        "context": context,
        "policy_version": "declared_activity_claims_1"
        if wire == "itinerary_3"
        else "structural_claims_directed_occurrences_5",
        "projection": prefix,
        "wire_version": wire,
        "planner_version": version,
        "transport_source": "activity" if version == "v0" else "transfer",
        "ignored_transport": ignored_transport,
        "absent_fields": [
            k
            for k in ("output_version", "transfers", "reference_recommendations")
            if k not in itinerary
        ],
        "header": {k: itinerary.get(k) for k in ("destination", "start_date", "end_date")},
        "declared_days": [d["date"] for d in days],
        "activities": records,
        "legs": legs,
        "unbound_transport": [c for c in claims if c["association_status"] != "unique"],
        "nearby": [
            {
                "source": source(context, f"{prefix}/reference_recommendations/{i}"),
                "original": {
                    k: r[k]
                    for k in (
                        "place_name",
                        "source_place_id",
                        "reason",
                        "associated_day",
                        "area",
                        "uncertainty",
                    )
                    if k in r
                },
            }
            for i, r in enumerate(itinerary.get("reference_recommendations", []) or [])
            if isinstance(r, dict)
        ]
        if isinstance(itinerary.get("reference_recommendations", []), list)
        else [],
        "diagnostics": diagnostics,
    }


def contains(start, end, inner_start, inner_end):
    outer, inner = interval(start, end), interval(inner_start, inner_end)
    try:
        return bool(outer and inner and outer[0] <= inner[0] and inner[1] <= outer[1])
    except TypeError:
        return False


def attach(claim, matches, claims):
    claim["association_status"] = "unique" if len(matches) == 1 else "unbound"
    if len(matches) > 1:
        claim["association_status"] = "ambiguous"
    claims.append(claim)
    if len(matches) == 1:
        matches[0]["claims"].append(claim)


def reconcile(claims):
    """Separate duplicates, segments and incompatible alternatives without choosing a winner."""
    if not claims:
        return {"agreement": "incomplete", "occupancy": [], "representation": "absent"}
    groups = {}
    for claim in claims:
        if interval(claim["start"], claim["end"]) is None:
            return {"agreement": "incomplete", "occupancy": [], "representation": "unresolved"}
        key = (claim["mode"], claim["start"], claim["end"])
        groups.setdefault(key, []).append(claim["source"])
    if any(mode is None or interval(a, b) is None for mode, a, b in groups):
        return {"agreement": "incomplete", "occupancy": [], "representation": "unresolved"}
    try:
        windows = sorted(groups, key=lambda key: clock(key[1]))
        segmented = all(
            clock(a[2]) <= clock(b[1]) for a, b in zip(windows, windows[1:], strict=False)
        )
    except TypeError:
        return {"agreement": "incomplete", "occupancy": [], "representation": "unresolved"}
    if len(windows) > 1 and (not segmented or any(c["kind"] == "transfer" for c in claims)):
        return {"agreement": "conflicting", "occupancy": [], "representation": "alternatives"}
    return {
        "agreement": "consistent",
        "representation": "segments" if len(windows) > 1 else "single",
        "occupancy": [
            {"mode": m, "start": a, "end": b, "sources": groups[(m, a, b)]} for m, a, b in windows
        ],
    }
