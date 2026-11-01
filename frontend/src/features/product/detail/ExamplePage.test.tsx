import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { routes } from '../../../app/router';
import london from '../../../../../backend/app/product/examples/london-example.json';

afterEach(() => { sessionStorage.clear(); vi.unstubAllGlobals(); });

it('renders a read-only guest example with local photos and no media service requests', async () => {
  const mediaRequests: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    if (input === '/api/auth/current') return Response.json({}, { status: 401 });
    if (input === '/api/examples/london-example') return Response.json(london.detail);
    if (input.includes('/media') || input.includes('/supporting-media')) mediaRequests.push(input);
    return Response.json({}, { status: 404 });
  }));
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/examples/london-example'] })} />);
  await screen.findByRole('heading', { name: london.detail.title });
  expect(await screen.findByRole('img', { name: 'Tower of London · place photograph' })).toBeVisible();
  expect(await screen.findByRole('img', { name: 'London, United Kingdom destination atmosphere' })).toBeVisible();
  for (const image of screen.getAllByRole('img')) expect(image.getAttribute('src')).toMatch(/^\/dayloom\//);
  expect(mediaRequests).toEqual([]);
  expect(screen.queryByRole('button', { name: /Plan again|Save a copy|Export/i })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'WALK · 8 min · Fits your schedule →' })).toBeVisible();
  expect(screen.queryByText(/unavailable|Avg —/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByLabelText('Weather details for Oct 15'));
  expect(screen.getByText('High 20.5°C')).toBeVisible();
  expect(screen.getByText('Rain chance 6%')).toBeVisible();
  const showModal = vi.spyOn(HTMLDialogElement.prototype, 'showModal').mockImplementation(function (this: HTMLDialogElement) { this.open = true; });
  await userEvent.click(screen.getByRole('button', { name: 'View Tower of London' }));
  expect(within(screen.getByRole('dialog')).getByText('Check admission and booking prices before you go.')).toBeVisible();
  expect(within(screen.getByRole('dialog')).getByRole('link', { name: 'License' })).toHaveAttribute('href', expect.stringContaining('creativecommons.org'));
  expect(screen.queryByRole('button', { name: 'Refresh photo' })).not.toBeInTheDocument();
  expect(screen.queryByText(/unavailable/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Close dialog' }));
  await userEvent.click(screen.getByRole('button', { name: "View Muriel's Espresso Bar" }));
  const nearbyDialog = within(screen.getByRole('dialog'));
  expect(nearbyDialog.getByRole('img', { name: "Muriel's Espresso Bar · place photograph" })).toHaveAttribute('src', expect.stringMatching(/^\/dayloom\/examples\/muriels-espresso-[a-f0-9]+\.jpg$/));
  expect(nearbyDialog.getByText('Google Maps')).toBeVisible();
  expect(nearbyDialog.getByRole('link', { name: 'Tuba Polat' })).toHaveAttribute('href', 'https://maps.google.com/maps/contrib/108697199764947603483');
  expect(nearbyDialog.getByRole('link', { name: 'Photo source' })).toHaveAttribute('href', expect.stringContaining('https://www.google.com/maps/place/'));
  expect(nearbyDialog.queryByRole('link', { name: 'License' })).not.toBeInTheDocument();
  expect(mediaRequests).toEqual([]);
  showModal.mockRestore();
});
