import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../../app/router';
import { CuratedPhoto, DestinationPhoto } from './MediaPhoto';
import { StrictMode } from 'react';
import { invalidatePhotos } from './photoSession';

const cover = (city: string) => ({ status: 'available', provider: 'Unsplash', kind: 'atmosphere',
  image_url: `https://images.unsplash.com/${city}`, alt: `${city} atmosphere`,
  authors: [{ name: 'Photographer', url: 'https://unsplash.com/@fixture' }],
  source_url: `https://unsplash.com/photos/${city}` });

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it('reuses successful cover metadata after remount without extending its acquisition time', async () => {
  const fetcher = vi.fn(async () => Response.json(cover('Melbourne')));
  vi.stubGlobal('fetch', fetcher);
  const first = render(<DestinationPhoto destination="Melbourne" label="Melbourne atmosphere" />);
  await screen.findByRole('button', { name: 'Photo credits' });
  const acquired = sessionStorage.getItem('dayloom.photos.session.v1');
  first.unmount();
  render(<DestinationPhoto destination="Melbourne" label="Melbourne atmosphere" />);
  await screen.findByRole('button', { name: 'Photo credits' });
  expect(fetcher).toHaveBeenCalledOnce();
  expect(sessionStorage.getItem('dayloom.photos.session.v1')).toBe(acquired);
});

it('expires cover metadata one hour after acquisition without extending reads', async () => {
  const clock = vi.spyOn(Date, 'now').mockReturnValue(1800000000000);
  const fetcher = vi.fn(async () => Response.json(cover('Melbourne')));
  vi.stubGlobal('fetch', fetcher);
  const first = render(<DestinationPhoto destination="Melbourne" label="Melbourne atmosphere" />);
  await screen.findByRole('button', { name: 'Photo credits' });
  first.unmount();
  clock.mockReturnValue(1800003540000);
  const second = render(<DestinationPhoto destination="Melbourne" label="Melbourne atmosphere" />);
  await screen.findByRole('button', { name: 'Photo credits' });
  expect(fetcher).toHaveBeenCalledOnce();
  expect(JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!).entries[0].fetchedAt).toBe(1800000000000);
  second.unmount();
  clock.mockReturnValue(1800003600000);
  render(<DestinationPhoto destination="Melbourne" label="Melbourne atmosphere" />);
  await screen.findByRole('button', { name: 'Photo credits' });
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it('merges concurrent same-city covers through StrictMode remounts', async () => {
  const fetcher = vi.fn(async () => Response.json(cover('Melbourne')));
  vi.stubGlobal('fetch', fetcher);
  render(<StrictMode><DestinationPhoto owner="alice" destination="Melbourne" label="Card" /><DestinationPhoto owner="alice" destination="Melbourne" label="Hero" /></StrictMode>);
  await waitFor(() => expect(screen.getAllByRole('button', { name: 'Photo credits' })).toHaveLength(2));
  expect(fetcher).toHaveBeenCalledOnce();
  expect(JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!).entries).toHaveLength(1);
});

it.each(['sydney', 'london'] as const)('also caches the fixed %s cover with its provider metadata', async image => {
  const metadata = image === 'london' ? { status: 'available', provider: 'Google Maps', kind: 'verified_place',
    image_url: 'https://lh3.googleusercontent.com/london', authors: [] } : cover('Sydney');
  const fetcher = vi.fn(async () => Response.json(metadata));
  vi.stubGlobal('fetch', fetcher);
  const first = render(<CuratedPhoto image={image} label="Cover" />);
  await screen.findByRole('button', { name: 'Photo credits' });
  first.unmount();
  render(<CuratedPhoto image={image} label="Cover" />);
  await screen.findByRole('button', { name: 'Photo credits' });
  expect(fetcher).toHaveBeenCalledOnce();
});

it('still displays a cover when browser storage is unavailable', async () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('Quota exceeded', 'QuotaExceededError'); });
  const fetcher = vi.fn(async () => Response.json(cover('Melbourne')));
  vi.stubGlobal('fetch', fetcher);
  const first = render(<DestinationPhoto destination="Melbourne" label="City" />);
  await screen.findByRole('img', { name: 'Melbourne atmosphere' });
  first.unmount();
  render(<DestinationPhoto destination="Melbourne" label="City" />);
  await screen.findByRole('img', { name: 'Melbourne atmosphere' });
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it('isolates owner and guest cover cache entries for the same destination', async () => {
  const fetcher = vi.fn(async () => Response.json(cover('Melbourne')));
  vi.stubGlobal('fetch', fetcher);
  const view = render(<DestinationPhoto owner="alice" destination="Melbourne" label="City" />);
  await screen.findByRole('button', { name: 'Photo credits' });
  view.rerender(<DestinationPhoto owner="bob" destination="Melbourne" label="City" />);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  await screen.findByRole('button', { name: 'Photo credits' });
  view.rerender(<DestinationPhoto destination="Melbourne" label="City" />);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
  await screen.findByRole('button', { name: 'Photo credits' });
  expect(JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!).entries.map((entry: { owner: string | null }) => entry.owner)).toEqual(['alice', 'bob', null]);
  act(() => invalidatePhotos({ privateOnly: true }));
  expect(JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!).entries.map((entry: { owner: string | null }) => entry.owner)).toEqual([null]);
});

it('rejects a delayed private cover after account invalidation', async () => {
  let deliver!: (response: Response) => void;
  const fetcher = vi.fn(() => new Promise<Response>(resolve => { deliver = resolve; }));
  vi.stubGlobal('fetch', fetcher);
  render(<DestinationPhoto owner="alice" destination="Melbourne" label="City" />);
  act(() => invalidatePhotos({ owner: 'alice' }));
  await act(async () => deliver(Response.json(cover('Melbourne'))));
  expect(screen.getByRole('img')).toHaveAttribute('src', '/dayloom/nature.svg');
  expect(sessionStorage.getItem('dayloom.photos.session.v1')).not.toContain('images.unsplash.com');
  expect(fetcher).toHaveBeenCalledOnce();
});

it('evicts a failed cached cover and attempts image recovery only once per display', async () => {
  let acquisitions = 0;
  const fetcher = vi.fn(async () => Response.json(cover(`image-${++acquisitions}`)));
  vi.stubGlobal('fetch', fetcher);
  const first = render(<DestinationPhoto destination="Melbourne" label="City" />);
  await screen.findByRole('img', { name: 'image-1 atmosphere' });
  first.unmount();
  render(<DestinationPhoto destination="Melbourne" label="City" />);
  fireEvent.error(await screen.findByRole('img', { name: 'image-1 atmosphere' }));
  fireEvent.error(await screen.findByRole('img', { name: 'image-2 atmosphere' }));
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(screen.getByRole('img')).toHaveAttribute('src', '/dayloom/nature.svg');
  expect(sessionStorage.getItem('dayloom.photos.session.v1')).not.toContain('images.unsplash.com');
});

it('loads distinct destination queries for Melbourne and New York collection covers', async () => {
  let failedMelbourne = false;
  const fetcher = vi.fn(async (address: string) => {
    if (address === '/api/auth/current') return Response.json({ id: 'alice', display_name: 'Alice', csrf_token: 'token' });
    if (address.startsWith('/api/library?')) return Response.json({ total: 2, items: ['Melbourne', 'New York'].map(city => ({
      id: city === 'Melbourne' ? 'melbourne' : 'new-york', kind: 'saved', title: `${city} journey`, destination: city, revision: 1,
    })) });
    if (address.includes('/cover-media?')) {
      const destination = new URL(address, 'http://localhost').searchParams.get('destination')!;
      return Response.json(failedMelbourne && destination === 'Melbourne' ? { status: 'unavailable' } : cover(destination));
    }
    return Response.json([]);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/trips'] })} />);
  expect(await screen.findByRole('img', { name: 'Melbourne atmosphere' })).toHaveAttribute('src', 'https://images.unsplash.com/Melbourne');
  expect(await screen.findByRole('img', { name: 'New York atmosphere' })).toHaveAttribute('src', 'https://images.unsplash.com/New York');
  expect(fetcher.mock.calls.map(([address]) => address)).toEqual(expect.arrayContaining([
    '/api/trips/melbourne/cover-media?destination=Melbourne', '/api/trips/new-york/cover-media?destination=New%20York',
  ]));
  expect(fetcher.mock.calls.some(([address]) => address.includes('/curated/'))).toBe(false);
  failedMelbourne = true;
  fireEvent.error(screen.getByRole('img', { name: 'Melbourne atmosphere' }));
  await waitFor(() => expect(screen.getByRole('img', { name: 'Melbourne destination atmosphere · illustration' })).toHaveAttribute('src', '/dayloom/nature.svg'));
  expect(screen.getByRole('img', { name: 'New York atmosphere' })).toHaveAttribute('src', 'https://images.unsplash.com/New York');
});

it.each(['unavailable', 'request-error'])('shows an illustration after %s without a fixed-photo request', async failure => {
  const fetcher = vi.fn(async () => {
    if (failure === 'request-error') throw new Error('Controlled failure');
    return Response.json({ status: 'unavailable' });
  });
  vi.stubGlobal('fetch', fetcher);
  const first = render(<DestinationPhoto destination="New York" label="New York atmosphere" />);
  await waitFor(() => expect(fetcher).toHaveBeenCalledOnce());
  expect(screen.getByRole('img')).toHaveAttribute('src', '/dayloom/nature.svg');
  expect(screen.queryByRole('button', { name: 'Photo credits' })).not.toBeInTheDocument();
  first.unmount();
  render(<DestinationPhoto destination="New York" label="New York atmosphere" />);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
});

it('does not query a missing destination', () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  render(<DestinationPhoto destination="   " label="Destination atmosphere" />);
  expect(fetcher).not.toHaveBeenCalled();
  expect(screen.getByRole('img')).toHaveAttribute('src', '/dayloom/nature.svg');
});

it('preserves a complete Unicode character at the destination query boundary', async () => {
  const destination = 'x'.repeat(119) + '\u{1F30D}' + 'ignored suffix';
  const fetcher = vi.fn<(address: string) => Promise<Response>>(async () => Response.json({ status: 'unavailable' }));
  vi.stubGlobal('fetch', fetcher);
  render(<DestinationPhoto destination={destination} label="Destination atmosphere" />);
  await waitFor(() => expect(fetcher).toHaveBeenCalledOnce());
  const query = new URL(fetcher.mock.calls[0][0], 'http://localhost').searchParams.get('destination');
  expect(query).toBe('x'.repeat(119) + '\u{1F30D}');
  expect(screen.getByRole('img')).toHaveAttribute('src', '/dayloom/nature.svg');
});

it('ignores a late cover response when the destination changes', async () => {
  const responses = new Map<string, (response: Response) => void>();
  vi.stubGlobal('fetch', vi.fn((address: string) => new Promise<Response>(resolve => {
    responses.set(new URL(address, 'http://localhost').searchParams.get('destination')!, resolve);
  })));
  const view = render(<DestinationPhoto destination="Melbourne" label="Melbourne atmosphere" />);
  view.rerender(<DestinationPhoto destination="New York" label="New York atmosphere" />);
  await act(async () => responses.get('New York')!(Response.json(cover('New York'))));
  expect(screen.getByRole('img')).toHaveAttribute('src', 'https://images.unsplash.com/New York');
  await act(async () => responses.get('Melbourne')!(Response.json(cover('Melbourne'))));
  expect(screen.getByRole('img')).toHaveAttribute('src', 'https://images.unsplash.com/New York');
});
