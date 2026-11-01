import catalog from '../../../../../backend/app/product/example_media.json';
import type { DisplayMedia } from './media';

type Example = { cover: string; slots: Record<string, string | null> };
const examples: Record<string, Example> = catalog.examples;
const assets: Record<string, { image_url: string; provider: string; authors: { name: string; url: string }[]; source_url: string; license_url: string }> = catalog.assets;

function photo(asset?: string | null): DisplayMedia {
  const entry = asset ? assets[asset] : undefined;
  return entry ? { status: 'available', kind: 'verified_place', image_url: entry.image_url,
    provider: entry.provider, authors: entry.authors, source_url: entry.source_url,
    license_url: entry.license_url } : { status: 'unavailable' };
}

export function exampleCover(id: string) {
  return photo(examples[id]?.cover);
}

export function examplePhotos(id: string) {
  return Object.fromEntries(Object.entries(examples[id]?.slots || {}).map(([slot, asset]) => [slot, photo(asset)]));
}
