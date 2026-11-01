import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { getTripDateWindow } from "../planning/api";
import { DestinationCombobox } from "../planning/components/DestinationCombobox";
import { PreferencePolisher } from "../planning/components/PreferencePolisher";
import { TripDateInput } from "../planning/components/TripDateInput";
import { isValidISODate, latestEndDate, type TripDateWindow } from "../planning/datePolicy";
import { currencies, isListedCurrency } from "../planning/currencies";
import { briefErrors, createBrief, editPreferences, interestPrompts, pacePrompts, toggleInterest, togglePace, toggleTransport, transportLabels, type Brief, type Interest, type Pace, type Transport, type TextReplacement } from "./editor";
import { useSession } from "./session";
import { DraftControls, type DraftActionsHandle } from "./DraftControls";
import "./editor.css";
import { Icon } from "./Icon";
import { PlanProgress, PlanResult, BusyPlanningDialog } from "./PlanOutput";
import { usePlanTask } from "./usePlanTask";
import { planTaskLink, taskRequest, TaskFailure, sameConfirmedRequest, submissionGeneration, readSubmissionIntent, rememberSubmissionIntent, taskActive, type PlanningTask } from './taskClient';
import { useTasks } from './taskContext';
import { planningInput } from './editor';

const moodChoices: Record<string, Interest[]> = { art: ["Art & museums", "History & culture"], nature: ["Nature", "Free exploration"], city: ["City walks", "History & culture"] };

/** The single Product editor, shared by recovery and future drafts/submission. */
export function BriefPage() {
  const session = useSession();
  const navigate = useNavigate();
  const draftActions = useRef<DraftActionsHandle>(null);
  const location = useLocation();
  const draftId = new URLSearchParams(location.search).get("draft");
  const { initializeNewBrief, briefOrigin, status } = session;
  const mood = (location.state as { mood?: string } | null)?.mood;
  const hasMood = Boolean(mood && moodChoices[mood]);
  const liveEditor = useRef({ session, location: location.key });
  liveEditor.current = { session, location: location.key };
  useEffect(() => {
    if (!hasMood && !draftId && (status === "authenticated" || status === "guest") && briefOrigin === "new") void initializeNewBrief();
  }, [draftId, status, briefOrigin, initializeNewBrief, hasMood]);
  const appliedMood = useRef<string | null>(null);
  useEffect(() => {
    if (!mood || !hasMood || appliedMood.current === location.key || draftId || (status !== "guest" && status !== "authenticated")) return;
    appliedMood.current = location.key;
    const key = location.key;
    const owner = session.account?.id;
    void initializeNewBrief().then(() => {
      const current = liveEditor.current;
      if (current.location !== key || current.session.account?.id !== owner || !["guest", "authenticated"].includes(current.session.status)) return;
      let next = current.session.brief;
      for (const interest of moodChoices[mood]) if (!next.interests.includes(interest)) next = toggleInterest(next, interest);
      if (next.pace !== "relaxed") next = togglePace(next, "relaxed");
      current.session.editBrief(next);
    });
  }, [mood, hasMood, location.key, draftId, status, session.account?.id, initializeNewBrief]);
  const [dateWindow, setDateWindow] = useState<TripDateWindow | null>(null);
  const [dateError, setDateError] = useState(false);
  type SubmissionState = { owner?: string; csrf?: string; generation?: string; location?: string; editor?: Brief; busy?: boolean; message?: string; taskId?: string; activeConflict?: boolean };
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
  const [preferencesOpen, setPreferencesOpen] = useState<boolean | null>(null);
  const [clearRevision, setClearRevision] = useState(0);
  const notesInput = useRef<HTMLTextAreaElement>(null);
  const textEdit = useRef<(TextReplacement & { before: string }) | null>(null);
  const brief = session.brief;
  const hasPreferences = Boolean(brief.preferences || brief.required || brief.exclusions || brief.interests.length || brief.pace || brief.transport.length);
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
  function clearBrief() {
    if (draftLoading || submission.busy) return;
    attempt.current++;
    // An intentionally blank brief must not reapply account defaults.
    session.replaceBrief(createBrief(), "restored");
    setSubmitState({});
    setChecked(false);
    setPreferencesOpen(false);
    textEdit.current = null;
    setClearRevision(value => value + 1);
    navigate("/plan", { replace: true, state: null });
  }
  function change(field: "destination" | "start_date" | "end_date" | "travelers" | "budget" | "currency" | "required" | "exclusions", value: string) { update({ ...brief, [field]: value }); }
  const errors = briefErrors(brief, dateWindow);
  const matchingTask = dateWindow && !errors.length ? tasks.find(task => task.request?.budget && sameConfirmedRequest(task.request, planningInput(brief, dateWindow))) : undefined;
  const selectedTaskId = submission.taskId || new URLSearchParams(location.search).get("task");
  const observed = usePlanTask(selectedTaskId, tasks.find(taskActive) || matchingTask || tasks[0]);
  useEffect(() => {
    if (!location.hash || session.status !== 'authenticated') return;
    document.getElementById(location.hash.slice(1))?.scrollIntoView?.({ block: 'start' });
  }, [location.key, location.hash, session.status]);
  const validBudget = brief.budget.trim() !== "" && Number.isFinite(Number(brief.budget)) && Number(brief.budget) >= 0 && isListedCurrency(brief.currency);
  const loginReturn = `/login?return=${encodeURIComponent(`/plan${location.search}${location.hash}`)}`;
  async function generate(restart = false) {
    const initialKey = (restart ? null : session.actionId) || crypto.randomUUID();
    if (restart || !session.actionId) { session.setActionId(initialKey); context.current.action = initialKey; }
    if (!session.account) { navigate(loginReturn); return; }
    setChecked(true);
    if (errors.some(error => error.startsWith("Preferences"))) setPreferencesOpen(true);
    if (errors.length || !dateWindow || submission.busy) return;
    const account = session.account;
    const request = planningInput(brief, dateWindow);
    const sequence = ++attempt.current;
    const ownership = { owner: account.id, csrf: account.csrf_token, generation: submissionGeneration(account.id), location: location.key, editor: brief };
    let action = initialKey;
    let key: string | null = restart ? null : session.actionId;
    function ownsAction() {
      const current = context.current;
      return mounted.current && attempt.current === sequence && current.owner === account.id && current.csrf === ownership.csrf && current.location === ownership.location && current.editor === brief && current.action === action && submissionGeneration(account.id) === ownership.generation;
    }
    function show(value: Pick<SubmissionState, 'busy' | 'message' | 'taskId' | 'activeConflict'>) {
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
          show({ message: 'An earlier submission is unresolved. Your new brief is retained. Check planning progress before submitting another brief.' });
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
      navigate(planTaskLink(task.id));
    } catch (error) {
      if (!ownsAction()) return;
      if (error instanceof TaskFailure) {
        if (error.status === 401) void session.refresh();
        show({ message: error.message, taskId: error.detail.task_id, activeConflict: error.status === 409 && error.detail.code === "planning_task_active" });
      } else {
        // Unknown write outcome: observe by identity; never automatically POST again.
        try {
          const recovered = key ? await taskRequest<PlanningTask | null>(`/api/planning/tasks?operation_key=${encodeURIComponent(key)}`) : null;
          if (!ownsAction()) return;
          show({ message: recovered ? 'Your task was accepted. Open progress to continue.' : 'The response was lost. Check planning progress before explicitly trying again.', taskId: recovered?.id });
        } catch { show({ message: 'The response was lost. Check planning progress when reconnected before explicitly trying again.' }); }
      }
    }
  }
  if (session.status === "loading") return <div className="page container" role="status">Checking your session…</div>;
  if (session.status === "expired") return <div className="page container"><h1>Log in to continue your brief.</h1><p>Your unsaved input is kept private until you return to the same account.</p><Link to={loginReturn} className="btn btn-primary">Log in</Link></div>;
  if (draftId && !session.account) return <div className="page container"><h1>Log in to open this draft.</h1><p>Planning drafts are private to their account.</p><Link to={loginReturn} className="btn btn-primary">Log in</Link></div>;

  return <div className="page container plan-page brief-editor">
    <div className="page-heading"><span className="eyebrow">YOUR JOURNEY, YOUR WAY</span><h1>Where will you go next?</h1><p>Start with the essentials. Make room for what you love.</p></div>
    <section className="flow-card form-card" id="travel-brief">
      <div className="flow-title"><span className="step-number">01</span><div><h2>Your travel brief</h2></div><span className="count-badge">About 1 minute</span></div>
      <form noValidate onSubmit={event => {
        event.preventDefault();
        void generate();
      }}>

        <fieldset className="form-fields" disabled={draftLoading}><legend className="visually-hidden">Travel brief</legend>
          <div className="form-grid form-grid-essentials" key={clearRevision}>
            <DestinationCombobox label={<span><Icon name="pin" size={16} /> Destination <b aria-hidden="true">*</b></span>} placeholder="Choose or enter a city" value={brief.destination} onChange={value => change("destination", value)} disabled={false} />
            <TripDateInput labelContent={<span><Icon name="calendar" size={16} /> Start date <b aria-hidden="true">*</b></span>} label="Start date" value={brief.start_date} onChange={value => change("start_date", value)} min={dateWindow?.allowedStart} max={dateWindow?.allowedEnd} />
            <TripDateInput labelContent={<span><Icon name="calendar" size={16} /> End date <b aria-hidden="true">*</b></span>} label="End date" value={brief.end_date} onChange={value => change("end_date", value)} min={isValidISODate(brief.start_date) ? brief.start_date : dateWindow?.allowedStart} max={dateWindow ? latestEndDate(brief.start_date, dateWindow) : undefined} />
            <label className="field"><span><Icon name="users" size={16} /> Travelers <b aria-hidden="true">*</b></span><input aria-label="Travelers" type="number" min="1" step="1" required placeholder="2" value={brief.travelers} onChange={event => change("travelers", event.target.value)} /></label>
            <label className="field"><span><Icon name="leaf" size={16} /> Whole-trip budget <b aria-hidden="true">*</b></span><span className="budget-input"><input aria-label="Whole-trip budget" type="number" min="0" step="0.01" required placeholder="1000" value={brief.budget} onChange={event => change("budget", event.target.value)} /><select aria-label="Currency" value={brief.currency} required onChange={event => change("currency", event.target.value)}><option value="">Select currency</option>{currencies.map(value => <option key={value.code} value={value.code}>{value.code}</option>)}</select></span></label>
          </div>
          <div className="field-help-row"><p className="subtle-help">{dateWindow ? `Plan ${dateWindow.allowedStart}–${dateWindow.allowedEnd}, up to ${dateWindow.maxTripDays} days.` : dateError ? "Date limits could not be loaded. Reload to try again." : "Loading date limits…"}</p></div>
          <details className="optional-preferences" open={preferencesOpen ?? hasPreferences} onToggle={event => setPreferencesOpen(event.currentTarget.open)}>
            <summary><Icon name="sliders" size={18} /><span><strong>Personalize your trip</strong><small>{hasPreferences ? "Preferences added · review or edit" : "Optional · interests, pace, transport and places"}</small></span><Icon name="chevron" size={17} /></summary>
          <fieldset className="field-group brief-choice-group"><legend className="label-row"><Icon name="spark" size={16} /> <strong>Experiences you love</strong></legend><div className="chips">{(Object.keys(interestPrompts) as Interest[]).map(value => <button key={value} type="button" className={`chip ${brief.interests.includes(value) ? "active" : ""}`} aria-pressed={brief.interests.includes(value)} onClick={() => update(toggleInterest(brief, value))}><Icon name={brief.interests.includes(value) ? "check" : "plus"} size={14} /> {value}</button>)}</div></fieldset>
          <div className="preference-pair">
            <fieldset className="field-group brief-choice-group"><legend className="label-row"><Icon name="sliders" size={16} /> <strong>Travel pace</strong></legend><div className="pace-row">{(Object.keys(pacePrompts) as Pace[]).map((value, index) => <button key={value} type="button" aria-label={value[0].toUpperCase() + value.slice(1)} className={`pace-btn ${brief.pace === value ? "selected" : ""}`} aria-pressed={brief.pace === value} onClick={() => update(togglePace(brief, value))}><span>{["Take it slowly", "A little of both", "See a little more"][index]}</span><strong>{value[0].toUpperCase() + value.slice(1)}</strong></button>)}</div></fieldset>
            <fieldset className="field-group brief-choice-group transport-selection"><legend className="label-row"><Icon name="route" size={16} /> <strong>Transport preferences</strong></legend><div className="pace-row">{(Object.keys(transportLabels) as Transport[]).map(value => <button key={value} type="button" className={`pace-btn ${brief.transport.includes(value) ? "selected" : ""}`} aria-pressed={brief.transport.includes(value)} onClick={() => update(toggleTransport(brief, value))}><span><Icon name={value === "walk" ? "walk" : value === "transit" ? "bus" : "car"} size={17} /></span><strong>{transportLabels[value]}</strong></button>)}</div></fieldset>
          </div>
          <div className="requirements-pair"><label className="field"><span><Icon name="bookmark" size={16} /> Places or experiences to include <small aria-hidden="true">Optional</small></span><input aria-label="Places or experiences to include" value={brief.required} onChange={event => change("required", event.target.value)} placeholder="An art museum, a waterfront walk…" /></label><label className="field"><span><Icon name="close" size={16} /> Places or experiences to avoid <small aria-hidden="true">Optional</small></span><input aria-label="Places or experiences to avoid" value={brief.exclusions} onChange={event => change("exclusions", event.target.value)} placeholder="Large malls, very crowded places…" /></label></div>
          <label className="field notes-wide"><span><Icon name="edit" size={16} /> Additional preferences <small aria-hidden="true">Optional</small></span><textarea aria-label="Additional preferences" id="plan-notes" ref={notesInput} rows={5} value={brief.preferences} onInput={event => {
            const replacement = textEdit.current?.before === brief.preferences ? textEdit.current : undefined;
            textEdit.current = null;
            update(editPreferences(brief, event.currentTarget.value, replacement));
          }} onBlur={() => { textEdit.current = null; }} placeholder="Tell us about slow mornings, accessibility needs, or anything else that matters…" /></label>
          <PreferencePolisher key={clearRevision} product buttonIcon={<Icon name="spark" size={15} />} text={brief.preferences} context={{
            ...(brief.destination.trim() && { destination: brief.destination.trim() }),
            ...(isValidISODate(brief.start_date) && { start_date: brief.start_date }),
            ...(isValidISODate(brief.end_date) && { end_date: brief.end_date }),
            ...(/^[1-9]\d*$/.test(brief.travelers) && Number.isSafeInteger(Number(brief.travelers)) && { traveler_count: Number(brief.travelers) }),
            ...(validBudget && { budget: { amount: brief.budget, currency: brief.currency } }),
          }} disabled={false} onApply={value => update(editPreferences(brief, value))} />
          </details>
        </fieldset>
        {checked && errors.length > 0 && <div className="form-error" role="alert"><ul>{errors.map(error => <li key={error}>{error}</li>)}</ul></div>}
        <div className="form-bottom"><p><Icon name="shield" size={16} /> City sights and experiences. Accommodation, tickets and travel to your destination are not included.</p><button type="submit" disabled={draftLoading || submission.busy} className="btn btn-primary btn-large"><Icon name="spark" size={18} /> {submission.busy ? 'Submitting…' : 'Generate itinerary'} <Icon name="arrow" size={17} /></button></div>
        <DraftControls key={clearRevision} actionsRef={draftActions} onLoading={setDraftLoading} onClear={clearBrief} clearDisabled={draftLoading || !!submission.busy} />
        {submission.message && <p className="subtle-help" role="status">{submission.message} {submission.taskId && <Link to={planTaskLink(submission.taskId)}>Open task progress →</Link>}</p>}
      </form>
    </section>
    {submission.activeConflict && <BusyPlanningDialog taskId={submission.taskId} close={() => setSubmitState(previous => ({ ...previous, activeConflict: false }))} save={async () => { await draftActions.current?.save(); }} />}
    {(observed.task || observed.error || observed.loading || selectedTaskId || location.hash === '#generation-progress') && <PlanProgress task={observed.task} error={observed.error} loading={observed.loading} check={observed.check} onUpdate={observed.update} loginHref={!session.account && selectedTaskId ? loginReturn : undefined} submitting={submission.busy} onGenerateAgain={observed.task && dateWindow && !errors.length && sameConfirmedRequest(observed.task.request, planningInput(brief, dateWindow)) ? () => void generate(true) : undefined} />}
    <PlanResult key={`${session.account?.id}:${session.account?.csrf_token}:${observed.task?.id || "empty"}:${new URLSearchParams(location.search).get("preview") || ""}:${generation}`} task={observed.task} previewId={new URLSearchParams(location.search).get("preview") || undefined} />
  </div>;
}
