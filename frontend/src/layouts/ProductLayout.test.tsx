import { fireEvent, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ProductLayout } from "./ProductLayout";

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it.each([
  ["/trips", true],
  ["/trips/f471a830-ad20-4830-a21c-108f312cafb2", true],
  ["/drafts/f471a830-ad20-4830-a21c-108f312cafb2", true],
  ["/examples/sydney-example", true],
  ["/previews/f471a830-ad20-4830-a21c-108f312cafb2", true],
  ["/import", true],
  ["/", false],
  ["/plan", false],
  ["/planning", false],
  ["/account", false],
])("shows the My trips navigation state for %s in desktop and mobile menus", async (path, selected) => {
  const writes: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method && options.method !== "GET") writes.push(url);
    return url === "/api/auth/current"
      ? Response.json({ detail: { code: "login_required" } }, { status: 401 })
      : Response.json([]);
  }));
  const router = createMemoryRouter([
    { element: <ProductLayout />, children: [{ path: "*", element: <p>Page content</p> }] },
  ], { initialEntries: [String(path)] });
  render(<RouterProvider router={router} />);
  const desktop = within(screen.getByRole("navigation", { name: "Main navigation" })).getByRole("link", { name: "My trips" });
  fireEvent.click(screen.getByLabelText("Open navigation"));
  const mobile = within(screen.getByLabelText("Mobile navigation")).getByText("My trips", { selector: "a" });
  for (const link of [desktop, mobile]) {
    expect(link.classList.contains("selected")).toBe(selected);
    if (selected) expect(link).toHaveAttribute("aria-current", "page");
    else expect(link).not.toHaveAttribute("aria-current");
    expect(link).toHaveAttribute("href", "/trips");
  }
  expect(writes).toEqual([]);
});
