import { isDialogBackdropClick } from '../../shared/dialog';
import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Icon } from "./Icon";
import { PreviewDecisionControls, DecisionReceipt } from "./PreviewDecision";
import { TaskActions, TaskOutcome } from "./TaskActions";
import { planTaskLink, taskActive, taskRequest, TaskFailure, type PlanningTask, type Preview } from "./taskClient";
import { useSession } from "./session";
import { useTasks } from "./taskContext";
import { UnsavedPreviews } from "./tasks";
import { CuratedPhoto } from "./detail/MediaPhoto";
import type { ExampleCard, ProductDetail } from "./detail/types";
import { destinationCover, dottedDate, monthDay } from "./detail/display";

function ExampleChooser({ close }: { close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const navigate = useNavigate();
  const [cards, setCards] = useState<ExampleCard[] | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => { dialog.current?.showModal(); }, []);
  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    taskRequest<ExampleCard[]>("/api/examples", { signal: controller.signal }).then(value => {
      if (!controller.signal.aborted) setCards(Array.isArray(value) ? value : []);
    }, () => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [retry]);
  return <dialog ref={dialog} className="library-dialog modal-card" aria-labelledby="examples-title" onCancel={close} onClick={event => {
    if (isDialogBackdropClick(event)) close();
  }}><button type="button" className="modal-close" aria-label="Close" onClick={close}><Icon name="close" size={20} /></button><div className="modal-icon"><Icon name="globe" size={23} /></div><h2 id="examples-title">A little inspiration.</h2><p>Explore the same timeline across different destinations and lengths of stay.</p>
    {error ? <p role="alert">Examples are unavailable. <button type="button" className="inline-action" onClick={() => setRetry(value => value + 1)}>Try again</button></p> : cards ? <div className="menu-stack">{cards.map(card => <button className="menu-option" type="button" key={card.id} onClick={() => navigate(`/examples/${encodeURIComponent(card.id)}`)}><Icon name="pin" size={18} />{card.title}</button>)}</div> : <p role="status">Loading examples…</p>}
  </dialog>;
}

export function BusyPlanningDialog({ taskId, close, save }: { taskId?: string; close: () => void; save: () => Promise<void> }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const mounted = useRef(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { mounted.current = true; dialog.current?.showModal(); return () => { mounted.current = false; }; }, []);
  return <dialog ref={dialog} className="library-dialog modal-card" aria-labelledby="planning-busy-title" onCancel={event => { if (busy) event.preventDefault(); else close(); }} onClick={event => {
    if (!busy && isDialogBackdropClick(event)) close();
  }}><button type="button" className="modal-close" aria-label="Close" disabled={busy} onClick={close}><Icon name="close" size={20} /></button><div className="modal-icon"><Icon name="clock" size={23} /></div><h2 id="planning-busy-title">One journey at a time.</h2><p>A trip is already being planned. You can save these ideas as a draft while you wait.</p><div className="modal-actions"><button type="button" className="btn btn-light" disabled={busy} onClick={() => { setBusy(true); void save().finally(() => { if (mounted.current) { setBusy(false); close(); } }); }}>Save travel brief</button><Link className="btn btn-primary" to={taskId ? planTaskLink(taskId) : "/plan#generation-progress"}>View progress</Link></div></dialog>;
}

const stages = ["Understand your trip", "Explore your destination", "Plan & check your days", "Refine your itinerary", "Prepare nearby ideas"];
const stageIndex: Record<string, number> = { starting: 0, requirements: 0, destination: 1, candidates: 1, retrieval: 1, official_information: 1, introductions: 1, weather: 2, routes: 2, generation: 2, date_validation: 2, transfers: 2, validation: 2, repair: 3, repair_round: 3, repair_preparation: 3, repair_model: 3, repair_reason_compression: 3, revalidation: 3, nearby: 4 };

export function PlanProgress({ task, error, loading, check, onGenerateAgain, submitting, onUpdate, loginHref }: { task?: PlanningTask; error?: string; loading?: boolean; check?: () => Promise<void>; onGenerateAgain?: () => void; submitting?: boolean; onUpdate?: (task: PlanningTask) => void; loginHref?: string }) {
  const { refresh } = useTasks();
  const running = task && taskActive(task);
  const done = task?.state === "completed";
  const current = task ? stageIndex[task.progress.stage] : undefined;
  const message = !task ? "Ready when you are." : running ? task.progress.message : done ? "Your itinerary preview is ready." : task.state === "cancelled" ? "Planning stopped. Your travel brief is still here." : task.state === "needs_clarification" ? (task.outcome?.message || "A few details need your attention. Update your brief before trying again.") : "Planning could not finish. Your travel brief is still here.";
  return <section className="flow-card progress-card" id="generation-progress"><div className="flow-title"><span className="step-number">02</span><div><h2>Planning progress</h2><p>{loading || error ? 'Checking planning progress.' : message}</p></div></div>
    <div className="progress-steps">{stages.map((label, index) => {
      const complete = done || (running && current !== undefined && index < current);
      const active = running && current === index;
      return <div className={`progress-step ${complete ? "complete" : ""} ${active ? "current" : ""}`} key={label}><div className="progress-dot">{complete ? <Icon name="check" size={16} /> : index + 1}</div><strong>{label}</strong><span>{complete ? "Complete" : active ? "In progress" : "Waiting"}</span></div>;
    })}</div>
    {task && <p className="submitted-trip">{task.request.destination} · {monthDay(task.request.start_date || "")}–{task.request.start_date?.slice(0, 7) === task.request.end_date?.slice(0, 7) ? task.request.end_date?.slice(8, 10).replace(/^0/, "") : monthDay(task.request.end_date || "")}, {task.request.end_date?.slice(0, 4)}</p>}
    {(loading || error) && <div className="plan-reconnect" role="status"><span>{error || 'Reading your existing task…'}</span><button type="button" className="inline-action" onClick={() => void check?.()}>Check status</button></div>}
    {loginHref && <Link className="btn btn-light" to={loginHref}>Log in to recover planning</Link>}
    {task && <><TaskOutcome task={task} /><TaskActions key={task.id} task={task} onUpdate={next => { onUpdate?.(next); void refresh(); }} onGenerateAgain={onGenerateAgain} submitting={submitting} /></>}
  </section>;
}

/** The parent keys this view to the authenticated owner and an exact confirmed brief. */
export function PlanResult({ task, previewId }: { task?: PlanningTask; previewId?: string }) {
  const location = useLocation();
  const { tasks, markViewed } = useTasks();
  const { account, refresh } = useSession();
  const [result, setResult] = useState<{ id: string; preview?: Preview; error?: string } | null>(null);
  const [examples, setExamples] = useState(false);
  const [saved, setSaved] = useState<{ previewId: string; tripId: string; detail?: ProductDetail; error?: string } | null>(null);
  const [savedRetry, setSavedRetry] = useState(0);
  const [previewRetry, setPreviewRetry] = useState(0);
  const id = previewId || task?.preview_id;
  useEffect(() => {
    if (!id || !account) return;
    const controller = new AbortController();
    taskRequest<Preview>(`/api/previews/${encodeURIComponent(id)}`, { signal: controller.signal }).then(preview => {
      if (!controller.signal.aborted) setResult({ id, preview });
    }, error => {
      if (controller.signal.aborted) return;
      setResult({ id, error: "Could not load this itinerary preview. Try again when connected." });
      if (error instanceof TaskFailure && error.status === 401) void refresh();
    });
    return () => controller.abort();
  }, [id, account, refresh, previewRetry]);
  const preview = result && result.id === id ? result.preview : undefined;
  const tripId = preview?.state === "saved" && preview.outcome !== "saved_result_deleted" ? preview.saved_trip_id : null;
  useEffect(() => {
    if (!id || !tripId || !account) return;
    const controller = new AbortController();
    setSaved({ previewId: id, tripId });
    taskRequest<ProductDetail>(`/api/trips/${encodeURIComponent(tripId)}`, { signal: controller.signal }).then(detail => {
      if (!controller.signal.aborted) setSaved({ previewId: id, tripId, detail });
    }, error => {
      if (controller.signal.aborted) return;
      if (error instanceof TaskFailure && error.status === 401) { void refresh(); return; }
      if (error instanceof TaskFailure && error.status === 404) {
        setResult(previous => previous?.id === id && previous.preview ? { id, preview: { ...previous.preview, snapshot: null, outcome: "saved_result_deleted" } } : previous);
      } else setSaved({ previewId: id, tripId, error: "Could not load your saved itinerary. Try again when connected." });
    });
    return () => controller.abort();
  }, [id, tripId, account, refresh, savedRetry]);
  const savedDetail = saved && saved.previewId === id && saved.tripId === tripId ? saved.detail : undefined;
  const detail = preview?.state === "pending" ? preview.snapshot : savedDetail;
  const sourceTask = tasks.find(candidate => candidate.preview_id === id) || (task?.preview_id === id ? task : undefined);
  useEffect(() => {
    if (!sourceTask || !preview) return;
    if (location.hash === '#result') { markViewed(sourceTask); return; }
    const node = document.getElementById('result');
    if (!node || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { markViewed(sourceTask); observer.disconnect(); }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [sourceTask, preview, markViewed, location.hash]);
  if (!id && !task) return account ? <UnsavedPreviews /> : <div className="planning-inspiration"><Icon name="pin" size={18} /><span>See how a journey comes together.</span><button type="button" className="inline-action" onClick={() => setExamples(true)}>Explore an example <Icon name="arrow" size={16} /></button>{examples && <ExampleChooser close={() => setExamples(false)} />}</div>;
  return <section className="flow-card result-section" id="result"><div className="flow-title"><span className="step-number">03</span><div><h2>Your itinerary</h2><p>Preview every day. Save it when it feels right.</p></div></div>
    <UnsavedPreviews currentPreviewId={id} refreshKey={`${id}:${preview?.state}`} />
    {preview && (preview.state === "discarded" || preview.outcome === "saved_result_deleted") ? <DecisionReceipt decision={preview} /> : detail && preview ? <div className="result-ready">
      <div className="result-summary"><div className="result-cover"><CuratedPhoto image={destinationCover(detail.destination)} fallback={detail.illustration_key ? `/dayloom/${detail.illustration_key}.svg` : undefined} label={`${detail.destination} destination atmosphere`} /><span className="cover-label">{detail.destination}</span></div><div className="result-intro"><span className="eyebrow">YOUR ITINERARY</span><h3>{detail.title}</h3><p>{dottedDate(detail.start_date)}–{dottedDate(detail.end_date)}{detail.request?.traveler_count ? ` · ${detail.request.traveler_count} travelers` : ""}</p><div className="result-highlights"><span><Icon name="calendar" size={15} />{detail.days.length} days</span><span><Icon name="pin" size={15} />{detail.days.reduce((count, day) => count + day.activities.filter(activity => activity.time_use !== "free_window").length, 0)} places</span><span><Icon name="walk" size={15} />{detail.transfers.length} connections</span>{detail.request?.budget && <span><Icon name="leaf" size={15} />Budget {detail.request.budget.currency} {detail.request.budget.amount}</span>}</div></div></div>
      <div className={`preview-days ${detail.days.length > 3 ? "preview-days-many" : ""}`}>{detail.days.map((day, index) => {
        const first = day.activities.find(activity => activity.time_use !== "free_window");
        return <div className="preview-day" key={day.date}><span className="eyebrow">DAY {String(index + 1).padStart(2, "0")} · {monthDay(day.date)}</span><strong>{first?.place_name || first?.title || "Room to explore"}</strong><p>{day.activities.map(activity => `${activity.start_time.match(/T(\d{2}:\d{2})/)?.[1] || "Time unavailable"} ${activity.time_use === "free_window" ? "Free time" : activity.place_name || activity.title}`).join(" · ")}</p></div>;
      })}</div>
      <div className="result-actions">{preview.state === "pending" ? <PreviewDecisionControls saveIcon={<Icon name="bookmark" size={17} />} preview={preview} onDecision={next => setResult({ id: id!, preview: next })} /> : <span className="resume-hint"><Icon name="check" size={15} /> Saved to My trips</span>}<Link className="btn btn-light" to={tripId ? `/trips/${tripId}` : `/previews/${preview.id}`}>View full itinerary <Icon name="arrow" size={17} /></Link></div>
    </div> : tripId ? <div className="preview-empty"><p role={saved?.error ? "alert" : "status"}>{saved?.error || "Loading your saved itinerary…"}</p>{saved?.error && <button className="btn btn-light" onClick={() => setSavedRetry(value => value + 1)}>Reload saved itinerary</button>}</div> : <div className="result-placeholder"><div className="placeholder-glyph"><Icon name="layers" size={36} /></div><strong>A new journey is waiting.</strong><p>{result && result.id === id && result.error ? result.error : "Fill in your travel brief. Your day-by-day itinerary will appear here."}</p>{result?.id === id && result?.error && <button className="btn btn-light" onClick={() => setPreviewRetry(value => value + 1)}>Reload preview</button>}{!account && <button className="btn btn-light" onClick={() => setExamples(true)}><Icon name="pin" size={16} /> Explore an example</button>}</div>}
    {examples && <ExampleChooser close={() => setExamples(false)} />}
  </section>;
}
