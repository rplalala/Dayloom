import { render } from '@testing-library/react';
import { expect, it } from 'vitest';
import { Icon } from './Icon';

it('renders distinct route, museum and tree glyphs instead of the info fallback', () => {
  const { container } = render(<><Icon name="route" /><Icon name="museum" size={52} /><Icon name="tree" size={52} /><Icon name="info" /></>);
  const glyphs = [...container.querySelectorAll('svg')];
  expect(new Set(glyphs.map(glyph => glyph.innerHTML)).size).toBe(4);
  expect(glyphs.every(glyph => glyph.getAttribute('aria-hidden') === 'true')).toBe(true);
});
