import { submissionGeneration } from './taskClient';

export type CopyKind = 'copied' | 'example';
export type CopyIntent = {
  owner: string | null;
  generation: string;
  kind: CopyKind;
  source: string;
  title?: string;
  key: string | null;
  uncertain: boolean;
  resolved?: boolean;
};
const storageKey = 'dayloom.copy.intent.v1';
export const copyIntentEvent = 'dayloom-copy-intent';

function stored(): CopyIntent[] {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
    // Preserve identities written by the original single-intent client.
    const entries: unknown[] = Array.isArray(value) ? value : value ? [value] : [];
    return entries.filter((entry): entry is CopyIntent => {
      if (!entry || typeof entry !== 'object') return false;
      const saved = entry as Partial<CopyIntent>;
      return (saved.owner === null || typeof saved.owner === 'string') &&
        typeof saved.generation === 'string' &&
        (saved.kind === 'copied' || saved.kind === 'example') &&
        typeof saved.source === 'string' &&
        (saved.title === undefined || typeof saved.title === 'string') &&
        (saved.key === null || typeof saved.key === 'string');
    });
  } catch { return []; }
}

export function ownerCopyIntents(owner: string): CopyIntent[] {
  return stored().filter(saved => saved.owner === owner && saved.generation === submissionGeneration(owner));
}

export function forgetOwnerCopyIntents(owner: string) {
  try {
    const remaining = stored().filter(saved => saved.owner !== owner);
    if (remaining.length) sessionStorage.setItem(storageKey, JSON.stringify(remaining));
    else sessionStorage.removeItem(storageKey);
    window.dispatchEvent(new Event(copyIntentEvent));
  } catch { /* Owner generation still fences unavailable recovery storage. */ }
}

export function restoreCopyIntent(owner: string | null, kind: CopyKind, source: string, title?: string): CopyIntent {
  const saved = stored().find(item => item.kind === kind && item.source === source &&
    (item.owner === null || item.owner === owner) &&
    (!item.owner || item.generation === submissionGeneration(item.owner)));
  return saved ? { ...saved, uncertain: Boolean(saved.key) } :
    { owner, generation: owner ? submissionGeneration(owner) : '', kind, source, title, key: null, uncertain: false };
}

export function rememberCopyIntent(next: CopyIntent) {
  try {
    const other = stored().filter(saved => !(saved.kind === next.kind && saved.source === next.source &&
      (saved.owner === next.owner || saved.owner === null)));
    sessionStorage.setItem(storageKey, JSON.stringify([...other, next]));
    window.dispatchEvent(new Event(copyIntentEvent));
  } catch { /* Explicit actions still work when optional storage is unavailable. */ }
}
