import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { AccountPage } from './AccountPage';
import { SessionProvider, useSession } from './session';
import { createBrief } from './editor';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

function setup(email = 'alice@example.com', deletion?: Response | Promise<Response>) {
  const account = { id: 'alice', email, display_name: 'Alice', initials: 'A', csrf_token: 'csrf' };
  const requests: RequestInit[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/auth/account') { requests.push(options!); return deletion || new Response(null, { status: 204 }); }
    if (url === '/api/profile') return Response.json({ display_name: 'Alice', initials: 'A', currency: 'AUD',
      interests: [], pace: null, transport: [], notes: '', can_delete_account: email !== 'admin@admin.com' });
    return Response.json(account);
  }));
  render(<MemoryRouter><SessionProvider><AccountPage /></SessionProvider></MemoryRouter>);
  return requests;
}

it('requires an explicit confirmation and clears the session after account deletion', async () => {
  sessionStorage.setItem('dayloom.editor.v1', JSON.stringify({ owner: 'alice', brief: { ...createBrief(), destination: 'Private city' }, actionId: 'private-operation' }));
  sessionStorage.setItem('dayloom.task.intent.v1', JSON.stringify({ owner: 'alice' }));
  sessionStorage.setItem('dayloom.import.intent.v1', JSON.stringify({ owner: 'alice' }));
  const requests = setup();
  fireEvent.click(await screen.findByRole('button', { name: 'Delete account' }));
  expect(screen.getByRole('dialog', { name: 'Permanently delete your account?' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Delete my account' })).toBeDisabled();
  expect(requests).toEqual([]);
  fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'my current password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Delete my account' }));
  await screen.findByText('Your account and its travel data have been deleted.');
  expect(requests).toHaveLength(1);
  expect(requests[0].method).toBe('DELETE');
  expect(requests[0].headers).toMatchObject({ 'X-CSRF-Token': 'csrf' });
  expect(JSON.parse(requests[0].body as string)).toEqual({ password: 'my current password', confirmed: true });
  expect(screen.queryByLabelText('Display name')).not.toBeInTheDocument();
  await waitFor(() => expect(JSON.parse(sessionStorage.getItem('dayloom.editor.v1')!).owner).toBeNull());
  expect(sessionStorage.getItem('dayloom.task.intent.v1')).toBeNull();
  expect(sessionStorage.getItem('dayloom.import.intent.v1')).toBeNull();
  expect(sessionStorage.getItem('dayloom.editor.v1')).not.toContain('Private city');
  fireEvent(window, new Event('focus'));
  expect(screen.queryByLabelText('Display name')).not.toBeInTheDocument();
});

it('disables deletion for the default test admin and explains why', async () => {
  const requests = setup('admin@admin.com');
  expect(await screen.findByRole('button', { name: 'Delete account' })).toBeDisabled();
  expect(screen.getByText('The default test account cannot be deleted.')).toBeVisible();
  expect(requests).toEqual([]);
});

it('cancels the confirmation without deleting anything', async () => {
  const requests = setup();
  fireEvent.click(await screen.findByRole('button', { name: 'Delete account' }));
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Display name')).toHaveValue('Alice');
  expect(requests).toEqual([]);
});

it.each([
  ['invalid_password', 403, 'Your current password is incorrect.'],
  ['account_tasks_active', 409, 'Stop active planning tasks before deleting your account.'],
] as const)('keeps the account and reports %s without retrying', async (code, status, message) => {
  const requests = setup('alice@example.com', Response.json({ detail: { code } }, { status }));
  fireEvent.click(await screen.findByRole('button', { name: 'Delete account' }));
  fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'wrong password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Delete my account' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(message);
  expect(screen.getByLabelText('Display name')).toHaveValue('Alice');
  expect(screen.getByLabelText('Current password')).toHaveValue('');
  expect(requests).toHaveLength(1);
});

it('sends only one deletion while the confirmation is pending', async () => {
  let resolve!: (response: Response) => void;
  const requests = setup('alice@example.com', new Promise(done => { resolve = done; }));
  fireEvent.click(await screen.findByRole('button', { name: 'Delete account' }));
  fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Delete my account' }));
  expect(screen.getByRole('button', { name: 'Deleting…' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Deleting…' }));
  expect(requests).toHaveLength(1);
  await act(async () => resolve(new Response(null, { status: 204 })));
});

it('does not retry a deletion whose network result is unknown', async () => {
  let reject!: (error: Error) => void;
  const requests = setup('alice@example.com', new Promise((_done, fail) => { reject = fail; }));
  fireEvent.click(await screen.findByRole('button', { name: 'Delete account' }));
  fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Delete my account' }));
  await act(async () => reject(new Error('Connection lost')));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not confirm account deletion.');
  expect(screen.getByLabelText('Display name')).toHaveValue('Alice');
  expect(requests).toHaveLength(1);
});

function SwitchAccount() {
  const session = useSession();
  return <button onClick={() => void session.authenticate('login', { email: 'bob@example.com', password: 'password' })}>Switch account</button>;
}

it('keeps a newer account when an older deletion completes late', async () => {
  let complete!: (response: Response) => void;
  const pending = new Promise<Response>(resolve => { complete = resolve; });
  let account = { id: 'alice', email: 'alice@example.com', display_name: 'Alice', initials: 'A', csrf_token: 'alice-csrf' };
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/auth/account') return pending;
    if (url === '/api/auth/login') account = { id: 'bob', email: 'bob@example.com', display_name: 'Bob', initials: 'B', csrf_token: 'bob-csrf' };
    if (url === '/api/profile') return Response.json({ ...account, currency: 'AUD', interests: [], pace: null, transport: [], notes: '', can_delete_account: true });
    return Response.json(account);
  }));
  render(<MemoryRouter><SessionProvider><AccountPage /><SwitchAccount /></SessionProvider></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', { name: 'Delete account' }));
  fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Delete my account' }));
  fireEvent.click(screen.getByRole('button', { name: 'Switch account' }));
  await screen.findByDisplayValue('Bob');
  await act(async () => complete(new Response(null, { status: 204 })));
  fireEvent(window, new Event('focus'));
  await waitFor(() => expect(screen.getByLabelText('Display name')).toHaveValue('Bob'));
  expect(screen.queryByText('Your account and its travel data have been deleted.')).not.toBeInTheDocument();
  expect(JSON.parse(sessionStorage.getItem('dayloom.editor.v1')!).owner).toBe('bob');
});
