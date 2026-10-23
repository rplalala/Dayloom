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
  it.each(["preview", "saved"] as const)("keeps an unmet Rich pace visible in %s", mode => {
    render(<MemoryRouter><TripDetail mode={mode} detail={{ ...detail, provenance: "generated", trust: "generated_projection", completion: {
      policy_completion: "complete", policy_reasons: [], preference_coverage: [], minimum_daily_coverage: [],
      pace_review: { status: "partial", days: [
        { date: "2026-10-15", count: 2, target_count: 3, state: "residual" },
      ] },
    } }} /></MemoryRouter>);
    expect(screen.getByText("Rich pace is not fully met. Some days do not have three main visits.")).toBeVisible();
    expect(screen.queryByText(/Repair success|Repair complete/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/rtpeval|ACCEPTED_PARTIAL|residual/)).not.toBeInTheDocument();
  });

  it("keeps internal planning diagnostics out of the travel experience", () => {
    render(<MemoryRouter><TripDetail detail={{ ...detail, completion: {
      policy_completion: "incomplete", policy_reasons: ["internal_policy_reason"],
      source_claims: ["internal_source_claim"], preference_coverage: [],
      minimum_daily_coverage: [{ date: "2026-10-15", countable_primary_activities: 1,
        status: "satisfied", reason: "countable_primary_present_not_feasibility" }],
    } }} /></MemoryRouter>);
    expect(screen.queryByText(/Planning review/)).not.toBeInTheDocument();
    expect(screen.queryByText(/internal_policy_reason|internal_source_claim|countable_primary_present_not_feasibility/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Anchor:|saved evidence snapshot|source claims/)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Daily itinerary" })).toBeVisible();
  });
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
      "Travel time to confirm",
    ],
    [
      "generated",
      "generated_projection",
      "confirmed",
      "PASS",
      null,
      "Fits your schedule",
    ],
    [
      "generated",
      "generated_projection",
      "confirmed",
      null,
      null,
      "Travel time to confirm",
    ],
    [
      "example",
      "source_fixture",
      "confirmed",
      "PASS",
      null,
      "Fits your schedule",
    ],
    [
      "example",
      "source_fixture",
      "source_claim",
      "PASS",
      "PASS",
      "Travel time to confirm",
    ],
    [
      "imported",
      "unverified_import",
      "confirmed",
      "PASS",
      "PASS",
      "Travel time to confirm",
    ],
    [
      "generated",
      "generated_projection",
      "source_claim",
      "CONFIRMED",
      "CONFIRMED",
      "Travel time to confirm",
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
        screen.getByRole("button", { name: /The Rocks → The Rocks Walking/ }),
      ).toHaveTextContent(label);
      await user.click(connector);
      const dialog = screen.getByRole("dialog");
      expect(within(dialog).getByText(label, { exact: false })).toBeVisible();
      expect(within(dialog).queryByText(/Route evidence|source claim|generated snapshot|Estimate:|Buffer:|PASS|CONFIRMED/)).not.toBeInTheDocument();
      expect(within(dialog).getByText(/check current routes before you travel/i)).toBeVisible();
    },
  );
  it("keeps weather compact until its daily summary is opened", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><TripDetail detail={{ ...detail, days: [{
      ...detail.days[0], date: "2026-10-23", weather: {
        summary: "Clear", temperature_min_c: 14, temperature_max_c: 22,
        precipitation_probability_percent: 20, max_wind_speed_kph: 18,
        attribution: "Weather fixture", source_url: "https://example.invalid/weather",
      },
    }] }} /></MemoryRouter>);
    const summary = screen.getByLabelText("Weather details for Oct 23");
    expect(within(summary).getByText("≈18°C")).toBeVisible();
    expect(within(summary).getByText("20%")).toBeVisible();
    expect(screen.getByText("Low 14°C")).not.toBeVisible();
    expect(screen.getByText("Wind up to 18 km/h")).not.toBeVisible();
    await user.click(summary);
    expect(screen.getByText("Low 14°C")).toBeVisible();
    expect(screen.getByText("High 22°C")).toBeVisible();
    expect(screen.getByText("Wind up to 18 km/h")).toBeVisible();
    expect(screen.getByText("Average estimated from the daily low and high.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Weather source 1 ↗" })).toHaveAttribute("href", "https://example.invalid/weather");
    await user.click(summary);
    expect(screen.getByText("Low 14°C")).not.toBeVisible();
  });
  it("shows supplied zero costs and weather metrics while rejecting unsafe source links", async () => {
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
    const summary = screen.getByLabelText("Weather details for Oct 15");
    expect(within(summary).getByText("≈0°C")).toBeVisible();
    expect(within(summary).getByText("0%")).toBeVisible();
    await userEvent.click(screen.getByLabelText("Weather details for Oct 15"));
    expect(screen.getByText("Low 0°C")).toBeVisible();
    expect(screen.getByText("Rain chance 0%")).toBeVisible();
    expect(screen.getByText("Wind up to 0 km/h")).toBeVisible();
    expect(
      screen.queryByRole("link", { name: /Weather source/ }),
    ).not.toBeInTheDocument();
  });
  it("does not invent an average or rain chance when a day's inputs are incomplete", async () => {
    render(<MemoryRouter><TripDetail detail={{ ...detail, days: [{
      ...detail.days[0], weather: { temperature_min_c: 14 },
    }] }} /></MemoryRouter>);
    const summary = screen.getByLabelText("Weather details for Oct 15");
    expect(within(summary).getByText("Avg —")).toBeVisible();
    expect(within(summary).getByText("—")).toBeVisible();
    await userEvent.click(summary);
    expect(screen.getByText("Low 14°C")).toBeVisible();
    expect(screen.queryByText(/Average estimated/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Rain chance \d/)).not.toBeInTheDocument();
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
      within(other).queryByText(/Anchor:/),
    ).not.toBeInTheDocument();
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
