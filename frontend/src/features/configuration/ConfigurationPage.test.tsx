import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ConfigurationPage } from './ConfigurationPage';

afterEach(() => vi.unstubAllGlobals());

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
    if (url.endsWith('/session')) {
      return new Response(JSON.stringify(init?.method === 'POST' ? { csrf_token: 'csrf' } : {}),
        { status: init?.method === 'POST' ? 200 : 401 });
    }
    return new Response(JSON.stringify(init?.method === 'PUT'
      ? { ...config, restart_required: true } : config));
  }));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  fireEvent.change(await screen.findByLabelText('Management token'), { target: { value: 'local-token' } });
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
  expect(calls).toEqual(['/api/config/session', '/api/config', '/api/config/readiness']);
});

it('clears typed secrets when the management session expires', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') return new Response(JSON.stringify({ detail: { code: 'configuration_locked' } }), { status: 401 });
    return new Response(JSON.stringify(url.endsWith('/session') ? { csrf_token: 'csrf' } : {
      revision: 'c'.repeat(64), restart_required: false, running_ready: true,
      fields: { OPENAI_API_KEY: { value: null, secret: true, configured: false, locked: false } },
    }));
  }));
  render(<MemoryRouter><ConfigurationPage /></MemoryRouter>);
  fireEvent.change(await screen.findByLabelText('OpenAI API key'), { target: { value: 'unsaved-private' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save configuration' }));
  await screen.findByLabelText('Management token');
  expect(screen.queryByDisplayValue('unsaved-private')).not.toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent(/session has expired/);
});
