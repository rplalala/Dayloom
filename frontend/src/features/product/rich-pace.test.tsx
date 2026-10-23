import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";
import { createBrief, pacePrompts, togglePace } from "./editor";

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it.each(["selection", "account default", "restored draft", "replan"])(
  "submits the same Rich preference through %s without introducing an exact-count requirement",
  async origin => {
    const brief = togglePace(createBrief(), "rich");
    const requests: Record<string, unknown>[] = [];
    const sourceRequest = {
      destination: "Sydney", start_date: "2026-09-12", end_date: "2026-09-13",
      traveler_count: 2, budget: { amount: "1000", currency: "AUD" },
      additional_preferences: pacePrompts.rich,
    };
    if (origin === "restored draft") {
      sessionStorage.setItem("dayloom.editor.v1", JSON.stringify({
        owner: "alice", brief, actionId: null, origin: "restored",
      }));
    }
    vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
      if (url === "/api/auth/current") return Response.json({ id: "alice", display_name: "Alice", initials: "A", csrf_token: "csrf" });
      if (url === "/api/planning/date-window") return Response.json({ allowedStart: "2026-09-12", allowedEnd: "2026-09-20", maxTripDays: 10 });
      if (url === "/api/profile") return Response.json({ currency: "AUD", interests: [], pace: origin === "account default" ? "rich" : "relaxed", transport: [], notes: "" });
      if (url === "/api/trips/saved") return Response.json({
        schema_version: "product_detail_1", id: "saved", title: "Saved Rich trip",
        destination: "Sydney", provenance: "generated", trust: "generated_projection",
        request: sourceRequest, days: [], nearby: [], transfers: [],
        completion: { pace_review: { status: "partial", days: [
          { date: "2026-09-12", count: 2, target_count: 3, state: "residual" },
        ] } },
      });
      if (url === "/api/planning/tasks" && options?.method === "POST") {
        const body = JSON.parse(String(options.body));
        requests.push(body.request);
        return Response.json({ id: "task", state: "pending" }, { status: 202 });
      }
      return Response.json(url.includes("operation_key=") ? null : []);
    }));
    render(<RouterProvider router={createMemoryRouter(routes, {
      initialEntries: [origin === "replan" ? "/trips/saved" : "/plan"],
    })} />);
    if (origin === "replan") fireEvent.click(await screen.findByRole("button", { name: "Plan again" }));
    await screen.findByLabelText("Destination");
    fireEvent.click(screen.getByText("Personalize your trip"));
    if (origin === "selection") {
      await waitFor(() => expect(screen.getByRole("button", { name: /Relaxed/ })).toHaveAttribute("aria-pressed", "true"));
      fireEvent.click(screen.getByRole("button", { name: /Rich/ }));
    }
    await waitFor(() => expect(screen.getByLabelText("Additional preferences")).toHaveValue(pacePrompts.rich));
    for (const [field, value] of [
      ["Destination", "Sydney"], ["Start date", "2026-09-12"], ["End date", "2026-09-13"],
      ["Travelers", "2"], ["Whole-trip budget", "1000"],
    ]) fireEvent.change(screen.getByLabelText(field), { target: { value } });
    fireEvent.click(screen.getByRole("button", { name: "Generate itinerary" }));
    await waitFor(() => expect(requests).toHaveLength(1));
    expect(requests[0]).toEqual(sourceRequest);
  },
);
