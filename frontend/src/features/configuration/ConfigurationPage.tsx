import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import './configuration.css';

type Field = { value: string | null; secret: boolean; configured: boolean; locked: boolean };
type Configuration = { revision: string; restart_required: boolean; running_ready: boolean; fields: Record<string, Field> };
type Readiness = { ready: boolean; missing: string[]; credentials_verified: boolean; resources: { id: string; ready: boolean }[] };
const sections = [
  { title: 'Azure Foundry', description: 'Connect the model deployment used by this installation.', fields: [
    ['AZURE_OPENAI_ENDPOINT', 'Foundry endpoint', 'HTTPS endpoint ending in /openai/v1.'],
    ['AZURE_OPENAI_DEPLOYMENT', 'Deployment', 'Use the deployment supported by the current runtime profile.'],
    ['AZURE_OPENAI_API_KEY', 'Foundry API key', 'Used for itinerary planning and supporting model calls.'],
  ] },
  { title: 'OpenAI', description: 'Connect the existing retrieval and web evidence services.', fields: [
    ['OPENAI_API_KEY', 'OpenAI API key', 'Used for TripWorld query embeddings and the configured web search.'],
  ] },
  { title: 'Google Maps', description: 'Find places, calculate connections and display place photographs.', fields: [
    ['GOOGLE_MAPS_API_KEY', 'Google Maps API key', 'Shared by planning and place photographs.'],
  ] },
  { title: 'Unsplash', description: 'Optional atmosphere photographs. Illustrations are used when unavailable.', fields: [
    ['PRODUCT_UNSPLASH_ACCESS_KEY', 'Unsplash access key', 'Optional. Existing UNSPLASH_API_KEY settings are also recognized.'],
  ] },
];
const resourceHelp: Record<string, [string, string]> = {
  product_settings: ['Application settings', 'Prepare DAYLOOM_DB_PASSWORD and PRODUCT_JWT_SECRET (at least 32 characters) in .env.'],
  database: ['PostgreSQL', 'Start the local database using scripts/run_database.py.'],
  migrations: ['Product migrations', 'Apply Product migrations using scripts/migrate_product.py.'],
  tokenizers: ['Tokenizer resources', 'Prepare both tokenizers following docs/guides/development.md.'],
  tripworld: ['TripWorld retrieval', 'Prepare the compatible database and retrieval files following docs/guides/development.md.'],
};
const errors: Record<string, string> = {
  invalid_management_token: 'The management token is incorrect. Copy it from the running Dayloom terminal.',
  configuration_locked: 'Your management session has expired. Unlock configuration again.',
  configuration_changed: 'The configuration changed elsewhere. Reload it before saving again.',
  setting_managed_by_environment: 'A setting is controlled by the process environment. Reload to see its current status.',
  invalid_foundry_endpoint: 'Use a Microsoft Foundry HTTPS endpoint ending in /openai/v1.',
  invalid_foundry_deployment: 'Use a deployment name containing letters, numbers, dots, underscores or hyphens.',
  invalid_setting_value: 'A value contains unsupported characters or exceeds the allowed length.',
  configuration_unreadable: 'The local configuration could not be read or saved. Check .env and product.yaml in the terminal.',
  invalid_dotenv: 'The .env file has invalid syntax. Correct it in a text editor, then try again.',
  too_many_attempts: 'Too many attempts. Wait a minute before trying again.',
  too_many_sessions: 'Too many management sessions are open. Lock another session or restart Dayloom.',
  local_configuration_unavailable: 'Local configuration is available through scripts/run_product.py on a loopback address.',
};

class ConfigurationFailure extends Error {
  constructor(public status: number, code: string) {
    super(errors[code] || 'The configuration request failed. Check that Dayloom is running at its configured local address.');
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/config${path}`, {
    ...init, credentials: 'same-origin', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...init.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ConfigurationFailure(response.status, body.detail?.code || '');
  }
  return response.status === 204 ? undefined as T : response.json();
}

export function ConfigurationPage() {
  const [config, setConfig] = useState<Configuration | null>(null);
  const [csrf, setCsrf] = useState('');
  const [token, setToken] = useState('');
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    async function restore() {
      try {
        const session = await request<{ csrf_token: string }>('/session', { signal: controller.signal });
        const saved = await request<Configuration>('', { signal: controller.signal });
        if (!controller.signal.aborted) { setCsrf(session.csrf_token); setConfig(saved); }
      } catch (failure) {
        if (!controller.signal.aborted && !(failure instanceof ConfigurationFailure && failure.status === 401)) {
          setError(failure instanceof ConfigurationFailure ? failure.message : 'Could not reach the local application.');
        }
      } finally {
        if (!controller.signal.aborted) setInitializing(false);
      }
    }
    void restore();
    return () => controller.abort();
  }, []);

  async function perform(action: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await action(); }
    catch (failure) {
      if (failure instanceof ConfigurationFailure && failure.status === 401) {
        setConfig(null); setCsrf(''); setEdits({}); setReadiness(null); setToken('');
      }
      setError(failure instanceof ConfigurationFailure ? failure.message : 'Could not reach the local application. Try again.');
    } finally { setBusy(false); }
  }

  function unlock(event: FormEvent) {
    event.preventDefault();
    void perform(async () => {
      const session = await request<{ csrf_token: string }>('/session', { method: 'POST', body: JSON.stringify({ token }) });
      setToken('');
      const saved = await request<Configuration>('');
      setCsrf(session.csrf_token); setConfig(saved);
    });
  }

  function save(event: FormEvent) {
    event.preventDefault();
    void perform(async () => {
      const saved = await request<Configuration>('', { method: 'PUT', headers: { 'X-CSRF-Token': csrf },
        body: JSON.stringify({ revision: config!.revision, changes: edits }) });
      setConfig(saved); setEdits({}); setReadiness(null);
      setNotice('Saved. Restart Dayloom from the terminal after active tasks finish to apply your changes.');
    });
  }

  function edit(key: string, value: string, secret: boolean) {
    setEdits(current => {
      const next = { ...current };
      if (secret && !value) delete next[key];
      else next[key] = value;
      return next;
    });
    setNotice('');
  }

  return <div className="config-page">
    <header className="config-header"><Link to="/" className="config-brand">Dayloom<span>Local configuration</span></Link>
      {config && <button type="button" disabled={busy} onClick={() => void perform(async () => {
        await request('/session', { method: 'DELETE', headers: { 'X-CSRF-Token': csrf } });
        setConfig(null); setCsrf(''); setEdits({}); setReadiness(null);
      })}>Lock configuration</button>}
    </header>
    <main className="config-content">
      <div className="config-intro"><p className="config-eyebrow">YOUR LOCAL INSTALLATION</p><h1>Make Dayloom ready.</h1>
        <p>Connect the services used by this installation. Saved changes take effect after restarting Dayloom.</p></div>
      {error && <p className="config-message config-error" role="alert">{error}</p>}
      {notice && <p className="config-message" role="status">{notice}</p>}
      {initializing ? <p role="status">Checking local management session…</p> : !config ?
        <section className="config-card config-unlock"><h2>Unlock configuration</h2>
          <p>Copy the management token printed by the running Dayloom terminal. This access is separate from traveler accounts.</p>
          <form onSubmit={unlock}><label htmlFor="management-token">Management token</label>
            <input id="management-token" type="password" autoComplete="off" value={token} required maxLength={256}
              onChange={event => setToken(event.target.value)} />
            <button className="config-primary" type="submit" disabled={busy}>{busy ? 'Unlocking…' : 'Unlock configuration'}</button>
          </form></section> : <>
          <aside className="config-message" aria-label="Application status">
            <strong>{config.running_ready ? 'Application started with ready local resources.' : 'Setup is incomplete. Planning is paused.'}</strong>
            <span>{config.restart_required ? 'Saved configuration differs from the running process. Restart required.' : 'No saved provider changes are waiting for a restart.'}</span>
          </aside>
          <form onSubmit={save}>
            <div className="config-grid">{sections.map(section => <section className="config-card" key={section.title}>
              <h2>{section.title}</h2><p>{section.description}</p>
              {section.fields.map(([key, label, help]) => {
                const field = config.fields[key];
                if (!field) return null;
                const edited = Object.hasOwn(edits, key);
                return <div className="config-field" key={key}>
                  <label htmlFor={key}>{label}<span>{field.locked ? 'Managed by environment' : edited ? (edits[key] ? 'Change pending' : 'Will be cleared') : field.configured ? 'Configured' : 'Missing'}</span></label>
                  <div className="config-input-row"><input id={key} type={field.secret ? 'password' : 'text'}
                    autoComplete="off" spellCheck={false} maxLength={field.secret ? 4096 : key.endsWith('DEPLOYMENT') ? 128 : 4096}
                    aria-label={label} aria-describedby={`${key}-help`} disabled={busy || field.locked}
                    placeholder={field.secret && field.configured ? 'Leave empty to keep the saved key' : ''}
                    value={edited ? edits[key] : field.secret ? '' : field.value || ''}
                    onChange={event => edit(key, event.target.value, field.secret)} />
                    {field.secret && field.configured && !field.locked && <button type="button" disabled={busy}
                      aria-label={`Clear ${label}`} onClick={() => setEdits(current => ({ ...current, [key]: '' }))}>Clear</button>}
                  </div><small id={`${key}-help`}>{help}</small>
                </div>;
              })}
            </section>)}</div>
            <div className="config-actions"><button className="config-primary" type="submit" disabled={busy || !Object.keys(edits).length}>Save configuration</button>
              <button type="button" disabled={busy} onClick={() => void perform(async () => {
                setConfig(await request<Configuration>('')); setEdits({}); setReadiness(null);
              })}>Reload saved configuration</button>
              <span>Keys are stored locally and are never displayed after saving.</span>
            </div>
          </form>
          <section className="config-card config-resources"><div className="config-resource-heading"><div><h2>Local resources</h2>
            <p>Checks saved configuration and local resources. No external API calls are made, and key validity is not verified.</p></div>
            <button type="button" disabled={busy || !!Object.keys(edits).length} onClick={() => void perform(async () => {
              setReadiness(await request<Readiness>('/readiness'));
            })}>Check local readiness</button></div>
            {Object.keys(edits).length > 0 && <p>Save or reload your changes before checking readiness.</p>}
            {readiness && <><p role="status">{readiness.ready ? 'Saved configuration and local resources are ready. Restart if changes are pending.' : 'Some configuration or local resources still need attention.'}</p>
              {readiness.missing.length > 0 && <p>Missing settings: {readiness.missing.join(', ')}</p>}
              <ul>{readiness.resources.map(resource => <li key={resource.id}>
                <div><strong>{resourceHelp[resource.id]?.[0] || resource.id}</strong><span className={resource.ready ? 'config-ready' : 'config-missing'}>{resource.ready ? 'Ready' : 'Needs attention'}</span></div>
                {!resource.ready && <p>{resourceHelp[resource.id]?.[1] || 'Follow the local deployment guide to prepare this resource.'}</p>}
              </li>)}</ul></>}
            <p>Database credentials, signing keys and data preparation follow <code>docs/guides/development.md</code>.</p>
          </section>
        </>}
    </main>
    <footer className="config-footer">Local instance settings · Finish active tasks before restarting · API charges belong to your service accounts</footer>
  </div>;
}
