import { isListedCurrency } from "../planning/currencies";
import { isDateWithinTripWindow, latestEndDate, type TripDateWindow } from "../planning/datePolicy";
import type { ProductPlanningInput } from "../planning/types";

export const interestPrompts = {
  "City walks": "Enjoy neighborhood walks, local architecture and everyday city life.",
  "History & culture": "Explore historic districts, cultural landmarks and museums.",
  "Art & museums": "Visit art galleries and museums, with time to enjoy each stop.",
  Nature: "Enjoy parks, waterfronts and gentle outdoor experiences.",
  "Local food": "Discover local food, with optional places to eat along the way.",
  Photography: "Include scenic viewpoints and time for photography.",
  "Family experiences": "Include family-friendly experiences and time to rest.",
  "Free exploration": "Leave some unscheduled time for independent exploration.",
} as const;
export type Interest = keyof typeof interestPrompts;
export const pacePrompts = {
  relaxed: "Travel pace: relaxed. Allow generous time at each stop and fewer transfers.",
  balanced: "Travel pace: balanced. Balance the main sights with time to rest.",
  rich: "Travel pace: rich. Include more experiences where time and connections allow.",
} as const;
export type Pace = keyof typeof pacePrompts;
export const transportLabels = { walk: "Walking", transit: "Public transit", drive: "Driving" } as const;
export type Transport = keyof typeof transportLabels;
type BindingKey = `interest:${Interest}` | "pace" | "transport";
export type PromptBinding = { key: BindingKey; start: number; end: number; text: string };
export type TextReplacement = { start: number; end: number };
export type Brief = {
  editor_version: 1;
  destination: string;
  start_date: string;
  end_date: string;
  travelers: string;
  budget: string;
  currency: string;
  required: string;
  exclusions: string;
  preferences: string;
  interests: Interest[];
  pace: Pace | null;
  transport: Transport[];
  bindings: PromptBinding[];
};

export function createBrief(): Brief {
  return { editor_version: 1, destination: "", start_date: "", end_date: "", travelers: "", budget: "", currency: "AUD", required: "", exclusions: "", preferences: "", interests: [], pace: null, transport: [], bindings: [] };
}

function transportPrompt(values: Transport[]): string {
  return values.length ? `Prefer ${values.map(value => transportLabels[value].toLowerCase()).join(" and ")} where practical.` : "";
}

function detach(brief: Brief, key: BindingKey) {
  if (key === "pace") brief.pace = null;
  else if (key === "transport") brief.transport = [];
  else brief.interests = brief.interests.filter(value => key !== `interest:${value}`);
}

/** Restore only exact, versioned metadata; never search the text to recover ownership. */
export function restoreBrief(value: unknown): Brief {
  const brief = createBrief();
  if (!value || typeof value !== "object") return brief;
  const saved = value as Record<string, unknown>;
  for (const field of ["destination", "start_date", "end_date", "travelers", "budget", "currency", "required", "exclusions", "preferences"] as const) {
    if (typeof saved[field] === "string") brief[field] = saved[field];
  }
  if (saved.editor_version !== 1) return brief;
  brief.interests = Array.isArray(saved.interests) ? [...new Set(saved.interests.filter((v): v is Interest => typeof v === "string" && Object.hasOwn(interestPrompts, v)))] : [];
  brief.pace = typeof saved.pace === "string" && Object.hasOwn(pacePrompts, saved.pace) ? saved.pace as Pace : null;
  brief.transport = Array.isArray(saved.transport) ? [...new Set(saved.transport.filter((v): v is Transport => typeof v === "string" && Object.hasOwn(transportLabels, v)))] : [];
  const expected = new Map<string, string>(brief.interests.map(v => [`interest:${v}`, interestPrompts[v]]));
  if (brief.pace) expected.set("pace", pacePrompts[brief.pace]);
  if (brief.transport.length) expected.set("transport", transportPrompt(brief.transport));
  if (Array.isArray(saved.bindings)) {
    const candidates = saved.bindings.filter((v): v is PromptBinding => !!v && typeof v === "object" && typeof v.key === "string");
    for (const binding of candidates) {
      const valid = Number.isInteger(binding.start) && Number.isInteger(binding.end) && binding.start >= 0 && binding.end > binding.start && binding.end <= brief.preferences.length &&
        expected.get(binding.key) === binding.text && brief.preferences.slice(binding.start, binding.end) === binding.text &&
        candidates.filter(v => v.key === binding.key).length === 1 &&
        !candidates.some(v => v !== binding && v.start < binding.end && v.end > binding.start);
      if (valid) brief.bindings.push({ key: binding.key, start: binding.start, end: binding.end, text: binding.text });
      else detach(brief, binding.key);
    }
  }
  return brief;
}

/** A single text replacement shifts outside spans and relinquishes every touched span. */
export function editPreferences(source: Brief, text: string, replacement?: TextReplacement): Brief {
  if (source.preferences === text && !replacement) return source;
  const brief = { ...source, bindings: [] as PromptBinding[] };
  const old = source.preferences;
  let start = 0, suffix = 0;
  while (start < old.length && start < text.length && old[start] === text[start]) start++;
  while (suffix < old.length && suffix < text.length && old[old.length - suffix - 1] === text[text.length - suffix - 1]) suffix++;
  const common = Math.min(old.length, text.length);
  // Repeated identical text can admit several edit locations. Relinquish every
  // potentially touched span rather than silently moving ownership to user text.
  const ambiguous = start + suffix > common;
  let end = ambiguous ? start + Math.max(0, old.length - text.length) : old.length - suffix;
  if (ambiguous) start = common - suffix;
  const delta = text.length - old.length;
  if (replacement) {
    const inserted = replacement.end - replacement.start + delta;
    if (Number.isInteger(replacement.start) && Number.isInteger(replacement.end) && replacement.start >= 0 && replacement.end >= replacement.start && replacement.end <= old.length && inserted >= 0 && old.slice(0, replacement.start) === text.slice(0, replacement.start) && old.slice(replacement.end) === text.slice(replacement.start + inserted)) {
      start = replacement.start;
      end = replacement.end;
    }
  }
  for (const binding of source.bindings) {
    if (old.slice(binding.start, binding.end) !== binding.text) { detach(brief, binding.key); continue; }
    if (binding.end <= start) brief.bindings.push(binding);
    else if (binding.start >= end) brief.bindings.push({ ...binding, start: binding.start + delta, end: binding.end + delta });
    else detach(brief, binding.key);
  }
  brief.preferences = text;
  return brief;
}

function setPrompt(source: Brief, key: BindingKey, text: string): Brief {
  let brief = { ...source, bindings: [...source.bindings] };
  const owned = brief.bindings.find(v => v.key === key && brief.preferences.slice(v.start, v.end) === v.text);
  if (owned) {
    let { start, end } = owned;
    if ((start === 0 || brief.preferences[start - 1] === "\n") && (end === brief.preferences.length || brief.preferences[end] === "\n")) {
      if (end < brief.preferences.length) end++; else if (start > 0) start--;
    }
    brief.bindings = brief.bindings.filter(v => v.key !== key).map(v => v.start >= end ? { ...v, start: v.start - (end - start), end: v.end - (end - start) } : v);
    brief.preferences = brief.preferences.slice(0, start) + brief.preferences.slice(end);
  }
  if (!text || brief.preferences.split("\n").includes(text)) return brief;
  const separator = brief.preferences && !brief.preferences.endsWith("\n") ? "\n" : "";
  const start = brief.preferences.length + separator.length;
  brief = { ...brief, preferences: brief.preferences + separator + text, bindings: [...brief.bindings, { key, start, end: start + text.length, text }] };
  return brief;
}

export function toggleInterest(brief: Brief, value: Interest): Brief {
  const selected = brief.interests.includes(value);
  return setPrompt({ ...brief, interests: selected ? brief.interests.filter(v => v !== value) : [...brief.interests, value] }, `interest:${value}`, selected ? "" : interestPrompts[value]);
}
export function togglePace(brief: Brief, value: Pace): Brief {
  const pace = brief.pace === value ? null : value;
  return setPrompt({ ...brief, pace }, "pace", pace ? pacePrompts[pace] : "");
}
export function toggleTransport(brief: Brief, value: Transport): Brief {
  const transport = brief.transport.includes(value) ? brief.transport.filter(v => v !== value) : [...brief.transport, value];
  return setPrompt({ ...brief, transport }, "transport", transportPrompt(transport));
}

export function briefErrors(brief: Brief, window: TripDateWindow | null): string[] {
  const errors: string[] = [];
  if (!brief.destination.trim()) errors.push("Enter a destination.");
  if (!window) errors.push("Date limits must load before continuing.");
  else if (!isDateWithinTripWindow(brief.start_date, window) || !isDateWithinTripWindow(brief.end_date, window)) errors.push(`Enter real dates between ${window.allowedStart} and ${window.allowedEnd}, using YYYY-MM-DD.`);
  else if (brief.end_date < brief.start_date) errors.push("End date must be on or after the start date.");
  else if (brief.end_date > latestEndDate(brief.start_date, window)) errors.push(`Trips may last at most ${window.maxTripDays} days, including both dates.`);
  if (!/^[1-9]\d*$/.test(brief.travelers) || !Number.isSafeInteger(Number(brief.travelers))) errors.push("Enter a whole number of travelers greater than zero.");
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(brief.budget) || !Number.isFinite(Number(brief.budget)) || Number(brief.budget) < 0 || !isListedCurrency(brief.currency)) errors.push("Enter a finite non-negative whole-trip budget and select a supported currency.");
  if (composedPreferences(brief).length > 24000) errors.push("Preferences may contain at most 24,000 characters, including required and avoided experiences.");
  return errors;
}

export function composedPreferences(brief: Brief): string {
  return [brief.required.trim() ? `Must include: ${brief.required.trim()}.` : "", brief.exclusions.trim() ? `Please avoid: ${brief.exclusions.trim()}.` : "", brief.preferences].filter(Boolean).join("\n");
}

/** Compose visible inputs into the existing request contract only at explicit submission. */
export function planningInput(brief: Brief, window: TripDateWindow): ProductPlanningInput {
  const errors = briefErrors(brief, window);
  if (errors.length) throw new Error(errors.join(" "));
  const additional_preferences = composedPreferences(brief);
  return { destination: brief.destination, start_date: brief.start_date, end_date: brief.end_date, traveler_count: Number(brief.travelers), budget: { amount: brief.budget, currency: brief.currency }, ...(additional_preferences.trim() && { additional_preferences }) };
}
