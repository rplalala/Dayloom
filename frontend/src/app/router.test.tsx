import { act, fireEvent, render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { routes } from "./router";
import { submitPlanningRequest } from "../features/planning/api";
import { submitDeveloperPlanningRequest } from "../features/developer-planning/api";

describe("application route boundaries", () => {
  it.each(["/dev"])(
    "cancels active requests when navigating away from %s",
    async (path) => {
      const product = vi.mocked(submitPlanningRequest);
      const developer = vi.mocked(submitDeveloperPlanningRequest);
      product.mockReset().mockImplementation(() => new Promise(() => {}));
      developer.mockReset().mockImplementation(() => new Promise(() => {}));
      const testRouter = createMemoryRouter(routes, { initialEntries: [path] });
      render(<RouterProvider router={testRouter} />);
      await act(async () => {});
      for (const [label, value] of Object.entries({
        Destination: "Kyoto",
        "Start date": "2026-09-12",
        "End date": "2026-09-12",
        Travelers: "2",
        "Budget amount": "2000",
        Currency: "AUD",
      })) {
        fireEvent.change(screen.getByLabelText(label), { target: { value } });
      }
      fireEvent.click(
        screen.getByRole("button", {
          name: path === "/plan" ? "Generate itinerary" : "Run all versions",
        }),
      );
      const calls =
        path === "/plan" ? product.mock.calls : developer.mock.calls;
      expect(calls).toHaveLength(path === "/plan" ? 1 : 4);
      expect(calls.every(([, options]) => !options!.signal.aborted)).toBe(true);
      await act(async () => {
        await testRouter.navigate("/");
      });
      expect(testRouter.state.location.pathname).toBe("/");
      expect(calls.every(([, options]) => options!.signal.aborted)).toBe(true);
      await act(async () => {
        for (const [, options] of calls)
          options!.onEvent({
            type: "stage",
            run_id: "old",
            sequence: 1,
            elapsed_ms: 100,
            message: "Stale repair update",
            stage: "repair",
          });
      });
      expect(screen.queryByText("Stale repair update")).not.toBeInTheDocument();
    },
  );
  it("does not keep the old developer planner page", () => {
    const testRouter = createMemoryRouter(routes, {
      initialEntries: ["/dev/planner"],
    });
    render(<RouterProvider router={testRouter} />);
    expect(
      screen.queryByText("Run all research planners"),
    ).not.toBeInTheDocument();
  });
  it("renders the product layout for the planner", () => {
    const testRouter = createMemoryRouter(routes, {
      initialEntries: ["/plan"],
    });
    render(<RouterProvider router={testRouter} />);

    expect(screen.getByLabelText("Main navigation")).toBeInTheDocument();
    expect(screen.getAllByText(/Dayloom/).length).toBeGreaterThan(0);
    expect(
      screen.queryByText("Local development and research"),
    ).not.toBeInTheDocument();
  });

  it("renders the isolated developer layout and deployment warning", () => {
    const testRouter = createMemoryRouter(routes, { initialEntries: ["/dev"] });
    render(<RouterProvider router={testRouter} />);

    expect(
      screen.getByText("Local development and research"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Protect or disable it before any public production deployment/,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Main navigation")).not.toBeInTheDocument();
  });
});

vi.mock("../features/planning/api", () => ({
  submitPlanningRequest: vi.fn(),
  getTripDateWindow: vi
    .fn()
    .mockResolvedValue({
      allowedStart: "2026-09-11",
      allowedEnd: "2026-09-24",
      maxTripDays: 10,
    }),
}));
vi.mock("../features/developer-planning/api", () => ({
  submitDeveloperPlanningRequest: vi.fn(),
}));
