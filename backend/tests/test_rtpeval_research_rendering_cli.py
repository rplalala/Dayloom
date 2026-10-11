"""Public CLI provenance rendering across filesystem volumes."""

import json
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from backend.tests.test_rtpeval_research_common_cli import TRACKS

pytest_plugins = ("backend.tests.test_rtpeval_research_population_cli",)


@pytest.mark.parametrize("track", TRACKS)
def test_cross_volume_provenance_uses_absolute_filesystem_links(
    installed_cli, research_material, tmp_path, track
):
    import os
    import shutil
    from tempfile import TemporaryDirectory

    alternate = os.environ.get("RTPEVAL_TEST_ALT_SOURCE_ROOT")
    if alternate is None:
        pytest.skip("A writable alternate-volume source root is not configured")
    alternate = Path(alternate).resolve()
    if alternate.drive.casefold() == tmp_path.drive.casefold():
        pytest.skip("Alternate source root must be on another filesystem volume")
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    declaration = research_material[-1](include_census=False)
    with TemporaryDirectory(prefix="rtpeval-provenance-", dir=alternate) as staging:
        root = Path(staging) / "source [review] #50%"
        shutil.copytree(research_material[0], root)
        directory = tmp_path / track
        result = installed_cli(
            "research",
            "report",
            root / declaration.name,
            "--track",
            track,
            "--directory",
            directory,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        value = json.loads((directory / (track + ".json")).read_bytes())
        markdown = (directory / (track + ".md")).read_text(encoding="utf-8")
        section = markdown.split("## Sources\n", 1)[1]
        targets = re.findall(r"\]\(([^)]+)\)", section)
        assert all(not target.startswith("file:") for target in targets)
        paths = {Path(unquote(target)) for target in targets}
        assert all(path.is_absolute() and path.is_file() for path in paths)
        assert paths == {(root / source["path"]).resolve() for source in value["source_bindings"]}
        assert "%23" in section and "%25" in section and "%5B" in section
