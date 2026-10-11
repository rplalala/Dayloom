"""Public offline CLI corrections shared by every research report track."""

import json
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from backend.tests.test_rtpeval_research_population_cli import save

pytest_plugins = ("backend.tests.test_rtpeval_research_population_cli",)

TRACKS = ("population", "opportunities", "relevance", "repair", "tradeoffs")


@pytest.mark.parametrize("track", TRACKS)
def test_provenance_links_resolve_from_markdown_location_with_reserved_filenames(
    installed_cli, research_material, tmp_path, track
):
    root, population, _, _, write = research_material
    population["cases"] = population["cases"][:1]
    population["cases"][0]["input_ref"] = save(
        root, "inputs/input [review] #50% (original).json", {"destination": "Sydney"}
    )
    declaration = write(include_census=False)
    directory = tmp_path / "reports with spaces" / track
    result = installed_cli(
        "research", "report", declaration, "--track", track, "--directory", directory
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((directory / (track + ".json")).read_bytes())
    markdown = (directory / (track + ".md")).read_text(encoding="utf-8")
    assert markdown.count("## Sources\n") == 1
    section = markdown.split("## Sources\n", 1)[1]
    links = re.findall(r"\]\(([^)]+)\)", section)
    assert len(links) == len(report["source_bindings"])
    expected = {str((root / source["path"]).resolve()) for source in report["source_bindings"]}
    actual = {str((directory / unquote(target)).resolve()) for target in links}
    assert actual == expected
    assert all(Path(path).is_file() for path in actual)
    assert "%23" in section and "%25" in section and "%28" in section and "%5B" in section
    assert "input \\[review\\]" in section
    # Rendering at another depth changes only Markdown destinations.
    other = tmp_path / "other"
    second = installed_cli(
        "research", "report", declaration, "--track", track, "--directory", other
    )
    assert second.returncode == 0, second.stdout + second.stderr
    assert json.loads((other / (track + ".json")).read_bytes()) == report


@pytest.mark.parametrize("track", TRACKS)
@pytest.mark.parametrize(
    "fault", ["collection_status", "model_calls", "completed_failed_usage", "coverage"]
)
def test_supplied_usage_is_consistently_validated_before_track_selection(
    installed_cli, research_material, track, fault
):
    from backend.tests.test_rtpeval_research_tradeoffs_cli import usage_attempt

    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt, usage = usage_attempt(research_material, "v1")
    if fault == "collection_status":
        usage["collection_status"] = "invented"
    elif fault == "model_calls":
        usage["model_calls"] = {}
    elif fault == "coverage":
        usage["coverage"] = []
    else:
        usage["outcome"] = "failed"
    attempt["usage_ref"] = save(research_material[0], "usage-invalid.json", usage)
    result = installed_cli("research", "validate", research_material[-1](), "--track", track)
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"


@pytest.mark.parametrize("track", TRACKS)
@pytest.mark.parametrize("kind", ["unavailable", "failed_workflow_completed_capture"])
def test_common_usage_validation_retains_native_unavailable_and_failure_capture(
    installed_cli, research_material, track, kind
):
    from backend.tests.test_rtpeval_research_tradeoffs_cli import usage_attempt

    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt, usage = usage_attempt(
        research_material,
        "v1",
        "required_mechanism_failed" if kind == "failed_workflow_completed_capture" else "completed",
    )
    if kind == "unavailable":
        usage["collection_status"] = "unavailable"
        for field in (
            "outcome",
            "model_calls",
            "provider_events",
            "cache_events",
            "coverage",
            "timing",
            "repair_summary",
        ):
            usage.pop(field, None)
    else:
        usage["outcome"] = "completed"
    attempt["usage_ref"] = save(research_material[0], "native-valid-usage.json", usage)
    result = installed_cli("research", "validate", research_material[-1](), "--track", track)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("track", TRACKS)
def test_undispatched_unavailable_placeholder_is_preserved_without_consumption(
    installed_cli, research_material, tmp_path, track
):
    from backend.tests.test_rtpeval_research_population_cli import add_attempt

    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt = add_attempt(research_material, 0, "v1", "not_started", dispatched=False)
    attempt["group_id"] = "g"
    usage = {
        "schema_version": "rtpeval_usage_1",
        "namespace": "planner",
        "group_id": "g",
        "version": "v1",
        "run_id": attempt["run_id"],
        "result_sha256": None,
        "collection_status": "unavailable",
        "outcome": "unavailable",
        "model_calls": [],
        "provider_events": [],
        "cache_events": [],
        "timing": {"scope": "selected_invocation_through_cleanup", "elapsed_seconds": None},
        "repair_summary": {"model_event_ids": [], "provider_event_ids": [], "observed_rounds": 0},
    }
    attempt["usage_ref"] = save(research_material[0], "unstarted-usage.json", usage)
    directory = tmp_path / track
    result = installed_cli(
        "research", "report", research_material[-1](), "--track", track, "--directory", directory
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((directory / (track + ".json")).read_bytes())
    assert any(source["path"] == "unstarted-usage.json" for source in report["source_bindings"])
    if track == "population":
        assert report["slots"][1]["status"] == "unstarted"
    if track == "tradeoffs":
        assert report["all_attempts"]["dispatched_attempts"] == 0
        assert report["all_attempts"]["rows"] == []


@pytest.mark.parametrize("track", TRACKS)
@pytest.mark.parametrize(
    "observation",
    ["model_calls", "provider_events", "cache_events", "timing", "repair", "stage", "outcome"],
)
def test_undispatched_attempt_rejects_actual_generation_usage(
    installed_cli, research_material, track, observation
):
    from backend.tests.test_rtpeval_research_population_cli import add_attempt
    from backend.tests.test_rtpeval_research_tradeoffs_cli import usage_attempt

    research_material[1]["cases"] = research_material[1]["cases"][:1]
    _, observed = usage_attempt(research_material, "v1")
    research_material[3]["attempts"].clear()
    attempt = add_attempt(research_material, 0, "v1", "not_started", dispatched=False)
    attempt["group_id"] = "g"
    usage = {
        "schema_version": "rtpeval_usage_1",
        "namespace": "planner",
        "group_id": "g",
        "version": "v1",
        "run_id": attempt["run_id"],
        "result_sha256": None,
        "collection_status": "unavailable",
    }
    if observation in ("model_calls", "provider_events"):
        usage[observation] = observed[observation]
    elif observation == "cache_events":
        usage[observation] = [
            {"event_id": "cache-1", "operation": "cache_read", "outcome": "cache_lookup_miss"}
        ]
    elif observation == "timing":
        usage["timing"] = {"elapsed_seconds": 0}
    elif observation == "repair":
        usage["repair_summary"] = {"observed_rounds": 1}
    elif observation == "stage":
        usage["stage_summaries"] = [{"stage": "generation", "elapsed_seconds": 0}]
    else:
        usage["outcome"] = "completed"
    attempt["usage_ref"] = save(research_material[0], "unstarted-observed-usage.json", usage)
    result = installed_cli("research", "validate", research_material[-1](), "--track", track)
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
