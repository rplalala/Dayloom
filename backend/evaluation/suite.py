"""Source-bound sequential composition of native evaluation runs."""

import base64
import hashlib
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .evaluation_run import prepare_run
from .intake import _read, load_batch
from .records import canonical_digest
from .snapshot import _bytes
from .suite_selection import CaseSelection
from .suite_tracks import prepare_tracks

PREPARATION_VERSION = "rtpeval_suite_preparation_1"
REPORT_VERSION = "rtpeval_suite_report_1"
INPUT_FILES = (
    "manifest",
    "options",
    "prices",
    "context",
    "occupancy_reviews",
    "route_reviews",
    "density_reviews",
)


def _save(root, name, value):
    (root / name).write_bytes(_bytes(value))


def _money(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise ValueError("Explicit decimal USD allowance required")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Invalid reference allowance") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Positive finite reference allowance required")
    return amount


def _source(root, name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Explicit relative source path required")
    relative = Path(name)
    path = (root / relative).resolve()
    if relative.is_absolute() or relative.drive or not path.is_relative_to(root):
        raise ValueError("Suite source path escapes declaration root")
    return path


def prepare_suite(declaration, directory):
    """Validate the entire selection offline and prepare fresh native packages."""
    source = Path(declaration).resolve()
    supplied, digest = _read(source)
    allowed = {"schema_version", "suite_id", "max_cost_usd", "cases", "tracks"}
    if set(supplied) - allowed or supplied.get("schema_version") != "rtpeval_suite_1":
        raise ValueError("Unsupported suite declaration schema or fields")
    if not isinstance(supplied.get("suite_id"), str) or not supplied["suite_id"].strip():
        raise ValueError("Explicit suite_id required")
    allowance = _money(supplied.get("max_cost_usd"))
    cases = supplied.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Ordered nonempty case selection required")
    root = Path(directory).resolve()
    if root.exists():
        raise FileExistsError("Fresh suite directory required")
    if source.is_relative_to(root):
        raise ValueError("Suite outputs cannot contain selected sources")
    bindings = {str(source): digest}
    names, revisions, run_ids = set(), set(), set()
    resolved = []
    reserved = Decimal(0)
    for case in cases:
        required = {"case_id", "revision", "manifest", "options", "prices"}
        if (
            not isinstance(case, dict)
            or not required <= case.keys()
            or set(case) - set(INPUT_FILES) - {"case_id", "revision", "tracks"}
        ):
            raise ValueError("Explicit case identity, revision and native configuration required")
        name = case["case_id"]
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError("Duplicate or missing case identity")
        names.add(name)
        files = {key: _source(source.parent, case[key]) for key in INPUT_FILES if key in case}
        if any(path.is_relative_to(root) for path in files.values()):
            raise ValueError("Suite output overlaps selected sources")
        values = {}
        for key, path in files.items():
            value, sha = _read(path)
            bindings[str(path)] = sha
            values[key] = value
        intake = load_batch(files["manifest"]).to_dict()
        if intake["status"] != "accepted" or len(intake["inventory"]) != 1:
            raise ValueError("Each case requires one accepted four-version group")
        if case["revision"] != intake["revision"]:
            raise ValueError("Declared case revision differs from accepted source")
        revision = (intake["batch_id"], intake["revision"], intake["inventory"][0]["group_id"])
        if revision in revisions:
            raise ValueError("Duplicate selected case revision")
        revisions.add(revision)
        for run in intake["inventory"][0]["runs"].values():
            if run["final"]["context"]["run_id"] in run_ids:
                raise ValueError("Duplicate selected run identity across cases")
            run_ids.add(run["final"]["context"]["run_id"])
        reserved += _money(values["options"].get("max_cost_usd"))
        resolved.append(CaseSelection(case, intake, files=files, values=values))
    if reserved > allowance:
        raise ValueError("Sum of per-case reference reservations exceeds whole-suite allowance")
    track_configuration = prepare_tracks(supplied, resolved, source_root=source.parent)
    for name, sha in track_configuration.get("source_bindings", {}).items():
        path = Path(name).resolve()
        if (
            not path.is_relative_to(source.parent)
            or hashlib.sha256(path.read_bytes()).hexdigest() != sha
        ):
            raise ValueError("Extension source binding is invalid")
        bindings[str(path)] = sha
    prepared_cases = []
    for index, selection in enumerate(resolved, 1):
        case, files, values = selection.declaration, selection.files, selection.values
        relative = f"cases/{index:04d}/primary"
        primary = prepare_run(
            files["manifest"],
            root / relative,
            options=values["options"],
            prices=values["prices"],
            schedule_context=values.get("context"),
            **{
                key: values.get(key)
                for key in ("occupancy_reviews", "route_reviews", "density_reviews")
            },
        )
        prepared_cases.append(
            {
                "case_id": case["case_id"],
                "revision": case["revision"],
                "directory": relative,
                "primary": primary,
            }
        )
    value = {
        "schema_version": PREPARATION_VERSION,
        "status": "prepared",
        "suite_id": supplied["suite_id"],
        "directory": str(root),
        "declaration": supplied,
        "source_root": str(source.parent),
        "source_bindings": bindings,
        "max_cost_usd": str(allowance),
        "reserved_cost_usd": str(reserved),
        "cases": prepared_cases,
        "track_configuration": track_configuration,
        "implementation_hashes": {
            str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                Path(__file__),
                Path(__file__).with_name("suite_tracks.py"),
                Path(__file__).with_name("suite_external.py"),
                Path(__file__).parents[1] / "cli" / "suite.py",
            )
        },
    }
    value["content_sha256"] = canonical_digest(value)
    write_track_artifacts(root, track_configuration.get("artifacts", {}))
    write_raw_artifacts(root, track_configuration.get("raw_artifacts", {}))
    _save(root, "preparation.json", value)
    return {
        "status": "prepared",
        "directory": str(root),
        "preparation_sha256": value["content_sha256"],
        "reserved_cost_usd": str(reserved),
        "case_count": len(cases),
    }


def _load(directory, *, implementation=False):
    from .evaluation_run import _verify

    root = Path(directory).resolve()
    value = _read(root / "preparation.json")[0]
    if (
        value.get("schema_version") != PREPARATION_VERSION
        or value.get("directory") != str(root)
        or canonical_digest({k: v for k, v in value.items() if k != "content_sha256"})
        != value.get("content_sha256")
    ):
        raise ValueError("Suite preparation digest or directory mismatch")
    for name, sha in value["source_bindings"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != sha:
            raise ValueError("Suite original sources changed")
    if implementation:
        for name, sha in value["implementation_hashes"].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != sha:
                raise ValueError("Suite implementation changed since preparation")
    for case in value["cases"]:
        expected = (root / case["directory"]).resolve()
        if not expected.is_relative_to(root) or case["primary"]["directory"] != str(expected):
            raise ValueError("Native case directory escapes suite")
        _verify(case["primary"], implementation=implementation)
    for name, artifact in value["track_configuration"].get("artifacts", {}).items():
        path = track_artifact_path(root, name)
        if path.read_bytes() != _bytes(artifact):
            raise ValueError("Prepared extension artifact changed")
    for name, raw in value["track_configuration"].get("raw_artifacts", {}).items():
        if track_artifact_path(root, name).read_bytes() != base64.b64decode(raw, validate=True):
            raise ValueError("Imported external artifact changed")
    from .suite_external import verify_prepared_external

    verify_prepared_external(value)
    return root, value


def track_artifact_path(root, name):
    """Resolve an explicit new native report path within the track artifact namespace."""
    if not isinstance(name, str) or not name:
        raise ValueError("Explicit track artifact path required")
    relative = Path(name)
    path = (root / relative).resolve()
    if (
        relative.is_absolute()
        or relative.drive
        or not path.is_relative_to((root / "tracks").resolve())
    ):
        raise ValueError("Extension artifacts must remain under tracks/")
    return path


def write_track_artifacts(root, artifacts):
    """Serialize frozen adapter reports only in an explicit preparation/report write stage."""
    if not isinstance(artifacts, dict):
        raise ValueError("Track artifact map required")
    resolved = [
        (track_artifact_path(root, name), _bytes(value)) for name, value in artifacts.items()
    ]
    if len({path for path, _ in resolved}) != len(resolved):
        raise ValueError("Duplicate track artifact paths")
    for path, raw in resolved:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)


def write_raw_artifacts(root, artifacts):
    """Copy exact declared external bytes in the explicit write stage."""
    for name, encoded in artifacts.items():
        path = track_artifact_path(root, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(base64.b64decode(encoded, validate=True))


def _inventory(root, *, refresh=False):
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Suite output symlinks are forbidden")
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        if name == "receipt.json" or (not refresh and name.startswith("reports/")):
            continue
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _close(root, digest, *, refresh=False):
    _save(
        root,
        "receipt.json",
        {"preparation_sha256": digest, "files": _inventory(root, refresh=refresh)},
    )


def _check_closed(root, digest, *, refresh=False):
    receipt = _read(root / "receipt.json")[0]
    if receipt.get("preparation_sha256") != digest or receipt.get("files") != _inventory(
        root, refresh=refresh
    ):
        raise ValueError("Suite artifact integrity or closed inventory mismatch")


def _case_row(case, result=None, *, reason=None):
    status = result["processing_status"] if result else "unstarted"
    primary = {
        "processing_status": status,
        "acquisition_status": result.get("acquisition_status", "not_started")
        if result
        else "not_started",
        "evidence_status": result.get("evidence_status", "not_completed")
        if result
        else "not_completed",
        "applicability": "applicable",
        "report": case["directory"] + "/execution/report.json"
        if result and (Path(case["primary"]["directory"]) / "execution/report.json").is_file()
        else None,
    }
    if reason:
        primary["reason"] = reason
    return {
        "case_id": case["case_id"],
        "revision": case["revision"],
        "processing_status": status,
        "primary_report": result,
        "tracks": {"primary": primary},
    }


def _summary(preparation, rows, *, allow_material_correction=False):
    from .suite_tracks import compose_tracks

    rows, tracks = compose_tracks(
        preparation,
        Path(preparation["directory"]),
        rows,
        allow_material_correction=allow_material_correction,
    )
    invalid_tracks = any(
        track.get("invalid_artifacts")
        for track in [
            *(track for row in rows for track in row["tracks"].values()),
            *tracks.values(),
        ]
    )
    return {
        "schema_version": REPORT_VERSION,
        "suite_id": preparation["suite_id"],
        "preparation_sha256": preparation["content_sha256"],
        "processing_status": "complete"
        if not invalid_tracks and all(row["processing_status"] == "complete" for row in rows)
        else "stopped",
        "max_cost_usd": preparation["max_cost_usd"],
        "reserved_cost_usd": preparation["reserved_cost_usd"],
        "cases": rows,
        "tracks": tracks,
    }


def execute_suite(directory, *, approved_sha256, env_file=None, http_client=None):
    """Consume one prepared suite, sequentially stopping at the first incomplete case."""
    import asyncio
    import os

    from .evaluation_run import execute_run

    root, preparation = _load(directory, implementation=True)
    if approved_sha256 != preparation["content_sha256"]:
        raise ValueError("Exact suite preparation approval required")
    if (root / "started.json").exists():
        raise FileExistsError("Suite already consumed; retry or resume is forbidden")
    if env_file:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)
    google = os.environ.get("GOOGLE_MAPS_API_KEY")
    model = os.environ.get("AZURE_OPENAI_API_KEY")
    if not google or not model:
        raise ValueError("Independent Google and V0 model credentials required")
    # Exclusive creation prevents simultaneous callers consuming the same package.
    with (root / "started.json").open("xb") as stream:
        stream.write(_bytes({"preparation_sha256": approved_sha256}))
    rows, stopped = [], False
    for case in preparation["cases"]:
        if stopped:
            rows.append(_case_row(case, reason="earlier_primary_stop"))
            continue
        try:
            _load(directory, implementation=True)
            result = asyncio.run(
                execute_run(
                    case["primary"],
                    approved_sha256=case["primary"]["content_sha256"],
                    google_api_key=google,
                    model_api_key=model,
                    http_client=http_client,
                )
            )
        except (
            ValueError,
            TypeError,
            KeyError,
            OSError,
            RuntimeError,
            asyncio.CancelledError,
            KeyboardInterrupt,
        ) as exc:
            result = {
                "processing_status": "stopped",
                "acquisition_status": "partial"
                if (root / case["directory"] / "execution").exists()
                else "not_started",
                "evidence_status": "not_completed",
                "error_type": type(exc).__name__,
                "reason": str(exc)
                or (
                    "execution_cancelled"
                    if isinstance(exc, asyncio.CancelledError)
                    else "execution_interrupted"
                    if isinstance(exc, KeyboardInterrupt)
                    else "execution_failed"
                ),
            }
        rows.append(_case_row(case, result))
        stopped = result["processing_status"] != "complete"
    report = _summary(preparation, rows, allow_material_correction=True)
    _save(root, "summary.json", report)
    _close(root, approved_sha256)
    return report


def replay_suite(directory):
    """Validate all inventories and recompose completed native reports without networking."""
    from .evaluation_run import replay_run

    root, preparation = _load(directory)
    _check_closed(root, preparation["content_sha256"])
    saved = _read(root / "summary.json")[0]
    rows = []
    if len(saved["cases"]) != len(preparation["cases"]):
        raise ValueError("Suite case inventory mismatch")
    for case, prior in zip(preparation["cases"], saved["cases"], strict=True):
        if prior["case_id"] != case["case_id"] or prior["revision"] != case["revision"]:
            raise ValueError("Suite case identity mismatch")
        if prior["processing_status"] == "unstarted":
            if (root / case["directory"] / "execution").exists():
                raise ValueError("Unstarted case contains unexpected execution")
            rows.append(_case_row(case, reason="earlier_primary_stop"))
        elif (
            prior["processing_status"] == "stopped"
            and not (root / case["directory"] / "execution").exists()
        ):
            result = prior["primary_report"]
            if (
                result.get("processing_status") != "stopped"
                or result.get("acquisition_status") != "not_started"
                or result.get("evidence_status") != "not_completed"
                or not result.get("error_type")
                or not result.get("reason")
            ):
                raise ValueError("Stopped case without native execution has invalid status")
            rows.append(_case_row(case, result))
        else:
            result = replay_run(root / case["directory"])
            rows.append(_case_row(case, result))
    report = _summary(preparation, rows)
    if report != saved:
        raise ValueError("Suite report replay differs")
    from .suite_external import verify_refreshes

    return verify_refreshes(root, preparation, report)


def report_suite(directory, *, attachments=None):
    """Append an offline summary without executing studies or rescoring primary output."""
    from .suite_external import append_refresh, verify_refreshes

    root, preparation = _load(directory)
    _check_closed(root, preparation["content_sha256"])
    original = _read(root / "summary.json")[0]
    report = verify_refreshes(root, preparation, original)
    return append_refresh(root, preparation, report, attachments=attachments)
