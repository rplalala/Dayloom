import type { DisplayMedia } from './media';
import { submissionGeneration } from '../taskClient';

export type PhotoScope = { owner: string | null; generation: string; snapshot: string;
  provider?: 'Google Maps' | 'Unsplash'; kind?: 'verified_place' | 'atmosphere';
  themes?: Record<string, NonNullable<DisplayMedia['theme']>>; width?: number; height?: number };
type Entry = { key: string; sharedKey?: string; owner: string | null; resource: string; fetchedAt: number; media: DisplayMedia };
const storageKey = 'dayloom.photos.session.v1';
const lifetime = 30 * 60 * 1000;
const maxBytes = 1024 * 1024;
const fences = new Map<string, number>();
const listeners = new Set<() => void>();

export function photoFence(resource: string, scope?: PhotoScope): number {
  const key = JSON.stringify([scope?.owner ?? null, resource]);
  if (!fences.has(key)) fences.set(key, 0);
  return fences.get(key)!;
}

export function subscribePhotos(listener: () => void): () => void {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function invalidatePhotos(filter: { owner?: string | null; resource?: string; privateOnly?: boolean } = {}) {
  const matches = (owner: string | null, resource: string) =>
    (!filter.privateOnly || owner !== null) && (filter.owner === undefined || owner === filter.owner) && (!filter.resource || resource === filter.resource);
  for (const [key, value] of fences) {
    const [owner, resource] = JSON.parse(key);
    if (matches(owner, resource)) fences.set(key, value + 1);
  }
  if (!save(entries().filter(entry => !matches(entry.owner, entry.resource)))) clearStorage();
  listeners.forEach(listener => listener());
}

export function photoGeneration(owner: string | null): string {
  if (!owner) return '';
  try {
    const active = JSON.parse(localStorage.getItem('dayloom.account.active') || 'null');
    return JSON.stringify([submissionGeneration(owner), active?.id === owner ? active.nonce : '']);
  } catch { return JSON.stringify([submissionGeneration(owner), '']); }
}

/** A change detector only; ownership is always checked by the detail endpoint. */
export function photoFingerprint(value: unknown): string {
  const text = JSON.stringify(value);
  let left = 2166136261;
  let right = 5381;
  for (let i = 0; i < text.length; i++) {
    left = Math.imul(left ^ text.charCodeAt(i), 16777619);
    right = Math.imul(right, 33) ^ text.charCodeAt(i);
  }
  return `${text.length}:${left >>> 0}:${right >>> 0}`;
}

function safeUrl(value: unknown, hosts: string[], subdomains = false): value is string {
  if (typeof value !== 'string' || value.length > 8192) return false;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password && !url.hash &&
      (!url.port || url.port === '443') && hosts.some(host => url.hostname === host || (subdomains && url.hostname.endsWith(`.${host}`)));
  } catch { return false; }
}

export function validPhoto(value: unknown): value is DisplayMedia {
  if (!value || typeof value !== 'object') return false;
  const media = value as DisplayMedia;
  if (media.status === 'available' && media.kind === 'atmosphere' && media.provider === 'Unsplash') {
    return ['meal', 'rest', 'explore', 'walk', 'general'].includes(media.theme || '') &&
      safeUrl(media.image_url, ['images.unsplash.com']) && safeUrl(media.source_url, ['unsplash.com']) &&
      Array.isArray(media.authors) && media.authors.length > 0 && media.authors.length <= 100 &&
      media.authors.every(author => author && typeof author.name === 'string' && author.name.trim().length > 0
        && author.name.length <= 2000 && safeUrl(author.url, ['unsplash.com'])) &&
      (media.alt === undefined || typeof media.alt === 'string' && media.alt.length <= 2000);
  }
  return media.status === 'available' && media.kind === 'verified_place' && media.provider === 'Google Maps' &&
    safeUrl(media.image_url, ['googleusercontent.com'], true) &&
    (media.source_url == null || safeUrl(media.source_url, ['www.google.com', 'maps.google.com'])) &&
    Array.isArray(media.authors) && media.authors.length <= 100 && media.authors.every(author =>
      author && typeof author.name === 'string' && author.name.length <= 2000 &&
      (author.url == null || safeUrl(author.url, ['www.google.com', 'maps.google.com']))) &&
    (media.alt === undefined || typeof media.alt === 'string' && media.alt.length <= 2000);
}

function entries(): Entry[] {
  try {
    const raw = sessionStorage.getItem(storageKey);
    if (!raw) return [];
    if (new Blob([raw]).size > maxBytes) { sessionStorage.removeItem(storageKey); return []; }
    const saved = JSON.parse(raw);
    if (saved?.version !== 1 || !Array.isArray(saved.entries) || saved.entries.length > 200) return [];
    const now = Date.now();
    return saved.entries.filter((entry: Entry) => entry && typeof entry.key === 'string' &&
      (entry.owner === null || typeof entry.owner === 'string') && typeof entry.resource === 'string' &&
      Number.isSafeInteger(entry.fetchedAt) && entry.fetchedAt > 0 && entry.fetchedAt <= now && now - entry.fetchedAt < lifetime && validPhoto(entry.media));
  } catch { return []; }
}

function save(values: Entry[]) {
  try {
    values.sort((a, b) => a.fetchedAt - b.fetchedAt);
    while (values.length > 200) values.shift();
    let serialized = JSON.stringify({ version: 1, entries: values });
    while (values.length && new Blob([serialized]).size > maxBytes) {
      values.shift();
      serialized = JSON.stringify({ version: 1, entries: values });
    }
    sessionStorage.setItem(storageKey, serialized);
    return true;
  } catch { return false; }
}

function clearStorage() {
  try { sessionStorage.removeItem(storageKey); } catch { /* In-memory fences still prevent reuse. */ }
}

export function photoKey(resource: string, scope: PhotoScope, slot: string): string {
  return JSON.stringify([scope.owner, scope.generation, resource, scope.snapshot,
    scope.width || 960, scope.height || 640, slot, scope.provider || 'Google Maps',
    scope.kind || 'verified_place', scope.provider === 'Unsplash' ? scope.themes?.[slot] || 'general' : null]);
}

export function photoRequestKey(resource: string, scope: PhotoScope, slot: string): string {
  const key = JSON.parse(photoKey(resource, scope, slot));
  if (scope.provider === 'Unsplash') key[6] = '@theme';
  return JSON.stringify(key);
}

function matchesScope(media: DisplayMedia, scope: PhotoScope, slot: string) {
  return media.provider === (scope.provider || 'Google Maps') && media.kind === (scope.kind || 'verified_place')
    && (scope.provider !== 'Unsplash' || media.theme === (scope.themes?.[slot] || 'general'));
}

export function readPhoto(resource: string, scope: PhotoScope, slot: string): DisplayMedia | undefined {
  if (scope.owner && scope.generation !== photoGeneration(scope.owner)) return undefined;
  const values = entries();
  const key = photoKey(resource, scope, slot);
  const sharedKey = scope.provider === 'Unsplash' ? photoRequestKey(resource, scope, slot) : undefined;
  const allowed = values.filter(entry => entry.owner === scope.owner && entry.resource === resource && matchesScope(entry.media, scope, slot));
  const entry = allowed.find(entry => entry.key === key) || (sharedKey && allowed.find(entry => entry.sharedKey === sharedKey));
  if (!entry) return undefined;
  if (entry.key !== key) save([...values.filter(value => value.key !== key), { ...entry, key }]);
  return entry.media;
}

export function writePhoto(resource: string, scope: PhotoScope, slot: string, media: DisplayMedia, fetchedAt = Date.now()) {
  if (!validPhoto(media) || !matchesScope(media, scope, slot)) return;
  const key = photoKey(resource, scope, slot);
  // Whitelist the display DTO; never persist extra provider or application fields.
  const photo: DisplayMedia = { status: 'available', kind: media.kind, provider: media.provider,
    image_url: media.image_url, source_url: media.source_url,
    authors: media.authors!.map(({ name, url }) => ({ name, ...(url && { url }) })),
    ...(media.theme && { theme: media.theme }),
    ...(media.alt && { alt: media.alt }) };
  const sharedKey = scope.provider === 'Unsplash' ? photoRequestKey(resource, scope, slot) : undefined;
  save([...entries().filter(entry => entry.key !== key), { key, ...(sharedKey && { sharedKey }), owner: scope.owner, resource, fetchedAt, media: photo }]);
}

export function evictPhoto(resource: string, scope: PhotoScope, slot: string) {
  if (!save(entries().filter(entry => entry.key !== photoKey(resource, scope, slot)))) clearStorage();
}
