"""Offline generation resources and saved mechanism composition for suite cases."""

import hashlib
import json
from pathlib import Path

from .cost_report import build_cost_report
from .intake import _artifact, _constant, _float, _pairs, _read
from .mechanism_preparation import read_batch_sources
from .mechanism_report import report_mechanism
from .usage_report import compare_usage, summarize


def _track_inputs(configuration, fields, *, root, bindings):
    if not isinstance(configuration, dict) or set(configuration) - set(fields):
        raise ValueError("Unsupported generation/mechanism track configuration")
    values = {}
    for name, reference in configuration.items():
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("Explicit relative track source path required")
        relative = Path(reference)
        path = (root / relative).resolve()
        if relative.is_absolute() or relative.drive or not path.is_relative_to(root):
            raise ValueError("Track source path escapes declaration root")
        raw = path.read_bytes()
        values[name] = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_constant,
            parse_float=_float,
        )
        bindings[str(path)] = hashlib.sha256(raw).hexdigest()
    return values


def _generation_usage(sources):
    selected, comparable = [], []
    for source in sources:
        usage = source["usage"]
        summarize(usage)  # Malformed saved material is never hidden by scope exclusions.
        namespace = usage.get("namespace", "planner")
        frozen = any(
            value == "frozen_simulation"
            for value in (
                usage.get("scope"),
                usage.get("usage_scope"),
                usage.get("timing", {}).get("scope"),
            )
        )
        reason = namespace if namespace != "planner" else "frozen_simulation" if frozen else None
        if reason:
            comparable.append(
                {
                    **{
                        key: usage[key]
                        for key in (
                            "schema_version",
                            "group_id",
                            "run_id",
                            "version",
                            "result_sha256",
                        )
                    },
                    "namespace": "planner",
                    "collection_status": "unavailable",
                    "missing_fields": ["generation_usage_excluded:" + str(reason)],
                }
            )
        else:
            envelope = {"namespace": "planner", **usage}
            comparable.append(envelope)
            selected.append({**source, "usage": envelope})
    return selected, comparable


def _reports(case):
    try:
        sources, envelopes = _generation_usage(case["usage_sources"])
        resources = compare_usage(envelopes)
        pricing = case["pricing"]
        cost = (
            build_cost_report(
                sources,
                pricing["prices"],
                bills=pricing.get("bills"),
                annotations=pricing.get("annotations"),
            )
            if "prices" in pricing
            else {
                "schema_version": "rtpeval_suite_generation_cost_1",
                "status": "unavailable",
                "reason": "generation_prices_not_supplied",
                "report": None,
            }
        )
        return {
            "resources": resources,
            "cost": cost,
            "mechanism_preparation": case["mechanism_preparation"],
            "mechanism": report_mechanism(case["mechanism_preparation"]),
        }
    except (AttributeError, IndexError) as exc:
        raise ValueError("Malformed saved generation/mechanism material: " + str(exc)) from exc


def prepare_resources(cases, *, source_root):
    """Bind selected generation envelopes and render their native saved reports."""
    configuration = {"artifacts": {}, "source_bindings": {}, "resources": []}
    for index, (declaration, files, values, _intake) in enumerate(cases, 1):
        sources = []
        for run in values["manifest"]["groups"][0]["selected_runs"].values():
            usage, sha = _artifact(files["manifest"].parent, run["usage_ref"], "rtpeval_usage_1")
            sources.append({"sha256": sha, "usage": usage})
        pricing = _track_inputs(
            declaration.get("tracks", {}).get("resources", {}),
            ("prices", "bills", "annotations"),
            root=source_root,
            bindings=configuration["source_bindings"],
        )
        if ("bills" in pricing or "annotations" in pricing) and "prices" not in pricing:
            raise ValueError("Generation bills/annotations require explicit generation prices")
        mechanism = _track_inputs(
            declaration.get("tracks", {}).get("mechanism", {}),
            ("observations",),
            root=source_root,
            bindings=configuration["source_bindings"],
        )
        observations = mechanism.get("observations", {"records": []})
        if (
            not isinstance(observations, dict)
            or set(observations) != {"records"}
            or not isinstance(observations["records"], list)
        ):
            raise ValueError("Mechanism observations require explicit records array")
        case = {
            "case_id": declaration["case_id"],
            "usage_sources": sources,
            "pricing": pricing,
            "mechanism_preparation": read_batch_sources(
                files["manifest"], observations=observations["records"]
            ).to_dict(),
            "paths": {
                name: f"tracks/{index:04d}/{name}.json"
                for name in ("resources", "cost", "mechanism_preparation", "mechanism")
            },
        }
        reports = _reports(case)
        prepared = case["mechanism_preparation"]
        if (
            prepared["optional_diagnostics"]
            or any(
                channel["diagnostics"]
                for run in prepared["runs"]
                for channel in run["channels"].values()
            )
            or any(run["trace_diagnostics"] for run in reports["mechanism"]["runs"])
        ):
            raise ValueError("Supplied mechanism material requires correction")
        configuration["resources"].append(case)
        configuration["artifacts"].update(
            {case["paths"][name]: report for name, report in reports.items()}
        )
    return configuration


def _availability(values):
    observed = [value is not None for value in values]
    return (
        "available" if observed and all(observed) else "partial" if any(observed) else "unavailable"
    )


def compose_resources(preparation, directory, cases):
    """Verify deterministic native reports and index them independently of primary status."""
    configured = preparation["track_configuration"]["resources"]
    for row, case in zip(cases, configured, strict=True):
        if row["case_id"] != case["case_id"]:
            raise ValueError("Generation/mechanism case inventory mismatch")
        reports = _reports(case)
        for name, report in reports.items():
            if _read(directory / case["paths"][name])[0] != report:
                raise ValueError("Saved generation/mechanism report replay differs")
        row["tracks"]["resources"] = {
            "processing_status": "complete",
            "evidence_status": _availability(
                [
                    value
                    for group in reports["resources"]["groups"]
                    for run in group["runs"].values()
                    for value in run["metrics"].values()
                ]
            ),
            "applicability": "applicable",
            "report": case["paths"]["resources"],
            "cost_report": case["paths"]["cost"],
            "cost_status": _availability(
                [run["best_available_total"] for run in reports["cost"]["runs"]]
            )
            if "runs" in reports["cost"]
            else "unavailable",
        }
        mechanism = reports["mechanism"]
        v3 = next(run for run in mechanism["runs"] if run["version"] == "v3")
        coverage = v3["coverage"]
        if coverage == "unavailable" and v3["trace_coverage"] == "partial":
            coverage = "partial"
        row["tracks"]["mechanism"] = {
            "processing_status": mechanism["status"],
            "evidence_status": coverage,
            "applicability": "applicable",
            "report": case["paths"]["mechanism"],
            "preparation": case["paths"]["mechanism_preparation"],
            "trace_evidence_status": v3["trace_coverage"],
        }
    return cases
