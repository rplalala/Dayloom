import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";
import { createBrief } from "./editor";

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("saves an incomplete brief, updates its identity, and preserves local edits on conflict", async () => {
  let revision = 1;
  const writes: { url: string; body: Record<string, unknown> }[] = [];
  const draft = { id: "e8a18ca5-30e0-4df1-8786-dc3b0f42a752", title: "Kyoto idea", revision, editor: createBrief() };
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url === "/api/auth/current") return Response.json({ id: "alice", display_name: "Alice", initials: "A", csrf_token: "token" });
    if (url === "/api/planning/date-window") return Response.json({ allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 });
    if (url.startsWith("/api/drafts") && options?.method) {
      const body = JSON.parse(String(options.body)); writes.push({ url, body });
      if (options.method === "PUT" && body.revision !== revision) return Response.json({ detail: { code: "draft_revision_conflict" } }, { status: 409 });
      return Response.json({ ...draft, ...body, revision: options.method === "PUT" ? ++revision : 1 });
    }
    return Response.json({ ...draft, revision });
  }));
  const router = createMemoryRouter(routes, { initialEntries: ["/plan"] });
  render(<RouterProvider router={router} />);
  const destination = await screen.findByLabelText("Destination");
  fireEvent.change(destination, { target: { value: "Kyoto" } });
  fireEvent.change(screen.getByLabelText("Draft title"), { target: { value: "Kyoto idea" } });
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await screen.findByText("Draft saved.");
  expect(writes[0].body.editor).toMatchObject({ destination: "Kyoto", start_date: "" });
  expect(router.state.location.search).toContain("draft=");
  fireEvent.change(destination, { target: { value: "My local Kyoto" } });
  revision = 3;
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await screen.findByRole("button", { name: "Reload saved draft" });
  expect(destination).toHaveValue("My local Kyoto");
  expect(writes[1].url).toContain(draft.id);
  fireEvent.click(screen.getByRole("button", { name: "Save as new draft" }));
  await waitFor(() => expect(writes).toHaveLength(3));
  expect(writes[2].url).toBe("/api/drafts");
  expect(writes[2].body.editor).toMatchObject({ destination: "My local Kyoto" });
});

it("keeps typing during a pending save and identifies the unsaved newer input", async () => {
  let release!: (response: Response) => void;
  const pending = new Promise<Response>(resolve => { release = resolve; });
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url === "/api/auth/current") return Response.json({ id: "alice", csrf_token: "token" });
    if (url === "/api/drafts" && options?.method === "POST") return pending;
    return Response.json({ allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 });
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/plan"] })} />);
  const destination = await screen.findByLabelText("Destination");
  fireEvent.change(destination, { target: { value: "Submitted" } });
  fireEvent.change(screen.getByLabelText("Draft title"), { target: { value: "Idea" } });
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  fireEvent.change(destination, { target: { value: "Still typing" } });
  release(Response.json({ id: "saved-id", title: "Idea", revision: 1 }));
  await screen.findByText("You have unsaved changes.");
  expect(destination).toHaveValue("Still typing");
  expect(screen.queryByText("Draft saved.")).not.toBeInTheDocument();
});

it("explicitly reloads a conflicting recovered draft even without an initial query string", async () => {
  const id = "e8a18ca5-30e0-4df1-8786-dc3b0f42a752";
  sessionStorage.setItem("dayloom.editor.v1", JSON.stringify({ owner: "alice", brief: { ...createBrief(), destination: "Private local work" }, actionId: null, draftRef: { id, title: "Idea", revision: 1 }, draftTitle: "Idea" }));
  vi.spyOn(window, "confirm").mockReturnValue(true);
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url === "/api/auth/current") return Response.json({ id: "alice", csrf_token: "token" });
    if (url.startsWith("/api/drafts/")) return options?.method === "PUT" ? Response.json({ detail: { code: "draft_revision_conflict" } }, { status: 409 }) : Response.json({ id, title: "Server idea", revision: 2, editor: { ...createBrief(), destination: "Server update" } });
    return Response.json({ allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 });
  }));
  const router = createMemoryRouter(routes, { initialEntries: ["/plan"] });
  render(<RouterProvider router={router} />);
  await waitFor(() => expect(screen.getByLabelText("Destination")).toHaveValue("Private local work"));
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  fireEvent.click(await screen.findByRole("button", { name: "Reload saved draft" }));
  await waitFor(() => expect(screen.getByLabelText("Destination")).toHaveValue("Server update"));
  expect(router.state.location.search).toContain(id);
  vi.restoreAllMocks();
});

it.each(["draft", "unmount", "late-error"])("fences a late save after navigation to another %s context", async mode => {
  const firstId = "e8a18ca5-30e0-4df1-8786-dc3b0f42a752";
  const nextId = "80d0aef6-27f9-49d5-8986-e9ab928b815e";
  let release!: (response: Response) => void;
  const pending = new Promise<Response>(resolve => { release = resolve; });
  let releaseNext!: (response: Response) => void;
  const nextPending = new Promise<Response>(resolve => { releaseNext = resolve; });
  const writes: { url: string; body: Record<string, unknown> }[] = [];
  sessionStorage.setItem("dayloom.editor.v1", JSON.stringify({ owner: "alice", brief: { ...createBrief(), destination: "A input" }, actionId: null, draftRef: { id: firstId, title: "A", revision: 1 }, draftTitle: "A" }));
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url === "/api/auth/current") return Response.json({ id: "alice", csrf_token: "token" });
    if (url.startsWith("/api/library")) return Response.json({ items: [], total: 0 });
    if (url.startsWith("/api/drafts/")) {
      if (options?.method === "PUT") {
        writes.push({ url, body: JSON.parse(String(options.body)) });
        return url.endsWith(firstId) ? pending : mode === "late-error" ? nextPending : Response.json({ id: nextId, title: "B", revision: 2 });
      }
      return Response.json({ id: nextId, title: "B", revision: 1, editor: { ...createBrief(), destination: "B input" } });
    }
    return Response.json({ allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 });
  }));
  const router = createMemoryRouter(routes, { initialEntries: [`/plan?draft=${firstId}`] });
  render(<RouterProvider router={router} />);
  await waitFor(() => expect(screen.getByLabelText("Destination")).toHaveValue("A input"));
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await act(() => router.navigate(mode === "unmount" ? "/trips" : `/plan?draft=${nextId}`));
  if (mode !== "unmount") await waitFor(() => expect(screen.getByLabelText("Destination")).toHaveValue("B input"));
  if (mode === "late-error") fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await act(async () => release(mode === "late-error" ? Response.json({ detail: { code: "draft_revision_conflict" } }, { status: 409 }) : Response.json({ id: firstId, title: "A", revision: 2 })));
  expect(router.state.location.pathname + router.state.location.search).toBe(mode === "unmount" ? "/trips" : `/plan?draft=${nextId}`);
  if (mode === "unmount") await act(() => router.navigate(`/plan?draft=${nextId}`));
  await waitFor(() => expect(screen.getByLabelText("Destination")).toHaveValue("B input"));
  if (mode === "late-error") {
    expect(screen.getByRole("button", { name: "Save draft" })).toBeDisabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await act(async () => releaseNext(Response.json({ id: nextId, title: "B", revision: 2 })));
  } else fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await waitFor(() => expect(writes).toHaveLength(2));
  expect(writes[1]).toMatchObject({ url: `/api/drafts/${nextId}`, body: { editor: { destination: "B input" } } });
});
