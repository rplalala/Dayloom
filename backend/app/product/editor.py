"""Versioned incomplete editor snapshots, separate from generation validation."""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

Text = Annotated[str, StringConstraints(strict=True, max_length=24000)]
ShortText = Annotated[str, StringConstraints(strict=True, max_length=500)]
Interest = Literal[
    "City walks",
    "History & culture",
    "Art & museums",
    "Nature",
    "Local food",
    "Photography",
    "Family experiences",
    "Free exploration",
]
Transport = Literal["walk", "transit", "drive"]
INTEREST_PROMPTS = {
    "City walks": "Enjoy neighborhood walks, local architecture and everyday city life.",
    "History & culture": "Explore historic districts, cultural landmarks and museums.",
    "Art & museums": "Visit art galleries and museums, with time to enjoy each stop.",
    "Nature": "Enjoy parks, waterfronts and gentle outdoor experiences.",
    "Local food": "Discover local food, with optional places to eat along the way.",
    "Photography": "Include scenic viewpoints and time for photography.",
    "Family experiences": "Include family-friendly experiences and time to rest.",
    "Free exploration": "Leave some unscheduled time for independent exploration.",
}
PACE_PROMPTS = {
    "relaxed": "Travel pace: relaxed. Allow generous time at each stop and fewer transfers.",
    "balanced": "Travel pace: balanced. Balance the main sights with time to rest.",
    "rich": "Travel pace: rich. Include more experiences where time and connections allow.",
}


class Binding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: ShortText
    start: StrictInt
    end: StrictInt
    text: ShortText

    @field_validator("key")
    @classmethod
    def supported_key(cls, value):
        if value not in {"pace", "transport", *(f"interest:{key}" for key in INTEREST_PROMPTS)}:
            raise ValueError("Unsupported binding key")
        return value


class EditorSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    editor_version: Literal[1]
    destination: ShortText
    start_date: ShortText
    end_date: ShortText
    travelers: ShortText
    budget: ShortText
    currency: ShortText
    required: Text
    exclusions: Text
    preferences: Text
    interests: list[Interest] = Field(max_length=8)
    pace: Literal["relaxed", "balanced", "rich"] | None
    transport: list[Transport] = Field(max_length=3)
    bindings: list[Binding] = Field(max_length=10)

    @field_validator("editor_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Unsupported editor version")
        return value

    @model_validator(mode="after")
    def supported_controls(self):
        for value in self.model_dump().values():
            if isinstance(value, str) and (
                "\x00" in value or any(0xD800 <= ord(c) <= 0xDFFF for c in value)
            ):
                raise ValueError("Text must contain valid Unicode without null characters")
        if self.currency not in {
            "AUD",
            "USD",
            "EUR",
            "GBP",
            "CNY",
            "JPY",
            "CAD",
            "NZD",
            "SGD",
            "HKD",
            "CHF",
            "KRW",
            "INR",
            "THB",
            "MYR",
            "IDR",
            "VND",
            "PHP",
            "AED",
            "ZAR",
        }:
            raise ValueError("Unsupported currency")
        if len(set(self.interests)) != len(self.interests) or len(set(self.transport)) != len(
            self.transport
        ):
            raise ValueError("Repeated preference controls")
        expected = {f"interest:{v}": INTEREST_PROMPTS[v] for v in self.interests}
        if self.pace:
            expected["pace"] = PACE_PROMPTS[self.pace]
        if self.transport:
            labels = {"walk": "walking", "transit": "public transit", "drive": "driving"}
            expected["transport"] = (
                "Prefer " + " and ".join(labels[v] for v in self.transport) + " where practical."
            )
        # Browser offsets count UTF-16 code units, including astral user text.
        encoded = self.preferences.encode("utf-16-le")
        valid = []
        for item in self.bindings:
            segment = encoded[item.start * 2 : item.end * 2].decode("utf-16-le", errors="replace")
            if (
                0 <= item.start < item.end
                and item.end * 2 <= len(encoded)
                and expected.get(item.key) == item.text == segment
                and sum(v.key == item.key for v in self.bindings) == 1
                and not any(
                    v is not item and v.start < item.end and v.end > item.start
                    for v in self.bindings
                )
            ):
                valid.append(item)
            else:
                if item.key == "pace":
                    self.pace = None
                elif item.key == "transport":
                    self.transport = []
                else:
                    self.interests = [v for v in self.interests if item.key != f"interest:{v}"]
        self.bindings = valid
        return self
