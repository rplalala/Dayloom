import { expect, it } from "vitest";
import { createBrief, editPreferences, toggleInterest, togglePace, toggleTransport, restoreBrief, planningInput, briefErrors } from "./editor";

it("owns inserted sentences and preserves manually identical lines", () => {
  let brief = createBrief();
  brief = editPreferences(brief, "Enjoy parks, waterfronts and gentle outdoor experiences.");
  brief = toggleInterest(brief, "Nature");
  expect(brief.bindings).toEqual([]);
  brief = toggleInterest(brief, "Nature");
  expect(brief.preferences).toBe("Enjoy parks, waterfronts and gentle outdoor experiences.");
  brief = togglePace(brief, "relaxed");
  brief = togglePace(brief, "rich");
  expect(brief.preferences).toContain("Travel pace: rich.");
  expect(brief.preferences).not.toContain("Travel pace: relaxed.");
});

it("shifts ownership around outside edits, detaches inside edits, and never deletes the user's version", () => {
  let brief = toggleInterest(togglePace(createBrief(), "balanced"), "Nature");
  brief = editPreferences(brief, "My own line\n" + brief.preferences);
  expect(brief.pace).toBe("balanced");
  brief = editPreferences(brief, brief.preferences.replace("parks", "quiet parks"));
  expect(brief.interests).toEqual([]);
  expect(brief.pace).toBe("balanced");
  brief = togglePace(brief, "balanced");
  expect(brief.preferences).toBe("My own line\nEnjoy quiet parks, waterfronts and gentle outdoor experiences.");
});

it("discards stale, overlapping and unknown-version saved ownership without guessing", () => {
  const brief = togglePace(createBrief(), "balanced");
  expect(restoreBrief(JSON.parse(JSON.stringify(brief)))).toEqual(brief);
  const stale = { ...brief, bindings: [{ ...brief.bindings[0], end: brief.preferences.length + 10 }] };
  expect(restoreBrief(stale).bindings).toEqual([]);
  expect(restoreBrief(stale).pace).toBeNull();
  expect(restoreBrief({ ...brief, editor_version: 999 }).bindings).toEqual([]);
  expect(restoreBrief({ ...brief, bindings: [...brief.bindings, brief.bindings[0]] }).pace).toBeNull();
  expect(restoreBrief({ preferences: brief.preferences }).preferences).toBe(brief.preferences);
});

it("keeps pace one-or-none and transport one/many/none as soft priorities through recovery", () => {
  let brief = toggleTransport(createBrief(), "walk");
  brief = toggleTransport(brief, "transit");
  expect(brief.preferences).toBe("Prefer walking and public transit where practical.");
  brief = restoreBrief(JSON.parse(JSON.stringify(brief)));
  brief = toggleTransport(brief, "walk");
  expect(brief.preferences).toBe("Prefer public transit where practical.");
  brief = toggleTransport(brief, "transit");
  expect(brief.preferences).toBe("");
  brief = togglePace(togglePace(brief, "relaxed"), "relaxed");
  expect(brief.pace).toBeNull();
  expect(brief.preferences).toBe("");
});

it("handles insertions at owned boundaries and clears all transport choices after an inside edit", () => {
  let brief = toggleTransport(createBrief(), "walk");
  brief = editPreferences(brief, "Before " + brief.preferences);
  brief = editPreferences(brief, brief.preferences + " After");
  expect(brief.transport).toEqual(["walk"]);
  // Both boundaries stay unowned; only the exact sentence can be removed.
  brief = toggleTransport(brief, "walk");
  expect(brief.preferences).toBe("Before  After");
  brief = toggleTransport(toggleTransport(createBrief(), "walk"), "drive");
  brief = editPreferences(brief, brief.preferences.replace("practical", "possible"));
  expect(brief.transport).toEqual([]);
  expect(brief.preferences).toBe("Prefer walking and driving where possible.");
});

it("does not transfer ownership to an identical manual line after ambiguous deletion", () => {
  let brief = toggleInterest(createBrief(), "Nature");
  const sentence = brief.preferences;
  brief = editPreferences(brief, sentence + "\n" + sentence);
  brief = editPreferences(brief, sentence);
  brief = toggleInterest(brief, "Nature");
  expect(brief.preferences).toBe(sentence);
});

it("uses a known edit range to keep outside duplicate insertions unowned and detach same-text replacement", () => {
  let brief = toggleInterest(createBrief(), "Nature");
  const sentence = brief.preferences;
  brief = editPreferences(brief, sentence + "\n" + sentence, { start: sentence.length, end: sentence.length });
  expect(brief.interests).toEqual(["Nature"]);
  brief = toggleInterest(brief, "Nature");
  expect(brief.preferences).toBe(sentence);
  brief = toggleInterest(createBrief(), "Nature");
  brief = editPreferences(brief, sentence, { start: 0, end: sentence.length });
  expect(brief.interests).toEqual([]);
  expect(brief.preferences).toBe(sentence);
});

const window = { allowedStart: "2026-10-21", allowedEnd: "2026-11-03", maxTripDays: 10 };
const complete = { ...createBrief(), destination: "Kyoto", start_date: "2026-10-21", end_date: "2026-10-30", travelers: "2", budget: "0", required: "Art museum", exclusions: "Large malls", preferences: "Keep my words." };

it("composes only visible requirements into the unchanged PlanningRequest boundary", () => {
  expect(planningInput(complete, window)).toEqual({ destination: "Kyoto", start_date: "2026-10-21", end_date: "2026-10-30", traveler_count: 2, budget: { amount: "0", currency: "AUD" }, additional_preferences: "Must include: Art museum.\nPlease avoid: Large malls.\nKeep my words." });
  expect(briefErrors(complete, window)).toEqual([]);
});

it("rejects impossible, ambiguous, reversed, unsupported and overlong date-only values", () => {
  for (const patch of [{ start_date: "2026-02-30" }, { start_date: "10/21/2026" }, { start_date: "2026-10-31" }, { start_date: "2026-10-20" }, { end_date: "2026-11-04" }, { end_date: "2026-10-31" }]) {
    expect(briefErrors({ ...complete, ...patch }, window).length).toBeGreaterThan(0);
  }
  const leap = { allowedStart: "2028-02-28", allowedEnd: "2028-03-12", maxTripDays: 10 };
  expect(briefErrors({ ...complete, start_date: "2028-02-29", end_date: "2028-03-01" }, leap)).toEqual([]);
});

it("rejects invalid numeric/currency domains and the public preference character ceiling", () => {
  for (const patch of [{ travelers: "1.5" }, { travelers: "0" }, { travelers: "1e2" }, { budget: "" }, { budget: "-1" }, { budget: "Infinity" }, { currency: "XYZ" }, { preferences: "x".repeat(24001) }]) {
    expect(briefErrors({ ...complete, ...patch }, window).length).toBeGreaterThan(0);
  }
});
