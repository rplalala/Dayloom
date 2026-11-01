import { useCallback, useRef, useState } from 'react';
import { createBrief, restoreBrief, type Brief } from './editor';
import type { BriefOrigin } from './session';

const storageKey = 'dayloom.expired-guest.brief.v1';
const blank = createBrief();
type GuestBrief = { scope: string; brief: Brief; origin: BriefOrigin; actionId: string | null; draftTitle: string; edited: boolean };

function read(): GuestBrief | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
    return value && typeof value.scope === 'string' && typeof value.edited === 'boolean'
      ? { ...value, brief: restoreBrief(value.brief), origin: 'restored', actionId: null, draftTitle: typeof value.draftTitle === 'string' ? value.draftTitle : '' }
      : null;
  } catch { return null; }
}

/** Public editing never mutates the expired account's quarantined recovery. */
export function useExpiredGuestBrief(scope: string) {
  const [saved, setSaved] = useState(read);
  const current = useRef(saved);
  const value = saved?.scope === scope ? saved : null;
  const update = useCallback((change: Partial<GuestBrief>) => {
    const previous = current.current?.scope === scope ? current.current : null;
    const next: GuestBrief = { scope, brief: blank, origin: 'new', actionId: null, draftTitle: '', edited: false, ...previous, ...change };
    current.current = next; setSaved(next);
    try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch { /* Memory remains editable. */ }
  }, [scope]);
  const clear = useCallback(() => {
    current.current = null; setSaved(null);
    try { sessionStorage.removeItem(storageKey); } catch { /* Memory is cleared. */ }
  }, []);
  const editBrief = useCallback((brief: Brief) => update({ brief, origin: 'edited', edited: true }), [update]);
  const replaceBrief = useCallback((brief: Brief, origin: 'draft' | 'replan' | 'restored') => update({ brief: restoreBrief(brief), origin, actionId: null, draftTitle: '', edited: true }), [update]);
  const newBrief = useCallback(() => update({ brief: createBrief(), origin: 'new', actionId: null, draftTitle: '', edited: true }), [update]);
  const initializeNewBrief = useCallback(async () => {}, []);
  const setDraftTitle = useCallback((draftTitle: string) => update({ draftTitle, edited: true }), [update]);
  const setActionId = useCallback((actionId: string | null) => update({ actionId }), [update]);
  const snapshot = () => current.current?.scope === scope ? current.current : null;
  return { value, snapshot, clear, editor: {
    brief: value?.brief || blank, briefOrigin: value?.origin || 'new' as BriefOrigin,
    defaultsApplied: false, draftRef: null, draftTitle: value?.draftTitle || '', actionId: value?.actionId || null,
    editBrief, replaceBrief, newBrief, initializeNewBrief, setDraftTitle, setActionId,
    setDraftRef: () => {},
  } };
}
