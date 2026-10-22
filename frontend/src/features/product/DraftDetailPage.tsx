import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useSession } from "./session";
import { draftRequest, DraftFailure, type Draft } from "./drafts";
import { restoreBrief } from "./editor";
import { submissionGeneration } from "./taskClient";
import { isValidISODate } from "../planning/datePolicy";
import { isListedCurrency } from "../planning/currencies";
import { CuratedPhoto } from "./detail/MediaPhoto";
import { dottedDate } from "./detail/display";
import { Icon } from "./Icon";
import "./detail/detail.css";

export function DraftDetailPage() {
  const { draftId = "" } = useParams();
  const { account, status, refresh } = useSession();
  if (status === "loading") return <p className="container page" role="status">Checking your session…</p>;
  if (!account) return <div className="container page"><h1>Your draft is private.</h1><p>Log in to the same account to view it.</p><Link to={`/login?return=${encodeURIComponent(`/drafts/${draftId}`)}`}>Log in</Link></div>;
  return <OwnedDraft key={`${account.id}:${account.csrf_token}:${draftId}:${submissionGeneration(account.id)}`} id={draftId} owner={account.id} refresh={refresh} />;
}

function OwnedDraft({ id, owner, refresh }: { id: string; owner: string; refresh: () => Promise<void> }) {
  const [result, setResult] = useState<{ draft?: Draft; error?: string }>({});
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const generation = submissionGeneration(owner);
    const valid = () => !controller.signal.aborted && submissionGeneration(owner) === generation;
    setResult({});
    draftRequest<Draft>(`/api/drafts/${encodeURIComponent(id)}`, "GET", undefined, undefined, controller.signal).then(draft => {
      if (valid()) setResult({ draft });
    }, failure => {
      if (!valid()) return;
      setResult({ error: "This draft is unavailable." });
      if (failure instanceof DraftFailure && failure.status === 401) void refresh();
    });
    return () => controller.abort();
  }, [id, owner, refresh, retry]);
  if (result.error) return <div className="container page"><h1>{result.error}</h1><button className="btn btn-light" onClick={() => setRetry(value => value + 1)}>Reload draft</button><Link to="/trips">Back to My trips</Link></div>;
  if (!result.draft) return <p className="container page" role="status">Loading draft…</p>;
  const draft = result.draft;
  // A draft is an incomplete editor snapshot, never an itinerary or provider result.
  const editor = restoreBrief(draft.editor);
  const budget = editor.budget.trim() && Number.isFinite(Number(editor.budget)) && Number(editor.budget) >= 0 && isListedCurrency(editor.currency) ? `${editor.currency} ${Number(editor.budget).toLocaleString("en", { maximumFractionDigits: 2 })}` : null;
  const travelers = /^[1-9]\d*$/.test(editor.travelers) && Number.isSafeInteger(Number(editor.travelers)) ? editor.travelers : null;
  const destination = editor.destination || "Destination not set";
  const continuePath = `/plan?draft=${encodeURIComponent(id)}`;
  const dateLabel = (value: string) => dottedDate(isValidISODate(value) ? value : null);
  const scrollTo = (section: string) => document.getElementById(section)?.scrollIntoView({ block: "start", behavior: window.matchMedia?.("(prefers-reduced-motion:reduce)").matches ? "instant" : "smooth" });
  return <div className="detail-page">
    <section className="detail-hero"><div className="detail-cover"><CuratedPhoto image={/sydney/i.test(editor.destination) ? "sydney" : "nature"} label={`${destination} destination atmosphere`} className="detail-hero-image" /><div className="detail-cover-shade" /></div><div className="container detail-hero-inner">
      <Link to="/trips" className="detail-back"><Icon name="back" size={17} />Back to My trips</Link><span className="detail-eyebrow">YOUR NEXT IDEA</span><h1>{draft.title}</h1>
      <div className="detail-meta"><span><Icon name="pin" size={17} />{destination}</span><span><Icon name="calendar" size={17} />{dateLabel(editor.start_date)} — {dateLabel(editor.end_date)}</span><span><Icon name="layers" size={17} />0 days / 0 stops</span>{travelers && <span><Icon name="users" size={17} />{travelers} travelers</span>}</div>
      <div className="detail-hero-buttons"><Link className="btn btn-primary" to={continuePath}><Icon name="spark" size={17} />Continue planning</Link></div>
    </div></section>
    <div className="container detail-below"><nav className="detail-anchor-nav" aria-label="Itinerary sections">{[["overview", "layers", "Overview"], ["daily", "calendar", "Daily itinerary"], ["transport", "walk", "Connections"], ["weather", "sun", "Weather"], ["nearby", "pin", "Nearby"]].map(([section, icon, label]) => <button type="button" key={section} onClick={() => scrollTo(section)}><Icon name={icon} size={17} />{label}</button>)}</nav>
      <div className="detail-grid"><div className="detail-main">
        <section className="content-card overview-panel" id="overview"><div className="content-heading"><span className="section-icon"><Icon name="layers" size={21} /></span><h2>Trip overview</h2><span className="historical-pill"><Icon name="info" size={13} />Planning draft</span></div><p className="overview-lead">Your ideas are saved. Come back and make them a journey.</p><div className="stat-grid"><div><strong>00</strong><span>days</span></div><div><strong>00</strong><span>planned stops</span></div><div><strong>00</strong><span>connections</span></div><div><strong className={budget ? "overview-budget" : undefined}>{budget || "—"}</strong><span>{budget ? "whole-trip budget · not actual spend" : "costs to confirm"}</span></div></div></section>
        <section className="content-card days-panel" id="daily"><div className="content-heading"><span className="section-icon"><Icon name="calendar" size={21} /></span><h2>Daily itinerary</h2></div><div className="empty-state inline-empty"><div className="empty-illustration"><Icon name="layers" size={32} /></div><h3>Room for your next journey.</h3><p>Keep shaping your brief, then bring your days together.</p><Link className="btn btn-primary" to={continuePath}>Continue this brief</Link></div></section>
        <section className="content-card transport-panel" id="transport"><div className="content-heading"><span className="section-icon"><Icon name="walk" size={21} /></span><h2>Between one place and the next</h2><span className="small-muted">0 connections</span></div><p className="aside-intro">No connection information is available.</p></section>
      </div><aside className="detail-sidebar">
        <section className="content-card weather-panel" id="weather"><div className="content-heading"><span className="section-icon weather-icon"><Icon name="sun" size={20} /></span><h2>Weather at a glance</h2></div><p className="aside-intro">A little context for each day.</p><p className="aside-intro">Choose your dates to plan your days.</p><p className="footnote"><Icon name="info" size={14} />Saved weather is a snapshot; check current conditions before you go.</p></section>
        <section className="content-card nearby-panel" id="nearby"><div className="nearby-sidebar-groups"><div className="content-heading"><span className="section-icon nearby-icon"><Icon name="pin" size={21} /></span><h2>Nearby · A little discovery</h2></div><p className="aside-intro">Ideas near your planned stops. These are not scheduled visits.</p><p className="nearby-empty">No nearby ideas for these stops.</p></div></section>
        <section className="content-card promise-card"><span className="eyebrow">DESIGNED FOR THE EXPERIENCE</span><h3>More time for the place.<br />Less time for the planning.</h3><p>Keep your own rhythm. Make room for the next discovery.</p><Link className="text-link inline-action" to={continuePath}>Plan another journey <Icon name="arrow" size={17} /></Link></section>
      </aside></div>
    </div>
  </div>;
}
