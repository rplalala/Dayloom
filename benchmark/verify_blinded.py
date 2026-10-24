"""Verify the current blinded questionnaire, confirmed answers and mean ranks offline."""

import json
import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.evaluation.human_answers import validate_answers
from backend.evaluation.human_tasks import ACTIVITY_FIELDS, INPUT_FIELDS
from benchmark.verify_automatic import ROOT, digest, load, published_sha256

DIRECTORY = ROOT / "benchmark/blinded-results"
DATA = re.compile(r'(<script id="human-data" type="application/json">)(.*?)(</script>)', re.S)


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
    current_html = (DIRECTORY / "review.html").read_text("utf-8")
    current = presentation(current_html)
    assert binding["current"]["assessment_status"] == "completed"
    for key in ("presentation_id", "presentation_hash", "batch_revision"):
        assert current[key] == binding["current"][key]
    assert current["presentation_hash"] == digest(
        {k: v for k, v in current.items() if k != "presentation_hash"}
    )
    assert current["dimensions"] == ["preference", "pace", "usefulness"]
    assert [t["task_id"] for t in current["tasks"]] == [f"task-{i}" for i in range(1, 13)]
    mappings = []
    for number, task in enumerate(current["tasks"], 1):
        assert list(task["plans"]) == ["A", "B", "C", "D"]
        assert digest(task) == binding["current"]["task_semantic_sha256"][task["task_id"]]
        case = f"case-{number:02d}"
        request = load(f"benchmark/inputs/{case}.json")
        assert task["input"] == {k: request[k] for k in INPUT_FIELDS}
        selected = {
            digest(
                activity_signature(load(f"benchmark/{case}/generation/{v}/itinerary.json")["days"])
            ): v
            for v in ("v0", "v1", "v2", "v3")
        }
        assert len(selected) == 4
        labels = {
            label: selected[digest(activity_signature(plan["days"], True))]
            for label, plan in task["plans"].items()
        }
        assert len(set(labels.values())) == 4
        mappings.append({"task_id": task["task_id"], "group_id": case, "labels": labels})
    dictionaries = []
    for name in ("review.html", "review.zh-CN.html"):
        html = (DIRECTORY / name).read_text("utf-8")
        assert presentation(html) == current
        assert renderer(html) == renderer(current_html)
        assert re.findall(r"<style>(.*?)</style>", html, re.S) == re.findall(
            r"<style>(.*?)</style>", current_html, re.S
        )
        dictionaries.append(translations(html)[0])
    assert dictionaries[0] == dictionaries[1]
    for name in ("review.html", "review.zh-CN.html", "answers_human.json", "answers_6.1sol.json"):
        assert published_sha256(DIRECTORY / name) == binding["current"]["artifacts"][name]
    private = {
        "schema_version": "rtpeval_human_mapping_1",
        "public_sha256": digest(current),
        "tasks": mappings,
    }
    private["content_hash"] = digest(private)
    report = (DIRECTORY / "report.md").read_text("utf-8")
    rows = [
        [cell.strip().replace("**", "") for cell in line.strip("|").split("|")]
        for line in report.splitlines()
        if line.startswith("|")
    ]
    overall = {}
    for name in ("answers_human.json", "answers_6.1sol.json"):
        assert not (DIRECTORY / name.replace(".json", ".current.json")).exists()
        bundle = load(DIRECTORY / name)
        imported = validate_answers(current, private, [bundle])
        assert len(bundle["answers"]) == len(imported["effective"]) == 12
        sums = {
            v: {d: Fraction(0) for d in current["dimensions"]} for v in ("v0", "v1", "v2", "v3")
        }
        by_task = {m["task_id"]: m["labels"] for m in mappings}
        for answer in imported["effective"]:
            for dimension, response in answer["responses"].items():
                assert response["status"] == "ranked"
                position = 1
                for group in response["tie_groups"]:
                    rank = Fraction(2 * position + len(group) - 1, 2)
                    for label in group:
                        sums[by_task[answer["task_id"]][label]][dimension] += rank
                    position += len(group)
        reviewer = "Human" if "human" in name else "Model"
        overall[reviewer] = {}
        for version, totals in sums.items():
            means = [total / 12 for total in totals.values()]
            assert [reviewer, version.upper(), *[f"{float(n):.3f}" for n in means]] in rows
            overall[reviewer][version] = sum(means) / 3
    for version in overall["Human"]:
        assert [
            version.upper(),
            *[f"{float(overall[r][version]):.3f}" for r in ("Human", "Model")],
        ] in rows
    print(
        "Verified 12 current tasks, 48 selected plans, bilingual questionnaires, "
        "24 confirmed answers, published mean ranks and current source hashes."
    )


if __name__ == "__main__":
    verify()
