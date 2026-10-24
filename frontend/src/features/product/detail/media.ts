import { createContext, useEffect, useState } from 'react';
import { requestJson } from '../../../shared/api/http';

export type DisplayMedia = {
  status: 'loading' | 'available' | 'unavailable';
  kind?: 'verified_place' | 'atmosphere';
  image_url?: string;
  provider?: string;
  authors?: { name: string; url?: string | null }[];
  alt?: string;
  source_url?: string;
};
export const PlaceMedia = createContext<Record<string, DisplayMedia>>({});

export function usePlaceMedia(endpoint?: string, slots: readonly string[] = []) {
  const [result, setResult] = useState<{ endpoint?: string; items: Record<string, DisplayMedia> }>({ items: {} });
  const [revision, refresh] = useState(0);
  const slotKey = JSON.stringify([...new Set(slots)]);
  useEffect(() => {
    if (!endpoint) return;
    const controller = new AbortController();
    const ordered: string[] = JSON.parse(slotKey);
    const merge = (incoming: Record<string, DisplayMedia>) => setResult(previous => {
      if (controller.signal.aborted) return previous;
      const items = previous.endpoint === endpoint ? { ...previous.items } : {};
      for (const [slot, item] of Object.entries(incoming)) {
        if (item.status === 'available' || items[slot]?.status !== 'available') items[slot] = item;
      }
      return { endpoint, items };
    });
    const load = async () => {
      for (let offset = 0; offset < ordered.length && !controller.signal.aborted; offset += 12) {
        const batch = ordered.slice(offset, offset + 12);
        merge(Object.fromEntries(batch.map(slot => [slot, { status: 'loading' }])));
        const query = new URLSearchParams();
        batch.forEach(slot => query.append('slot', slot));
        try {
          const value = await requestJson<{ items: Record<string, DisplayMedia> }>(
            `${endpoint}${endpoint.includes('?') ? '&' : '?'}${query}`, { signal: controller.signal },
          );
          merge(Object.fromEntries(batch.map(slot => [slot, value.items?.[slot] || { status: 'unavailable' }])));
        } catch {
          merge(Object.fromEntries(batch.map(slot => [slot, { status: 'unavailable' }])));
        }
      }
    };
    void load();
    return () => controller.abort();
  }, [endpoint, revision, slotKey]);
  const items: Record<string, DisplayMedia> = !endpoint
    ? Object.fromEntries(slots.map(slot => [slot, { status: 'unavailable' }]))
    : result.endpoint === endpoint ? result.items : {};
  return { items, refresh: () => refresh(n => n + 1) };
}
