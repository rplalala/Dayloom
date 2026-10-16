"""Source-selected scheduled commitments and independently expanded protected blockers."""

from dataclasses import dataclass
from datetime import date, datetime

from .records import canonical_digest as stable_id
from .records import freeze, require, text, thaw
from .schedule_time import Span, expand_protection, normalize_interval


def union(spans):
    """Union half-open intervals, including touching spans, without filling gaps."""
    result = []
    for span in sorted(spans, key=lambda item: (item.start, item.end)):
        if result and span.start <= result[-1].end:
            result[-1] = Span(result[-1].start, max(result[-1].end, span.end))
        else:
            result.append(span)
    return result


def intersections(left, right):
    return union(
        Span(max(a.start, b.start), min(a.end, b.end))
        for a in left
        for b in right
        if max(a.start, b.start) < min(a.end, b.end)
    )


def read_span(value):
    return Span(datetime.fromisoformat(value["start"]), datetime.fromisoformat(value["end"]))


def _relation(left, right):
    """Universal alternative evidence can prove conflict; an unknown scenario cannot."""
    outcomes = [
        intersections(a, b) if a is not None and b is not None else None
        for a in left.scenarios
        for b in right.scenarios
    ]
    state = (
        "FAIL"
        if outcomes and all(outcomes)
        else ("PASS" if outcomes and all(item == [] for item in outcomes) else "UNKNOWN")
    )
    guaranteed = list(outcomes[0]) if outcomes and outcomes[0] is not None else []
    for outcome in outcomes[1:]:
        guaranteed = intersections(guaranteed, outcome) if outcome is not None else []
    return state, guaranteed


def _applies(unit, scope):
    return scope == "scheduled_commitments" or unit.kind == "primary_visit"


def _candidate_unit(candidate):
    interval = candidate.get("interval")
    return Commitment(
        stable_id(candidate["sources"]),
        candidate.get("kind", "unresolved"),
        (),
        candidate.get("declared_day"),
        ((read_span(interval),) if interval else None,),
    )


def _candidate_applies(candidate, scope):
    return scope == "scheduled_commitments" or candidate.get("kind", "unresolved") in (
        "unresolved",
        "primary_visit",
    )


def _measure(spans, unknown_count):
    known = union(spans)
    return {
        "seconds": sum(item.seconds for item in known) if known or not unknown_count else None,
        "intervals": [item.to_dict() for item in known],
        "status": "lower_bound" if unknown_count else "complete",
        "unknown_record_count": unknown_count,
    }


def assess_occupancy(prepared):
    """One verdict per commitment, with pair measures separate from union measures."""
    units = prepared.commitments
    states = {unit.commitment_id: "PASS" if unit.complete else "UNKNOWN" for unit in units}
    reasons = {unit.commitment_id: list(unit.reasons) for unit in units}
    pairs, pair_spans, protection_spans, protection_conflicts = [], [], [], []
    pair_unknown = protection_unknown = 0
    protection_states = {}

    def update(unit, state, reason):
        key = unit.commitment_id
        if state == "FAIL" or state == "UNKNOWN" and states[key] == "PASS":
            states[key] = state
        if state != "PASS":
            reasons[key].append(reason)

    for index, left in enumerate(units):
        for right in units[index + 1 :]:
            state, spans = _relation(left, right)
            update(
                left,
                state,
                "commitment_overlap" if state == "FAIL" else "possible_commitment_overlap",
            )
            update(
                right,
                state,
                "commitment_overlap" if state == "FAIL" else "possible_commitment_overlap",
            )
            pair_unknown += int(
                state == "UNKNOWN" or state == "FAIL" and not (left.complete and right.complete)
            )
            if state == "FAIL" or spans:
                pairs.append(
                    {
                        "commitment_ids": [left.commitment_id, right.commitment_id],
                        "state": state,
                        "intervals": [span.to_dict() for span in spans],
                        "seconds": sum(span.seconds for span in spans) if spans else None,
                        "status": "complete" if left.complete and right.complete else "lower_bound",
                    }
                )
                pair_spans.extend(spans)
    for blocker in thaw(prepared.blockers):
        for oid in blocker["obligation_ids"]:
            original = read_span(blocker["original_intervals"][oid])
            boundary = Commitment(oid, "protection", (), blocker["date"], ((original,),))
            states_for_obligation = []
            for unit in units:
                if not _applies(unit, blocker["scope"]):
                    continue
                state, spans = _relation(unit, boundary)
                update(
                    unit,
                    state,
                    "protected_time_overlap" if state == "FAIL" else "possible_protected_overlap",
                )
                states_for_obligation.append(state)
                protection_unknown += int(
                    state == "UNKNOWN" or state == "FAIL" and not unit.complete
                )
                if state == "FAIL" or spans:
                    protection_conflicts.append(
                        {
                            "commitment_id": unit.commitment_id,
                            "obligation_id": oid,
                            "state": state,
                            "intervals": [span.to_dict() for span in spans],
                        }
                    )
                    protection_spans.extend(spans)
            for candidate in thaw(prepared.candidates):
                if (
                    _candidate_applies(candidate, blocker["scope"])
                    and _relation(_candidate_unit(candidate), boundary)[0] != "PASS"
                ):
                    states_for_obligation.append("UNKNOWN")
                    protection_unknown += 1
            protection_states[oid] = (
                "FAIL"
                if "FAIL" in states_for_obligation
                else ("UNKNOWN" if "UNKNOWN" in states_for_obligation else "PASS")
            )
    for pending in thaw(prepared.pending_protections):
        protection_states[pending["obligation_id"]] = "UNKNOWN"
        protection_unknown += 1
        for unit in units:
            if pending["scope"] is None or _applies(unit, pending["scope"]):
                update(unit, "UNKNOWN", "protection_time_unresolved")
    if prepared.candidates:
        for unit in units:
            for candidate in thaw(prepared.candidates):
                if _relation(unit, _candidate_unit(candidate))[0] != "PASS":
                    update(unit, "UNKNOWN", "candidate_commitment_conflict_unresolved")
                    pair_unknown += 1
        # Candidate-to-candidate grouping and applicability remain unavailable.
        pair_unknown += max(0, len(prepared.candidates) - 1)
    checks = [
        {
            "check_id": stable_id(["non_overlap", unit.commitment_id]),
            "commitment_id": unit.commitment_id,
            "kind": unit.kind,
            "applicability": "applicable",
            "sources": thaw(unit.sources),
            "state": states[unit.commitment_id],
            "reasons": list(dict.fromkeys(reasons[unit.commitment_id])),
        }
        for unit in units
    ]
    missing = sum(not unit.complete for unit in units) + len(prepared.candidates)
    occupied = [span for unit in units for span in unit.guaranteed]
    measures = {
        "scope": "all_submitted_commitments",
        "commitment_pairs": pairs,
        "protection_conflicts": protection_conflicts,
        "scheduled_occupied": _measure(occupied, missing),
        "protected_reserved": _measure(
            [read_span(b["interval"]) for b in thaw(prepared.blockers)],
            len(prepared.pending_protections),
        ),
        "commitment_conflict": _measure(pair_spans, pair_unknown),
        "protection_conflict": _measure(protection_spans, protection_unknown),
        "combined_conflict": _measure(
            pair_spans + protection_spans, pair_unknown + protection_unknown
        ),
        "pair_intersection_sum": {
            "seconds": sum(span.seconds for span in pair_spans)
            if pair_spans or not pair_unknown
            else None,
            "status": "lower_bound" if pair_unknown else "complete",
            "unknown_record_count": pair_unknown,
        },
    }
    return checks, protection_states, measures


@dataclass(frozen=True)
class Commitment:
    commitment_id: str
    kind: str
    sources: tuple
    declared_day: str
    # A scenario is complete submitted occupancy; None preserves an unknown alternative.
    scenarios: tuple
    reasons: tuple = ()
    time_records: tuple = ()

    @property
    def complete(self):
        return len(self.scenarios) == 1 and self.scenarios[0] is not None

    @property
    def guaranteed(self):
        if not self.scenarios or any(item is None for item in self.scenarios):
            return []
        result = list(self.scenarios[0])
        for scenario in self.scenarios[1:]:
            result = intersections(result, scenario)
        return result

    def to_dict(self):
        return {
            "commitment_id": self.commitment_id,
            "kind": self.kind,
            "sources": thaw(self.sources),
            "declared_day": self.declared_day,
            "intervals": [item.to_dict() for item in self.guaranteed],
            "time_complete": self.complete,
            "alternatives": [
                [span.to_dict() for span in item] if item is not None else None
                for item in self.scenarios
            ],
            "reasons": list(self.reasons),
            "time_records": thaw(self.time_records),
        }


@dataclass(frozen=True)
class OccupancyResult:
    commitments: tuple
    blockers: tuple
    candidates: tuple
    pending_protections: tuple
    transport_coverage: tuple

    def to_dict(self):
        return {
            "commitments": [item.to_dict() for item in self.commitments],
            "blockers": thaw(self.blockers),
            "candidates": thaw(self.candidates),
            "pending_protections": thaw(self.pending_protections),
            "transport_coverage": thaw(self.transport_coverage),
            "denominator_unresolved": bool(self.candidates),
        }


def _activity_unit(activity, kind, timezone):
    raw = activity["original"]
    interval = normalize_interval(
        raw.get("start_time"), raw.get("end_time"), activity["declared_day"], timezone
    )
    return Commitment(
        stable_id([kind, activity["source"]]),
        kind,
        (freeze(activity["source"]),),
        activity["declared_day"],
        ((interval.span,) if interval.span else None,),
        interval.reasons,
        (freeze({"source": activity["source"], **interval.to_dict()}),),
    )


def _journey(leg, timezone):
    claims = leg["claims"]
    sources = tuple(freeze(claim["source"]) for claim in claims)
    windows = {}
    reasons, time_records = [], []
    for claim in claims:
        interval = normalize_interval(claim["start"], claim["end"], leg["declared_day"], timezone)
        reasons.extend(interval.reasons)
        time_records.append(freeze({"source": claim["source"], **interval.to_dict()}))
        windows[stable_id([claim["start"], claim["end"]])] = interval.span
    known = sorted((span for span in windows.values() if span), key=lambda span: span.start)
    segmented = all(a.end <= b.start for a, b in zip(known, known[1:], strict=False))
    if len(windows) == 1:
        scenarios = ((known[0],) if known else None,)
    elif len(known) == len(windows) and segmented and all(c["kind"] == "activity" for c in claims):
        scenarios = (tuple(known),)
    else:
        scenarios = tuple((span,) if span else None for span in windows.values())
        reasons.append("journey_occupancy_unresolved")
    return Commitment(
        stable_id(["journey", leg["from_source"], leg["to_source"]]),
        "transport",
        sources,
        leg["declared_day"],
        scenarios,
        tuple(dict.fromkeys(reasons)),
        tuple(time_records),
    )


def prepare_occupancy(projection, obligations, timezone=None, reviews=()):
    """Prepare occupancy only; obligation validation and review linkage precede this boundary."""
    decisions = {item["source"]["record_id"]: item for item in reviews}
    protections = [item for item in obligations if item["kind"] == "protected_time"]
    blockers, pending = [], []
    expanded = {}
    for item in protections:
        interval = expand_protection(item, timezone) if item["resolution"] == "resolved" else None
        if interval and interval.span:
            expanded[item["obligation_id"]] = interval.span
            blockers.append(
                {
                    "date": item["date"],
                    "scope": item["scope"],
                    "span": interval.span,
                    "obligation_ids": [item["obligation_id"]],
                }
            )
        else:
            pending.append(
                {
                    "obligation_id": item["obligation_id"],
                    "date": item.get("date"),
                    "scope": item.get("scope"),
                    "reasons": list(interval.reasons) if interval else ["unresolved_protection"],
                }
            )
    merged = []
    for blocker in sorted(blockers, key=lambda b: (b["date"], b["scope"], b["span"].start)):
        if (
            merged
            and (merged[-1]["date"], merged[-1]["scope"]) == (blocker["date"], blocker["scope"])
            and blocker["span"].start <= merged[-1]["span"].end
        ):
            old = merged[-1]
            old["span"] = Span(old["span"].start, max(old["span"].end, blocker["span"].end))
            old["obligation_ids"].extend(blocker["obligation_ids"])
        else:
            merged.append(blocker.copy())
    output_blockers = [
        {
            "date": b["date"],
            "scope": b["scope"],
            "interval": b["span"].to_dict(),
            "obligation_ids": b["obligation_ids"],
            "original_intervals": {key: expanded[key].to_dict() for key in b["obligation_ids"]},
        }
        for b in merged
    ]
    commitments, candidates, coverage = [], [], []
    for activity in projection["activities"]:
        role = activity["evaluation_role"]
        decision = decisions.get(activity["source"]["record_id"])
        if role == "primary_visit":
            commitments.append(_activity_unit(activity, "primary_visit", timezone))
        elif role == "transport":
            continue  # Only the version-selected claims below establish transport occupancy.
        elif (
            role == "transition"
            and not decision
            and projection.get("wire_version") == "itinerary_3"
        ):
            if activity["original"]["time_use"] == "scheduled":
                commitments.append(_activity_unit(activity, "fixed_generic", timezone))
        elif role == "transition" and decision and decision["occupancy"] == "committed":
            commitments.append(_activity_unit(activity, "fixed_generic", timezone))
        elif role == "transition" and decision and decision["occupancy"] == "uncommitted":
            refs = decision.get("protected_obligation_refs", [])
            if refs:
                unit = _activity_unit(activity, "fixed_generic", timezone)
                reserved = union(expanded[key] for key in refs if key in expanded)
                if unit.complete and all(key in expanded for key in refs):
                    require(
                        unit.guaranteed == reserved,
                        activity["source"]["record_id"],
                        "Reviewed placeholder conflicts with linked protection intervals",
                    )
                if (
                    not all(key in expanded for key in refs)
                    or len(reserved) != 1
                    or not unit.complete
                    or unit.guaranteed != reserved
                ):
                    candidates.append(
                        {
                            "sources": [activity["source"]],
                            "reason": "placeholder_correspondence_unresolved",
                            "kind": "fixed_generic",
                            "interval": unit.guaranteed[0].to_dict() if unit.complete else None,
                        }
                    )
        elif (
            role == "transition"
            and not decision
            and not activity["original"].get("notes")
            and not text(activity["original"].get("place_name"))
            and not text(activity["original"].get("source_place_id"))
            and not activity["original"].get("location")
        ):
            continue
        else:
            unit = _activity_unit(activity, role, timezone)
            candidates.append(
                {
                    "sources": [activity["source"]],
                    "reason": "occupancy_unresolved",
                    "kind": role,
                    "declared_day": activity["declared_day"],
                    "interval": unit.guaranteed[0].to_dict() if unit.complete else None,
                    "time_records": thaw(unit.time_records),
                }
            )
    for leg in projection["legs"]:
        coverage.append(
            {
                "from_source": leg["from_source"],
                "to_source": leg["to_source"],
                "claims_present": bool(leg["claims"]),
            }
        )
        if leg["claims"]:
            commitments.append(_journey(leg, timezone))
    for claim in projection["unbound_transport"]:
        activity = next(
            (a for a in projection["activities"] if a["source"] == claim["source"]), None
        )
        if (
            projection["planner_version"] == "v0"
            and activity is not None
            and activity["evaluation_role"] == "transport"
        ):
            commitments.append(_activity_unit(activity, "transport", timezone))
            continue
        day = activity["declared_day"] if activity else None
        if day is None and isinstance(claim["start"], str):
            try:
                day = date.fromisoformat(claim["start"][:10]).isoformat()
            except ValueError:
                pass
        interval = normalize_interval(claim["start"], claim["end"], day, timezone)
        candidates.append(
            {
                "sources": [claim["source"]],
                "reason": "transport_association_unresolved",
                "kind": "transport",
                "start": claim["start"],
                "end": claim["end"],
                "declared_day": day,
                "date_basis": "activity_declared_day" if activity else "explicit_claim_timestamp",
                "interval": interval.span.to_dict() if interval.span else None,
                "time_records": [{"source": claim["source"], **interval.to_dict()}],
            }
        )
    return OccupancyResult(
        tuple(commitments),
        tuple(freeze(output_blockers)),
        tuple(freeze(candidates)),
        tuple(freeze(pending)),
        tuple(freeze(coverage)),
    )
