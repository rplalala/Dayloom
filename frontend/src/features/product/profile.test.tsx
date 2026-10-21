import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";
import { useSession } from "./session";

const account = { id: "alice", email: "alice@example.com", display_name: "Alice", initials: "A", csrf_token: "csrf" };
const profile = { display_name: "Alice", initials: "A", currency: "JPY", interests: ["Nature"], pace: "relaxed", transport: ["walk", "transit"], notes: "Quiet mornings" };
afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

function setup(profileResponse: Promise<Response>) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url === "/api/auth/current") return new Response(JSON.stringify(account));
    if (url === "/api/profile") return profileResponse;
    return new Response(JSON.stringify({ allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 }));
  }));
  const router = createMemoryRouter(routes, { initialEntries: ["/plan"] });
  render(<RouterProvider router={router} />);
  return router;
}

it("visibly prefills only a new brief and retains edited-cleared work across navigation", async () => {
  const router = setup(Promise.resolve(new Response(JSON.stringify(profile))));
  await waitFor(() => expect(screen.getByLabelText("Currency")).toHaveValue("JPY"));
  expect((screen.getByLabelText("Additional preferences") as HTMLTextAreaElement).value).toContain("Quiet mornings");
  expect(screen.getByRole("button", { name: "Nature" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "Kyoto" } });
  fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "" } });
  fireEvent.input(screen.getByLabelText("Additional preferences"), { target: { value: "" } });
  await act(() => router.navigate("/account"));
  await act(() => router.navigate("/plan"));
  expect(screen.getByLabelText("Additional preferences")).toHaveValue("");
});

it("does not overlay a keystroke when a slow defaults response arrives", async () => {
  let settle: (response: Response) => void = () => {};
  setup(new Promise(resolve => { settle = resolve; }));
  const destination = await screen.findByLabelText("Destination");
  fireEvent.change(destination, { target: { value: "My trip" } });
  await act(async () => settle(new Response(JSON.stringify(profile))));
  expect(destination).toHaveValue("My trip");
  expect(screen.getByLabelText("Currency")).toHaveValue("AUD");
  expect(screen.getByLabelText("Additional preferences")).toHaveValue("");
});

function NewBriefAction() {
  const session = useSession();
  return <button onClick={() => session.newBrief()}>Start a genuinely new brief</button>;
}

it("explicitly creates another new brief from latest defaults even before any edit", async () => {
  let current = profile;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(
    url === "/api/auth/current" ? account : url === "/api/profile" ? current : { allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 }
  ))));
  const routeCopy = routes.map((route, index) => index || route.index ? route : { ...route, children: [...route.children!, { path: "new-action", element: <NewBriefAction /> }] });
  const router = createMemoryRouter(routeCopy, { initialEntries: ["/plan"] });
  render(<RouterProvider router={router} />);
  await waitFor(() => expect(screen.getByLabelText("Currency")).toHaveValue("JPY"));
  current = { ...profile, currency: "USD", notes: "Latest defaults" };
  await act(() => router.navigate("/new-action"));
  fireEvent.click(screen.getByRole("button", { name: "Start a genuinely new brief" }));
  await act(() => router.navigate("/plan"));
  await waitFor(() => expect(screen.getByLabelText("Currency")).toHaveValue("USD"));
  expect((screen.getByLabelText("Additional preferences") as HTMLTextAreaElement).value).toContain("Latest defaults");
});

it("treats a restored blank brief as existing work rather than new", async () => {
  sessionStorage.setItem("dayloom.editor.v1", JSON.stringify({ owner: "alice", brief: { destination: "", start_date: "", end_date: "", travelers: "", budget: "", currency: "AUD", preferences: "" }, actionId: null }));
  setup(Promise.resolve(new Response(JSON.stringify(profile))));
  await screen.findByLabelText("Destination");
  expect(screen.getByLabelText("Currency")).toHaveValue("AUD");
  expect(screen.getByLabelText("Additional preferences")).toHaveValue("");
});
