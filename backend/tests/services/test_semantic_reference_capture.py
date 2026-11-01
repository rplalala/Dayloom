"""Controlled responses exercise provenance rejection, not model accuracy."""

import asyncio

import pytest

from backend.app.schemas.poi_semantics import SemanticAssessmentError
from backend.tests.services.test_poi_semantics import Model, service
from backend.tests.versions.v3.test_validation import contract, place
from tools.validation.poi_semantics_acceptance import CapturedSemantics


def test_development_capture_redacts_and_reports_cap(tmp_path):
    from types import SimpleNamespace

    errors = []
    client = CapturedSemantics(
        SimpleNamespace(_capture_secrets=("secret-value",)), tmp_path, {}, errors
    )
    client.capture_poi_semantics("input", {"call_id": "one", "input": "secret-value"})
    saved = next(tmp_path.glob("*.json")).read_text()
    assert "secret-value" not in saved and "[REDACTED]" in saved
    client.remaining_bytes = 1
    client.capture_poi_semantics("output", {"call_id": "one", "output": "large"})
    assert errors == ["semantic_capture_limit"]
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_match_failure_has_bounded_details_and_prevalidation_capture():
    def mutate(rows):
        rows[0]["matches"] = [
            dict(requirement_id="named_1", relation="supported", evidence_refs=["e02"])
        ]

    model = Model(mutate)
    captured = []
    model.capture_poi_semantics = lambda stage, payload: captured.append((stage, payload))
    svc = service(model)
    with pytest.raises(SemanticAssessmentError) as error:
        asyncio.run(svc.assess([place("a"), place("b")], contract("REQUIRED")))
    assert error.value.details["place_id"] == "p01"
    assert error.value.details["offending_refs"] == ["e02"]
    assert [stage for stage, _ in captured] == ["input", "output", "outcome"] * 2
    assert len({p["call_id"] for _, p in captured}) == 2
    assert captured[1][1]["output"]["assessments"][0]["matches"][0]["evidence_refs"] == ["e02"]
    assert captured[-1][1]["error_details"] == error.value.details
    assert svc.calls == 2 and not svc.ledger and svc.failed


@pytest.mark.parametrize(
    "refs,relation,message",
    [
        (["e01"], "supported", None),
        (["e02"], "supported", "Invalid match evidence references"),
        (["named_1"], "supported", "Invalid match evidence references"),
        (["places:a.primary_type"], "supported", "Invalid match evidence references"),
        ([], "supported", "Supported match requires input evidence"),
        ([], "unresolved", None),
    ],
)
def test_sdk_reference_boundary_and_capture(tmp_path, refs, relation, message):
    import json

    import httpx2 as httpx

    from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
    from backend.tests.llm.azure_foundry.test_requirement_acceptance_harness import response

    rows = []
    for pid in ("a", "b"):
        rows.append(
            dict(
                candidate_ref="p01" if pid == "a" else "p02",
                visit_object=pid,
                role="attraction",
                categories=["museum"],
                reason="Supplied facts",
                evidence_refs=["e01" if pid == "a" else "e02"],
                matches=[dict(requirement_id="named_1", relation=relation, evidence_refs=refs)]
                if pid == "a"
                else [],
                exception_requirement_ids=[],
            )
        )
    sends = []

    def handler(request):
        sends.append(json.loads(request.content))
        return httpx.Response(200, json=response(json.dumps({"assessments": rows}), 1))

    async def exercise():
        client = AzureFoundryStructuredLLMClient(
            endpoint="https://fixture.invalid/openai/v1",
            deployment="fixture-model",
            api_key="fixture-secret",
            http_async_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        errors = []
        svc = service(CapturedSemantics(client, tmp_path, {"case_id": "fixture"}, errors))
        try:
            if message:
                with pytest.raises(SemanticAssessmentError, match=message):
                    await svc.assess([place("a"), place("b")], contract("REQUIRED"))
                assert not svc.cache and not svc.ledger
                with pytest.raises(SemanticAssessmentError, match="already failed"):
                    await svc.assess([place("a")], contract("REQUIRED"))
            else:
                assert len(await svc.assess([place("a"), place("b")], contract("REQUIRED"))) == 2
            assert not errors
        finally:
            await client.aclose()

    asyncio.run(exercise())
    records = [json.loads(f.read_text()) for f in tmp_path.glob("*.json")]
    assert {r["validation_stage"] for r in records} == {
        "semantic_input",
        "semantic_output",
        "semantic_outcome",
    }
    assert len({r["call_id"] for r in records}) == (2 if message else 1)
    assert len({r["input_sha256"] for r in records}) == (2 if message else 1)
    assert all(r["prompt_version"] == "poi_semantics_prompt_7" for r in records)
    assert len(sends) == (2 if message else 1)
    assert "copy only the exact source_ref" in json.dumps(sends[0])


@pytest.mark.parametrize("failure", ["return_none", "raise"])
def test_capture_write_failure_does_not_change_rejection(tmp_path, monkeypatch, failure):
    def mutate(rows):
        rows[0]["matches"] = [
            dict(requirement_id="named_1", relation="supported", evidence_refs=["wrong"])
        ]

    errors = []
    wrapper = CapturedSemantics(Model(mutate), tmp_path, {}, errors)

    def fail(*args, **kwargs):
        if failure == "raise":
            raise OSError("Fixture failure")
        return None

    monkeypatch.setattr(wrapper.capture, "record", fail)
    svc = service(wrapper)
    with pytest.raises(SemanticAssessmentError, match="Invalid match evidence references"):
        asyncio.run(svc.assess([place()], contract("REQUIRED")))
    assert errors and svc.calls == 2 and not svc.ledger


def test_reference_details_are_bounded():
    def mutate(rows):
        rows[0]["matches"] = [
            dict(requirement_id="named_1", relation="unresolved", evidence_refs=["x" * 2000] * 8)
        ]

    svc = service(Model(mutate))
    with pytest.raises(SemanticAssessmentError) as caught:
        asyncio.run(svc.assess([place()], contract("REQUIRED")))
    assert caught.value.details["truncated"]
    assert len(caught.value.details["offending_refs"]) == 8
    assert all(len(ref) == 256 for ref in caught.value.details["offending_refs"])


def test_acceptance_semantic_capture_is_default_off_and_reports_initialization_failure(
    tmp_path, monkeypatch
):
    import tools.validation.poi_semantics_acceptance as entry
    from backend.tests.llm.azure_foundry.test_poi_semantics_acceptance import setup_case
    from tools.validation.poi_semantics_acceptance import run_case

    request, _, _ = setup_case(tmp_path, monkeypatch)
    result = run_case(request, tmp_path / "off", reference_date="2026-09-26")
    assert result["semantic_capture_status"] == "disabled"
    assert not (tmp_path / "off" / "semantics").exists()

    def fail(*args, **kwargs):
        raise OSError("Fixture init failure")

    monkeypatch.setattr(entry, "DevelopmentRequirementCapture", fail)
    result = run_case(
        request, tmp_path / "failed", capture_semantics=True, reference_date="2026-09-26"
    )
    assert result["application_exit_code"] == 2
    assert result["semantic_capture_status"] == "incomplete"
    assert result["acceptance_status"] == "evidence_incomplete"


def test_prompt_fingerprint_matches_capture_and_cache_reassesses_new_prompt(monkeypatch):
    import hashlib

    import backend.app.services.poi_semantics as module

    svc = service()
    asyncio.run(svc.assess([place()], contract()))
    first = svc.snapshot()["prompt_sha256"]
    monkeypatch.setattr(
        module, "POI_SEMANTICS_PROMPT", module.POI_SEMANTICS_PROMPT + "\nChanged instructions."
    )
    asyncio.run(svc.assess([place()], contract()))
    assert svc.calls == 2
    assert first != svc.snapshot()["prompt_sha256"]
    assert (
        svc.records[-1]["prompt_sha256"]
        == hashlib.sha256(module.POI_SEMANTICS_PROMPT.encode()).hexdigest()
    )


def test_partial_write_failures_cannot_bypass_case_cap(tmp_path, monkeypatch):
    import os
    from types import SimpleNamespace

    original = os.fdopen

    class PartialWrite:
        def __init__(self, *args, **kwargs):
            self.stream = original(*args, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def write(self, content):
            self.stream.write(content[: len(content) // 2])
            self.stream.flush()
            raise OSError("Simulated partial disk write")

    errors = []
    wrapper = CapturedSemantics(SimpleNamespace(), tmp_path, {}, errors)
    monkeypatch.setattr(os, "fdopen", PartialWrite)
    for _ in range(12):
        wrapper.capture_poi_semantics("output", {"call_id": "fixture", "output": "x" * 900000})
    assert sum(p.stat().st_size for p in tmp_path.glob("*.json")) <= 4 * 1024 * 1024
    assert "semantic_capture_limit" in errors


@pytest.mark.parametrize("failure", ["citation", "identity", "exception"])
def test_sdk_corrected_response_is_accepted_with_linked_capture(tmp_path, failure):
    import json

    import httpx2 as httpx

    from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
    from backend.tests.llm.azure_foundry.test_requirement_acceptance_harness import response

    sends = []

    def handler(request):
        sends.append(json.loads(request.content))
        row = dict(
            candidate_ref="p01",
            visit_object="Museum",
            role="attraction",
            categories=["museum"],
            reason="Supplied evidence",
            evidence_refs=["wrong" if len(sends) == 1 else "e01"],
            matches=[],
            exception_requirement_ids=[],
        )
        if len(sends) == 1 and failure != "citation":
            row["evidence_refs"] = ["e01"]
            if failure == "identity":
                row["candidate_ref"] = "invented"
            else:
                row.update(role="exception_only", exception_requirement_ids=["invented"])
        return httpx.Response(200, json=response(json.dumps({"assessments": [row]}), 1))

    errors = []

    async def run():
        client = AzureFoundryStructuredLLMClient(
            endpoint="https://fixture.invalid/openai/v1",
            deployment="fixture-model",
            api_key="fixture-secret",
            http_async_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        try:
            svc = service(CapturedSemantics(client, tmp_path, {}, errors))
            assert (await svc.prepare([place()], contract()))["a"].main_eligible
            assert (await svc.prepare([place()], contract()))["a"].main_eligible
            assert svc.calls == 2
        finally:
            await client.aclose()

    asyncio.run(run())
    assert len(sends) == 2 and errors == []
    records = [json.loads(p.read_text()) for p in tmp_path.glob("*.json")]
    outcomes = [r for r in records if r["validation_stage"] == "semantic_outcome"]
    failed = next(r for r in outcomes if r["status"] == "failed")
    accepted = next(r for r in outcomes if r["status"] == "accepted")
    assert accepted["correction_of"] == failed["call_id"]
    assert "contract_correction" in json.dumps(sends[1])
