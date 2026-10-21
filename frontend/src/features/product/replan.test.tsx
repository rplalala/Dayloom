import { fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../app/router';
import type { ProductDetail } from './detail/types';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

const cases: [ProductDetail['request'], string[]][] = [
  [null, ['', '', '', '', '', '', '']],
  [{ known_fields: ['destination', 'traveler_count'], destination: 'Original city', traveler_count: null }, ['Original city', '', '', '', '', '', '']],
  [{ destination: 'Sydney', start_date: '2026-10-22', end_date: '2026-10-23', traveler_count: 3, budget: { amount: '0', currency: 'JPY' }, additional_preferences: 'Must include: my original wording.' }, ['Sydney', '2026-10-22', '2026-10-23', '3', '0', 'JPY', 'Must include: my original wording.']],
];

it.each(cases)('opens an editable original request without adopting generated schedule content: %j', async (request, expected) => {
  const writes: string[] = [];
  const detail = { schema_version: 'product_detail_1', id: 'saved', title: 'Saved source', destination: 'Generated destination', start_date: '2020-01-01', end_date: '2020-01-03', provenance: request?.budget ? 'generated' : 'imported', trust: 'unverified_import', request, days: [], nearby: [], transfers: [], description: 'Generated explanation: visit the museum.' };
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method && options.method !== 'GET') writes.push(url);
    if (url === '/api/auth/current') return Response.json({ id: 'alice', display_name: 'Alice', initials: 'A', csrf_token: 'csrf' });
    if (url === '/api/trips/saved') return Response.json(detail);
    if (url === '/api/planning/date-window') return Response.json({ allowedStart: '2026-10-21', allowedEnd: '2026-11-03', maxTripDays: 10 });
    if (url === '/api/planning/tasks/recent?limit=10') return Response.json([]);
    if (url === '/api/profile') throw new Error('Replan must not request profile defaults');
    throw new Error(`Unexpected request: ${url}`);
  }));
  const router = createMemoryRouter(routes, { initialEntries: ['/trips/saved'] });
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
  expect(router.state.location.pathname).toBe('/plan');
  expect(writes).toEqual([]);
  fireEvent.change(screen.getByLabelText('Travelers'), { target: { value: '4' } });
  expect(screen.getByLabelText('Travelers')).toHaveValue(4);
});
