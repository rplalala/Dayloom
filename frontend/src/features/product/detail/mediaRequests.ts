import { HttpError, requestJson } from '../../../shared/api/http';
import type { DisplayMedia } from './media';
import { invalidatePhotos, photoFence, photoGeneration, photoRequestKey, writePhoto, type PhotoScope } from './photoSession';

type Pending = { promise: Promise<DisplayMedia>; users: number; group: Group; fetchedAt: number };
type Group = { controller: AbortController; entries: Pending[] };
const pending = new Map<string, Pending>();

/** Leases let StrictMode reattach before aborting an abandoned network request. */
export function acquirePhotos(endpoint: string, slots: string[], scope?: PhotoScope, revision?: string) {
  return acquireMedia(endpoint, slots, scope, 'slots', revision);
}

export function acquireCover(endpoint: string, scope: PhotoScope, revision?: string) {
  const request = acquireMedia(endpoint, ['cover'], scope, 'cover', revision);
  return { promise: request.promise.then(items => items.cover), release: request.release };
}

function acquireMedia(endpoint: string, slots: string[], scope: PhotoScope | undefined, mode: 'slots' | 'cover', revision?: string) {
  const fence = photoFence(endpoint, scope);
  const valid = () => photoFence(endpoint, scope) === fence && (!scope?.owner || scope.generation === photoGeneration(scope.owner));
  const keyFor = (slot: string) => `${mode}:${fence}:${scope ? photoRequestKey(endpoint, scope, slot) : JSON.stringify([endpoint, slot])}:${revision || ''}`;
  const representatives = new Map<string, string>();
  for (const slot of slots) if (!pending.has(keyFor(slot)) && !representatives.has(keyFor(slot))) representatives.set(keyFor(slot), slot);
  const missing = [...representatives.values()];
  if (missing.length) {
    const group: Group = { controller: new AbortController(), entries: [] };
    const query = new URLSearchParams();
    missing.forEach(slot => query.append('slot', slot));
    if (revision) query.set('refresh', revision);
    const url = mode === 'cover' && !revision ? endpoint : `${endpoint}${endpoint.includes('?') ? '&' : '?'}${query}`;
    const response = requestJson<DisplayMedia | { items: Record<string, DisplayMedia> }>(
      url, { signal: group.controller.signal },
    ).catch(error => {
      if (!group.controller.signal.aborted && valid() && scope && error instanceof HttpError) {
        if (error.status === 401) invalidatePhotos({ owner: scope.owner });
        else if (error.status === 403 || error.status === 404) invalidatePhotos({ owner: scope.owner, resource: endpoint });
      }
      throw error;
    });
    for (const slot of missing) {
      const key = keyFor(slot);
      const entry: Pending = { group, users: 0, fetchedAt: 0, promise: response.then(value => {
        let media = (mode === 'cover' ? value as DisplayMedia : (value as { items?: Record<string, DisplayMedia> })?.items?.[slot]) || { status: 'unavailable' as const };
        if (mode === 'cover' && media.provider === 'Unsplash' && media.kind === 'atmosphere' && !media.theme) media = { ...media, theme: 'general' };
        entry.fetchedAt = Date.now();
        return media;
      }).catch(() => ({ status: 'unavailable' as const })).finally(() => {
        if (pending.get(key) === entry) pending.delete(key);
      }) };
      group.entries.push(entry);
      pending.set(key, entry);
    }
  }
  const leases = slots.map(slot => {
    const entry = pending.get(keyFor(slot))!;
    entry.users++;
    return { slot, entry };
  });
  let released = false;
  return {
    promise: Promise.all(leases.map(async ({ slot, entry }) => {
      const media = await entry.promise;
      if (entry.users > 0 && !entry.group.controller.signal.aborted && valid() && scope) writePhoto(endpoint, scope, slot, media, entry.fetchedAt);
      return [slot, media] as const;
    })).then(entries => Object.fromEntries(entries)),
    release: () => {
      if (released) return;
      released = true;
      leases.forEach(({ entry }) => { entry.users--; });
      queueMicrotask(() => {
        for (const { entry } of leases) {
          if (entry.group.entries.every(item => item.users === 0)) {
            entry.group.controller.abort();
            for (const [key, value] of pending) if (value.group === entry.group) pending.delete(key);
          }
        }
      });
    },
  };
}
