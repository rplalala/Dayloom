import { isDialogBackdropClick } from '../../../shared/dialog';
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import type {
  DetailActivity,
  DetailNearby,
  DetailTransfer,
  ProductDetail,
} from "./types";
import "./detail.css";
import { Icon } from "../Icon";
import { WeatherRow } from "./WeatherRow";
import { monthDay, weekday, dottedDate, routeDuration, routeDistance, illustrationFor, transferFeasibility, paceNotice } from "./display";
import { ExperienceGuidance } from './ExperienceGuidance';
import { ExportControls } from './ExportControls';
import { DestinationPhoto, PlacePhoto, SupportingPhoto } from './MediaPhoto';
import { PlaceMedia, PlaceMediaActions, usePlaceMedia } from './media';
import { photoFingerprint, photoGeneration } from './photoSession';

type Group = {
  key: string;
  date: string;
  day: number;
  activity: DetailActivity;
  items: DetailNearby[];
};
type Information = {
  title: string;
  icon: string;
  introduction?: string;
  photo?: { slot: string; label: string; fallback: string; atmosphere?: boolean };
  notes: { heading: ReactNode; body: ReactNode; className?: string }[];
  stats?: { duration: string; distance: string };
  body?: string[];
  map?: string;
};
const keyFor = (date: string, id: string) => JSON.stringify([date, id]);
const domId = (kind: string, key: string) =>
  `detail-${kind}-${encodeURIComponent(key)}`;
const name = (activity: DetailActivity) =>
  activity.place_name || activity.title;
const clock = (value?: string | null) =>
  value?.match(/T(\d{2}:\d{2})/)?.[1] || "Time unavailable";
const cost = (money: DetailActivity["estimated_cost"]) =>
  money ? `${money.currency} ${money.amount}` : "Cost to confirm";
const hasPlacePhoto = (activity: DetailActivity) => activity.time_use !== 'free_window'
  && activity.activity_kind !== 'generic_activity' && activity.activity_kind !== 'transport';
const modeName = (mode?: string | null) => ({ WALK: "Walking", TRANSIT: "Public transit", DRIVE: "Driving" }[mode || ""] || "Transport to confirm");
const modeIcon = (mode?: string | null) => ({ WALK: "walk", TRANSIT: "bus", DRIVE: "car" }[mode || ""] || "info");
const mapLink = (place: string, area?: string | null) =>
  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([place, area].filter(Boolean).join(", "))}`;


function InformationDialog({
  information,
  close,
  refreshPhotos,
}: {
  information: Information;
  close: () => void;
  refreshPhotos?: (slot: string) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const dismiss = () => {
    ref.current?.close();
    close();
  };
  useEffect(() => {
    const opener = document.activeElement;
    const dialog = ref.current;
    dialog?.showModal();
    return () => {
      if (dialog?.open) dialog.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);
  return (
    <dialog
      className="modal-card detail-dialog"
      ref={ref}
      onCancel={event => { event.preventDefault(); dismiss(); }}
      onClick={event => {
        if (isDialogBackdropClick(event)) dismiss();
      }}
      aria-labelledby="detail-dialog-title"
    >
      <button type="button" className="modal-close" aria-label="Close dialog" onClick={dismiss}><Icon name="close" size={21} /></button>
      <div className="modal-icon"><Icon name={information.icon} size={23} /></div>
      <h2 id="detail-dialog-title">{information.title}</h2>
      {information.photo && <div className="photo-large">{information.photo.atmosphere
        ? <SupportingPhoto fullCredit className="dialog-place-photo" {...information.photo} />
        : <PlacePhoto fullCredit className="dialog-place-photo" {...information.photo} />}</div>}
      {information.photo && refreshPhotos && <button type="button" className="inline-action media-refresh" onClick={() => refreshPhotos(information.photo!.slot)}>Refresh photo</button>}
      {information.introduction && <p>{information.introduction}</p>}
      {information.stats && <div className="route-big-stats"><div><strong>{information.stats.duration}</strong><span>Estimated duration</span></div><div><strong>{information.stats.distance}</strong><span>Route distance</span></div></div>}
      {information.notes.map((note, i) => <div className="detail-note" key={i}><strong className={note.className}>{note.heading}</strong><span>{note.body}</span></div>)}
      {information.body?.map((text, i) => (
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
            View on map <Icon name="external" size={15} />
          </a>
        )}
        <button
          className="btn btn-primary"
          onClick={dismiss}
        >
          Close
        </button>
      </div>
    </dialog>
  );
}

function NearbyRows({
  items,
  show,
  positionOf,
}: {
  items: DetailNearby[];
  show: (value: Information) => void;
  positionOf: (item: DetailNearby) => number;
}) {
  const informationFor = (item: DetailNearby): Information => ({
    title: item.place_name,
    icon: "pin",
    photo: { slot: `nearby:${positionOf(item)}`, label: item.place_name, fallback: item.illustration_key ? `/dayloom/${item.illustration_key}.svg` : illustrationFor(item.place_name) },
    introduction: item.reason || "An optional place near a planned stop.",
    notes: [
      { heading: "Location", body: item.area || "Address unavailable." },
      { heading: "Before you go", body: item.uncertainty || "Availability, prices and accessibility are unverified. This is not a scheduled visit." },
    ],
    body: item.attribution ? [item.attribution] : [],
    map: mapLink(item.place_name, item.area),
  });
  return items.map((item, i) => (
    <div className="nearby-item nearby-media-item" key={i}>
      <PlacePhoto className="nearby-media" slot={`nearby:${positionOf(item)}`} fallback={item.illustration_key ? `/dayloom/${item.illustration_key}.svg` : undefined} label={item.place_name} onOpen={() => show(informationFor(item))}>
      <div className="nearby-body">
        <strong>{item.place_name}</strong>
        <div className="nearby-actions">
          <button
            aria-label="Details →"
            onClick={() =>
              show(informationFor(item))
            }
          >
            Details <Icon name="chevron" size={13} />
          </button>
        </div>
      </div>
      </PlacePhoto>
    </div>
  ));
}

function NearbyInline({ group, open, onToggle, show, positionOf }: {
  group: Group;
  open: boolean;
  onToggle: () => void;
  show: (value: Information) => void;
  positionOf: (item: DetailNearby) => number;
}) {
  return <section className="nearby-inline" id={domId('inline', group.key)} data-nearby-key={group.key}>
    <button className={`nearby-inline-trigger ${open ? 'open' : ''}`}
      aria-label={`Show nearby for ${name(group.activity)} on ${group.date}`}
      aria-expanded={open} aria-controls={domId('inline-items', group.key)} onClick={onToggle}>
      <Icon name="pin" size={20} /> Nearby · {group.items.length} places <Icon name="down" size={20} />
    </button>
    <div className="nearby-inline-items" id={domId('inline-items', group.key)} hidden={!open}>
      <p className="nearby-inline-note">Optional places · not scheduled visits</p>
      <NearbyRows items={group.items} show={show} positionOf={positionOf} />
    </div>
  </section>;
}

export function TripDetail({ detail, mediaEndpoint, mediaOwner, onReplan, actions, mode }: { detail: ProductDetail; mediaEndpoint?: string; mediaOwner?: string | null; onReplan?: () => void; actions?: ReactNode; mode?: "preview" | "saved" }) {
  const paceMessage = paceNotice(detail.completion?.pace_review);
  const positionOf = (item: DetailNearby) => detail.nearby.indexOf(item);
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
  const media = usePlaceMedia(mediaEndpoint, [
    ...detail.days.flatMap(day => day.activities
      .filter(hasPlacePhoto)
      .map(activity => `activity:${activity.activity_id}`)),
    ...detail.nearby.map((_, index) => `nearby:${index}`),
  ], mediaOwner === undefined ? undefined : { owner: mediaOwner, generation: photoGeneration(mediaOwner), snapshot: photoFingerprint(detail) });
  const themes = Object.fromEntries(detail.days.flatMap(day => day.activities
    .filter(activity => activity.activity_kind === 'generic_activity' && activity.time_use === 'scheduled')
    .map(activity => [`activity:${activity.activity_id}`, activity.atmosphere_theme || 'general'])));
  const supportingEndpoint = mediaEndpoint && Object.keys(themes).length
    ? `${mediaEndpoint.replace(/\/media$/, '/supporting-media')}?width=360&height=240` : undefined;
  const supportingMedia = usePlaceMedia(supportingEndpoint, Object.keys(themes), mediaOwner === undefined ? undefined : {
    owner: mediaOwner, generation: photoGeneration(mediaOwner), snapshot: photoFingerprint(detail),
    provider: 'Unsplash', kind: 'atmosphere', width: 360, height: 240, themes,
  });
  const combinedMedia = {
    items: { ...media.items, ...supportingMedia.items },
    refresh: (slot: string) => themes[slot] ? supportingMedia.refresh(slot) : media.refresh(slot),
    imageFailed: (slot: string, value: Parameters<typeof media.imageFailed>[1]) =>
      themes[slot] ? supportingMedia.imageFailed(slot, value) : media.imageFailed(slot, value),
  };
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
      icon: "pin",
      photo: activity.time_use === 'free_window' || activity.activity_kind === 'transport' ? undefined : {
        slot: `activity:${activity.activity_id}`, label: name(activity), atmosphere: activity.activity_kind === 'generic_activity',
        fallback: activity.illustration_key ? `/dayloom/${activity.illustration_key}.svg` : illustrationFor(`${name(activity)} ${activity.category || ""}`),
      },
      introduction: [activity.place_name, activity.location || "Location unavailable."].filter(Boolean).join("\n"),
      notes: [
        { heading: <><Icon name="clock" size={17} />{activity.time_use === "free_window" ? "Free time" : "Planned visit"}</>, body: `${dottedDate(activity.start_time)} · ${clock(activity.start_time)}–${clock(activity.end_time)}` },
        ...(activity.introduction ? [{ heading: "About this place", body: activity.introduction }] : []),
        { heading: "Good to know", body: activity.notes || "No additional notes." },
        ...(activity.time_use === "free_window" ? [] : [{ heading: "Estimated cost", body: activity.estimated_cost ? cost(activity.estimated_cost) : "Check admission and booking prices before you go." }]),
      ],
      map:
        activity.time_use === "free_window"
          ? undefined
          : mapLink(name(activity), activity.location),
    });
  const transferInfo = (transfer: DetailTransfer) =>
    setInformation({
      title: modeName(transfer.mode),
      icon: modeIcon(transfer.mode),
      introduction: [transfer.from_activity_id, transfer.to_activity_id].map(id => {
        const activity = detail.days.flatMap(day => day.activities).find(activity => activity.activity_id === id);
        return activity ? name(activity) : "Planned stop";
      }).join(" → "),
      stats: { duration: routeDuration(transfer.provider_duration_seconds), distance: routeDistance(transfer.distance_meters) },
      notes: [
        { heading: "Time between visits", body: `Previous activity ends ${clock(transfer.preceding_end_time || detail.days.flatMap(day => day.activities).find(activity => activity.activity_id === transfer.from_activity_id)?.end_time)}; next begins ${clock(transfer.following_start_time || detail.days.flatMap(day => day.activities).find(activity => activity.activity_id === transfer.to_activity_id)?.start_time)}.${transfer.reserve_seconds != null ? `\nAllow an additional ${routeDuration(transfer.reserve_seconds)} buffer.` : "\nAllow time for delays."}` },
        { heading: transferFeasibility(detail, transfer).label, body: transferFeasibility(detail, transfer).message, className: transferFeasibility(detail, transfer).className === "has-conflict" ? "state-conflict" : transferFeasibility(detail, transfer).className ? "state-unknown" : "state-ok" },
      ],
      body: ["Travel times are estimates. Check current routes before you travel.", transfer.attribution || ""].filter(Boolean),
    });
  const visibleOther = other.filter(
    (n) => !filter || !n.associated_day || n.associated_day === filter,
  );
  const activityCount = detail.days.reduce(
    (total, d) =>
      total + d.activities.filter((a) => a.time_use !== "free_window").length,
    0,
  );
  return (
    <PlaceMediaActions.Provider value={combinedMedia}><PlaceMedia.Provider value={combinedMedia.items}><div className="detail-page">
      <section className="detail-hero">
        <div className="detail-cover"><DestinationPhoto owner={mediaOwner ?? null} destination={detail.destination} label={`${detail.destination} destination atmosphere`} fallback={detail.illustration_key ? `/dayloom/${detail.illustration_key}.svg` : undefined} className="detail-hero-image" /><div className="detail-cover-shade" /></div>
        <div className="container detail-hero-inner">
          <Link to={mode === "preview" ? "/plan?recover=1" : "/trips"} className="detail-back"><Icon name="back" size={17} />{mode === "preview" ? "Back to previews" : "Back to My trips"}</Link>
          <span className="detail-eyebrow">YOUR JOURNEY, DAY BY DAY</span>
          <h1>{detail.title}</h1>
          <div className="detail-meta"><span><Icon name="pin" size={17} />{detail.destination}</span><span><Icon name="calendar" size={17} />{dottedDate(detail.start_date)}{detail.end_date ? ` — ${dottedDate(detail.end_date)}` : ""}</span><span><Icon name="layers" size={17} />{detail.days.length} days / {activityCount} stops</span>{detail.request?.traveler_count && <span><Icon name="users" size={17} />{detail.request.traveler_count} travelers</span>}</div>
          <div className="detail-hero-buttons">{onReplan && <button type="button" className="btn btn-primary" onClick={onReplan}><Icon name="spark" size={17} />Plan again</button>}<ExportControls detail={detail} />{actions}</div>
        </div>
      </section>
      <div className="container detail-below">
        <nav className="detail-anchor-nav" aria-label="Itinerary sections">
          {[["overview", "layers", "Overview"], ["daily", "calendar", "Daily itinerary"], ["transport", "walk", "Connections"], ["weather", "sun", "Weather"]].map(([id, icon, label]) => <button key={id} onClick={() => document.getElementById(id)?.scrollIntoView({ block: "start", behavior: window.matchMedia?.("(prefers-reduced-motion:reduce)").matches ? "instant" : "smooth" })}><Icon name={icon} size={17} />{label}</button>)}
          <button
            onClick={() => {
              const group = groups.find((g) => !filter || g.date === filter);
              if (group) locate(group, "group");
              else document.getElementById("nearby-other")?.scrollIntoView();
            }}
          >
            <Icon name="pin" size={17} /> Nearby
          </button>
        </nav>

        <div className="detail-grid">
          <div className="detail-main">
            <section className="content-card overview-panel" id="overview">
              <div className="content-heading">
                <span className="section-icon" aria-hidden="true">
                  <Icon name="layers" size={21} />
                </span>
                <h2>Trip overview</h2><span className="historical-pill"><Icon name="info" size={13} />{mode === "preview" ? "Unsaved preview" : detail.provenance === "example" ? "Example itinerary" : detail.provenance === "imported" ? "Imported itinerary" : mode === "saved" ? "Saved itinerary" : "Generated itinerary"}</span>
              </div>
              <p className="overview-lead">
                {detail.description ||
                  "Your days, places and connections, together in one itinerary."}
              </p>
              {paceMessage && <p className="footnote caution-text" role="status">{paceMessage}</p>}
              <ExperienceGuidance detail={detail} onLocate={(date, activityId) => {
                const day = detail.days.findIndex(day => day.date === date);
                const activity = detail.days[day]?.activities.find(item => item.activity_id === activityId);
                if (activity) locate({ key: keyFor(date, activityId), date, day: day + 1, activity, items: [] }, 'stop');
              }} />
              <div className="stat-grid">
                <div>
                  <strong>{String(detail.days.length).padStart(2, "0")}</strong>
                  <span>days</span>
                </div>
                <div>
                  <strong>{String(activityCount).padStart(2, "0")}</strong>
                  <span>planned stops</span>
                </div>
                <div>
                  <strong>{String(detail.transfers.length).padStart(2, "0")}</strong>
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
              {Boolean(detail.display_tags?.length || detail.request?.additional_preferences) && <div className="request-overview">{(detail.display_tags?.length ? detail.display_tags : detail.request?.additional_preferences?.split(/\n+/).filter(Boolean) || []).map((text, index) => <span key={index}>{text}</span>)}</div>}
              <details className="source-details"><summary>Before you go</summary><p>{detail.provenance === "imported" ? "This imported itinerary has not been checked. " : detail.provenance === "example" ? "This historical example keeps its original travel dates. " : ""}Confirm access, opening hours, prices and weather before travel.</p></details>
            </section>
            <section className="content-card days-panel" id="daily">
              <div className="content-heading">
                <span className="section-icon" aria-hidden="true">
                  <Icon name="calendar" size={21} />
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
                    <small>{monthDay(day.date)}</small>
                  </button>
                ))}
              </div>
              {!detail.days.length && <p>No day information is available.</p>}
              {detail.days.map(
                (day, i) =>
                  (!filter || day.date === filter) && (
                    <article className={`day-block ${closedDays.has(day.date) ? "" : "open"}`} key={day.date}>
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
                            {monthDay(day.date)} · {weekday(day.date)} <span>DAY {String(i + 1).padStart(2, "0")}</span>
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
                        <Icon name="down" size={20} />
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
                          const supporting = !free && activity.activity_kind === 'generic_activity';
                          const transport = activity.activity_kind === 'transport';
                          const cardRole = free ? 'free-window' : supporting ? 'supporting-activity'
                            : activity.activity_kind === 'main_poi' ? 'principal-visit' : 'unknown-activity';
                          return (
                            <div
                              className="activity-wrap"
                              key={activity.activity_id}
                            >
                              {transport ? <div className="transport-event">
                                <button type="button" id={domId('stop', key)}
                                  className={`transfer-connector scheduled-transport ${selected?.key === key ? 'nearby-linked-selected' : ''}`}
                                  aria-label={`${name(activity)} · ${clock(activity.start_time)}–${clock(activity.end_time)}`}
                                  onClick={() => activityInfo(activity)}>
                                  <span className="transfer-line" aria-hidden="true" />
                                  <span className="transfer-copy">
                                    <Icon name="route" size={17} />
                                    <span>{name(activity)} <small>{clock(activity.start_time)}–{clock(activity.end_time)}</small></span>
                                    <Icon name="chevron" size={14} />
                                  </span>
                                </button>
                                {group && <>
                                  <button className="mini-link detail-desktop-nearby transport-nearby"
                                    aria-label={`Show ${group.items.length} nearby places for ${name(activity)} on ${day.date}`}
                                    onClick={() => locate(group, 'group')}>
                                    <Icon name="pin" size={13} /> Nearby · {group.items.length} <Icon name="chevron" size={12} />
                                  </button>
                                  <NearbyInline group={group} open={inlineOpen.has(key)}
                                    onToggle={() => toggle(setInlineOpen, key)} show={setInformation} positionOf={positionOf} />
                                </>}
                              </div> : <div className={`activity-item ${supporting ? 'supporting-event' : ''}`}>
                                <div className="activity-time">
                                  <strong>{clock(activity.start_time)}</strong>
                                  <span>{clock(activity.end_time)}</span>
                                </div>
                                <div className="activity-marker" aria-hidden="true" />
                                <div
                                  className={`activity-content ${cardRole} ${selected?.key === key ? "nearby-linked-selected" : ""}`}
                                  role="group"
                                  id={domId("stop", key)}
                                  tabIndex={-1}
                                  aria-label={`${name(activity)} on ${day.date}`}
                                >
                                  {free && <span className="free-glyph"><Icon name="leaf" size={30} /></span>}
                                  {hasPlacePhoto(activity) && (
                                    <PlacePhoto fallback={activity.illustration_key ? `/dayloom/${activity.illustration_key}.svg` : illustrationFor(`${name(activity)} ${activity.category || ""}`)} className="activity-photo" slot={`activity:${activity.activity_id}`} label={name(activity)} onOpen={() => activityInfo(activity)} />
                                  )}
                                  {supporting && <SupportingPhoto slot={`activity:${activity.activity_id}`}
                                    label={name(activity)} onOpen={() => activityInfo(activity)} />}
                                  <div className="activity-details">
                                    <span className="activity-tag">
                                      {free
                                        ? "Free time · no fixed place"
                                        : supporting ? "Along the way" : activity.activity_kind === 'main_poi' ? "Main visit" : activity.category ||
                                          "Planned activity"}
                                    </span>
                                    <h3>{name(activity)}</h3>
                                    {activity.location && !free && (
                                      <p><Icon name="pin" size={14} />{activity.location}</p>
                                    )}
                                    {activity.introduction && (
                                      <p className="activity-intro">
                                        {activity.introduction}
                                      </p>
                                    )}
                                    {supporting && !activity.introduction && activity.notes && (
                                      <p className="activity-intro">{activity.notes}</p>
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
                                        Details <Icon name="chevron" size={14} />
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
                                          Map <Icon name="external" size={14} />
                                        </a>
                                      )}
                                      {group && (
                                        <button
                                          className="mini-link nearby-pill detail-desktop-nearby"
                                          aria-label={`Show ${group.items.length} nearby places for ${name(activity)} on ${day.date}`}
                                          onClick={() => locate(group, "group")}
                                        >
                                          <Icon name="pin" size={13} /> Nearby · {group.items.length} <Icon name="chevron" size={12} />
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                  {group && (
                                    <NearbyInline group={group} open={inlineOpen.has(key)}
                                      onToggle={() => toggle(setInlineOpen, key)} show={setInformation} positionOf={positionOf} />
                                  )}
                                </div>
                              </div>}
                              {detail.transfers
                                .filter(
                                  (t) =>
                                    t.from_activity_id === activity.activity_id,
                                )
                                .map((t, j) => (
                                  <button
                                    className="transfer-connector"
                                    aria-label={`${t.mode || "Transport"} · ${t.provider_duration_seconds == null ? "Duration unavailable" : `${Math.ceil(t.provider_duration_seconds / 60)} min`} · ${transferFeasibility(detail, t).label} →`}
                                    key={j}
                                    onClick={() => transferInfo(t)}
                                  >
                                    <span className="transfer-line" />
                                    <span
                                      className={`transfer-copy ${transferFeasibility(detail, t).className}`}
                                    >
                                      <span><Icon name={modeIcon(t.mode)} size={17} /> {modeName(t.mode)} · {routeDuration(t.provider_duration_seconds)} <small>· {routeDistance(t.distance_meters)}</small></span>
                                      <span className={`state-label ${transferFeasibility(detail, t).className === "has-conflict" ? "state-conflict" : transferFeasibility(detail, t).className ? "state-unknown" : "state-ok"}`}><Icon name={transferFeasibility(detail, t).className === "has-conflict" ? "alert" : transferFeasibility(detail, t).className ? "info" : "check"} size={13} /> {transferFeasibility(detail, t).label}</span>
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
                <span className="section-icon"><Icon name="walk" size={21} /></span><h2>Between one place and the next</h2><span className="small-muted">{detail.transfers.length} connections</span>
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
                          ?.place_name || detail.days.flatMap(d => d.activities).find(a => a.activity_id === t.from_activity_id)?.title || "Planned stop"}{" "}
                        →{" "}
                        {detail.days
                          .flatMap((d) => d.activities)
                          .find((a) => a.activity_id === t.to_activity_id)
                          ?.place_name || detail.days.flatMap(d => d.activities).find(a => a.activity_id === t.to_activity_id)?.title || "Planned stop"}
                      </strong>
                      <small>
                        {modeName(t.mode)} ·{" "}
                        {transferFeasibility(detail, t).label}
                      </small><span className="transport-metrics"><Icon name={(t.mode || "").toLowerCase().includes("walk") ? "walk" : "route"} size={16} />{routeDuration(t.provider_duration_seconds)} · {routeDistance(t.distance_meters)}</span>
                    </span><Icon name="chevron" size={17} />
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
                <span className="section-icon weather-icon" aria-hidden="true">
                  <Icon name="sun" size={20} />
                </span>
                <h2>Weather at a glance</h2>
              </div>
              <p className="aside-intro">A little context for each day.</p>
              {detail.days
                .filter((d) => !filter || d.date === filter)
                .map((day, i) => (
                  <WeatherRow key={day.date} day={day} sourceNumber={i + 1} />
                ))}
              <p className="footnote">
                {detail.provenance === "example"
                  ? "Weather belongs to this historical example."
                  : "Weather is a snapshot. Check current conditions before you go."}
              </p>
            </section>
            <section className={`content-card nearby-panel ${visibleOther.length ? "has-other" : ""}`} id="nearby">
              <div className="nearby-sidebar-groups">
                <div className="content-heading">
                  <span className="section-icon nearby-icon" aria-hidden="true">
                    <Icon name="pin" size={20} />
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
                          DAY {String(i + 1).padStart(2, "0")} <span>· {monthDay(day.date)}</span>
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
                                  <Icon name="pin" size={15} />
                                  <span>
                                    <strong>{name(group.activity)}</strong>
                                    <small>
                                      Around this stop · {group.items.length}{" "}
                                      places
                                    </small>
                                  </span>
                                </button>
                                <button
                                  className={`nearby-group-toggle ${collapsed.has(group.key) ? "" : "open"}`}
                                  aria-label={`${collapsed.has(group.key) ? "Expand" : "Collapse"} nearby for ${name(group.activity)} on ${group.date}`}
                                  aria-expanded={!collapsed.has(group.key)}
                                  aria-controls={domId("items", group.key)}
                                  onClick={() =>
                                    toggle(setCollapsed, group.key)
                                  }
                                ><Icon name="down" size={14} /></button>
                              </div>
                              <div
                                className="nearby-group-items"
                                id={domId("items", group.key)}
                                hidden={collapsed.has(group.key)}
                              >
                                <NearbyRows
                                  items={group.items}
                                  show={setInformation}
                                  positionOf={positionOf}
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
                    show={setInformation}
                    positionOf={positionOf}
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
              <p>Keep your own rhythm. Make room for the next discovery.</p>
              {onReplan ? <button type="button" className="text-link inline-action" onClick={onReplan}>Plan another journey →</button> : <Link to="/plan" className="text-link">Plan another journey →</Link>}
            </section>
          </aside>
        </div>
      </div>
      {information && (
        <InformationDialog
          information={information}
          close={() => setInformation(null)}
          refreshPhotos={mediaEndpoint ? combinedMedia.refresh : undefined}
        />
      )}
    </div></PlaceMedia.Provider></PlaceMediaActions.Provider>
  );
}
