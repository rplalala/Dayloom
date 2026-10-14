"""Shared first-generation route work, independent of Repair authority."""

from contextlib import contextmanager
from hashlib import sha256
from time import monotonic

from backend.app.evidence.models import RouteEvidenceBundle, RouteEvidencePurpose
from backend.app.integrations.google.routes import ROUTE_MATRIX_FIELD_MASK
from backend.app.integrations.models import LatLng, RouteMatrixRequest, RouteWaypoint
from backend.app.observability.run_trace import TracePayloadMode
from backend.app.policies.itinerary_schedule import (
    available_intervals,
    build_schedule,
    ordered_activities,
)
from backend.app.policies.route_options import route_option, route_rows, transfer_time_check
from backend.app.runtime.budget import ToolBudgetExceededError, ToolBudgetKey


class RouteWork:
    """Overlapping work intervals count once; pauses do not consume route wall time."""

    def __init__(self, config, clock=monotonic):
        self.config, self.clock = config, clock
        self.elapsed = 0.0
        self.depth = 0
        self.started = None
        self.phase = "pre"

    @contextmanager
    def active(self, phase):
        if not self.depth:
            self.started, self.phase = self.clock(), phase
        self.depth += 1
        try:
            yield self
        finally:
            self.depth -= 1
            if not self.depth:
                self.elapsed += self.clock() - self.started
                self.started = None

    def remaining(self):
        used = self.elapsed + (self.clock() - self.started if self.depth else 0)
        reserve = self.config.post_generation_reserved_seconds if self.phase == "pre" else 0
        remaining = self.config.work_seconds - reserve - used
        deadline = getattr(self, "request_deadline", None)
        if deadline is not None:
            remaining = min(
                remaining,
                deadline
                - self.clock()
                - getattr(self, "nearby_reserve", 0)
                - getattr(self, "downstream_reserve", 0),
            )
        return max(0, remaining)


def permitted_modes(mode):
    if mode.allowed_modes is not None:
        return tuple(m.value for m in mode.allowed_modes)
    if mode.is_explicit or mode.travel_mode != "WALK":
        return (mode.travel_mode.value if hasattr(mode.travel_mode, "value") else mode.travel_mode,)
    return ("WALK", "TRANSIT", "DRIVE")


def compact_routes(bundle):
    """Keep all directed facts; deduplicate packaging, never equate omission with absence."""
    sources, facts = {}, {}
    for route in (bundle.baseline, *bundle.alternatives):
        key = sha256(route.model_dump_json().encode()).hexdigest()[:20]
        sources[key] = dict(
            source_ref=route.source_ref,
            mode=route.travel_mode,
            routing_preference=route.routing_preference,
            departure=route.representative_departure_time.isoformat()
            if route.representative_departure_time
            else None,
            retrieved_at=route.retrieved_at.isoformat(),
            availability=route.availability,
        )
        for e in route.elements:
            row = dict(
                origin=e.origin_place_id,
                destination=e.destination_place_id,
                seconds=e.duration_seconds,
                metres=e.distance_meters,
                status=e.status_state,
                condition=e.condition,
                evidence_type=e.evidence_type,
                availability=e.availability,
                fallback=e.fallback_info,
                source=key,
            )
            facts[(key, e.origin_place_id, e.destination_place_id)] = row
    return dict(
        projection_version="primary_mixed_routes_1",
        sources=sources,
        directed_facts=[facts[k] for k in sorted(facts)],
        omissions=[],
        qualification="Planning options only. Recheck actual adjacency and departure; "
        "representative TRANSIT is not final-time validation. Application DRIVE reserve "
        "is separate from provider duration. Missing options do not prove unreachable.",
    )


class InitialRoutes:
    def __init__(self, acquisition, config):
        self.acq, self.config = acquisition, config
        self.policy = config.transport or config.v3_repair.spatial
        self.work = RouteWork(config.budget.routes)
        self.pairs = set()
        self.stops = []
        acquisition.initial_route_work = self.work
        self.work.request_deadline = getattr(acquisition, "request_deadline", None) or getattr(
            acquisition._routes, "deadline", None
        )
        self.work.nearby_reserve = config.reference_discovery.deadline_seconds

    def allowed(self, key):
        cfg = self.config.budget.routes
        reserves = {
            ToolBudgetKey.ALTERNATIVE_ROUTE_PAIRS: cfg.post_generation_reserved_pairs,
            ToolBudgetKey.ALTERNATIVE_ROUTE_MATRIX_CALLS: cfg.post_generation_reserved_requests,
            ToolBudgetKey.ALTERNATIVE_ROUTE_ELEMENTS: cfg.post_generation_reserved_elements,
        }
        return max(
            0, self.acq._budget.remaining(key) - (reserves[key] if self.work.phase == "pre" else 0)
        )

    async def fetch(self, origin, destination, mode, departure, places, preference=None):
        if mode == "TRANSIT" and departure is None:
            self.stops.append("departure_unavailable")
            return None

        def waypoint(pid):
            p = places[pid]
            return RouteWaypoint(
                place_id=pid, location=LatLng(latitude=p.latitude, longitude=p.longitude)
            )

        if origin not in places or destination not in places:
            self.stops.append("identity_outside_supply")
            return None
        if any(
            places[pid].latitude is None or places[pid].longitude is None
            for pid in (origin, destination)
        ):
            self.stops.append("route_coordinates_unavailable")
            return None
        request = RouteMatrixRequest(
            origins=[waypoint(origin)],
            destinations=[waypoint(destination)],
            travel_mode=mode,
            routing_preference=(preference or "TRAFFIC_UNAWARE") if mode == "DRIVE" else None,
            departure_time=departure
            if mode == "TRANSIT" or mode == "DRIVE" and preference not in (None, "TRAFFIC_UNAWARE")
            else None,
            field_mask=ROUTE_MATRIX_FIELD_MASK,
        )
        key = self.acq._route_cache_key(request)
        _, cached = self.acq._cache.lookup(key)
        if not cached:
            if self.acq._cache.terminal_attempt(key):
                self.stops.append("previous_sent_request")
                return None
            if self.work.remaining() <= 0:
                self.stops.append("route_work_exhausted")
                return None
            for budget_key in (
                ToolBudgetKey.ALTERNATIVE_ROUTE_MATRIX_CALLS,
                ToolBudgetKey.ALTERNATIVE_ROUTE_ELEMENTS,
            ):
                if not self.allowed(budget_key):
                    self.stops.append(budget_key.value)
                    return None
            pair = (origin, destination)
            if pair not in self.pairs:
                if not self.allowed(ToolBudgetKey.ALTERNATIVE_ROUTE_PAIRS):
                    self.stops.append("alternative_route_pairs")
                    return None
                self.acq._budget.consume(ToolBudgetKey.ALTERNATIVE_ROUTE_PAIRS, 1)
                self.pairs.add(pair)
        try:
            return await self.acq._acquire_route_matrix(
                request,
                mode_reason="shared_initial_mixed",
                purpose=RouteEvidencePurpose.NON_WALKABLE_ALTERNATIVE,
                budget_key=ToolBudgetKey.ALTERNATIVE_ROUTE_ELEMENTS,
                call_budget_key=ToolBudgetKey.ALTERNATIVE_ROUTE_MATRIX_CALLS,
            )
        except ToolBudgetExceededError as exc:
            self.stops.append(exc.key.value)
            return None

    def usable(self, origin, destination, mode, departure, evidence, preference=None):
        rows = route_rows(origin, destination, mode, preference, departure, evidence)
        if not rows or len({r["duration_seconds"] for r in rows}) != 1:
            return False
        row = rows[0]
        limit = (
            self.policy.max_leg_minutes
            if mode == "WALK"
            else self.policy.transit_max_minutes
            if mode == "TRANSIT"
            else self.policy.drive_max_minutes
        )
        return row["duration_seconds"] <= limit * 60 and (
            mode != "WALK"
            or row["element"].get("distance_meters") is not None
            and row["element"]["distance_meters"] <= self.policy.walk_route_max_km * 1000
        )

    async def prepare(self, *, places, mode, requirements):
        lookup = {p.place_id: p for p in places}
        departure = self.acq._representative_departure_time(places, requirements)
        with self.work.active("pre"):
            waypoints = [
                RouteWaypoint(
                    place_id=p.place_id, location=LatLng(latitude=p.latitude, longitude=p.longitude)
                )
                for p in places
            ]
            baseline = await self.acq._acquire_baseline_route_chunks(
                waypoints=waypoints,
                mode=mode,
                departure_time=departure if mode.travel_mode == "TRANSIT" else None,
            )
            evidence = [baseline]
            modes = permitted_modes(mode)
            ids = sorted(lookup)
            # Rotate destinations across every origin before giving an origin another turn.
            # No score and no inferred dates/targets exist before generation.
            for offset in range(1, len(ids)):
                for index, origin in enumerate(ids):
                    destination = ids[(index + offset) % len(ids)]
                    if any(
                        self.usable(
                            origin, destination, m, departure, evidence, mode.routing_preference
                        )
                        for m in modes
                    ):
                        continue
                    for m in modes:
                        # Do not reconstruct failed baseline chunks as smaller retry requests.
                        if m == mode.travel_mode:
                            continue
                        extra = await self.fetch(origin, destination, m, departure, lookup)
                        if extra:
                            evidence.append(extra)
                        if self.usable(origin, destination, m, departure, evidence):
                            break
            bundle = RouteEvidenceBundle(baseline=baseline, alternatives=evidence[1:])
        self.acq._tracer.event(
            "initial_route_projection",
            {"policy": self.policy.model_dump(), "projection": compact_routes(bundle)},
        )
        self.acq._tracer.payload(
            "evidence",
            "route_evidence_bundle",
            bundle,
            minimum_mode=TracePayloadMode.NORMALIZED,
        )
        self.audit("pre")
        return bundle

    def audit(self, phase):
        self.acq._tracer.event(
            "initial_route_work",
            dict(
                phase=phase,
                elapsed_seconds=self.work.elapsed,
                directed_pairs=sorted(self.pairs),
                stops=list(self.stops),
                budget=self.acq._route_budget_summary(),
            ),
        )

    async def bind(self, itinerary, contract, places, bundle, mode):
        evidence = [bundle.baseline, *bundle.alternatives]
        lookup = {p.place_id: p for p in places}
        schedule = build_schedule(itinerary, contract, places, primary_generated=True)
        transfers, diagnostics = [], []
        with self.work.active("post"):
            for day in itinerary.days:
                ordered = ordered_activities(day, schedule)
                for left, right in zip(ordered, ordered[1:], strict=False):
                    modes = permitted_modes(mode)
                    if (
                        not left.source_place_id
                        or not right.source_place_id
                        or not available_intervals(left, right, schedule)
                    ):
                        diagnostics.append(
                            leg_diagnostic(
                                left, right, modes, evidence, self.policy, schedule, mode
                            )
                        )
                        continue

                    def choose(left=left, right=right, modes=modes):
                        return next(
                            (
                                option
                                for m in modes
                                if m in ("WALK", "TRANSIT", "DRIVE")
                                and (
                                    option := route_option(
                                        left,
                                        right,
                                        m,
                                        evidence,
                                        self.policy,
                                        schedule,
                                        mode.routing_preference if mode.is_explicit else None,
                                    )
                                )
                            ),
                            None,
                        )

                    selected = choose()
                    if selected is None:
                        for m in modes:
                            if m not in ("WALK", "TRANSIT", "DRIVE"):
                                continue
                            for start, _ in available_intervals(left, right, schedule):
                                existing = route_rows(
                                    left.source_place_id,
                                    right.source_place_id,
                                    m,
                                    mode.routing_preference if mode.is_explicit else None,
                                    start,
                                    evidence,
                                )
                                if existing:
                                    continue
                                extra = await self.fetch(
                                    left.source_place_id,
                                    right.source_place_id,
                                    m,
                                    start,
                                    lookup,
                                    mode.routing_preference if mode.is_explicit else None,
                                )
                                if extra:
                                    evidence.append(extra)
                                selected = choose()
                                if selected:
                                    break
                            if selected:
                                break
                    if selected:
                        if mode.is_explicit:
                            selected = selected.model_copy(update={"mode_source": "USER_EXPLICIT"})
                        transfers.append(selected)
                    diagnostics.append(
                        leg_diagnostic(
                            left, right, modes, evidence, self.policy, schedule, mode, selected
                        )
                    )
        final = itinerary.model_copy(
            update={"transfers": transfers, "route_diagnostics": diagnostics}, deep=True
        )
        from backend.app.policies.transport_constraints import validate_restricted_transport

        validate_restricted_transport(final, contract.transport_constraint)
        self.audit("post")
        return final, bundle.model_copy(update={"alternatives": evidence[1:]})


def leg_diagnostic(left, right, modes, evidence, policy, schedule, decision, adopted=None):
    row = dict(
        from_activity_id=left.activity_id,
        to_activity_id=right.activity_id,
        origin=left.source_place_id,
        destination=right.source_place_id,
        departure=left.end_time.isoformat(),
        next_start=right.start_time.isoformat(),
        considered_modes=list(modes),
        adopted_mode=adopted.mode if adopted else None,
        result=adopted.validation_state if adopted else "UNKNOWN",
        reason="bound" if adopted else "insufficient_evidence",
        mode_results=[],
    )
    if (
        not left.source_place_id
        or not right.source_place_id
        or left.end_time.utcoffset() is None
        or right.start_time.utcoffset() is None
    ):
        row.update(result="UNKNOWN", reason="not_evaluable_location_or_time")
        return row
    intervals = available_intervals(left, right, schedule)
    for m in modes:
        departure = (
            adopted.departure_time
            if adopted and adopted.mode == m
            else (intervals[0][0] if intervals else left.end_time)
        )
        rows = route_rows(
            left.source_place_id,
            right.source_place_id,
            m,
            decision.routing_preference if decision.is_explicit else None,
            departure,
            evidence,
        )
        status, reason = "UNKNOWN", "applicable_route_unavailable"
        if rows and len({r["duration_seconds"] for r in rows}) == 1:
            reserve = policy.drive_reserve_minutes * 60 if m == "DRIVE" else 0
            comparison = transfer_time_check(left, right, rows, schedule, departure, reserve)
            status = "UNKNOWN" if comparison is None else "CONFIRMED" if comparison[1] else "PASS"
            reason = (
                "specific_mode_transfer_deficit"
                if status == "CONFIRMED"
                else "time_connection_only"
            )
        row["mode_results"].append(dict(mode=m, status=status, reason=reason, evidence=rows))
    if (
        not adopted
        and row["mode_results"]
        and all(r["status"] == "CONFIRMED" for r in row["mode_results"])
    ):
        row.update(
            result="CONFIRMED",
            reason="required_mode_deficit"
            if decision.is_explicit
            else "all_allowed_modes_checked_deficit",
        )
    elif not adopted and any(r["status"] == "PASS" for r in row["mode_results"]):
        row["reason"] = "automatic_mode_policy_not_satisfied"
    return row
