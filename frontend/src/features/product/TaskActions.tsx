import { isDialogBackdropClick } from '../../shared/dialog';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { createBrief, restoreBrief } from './editor';
import { draftRequest, DraftFailure } from './drafts';
import { useSession } from './session';
import { taskActive, TaskFailure, taskRequest, type PlanningTask } from './taskClient';
import { useTasks } from './taskContext';
import { Icon } from './Icon';

function submittedBrief(task: PlanningTask) {
  if (task.editor_snapshot) return restoreBrief(task.editor_snapshot);
  // Legacy tasks retain only known submitted fields. Profile defaults never enter recovery.
  return { ...createBrief(), destination: task.request.destination,
    start_date: task.request.start_date, end_date: task.request.end_date,
    travelers: String(task.request.traveler_count), budget: String(task.request.budget.amount),
    currency: task.request.budget.currency, preferences: task.request.additional_preferences || '' };
}

export function TaskActions({ task, onUpdate }: { task: PlanningTask; onUpdate: (task: PlanningTask) => void }) {
  const session = useSession();
  const { refresh } = useTasks();
  const navigate = useNavigate();
  const location = useLocation();
  const navigation = useRef(location.key);
  navigation.current = location.key;
  const operation = useRef(0);
  const current = useRef(session);
  current.current = session;
  const mounted = useRef(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    operation.current++;
    setBusy(false); setError(''); setConfirm(false);
  }, [location.key, task.id, session.account?.id, session.account?.csrf_token, session.status, session.brief, session.briefOrigin, session.draftRef, session.draftTitle, session.actionId]);
  useEffect(() => { if (confirm) dialog.current?.showModal(); else dialog.current?.close(); }, [confirm]);

  function revise() {
    current.current.replaceBrief(submittedBrief(task), 'restored');
    setConfirm(false);
    navigate('/plan');
  }
  async function perform(kind: 'stop' | 'save') {
    const account = session.account;
    if (!account || busy) return;
    const sequence = ++operation.current;
    const navigationAtStart = location.key;
    const stillCurrent = () => mounted.current && operation.current === sequence && navigation.current === navigationAtStart &&
      current.current.status === 'authenticated' && current.current.account?.id === account.id && current.current.account.csrf_token === account.csrf_token &&
      current.current.brief === session.brief && current.current.briefOrigin === session.briefOrigin && current.current.draftRef === session.draftRef &&
      current.current.draftTitle === session.draftTitle && current.current.actionId === session.actionId;
    setBusy(true); setError('');
    try {
      if (kind === 'stop') {
        const stopped = await taskRequest<PlanningTask>(`/api/planning/tasks/${encodeURIComponent(task.id)}/stop`, { csrf: account.csrf_token, body: {} });
        if (!stillCurrent()) return;
        onUpdate(stopped);
        await refresh();
      } else {
        await draftRequest('/api/drafts', 'POST', account.csrf_token, { title: (session.draftTitle.trim() || `${session.brief.destination || 'Travel'} brief`).slice(0, 120), editor: session.brief });
        if (!stillCurrent()) return;
        revise();
      }
    } catch (failure) {
      if (!stillCurrent()) return;
      if ((failure instanceof TaskFailure || failure instanceof DraftFailure) && failure.status === 401) void current.current.refresh();
      setError(kind === 'stop' ? 'Could not confirm Stop. Refresh progress to check the task before trying again.' : 'Could not save your current brief. It is still here; try again when connected.');
    } finally { if (stillCurrent()) setBusy(false); }
  }
  return <div className="task-actions">
    {taskActive(task) ? <><p>Stopping closes this task's connections. External work already sent may still finish or be billed.</p><button type="button" className="btn btn-quiet" disabled={busy || task.state === 'stopping'} onClick={() => void perform('stop')}>{task.state === 'stopping' ? 'Stopping planning…' : 'Stop planning'}</button></> : task.state !== 'completed' && <button type="button" className="btn btn-light" onClick={() => {
      const restored = submittedBrief(task);
      const blank = createBrief();
      if (JSON.stringify(session.brief) !== JSON.stringify(blank) && JSON.stringify(session.brief) !== JSON.stringify(restored)) setConfirm(true);
      else revise();
    }}>Revise submitted brief</button>}
    {error && !confirm && <p role="alert">{error}</p>}
    <dialog ref={dialog} className="library-dialog modal-card" aria-labelledby={`revise-${task.id}`} onCancel={event => { if (busy) event.preventDefault(); else setConfirm(false); }} onClick={event => {
      if (!busy && isDialogBackdropClick(event)) setConfirm(false);
    }}>
      <button type="button" className="modal-close" aria-label="Close" disabled={busy} onClick={() => setConfirm(false)}><Icon name="close" size={20} /></button><div className="modal-icon"><Icon name="edit" size={23} /></div><h2 id={`revise-${task.id}`}>Keep your current brief?</h2><p>Opening this submitted brief replaces the editor. Save your current brief as a draft first, or choose to replace it.</p>
      <div className="modal-actions"><button type="button" className="btn btn-primary" disabled={busy} onClick={() => void perform('save')}>Save current brief and revise</button><button type="button" className="btn btn-light" disabled={busy} onClick={revise}>Replace current brief</button><button type="button" className="btn btn-quiet" disabled={busy} onClick={() => setConfirm(false)}>Keep current brief</button></div>
      {error && <p role="alert">{error}</p>}
    </dialog>
  </div>;
}

export function TaskOutcome({ task }: { task: PlanningTask }) {
  if (!task.outcome) return null;
  const title = task.state === 'needs_clarification' ? 'A few details need your attention' : task.state === 'safety_blocked' ? 'Travel planning paused' : task.state === 'provider_blocked' ? 'Please revise your preferences' : task.state === 'cancelled' ? 'Planning stopped' : task.outcome.code === 'planning_interrupted' ? 'Planning was interrupted' : 'Planning could not finish';
  return <section className="task-outcome" aria-label="Planning outcome"><h3>{title}</h3><p>{task.outcome.message}</p><p>{task.outcome.action}</p>
    {task.state === 'needs_clarification' && task.outcome.issues?.issues?.map((issue, index) => <div key={index} className="task-clarification">{issue.source_refs.map((source, sourceIndex) => <blockquote key={sourceIndex}>{source.quote}</blockquote>)}{issue.quote_status === 'unavailable' && <p>Original quote unavailable.</p>}{issue.related_field && <p>Current {issue.related_field}: {String(issue.current_value ?? '')}</p>}<p>{issue.reason}</p><p>{issue.action}</p></div>)}
    <p>Revising opens editable inputs. Planning starts only when you choose Generate itinerary again.</p>
  </section>;
}
