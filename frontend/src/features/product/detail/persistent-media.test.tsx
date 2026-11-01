import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { DestinationPhoto } from './MediaPhoto';
import { usePlaceMedia } from './media';
import { photoGeneration } from './photoSession';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

const version = (i: number) => `00000000-0000-4000-8000-${String(i).padStart(12, '0')}`;
const photo = (i: number) => ({ status: 'available', kind: 'verified_place', provider: 'Google Maps',
  image_url: `https://lh3.googleusercontent.com/image-${i}`, authors: [], cache_revision: version(i) });

it('refreshes a failed database image once using its version and leaves other slots alone', async () => {
  const addresses: URL[] = [];
  vi.stubGlobal('fetch', vi.fn(async (address: string) => {
    const url = new URL(address, 'http://localhost'); addresses.push(url);
    return Response.json({ items: addresses.length === 1 ? { left: photo(1), right: photo(2) } : { left: photo(addresses.length + 1) } });
  }));
  const { result } = renderHook(() => usePlaceMedia('/api/trips/one/media', ['left', 'right'], {
    owner: 'alice', generation: photoGeneration('alice'), snapshot: 'one',
  }));
  await waitFor(() => expect(result.current.items.left?.status).toBe('available'));
  expect(sessionStorage.getItem('dayloom.photos.session.v1')).toContain(version(1));
  act(() => result.current.imageFailed('left', result.current.items.left));
  await waitFor(() => expect(result.current.items.left?.image_url).toBe(photo(3).image_url));
  expect(addresses[1].searchParams.getAll('slot')).toEqual(['left']);
  expect(addresses[1].searchParams.get('refresh')).toBe(version(1));
  expect(result.current.items.right).toEqual(photo(2));
  act(() => result.current.imageFailed('left', result.current.items.left));
  expect(result.current.items.left.status).toBe('unavailable');
  expect(addresses).toHaveLength(2);
  act(() => result.current.refresh('left'));
  await waitFor(() => expect(addresses).toHaveLength(3));
  expect(addresses[2].searchParams.get('refresh')).toBe(version(3));
});

it('recovers an owned cover using its database version with no unbounded image retries', async () => {
  const addresses: URL[] = [];
  vi.stubGlobal('fetch', vi.fn(async (address: string) => {
    addresses.push(new URL(address, 'http://localhost'));
    return Response.json({ status: 'available', provider: 'Unsplash', kind: 'atmosphere',
      image_url: `https://images.unsplash.com/image-${addresses.length}`, alt: `Cover ${addresses.length}`,
      authors: [{ name: 'Author', url: 'https://unsplash.com/@author' }],
      source_url: 'https://unsplash.com/photos/source', cache_revision: version(addresses.length) });
  }));
  render(<DestinationPhoto owner="alice" endpoint="/api/trips/one/cover-media" destination="Sydney" label="Sydney" />);
  fireEvent.error(await screen.findByRole('img', { name: 'Cover 1' }));
  expect(addresses[0].pathname).toBe('/api/trips/one/cover-media');
  fireEvent.error(await screen.findByRole('img', { name: 'Cover 2' }));
  expect(addresses[1].searchParams.get('refresh')).toBe(version(1));
  expect(addresses).toHaveLength(2);
  expect(screen.getByRole('img')).toHaveAttribute('src', '/dayloom/nature.svg');
});
