import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";
import { useSession } from "./session";
import { createBrief } from "./editor";

const account = { id: "alice", email: "alice@example.com", display_name: "Alice", initials: "A", csrf_token: "csrf" };
const profile = { display_name: "Alice", initials: "A", currency: "JPY", interests: ["Nature"], pace: "relaxed", transport: ["walk", "transit"], notes: "Quiet mornings" };
afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it.each(["sidebar", "form"])("keeps a failed %s logout visible after quarantining the profile", async control => {
  let complete!: (response: Response) => void;
  const pending = new Promise<Response>(resolve => { complete = resolve; });
  let logoutWrites = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url === "/api/auth/current") return Response.json(account);
    if (url === "/api/auth/logout") { logoutWrites++; expect(options?.method).toBe("POST"); return pending; }
    return Response.json(url === "/api/profile" ? profile : []);
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/account"] })} />);
  await screen.findByLabelText("Display name");
  const actions = screen.getAllByRole("button", { name: "Log out" });
  fireEvent.click(control === "sidebar" ? actions[0] : actions[actions.length - 1]);
  await waitFor(() => expect(screen.queryByLabelText("Display name")).not.toBeInTheDocument());
  expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
  await act(async () => complete(Response.json({ detail: "Controlled logout failure" }, { status: 503 })));
  expect(await screen.findByRole("alert")).toHaveTextContent("Could not end the server session.");
  expect(logoutWrites).toBe(1);
  expect(screen.queryByDisplayValue("Quiet mornings")).not.toBeInTheDocument();
});

it("previews the edited profile name and initials in the sidebar before an explicit save", async () => {
  const writes: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method && !["GET", "HEAD"].includes(options.method)) writes.push(options.method);
    return Response.json(url === "/api/auth/current" ? account : url === "/api/profile" ? profile : { allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 });
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/account"] })} />);
  const displayName = await screen.findByLabelText("Display name");
  fireEvent.change(displayName, { target: { value: "Ada Lovelace" } });
  expect(screen.getByRole("heading", { level: 3, name: "Ada Lovelace" })).toBeVisible();
  expect(screen.getByLabelText("Account initials: AL")).toBeVisible();
  expect(writes).toEqual([]);
});

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

function savedProfileEntry(brief = createBrief(), metadata: Record<string, unknown> = {}) {
  sessionStorage.setItem('dayloom.editor.v1', JSON.stringify({ owner: 'alice', brief, actionId: null, origin: 'restored', ...metadata }));
  const saved = { ...profile, pace: 'rich', transport: ['walk'] };
  let reads = 0;
  vi.stubGlobal('fetch', vi.fn(async (url: string) => Response.json(
    url === '/api/auth/current' ? account : url === '/api/profile' ? (reads++, saved)
      : url === '/api/planning/date-window' ? { allowedStart: '2026-10-21', allowedEnd: '2026-11-03', maxTripDays: 10 } : [],
  )));
  const router = createMemoryRouter(routes, { initialEntries: ['/account'] });
  render(<RouterProvider router={router} />);
  return { router, profileReads: () => reads };
}

it('loads saved preferences when Plan a trip is explicitly opened from a restored empty editor', async () => {
  savedProfileEntry();
  await screen.findByLabelText('Display name');
  fireEvent.click(screen.getByRole('link', { name: 'Plan a trip' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Rich' })).toHaveAttribute('aria-pressed', 'true'));
  expect(screen.getByRole('button', { name: 'Walking' })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByLabelText('Currency')).toHaveValue('JPY');
  expect((screen.getByLabelText('Additional preferences') as HTMLTextAreaElement).value).toContain('Quiet mornings');
});

it.each([
  ['destination', { destination: 'Kyoto' }, {}],
  ['currency', { currency: 'USD' }, {}],
  ['preferences', { preferences: 'My own preferences' }, {}],
  ['saved draft', {}, { draftRef: { id: 'existing', title: 'My draft', revision: 1 } }],
  ['draft title', {}, { draftTitle: 'My title' }],
  ['operation recovery', {}, { actionId: 'existing-operation' }],
] as const)('preserves existing %s when entering Plan from navigation', async (_label, values, metadata) => {
  const brief = { ...createBrief(), ...values };
  const { profileReads } = savedProfileEntry(brief, metadata);
  await screen.findByLabelText('Display name');
  fireEvent.click(screen.getByRole('link', { name: 'Plan a trip' }));
  expect(await screen.findByLabelText('Destination')).toHaveValue(brief.destination);
  expect(screen.getByLabelText('Currency')).toHaveValue(brief.currency);
  expect(screen.getByLabelText('Additional preferences')).toHaveValue(brief.preferences);
  expect(profileReads()).toBe(1);
});

it.each(['mobile', 'footer', 'home'] as const)('also applies saved defaults from the %s planning entry', async entry => {
  const { router } = savedProfileEntry();
  await screen.findByLabelText('Display name');
  if (entry === 'mobile') {
    fireEvent.click(screen.getByLabelText('Open navigation'));
    fireEvent.click(within(screen.getByLabelText('Mobile navigation')).getByText('Plan a trip', { exact: true }));
  } else if (entry === 'footer') {
    fireEvent.click(within(screen.getByRole('contentinfo')).getByRole('link', { name: 'Start planning' }));
  } else {
    await act(() => router.navigate('/'));
    fireEvent.click(within(screen.getByRole('main')).getAllByRole('link', { name: /Start planning/ })[0]);
  }
  await waitFor(() => expect(screen.getByRole('button', { name: 'Rich' })).toHaveAttribute('aria-pressed', 'true'));
});

it('keeps Clear empty until another explicit planning entry', async () => {
  savedProfileEntry();
  await screen.findByLabelText('Display name');
  fireEvent.click(screen.getByRole('link', { name: 'Plan a trip' }));
  await waitFor(() => expect(screen.getByLabelText('Currency')).toHaveValue('JPY'));
  fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
  expect(screen.getByLabelText('Additional preferences')).toHaveValue('');
  expect(screen.getByRole('button', { name: 'Rich' })).toHaveAttribute('aria-pressed', 'false');
  fireEvent.click(screen.getByRole('link', { name: 'Plan a trip' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Rich' })).toHaveAttribute('aria-pressed', 'true'));
});

it.each([
  ["load", "session_expired"], ["save", "session_expired"],
  ["load", "session_revoked"], ["save", "session_revoked"],
])("hides private profile on %s rejection and applies canonical %s recovery", async (operation, code) => {
  sessionStorage.setItem("dayloom.editor.v1", JSON.stringify({ owner: "alice", brief: { ...createBrief(), preferences: "Private unsaved brief" }, actionId: "private-action" }));
  let lostSession = false;
  let writes = 0;
  let authReads = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url === "/api/auth/current") {
      authReads++;
      return lostSession
        ? new Response(JSON.stringify({ detail: { code } }), { status: 401 })
        : new Response(JSON.stringify(account));
    }
    if (url !== "/api/profile") return Response.json([]);
    if (options?.method === "PUT") writes++;
    if (operation === "load" || options?.method === "PUT") {
      lostSession = true;
      return new Response(JSON.stringify({ detail: { code } }), { status: 401 });
    }
    return new Response(JSON.stringify(profile));
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/account"] })} />);
  if (operation === "save") {
    await screen.findByDisplayValue("Quiet mornings");
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  }
  await waitFor(() => expect(authReads).toBeGreaterThanOrEqual(2));
  await screen.findAllByRole("link", { name: "Log in" });
  expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
  expect(screen.queryByDisplayValue("Quiet mornings")).not.toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Log in" }).length).toBeGreaterThan(0);
  const recovery = JSON.parse(sessionStorage.getItem("dayloom.editor.v1")!);
  expect(recovery.brief.preferences).toBe(code === "session_expired" ? "Private unsaved brief" : "");
  expect(recovery.actionId).toBe(code === "session_expired" ? "private-action" : null);
  expect(writes).toBe(operation === "save" ? 1 : 0);
});
