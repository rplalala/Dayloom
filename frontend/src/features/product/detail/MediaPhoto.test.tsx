import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MediaPhoto } from './MediaPhoto';

describe('credited media display', () => {
  it('reveals atmosphere credits on hover, keyboard focus or an explicit touch action', () => {
    render(<MediaPhoto atmosphere label="Harbour" media={{ status: 'available', provider: 'Unsplash', image_url: 'https://images.unsplash.com/fixture', authors: [{ name: 'Harbour Photographer', url: 'https://unsplash.com/@fixture' }], source_url: 'https://unsplash.com/photos/fixture' }} />);
    const button = screen.getByRole('button', { name: 'Photo credits' });
    const credit = screen.getByRole('link', { name: 'Harbour Photographer', hidden: true });
    expect(credit).not.toBeVisible();
    fireEvent.pointerEnter(screen.getByRole('figure'));
    expect(credit).toBeVisible();
    fireEvent.pointerLeave(screen.getByRole('figure'));
    expect(credit).not.toBeVisible();
    fireEvent.focus(button);
    expect(credit).toBeVisible();
    fireEvent.keyDown(button, { key: 'Escape' });
    expect(credit).not.toBeVisible();
    fireEvent.click(button);
    expect(credit).toBeVisible();
    expect(button).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(screen.getByRole("button", { name: "Hide photo credits" }));
    expect(credit).not.toBeVisible();
    expect(button).toHaveFocus();
  });
  it('keeps attribution beside the photo and recovers honestly after an expired image', () => {
    render(<MediaPhoto label="Verified park" media={{ status: 'available', kind: 'verified_place', image_url: 'https://lh3.googleusercontent.com/fixture', provider: 'Google Maps', authors: [{ name: 'Travel Photographer', url: 'https://www.google.com/maps/contrib/123' }] }} />);
    expect(screen.getByRole('link', { name: 'Travel Photographer' })).toHaveAttribute('href', 'https://www.google.com/maps/contrib/123');
    fireEvent.error(screen.getByRole('img', { name: 'Verified park · place photograph' }));
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Illustration')).toBeVisible();
  });
  it('keeps the activity thumbnail details action separate from credit links', () => {
    const open = vi.fn();
    render(<MediaPhoto label="Verified park" onOpen={open} />);
    fireEvent.click(screen.getByRole('button', { name: 'View Verified park' }));
    expect(open).toHaveBeenCalledOnce();
  });
});


it('labels bundled illustrations without presenting them as venue photographs', () => {
  render(<MediaPhoto label="Gallery cafe" creditInDetails media={{ status: 'available', kind: 'illustration', image_url: '/dayloom/examples/gallery-cafe-local.svg', provider: 'Dayloom' }} />);
  expect(screen.getByRole('img', { name: 'Gallery cafe · illustration' })).toBeVisible();
  expect(screen.getByLabelText('Illustration')).toBeVisible();
  expect(screen.queryByRole('img', { name: /place photograph/ })).not.toBeInTheDocument();
});
