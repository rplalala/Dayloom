import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { SavedPage } from '../SavedPage';
import { SessionProvider, useSession } from '../session';
import { photoFingerprint, photoGeneration, readPhoto, writePhoto } from './photoSession';
import type { ProductDetail } from './types';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });
const account = { id: 'alice', email: 'alice@example.com', display_name: 'Alice', initials: 'A', csrf_token: 'fixture' };
const detail: ProductDetail = { schema_version: 'product_detail_1', id: 'fixture', title: 'Private trip', destination: 'Sydney', provenance: 'generated', trust: 'generated_projection', request: null,
  days: [{ date: '2026-10-31', activities: [{ activity_id: 'museum', title: 'Private museum', time_use: 'scheduled', start_time: '2026-10-31T10:00:00+11:00', end_time: '2026-10-31T11:00:00+11:00' }] }], nearby: [], transfers: [] };
const photo = { status: 'available' as const, kind: 'verified_place' as const, provider: 'Google Maps', authors: [],
  image_url: 'https://lh3.googleusercontent.com/private', source_url: 'https://www.google.com/maps/photo/fixture' };

function SessionActions() {
  const session = useSession();
  return <button onClick={() => void session.logout()}>End fixture session</button>;
}
function openSaved() {
  return render(<MemoryRouter initialEntries={['/trips/fixture']}><SessionProvider><SessionActions /><Routes><Route path="/trips/:tripId" element={<SavedPage />} /></Routes></SessionProvider></MemoryRouter>);
}

it('clears private cached photos when the authenticated session expires', async () => {
  const scope = { owner: account.id, generation: photoGeneration(account.id), snapshot: photoFingerprint(detail) };
  writePhoto('/api/trips/fixture/media', scope, 'activity:museum', photo);
  let expired = false;
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/auth/current') return expired ? Response.json({}, { status: 401 }) : Response.json(account);
    if (url === '/api/trips/fixture') return Response.json(detail);
    return Response.json({ status: 'unavailable', items: {} });
  }));
  render(<MemoryRouter initialEntries={['/trips/fixture']}><SessionProvider><Routes><Route path="/trips/:tripId" element={<SavedPage />} /></Routes></SessionProvider></MemoryRouter>);
  await screen.findByRole('heading', { name: 'Private trip' });
  expired = true;
  fireEvent(window, new Event('focus'));
  await screen.findByRole('heading', { name: 'Log in to view your saved itinerary.' });
  await waitFor(() => expect(readPhoto('/api/trips/fixture/media', scope, 'activity:museum')).toBeUndefined());
});

it('waits for both authentication and owned detail before reusing private photos', async () => {
  const scope = { owner: account.id, generation: photoGeneration(account.id), snapshot: photoFingerprint(detail) };
  writePhoto('/api/trips/fixture/media', scope, 'activity:museum', photo);
  let authenticate!: (response: Response) => void;
  let authorize!: (response: Response) => void;
  const mediaReads: string[] = [];
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url === '/api/auth/current') return new Promise<Response>(resolve => { authenticate = resolve; });
    if (url === '/api/trips/fixture') return new Promise<Response>(resolve => { authorize = resolve; });
    if (url.startsWith('/api/trips/fixture/media')) mediaReads.push(url);
    return Promise.resolve(Response.json({ status: 'unavailable', items: {} }));
  }));
  openSaved();
  expect(screen.queryByRole('img', { name: 'Private museum · place photograph' })).not.toBeInTheDocument();
  await act(async () => authenticate(Response.json(account)));
  expect(screen.getByText('Loading itinerary…')).toBeVisible();
  expect(screen.queryByRole('img', { name: 'Private museum · place photograph' })).not.toBeInTheDocument();
  await act(async () => authorize(Response.json(detail)));
  expect(await screen.findByRole('img', { name: 'Private museum · place photograph' })).toBeVisible();
  expect(mediaReads).toEqual([]);
});

it.each(['logout', 'cross-tab invalidation', 'cross-tab login', 'account switch'])('clears private photo reuse after %s', async action => {
  const scope = { owner: account.id, generation: photoGeneration(account.id), snapshot: photoFingerprint(detail) };
  writePhoto('/api/trips/fixture/media', scope, 'activity:museum', photo);
  let switched = false;
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/auth/current') return Response.json(switched ? { ...account, id: 'bob', csrf_token: 'bob-csrf' } : account);
    if (url === '/api/trips/fixture') return switched ? Response.json({}, { status: 404 }) : Response.json(detail);
    return Response.json({ status: 'unavailable', items: {} });
  }));
  openSaved();
  await screen.findByRole('img', { name: 'Private museum · place photograph' });
  if (action === 'logout') fireEvent.click(screen.getByRole('button', { name: 'End fixture session' }));
  else if (action === 'account switch') { switched = true; fireEvent(window, new Event('focus')); }
  else if (action === 'cross-tab login') {
    localStorage.setItem('dayloom.account.active', JSON.stringify({ id: 'alice', nonce: 'new-login' }));
    fireEvent(window, new StorageEvent('storage', { key: 'dayloom.account.active', newValue: localStorage.getItem('dayloom.account.active') }));
  } else {
    localStorage.setItem('dayloom.account.invalidation.alice', 'revoked');
    fireEvent(window, new StorageEvent('storage', { key: 'dayloom.account.invalidation.alice', newValue: 'revoked' }));
  }
  await waitFor(() => expect(screen.queryByRole('img', { name: 'Private museum · place photograph' })).not.toBeInTheDocument());
  expect(readPhoto('/api/trips/fixture/media', scope, 'activity:museum')).toBeUndefined();
  expect(sessionStorage.getItem('dayloom.photos.session.v1')).not.toContain('googleusercontent');
});
