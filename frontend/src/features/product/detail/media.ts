import { createContext, useEffect, useState } from 'react';
import { requestJson } from '../../../shared/api/http';

export type DisplayMedia = {
  status: 'available' | 'unavailable';
  kind?: 'verified_place' | 'atmosphere';
  image_url?: string;
  provider?: string;
  authors?: { name: string; url?: string | null }[];
  alt?: string;
  source_url?: string;
};
export const PlaceMedia = createContext<Record<string, DisplayMedia>>({});

export function usePlaceMedia(endpoint?: string) {
  const [result, setResult] = useState<{ endpoint?: string; items: Record<string, DisplayMedia> }>({ items: {} });
  const [revision, refresh] = useState(0);
  useEffect(() => {
    if (!endpoint) return;
    const controller = new AbortController();
    requestJson<{ items: Record<string, DisplayMedia> }>(endpoint, { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) setResult({ endpoint, items: value.items }); })
      .catch(() => { if (!controller.signal.aborted) setResult({ endpoint, items: {} }); });
    return () => controller.abort();
  }, [endpoint, revision]);
  return { items: result.endpoint === endpoint ? result.items : {}, refresh: () => refresh(n => n + 1) };
}
