import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";
import { createBrief } from "./editor";

afterEach(() => {
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

it("clears the travel brief and preference choices without submitting", async () => {
  const fetchMock = vi.fn(async (url: string) => Response.json(
    url === "/api/planning/date-window" ? { allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 } : {},
    { status: url === "/api/auth/current" ? 401 : 200 },
  ));
  vi.stubGlobal("fetch", fetchMock);
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/plan"] })} />);
  await screen.findByLabelText("Destination");
  for (const [label, value] of Object.entries({ Destination: "Sydney", "Start date": "2026-10-22", "End date": "2026-10-23", Travelers: "3", "Whole-trip budget": "2500", Currency: "NZD" })) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByText("Personalize your trip"));
  fireEvent.click(screen.getByRole("button", { name: "Nature" }));
  fireEvent.click(screen.getByRole("button", { name: "Relaxed" }));
  fireEvent.click(screen.getByRole("button", { name: "Walking" }));
  fireEvent.change(screen.getByLabelText("Places or experiences to include"), { target: { value: "Opera House" } });
  fireEvent.change(screen.getByLabelText("Places or experiences to avoid"), { target: { value: "Malls" } });
  fireEvent.click(screen.getByRole("button", { name: "Clear" }));
  for (const label of ["Destination", "Start date", "End date", "Places or experiences to include", "Places or experiences to avoid", "Additional preferences"]) {
    expect(screen.getByLabelText(label)).toHaveValue("");
  }
  expect(screen.getByLabelText("Travelers")).toHaveValue(null);
  expect(screen.getByLabelText("Whole-trip budget")).toHaveValue(null);
  expect(screen.getByLabelText("Currency")).toHaveValue("AUD");
  expect(screen.getByLabelText("Additional preferences")).not.toBeVisible();
  fireEvent.click(screen.getByText("Personalize your trip"));
  for (const name of ["Nature", "Relaxed", "Walking"]) expect(screen.getByRole("button", { name })).toHaveAttribute("aria-pressed", "false");
  expect(JSON.parse(sessionStorage.getItem("dayloom.editor.v1")!).brief.destination).toBe("");
  expect(fetchMock.mock.calls.map(([url]) => url)).not.toContain("/api/planning/tasks");
  fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "London" } });
  expect(screen.getByLabelText("Destination")).toHaveValue("London");
});

it("starts a blank brief after clearing a saved draft without changing the saved draft", async () => {
  const writes: string[] = [];
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method && options.method !== "GET") writes.push(url);
    return Response.json(url === "/api/auth/current" ? { id: "alice", display_name: "Alice", csrf_token: "token" }
      : url === "/api/planning/date-window" ? { allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 }
      : url === "/api/drafts/saved-brief" ? { id: "saved-brief", title: "Sydney idea", revision: 1, editor: { ...createBrief(), destination: "Sydney", preferences: "Quiet mornings" } }
      : []);
  });
  vi.stubGlobal("fetch", fetchMock);
  const router = createMemoryRouter(routes, { initialEntries: ["/plan?draft=saved-brief"] });
  render(<RouterProvider router={router} />);
  await waitFor(() => expect(screen.getByLabelText("Destination")).toHaveValue("Sydney"));
  fireEvent.click(screen.getByRole("button", { name: "Generate itinerary" }));
  expect(await screen.findByRole("alert")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Clear" }));
  expect(screen.getByLabelText("Destination")).toHaveValue("");
  expect(screen.getByLabelText("Additional preferences")).toHaveValue("");
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(router.state.location.search).toBe("");
  expect(screen.getByRole("button", { name: "Save draft" })).toHaveTextContent("Save travel brief");
  const recovery = JSON.parse(sessionStorage.getItem("dayloom.editor.v1")!);
  expect(recovery.draftRef).toBeNull();
  expect(recovery.draftTitle).toBe("");
  expect(recovery.actionId).toBeNull();
  expect(fetchMock.mock.calls.map(([url]) => url)).not.toContain("/api/profile");
  expect(writes).toEqual([]);
});

it("returns a guest brief through registration without generating", async () => {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      calls.push(url);
      if (url === "/api/auth/current")
        return new Response(
          JSON.stringify({ detail: { code: "login_required" } }),
          { status: 401 },
        );
      return new Response(
        JSON.stringify({
          id: "alice",
          email: "alice@example.com",
          display_name: "Alice",
          initials: "A",
          csrf_token: "csrf",
        }),
        { status: 201 },
      );
    }),
  );
  const router = createMemoryRouter(routes, { initialEntries: ["/plan"] });
  render(<RouterProvider router={router} />);
  await waitFor(() =>
    expect(screen.getByLabelText("Destination")).toBeEnabled(),
  );
  fireEvent.change(screen.getByLabelText("Destination"), {
    target: { value: "Kyoto" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Generate itinerary/ }));
  await screen.findByRole("heading", { name: "Welcome back." });
  fireEvent.click(screen.getByRole("tab", { name: "Sign up" }));
  fireEvent.change(screen.getByLabelText("Display name"), {
    target: { value: "Alice" },
  });
  fireEvent.change(screen.getByLabelText("Email address"), {
    target: { value: "alice@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), {
    target: { value: "safe password" },
  });
  fireEvent.change(screen.getByLabelText("Confirm password"), {
    target: { value: "safe password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Destination")).toHaveValue("Kyoto"),
  );
  expect(calls).not.toContain("/api/planning");
});

it("keeps optional preferences discoverable and detaches an edited sentence without deleting it", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(
    url === "/api/planning/date-window" ? { allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 } : { detail: { code: "login_required" } }
  ), { status: url === "/api/auth/current" ? 401 : 200 })));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/plan"] })} />);
  await screen.findByLabelText("Destination");
  fireEvent.click(screen.getByText("Personalize your trip"));
  const nature = await screen.findByRole("button", { name: "Nature" });
  fireEvent.click(nature);
  expect(nature).toHaveAttribute("aria-pressed", "true");
  const notes = screen.getByLabelText("Additional preferences");
  fireEvent.input(notes, { target: { value: "Enjoy quiet parks, waterfronts and gentle outdoor experiences." } });
  expect(nature).toHaveAttribute("aria-pressed", "false");
  fireEvent.click(screen.getByRole("button", { name: /Balanced/ }));
  fireEvent.click(screen.getByRole("button", { name: /Relaxed/ }));
  expect((notes as HTMLTextAreaElement).value).toContain("Enjoy quiet parks");
  fireEvent.click(screen.getByRole("button", { name: "Walking" }));
  fireEvent.click(screen.getByRole("button", { name: "Public transit" }));
  expect((notes as HTMLTextAreaElement).value).toContain("Prefer walking and public transit where practical.");
  expect(screen.getByLabelText("Places or experiences to include")).toBeVisible();
  expect(screen.getByLabelText("Places or experiences to avoid")).toBeVisible();
});

it("starts with essentials and keeps optional values when their section is collapsed", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => Response.json(
    url === "/api/planning/date-window" ? { allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 } : {},
    { status: url === "/api/auth/current" ? 401 : 200 },
  )));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/plan"] })} />);
  await screen.findByLabelText("Destination");
  expect(screen.getByRole("button", { name: "Generate itinerary" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Planning progress" })).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Your itinerary" })).not.toBeInTheDocument();
  const notes = screen.getByLabelText("Additional preferences");
  expect(notes).not.toBeVisible();
  const disclosure = screen.getByText("Personalize your trip");
  fireEvent.click(disclosure);
  expect(notes).toBeVisible();
  fireEvent.input(notes, { target: { value: "Step-free access and a quiet afternoon" } });
  fireEvent.click(disclosure);
  expect(notes).not.toBeVisible();
  fireEvent.click(disclosure);
  expect(notes).toHaveValue("Step-free access and a quiet afternoon");
});


it("keeps the submitted itinerary separate while the traveler edits another brief", async () => {
  const brief = { editor_version: 1, destination: "Sydney", start_date: "2026-10-22", end_date: "2026-10-23", travelers: "2", budget: "1000", currency: "AUD", required: "", exclusions: "", preferences: "", interests: [], pace: null, transport: [], bindings: [] };
  sessionStorage.setItem("dayloom.editor.v1", JSON.stringify({ owner: "alice", brief, actionId: null }));
  const request = { destination: "Sydney", start_date: "2026-10-22", end_date: "2026-10-23", traveler_count: 2, budget: { amount: "1000", currency: "AUD" }, additional_preferences: "" };
  vi.stubGlobal("fetch", vi.fn(async (url: string) => Response.json(
    url === "/api/auth/current" ? { id: "alice", display_name: "Alice", csrf_token: "token" }
      : url === "/api/planning/date-window" ? { allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 }
      : url === "/api/planning/tasks/recent?limit=10" ? [{ id: "accepted", state: "completed", revision: 2, request, progress: { stage: "completed", message: "Ready" }, preview_id: "preview-a" }]
      : url === "/api/previews/preview-a" ? { id: "preview-a", state: "pending", saved_trip_id: null, snapshot: { schema_version: "product_detail_1", id: "preview-a", title: "A matching Sydney journey", destination: "Sydney", start_date: "2026-10-22", end_date: "2026-10-23", provenance: "generated", trust: "generated_projection", request, days: [{ date: "2026-10-22", activities: [] }, { date: "2026-10-23", activities: [] }], transfers: [], nearby: [] } }
      : [])));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/plan"] })} />);
  expect(await screen.findByRole("heading", { name: "A matching Sydney journey" })).toBeVisible();
  expect(screen.getByRole("link", { name: /View full itinerary/ })).toHaveAttribute("href", "/previews/preview-a");
  fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "Kyoto" } });
  expect(screen.getByRole("heading", { name: "A matching Sydney journey" })).toBeVisible();
  expect(screen.getByLabelText("Destination")).toHaveValue("Kyoto");
});
