import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { routes } from "../../app/router";

afterEach(() => {
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

it("returns a guest brief through registration without generating", async () => {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      calls.push(url);
      if (url === "/api/auth/current")
        return new Response(
          JSON.stringify({ detail: { code: "login_required" } }),
          { status: 401 },
        );
      return new Response(
        JSON.stringify({
          id: "alice",
          email: "alice@example.com",
          display_name: "Alice",
          initials: "A",
          csrf_token: "csrf",
        }),
        { status: 201 },
      );
    }),
  );
  const router = createMemoryRouter(routes, { initialEntries: ["/plan"] });
  render(<RouterProvider router={router} />);
  await waitFor(() =>
    expect(screen.getByLabelText("Destination")).toBeEnabled(),
  );
  fireEvent.change(screen.getByLabelText("Destination"), {
    target: { value: "Kyoto" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Generate itinerary/ }));
  await screen.findByRole("heading", { name: "Welcome back." });
  fireEvent.click(screen.getByRole("tab", { name: "Sign up" }));
  fireEvent.change(screen.getByLabelText("Display name"), {
    target: { value: "Alice" },
  });
  fireEvent.change(screen.getByLabelText("Email address"), {
    target: { value: "alice@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), {
    target: { value: "safe password" },
  });
  fireEvent.change(screen.getByLabelText("Confirm password"), {
    target: { value: "safe password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Destination")).toHaveValue("Kyoto"),
  );
  expect(calls).not.toContain("/api/planning");
});
