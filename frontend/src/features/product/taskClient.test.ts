import { expect, it } from 'vitest';
import { sameConfirmedRequest } from './taskClient';
import type { ProductPlanningInput } from '../planning/types';

function request(amount: string): ProductPlanningInput {
  return { destination: 'Sydney', start_date: '2026-10-22', end_date: '2026-10-23',
    traveler_count: 1, budget: { amount, currency: 'AUD' }, additional_preferences: 'Quiet parks' };
}

it.each([
  ['1.00000000000000000000000000001', '1.00000000000000000000000000002'],
  ['1E+1000000', '1E+999999'],
  ['1E-1000000', '0'],
])('keeps distinct confirmed amounts %s and %s as different operations', (left, right) => {
  expect(sameConfirmedRequest(request(left), request(right))).toBe(false);
});

it.each([
  ['1', '1.0'], ['100', '1E+2'], ['1E+1000000', '10E+999999'],
  ['1.00000000000000000000000000001', '1.0000000000000000000000000000100'],
  ['0E+9000', '-0.00'],
])('recovers equivalent confirmed amounts %s and %s under the original operation', (left, right) => {
  expect(sameConfirmedRequest(request(left), request(right))).toBe(true);
});
