"""Product-only writing policy; borrowed providers retain their native ownership."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace

from backend.app.runtime.config_loader import load_runtime_config
from backend.app.schemas.itinerary_projection import V1Itinerary
from backend.app.services.generation_resources import check_primary_input
from backend.app.services.planner_runtime import (
    PlannerDependencies,
    create_planner_dependencies,
)
from backend.app.versions.v3.repair_projection import RepairInputOverflow, size_repair_input

PRODUCT_WRITING_INSTRUCTION = (
    "Product writing policy: Write newly authored itinerary titles, notes and explanations "
    "in English, including replacement prose in Repair. Preserve supplied proper names, "
    "place names, complete source addresses, quoted original user text, identifiers, source "
    "evidence and numeric/time facts verbatim. Do not translate or reinterpret constraints; "
    "do not add requirements."
)


class ProductEnglishClient:
    """Add a writing instruction to itinerary generation, never to extraction/evidence."""

    def __init__(self, client, *, config=None, tracer=None):
        self._client = client
        self._config, self._tracer = config or load_runtime_config(), tracer
        for name in ("generate_primary_structured", "generate_repair_structured"):
            if hasattr(client, name):
                setattr(
                    self,
                    name,
                    self._with_writing_policy(
                        getattr(client, name), primary=name == "generate_primary_structured"
                    ),
                )

    def _admit_primary(self, system_prompt, user_prompt, generation_config=None):
        limits = (
            generation_config if generation_config is not None else self._config.main_generation
        )
        if limits.enabled:
            counts = check_primary_input(system_prompt, user_prompt, limits)
            if self._tracer is not None:
                self._tracer.event("product_primary_generation_resources", counts)

    def _with_writing_policy(self, operation, *, primary):
        async def invoke(*, system_prompt, **kwargs):
            system_prompt += "\n" + PRODUCT_WRITING_INSTRUCTION
            if primary:
                self._admit_primary(
                    system_prompt, kwargs["user_prompt"], kwargs.get("generation_config")
                )
            else:
                _, counts = size_repair_input(
                    system_prompt, kwargs["user_prompt"], self._config.v3_repair
                )
                if self._tracer is not None:
                    self._tracer.event("product_repair_generation_resources", counts)
                if counts["total_tokens"] > counts["input_ceiling"]:
                    raise RepairInputOverflow(counts)
            return await operation(system_prompt=system_prompt, **kwargs)

        return invoke

    def __getattr__(self, name):
        return getattr(self._client, name)

    async def generate_structured(self, *, system_prompt, response_schema, **kwargs):
        if response_schema is V1Itinerary:
            system_prompt += "\n" + PRODUCT_WRITING_INSTRUCTION
            self._admit_primary(system_prompt, kwargs["user_prompt"])
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
            dependencies,
            llm=ProductEnglishClient(dependencies.llm, config=config, tracer=tracer),
            llm_identity=identity,
        )
