import { render, screen, within, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { TripDetail } from './TripDetail';
import type { ProductDetail } from './types';

afterEach(() => { sessionStorage.clear(); localStorage.clear(); vi.unstubAllGlobals(); });

it('shows a small atmosphere photo with operable credits and removes failed imagery cleanly', async () => {
  const user = userEvent.setup();
  vi.stubGlobal('fetch', vi.fn(async (url: string) => new Response(JSON.stringify(
    String(url).includes('/supporting-media') ? { items: { 'activity:walk': {
      status: 'available', kind: 'atmosphere', theme: 'walk', provider: 'Unsplash',
      image_url: 'https://images.unsplash.com/first?ixid=kept', source_url: 'https://unsplash.com/photos/first',
      alt: 'Scenic atmosphere', authors: [{ name: 'Photographer', url: 'https://unsplash.com/@fixture' }],
    } } } : { status: 'unavailable', items: {} }
  ))));
  const detail: ProductDetail = { schema_version: 'product_detail_1', id: 'owned', title: 'A quiet day', destination: 'City',
    provenance: 'generated', trust: 'generated_projection', request: null, nearby: [], transfers: [],
    days: [{ date: '2026-10-15', activities: [{ activity_id: 'walk', title: 'Time to wander',
      activity_kind: 'generic_activity', atmosphere_theme: 'walk', time_use: 'scheduled',
      start_time: '2026-10-15T12:00:00', end_time: '2026-10-15T13:00:00' }] }],
  };
  render(<MemoryRouter><TripDetail detail={detail} mediaEndpoint="/api/trips/owned/media" mediaOwner="alice" /></MemoryRouter>);
  const card = screen.getByRole('group', { name: 'Time to wander on 2026-10-15' });
  const image = await within(card).findByRole('img', { name: 'Scenic atmosphere' });
  expect(within(card).getByText('Atmosphere photo')).toBeVisible();
  await user.click(within(card).getByRole('button', { name: 'Photo credits' }));
  expect(within(card).getByRole('link', { name: 'Photographer' })).toHaveAttribute('href', 'https://unsplash.com/@fixture');
  fireEvent.error(image);
  await waitFor(() => expect(within(card).queryByRole('img')).not.toBeInTheDocument());
  expect(within(card).getByText('12:00–13:00')).toBeVisible();
});
