import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type {
  DetailActivity,
  DetailNearby,
  DetailTransfer,
  ProductDetail,
} from "./types";
import "./detail.css";
import { ExportControls } from './ExportControls';

type Group = {
  key: string;
  date: string;
  day: number;
  activity: DetailActivity;
  items: DetailNearby[];
};
type Information = { title: string; body: string[]; map?: string };
const keyFor = (date: string, id: string) => JSON.stringify([date, id]);
const domId = (kind: string, key: string) =>
  `detail-${kind}-${encodeURIComponent(key)}`;
const name = (activity: DetailActivity) =>
  activity.place_name || activity.title;
const clock = (value?: string | null) =>
  value?.match(/T(\d{2}:\d{2})/)?.[1] || "Time unavailable";
const cost = (money: DetailActivity["estimated_cost"]) =>
  money ? `${money.currency} ${money.amount}` : "Cost to confirm";
const mapLink = (place: string, area?: string | null) =>
  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([place, area].filter(Boolean).join(", "))}`;
const safeSource = (value?: string | null) => {
  try {
    const url = new URL(value || "");
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
};

const trustedTransfer = (detail: ProductDetail, transfer: DetailTransfer) =>
  detail.provenance === "generated" &&
  detail.trust === "generated_projection" &&
  transfer.status !== "source_claim";

function transferFeasibility(detail: ProductDetail, transfer: DetailTransfer) {
  if (!trustedTransfer(detail, transfer)) {
    const claim = transfer.source_status ?? transfer.validation_state;
    return {
      label: `Unverified source claim${claim ? ` (${claim})` : ""}`,
      message: "Source claims are not a fresh route or timing check.",
      className: "has-unknown",
    };
  }
  if (transfer.validation_state === "CONFIRMED")
    return {
      label: "Timing conflict remains",
      message:
        "The adopted transfer has a confirmed timing conflict between the supplied activities.",
      className: "has-conflict",
    };
  if (transfer.validation_state === "PASS")
    return {
      label: "Fits supplied timing",
      message:
        "The adopted transfer fits the supplied activity timing. This is a snapshot, not a live route update.",
      className: "",
    };
  return {
    label: "Transfer feasibility unverified",
    message:
      "Available information does not establish whether the transfer fits the supplied activity timing.",
    className: "has-unknown",
  };
}

function InformationDialog({
  information,
  close,
}: {
  information: Information;
  close: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      className="detail-dialog"
      ref={ref}
      onClose={close}
      aria-labelledby="detail-dialog-title"
    >
      <h2 id="detail-dialog-title">{information.title}</h2>
      {information.body.map((text, i) => (
        <p key={i}>{text}</p>
      ))}
      <div className="modal-actions">
        {information.map && (
          <a
            className="btn btn-light"
            href={information.map}
            target="_blank"
            rel="noopener noreferrer"
          >
            View on map ↗
          </a>
        )}
        <button
          className="btn btn-primary"
          onClick={() => ref.current?.close()}
        >
          Close
        </button>
      </div>
    </dialog>
  );
}

function NearbyRows({
  items,
  other = false,
  show,
}: {
  items: DetailNearby[];
  other?: boolean;
  show: (value: Information) => void;
}) {
  return items.map((item, i) => (
    <div className="nearby-item" key={i}>
      <div
        className="nearby-photo detail-illustration"
        aria-label="Illustration, not a place photograph"
      >
        ⌂
      </div>
      <div className="nearby-body">
        <strong>{item.place_name}</strong>
        {other && (
          <p className="detail-source-anchor">
            Anchor: {item.anchor_activity_id ?? "not supplied"} · Date:{" "}
            {item.associated_day ?? "not supplied"}
          </p>
        )}
        <div className="nearby-actions">
          <button
            onClick={() =>
              show({
                title: item.place_name,
                body: [
                  item.reason || "Optional nearby reference.",
                  item.area || "Address unavailable.",
                  item.uncertainty ||
                    "Availability, prices and accessibility are unverified. This is not a scheduled visit.",
                  item.attribution || "",
                  "Illustration shown; place photograph unavailable.",
                ].filter(Boolean),
                map: mapLink(item.place_name, item.area),
              })
            }
          >
            Details →
          </button>
        </div>
      </div>
    </div>
  ));
}

export function TripDetail({ detail, onReplan }: { detail: ProductDetail; onReplan?: () => void }) {
  const [filter, setFilter] = useState<string | null>(null);
  const [closedDays, setClosedDays] = useState<Set<string>>(() => new Set());
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set());
  const [inlineOpen, setInlineOpen] = useState<Set<string>>(() => new Set());
  const [selected, setSelected] = useState<{ key: string } | null>(null);
  const [pending, setPending] = useState<{
    key: string;
    destination: "stop" | "group";
  } | null>(null);
  const [information, setInformation] = useState<Information | null>(null);
  const { groups, other } = useMemo(() => {
    const candidates: Group[] = detail.days.flatMap((day, i) =>
      day.activities
        .filter((a) => a.time_use !== "free_window")
        .map((activity) => ({
          key: keyFor(day.date, activity.activity_id),
          date: day.date,
          day: i + 1,
          activity,
          items: [],
        })),
    );
    const other: DetailNearby[] = [];
    for (const item of detail.nearby) {
      const matches = candidates.filter(
        (g) =>
          item.anchor_activity_id === g.activity.activity_id &&
          (!item.associated_day || item.associated_day === g.date),
      );
      if (matches.length === 1) matches[0].items.push(item);
      else other.push(item);
    }
    return { groups: candidates.filter((g) => g.items.length), other };
  }, [detail]);
  useEffect(() => {
    if (!selected) return;
    const timer = window.setTimeout(() => setSelected(null), 2600);
    return () => window.clearTimeout(timer);
  }, [selected]);
  useEffect(() => {
    if (!pending) return;
    const mobile = window.matchMedia?.("(max-width:800px)").matches;
    const kind =
      pending.destination === "stop" ? "stop" : mobile ? "inline" : "group";
    const target = document.getElementById(domId(kind, pending.key));
    (pending.destination === "stop"
      ? target
      : target?.querySelector("button")
    )?.focus({ preventScroll: true });
    target?.scrollIntoView?.({
      block: "center",
      behavior: window.matchMedia?.("(prefers-reduced-motion:reduce)").matches
        ? "instant"
        : "smooth",
    });
  }, [pending]);
  useEffect(() => {
    const media = window.matchMedia?.("(max-width:800px)");
    if (!media) return;
    let focusedKey: string | undefined;
    const rememberFocus = (event: FocusEvent) => {
      focusedKey = (event.target as HTMLElement).closest<HTMLElement>(
        "[data-nearby-key]",
      )?.dataset.nearbyKey;
    };
    const relocateFocus = () => {
      const active =
        document.activeElement?.closest<HTMLElement>("[data-nearby-key]");
      // Browsers can blur a CSS-hidden control before dispatching the media event.
      const key =
        active?.dataset.nearbyKey ||
        (document.activeElement === document.body ? focusedKey : undefined);
      if (!key) return;
      const target = document.getElementById(
        domId(media.matches ? "inline" : "group", key),
      );
      target?.querySelector("button")?.focus({ preventScroll: true });
    };
    document.addEventListener("focusin", rememberFocus);
    media.addEventListener("change", relocateFocus);
    return () => {
      document.removeEventListener("focusin", rememberFocus);
      media.removeEventListener("change", relocateFocus);
    };
  }, []);
  const toggle = (
    set: React.Dispatch<React.SetStateAction<Set<string>>>,
    key: string,
  ) =>
    set((previous) => {
      const next = new Set(previous);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  const locate = (group: Group, destination: "stop" | "group") => {
    setClosedDays(
      (previous) =>
        new Set([...previous].filter((date) => date !== group.date)),
    );
    setCollapsed(
      (previous) => new Set([...previous].filter((key) => key !== group.key)),
    );
    if (window.matchMedia?.("(max-width:800px)").matches)
      setInlineOpen((previous) => new Set(previous).add(group.key));
    if (filter && filter !== group.date) setFilter(group.date);
    setSelected({ key: group.key });
    setPending({ key: group.key, destination });
  };
  const activityInfo = (activity: DetailActivity) =>
    setInformation({
      title: name(activity),
      body: [
        activity.location || "Location unavailable.",
        `${activity.start_time} — ${activity.end_time}`,
        activity.introduction || "",
        activity.notes || "No additional notes.",
        activity.time_use === "free_window"
          ? "Free time · no fixed place."
          : cost(activity.estimated_cost),
        "Illustration shown; place photograph unavailable.",
      ].filter(Boolean),
      map:
        activity.time_use === "free_window"
          ? undefined
          : mapLink(name(activity), activity.location),
    });
  const transferInfo = (transfer: DetailTransfer) =>
    setInformation({
      title: `${transfer.mode || "Transport"} connection`,
      body: [
        `${transfer.from_activity_id} → ${transfer.to_activity_id}`,
        transfer.provider_duration_seconds == null
          ? "Duration unavailable."
          : `${Math.ceil(transfer.provider_duration_seconds / 60)} min estimated duration`,
        transfer.distance_meters == null
          ? "Distance unavailable."
          : `${transfer.distance_meters} m`,
        `Departure: ${transfer.departure_time || transfer.preceding_end_time || "not supplied"}. Arrival: ${transfer.arrival_time || "not supplied"}. Next activity: ${transfer.following_start_time || "not supplied"}.`,
        `Buffer: ${transfer.reserve_seconds == null ? "not supplied" : `${transfer.reserve_seconds} seconds`}. Estimate: ${transfer.estimate_kind}.`,
        `${transferFeasibility(detail, transfer).label}. ${transferFeasibility(detail, transfer).message}`,
        trustedTransfer(detail, transfer)
          ? `Route evidence: ${transfer.estimate_kind} estimate in the supplied generated snapshot. ${transfer.status === "unknown" ? "Evidence availability remains to confirm." : "Evidence availability does not independently establish timing feasibility."}`
          : `The source describes the estimate as ${transfer.estimate_kind}; this evidence has not been independently checked.`,
        ...transfer.unknowns,
        transfer.attribution || "",
      ].filter(Boolean),
    });
  const visibleOther = other.filter(
    (n) => !filter || !n.associated_day || n.associated_day === filter,
  );
  const activityCount = detail.days.reduce(
    (total, d) =>
      total + d.activities.filter((a) => a.time_use !== "free_window").length,
    0,
  );
  const sourceLabel =
    detail.trust === "source_fixture"
      ? "Historical example · source claims, not a fresh verification"
      : detail.trust === "unverified_import"
        ? "Imported content · not regenerated or rechecked"
        : "Generated itinerary · saved evidence snapshot";
  return (
    <div className="detail-page">
      <section className="detail-hero detail-example-hero">
        <div className="container detail-hero-inner">
          <Link to="/trips" className="detail-back">
            ← My trips
          </Link>
          <span className="source-pill">
            {detail.provenance === "example"
              ? "CURATED EXAMPLE"
              : detail.provenance.toUpperCase()}
          </span>
          <h1>{detail.title}</h1>
          <p>
            {detail.destination} · {detail.start_date || "Dates unavailable"}
            {detail.end_date ? ` — ${detail.end_date}` : ""}
          </p>
          {onReplan && <div className="detail-hero-buttons"><button type="button" className="btn btn-primary" onClick={onReplan}>Plan again</button></div>}
          <span className="detail-art-credit">Landscape illustration</span>
        </div>
      </section>
      <div className="container detail-body">
        <ExportControls detail={detail} />
        <nav className="detail-anchor-nav" aria-label="Itinerary sections">
          {[
            ["overview", "Overview"],
            ["daily", "Daily itinerary"],
            ["transport", "Connections"],
            ["weather", "Weather"],
          ].map(([id, label]) => (
            <a href={`#${id}`} key={id}>
              {label}
            </a>
          ))}
          <button
            onClick={() => {
              const group = groups.find((g) => !filter || g.date === filter);
              if (group) locate(group, "group");
              else document.getElementById("nearby-other")?.scrollIntoView();
            }}
          >
            Nearby
          </button>
        </nav>
        <p className="trip-notice">
          {sourceLabel}. Confirm access, opening hours, prices and weather
          before travel.
        </p>
        <div className="detail-grid">
          <div className="detail-main">
            <section className="content-card overview-panel" id="overview">
              <div className="content-heading">
                <span className="section-icon" aria-hidden="true">
                  ▤
                </span>
                <h2>Trip overview</h2>
              </div>
              <p className="overview-lead">
                {detail.description ||
                  "Your days, places and connections, together in one itinerary."}
              </p>
              <div className="stat-grid">
                <div>
                  <strong>{detail.days.length}</strong>
                  <span>days</span>
                </div>
                <div>
                  <strong>{activityCount}</strong>
                  <span>planned stops</span>
                </div>
                <div>
                  <strong>{detail.transfers.length}</strong>
                  <span>connections</span>
                </div>
                <div>
                  <strong className="overview-budget">
                    {detail.request?.budget ? cost(detail.request.budget) : "—"}
                  </strong>
                  <span>
                    {detail.request?.budget
                      ? "whole-trip budget · not actual spend"
                      : "costs to confirm"}
                  </span>
                </div>
              </div>
              {detail.completion && (
                <details className="review-panel">
                  <summary>
                    Planning review · {detail.completion.policy_completion}
                  </summary>
                  {detail.completion.policy_reasons.map((reason, i) => (
                    <p key={i}>{reason}</p>
                  ))}
                  {detail.completion.source_claims?.map((claim, i) => <p key={`source-${i}`}>Unverified source claim: {claim}</p>)}
                  {detail.completion.preference_coverage.map((coverage, i) => (
                    <p key={i}>
                      {coverage.preference}: {coverage.scheduled}/
                      {coverage.target} · {coverage.status}
                    </p>
                  ))}
                  {detail.completion.minimum_daily_coverage.map(
                    (coverage, i) => (
                      <p key={i}>
                        {coverage.date}: {coverage.countable_primary_activities}{" "}
                        planned stops · {coverage.status}. {coverage.reason}
                      </p>
                    ),
                  )}
                </details>
              )}
            </section>
            <section className="content-card days-panel" id="daily">
              <div className="content-heading">
                <span className="section-icon" aria-hidden="true">
                  ▦
                </span>
                <h2>Daily itinerary</h2>
                <button
                  className="btn btn-quiet btn-tiny"
                  onClick={() => setClosedDays(new Set())}
                >
                  Expand all
                </button>
              </div>
              <div className="day-filter" aria-label="Filter days">
                <button
                  aria-pressed={!filter}
                  className={!filter ? "active" : ""}
                  onClick={() => setFilter(null)}
                >
                  All days
                </button>
                {detail.days.map((day, i) => (
                  <button
                    key={day.date}
                    aria-label={`Filter Day ${i + 1} · ${day.date}`}
                    aria-pressed={filter === day.date}
                    className={filter === day.date ? "active" : ""}
                    onClick={() => setFilter(day.date)}
                  >
                    Day {i + 1}
                    <small>{day.date}</small>
                  </button>
                ))}
              </div>
              {!detail.days.length && <p>No day information is available.</p>}
              {detail.days.map(
                (day, i) =>
                  (!filter || day.date === filter) && (
                    <article className="day-block" key={day.date}>
                      <button
                        className="day-header"
                        aria-label={`Day ${i + 1} · ${day.date}`}
                        aria-expanded={!closedDays.has(day.date)}
                        aria-controls={`day-${i}`}
                        onClick={() => toggle(setClosedDays, day.date)}
                      >
                        <span className="day-counter">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span className="day-head-copy">
                          <strong>
                            Day {i + 1} · {day.date}
                          </strong>
                          <small>
                            {
                              day.activities.filter(
                                (a) => a.time_use !== "free_window",
                              ).length
                            }{" "}
                            places / activities ·{" "}
                            {day.weather?.summary || "Weather unavailable"}
                          </small>
                        </span>
                        <span aria-hidden="true">⌄</span>
                      </button>
                      <div
                        id={`day-${i}`}
                        className="day-events"
                        hidden={closedDays.has(day.date)}
                      >
                        {!day.activities.length && (
                          <p>No scheduled activities for this day.</p>
                        )}
                        {day.activities.map((activity) => {
                          const key = keyFor(day.date, activity.activity_id);
                          const group = groups.find((g) => g.key === key);
                          const free = activity.time_use === "free_window";
                          return (
                            <div
                              className="activity-wrap"
                              key={activity.activity_id}
                            >
                              <div className="activity-item">
                                <div className="activity-time">
                                  <strong>{clock(activity.start_time)}</strong>
                                  <span>{clock(activity.end_time)}</span>
                                </div>
                                <div className="activity-marker" />
                                <div
                                  className={`activity-content ${free ? "free-window" : ""} ${selected?.key === key ? "nearby-linked-selected" : ""}`}
                                  id={domId("stop", key)}
                                  tabIndex={-1}
                                  aria-label={`${name(activity)} on ${day.date}`}
                                >
                                  {!free && (
                                    <button
                                      className="activity-photo detail-illustration"
                                      aria-label={`View ${name(activity)}`}
                                      onClick={() => activityInfo(activity)}
                                    >
                                      <span aria-hidden="true">⌂</span>
                                      <small>Illustration</small>
                                    </button>
                                  )}
                                  <div className="activity-details">
                                    <span className="activity-tag">
                                      {free
                                        ? "Free time · no fixed place"
                                        : activity.category ||
                                          "Planned activity"}
                                    </span>
                                    <h3>{name(activity)}</h3>
                                    {activity.location && !free && (
                                      <p>{activity.location}</p>
                                    )}
                                    {activity.introduction && (
                                      <p className="activity-intro">
                                        {activity.introduction}
                                      </p>
                                    )}
                                    <div className="activity-meta">
                                      <span>
                                        {clock(activity.start_time)}–
                                        {clock(activity.end_time)}
                                      </span>
                                      {!free && (
                                        <span>
                                          {cost(activity.estimated_cost)}
                                        </span>
                                      )}
                                    </div>
                                    <div className="activity-actions">
                                      <button
                                        className="mini-link"
                                        onClick={() => activityInfo(activity)}
                                      >
                                        Details →
                                      </button>
                                      {!free && (
                                        <a
                                          className="mini-link"
                                          href={mapLink(
                                            name(activity),
                                            activity.location,
                                          )}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                        >
                                          Map ↗
                                        </a>
                                      )}
                                      {group && (
                                        <button
                                          className="mini-link nearby-pill detail-desktop-nearby"
                                          aria-label={`Show ${group.items.length} nearby places for ${name(activity)} on ${day.date}`}
                                          onClick={() => locate(group, "group")}
                                        >
                                          Nearby · {group.items.length} →
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                  {group && (
                                    <section
                                      className="nearby-inline"
                                      id={domId("inline", key)}
                                      data-nearby-key={key}
                                    >
                                      <button
                                        className="nearby-inline-trigger"
                                        aria-label={`Show nearby for ${name(activity)} on ${day.date}`}
                                        aria-expanded={inlineOpen.has(key)}
                                        aria-controls={domId(
                                          "inline-items",
                                          key,
                                        )}
                                        onClick={() =>
                                          toggle(setInlineOpen, key)
                                        }
                                      >
                                        ⌖ Nearby · {group.items.length} places{" "}
                                        <span aria-hidden="true">⌄</span>
                                      </button>
                                      <div
                                        className="nearby-inline-items"
                                        id={domId("inline-items", key)}
                                        hidden={!inlineOpen.has(key)}
                                      >
                                        <p className="nearby-inline-note">
                                          Optional places · not scheduled visits
                                        </p>
                                        <NearbyRows
                                          items={group.items}
                                          show={setInformation}
                                        />
                                      </div>
                                    </section>
                                  )}
                                </div>
                              </div>
                              {detail.transfers
                                .filter(
                                  (t) =>
                                    t.from_activity_id === activity.activity_id,
                                )
                                .map((t, j) => (
                                  <button
                                    className="transfer-connector"
                                    key={j}
                                    onClick={() => transferInfo(t)}
                                  >
                                    <span className="transfer-line" />
                                    <span
                                      className={`transfer-copy ${transferFeasibility(detail, t).className}`}
                                    >
                                      {t.mode || "Transport"} ·{" "}
                                      {t.provider_duration_seconds == null
                                        ? "Duration unavailable"
                                        : `${Math.ceil(t.provider_duration_seconds / 60)} min`}{" "}
                                      · {transferFeasibility(detail, t).label} →
                                    </span>
                                  </button>
                                ))}
                            </div>
                          );
                        })}
                      </div>
                    </article>
                  ),
              )}
            </section>
            <section className="content-card transport-panel" id="transport">
              <div className="content-heading">
                <h2>Between one place and the next</h2>
              </div>
              {!detail.transfers.length && (
                <p className="aside-intro">
                  No connection information is available.
                </p>
              )}
              {detail.transfers
                .filter(
                  (t) =>
                    !filter ||
                    detail.days.some(
                      (d) =>
                        d.date === filter &&
                        d.activities.some(
                          (a) => a.activity_id === t.from_activity_id,
                        ),
                    ),
                )
                .map((t, i) => (
                  <button
                    className="transport-item"
                    key={i}
                    onClick={() => transferInfo(t)}
                  >
                    <span className="transport-no">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="transport-body">
                      <strong>
                        {detail.days
                          .flatMap((d) => d.activities)
                          .find((a) => a.activity_id === t.from_activity_id)
                          ?.title || t.from_activity_id}{" "}
                        →{" "}
                        {detail.days
                          .flatMap((d) => d.activities)
                          .find((a) => a.activity_id === t.to_activity_id)
                          ?.title || t.to_activity_id}
                      </strong>
                      <small>
                        {t.mode || "Mode unknown"} ·{" "}
                        {transferFeasibility(detail, t).label} · Details
                      </small>
                    </span>
                  </button>
                ))}
              <p className="footnote">
                Route estimates are a guide. Missing details remain to confirm.
              </p>
            </section>
          </div>
          <aside className="detail-sidebar">
            <section className="content-card weather-panel" id="weather">
              <div className="content-heading">
                <span className="section-icon" aria-hidden="true">
                  ☀
                </span>
                <h2>Weather at a glance</h2>
              </div>
              {detail.days
                .filter((d) => !filter || d.date === filter)
                .map((day, i) => (
                  <div className="weather-item" key={day.date}>
                    <span className="weather-day">{day.date}</span>
                    <div className="weather-summary">
                      <strong>
                        {day.weather?.summary || "Weather unavailable"}
                      </strong>
                      {day.weather?.temperature_min_c != null && (
                        <small>Low {day.weather.temperature_min_c}°C</small>
                      )}
                      {day.weather?.temperature_max_c != null && (
                        <small>High {day.weather.temperature_max_c}°C</small>
                      )}
                      {day.weather?.precipitation_probability_percent !=
                        null && (
                        <small>
                          Rain chance{" "}
                          {day.weather.precipitation_probability_percent}%
                        </small>
                      )}
                      {day.weather?.max_wind_speed_kph != null && (
                        <small>
                          Wind up to {day.weather.max_wind_speed_kph} km/h
                        </small>
                      )}
                      {day.weather?.attribution && (
                        <small>{day.weather.attribution}</small>
                      )}
                      {safeSource(day.weather?.source_url) && (
                        <a
                          href={safeSource(day.weather?.source_url)}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Weather source {i + 1} ↗
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              <p className="footnote">
                {detail.provenance === "example"
                  ? "Weather belongs to this historical example."
                  : "Weather is a snapshot. Check current conditions before you go."}
              </p>
            </section>
            <section className="content-card nearby-panel" id="nearby">
              <div className="nearby-sidebar-groups">
                <div className="content-heading">
                  <span className="section-icon" aria-hidden="true">
                    ⌖
                  </span>
                  <h2>Nearby · A little discovery</h2>
                </div>
                <p className="aside-intro">
                  Ideas near your planned stops. These are not scheduled visits.
                </p>
                {detail.days.map(
                  (day, i) =>
                    (!filter || day.date === filter) &&
                    groups.some((g) => g.date === day.date) && (
                      <section className="nearby-day" key={day.date}>
                        <h3>
                          DAY {i + 1} <span>· {day.date}</span>
                        </h3>
                        {groups
                          .filter((g) => g.date === day.date)
                          .map((group) => (
                            <section
                              className={`nearby-group ${selected?.key === group.key ? "nearby-linked-selected" : ""}`}
                              id={domId("group", group.key)}
                              data-nearby-key={group.key}
                              aria-label={`Nearby for ${name(group.activity)} on ${group.date}`}
                              key={group.key}
                            >
                              <div className="nearby-group-heading">
                                <button
                                  className="nearby-anchor-link"
                                  aria-label={`Find ${name(group.activity)} in Day ${group.day} itinerary`}
                                  onClick={() => locate(group, "stop")}
                                >
                                  <span>
                                    <strong>{name(group.activity)}</strong>
                                    <small>
                                      Around this stop · {group.items.length}{" "}
                                      places
                                    </small>
                                  </span>
                                </button>
                                <button
                                  className="nearby-group-toggle"
                                  aria-label={`${collapsed.has(group.key) ? "Expand" : "Collapse"} nearby for ${name(group.activity)} on ${group.date}`}
                                  aria-expanded={!collapsed.has(group.key)}
                                  aria-controls={domId("items", group.key)}
                                  onClick={() =>
                                    toggle(setCollapsed, group.key)
                                  }
                                >
                                  ⌄
                                </button>
                              </div>
                              <div
                                className="nearby-group-items"
                                id={domId("items", group.key)}
                                hidden={collapsed.has(group.key)}
                              >
                                <NearbyRows
                                  items={group.items}
                                  show={setInformation}
                                />
                              </div>
                            </section>
                          ))}
                      </section>
                    ),
                )}
                {!groups.some((g) => !filter || g.date === filter) && (
                  <p>No nearby ideas for these stops.</p>
                )}
              </div>
              {!!visibleOther.length && (
                <section
                  className="nearby-other"
                  id="nearby-other"
                  aria-label="Other nearby references"
                >
                  <h3>Other nearby references</h3>
                  <p className="aside-intro">
                    Optional places without a linked scheduled stop.
                  </p>
                  <NearbyRows
                    items={visibleOther}
                    other
                    show={setInformation}
                  />
                </section>
              )}
              <p className="footnote caution-text">
                Straight-line distances are not walking routes.
              </p>
            </section>
            <section className="content-card promise-card">
              <span className="eyebrow">DESIGNED FOR THE EXPERIENCE</span>
              <h3>
                More time for the place.
                <br />
                Less time for the planning.
              </h3>
              {onReplan ? <button type="button" className="text-link inline-action" onClick={onReplan}>Plan another journey →</button> : <Link to="/plan" className="text-link">Plan another journey →</Link>}
            </section>
          </aside>
        </div>
      </div>
      {information && (
        <InformationDialog
          information={information}
          close={() => setInformation(null)}
        />
      )}
    </div>
  );
}
