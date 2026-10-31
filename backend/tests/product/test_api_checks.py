"""Configuration probes use synthetic credentials and a socket-free HTTP transport."""

import json

import httpx
import pytest

from backend.app.product.api_checks import ApiChecker


def structured_response():
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": '{"ok": true}'},
                ],
            }
        ],
    }


def successful_provider(request):
    if request.url.host.endswith("azure.com"):
        return httpx.Response(200, json=structured_response())
    if request.url.path == "/v1/embeddings":
        return httpx.Response(
            200,
            json={
                "model": "text-embedding-3-small",
                "data": [
                    {"index": 0, "embedding": [0.001] * 1536},
                ],
            },
        )
    if request.url.path == "/v1/responses":
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {"type": "web_search_call", "status": "completed"},
                ],
            },
        )
    if request.url.path == "/v1/places:searchText":
        return httpx.Response(200, json={"places": [{"id": "sample_place"}]})
    if request.url.host == "routes.googleapis.com":
        return httpx.Response(
            200,
            json=[
                {
                    "originIndex": 0,
                    "destinationIndex": 0,
                    "status": {},
                    "condition": "ROUTE_EXISTS",
                    "duration": "60s",
                    "distanceMeters": 100,
                }
            ],
        )
    if request.url.path == "/v1/places/sample_place":
        return httpx.Response(
            200,
            json={
                "photos": [
                    {
                        "name": "places/sample_place/photos/sample_photo",
                    }
                ]
            },
        )
    if request.url.path.endswith("/media"):
        return httpx.Response(200, json={"photoUri": "https://lh3.googleusercontent.com/sample"})
    if request.url.host == "api.unsplash.com":
        return httpx.Response(
            200,
            json={
                "id": "7Zb7kUyQg1E",
                "urls": {"raw": "https://images.unsplash.com/sample"},
            },
        )
    raise AssertionError("Unexpected external request")


def test_foundry_checks_the_saved_deployment_with_one_bounded_structured_call(provider_values):
    import asyncio

    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=structured_response())

    checker = ApiChecker(transport=httpx.MockTransport(respond))
    result = asyncio.run(checker.check("foundry", provider_values))
    assert result["request_count"] == 1
    assert result["results"][0]["status"] == "passed"
    assert result["results"][0]["id"] == "foundry"
    assert str(requests[0].url) == "https://example.services.ai.azure.com/openai/v1/responses"
    payload = json.loads(requests[0].content)
    assert payload["model"] == "gpt-6-luna"
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["store"] is False
    assert 0 < payload["max_output_tokens"] <= 1024
    assert "synthetic-foundry" not in json.dumps(result)


def test_all_services_check_distinct_permissions_with_exactly_eight_requests(provider_values):
    import asyncio

    requests = []

    def respond(request):
        requests.append(request)
        return successful_provider(request)

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(respond)).check(
            "all",
            provider_values,
        )
    )
    assert result["request_count"] == len(requests) == 8
    assert [item["id"] for item in result["results"]] == [
        "foundry",
        "openai_embeddings",
        "openai_search",
        "google_places",
        "google_routes",
        "google_photos",
        "unsplash",
    ]
    assert all(item["status"] == "passed" for item in result["results"])
    search = json.loads(
        next(
            r.content
            for r in requests
            if r.url.host == "api.openai.com" and r.url.path == "/v1/responses"
        )
    )
    assert search["max_tool_calls"] == 1
    assert search["tool_choice"] == "required"
    assert all("synthetic-" not in str(request.url) for request in requests)
    assert "synthetic-" not in json.dumps(result)


@pytest.mark.parametrize(
    "service,expected", [("foundry", 1), ("openai", 2), ("google", 4), ("unsplash", 1)]
)
def test_service_buttons_only_send_their_own_requests(provider_values, service, expected):
    import asyncio

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(successful_provider)).check(
            service,
            provider_values,
        )
    )
    assert result["request_count"] == expected
    assert all(item["status"] == "passed" for item in result["results"])


@pytest.mark.parametrize(
    "http_status,error,status",
    [
        (401, {}, "authentication_failed"),
        (403, {"details": [{"reason": "SERVICE_DISABLED"}]}, "permission_denied"),
        (403, {"details": [{"reason": "BILLING_DISABLED"}]}, "billing_required"),
        (400, {"details": [{"reason": "API_KEY_INVALID"}]}, "authentication_failed"),
        (429, {"code": "insufficient_quota"}, "quota_exceeded"),
        (429, {"code": "rate_limit_exceeded"}, "rate_limited"),
        (
            429,
            {"status": "RESOURCE_EXHAUSTED", "details": [{"reason": "RATE_LIMIT_EXCEEDED"}]},
            "rate_limited",
        ),
        (404, {"code": "DeploymentNotFound"}, "not_found"),
        (503, {}, "provider_error"),
    ],
)
def test_provider_errors_are_classified_without_retries_or_secret_leaks(
    provider_values,
    http_status,
    error,
    status,
):
    import asyncio

    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            http_status,
            json={
                "error": {
                    **error,
                    "message": "synthetic-foundry private failure body",
                }
            },
        )

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(respond)).check(
            "foundry",
            provider_values,
        )
    )
    assert len(requests) == result["request_count"] == 1
    assert result["results"][0]["status"] == status
    assert "synthetic-foundry" not in json.dumps(result)
    assert "private failure" not in json.dumps(result)


def test_missing_credentials_skip_all_services_without_sends():
    import asyncio

    def forbidden(request):
        raise AssertionError("Missing credentials must never send")

    result = asyncio.run(ApiChecker(transport=httpx.MockTransport(forbidden)).check("all", {}))
    assert result["request_count"] == 0
    assert all(item["status"] == "not_configured" for item in result["results"])


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://untrusted.example/openai/v1",
        "https://user:synthetic-foundry@example.services.ai.azure.com/openai/v1",
    ],
)
def test_untrusted_foundry_endpoint_never_receives_a_credential(provider_values, endpoint):
    import asyncio

    def forbidden(request):
        raise AssertionError("Untrusted endpoint must never receive a request")

    provider_values["AZURE_OPENAI_ENDPOINT"] = endpoint
    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(forbidden)).check(
            "foundry",
            provider_values,
        )
    )
    assert result["request_count"] == 0
    assert result["results"][0]["status"] == "invalid_configuration"


@pytest.mark.parametrize(
    "failure,status", [(httpx.ConnectError, "network_error"), (httpx.ReadTimeout, "timeout")]
)
def test_network_failures_are_not_reported_as_bad_credentials(provider_values, failure, status):
    import asyncio

    def fail(request):
        raise failure("synthetic-foundry private transport error", request=request)

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(fail)).check(
            "foundry",
            provider_values,
        )
    )
    assert result["request_count"] == 1
    assert result["results"][0]["status"] == status
    assert "synthetic-foundry" not in json.dumps(result)


def test_redirects_are_not_followed(provider_values):
    import asyncio

    requests = []

    def redirect(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "https://untrusted.example/credential"})

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(redirect)).check(
            "foundry",
            provider_values,
        )
    )
    assert len(requests) == 1
    assert result["results"][0]["status"] == "provider_error"


def test_failed_places_lookup_does_not_hide_route_permission_result(provider_values):
    import asyncio

    def respond(request):
        if request.url.path == "/v1/places:searchText":
            return httpx.Response(403, json={"error": {"message": "private"}})
        return successful_provider(request)

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(respond)).check(
            "google",
            provider_values,
        )
    )
    assert result["request_count"] == 2
    assert [item["status"] for item in result["results"]] == [
        "permission_denied",
        "passed",
        "not_checked",
    ]


def test_response_size_is_bounded(provider_values):
    import asyncio

    result = asyncio.run(
        ApiChecker(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=b"x" * 140000)
            )
        ).check("foundry", provider_values)
    )
    assert result["results"][0]["status"] == "invalid_response"
    assert result["request_count"] == 1


def test_deadline_stops_remaining_sends(provider_values):
    import asyncio

    now = [0.0]

    def respond(request):
        now[0] = 61.0
        return successful_provider(request)

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(respond), clock=lambda: now[0]).check(
            "all",
            provider_values,
        )
    )
    assert result["request_count"] == 1
    assert all(item["status"] == "not_checked" for item in result["results"][1:])


def test_concurrent_checks_cannot_multiply_requests_and_cancellation_releases_slot(provider_values):
    import asyncio

    from backend.app.product.api_checks import CheckBusy

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def respond(request):
            entered.set()
            await release.wait()
            return successful_provider(request)

        checker = ApiChecker(transport=httpx.MockTransport(respond))
        first = asyncio.create_task(checker.check("foundry", provider_values))
        await entered.wait()
        with pytest.raises(CheckBusy):
            await checker.check("foundry", provider_values)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        release.set()
        assert (await checker.check("foundry", provider_values))["request_count"] == 1

    asyncio.run(scenario())


def test_an_in_flight_request_has_a_real_timeout(provider_values, monkeypatch):
    import asyncio

    from backend.app.product import api_checks

    monkeypatch.setattr(api_checks, "REQUEST_TIMEOUT_SECONDS", 0.01)

    async def slow(request):
        await asyncio.Event().wait()

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(slow)).check(
            "foundry",
            provider_values,
        )
    )
    assert result["request_count"] == 1
    assert result["results"][0]["status"] == "timeout"


def test_request_cap_remains_enforced_when_other_probes_are_pending(provider_values, monkeypatch):
    import asyncio

    from backend.app.product import api_checks

    monkeypatch.setattr(api_checks, "MAX_REQUESTS", 3)
    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(successful_provider)).check(
            "all",
            provider_values,
        )
    )
    assert result["request_count"] == 3
    assert all(item["status"] == "not_checked" for item in result["results"][3:])


def test_provider_photo_paths_cannot_choose_another_destination(provider_values):
    import asyncio

    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/v1/places/sample_place":
            return httpx.Response(
                200,
                json={
                    "photos": [
                        {
                            "name": "https://untrusted.example/private",
                        }
                    ]
                },
            )
        return successful_provider(request)

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(respond)).check(
            "google",
            provider_values,
        )
    )
    assert len(requests) == result["request_count"] == 3
    assert result["results"][-1]["status"] == "invalid_response"
    assert all(request.url.host.endswith("googleapis.com") for request in requests)


def test_missing_sample_photo_is_inconclusive_instead_of_bad_credentials(provider_values):
    import asyncio

    def respond(request):
        if request.url.path == "/v1/places/sample_place":
            return httpx.Response(200, json={})
        return successful_provider(request)

    result = asyncio.run(
        ApiChecker(transport=httpx.MockTransport(respond)).check(
            "google",
            provider_values,
        )
    )
    assert result["request_count"] == 3
    assert result["results"][-1]["status"] == "inconclusive"


def test_reflected_credentials_cannot_enter_request_urls_or_http_logs(provider_values, caplog):
    import asyncio
    import logging

    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/v1/places:searchText":
            return httpx.Response(200, json={"places": [{"id": "synthetic-google"}]})
        if request.url.path == "/v1/places/synthetic-google":
            return httpx.Response(200, json={})
        return successful_provider(request)

    with caplog.at_level(logging.INFO, logger="httpx"):
        result = asyncio.run(
            ApiChecker(transport=httpx.MockTransport(respond)).check(
                "google",
                provider_values,
            )
        )
    assert "synthetic-google" not in caplog.text
    assert all("synthetic-google" not in str(request.url) for request in requests)
    assert result["results"][-1]["status"] != "passed"
