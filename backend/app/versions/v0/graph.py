"""LangGraph definition for the V0 plain-LLM workflow."""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from backend.app.llm.client import StructuredLLMClient
from backend.app.policies.itinerary_output import validate_output_sources
from backend.app.policies.trip_dates import (
    TripDatePolicyError,
)
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.schemas.itinerary import Itinerary
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.preference_interpretation import interpret_preferences
from backend.app.versions.v0.prompts import (
    ITINERARY_GENERATION_SYSTEM_PROMPT,
    build_itinerary_generation_prompt,
)
from backend.app.versions.v0.state import V0State


class V0StageError(RuntimeError):
    """Identify the V0 stage in which a provider or schema failure occurred."""

    def __init__(self, stage: str) -> None:
        self.stage = stage
        super().__init__(f"V0 stage failed: {stage}")


def build_v0_graph(llm_client: StructuredLLMClient) -> CompiledStateGraph:
    """Build the fixed two-node V0 graph without tools or persistence."""

    async def extract_requirements(state: V0State) -> dict[str, object]:
        try:
            contract = await interpret_preferences(
                state["request"], state["reference_date"], llm_client
            )
        except (
            ClarificationRequired,
            RequirementBoundaryError,
            ValidationError,
            TripDatePolicyError,
        ):
            raise
        except Exception as exc:
            raise V0StageError("extract_requirements") from exc
        return {"requirements": contract.requirements, "interpreted_requirements": contract}

    async def generate_itinerary(state: V0State) -> dict[str, Itinerary]:
        requirements = state["requirements"]
        try:
            itinerary = await llm_client.generate_structured(
                system_prompt=ITINERARY_GENERATION_SYSTEM_PROMPT,
                user_prompt=build_itinerary_generation_prompt(
                    state["request"],
                    requirements,
                    state["reference_date"],
                    state["interpreted_requirements"],
                ),
                response_schema=Itinerary,
            )
            itinerary = validate_output_sources(itinerary)
            from backend.app.policies.transport_constraints import validate_restricted_transport

            validate_restricted_transport(
                itinerary, state["interpreted_requirements"].transport_constraint, plain=True
            )
        except Exception as exc:
            raise V0StageError("generate_itinerary") from exc

        return {"itinerary": itinerary}

    graph_builder = StateGraph(V0State)
    graph_builder.add_node("extract_requirements", extract_requirements)
    graph_builder.add_node("generate_itinerary", generate_itinerary)
    graph_builder.add_edge(START, "extract_requirements")
    graph_builder.add_edge("extract_requirements", "generate_itinerary")
    graph_builder.add_edge("generate_itinerary", END)
    return graph_builder.compile(name="v0")
