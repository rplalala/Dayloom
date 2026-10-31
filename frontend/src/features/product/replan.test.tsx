import { fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../app/router';
import type { ProductDetail } from './detail/types';
import { createBrief, toggleInterest, togglePace, toggleTransport } from './editor';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

const cases: [ProductDetail['request'], string[]][] = [
  [null, ['', '', '', '', '', '', '']],
  [{ known_fields: ['destination', 'traveler_count'], destination: 'Original city', traveler_count: null }, ['Original city', '', '', '', '', '', '']],
  [{ destination: 'Sydney', start_date: '2026-10-22', end_date: '2026-10-23', traveler_count: 3, budget: { amount: '0', currency: 'JPY' }, additional_preferences: 'Must include: my original wording.' }, ['Sydney', '2026-10-22', '2026-10-23', '3', '0', 'JPY', '']],
];

it.each(cases.flatMap(([request, expected]) => ['/trips/saved', '/previews/source-preview', '/examples/sydney-example'].map(path => [path, request, expected] as const)))('replans %s with only known basics and no personalization: %j', async (path, request, expected) => {
  const oldBrief = togglePace(toggleInterest(toggleTransport(createBrief(), 'drive'), 'Nature'), 'rich');
  oldBrief.required = 'Old required place';
  oldBrief.exclusions = 'Old avoided place';
  sessionStorage.setItem('dayloom.editor.v1', JSON.stringify({ owner: 'alice', brief: oldBrief, actionId: null, origin: 'edited' }));
  const writes: string[] = [];
  const reads: string[] = [];
  const detail = { schema_version: 'product_detail_1', id: 'saved', title: 'Saved source', destination: 'Generated destination', start_date: '2020-01-01', end_date: '2020-01-03', provenance: request?.budget ? 'generated' : 'imported', trust: 'unverified_import', request, days: [], nearby: [], transfers: [], description: 'Generated explanation: visit the museum.' };
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method && options.method !== 'GET') writes.push(url);
    else reads.push(url);
    if (url === '/api/auth/current') return Response.json({ id: 'alice', display_name: 'Alice', initials: 'A', csrf_token: 'csrf' });
    if (url === '/api/trips/saved') return Response.json(detail);
    if (url === '/api/examples/sydney-example') return Response.json(detail);
    if (url === '/api/previews/source-preview') return Response.json({ id: 'source-preview', state: 'pending', snapshot: detail, source_task_id: null, saved_trip_id: null });
    if (url === '/api/planning/date-window') return Response.json({ allowedStart: '2026-10-21', allowedEnd: '2026-11-03', maxTripDays: 10 });
    if (url === '/api/planning/tasks/recent?limit=10') return Response.json([]);
    if (url === '/api/profile') throw new Error('Replan must not request profile defaults');
    throw new Error(`Unexpected request: ${url}`);
  }));
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  fireEvent.click(await screen.findByRole('button', { name: request ? 'Plan again' : 'Plan another journey →' }));
  await screen.findByLabelText('Destination');
  ['Destination', 'Start date', 'End date', 'Travelers', 'Whole-trip budget', 'Currency', 'Additional preferences'].forEach((field, index) => {
    const control = screen.getByLabelText(field, { exact: true });
    if (field === 'Currency') expect(control).toHaveValue(expected[index]);
    else expect(control).toHaveDisplayValue(expected[index]);
  });
  expect(screen.getByLabelText('Places or experiences to include')).toHaveValue('');
  expect(screen.getByLabelText('Places or experiences to avoid')).toHaveValue('');
  fireEvent.click(screen.getByText('Personalize your trip'));
  expect(screen.queryAllByRole('button', { pressed: true })).toHaveLength(0);
  expect(router.state.location.pathname).toBe('/plan');
  expect(writes).toEqual([]);
  expect(reads).not.toContain('/api/profile');
  fireEvent.change(screen.getByLabelText('Travelers'), { target: { value: '4' } });
  expect(screen.getByLabelText('Travelers')).toHaveValue(4);
});
