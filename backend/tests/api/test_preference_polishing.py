"""Offline user-facing preference polish contract with fake model responses."""

import asyncio

import httpx
import pytest

from backend.app.api.input_assistance import get_polishing_service
from backend.app.llm.azure_foundry.polishing import PolishProviderBlocked
from backend.app.main import app
from backend.app.runtime.config_models import PreferencePolishingConfig
from backend.app.services.preference_polishing import PreferencePolishingService


class FakePolisher:
    def __init__(self, draft, review=None):
        self.draft_result = draft
        self.review_result = review
        self.calls = []

    async def draft(self, system_prompt, user_prompt, output_tokens):
        self.calls.append(("draft", output_tokens, user_prompt))
        return self.draft_result

    async def review(self, system_prompt, user_prompt, output_tokens):
        self.calls.append(("review", output_tokens, user_prompt))
        return self.review_result


def payload(text="I like climbing mountain, visiting a zoo, and a rich trip."):
    return {
        "original_text": text,
        "client_revision": "rev-1",
        "context": {
            "destination": "London",
            "start_date": "2026-10-01",
            "end_date": "2026-10-08",
            "traveler_count": 1,
            "budget": {"amount": "3000", "currency": "AUD"},
        },
    }


async def request(service, body):
    app.dependency_overrides[get_polishing_service] = lambda: service
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post("/api/input-assistance/preferences/polish", json=body)
    finally:
        app.dependency_overrides.pop(get_polishing_service, None)


def test_suggested_text_is_presented_after_one_call_without_changing_context():
    candidate = "I enjoy mountain climbing, would like to visit a zoo, and want a varied trip."
    fake = FakePolisher(
        {
            "status": "suggested",
            "suggested_text": candidate,
            "explanation": "Clarified the three wishes.",
            "questions": [],
        },
        {"verdict": "preserved", "reason": "All three wishes retain their original strength."},
    )
    result = asyncio.run(request(PreferencePolishingService(lambda: fake), payload()))
    assert result.status_code == 200
    assert result.json() == {
        "status": "suggested",
        "original_text": payload()["original_text"],
        "suggested_text": candidate,
        "explanation": "Clarified the three wishes.",
        "questions": [],
        "client_revision": "rev-1",
    }
    assert [call[0] for call in fake.calls] == ["draft"]
    assert [call[1] for call in fake.calls] == [2000]
    assert '"destination": "London"' in fake.calls[0][2]


def test_polish_preserves_exact_user_text_for_revision_and_span_ownership():
    original = "  Enjoy quiet parks.\n"
    candidate = "  Enjoy peaceful parks.\n"
    fake = FakePolisher({
        "status": "suggested", "suggested_text": candidate,
        "explanation": "Clarified wording.", "questions": [],
    })
    result = asyncio.run(request(PreferencePolishingService(lambda: fake), payload(original)))
    assert result.status_code == 200
    assert result.json()["original_text"] == original
    assert result.json()["suggested_text"] == candidate


def test_changed_number_is_presented_for_user_decision():
    fake = FakePolisher(
        {
            "status": "suggested",
            "suggested_text": "Visit the British Museum three times.",
            "explanation": "Improved clarity.",
            "questions": [],
        },
        {"verdict": "preserved", "reason": "Looks good."},
    )
    result = asyncio.run(
        request(
            PreferencePolishingService(lambda: fake),
            payload("Visit the British Museum exactly 2 times."),
        )
    )
    assert result.status_code == 200
    assert result.json()["status"] == "suggested"
    assert result.json()["suggested_text"] == fake.draft_result["suggested_text"]
    assert len(fake.calls) == 1


def test_date_and_currency_changes_are_presented_for_user_decision():
    fake = FakePolisher(
        {"status": "suggested", "suggested_text": "Visit on 2026-01-10 with 3000 usd.",
         "explanation": "Rephrased.", "questions": []},
        {"verdict": "preserved", "reason": "Looks unchanged."},
    )
    result = asyncio.run(request(
        PreferencePolishingService(lambda: fake), payload("Visit on 2026-10-01 with 3000 aud.")
    ))
    assert result.status_code == 200
    assert result.json()["status"] == "suggested"
    assert result.json()["suggested_text"] == fake.draft_result["suggested_text"]


def test_other_currency_changes_are_presented_for_user_decision():
    fake = FakePolisher(
        {"status": "suggested", "suggested_text": "Spend 3000 brl.",
         "explanation": "Rephrased.", "questions": []},
        {"verdict": "preserved", "reason": "Looks unchanged."},
    )
    result = asyncio.run(request(
        PreferencePolishingService(lambda: fake), payload("Spend 3000 mxn.")
    ))
    assert result.status_code == 200
    assert result.json()["status"] == "suggested"
    assert result.json()["suggested_text"] == fake.draft_result["suggested_text"]


def test_invalid_model_result_is_502_and_original_is_unmodified():
    fake = FakePolisher({"status": "needs_input", "suggested_text": None,
                         "explanation": "Clarify.", "questions": []})
    result = asyncio.run(request(PreferencePolishingService(lambda: fake), payload()))
    assert result.status_code == 502
    assert result.json()["error"]["code"] == "polish_invalid_response"
    assert result.json()["client_revision"] == "rev-1"


def test_cleanup_failure_does_not_override_result_or_hold_the_process_slot():
    class CleanupFailure(FakePolisher):
        async def aclose(self):
            raise RuntimeError("private cleanup detail")

    created = []

    def factory():
        fake = CleanupFailure({"status": "unchanged", "suggested_text": None,
                               "explanation": "Already clear.", "questions": []})
        created.append(fake)
        return fake

    service = PreferencePolishingService(factory)
    assert asyncio.run(request(service, payload())).status_code == 200
    assert asyncio.run(request(service, payload())).status_code == 200
    assert len(created) == 2


def test_invalid_or_oversized_assistance_input_makes_no_model_call():
    created = []
    service = PreferencePolishingService(lambda: created.append(True))
    result = asyncio.run(request(service, payload("x" * 4001)))
    assert result.status_code == 422
    assert created == []


@pytest.mark.parametrize(
    "original,candidate,verdict",
    [
        (
            "I like mountain climbing and want to visit a zoo.",
            "I would like to go indoor climbing and visit a zoo.",
            "changed",
        ),
        (
            "Do not visit zoos; visit the British Museum at least twice.",
            "Visit zoos and the British Museum exactly twice.",
            "changed",
        ),
        (
            "Wheelchair step-free access is mandatory; quiet mornings are optional.",
            "Step-free access and quiet mornings would be nice.",
            "changed",
        ),
        (
            "Exclude flights and hotels from our 3000 AUD budget.",
            "Our total budget is 3000 AUD including flights and hotels.",
            "changed",
        ),
        (
            "Visit the British Museum exactly twice on different dates.",
            "Visit the British Museum exactly twice on different dates.",
            "uncertain",
        ),
    ],
)
def test_candidate_is_presented_without_consulting_a_reviewer(
    original, candidate, verdict
):
    fake = FakePolisher(
        {
            "status": "suggested",
            "suggested_text": candidate,
            "explanation": "Rephrased the request.",
            "questions": [],
        },
        {"verdict": verdict, "reason": "Meaning cannot be confirmed."},
    )
    result = asyncio.run(request(PreferencePolishingService(lambda: fake), payload(original)))
    assert result.json()["status"] == "suggested"
    assert result.json()["suggested_text"] == fake.draft_result["suggested_text"]
    assert len(fake.calls) == 1


def test_conflicting_structured_context_returns_a_question_after_one_call():
    fake = FakePolisher(
        {
            "status": "needs_input",
            "suggested_text": None,
            "explanation": "The destination conflicts with the trip form.",
            "questions": ["Should the trip destination be London or Paris?"],
        }
    )
    result = asyncio.run(
        request(
            PreferencePolishingService(lambda: fake), payload("My trip is in Paris, not London.")
        )
    )
    assert result.json()["questions"] == ["Should the trip destination be London or Paris?"]
    assert [call[0] for call in fake.calls] == ["draft"]


def test_provider_block_is_sanitized_and_does_not_start_a_review():
    class Blocked(FakePolisher):
        async def draft(self, *args):
            self.calls.append(("draft",))
            raise PolishProviderBlocked("raw provider payload")

    fake = Blocked(None)
    result = asyncio.run(request(PreferencePolishingService(lambda: fake), payload()))
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "polishing_blocked"
    assert "raw provider payload" not in str(result.json())
    assert len(fake.calls) == 1


def test_local_daily_allowance_rejects_a_second_operation_before_model_construction():
    created = []

    def factory():
        created.append(True)
        return FakePolisher(
            {
                "status": "unchanged",
                "suggested_text": None,
                "explanation": "Already clear.",
                "questions": [],
            }
        )

    service = PreferencePolishingService(
        factory, PreferencePolishingConfig(daily_operations_per_process=1)
    )
    assert asyncio.run(request(service, payload())).status_code == 200
    assert asyncio.run(request(service, payload())).status_code == 429
    assert len(created) == 1
