"""Saved synthetic native evaluation material for research CLI acceptance."""

import hashlib
import json

from backend.evaluation.intake import load_batch
from backend.evaluation.quality_report import build_quality_report
from backend.evaluation.v3_correspondence import read_v3_result_sources
from backend.evaluation.v3_pair_report import build_v3_pair_report
from backend.tests.evaluation.test_daily_density import density_reviews
from backend.tests.evaluation.test_quality_report import replay_evidence
from backend.tests.test_rtpeval_research_population_cli import save

STAMP = "2026-10-03T00:00:00Z"


def file_ref(root, path):
    value = json.loads(path.read_bytes())
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "media_type": "application/json",
        "availability": "available",
        **({"schema_version": value["schema_version"]} if "schema_version" in value else {}),
    }


def native_descriptor(root, case, kind):
    intake, identity, directory, context, reviews, coordinates, plan = case
    density = density_reviews(intake, "relaxed")
    options = dict(
        schedule_context=context,
        route_reviews=reviews,
        coordinate_evidence=coordinates,
        expected_plan=plan,
        density_reviews=density,
    )
    if kind == "quality":
        report = build_quality_report(
            intake, identity, directory, **options, generated_at=STAMP
        ).to_dict()
    else:
        report = build_v3_pair_report(
            intake,
            identity,
            directory,
            **options,
            result_sources=read_v3_result_sources(intake, root / "manifest.json"),
            generated_at=STAMP,
        ).to_dict()
    assert report["status"] == "complete", report["diagnostics"]
    return {
        "manifest_ref": file_ref(root, root / "manifest.json"),
        "report_ref": save(root, kind + "-report.json", report),
        "identity_ref": save(
            root,
            kind + "-identity.json",
            identity.to_dict() if hasattr(identity, "to_dict") else identity,
        ),
        **({"snapshot_ref": file_ref(root, directory / "manifest.json")} if directory else {}),
        **{
            name + "_ref": save(root, kind + "-" + name + ".json", value)
            for name, value in options.items()
            if value is not None
        },
    }


def declare_native(root, manifest, *, quality=(), pairs=(), mechanisms=(), controlled=None):
    runs = manifest["groups"][0]["selected_runs"]
    original = manifest["groups"][0]["input_ref"]
    population = {
        "schema_version": "rtpeval_research_population_1",
        "population_id": "p",
        "revision": "1",
        "cases": [
            {
                "case_id": "c",
                "revision": "1",
                "input_ref": original,
                "metadata": {},
                "planned_versions": list(runs),
                "repetition_ids": ["r"],
            }
        ],
    }
    profile = {
        "schema_version": "rtpeval_research_profile_1",
        "profile_id": "selection",
        "revision": "1",
        "population_id": "p",
        "population_revision": "1",
        "source_revision": "synthetic",
        "declared_at": "2026-10-01T00:00:00Z",
        "timing_basis": "prospective",
        "first_attempt_rule": "first_dispatched",
        "retry_rule": {"selection": "none", "scope": "slot"},
        "completion_policy_ref": "selected_workflow_1",
        "completion_mapping": {"completed": "completed"},
        "configurations": {v: save(root, v + "-config.json", {"version": v}) for v in runs},
    }
    attempts = []
    for v, run in runs.items():
        # The native fixture starts with an unavailable envelope; namespace remains explicit.
        usage = json.loads((root / run["usage_ref"]["path"]).read_bytes())
        assert usage["namespace"] == "planner"
        completion = {
            "declared_by": "fixture",
            "declared_at": "2026-10-02T00:00:00Z",
            "policy_ref": "selected_workflow_1",
            "workflow_status": "completed",
            "required_mechanisms": {
                "generation": "completed",
                **({"retrieval": "completed"} if v in ("v2", "v3") else {}),
                **({"validation": "completed", "repair": "not_applicable"} if v == "v3" else {}),
            },
        }
        attempts.append(
            {
                "case_id": "c",
                "case_revision": "1",
                "repetition_id": "r",
                "version": v,
                "attempt_id": "a-" + v,
                "run_id": run["run_id"],
                "group_id": "g",
                "order": 1,
                "prior_attempt_id": None,
                "dispatched": True,
                "dispatched_at": "2026-10-02T00:00:00Z",
                "reason_type": "completed",
                "execution_metadata": {},
                "input_sha256": original["sha256"],
                "configuration_sha256": profile["configurations"][v]["sha256"],
                "result_ref": run["result_ref"],
                "usage_ref": run["usage_ref"],
                "provenance_ref": run["provenance_ref"],
                "completion_ref": save(root, v + "-completion.json", completion),
            }
        )
    census = {
        "schema_version": "rtpeval_research_census_1",
        "population_id": "p",
        "population_revision": "1",
        "profile_id": "selection",
        "profile_revision": "1",
        "attempts": attempts,
    }
    material = {
        "schema_version": "rtpeval_research_repair_1",
        "population_id": "p",
        "population_revision": "1",
        "profile_id": "selection",
        "profile_revision": "1",
        "quality_reports": list(quality),
        "pair_reports": list(pairs),
        "mechanism_reports": list(mechanisms),
        "controlled": controlled,
    }
    declaration = {
        "schema_version": "rtpeval_research_declaration_1",
        "population_ref": save(root, "population.json", population),
        "profile_ref": save(root, "profile.json", profile),
        "census_ref": save(root, "census.json", census),
        "track_refs": {"repair": save(root, "repair-material.json", material)},
    }
    save(root, "research.json", declaration)
    return root / "research.json"


def prepare_namespaced_usage(batch):
    manifest, _, write, saver, root = batch
    for run in manifest["groups"][0]["selected_runs"].values():
        usage = json.loads((root / run["usage_ref"]["path"]).read_bytes())
        usage["namespace"] = "planner"
        run["usage_ref"] = saver(run["usage_ref"]["path"], usage, usage["schema_version"])
    write()


def final_case(case):
    # Reacquire only through the synthetic in-process transport to change paired scope.
    return replay_evidence(case)


def reload_intake(root):
    return load_batch(root / "manifest.json")
