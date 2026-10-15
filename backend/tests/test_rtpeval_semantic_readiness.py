"""Synthetic reviews exercise the real offline material and preparation boundaries."""

import json

import pytest

from backend.evaluation.evaluation_run import prepare_run
from backend.tests import test_rtpeval_finalize_cli as final_tests
from backend.tests.evaluation.test_evaluation_run import options, run_prices

handoff = final_tests.handoff
installed_cli = final_tests.installed_cli
collection = final_tests.collection

pytest_plugins = ("backend.tests.evaluation.test_intake",)


def ambiguous_activity(batch):
    _, results, write, _, _ = batch
    item = results["v1"]["itinerary"]["days"][0]["activities"][0]
    item.update(
        activity_kind="generic_activity",
        title="Synthetic neighbourhood exploration",
        place_name=None,
        notes="Synthetic ambiguous window; no semantic review was performed.",
    )
    return write("v1")


def test_missing_review_stops_preparation_before_acquisition(batch):
    manifest = ambiguous_activity(batch)
    directory = batch[4] / "evaluation"
    with pytest.raises(ValueError, match="missing_semantic_reviews"):
        prepare_run(manifest, directory, options=options(), prices=run_prices())
    assert not directory.exists()


def synthetic_reviews(batch):
    """Simulated independent decisions only; never adopted as actual case reviews."""
    manifest, _, write, save, root = batch
    write()
    from backend.evaluation.records import source as activity_source

    run = manifest["groups"][0]["selected_runs"]["v1"]
    source = activity_source(
        {
            "batch_id": manifest["batch_id"],
            "group_id": "g",
            "run_id": run["run_id"],
            "artifact_sha256": run["result_ref"]["sha256"],
        },
        "/itinerary/days/0/activities/0",
    )
    common = {
        "revision": "synthetic-1",
        "reviewer_ref": "synthetic-independent-reviewer-no-agent-run",
        "reviewed_at": "2026-10-15T01:00:00+00:00",
        "rationale": "Synthetic test decision; no actual semantic review was performed.",
    }
    roles = {
        "schema_version": "rtpeval_reviews_1",
        "batch_id": manifest["batch_id"],
        "records": [
            {
                **{k: source[k] for k in ("group_id", "run_id", "artifact_sha256", "pointer")},
                **common,
                "role": "transition",
            }
        ],
    }
    occupancy = {
        "schema_version": "rtpeval_occupancy_reviews_1",
        "batch_id": manifest["batch_id"],
        "revision": "synthetic-1",
        "records": [{"source": source, **common, "occupancy": "committed"}],
    }
    save("role-reviews.json", roles, roles["schema_version"])
    save("occupancy-reviews.json", occupancy, occupancy["schema_version"])
    return roles, occupancy


@pytest.mark.parametrize("review_entry", ["finalization", "collection"])
def test_cli_finalization_forwards_reviews_to_preparation(
    installed_cli, handoff, batch, review_entry
):
    _, write_handoff, save_collection, root = handoff
    ambiguous_activity(batch)
    roles, occupancy = synthetic_reviews(batch)
    # The collection fixture copies run refs, so update its selected runs explicitly.
    collection_config = save_collection()
    value = json.loads(collection_config.read_bytes())
    native = batch[0]["groups"][0]["selected_runs"]["v1"]
    value["groups"][0]["selected_runs"]["v1"].update(native)
    if review_entry == "collection":
        for field, name, envelope in (
            ("projection_reviews_ref", "role-reviews.json", roles),
            ("occupancy_reviews_ref", "occupancy-reviews.json", occupancy),
        ):
            value[field] = batch[3](name, envelope, envelope["schema_version"])
    collection_config.write_text(json.dumps(value), encoding="utf-8")
    stage, attached, final = root / "stage", root / "attached", root / "final"
    assert (
        installed_cli("batch", "collect", collection_config, "--directory", stage).returncode == 0
    )
    result = installed_cli(
        "batch",
        "attach-requirements",
        stage / "staging.json",
        write_handoff(),
        "--directory",
        attached,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    review_args = (
        [
            "--projection-reviews",
            root / "role-reviews.json",
            "--occupancy-reviews",
            root / "occupancy-reviews.json",
        ]
        if review_entry == "finalization"
        else []
    )
    result = installed_cli(
        "batch", "finalize", attached / "attachment.json", "--directory", final, *review_args
    )
    assert result.returncode == 0, result.stdout + result.stderr
    preparation = prepare_run(
        final / "manifest.json", root / "evaluation", options=options(), prices=run_prices()
    )
    assert preparation["semantic_readiness"]["status"] == "ready"
    assert preparation["context"]["occupancy_reviews"] == occupancy
    loaded = preparation["intake"]["inventory"][0]["runs"]["v1"]["final"]["activities"][0]
    assert loaded["review"] == roles["records"][0]
    assert loaded["original"]["notes"].startswith("Synthetic ambiguous")


def test_manifest_review_drift_is_rejected_before_execution(batch):
    import asyncio

    from backend.evaluation.evaluation_run import execute_run

    ambiguous_activity(batch)
    roles, occupancy = synthetic_reviews(batch)
    manifest = bind_reviews(batch, roles, occupancy)
    preparation = prepare_run(manifest, batch[4] / "ready", options=options(), prices=run_prices())
    review_path = batch[4] / "occupancy-reviews.json"
    review_path.write_bytes(review_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        asyncio.run(
            execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic",
                model_api_key="synthetic",
            )
        )
    assert not (batch[4] / "ready/execution").exists()


def test_non_primary_role_review_does_not_imply_flexible_occupancy(batch):
    ambiguous_activity(batch)
    batch[1]["v1"]["itinerary"]["days"][0]["activities"][0].pop("notes")
    batch[2]("v1")
    roles, _ = synthetic_reviews(batch)
    manifest = bind_reviews(batch, roles)
    from backend.cli.reviews import preflight

    report = preflight(manifest)
    assert report["missing_role_count"] == 0
    assert report["missing_occupancy_count"] == 1


@pytest.mark.parametrize(
    "wire", ["rtpeval_execution_preparation_1", "rtpeval_execution_preparation_2"]
)
def test_legacy_preparation_without_readiness_still_executes_and_replays_synthetic_material(
    batch, wire
):
    import asyncio

    import httpx

    from backend.evaluation.evaluation_run import execute_run, replay_run
    from backend.evaluation.records import canonical_digest
    from backend.tests.evaluation.test_evaluation_run import mock_provider

    directory = batch[4] / "legacy"
    preparation = prepare_run(batch[2](), directory, options=options(), prices=run_prices())
    # A synthetic legacy packet, not an edited original case/preparation.
    preparation.pop("semantic_readiness")
    preparation.pop("content_sha256")
    preparation["schema_version"] = wire
    preparation["content_sha256"] = canonical_digest(preparation)
    saved = (json.dumps(preparation) + "\n").encode()
    (directory / "preparation.json").write_bytes(saved)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
            return await execute_run(
                preparation,
                approved_sha256=preparation["content_sha256"],
                google_api_key="synthetic",
                model_api_key="synthetic",
                http_client=client,
            )

    report = asyncio.run(execute())
    assert report["processing_status"] == "complete"
    assert replay_run(directory) == report
    assert (directory / "preparation.json").read_bytes() == saved


def bind_reviews(batch, roles, occupancy=None):
    manifest, _, write, save, _ = batch
    manifest["projection_reviews_ref"] = save("role-reviews.json", roles, roles["schema_version"])
    if occupancy is not None:
        manifest["occupancy_reviews_ref"] = save(
            "occupancy-reviews.json", occupancy, occupancy["schema_version"]
        )
    return write()


def test_installed_preflight_reports_role_then_occupancy_and_one_step_stops(installed_cli, batch):
    manifest = ambiguous_activity(batch)
    result = installed_cli("batch", "preflight", manifest)
    assert result.returncode == 2, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["missing_role_count"] == report["awaiting_role_count"] == 1
    assert report["missing_occupancy_count"] == 0
    assert report["queue"][0]["source"]["pointer"] == "/itinerary/days/0/activities/0"
    roles, occupancy = synthetic_reviews(batch)
    bind_reviews(batch, roles)
    result = installed_cli("batch", "preflight", manifest)
    report = json.loads(result.stdout)
    assert report["missing_role_count"] == 0
    assert report["missing_occupancy_count"] == 1
    root = batch[4]
    for name, value in (("options", options()), ("prices", run_prices())):
        (root / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
    result = installed_cli(
        "evaluate",
        "execute",
        manifest,
        "--directory",
        root / "blocked",
        "--options",
        root / "options.json",
        "--prices",
        root / "prices.json",
        evaluation_offline=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_semantic_review"
    assert not (root / "blocked").exists()
    bind_reviews(batch, roles, occupancy)
    assert installed_cli("batch", "preflight", manifest).returncode == 0


@pytest.mark.parametrize(
    "role,occupancy",
    [
        ("unresolved", None),
        ("transition", "unresolved"),
        ("transition", "committed"),
        ("transition", "uncommitted"),
        ("primary_visit", "committed"),
    ],
)
def test_completed_reviews_allow_unknown_without_changing_original_activity(batch, role, occupancy):
    ambiguous_activity(batch)
    roles, envelope = synthetic_reviews(batch)
    roles["records"][0]["role"] = role
    if occupancy is None:
        envelope = None
    else:
        envelope["records"][0]["occupancy"] = occupancy
    manifest = bind_reviews(batch, roles, envelope)
    original = batch[1]["v1"]["itinerary"]["days"][0]["activities"][0].copy()
    preparation = prepare_run(manifest, batch[4] / "ready", options=options(), prices=run_prices())
    report = preparation["semantic_readiness"]
    assert report["status"] == "ready"
    assert report["reviewed_unresolved_count"] == int(
        role == "unresolved" or occupancy == "unresolved"
    )
    assert report["score_decidability"] == "not_assessed"
    assert (
        preparation["intake"]["inventory"][0]["runs"]["v1"]["final"]["activities"][0]["original"]
        == original
    )


@pytest.mark.parametrize(
    "fault",
    [
        "role_hash",
        "role_run",
        "role_pointer",
        "role_duplicate",
        "role_provenance",
        "role_time",
        "role_batch",
        "role_version",
        "occupancy_hash",
        "occupancy_run",
        "occupancy_pointer",
        "occupancy_duplicate",
        "occupancy_provenance",
        "occupancy_revision",
        "occupancy_conflict",
        "primary_uncommitted",
        "occupancy_batch",
    ],
)
def test_wrong_review_material_is_rejected_without_preparation(batch, fault):
    ambiguous_activity(batch)
    roles, occupancy = synthetic_reviews(batch)
    role_record, occupancy_record = roles["records"][0], occupancy["records"][0]
    if fault.startswith("role_"):
        field = fault.removeprefix("role_")
        if field in ("hash", "run", "pointer"):
            role_record[
                {"hash": "artifact_sha256", "run": "run_id", "pointer": "pointer"}[field]
            ] = "wrong"
        elif field == "duplicate":
            roles["records"].append(role_record.copy())
        elif field == "provenance":
            role_record.pop("rationale")
        elif field == "time":
            role_record["reviewed_at"] = "2026-10-15T01:00:00"
        elif field == "batch":
            roles["batch_id"] = "wrong"
        elif field == "version":
            role_record["version"] = "v0"
    elif fault in ("occupancy_hash", "occupancy_run", "occupancy_pointer"):
        occupancy_record["source"][
            {
                "occupancy_hash": "artifact_sha256",
                "occupancy_run": "run_id",
                "occupancy_pointer": "pointer",
            }[fault]
        ] = "wrong"
    elif fault == "occupancy_duplicate":
        occupancy["records"].append(occupancy_record.copy())
    elif fault == "occupancy_provenance":
        occupancy_record.pop("reviewer_ref")
    elif fault == "occupancy_revision":
        occupancy.pop("revision")
    elif fault == "primary_uncommitted":
        role_record["role"] = "primary_visit"
        occupancy_record["occupancy"] = "uncommitted"
    elif fault == "occupancy_batch":
        occupancy["batch_id"] = "wrong"
    manifest = bind_reviews(batch, roles, occupancy)
    supplied = None
    if fault == "occupancy_conflict":
        import copy

        supplied = copy.deepcopy(occupancy)
        supplied["records"][0]["occupancy"] = "uncommitted"
    with pytest.raises(ValueError):
        prepare_run(
            manifest,
            batch[4] / "rejected",
            options=options(),
            prices=run_prices(),
            occupancy_reviews=supplied,
        )
    assert not (batch[4] / "rejected").exists()


@pytest.mark.parametrize(
    "kind,title,place,notes,expected",
    [
        ("free_time", "Free time", None, None, "ready"),
        ("generic_activity", "Free time", None, None, "ready"),
        ("generic_activity", "Unfamiliar activity prose", "Named Museum", None, "ready"),
        ("generic_activity", "Free time", None, "Fixed appointment", "needs_semantic_review"),
        ("generic_activity", "A named-looking story", None, None, "needs_semantic_review"),
    ],
)
def test_preflight_uses_existing_structured_rules_without_prose_guessing(
    batch, kind, title, place, notes, expected
):
    _, results, write, _, _ = batch
    activity = results["v1"]["itinerary"]["days"][0]["activities"][0]
    activity.update(activity_kind=kind, title=title, place_name=place, notes=notes)
    manifest = write("v1")
    from backend.cli.reviews import preflight

    assert preflight(manifest)["status"] == expected


@pytest.mark.parametrize(
    "start,end",
    [("invalid", "invalid"), ("2020-01-01T12:00:00+00:00", "2020-01-01T11:00:00+00:00")],
)
def test_review_completion_does_not_fix_invalid_submitted_times(batch, start, end):
    ambiguous_activity(batch)
    activity = batch[1]["v1"]["itinerary"]["days"][0]["activities"][0]
    activity.update(start_time=start, end_time=end)
    batch[2]("v1")
    roles, occupancy = synthetic_reviews(batch)
    manifest = bind_reviews(batch, roles, occupancy)
    preparation = prepare_run(manifest, batch[4] / "ready", options=options(), prices=run_prices())
    projection = preparation["intake"]["inventory"][0]["runs"]["v1"]["final"]
    from backend.evaluation.occupancy import prepare_occupancy

    units = prepare_occupancy(projection, [], reviews=occupancy["records"]).to_dict()["commitments"]
    fixed = next(u for u in units if u["kind"] == "fixed_generic")
    assert not fixed["time_complete"]
    assert preparation["semantic_readiness"]["status"] == "ready"
