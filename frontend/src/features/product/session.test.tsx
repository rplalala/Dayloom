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

afterEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  vi.unstubAllGlobals();
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
