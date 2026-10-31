import { HttpError, requestJson } from '../../../shared/api/http';
import type { DisplayMedia } from './media';
import { invalidatePhotos, photoFence, photoGeneration, photoKey, writePhoto, type PhotoScope } from './photoSession';

type Pending = { promise: Promise<DisplayMedia>; users: number; group: Group };
type Group = { controller: AbortController; entries: Pending[] };
const pending = new Map<string, Pending>();

/** Leases let StrictMode reattach before aborting an abandoned network request. */
export function acquirePhotos(endpoint: string, slots: string[], scope?: PhotoScope) {
  const fence = photoFence(endpoint, scope);
  const valid = () => photoFence(endpoint, scope) === fence && (!scope?.owner || scope.generation === photoGeneration(scope.owner));
  const keyFor = (slot: string) => `${fence}:${scope ? photoKey(endpoint, scope, slot) : JSON.stringify([endpoint, slot])}`;
  const missing = slots.filter(slot => !pending.has(keyFor(slot)));
  if (missing.length) {
    const group: Group = { controller: new AbortController(), entries: [] };
    const query = new URLSearchParams();
    missing.forEach(slot => query.append('slot', slot));
    const response = requestJson<{ items: Record<string, DisplayMedia> }>(
      `${endpoint}${endpoint.includes('?') ? '&' : '?'}${query}`, { signal: group.controller.signal },
    ).catch(error => {
      if (!group.controller.signal.aborted && valid() && scope && error instanceof HttpError) {
        if (error.status === 401) invalidatePhotos({ owner: scope.owner });
        else if (error.status === 403 || error.status === 404) invalidatePhotos({ owner: scope.owner, resource: endpoint });
      }
      throw error;
    });
    for (const slot of missing) {
      const key = keyFor(slot);
      const entry: Pending = { group, users: 0, promise: response.then(value => {
        const media = value?.items?.[slot] || { status: 'unavailable' as const };
        if (entry.users > 0 && !group.controller.signal.aborted && valid() && scope) writePhoto(endpoint, scope, slot, media);
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
    promise: Promise.all(leases.map(async ({ slot, entry }) => [slot, await entry.promise] as const)).then(Object.fromEntries),
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
