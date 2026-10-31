import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSession } from './session';
import { submissionGeneration, taskRequest, TaskFailure } from './taskClient';
import type { PreviewDecision } from './PreviewDecision';
import { rememberCopyIntent, restoreCopyIntent, type CopyIntent, type CopyKind } from './copyIntents';

type Props = { kind: CopyKind; source: string; title?: string; label?: string; statusOnly?: boolean; onCopied?: (decision: PreviewDecision) => void; buttonClassName?: string; repeatable?: boolean; ariaLabel?: string; buttonIcon?: ReactNode };

export function CopyControls(props: Props) {
  const session = useSession();
  return <CopyAction key={`${session.account?.id || session.status}:${props.kind}:${props.source}`} {...props} />;
}

function CopyAction({ kind, source, title, label = kind === 'example' ? 'Keep a copy' : 'Make a copy', statusOnly = false, onCopied, buttonClassName = "btn btn-light", repeatable = false, ariaLabel, buttonIcon }: Props) {
  const session = useSession();
  const navigate = useNavigate();
  const [intent, setIntent] = useState(() => {
    const restored = restoreCopyIntent(session.account?.id || null, kind, source, title);
    return repeatable && restored.resolved ? { ...restored, key: null, uncertain: false, resolved: false } : restored;
  });
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

  function remember(next: CopyIntent) {
    setIntent(next);
    rememberCopyIntent(next);
  }
  async function perform(check = false) {
    if (busy || session.status === 'loading') return;
    if (statusOnly && !intent.key) return;
    check = check || statusOnly;
    const account = session.account;
    if (!account) { remember({ ...intent, owner: null, generation: '' }); navigate(loginPath); return; }
    const generation = submissionGeneration(account.id);
    const key = intent.key || crypto.randomUUID();
    const next = { ...intent, owner: account.id, generation, key, uncertain: true, resolved: false };
    remember(next); setBusy(true); setError('');
    const valid = () => mounted.current && current.current.account?.id === account.id && current.current.account.csrf_token === account.csrf_token && submissionGeneration(account.id) === generation;
    try {
      const value = await taskRequest<PreviewDecision>(check ? `/api/copies?${new URLSearchParams({ source_kind: kind, operation_key: key })}` : '/api/copies', check ? {} : { csrf: account.csrf_token, body: { source_kind: kind, source_id: source, operation_key: key } });
      if (!valid()) return;
      remember({ ...next, resolved: true });
      if (value.outcome === 'saved' && repeatable && onCopied) {
        setIntent({ ...next, key: null, uncertain: false, resolved: true });
        setDecision(null);
        onCopied(value);
      } else {
        setDecision(value);
        if (value.outcome === 'saved') onCopied?.(value);
      }
    } catch (failure) {
      if (!valid()) return;
      if (failure instanceof TaskFailure && failure.status === 401) { setLocked(true); void session.refresh(); return; }
      if (check && failure instanceof TaskFailure && failure.status === 404) {
        remember({ ...next, uncertain: false }); setError(statusOnly ? 'We could not find a saved copy. Return to My trips to try again.' : 'We could not find a saved copy. You can try copying it again.');
      } else if (!check && failure instanceof TaskFailure && failure.status === 404) {
        remember({ ...next, key: null, uncertain: false }); setError('The source itinerary is no longer available.');
      } else {
        setError('Copy could not be confirmed. Check its status before explicitly retrying.');
      }
    } finally { if (valid()) setBusy(false); }
  }
  if (statusOnly && !intent.key) return null;
  if (session.status === 'expired' || locked) return <div className="copy-controls"><p>Your copy action is private. Log in to the same account to check its status.</p><Link className="btn btn-light" to={loginPath}>Log in</Link></div>;
  return <div className="copy-controls">
    {decision ? <div role="status"><p>{decision.outcome === 'saved_result_deleted' ? 'This saved copy was deleted. It will not be recreated.' : 'An independent copy was added to My trips.'}</p>
      {decision.outcome === 'saved' && <Link className="btn btn-light" to={`/trips/${decision.saved_trip_id}`}>View saved copy</Link>}
      {!statusOnly && <button type="button" className="btn btn-light" onClick={() => { remember({ owner: session.account?.id || null, generation: session.account ? submissionGeneration(session.account.id) : '', kind, source, title, key: null, uncertain: false }); setDecision(null); setError(''); }}>Start another copy</button>}
    </div> : <button type="button" aria-label={!intent.uncertain && !busy ? ariaLabel : undefined} className={buttonClassName} disabled={busy || session.status === 'loading'} onClick={() => void perform(intent.uncertain)}>{buttonIcon}{busy ? 'Checking copy…' : statusOnly || intent.uncertain ? 'Check copy status' : intent.key ? 'Retry copy' : label}</button>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
