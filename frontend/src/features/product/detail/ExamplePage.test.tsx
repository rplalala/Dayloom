import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../../app/router';
import london from '../../../../../backend/app/product/examples/london-example.json';

afterEach(() => { sessionStorage.clear(); vi.unstubAllGlobals(); });

it('renders a complete public example with the same photos, weather and routes as a trip', async () => {
  const photo = { status: 'available', provider: 'Google Maps', image_url: 'https://lh3.googleusercontent.com/london', authors: [{ name: 'Photographer' }] };
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    if (input === '/api/auth/current') return Response.json({}, { status: 401 });
    if (input === '/api/examples/london-example') return Response.json(london.detail);
    if (input.startsWith('/api/examples/london-example/media?')) return Response.json({ items: Object.fromEntries(Object.keys(london.media_bindings).map(slot => [slot, photo])) });
    if (input.startsWith('/api/media/destination?')) {
      expect(new URL(input, 'http://localhost').searchParams.get('destination')).toBe(london.detail.destination);
      return Response.json({ ...photo, provider: 'Unsplash', kind: 'atmosphere',
        image_url: 'https://images.unsplash.com/london', alt: 'London atmosphere' });
    }
    return Response.json({}, { status: 404 });
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/examples/london-example'] })} />);
  await screen.findByRole('heading', { name: london.detail.title });
  expect(await screen.findByRole('img', { name: 'Tower of London · place photograph' })).toBeVisible();
  expect(await screen.findByRole('img', { name: 'London atmosphere' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'WALK · 8 min · Fits your schedule →' })).toBeVisible();
  expect(screen.queryByText(/unavailable|Avg —/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByLabelText('Weather details for Oct 15'));
  expect(screen.getByText('High 20.5°C')).toBeVisible();
  expect(screen.getByText('Rain chance 6%')).toBeVisible();
  const showModal = vi.spyOn(HTMLDialogElement.prototype, 'showModal').mockImplementation(function (this: HTMLDialogElement) { this.open = true; });
  await userEvent.click(screen.getByRole('button', { name: 'View Tower of London' }));
  expect(within(screen.getByRole('dialog')).getByText('Check admission and booking prices before you go.')).toBeVisible();
  expect(screen.queryByText(/unavailable/i)).not.toBeInTheDocument();
  showModal.mockRestore();
});
