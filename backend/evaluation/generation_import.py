"""Validated producer HTTP captures usable only through labelled paired imports."""

import hashlib
from urllib.parse import parse_qsl, urlsplit

from .snapshot import _bytes, _decode, _summary, _utc_time


def generation_observations(read_bytes, source, plan, intake):
    from .evaluation_transport import google_wire

    def read(name):
        return _decode(read_bytes(name))

    index = read("evidence-index.json")
    capture = read("manifest.json")
    provenance = read("provenance.json")
    usage = read("usage.json")
    if (
        index.get("schema_version") != "rtpeval_generation_evidence_1"
        or index.get("adapter_coverage") != "default_adapters"
        or capture.get("kind") != "development_planner_usage_capture"
        or capture.get("status") != "completed"
        or capture.get("execution_requested") is not True
        or capture.get("evidence_requested") is not True
    ):
        raise ValueError("Completed default-adapter generation capture required")
    selected = [
        (group, run)
        for group in intake["inventory"]
        for version, run in group["runs"].items()
        if version == "v3"
        and group["group_id"] == index.get("group_id")
        and run["final"]["context"]["run_id"] == index.get("run_id")
    ]
    if len(selected) != 1:
        raise ValueError("Generation source is not the selected V3 run")
    group, run = selected[0]
    for value in (index, capture, provenance):
        if (
            value.get("group_id"),
            value.get("run_id"),
            value.get("version"),
            value.get("input_sha256"),
        ) != (group["group_id"], run["final"]["context"]["run_id"], "v3", group["input_sha256"]):
            raise ValueError("Generation source input/run binding mismatch")

    def sha(name):
        return hashlib.sha256(read_bytes(name)).hexdigest()

    if (
        sha("result.json") != run["final"]["context"]["artifact_sha256"]
        or index["result_sha256"] != sha("result.json")
        or provenance["result_sha256"] != sha("result.json")
        or sha("usage.json") != run["usage_hash"]
        or sha("provenance.json") != run["provenance_hash"]
        or sha("input.json") != group["input_sha256"]
    ):
        raise ValueError("Generation selected source hash mismatch")
    if any(
        index.get(field) != capture.get(field)
        for field in ("source_revision", "runtime_policy_sha256")
    ):
        raise ValueError("Generation capture configuration mismatch")
    configuration = provenance.get("configuration_ref")
    evidence_ref = provenance.get("evidence_index_ref")
    if (
        not isinstance(configuration, dict)
        or sha(configuration["path"]) != configuration["sha256"]
        or not isinstance(evidence_ref, dict)
        or evidence_ref.get("path") != "evidence-index.json"
        or sha("evidence-index.json") != evidence_ref.get("sha256")
    ):
        raise ValueError("Generation provenance capture/configuration mismatch")
    policy = read(configuration["path"])
    if policy.get("sha256") != index["runtime_policy_sha256"]:
        raise ValueError("Generation runtime policy mismatch")
    artifacts = index.get("artifacts")
    if not isinstance(artifacts, list) or len({r["path"] for r in artifacts}) != len(artifacts):
        raise ValueError("Generation explicit unique artifact inventory required")
    artifact_map = {r["path"]: r for r in artifacts}
    for artifact in artifacts:
        if artifact.get("sha256") is not None and sha(artifact["path"]) != artifact["sha256"]:
            raise ValueError("Generation evidence artifact hash mismatch")
    start, finish = usage["timing"]["started_at"], usage["timing"]["finished_at"]
    if _utc_time(start) > _utc_time(finish):
        raise ValueError("Generation capture time order mismatch")
    providers = usage.get("provider_events")
    if not isinstance(providers, list) or len({r["event_id"] for r in providers}) != len(providers):
        raise ValueError("Generation usage event identity mismatch")
    providers = {r["event_id"]: r for r in providers}
    events = index.get("http_events")
    if not isinstance(events, list) or len({r["event_id"] for r in events}) != len(events):
        raise ValueError("Generation HTTP event identity mismatch")
    candidates = []
    for event in events:
        observed = providers.get(event["event_id"])
        if observed is None or observed.get("provider") != "google":
            continue
        if observed.get("source") != "http_request_hook" or observed.get(
            "status_code"
        ) != event.get("status_code"):
            raise ValueError("Generation HTTP event/usage mismatch")
        if any(event.get(kind + "_body_status") != "complete" for kind in ("request", "response")):
            continue
        bodies = {}
        for kind in ("request", "response"):
            name = event.get(kind + "_body_ref")
            if name not in artifact_map or artifact_map[name].get("sha256") is None:
                raise ValueError("Generation wire body lacks hashed artifact binding")
            wire = read(name)
            if wire.get("representation") != "credential_filtered_utf8":
                raise ValueError("Unsupported generation body representation")
            bodies[kind] = wire["body"]
        for request in plan["requests"]:
            wire = google_wire(request)
            expected_operation = (
                "place_details"
                if request["operation"] == "places_details"
                else request["operation"]
            )
            if observed.get("operation") != expected_operation:
                continue
            mask = event.get("request_headers", {}).get("x-goog-fieldmask", "")
            required = set(wire["field_mask"].split(","))
            # Claimed-ID identity can use exact names/addresses without address components.
            if request["operation"] == "places_details":
                required.discard("addressComponents")
            body = bodies["request"]
            if event["method"] == "GET" and body == "":
                body = None
            source_url = urlsplit(event["url"])
            language = None
            url_matches = event["url"] == wire["url"]
            if request["operation"] == "places_details":
                # The selected producer uses English details; retain the explicit locale.
                query = parse_qsl(source_url.query, keep_blank_values=True)
                if query == [("languageCode", "en")]:
                    language = "en"
                    url_matches = source_url._replace(query="").geturl() == wire["url"]
            if (
                event["method"] != wire["method"]
                or not url_matches
                or body != wire["json"]
                or not required <= set(mask.split(","))
            ):
                continue
            if (
                request["operation"] == "route_matrix"
                and request["parameters"]["time_basis"] != "explicit_departure"
            ):
                continue
            response = bodies["response"]
            response_bytes = (
                response.encode("utf-8") if isinstance(response, str) else _bytes(response)
            )
            summary = _summary(request, event["status_code"], response_bytes)
            raw_name = event["response_body_ref"]
            candidates.append(
                {
                    "request": request,
                    "summary": summary,
                    "attempt": {
                        "attempt": 1,
                        "requested_at": start,
                        "retrieved_at": finish,
                        "status_code": event["status_code"],
                        "raw": {"path": source["files"][raw_name]["path"], "sha256": sha(raw_name)},
                    },
                    "raw_path": source["files"][raw_name]["path"],
                    "origin": {
                        "kind": "planner_generation",
                        "http_event_id": event["event_id"],
                        "observation_time_basis": "run_capture_window",
                        "response_representation": "credential_filtered_utf8",
                        "source_field_mask": mask,
                        "required_fields": sorted(required),
                        "source_run_id": index["run_id"],
                        "source_url": event["url"],
                        "source_language_code": language,
                    },
                }
            )
    return candidates, {
        "kind": "planner_generation",
        "usage_sha256": sha("usage.json"),
        "attribution": "inherited_source_only",
        "charged_in_current_phase": False,
        "actual_source_google_sends": sum(r["provider"] == "google" for r in providers.values()),
    }
