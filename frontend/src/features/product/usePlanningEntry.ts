import type { MouseEvent } from 'react';
import { createBrief, type Brief } from './editor';
import { useSession } from './session';

/** An explicit planning entry can reopen defaults without replacing existing work. */
export function usePlanningEntry() {
  const session = useSession();
  return (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.defaultPrevented) return;
    if (!session.account || session.status !== 'authenticated' || session.draftRef || session.draftTitle || session.actionId) return;
    const empty = createBrief();
    const isEmpty = Object.entries(empty).every(([key, value]) => {
      const current = session.brief[key as keyof Brief];
      return Array.isArray(value) ? Array.isArray(current) && current.length === 0 : current === value;
    });
    if (isEmpty || session.briefOrigin === 'new') session.newBrief();
  };
}
