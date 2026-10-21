import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSession } from './session';
import { submissionGeneration, taskRequest, TaskFailure } from './taskClient';
import type { PreviewDecision } from './PreviewDecision';

type Kind = 'copied' | 'example';
type Intent = { owner: string | null; generation: string; kind: Kind; source: string; key: string | null; uncertain: boolean };
const storageKey = 'dayloom.copy.intent.v1';

function restored(owner: string | null, kind: Kind, source: string): Intent {
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
    if (saved && saved.kind === kind && saved.source === source && (saved.owner === null || saved.owner === owner) && (!saved.owner || saved.generation === submissionGeneration(saved.owner)) && (saved.key === null || typeof saved.key === 'string')) return { ...saved, uncertain: Boolean(saved.key) };
  } catch { /* The explicit action also works without optional storage. */ }
  return { owner, generation: owner ? submissionGeneration(owner) : '', kind, source, key: null, uncertain: false };
}

export function CopyControls({ kind, source, label, onCopied }: { kind: Kind; source: string; label?: string; onCopied?: () => void }) {
  const session = useSession();
  return <CopyAction key={`${session.account?.id || session.status}:${kind}:${source}`} kind={kind} source={source} label={label} onCopied={onCopied} />;
}

function CopyAction({ kind, source, label = kind === 'example' ? 'Keep a copy' : 'Make a copy', onCopied }: { kind: Kind; source: string; label?: string; onCopied?: () => void }) {
  const session = useSession();
  const navigate = useNavigate();
  const [intent, setIntent] = useState(() => restored(session.account?.id || null, kind, source));
  const [decision, setDecision] = useState<PreviewDecision | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [locked, setLocked] = useState(false);
  const mounted = useRef(false);
  const current = useRef(session);
  current.current = session;
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const returnPath = kind === 'example' ? `/examples/${source}` : `/trips/${source}`;
  const loginPath = `/login?return=${encodeURIComponent(returnPath)}`;

  function remember(next: Intent) {
    setIntent(next);
    try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch { /* Optional tab recovery. */ }
  }
  async function perform(check = false) {
    if (busy || session.status === 'loading') return;
    const account = session.account;
    if (!account) { remember({ ...intent, owner: null, generation: '' }); navigate(loginPath); return; }
    const generation = submissionGeneration(account.id);
    const key = intent.key || crypto.randomUUID();
    const next = { ...intent, owner: account.id, generation, key, uncertain: true };
    remember(next); setBusy(true); setError('');
    const valid = () => mounted.current && current.current.account?.id === account.id && current.current.account.csrf_token === account.csrf_token && submissionGeneration(account.id) === generation;
    try {
      const value = await taskRequest<PreviewDecision>(check ? `/api/copies/${kind}/${encodeURIComponent(key)}` : '/api/copies', check ? {} : { csrf: account.csrf_token, body: { source_kind: kind, source_id: source, operation_key: key } });
      if (!valid()) return;
      setDecision(value);
      if (value.outcome === 'saved') onCopied?.();
    } catch (failure) {
      if (!valid()) return;
      if (failure instanceof TaskFailure && failure.status === 401) { setLocked(true); void session.refresh(); return; }
      if (check && failure instanceof TaskFailure && failure.status === 404) {
        remember({ ...next, uncertain: false }); setError('No copy is recorded yet. You may explicitly retry with the same key.');
      } else if (!check && failure instanceof TaskFailure && failure.status === 404) {
        remember({ ...next, key: null, uncertain: false }); setError('The source itinerary is no longer available.');
      } else {
        setError('Copy could not be confirmed. Check its status before explicitly retrying.');
      }
    } finally { if (valid()) setBusy(false); }
  }
  if (session.status === 'expired' || locked) return <div className="copy-controls"><p>Your copy action is private. Log in to the same account to check its status.</p><Link className="btn btn-light" to={loginPath}>Log in</Link></div>;
  return <div className="copy-controls">
    {decision ? <div role="status"><p>{decision.outcome === 'saved_result_deleted' ? 'This saved copy was deleted. It will not be recreated.' : 'An independent copy was added to My trips.'}</p>
      {decision.outcome === 'saved' && <Link className="btn btn-light" to={`/trips/${decision.saved_trip_id}`}>View saved copy</Link>}
      <button type="button" className="btn btn-light" onClick={() => { remember({ owner: session.account?.id || null, generation: session.account ? submissionGeneration(session.account.id) : '', kind, source, key: null, uncertain: false }); setDecision(null); setError(''); }}>Start another copy</button>
    </div> : <button type="button" className="btn btn-light" disabled={busy || session.status === 'loading'} onClick={() => void perform(intent.uncertain)}>{busy ? 'Checking copy…' : intent.uncertain ? 'Check copy status' : intent.key ? 'Retry copy with same key' : label}</button>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
