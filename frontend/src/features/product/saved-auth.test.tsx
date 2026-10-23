import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { AuthPage } from './AuthPage';
import { SavedPage } from './SavedPage';
import { PreviewPage } from './tasks';
import { SessionProvider } from './session';

const id = '11111111-1111-4111-8111-111111111111';
const account = { id: 'alice', email: 'alice@example.com', display_name: 'Alice', initials: 'A', csrf_token: 'csrf' };
const detail = { schema_version: 'product_detail_1', id, title: 'Private itinerary title', destination: 'Sydney', provenance: 'generated', trust: 'generated_projection', request: null, days: [], nearby: [], transfers: [] };
const expired = () => Response.json({ detail: { code: 'session_expired' } }, { status: 401 });

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

function open(path: string) {
  const router = createMemoryRouter([
    { path: '/trips/:tripId', element: <SavedPage /> },
    { path: '/previews/:previewId', element: <PreviewPage /> },
    { path: '/login', element: <AuthPage /> },
    { path: '/plan', element: <p>Plan recovery</p> },
    { path: '/trips', element: <p>Collection fallback</p> },
  ], { initialEntries: [path] });
  render(<SessionProvider><RouterProvider router={router} /></SessionProvider>);
  return router;
}

async function login() {
  fireEvent.change(await screen.findByLabelText('Email address'), { target: { value: 'alice@example.com' } });
  fireEvent.change(screen.getByLabelText('Password', { exact: true }), { target: { value: 'offline password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }));
}

it('returns from saved-detail login to that exact UUID detail', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => url === '/api/auth/login' ? Response.json(account) : url === `/api/trips/${id}` ? Response.json(detail) : expired()));
  const router = open(`/trips/${id}`);
  fireEvent.click(await screen.findByRole('link', { name: 'Log in' }));
  expect(router.state.location.search).toBe(`?return=${encodeURIComponent(`/trips/${id}`)}`);
  await login();
  await screen.findByRole('heading', { name: detail.title });
  expect(router.state.location.pathname).toBe(`/trips/${id}`);
});

it.each([
  'https://example.com/private',
  '//example.com/private',
  `/trips/${id}?next=https://example.com`,
  '/trips/------------------------------------',
  `/trips/${id}/../account`,
  `/plan?task=${id}&next=https://example.com`,
  `/plan?preview=${id}#unknown`,
])('rejects unsafe or malformed saved return target %s', async target => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => url === '/api/auth/login' ? Response.json(account) : expired()));
  const router = open(`/login?return=${encodeURIComponent(target)}`);
  await login();
  await screen.findByText('Collection fallback');
  expect(router.state.location.pathname).toBe('/trips');
});

it.each(['task', 'preview'])('retains the exact Plan %s receipt and section after login without generating', async kind => {
  const writes: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method === 'POST') writes.push(url);
    return url === '/api/auth/login' ? Response.json(account) : expired();
  }));
  const target = `/plan?${kind}=${id}#${kind === 'task' ? 'generation-progress' : 'result'}`;
  const router = open(`/login?return=${encodeURIComponent(target)}`);
  await login();
  await screen.findByText('Plan recovery');
  expect(router.state.location.pathname + router.state.location.search + router.state.location.hash).toBe(target);
  expect(writes).toEqual(['/api/auth/login']);
});

it.each(['save', 'discard'])('quarantines an expired %s reconciliation and recovers the same owner by reads only', async action => {
  let authReads = 0;
  let lost = false;
  const writes: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/auth/current') { authReads++; return lost ? expired() : Response.json(account); }
    if (url === '/api/auth/login') return Response.json({ ...account, csrf_token: 'renewed-csrf' });
    if (url === `/api/previews/${id}/${action}`) { writes.push(options?.method || ''); lost = true; throw new TypeError('Controlled lost response'); }
    if (url === `/api/previews/${id}`) return lost ? expired() : Response.json({ id, state: 'pending', saved_trip_id: null, snapshot: detail });
    throw new Error(`Unexpected test request: ${url}`);
  }));
  const router = open(`/previews/${id}`);
  await screen.findByRole('heading', { name: detail.title });
  if (action === 'discard') {
    fireEvent.click(screen.getByRole('button', { name: 'Discard preview' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm discard' }));
  } else fireEvent.click(screen.getByRole('button', { name: 'Save to My trips' }));
  const link = await screen.findByRole('link', { name: 'Log in' });
  expect(authReads).toBe(2);
  expect(screen.queryByRole('heading', { name: detail.title })).not.toBeInTheDocument();
  expect(writes).toEqual(['POST']);
  // A new session only observes the already committed decision; it cannot replay it.
  lost = false;
  vi.mocked(fetch).mockImplementation(async (url) => {
    if (url === '/api/auth/login') return Response.json({ ...account, csrf_token: 'renewed-csrf' });
    if (url === `/api/previews/${id}`) return Response.json({ id, state: action === 'save' ? 'saved' : 'discarded', saved_trip_id: action === 'save' ? id : null, snapshot: null, outcome: action === 'save' ? 'saved' : 'discarded' });
    throw new Error(`Unexpected recovery request: ${String(url)}`);
  });
  fireEvent.click(link);
  await login();
  await screen.findByText(action === 'save' ? 'Saved to My trips.' : 'Preview discarded.');
  expect(router.state.location.pathname).toBe(`/previews/${id}`);
  await waitFor(() => expect(writes).toEqual(['POST']));
});
