import { useState, type FormEvent } from 'react';

export type ConfigurationAccess = { password_required: boolean; revision: string };
export type AccessChange = {
  revision: string; enabled: boolean; current_password?: string;
  new_password?: string; confirmation?: string;
};

export function ConfigurationAccessSettings({ access, busy, pendingProviderEdits, onSave, onVerify }: {
  access: ConfigurationAccess; busy: boolean; pendingProviderEdits: boolean;
  onSave: (change: AccessChange) => void;
  onVerify: (password: string) => Promise<boolean>;
}) {
  const [enabled, setEnabled] = useState(access.password_required);
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [verified, setVerified] = useState(false);
  const disabled = busy || pendingProviderEdits;
  const canChange = !access.password_required || verified;

  function save(event: FormEvent) {
    event.preventDefault();
    if (disabled || !canChange) return;
    setError('');
    if (enabled && password !== confirmation) { setError('Passwords do not match.'); return; }
    onSave({ revision: access.revision, enabled,
      ...(access.password_required ? { current_password: current } : {}),
      ...(enabled ? { new_password: password, confirmation } : {}),
    });
    setCurrent(''); setPassword(''); setConfirmation(''); setVerified(false);
  }

  return <section className="config-card config-security" aria-labelledby="config-access-title">
    <h2 id="config-access-title">Configuration access</h2>
    <p>{access.password_required ? 'Enter the password each time you open configuration. Verify it again before changing access settings.' : 'Configuration opens without a password.'}
      {' '}Access settings take effect immediately and remain saved after restarting.</p>
    <form onSubmit={save}>
      {pendingProviderEdits && <p>Save or reload provider edits before changing access settings.</p>}
      <label className="config-toggle"><input type="checkbox" checked={enabled} disabled={disabled}
        onChange={event => { setEnabled(event.target.checked); setError(''); }} />
        <span>Require a password to open configuration</span></label>
      <div className="config-password-grid">
        {access.password_required && <div className="config-field"><label htmlFor="config-current-password">Current password</label>
          <input id="config-current-password" type="password" autoComplete="current-password" value={current}
            required maxLength={128} disabled={disabled || verified} onChange={event => setCurrent(event.target.value)} />
          {!verified ? <button type="button" disabled={disabled || !current}
            onClick={() => void onVerify(current).then(setVerified)}>Verify current password</button>
            : <small role="status">Current password verified.</small>}</div>}
        {enabled && canChange && <><div className="config-field"><label htmlFor="config-new-password">New password</label>
          <input id="config-new-password" type="password" autoComplete="new-password" value={password} required minLength={10}
            maxLength={128} disabled={disabled} aria-describedby="config-password-length" onChange={event => setPassword(event.target.value)} />
          <small id="config-password-length">Use 10–128 characters. This password is separate from traveler accounts.</small></div>
          <div className="config-field"><label htmlFor="config-confirm-password">Confirm password</label>
            <input id="config-confirm-password" type="password" autoComplete="new-password" value={confirmation} required
              maxLength={128} disabled={disabled} onChange={event => setConfirmation(event.target.value)} /></div></>}
      </div>
      {error && <p role="alert">{error}</p>}
      <div className="config-access-actions"><button type="submit" disabled={disabled || !canChange || (enabled === access.password_required && !password)}>
        Save access settings</button></div>
    </form>
  </section>;
}
