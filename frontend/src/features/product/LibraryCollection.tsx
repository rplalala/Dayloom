import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSession } from "./session";
import { DraftFailure, draftRequest, type LibraryCard, type LibraryPageResult } from "./drafts";
import "./library.css";
import { CopyControls } from './CopyControls';

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
  const [action, setAction] = useState<{ kind: "menu" | "rename" | "delete" | "copy"; card: LibraryCard } | null>(null);
  const [title, setTitle] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const owner = session.account!.id;
  const current = useRef(session);
  current.current = session;
  useEffect(() => {
    const controller = new AbortController();
    setPage(null); setError("");
    draftRequest<LibraryPageResult>(`/api/library?q=${encodeURIComponent(search)}&sort=${sort}&limit=12&offset=${offset}`, "GET", undefined, undefined, controller.signal)
      .then(value => { if (!controller.signal.aborted) setPage(value); })
      .catch(failure => {
        if (controller.signal.aborted) return;
        setError(failure instanceof Error ? failure.message : "Collection unavailable.");
        if (failure instanceof DraftFailure && failure.status === 401) void current.current.refresh();
      });
    return () => controller.abort();
  }, [owner, search, sort, offset, reload]);
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

  return <>
    <section className="library-intro">
      <div className="library-count"><span className="eyebrow">YOUR COLLECTION</span><strong>{page ? String(page.total).padStart(2, "0") : "—"}</strong><span>{search ? "matching trips and drafts" : "saved trips and drafts"}</span></div>
      <div className="library-copy"><h2>Good places.<br /><em>Worth keeping.</em></h2><p>Plans to look forward to. Memories to return to.</p></div>
      <button className="btn btn-primary btn-large" onClick={() => { session.newBrief(); navigate("/plan"); }}>Plan a trip →</button>
    </section>
    <div className="library-tools trips-toolbar">
      <form className="search-box" role="search" onSubmit={event => { event.preventDefault(); setSearch(query); setOffset(0); }}><input aria-label="Search trips" value={query} maxLength={100} placeholder="Search title or destination" onChange={event => setQuery(event.target.value)} /><button className="library-search-submit" type="submit">Search</button></form>
      <label className="sort-box"><span aria-hidden="true">↕</span><select aria-label="Sort trips" value={sort} onChange={event => { setSort(event.target.value); setOffset(0); }}><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="name">Name</option></select></label>
    </div>
    {error && !action && <div role="alert"><p>{error}</p><button className="btn btn-light" onClick={() => setReload(n => n + 1)}>Retry collection</button></div>}
    {!page && !error && <p role="status">Loading your collection…</p>}
    {page && page.total === 0 && <section className="flow-card result-placeholder"><h2>{search ? "No matching journeys." : "Your next journey starts here."}</h2><p>{search ? "Try another title or destination." : "No trips yet. Start with an idea and make it yours."}</p></section>}
    {page && <div className="trip-grid">{page.items.map(card => <article className="trip-card" key={`${card.kind}:${card.id}`}>
      <div className="library-card-cover">
        <Link className="draft-card-cover" to={card.kind === "draft" ? `/plan?draft=${card.id}` : `/trips/${card.id}`} aria-label={`${card.kind === "draft" ? "Continue" : "View"} ${card.title}`}>{card.kind === "draft" ? "✎" : "◇"}</Link>
        <button type="button" className="card-menu-trigger" aria-label={`Manage ${card.title}`} aria-haspopup="dialog" aria-controls="library-management-dialog" aria-expanded={Boolean(action && action.card.id === card.id && action.card.kind === card.kind)} disabled={busy} onClick={() => { setError(""); setAction({ kind: "menu", card }); }}><span aria-hidden="true">•••</span></button>
      </div>
      <div className="trip-card-body"><span className="eyebrow">{card.kind === "draft" ? "PLANNING DRAFT" : "SAVED ITINERARY"}</span><h2>{card.title}</h2><p>{card.destination || "Destination to decide"}</p><p>{card.start_date || "Dates to decide"}{card.end_date && ` – ${card.end_date}`}</p><Link className="text-link" to={card.kind === "draft" ? `/plan?draft=${card.id}` : `/trips/${card.id}`}>{card.kind === "draft" ? "Continue planning →" : "View details →"}</Link>
        {card.kind === "saved" && <button type="button" className="btn btn-quiet btn-tiny" onClick={() => setAction({ kind: "copy", card })}>Copy</button>}
      </div></article>)}</div>}
    {page && page.total > 12 && <nav className="library-pagination" aria-label="Collection pages"><button className="btn btn-light" disabled={offset === 0} onClick={() => setOffset(n => Math.max(0, n - 12))}>Previous</button><span>{offset + 1}–{Math.min(offset + 12, page.total)} of {page.total}</span><button className="btn btn-light" disabled={offset + 12 >= page.total} onClick={() => setOffset(n => n + 12)}>Next</button></nav>}
    <dialog id="library-management-dialog" ref={dialog} className="library-dialog" aria-labelledby="library-dialog-title" onCancel={event => { if (busy) event.preventDefault(); else setAction(null); }} onClick={event => {
      if (busy || event.target !== event.currentTarget) return;
      const bounds = event.currentTarget.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) setAction(null);
    }}>
      {action && <>
        <h2 id="library-dialog-title">{action.kind === "copy" ? 'Keep an independent copy' : action.kind === "menu" ? `Manage your ${action.card.kind === "draft" ? "draft" : "trip"}` : action.kind === "rename" ? `Rename ${action.card.kind === "draft" ? "draft" : "trip"}` : `Delete ${action.card.kind === "draft" ? "draft" : "trip"}?`}</h2>
        {action.kind === "menu" ? <>
          <p className="library-managed-title">{action.card.title}</p>
          <div className="menu-stack">
            <button type="button" autoFocus className="menu-option" aria-label={`Rename ${action.card.title}`} disabled={busy} onClick={() => { setTitle(action.card.title); setError(""); setAction({ ...action, kind: "rename" }); }}>Rename</button>
            {action.card.kind === "draft" && <button type="button" className="menu-option" aria-label={`Copy ${action.card.title}`} disabled={busy} onClick={() => void mutate(action.card, "copy")}>Make a copy</button>}
            {action.card.kind === "saved" && <button type="button" className="menu-option" aria-label={`Copy ${action.card.title}`} onClick={() => setAction({ ...action, kind: "copy" })}>Make a copy</button>}
            <button type="button" className="menu-option danger-text" aria-label={`Delete ${action.card.title}`} disabled={busy} onClick={() => { setError(""); setAction({ ...action, kind: "delete" }); }}>Delete</button>
          </div>
          {error && <div role="alert"><p>{error}</p><button type="button" className="btn btn-light" onClick={() => { setAction(null); setReload(n => n + 1); }}>Reload collection</button></div>}
          <div className="draft-actions"><button type="button" disabled={busy} className="btn btn-light" onClick={() => setAction(null)}>Close</button></div>
        </> : action.kind === "copy" ? <><p>{action.card.title}</p><CopyControls kind="copied" source={action.card.id} title={action.card.title} onCopied={() => { setOffset(0); setReload(n => n + 1); }} /><button type="button" className="btn btn-light" onClick={() => setAction(null)}>Close</button></> : <form onSubmit={event => { event.preventDefault(); void mutate(action.card, action.kind === "rename" ? "rename" : "delete"); }}>
          {action.kind === "rename" ? <label className="field"><span>{action.card.kind === "draft" ? "New draft title" : "New trip title"}</span><input autoFocus required maxLength={120} value={title} onChange={event => setTitle(event.target.value)} /></label> : <p>Delete “{action.card.title}”? This removes this {action.card.kind === "draft" ? "draft" : "trip"} permanently. Independent copies stay in your collection.</p>}
          {error && <div role="alert"><p>{error}</p><button type="button" className="btn btn-light" onClick={() => { setAction(null); setReload(n => n + 1); }}>Reload collection</button></div>}
          <div className="draft-actions"><button type="button" disabled={busy} className="btn btn-light" onClick={() => setAction(null)}>Cancel</button><button disabled={busy || (action.kind === "rename" && !title.trim())} className={action.kind === "delete" ? "btn btn-danger" : "btn btn-primary"}>{action.kind === "rename" ? "Save title" : `Delete ${action.card.kind === "draft" ? "draft" : "trip"}`}</button></div>
        </form>}
      </>}
    </dialog>
  </>;
}
