import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { ExampleCards } from './ExampleCards';
import { SessionProvider } from '../session';
import { DestinationPhoto } from './MediaPhoto';

const cover = (city: string) => ({ status: 'available', provider: 'Unsplash', kind: 'atmosphere',
  image_url: `https://images.unsplash.com/${city}`, alt: `${city} atmosphere`,
  authors: [{ name: 'Photographer', url: 'https://unsplash.com/@fixture' }],
  source_url: `https://unsplash.com/photos/${city}` });

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it('loads distinct destination queries for Melbourne and New York collection covers', async () => {
  const fetcher = vi.fn(async (address: string) => {
    if (address === '/api/auth/current') return Response.json({}, { status: 401 });
    if (address === '/api/examples') return Response.json(['Melbourne', 'New York'].map(city => ({
      id: city, title: `${city} journey`, destination: city, day_count: 2,
    })));
    const destination = new URL(address, 'http://localhost').searchParams.get('destination');
    return Response.json(destination ? cover(destination) : { status: 'unavailable' });
  });
  vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter><SessionProvider><ExampleCards /></SessionProvider></MemoryRouter>);
  expect(await screen.findByRole('img', { name: 'Melbourne atmosphere' })).toHaveAttribute('src', 'https://images.unsplash.com/Melbourne');
  expect(await screen.findByRole('img', { name: 'New York atmosphere' })).toHaveAttribute('src', 'https://images.unsplash.com/New York');
  expect(fetcher.mock.calls.map(([address]) => address)).toEqual(expect.arrayContaining([
    '/api/media/destination?destination=Melbourne', '/api/media/destination?destination=New%20York',
  ]));
  expect(fetcher.mock.calls.some(([address]) => address.includes('/curated/'))).toBe(false);
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
  render(<DestinationPhoto destination="New York" label="New York atmosphere" />);
  await waitFor(() => expect(fetcher).toHaveBeenCalledOnce());
  expect(screen.getByRole('img')).toHaveAttribute('src', '/dayloom/nature.svg');
  expect(screen.queryByRole('button', { name: 'Photo credits' })).not.toBeInTheDocument();
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
