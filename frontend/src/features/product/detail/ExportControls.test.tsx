import { fireEvent, render, screen, within } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { ExportControls } from "./ExportControls";
import type { ProductDetail } from "./types";

const detail: ProductDetail = { schema_version: "product_detail_1", id: "example", title: "A city day", destination: "Sydney", provenance: "example", trust: "source_fixture", request: null, days: [], transfers: [], nearby: [] };
afterEach(() => { vi.unstubAllGlobals(); });

it("offers a readable summary without internal review fields or record identifiers", async () => {
  vi.stubGlobal("navigator", {});
  render(<ExportControls detail={{ ...detail, completion: { policy_completion: "incomplete", policy_reasons: ["internal_reason_code"], preference_coverage: [], minimum_daily_coverage: [] }, transfers: [{ from_activity_id: "private_from", to_activity_id: "private_to", estimate_kind: "provider", status: "unknown", unknowns: ["internal_route_reason"] }], nearby: [{ place_name: "A garden", anchor_activity_id: "private_anchor" }] }} />);
  fireEvent.click(screen.getByRole("button", { name: "Copy summary" }));
  const dialog = await screen.findByRole("dialog", { name: "Copy your itinerary summary" });
  const text = (within(dialog).getByRole("textbox", { name: "Itinerary summary" }) as HTMLTextAreaElement).value;
  expect(text).toContain("A garden");
  expect(text).toContain("Travel time to confirm");
  expect(text).not.toMatch(/internal_|private_|policy_completion|estimate_kind|source claims|evidence snapshot/);
});

it("reports successful clipboard copying without opening the manual fallback", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  render(<StrictMode><ExportControls detail={detail} /></StrictMode>);
  fireEvent.click(screen.getByRole("button", { name: "Copy summary" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Itinerary summary copied.");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(writeText).toHaveBeenCalledWith(expect.stringContaining("A city day"));
});

it.each(["rejected", "unavailable"])("opens a selectable summary only when clipboard access is %s", async state => {
  vi.stubGlobal("navigator", state === "rejected" ? { clipboard: { writeText: vi.fn().mockRejectedValue(new Error("Controlled clipboard denial")) } } : {});
  render(<StrictMode><ExportControls detail={detail} /></StrictMode>);
  fireEvent.click(screen.getByRole("button", { name: "Copy summary" }));
  const dialog = await screen.findByRole("dialog", { name: "Copy your itinerary summary" });
  expect((within(dialog).getByRole("textbox", { name: "Itinerary summary" }) as HTMLTextAreaElement).value).toContain("Example itinerary");
  fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("opens the export menu with native close controls and unchanged download actions", () => {
  render(<StrictMode><ExportControls detail={detail} /></StrictMode>);
  fireEvent.click(screen.getByRole("button", { name: "Export itinerary" }));
  const dialog = screen.getByRole("dialog", { name: "Take your itinerary with you." });
  expect(within(dialog).getByRole("button", { name: "Export text" })).toBeVisible();
  expect(within(dialog).getByRole("button", { name: "Export JSON" })).toBeVisible();
  fireEvent.click(within(dialog).getByRole("button", { name: "Close dialog" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("keeps content and dialog padding clicks open and dismisses only an outside backdrop click", () => {
  render(<ExportControls detail={detail} />);
  fireEvent.click(screen.getByRole("button", { name: "Export itinerary" }));
  const dialog = screen.getByRole("dialog");
  vi.spyOn(dialog, "getBoundingClientRect").mockReturnValue({ left: 100, right: 500, top: 100, bottom: 400 } as DOMRect);
  fireEvent.click(within(dialog).getByRole("heading"), { clientX: 0, clientY: 0 });
  expect(dialog).toBeVisible();
  fireEvent.click(dialog, { clientX: 105, clientY: 105 });
  expect(dialog).toBeVisible();
  fireEvent.click(dialog, { clientX: 50, clientY: 50 });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
