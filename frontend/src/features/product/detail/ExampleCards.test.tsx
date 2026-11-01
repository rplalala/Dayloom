import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../../app/router";

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it("orders guest examples by creation time and supports source sort and live search", async () => {
  const cards = [
    { id: "sydney-example", title: "Sydney harbour", destination: "Sydney", created_at: "2026-10-13T18:00:00+11:00", start_date: "2026-10-24", end_date: "2026-10-25", day_count: 2 },
    { id: "london-example", title: "London landmarks", destination: "London", created_at: "2026-10-22T08:00:00Z", start_date: "2026-10-22", end_date: "2026-10-23", day_count: 2 },
  ];
  vi.stubGlobal("fetch", vi.fn(async (url: string) => url === "/api/auth/current" ? Response.json({ detail: { code: "login_required" } }, { status: 401 }) : Response.json(url === "/api/examples" ? cards : [])));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/trips"] })} />);
  const titles = () => screen.getAllByRole("article").map(card => within(card).getByRole("heading", { level: 3 }).textContent);
  await screen.findByRole("heading", { name: "London landmarks" });
  expect(titles()).toEqual(["London landmarks", "Sydney harbour"]);
  expect(screen.getAllByRole("link", { name: "View details" })).toHaveLength(2);
  expect(screen.queryByRole("button", { name: "Copy" })).not.toBeInTheDocument();
  for (const image of screen.getAllByRole('img')) expect(image.getAttribute('src')).toMatch(/^\/dayloom\//);
  fireEvent.change(screen.getByLabelText("Sort trips"), { target: { value: "oldest" } });
  expect(titles()).toEqual(["Sydney harbour", "London landmarks"]);
  fireEvent.change(screen.getByLabelText("Sort trips"), { target: { value: "name" } });
  expect(titles()).toEqual(["London landmarks", "Sydney harbour"]);
  fireEvent.change(screen.getByLabelText("Search trips"), { target: { value: "SYDNEY" } });
  expect(titles()).toEqual(["Sydney harbour"]);
  fireEvent.change(screen.getByLabelText("Search trips"), { target: { value: "Nowhere" } });
  expect(await screen.findByRole("heading", { name: "No trips found" })).toBeVisible();
  expect(screen.queryByRole("article")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Search trips"), { target: { value: "" } });
  await waitFor(() => expect(titles()).toHaveLength(2));
});
