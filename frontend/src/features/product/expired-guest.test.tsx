import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../app/router';
import { createBrief } from './editor';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

function expiredPage(path: string, loginDelay?: Promise<void>) {
  sessionStorage.setItem('dayloom.editor.v1', JSON.stringify({ owner: 'alice',
    brief: { ...createBrief(), destination: 'Private city', preferences: 'Private preferences' },
    actionId: 'private-operation', draftRef: { id: 'private-draft', title: 'Private draft', revision: 2 } }));
  const requests: string[] = [];
  let signedIn = false;
  let account = { id: 'alice', email: 'alice@example.com', display_name: 'Alice', initials: 'A', csrf_token: 'new-csrf' };
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    requests.push(url);
    if (url === '/api/auth/login') {
      signedIn = true;
      if (JSON.parse(options?.body as string).email === 'bob@example.com') account = { ...account, id: 'bob', email: 'bob@example.com' };
      await loginDelay;
    }
    if (url === '/api/auth/login' || (url === '/api/auth/current' && signedIn)) return Response.json(account);
    if (url === '/api/auth/current') return Response.json({ detail: { code: 'session_expired' } }, { status: 401 });
    if (url === '/api/examples') return Response.json([{ id: 'sydney-example', title: 'Sydney harbour', destination: 'Sydney', start_date: '2026-10-24', end_date: '2026-10-25', day_count: 2, stop_count: 3, transfer_count: 2 }]);
    if (url === '/api/planning/date-window') return Response.json({ allowedStart: '2026-10-21', allowedEnd: '2026-11-03', maxTripDays: 10 });
    if (url === '/api/drafts' && options?.method === 'POST') return Response.json({ id: 'guest-draft', title: 'Guest draft', revision: 1 });
    if (url === '/api/drafts/guest-draft') return Response.json({ id: 'guest-draft', title: 'Guest draft', revision: 1, editor: { ...createBrief(), destination: 'Guest city' } });
    return Response.json([]);
  }));
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const view = render(<RouterProvider router={router} />);
  return { requests, router, unmount: view.unmount, loginInAnotherTab: () => { signedIn = true; } };
}

async function signIn(email = 'alice@example.com') {
  fireEvent.change(await screen.findByLabelText('Email address'), { target: { value: email } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }));
}

it('shows public examples and a login reminder when a private session has expired', async () => {
  const { requests } = expiredPage('/trips');
  expect(await screen.findByRole('heading', { name: 'Sydney harbour' })).toBeVisible();
  expect(screen.getByRole('link', { name: 'Log in again' })).toHaveAttribute('href', '/login?return=%2Ftrips');
  expect(screen.queryByText('Private city')).not.toBeInTheDocument();
  expect(requests.some(url => url.startsWith('/api/library'))).toBe(false);
  expect(sessionStorage.getItem('dayloom.editor.v1')).toContain('Private preferences');
});

it('continues an edited guest brief after login and can explicitly restore the old private brief', async () => {
  const { requests } = expiredPage('/plan');
  fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Guest city' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
  await signIn();
  expect(await screen.findByLabelText('Destination')).toHaveValue('Guest city');
  expect(screen.getByRole('button', { name: 'Save draft' })).toHaveTextContent('Save travel brief');
  const confirmation = vi.spyOn(window, 'confirm').mockReturnValue(true);
  fireEvent.click(screen.getByRole('button', { name: 'Restore previous brief' }));
  expect(screen.getByLabelText('Destination')).toHaveValue('Private city');
  expect(screen.getByRole('button', { name: 'Save draft' })).toHaveTextContent('Update draft');
  expect(requests).not.toContain('/api/drafts');
  confirmation.mockRestore();
});

it('retains the separate guest brief across application recreation', async () => {
  const first = expiredPage('/plan');
  fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Guest city' } });
  first.unmount();
  expiredPage('/plan');
  expect(await screen.findByLabelText('Destination')).toHaveValue('Guest city');
  expect(sessionStorage.getItem('dayloom.editor.v1')).toContain('Private city');
});

it('restores the private brief on login when the guest has not edited', async () => {
  expiredPage('/plan');
  fireEvent.click(await screen.findByRole('link', { name: 'Log in again' }));
  await signIn();
  expect(await screen.findByLabelText('Destination')).toHaveValue('Private city');
  expect(screen.queryByRole('button', { name: 'Restore previous brief' })).not.toBeInTheDocument();
});

it('carries only guest input into another account and clears the old private recovery', async () => {
  expiredPage('/plan');
  fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Guest city' } });
  fireEvent.click(screen.getByRole('link', { name: 'Log in again' }));
  await signIn('bob@example.com');
  expect(await screen.findByLabelText('Destination')).toHaveValue('Guest city');
  expect(screen.queryByRole('button', { name: 'Restore previous brief' })).not.toBeInTheDocument();
  expect(sessionStorage.getItem('dayloom.editor.v1')).not.toContain('Private city');
  expect(sessionStorage.getItem('dayloom.editor.previous.v1')).toBeNull();
});

it('clears expired guest input and private recovery after account invalidation', async () => {
  expiredPage('/plan');
  fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Guest city' } });
  await act(async () => {
    localStorage.setItem('dayloom.account.invalidation.alice', 'revoked');
    window.dispatchEvent(new StorageEvent('storage', { key: 'dayloom.account.invalidation.alice', newValue: 'revoked' }));
  });
  expect(screen.getByLabelText('Destination')).toHaveValue('');
  expect(sessionStorage.getItem('dayloom.expired-guest.brief.v1')).toBeNull();
  expect(sessionStorage.getItem('dayloom.editor.v1')).not.toContain('Private city');
});

it('keeps guest edits when a focus refresh sees login before its response finishes', async () => {
  let finish!: () => void;
  const gate = new Promise<void>(resolve => { finish = resolve; });
  expiredPage('/plan', gate);
  fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Guest city' } });
  fireEvent.click(screen.getByRole('link', { name: 'Log in again' }));
  await signIn();
  await act(async () => window.dispatchEvent(new Event('focus')));
  await act(async () => finish());
  expect(await screen.findByLabelText('Destination')).toHaveValue('Guest city');
  expect(screen.getByRole('button', { name: 'Restore previous brief' })).toBeVisible();
});

it('continues edited guest input when the same account logs in through another tab', async () => {
  const { loginInAnotherTab } = expiredPage('/plan');
  fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Guest city' } });
  await act(async () => {
    loginInAnotherTab();
    const value = JSON.stringify({ id: 'alice', nonce: 'other-tab-login' });
    localStorage.setItem('dayloom.account.active', value);
    window.dispatchEvent(new StorageEvent('storage', { key: 'dayloom.account.active', newValue: value }));
  });
  expect(await screen.findByLabelText('Destination')).toHaveValue('Guest city');
  expect(screen.getByRole('button', { name: 'Restore previous brief' })).toBeVisible();
});

it('clears a newly saved draft route before restoring the previous private brief', async () => {
  const { requests, router } = expiredPage('/plan');
  fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Guest city' } });
  fireEvent.click(screen.getByRole('link', { name: 'Log in again' }));
  await signIn();
  await screen.findByLabelText('Destination');
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
  await waitFor(() => expect(router.state.location.search).toBe('?draft=guest-draft'));
  const confirmation = vi.spyOn(window, 'confirm').mockReturnValue(true);
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Restore previous brief' })));
  expect(router.state.location.search).toBe('');
  expect(screen.getByLabelText('Destination')).toHaveValue('Private city');
  expect(requests).not.toContain('/api/drafts/guest-draft');
  confirmation.mockRestore();
});

it('lets an expired visitor edit and clear a separate guest brief while preserving private recovery', async () => {
  const { router, requests } = expiredPage('/plan');
  const input = await screen.findByLabelText('Destination');
  expect(input).toHaveValue('');
  expect(screen.getByRole('link', { name: 'Log in again' })).toBeVisible();
  fireEvent.change(input, { target: { value: 'Guest city' } });
  expect(input).toHaveValue('Guest city');
  await act(async () => window.dispatchEvent(new Event('focus')));
  expect(screen.getByLabelText('Destination')).toHaveValue('Guest city');
  await act(async () => router.navigate('/trips'));
  await screen.findByRole('heading', { name: 'Sydney harbour' });
  await act(async () => router.navigate('/plan'));
  expect(await screen.findByLabelText('Destination')).toHaveValue('Guest city');
  expect(sessionStorage.getItem('dayloom.editor.v1')).toContain('Private city');
  expect(sessionStorage.getItem('dayloom.editor.v1')).not.toContain('Guest city');
  fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
  expect(screen.getByLabelText('Destination')).toHaveValue('');
  expect(sessionStorage.getItem('dayloom.editor.v1')).toContain('Private preferences');
  expect(requests).not.toContain('/api/profile');
  expect(requests).not.toContain('/api/drafts/private-draft');
});
