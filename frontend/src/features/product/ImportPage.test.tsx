import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it("reopens the import dialog after guest registration with the pasted input and no import write", async () => {
  let authenticated = false;
  const writes: string[] = [];
  const account = { id: "alice", display_name: "Alice", email: "alice@example.com", csrf_token: "token" };
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url === "/api/auth/register") { authenticated = true; return Response.json(account, { status: 201 }); }
    if (url === "/api/auth/current") return Response.json(authenticated ? account : { detail: { code: "login_required" } }, { status: authenticated ? 200 : 401 });
    if (url.startsWith("/api/library")) return Response.json({ items: [], total: 0 });
    if (url === "/api/imports" && options?.method === "POST") writes.push(url);
    return Response.json([]);
  }));
  const router = createMemoryRouter(routes, { initialEntries: ["/import"] });
  render(<RouterProvider router={router} />);
  const pasted = '{"destination":"Sydney","days":[]}';
  fireEvent.change(await screen.findByLabelText("Itinerary JSON"), { target: { value: pasted } });
  fireEvent.click(screen.getByRole("link", { name: "Log in to preview" }));
  fireEvent.click(await screen.findByRole("tab", { name: "Sign up" }));
  fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Alice" } });
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "alice@example.com" } });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), { target: { value: "safe password" } });
  fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "safe password" } });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
  await waitFor(() => expect(router.state.location.pathname).toBe("/import"));
  expect(await screen.findByRole("dialog", { name: "Bring an itinerary along." })).toHaveAttribute("open");
  expect(screen.getByLabelText("Itinerary JSON")).toHaveValue(pasted);
  expect(writes).toEqual([]);
});


it("returns keyboard focus to the import link when the route dialog closes", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => url === "/api/auth/current" ? Response.json({ detail: { code: "login_required" } }, { status: 401 }) : Response.json([])));
  const router = createMemoryRouter(routes, { initialEntries: ["/trips"] });
  render(<RouterProvider router={router} />);
  fireEvent.click(await screen.findByRole("link", { name: "Import an itinerary" }));
  fireEvent.click(await screen.findByRole("button", { name: "Close import" }));
  await waitFor(() => expect(router.state.location.pathname).toBe("/trips"));
  expect(screen.getByRole("link", { name: "Import an itinerary" })).toHaveFocus();
});


it("does not steal a focus target chosen while the returning Library session loads", async () => {
  let release: ((response: Response) => void) | undefined;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => url === "/api/auth/current" ? new Promise<Response>(resolve => { release = resolve; }) : Response.json([])));
  const router = createMemoryRouter(routes, { initialEntries: [{ pathname: "/trips", state: { focusImport: true } }] });
  render(<RouterProvider router={router} />);
  const home = screen.getByRole("link", { name: "Dayloom home" });
  home.focus();
  await waitFor(() => expect(release).toBeDefined());
  await act(async () => { release!(Response.json({ detail: { code: "login_required" } }, { status: 401 })); });
  await screen.findByRole("link", { name: "Import an itinerary" });
  expect(home).toHaveFocus();
});
