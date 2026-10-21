import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSession } from "./session";
import { DraftFailure, draftRequest, type LibraryCard, type LibraryPageResult } from "./drafts";
import "./library.css";

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
  const [action, setAction] = useState<{ kind: "rename" | "delete"; card: LibraryCard } | null>(null);
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
  useEffect(() => { if (action) dialog.current?.showModal(); else dialog.current?.close(); }, [action]);

  async function mutate(card: LibraryCard, kind: "copy" | "rename" | "delete") {
    const account = session.account;
    if (!account || card.kind !== "draft") return;
    setBusy(true); setError("");
    try {
      await draftRequest(`/api/drafts/${card.id}${kind === "copy" ? "/copy" : kind === "delete" ? `?revision=${card.revision}` : ""}`,
        kind === "copy" ? "POST" : kind === "delete" ? "DELETE" : "PATCH", account.csrf_token,
        kind === "delete" ? undefined : { revision: card.revision, ...(kind === "rename" && { title }) });
      if (current.current.account?.id !== account.id) return;
      setAction(null); setOffset(0); setReload(n => n + 1);
    } catch (failure) {
      if (current.current.account?.id !== account.id) return;
      setError(failure instanceof Error ? failure.message : "Unable to update this draft.");
      if (failure instanceof DraftFailure && failure.status === 401) await session.refresh();
    } finally { setBusy(false); }
  }

  return <>
    <div className="library-tools">
      <form role="search" onSubmit={event => { event.preventDefault(); setSearch(query); setOffset(0); }}><input aria-label="Search trips" value={query} maxLength={100} placeholder="Search title or destination" onChange={event => setQuery(event.target.value)} /><button className="btn btn-outline">Search</button></form>
      <label>Sort <select aria-label="Sort trips" value={sort} onChange={event => { setSort(event.target.value); setOffset(0); }}><option value="newest">Newest updated</option><option value="oldest">Oldest updated</option><option value="name">Name</option></select></label>
      <button className="btn btn-primary" onClick={() => { session.newBrief(); navigate("/plan"); }}>Plan a trip →</button>
    </div>
    {error && !action && <div role="alert"><p>{error}</p><button className="btn btn-outline" onClick={() => setReload(n => n + 1)}>Retry collection</button></div>}
    {!page && !error && <p role="status">Loading your collection…</p>}
    {page && page.total === 0 && <section className="flow-card result-placeholder"><h2>{search ? "No matching journeys." : "Your next journey starts here."}</h2><p>{search ? "Try another title or destination." : "No trips yet. Start with an idea and make it yours."}</p></section>}
    {page && <div className="trip-grid">{page.items.map(card => <article className="trip-card" key={`${card.kind}:${card.id}`}>
      <Link className="draft-card-cover" to={card.kind === "draft" ? `/plan?draft=${card.id}` : `/trips/${card.id}`} aria-label={`${card.kind === "draft" ? "Continue" : "View"} ${card.title}`}>{card.kind === "draft" ? "✎" : "◇"}</Link>
      <div className="trip-card-body"><span className="eyebrow">{card.kind === "draft" ? "PLANNING DRAFT" : "SAVED ITINERARY"}</span><h2>{card.title}</h2><p>{card.destination || "Destination to decide"}</p><p>{card.start_date || "Dates to decide"}{card.end_date && ` – ${card.end_date}`}</p><Link className="text-link" to={card.kind === "draft" ? `/plan?draft=${card.id}` : `/trips/${card.id}`}>{card.kind === "draft" ? "Continue planning →" : "View details →"}</Link>
        {card.kind === "draft" && <div className="library-actions"><button aria-label={`Rename ${card.title}`} disabled={busy} onClick={() => { setTitle(card.title); setError(""); setAction({ kind: "rename", card }); }}>Rename</button><button aria-label={`Copy ${card.title}`} disabled={busy} onClick={() => void mutate(card, "copy")}>Copy</button><button aria-label={`Delete ${card.title}`} disabled={busy} onClick={() => { setError(""); setAction({ kind: "delete", card }); }}>Delete</button></div>}
      </div></article>)}</div>}
    {page && page.total > 12 && <nav className="library-pagination" aria-label="Collection pages"><button className="btn btn-outline" disabled={offset === 0} onClick={() => setOffset(n => Math.max(0, n - 12))}>Previous</button><span>{offset + 1}–{Math.min(offset + 12, page.total)} of {page.total}</span><button className="btn btn-outline" disabled={offset + 12 >= page.total} onClick={() => setOffset(n => n + 12)}>Next</button></nav>}
    <dialog ref={dialog} className="library-dialog" aria-labelledby="library-dialog-title" onCancel={event => { if (busy) event.preventDefault(); else setAction(null); }}>
      {action && <form onSubmit={event => { event.preventDefault(); void mutate(action.card, action.kind); }}>
        <h2 id="library-dialog-title">{action.kind === "rename" ? "Rename draft" : "Delete draft?"}</h2>
        {action.kind === "rename" ? <label className="field"><span>New draft title</span><input autoFocus required maxLength={120} value={title} onChange={event => setTitle(event.target.value)} /></label> : <p>Delete “{action.card.title}”? This removes this draft permanently. Independent copies stay in your collection.</p>}
        {error && <p role="alert">{error}</p>}
        <div className="draft-actions"><button type="button" disabled={busy} className="btn btn-outline" onClick={() => setAction(null)}>Cancel</button><button disabled={busy || (action.kind === "rename" && !title.trim())} className="btn btn-primary">{action.kind === "rename" ? "Save title" : "Delete draft"}</button></div>
      </form>}
    </dialog>
  </>;
}
