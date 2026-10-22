import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, MemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { AuthPage } from "./AuthPage";
import { SessionProvider } from "./session";

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it.each([
  "https://example.invalid/drafts/f471a830-ad20-4830-a21c-108f312cafb2",
  "//example.invalid/drafts/f471a830-ad20-4830-a21c-108f312cafb2",
  "/drafts/not-a-uuid",
  "/drafts/f471a830-ad20-4830-a21c-108f312cafb2?return=//example.invalid",
  "/drafts/f471a830-ad20-4830-a21c-108f312cafb2/../account",
])("rejects an unapproved login return target: %s", async target => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => url === "/api/auth/login"
    ? Response.json({ id: "alice", display_name: "Alice", csrf_token: "csrf" })
    : Response.json({ detail: { code: "login_required" } }, { status: 401 })));
  const router = createMemoryRouter([
    { path: "/login", element: <SessionProvider><AuthPage /></SessionProvider> },
    { path: "/trips", element: <h1>Trip library</h1> },
  ], { initialEntries: [`/login?return=${encodeURIComponent(target)}`] });
  render(<RouterProvider router={router} />);
  fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "alice@example.com" } });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), { target: { value: "valid-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Log in" }));
  await waitFor(() => expect(router.state.location.pathname).toBe("/trips"));
  expect(screen.getByRole("heading", { name: "Trip library" })).toBeVisible();
});

it("keeps login and registration fields and password visibility independent across tabs", async () => {
  const fetcher = vi.fn<typeof fetch>(async () => Response.json({ status: "unavailable" }));
  vi.stubGlobal("fetch", fetcher);
  render(<MemoryRouter><SessionProvider><AuthPage /></SessionProvider></MemoryRouter>);
  const email = await screen.findByLabelText("Email address");
  fireEvent.change(email, { target: { value: "returning@example.com" } });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), { target: { value: "login password" } });
  fireEvent.click(screen.getByRole("button", { name: "Show or hide password" }));
  fireEvent.click(screen.getByRole("tab", { name: "Sign up" }));
  expect(screen.getByLabelText("Email address")).toHaveValue("");
  expect(screen.getByLabelText("Password", { exact: true })).toHaveAttribute("type", "password");
  fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Alex" } });
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "new@example.com" } });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), { target: { value: "registration password" } });
  fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "registration password" } });
  fireEvent.click(screen.getByRole("tab", { name: "Log in" }));
  expect(screen.getByLabelText("Email address")).toHaveValue("returning@example.com");
  expect(screen.getByLabelText("Password", { exact: true })).toHaveValue("login password");
  expect(screen.getByLabelText("Password", { exact: true })).toHaveAttribute("type", "text");
  fireEvent.click(screen.getByRole("tab", { name: "Sign up" }));
  expect(screen.getByLabelText("Display name")).toHaveValue("Alex");
  expect(screen.getByLabelText("Confirm password")).toHaveValue("registration password");
  expect(fetcher.mock.calls.every(([, options]) => !options?.method || ["GET", "HEAD"].includes(options.method))).toBe(true);
});
