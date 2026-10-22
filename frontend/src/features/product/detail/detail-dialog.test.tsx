import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { TripDetail } from "./TripDetail";
import type { ProductDetail } from "./types";

const detail: ProductDetail = {
  schema_version: "product_detail_1", id: "dialog", title: "A city day", destination: "Sydney",
  provenance: "imported", trust: "unverified_import", request: null,
  days: [{ date: "2026-10-22", activities: [{ activity_id: "museum", title: "City museum", time_use: "scheduled", start_time: "2026-10-22T10:00:00+11:00", end_time: "2026-10-22T11:00:00+11:00", location: "Museum street", introduction: "A collection of city stories.", notes: "Check access before travel.", estimated_cost: { currency: "AUD", amount: "0" } }] }],
  nearby: [], transfers: [{ from_activity_id: "museum", to_activity_id: "next", mode: "WALK", provider_duration_seconds: 0, distance_meters: 0, estimate_kind: "provider", status: "source_claim", validation_state: "PASS", unknowns: ["Opening hours were not checked."] }],
};

it("opens the same activity photograph and labeled visit details without implying a free unknown cost", async () => {
  render(<MemoryRouter><TripDetail detail={detail} /></MemoryRouter>);
  await userEvent.click(screen.getByRole("button", { name: "View City museum" }));
  const dialog = screen.getByRole("dialog");
  expect(dialog.querySelector(".photo-large")).toBeVisible();
  expect(within(dialog).getByText("Planned visit")).toBeVisible();
  expect(within(dialog).getByText("About this place")).toBeVisible();
  expect(within(dialog).getByText("Estimated cost")).toBeVisible();
  expect(within(dialog).getByText("AUD 0")).toBeVisible();
  expect(within(dialog).getByRole("link", { name: "View on map" })).toHaveAttribute("rel", "noopener noreferrer");
});

it("preserves zero route measurements and unverified claims in structured connection details", async () => {
  render(<MemoryRouter><TripDetail detail={detail} /></MemoryRouter>);
  await userEvent.click(screen.getByRole("button", { name: "WALK · 0 min · Travel time to confirm →" }));
  const dialog = screen.getByRole("dialog");
  expect(dialog.querySelector(".route-big-stats")).toBeVisible();
  expect(within(dialog).getByText("0 min")).toBeVisible();
  expect(within(dialog).getByText("0 m")).toBeVisible();
  expect(within(dialog).getByText(/Travel time for this itinerary has not been checked/)).toBeVisible();
  expect(within(dialog).getByText(/Check current routes before you travel/)).toBeVisible();
});
