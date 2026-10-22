import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { TripDetail } from "./TripDetail";
import type { ProductDetail } from "./types";

afterEach(() => vi.unstubAllGlobals());

it("refreshes place metadata only through the explicit disclosure action", async () => {
  const endpoint = "/api/trips/offline/media";
  let reads = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url !== endpoint) return Response.json({ status: "unavailable" });
    reads++;
    return Response.json({ items: reads === 1 ? {} : { "activity:museum": { status: "available", kind: "verified_place", provider: "Google Maps", image_url: "https://lh3.googleusercontent.com/offline-fixture" } } });
  }));
  const detail: ProductDetail = { schema_version: "product_detail_1", id: "offline", title: "A city day", destination: "Sydney", provenance: "generated", trust: "generated_projection", request: null, days: [{ date: "2026-10-22", activities: [{ activity_id: "museum", title: "City museum", time_use: "scheduled", start_time: "2026-10-22T10:00:00+11:00", end_time: "2026-10-22T11:00:00+11:00" }] }], transfers: [], nearby: [] };
  render(<MemoryRouter><TripDetail detail={detail} mediaEndpoint={endpoint} /></MemoryRouter>);
  await waitFor(() => expect(reads).toBe(1));
  expect(screen.queryByRole("img", { name: "City museum · place photograph" })).not.toBeInTheDocument();
  expect(screen.getByText("Refresh place photos")).not.toBeVisible();
  fireEvent.click(screen.getByText("Source and travel information"));
  fireEvent.click(screen.getByRole("button", { name: "Refresh place photos" }));
  expect(await screen.findByRole("img", { name: "City museum · place photograph" })).toBeVisible();
  expect(reads).toBe(2);
});
