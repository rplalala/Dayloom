"""Verify content-only blinded display synchronization without network access."""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.evaluation.human_tasks import ACTIVITY_FIELDS, INPUT_FIELDS
from benchmark.verify_automatic import ROOT, digest, load, published_sha256

DIRECTORY = ROOT / "benchmark/blinded-results"
DATA = re.compile(r'(<script id="human-data" type="application/json">)(.*?)(</script>)', re.S)


def historical(revision, name):
    return subprocess.check_output(
        ["git", "show", f"{revision}:benchmark/blinded-results/{name}"], cwd=ROOT
    )


def presentation(html):
    return json.loads(DATA.search(html)[2])


def translations(html):
    marker = "translations:"
    start = html.index(marker) + len(marker)
    if html.startswith("JSON.parse(`", start):
        end = html.index("`)", start) + 2
        value = json.loads(html[start + len("JSON.parse(`") : end - 2])
    else:
        value, length = json.JSONDecoder().raw_decode(html[start:])
        end = start + length
    return value, start, end


def renderer(html):
    """Compare executable behavior after removing only translated content."""
    scripts = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", html, re.S)
    javascript = scripts[-1].replace("\r\n", "\n")
    _, start, end = translations(javascript)
    return javascript[:start] + "CONTENT" + javascript[end:]


def activity_signature(days, displayed=False):
    return [
        {
            "date": day["date"],
            "activities": [
                item["fields"] if displayed else {k: item[k] for k in ACTIVITY_FIELDS}
                for item in day["items" if displayed else "activities"]
                if (
                    item["kind"] == "activity"
                    if displayed
                    else item["activity_kind"] != "transport"
                )
            ],
        }
        for day in days
    ]


def verify():
    binding = load(DIRECTORY / "source-binding.json")
    assessed = binding["assessed"]
    for name, expected in assessed["artifacts"].items():
        assert hashlib.sha256(historical(assessed["git_revision"], name)).hexdigest() == expected
    old_html = historical(assessed["git_revision"], "review.html").decode("utf-8")
    old = presentation(old_html)
    current_html = (DIRECTORY / "review.html").read_text("utf-8")
    current = presentation(current_html)
    assert old["presentation_hash"] == assessed["presentation_hash"]
    assert current["presentation_hash"] == binding["current"]["presentation_hash"]
    for package in (old, current):
        assert package["presentation_hash"] == digest(
            {k: v for k, v in package.items() if k != "presentation_hash"}
        )
        assert package["dimensions"] == ["preference", "pace", "usefulness"]
        assert len(package["tasks"]) == 12
    assert current["presentation_id"] != old["presentation_id"]
    assert current["presentation_hash"] != old["presentation_hash"]
    assert current["batch_revision"] == 2
    for before, after in zip(old["tasks"], current["tasks"], strict=True):
        assert before["task_id"] == after["task_id"]
        assert list(after["plans"]) == ["A", "B", "C", "D"]
        assert digest(after) == binding["current"]["task_semantic_sha256"][after["task_id"]]
        if after["task_id"] != "task-4":
            assert after == before
    task = current["tasks"][3]
    request = load("benchmark/inputs/case-04.json")
    assert task["input"] == {k: request[k] for k in INPUT_FIELDS}
    selected = [
        load(f"benchmark/case-04/generation/{v}/itinerary.json") for v in ("v0", "v1", "v2", "v3")
    ]
    expected = {digest(activity_signature(itinerary["days"])) for itinerary in selected}
    actual = {digest(activity_signature(plan["days"], True)) for plan in task["plans"].values()}
    assert len(expected) == 4 and actual == expected
    dictionaries = []
    for name in ("review.html", "review.zh-CN.html"):
        html = (DIRECTORY / name).read_text("utf-8")
        previous = historical(assessed["git_revision"], name).decode("utf-8").replace("\r\n", "\n")
        assert presentation(html) == current
        assert renderer(html) == renderer(previous)
        assert re.findall(r"<style>(.*?)</style>", html, re.S) == re.findall(
            r"<style>(.*?)</style>", previous, re.S
        )
        dictionary = translations(html)[0]
        assert all(dictionary[k] == v for k, v in translations(previous)[0].items())
        dictionaries.append(dictionary)
        assert published_sha256(DIRECTORY / name) == binding["current"]["artifacts"][name]
    assert dictionaries[0] == dictionaries[1]
    for name in ("answers_human.json", "answers_6.1sol.json"):
        original = historical(assessed["git_revision"], name)
        assert (DIRECTORY / name).read_bytes() == original
        answers = json.loads(original)["answers"]
        assert len(answers) == 12
        for answer in answers:
            for key in (
                "batch_id",
                "batch_revision",
                "presentation_id",
                "presentation_hash",
                "rater_ref",
            ):
                assert answer[key] == old[key]
            assert answer["state"] == "submitted"
            assert set(answer["responses"]) == set(old["dimensions"])
    previous_report = historical(assessed["git_revision"], "report.md").decode("utf-8")
    current_report = (DIRECTORY / "report.md").read_text("utf-8")

    def tables(text):
        return [line for line in text.splitlines() if line.startswith("|")]

    assert tables(previous_report) == tables(current_report)
    print(
        "Verified 12 tasks, four selected plans, bilingual content, "
        "unchanged renderer/ranking rules, "
        "24 original answers, all result tables and distinct source bindings."
    )


if __name__ == "__main__":
    verify()
