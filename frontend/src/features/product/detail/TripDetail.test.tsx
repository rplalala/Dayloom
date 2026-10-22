import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { TripDetail } from "./TripDetail";
import type { ProductDetail } from "./types";

// JSDOM does not implement the browser's native modal-opening method.
const nativeShowModal = HTMLDialogElement.prototype.showModal;
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
});
afterAll(() => {
  HTMLDialogElement.prototype.showModal = nativeShowModal;
});

const detail: ProductDetail = {
  schema_version: "product_detail_1",
  id: "test",
  title: "A supplied trip",
  destination: "Sydney",
  provenance: "example",
  trust: "source_fixture",
  request: null,
  days: [
    {
      date: "2026-10-15",
      activities: [
        {
          activity_id: "later",
          title: "The Rocks",
          start_time: "2026-10-15T10:00:00+11:00",
          end_time: "2026-10-15T11:00:00+11:00",
          time_use: "scheduled",
        },
      ],
    },
    {
      date: "2026-10-13",
      activities: [
        {
          activity_id: "first",
          title: "The Rocks",
          start_time: "2026-10-13T10:00:00+11:00",
          end_time: "2026-10-13T11:00:00+11:00",
          time_use: "scheduled",
        },
      ],
    },
    { date: "2026-10-14", activities: [] },
  ],
  transfers: [],
  nearby: [
    {
      place_name: "First café",
      anchor_activity_id: "first",
      associated_day: "2026-10-13",
    },
    {
      place_name: "Second café",
      anchor_activity_id: "first",
      associated_day: "2026-10-13",
    },
    {
      place_name: "Later café",
      anchor_activity_id: "later",
      associated_day: "2026-10-15",
    },
    { place_name: "Undated anchored café", anchor_activity_id: "later" },
    {
      place_name: "Wrong date",
      anchor_activity_id: "first",
      associated_day: "2026-10-15",
    },
    {
      place_name: "<img src=x onerror=alert(1)>",
      anchor_activity_id: "missing",
      associated_day: null,
    },
  ],
};

describe("Product detail", () => {
  it.each([
    [
      "generated",
      "generated_projection",
      "confirmed",
      "CONFIRMED",
      null,
      "Timing conflict remains",
    ],
    [
      "generated",
      "generated_projection",
      "unknown",
      "CONFIRMED",
      null,
      "Timing conflict remains",
    ],
    [
      "generated",
      "generated_projection",
      "confirmed",
      "UNKNOWN",
      null,
      "Transfer feasibility unverified",
    ],
    [
      "generated",
      "generated_projection",
      "confirmed",
      "PASS",
      null,
      "Fits supplied timing",
    ],
    [
      "generated",
      "generated_projection",
      "confirmed",
      null,
      null,
      "Transfer feasibility unverified",
    ],
    [
      "example",
      "source_fixture",
      "source_claim",
      "PASS",
      "PASS",
      "Unverified source claim (PASS)",
    ],
    [
      "imported",
      "unverified_import",
      "confirmed",
      "PASS",
      "PASS",
      "Unverified source claim (PASS)",
    ],
    [
      "generated",
      "generated_projection",
      "source_claim",
      "CONFIRMED",
      "CONFIRMED",
      "Unverified source claim (CONFIRMED)",
    ],
  ] as const)(
    "preserves transfer feasibility separately from evidence for %s/%s/%s/%s",
    async (
      provenance,
      trust,
      status,
      validation_state,
      source_status,
      label,
    ) => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <TripDetail
            detail={{
              ...detail,
              provenance,
              trust,
              transfers: [
                {
                  from_activity_id: "later",
                  to_activity_id: "first",
                  mode: "WALK",
                  provider_duration_seconds: 1800,
                  status,
                  validation_state,
                  source_status,
                  estimate_kind: "provider",
                  unknowns: [],
                },
              ],
            }}
          />
        </MemoryRouter>,
      );
      const connector = screen.getByRole("button", {
        name: `WALK · 30 min · ${label} →`,
      });
      expect(connector).toBeVisible();
      expect(
        screen.getByRole("button", { name: /The Rocks → The Rocks WALK/ }),
      ).toHaveTextContent(label);
      await user.click(connector);
      const dialog = screen.getByRole("dialog");
      expect(within(dialog).getByText(label, { exact: false })).toBeVisible();
      if (label.startsWith("Unverified")) {
        expect(
          within(dialog).getByText(
            /Source claims are not a fresh route or timing check/,
          ),
        ).toBeVisible();
        expect(
          within(dialog).queryByText(/Fits supplied timing/),
        ).not.toBeInTheDocument();
        expect(
          within(dialog).getByText(
            /this evidence has not been independently checked/,
          ),
        ).toBeVisible();
      } else {
        expect(
          within(dialog).getByText(
            /Route evidence: provider estimate in the supplied generated snapshot/,
          ),
        ).toBeVisible();
      }
    },
  );
  it("shows supplied zero costs and weather metrics while rejecting unsafe source links", () => {
    const supplied: ProductDetail = {
      ...detail,
      days: [
        {
          ...detail.days[0],
          weather: {
            summary: "Clear",
            temperature_min_c: 0,
            temperature_max_c: 0,
            precipitation_probability_percent: 0,
            max_wind_speed_kph: 0,
            source_url: "javascript:alert(1)",
          },
          activities: [
            {
              ...detail.days[0].activities[0],
              estimated_cost: { amount: "0", currency: "AUD" },
            },
          ],
        },
      ],
    };
    render(
      <MemoryRouter>
        <TripDetail detail={supplied} />
      </MemoryRouter>,
    );
    expect(screen.getByText("AUD 0")).toBeVisible();
    expect(screen.getByText("Low 0°C")).toBeVisible();
    expect(screen.getByText("Rain chance 0%")).toBeVisible();
    expect(screen.getByText("Wind up to 0 km/h")).toBeVisible();
    expect(
      screen.queryByRole("link", { name: /Weather source/ }),
    ).not.toBeInTheDocument();
  });
  it("keeps actual day order, exact Nearby counts, unresolved source anchors and synchronized filters", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <TripDetail detail={detail} />
      </MemoryRouter>,
    );
    expect(
      screen
        .getAllByRole("button", { name: /^Day \d ·/ })
        .map((b) => b.textContent),
    ).toEqual([
      expect.stringContaining("Oct 15"),
      expect.stringContaining("Oct 13"),
      expect.stringContaining("Oct 14"),
    ]);
    expect(
      screen.getByRole("button", {
        name: "Show 2 nearby places for The Rocks on 2026-10-13",
      }),
    ).toBeVisible();
    expect(
      within(
        screen.getByRole("region", {
          name: "Nearby for The Rocks on 2026-10-15",
        }),
      ).getByText("Undated anchored café"),
    ).toBeVisible();
    const other = screen.getByRole("region", {
      name: "Other nearby references",
    });
    expect(
      within(other).getByText("Anchor: first · Date: 2026-10-15"),
    ).toBeVisible();
    expect(
      within(other).getByText("<img src=x onerror=alert(1)>"),
    ).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Filter Day 2 · 2026-10-13" }),
    );
    expect(
      screen.queryByRole("region", {
        name: "Nearby for The Rocks on 2026-10-15",
      }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Wrong date")).not.toBeInTheDocument();
    expect(
      within(other).getByText("<img src=x onerror=alert(1)>"),
    ).toBeVisible();
    expect(
      within(
        screen.getByRole("region", {
          name: "Nearby for The Rocks on 2026-10-13",
        }),
      ).getByText("First café"),
    ).toBeVisible();
  });
});
