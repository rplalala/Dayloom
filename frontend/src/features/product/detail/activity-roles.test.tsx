import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it } from 'vitest';
import { TripDetail } from './TripDetail';
import { exportArtifact } from './export';
import type { ProductDetail, DetailActivity } from './types';

const activity = (id: string, kind?: DetailActivity['activity_kind']): DetailActivity => ({
  activity_id: id, title: id, activity_kind: kind, time_use: 'scheduled',
  start_time: '2026-10-15T10:00:00', end_time: '2026-10-15T11:00:00',
  notes: 'Enjoy the harbour at your own pace.',
});

it('separates principal, supporting and transport structures without guessing historical roles', () => {
  const detail: ProductDetail = {
    schema_version: 'product_detail_1', id: 'roles', title: 'A day out', destination: 'Sydney',
    provenance: 'generated', trust: 'generated_projection', request: null, nearby: [],
    days: [{ date: '2026-10-15', activities: [
      activity('Museum', 'main_poi'), activity('Waterfront walk', 'generic_activity'),
      activity('Ride to the harbour', 'transport'), activity('Historic museum'),
    ] }],
    transfers: [{ from_activity_id: 'Museum', to_activity_id: 'Waterfront walk', mode: 'WALK',
      provider_duration_seconds: 600, distance_meters: 700, status: 'unknown',
      estimate_kind: 'unverified', unknowns: ['Opening time not confirmed'] }],
  };
  const { container } = render(<MemoryRouter><TripDetail detail={detail} /></MemoryRouter>);
  const supporting = screen.getByRole('group', { name: 'Waterfront walk on 2026-10-15' });
  expect(supporting).toHaveClass('supporting-activity');
  expect(within(supporting).getByText('Enjoy the harbour at your own pace.')).toBeVisible();
  expect(within(supporting).getByText('10:00–11:00')).toBeVisible();
  expect(within(supporting).queryByRole('img')).not.toBeInTheDocument();
  expect(screen.getByRole('group', { name: 'Museum on 2026-10-15' })).toHaveClass('principal-visit');
  expect(screen.getByRole('group', { name: 'Historic museum on 2026-10-15' })).toHaveClass('unknown-activity');
  const transport = screen.getByRole('button', { name: /Ride to the harbour · 10:00–11:00/ });
  expect(transport).toHaveClass('transfer-connector');
  expect(transport.querySelector('.activity-marker, img')).toBeNull();
  expect(container.querySelectorAll('.transfer-connector')).toHaveLength(2);
  const exported = exportArtifact(detail);
  expect(exported.itinerary.days[0].activities[1]).toMatchObject({
    activity_kind: 'generic_activity', time_use: 'scheduled', activity_id: 'Waterfront walk',
  });
});
