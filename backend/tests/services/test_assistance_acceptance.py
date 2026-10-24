"""Acceptance assistance stays available beyond shared development daily quotas."""

import asyncio

import pytest

from backend.app.runtime.config_loader import load_runtime_profile
from backend.app.schemas.input_assistance import PolishRequest
from backend.app.services.destination_suggestions import DestinationSuggestionService
from backend.app.services.preference_polishing import (
    PolishingRateLimited,
    PreferencePolishingService,
)
from backend.tests.api.test_preference_polishing import FakePolisher, payload


def test_acceptance_assistance_has_no_small_process_daily_cutoff():
    async def scenario():
        clock = [0.0]
        config = load_runtime_profile("acceptance").input_assistance

        class Places:
            async def search(self, *args, **kwargs):
                return []

        destinations = DestinationSuggestionService(
            Places(), config.destination, now=lambda: clock[0]
        )
        polisher = FakePolisher(
            {
                "status": "unchanged",
                "suggested_text": None,
                "explanation": "Already clear.",
                "questions": [],
            }
        )
        polishing = PreferencePolishingService(
            lambda: polisher, config.polishing, now=lambda: clock[0]
        )
        for _ in range(105):
            clock[0] += 3
            assert await destinations.suggest("Paris", actor="user:one") == []
            result = await polishing.polish(
                PolishRequest.model_validate(payload()), actor="user:one"
            )
            assert result.original_text == payload()["original_text"]
        assert len(polisher.calls) == 105

    asyncio.run(scenario())


def test_polishing_per_user_and_provider_concurrency_release_on_cancellation():
    async def scenario():
        entered = asyncio.Queue()
        release = asyncio.Event()

        class WaitingPolisher:
            async def draft(self, *args):
                await entered.put(True)
                await release.wait()
                return {
                    "status": "unchanged",
                    "suggested_text": None,
                    "explanation": "Clear.",
                    "questions": [],
                }

        clock = [0.0]
        service = PreferencePolishingService(
            WaitingPolisher,
            load_runtime_profile("acceptance").input_assistance.polishing,
            now=lambda: clock[0],
        )
        request = PolishRequest.model_validate(payload())
        tasks = []
        for actor in ("a", "b", "c", "d"):
            tasks.append(asyncio.create_task(service.polish(request, actor=actor)))
            await entered.get()
        for actor in ("a", "e"):
            with pytest.raises(PolishingRateLimited):
                await service.polish(request, actor=actor)
        tasks[0].cancel()
        with pytest.raises(asyncio.CancelledError):
            await tasks[0]
        tasks.append(asyncio.create_task(service.polish(request, actor="e")))
        await entered.get()
        release.set()
        await asyncio.gather(*tasks[1:])
        with pytest.raises(PolishingRateLimited):
            await service.polish(request, actor="e")
        clock[0] = 3
        assert (await service.polish(request, actor="e")).status == "unchanged"

    asyncio.run(scenario())
