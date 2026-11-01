import { useEffect, useRef, useState } from 'react';
import { isDialogBackdropClick } from '../../shared/dialog';

export function AccountDeletion({ allowed, onDelete }: { allowed: boolean; onDelete: (password: string) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  const mounted = useRef(false);
  const pending = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!open) return;
    const node = dialog.current;
    const opener = document.activeElement;
    node?.showModal();
    return () => {
      if (node?.open) node.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [open]);
  const close = () => { if (!pending.current) { setOpen(false); setPassword(''); setError(''); } };
  return <section className="account-delete" aria-label="Account deletion">
    <h2>Delete account</h2>
    <p className="small-muted">{allowed ? 'Permanently delete your account and its saved travel data.' : 'The default test account cannot be deleted.'}</p>
    <button type="button" className="btn btn-light text-danger" disabled={!allowed} onClick={() => setOpen(true)}>Delete account</button>
    {open && <dialog ref={dialog} className="modal-card library-dialog account-delete-dialog" aria-labelledby="delete-account-title"
      onCancel={event => { event.preventDefault(); close(); }} onClick={event => { if (isDialogBackdropClick(event)) close(); }}>
      <h2 id="delete-account-title">Permanently delete your account?</h2>
      <p>Your profile, saved travel briefs, planning history and trips will be permanently deleted. This cannot be undone.</p>
      <form onSubmit={event => {
        event.preventDefault();
        if (!allowed || pending.current || !password) return;
        pending.current = true; setBusy(true); setError('');
        void onDelete(password).catch(failure => {
          if (mounted.current) setError(failure instanceof Error ? failure.message : 'Your account could not be deleted.');
        }).finally(() => {
          pending.current = false;
          if (mounted.current) { setBusy(false); setPassword(''); }
        });
      }}>
        <label className="field"><span>Current password</span><input type="password" autoComplete="current-password" required maxLength={128} value={password} disabled={busy} onChange={event => setPassword(event.target.value)} /></label>
        {error && <p role="alert">{error}</p>}
        <div className="modal-actions"><button type="button" className="btn btn-light" disabled={busy} onClick={close}>Cancel</button><button type="submit" className="btn btn-danger" disabled={busy || !password}>{busy ? 'Deleting…' : 'Delete my account'}</button></div>
      </form>
    </dialog>}
  </section>;
}
