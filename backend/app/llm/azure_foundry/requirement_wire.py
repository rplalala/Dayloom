"""Versioned requirement transport; historical DTOs remain readable unchanged."""

import copy
import json
import re
from hashlib import sha256

from backend.app.schemas.requirement_boundary import RequirementBoundaryError

SOURCE_TEXT_FIELDS = {"source_text", "target_source_text", "scope_text", "date_source_text"}


class SourceSpans:
    """Application-owned token spans; endpoints select a contiguous original interval."""

    def __init__(self, prompt, text):
        self.text = text
        prefix = sha256(prompt.encode("utf-8")).hexdigest()[:16]
        self.spans = {
            f"s{prefix}_{i}": (m.start(), m.end())
            for i, m in enumerate(re.finditer(r"\S{1,64}", text))
        }

    def inventory(self):
        return [
            {"id": key, "text": self.text[start:end]} for key, (start, end) in self.spans.items()
        ]

    def source(self, value, path):
        if not isinstance(value, dict) or set(value) != {"first_id", "last_id"}:
            invalid("invalid_source_span", path)
        first, last = value["first_id"], value["last_id"]
        if not isinstance(first, str) or not isinstance(last, str):
            invalid("invalid_source_span", path)
        if first not in self.spans or last not in self.spans:
            invalid("invalid_source_span", path)
        start, end = self.spans[first][0], self.spans[last][1]
        if start >= end:
            invalid("invalid_source_span", path)
        quote = self.text[start:end]
        occurrence, position = 0, self.text.find(quote)
        while position != start:
            position = self.text.find(quote, position + 1)
            occurrence += 1
        return {"quote": quote, "occurrence": occurrence}

    def restore(self, node, path=()):
        if isinstance(node, list):
            return [self.restore(v, (*path, i)) for i, v in enumerate(node)]
        if not isinstance(node, dict):
            return node
        result = {}
        for key, value in node.items():
            loc = (*path, key)
            if key == "source_refs" and isinstance(value, list):
                result[key] = [self.source(v, (*loc, i)) for i, v in enumerate(value)]
            elif key == "trip_focus_source" and value is not None:
                result[key] = self.source(value, loc)
            elif key in SOURCE_TEXT_FIELDS and value is not None:
                result[key] = self.source(value, loc)["quote"]
            else:
                result[key] = self.restore(value, loc)
        return result


def planning_envelope(prompt):
    """Only the application planning envelope selects the current wire version."""
    try:
        value = json.loads(prompt)
    except (ValueError, TypeError):
        return None
    if isinstance(value, dict) and isinstance(value.get("additional_preferences"), str):
        return value
    return None


def invalid(code, path):
    raise RequirementBoundaryError(
        code, stage="wire_mapping", errors=({"loc": tuple(path), "type": code},)
    )


def current_schema(schema):
    schema = copy.deepcopy(schema)
    selection = {
        "type": "object",
        "properties": {"first_id": {"type": "string"}, "last_id": {"type": "string"}},
        "required": ["first_id", "last_id"],
        "additionalProperties": False,
    }
    schema["$defs"]["FoundrySourceQuoteDTO"] = selection

    def sources(node):
        if isinstance(node, dict):
            if "description" in node:
                node["description"] = node["description"].replace(
                    "Exact original quote/zero-based occurrence pairs.",
                    "Original source_spans first_id/last_id pairs.",
                )
            for field, value in node.get("properties", {}).items():
                if field in SOURCE_TEXT_FIELDS:
                    nullable = any(v.get("type") == "null" for v in value.get("anyOf", []))
                    node["properties"][field] = (
                        {"anyOf": [selection, {"type": "null"}]} if nullable else selection
                    )
            for value in list(node.values()):
                sources(value)
        elif isinstance(node, list):
            for value in node:
                sources(value)

    sources(schema)
    item = {"$ref": "#/$defs/FoundryDailyPaceDTO"}
    schema["properties"]["daily_pace"] = {
        "type": "object",
        "properties": {
            "trip_default": item,
            "date_overrides": {"type": "array", "items": item},
        },
        "required": ["trip_default", "date_overrides"],
        "additionalProperties": False,
    }
    return schema


def restore_current(payload, spans):
    value = copy.deepcopy(payload)
    pace = value.get("daily_pace") if isinstance(value, dict) else None
    if (
        not isinstance(pace, dict)
        or set(pace) != {"trip_default", "date_overrides"}
        or not isinstance(pace["trip_default"], dict)
        or pace["trip_default"].get("date", "missing") is not None
        or not isinstance(pace["date_overrides"], list)
    ):
        invalid("invalid_daily_pace_default", ("daily_pace", "trip_default"))
    for i, override in enumerate(pace["date_overrides"]):
        if not isinstance(override, dict) or override.get("date") is None:
            invalid("invalid_daily_pace_override", ("daily_pace", "date_overrides", i))
    value = spans.restore(value)
    pace = value["daily_pace"]
    value["daily_pace"] = [pace["trip_default"], *pace["date_overrides"]]
    return value


def _replace_instruction(prompt, before, after):
    if prompt.count(before) != 1:
        raise RequirementBoundaryError(
            "requirement_prompt_version_mismatch",
            stage="configuration",
            category="configuration_failure",
            errors=({"loc": ("system_prompt",), "type": "instruction_version_mismatch"},),
        )
    return prompt.replace(before, after, 1)


def current_prompt(prompt):
    """Project the historical instructions together with their new wire representation."""
    prompt = _replace_instruction(prompt, "shared requirements 4", "shared requirements 5")
    prompt = _replace_instruction(
        prompt,
        "preference_prompt_19 / preference_draft_12",
        "preference_prompt_20 / preference_draft_13",
    )
    prompt = _replace_instruction(
        prompt,
        "copied EXACTLY including casing and punctuation, each <=320 Unicode code "
        "points. occurrence is\n"
        "zero-based among exact occurrences, including repeated quotes. Do not "
        "return offsets or hashes.",
        "selected using source_spans endpoints, each <=320 Unicode code points. Return\n"
        "{first_id,last_id}; the application restores text, occurrence and offsets. "
        "Never copy quotes.",
    )
    prompt = _replace_instruction(
        prompt, "provide that quote and occurrence", "select that source interval"
    )
    prompt = _replace_instruction(
        prompt, "exact quote/occurrence pairs", "source-span endpoint pairs"
    )
    prompt = _replace_instruction(
        prompt,
        "Use exact original text, including case and punctuation; never rewrite "
        "quotes or guess occurrence.",
        "Select original source intervals using their IDs; never author quote text "
        "or occurrence values.",
    )
    prompt = _replace_instruction(
        prompt,
        '{"quote":"I want to visit the Bronx Zoo in New York.","occurrence":0}',
        '{"first_id":"<first-source-id>","last_id":"<last-source-id>"}',
    )
    prompt = _replace_instruction(
        prompt,
        "Return one default record with date=null\nand at most one override for each "
        "requested date.",
        "Return daily_pace={trip_default:{date:null,profile,exact_count,source_refs},\n"
        "date_overrides:[]} with at most one dated override for each requested date.",
    )
    prompt = _replace_instruction(
        prompt,
        "ordinary without an expressed pace may use [].",
        "ordinary trip_default without an expressed pace uses source_refs=[].",
    )
    return prompt + (
        "\ntransport_constraint is null without an exclusive hard mode restriction. "
        "Otherwise return "
        "allowed_modes, requirement_refs pointing to the corresponding hard constraint/transport "
        "semantic handles, and their exact source_refs. It applies to the whole party/trip. Keep "
        "the single-mode transport_preference as a soft preference. A clear "
        "WALK/TRANSIT-only clause "
        "is supported; preserve its hard semantic requirement and link it, rather than asking for "
        "clarification. Independent unsupported hard conditions remain separate.\n"
        "\nSource transport: source_spans is an ordered application-owned inventory. "
        "Every source_refs "
        "entry and trip_focus_source uses {first_id,last_id}. The source_text, target_source_text, "
        "scope_text and date_source_text fields use the same selection object or schema-permitted "
        "null. Endpoints are inclusive; all original text between them is retained, including "
        "whitespace. IDs belong to this request only. Select the smallest sufficient interval.\n"
    )
