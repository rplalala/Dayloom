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
    destination = DestinationSuggestionService(GeoDBClient(transport=httpx.MockTransport(geodb)))
    polish = PreferencePolishingService(EditorPolisher)
    application.dependency_overrides[get_destination_service] = lambda: destination
    application.dependency_overrides[get_polishing_service] = lambda: polish
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
