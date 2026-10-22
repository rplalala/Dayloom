import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useParams, useNavigate, useLocation } from 'react-router-dom';
import { useSession } from './session';
import { TripDetail } from './detail/TripDetail';
import './tasks.css';
import { TaskContext, useTasks } from './taskContext';
import { taskRequest, TaskFailure, taskActive, type PlanningTask, type Preview } from './taskClient';
import { DecisionReceipt, PreviewDecisionControls } from './PreviewDecision';
import { PlanProgress } from './PlanOutput';
import { Icon } from './Icon';
import { replanBrief } from './replan';

const viewedKey = (owner: string, task: PlanningTask) => `dayloom.task.viewed.${owner}.${task.id}.${task.revision}`;

export function TaskProvider({ children }: { children: ReactNode }) {
  const { account, refresh: refreshSession } = useSession();
  const owner = account?.id;
  const { pathname } = useLocation();
  const [viewed, setViewed] = useState<Set<string>>(() => new Set());
  const [snapshot, setSnapshot] = useState<{ owner?: string; tasks: PlanningTask[]; error: string }>({ tasks: [], error: '' });
  const [notice, setNotice] = useState<{ owner: string; task: PlanningTask } | null>(null);
  const currentOwner = useRef(owner);
  const inFlight = useRef<{ owner: string; promise: Promise<void> } | null>(null);
  const seen = useRef(new Set<string>());
  useEffect(() => { currentOwner.current = owner; }, [owner]);
  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (!owner) return;
    if (inFlight.current?.owner === owner) return inFlight.current.promise;
    const request = (async () => { try {
      const result = await taskRequest<PlanningTask[]>('/api/planning/tasks/recent?limit=10', { signal });
      if (signal?.aborted || currentOwner.current !== owner) return;
      const tasks = Array.isArray(result) ? result : [];
      setSnapshot({ owner, tasks, error: '' });
      for (const task of tasks) {
        if (task.state !== 'completed') continue;
        const key = `dayloom.task.observed.${owner}.${task.id}.${task.revision}`;
        let observed = seen.current.has(key);
        seen.current.add(key);
        try { observed = observed || sessionStorage.getItem(key) === 'yes'; sessionStorage.setItem(key, 'yes'); } catch { /* Memory still deduplicates within the mounted observer. */ }
        if (!observed) { setNotice({ owner, task }); break; }
      }
    } catch (error) {
      if (signal?.aborted || currentOwner.current !== owner) return;
      if (error instanceof TaskFailure && error.status === 401) { void refreshSession(); return; }
      setSnapshot(previous => ({ owner, tasks: previous.owner === owner ? previous.tasks : [], error: 'Could not refresh planning progress. Reconnect to try again.' }));
    } })();
    inFlight.current = { owner, promise: request };
    try { await request; } finally { if (inFlight.current?.promise === request) inFlight.current = null; }
  }, [owner, refreshSession]);
  useEffect(() => {
    if (!owner) return;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const poll = async () => { if (document.visibilityState !== 'hidden') await refresh(controller.signal); if (!controller.signal.aborted) timer = setTimeout(poll, 3000); };
    const reconnect = () => { if (document.visibilityState !== 'hidden') void refresh(controller.signal); };
    void poll();
    window.addEventListener('focus', reconnect); window.addEventListener('online', reconnect); document.addEventListener('visibilitychange', reconnect);
    return () => { controller.abort(); clearTimeout(timer); window.removeEventListener('focus', reconnect); window.removeEventListener('online', reconnect); document.removeEventListener('visibilitychange', reconnect); };
  }, [owner, refresh]);
  const tasks = snapshot.owner === owner && owner ? snapshot.tasks : [];
  const readyTask = tasks.find(task => {
    if (task.state !== 'completed' || !task.preview_id || !owner) return false;
    const key = viewedKey(owner, task);
    if (viewed.has(key)) return false;
    try { return sessionStorage.getItem(key) !== 'yes'; } catch { return true; }
  });
  useEffect(() => {
    if (!owner || snapshot.owner !== owner) return;
    const opened = snapshot.tasks.filter(task => task.state === 'completed' && task.preview_id && pathname === `/previews/${task.preview_id}`);
    if (!opened.length) return;
    const keys = opened.map(task => viewedKey(owner, task));
    setViewed(previous => keys.every(key => previous.has(key)) ? previous : new Set([...previous, ...keys]));
    for (const key of keys) {
      try { sessionStorage.setItem(key, 'yes'); } catch { /* Memory still records views within this mounted session. */ }
    }
    setNotice(previous => previous?.owner === owner && opened.some(task => task.id === previous.task.id) ? null : previous);
  }, [owner, pathname, snapshot]);
  return <TaskContext.Provider value={{ tasks, readyTask, error: snapshot.owner === owner ? snapshot.error : '', refresh }}>
    {notice && notice.owner === owner && owner && <div className="dayloom task-notice-layer"><div className="task-completion-notice" role="status"><span>Your itinerary preview is ready.</span><Link to={`/previews/${notice.task.preview_id}`}>View preview</Link><button type="button" aria-label="Dismiss completion notice" onClick={() => setNotice(null)}>×</button></div></div>}
    {children}
  </TaskContext.Provider>;
}


export function TaskEntry() {
  const { account } = useSession();
  const { tasks, readyTask } = useTasks();
  if (!account) return null;
  const active = tasks.find(taskActive);
  if (!active && !readyTask) return null;
  return <Link className={`task-entry ${active ? 'running' : ''}`} to={active ? '/planning' : `/previews/${readyTask!.preview_id}`} aria-label={active ? 'Planning task running' : 'Itinerary ready'}><span className="task-dot" aria-hidden="true" /><span>{active ? 'Planning your trip' : 'Itinerary ready'}</span></Link>;
}

export function PlanningTasksPage() {
  const { account, status, refresh: refreshSession } = useSession();
  const { tasks, error, refresh } = useTasks();
  const { taskId } = useParams();
  const [selected, setSelected] = useState<{ id?: string; owner?: string; task?: PlanningTask; error?: string }>({});
  useEffect(() => {
    if (!taskId || !account) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function read() {
      try {
        const task = await taskRequest<PlanningTask>(`/api/planning/tasks/${encodeURIComponent(taskId || '')}`, { signal: controller.signal });
        if (!controller.signal.aborted) { setSelected({ id: taskId, owner: account!.id, task }); if (taskActive(task)) timer = setTimeout(read, 3000); }
      } catch (failure) { if (!controller.signal.aborted) { setSelected({ id: taskId, owner: account!.id, error: 'This planning task is unavailable.' }); if (failure instanceof TaskFailure && failure.status === 401) void refreshSession(); } }
    }
    void read();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [account, taskId, refreshSession]);
  if (!account) return <div className="container page"><h1>Your planning tasks are private.</h1><p>{status === 'loading' ? 'Checking your session…' : 'Log in to recover planning progress and previews.'}</p><Link to="/login?return=/planning">Log in</Link></div>;
  const shown = taskId ? selected.id === taskId && selected.owner === account.id && selected.task ? [selected.task] : [] : tasks;
  return <div className="container page task-page"><div className="page-heading"><span className="eyebrow">YOUR JOURNEY IN PROGRESS</span><h1>Planning tasks</h1><p>You can leave this page. Planning continues while you work on another brief.</p></div>
    {(error || selected.error) && <p role="alert">{error || selected.error}</p>}
    <button className="btn btn-light" onClick={() => void refresh()}>Refresh progress</button>
    {!shown.length && <p>{taskId ? 'Loading task…' : 'No recent planning tasks. Start with a travel brief.'}</p>}
    {shown.map(task => <div key={task.id} className="task-progress"><h2>{task.request.destination}</h2><PlanProgress task={task} />{task.preview_id && <Link className="btn btn-primary" to={`/previews/${task.preview_id}`}>Open itinerary preview <Icon name="arrow" size={17} /></Link>}<details className="review-panel"><summary>Submitted brief</summary><p>{task.request.start_date} – {task.request.end_date} · {task.request.traveler_count} travelers</p><p>{task.request.budget.amount} {task.request.budget.currency}</p><p className="literal-preferences">{task.request.additional_preferences}</p></details></div>)}
    <RecoverablePreviews /><Link to="/plan" className="btn btn-light">Continue a brief</Link>
  </div>;
}

export function RecoverablePreviews({ compact = false }: { compact?: boolean }) {
  const { account, refresh: refreshSession } = useSession();
  const [result, setResult] = useState<{ owner?: string; previews: Preview[]; error?: string; more?: boolean }>({ previews: [] });
  const [loadingMore, setLoadingMore] = useState(false);
  const owner = useRef(account?.id);
  useEffect(() => { owner.current = account?.id; }, [account?.id]);
  const { tasks } = useTasks();
  const completedPreviews = tasks.filter(task => task.state === 'completed').map(task => task.preview_id).join(',');
  useEffect(() => {
    if (!account) return;
    const controller = new AbortController();
    taskRequest<Preview[]>('/api/previews?limit=20', { signal: controller.signal }).then(previews => { if (!controller.signal.aborted) setResult({ owner: account.id, previews: Array.isArray(previews) ? previews : [], more: Array.isArray(previews) && previews.length === 20 }); }, error => { if (!controller.signal.aborted) { setResult({ owner: account.id, previews: [], error: 'Could not load recoverable previews.' }); if (error instanceof TaskFailure && error.status === 401) void refreshSession(); } });
    return () => controller.abort();
  }, [account, completedPreviews, refreshSession]);
  if (!account || result.owner !== account.id) return null;
  async function loadMore() {
    if (!account || loadingMore) return;
    const expectedOwner = account.id;
    setLoadingMore(true);
    try { const next = await taskRequest<Preview[]>(`/api/previews?limit=20&offset=${result.previews.length}`);
      if (owner.current === expectedOwner) setResult(previous => ({ owner: expectedOwner, previews: [...previous.previews, ...next].filter((value, index, all) => all.findIndex(item => item.id === value.id) === index), more: next.length === 20 }));
    } catch { if (owner.current === expectedOwner) setResult(previous => ({ ...previous, error: 'Could not load older previews. Try again.' })); }
    finally { setLoadingMore(false); }
  }
  const rows = <>{result.error && <p role="alert">{result.error}</p>}{!result.error && !result.previews.length && <p>No pending previews.</p>}{result.previews.map(preview => <div key={preview.id} className="recovery-row"><div><strong>{preview.title || 'Itinerary preview'}</strong><small>{preview.destination || "A journey to return to"} · Unsaved preview</small></div><div className="recovery-actions"><Link className="btn btn-light btn-small" to={`/previews/${preview.id}`}>View preview</Link>{compact && <PreviewDecisionControls saveLabel="Save" discardLabel="Discard" key={`${account.id}:${account.csrf_token}:${preview.id}`} preview={preview} onDecision={decision => setResult(previous => previous.owner === account.id ? { ...previous, previews: previous.previews.filter(item => item.id !== decision.id) } : previous)} />}</div></div>)}{result.more && <button className="btn btn-light" disabled={loadingMore} onClick={() => void loadMore()}>Load older previews</button>}</>;
  if (compact) return result.previews.length || result.error ? <details className="recovery-panel"><summary><Icon name="layers" size={17} />Unsaved previews <span className="count-badge">{result.previews.length}</span></summary><p className="small-muted">Pick up where you left off. These are kept until you save or discard them.</p>{rows}</details> : null;
  return <section className="recovery-panel"><h2>Recoverable previews</h2><p className="small-muted">Unsaved itineraries stay here until you decide to keep or discard them.</p>{rows}</section>;

}

export function PreviewPage() {
  const { previewId } = useParams();
  const { account, refresh, replaceBrief } = useSession();
  const navigate = useNavigate();
  const [result, setResult] = useState<{ id?: string; owner?: string; preview?: Preview; error?: string }>({});
  useEffect(() => {
    if (!account) return;
    const controller = new AbortController();
    taskRequest<Preview>(`/api/previews/${encodeURIComponent(previewId || '')}`, { signal: controller.signal }).then(preview => { if (!controller.signal.aborted) setResult({ id: previewId, owner: account.id, preview }); }, error => { if (!controller.signal.aborted) { setResult({ id: previewId, owner: account.id, error: 'This preview is unavailable.' }); if (error instanceof TaskFailure && error.status === 401) void refresh(); } });
    return () => controller.abort();
  }, [previewId, account, refresh]);
  if (!account) return <div className="container page"><h1>Log in to recover this preview.</h1><Link to={`/login?return=${encodeURIComponent(`/previews/${previewId}`)}`}>Log in</Link></div>;
  if (result.owner !== account.id || result.id !== previewId) return <p className="container page" role="status">Loading preview…</p>;
  if (result.preview && result.preview.state !== 'pending') return <DecisionReceipt decision={result.preview} />;
  if (result.error || !result.preview?.snapshot) return <div className="container page"><h1>{result.error || 'This preview is unavailable.'}</h1><Link to="/planning">Return to planning tasks</Link></div>;
  return <TripDetail mode="preview" detail={result.preview.snapshot} mediaEndpoint={`/api/previews/${previewId}/media`} onReplan={() => { replaceBrief(replanBrief(result.preview!.snapshot!.request), "replan"); navigate("/plan"); }} actions={<PreviewDecisionControls saveClassName="btn btn-glass" key={`${account.id}:${account.csrf_token}:${previewId}`} preview={result.preview} onDecision={preview => setResult({ id: previewId, owner: account.id, preview })} />} />;
}
