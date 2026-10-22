import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { draftRequest, DraftFailure, type Draft } from "./drafts";
import { composedPreferences, restoreBrief } from "./editor";
import { useSession } from "./session";
import { Icon } from "./Icon";
import { dottedDate } from "./detail/display";
import "./library.css";

export type DraftActionsHandle = { save: () => Promise<void> };

export function DraftControls({ onLoading, actionsRef }: { onLoading: (loading: boolean) => void; actionsRef?: Ref<DraftActionsHandle> }) {
  const session = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const navigation = useRef(location.key);
  navigation.current = location.key;
  const mounted = useRef(true);
  const [params, setParams] = useSearchParams();
  const id = params.get("draft") || session.draftRef?.id || null;
  const title = session.draftTitle || `${session.brief.destination.trim() || "A new travel idea"} · Planning draft`;
  const acceptedTitle = session.draftRef?.title || `${session.brief.destination.trim() || "A new travel idea"} · Planning draft`;
  const recoveredTitle = session.draftTitle && session.draftTitle !== acceptedTitle ? session.draftTitle : null;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [saved, setSaved] = useState<{ editor: string; title: string } | null>(null);
  const [review, setReview] = useState(false);
  const reviewDialog = useRef<HTMLDialogElement>(null);
  const current = useRef(session);
  current.current = session;
  const owner = session.account?.id;
  useImperativeHandle(actionsRef, () => ({ save: () => save(false) }));
  useEffect(() => {
    const dialog = reviewDialog.current;
    if (!review || !dialog) return;
    const opener = document.activeElement;
    dialog.showModal();
    return () => {
      if (dialog.open) dialog.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [review]);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  useEffect(() => { setBusy(false); }, [location.key]);

  useEffect(() => {
    if (!owner || session.status !== "authenticated") { onLoading(false); return; }
    if (!id) { onLoading(false); return; }
    // Recovery carries the revision with the local editor, including after expiry.
    if (session.draftRef?.id === id) { onLoading(false); return; }
    const controller = new AbortController();
    onLoading(true);
    draftRequest<Draft>(`/api/drafts/${encodeURIComponent(id)}`, "GET", undefined, undefined, controller.signal)
      .then(draft => {
        if (controller.signal.aborted || current.current.account?.id !== owner) return;
        current.current.replaceBrief(restoreBrief(draft.editor), "draft");
        current.current.setDraftRef({ id: draft.id, title: draft.title, revision: draft.revision });
        current.current.setDraftTitle(draft.title); setError(""); setConflict(false); setSaved(null); onLoading(false);
      }).catch(failure => {
        if (controller.signal.aborted) return;
        setError(failure instanceof Error ? failure.message : "Draft unavailable.");
        if (failure instanceof DraftFailure && failure.status === 401) void current.current.refresh();
        // Keep the editor disabled until the requested snapshot is known.
      });
    return () => controller.abort();
  }, [id, owner, session.status, session.draftRef, onLoading]);

  async function save(asNew: boolean) {
    setError(""); setSaved(null);
    if (!session.account) { navigate("/login?return=/plan"); return; }
    if (!title.trim()) { setError("Enter a draft title."); return; }
    // Even an untouched blank brief becomes explicit editor work at Save.
    session.editBrief(session.brief);
    const ownerAtStart = session.account.id;
    const csrfAtStart = session.account.csrf_token;
    const navigationAtStart = location.key;
    const stillCurrent = () => mounted.current && navigation.current === navigationAtStart &&
      current.current.account?.id === ownerAtStart && current.current.account.csrf_token === csrfAtStart;
    const existing = !asNew && session.draftRef?.id === id ? session.draftRef : null;
    setBusy(true);
    try {
      const draft = await draftRequest<Draft>(existing ? `/api/drafts/${existing.id}` : "/api/drafts", existing ? "PUT" : "POST", session.account.csrf_token,
        { title, editor: session.brief, ...(existing && { revision: existing.revision }) });
      if (!stillCurrent()) return;
      // Saving never replaces the editor: typing during a request remains local.
      current.current.setDraftRef({ id: draft.id, title: draft.title, revision: draft.revision });
      setParams({ draft: draft.id }, { replace: true });
      setConflict(false); setSaved({ editor: JSON.stringify(session.brief), title });
    } catch (failure) {
      if (!stillCurrent()) return;
      setError(failure instanceof Error ? failure.message : "Unable to save draft.");
      if (failure instanceof DraftFailure) {
        setConflict(failure.status === 409);
        if (failure.status === 401) await session.refresh();
      }
    } finally { if (stillCurrent()) setBusy(false); }
  }

  return <section className="draft-controls" aria-label="Planning draft">
    <div className="quiet-links draft-actions">
      <button type="button" className="inline-action" aria-label="Save draft" disabled={busy || (!!id && session.draftRef?.id !== id)} onClick={() => void save(false)}>{id ? "Update draft" : "Save travel brief"}</button>
      {id && <button type="button" className="inline-action" aria-label="Save as new draft" disabled={busy || session.draftRef?.id !== id} onClick={() => void save(true)}>Save as a new draft</button>}
      {conflict && <button type="button" className="inline-action" disabled={busy} onClick={() => {
        if (window.confirm("Reload the saved draft? This replaces your local edits.")) {
          if (id) setParams({ draft: id }, { replace: true });
          session.setDraftRef(null); setConflict(false);
        }
      }}>Reload saved draft</button>}
      <button type="button" className="inline-action" onClick={() => setReview(true)}>Review travel brief</button>
    </div>
    {error && <p role="alert" className="form-error">{error}</p>}
    {saved && <p className="subtle-help" role="status">{saved.editor === JSON.stringify(session.brief) && saved.title === title ? "Draft saved." : "You have unsaved changes."}</p>}
    {review && <dialog className="modal-card library-dialog" ref={reviewDialog} aria-labelledby="travel-brief-title" onCancel={event => { event.preventDefault(); setReview(false); }} onClick={event => {
      const box = event.currentTarget.getBoundingClientRect();
      if (event.target === event.currentTarget && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) setReview(false);
    }}>
      <button type="button" className="modal-close" aria-label="Close dialog" onClick={() => setReview(false)}><Icon name="close" size={21} /></button>
      <div className="modal-icon"><Icon name="sliders" size={23} /></div>
      <h2 id="travel-brief-title">Your travel brief</h2><p>Everything you have chosen, in one place.</p>
      <div className="detail-note"><strong>Destination &amp; dates</strong><span>{session.brief.destination || "Not entered"}<br />{dottedDate(session.brief.start_date)} — {dottedDate(session.brief.end_date)}{recoveredTitle && <><br /><span>Recovered draft name: {recoveredTitle}</span></>}</span></div>
      <div className="detail-note"><strong>Travelers &amp; whole-trip budget</strong><span>{session.brief.travelers || "Not entered"} travelers · {session.brief.budget ? `${session.brief.currency || "Currency not set"} ${session.brief.budget}` : "Budget not entered"}</span></div>
      <div className="detail-note"><strong>Preferences &amp; requirements</strong><span style={{ whiteSpace: "pre-wrap" }}>{composedPreferences(session.brief) || "No additional preferences."}</span></div>
      <div className="modal-actions"><button type="button" className="btn btn-primary" onClick={() => setReview(false)}>Keep editing</button></div>
    </dialog>}
  </section>;
}
