"""Public offline CLI corrections shared by every research report track."""

import json
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from backend.tests.test_rtpeval_research_population_cli import save

pytest_plugins = ("backend.tests.test_rtpeval_research_population_cli",)

TRACKS = ("population", "opportunities", "repair", "tradeoffs")


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
