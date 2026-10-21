import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MediaPhoto } from './MediaPhoto';

describe('credited media display', () => {
  it('keeps attribution beside the photo and recovers honestly after an expired image', () => {
    render(<MediaPhoto label="Verified park" media={{ status: 'available', kind: 'verified_place', image_url: 'https://lh3.googleusercontent.com/fixture', provider: 'Google Maps', authors: [{ name: 'Travel Photographer', url: 'https://www.google.com/maps/contrib/123' }] }} />);
    expect(screen.getByRole('link', { name: 'Travel Photographer' })).toHaveAttribute('href', 'https://www.google.com/maps/contrib/123');
    fireEvent.error(screen.getByRole('img', { name: 'Verified park · place photograph' }));
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByText('Place photograph unavailable · illustration')).toBeVisible();
  });
  it('keeps the activity thumbnail details action separate from credit links', () => {
    const open = vi.fn();
    render(<MediaPhoto label="Verified park" onOpen={open} />);
    fireEvent.click(screen.getByRole('button', { name: 'View Verified park' }));
    expect(open).toHaveBeenCalledOnce();
  });
});
