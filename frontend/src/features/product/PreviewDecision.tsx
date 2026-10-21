import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from './session';
import { submissionGeneration, taskRequest, TaskFailure, type Preview } from './taskClient';

export type PreviewDecision = { id: string; state: 'saved' | 'discarded'; saved_trip_id: string | null; outcome: 'saved' | 'discarded' | 'saved_result_deleted' };

export function DecisionReceipt({ decision }: { decision: Pick<Preview, 'state' | 'saved_trip_id' | 'outcome'> }) {
  return <div className="container preview-state" role="status">
    <strong>{decision.outcome === 'saved_result_deleted' ? 'This saved itinerary was deleted.' : decision.state === 'saved' ? 'Saved to My trips.' : 'Preview discarded.'}</strong>
    {decision.state === 'saved' && decision.saved_trip_id && decision.outcome !== 'saved_result_deleted' && <Link className="btn btn-primary" to={`/trips/${decision.saved_trip_id}`}>View saved itinerary</Link>}
    <Link to="/planning">Return to planning tasks</Link>
  </div>;
}

/** A keyed, mounted preview owns its response; writes never navigate another page. */
export function PreviewDecisionControls({ preview, onDecision }: { preview: Preview; onDecision: (preview: Preview) => void }) {
  const { account, refresh } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [needsCheck, setNeedsCheck] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const mounted = useRef(false);
  const current = useRef(account);
  current.current = account;
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { if (confirm) dialog.current?.showModal(); else dialog.current?.close(); }, [confirm]);

  async function perform(action?: 'save' | 'discard') {
    if (!account || busy) return;
    const expected = account;
    const generation = submissionGeneration(account.id);
    const valid = () => mounted.current && current.current?.id === expected.id && current.current.csrf_token === expected.csrf_token && submissionGeneration(expected.id) === generation;
    setBusy(true); setError('');
    function apply(value: Preview | PreviewDecision) {
      if (!valid()) return;
      if (value.state !== 'pending') {
        setConfirm(false);
        onDecision({ ...preview, ...value, snapshot: null });
      } else {
        setNeedsCheck(false);
        setError('Your preview is still unsaved. Choose Save or Discard to retry explicitly.');
      }
    }
    try {
      const value = await taskRequest<Preview | PreviewDecision>(`/api/previews/${encodeURIComponent(preview.id)}${action ? `/${action}` : ''}`, action ? { csrf: expected.csrf_token, body: action === 'discard' ? { confirmed: true } : {} } : {});
      apply(value);
    } catch (failure) {
      if (!valid()) return;
      if (failure instanceof TaskFailure && failure.status === 401) { void refresh(); return; }
      if (failure instanceof TaskFailure && failure.detail.decision) { apply(failure.detail.decision); return; }
      // A response may be lost after commit. Reconcile with GET; never replay POST.
      try {
        const value = await taskRequest<Preview>(`/api/previews/${encodeURIComponent(preview.id)}`);
        apply(value);
      } catch {
        if (valid()) { setNeedsCheck(true); setError('Could not confirm your decision. Check its status before trying again.'); }
      }
    } finally { if (valid()) setBusy(false); }
  }
  return <>
    <div className="preview-decision-actions">
      {needsCheck ? <button className="btn btn-light" disabled={busy} onClick={() => void perform()}>Check decision status</button> : <>
        <button className="btn btn-primary" disabled={busy} onClick={() => void perform('save')}>{busy ? 'Saving decision…' : 'Save to My trips'}</button>
        <button className="btn btn-light" disabled={busy} onClick={() => setConfirm(true)}>Discard preview</button>
      </>}
      {error && <p role="alert">{error}</p>}
    </div>
    <dialog ref={dialog} className="library-dialog" aria-labelledby="discard-preview-title" onCancel={event => { if (busy) event.preventDefault(); else setConfirm(false); }}>
      <h2 id="discard-preview-title">Discard this preview?</h2><p>This removes the unsaved itinerary permanently. Your submitted travel brief stays available in planning tasks.</p>
      {error && <p role="alert">{error}</p>}
      <div className="draft-actions"><button className="btn btn-light" disabled={busy} onClick={() => setConfirm(false)}>Keep preview</button><button className="btn btn-primary" disabled={busy || needsCheck} onClick={() => void perform('discard')}>Confirm discard</button></div>
    </dialog>
  </>;
}
