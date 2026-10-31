import { createBrief, type Brief } from './editor';
import type { ProductDetail } from './detail/types';

/** Keep only known trip basics; personalization starts empty and missing facts stay blank. */
export function replanBrief(request: ProductDetail['request']): Brief {
  const brief = { ...createBrief(), currency: '' };
  if (!request) return brief;
  const known = (field: string) => request.known_fields == null || request.known_fields.includes(field);
  for (const field of ['destination', 'start_date', 'end_date'] as const) {
    if (known(field) && request[field] != null) brief[field] = request[field];
  }
  if (known('traveler_count') && request.traveler_count != null) brief.travelers = String(request.traveler_count);
  if (known('budget') && request.budget != null) {
    brief.budget = String(request.budget.amount);
    brief.currency = request.budget.currency;
  }
  return brief;
}
