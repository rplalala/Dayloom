import { isDialogBackdropClick } from '../../shared/dialog';
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSession } from "./session";
import { DraftFailure, draftRequest, type LibraryCard, type LibraryPageResult } from "./drafts";
import "./library.css";
import { CopyControls } from './CopyControls';
import { Icon } from "./Icon";
import { isValidISODate } from "../planning/datePolicy";
import { dottedDate } from "./detail/display";
import type { PreviewDecision } from "./PreviewDecision";
import type { ProductDetail } from "./detail/types";
import { DestinationPhoto } from './detail/MediaPhoto';
import { invalidatePhotos } from './detail/photoSession';

export function LibraryCollection() {
  const session = useSession();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [offset, setOffset] = useState(0);
  const [reload, setReload] = useState(0);
  const [page, setPage] = useState<LibraryPageResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const emptyCollection = page?.total === 0 && !search;
  const [action, setAction] = useState<{ kind: "menu" | "rename" | "delete"; card: LibraryCard } | null>(null);
  const [title, setTitle] = useState("");
  const [copyNotice, setCopyNotice] = useState<PreviewDecision | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const owner = session.account!.id;
  const cardKey = page?.items.map(card => `${card.kind}:${card.id}:${card.revision}`).join("|") || "";
  const [summaries, setSummaries] = useState<{ owner: string; key: string; values: Record<string, ProductDetail> } | null>(null);
  useEffect(() => {
    if (!page) return;
    const controller = new AbortController();
    void Promise.all(page.items.filter(card => card.kind === "saved").map(async card => {
      try {
        const detail = await draftRequest<ProductDetail>(`/api/trips/${encodeURIComponent(card.id)}`, "GET", undefined, undefined, controller.signal);
        return Array.isArray(detail?.days) && Array.isArray(detail?.transfers) ? [card.id, detail] as const : null;
      } catch (failure) {
        if (!controller.signal.aborted && failure instanceof DraftFailure && failure.status === 401) void current.current.refresh();
        return null;
      }
    })).then(values => { if (!controller.signal.aborted) setSummaries({ owner, key: cardKey, values: Object.fromEntries(values.filter(value => value !== null)) }); });
    return () => controller.abort();
  }, [page, owner, cardKey]);
  const current = useRef(session);
  current.current = session;
  useEffect(() => {
    const controller = new AbortController();
    setPage(null); setError("");
    draftRequest<LibraryPageResult>(`/api/library?q=${encodeURIComponent(search)}&sort=${sort}&limit=4&offset=${offset}`, "GET", undefined, undefined, controller.signal)
      .then(value => { if (!controller.signal.aborted) setPage(value); })
      .catch(failure => {
        if (controller.signal.aborted) return;
        setError(failure instanceof Error ? failure.message : "Collection unavailable.");
        if (failure instanceof DraftFailure && failure.status === 401) void current.current.refresh();
      });
    return () => controller.abort();
  }, [owner, search, sort, offset, reload]);
  useEffect(() => {
    if (query === search) return;
    const timer = window.setTimeout(() => { setSearch(query); setOffset(0); }, 200);
    return () => window.clearTimeout(timer);
  }, [query, search]);
  useEffect(() => { if (action && !dialog.current?.open) dialog.current?.showModal(); else if (!action) dialog.current?.close(); }, [action]);

  async function mutate(card: LibraryCard, kind: "copy" | "rename" | "delete") {
    const account = session.account;
    if (!account || (kind === "copy" && card.kind !== "draft")) return;
    setBusy(true); setError("");
    try {
      await draftRequest(`/api/${card.kind === "draft" ? "drafts" : "trips"}/${card.id}${kind === "copy" ? "/copy" : kind === "delete" && card.kind === "draft" ? `?revision=${card.revision}` : ""}`,
        kind === "copy" ? "POST" : kind === "delete" ? "DELETE" : "PATCH", account.csrf_token,
        kind === "delete" ? (card.kind === "saved" ? { revision: card.revision, confirmed: true } : undefined) : { revision: card.revision, ...(kind === "rename" && { title }) });
      if (current.current.account?.id !== account.id) return;
      if (kind === 'delete' && card.kind === 'saved') invalidatePhotos({ owner: account.id, resource: `/api/trips/${encodeURIComponent(card.id)}/media` });
      setAction(null); setOffset(0); setReload(n => n + 1);
    } catch (failure) {
      if (current.current.account?.id !== account.id) return;
      setError(failure instanceof DraftFailure && failure.status === 409 ? "This item changed elsewhere. Reload your collection before trying again." : failure instanceof Error ? failure.message : "Unable to update this item.");
      if (failure instanceof DraftFailure && failure.status === 401) {
        setPage(null); setAction(null); setTitle("");
        await session.refresh();
      }
    } finally { setBusy(false); }
  }

  function copied(decision: PreviewDecision) {
    setCopyNotice(decision); setAction(null); setOffset(0); setReload(value => value + 1);
  }
  return <>
    {copyNotice && <div className="toast show library-copy-notice" role="status"><span>An independent copy was added to My trips.</span><Link to={`/trips/${copyNotice.saved_trip_id}`}>View saved copy</Link><button type="button" aria-label="Dismiss copy notice" onClick={() => setCopyNotice(null)}><Icon name="close" size={15} /></button></div>}
    {!emptyCollection && <section className="library-intro">
      <div className="library-count"><span className="eyebrow">YOUR COLLECTION</span><strong>{page ? String(page.total).padStart(2, "0") : "—"}</strong><span>{search ? "matching trips and drafts" : "saved trips and drafts"}</span></div>
      <div className="library-copy"><h2>Good places.<br /><em>Worth keeping.</em></h2><p>Plans to look forward to. Memories to return to.</p></div>
      <button className="btn btn-primary btn-large" onClick={() => { session.newBrief(); navigate("/plan"); }}><Icon name="plus" size={18} /> Create a trip</button>
    </section>}
    {!emptyCollection && <div className="library-tools trips-toolbar">
      <form className="search-box" role="search" onSubmit={event => { event.preventDefault(); setSearch(query); setOffset(0); }}><Icon name="search" size={18} /><input aria-label="Search trips" value={query} maxLength={100} placeholder="Search by trip name or destination" onChange={event => setQuery(event.target.value)} /></form>
      <label className="sort-box"><Icon name="sliders" size={16} /><select aria-label="Sort trips" value={sort} onChange={event => { setSort(event.target.value); setOffset(0); }}><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="name">By name</option></select></label>
    </div>}
    {error && !action && <div role="alert"><p>{error}</p><button className="btn btn-light" onClick={() => setReload(n => n + 1)}>Retry collection</button></div>}
    {!page && !error && <p role="status">Loading your collection…</p>}
    {page && page.total === 0 && (search ? <div className="empty-state"><Icon name="search" size={32} /><h3>No trips found</h3><p>Try a shorter name or a different destination.</p></div> : <section className="library-welcome" aria-labelledby="library-welcome-title">
      <div className="library-welcome-art" aria-hidden="true"><img src="/dayloom/journey.svg" alt="" /></div>
      <div className="library-welcome-copy">
        <span className="eyebrow">A LITTLE INSPIRATION, A NEW BEGINNING</span>
        <h2 id="library-welcome-title">Somewhere new is waiting.</h2>
        <p>A city you have been dreaming of. A few days to make your own. Start with an idea — your journeys will grow from here.</p>
        <button type="button" className="btn btn-primary btn-large" onClick={() => { session.newBrief(); navigate("/plan"); }}>Plan your first trip <Icon name="arrow" size={17} /></button>
        <span className="library-welcome-note">Your saved trips and travel briefs, all in one place.</span>
      </div>
    </section>)}
    {page && <div className="trip-grid">{page.items.map(card => {
      const path = card.kind === "draft" ? `/drafts/${card.id}` : `/trips/${card.id}`;
      const duration = isValidISODate(card.start_date || "") && isValidISODate(card.end_date || "") ? Math.max(0, Math.round((Date.parse(card.end_date) - Date.parse(card.start_date)) / 86400000) + 1) : card.kind === "draft" ? 0 : null;
      const detail = summaries?.owner === owner && summaries.key === cardKey ? summaries.values[card.id] : undefined;
      return <article className="trip-card" key={`${card.kind}:${card.id}`}>
        <div className="trip-card-photo">
          <DestinationPhoto link={{ to: path, label: `View ${card.title}` }} destination={card.destination || ''} label={card.destination ? `${card.destination} destination atmosphere` : 'Landscape atmosphere'} fallback={summaries?.owner === owner && summaries.key === cardKey && summaries.values[card.id]?.illustration_key ? `/dayloom/${summaries.values[card.id].illustration_key}.svg` : undefined} />
          <span className={`trip-status ${card.kind === "draft" ? "status-draft" : ""}`}>{card.kind === "draft" ? "Planning draft" : card.source === "imported" ? "Imported" : "Saved"}</span>
          <button type="button" className="card-menu-trigger" aria-label={`Manage ${card.title}`} aria-haspopup="dialog" aria-controls="library-management-dialog" aria-expanded={Boolean(action && action.card.id === card.id && action.card.kind === card.kind)} disabled={busy} onClick={() => { setError(""); setAction({ kind: "menu", card }); }}><Icon name="dots" size={19} /></button>
        </div>
        <div className="trip-card-body"><div className="trip-card-kicker">{card.kind === "draft" ? "YOUR NEXT IDEA" : "TRIP ITINERARY"}</div><h3><Link to={path}>{card.title}</Link></h3>
          <div className="trip-date"><Icon name="calendar" size={16} />{dottedDate(isValidISODate(card.start_date || "") ? card.start_date : null)}{isValidISODate(card.end_date || "") && ` — ${dottedDate(card.end_date)}`}</div>
          <p>{card.kind === "draft" ? "Your travel ideas, ready when you are." : detail?.description || "A journey worth looking forward to."}</p>
          <div className="trip-card-stats"><span><Icon name="calendar" size={15} />{detail ? detail.days.length : duration ?? "—"} days</span><span><Icon name="pin" size={15} />{detail ? `${detail.days.reduce((count, day) => count + day.activities.filter(activity => activity.time_use !== "free_window").length, 0)} stops` : card.kind === "draft" ? "0 stops" : "Stops to confirm"}</span><span><Icon name="walk" size={15} />{detail ? `${detail.transfers.length} connections` : card.kind === "draft" ? "0 connections" : "Connections to confirm"}</span></div>
          <div className="trip-card-foot"><Link className="text-link" to={path}>View details <Icon name="arrow" size={17} /></Link>{card.kind === "draft" ? <button type="button" className="btn btn-quiet btn-tiny" onClick={() => void mutate(card, "copy")}><Icon name="copy" size={15} /> Copy</button> : <CopyControls repeatable kind="copied" source={card.id} title={card.title} label="Copy" buttonIcon={<Icon name="copy" size={15} />} buttonClassName="btn btn-quiet btn-tiny" onCopied={copied} />}</div>
        </div>
      </article>;
    })}{!search && page.total > 0 && <Link className="new-trip-card" to="/plan" onClick={() => session.newBrief()}><span className="new-trip-icon"><Icon name="plus" size={32} /></span><strong>Another journey, waiting to be written.</strong><p>Choose a destination and begin a new travel brief.</p><span className="new-trip-arrow">Create a trip <Icon name="arrow" size={16} /></span></Link>}</div>}
    {page && (page.total > 0 || search) && <nav className="pagination" aria-label="Collection pages"><span>{page.total} items · Page {Math.floor(offset / 4) + 1} of {Math.max(1, Math.ceil(page.total / 4))}</span><div className="pagination-controls"><button className="page-btn" aria-label="Previous" disabled={offset === 0} onClick={() => setOffset(n => Math.max(0, n - 4))}><Icon name="back" size={17} /></button>{Array.from({ length: Math.max(1, Math.ceil(page.total / 4)) }, (_, index) => <button className={`page-btn ${offset === index * 4 ? "active" : ""}`} aria-label={`Page ${index + 1}`} aria-current={offset === index * 4 ? "page" : undefined} key={index} onClick={() => setOffset(index * 4)}>{index + 1}</button>)}<button className="page-btn" aria-label="Next" disabled={offset + 4 >= page.total} onClick={() => setOffset(n => n + 4)}><Icon name="arrow" size={17} /></button></div></nav>}
    <dialog id="library-management-dialog" ref={dialog} className="library-dialog" aria-labelledby="library-dialog-title" onCancel={event => { if (busy) event.preventDefault(); else setAction(null); }} onClick={event => {
      if (!busy && isDialogBackdropClick(event)) setAction(null);
    }}>
      {action && <>
        <button type="button" disabled={busy} className="modal-close" aria-label="Close" onClick={() => setAction(null)}><Icon name="close" size={20} /></button>
        <div className="modal-icon"><Icon name={action.kind === "rename" ? "edit" : action.kind === "delete" ? "trash" : "dots"} size={23} /></div><h2 id="library-dialog-title">{action.kind === "menu" ? "Manage your trip" : action.kind === "rename" ? "Give this journey a name." : `Delete this ${action.card.kind === "draft" ? "draft" : "trip"}?`}</h2>
        {action.kind === "menu" ? <>
          <p className="library-managed-title">{action.card.title}</p>
          <div className="menu-stack">
            <button type="button" autoFocus className="menu-option" aria-label={`Rename ${action.card.title}`} disabled={busy} onClick={() => { setTitle(action.card.title); setError(""); setAction({ ...action, kind: "rename" }); }}><Icon name="edit" size={18} /> Rename</button>
            {action.card.kind === "draft" && <button type="button" className="menu-option" aria-label={`Copy ${action.card.title}`} disabled={busy} onClick={() => void mutate(action.card, "copy")}><Icon name="copy" size={18} /> Make a copy</button>}
            {action.card.kind === "saved" && <CopyControls repeatable kind="copied" source={action.card.id} title={action.card.title} label="Make a copy" ariaLabel={`Copy ${action.card.title}`} buttonIcon={<Icon name="copy" size={18} />} buttonClassName="menu-option" onCopied={copied} />}
            <button type="button" className="menu-option danger-text" aria-label={`Delete ${action.card.title}`} disabled={busy} onClick={() => { setError(""); setAction({ ...action, kind: "delete" }); }}><Icon name="trash" size={18} /> Delete</button>
          </div>
          {error && <div role="alert"><p>{error}</p><button type="button" className="btn btn-light" onClick={() => { setAction(null); setReload(n => n + 1); }}>Reload collection</button></div>}
        </> : <form onSubmit={event => { event.preventDefault(); void mutate(action.card, action.kind === "rename" ? "rename" : "delete"); }}>
          {action.kind === "rename" ? <label className="field"><span>Trip name</span><input aria-label={action.card.kind === "draft" ? "New draft title" : "New trip title"} autoFocus required maxLength={120} value={title} onChange={event => setTitle(event.target.value)} /></label> : <p>“{action.card.title}” will be removed from your account. This cannot be undone.</p>}
          {error && <div role="alert"><p>{error}</p><button type="button" className="btn btn-light" onClick={() => { setAction(null); setReload(n => n + 1); }}>Reload collection</button></div>}
          <div className="draft-actions"><button type="button" aria-label="Cancel" disabled={busy} className="btn btn-light" onClick={() => setAction(null)}>{action.kind === "delete" ? "Keep it" : "Cancel"}</button><button aria-label={action.kind === "rename" ? "Save name" : "Delete"} disabled={busy || (action.kind === "rename" && !title.trim())} className={action.kind === "delete" ? "btn btn-danger" : "btn btn-primary"}>{action.kind === "rename" ? "Save name" : "Delete"}</button></div>
        </form>}
      </>}
    </dialog>
  </>;
}
