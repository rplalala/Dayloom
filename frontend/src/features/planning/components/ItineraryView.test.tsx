import { render, screen, within, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { Itinerary, ReferenceRecommendation } from "../types";
import { ItineraryView } from "./ItineraryView";

const base: Itinerary = {
  destination: "Example city", start_date: "2026-09-21", end_date: "2026-09-21",
  days: [{ date: "2026-09-21", activities: [{
    activity_id: "a", title: "Primary visit", place_name: "Museum", location: null,
    start_time: "2026-09-21T10:00:00+10:00", end_time: "2026-09-21T11:00:00+10:00",
    estimated_cost: null, notes: null,
  }] }],
};
const suggestion: ReferenceRecommendation = {
  place_name: "Optional cafe", source_place_id: null, source_ref: null,
  reason: "An extra place to consider", associated_day: null, area: null, uncertainty: null,
};

it("distinguishes discretionary availability from an occupied movable activity", () => {
  const plan = structuredClone(base);
  plan.days[0].activities[0].time_use = "free_window";
  render(<ItineraryView itinerary={plan} />);
  expect(screen.getByText("Free window — optional suggestions")).toBeInTheDocument();
});

it("shows soft preference gaps without labeling the itinerary incomplete", () => {
  render(<ItineraryView itinerary={base} policyCompletion="complete" preferenceCoverage={[{
    preference: "Museums", target: 2, scheduled: 1, remaining: 1, status: "gap",
    target_origin: "current_trip_focus", basis: "model_semantic_judgment_not_operating_fact",
  }]} />);
  expect(screen.getByText(/Museums: 1 of 2/)).toBeInTheDocument();
  expect(screen.getByText(/1 remaining/)).toBeInTheDocument();
  expect(screen.queryByText(/This itinerary is incomplete/)).toBeNull();
  expect(screen.getByText(/not verified suitability/)).toBeInTheDocument();
});

it("shows policy incompleteness without hiding the adopted itinerary", () => {
  render(<ItineraryView itinerary={base} policyCompletion="incomplete" />);
  expect(screen.getByRole("status")).toHaveTextContent("This itinerary is incomplete");
  expect(screen.getByText("Primary visit")).toBeInTheDocument();
});

it("renders final daily weather, optional introduction and nested Nearby as text", () => {
  const day = base.days[0];
  render(<ItineraryView itinerary={{ ...base, days: [{ ...day,
    weather: { status: "available", forecast: { date: day.date, condition: "Cloudy", min_temperature_c: 0,
      max_temperature_c: 18, precipitation_probability_percent: 0, max_wind_speed_kph: null },
      attribution: "Weather attribution", source_url: "https://open-meteo.com/" },
    activities: [{ ...day.activities[0], introduction: "A local history museum.", nearby: [{
      place_name: "<script>cafe</script>", reason: "An optional stop", associated_day: day.date,
      anchor_activity_id: "a", area: null, uncertainty: "Hours unknown", attribution: "Google Places",
    }] }],
  }] }} />);
  expect(screen.getByText("Low: 0 °C")).toBeInTheDocument();
  expect(screen.getByText("Chance of rain: 0%")).toBeInTheDocument();
  expect(screen.getByText("A local history museum.")).toBeInTheDocument();
  const nearby = screen.getByRole("region", { name: "Nearby Museum" });
  expect(nearby.closest("article")).toHaveTextContent("Primary visit");
  expect(nearby).toHaveClass("nearby-list");
  expect(within(nearby).getByText("<script>cafe</script>")).toBeInTheDocument();
  expect(nearby.querySelector("script")).toBeNull();
  expect(within(nearby).queryByText(/Estimated cost|10:00/)).toBeNull();
});

it("keeps forecast facts in a compact strip with accessible source details", () => {
  const day = base.days[0];
  render(<ItineraryView itinerary={{ ...base, days: [{ ...day, weather: {
    status: "available", forecast: { date: day.date, condition: "Cloudy",
      min_temperature_c: 0, max_temperature_c: 18,
      precipitation_probability_percent: 0, max_wind_speed_kph: 12 },
    attribution: "Weather attribution", source_url: "https://open-meteo.com/",
  } }] }} />);
  const weather = screen.getByLabelText("Daily weather");
  expect(weather).toHaveClass("weather-strip");
  expect(within(weather).getByText("Cloudy")).toBeInTheDocument();
  expect(within(weather).getByText("Maximum wind: 12 km/h")).toBeInTheDocument();
  expect(within(weather).getByRole("link", { name: "Open-Meteo" })).toHaveAttribute("href", "https://open-meteo.com/");
  expect(within(weather).getByText("Weather attribution").closest("details")).not.toBeNull();
  expect(screen.getByText("Primary visit")).toBeInTheDocument();
});

it("renders unavailable weather and unknown transport without false attribution", () => {
  render(<ItineraryView itinerary={{ ...base,
    days: [{ ...base.days[0], weather: { status: "unavailable", forecast: null, attribution: null, source_url: null } }],
    transfers: [{ from_activity_id: "before", to_activity_id: "a", mode: null,
      provider_duration_seconds: null, distance_meters: null, reserve_seconds: 0,
      validation_state: "UNKNOWN", unknowns: [], estimate_kind: "unverified" }],
  }} />);
  expect(screen.getByText(/Weather information is unavailable/)).toBeInTheDocument();
  expect(screen.getByText(/Transport unverified: Time unknown/)).toBeInTheDocument();
  expect(screen.queryByText(/Google|Open-Meteo/)).toBeNull();
});
afterEach(cleanup);
describe("Itinerary reference roles", () => {
  it.each([undefined, []])("hides empty and historical references", (references) => {
    render(<ItineraryView itinerary={{ ...base, reference_recommendations: references }} />);
    expect(screen.queryByRole("region", { name: "Optional reference recommendations" })).not.toBeInTheDocument();
    expect(screen.getByText("10:00–11:00")).toBeInTheDocument();
  });
  it("separates model suggestions from timed visits and committed costs", () => {
    render(<ItineraryView itinerary={{ ...base, reference_recommendations: [suggestion] }} />);
    const section = screen.getByRole("region", { name: "Optional reference recommendations" });
    expect(within(section).getByText("Optional cafe")).toBeInTheDocument();
    expect(within(section).getByText(/Model-generated suggestion; not live-verified/)).toBeInTheDocument();
    expect(within(section).getByText(/No bookings have been made/)).toBeInTheDocument();
    expect(within(section).queryByText(/10:00|Estimated cost|Suggested day/)).not.toBeInTheDocument();
    expect(within(section).getAllByRole("article")).toHaveLength(1);
  });
  it("shows grounded source context, optional association and uncertainty without debug IDs", () => {
    render(<ItineraryView itinerary={{ ...base, reference_recommendations: [{ ...suggestion,
      source_place_id: "canonical-id", source_ref: "google_places:canonical-id",
      associated_day: "2026-09-21", area: "Old district", uncertainty: "Opening hours unknown",
    }] }} />);
    expect(screen.getByText(/Linked to supplied place information/)).toBeInTheDocument();
    expect(screen.getByText("Suggested day: 2026-09-21")).toBeInTheDocument();
    expect(screen.getByText("Old district")).toBeInTheDocument();
    expect(screen.getByText("Opening hours unknown")).toBeInTheDocument();
    expect(screen.queryByText(/canonical-id/)).not.toBeInTheDocument();
  });
});


describe("Adopted structured transfers", () => {
  it.each([
    ["WALK", "Walk", 720, 800, 0],
    ["TRANSIT", "Public transport", 1500, 4300, 0],
    ["DRIVE", "Car transport", 1080, 7200, 600],
  ] as const)("displays %s facts separately from reserves", (mode, label, seconds, metres, reserve) => {
    render(<ItineraryView itinerary={{ ...base, transfers: [{
      from_activity_id: "previous", to_activity_id: "a", mode, mode_source: "APPLICATION_DEFAULT",
      calculation_basis: "provider_estimate", provider_duration_seconds: seconds, distance_meters: metres,
      reserve_seconds: reserve, validation_state: "PASS",
      unknowns: mode === "DRIVE" ? ["Car transport must be arranged; cost and availability not verified."] : [],
    }] }} />);
    const card = screen.getByLabelText("Transfer");
    expect(within(card).getByText(new RegExp(`${label}: about ${seconds / 60} min`))).toBeInTheDocument();
    expect(card.textContent).toContain(`${(metres / 1000).toFixed(1)} km`);
    if (reserve) {
      expect(within(card).getByText(/additional 10 min/)).toBeInTheDocument();
      expect(within(card).getByText(/Car transport must be arranged/)).toBeInTheDocument();
      expect(within(card).queryByText(/about 28 min/)).not.toBeInTheDocument();
    }
    expect(within(card).queryByText(/station|subway line|rental car/i)).not.toBeInTheDocument();
  });
  it("does not invent unknown estimates or transfers for references", () => {
    render(<ItineraryView itinerary={{ ...base, reference_recommendations: [suggestion], transfers: [{
      from_activity_id: "previous", to_activity_id: "a", mode: "WALK", mode_source: "APPLICATION_DEFAULT_WALK",
      calculation_basis: "route_unknown", provider_duration_seconds: null, distance_meters: null, reserve_seconds: 0,
      validation_state: "UNKNOWN", unknowns: [],
    }] }} />);
    expect(screen.getByText(/Time unknown/)).toBeInTheDocument();
    expect(screen.getByText(/Distance unknown/)).toBeInTheDocument();
    expect(screen.getAllByLabelText("Transfer")).toHaveLength(1);
    expect(within(screen.getByRole("region", { name: "Optional reference recommendations" })).queryByLabelText("Transfer")).not.toBeInTheDocument();
  });
});


it("shows an unmet daily minimum separately from optional Nearby references", () => {
  render(<ItineraryView itinerary={{ ...base, reference_recommendations: [suggestion] }}
    minimumCoverage={[{ date: "2026-09-21", countable_primary_activities: 0,
      status: "missing", reason: "minimum_daily_coverage_missing" }]} />);
  expect(screen.getByRole("status")).toHaveTextContent("Minimum daily coverage remains unmet");
  expect(screen.getByText("Optional cafe")).toBeInTheDocument();
});

it("renders a final conflicting connection without hiding the itinerary", () => {
  render(<ItineraryView itinerary={{ ...base, transfers: [{
    from_activity_id: "previous", to_activity_id: "a", mode: "WALK",
    preceding_end_time: "2026-09-21T10:10:00+10:00",
    following_start_time: "2026-09-21T10:00:00+10:00",
    provider_duration_seconds: 720, distance_meters: 800, reserve_seconds: 0,
    validation_state: "CONFIRMED", unknowns: [], estimate_kind: "provider",
  }] }} />);
  expect(screen.getByText("Primary visit")).toBeInTheDocument();
  const card = within(screen.getByLabelText("Transfer"));
  expect(card.getByText("Transfer conflict remains.")).toBeInTheDocument();
  expect(card.getByText("10:10: Previous activity ends")).toBeInTheDocument();
  expect(card.getByText("10:00: Next activity starts")).toBeInTheDocument();
});
