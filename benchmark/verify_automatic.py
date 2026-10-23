"""Verify published automatic arithmetic and source-linked material, without network.

Run from the repository root: python benchmark/verify_automatic.py
Native provider receipts remain in private evidence and have separate replay commands.
"""

import hashlib
import json
import sys
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def published_sha256(path):
    """Hash published LF text, independent of Windows checkout conversion.

    This applies only to public JSON/Markdown projections. Native private source
    and acquisition hashes continue to identify their exact original bytes.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@lru_cache(None)
def raw(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dereference(value, source):
    while isinstance(value, dict) and set(value) == {"$case_material_ref"}:
        ref = value["$case_material_ref"]
        case = next(p for p in source.parents if p.name.startswith("case-"))
        candidates = {
            p.resolve() for p in (source.parent / ref["path"], case / ref["path"]) if p.is_file()
        }
        assert len(candidates) == 1, (source, ref)
        source = candidates.pop()
        assert source.is_relative_to(case.resolve())
        value = node(str(source), ref.get("pointer", ref.get("json_pointer", "")))
        expected = ref.get("expanded_semantic_sha256", ref.get("semantic_sha256"))
        assert digest(value) == expected, (source, ref)
    return value, source


@lru_cache(None)
def node(path, pointer=""):
    source, value = Path(path), raw(path)
    for key in pointer.lstrip("/").split("/") if pointer else []:
        value, source = dereference(value, source)
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return expand(value, source)


def expand(value, source):
    value, source = dereference(value, source)
    if isinstance(value, dict):
        return {key: expand(item, source) for key, item in value.items()}
    if isinstance(value, list):
        return [expand(item, source) for item in value]
    return value


def load(path):
    return node(str((ROOT / path).resolve()))


def exact(total):
    fraction = total["exact_fraction"]
    return Fraction(fraction["numerator"], fraction["denominator"])


def verify_score(case, material, input_source=None):
    from backend.evaluation.daily_density import apply_density_penalty, score_daily_density

    density = material["daily_density"]
    policy = {
        "rules_profile_id": "rtpeval_daily_density_3",
        "default": None,
        "days": {day["date"]: day["policy"] for day in density["days"]},
        "review": density["review"],
    }
    rebuilt = score_daily_density(
        {"input": load("benchmark/" + (input_source or f"inputs/{case}.json"))},
        density["days"],
        policy,
    )
    assert rebuilt == density, (case, "density")
    scored = {"daily_density": rebuilt, "auxiliary_total": material["auxiliary_total"]}
    apply_density_penalty(scored)
    assert scored["overall_total"] == material["overall_total"], (case, "overall")


def verify_reader_sizes(value, base):
    """Check published reader sizes where an index records them."""
    if isinstance(value, dict):
        if value.get("path") == "report.md" and "bytes" in value:
            assert len((base / "report.md").read_bytes().replace(b"\r\n", b"\n")) == value["bytes"]
        for key, child in value.items():
            if key not in ("source", "sources", "native_source", "original_source"):
                verify_reader_sizes(child, base)
    elif isinstance(value, list):
        for child in value:
            verify_reader_sizes(child, base)


def main():
    report = load("benchmark/automatic-results.json")
    assert report["content_sha256"] == digest(
        {key: value for key, value in report.items() if key != "content_sha256"}
    )
    scores, ranks = {}, {}
    pair_counts = Counter()
    for case in report["cases"]:
        cid = case["case_id"]
        input_source = case.get("input_source")
        if input_source:
            assert published_sha256(ROOT / "benchmark" / input_source) == case["input_file_sha256"]
        final = load("benchmark/" + case["primary_source"])
        pair = load("benchmark/" + case["pair_source"])
        case_index = load(f"benchmark/{cid}/material-index.json")
        verify_reader_sizes(case_index, ROOT / "benchmark" / cid)
        for kind in ("final", "pair"):
            binding = case_index.get("density_policy_derivations", {}).get(kind)
            if binding:
                assert (
                    published_sha256(ROOT / "benchmark" / cid / binding["path"])
                    == binding["sha256"]
                )
        for value in (final, pair):
            if "content_sha256" in value:
                assert value["content_sha256"] == digest(
                    {k: v for k, v in value.items() if k != "content_sha256"}
                )
            source = value.get("source", {})
            if source.get("public_path"):
                assert published_sha256(ROOT / source["public_path"]) == source["file_sha256"]
        final = final.get("quality", final)["groups"][0]
        pair = pair["groups"][0]
        scores[cid], ranks[cid] = {}, {}
        for version, material in final["versions"].items():
            verify_score(cid, material, input_source)
            score = exact(material["overall_total"]) * 100
            assert score == exact({"exact_fraction": case["versions"][version]["score"]})
            assert material["daily_density"] == case["versions"][version]["daily_density"]
            assert material["dimensions"] == case["versions"][version]["dimensions"]
            scores[cid][version] = score
        for version, score in scores[cid].items():
            rank = 1 + sum(s > score for s in scores[cid].values())
            rank += Fraction(sum(s == score for s in scores[cid].values()) - 1, 2)
            assert rank == exact({"exact_fraction": case["versions"][version]["rank"]})
            ranks[cid][version] = rank
        for stage, material in pair["stages"].items():
            verify_score(cid, material, input_source)
            key = "final" if stage == "final_primary" else stage
            assert exact(material["overall_total"]) * 100 == exact(
                {"exact_fraction": case["pair"][key]}
            )
        delta = exact(pair["stages"]["final_primary"]["overall_total"]) - exact(
            pair["stages"]["draft"]["overall_total"]
        )
        pair_counts["improved" if delta > 0 else "worsened" if delta < 0 else "unchanged"] += 1
        for name in ("removed", "added", "replaced"):
            pair_counts[name] += pair["visit_changes"][name + "_count"]
    assert all(pair_counts[key] == value for key, value in report["paired_summary"].items())
    for version, aggregate in report["summary"].items():
        assert sum(s[version] for s in scores.values()) / 12 == exact(
            {"exact_fraction": aggregate["mean_score"]}
        )
        assert sum(r[version] for r in ranks.values()) / 12 == exact(
            {"exact_fraction": aggregate["mean_rank"]}
        )
        rows = [r for r in report["selected_generation"] if r["version"] == version]
        assert len(rows) == 12 and len({r["run_id"] for r in rows}) == 12
        resources = aggregate["resources"]
        assert sum(Decimal(r["reference_usd"]) for r in rows) == Decimal(
            resources["reference_total_usd"]
        )
        assert median(Decimal(r["reference_usd"]) for r in rows) == Decimal(
            resources["median_reference_usd"]
        )
        assert median(r["elapsed_seconds"] for r in rows) == resources["median_elapsed_seconds"]
        for metric, total in resources["totals"].items():
            values = [r["metrics"][metric] for r in rows]
            assert total == (sum(values) if all(v is not None for v in values) else None)
        for row in rows:
            assert sum(row["metrics"]["provider_sends"].values()) == row["metrics"]["http_sends"]
    base = ROOT / "benchmark/case-04"
    index = load("benchmark/case-04/material-index.json")
    for entry in index["entries"]:
        path = base / entry["path"]
        assert published_sha256(path) == entry["sha256"], path
        assert digest(load(path)) == entry["expanded_semantic_sha256"], path
    for entry in index["reader_views"]:
        assert published_sha256(base / entry["path"]) == entry["sha256"]
    ledger = load("benchmark/case-04/analysis/resources/all-attempt-resources.json")
    keys = [
        tuple(event[k] for k in ("namespace", "run_id", "kind", "provider", "event_id"))
        for event in ledger["events"]
    ]
    assert len(keys) == len(set(keys)) == ledger["event_count"]
    assert (
        sum(e["reference_usd"] is None for e in ledger["events"])
        == ledger["unpriced_or_conflicting_events"]
    )
    assert sum(
        Decimal(e["reference_usd"]) for e in ledger["events"] if e["reference_usd"] is not None
    ) == Decimal(ledger["reference_observed_subtotal_usd"])
    print(
        "Verified 48 finals, 24 paired stages, exact ranks, 48 resource rows, "
        "and case-04 index/event identities."
    )


if __name__ == "__main__":
    main()
