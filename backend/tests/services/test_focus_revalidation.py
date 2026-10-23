"""The follow-up launcher cannot reopen the exhausted three-case batch."""

from types import SimpleNamespace

import pytest

from tools.validation import focus_revalidation
from tools.validation import landmark_pilot as pilot


def test_followup_has_isolated_single_attempt_and_matching_child(tmp_path, monkeypatch):
    original_main = pilot.main
    original_output = pilot.OUTPUT
    for name in ("CASES", "OUTPUT", "CHILD_MODULE"):
        monkeypatch.setattr(pilot, name, getattr(pilot, name))
    monkeypatch.setattr(pilot, "main", lambda: None)
    focus_revalidation.main()
    assert pilot.CASES == ("focus_melbourne_v3",)
    assert pilot.OUTPUT != original_output
    assert pilot.OUTPUT.name == "focus_revalidation_20260928"
    monkeypatch.setattr(pilot, "main", original_main)
    monkeypatch.setattr(pilot, "OUTPUT", tmp_path / "followup")
    monkeypatch.setattr(pilot, "local_dependencies", lambda: None)
    monkeypatch.setattr(pilot, "source_hashes", lambda: {"fixture": "frozen"})
    monkeypatch.setattr(pilot, "today_and_validate", lambda: "2026-09-28")
    pilot.prepare()
    head = pilot.read(pilot.OUTPUT / "manifest.json")["git_head"]
    monkeypatch.setattr(pilot.subprocess, "check_output", lambda *a, **kw: head)
    (tmp_path / ".env").touch()
    monkeypatch.setattr(pilot, "ROOT", tmp_path)

    def launch(command, **kwargs):
        assert command[3] == "tools.validation.focus_revalidation"
        assert kwargs["timeout"] == 660
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(pilot.subprocess, "run", launch)
    assert pilot.execute("focus_melbourne_v3") == 0
    with pytest.raises(FileExistsError):
        pilot.execute("focus_melbourne_v3")
    with pytest.raises(ValueError, match="Unknown case"):
        pilot.preflight("ordinary_sydney_v3")
