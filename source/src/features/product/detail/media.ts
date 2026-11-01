import { createContext } from 'react';

export type DisplayMedia = {
  status: 'loading' | 'available' | 'unavailable';
  kind?: 'verified_place' | 'atmosphere' | 'illustration';
  theme?: 'meal' | 'rest' | 'explore' | 'walk' | 'general';
  fallback?: 'google_no_photos';
  image_url?: string;
  provider?: string;
  authors?: { name: string; url?: string | null }[];
  alt?: string;
  source_url?: string | null;
  license_url?: string | null;
  cache_revision?: string;
};
export const PlaceMedia = createContext<Record<string, DisplayMedia>>({});
export const PlaceMediaActions = createContext<{ imageFailed: (slot: string, media: DisplayMedia) => void; refresh: (slot: string) => void } | null>(null);

export const validPhoto = (media?: DisplayMedia): boolean => media?.status === 'available' && Boolean(media.image_url);
export const isPlaceFallback = (media?: DisplayMedia): boolean => media?.kind === 'atmosphere';
