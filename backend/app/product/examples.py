"""Two public historical V3 itineraries, projected through the normal Product contract."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.product.detail import ExampleCard, ProductDetail

router = APIRouter(prefix="/api/examples", tags=["Product examples"])
FIXTURES = Path(__file__).with_name("examples")
COLLECTION = ("sydney-example", "london-example")


def example_source(example_id: str) -> dict:
    """The server allowlist is the sole source of public example and photo authority."""
    if example_id not in COLLECTION:
        raise HTTPException(404, "Example not found")
    return json.loads((FIXTURES / f"{example_id}.json").read_text(encoding="utf-8"))


def example_detail(example_id: str) -> ProductDetail:
    source = example_source(example_id)
    detail = ProductDetail.model_validate(source["detail"])
    detail._media_bindings = dict(source["media_bindings"])
    return detail


@router.get("", response_model=list[ExampleCard])
def list_examples() -> list[ExampleCard]:
    return [
        ExampleCard(
            id=d.id,
            created_at=example_source(d.id)["created_at"],
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
