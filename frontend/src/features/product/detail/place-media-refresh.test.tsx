import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterAll, afterEach, beforeAll, expect, it, vi } from "vitest";
import { TripDetail } from "./TripDetail";
import type { ProductDetail } from "./types";

const original = HTMLDialogElement.prototype.showModal;
beforeAll(() => { HTMLDialogElement.prototype.showModal = function () { this.open = true; }; });
afterAll(() => { HTMLDialogElement.prototype.showModal = original; });
afterEach(() => vi.unstubAllGlobals());

it("shows photographs in the itinerary before opening details and keeps full source links in the dialog", async () => {
  const endpoint = "/api/trips/offline/media";
  let reads = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url !== endpoint) return Response.json({ status: "unavailable" });
    reads++;
    return Response.json({ items: { "activity:museum": { status: "available", kind: "verified_place", provider: "Google Maps", image_url: "https://lh3.googleusercontent.com/offline-fixture", source_url: "https://www.google.com/maps/photo/fixture", authors: [{ name: "Museum Photographer", url: "https://www.google.com/maps/contrib/123" }] } } });
  }));
  const detail: ProductDetail = { schema_version: "product_detail_1", id: "offline", title: "A city day", destination: "Sydney", provenance: "generated", trust: "generated_projection", request: null, days: [{ date: "2026-10-22", activities: [{ activity_id: "museum", title: "City museum", time_use: "scheduled", start_time: "2026-10-22T10:00:00+11:00", end_time: "2026-10-22T11:00:00+11:00" }] }], transfers: [], nearby: [] };
  render(<MemoryRouter><TripDetail detail={detail} mediaEndpoint={endpoint} /></MemoryRouter>);
  expect(await screen.findByRole("img", { name: "City museum · place photograph" })).toBeVisible();
  expect(screen.queryByRole("link", { name: "Museum Photographer" })).not.toBeInTheDocument();
  expect(screen.queryByText("Google Maps")).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Photo source" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "View City museum" }));
  const dialog = screen.getByRole("dialog");
  await waitFor(() => expect(reads).toBe(1));
  fireEvent.click(within(dialog).getByRole("button", { name: "Refresh place photos" }));
  expect(await within(dialog).findByRole("img", { name: "City museum · place photograph" })).toBeVisible();
  expect(within(dialog).getByRole("link", { name: "Museum Photographer" })).toBeVisible();
  expect(within(dialog).getByRole("link", { name: "Photo source" })).toHaveAttribute("href", "https://www.google.com/maps/photo/fixture");
  expect(screen.getAllByRole("img", { name: "City museum · place photograph" })).toHaveLength(2);
  fireEvent.click(within(dialog).getByRole("button", { name: "Close dialog" }));
  expect(screen.getByRole("img", { name: "City museum · place photograph" })).toBeVisible();
  expect(screen.queryByRole("link", { name: "Photo source" })).not.toBeInTheDocument();
});
