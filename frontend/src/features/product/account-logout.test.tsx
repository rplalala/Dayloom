import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { AccountPage } from "./AccountPage";

const useMockSession = vi.hoisted(() => vi.fn());
vi.mock("./session", () => ({ useSession: useMockSession }));
afterEach(() => vi.unstubAllGlobals());

it.each(["before", "after"])("does not show an old logout failure when a new owner arrives %s its response", async arrival => {
  let reject!: (error: Error) => void;
  const pending = new Promise<void>((_, fail) => { reject = fail; });
  const logout = vi.fn(() => pending);
  const alice = { id: "alice", email: "alice@example.com", display_name: "Alice", initials: "A", csrf_token: "alice-fixture-session" };
  const bob = { id: "bob", email: "bob@example.com", display_name: "Bob", initials: "B", csrf_token: "bob-fixture-session" };
  const session = { account: alice as typeof alice | null, status: "authenticated", logout, refresh: vi.fn(async () => {}) };
  useMockSession.mockImplementation(() => session);
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ display_name: session.account?.display_name || "", initials: session.account?.initials || "", currency: "AUD", interests: [], pace: null, transport: [], notes: "" })));
  const view = render(<MemoryRouter><AccountPage /></MemoryRouter>);
  await screen.findByLabelText("Display name");
  const buttons = screen.getAllByRole("button", { name: "Log out" });
  fireEvent.click(buttons[buttons.length - 1]);
  session.account = null;
  view.rerender(<MemoryRouter><AccountPage /></MemoryRouter>);
  if (arrival === "before") {
    session.account = bob;
    view.rerender(<MemoryRouter><AccountPage /></MemoryRouter>);
  }
  await act(async () => reject(new Error("Controlled old-owner logout failure")));
  if (arrival === "after") {
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not end the server session.");
    session.account = bob;
    view.rerender(<MemoryRouter><AccountPage /></MemoryRouter>);
  }
  await waitFor(() => expect(screen.getByLabelText("Display name")).toHaveValue("Bob"));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(logout).toHaveBeenCalledTimes(1);
});
