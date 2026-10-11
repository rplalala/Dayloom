"""Opt-in best-effort candidate stage export at caller-owned planner seams."""

import hashlib
import json
import logging
from pathlib import Path


class CandidateCapture:
    def __init__(self, path, version, run_id):
        self.path = Path(path)
        self.value = {
            "schema_version": "rtpeval_candidate_capture_1",
            "version": version,
            "run_id": str(run_id),
            "stages": {},
            "pre_rag_google_ids": None,
            "omissions": [],
            "rag": None,
        }

    def record(self, name, places, *, reasons=(), status="complete"):
        try:
            self.value["stages"][name] = {
                "status": status,
                "reasons": list(reasons),
                "places": [
                    {
                        "canonical_place_id": item.candidate.place_id,
                        "google_origins": [hit.model_dump(mode="json") for hit in item.query_hits],
                        "rag_origins": [
                            origin.model_dump(mode="json") for origin in item.discovery_origins
                        ],
                    }
                    for item in places
                ],
            }
        except Exception:
            logging.getLogger(__name__).warning("Candidate capture stage unavailable: %s", name)

    def pre_google(self, places):
        self.record("discovered", places, status="partial", reasons=["acquisition_in_progress"])
        self.value["pre_rag_google_ids"] = sorted(item.candidate.place_id for item in places)

    def omissions(self, rows):
        self.value["omissions"].extend(rows)

    def finish(self, *, result=None, rag=None, failure=None):
        try:
            self.value["rag"] = rag
            self.value["outcome"] = "failed" if failure else "completed"
            self.value["failure_type"] = type(failure).__name__ if failure else None
            self.value["result_semantic_sha256"] = (
                hashlib.sha256(
                    json.dumps(
                        result.model_dump(mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
                if result
                else None
            )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation prevents capture from replacing any existing caller material.
            with self.path.open("x", encoding="utf-8") as stream:
                json.dump(self.value, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
        except Exception:
            logging.getLogger(__name__).warning("Candidate capture export unavailable")
