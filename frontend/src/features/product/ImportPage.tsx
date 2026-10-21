import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSession } from './session';
import { submissionGeneration, type Preview } from './taskClient';

const storageKey = 'dayloom.import.intent.v1';
const maximum = 5 * 1024 * 1024;
type Intent = { owner: string | null; generation: string; content: string; key: string | null; uncertain: boolean };
function restore(owner: string | null): Intent {
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
    if (saved && typeof saved.content === 'string' && new Blob([saved.content]).size <= maximum && (saved.owner === null || saved.owner === owner) && (!saved.owner || saved.generation === submissionGeneration(saved.owner))) return { ...saved, uncertain: Boolean(saved.key) };
  } catch { /* Storage is optional. */ }
  return { owner, generation: owner ? submissionGeneration(owner) : '', content: '', key: null, uncertain: false };
}
export function ImportPage() {
  const { account, status, refresh } = useSession();
  // The session wrapper remounts on explicit account changes; owner data stays quarantined.
  if (status === 'loading') return <p role="status">Checking your session…</p>;
  return <ImportEditor key={account?.id || status} accountId={account?.id || null} csrf={account?.csrf_token} expired={status === 'expired'} refresh={refresh} />;
}
function ImportEditor({ accountId, csrf, expired, refresh }: { accountId: string | null; csrf?: string; expired: boolean; refresh: () => Promise<void> }) {
  const navigate = useNavigate();
  const [intent, setIntent] = useState(() => restore(accountId));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [locked, setLocked] = useState(false);
  const mounted = useRef(true);
  const editRevision = useRef(0);
  const currentSession = useRef({ accountId, csrf });
  currentSession.current = { accountId, csrf };
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const currentGeneration = accountId ? submissionGeneration(accountId) : '';
  function remember(next: Intent) {
    setIntent(next);
    try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch { /* The form still works without storage. */ }
  }
  function edit(content: string) {
    editRevision.current += 1;
    if (!mounted.current || (accountId && submissionGeneration(accountId) !== currentGeneration)) return;
    if (new Blob([content]).size > maximum) { setError('JSON must be at most 5 MiB.'); return; }
    setError(''); remember({ owner: accountId, generation: currentGeneration, content, key: null, uncertain: false });
  }
  function readFile(file: File | undefined) {
    const revision = ++editRevision.current;
    const valid = () => mounted.current && revision === editRevision.current && currentSession.current.accountId === accountId && currentSession.current.csrf === csrf && (!accountId || submissionGeneration(accountId) === currentGeneration);
    if (!file) return;
    if (file.size > maximum) { setError('JSON must be at most 5 MiB.'); return; }
    void file.text().then(content => { if (valid()) edit(content); }, () => { if (valid()) setError('Could not read this file.'); });
  }
  async function perform(check = false) {
    if (!accountId || !csrf || busy) return;
    editRevision.current += 1;
    const key = intent.key || crypto.randomUUID();
    const next = { ...intent, owner: accountId, generation: currentGeneration, key, uncertain: true };
    remember(next); setBusy(true); setError('');
    const valid = () => mounted.current && currentSession.current.accountId === accountId && currentSession.current.csrf === csrf && submissionGeneration(accountId) === currentGeneration;
    try {
      const response = await fetch(check ? `/api/imports/${encodeURIComponent(key)}` : '/api/imports', { credentials: 'same-origin', cache: 'no-store', method: check ? 'GET' : 'POST', headers: check ? {} : { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'X-Import-Key': key }, ...(check ? {} : { body: intent.content }) });
      const body = await response.json();
      if (!valid()) return;
      if (response.status === 401) { setLocked(true); await refresh(); return; }
      if (response.ok) { const preview = body as Preview; navigate(`/previews/${preview.id}`); return; }
      if (check && response.status === 404) { remember({ ...next, uncertain: false }); setError('No import is recorded yet. You may explicitly retry with the same key.'); return; }
      if (!check && response.status >= 400 && response.status < 500) remember({ ...next, key: response.status === 409 ? key : null, uncertain: response.status === 409 });
      setError(`${body.detail?.path || ''} ${body.detail?.message || (response.status === 409 ? 'This operation key belongs to different content. Check its status.' : 'Import could not be confirmed. Check status before retrying.')}`.trim());
    } catch { if (valid()) setError('Import response was not received. Check status before explicitly retrying.'); }
    finally { if (valid()) setBusy(false); }
  }
  if (expired || locked) return <div className="container page"><h1>Your import is private.</h1><p>Log in to the same account to recover your input and check its status.</p><Link to="/login?return=/import">Log in</Link></div>;
  return <div className="container page"><div className="page-heading"><span className="eyebrow">KEEP A PAST JOURNEY</span><h1>Import itinerary</h1><p>Paste or choose historical itinerary JSON, up to 5 MiB. Review the separate preview before saving.</p></div>
    <div className="content-card"><label htmlFor="import-file">Choose JSON file</label><input id="import-file" type="file" accept=".json,application/json" disabled={busy || intent.uncertain} onChange={event => readFile(event.target.files?.[0])} />
      <label htmlFor="import-json">Itinerary JSON</label><textarea id="import-json" rows={16} value={intent.content} disabled={busy || intent.uncertain} onChange={event => edit(event.target.value)} style={{ width: '100%' }} />
      {error && <p role="alert">{error}</p>}
      {!accountId ? <Link className="btn btn-primary" to="/login?return=/import">Log in to preview</Link> : intent.uncertain ? <button className="btn btn-primary" disabled={busy} onClick={() => void perform(true)}>Check import status</button> : <button className="btn btn-primary" disabled={busy || !intent.content.trim()} onClick={() => void perform()}>{intent.key ? 'Retry import with same key' : 'Preview import'}</button>}
      <Link className="btn btn-light" to="/trips">My trips</Link>
      {intent.key && <button className="btn btn-light" disabled={busy} onClick={() => { editRevision.current += 1; remember({ owner: accountId, generation: currentGeneration, content: '', key: null, uncertain: false }); setError(''); }}>Start new import</button>}
    </div></div>;
}
