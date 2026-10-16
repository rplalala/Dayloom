"""Project synthetic legacy fixture meanings into the current source-selection wire."""

import copy
import json

from backend.app.llm.azure_foundry.requirement_wire import SOURCE_TEXT_FIELDS


def current_response(payload, request):
    """Only transform mocked current-wire responses; never modify saved evidence."""
    body = json.loads(request.content)
    if body.get("text", {}).get("format", {}).get("name") not in {
        "PreferenceDraftV13",
        "PreferenceDraftV14",
    }:
        return payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return payload
    payload = copy.deepcopy(payload)
    content = body["input"][-1]["content"]
    prompt = json.loads(content if isinstance(content, str) else content[0]["text"])
    text = prompt["additional_preferences"]
    inventory = prompt["source_spans"]
    first_key, last_key = (
        ("first_ref", "last_ref")
        if inventory and type(inventory[0]["id"]) is int
        else ("first_id", "last_id")
    )
    # Derive intervals independently from the supplied inventory's original token text.
    spans, offset = [], 0
    for row in inventory:
        start = text.index(row["text"], offset)
        spans.append((start, start + len(row["text"]), row["id"]))
        offset = spans[-1][1]

    def select(quote, occurrence=0):
        start = -1
        for _ in range(occurrence + 1):
            start = text.find(quote, start + 1)
            if start < 0:
                return {first_key: -1, last_key: -1}
        chosen = [row for row in spans if row[1] > start and row[0] < start + len(quote)]
        return {first_key: chosen[0][2], last_key: chosen[-1][2]}

    def encode(node):
        if isinstance(node, list):
            return [encode(v) for v in node]
        if not isinstance(node, dict):
            return node
        if set(node) == {"quote", "occurrence"}:
            return select(node["quote"], node["occurrence"])
        return {
            key: select(value)
            if key in SOURCE_TEXT_FIELDS and isinstance(value, str)
            else encode(value)
            for key, value in node.items()
        }

    payload = encode(payload)
    if isinstance(payload, dict) and "daily_pace" in payload:
        pace = payload["daily_pace"]
        default = next(
            (p for p in pace or [] if p["date"] is None),
            {"date": None, "profile": "ordinary", "exact_count": None, "source_refs": []},
        )
        payload["daily_pace"] = {
            "trip_default": default,
            "date_overrides": [p for p in pace or [] if p["date"] is not None],
        }
        payload.setdefault("transport_constraint", None)
    return payload
