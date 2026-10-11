"""Independent interest inventories, reviewed labels and stable source pointers."""

from backend.cli.collection import _require

from .context import text_fields, timestamp


def _case_key(value):
    text_fields(value, ("case_id", "case_revision"))
    return value["case_id"], value["case_revision"]


def _pointer(value, pointer):
    _require(
        isinstance(pointer, str) and pointer.startswith("/"),
        "Explicit original JSON pointer required",
    )
    current = value
    for token in pointer[1:].split("/"):
        _require(
            "~" not in token.replace("~0", "").replace("~1", ""), "Malformed JSON pointer escape"
        )
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            _require(token.isdigit() and str(int(token)) == token, "Invalid JSON array pointer")
            _require(int(token) < len(current), "Foreign JSON array pointer")
            current = current[int(token)]
        else:
            _require(
                isinstance(current, dict) and token in current, "Foreign original source pointer"
            )
            current = current[token]
    return current


def _reviewer(value):
    text_fields(value, ("revision", "reviewer_ref", "reviewer_kind", "reviewed_at", "rationale"))
    _require(
        value["reviewer_kind"] in ("human", "external_model"), "Independent reviewer kind required"
    )
    timestamp(value["reviewed_at"])


def _interests(context, refs):
    cases = {(case["case_id"], case["revision"]): case for case in context.population["cases"]}
    inventories = {}
    for ref in refs:
        value = context.read_ref(ref, "rtpeval_research_interests_1")
        key = _case_key(value)
        _require(
            key in cases and key not in inventories,
            "Foreign or duplicate independent interest inventory",
        )
        case = cases[key]
        _require(
            value.get("input_sha256") == case["input_ref"]["sha256"],
            "Interest original input hash mismatch",
        )
        _reviewer(value)
        original = context.read_ref(case["input_ref"])
        spec = context.read_ref(value.get("requirement_spec_ref"), "rtpeval_requirements_1")
        text_fields(spec, ("spec_id", "revision", "group_id"))
        _require(
            spec.get("input_sha256") == value["input_sha256"],
            "Interest RequirementSpec input mismatch",
        )
        review = spec.get("review")
        _require(
            isinstance(review, dict) and review.get("status") == "reviewed",
            "Independent reviewed RequirementSpec required",
        )
        text_fields(review, ("reviewer_ref", "reviewed_at"))
        timestamp(review["reviewed_at"])
        for field in ("subjects", "obligations", "soft_preferences", "unresolved_items"):
            _require(
                isinstance(spec.get(field), list), "Malformed reviewed RequirementSpec: " + field
            )
        interests = value.get("interests")
        _require(isinstance(interests, list), "Explicit independent interest inventory required")
        ids = set()
        for interest in interests:
            text_fields(
                interest, ("interest_id", "source_pointer", "source_text", "requirement_pointer")
            )
            _require(interest["interest_id"] not in ids, "Duplicate stable interest identity")
            ids.add(interest["interest_id"])
            source = _pointer(original, interest["source_pointer"])
            _require(
                isinstance(source, str) and source == interest["source_text"],
                "Stale original interest pointer/text binding",
            )
            requirement = _pointer(spec, interest["requirement_pointer"])
            _require(
                isinstance(requirement, dict)
                and interest["interest_id"]
                in (
                    requirement.get("preference_id"),
                    requirement.get("obligation_id"),
                    requirement.get("interest_id"),
                ),
                "Interest reviewed RequirementSpec pointer mismatch",
            )
        inventories[key] = {"value": value, "sha256": ref["sha256"]}
    return inventories


def _reviews(context, refs, inventories, runs):
    available_places = {}
    for run in runs:
        available_places.setdefault(_case_key(run), set()).update(run["places"])
        available_places[_case_key(run)].update(run["scheduled"]["canonical_ids"])
    reviews, ids = {}, set()
    for ref in refs:
        value = context.read_ref(ref, "rtpeval_research_relevance_reviews_1")
        _require(
            isinstance(value.get("records"), list),
            "Explicit independent relevance reviews required",
        )
        for record in value["records"]:
            key = _case_key(record)
            _require(key in inventories, "Review has no source-bound interest inventory")
            inventory = inventories[key]
            source = inventory["value"]
            text_fields(record, ("review_id", "interest_id", "source_pointer"))
            _require(record["review_id"] not in ids, "Duplicate relevance review identity")
            ids.add(record["review_id"])
            _reviewer(record)
            for field, expected in (
                ("input_sha256", source["input_sha256"]),
                ("interest_inventory_sha256", inventory["sha256"]),
                ("requirement_spec_sha256", source["requirement_spec_ref"]["sha256"]),
            ):
                _require(
                    record.get(field) == expected, "Stale relevance review source binding: " + field
                )
            interests = {interest["interest_id"]: interest for interest in source["interests"]}
            _require(record["interest_id"] in interests, "Foreign reviewed interest")
            _require(
                record["source_pointer"] == interests[record["interest_id"]]["source_pointer"],
                "Stale relevance review request pointer",
            )
            _require(
                record.get("verdict") in ("relevant", "not_relevant", "unknown"),
                "Invalid relevance verdict",
            )
            pid, unresolved = record.get("canonical_place_id"), record.get("unresolved_subject_id")
            _require(
                (isinstance(pid, str) and bool(pid) and unresolved is None)
                or (pid is None and isinstance(unresolved, str) and bool(unresolved)),
                "Exactly one canonical or unresolved venue subject required",
            )
            if pid:
                _require(pid in available_places.get(key, set()), "Foreign relevance venue subject")
            evidence_refs = record.get("venue_evidence_refs")
            _require(isinstance(evidence_refs, list), "Explicit venue evidence refs required")
            _require(
                record["verdict"] == "unknown" or evidence_refs,
                "Known relevance verdict requires venue evidence",
            )
            for evidence_ref in evidence_refs:
                evidence = context.read_ref(evidence_ref)
                _require(
                    evidence.get("source_kind")
                    in (
                        "independent_google_places",
                        "independent_official",
                        "independent_reviewed_description",
                    ),
                    "Planner/query evidence cannot establish independent relevance",
                )
                _require(
                    evidence.get("canonical_place_id") == pid
                    and evidence.get("unresolved_subject_id") == unresolved,
                    "Foreign venue evidence subject binding",
                )
            label_key = record["interest_id"], pid or ("unresolved:" + unresolved)
            labels = reviews.setdefault(key, {})
            _require(label_key not in labels, "Duplicate or contradictory relevance judgment")
            labels[label_key] = record
    return reviews
