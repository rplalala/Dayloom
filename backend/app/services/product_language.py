"""Product-only writing policy; borrowed providers retain their native ownership."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace

from backend.app.schemas.itinerary_projection import V1Itinerary
from backend.app.services.planner_runtime import (
    PlannerDependencies,
    create_planner_dependencies,
)

PRODUCT_WRITING_INSTRUCTION = (
    "Product writing policy: Write newly authored itinerary titles, notes and explanations "
    "in English, including replacement prose in Repair. Preserve supplied proper names, "
    "place names, complete source addresses, quoted original user text, identifiers, source "
    "evidence and numeric/time facts verbatim. Do not translate or reinterpret constraints; "
    "do not add requirements."
)


class ProductEnglishClient:
    """Add a writing instruction to itinerary generation, never to extraction/evidence."""

    def __init__(self, client):
        self._client = client
        for name in ("generate_primary_structured", "generate_repair_structured"):
            if hasattr(client, name):
                setattr(self, name, self._with_writing_policy(getattr(client, name)))

    @staticmethod
    def _with_writing_policy(operation):
        async def invoke(*, system_prompt, **kwargs):
            return await operation(
                system_prompt=system_prompt + "\n" + PRODUCT_WRITING_INSTRUCTION, **kwargs
            )

        return invoke

    def __getattr__(self, name):
        return getattr(self._client, name)

    async def generate_structured(self, *, system_prompt, response_schema, **kwargs):
        if response_schema is V1Itinerary:
            system_prompt += "\n" + PRODUCT_WRITING_INSTRUCTION
        return await self._client.generate_structured(
            system_prompt=system_prompt, response_schema=response_schema, **kwargs
        )


@asynccontextmanager
async def create_product_planner_dependencies(
    version, config, tracer, *, dependency_factory=create_planner_dependencies
) -> AsyncIterator[PlannerDependencies]:
    """Borrow request-local providers; the underlying factory alone owns their cleanup."""
    async with dependency_factory(version, config, tracer) as dependencies:
        identity = dependencies.llm_identity or (
            f"{type(dependencies.llm).__module__}.{type(dependencies.llm).__qualname__}"
        )
        yield replace(
            dependencies, llm=ProductEnglishClient(dependencies.llm), llm_identity=identity
        )
