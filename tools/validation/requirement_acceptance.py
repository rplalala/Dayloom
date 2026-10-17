"""Reusable frozen acceptance runner; live execution always requires separate authorization."""

import argparse
import asyncio
import hashlib
import json
import time
from datetime import date
from importlib.metadata import version
from pathlib import Path

from backend.app.llm.azure_foundry.client import requirement_wire_format
from backend.app.runtime.fingerprints import digest
from backend.app.schemas.interpreted_requirements import (
    CONTRACT_VERSION,
    ClarificationRequired,
    InterpretedTripRequirements,
)
from backend.app.schemas.request import PlanningRequest
from backend.app.services.preference_interpretation import (
    interpret_preferences,
    validate_planning_request,
)
from backend.app.services.preference_prompts import PREFERENCE_INTERPRETATION_SYSTEM_PROMPT
from backend.app.versions.v0.config import V0Settings


def write_once(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2, default=str)


def implementation_hashes():
    paths = [
        *Path("backend/app").rglob("*.py"),
        Path(__file__),
        Path(__file__).with_name("runtime_acceptance.py"),
        Path("config/runtime.yaml"),
    ]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def boundary_identity(client):
    from backend.app.llm.azure_foundry.requirement_profiles import (
        CURRENT_REQUIREMENT_PROFILE,
        requirement_profile,
    )

    profile = requirement_profile(CURRENT_REQUIREMENT_PROFILE)

    return {
        "prompt_hash": digest(profile.project_prompt(PREFERENCE_INTERPRETATION_SYSTEM_PROMPT)),
        "prompt_version": profile.prompt_version,
        "wire_hash": digest(requirement_wire_format(profile=profile)),
        "contract_version": CONTRACT_VERSION,
        "canonical_schema_hash": digest(InterpretedTripRequirements.model_json_schema()),
        "configuration": client._requirement_config,
        "configuration_hash": digest(client._requirement_config),
        "endpoint_hash": digest(str(client._chat_model.root_async_client.base_url)),
        "implementation_hashes": implementation_hashes(),
        "dependencies": {
            name: version(name)
            for name in ("openai", "langchain-openai", "langchain-core", "httpx", "httpx2")
        },
        "model_defaults": client._chat_model._default_params,
        "sdk_timeout": str(client._chat_model.root_async_client.timeout),
        "sdk_retries": client._chat_model.root_async_client.max_retries,
    }


def freeze_matrix(source, output, client):
    cases = source["cases"]
    assert 1 <= len(cases) <= 10 and len({c["case_id"] for c in cases}) == len(cases)
    for case in cases:
        assert case["case_id"].isascii() and case["case_id"].isidentifier()
        assert case["expected_outcome"] and case["checks"]
        assert case.get("engine", "shared") in ("shared", "v0", "v1")
        validate_planning_request(case["request"], date.fromisoformat(source["reference_date"]))
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        **source,
        "boundary": boundary_identity(client),
        "case_input_hashes": {c["case_id"]: digest(c["request"]) for c in cases},
        "scenario_limit": len(cases),
        "automatic_retries": 0,
    }
    write_once(output / "manifest.json", manifest)
    write_once(output / "manifest_hash.json", {"sha256": digest(manifest)})
    write_once(output / "wire_schema.json", requirement_wire_format(current=True))
    return manifest


async def run_matrix(manifest, output, client=None, *, session=None, providers=None):
    """Run frozen cases once through real runners; resource ownership is session-scoped.

    A legacy caller-supplied client is borrowed, never closed. CLI and new tests use
    an explicit owned AcceptanceSession. Provider objects are borrowed injections.
    """
    from backend.app.versions.v0.runner import run_v0
    from backend.app.versions.v1.runner import run_v1
    from tools.validation.runtime_acceptance import (
        AcceptanceSession,
        SharedDependencyFailure,
        failure_kind,
    )

    if session is None:
        async with AcceptanceSession(client=client, directory=output) as borrowed:
            return await run_matrix(manifest, output, session=borrowed, providers=providers)
    client = session.client
    assert digest(manifest) == json.loads((output / "manifest_hash.json").read_text())["sha256"]
    assert boundary_identity(client) == manifest["boundary"]
    assert not (
        list(output.glob("*/invocation_started.json")) or list(output.glob("*/result.json"))
    ), "Never repeat a historical spent matrix"
    write_once(output / "execution_started.json", {"session_id": session.session_id})
    outcomes = []
    reference = date.fromisoformat(manifest["reference_date"])
    for case in manifest["cases"]:
        result = {"case_id": case["case_id"], "engine": case.get("engine", "shared")}
        if session.broken or session.capture_errors:
            result.update(outcome="unexecuted", reason=session.broken or "capture_unhealthy")
            outcomes.append(result)
            continue
        started = time.monotonic()
        calls_before = len(session.calls)
        try:
            session.begin_case(case["case_id"])
            assert boundary_identity(client) == manifest["boundary"]
            request = PlanningRequest.model_validate(case["request"])
            if result["engine"] == "v0":
                value = await run_v0(request, session, reference_date=reference)
            elif result["engine"] == "v1":
                if providers is None:
                    raise SharedDependencyFailure("Explicit V1 provider injections are required")
                value = await run_v1(request, session, reference_date=reference, **providers)
            elif result["engine"] == "shared":
                value = await interpret_preferences(request, reference, session)
            else:
                raise ValueError("Unknown acceptance engine")
            result.update(outcome="completed", value=value.model_dump(mode="json"))
        except ClarificationRequired as exc:
            result.update(outcome="clarification", code=exc.code)
        except Exception as exc:
            category = failure_kind(exc, session)
            result.update(outcome=category, error=type(exc).__name__)
            if category in ("shared_dependency_failure", "provider_failure"):
                session.broken = category
        result.update(
            elapsed_seconds=time.monotonic() - started,
            client_invocations=len(session.calls) - calls_before,
        )
        outcomes.append(result)
        session.save_result(result)
    session.record("matrix_outcomes", outcomes)
    return outcomes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "execute"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cases", type=Path)
    args = parser.parse_args()
    from tools.validation.runtime_acceptance import AcceptanceSession

    async def execute():
        async with AcceptanceSession(settings=V0Settings(), directory=args.output) as session:
            if args.action == "freeze":
                source = json.loads(args.cases.read_text(encoding="utf-8"))
                manifest = freeze_matrix(source, args.output, session.client)
                print(json.dumps({"manifest_hash": digest(manifest)}))
            else:
                manifest = json.loads((args.output / "manifest.json").read_text(encoding="utf-8"))
                outcomes = await run_matrix(manifest, args.output, session=session)
                print(json.dumps({"outcomes": outcomes, "capture_health": session.capture_errors}))

    asyncio.run(execute())


if __name__ == "__main__":
    main()
