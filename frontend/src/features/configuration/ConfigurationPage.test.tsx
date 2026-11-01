import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ConfigurationPage } from './ConfigurationPage';

afterEach(() => vi.unstubAllGlobals());

it.each(['unlock', 'reload'])('ignores a delayed %s response after the protected page is hidden and restored', async operation => {
  const config = { revision: 'a'.repeat(64), restart_required: false, running_ready: true,
    fields: { OPENAI_API_KEY: { value: null, secret: true, configured: true, locked: false } } };
  let resolveConfig!: (response: Response) => void;
  let waiting = false;
  let reads = 0;
  const deferred = new Promise<Response>(resolve => { resolveConfig = resolve; });
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.endsWith('/access')) return Response.json({ password_required: true, revision: 'f'.repeat(64) });
    if (url.endsWith('/session')) return Response.json({ csrf_token: 'page-token' });
    if (operation === 'reload' && reads++ === 0) return Response.json(config);
    waiting = true;
    return deferred;
  }));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  fireEvent.change(await screen.findByLabelText('Configuration password'), { target: { value: 'private-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Unlock configuration' }));
  if (operation === 'reload') {
    await screen.findByLabelText('OpenAI API key');
    fireEvent.click(screen.getByRole('button', { name: 'Reload saved configuration' }));
  }
  await waitFor(() => expect(waiting).toBe(true));
  act(() => {
    window.dispatchEvent(new Event('pagehide'));
    window.dispatchEvent(new Event('pageshow'));
  });
  await act(async () => { resolveConfig(Response.json(config)); });
  expect(screen.getByLabelText('Configuration password')).toBeInTheDocument();
  expect(screen.queryByLabelText('OpenAI API key')).not.toBeInTheDocument();
});

it('opens configuration automatically when password verification is off', async () => {
  const writes: { url: string; body: unknown }[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'POST') writes.push({ url, body: JSON.parse(init.body as string) });
    if (url.endsWith('/access')) return Response.json({ password_required: false, revision: 'f'.repeat(64) });
    if (url.endsWith('/session')) return init?.method === 'POST'
      ? Response.json({ csrf_token: 'csrf' }) : Response.json({}, { status: 401 });
    return Response.json({ revision: 'a'.repeat(64), restart_required: false, running_ready: true,
      fields: { OPENAI_API_KEY: { value: null, secret: true, configured: false, locked: false } } });
  }));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  expect(await screen.findByLabelText('OpenAI API key')).toBeInTheDocument();
  expect(screen.queryByLabelText('Management token')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Configuration password')).not.toBeInTheDocument();
  expect(writes).toEqual([{ url: '/api/config/session', body: {} }]);
  fireEvent.change(screen.getByLabelText('OpenAI API key'), { target: { value: 'unsaved-private-key' } });
  expect(screen.getByLabelText('Require a password to open configuration')).toBeDisabled();
  expect(screen.getByText('Save or reload provider edits before changing access settings.')).toBeInTheDocument();
});

it('enables password verification and requires the current password to turn it off', async () => {
  let protectedAccess = false;
  let locked = false;
  const updates: Record<string, unknown>[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/access')) {
      if (init?.method === 'PUT') {
        const body = JSON.parse(init.body as string);
        updates.push(body); protectedAccess = body.enabled; locked = true;
      }
      return Response.json({ password_required: protectedAccess, revision: (protectedAccess ? 'b' : 'a').repeat(64) });
    }
    if (url.endsWith('/session')) {
      if (init?.method === 'POST') locked = false;
      return locked ? Response.json({}, { status: 401 }) : Response.json({ csrf_token: 'csrf' });
    }
    return Response.json({ revision: 'a'.repeat(64), restart_required: false, running_ready: true,
      fields: { OPENAI_API_KEY: { value: null, secret: true, configured: false, locked: false } } });
  }));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  fireEvent.click(await screen.findByLabelText('Require a password to open configuration'));
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'new-private-password' } });
  fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'new-private-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save access settings' }));
  const password = await screen.findByLabelText('Configuration password');
  expect(screen.queryByLabelText('OpenAI API key')).not.toBeInTheDocument();
  fireEvent.change(password, { target: { value: 'new-private-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Unlock configuration' }));
  fireEvent.click(await screen.findByLabelText('Require a password to open configuration'));
  fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'new-private-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Verify current password' }));
  await screen.findByText('Current password verified.');
  fireEvent.click(screen.getByRole('button', { name: 'Save access settings' }));
  await screen.findByText(/^Configuration opens without a password\./);
  expect(screen.getByLabelText('OpenAI API key')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Lock configuration' })).not.toBeInTheDocument();
  expect(updates[0]).toMatchObject({ enabled: true, new_password: 'new-private-password', confirmation: 'new-private-password' });
  expect(updates[1]).toMatchObject({ enabled: false, current_password: 'new-private-password' });
});

it('requires the password again on every entry even when a browser session already exists', async () => {
  const calls: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push(`${init?.method || 'GET'} ${url}`);
    if (url.endsWith('/access')) return Response.json({ password_required: true, revision: 'a'.repeat(64) });
    if (url.endsWith('/session')) return Response.json({ csrf_token: 'page-only-token' });
    expect(init?.headers).toMatchObject({ 'X-CSRF-Token': 'page-only-token' });
    return Response.json({ revision: 'a'.repeat(64), restart_required: false, running_ready: true,
      fields: { OPENAI_API_KEY: { value: null, secret: true, configured: true, locked: false } } });
  }));
  const first = render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  const password = await screen.findByLabelText('Configuration password');
  expect(calls).toEqual(['GET /api/config/access']);
  fireEvent.change(password, { target: { value: 'current-private-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Unlock configuration' }));
  await screen.findByLabelText('OpenAI API key');
  expect(screen.queryByLabelText('New password')).not.toBeInTheDocument();
  first.unmount();
  calls.length = 0;
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  await screen.findByLabelText('Configuration password');
  expect(calls).toEqual(['GET /api/config/access']);
  expect(screen.queryByLabelText('OpenAI API key')).not.toBeInTheDocument();
});

it('unlocks independently, saves only edited fields and clears typed secrets', async () => {
  const config = { revision: 'a'.repeat(64), restart_required: false, running_ready: false,
    fields: {
      AZURE_OPENAI_ENDPOINT: { value: 'https://example.services.ai.azure.com/openai/v1', secret: false, configured: true, locked: false },
      AZURE_OPENAI_DEPLOYMENT: { value: 'gpt-6-luna', secret: false, configured: true, locked: false },
      AZURE_OPENAI_API_KEY: { value: null, secret: true, configured: true, locked: false },
      OPENAI_API_KEY: { value: null, secret: true, configured: true, locked: false },
      GOOGLE_MAPS_API_KEY: { value: null, secret: true, configured: false, locked: false },
      PRODUCT_UNSPLASH_ACCESS_KEY: { value: null, secret: true, configured: false, locked: false },
    } };
  const requests: { url: string; init?: RequestInit }[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    requests.push({ url, init });
    if (url.endsWith('/access')) return Response.json({ password_required: true, revision: 'f'.repeat(64) });
    if (url.endsWith('/session')) {
      return new Response(JSON.stringify(init?.method === 'POST' ? { csrf_token: 'csrf' } : {}),
        { status: init?.method === 'POST' ? 200 : 401 });
    }
    return new Response(JSON.stringify(init?.method === 'PUT'
      ? { ...config, restart_required: true } : config));
  }));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  fireEvent.change(await screen.findByLabelText('Configuration password'), { target: { value: 'local-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Unlock configuration' }));
  const key = await screen.findByLabelText('OpenAI API key');
  expect(key).toHaveValue('');
  fireEvent.change(key, { target: { value: 'synthetic-new-key' } });
  expect(screen.getByRole('button', { name: 'Check local readiness' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Save configuration' }));
  await screen.findByText(/Saved. Restart Dayloom/);
  expect(screen.getByLabelText('OpenAI API key')).toHaveValue('');
  const saved = requests.find(request => request.init?.method === 'PUT')!;
  expect(JSON.parse(saved.init!.body as string)).toEqual({ revision: 'a'.repeat(64), changes: { OPENAI_API_KEY: 'synthetic-new-key' } });
  expect((saved.init!.headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf');
  await waitFor(() => expect(requests.some(request => request.url.includes('/api/auth'))).toBe(false));
});

it('locks fields controlled by the process environment and reports local resource checks', async () => {
  const calls: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    calls.push(url);
    if (url.endsWith('/access')) return Response.json({ password_required: false, revision: 'f'.repeat(64) });
    const value = url.endsWith('/session') ? { csrf_token: 'restored-csrf' }
      : url.endsWith('/readiness') ? { ready: false, credentials_verified: false,
        missing: ['GOOGLE_MAPS_API_KEY'], resources: [{ id: 'database', ready: false }] }
      : { revision: 'b'.repeat(64), restart_required: false, running_ready: true, fields: {
        OPENAI_API_KEY: { value: null, configured: true, secret: true, locked: true },
      } };
    return new Response(JSON.stringify(value));
  }));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  expect(await screen.findByLabelText('OpenAI API key')).toBeDisabled();
  expect(screen.queryByRole('button', { name: 'Clear OpenAI API key' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Check local readiness' }));
  await screen.findByText('Needs attention');
  expect(screen.getByText(/Missing settings: GOOGLE_MAPS_API_KEY/)).toBeInTheDocument();
  expect(calls).toEqual(['/api/config/access', '/api/config/session', '/api/config', '/api/config/readiness']);
});

it('clears typed secrets when the management session expires', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') return new Response(JSON.stringify({ detail: { code: 'configuration_locked' } }), { status: 401 });
    if (url.endsWith('/access')) return Response.json({ password_required: true, revision: 'f'.repeat(64) });
    return new Response(JSON.stringify(url.endsWith('/session') ? { csrf_token: 'csrf' } : {
      revision: 'c'.repeat(64), restart_required: false, running_ready: true,
      fields: { OPENAI_API_KEY: { value: null, secret: true, configured: false, locked: false } },
    }));
  }));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  fireEvent.change(await screen.findByLabelText('Configuration password'), { target: { value: 'current-private-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Unlock configuration' }));
  fireEvent.change(await screen.findByLabelText('OpenAI API key'), { target: { value: 'unsaved-private' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save configuration' }));
  await screen.findByLabelText('Configuration password');
  expect(screen.queryByDisplayValue('unsaved-private')).not.toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent(/session has expired/);
});

it('checks APIs only on click and invalidates results when settings are edited', async () => {
  const calls: { url: string; init?: RequestInit }[] = [];
  const revision = 'd'.repeat(64);
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    if (url.endsWith('/access')) return Response.json({ password_required: false, revision: 'f'.repeat(64) });
    const value = url.endsWith('/session') ? { csrf_token: 'csrf' }
      : url.endsWith('/check') ? { revision, stale: false, request_count: 8,
        checked_at: '2026-11-01T00:00:00Z', service: 'all', results: [
          { id: 'foundry', service: 'foundry', status: 'passed', message: 'Model responded.', latency_ms: 5 },
          { id: 'foundry_search', service: 'foundry', status: 'passed', message: 'Search responded.', latency_ms: 8 },
          { id: 'openai_embeddings', service: 'openai', status: 'authentication_failed', message: 'The service rejected the credential.', latency_ms: 10 },
        ] }
      : { revision, restart_required: false, running_ready: true, fields: {
        OPENAI_API_KEY: { value: null, secret: true, configured: true, locked: false },
      } };
    return new Response(JSON.stringify(value));
  }));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  await screen.findByLabelText('OpenAI API key');
  expect(calls.some(call => call.url.endsWith('/check'))).toBe(false);
  expect(screen.getByText(/may incur charges/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Check all APIs' }));
  await screen.findByText('Search responded.');
  expect(within(screen.getByLabelText('Azure Foundry API results')).getByText('Web search')).toBeInTheDocument();
  expect(within(screen.getByLabelText('OpenAI API results')).queryByText('Web search')).not.toBeInTheDocument();
  expect(screen.getByText('Authentication failed')).toBeInTheDocument();
  const check = calls.find(call => call.url.endsWith('/check'))!;
  expect(check.init?.method).toBe('POST');
  expect(JSON.parse(check.init!.body as string)).toEqual({ revision, service: 'all' });
  expect((check.init!.headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf');
  expect(calls.some(call => call.init?.method === 'PUT')).toBe(false);
  fireEvent.change(screen.getByLabelText('OpenAI API key'), { target: { value: 'unsaved' } });
  expect(screen.queryByText('Passed')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Check all APIs' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Check OpenAI API' })).toBeDisabled();
});

it('never displays a stale result as a passed check', async () => {
  const revision = 'e'.repeat(64);
  vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('/access')
    ? Response.json({ password_required: false, revision: 'f'.repeat(64) }) : new Response(JSON.stringify(
    url.endsWith('/session') ? { csrf_token: 'csrf' }
      : url.endsWith('/check') ? { revision, stale: true, service: 'foundry',
        checked_at: '2026-11-01T00:00:00Z', request_count: 1,
        results: [{ id: 'foundry', service: 'foundry', status: 'passed', message: 'Old result.', latency_ms: 1 }] }
      : { revision, restart_required: false, running_ready: true, fields: {} },
  ))));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', { name: 'Check Azure Foundry API' }));
  await screen.findByText(/Configuration changed while/);
  expect(screen.queryByText('Passed')).not.toBeInTheDocument();
});
