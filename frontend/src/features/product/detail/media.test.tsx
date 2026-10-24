import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { usePlaceMedia } from './media';
import { render, screen } from '@testing-library/react';
import { MediaPhoto } from './MediaPhoto';

afterEach(() => vi.unstubAllGlobals());

it('distinguishes queued, loading and unavailable photographs in the UI', () => {
  const { rerender } = render(<MediaPhoto label="A place" />);
  expect(screen.getByText('Photo pending')).toBeVisible();
  rerender(<MediaPhoto label="A place" media={{ status: 'loading' }} />);
  expect(screen.getByText('Loading photo…')).toBeVisible();
  rerender(<MediaPhoto label="A place" media={{ status: 'unavailable' }} />);
  expect(screen.queryByText('Loading photo…')).not.toBeInTheDocument();
  expect(screen.getByText('Illustration')).toBeVisible();
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
