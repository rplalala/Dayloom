import { act, renderHook, waitFor, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { usePlaceMedia, type DisplayMedia } from './media';
import { evictPhoto, invalidatePhotos, photoGeneration, readPhoto, writePhoto } from './photoSession';
import { TripDetail } from './TripDetail';
import type { ProductDetail } from './types';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

function fallback(identity: string): DisplayMedia {
  return { status: 'available', kind: 'atmosphere', theme: 'general', provider: 'Unsplash',
    fallback: 'google_no_photos', image_url: `https://images.unsplash.com/${identity}`,
    source_url: `https://unsplash.com/photos/${identity}`,
    authors: [{ name: 'Photographer', url: 'https://unsplash.com/@fixture' }],
  };
}

it('reuses each place fallback independently after remount without repeating either provider chain', async () => {
  const photos: Record<string, DisplayMedia> = { square: fallback('square'), cafe: fallback('cafe') };
  const fetcher = vi.fn(async () => Response.json({ items: photos }));
  vi.stubGlobal('fetch', fetcher);
  const scope = { owner: 'alice', generation: photoGeneration('alice'), snapshot: 'melbourne' };
  const first = renderHook(() => usePlaceMedia('/api/previews/melbourne/media', ['square', 'cafe'], scope));
  await waitFor(() => expect(first.result.current.items.cafe?.status).toBe('available'));
  first.unmount();
  const second = renderHook(() => usePlaceMedia('/api/previews/melbourne/media', ['square', 'cafe'], scope));
  await waitFor(() => expect(second.result.current.items.cafe?.status).toBe('available'));
  expect(second.result.current.items.square).toEqual(photos.square);
  expect(second.result.current.items.cafe).toEqual(photos.cafe);
  expect(fetcher).toHaveBeenCalledTimes(1);
  await act(async () => second.result.current.refresh('square'));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  expect(second.result.current.items.cafe).toEqual(photos.cafe);
});

it('isolates fallback scope, expiry and eviction without borrowing supporting-theme aliases', () => {
  const endpoint = '/api/previews/cache/media';
  const scope = { owner: 'alice', generation: photoGeneration('alice'), snapshot: 'cache' };
  const acquired = Date.now() - 1000;
  writePhoto(endpoint, scope, 'square', fallback('square'), acquired);
  writePhoto(endpoint, scope, 'cafe', fallback('cafe'), acquired);
  expect(readPhoto(endpoint, scope, 'missing')).toBeUndefined();
  expect(readPhoto(endpoint, { ...scope, owner: 'bob' }, 'square')).toBeUndefined();
  expect(readPhoto(endpoint, { ...scope, snapshot: 'changed' }, 'square')).toBeUndefined();
  expect(readPhoto(endpoint, { ...scope, provider: 'Unsplash', kind: 'atmosphere' }, 'square')).toBeUndefined();
  evictPhoto(endpoint, scope, 'square');
  expect(readPhoto(endpoint, scope, 'square')).toBeUndefined();
  expect(readPhoto(endpoint, scope, 'cafe')).toEqual(fallback('cafe'));
  const entries = JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!).entries;
  expect(entries).toHaveLength(1);
  expect(entries[0].fetchedAt).toBe(acquired);
  writePhoto(endpoint, scope, 'old', fallback('old'), Date.now() - 60 * 60 * 1000);
  expect(readPhoto(endpoint, scope, 'old')).toBeUndefined();
  invalidatePhotos({ owner: 'alice' });
  expect(readPhoto(endpoint, scope, 'cafe')).toBeUndefined();
});

it('rejects a delayed fallback after private-resource invalidation', async () => {
  let deliver!: (value: Response) => void;
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { deliver = resolve; })));
  const endpoint = '/api/trips/late/media';
  const scope = { owner: 'alice', generation: photoGeneration('alice'), snapshot: 'late' };
  const view = renderHook(() => usePlaceMedia(endpoint, ['square'], scope));
  act(() => invalidatePhotos({ owner: 'alice', resource: endpoint }));
  await act(async () => deliver(Response.json({ items: { square: fallback('square') } })));
  expect(view.result.current.items.square).toBeUndefined();
  expect(readPhoto(endpoint, scope, 'square')).toBeUndefined();
});

it('labels a main-visit fallback as atmosphere in Details without pretending it is a place photograph', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => Response.json(String(url).includes('/media?')
    ? { items: { 'activity:square': fallback('square') } } : { status: 'unavailable' })));
  const detail: ProductDetail = { schema_version: 'product_detail_1', id: 'owned', title: 'Melbourne', destination: 'Melbourne',
    provenance: 'generated', trust: 'generated_projection', request: null, nearby: [], transfers: [],
    days: [{ date: '2026-11-01', activities: [{ activity_id: 'square', title: 'Federation Square', place_name: 'Federation Square',
      activity_kind: 'main_poi', time_use: 'scheduled', start_time: '2026-11-01T10:00:00', end_time: '2026-11-01T11:00:00' }] }],
  };
  render(<MemoryRouter><TripDetail detail={detail} mediaEndpoint="/api/trips/owned/media" mediaOwner="alice" /></MemoryRouter>);
  const card = screen.getByRole('group', { name: 'Federation Square on 2026-11-01' });
  expect(await within(card).findByRole('img', { name: 'Federation Square' })).toHaveAttribute('src', 'https://images.unsplash.com/square');
  expect(within(card).queryByText('Atmosphere photo')).not.toBeInTheDocument();
  await userEvent.click(within(card).getByRole('button', { name: /Details/ }));
  const dialog = screen.getByRole('dialog', { name: 'Federation Square' });
  expect(within(dialog).getByText('Atmosphere photo')).toBeVisible();
  expect(within(dialog).getByText('Unsplash')).toBeVisible();
  expect(within(dialog).queryByText('Google Maps')).not.toBeInTheDocument();
  expect(within(dialog).getByRole('link', { name: 'Photographer' })).toHaveAttribute('href', 'https://unsplash.com/@fixture');
});
