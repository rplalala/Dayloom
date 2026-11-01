import { afterEach, expect, it, vi } from 'vitest';
import { evictPhoto, invalidatePhotos, photoGeneration, readPhoto, writePhoto, type PhotoScope } from './photoSession';

const resource = '/api/trips/owned/supporting-media?width=360&height=240';
const scope = (): PhotoScope => ({ owner: 'alice', generation: photoGeneration('alice'), snapshot: 'trip-v1',
  provider: 'Unsplash', kind: 'atmosphere', width: 360, height: 240, themes: { a: 'meal', b: 'meal' } });
const photo = { status: 'available' as const, kind: 'atmosphere' as const, provider: 'Unsplash', theme: 'meal' as const,
  image_url: 'https://images.unsplash.com/first?ixid=kept', source_url: 'https://unsplash.com/photos/first',
  authors: [{ name: 'Photographer', url: 'https://unsplash.com/@fixture' }] };

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.restoreAllMocks(); });

it('does not reuse theme-only photos acquired before destination-aware search', () => {
  writePhoto(resource, scope(), 'a', photo);
  const saved = JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!);
  for (const entry of saved.entries) {
    entry.key = JSON.stringify(JSON.parse(entry.key).slice(0, 10));
    if (entry.sharedKey) entry.sharedKey = JSON.stringify(JSON.parse(entry.sharedKey).slice(0, 10));
  }
  sessionStorage.setItem('dayloom.photos.session.v1', JSON.stringify(saved));
  expect(readPhoto(resource, scope(), 'a')).toBeUndefined();
  expect(readPhoto(resource, scope(), 'b')).toBeUndefined();
});

it('keeps per-slot theme metadata at its original acquisition time and refreshes independently', () => {
  const clock = vi.spyOn(Date, 'now').mockReturnValue(1800000000000);
  writePhoto(resource, scope(), 'a', photo);
  clock.mockReturnValue(1800000060000);
  expect(readPhoto(resource, scope(), 'b')).toBeUndefined();
  writePhoto(resource, scope(), 'b', photo, 1800000000000);
  const entries = JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!).entries;
  expect(entries.map((entry: { fetchedAt: number }) => entry.fetchedAt)).toEqual([1800000000000, 1800000000000]);
  evictPhoto(resource, scope(), 'a');
  writePhoto(resource, scope(), 'a', { ...photo, image_url: 'https://images.unsplash.com/refresh' });
  expect(readPhoto(resource, scope(), 'b')?.image_url).toBe(photo.image_url);
  expect(readPhoto(resource, scope(), 'a')?.image_url).toContain('/refresh');
});

it('keeps provider, theme, resource and owner boundaries independent', () => {
  writePhoto(resource, scope(), 'a', photo);
  expect(readPhoto(resource, { ...scope(), themes: { b: 'walk' } }, 'b')).toBeUndefined();
  expect(readPhoto(resource, { ...scope(), owner: 'bob' }, 'b')).toBeUndefined();
  expect(readPhoto('/api/trips/other/supporting-media', scope(), 'b')).toBeUndefined();
  writePhoto('/api/trips/owned/media', { ...scope(), provider: undefined, kind: undefined }, 'a', photo);
  expect(readPhoto('/api/trips/owned/media', { ...scope(), provider: undefined, kind: undefined }, 'a')).toBeUndefined();
});

it.each(['trips', 'previews'])('invalidates supporting metadata through the shared %s decision resource', kind => {
  const current = resource.replace('/trips/', `/${kind}/`);
  writePhoto(current, scope(), 'a', photo);
  invalidatePhotos({ owner: 'alice', resource: `/api/${kind}/owned/media` });
  expect(readPhoto(current, scope(), 'a')).toBeUndefined();
});
