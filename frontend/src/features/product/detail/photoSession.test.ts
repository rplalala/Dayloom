import { afterEach, expect, it, vi } from 'vitest';
import { invalidatePhotos, photoGeneration, readPhoto, writePhoto, type PhotoScope } from './photoSession';

const resource = '/api/trips/fixture/media';
const scope = (): PhotoScope => ({ owner: 'alice', generation: photoGeneration('alice'), snapshot: 'fixture-v1' });
const photo = { status: 'available' as const, kind: 'verified_place' as const, provider: 'Google Maps',
  image_url: 'https://lh3.googleusercontent.com/fixture', source_url: 'https://www.google.com/maps/photo/fixture',
  authors: [{ name: 'Fixture photographer', url: 'https://www.google.com/maps/contrib/123' }] };
afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.restoreAllMocks(); });

it('expires thirty minutes after acquisition without extending on reads or restored storage', () => {
  const clock = vi.spyOn(Date, 'now').mockReturnValue(1800000000000);
  writePhoto(resource, scope(), 'museum', photo);
  const saved = sessionStorage.getItem('dayloom.photos.session.v1')!;
  clock.mockReturnValue(1800001740000);
  expect(readPhoto(resource, scope(), 'museum')).toEqual(photo);
  sessionStorage.clear();
  sessionStorage.setItem('dayloom.photos.session.v1', saved);
  clock.mockReturnValue(1800001800000);
  expect(readPhoto(resource, scope(), 'museum')).toBeUndefined();
});

it.each([null, undefined])('reuses successful photos when the provider omits the optional source link (%s)', source => {
  writePhoto(resource, scope(), 'museum', { ...photo, source_url: source });
  expect(readPhoto(resource, scope(), 'museum')?.image_url).toBe(photo.image_url);
  expect(readPhoto(resource, scope(), 'museum')?.authors).toEqual(photo.authors);
});

it('separates account, generation, resource, snapshot and requested dimensions', () => {
  const original = scope();
  writePhoto(resource, original, 'museum', photo);
  expect(readPhoto(resource, { ...original, owner: 'bob' }, 'museum')).toBeUndefined();
  expect(readPhoto('/api/previews/fixture/media', original, 'museum')).toBeUndefined();
  expect(readPhoto(resource, { ...original, snapshot: 'v2' }, 'museum')).toBeUndefined();
  expect(readPhoto(resource + '?width=800', original, 'museum')).toBeUndefined();
  localStorage.setItem('dayloom.account.invalidation.alice', 'revoked');
  expect(readPhoto(resource, original, 'museum')).toBeUndefined();
  expect(readPhoto(resource, scope(), 'museum')).toBeUndefined();
});

it.each([
  { image_url: 'https://googleusercontent.com.evil.test/photo' },
  { image_url: 'https://user:password@lh3.googleusercontent.com/photo' },
  { image_url: 'https://lh3.googleusercontent.com:8443/photo' },
  { source_url: 'javascript:alert(1)' },
  { authors: [{ name: 'Unsafe author', url: 'https://evil.test/profile' }] },
  { authors: [{ url: 'https://www.google.com/maps/contrib/123' }] },
])('rejects unsafe or incomplete metadata %j', invalid => {
  writePhoto(resource, scope(), 'museum', { ...photo, ...invalid } as typeof photo);
  expect(readPhoto(resource, scope(), 'museum')).toBeUndefined();
});

it.each(['{broken', '{"version":2,"entries":[]}', '{"version":1,"entries":{}}'])('tolerates corrupt or unsupported storage %s', raw => {
  sessionStorage.setItem('dayloom.photos.session.v1', raw);
  expect(readPhoto(resource, scope(), 'museum')).toBeUndefined();
  writePhoto(resource, scope(), 'museum', photo);
  expect(readPhoto(resource, scope(), 'museum')).toEqual(photo);
});

it('rejects restored data with future timestamps or invalid metadata', () => {
  writePhoto(resource, scope(), 'museum', photo);
  const saved = JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1')!);
  saved.entries[0].fetchedAt = Date.now() + 60000;
  sessionStorage.setItem('dayloom.photos.session.v1', JSON.stringify(saved));
  expect(readPhoto(resource, scope(), 'museum')).toBeUndefined();
  saved.entries[0].fetchedAt = Date.now();
  saved.entries[0].media.image_url = 'http://lh3.googleusercontent.com/fixture';
  sessionStorage.setItem('dayloom.photos.session.v1', JSON.stringify(saved));
  expect(readPhoto(resource, scope(), 'museum')).toBeUndefined();
});

it('evicts oldest entries at the count and serialized byte limits', () => {
  for (let i = 0; i < 201; i++) writePhoto(resource, scope(), `slot:${i}`, photo);
  expect(readPhoto(resource, scope(), 'slot:0')).toBeUndefined();
  expect(readPhoto(resource, scope(), 'slot:200')).toEqual(photo);
  invalidatePhotos();
  const large = { ...photo, authors: Array.from({ length: 80 }, () => ({ name: 'X'.repeat(1900) })) };
  for (let i = 0; i < 10; i++) writePhoto(resource, scope(), `large:${i}`, large);
  expect(new Blob([sessionStorage.getItem('dayloom.photos.session.v1')!]).size).toBeLessThanOrEqual(1048576);
  expect(readPhoto(resource, scope(), 'large:0')).toBeUndefined();
  expect(readPhoto(resource, scope(), 'large:9')).toEqual(large);
});

it('tolerates storage denial/quota failure and stores only whitelisted display metadata', () => {
  writePhoto(resource, scope(), 'museum', { ...photo, csrf_token: 'not-for-storage', media_bindings: { private: 'place-id' } } as typeof photo);
  expect(sessionStorage.getItem('dayloom.photos.session.v1')).not.toContain('not-for-storage');
  expect(sessionStorage.getItem('dayloom.photos.session.v1')).not.toContain('media_bindings');
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('Quota exceeded', 'QuotaExceededError'); });
  expect(() => writePhoto(resource, scope(), 'other', photo)).not.toThrow();
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new DOMException('Access denied', 'SecurityError'); });
  expect(readPhoto(resource, scope(), 'museum')).toBeUndefined();
});

it('removes only the invalidated resource or private owner and retains independent guest photos', () => {
  const guest = { owner: null, generation: '', snapshot: 'public' };
  writePhoto(resource, scope(), 'museum', photo);
  writePhoto('/api/previews/other/media', scope(), 'museum', photo);
  writePhoto('/api/examples/public/media', guest, 'museum', photo);
  invalidatePhotos({ owner: 'alice', resource });
  expect(readPhoto(resource, scope(), 'museum')).toBeUndefined();
  expect(readPhoto('/api/previews/other/media', scope(), 'museum')).toEqual(photo);
  invalidatePhotos({ privateOnly: true });
  expect(readPhoto('/api/previews/other/media', scope(), 'museum')).toBeUndefined();
  expect(readPhoto('/api/examples/public/media', guest, 'museum')).toEqual(photo);
});
