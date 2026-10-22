import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { AuthPage } from "./AuthPage";
import { SessionProvider } from "./session";

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

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
