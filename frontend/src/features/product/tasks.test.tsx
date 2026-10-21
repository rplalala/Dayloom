import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../app/router';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it('observes completion without redirecting or replacing the editable brief', async () => {
  const task = { id: 'one', state: 'completed', revision: 4, request: { destination: 'Sydney' },
    progress: { message: 'Your itinerary preview is ready' }, preview_id: 'preview-one' };
  vi.stubGlobal('fetch', vi.fn(async (url: string) => new Response(JSON.stringify(
    url === '/api/auth/current' ? { id: 'alice', display_name: 'Alice', initials: 'A', csrf_token: 'csrf' }
    : url === '/api/planning/tasks/recent?limit=10' ? [task]
    : url === '/api/planning/date-window' ? { allowedStart: '2026-10-21', allowedEnd: '2026-11-03', maxTripDays: 10 }
    : url === '/api/previews' ? [] : null))));
  const router = createMemoryRouter(routes, { initialEntries: ['/plan'] });
  render(<RouterProvider router={router} />);
  const notice = await screen.findByText('Your itinerary preview is ready.');
  expect(notice.closest('.dayloom')).not.toBeNull();
  expect(router.state.location.pathname).toBe('/plan');
  await waitFor(() => expect(screen.getByLabelText('Destination')).toHaveValue(''));
  expect(screen.getByRole('link', { name: 'View preview' })).toHaveAttribute('href', '/previews/preview-one');
});

it('hides accepted task identity immediately after cross-tab logout on the same editor', async () => {
  let loggedOut = false;
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/auth/current') return Response.json(loggedOut ? { detail: { code: 'session_revoked' } } : { id: 'alice', display_name: 'Alice', initials: 'A', csrf_token: 'csrf' }, { status: loggedOut ? 401 : 200 });
    if (url === '/api/planning/date-window') return Response.json({ allowedStart: '2026-10-21', allowedEnd: '2026-11-03', maxTripDays: 10 });
    if (url === '/api/planning/tasks' && options?.method === 'POST') return Response.json({ id: 'private-task-a', state: 'pending' }, { status: 202 });
    if (url.includes('/api/planning/tasks')) return Response.json(url.includes('operation_key') ? null : []);
    return Response.json(null);
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/plan'] })} />);
  fireEvent.change(await screen.findByLabelText('Destination'), { target: { value: 'Sydney' } });
  fireEvent.change(screen.getByLabelText('Start date'), { target: { value: '2026-10-22' } });
  fireEvent.change(screen.getByLabelText('End date'), { target: { value: '2026-10-23' } });
  fireEvent.change(screen.getByLabelText('Travelers'), { target: { value: '2' } });
  fireEvent.change(screen.getByLabelText('Whole-trip budget'), { target: { value: '1000' } });
  fireEvent.click(screen.getByRole('button', { name: /Generate itinerary/ }));
  const link = await screen.findByRole('link', { name: /Open task progress/ });
  expect(link).toHaveAttribute('href', '/planning/private-task-a');
  loggedOut = true;
  fireEvent(window, new StorageEvent('storage', { key: 'dayloom.account.notice', newValue: JSON.stringify({ type: 'logout' }) }));
  await waitFor(() => expect(screen.queryByRole('link', { name: /Open task progress/ })).not.toBeInTheDocument());
  expect(sessionStorage.getItem('dayloom.task.intent.v1')).toBeNull();
});
