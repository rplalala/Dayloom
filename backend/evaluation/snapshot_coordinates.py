"""Offline coordinate preparation from linked independent identity snapshots."""

import math
from dataclasses import dataclass
from pathlib import Path

from .identity_program import VERSIONED_TARGET_POLICIES
from .intake import _read
from .place_association import associated_place_id
from .preparation import identity_ready
from .records import MaterialError, canonical_digest, freeze, require, thaw
from .snapshot import build_identity_plan, identity_evidence, load_snapshot

PREPARATION_VERSION = "rtpeval_snapshot_coordinates_1"


@dataclass(frozen=True)
class SnapshotCoordinates:
    """Immutable source-derived coordinates or whole-material diagnostics."""

    status: str
    data: object

    def to_dict(self):
        return {"status": self.status, **thaw(self.data)}


def prepare_snapshot_coordinates(intake, identity_report, snapshot_directory):
    """Revalidate original evidence and extract only verified physical coordinates."""
    prepared = intake.to_dict() if hasattr(intake, "to_dict") else thaw(intake)
    identity = (
        identity_report.to_dict() if hasattr(identity_report, "to_dict") else thaw(identity_report)
    )
    base = {"schema_version": PREPARATION_VERSION, "records": [], "diagnostics": []}
    try:
        require(
            identity_ready(prepared, identity),
            "identity",
            "Current linked identity report required",
        )
        if any(
            "programmatic_judgment" in r or "candidate_correspondence" in r
            for r in identity["records"]
        ):
            base["unadopted_references"] = [
                {key: r[key] for key in ("reference_id", "source", "reason", "grounding_verdict")}
                for r in identity["records"]
                if associated_place_id(r) is None
            ]
        snapshot = load_snapshot(snapshot_directory)
        plan = snapshot["plan"]
        require(
            plan["phase"] == "identity"
            and type(plan.get("paired")) is bool
            and plan == build_identity_plan(prepared, paired=plan["paired"]),
            "snapshot/plan",
            "Identity snapshot intake/plan mismatch",
        )
        evidence = identity_evidence(
            snapshot,
            historical=identity.get("association_policy_version") not in VERSIONED_TARGET_POLICIES,
        )
        require(
            identity["evidence_hash"] == canonical_digest(evidence),
            "identity/evidence_hash",
            "Identity snapshot evidence mismatch",
        )
        manifest, manifest_hash = _read(Path(snapshot_directory) / "manifest.json")
        require(manifest == snapshot, "snapshot", "Snapshot changed during preparation")
        base.update(
            batch_id=prepared["batch_id"],
            batch_revision=prepared["revision"],
            source_hashes={
                "intake": canonical_digest(prepared),
                "identity": canonical_digest(identity),
                "snapshot_manifest": manifest_hash,
                "snapshot_plan": snapshot["plan_hash"],
            },
        )
        observed = {r["reference_id"]: r for r in evidence["records"]}
        records = {r["key"]: r for r in snapshot["records"]}
        refs = {r["reference_id"]: r for r in plan["references"]}
        selected = {}
        for adopted in identity["records"]:
            pid = associated_place_id(adopted)
            if pid is None:
                continue
            rid = adopted.get("evidence_reference_id", adopted["reference_id"])
            require(
                adopted["evidence_hash"] == canonical_digest(observed.get(rid))
                and adopted["observation_id"] == observed[rid]["observation_id"],
                rid,
                "Adopted identity observation mismatch",
            )
            candidates = selected.setdefault(pid, {})
            for kind, key in refs[rid]["requests"].items():
                record = records[key]
                if observed[rid][kind]["status"] != "available":
                    continue
                payload = record["summary"]["payload"]
                places = (
                    [("", payload)]
                    if kind == "details"
                    else [
                        (f"/places/{i}", place) for i, place in enumerate(payload.get("places", []))
                    ]
                )
                for pointer, place in places:
                    if not isinstance(place, dict) or place.get("id") != pid:
                        continue
                    attempt = record["attempts"][-1]
                    origin = {
                        "request_key": key,
                        "raw_sha256": attempt["raw"]["sha256"],
                        "pointer": (
                            "/body"
                            if record.get("origin", {})
                            and record["origin"]["kind"] == "planner_generation"
                            else ""
                        )
                        + pointer
                        + "/location",
                        "retrieved_at": attempt["retrieved_at"],
                        **(
                            {"acquisition_origin": record["origin"]}
                            if snapshot.get("schema_version") == "rtpeval_imported_snapshot_1"
                            else {}
                        ),
                    }
                    if "location" in place:
                        candidates[(key, pointer)] = {
                            "coordinate": place["location"],
                            "source": origin,
                        }
        for pid, candidates in sorted(selected.items()):
            if not candidates:
                base["diagnostics"].append({"place_id": pid, "reason": "coordinates_missing"})
                continue
            items = [candidates[k] for k in sorted(candidates)]
            if any(
                not isinstance(item["coordinate"], dict)
                or any(
                    type(item["coordinate"].get(field)) not in (int, float)
                    or abs(item["coordinate"][field]) > limit
                    or not math.isfinite(item["coordinate"][field])
                    for field, limit in (("latitude", 90), ("longitude", 180))
                )
                for item in items
            ):
                base["diagnostics"].append(
                    {
                        "place_id": pid,
                        "reason": "coordinates_invalid",
                        "observations": [item["source"] for item in items],
                    }
                )
                continue
            point = items[0]["coordinate"]
            sources = [item["source"] for item in items]
            if any(
                any(
                    item["coordinate"][field] != point[field] for field in ("latitude", "longitude")
                )
                for item in items[1:]
            ):
                base["diagnostics"].append(
                    {"place_id": pid, "reason": "coordinates_conflicting", "observations": sources}
                )
                continue
            digest = canonical_digest(
                {"place_id": pid, "coordinate": point, "observations": sources}
            )
            base["records"].append(
                {
                    "place_id": pid,
                    "latitude": point["latitude"],
                    "longitude": point["longitude"],
                    "evidence_sha256": digest,
                    "source_kind": "imported_snapshot"
                    if snapshot.get("schema_version") == "rtpeval_imported_snapshot_1"
                    else "independent_snapshot",
                    "observations": sources,
                }
            )
        return SnapshotCoordinates("complete", freeze(base))
    except (MaterialError, ValueError, KeyError, TypeError, OSError) as exc:
        base["records"] = []
        base["diagnostics"] = [
            exc.diagnostic
            if isinstance(exc, MaterialError)
            else {"reason": "coordinate_preparation_invalid", "explanation": str(exc)}
        ]
        return SnapshotCoordinates("needs_material_correction", freeze(base))
