"""Exact-byte, root-bounded material reading and stable semantic digests."""

import hashlib
import json
from pathlib import Path

from backend.cli.collection import CollectionError, _json, _path, _require


class ResearchError(CollectionError):
    """Submitted research material cannot be safely or consistently interpreted."""


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


class Sources:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.bindings = {}

    def read_bytes(self, ref):
        _require(isinstance(ref, dict), "Expected explicit research source reference")
        path = _path(self.root, ref.get("path"))
        _require(ref.get("availability") == "available", "Referenced source must be available")
        _require(
            isinstance(ref.get("media_type"), str) and ref["media_type"],
            "Source media type required",
        )
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        _require(ref.get("sha256") == sha, "Source hash mismatch: " + ref["path"])
        key = path.relative_to(self.root).as_posix()
        previous = self.bindings.get(key)
        _require(previous is None or previous["sha256"] == sha, "Contradictory source reference")
        self.bindings[key] = {
            "path": key,
            "sha256": sha,
            "schema_version": ref.get("schema_version"),
        }
        return raw

    def read_ref(self, ref, schema=None):
        raw = self.read_bytes(ref)
        _require(ref.get("media_type") == "application/json", "Source must be JSON")
        value = _json(raw)
        if schema:
            _require(value.get("schema_version") == schema, "Unsupported source schema: " + schema)
            _require(ref.get("schema_version") == schema, "Source schema reference mismatch")
        elif ref.get("schema_version") is not None:
            _require(
                ref["schema_version"] in (value.get("schema_version"), value.get("input_version")),
                "Declared source schema mismatch",
            )
        return value

    def manifest(self):
        return [self.bindings[key] for key in sorted(self.bindings)]
