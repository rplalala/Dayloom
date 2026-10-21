import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { getTripDateWindow } from "../planning/api";
import { DestinationCombobox } from "../planning/components/DestinationCombobox";
import { PreferencePolisher } from "../planning/components/PreferencePolisher";
import { TripDateInput } from "../planning/components/TripDateInput";
import { isValidISODate, latestEndDate, type TripDateWindow } from "../planning/datePolicy";
import { currencies, isListedCurrency } from "../planning/currencies";
import { briefErrors, editPreferences, interestPrompts, pacePrompts, toggleInterest, togglePace, toggleTransport, transportLabels, type Brief, type Interest, type Pace, type Transport, type TextReplacement } from "./editor";
import { useSession } from "./session";
import { DraftControls } from "./DraftControls";
import "./editor.css";
import { taskRequest, TaskFailure, sameConfirmedRequest, submissionGeneration, readSubmissionIntent, rememberSubmissionIntent, taskActive, type PlanningTask } from './taskClient';
import { useTasks } from './taskContext';
import { planningInput } from './editor';

/** The single Product editor, shared by recovery and future drafts/submission. */
export function BriefPage() {
  const session = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const draftId = new URLSearchParams(location.search).get("draft");
  const { initializeNewBrief, briefOrigin, status } = session;
  useEffect(() => {
    if (!draftId && (status === "authenticated" || status === "guest") && briefOrigin === "new") void initializeNewBrief();
  }, [draftId, status, briefOrigin, initializeNewBrief]);
  const [dateWindow, setDateWindow] = useState<TripDateWindow | null>(null);
  const [dateError, setDateError] = useState(false);
  type SubmissionState = { owner?: string; csrf?: string; generation?: string; location?: string; editor?: Brief; busy?: boolean; message?: string; taskId?: string };
  const [submitState, setSubmitState] = useState<SubmissionState>({});
  const generation = session.account ? submissionGeneration(session.account.id) : '';
  const submission = submitState.owner === session.account?.id && submitState.csrf === session.account?.csrf_token && submitState.generation === generation && submitState.editor === session.brief && submitState.location === location.key ? submitState : {};
  const { tasks, refresh: refreshTasks } = useTasks();
  const mounted = useRef(false);
  const attempt = useRef(0);
  const context = useRef({ owner: session.account?.id, csrf: session.account?.csrf_token, location: location.key, editor: session.brief, action: session.actionId });
  useLayoutEffect(() => {
    context.current = { owner: session.account?.id, csrf: session.account?.csrf_token, location: location.key, editor: session.brief, action: session.actionId };
  });
  useLayoutEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [checked, setChecked] = useState(false);
  const [draftLoading, setDraftLoading] = useState(false);
  const notesInput = useRef<HTMLTextAreaElement>(null);
  const textEdit = useRef<(TextReplacement & { before: string }) | null>(null);
  const brief = session.brief;
  useEffect(() => {
    let active = true;
    getTripDateWindow().then(value => { if (active) setDateWindow(value); }, () => { if (active) setDateError(true); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    const node = notesInput.current;
    if (!node) return;
    function beforeInput(event: InputEvent) {
      if (!node) return;
      let start = node.selectionStart, end = node.selectionEnd;
      if (start === end && event.inputType === "deleteContentBackward") start = Math.max(0, start - 1);
      if (start === end && event.inputType === "deleteContentForward") end = Math.min(node.value.length, end + 1);
      textEdit.current = { before: node.value, start, end };
    }
    // Native beforeinput includes paste and unchanged replacements. React's
    // synthetic beforeinput/change pair can omit either of these edits.
    node.addEventListener("beforeinput", beforeInput);
    return () => {
      node.removeEventListener("beforeinput", beforeInput);
      textEdit.current = null;
    };
  }, [session.status]);
  function update(next: Brief) { session.editBrief(next); }
  function change(field: "destination" | "start_date" | "end_date" | "travelers" | "budget" | "currency" | "required" | "exclusions", value: string) { update({ ...brief, [field]: value }); }
  const errors = briefErrors(brief, dateWindow);
  const validBudget = brief.budget.trim() !== "" && Number.isFinite(Number(brief.budget)) && Number(brief.budget) >= 0 && isListedCurrency(brief.currency);
  const loginReturn = `/login?return=${encodeURIComponent(draftId ? `/plan?draft=${draftId}` : "/plan")}`;
  async function generate() {
    const initialKey = session.actionId || crypto.randomUUID();
    if (!session.actionId) { session.setActionId(initialKey); context.current.action = initialKey; }
    if (!session.account) { navigate('/login?return=/plan'); return; }
    setChecked(true);
    if (errors.length || !dateWindow || submission.busy) return;
    const account = session.account;
    const request = planningInput(brief, dateWindow);
    const sequence = ++attempt.current;
    const ownership = { owner: account.id, csrf: account.csrf_token, generation: submissionGeneration(account.id), location: location.key, editor: brief };
    let action = initialKey;
    let key: string | null = session.actionId;
    function ownsAction() {
      const current = context.current;
      return mounted.current && attempt.current === sequence && current.owner === account.id && current.csrf === ownership.csrf && current.location === ownership.location && current.editor === brief && current.action === action && submissionGeneration(account.id) === ownership.generation;
    }
    function show(value: Pick<SubmissionState, 'busy' | 'message' | 'taskId'>) {
      if (ownsAction()) setSubmitState({ ...ownership, ...value });
    }
    show({ busy: true });
    try {
      if (key) {
        const intended = readSubmissionIntent(account.id, key);
        const existing = await taskRequest<PlanningTask | null>(`/api/planning/tasks?operation_key=${encodeURIComponent(key)}`);
        if (!ownsAction()) return;
        if (existing && sameConfirmedRequest(existing.request, request)) {
          show({ message: 'Your submitted task is available. Open progress to continue.', taskId: existing.id });
          void refreshTasks(); return;
        }
        if (!existing && intended && !sameConfirmedRequest(intended.request, request)) {
          show({ message: 'An earlier submission is unresolved. Your new brief is retained. Check planning tasks before submitting another brief.' });
          return;
        }
        if (existing) key = null;
      }
      if (!ownsAction()) return;
      key = key || (session.actionId ? crypto.randomUUID() : initialKey);
      action = key;
      context.current.action = key;
      session.setActionId(key);
      rememberSubmissionIntent(account.id, key, request, brief);
      const task = await taskRequest<PlanningTask>('/api/planning/tasks', { csrf: account.csrf_token, body: { operation_key: key, request, editor_snapshot: brief } });
      if (!ownsAction()) return;
      show({ message: 'Planning has started. You can keep editing or save another brief.', taskId: task.id });
      void refreshTasks();
    } catch (error) {
      if (!ownsAction()) return;
      if (error instanceof TaskFailure) {
        if (error.status === 401) void session.refresh();
        show({ message: error.message, taskId: error.detail.task_id });
      } else {
        // Unknown write outcome: observe by identity; never automatically POST again.
        try {
          const recovered = key ? await taskRequest<PlanningTask | null>(`/api/planning/tasks?operation_key=${encodeURIComponent(key)}`) : null;
          if (!ownsAction()) return;
          show({ message: recovered ? 'Your task was accepted. Open progress to continue.' : 'The response was lost. Check planning tasks before explicitly trying again.', taskId: recovered?.id });
        } catch { show({ message: 'The response was lost. Check planning tasks when reconnected before explicitly trying again.' }); }
      }
    }
  }
  if (session.status === "loading") return <div className="page container" role="status">Checking your session…</div>;
  if (session.status === "expired") return <div className="page container"><h1>Log in to continue your brief.</h1><p>Your unsaved input is kept private until you return to the same account.</p><Link to={loginReturn} className="btn btn-primary">Log in</Link></div>;
  if (draftId && !session.account) return <div className="page container"><h1>Log in to open this draft.</h1><p>Planning drafts are private to their account.</p><Link to={loginReturn} className="btn btn-primary">Log in</Link></div>;

  return <div className="page container plan-page brief-editor">
    <div className="page-heading"><span className="eyebrow">YOUR JOURNEY, YOUR WAY</span><h1>A city journey, made yours.</h1><p>Pick a destination. Bring your ideas. Make every day a little clearer.</p></div>
    <section className="flow-card form-card">
      <DraftControls onLoading={setDraftLoading} />
      <div className="flow-title"><span className="step-number">01</span><div><h2>Tell us how you like to travel</h2><p>A few essentials, and the things that make it your trip.</p></div><span className="count-badge">About 1 minute</span></div>
      <form noValidate onSubmit={event => {
        event.preventDefault();
        void generate();
      }}>
        {session.defaultsApplied && <p className="subtle-help" role="status">Your travel defaults are shown below. Edit them for this trip.</p>}
        <fieldset className="form-fields" disabled={draftLoading}><legend className="visually-hidden">Travel brief</legend>
          <div className="brief-essentials">
            <DestinationCombobox value={brief.destination} onChange={value => change("destination", value)} disabled={false} />
            <TripDateInput label="Start date" value={brief.start_date} onChange={value => change("start_date", value)} min={dateWindow?.allowedStart} max={dateWindow?.allowedEnd} />
            <TripDateInput label="End date" value={brief.end_date} onChange={value => change("end_date", value)} min={isValidISODate(brief.start_date) ? brief.start_date : dateWindow?.allowedStart} max={dateWindow ? latestEndDate(brief.start_date, dateWindow) : undefined} />
            <label className="field"><span>Travelers</span><input type="number" min="1" step="1" required placeholder="2" value={brief.travelers} onChange={event => change("travelers", event.target.value)} /></label>
            <div className="brief-budget"><label className="field"><span>Whole-trip budget</span><input type="number" min="0" step="0.01" required placeholder="1000" value={brief.budget} onChange={event => change("budget", event.target.value)} /></label><label className="field"><span>Currency</span><select aria-label="Currency" value={brief.currency} required onChange={event => change("currency", event.target.value)}><option value="">Select currency</option>{currencies.map(value => <option key={value.code} value={value.code}>{value.code}</option>)}</select></label></div>
          </div>
          <div className="field-help-row"><p className="subtle-help">{dateWindow ? `Plan ${dateWindow.allowedStart}–${dateWindow.allowedEnd}, up to ${dateWindow.maxTripDays} days.` : dateError ? "Date limits could not be loaded. Reload to try again." : "Loading date limits…"}</p><p className="subtle-help">Budget is the total for all travelers.</p></div>
          <fieldset className="brief-choice-group"><legend>What are you drawn to?</legend><div className="interest-chips">{(Object.keys(interestPrompts) as Interest[]).map(value => <button key={value} type="button" className={`interest-chip ${brief.interests.includes(value) ? "selected" : ""}`} aria-pressed={brief.interests.includes(value)} onClick={() => update(toggleInterest(brief, value))}>{value}</button>)}</div></fieldset>
          <div className="preference-pair">
            <fieldset className="brief-choice-group"><legend>Travel pace</legend><div className="pace-row">{(Object.keys(pacePrompts) as Pace[]).map((value, index) => <button key={value} type="button" className={`pace-btn ${brief.pace === value ? "selected" : ""}`} aria-pressed={brief.pace === value} onClick={() => update(togglePace(brief, value))}><span>{["Take it slowly", "A little of both", "See a little more"][index]}</span><strong>{value[0].toUpperCase() + value.slice(1)}</strong></button>)}</div><p className="selection-help">Choose a rhythm for your days. Select again to clear.</p></fieldset>
            <fieldset className="brief-choice-group"><legend>Transport preferences</legend><div className="pace-row">{(Object.keys(transportLabels) as Transport[]).map(value => <button key={value} type="button" className={`pace-btn ${brief.transport.includes(value) ? "selected" : ""}`} aria-pressed={brief.transport.includes(value)} onClick={() => update(toggleTransport(brief, value))}><strong>{transportLabels[value]}</strong></button>)}</div><p className="selection-help">Choose one or more. Leave empty for no preference.</p></fieldset>
          </div>
          <div className="requirements-pair"><label className="field"><span>Places or experiences to include</span><input value={brief.required} onChange={event => change("required", event.target.value)} placeholder="An art museum, a waterfront walk…" /></label><label className="field"><span>Places or experiences to avoid</span><input value={brief.exclusions} onChange={event => change("exclusions", event.target.value)} placeholder="Large malls, very crowded places…" /></label></div>
          <label className="field notes-wide"><span>Additional preferences</span><textarea ref={notesInput} rows={5} value={brief.preferences} onInput={event => {
            const replacement = textEdit.current?.before === brief.preferences ? textEdit.current : undefined;
            textEdit.current = null;
            update(editPreferences(brief, event.currentTarget.value, replacement));
          }} onBlur={() => { textEdit.current = null; }} aria-describedby="preference-sync-help" placeholder="Tell us about slow mornings, accessibility needs, or anything else that matters…" /></label>
          <p className="subtle-help" id="preference-sync-help">Your selections appear here. Edit any sentence to make it your own.</p>
          <PreferencePolisher text={brief.preferences} context={{
            ...(brief.destination.trim() && { destination: brief.destination.trim() }),
            ...(isValidISODate(brief.start_date) && { start_date: brief.start_date }),
            ...(isValidISODate(brief.end_date) && { end_date: brief.end_date }),
            ...(/^[1-9]\d*$/.test(brief.travelers) && Number.isSafeInteger(Number(brief.travelers)) && { traveler_count: Number(brief.travelers) }),
            ...(validBudget && { budget: { amount: brief.budget, currency: brief.currency } }),
          }} disabled={false} onApply={value => update(editPreferences(brief, value))} />
        </fieldset>
        {checked && errors.length > 0 && <div className="form-error" role="alert"><ul>{errors.map(error => <li key={error}>{error}</li>)}</ul></div>}
        <div className="form-bottom"><p>City sights and experiences. Accommodation, tickets and travel to your destination are not included.</p><button type="submit" disabled={draftLoading || submission.busy} className="btn btn-primary btn-large">{submission.busy ? 'Submitting…' : 'Generate itinerary →'}</button></div>
        {submission.message && <p className="subtle-help" role="status">{submission.message} {submission.taskId && <Link to={`/planning/${submission.taskId}`}>Open task progress →</Link>}</p>}
      </form>
    </section>
    <section className="flow-card"><div className="flow-title"><span className="step-number">02</span><div><h2>Planning progress</h2><p>{tasks.find(taskActive)?.progress.message || 'Ready when you are.'}</p></div></div>{session.account && <Link to="/planning">Open planning tasks and recoverable previews →</Link>}</section>
    <section className="flow-card"><div className="flow-title"><span className="step-number">03</span><div><h2>Your itinerary</h2><p>Preview every day. Save it when it feels right.</p></div></div><div className="result-placeholder"><strong>A new journey is waiting.</strong><p>Fill in your travel brief. Your day-by-day itinerary will appear here.</p></div></section>
  </div>;
}
