import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { SessionProvider, useSession } from "./session";

function AccountSurface() {
  const session = useSession();
  const [error, setError] = useState("");
  return (
    <>
      <p role="status">{session.account?.email || session.status}</p>
      <button
        onClick={() => {
          void session
            .logout()
            .catch(() => setError("Logout could not be confirmed"));
        }}
      >
        Log out
      </button>
      {error && <p role="alert">{error}</p>}
    </>
  );
}

function EditingSurface() {
  const session = useSession();
  return <>
    <p>{session.account?.email || session.status}</p>
    <button onClick={() => {
      session.editBrief({ ...session.brief, destination: 'Melbourne', preferences: 'Art museums' });
      session.setDraftRef({ id: 'existing-draft', title: 'Autumn trip', revision: 2 });
      session.setActionId('existing-operation');
    }}>Edit travel brief</button>
    <output>{JSON.stringify({ destination: session.brief.destination, preferences: session.brief.preferences, draft: session.draftRef?.id, action: session.actionId })}</output>
  </>;
}

afterEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  vi.unstubAllGlobals();
});

it('retains the edited brief and operation recovery when another tab logs into the same account', async () => {
  const account = { id: 'alice', email: 'alice@example.com', display_name: 'Alice', initials: 'A', csrf_token: 'csrf' };
  vi.stubGlobal('fetch', vi.fn(async () => Response.json(account)));
  render(<SessionProvider><EditingSurface /></SessionProvider>);
  await screen.findByText('alice@example.com');
  fireEvent.click(screen.getByRole('button', { name: 'Edit travel brief' }));
  const edited = screen.getByRole('status').textContent;
  expect(edited).toContain('Melbourne');
  localStorage.setItem('dayloom.account.active', JSON.stringify({ id: 'alice', nonce: 'new-login-in-another-tab' }));
  fireEvent(window, new StorageEvent('storage', { key: 'dayloom.account.active', newValue: localStorage.getItem('dayloom.account.active') }));
  await screen.findByText('alice@example.com');
  expect(screen.getByRole('status')).toHaveTextContent(edited!);
  const restored = JSON.parse(sessionStorage.getItem('dayloom.editor.v1')!);
  expect(restored.brief.destination).toBe('Melbourne');
  expect(restored.brief.preferences).toBe('Art museums');
  expect(restored.draftRef.id).toBe('existing-draft');
  expect(restored.actionId).toBe('existing-operation');
});

it.each([false, true])(
  "keeps logout cleared across a focus refresh and delayed response (lost=%s)",
  async (lost) => {
    let settle: (response: Response) => void = () => {};
    let fail: (reason: Error) => void = () => {};
    const logout = new Promise<Response>((resolve, reject) => {
      settle = resolve;
      fail = reject;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        url.endsWith("/logout")
          ? logout
          : Promise.resolve(
              new Response(
                JSON.stringify({
                  id: "alice",
                  email: "alice@example.com",
                  display_name: "Alice",
                  initials: "A",
                  csrf_token: "csrf",
                }),
              ),
            ),
      ),
    );
    render(
      <SessionProvider>
        <AccountSurface />
      </SessionProvider>,
    );
    await screen.findByText("alice@example.com");
    fireEvent.click(screen.getByRole("button", { name: "Log out" }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("guest"),
    );
    await act(async () => {
      window.dispatchEvent(new Event("focus"));
    });
    expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
    await act(async () => {
      if (lost) fail(new Error("Connection lost"));
      else settle(new Response(null, { status: 204 }));
    });
    expect(screen.getByRole("status")).toHaveTextContent("guest");
    if (lost)
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Logout could not be confirmed",
      );
    await act(async () => {
      window.dispatchEvent(new Event("focus"));
    });
    expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
  },
);
