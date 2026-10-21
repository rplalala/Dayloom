import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { draftRequest, DraftFailure, type Draft } from "./drafts";
import { restoreBrief } from "./editor";
import { useSession } from "./session";
import "./library.css";

export function DraftControls({ onLoading }: { onLoading: (loading: boolean) => void }) {
  const session = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const navigation = useRef(location.key);
  navigation.current = location.key;
  const mounted = useRef(true);
  const [params, setParams] = useSearchParams();
  const id = params.get("draft") || session.draftRef?.id || null;
  const title = session.draftTitle;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [saved, setSaved] = useState<{ editor: string; title: string } | null>(null);
  const current = useRef(session);
  current.current = session;
  const owner = session.account?.id;

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

  return <section className="draft-toolbar" aria-label="Planning draft">
    <label className="field"><span>Draft title</span><input value={title} maxLength={120} placeholder="A new travel idea" onChange={event => session.setDraftTitle(event.target.value)} /></label>
    <div className="draft-actions"><button type="button" className="btn btn-outline" disabled={busy || (!!id && session.draftRef?.id !== id)} onClick={() => void save(false)}>Save draft</button>
      {id && <button type="button" className="btn btn-outline" disabled={busy || session.draftRef?.id !== id} onClick={() => void save(true)}>Save as new draft</button>}
      {conflict && <button type="button" className="btn btn-outline" disabled={busy} onClick={() => {
        if (window.confirm("Reload the saved draft? This replaces your local edits.")) {
          if (id) setParams({ draft: id }, { replace: true });
          session.setDraftRef(null); setConflict(false);
        }
      }}>Reload saved draft</button>}
    </div>
    {error && <p role="alert" className="form-error">{error}</p>}
    {saved && <p role="status">{saved.editor === JSON.stringify(session.brief) && saved.title === title ? "Draft saved." : "You have unsaved changes."}</p>}
    <p className="subtle-help">Keep an unfinished idea. Saving a draft does not generate an itinerary.</p>
  </section>;
}
