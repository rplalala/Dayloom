import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ConfigurationAccessSettings, type AccessChange, type ConfigurationAccess } from './ConfigurationAccessSettings';
import './configuration.css';

type Field = { value: string | null; secret: boolean; configured: boolean; locked: boolean };
type Configuration = { revision: string; restart_required: boolean; running_ready: boolean; fields: Record<string, Field> };
type Readiness = { ready: boolean; missing: string[]; credentials_verified: boolean; resources: { id: string; ready: boolean }[] };
type Service = 'all' | 'foundry' | 'openai' | 'google' | 'unsplash';
type ApiResult = { id: string; service: Service; status: string; message: string; latency_ms: number; http_status?: number };
type ApiReport = { revision: string; stale: boolean; service: Service; checked_at: string; request_count: number; results: ApiResult[] };
const sections: { service?: Exclude<Service, 'all'>; title: string; description: string; fields: string[][] }[] = [
  { title: 'PostgreSQL', description: 'Use the same database for accounts and TripWorld retrieval. Connection changes do not move existing data.', fields: [
    ['DAYLOOM_DB_HOST', 'Database host', 'Local Compose normally uses 127.0.0.1.'],
    ['DAYLOOM_DB_PORT', 'Database port', 'Local Compose normally uses 55432.'],
    ['DAYLOOM_DB_NAME', 'Database name', 'Select the database containing your prepared data.'],
    ['DAYLOOM_DB_USER', 'Database user', 'The PostgreSQL login role.'],
    ['DAYLOOM_DB_PASSWORD', 'Database password', 'Must match the existing database role password.'],
    ['DAYLOOM_DB_URL', 'Connection URL (optional)', 'Overrides the host, port, name, user and password above. Clear it to use those fields.'],
  ] },
  { title: 'Account sessions', description: 'Existing signing keys are retained. New local installations generate and save a private key automatically.', fields: [
    ['PRODUCT_JWT_SECRET', 'JWT signing key', 'Use at least 32 characters, or generate a key below. Changing it signs out existing accounts after restart.'],
  ] },
  { service: 'foundry', title: 'Azure Foundry', description: 'Connect the model deployment used by this installation.', fields: [
    ['AZURE_OPENAI_ENDPOINT', 'Foundry endpoint', 'Saved in product.yaml → foundry.endpoint. Use an HTTPS endpoint ending in /openai/v1.'],
    ['AZURE_OPENAI_DEPLOYMENT', 'Deployment', 'Saved in product.yaml → foundry.deployment. Use the deployment supported by the current runtime profile.'],
    ['AZURE_OPENAI_API_KEY', 'Foundry API key', 'Used for itinerary planning, web search and supporting model calls.'],
  ] },
  { service: 'openai', title: 'OpenAI', description: 'Connect the existing retrieval embedding service.', fields: [
    ['OPENAI_API_KEY', 'OpenAI API key', 'Used for TripWorld query embeddings.'],
  ] },
  { service: 'google', title: 'Google Maps', description: 'Find places, calculate connections and display place photographs.', fields: [
    ['GOOGLE_MAPS_API_KEY', 'Google Maps API key', 'Shared by planning and place photographs.'],
  ] },
  { service: 'unsplash', title: 'Unsplash', description: 'Optional atmosphere photographs. Illustrations are used when unavailable.', fields: [
    ['PRODUCT_UNSPLASH_ACCESS_KEY', 'Unsplash access key', 'Optional. Existing UNSPLASH_API_KEY settings are also recognized.'],
  ] },
];
const apiNames: Record<string, string> = {
  foundry: 'Structured model response', foundry_search: 'Web search', openai_embeddings: 'Query embeddings',
  google_places: 'Places', google_routes: 'Routes', google_photos: 'Place photos', unsplash: 'Photo metadata',
};
const apiStatuses: Record<string, string> = {
  passed: 'Passed', not_configured: 'Not configured', authentication_failed: 'Authentication failed',
  permission_denied: 'Permission denied', billing_required: 'Billing required', quota_exceeded: 'Quota exhausted',
  rate_limited: 'Rate limited', not_found: 'Deployment / resource not found', network_error: 'Network error',
  timeout: 'Timed out', provider_error: 'Provider error', invalid_configuration: 'Invalid configuration',
  invalid_response: 'Response not verified', not_checked: 'Not checked', inconclusive: 'Not verified',
};
const resourceHelp: Record<string, [string, string]> = {
  product_settings: ['Application settings', 'Complete the database and account session settings above.'],
  database: ['PostgreSQL', 'Start the local database with uv run dayloom db up -d.'],
  migrations: ['Product migrations', 'Apply Product migrations with uv run dayloom migrate.'],
  tokenizers: ['Tokenizer resources', 'Prepare both tokenizers following docs/guides/development.md.'],
  tripworld: ['TripWorld retrieval', 'Prepare the compatible database and retrieval files following docs/guides/development.md.'],
};
const errors: Record<string, string> = {
  invalid_configuration_password: 'The configuration password is incorrect.',
  configuration_access_unreadable: 'Configuration access settings could not be read. Check .config-access.json in the project folder before trying again.',
  configuration_password_required: 'Enter a new configuration password containing 10–128 characters.',
  password_confirmation_mismatch: 'Passwords do not match.',
  configuration_locked: 'Your management session has expired. Unlock configuration again.',
  configuration_changed: 'The configuration changed elsewhere. Reload it before saving again.',
  setting_managed_by_environment: 'A setting is controlled by the process environment. Reload to see its current status.',
  invalid_foundry_endpoint: 'Use a Microsoft Foundry HTTPS endpoint ending in /openai/v1.',
  invalid_foundry_deployment: 'Use a deployment name containing letters, numbers, dots, underscores or hyphens.',
  invalid_database_setting: 'Enter a valid database connection and a port from 1 to 65535.',
  invalid_signing_key: 'Use a signing key containing at least 32 characters.',
  invalid_setting_value: 'A value contains unsupported characters or exceeds the allowed length.',
  configuration_unreadable: 'The local configuration could not be read or saved. Check .env and product.yaml in the terminal.',
  invalid_dotenv: 'The .env file has invalid syntax. Correct it in a text editor, then try again.',
  too_many_attempts: 'Too many attempts. Wait a minute before trying again.',
  too_many_sessions: 'Too many configuration sessions are open. Wait for a session to expire or restart Dayloom.',
  local_configuration_unavailable: 'Local configuration is available through uv run dayloom start on a loopback address.',
  api_check_in_progress: 'Another API check is already running. Wait for it to finish.',
  api_check_failed: 'The API check could not complete. No automatic retry was made.',
};

class ConfigurationFailure extends Error {
  constructor(public status: number, public code: string) {
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
  const pageGeneration = useRef(0);
  const pendingRequests = useRef(new Set<AbortController>());
  const [config, setConfig] = useState<Configuration | null>(null);
  const [csrf, setCsrf] = useState('');
  const [password, setPassword] = useState('');
  const [access, setAccess] = useState<ConfigurationAccess | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [apiReports, setApiReports] = useState<Partial<Record<Service, ApiReport>>>({});
  const [initializing, setInitializing] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const invalidateRequests = useCallback(() => {
    pageGeneration.current += 1;
    pendingRequests.current.forEach(controller => controller.abort());
    pendingRequests.current.clear();
  }, []);
  useEffect(() => invalidateRequests, [invalidateRequests]);

  useEffect(() => {
    const controller = new AbortController();
    async function restore() {
      try {
        const permissions = await request<ConfigurationAccess>('/access', { signal: controller.signal });
        if (controller.signal.aborted) return;
        setAccess(permissions);
        if (permissions.password_required) return;
        const session = await request<{ csrf_token: string }>('/session', {
          method: 'POST', body: '{}', signal: controller.signal,
        });
        const saved = await request<Configuration>('', { signal: controller.signal,
          headers: { 'X-CSRF-Token': session.csrf_token } });
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

  useEffect(() => {
    if (!access?.password_required) return;
    const relock = () => {
      invalidateRequests(); setBusy(false);
      setConfig(null); setCsrf(''); setPassword(''); setEdits({});
      setReadiness(null); setApiReports({}); setNotice('');
    };
    window.addEventListener('pagehide', relock);
    window.addEventListener('pageshow', relock);
    return () => {
      window.removeEventListener('pagehide', relock);
      window.removeEventListener('pageshow', relock);
    };
  }, [access?.password_required, invalidateRequests]);

  async function perform(action: (pageRequest: typeof request) => Promise<void>) {
    const generation = pageGeneration.current;
    const controller = new AbortController();
    pendingRequests.current.add(controller);
    async function pageRequest<T>(path: string, init: RequestInit = {}) {
      const result = await request<T>(path, { ...init, signal: controller.signal });
      if (generation !== pageGeneration.current) throw new Error('Page access ended.');
      return result;
    }
    setBusy(true); setError(''); setNotice('');
    try { await action(pageRequest); }
    catch (failure) {
      if (generation !== pageGeneration.current) return;
      if (failure instanceof ConfigurationFailure && failure.status === 401) {
        setConfig(null); setCsrf(''); setEdits({}); setReadiness(null); setPassword(''); setApiReports({});
        try { setAccess(await pageRequest<ConfigurationAccess>('/access')); }
        catch { if (generation === pageGeneration.current) setAccess(null); }
      }
      if (generation !== pageGeneration.current) return;
      if (failure instanceof ConfigurationFailure && ['configuration_changed', 'configuration_unreadable'].includes(failure.code)) setApiReports({});
      setError(failure instanceof ConfigurationFailure ? failure.message : 'Could not reach the local application. Try again.');
    } finally {
      pendingRequests.current.delete(controller);
      if (generation === pageGeneration.current) setBusy(false);
    }
  }

  function unlock(event: FormEvent) {
    event.preventDefault();
    void perform(async (request) => {
      const session = await request<{ csrf_token: string }>('/session', {
        method: 'POST', body: JSON.stringify(access?.password_required ? { password } : {}),
      });
      setPassword('');
      const saved = await request<Configuration>('', { headers: { 'X-CSRF-Token': session.csrf_token } });
      setCsrf(session.csrf_token); setConfig(saved);
    });
  }

  function save(event: FormEvent) {
    event.preventDefault();
    void perform(async (request) => {
      const saved = await request<Configuration>('', { method: 'PUT', headers: { 'X-CSRF-Token': csrf },
        body: JSON.stringify({ revision: config!.revision, changes: edits }) });
      setConfig(saved); setEdits({}); setReadiness(null); setApiReports({});
      setNotice('Saved. Restart Dayloom from the terminal after active tasks finish to apply your changes.');
    });
  }

  function saveAccess(change: AccessChange) {
    if (Object.keys(edits).length) return;
    void perform(async (request) => {
      const updated = await request<ConfigurationAccess>('/access', { method: 'PUT',
        headers: { 'X-CSRF-Token': csrf }, body: JSON.stringify(change) });
      setAccess(updated); setConfig(null); setCsrf(''); setPassword('');
      setEdits({}); setReadiness(null); setApiReports({});
      if (updated.password_required) {
        setNotice('Password verification is enabled. Enter your configuration password to continue.');
      } else {
        const session = await request<{ csrf_token: string }>('/session', { method: 'POST', body: '{}' });
        const saved = await request<Configuration>('', { headers: { 'X-CSRF-Token': session.csrf_token } });
        setCsrf(session.csrf_token); setConfig(saved);
        setNotice('Password verification is disabled. Configuration opens directly.');
      }
    });
  }

  async function verifyAccess(currentPassword: string) {
    let verified = false;
    await perform(async (request) => {
      await request('/access/verify', { method: 'POST', headers: { 'X-CSRF-Token': csrf },
        body: JSON.stringify({ current_password: currentPassword }) });
      verified = true;
    });
    return verified;
  }

  function edit(key: string, value: string, secret: boolean) {
    setEdits(current => {
      const next = { ...current };
      if (secret && !value) delete next[key];
      else next[key] = value;
      return next;
    });
    setNotice('');
    setApiReports({});
  }

  function checkApis(service: Service) {
    if (!config || Object.keys(edits).length) return;
    const revision = config.revision;
    void perform(async (request) => {
      setApiReports(current => service === 'all' ? {} : { ...current, [service]: undefined });
      const report = await request<ApiReport>('/check', { method: 'POST',
        headers: { 'X-CSRF-Token': csrf }, body: JSON.stringify({ revision, service }) });
      if (report.stale || report.revision !== revision) {
        setApiReports({});
        setError('Configuration changed while checks were running. Reload saved configuration and check again.');
        return;
      }
      setApiReports(current => {
        const next = { ...current };
        for (const section of sections) {
          if (section.service && (service === 'all' || service === section.service)) {
            next[section.service] = { ...report, results: report.results.filter(item => item.service === section.service) };
          }
        }
        return next;
      });
      setNotice(`API checks finished with ${report.request_count} HTTP attempts. Review the results below.`);
    });
  }

  return <div className={`config-page${!config ? ' config-locked' : ''}`}>
    <header className="config-header"><Link to="/" className="config-brand">Dayloom<span>Local configuration</span></Link>
    </header>
    <main className="config-content">
      <div className="config-intro"><p className="config-eyebrow">YOUR LOCAL INSTALLATION</p><h1>Make Dayloom ready.</h1>
        <p>Connect the services used by this installation. Saved changes take effect after restarting Dayloom.</p></div>
      {error && <p className="config-message config-error" role="alert">{error}</p>}
      {notice && <p className="config-message" role="status">{notice}</p>}
      {initializing ? <p role="status">Checking local management session…</p> : !config ?
        <section className="config-card config-unlock"><h2>{access?.password_required ? 'Unlock configuration' : 'Open configuration'}</h2>
          {access ? <form onSubmit={unlock}>
            {access.password_required && <><p id="configuration-password-help">Enter this installation's configuration password. This is separate from traveler accounts.</p>
              {access.default_test_password && <aside className="config-test-password" aria-label="Test password">
                <span>Default test password</span><code>{access.default_test_password}</code>
                <p>Use this password for local testing, then change it in configuration. If you have already changed it, enter your own password.</p>
              </aside>}
              <label htmlFor="configuration-password">Configuration password</label>
              <input id="configuration-password" type="password" autoComplete="current-password" value={password} required maxLength={128}
                aria-describedby="configuration-password-help" onChange={event => setPassword(event.target.value)} /></>}
            <button className="config-primary" type="submit" disabled={busy}>{busy ? 'Opening…' : access.password_required ? 'Unlock configuration' : 'Open configuration'}</button>
          </form> : <p>Local configuration is unavailable. Start Dayloom at its configured local address and reload this page.</p>}</section> : <>
          <aside className="config-message" aria-label="Application status">
            <strong>{config.running_ready ? 'Application started with ready local resources.' : 'Setup is incomplete. Planning is paused.'}</strong>
            <span>{config.restart_required ? 'Saved configuration differs from the running process. Restart required.' : 'No saved provider changes are waiting for a restart.'}</span>
          </aside>
          {access && <ConfigurationAccessSettings key={access.revision} access={access} busy={busy}
            pendingProviderEdits={!!Object.keys(edits).length} onSave={saveAccess} onVerify={verifyAccess} />}
          <section className="config-card config-api-intro" aria-label="API connectivity checks">
            <div><h2>Check service access</h2><p>API checks send small requests to your saved services and may incur charges.
              All checks use at most 8 HTTP attempts and 60 seconds, with no automatic retries.</p>
              <p>Requests are sent only when you click Check API or Check all APIs. Save or reload any edits first.</p></div>
            <button type="button" disabled={busy || !!Object.keys(edits).length} onClick={() => checkApis('all')}>Check all APIs</button>
          </section>
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
                    {field.secret && key !== 'PRODUCT_JWT_SECRET' && field.configured && !field.locked && <button type="button" disabled={busy}
                      aria-label={`Clear ${label}`} onClick={() => {
                        setEdits(current => ({ ...current, [key]: '' })); setApiReports({}); setNotice('');
                      }}>Clear</button>}
                  </div><small id={`${key}-help`}>{help}</small>
                </div>;
              })}
              {section.service && <div className="config-api-actions"><button type="button" aria-label={`Check ${section.title} API`}
                disabled={busy || !!Object.keys(edits).length} onClick={() => checkApis(section.service!)}>Check API</button></div>}
              {section.service && apiReports[section.service] && <div className="config-api-results" aria-label={`${section.title} API results`} aria-live="polite">
                <p className="config-api-time">Checked {new Date(apiReports[section.service]!.checked_at).toLocaleString()}</p>
                <ul>{apiReports[section.service]!.results.map(result => <li key={result.id} data-status={result.status}>
                  <div><strong>{apiNames[result.id] || result.id}</strong><span className="config-api-status">{apiStatuses[result.status] || 'Not verified'}</span></div>
                  <p>{result.message}</p><small>{result.latency_ms} ms{result.http_status ? ` · HTTP ${result.http_status}` : ''}</small>
                </li>)}</ul>
              </div>}
              {section.title === 'Account sessions' && config.fields.PRODUCT_JWT_SECRET && <div className="config-api-actions">
                <button type="button" disabled={busy || !!Object.keys(edits).length || config.fields.PRODUCT_JWT_SECRET.locked}
                  onClick={() => void perform(async (request) => {
                    const saved = await request<Configuration>('/signing-key', { method: 'POST', headers: { 'X-CSRF-Token': csrf },
                      body: JSON.stringify({ revision: config.revision }) });
                    setConfig(saved); setReadiness(null); setApiReports({});
                    setNotice('New signing key saved. Restart Dayloom after active tasks finish. Existing accounts will need to sign in again.');
                  })}>Generate signing key</button>
              </div>}
            </section>)}</div>
            <div className="config-actions"><button className="config-primary" type="submit" disabled={busy || !Object.keys(edits).length}>Save configuration</button>
              <button type="button" disabled={busy} onClick={() => void perform(async (request) => {
                setConfig(await request<Configuration>('', { headers: { 'X-CSRF-Token': csrf } })); setEdits({}); setReadiness(null); setApiReports({});
              })}>Reload saved configuration</button>
              <span>Saved settings belong to this installation. Secrets are never displayed after saving.</span>
            </div>
          </form>
          <section className="config-card config-resources"><div className="config-resource-heading"><div><h2>Local resources</h2>
            <p>Checks required settings and the running application's local resources. No external API calls are made; keys are not verified.</p></div>
            <button type="button" disabled={busy || !!Object.keys(edits).length} onClick={() => void perform(async (request) => {
              setReadiness(await request<Readiness>('/readiness', { headers: { 'X-CSRF-Token': csrf } }));
            })}>Check local readiness</button></div>
            {Object.keys(edits).length > 0 && <p>Save or reload your changes before checking readiness.</p>}
            {readiness && <><p role="status">{readiness.ready ? 'Required settings and current local resources are ready. Restart to check pending connection changes.' : 'Some configuration or local resources still need attention.'}</p>
              {readiness.missing.length > 0 && <p>Missing settings: {readiness.missing.join(', ')}</p>}
              <ul>{readiness.resources.map(resource => <li key={resource.id}>
                <div><strong>{resourceHelp[resource.id]?.[0] || resource.id}</strong><span className={resource.ready ? 'config-ready' : 'config-missing'}>{resource.ready ? 'Ready' : 'Needs attention'}</span></div>
                {!resource.ready && <p>{resourceHelp[resource.id]?.[1] || 'Follow the local deployment guide to prepare this resource.'}</p>}
              </li>)}</ul></>}
            <p>To check saved database changes before restarting, run <code>uv run dayloom check</code> in a new terminal. Preparation follows <code>docs/guides/development.md</code>.</p>
          </section>
        </>}
    </main>
    <footer className="config-footer">Local instance settings · Finish active tasks before restarting · API charges belong to your service accounts</footer>
  </div>;
}
