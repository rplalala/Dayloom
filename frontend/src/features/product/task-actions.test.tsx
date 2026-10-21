import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../app/router';
import { createBrief } from './editor';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

const briefB = { ...createBrief(), destination: 'Kyoto', start_date: '2026-10-22', end_date: '2026-10-23', travelers: '2', budget: '1000' };
const taskA = { id: 'task-a', state: 'cancelled', revision: 4, request: { destination: 'Sydney', start_date: '2026-10-22', end_date: '2026-10-23', traveler_count: 2, budget: { amount: '1000', currency: 'AUD' } }, editor_snapshot: { ...briefB, destination: 'Sydney' }, progress: { message: 'Preparing your itinerary' }, preview_id: null, outcome: { code: 'planning_cancelled', message: 'Planning stopped. Your submitted brief is retained.', action: 'Review your brief.' } };

function taskPage(tasks = [taskA]) {
  sessionStorage.setItem('dayloom.editor.v1', JSON.stringify({ owner: 'alice', brief: briefB, actionId: null, origin: 'restored', draftTitle: 'Brief B' }));
  const saves: ((response: Response) => void)[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/auth/current') return Response.json({ id: 'alice', display_name: 'Alice', initials: 'A', csrf_token: 'csrf' });
    if (url === '/api/planning/tasks/recent?limit=10') return Response.json(tasks);
    if (url === '/api/planning/tasks/task-a') return Response.json(tasks[0]);
    if (url === '/api/drafts' && options?.method === 'POST') return new Promise<Response>(resolve => { saves.push(resolve); });
    if (url === '/api/planning/date-window') return Response.json({ allowedStart: '2026-10-21', allowedEnd: '2026-11-03', maxTripDays: 10 });
    return Response.json([]);
  }));
  const router = createMemoryRouter(routes, { initialEntries: ['/planning/task-a'] });
  render(<RouterProvider router={router} />);
  return { router, saves };
}

async function openRevisionDialog() {
  const revise = await screen.findByRole('button', { name: 'Revise submitted brief' });
  // Settle the asynchronously loaded card's initial effects before a user action.
  await act(async () => {});
  fireEvent.click(revise);
  const dialog = await screen.findByRole('dialog', { name: 'Keep your current brief?' });
  return within(dialog).findByRole('button', { name: 'Save current brief and revise' });
}

it.each(['success', 'failure'])('a deferred save-and-revise %s cannot change the next task navigation', async result => {
  const { router, saves } = taskPage();
  fireEvent.click(await openRevisionDialog());
  await waitFor(() => expect(saves).toHaveLength(1));
  await act(async () => { await router.navigate('/planning'); });
  await act(async () => { saves[0](Response.json(result === 'success' ? { id: 'saved-b', revision: 1 } : { detail: 'Unavailable' }, { status: result === 'success' ? 201 : 500 })); });
  expect(router.state.location.pathname).toBe('/planning');
  expect(JSON.parse(sessionStorage.getItem('dayloom.editor.v1')!).brief.destination).toBe('Kyoto');
  expect(screen.queryByRole('dialog', { name: 'Keep your current brief?' })).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('a previous save response cannot settle a newer revision operation on the retained task card', async () => {
  const { router, saves } = taskPage();
  fireEvent.click(await openRevisionDialog());
  await waitFor(() => expect(saves).toHaveLength(1));
  await act(async () => { await router.navigate('/planning'); });
  fireEvent.click(await openRevisionDialog());
  await waitFor(() => expect(saves).toHaveLength(2));
  await act(async () => { saves[0](Response.json({ detail: 'Old failure' }, { status: 500 })); });
  expect(router.state.location.pathname).toBe('/planning');
  expect(screen.getByRole('button', { name: 'Save current brief and revise' })).toBeDisabled();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  await act(async () => { saves[1](Response.json({ id: 'saved-b', revision: 1 }, { status: 201 })); });
  expect(router.state.location.pathname).toBe('/plan');
  expect(await screen.findByLabelText('Destination')).toHaveValue('Sydney');
});

it.each(['needs_clarification', 'safety_blocked', 'provider_blocked', 'failed', 'cancelled'])('a terminal %s card does not announce its retained running stage', async state => {
  taskPage([{ ...taskA, state }]);
  const taskLink = await screen.findByRole('button', { name: 'Revise submitted brief' });
  expect(taskLink).toBeVisible();
  expect(screen.queryByText('Preparing your itinerary')).not.toBeInTheDocument();
  expect(screen.getByRole('region', { name: 'Planning outcome' })).toBeVisible();
});
