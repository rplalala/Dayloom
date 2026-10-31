import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { routes } from "./router";

describe("application route boundaries", () => {
  it.each(["/dev", "/dev/planner", "/dev/anything"])(
    "shows the not-found page for retired developer route %s", (path) => {
      const testRouter = createMemoryRouter(routes, { initialEntries: [path] });
      render(<RouterProvider router={testRouter} />);
      expect(screen.getByRole("heading", { name: "That route is not on the itinerary." })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Return home" })).toHaveAttribute("href", "/");
      expect(screen.queryByText("Local development and research")).not.toBeInTheDocument();
    },
  );

  it("renders the product layout for the planner", () => {
    const testRouter = createMemoryRouter(routes, { initialEntries: ["/plan"] });
    render(<RouterProvider router={testRouter} />);
    expect(screen.getByLabelText("Main navigation")).toBeInTheDocument();
    expect(screen.getAllByText(/Dayloom/).length).toBeGreaterThan(0);
  });
});

vi.mock("../features/planning/api", () => ({
  submitPlanningRequest: vi.fn(),
  getTripDateWindow: vi.fn().mockResolvedValue({
    allowedStart: "2026-09-11", allowedEnd: "2026-09-24", maxTripDays: 10,
  }),
}));
