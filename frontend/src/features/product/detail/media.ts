import { createContext, useEffect, useRef, useState } from 'react';
import { evictPhoto, photoFence, photoGeneration, readPhoto, subscribePhotos, type PhotoScope } from './photoSession';
import { acquirePhotos } from './mediaRequests';

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
export const PlaceMediaActions = createContext<{
  imageFailed: (slot: string, media: DisplayMedia) => void;
  refresh: (slot: string) => void;
} | null>(null);

export function usePlaceMedia(endpoint?: string, slots: readonly string[] = [], scope?: PhotoScope) {
  const [result, setResult] = useState<{ context: string; fence: number; items: Record<string, DisplayMedia> }>({ context: '', fence: 0, items: {} });
  const controls = useRef<{ refresh: (slot: string) => void; imageFailed: (slot: string, media: DisplayMedia) => void } | null>(null);
  const slotKey = JSON.stringify([...new Set(slots)]);
  const scopeKey = scope ? JSON.stringify(scope) : '';
  const context = JSON.stringify([endpoint, scopeKey, slotKey]);
  useEffect(() => {
    if (!endpoint) return;
    let active = true;
    const releases = new Set<() => void>();
    const ordered: string[] = JSON.parse(slotKey);
    const cacheScope: PhotoScope | undefined = scopeKey ? JSON.parse(scopeKey) : undefined;
    const fence = photoFence(endpoint, cacheScope);
    const valid = () => active && photoFence(endpoint, cacheScope) === fence &&
      (!cacheScope?.owner || cacheScope.generation === photoGeneration(cacheScope.owner));
    let displayed: Record<string, DisplayMedia> = {};
    const cachedSlots = new Set<string>();
    const attempted = new Set<string>();
    const merge = (incoming: Record<string, DisplayMedia>) => {
      if (!valid()) return;
      displayed = { ...displayed, ...incoming };
      setResult({ context, fence, items: displayed });
    };
    const unsubscribe = subscribePhotos(() => {
      if (valid()) return;
      active = false;
      releases.forEach(release => release());
      setResult({ context: '', fence, items: {} });
    });
    const fetchSlots = async (batch: string[]) => {
      if (!valid()) return;
      merge(Object.fromEntries(batch.map(slot => [slot, { status: 'loading' }])));
      const request = acquirePhotos(endpoint, batch, cacheScope);
      releases.add(request.release);
      const incoming = await request.promise;
      request.release();
      releases.delete(request.release);
      merge(incoming);
    };
    const refresh = (slot: string) => {
      if (!ordered.includes(slot) || !valid()) return;
      if (cacheScope) evictPhoto(endpoint, cacheScope, slot);
      cachedSlots.delete(slot);
      void fetchSlots([slot]);
    };
    controls.current = { refresh, imageFailed: (slot, media) => {
      if (!valid() || displayed[slot] !== media || media.status !== 'available') return;
      if (cacheScope) evictPhoto(endpoint, cacheScope, slot);
      merge({ [slot]: { status: 'unavailable' } });
      if (cachedSlots.has(slot) && !attempted.has(slot)) {
        attempted.add(slot);
        refresh(slot);
      }
    } };
    const load = async () => {
      const cached = Object.fromEntries(ordered.flatMap(slot => {
        const photo = cacheScope && readPhoto(endpoint, cacheScope, slot);
        if (photo) cachedSlots.add(slot);
        return photo ? [[slot, photo]] : [];
      }));
      merge(cached);
      const missing = ordered.filter(slot => !cached[slot]);
      for (let offset = 0; offset < missing.length && valid(); offset += 12) {
        const batch = missing.slice(offset, offset + 12);
        await fetchSlots(batch);
      }
    };
    void load();
    return () => { active = false; releases.forEach(release => release()); unsubscribe(); controls.current = null; };
  }, [endpoint, slotKey, scopeKey, context]);
  const items: Record<string, DisplayMedia> = !endpoint
    ? Object.fromEntries(slots.map(slot => [slot, { status: 'unavailable' }]))
    : result.context === context && result.fence === photoFence(endpoint, scope) && (!scope?.owner || scope.generation === photoGeneration(scope.owner)) ? result.items : {};
  return { items, refresh: (slot: string) => controls.current?.refresh(slot),
    imageFailed: (slot: string, media: DisplayMedia) => controls.current?.imageFailed(slot, media) };
}
