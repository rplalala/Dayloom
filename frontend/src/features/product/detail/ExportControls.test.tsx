import { fireEvent, render, screen, within } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { ExportControls } from "./ExportControls";
import type { ProductDetail } from "./types";

const detail: ProductDetail = { schema_version: "product_detail_1", id: "example", title: "A city day", destination: "Sydney", provenance: "example", trust: "source_fixture", request: null, days: [], transfers: [], nearby: [] };
afterEach(() => { vi.unstubAllGlobals(); });

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
  expect((within(dialog).getByRole("textbox", { name: "Itinerary summary" }) as HTMLTextAreaElement).value).toContain("Historical example · source claims");
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
