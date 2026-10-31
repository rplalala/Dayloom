import type { ProductDetail, DetailTransfer, PaceReview, RequiredExperience } from "./types";

export function requiredExperienceNotice(row: RequiredExperience): string {
  if (row.status === "satisfied") return "Included in your itinerary.";
  if (row.reason === "required_visits_not_scheduled") return "Your requested visits or dates are not fully arranged. Keep this in mind when reviewing your days.";
  return "This experience is still missing from the confirmed itinerary. You can plan again to include it.";
}

export function paceNotice(review?: PaceReview | null): string | null {
  if (!review) return null;
  if (review.status === "partial" && review.days.some(day => day.state === "residual" && day.target_count === 3)) {
    return "Some days have a lighter schedule than your chosen pace.";
  }
  if (review.status === "partial" || review.status === "unavailable") {
    return null;
  }
  if (review.status === "not_attempted") return null;
  if (review.days.some(day => day.state === "source_overridden")) {
    return "Your specific daily requests take priority over Rich pace.";
  }
  return null;
}

/** Locale-stable date labels; ISO values remain the operation and activity keys. */
export function monthDay(value: string): string {
  const date = new Date(`${value.slice(0, 10)}T12:00:00Z`);
  return Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat("en", { month: "short", day: "numeric", timeZone: "UTC" }).format(date) : "Date not set";
}

export function weekday(value: string): string {
  const date = new Date(`${value.slice(0, 10)}T12:00:00Z`);
  return Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat("en", { weekday: "short", timeZone: "UTC" }).format(date) : "";
}

export const dottedDate = (value?: string | null) => value ? value.slice(0, 10).replaceAll("-", ".") : "Dates not set";
export const routeDuration = (seconds?: number | null) => seconds == null ? "Time to confirm" : `${Math.ceil(seconds / 60)} min`;
export const routeDistance = (meters?: number | null) => meters == null ? "Distance to confirm" : meters >= 1000 ? `${(meters / 1000).toFixed(1)} km` : `${Math.round(meters)} m`;

export function destinationCover(destination: string): 'sydney' | 'london' | 'nature' {
  if (/^sydney\b/i.test(destination)) return 'sydney';
  if (/^london\b/i.test(destination)) return 'london';
  return 'nature';
}

/** Display themes never confer place verification or accept source-provided URLs. */
export function illustrationFor(value: string): string {
  if (/harbour|harbor|sydney|the rocks|opera/i.test(value)) return "/dayloom/sydney.svg";
  if (/gallery|museum|art|historic house/i.test(value)) return "/dayloom/art.svg";
  if (/city|architecture|tower|building|street|neighborhood|cafe|café|market/i.test(value)) return "/dayloom/city.svg";
  return "/dayloom/nature.svg";
}

const trustedTransfer = (detail: ProductDetail, transfer: DetailTransfer) =>
  ((detail.provenance === "generated" && detail.trust === "generated_projection") ||
    (detail.provenance === "example" && detail.trust === "source_fixture")) &&
  transfer.status !== "source_claim";

export function transferFeasibility(detail: ProductDetail, transfer: DetailTransfer) {
  if (!trustedTransfer(detail, transfer)) {
    return {
      label: "Travel time to confirm",
      message: "Travel time for this itinerary has not been checked.",
      className: "has-unknown",
    };
  }
  if (transfer.validation_state === "CONFIRMED")
    return {
      label: "Timing conflict remains",
      message:
        "There may not be enough time to get between these stops.",
      className: "has-conflict",
    };
  if (transfer.validation_state === "PASS")
    return {
      label: "Fits your schedule",
      message:
        "The estimated travel time fits between these stops.",
      className: "",
    };
  return {
    label: "Travel time to confirm",
    message:
      "Check the travel time between these stops before you go.",
    className: "has-unknown",
  };
}
