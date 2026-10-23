"""Public fixed r7 examples, explicitly projected from bundled source fixtures."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.product.detail import ExampleCard, ProductDetail

router = APIRouter(prefix="/api/examples", tags=["Product examples"])
FIXTURES = Path(__file__).with_name("examples")
COLLECTION = ("sydney-example", "kyoto-design", "melbourne-design")


def example_detail(example_id: str) -> ProductDetail:
    """Only named bundled fixtures can cross this boundary; no client path is used."""
    if example_id not in (*COLLECTION, "nearby-linking"):
        raise HTTPException(404, "Example not found")
    source = json.loads((FIXTURES / f"{example_id}.json").read_text(encoding="utf-8"))
    activity_fields = {
        "activity_id",
        "title",
        "time_use",
        "place_name",
        "location",
        "category",
        "start_time",
        "end_time",
        "estimated_cost",
        "notes",
        "introduction",
    }
    nearby_fields = {
        "place_name",
        "anchor_activity_id",
        "associated_day",
        "reason",
        "area",
        "uncertainty",
        "attribution",
    }
    transfer_fields = {
        "from_activity_id",
        "to_activity_id",
        "departure_time",
        "arrival_time",
        "preceding_end_time",
        "following_start_time",
        "mode",
        "provider_duration_seconds",
        "distance_meters",
        "reserve_seconds",
        "unknowns",
        "attribution",
    }
    return ProductDetail.model_validate(
        {
            **{
                key: source[key]
                for key in ("title", "destination", "start_date", "end_date", "description")
                if key in source
            },
            "id": example_id,
            "illustration_key": source.get("cover"),
            "display_tags": [
                *source.get("interests", []),
                *([source["pace"] + " pace"] if source.get("pace") else []),
            ],
            "provenance": "example",
            "trust": "source_fixture",
            "days": [
                {
                    "date": day["date"],
                    "activities": [
                        {
                            **{k: v for k, v in a.items() if k in activity_fields},
                            "illustration_key": a.get("image_key"),
                        }
                        for a in day.get("activities", [])
                    ],
                    "weather": {"summary": day["weather_note"]}
                    if day.get("weather_note")
                    else None,
                }
                for day in source.get("days", [])
            ],
            "nearby": [
                {
                    **{k: v for k, v in n.items() if k in nearby_fields},
                    "illustration_key": n.get("image_key"),
                }
                for n in source.get("nearby", [])
            ],
            "transfers": [
                {
                    **{k: v for k, v in t.items() if k in transfer_fields},
                    "status": "source_claim",
                    "source_status": t.get("validation_state"),
                    "estimate_kind": "unverified",
                }
                for t in source.get("transfers", [])
            ],
        }
    )


@router.get("", response_model=list[ExampleCard])
def list_examples() -> list[ExampleCard]:
    return [
        ExampleCard(
            id=d.id,
            created_at=json.loads(
                (FIXTURES / f"{d.id}.json").read_text(encoding="utf-8")
            ).get("created_at"),
            illustration_key=d.illustration_key,
            stop_count=sum(a.time_use != "free_window" for day in d.days for a in day.activities),
            transfer_count=len(d.transfers),
            title=d.title,
            destination=d.destination,
            start_date=d.start_date,
            end_date=d.end_date,
            day_count=len(d.days),
            description=d.description,
        )
        for d in map(example_detail, COLLECTION)
    ]


@router.get("/{example_id}", response_model=ProductDetail)
def read_example(example_id: str) -> ProductDetail:
    return example_detail(example_id)
