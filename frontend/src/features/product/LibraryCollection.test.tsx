import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it.each(["card", "menu"])("copies a saved %s with one explicit action and retains a lost reply for status-only recovery", async surface => {
  const posts: unknown[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url === "/api/auth/current") return Response.json({ id: "alice", display_name: "Alice", csrf_token: "token" });
    if (url.startsWith("/api/library")) return Response.json({ items: [{ id: "source", kind: "saved", title: "Harbour days", revision: 1, destination: "Sydney", start_date: "2026-10-22", end_date: "2026-10-23" }], total: 1 });
    if (url === "/api/trips/source") return Response.json({ days: [], transfers: [] });
    if (url === "/api/copies" && options?.method === "POST") { posts.push(JSON.parse(String(options.body))); throw new TypeError("Controlled lost copy reply"); }
    if (url.startsWith("/api/copies?")) return Response.json({ id: "receipt", state: "saved", saved_trip_id: "independent", outcome: "saved" });
    return Response.json([]);
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/trips"] })} />);
  if (surface === "menu") fireEvent.click(await screen.findByRole("button", { name: "Manage Harbour days" }));
  fireEvent.click(await screen.findByRole("button", { name: surface === "menu" ? "Copy Harbour days" : "Copy" }));
  await waitFor(() => expect(posts).toHaveLength(1));
  expect(screen.queryByRole("dialog", { name: "Keep an independent copy" })).not.toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Check copy status" }));
  expect(await screen.findByRole("link", { name: "View saved copy" })).toHaveAttribute("href", "/trips/independent");
  expect(posts).toHaveLength(1);
});


it("filters the owned library after typing without an extra submit action", async () => {
  const searches: string[] = [];
  const first = { id: "harbour", kind: "draft", title: "Harbour days", revision: 1, destination: "Sydney" };
  const second = { id: "gardens", kind: "draft", title: "Kyoto gardens", revision: 1, destination: "Kyoto" };
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url === "/api/auth/current") return Response.json({ id: "alice", csrf_token: "token" });
    if (url.startsWith("/api/library")) {
      const query = new URL(url, "http://localhost").searchParams.get("q") || "";
      searches.push(query);
      return Response.json({ items: query ? [second] : [first, second], total: query ? 1 : 2 });
    }
    return Response.json([]);
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/trips"] })} />);
  await screen.findByRole("heading", { name: "Harbour days" });
  fireEvent.change(screen.getByLabelText("Search trips"), { target: { value: "Kyoto" } });
  expect(searches).toEqual([""]);
  await waitFor(() => expect(searches).toEqual(["", "Kyoto"]));
  expect(await screen.findByRole("heading", { name: "Kyoto gardens" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Harbour days" })).not.toBeInTheDocument();
});
