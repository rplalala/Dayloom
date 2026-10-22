import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../app/router';
import { createBrief } from './editor';
import type { PlanningTask } from './taskClient';

const brief = { ...createBrief(), destination: 'Kyoto', start_date: '2026-10-23', end_date: '2026-10-24', travelers: '2', budget: '1000' };
const request = { destination: 'Sydney', start_date: brief.start_date, end_date: brief.end_date, traveler_count: 2, budget: { amount: '1000', currency: 'AUD' }, additional_preferences: '' };
const task: PlanningTask = { id: 'task-a', state: 'running', revision: 1, request, editor_snapshot: { ...brief, destination: 'Sydney' }, progress: { stage: 'generation', message: 'Planning your days.' }, preview_id: null, outcome: null, created_at: '', updated_at: '' };
const detail = { schema_version: 'product_detail_1', id: 'preview-a', title: 'A Sydney afternoon', destination: 'Sydney', start_date: brief.start_date, end_date: brief.end_date, request, days: [], transfers: [], nearby: [] };
afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

function setup(path = '/', recent = [task], selected = task) {
  sessionStorage.setItem('dayloom.editor.v1', JSON.stringify({ owner: 'alice', brief, actionId: null, origin: 'restored' }));
  const writes: string[] = [];
  const submissions: { operation_key: string }[] = [];
  let offline = false;
  let current = selected;
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method === 'POST') writes.push(url);
    if (url === '/api/auth/current') return Response.json({ id: 'alice', display_name: 'Alice', initials: 'A', csrf_token: 'csrf' });
    if (url === '/api/planning/tasks/recent?limit=10') return Response.json(recent);
    if (url === '/api/planning/tasks/task-a') { if (offline) throw new TypeError('Offline'); return Response.json(current); }
    if (url === '/api/planning/tasks/task-a/stop') { current = { ...current, state: 'cancelled', revision: 2, outcome: { code: 'planning_cancelled', message: 'Your travel brief is kept.', action: 'Review your brief.' } }; return Response.json(current); }
    if (url === '/api/planning/tasks' && options?.method === 'POST') { submissions.push(JSON.parse(String(options.body))); return Response.json({ ...task, id: 'new-task' }); }
    if (url === '/api/planning/tasks/new-task') return Response.json({ ...task, id: 'new-task' });
    if (url === '/api/previews/preview-a') return Response.json({ id: 'preview-a', source_task_id: 'task-a', state: 'pending', snapshot: detail });
    if (url === '/api/previews?limit=20') return Response.json([{ id: 'older-preview', state: 'pending', title: 'An earlier journey', destination: 'Kyoto' }]);
    if (url === '/api/planning/date-window') return Response.json({ allowedStart: '2026-10-22', allowedEnd: '2026-11-04', maxTripDays: 10 });
    return Response.json([]);
  }));
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return { router, writes, submissions, offline: (value: boolean) => { offline = value; } };
}

it('returns from the header to Plan progress without replacing another brief or submitting', async () => {
  const { router, writes } = setup();
  const entry = await screen.findByRole('link', { name: 'Planning task running' }, { timeout: 5000 });
  expect(entry).toHaveTextContent('Planning Sydney');
  fireEvent.click(entry);
  await waitFor(() => expect(router.state.location.pathname).toBe('/plan'));
  expect(router.state.location.search).toBe('?task=task-a');
  expect(router.state.location.hash).toBe('#generation-progress');
  expect(await screen.findByLabelText('Destination')).toHaveValue('Kyoto');
  expect(await screen.findByRole('button', { name: 'Stop planning' })).toBeEnabled();
  expect(screen.queryByRole('heading', { name: 'Planning tasks' })).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});

it('reconnects by reading the accepted task and never generates again automatically', async () => {
  const { writes, offline } = setup('/plan?task=task-a#generation-progress');
  await screen.findByRole('button', { name: 'Stop planning' });
  offline(true);
  fireEvent.focus(window);
  expect(await screen.findByText('Reconnecting…')).toBeVisible();
  offline(false);
  fireEvent.click(screen.getByRole('button', { name: 'Check status' }));
  await waitFor(() => expect(screen.queryByText('Reconnecting…')).not.toBeInTheDocument());
  expect(screen.getByLabelText('Destination')).toHaveValue('Kyoto');
  expect(writes).toEqual([]);
});

it('stops in Plan and generates a new attempt only after an explicit Generate again click', async () => {
  const { router, writes, submissions } = setup('/plan?task=task-a&preview=older-preview#generation-progress');
  fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Sydney' } });
  fireEvent.click(await screen.findByRole('button', { name: 'Stop planning' }));
  expect(await screen.findByText('Planning stopped', { selector: 'h3' })).toBeVisible();
  expect(writes).toEqual(['/api/planning/tasks/task-a/stop']);
  expect(screen.getByRole('link', { name: 'Keep editing' })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Generate again' }));
  await waitFor(() => expect(submissions).toHaveLength(1));
  await waitFor(() => expect(router.state.location.search).toBe('?task=new-task'));
  expect(submissions[0].operation_key).toBeTruthy();
  expect(writes).toEqual(['/api/planning/tasks/task-a/stop', '/api/planning/tasks']);
  expect(screen.getByLabelText('Destination')).toHaveValue('Sydney');
});

it('opens completion in section 03 with explicit decisions and older previews, keeping the current brief', async () => {
  const completed = { ...task, state: 'completed' as const, preview_id: 'preview-a' };
  const { router, writes } = setup('/', [completed], completed);
  fireEvent.click(await screen.findByRole('link', { name: 'Itinerary ready' }));
  await screen.findByRole('heading', { name: 'A Sydney afternoon' });
  expect(router.state.location.pathname).toBe('/plan');
  expect(router.state.location.hash).toBe('#result');
  const result = within(document.getElementById('result')!);
  expect(result.getByRole('button', { name: 'Save to My trips' })).toBeEnabled();
  expect(result.getByRole('button', { name: 'Discard preview' })).toBeEnabled();
  fireEvent.click(result.getByText('Unsaved previews'));
  expect(await result.findByText('An earlier journey')).toBeVisible();
  expect(screen.getByLabelText('Destination')).toHaveValue('Kyoto');
  await waitFor(() => expect(screen.queryByRole('link', { name: 'Itinerary ready' })).not.toBeInTheDocument());
  expect(writes).toEqual([]);
});

it('recovers an older task at its legacy address inside Plan without restoring its brief', async () => {
  const { router, writes } = setup('/planning/task-a', []);
  expect(await screen.findByLabelText('Destination')).toHaveValue('Kyoto');
  await waitFor(() => expect(router.state.location.pathname).toBe('/plan'));
  expect(router.state.location.search).toBe('?task=task-a');
  expect(await screen.findByRole('button', { name: 'Stop planning' })).toBeEnabled();
  expect(within(document.getElementById('generation-progress')!).getByText('Sydney · Oct 23–24, 2026')).toBeVisible();
  expect(screen.queryByText('Open planning tasks and recoverable previews →')).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});

it('acknowledges an older preview independently of the other task still running', async () => {
  const running = { ...task, id: 'task-b', request: { ...request, destination: 'Kyoto' } };
  const recent = [running, { ...task, state: 'completed' as const, preview_id: 'preview-a' }];
  const { router, writes } = setup('/plan?preview=preview-a#result', recent);
  await screen.findByRole('heading', { name: 'A Sydney afternoon' });
  expect(screen.getByRole('link', { name: 'Planning task running' })).toHaveTextContent('Planning Kyoto');
  await act(async () => { await router.navigate('/'); });
  recent[0] = { ...running, state: 'cancelled' };
  fireEvent.focus(window);
  await waitFor(() => expect(screen.queryByRole('link', { name: 'Planning task running' })).not.toBeInTheDocument());
  expect(screen.queryByRole('link', { name: 'Itinerary ready' })).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});
