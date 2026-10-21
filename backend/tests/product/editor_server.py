"""Browser acceptance factory: real application; replacements only at external adapters."""

import json

import httpx

from backend.app.api.input_assistance import get_destination_service, get_polishing_service
from backend.app.integrations.geodb.client import GeoDBClient
from backend.app.main import create_app
from backend.app.services.destination_suggestions import DestinationSuggestionService
from backend.app.services.preference_polishing import PreferencePolishingService


class EditorPolisher:
    async def draft(self, system_prompt, user_prompt, output_tokens):
        original = json.loads(user_prompt)["original_text"]
        return {
            "status": "suggested",
            "suggested_text": original.replace("quiet parks", "peaceful parks").replace(
                "time to rest", "unhurried breaks"
            ),
            "explanation": "Clarified the wording while preserving your preferences.",
            "questions": [],
        }


def geodb(request):
    if request.url.params["namePrefix"].startswith("Unavailable"):
        return httpx.Response(503)
    return httpx.Response(
        200,
        json={
            "data": [
                {
                    "id": 1,
                    "name": "Kyoto",
                    "region": "Kyoto Prefecture",
                    "country": "Japan",
                    "countryCode": "JP",
                }
            ]
        },
    )


def create_editor_app():
    application = create_app()
    from backend.tests.product.media_fakes import replace_media
    replace_media(application)
    destination = DestinationSuggestionService(GeoDBClient(transport=httpx.MockTransport(geodb)))
    polish = PreferencePolishingService(EditorPolisher)
    application.dependency_overrides[get_destination_service] = lambda: destination
    application.dependency_overrides[get_polishing_service] = lambda: polish
    # Later generation-enabled editors must still never reach paid providers here.
    from contextlib import asynccontextmanager

    from backend.app.api.dependencies import get_date_provider, get_planning_service
    from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
    from backend.app.services.planning import PlanningService
    from backend.app.versions.v3 import runner
    from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
    from backend.tests.versions.v2.test_v2_runner import Places
    from backend.tests.versions.v3.test_wiring import OwnedRetrieval

    class UnconfiguredBrowserModel:
        async def generate_structured(self, **kwargs):
            raise RuntimeError("The editor-only browser fixture has no generation response")

    @asynccontextmanager
    async def dependencies(*args):
        yield PlannerDependencies(
            UnconfiguredBrowserModel(), Places(), FakeWeatherProvider(), FakeRoutesProvider()
        )

    runner.RuntimeRetrieval = lambda config: OwnedRetrieval()
    planning = PlanningService(
        RequestPlannerRuntime(dependency_factory=dependencies), get_date_provider()
    )
    application.dependency_overrides[get_planning_service] = lambda: planning
    return application


if __name__ == "__main__":
    import argparse
    import asyncio

    import uvicorn

    from scripts.run_api import create_api_loop

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    arguments = parser.parse_args()
    server = uvicorn.Server(
        uvicorn.Config(
            create_editor_app(),
            host="127.0.0.1",
            port=arguments.port,
        )
    )
    asyncio.run(server.serve(), loop_factory=create_api_loop)
