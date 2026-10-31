"""One trusted final Product projection into the durable public detail contract."""

from uuid import uuid4

from backend.app.product.detail import ProductDetail


def generated_detail(result, request):
    itinerary = result.itinerary.model_dump(mode="json")
    nearby, days = [], []
    for day in itinerary["days"]:
        weather = day["weather"]
        forecast = weather["forecast"]
        public_weather = None
        if weather["status"] == "available" and forecast:
            public_weather = {
                key: value
                for key, value in forecast.items()
                if key
                in {
                    "summary",
                    "temperature_min_c",
                    "temperature_max_c",
                    "precipitation_probability_percent",
                    "max_wind_speed_kph",
                }
            }
            public_weather.update(
                attribution=weather["attribution"], source_url=weather["source_url"]
            )
            public_weather.update(
                summary=forecast.get("condition"),
                temperature_min_c=forecast.get("min_temperature_c"),
                temperature_max_c=forecast.get("max_temperature_c"),
            )
        activities = []
        for activity in day["activities"]:
            nearby.extend(activity.pop("nearby"))
            activity["time_use"] = activity["time_use"] or "scheduled"
            activities.append(activity)
        days.append({"date": day["date"], "activities": activities, "weather": public_weather})
    transfers = [
        {
            **transfer,
            "status": "unknown" if transfer["validation_state"] == "UNKNOWN" else "confirmed",
        }
        for transfer in itinerary["transfers"]
    ]
    detail = ProductDetail(
        id=str(uuid4()),
        title=f"{itinerary['destination']} journey",
        provenance="generated",
        trust="generated_projection",
        destination=itinerary["destination"],
        start_date=itinerary["start_date"],
        end_date=itinerary["end_date"],
        request=request.model_dump(mode="json", exclude={"input_version", "request_id"}),
        days=days,
        nearby=nearby,
        transfers=transfers,
        completion={
            "attention_items": result.attention_items,
            "required_experiences": result.required_experiences,
            "pace_review": result.pace_review,
            "policy_completion": result.policy_completion,
            "policy_reasons": result.policy_reasons,
            "preference_coverage": result.preference_coverage,
            "minimum_daily_coverage": result.minimum_daily_coverage,
        },
    )
    detail._media_bindings = dict(result._media_bindings)
    return detail
