import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { usePlaceMedia } from './media';
import { invalidatePhotos, photoGeneration, type PhotoScope } from './photoSession';

const endpoint = '/api/trips/owned/supporting-media';
const slots = Array.from({ length: 14 }, (_, i) => `activity:${i}`);
const scope = (): PhotoScope => ({ owner: 'alice', generation: photoGeneration('alice'), snapshot: 'v1',
  provider: 'Unsplash', kind: 'atmosphere', themes: Object.fromEntries(slots.map(slot => [slot, 'meal'])) });
const photo = (id: number) => ({ status: 'available', kind: 'atmosphere', provider: 'Unsplash', theme: 'meal',
  image_url: `https://images.unsplash.com/${id}?ixid=kept`, source_url: 'https://unsplash.com/photos/first',
  authors: [{ name: 'Photographer', url: 'https://unsplash.com/@fixture' }] });

function Photos({ chosen = slots }: { chosen?: string[] }) {
  const media = usePlaceMedia(endpoint, chosen, scope());
  return <><output aria-label={chosen[0]}>{JSON.stringify(media.items)}</output>
    <button onClick={() => media.refresh(chosen[0])}>Refresh {chosen[0]}</button></>;
}

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it('merges same-theme lookups across page batches and leaves neighbors unchanged on refresh', async () => {
  let calls = 0;
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const requested = new URL(String(url), 'http://localhost').searchParams.getAll('slot');
    calls++;
    return new Response(JSON.stringify({ items: Object.fromEntries(requested.map(slot => [slot, photo(calls)])) }));
  }));
  render(<Photos />);
  await waitFor(() => expect(JSON.parse(screen.getByRole('status', { name: slots[0] }).textContent!)[slots[13]]?.status).toBe('available'));
  expect(calls).toBe(1);
  const before = JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!).entries;
  fireEvent.click(screen.getByRole('button', { name: `Refresh ${slots[0]}` }));
  await waitFor(() => expect(calls).toBe(2));
  await waitFor(() => expect(JSON.parse(screen.getByRole('status', { name: slots[0] }).textContent!)[slots[0]]?.image_url).toContain('/2?'));
  const after = JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!).entries;
  expect(after.filter((entry: { key: string }) => JSON.parse(entry.key)[6] !== slots[0])).toEqual(before.filter((entry: { key: string }) => JSON.parse(entry.key)[6] !== slots[0]));
});

it.each(['owner', 'resource'])('merges concurrent subscribers and rejects late writes after %s invalidation', async kind => {
  let resolve!: (response: Response) => void;
  const fetch = vi.fn(() => new Promise<Response>(done => { resolve = done; }));
  vi.stubGlobal('fetch', fetch);
  render(<><Photos chosen={[slots[0]]} /><Photos chosen={[slots[1]]} /></>);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  invalidatePhotos({ owner: 'alice', ...(kind === 'resource' && { resource: '/api/trips/owned/media' }) });
  resolve(new Response(JSON.stringify({ items: { [slots[0]]: photo(1) } })));
  await waitFor(() => expect(JSON.parse(screen.getByRole('status', { name: slots[1] }).textContent!)).toEqual({}));
  expect(sessionStorage.getItem('dayloom.photos.session.v1')).not.toContain('images.unsplash.com');
});
