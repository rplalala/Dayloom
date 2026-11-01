import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import examples from '../../../data/examples.json';
const [sydney, london] = examples.map(detail => ({ detail, created_at: detail.created_at }));
import type { ProductDetail } from '../product/detail/types';
import { showcaseRoutes } from './ShowcaseApp';

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

it('lets a visitor browse the product home, examples and place details without a backend', async () => {
  const fetch = vi.fn(() => Promise.reject(new Error('The showcase has no API')));
  vi.stubGlobal('fetch', fetch);
  vi.stubGlobal('scrollTo', vi.fn());
  const router = createMemoryRouter(showcaseRoutes([sydney.detail, london.detail] as ProductDetail[]));
  render(<RouterProvider router={router} />);
  const user = userEvent.setup();

  expect(screen.getByRole('heading', { name: /So much to discover/ })).toBeVisible();
  expect(screen.getByText(/Public showcase/)).toBeVisible();
  expect(screen.queryByRole('link', { name: /Log in|Start planning/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole('link', { name: 'Browse examples' }));
  expect(screen.getByRole('heading', { name: 'Example itineraries' })).toBeVisible();
  await user.type(screen.getByRole('textbox', { name: 'Search trips' }), 'London');
  await user.click(screen.getByRole('link', { name: london.detail.title }));
  expect(screen.getByRole('heading', { name: london.detail.title })).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'View Tower of London' }));
  expect(within(screen.getByRole('dialog')).getByRole('link', { name: 'License' })).toHaveAttribute('href', expect.stringContaining('creativecommons.org'));
  expect(screen.queryByRole('button', { name: /Refresh photo|Plan again|Export itinerary|Save a copy/ })).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});

it('loads either example directly with project-relative images, including fallbacks', async () => {
  vi.stubEnv('BASE_URL', '/Dayloom/');
  vi.stubGlobal('scrollTo', vi.fn());
  const fetch = vi.fn(() => Promise.reject(new Error('The showcase has no API')));
  vi.stubGlobal('fetch', fetch);
  const router = createMemoryRouter(showcaseRoutes([sydney.detail, london.detail] as ProductDetail[]), { initialEntries: ['/examples/sydney-example'] });
  render(<RouterProvider router={router} />);
  expect(screen.getByRole('heading', { name: sydney.detail.title })).toBeVisible();
  fireEvent.error(screen.getByRole('img', { name: 'Sydney, Australia destination atmosphere' }));
  expect(screen.getByRole('img', { name: 'Sydney, Australia destination atmosphere · illustration' })).toHaveAttribute('src', '/Dayloom/dayloom/hero.svg');
  for (const image of screen.getAllByRole('img')) expect(image.getAttribute('src')).toMatch(/^\/Dayloom\/dayloom\//);
  await userEvent.click(screen.getByRole('link', { name: 'Back to examples' }));
  expect(screen.getByRole('heading', { name: 'Example itineraries' })).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();
});

it('sorts the public examples by their saved dates and explains the full application', async () => {
  vi.stubGlobal('scrollTo', vi.fn());
  const examples = [sydney, london].map(source => ({ ...source.detail, created_at: source.created_at })) as ProductDetail[];
  render(<RouterProvider router={createMemoryRouter(showcaseRoutes(examples), { initialEntries: ['/trips'] })} />);
  const user = userEvent.setup();
  expect(screen.getAllByRole('heading', { level: 3 })[0]).toHaveTextContent('London');
  await user.selectOptions(screen.getByRole('combobox', { name: 'Sort trips' }), 'oldest');
  expect(screen.getAllByRole('heading', { level: 3 })[0]).toHaveTextContent('Sydney');
  await user.click(within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('link', { name: 'About Dayloom' }));
  expect(screen.getByRole('heading', { name: 'Meet Dayloom.' })).toBeVisible();
  expect(screen.getByText(/Those services are not connected/)).toBeVisible();
  expect(screen.getByRole('link', { name: 'Get the full application' })).toHaveAttribute('href', 'https://github.com/rplalala/Dayloom#readme');
});
