import type { Brief } from "./editor";

export type DraftRef = { id: string; title: string; revision: number };
export type Draft = DraftRef & { editor: Brief; created_at: string; updated_at: string };
export type LibraryCard = DraftRef & { kind: "draft"; source: "draft"; draft_id: string; destination: string; start_date: string; end_date: string; created_at: string; updated_at: string };
export type LibraryPageResult = { items: LibraryCard[]; total: number; limit: number; offset: number };

export class DraftFailure extends Error {
  constructor(public status: number) {
    super(status === 409 ? "This draft changed elsewhere. Your local edits are still here." : status === 422 ? "The draft could not be saved. Check the title and shorten oversized fields." : status === 401 ? "Log in again to continue. Your input is retained privately." : "Your collection is unavailable. Please try again.");
  }
}

/** Cookie authentication and CSRF stay on the existing account boundary. */
export async function draftRequest<T>(url: string, method = "GET", csrf?: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { method, credentials: "same-origin", cache: "no-store", signal,
    headers: { ...(body !== undefined && { "Content-Type": "application/json" }), ...(csrf && { "X-CSRF-Token": csrf }) },
    ...(body !== undefined && { body: JSON.stringify(body) }) });
  if (!response.ok) throw new DraftFailure(response.status);
  return response.status === 204 ? undefined as T : response.json();
}
