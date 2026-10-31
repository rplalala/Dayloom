import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { usePlaceMedia } from './media';
import { render, screen } from '@testing-library/react';
import { MediaPhoto } from './MediaPhoto';
import { StrictMode } from 'react';
import { invalidatePhotos, photoGeneration, readPhoto, writePhoto } from './photoSession';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it('reuses twenty successful credited photos after remount without reacquiring links', async () => {
  const slots = Array.from({ length: 20 }, (_, i) => `activity:reload-${i}`);
  const acquired: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const batch = new URL(url, 'http://localhost').searchParams.getAll('slot');
    acquired.push(...batch);
    return Response.json({ items: Object.fromEntries(batch.map(slot => [slot, {
      status: 'available', kind: 'verified_place', provider: 'Google Maps',
      image_url: `https://lh3.googleusercontent.com/${slot}`,
      authors: [{ name: 'Fixture photographer', url: 'https://www.google.com/maps/contrib/123' }],
      source_url: 'https://www.google.com/maps/photo/fixture',
    }])) });
  }));
  const scope = { owner: 'alice', generation: photoGeneration('alice'), snapshot: 'snapshot-1' };
  const first = renderHook(() => usePlaceMedia('/api/trips/reload/media', slots, scope));
  await waitFor(() => expect(Object.values(first.result.current.items)).toHaveLength(20));
  await waitFor(() => expect(first.result.current.items[slots[19]]?.status).toBe('available'));
  first.unmount();
  const second = renderHook(() => usePlaceMedia('/api/trips/reload/media', slots, scope));
  await waitFor(() => expect(second.result.current.items[slots[19]]?.status).toBe('available'));
  expect(acquired).toEqual(slots);
  expect(second.result.current.items[slots[0]].authors?.[0].name).toBe('Fixture photographer');
});

it('distinguishes queued, loading and unavailable photographs in the UI', () => {
  const { rerender } = render(<MediaPhoto label="A place" />);
  expect(screen.getByText('Photo pending')).toBeVisible();
  rerender(<MediaPhoto label="A place" media={{ status: 'loading' }} />);
  expect(screen.getByText('Loading photo…')).toBeVisible();
  rerender(<MediaPhoto label="A place" media={{ status: 'unavailable' }} />);
  expect(screen.queryByText('Loading photo…')).not.toBeInTheDocument();
  expect(screen.getByText('Illustration')).toBeVisible();
});

it('deduplicates StrictMode and concurrent consumers of an in-flight slot', async () => {
  let release!: (response: Response) => void;
  const fetcher = vi.fn(() => new Promise<Response>(resolve => { release = resolve; }));
  vi.stubGlobal('fetch', fetcher);
  const scope = { owner: null, generation: '', snapshot: 'concurrent' };
  const first = renderHook(() => usePlaceMedia('/api/examples/shared/media', ['activity:1'], scope), { wrapper: StrictMode });
  const second = renderHook(() => usePlaceMedia('/api/examples/shared/media', ['activity:1'], scope));
  await act(async () => release(Response.json({ items: { 'activity:1': { status: 'unavailable' } } })));
  await waitFor(() => expect(first.result.current.items['activity:1']?.status).toBe('unavailable'));
  expect(second.result.current.items['activity:1']?.status).toBe('unavailable');
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it('reacquires a broken cached slot once and refreshes only the explicitly selected photo', async () => {
  const endpoint = '/api/examples/retry/media';
  const scope = { owner: null, generation: '', snapshot: 'retry' };
  const photo = { status: 'available' as const, kind: 'verified_place' as const, provider: 'Google Maps',
    image_url: 'https://lh3.googleusercontent.com/expired', source_url: 'https://www.google.com/maps/photo/fixture', authors: [] };
  writePhoto(endpoint, scope, 'broken', photo);
  writePhoto(endpoint, scope, 'neighbor', photo);
  const requests: string[][] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const slots = new URL(url, 'http://localhost').searchParams.getAll('slot');
    requests.push(slots);
    return Response.json({ items: { broken: { ...photo, image_url: 'https://lh3.googleusercontent.com/still-broken' } } });
  }));
  const { result } = renderHook(() => usePlaceMedia(endpoint, ['broken', 'neighbor'], scope));
  await waitFor(() => expect(result.current.items.broken?.status).toBe('available'));
  act(() => result.current.imageFailed('broken', result.current.items.broken));
  await waitFor(() => expect(result.current.items.broken?.image_url).toContain('still-broken'));
  act(() => result.current.imageFailed('broken', result.current.items.broken));
  await waitFor(() => expect(result.current.items.broken?.status).toBe('unavailable'));
  expect(readPhoto(endpoint, scope, 'broken')).toBeUndefined();
  expect(result.current.items.neighbor?.status).toBe('available');
  expect(requests).toEqual([['broken']]);
  act(() => result.current.refresh('broken'));
  await waitFor(() => expect(result.current.items.broken?.status).toBe('available'));
  expect(requests).toEqual([['broken'], ['broken']]);
});

it('fetches only missing slots and keeps successful first batches reusable after a later failure', async () => {
  const endpoint = '/api/examples/partial/media';
  const scope = { owner: null, generation: '', snapshot: 'partial' };
  const slots = Array.from({ length: 20 }, (_, i) => `slot:${i}`);
  const photo = { status: 'available' as const, kind: 'verified_place' as const, provider: 'Google Maps',
    image_url: 'https://lh3.googleusercontent.com/fixture', source_url: 'https://www.google.com/maps/photo/fixture', authors: [] };
  const batches: string[][] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const batch = new URL(url, 'http://localhost').searchParams.getAll('slot');
    batches.push(batch);
    if (batches.length === 2) return Response.json({}, { status: 503 });
    return Response.json({ items: Object.fromEntries(batch.map(slot => [slot, photo])) });
  }));
  const first = renderHook(() => usePlaceMedia(endpoint, slots, scope));
  await waitFor(() => expect(first.result.current.items['slot:19']?.status).toBe('unavailable'));
  first.unmount();
  batches.length = 0;
  writePhoto(endpoint, scope, 'slot:12', photo);
  writePhoto(endpoint, scope, 'slot:13', photo);
  writePhoto(endpoint, scope, 'slot:14', photo);
  writePhoto(endpoint, scope, 'slot:15', photo);
  writePhoto(endpoint, scope, 'slot:16', photo);
  writePhoto(endpoint, scope, 'slot:17', photo);
  const second = renderHook(() => usePlaceMedia(endpoint, slots, scope));
  await waitFor(() => expect(second.result.current.items['slot:19']?.status).toBe('available'));
  expect(batches).toEqual([['slot:18', 'slot:19']]);
});

it.each(['invalidate', 'unmount'])('fences late photo responses after %s', async action => {
  const endpoint = '/api/examples/late/media';
  const scope = { owner: null, generation: '', snapshot: 'late' };
  let resolve!: (response: Response) => void;
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(done => { resolve = done; })));
  const view = renderHook(() => usePlaceMedia(endpoint, ['late'], scope));
  if (action === 'invalidate') act(() => invalidatePhotos({ resource: endpoint }));
  else view.unmount();
  await act(async () => resolve(Response.json({ items: { late: { status: 'available', kind: 'verified_place', provider: 'Google Maps',
    image_url: 'https://lh3.googleusercontent.com/late', source_url: 'https://www.google.com/maps/photo/fixture', authors: [] } } })));
  expect(readPhoto(endpoint, scope, 'late')).toBeUndefined();
  if (action === 'invalidate') expect(view.result.current.items.late).toBeUndefined();
});

it('hides cached neighbors when a missing slot reveals revoked media access', async () => {
  const endpoint = '/api/trips/revoked/media';
  const scope = { owner: 'alice', generation: photoGeneration('alice'), snapshot: 'revoked' };
  writePhoto(endpoint, scope, 'cached', { status: 'available', kind: 'verified_place', provider: 'Google Maps',
    image_url: 'https://lh3.googleusercontent.com/private', source_url: 'https://www.google.com/maps/photo/fixture', authors: [] });
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({}, { status: 401 })));
  const view = renderHook(() => usePlaceMedia(endpoint, ['cached', 'missing'], scope));
  await waitFor(() => expect(view.result.current.items.cached).toBeUndefined());
  expect(readPhoto(endpoint, scope, 'cached')).toBeUndefined();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('loads every slot in itinerary order and retains earlier photos when a later batch fails', async () => {
  const slots = Array.from({ length: 25 }, (_, i) => `activity:${i}`);
  const batches: string[][] = [];
  let release!: () => void;
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const requested = new URL(url, 'http://localhost').searchParams.getAll('slot');
    batches.push(requested);
    if (batches.length === 1) await new Promise<void>(resolve => { release = resolve; });
    if (batches.length === 3) return Response.json({}, { status: 503 });
    return Response.json({ items: Object.fromEntries(requested.map(slot => [slot, {
      status: 'available', image_url: `https://lh3.googleusercontent.com/${slot}`,
    }])) });
  }));
  const { result } = renderHook(() => usePlaceMedia('/api/trips/test/media', slots));
  await waitFor(() => expect(result.current.items[slots[0]]?.status).toBe('loading'));
  expect(result.current.items[slots[24]]).toBeUndefined();
  await act(async () => release());
  await waitFor(() => expect(result.current.items[slots[24]]?.status).toBe('unavailable'));
  expect(batches.map(batch => batch.length)).toEqual([12, 12, 1]);
  expect(batches.flat()).toEqual(slots);
  expect(Object.values(result.current.items).filter(item => item.status === 'available')).toHaveLength(24);
});

it('aborts an old page and does not copy its photos into another itinerary', async () => {
  let oldResolve!: (value: Response) => void;
  let oldSignal: AbortSignal | undefined;
  vi.stubGlobal('fetch', vi.fn((url: string, init: RequestInit) => {
    if (url.startsWith('/old')) {
      oldSignal = init.signal as AbortSignal;
      return new Promise<Response>(resolve => { oldResolve = resolve; });
    }
    return Promise.resolve(Response.json({ items: { new: { status: 'unavailable' } } }));
  }));
  const { result, rerender } = renderHook(({ endpoint, slots }) => usePlaceMedia(endpoint, slots), {
    initialProps: { endpoint: '/old', slots: ['old'] },
  });
  rerender({ endpoint: '/new', slots: ['new'] });
  await act(async () => oldResolve(Response.json({ items: { old: { status: 'available' } } })));
  await waitFor(() => expect(result.current.items.new?.status).toBe('unavailable'));
  expect(oldSignal?.aborted).toBe(true);
  expect(result.current.items.old).toBeUndefined();
});
