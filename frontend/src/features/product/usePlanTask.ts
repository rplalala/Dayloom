import { useCallback, useEffect, useState } from 'react';
import { useSession } from './session';
import { useTasks } from './taskContext';
import { taskActive, TaskFailure, taskRequest, type PlanningTask } from './taskClient';

/** Observe a selected receipt independently of the editable brief and recent-list window. */
export function usePlanTask(id: string | null, fallback?: PlanningTask) {
  const { account, refresh: refreshSession } = useSession();
  const { error: recentError, refresh } = useTasks();
  const owner = account?.id;
  const csrf = account?.csrf_token;
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState<{ owner?: string; csrf?: string; id: string; task?: PlanningTask; error?: string }>();
  useEffect(() => {
    if (!owner || !id) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let inFlight = false;
    async function read() {
      if (inFlight || controller.signal.aborted) return;
      inFlight = true;
      try {
        const task = await taskRequest<PlanningTask>(`/api/planning/tasks/${encodeURIComponent(id!)}`, { signal: controller.signal });
        if (!task || task.id !== id || !task.request) throw new Error('Invalid task receipt');
        if (!controller.signal.aborted) {
          setSelected(previous => previous && previous.owner === owner && previous.csrf === csrf && previous.id === id && previous.task && previous.task.revision > task.revision ? previous : { owner, csrf, id: id!, task });
          if (taskActive(task)) timer = setTimeout(read, 3000);
        }
      } catch (failure) {
        if (controller.signal.aborted) return;
        if (failure instanceof TaskFailure && failure.status === 401) { void refreshSession(); return; }
        setSelected(previous => ({ owner, csrf, id: id!, task: previous && previous.owner === owner && previous.csrf === csrf && previous.id === id ? previous.task : undefined,
          error: failure instanceof TaskFailure && failure.status === 404 ? 'This planning task is unavailable.' : 'Reconnecting…' }));
        timer = setTimeout(read, 3000);
      } finally { inFlight = false; }
    }
    const reconnect = () => { clearTimeout(timer); void read(); };
    void read();
    window.addEventListener('online', reconnect);
    window.addEventListener('focus', reconnect);
    return () => { controller.abort(); clearTimeout(timer); window.removeEventListener('online', reconnect); window.removeEventListener('focus', reconnect); };
  }, [owner, csrf, id, retry, refreshSession]);
  const current = selected?.owner === owner && selected?.csrf === csrf && selected?.id === (id || fallback?.id) ? selected : undefined;
  const check = useCallback(async () => { setRetry(value => value + 1); await refresh(); }, [refresh]);
  const update = useCallback((task: PlanningTask) => setSelected({ owner, csrf, id: task.id, task }), [owner, csrf]);
  return { task: id ? current?.task : current?.task && (!fallback || current.task.revision > fallback.revision) ? current.task : fallback, error: id ? current?.error : recentError,
    loading: Boolean(owner && id && !current), check, update };
}
