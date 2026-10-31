"""Explicit non-agentic LangGraph workflow for V1 external evidence."""

import json

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from backend.app.evidence.models import (
    PlaceCandidate,
    PlaceEvidence,
    RouteElementEvidenceType,
)
from backend.app.evidence.opening_hours import planning_opening_hours
from backend.app.llm.client import StructuredLLMClient
from backend.app.observability.run_trace import RunTracer, TracePayloadMode
from backend.app.policies.category_visits import required_category_visit
from backend.app.policies.generation_diagnostics import observe_generation
from backend.app.policies.itinerary_output import output_role_summary, validate_output_sources
from backend.app.policies.requirement_feedback import attach_requirement_feedback
from backend.app.policies.transport import select_transport_mode_from_intent
from backend.app.policies.trip_dates import (
    TripDatePolicyError,
    create_trip_date_window,
    validate_itinerary_dates,
    validate_requested_trip_dates,
)
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.schemas.itinerary import Itinerary
from backend.app.schemas.itinerary_projection import V1Itinerary
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.candidate_acquisition import (
    CandidatePool,
)
from backend.app.services.evidence_acquisition import (
    NoViableCandidatesError,
    V1EvidenceAcquisitionService,
)
from backend.app.services.official_web_integration import OfficialWebIntegrationService
from backend.app.services.planning_supply_pipeline import (
    PlanningCandidateSupplyPipeline,
    PlanningSupplySelection,
    planner_supply_projection,
)
from backend.app.services.preference_interpretation import interpret_preferences
from backend.app.services.reference_discovery import ReferenceDiscoveryService
from backend.app.versions.v1.official_planner import build_official_planner_evidence
from backend.app.versions.v1.official_web import project_official_web_inputs
from backend.app.versions.v1.prompts import (
    ITINERARY_GENERATION_SYSTEM_PROMPT,
    build_itinerary_generation_prompt,
)
from backend.app.versions.v1.state import V1State


class V1StageError(RuntimeError):
    """Identify the V1 stage in which a provider, schema, or graph failure occurred."""

    def __init__(self, stage: str) -> None:
        self.stage = stage
        super().__init__(f"V1 stage failed: {stage}")


def project_selected_places(
    funnel: CandidatePool,
    selection: PlanningSupplySelection,
) -> tuple[list[PlaceCandidate], list[PlaceEvidence]]:
    """Project the stable selected order into aligned downstream Places contracts."""

    by_id = {item.candidate.place_id: item for item in funnel.enriched_candidates}
    candidates: list[PlaceCandidate] = []
    evidence: list[PlaceEvidence] = []
    for place_id in selection.selected_place_ids:
        item = by_id.get(place_id)
        if item is None or item.structured_evidence is None:
            raise ValueError(f"Selected Place {place_id} lacks structured Details evidence")
        if item.structured_evidence.place_id != place_id:
            raise ValueError("Selected candidate and Place evidence IDs do not align")
        candidates.append(item.candidate)
        evidence.append(item.structured_evidence)
    if not candidates:
        raise NoViableCandidatesError("No viable POIs remained after review-aware selection")
    if len({item.place_id for item in candidates}) != len(candidates):
        raise ValueError("Selected POI Place IDs must be unique")
    return candidates, evidence


def build_tools_graph(
    llm_client: StructuredLLMClient,
    evidence_service: V1EvidenceAcquisitionService,
    tracer: RunTracer,
    *,
    llm_config_identity: str = "run_scoped_llm",
    official_web_service: OfficialWebIntegrationService | None = None,
    reference_service: ReferenceDiscoveryService | None = None,
    discovery_extension=None,
    runtime_config=None,
    post_primary=None,
    reference_node=None,
    state_schema=V1State,
    graph_name="v1",
) -> CompiledStateGraph:
    """Build the fixed V1 graph with one bounded official-Web step."""

    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.services.initial_routes import InitialRoutes

    initial_routes = InitialRoutes(evidence_service, runtime_config or load_runtime_config())
    if post_primary is not None:
        repair_timing = initial_routes.config.v3_repair.timing
        initial_routes.work.downstream_reserve = (
            repair_timing.minimum_model_seconds + repair_timing.recheck_reserve_seconds
        )

    async def extract_requirements(state: V1State) -> dict[str, object]:
        try:
            contract = await interpret_preferences(
                state["request"], state["reference_date"], llm_client, tracer,
                category_visits=True,
            )
        except (
            ClarificationRequired,
            RequirementBoundaryError,
            ValidationError,
            TripDatePolicyError,
        ):
            raise
        except Exception as exc:
            raise V1StageError("extract_requirements") from exc
        return {
            "requirements": contract.requirements,
            "interpreted_requirements": contract,
            "requested_place_information": contract.requested_place_information,
            "transport_preference": contract.transport_preference,
        }

    async def validate_trip_dates(state: V1State) -> dict[str, object]:
        requirements = state["requirements"]
        validate_requested_trip_dates(
            requirements.start_date,
            requirements.end_date,
            create_trip_date_window(state["reference_date"]),
        )
        tracer.event(
            "date_window_validated",
            {
                "start_date": requirements.start_date,
                "end_date": requirements.end_date,
            },
        )
        return {}

    async def resolve_destination(state: V1State) -> dict[str, object]:
        tracer.event("destination_resolution_started")
        destination = await evidence_service.resolve_destination(state["requirements"].destination)
        tracer.event("destination_resolved", destination.model_dump(mode="json"))
        return {"destination_context": destination}

    async def acquire_candidate_funnel(state: V1State) -> dict[str, object]:
        pipeline = PlanningCandidateSupplyPipeline(
            evidence_service, llm_client, tracer, llm_config_identity
        )
        pipeline.discovery_extension = discovery_extension
        try:
            funnel, selection = await pipeline.run(
                state["interpreted_requirements"],
                state["destination_context"],
                create_trip_date_window(state["reference_date"]),
            )
        except ClarificationRequired as exc:
            attach_requirement_feedback(exc, state["interpreted_requirements"])
            raise
        try:
            candidates, places = project_selected_places(funnel, selection)
        except NoViableCandidatesError as exc:
            contract = state["interpreted_requirements"]
            error = ClarificationRequired(
                "no_qualified_candidates",
                requirement_ids=tuple(
                    r.requirement_id for r in contract.semantic_requirements
                    if required_category_visit(r)
                ),
            )
            attach_requirement_feedback(error, contract)
            raise error from exc
        tracer.payload(
            "evidence", "selected_place_evidence", places, minimum_mode=TracePayloadMode.NORMALIZED
        )
        return {
            "candidate_funnel": funnel,
            "review_selection": selection,
            "selected_candidates": candidates,
            "place_evidence": places,
            "selection_conflicts": (),
        }

    async def acquire_weather(state: V1State) -> dict[str, object]:
        tracer.event("weather_started")
        weather = await evidence_service.acquire_weather(
            requirements=state["requirements"],
            destination=state["destination_context"],
            reference_date=state["reference_date"],
        )
        tracer.event("weather_completed", {"availability": weather.availability.value})
        return {"weather_evidence": weather}

    async def acquire_routes(state: V1State) -> dict[str, object]:
        mode = select_transport_mode_from_intent(
            state["transport_preference"], state["interpreted_requirements"].transport_constraint
        )
        tracer.event("route_matrix_started", mode.model_dump(mode="json"))
        routes = await initial_routes.prepare(
            places=state["place_evidence"],
            mode=mode,
            requirements=state["requirements"],
        )
        tracer.event(
            "route_matrix_completed",
            {
                "baseline_availability": routes.baseline.availability.value,
                "baseline_element_count": len(routes.baseline.elements),
                "not_observed_reasons": {
                    reason: sum(
                        item.evidence_type is RouteElementEvidenceType.NOT_OBSERVED
                        and (item.unavailable_reason or "unspecified") == reason
                        for item in routes.baseline.elements
                    )
                    for reason in sorted(
                        {
                            item.unavailable_reason or "unspecified"
                            for item in routes.baseline.elements
                            if item.evidence_type is RouteElementEvidenceType.NOT_OBSERVED
                        }
                    )
                },
                "provider_route_not_found_count": sum(
                    item.evidence_type is RouteElementEvidenceType.PROVIDER_OBSERVED
                    and item.condition == "ROUTE_NOT_FOUND"
                    for item in routes.baseline.elements
                ),
                "alternative_count": len(routes.alternatives),
                "non_walkable_pair_count": len(routes.non_walkable_pairs),
            },
        )
        return {"transport_mode": mode, "route_evidence": routes}

    async def acquire_and_resolve_official_web(state: V1State) -> dict[str, object]:
        if official_web_service is None:
            from backend.app.observability.mechanism_observation import accepted_catalog

            accepted_catalog(())
            from backend.app.observability.progress import skipped

            skipped("official_information")
            tracer.event("official_web_disabled")
            return {"official_web_result": None}
        try:
            projection = project_official_web_inputs(
                funnel=state["candidate_funnel"],
                selection=state["review_selection"],
                candidates=state["selected_candidates"],
                places=state["place_evidence"],
            )
            result = await official_web_service.run(
                requirements=state["requirements"],
                projection=projection,
                requested_information=state["requested_place_information"],
            )
        except Exception as exc:
            tracer.event("official_web_integration_failed", {"error_type": type(exc).__name__})
            raise V1StageError("official_web") from exc
        planner_evidence = build_official_planner_evidence(result)
        from backend.app.observability.mechanism_observation import accepted_catalog

        accepted_catalog(result.accepted_evidence)
        tracer.event(
            "official_planner_evidence_prepared",
            {
                "places": [
                    {
                        "place_id": item["place_id"],
                        "accepted_facts": [
                            {
                                key: fact[key]
                                for key in (
                                    "dimension",
                                    "subject_scope",
                                    "scope_text",
                                    "date",
                                    "applicable_start_date",
                                    "applicable_end_date",
                                    "value_kind",
                                    "value_text",
                                    "relation",
                                    "source_refs",
                                )
                            }
                            for fact in item["accepted_effective_facts"]
                        ],
                        "operational_days": item["operational_days"],
                        "need_statuses": item["need_statuses"],
                        "conflict_source_refs": item["unresolved_conflict_source_refs"],
                        "task_statuses": [
                            {
                                "information_need": task["information_need"],
                                "acquisition_status": task["acquisition_status"],
                                "evidence_status": task["evidence_status"],
                                "facet_statuses": task["facet_statuses"],
                            }
                            for task in item["tasks"]
                        ],
                    }
                    for item in planner_evidence
                ],
            },
        )
        return {
            "official_web_result": result,
            "official_planner_evidence": planner_evidence,
        }

    async def generate_evidence_informed_itinerary(
        state: V1State,
    ) -> dict[str, Itinerary]:
        tracer.event("generation_started")
        trip_start = state["requirements"].start_date
        trip_end = state["requirements"].end_date
        if trip_start is None or trip_end is None:
            raise ValueError("Complete trip dates are required for opening-hours planning evidence")
        tracer.event(
            "opening_hours_planning_views_created",
            {
                "places": [
                    {
                        "place_id": place.place_id,
                        "current_present": place.current_opening_hours is not None,
                        "regular_present": place.regular_opening_hours is not None,
                        "current_window_start": (
                            place.current_opening_hours.valid_from
                            if place.current_opening_hours is not None
                            else None
                        ),
                        "current_window_end": (
                            place.current_opening_hours.valid_through
                            if place.current_opening_hours is not None
                            else None
                        ),
                        "date_bases": [
                            {"date": day.date, "basis": day.basis}
                            for day in planning_opening_hours(place, trip_start, trip_end)
                        ],
                    }
                    for place in state["place_evidence"]
                ]
            },
        )
        user_prompt = build_itinerary_generation_prompt(
            state["request"],
            state["requirements"],
            state["reference_date"],
            places=state["place_evidence"],
            weather=state["weather_evidence"],
            routes=state["route_evidence"],
            transport_policy=initial_routes.policy,
            requirement_conflicts=state["selection_conflicts"],
            official_evidence=state.get("official_planner_evidence"),
        )
        user_prompt += "\nPlanning candidate supply contract:\n" + json.dumps(
            planner_supply_projection(state["review_selection"], state["interpreted_requirements"]),
            ensure_ascii=True,
        )
        tracer.payload(
            "llm",
            "itinerary_generation_request",
            {
                "system_prompt": ITINERARY_GENERATION_SYSTEM_PROMPT,
                "user_prompt": user_prompt,
                "response_schema": "V1Itinerary",
            },
            minimum_mode=TracePayloadMode.RAW,
        )
        from backend.app.services.generation_resources import check_primary_input

        generation_config = runtime_config.main_generation if runtime_config else None
        if generation_config and generation_config.enabled:
            sizing = check_primary_input(
                ITINERARY_GENERATION_SYSTEM_PROMPT, user_prompt, generation_config
            )
            tracer.event("primary_generation_resources", sizing)
        generate = llm_client.generate_structured
        generation_kwargs = {}
        if (
            generation_config
            and generation_config.enabled
            and hasattr(llm_client, "generate_primary_structured")
        ):
            generate = llm_client.generate_primary_structured
            generation_kwargs["generation_config"] = generation_config
        try:
            from backend.app.observability.mechanism_observation import model_projection

            with model_projection("primary", state.get("official_planner_evidence") or []):
                itinerary = await generate(
                    **generation_kwargs,
                    system_prompt=ITINERARY_GENERATION_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    response_schema=V1Itinerary,
                )
            itinerary = validate_output_sources(
                itinerary,
                places=state["place_evidence"],
                supplied_ids=state["review_selection"].policy_result.selected_place_ids,
                semantic_assessments=state["review_selection"].semantic_assessments,
            )
        except Exception as exc:
            tracer.event("generation_failed", {"error": type(exc).__name__})
            raise V1StageError("generate_itinerary") from exc
        if isinstance(itinerary, V1Itinerary):
            for projection in itinerary.cost_projections:
                tracer.event("estimated_cost_projected", projection.as_trace_payload())
        tracer.payload(
            "llm",
            "itinerary_generation_response",
            itinerary,
            minimum_mode=TracePayloadMode.RAW,
        )
        tracer.event("generation_completed")
        return {"itinerary": itinerary}

    async def validate_itinerary_date_node(state: V1State) -> dict[str, object]:
        validate_itinerary_dates(
            state["requirements"],
            state["itinerary"],
            create_trip_date_window(state["reference_date"]),
        )
        tracer.event("itinerary_dates_validated")
        diagnostics = observe_generation(
            state["itinerary"],
            state["requirements"],
            reference_date=state["reference_date"],
            contract=state["interpreted_requirements"],
            blank_policy=runtime_config.v3_repair if runtime_config else None,
            places=state["place_evidence"],
            supplied_ids=state["review_selection"].policy_result.selected_place_ids,
            semantic_assessments=state["review_selection"].semantic_assessments,
            named_resolutions=state["candidate_funnel"].named_place_resolutions,
            related_requirement_ids=tuple(
                r.requirement_id for r in state["interpreted_requirements"].semantic_requirements
            ),
        )
        tracer.event("generation_diagnostics", diagnostics.model_dump(mode="json"))
        return {"generation_diagnostics": diagnostics}

    async def bind_actual_transfers(state):
        itinerary, routes = await initial_routes.bind(
            state["itinerary"],
            state["interpreted_requirements"],
            state["place_evidence"],
            state["route_evidence"],
            state["transport_mode"],
        )
        tracer.event("initial_transfer_binding", itinerary.route_diagnostics)
        return {"itinerary": itinerary, "route_evidence": routes}

    async def discover_reference_recommendations(state: V1State) -> dict[str, object]:
        if reference_service is None:
            from backend.app.observability.progress import skipped

            skipped("nearby")
        itinerary = state["itinerary"]
        selection = state["review_selection"].policy_result
        updates = {}
        if reference_service is not None:
            funnel = state["candidate_funnel"]
            result = await reference_service.discover(
                itinerary,
                state["place_evidence"],
                selection.selected_place_ids,
                funnel.excluded_place_ids,
                tuple(
                    item.structured_evidence
                    for item in funnel.enriched_candidates
                    if item.structured_evidence is not None
                ),
            )
            itinerary = result.itinerary
            tracer.event("reference_discovery_completed", result.diagnostics)
            tracer.payload(
                "evidence",
                "nearby_reference_ledger",
                {pid: entry.model_dump(mode="json") for pid, entry in result.ledger.items()},
                minimum_mode=TracePayloadMode.NORMALIZED,
            )
            updates.update(reference_discovery=result)
        summary = output_role_summary(itinerary, selection)
        tracer.event("itinerary_output_roles", summary.model_dump())
        tracer.event(
            "reference_supply_relationship",
            {
                "supply_not_scheduled_ids": sorted(
                    set(selection.selected_place_ids) - set(summary.scheduled_place_ids)
                ),
                "references_outside_supply_ids": sorted(
                    set(summary.reference_place_ids) - set(selection.selected_place_ids)
                ),
            },
        )
        return {"itinerary": itinerary, **updates}

    from backend.app.observability.progress import current_progress, observed

    # HTTP observers are opt-in; independent research runs keep the original node callables.
    if current_progress() is not None:
        resolve_destination = observed("destination")(resolve_destination)
        acquire_candidate_funnel = observed("candidates")(acquire_candidate_funnel)
        acquire_weather = observed("weather")(acquire_weather)
        acquire_routes = observed("routes")(acquire_routes)
        if official_web_service is not None:
            acquire_and_resolve_official_web = observed("official_information")(
                acquire_and_resolve_official_web
            )
        generate_evidence_informed_itinerary = observed("generation")(
            generate_evidence_informed_itinerary
        )
        validate_itinerary_date_node = observed("date_validation")(validate_itinerary_date_node)
        bind_actual_transfers = observed("transfers")(bind_actual_transfers)
        if reference_node is not None or reference_service is not None:
            reference_node = observed("nearby")(
                reference_node or discover_reference_recommendations
            )

    graph_builder = StateGraph(state_schema)
    graph_builder.add_node("extract_requirements", extract_requirements)
    graph_builder.add_node("validate_trip_dates", validate_trip_dates)
    graph_builder.add_node("resolve_destination", resolve_destination)
    graph_builder.add_node("acquire_candidate_funnel", acquire_candidate_funnel)
    graph_builder.add_node("acquire_weather", acquire_weather)
    graph_builder.add_node("acquire_routes", acquire_routes)
    graph_builder.add_node("acquire_and_resolve_official_web", acquire_and_resolve_official_web)
    graph_builder.add_node(
        "generate_evidence_informed_itinerary", generate_evidence_informed_itinerary
    )
    graph_builder.add_node("validate_itinerary_dates", validate_itinerary_date_node)
    graph_builder.add_node("bind_actual_transfers", bind_actual_transfers)
    graph_builder.add_node(
        "discover_reference_recommendations", reference_node or discover_reference_recommendations
    )
    graph_builder.add_edge(START, "extract_requirements")
    graph_builder.add_edge("extract_requirements", "validate_trip_dates")
    graph_builder.add_edge("validate_trip_dates", "resolve_destination")
    graph_builder.add_edge("resolve_destination", "acquire_candidate_funnel")
    graph_builder.add_edge("acquire_candidate_funnel", "acquire_weather")
    graph_builder.add_edge("acquire_weather", "acquire_routes")
    graph_builder.add_edge("acquire_routes", "acquire_and_resolve_official_web")
    graph_builder.add_edge(
        "acquire_and_resolve_official_web", "generate_evidence_informed_itinerary"
    )
    graph_builder.add_edge("generate_evidence_informed_itinerary", "validate_itinerary_dates")
    graph_builder.add_edge("validate_itinerary_dates", "bind_actual_transfers")
    if post_primary is None:
        graph_builder.add_edge("bind_actual_transfers", "discover_reference_recommendations")
    else:
        graph_builder.add_node("post_primary", post_primary)
        graph_builder.add_edge("bind_actual_transfers", "post_primary")
        graph_builder.add_edge("post_primary", "discover_reference_recommendations")
    graph_builder.add_edge("discover_reference_recommendations", END)
    return graph_builder.compile(name=graph_name)


def build_v1_graph(llm_client, evidence_service, tracer, **kwargs):
    """V1 explicitly omits retrieval dependencies and uses the common tools graph."""
    if kwargs.get("discovery_extension") is not None:
        raise ValueError("Use the V2 entry point for retrieval discovery")
    return build_tools_graph(llm_client, evidence_service, tracer, **kwargs)
