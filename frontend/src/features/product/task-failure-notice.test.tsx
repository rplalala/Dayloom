import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../app/router';
import { createBrief } from './editor';
import type { PlanningTask } from './taskClient';

const brief = { ...createBrief(), destination: 'Kyoto', start_date: '2026-10-23', end_date: '2026-10-24', travelers: '2', budget: '1000' };
const original: PlanningTask = { id: 'failed-task', state: 'running', revision: 1,
  request: { destination: 'Sydney', start_date: brief.start_date, end_date: brief.end_date, traveler_count: 2, budget: { amount: '1000', currency: 'AUD' }, additional_preferences: '' },
  editor_snapshot: { ...brief, destination: 'Sydney' }, preview_id: null, progress: { stage: 'generation', message: 'Planning your days.' }, outcome: null, created_at: '', updated_at: '' };
afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

function setup() {
  sessionStorage.setItem('dayloom.editor.v1', JSON.stringify({ owner: 'alice', brief, actionId: null, origin: 'restored' }));
  let task = original;
  let loggedOut = false;
  const history: PlanningTask[] = [];
  const writes: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method === 'POST') writes.push(url);
    if (url === '/api/auth/current') return loggedOut ? Response.json({ detail: { code: 'session_revoked' } }, { status: 401 }) : Response.json({ id: 'alice', display_name: 'Alice', initials: 'A', csrf_token: 'csrf' });
    if (url === '/api/planning/tasks/recent?limit=10') return Response.json([task, ...history]);
    if (url === '/api/planning/tasks/failed-task') return Response.json(history[0] || task);
    if (url === '/api/planning/tasks/retry-task') return Response.json(task);
    if (url === '/api/planning/tasks' && options?.method === 'POST') {
      history.push(task);
      task = { ...original, id: 'retry-task' };
      return Response.json(task, { status: 202 });
    }
    if (url === '/api/previews/retry-preview') return Response.json({ id: 'retry-preview', state: 'discarded', outcome: 'discarded' });
    if (url === '/api/planning/date-window') return Response.json({ allowedStart: '2026-10-22', allowedEnd: '2026-11-04', maxTripDays: 10 });
    if (url.startsWith('/api/library')) return Response.json({ items: [], total: 0 });
    return Response.json([]);
  }));
  const router = createMemoryRouter(routes, { initialEntries: ['/trips'] });
  const view = render(<RouterProvider router={router} />);
  return { router, view, writes, completeRetry: () => { task = { ...task, state: 'completed', revision: 3, preview_id: 'retry-preview' }; fireEvent.focus(window); }, logout: () => {
    loggedOut = true;
    fireEvent(window, new StorageEvent('storage', { key: 'dayloom.account.notice', newValue: JSON.stringify({ type: 'logout' }) }));
  }, finish: (state: PlanningTask['state'] = 'failed') => {
    task = { ...original, state, revision: 2, outcome: { code: 'planning_failed', message: 'Planning could not finish.', action: 'Review your brief and try again.' } };
    fireEvent.focus(window);
  } };
}

it('notifies failure in My trips and keeps a Plan entry through dismissal, viewing and refresh without submitting', async () => {
  const { router, view, writes, finish } = setup();
  await screen.findByRole('link', { name: 'Planning task running' });
  finish();
  const entry = await screen.findByRole('link', { name: 'Planning needs attention' });
  expect(router.state.location.pathname).toBe('/trips');
  const notice = (await screen.findByRole('link', { name: 'View details' })).closest('[role="status"]')!;
  expect(within(notice as HTMLElement).getByText('Planning needs attention. Your travel brief is kept.')).toBeVisible();
  expect(entry).toHaveAttribute('href', '/plan?task=failed-task#generation-progress');
  fireEvent.click(screen.getByRole('button', { name: 'Dismiss planning notice' }));
  expect(screen.getByRole('link', { name: 'Planning needs attention' })).toBeVisible();
  fireEvent.click(entry);
  await screen.findByRole('heading', { name: 'Planning could not finish' });
  expect(router.state.location.hash).toBe('#generation-progress');
  expect(screen.getByLabelText('Destination')).toHaveValue('Kyoto');
  expect(screen.getByRole('button', { name: 'Revise submitted brief' })).toBeEnabled();
  await act(async () => { await router.navigate('/trips'); });
  view.unmount();
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/trips'] })} />);
  expect(await screen.findByRole('link', { name: 'Planning needs attention' })).toBeVisible();
  expect(screen.queryByRole('link', { name: 'View details' })).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});

it('clears an obsolete failure notice on explicit retry and never revives the old failure after success', async () => {
  const { router, writes, finish, completeRetry } = setup();
  await screen.findByRole('link', { name: 'Planning task running' });
  finish();
  fireEvent.click(await screen.findByRole('link', { name: 'Planning needs attention' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Revise submitted brief' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Replace current brief' }));
  expect(writes).toEqual([]);
  fireEvent.click(await screen.findByRole('button', { name: 'Generate again' }));
  await waitFor(() => expect(router.state.location.search).toBe('?task=retry-task'));
  expect(await screen.findByRole('link', { name: 'Planning task running' })).toHaveTextContent('Planning Sydney');
  expect(screen.queryByRole('link', { name: 'Planning needs attention' })).not.toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'View details' })).not.toBeInTheDocument();
  completeRetry();
  fireEvent.click(await screen.findByRole('link', { name: 'Itinerary ready' }));
  await screen.findByText('Preview discarded.');
  expect(screen.queryByRole('link', { name: 'Planning needs attention' })).not.toBeInTheDocument();
  expect(writes).toEqual(['/api/planning/tasks']);
});

it.each(['needs_clarification', 'safety_blocked', 'provider_blocked'] as const)('retains a reason entry for %s without generating', async state => {
  const { router, writes, finish } = setup();
  await screen.findByRole('link', { name: 'Planning task running' });
  finish(state);
  await screen.findByRole('link', { name: 'Planning needs attention' });
  fireEvent.click(screen.getByRole('link', { name: 'View details' }));
  expect(await screen.findByRole('region', { name: 'Planning outcome' })).toHaveTextContent('Review your brief and try again.');
  expect(router.state.location.pathname + router.state.location.search + router.state.location.hash).toBe('/plan?task=failed-task#generation-progress');
  expect(screen.getByLabelText('Destination')).toHaveValue('Kyoto');
  expect(writes).toEqual([]);
});

it('does not announce a deliberate Stop as a failure', async () => {
  const { finish, writes } = setup();
  await screen.findByRole('link', { name: 'Planning task running' });
  finish('cancelled');
  await waitFor(() => expect(screen.queryByRole('link', { name: 'Planning task running' })).not.toBeInTheDocument());
  expect(screen.queryByRole('link', { name: 'Planning needs attention' })).not.toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'View details' })).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});

it('hides the failure notice and task entry immediately on logout', async () => {
  const { finish, logout, writes } = setup();
  await screen.findByRole('link', { name: 'Planning task running' });
  finish();
  await screen.findByRole('link', { name: 'Planning needs attention' });
  logout();
  await waitFor(() => expect(screen.queryByRole('link', { name: 'Planning needs attention' })).not.toBeInTheDocument());
  expect(screen.queryByRole('link', { name: 'View details' })).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});
