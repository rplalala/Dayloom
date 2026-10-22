import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";
import { createBrief } from "./editor";

const brief = { ...createBrief(), destination: "Sydney", start_date: "2026-10-22", end_date: "2026-10-23", travelers: "2", budget: "1000" };
const request = { destination: "Sydney", start_date: brief.start_date, end_date: brief.end_date, traveler_count: 2, budget: { currency: "AUD", amount: "1000" }, additional_preferences: "" };
const account = { id: "alice", display_name: "Alice", initials: "A", csrf_token: "csrf" };
const detail = { schema_version: "product_detail_1", id: "preview-one", title: "Harbour afternoon", destination: "Sydney", start_date: brief.start_date, end_date: brief.end_date, provenance: "generated", trust: "generated_projection", request, days: [{ date: brief.start_date, activities: [{ activity_id: "one", title: "A leisurely visit", place_name: "Harbour walk", time_use: "scheduled", start_time: "2026-10-22T10:00:00+11:00", end_time: "2026-10-22T11:00:00+11:00" }] }], transfers: [], nearby: [] };
const task = { id: "task-one", state: "completed", revision: 1, request, progress: { stage: "nearby", message: "Ready" }, preview_id: "preview-one" };
afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it("opens the guest example chooser without planning or writing", async () => {
  const writes: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method && options.method !== "GET") writes.push(url);
    if (url === "/api/auth/current") return Response.json({ detail: { code: "login_required" } }, { status: 401 });
    if (url === "/api/examples") return Response.json([{ id: "kyoto", title: "Kyoto gardens" }]);
    if (url === "/api/planning/date-window") return Response.json({ allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 });
    return Response.json([]);
  }));
  const router = createMemoryRouter(routes, { initialEntries: ["/plan"] });
  render(<RouterProvider router={router} />);
  fireEvent.click(await screen.findByRole("button", { name: "Explore an example" }));
  const modal = await screen.findByRole("dialog", { name: "A little inspiration." });
  expect(await within(modal).findByRole("button", { name: "Kyoto gardens" })).toBeEnabled();
  expect(router.state.location.pathname).toBe("/plan");
  fireEvent.click(within(modal).getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});

it.each([false, true])("loads the owned saved itinerary after a decision and never resurrects a deleted result (%s)", async deleted => {
  sessionStorage.setItem("dayloom.editor.v1", JSON.stringify({ owner: "alice", brief, actionId: null, origin: "restored" }));
  const writes: string[] = [];
  const reads: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    reads.push(url);
    if (url === "/api/auth/current") return Response.json(account);
    if (url === "/api/planning/date-window") return Response.json({ allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 });
    if (url === "/api/planning/tasks/recent?limit=10") return Response.json([task]);
    if (url === "/api/previews/preview-one/save") { writes.push(url); return Response.json({ id: "preview-one", state: "saved", saved_trip_id: "saved-one", outcome: "saved" }); }
    if (url === "/api/previews/preview-one") return Response.json({ id: "preview-one", source_task_id: task.id, state: "pending", snapshot: detail, saved_trip_id: null });
    if (url === "/api/trips/saved-one") return deleted ? Response.json({ detail: { code: "not_found" } }, { status: 404 }) : Response.json({ ...detail, id: "saved-one", title: "Persisted harbour afternoon" });
    if (options?.method === "POST") writes.push(url);
    return Response.json([]);
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/plan"] })} />);
  await screen.findByRole("heading", { name: "Harbour afternoon" });
  expect(screen.getByText("Harbour walk", { selector: "strong" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Save to My trips" }));
  await waitFor(() => expect(reads).toContain("/api/trips/saved-one"));
  if (deleted) {
    await screen.findByText("This saved itinerary was deleted.");
    expect(screen.queryByRole("heading", { name: "Harbour afternoon" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "View full itinerary" })).not.toBeInTheDocument();
  } else {
    await screen.findByRole("heading", { name: "Persisted harbour afternoon" });
    expect(screen.getByRole("link", { name: "View full itinerary" })).toHaveAttribute("href", "/trips/saved-one");
    expect(screen.getByText("Saved to My trips")).toBeInTheDocument();
  }
  expect(writes).toEqual(["/api/previews/preview-one/save"]);
});

it("offers explicit draft save after an active-task conflict without replaying generation", async () => {
  sessionStorage.setItem("dayloom.editor.v1", JSON.stringify({ owner: "alice", brief, actionId: null, origin: "restored" }));
  const writes: string[] = [];
  const draft = { id: "e8a18ca5-30e0-4df1-8786-dc3b0f42a752", title: "Sydney itinerary", revision: 1, editor: brief };
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method && options.method !== "GET") writes.push(url);
    if (url === "/api/auth/current") return Response.json(account);
    if (url === "/api/planning/date-window") return Response.json({ allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 });
    if (url === "/api/planning/tasks" && options?.method === "POST") return Response.json({ detail: { code: "planning_task_active", task_id: "already-running" } }, { status: 409 });
    if (url === "/api/drafts" || url === `/api/drafts/${draft.id}`) return Response.json(draft);
    return Response.json(url.includes("operation_key") ? null : []);
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/plan"] })} />);
  await screen.findByDisplayValue("Sydney");
  fireEvent.click(screen.getByRole("button", { name: "Generate itinerary" }));
  const modal = await screen.findByRole("dialog", { name: "One journey at a time." });
  expect(writes).toEqual(["/api/planning/tasks"]);
  expect(within(modal).getByRole("link", { name: "View progress" })).toHaveAttribute("href", "/planning/already-running");
  fireEvent.click(within(modal).getByRole("button", { name: "Save travel brief" }));
  await waitFor(() => expect(screen.queryByRole("dialog", { name: "One journey at a time." })).not.toBeInTheDocument());
  expect(writes).toEqual(["/api/planning/tasks", "/api/drafts"]);
  expect(screen.getByLabelText("Destination")).toHaveValue("Sydney");
});
