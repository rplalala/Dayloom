import type { Brief } from './editor';
import type { ProductPlanningInput } from '../planning/types';
import type { ProductDetail } from './detail/types';

export type PlanningTask = {
  id: string; state: 'pending' | 'running' | 'stopping' | 'completed' | 'needs_clarification' | 'safety_blocked' | 'provider_blocked' | 'failed' | 'cancelled';
  revision: number; progress: { stage: string; message: string; status?: string };
  request: ProductPlanningInput; editor_snapshot: Brief | null; preview_id: string | null;
  outcome: { code: string; message: string; action: string; issues?: unknown } | null;
  created_at: string; updated_at: string;
};
export type Preview = { id: string; source_task_id: string | null; state: 'pending' | 'saved' | 'discarded'; snapshot: ProductDetail | null; title?: string; destination?: string; saved_trip_id: string | null; created_at: string };
export const taskActive = (task: PlanningTask) => ['pending', 'running', 'stopping'].includes(task.state);

export class TaskFailure extends Error {
  constructor(public status: number, public detail: { code?: string; task_id?: string }) {
    super(status === 401 ? 'Log in again to continue. Your brief remains private.' : status === 409 && detail.code === 'planning_task_active' ? 'Planning is already running. Please wait or save this brief as a draft.' : status === 422 ? 'Check your trip dates, budget and preferences before generating.' : 'Planning is unavailable. Your brief is still here.');
  }
}
export async function taskRequest<T>(url: string, options: { signal?: AbortSignal; csrf?: string; body?: unknown } = {}): Promise<T> {
  const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', signal: options.signal,
    method: options.body === undefined ? 'GET' : 'POST',
    headers: { ...(options.body !== undefined && { 'Content-Type': 'application/json' }), ...(options.csrf && { 'X-CSRF-Token': options.csrf }) },
    ...(options.body !== undefined && { body: JSON.stringify(options.body) }) });
  const body = await response.json();
  if (!response.ok) throw new TaskFailure(response.status, body.detail || {});
  return body;
}

function exactAmount(value: string | number): string | null {
  const match = String(value).trim().match(/^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/);
  if (!match || !(match[2] || match[3])) return null;
  const fraction = match[3] || '';
  const digits = (match[2] + fraction).replace(/^0+/, '');
  if (!digits) return '0';
  const coefficient = digits.replace(/0+$/, '');
  const exponent = BigInt(match[4] || '0') - BigInt(fraction.length) + BigInt(digits.length - coefficient.length);
  return `${match[1] === '-' ? '-' : ''}${coefficient}e${exponent}`;
}

export function sameConfirmedRequest(left: ProductPlanningInput, right: ProductPlanningInput) {
  const amount = exactAmount(left.budget.amount);
  return amount !== null && amount === exactAmount(right.budget.amount) && left.destination === right.destination && left.start_date === right.start_date && left.end_date === right.end_date && left.traveler_count === right.traveler_count && left.budget.currency === right.budget.currency && (left.additional_preferences || '') === (right.additional_preferences || '');
}

type SubmissionIntent = { owner: string; generation: string; key: string; request: ProductPlanningInput; editor: Brief };
export function submissionGeneration(owner: string): string {
  try { return localStorage.getItem(`dayloom.account.invalidation.${owner}`) || ''; } catch { return ''; }
}
export function readSubmissionIntent(owner: string, key: string): SubmissionIntent | null {
  try { const intent = JSON.parse(sessionStorage.getItem('dayloom.task.intent.v1') || 'null');
    const generation = submissionGeneration(owner);
    return intent?.owner === owner && intent.key === key && intent.generation === generation ? intent : null;
  } catch { return null; }
}
export function rememberSubmissionIntent(owner: string, key: string, request: ProductPlanningInput, editor: Brief) {
  try { sessionStorage.setItem('dayloom.task.intent.v1', JSON.stringify({ owner, generation: submissionGeneration(owner), key, request, editor })); } catch { /* The server still enforces operation identity. */ }
}
