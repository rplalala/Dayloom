"""Validated original-input populations and source-compatible selected attempts."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.cli.collection import _completion, _json, _require, _text

from .sources import Sources
from .usage import validate_generation_usage

VERSIONS = ("v0", "v1", "v2", "v3")
STATUSES = (
    "completed",
    "clarification_required",
    "failed",
    "cancelled",
    "incomplete",
    "unstarted",
    "unknown_pending",
)


def text_fields(value, fields):
    _require(isinstance(value, dict), "Expected research object")
    for field in fields:
        _require(_text(value.get(field)), "Missing research field: " + field)


def timestamp(value):
    _require(_text(value), "Missing timezone-aware timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(parsed.utcoffset() is not None, "Timestamp requires timezone")
    return parsed


def slot_key(value):
    return tuple(value[field] for field in ("case_id", "case_revision", "version", "repetition_id"))


@dataclass
class ResearchContext:
    root: Path
    declaration: dict
    population: dict
    profile: dict
    census: dict | None
    sources: Sources
    slots: list[dict]

    def read_ref(self, ref, schema=None):
        return self.sources.read_ref(ref, schema)

    @property
    def selected_attempts(self):
        return {slot_key(slot): slot["primary_attempt"] for slot in self.slots}


def load_context(declaration_path, *, sources=None):
    path = Path(declaration_path).resolve()
    if sources is None:
        raw = path.read_bytes()
        sources = Sources(path.parent)
    else:
        _require(sources.root == path.parent, "Injected sources require the declaration root")
        binding = sources.bindings.get(path.name)
        _require(binding is not None, "Injected sources require a bound declaration")
        raw = sources.read_bytes(
            {**binding, "availability": "available", "media_type": "application/json"}
        )
    declaration = _json(raw)
    _require(
        declaration.get("schema_version") == "rtpeval_research_declaration_1",
        "Unsupported research declaration",
    )
    sources.bindings[path.name] = {
        "path": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "schema_version": declaration["schema_version"],
    }
    population = sources.read_ref(
        declaration.get("population_ref"), "rtpeval_research_population_1"
    )
    profile = sources.read_ref(declaration.get("profile_ref"), "rtpeval_research_profile_1")
    text_fields(population, ("population_id", "revision"))
    text_fields(profile, ("profile_id", "revision", "source_revision", "completion_policy_ref"))
    _require(
        profile.get("population_id") == population["population_id"]
        and profile.get("population_revision") == population["revision"],
        "Stale population profile binding",
    )
    timestamp(profile.get("declared_at"))
    _read_profile_history(sources, profile)
    _require(
        profile.get("timing_basis") in ("prospective", "retrospective", "unverified"),
        "Explicit selection timing basis required",
    )
    _require(
        profile.get("first_attempt_rule") == "first_dispatched",
        "Primary selection must use first dispatched attempt",
    )
    retry = profile.get("retry_rule")
    _require(
        isinstance(retry, dict)
        and retry.get("selection") in ("none", "last_dispatched")
        and retry.get("scope") == "slot",
        "Unsupported retry rule/scope",
    )
    mapping = profile.get("completion_mapping")
    _require(
        isinstance(mapping, dict)
        and mapping
        and all(_text(key) and value in STATUSES for key, value in mapping.items()),
        "Explicit valid native completion mapping required",
    )
    native_mapping = {
        "completed": "completed",
        "clarification_required": "clarification_required",
        "failed": "failed",
        "cancelled": "cancelled",
        "incomplete": "incomplete",
        "not_started": "unstarted",
        "pending": "unknown_pending",
        "required_mechanism_failed": "failed",
    }
    _require(
        mapping.get("completed") == "completed"
        and all(native_mapping.get(key, value) == value for key, value in mapping.items()),
        "Completion mapping contradicts native status semantics",
    )
    configs = profile.get("configurations")
    _require(
        isinstance(configs, dict) and configs, "Explicit version configuration bindings required"
    )
    _require(all(version in VERSIONS for version in configs), "Unknown configuration version")
    for ref in configs.values():
        _require(isinstance(ref, dict), "Explicit configuration reference required")
        if ref.get("media_type") == "application/json":
            sources.read_ref(ref)
        else:
            sources.read_bytes(ref)
    cases = population.get("cases")
    _require(
        isinstance(cases, list) and cases, "Explicit nonempty original input inventory required"
    )
    ids, slots = set(), []
    for case in cases:
        text_fields(case, ("case_id", "revision"))
        _require(case["case_id"] not in ids, "Duplicate case identity")
        ids.add(case["case_id"])
        sources.read_ref(case.get("input_ref"))
        _require(
            isinstance(case.get("metadata"), dict), "Explicit original-input metadata required"
        )
        versions, repetitions = case.get("planned_versions"), case.get("repetition_ids")
        _require(
            isinstance(versions, list)
            and versions
            and len(set(versions)) == len(versions)
            and all(v in VERSIONS and v in configs for v in versions),
            "Invalid planned versions",
        )
        _require(
            isinstance(repetitions, list)
            and repetitions
            and all(_text(r) for r in repetitions)
            and len(set(repetitions)) == len(repetitions),
            "Invalid planned repetitions",
        )
        for repetition in repetitions:
            for version in versions:
                slots.append(
                    {
                        "case_id": case["case_id"],
                        "case_revision": case["revision"],
                        "version": version,
                        "repetition_id": repetition,
                        "input_sha256": case["input_ref"]["sha256"],
                        "configuration_sha256": configs[version]["sha256"],
                        "status": "unknown_pending",
                        "reason_type": "missing_census_record",
                        "primary_attempt": None,
                        "attempts": [],
                        "retry_outcome": None,
                    }
                )
    census = None
    if declaration.get("census_ref") is not None:
        census = sources.read_ref(declaration["census_ref"], "rtpeval_research_census_1")
        _require(
            census.get("population_id") == population["population_id"]
            and census.get("population_revision") == population["revision"],
            "Stale census population binding",
        )
        _require(
            census.get("profile_id") == profile["profile_id"]
            and census.get("profile_revision") == profile["revision"],
            "Stale census selection profile binding",
        )
        _require(isinstance(census.get("attempts"), list), "Explicit attempt census required")
        _load_attempts(sources, census["attempts"], slots, profile)
    _require(isinstance(declaration.get("track_refs", {}), dict), "Invalid track references")
    return ResearchContext(path.parent, declaration, population, profile, census, sources, slots)


def _load_attempts(sources, records, slots, profile):
    inventory = {slot_key(slot): slot for slot in slots}
    attempt_ids, run_ids = set(), set()
    for record in records:
        text_fields(
            record,
            (
                "case_id",
                "case_revision",
                "version",
                "repetition_id",
                "attempt_id",
                "run_id",
                "reason_type",
            ),
        )
        key = slot_key(record)
        _require(key in inventory, "Foreign or stale attempt slot binding")
        slot = inventory[key]
        _require(
            record["attempt_id"] not in attempt_ids and record["run_id"] not in run_ids,
            "Duplicate attempt or run identity",
        )
        attempt_ids.add(record["attempt_id"])
        run_ids.add(record["run_id"])
        _require(
            type(record.get("order")) is int and record["order"] >= 1,
            "Attempt order must be a positive integer",
        )
        _require(type(record.get("dispatched")) is bool, "Explicit planner dispatch required")
        _require(
            isinstance(record.get("execution_metadata"), dict),
            "Explicit execution/cache/concurrency metadata required",
        )
        _require(
            record.get("input_sha256") == slot["input_sha256"],
            "Attempt original input hash mismatch",
        )
        _require(
            record.get("configuration_sha256") == slot["configuration_sha256"],
            "Attempt configuration hash mismatch",
        )
        if record.get("producer_metadata_ref") is not None:
            from .dispatch import read_dispatch

            read_dispatch(sources, record["producer_metadata_ref"], record)
        dispatched = timestamp(record.get("dispatched_at")) if record["dispatched"] else None
        _require(
            record["dispatched"] or record.get("dispatched_at") is None,
            "Undispatched attempt has dispatch timestamp",
        )
        if dispatched and profile["timing_basis"] == "prospective":
            _require(
                timestamp(profile["declared_at"]) <= dispatched,
                "Prospective profile declared after dispatch",
            )
        usage = _read_native_refs(sources, record)
        completion = None
        status = "unknown_pending"
        if record.get("completion_ref") is not None:
            completion = sources.read_ref(record["completion_ref"])
            text_fields(completion, ("declared_by", "declared_at", "policy_ref", "workflow_status"))
            mechanisms = completion.get("required_mechanisms")
            _require(
                isinstance(mechanisms, dict)
                and "generation" in mechanisms
                and all(_text(k) and _text(v) for k, v in mechanisms.items()),
                "Malformed producer required mechanisms",
            )
            if "producer_policy_ref" in completion:
                _require(
                    completion["producer_policy_ref"] == profile["completion_policy_ref"],
                    "Foreign producer completion policy",
                )
            declared = timestamp(completion["declared_at"])
            _require(
                dispatched is None or declared >= dispatched,
                "Completion declaration precedes dispatch",
            )
            _require(
                completion["policy_ref"] == profile["completion_policy_ref"],
                "Completion policy mismatch",
            )
            _require(
                completion["workflow_status"] in profile["completion_mapping"],
                "Unmapped native workflow outcome",
            )
            status = profile["completion_mapping"][completion["workflow_status"]]
            if status == "completed":
                errors = _completion(
                    completion, record["version"], profile["completion_policy_ref"]
                )
                _require(not errors, "Contradictory completed workflow: " + "; ".join(errors))
        _require(
            status != "unstarted" or not record["dispatched"],
            "Dispatched attempt declared unstarted",
        )
        _require(
            record["dispatched"] or status in ("unstarted", "unknown_pending"),
            "Terminal generation outcome without dispatch",
        )
        if usage is not None:
            validate_generation_usage(
                usage, dispatched=record["dispatched"], workflow_status=status
            )
        slot["attempts"].append({**record, "status": status, "producer_completion": completion})
    for slot in slots:
        attempts = slot["attempts"]
        previous, last_dispatch = None, None
        for index, attempt in enumerate(attempts, 1):
            _require(attempt["order"] == index, "Missing, duplicate or unordered attempt sequence")
            _require(attempt.get("prior_attempt_id") == previous, "Broken prior-attempt retry link")
            if attempt["dispatched"]:
                current = timestamp(attempt["dispatched_at"])
                _require(
                    last_dispatch is None or current >= last_dispatch,
                    "Attempt dispatch chronology contradicts order",
                )
                last_dispatch = current
            previous = attempt["attempt_id"]
        dispatched = [attempt for attempt in attempts if attempt["dispatched"]]
        primary = dispatched[0] if dispatched else None
        slot["primary_attempt"] = primary
        selected = primary or (attempts[-1] if attempts else None)
        if selected:
            slot["status"], slot["reason_type"] = selected["status"], selected["reason_type"]
        if profile["retry_rule"]["selection"] == "last_dispatched" and len(dispatched) > 1:
            slot["retry_outcome"] = dispatched[-1]


def _read_native_refs(sources, attempt):
    usage = None
    result_hash = None
    if attempt.get("result_ref") is not None:
        result = sources.read_ref(attempt["result_ref"])
        _require(result.get("system_version") == attempt["version"], "Result version mismatch")
        result_hash = attempt["result_ref"]["sha256"]
    for key, schema in (
        ("usage_ref", "rtpeval_usage_1"),
        ("provenance_ref", "rtpeval_provenance_1"),
    ):
        if attempt.get(key) is None:
            continue
        text_fields(attempt, ("group_id",))
        native = sources.read_ref(attempt[key], schema)
        for field in ("group_id", "run_id", "version"):
            _require(native.get(field) == attempt[field], key + " identity mismatch: " + field)
        _require(
            "result_sha256" in native and native["result_sha256"] == result_hash,
            key + " result hash mismatch",
        )
        if key == "provenance_ref":
            _require(
                native.get("input_sha256") == attempt["input_sha256"],
                "Provenance input hash mismatch",
            )
        else:
            usage = native
        for field in ("input_sha256", "configuration_sha256"):
            if field in native:
                _require(
                    native[field] == attempt[field], key + " source binding mismatch: " + field
                )

    return usage


def _read_profile_history(sources, profile):
    current, revisions = profile, {profile["revision"]}
    while current.get("previous_profile_ref") is not None:
        previous = sources.read_ref(current["previous_profile_ref"], "rtpeval_research_profile_1")
        text_fields(
            previous,
            ("profile_id", "revision", "population_id", "population_revision", "source_revision"),
        )
        _require(
            previous["profile_id"] == profile["profile_id"]
            and previous["population_id"] == profile["population_id"],
            "Foreign profile history binding",
        )
        _require(
            previous["revision"] not in revisions, "Duplicate or cyclic profile history revision"
        )
        _require(
            timestamp(previous.get("declared_at")) <= timestamp(current["declared_at"]),
            "Profile history timestamp order mismatch",
        )
        revisions.add(previous["revision"])
        current = previous
