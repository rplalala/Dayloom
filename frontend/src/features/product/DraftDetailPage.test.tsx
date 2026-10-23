import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";
import { createBrief } from "./editor";

const id = "f471a830-ad20-4830-a21c-108f312cafb2";
const account = { id: "alice", display_name: "Alice", initials: "A", csrf_token: "original-session" };
const editor = { ...createBrief(), destination: "Sydney", start_date: "2026-10-22", end_date: "2026-10-23", travelers: "2", budget: "1000" };
const draft = { id, title: "Harbour ideas", editor, revision: 7, created_at: "2026-10-22T08:00:00Z", updated_at: "2026-10-22T08:00:00Z" };
const local = { ...editor, destination: "Kyoto", preferences: "My unfinished private brief" };
const restore = () => sessionStorage.setItem("dayloom.editor.v1", JSON.stringify({ owner: account.id, brief: local, actionId: "private-operation", origin: "restored", draftTitle: "Private unsaved name" }));
afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it("returns to private draft details after logging in without restoring or saving the brief", async () => {
  let authenticated = false;
  const writes: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method === "POST") writes.push(url);
    if (url === "/api/auth/login") { authenticated = true; return Response.json(account); }
    if (url === "/api/auth/current") return Response.json(authenticated ? account : { detail: { code: "login_required" } }, { status: authenticated ? 200 : 401 });
    if (url === `/api/drafts/${id}`) return Response.json(draft);
    if (url.startsWith("/api/library")) return Response.json({ items: [], total: 0 });
    return Response.json([]);
  }));
  const router = createMemoryRouter(routes, { initialEntries: [`/drafts/${id}`] });
  render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { name: "Your draft is private." });
  fireEvent.click(screen.getAllByRole("link", { name: "Log in" }).find(link => link.getAttribute("href")?.includes("return="))!);
  fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "alice@example.com" } });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), { target: { value: "valid-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Log in" }));
  await waitFor(() => expect(router.state.location.pathname).toBe(`/drafts/${id}`));
  expect(await screen.findByRole("heading", { name: draft.title })).toBeVisible();
  expect(writes).toEqual(["/api/auth/login"]);
});

it("opens source draft details read-only, then restores only after explicit Continue planning", async () => {
  restore();
  const writes: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method && options.method !== "GET") writes.push(url);
    if (url === "/api/auth/current") return Response.json(account);
    if (url.startsWith("/api/library")) return Response.json({ items: [{ ...draft, ...editor, kind: "draft", destination: editor.destination }], total: 1 });
    if (url === `/api/drafts/${id}`) return Response.json(draft);
    if (url === "/api/planning/date-window") return Response.json({ allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 });
    return Response.json([]);
  }));
  const router = createMemoryRouter(routes, { initialEntries: ["/trips"] });
  render(<RouterProvider router={router} />);
  const card = await screen.findByRole("article");
  fireEvent.click(within(card).getByRole("link", { name: "View details" }));
  await screen.findByRole("heading", { name: draft.title });
  expect(router.state.location.pathname).toBe(`/drafts/${id}`);
  expect(screen.getByText("Planning draft")).toBeInTheDocument();
  expect(screen.getByText("Room for your next journey.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Export itinerary" })).not.toBeInTheDocument();
  expect(JSON.parse(sessionStorage.getItem("dayloom.editor.v1")!).brief).toEqual(local);
  expect(writes).toEqual([]);
  fireEvent.click(screen.getByRole("link", { name: "Continue planning" }));
  await waitFor(() => expect(screen.getByLabelText("Destination")).toHaveValue("Sydney"));
  expect(router.state.location.search).toBe(`?draft=${id}`);
  const recovered = JSON.parse(sessionStorage.getItem("dayloom.editor.v1")!);
  expect(recovered.draftRef).toMatchObject({ id, revision: 7 });
  expect(recovered.draftTitle).toBe(draft.title);
  expect(writes).toEqual([]);
});

it("quarantines a draft lookup after session expiry without discarding the current local brief", async () => {
  restore();
  let currentReads = 0;
  const writes: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method && options.method !== "GET") writes.push(url);
    if (url === "/api/auth/current") return ++currentReads === 1 ? Response.json(account) : Response.json({ detail: { code: "session_expired" } }, { status: 401 });
    if (url === `/api/drafts/${id}`) return Response.json({ detail: { code: "login_required" } }, { status: 401 });
    return Response.json([]);
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [`/drafts/${id}`] })} />);
  await screen.findByRole("heading", { name: "Your draft is private." });
  expect(screen.queryByText(draft.title)).not.toBeInTheDocument();
  expect(JSON.parse(sessionStorage.getItem("dayloom.editor.v1")!).brief).toEqual(local);
  expect(writes).toEqual([]);
});

it.each(["account", "session"])("a late draft read cannot cross a changed %s boundary", async boundary => {
  restore();
  let currentAccount = account;
  let release: ((value: Response) => void) | undefined;
  let reads = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url === "/api/auth/current") return Response.json(currentAccount);
    if (url === `/api/drafts/${id}`) {
      if (++reads === 1) return new Promise<Response>(resolve => { release = resolve; });
      return boundary === "account" ? Response.json({ detail: { code: "draft_not_found" } }, { status: 404 }) : Response.json({ ...draft, title: "Current session draft" });
    }
    return Response.json([]);
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [`/drafts/${id}`] })} />);
  await waitFor(() => expect(release).toBeDefined());
  currentAccount = { ...account, id: boundary === "account" ? "bob" : account.id, csrf_token: "new-session" };
  fireEvent(window, new StorageEvent("storage", { key: "dayloom.account.notice", newValue: JSON.stringify({ type: "account", id: currentAccount.id }) }));
  await screen.findByRole("heading", { name: boundary === "account" ? "This draft is unavailable." : "Current session draft" });
  await act(async () => { release!(Response.json(draft)); });
  expect(screen.queryByRole("heading", { name: draft.title })).not.toBeInTheDocument();
  if (boundary === "account") expect(sessionStorage.getItem("dayloom.editor.v1")).not.toContain("My unfinished private brief");
});
