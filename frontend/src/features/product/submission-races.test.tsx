import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../app/router';
import { createBrief } from './editor';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it.each(['draft navigation', 'logout and same-account login'])('an old lookup cannot submit or rebind a new action after %s', async transition => {
  const original = { ...createBrief(), destination: 'Sydney', start_date: '2026-10-22', end_date: '2026-10-23', travelers: '2', budget: '1000' };
  const next = { ...original, destination: 'Kyoto' };
  sessionStorage.setItem('dayloom.editor.v1', JSON.stringify({ owner: 'alice', brief: original, actionId: 'old-operation', origin: 'restored' }));
  let release: ((value: Response) => void) | undefined;
  let loggedIn = true;
  let csrf = 'original-session';
  const submissions: { operation_key: string; request: { destination: string } }[] = [];
  const draftId = 'e8a18ca5-30e0-4df1-8786-dc3b0f42a752';
  const account = () => ({ id: 'alice', display_name: 'Alice', initials: 'A', csrf_token: csrf });
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/auth/current') return Response.json(loggedIn ? account() : { detail: { code: 'session_revoked' } }, { status: loggedIn ? 200 : 401 });
    if (url === '/api/auth/login') { loggedIn = true; csrf = 'new-session'; return Response.json(account()); }
    if (url === '/api/planning/date-window') return Response.json({ allowedStart: '2026-10-21', allowedEnd: '2026-11-03', maxTripDays: 10 });
    if (url === '/api/profile') return Response.json({ currency: 'AUD', interests: [], pace: null, transport: [], additional_preferences: '' });
    if (url === `/api/drafts/${draftId}`) return Response.json({ id: draftId, title: 'New brief', revision: 1, editor: next });
    if (url.includes('operation_key=old-operation')) return new Promise<Response>(resolve => { release = resolve; });
    if (url === '/api/planning/tasks' && options?.method === 'POST') {
      const payload = JSON.parse(String(options.body)); submissions.push(payload);
      return Response.json({ id: `task-${submissions.length}`, state: 'pending' }, { status: 202 });
    }
    return Response.json(url.includes('operation_key=') ? null : []);
  }));
  const router = createMemoryRouter(routes, { initialEntries: ['/plan'] });
  render(<RouterProvider router={router} />);
  await screen.findByDisplayValue('Sydney');
  fireEvent.click(screen.getByRole('button', { name: /Generate itinerary/ }));
  await waitFor(() => expect(release).toBeDefined());
  if (transition === 'draft navigation') {
    await act(async () => { await router.navigate(`/plan?draft=${draftId}`); });
    await screen.findByDisplayValue('Kyoto');
  } else {
    // This tab can leave the editor before another tab explicitly revokes the session.
    await act(async () => { await router.navigate('/login?return=/plan'); });
    loggedIn = false;
    localStorage.setItem('dayloom.account.invalidation.alice', 'after-explicit-logout');
    fireEvent(window, new StorageEvent('storage', { key: 'dayloom.account.notice', newValue: JSON.stringify({ type: 'logout' }) }));
    fireEvent.change(await screen.findByLabelText('Email address'), { target: { value: 'alice@example.com' } });
    fireEvent.change(screen.getByLabelText('Password', { exact: true }), { target: { value: 'secure password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }));
    fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Kyoto' } });
    fireEvent.change(screen.getByLabelText('Start date'), { target: { value: next.start_date } });
    fireEvent.change(screen.getByLabelText('End date'), { target: { value: next.end_date } });
    fireEvent.change(screen.getByLabelText('Travelers'), { target: { value: next.travelers } });
    fireEvent.change(screen.getByLabelText('Whole-trip budget'), { target: { value: next.budget } });
  }
  fireEvent.click(screen.getByRole('button', { name: /Generate itinerary/ }));
  await screen.findByRole('link', { name: /Open task progress/ });
  expect(submissions).toHaveLength(1);
  const newKey = submissions[0].operation_key;
  await act(async () => { release!(Response.json(null)); });
  expect(submissions).toHaveLength(1);
  expect(sessionStorage.getItem('dayloom.editor.v1')).toContain(newKey);
  const intent = JSON.parse(sessionStorage.getItem('dayloom.task.intent.v1')!);
  expect(intent.key).toBe(newKey);
  expect(intent.request.destination).toBe('Kyoto');
  expect(screen.getByLabelText('Destination')).toHaveValue('Kyoto');
});
