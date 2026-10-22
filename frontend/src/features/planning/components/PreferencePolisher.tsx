import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  postPreferencePolish,
  type PreferencePolishContext,
  type PreferencePolishResponse,
} from "../api";

interface PreferencePolisherProps {
  text: string;
  context: PreferencePolishContext;
  onApply: (text: string) => void;
  disabled: boolean;
  product?: boolean;
  buttonIcon?: ReactNode;
}

const MAX_ATTEMPTS = 3;

export function PreferencePolisher({ text, context, onApply, disabled, product = false, buttonIcon }: PreferencePolisherProps) {
  const [response, setResponse] = useState<PreferencePolishResponse | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [undo, setUndo] = useState<{ before: string; after: string } | null>(null);
  const revision = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const signature = JSON.stringify([text, context]);
  const currentSignature = useRef(signature);
  currentSignature.current = signature;

  useEffect(() => {
    revision.current += 1;
    controller.current?.abort();
    controller.current = null;
    setBusy(false);
    setResponse(null);
    setError(false);
  }, [signature]);

  useEffect(() => () => controller.current?.abort(), []);

  async function polish() {
    if (disabled || busy || !text.trim() || text.length > 4000 || attempts >= MAX_ATTEMPTS) return;
    const sourceSignature = signature;
    const sourceRevision = String(++revision.current);
    const requestController = new AbortController();
    controller.current = requestController;
    setAttempts(value => value + 1);
    setBusy(true);
    setResponse(null);
    setError(false);
    setUndo(null);
    try {
      const result = await postPreferencePolish({
        original_text: text,
        context,
        client_revision: sourceRevision,
      }, requestController.signal);
      if (requestController.signal.aborted || revision.current !== Number(sourceRevision) ||
        currentSignature.current !== sourceSignature) return;
      if (result.client_revision !== sourceRevision || result.original_text !== text) {
        setError(true);
        return;
      }
      setResponse(result);
    } catch {
      if (!requestController.signal.aborted && currentSignature.current === sourceSignature) setError(true);
    } finally {
      if (controller.current === requestController) {
        controller.current = null;
        setBusy(false);
      }
    }
  }

  function apply() {
    if (!response || response.status !== "suggested" || !response.suggested_text ||
      response.original_text !== text) return;
    const candidate = response.suggested_text;
    setUndo({ before: text, after: candidate });
    setResponse(null);
    onApply(candidate);
  }

  function undoRewrite() {
    if (!undo || text !== undo.after) return;
    onApply(undo.before);
    setUndo(null);
  }

  const available = attempts < MAX_ATTEMPTS;
  if (product) return <div className="preference-assistance">
    <div className="preference-tools"><p id="preference-sync-help">Your selections appear here. Edit any sentence to make it your own.</p><button className="btn btn-quiet btn-small" type="button" onClick={polish} disabled={disabled || busy || !text.trim() || text.length > 4000 || !available}>{buttonIcon}{busy ? "Polishing…" : "Polish preferences"}</button></div>
    {attempts > 0 && <p className="subtle-help">{attempts}/{MAX_ATTEMPTS} attempts used</p>}
    {undo && text === undo.after && <div className="polish-applied"><span aria-hidden="true">✓</span><span>Suggestion applied.</span><button type="button" className="inline-action" onClick={undoRewrite} disabled={disabled}>Undo</button></div>}
    {text.length > 4000 && <p className="form-error">Polishing accepts at most 4,000 characters.</p>}
    {!available && <p className="subtle-help">The polish limit for this form has been reached.</p>}
    {error && <p role="alert">Polishing is unavailable. Your preferences were not changed.</p>}
    {response && <section className="polish-box" aria-live="polite"><div className="polish-heading"><span className="eyebrow">POLISH YOUR PREFERENCES</span><span className="small-muted">Review before applying</span></div>
      {response.status === "suggested" && response.suggested_text ? <><div className="polish-compare"><div><strong>Your original</strong><p>{response.original_text}</p></div><div><strong>A clearer expression</strong><p>{response.suggested_text}</p></div></div><p className="polish-explanation">Check that this still says what you mean. Your original stays unchanged until you apply it.</p><div className="polish-actions"><button type="button" className="btn btn-primary btn-small" onClick={apply} disabled={disabled}>Apply suggestion</button><button type="button" className="btn btn-light btn-small" onClick={() => setResponse(null)}>Keep original</button></div></> : <><p className="polish-explanation">{response.explanation}</p>{response.questions.map(question => <p key={question}>{question}</p>)}<button type="button" className="btn btn-light btn-small" onClick={() => setResponse(null)}>Keep original</button></>}
    </section>}
  </div>;

  return <div className="preference-assistance">
    <div className={product ? "preference-tools" : "preference-assistance-actions"}>
      {product && <p id="preference-sync-help">Your selections appear here. Edit any sentence to make it your own.</p>}
      <button className={product ? "btn btn-quiet btn-small" : "button button-secondary"} type="button" onClick={polish}
        disabled={disabled || busy || !text.trim() || text.length > 4000 || !available}>
        {buttonIcon}{busy ? "Polishing…" : "Polish preferences"}
      </button>
      {undo && text === undo.after && <button className="button button-secondary" type="button"
        onClick={undoRewrite} disabled={disabled}>Undo rewrite</button>}
      {(!product || attempts > 0) && <small>{attempts}/{MAX_ATTEMPTS} attempts used</small>}
    </div>
    {!product && <p className="field-help">Review any suggestion before applying it. Your original meaning and normal planning checks still matter.</p>}
    {text.length > 4000 && <p className="field-error">Polishing accepts at most 4,000 characters.</p>}
    {!available && <p className="field-help">The polish limit for this form has been reached.</p>}
    {error && <p role="alert">Polishing is unavailable. Your preferences were not changed.</p>}
    {response && <div className="preference-preview" aria-live="polite">
      {response.status === "suggested" && response.suggested_text && <>
        <div className="preference-compare">
          <section><h3>Original</h3><p>{response.original_text}</p></section>
          <section><h3>Suggested rewrite</h3><p>{response.suggested_text}</p></section>
        </div>
        <p>{response.explanation}</p>
        <div className="preference-assistance-actions">
          <button className="button button-primary" type="button" onClick={apply} disabled={disabled}>Apply rewrite</button>
          <button className="button button-secondary" type="button" onClick={() => setResponse(null)}>Dismiss</button>
        </div>
      </>}
      {response.status !== "suggested" && <>
        <p>{response.explanation}</p>
        {response.questions.map(question => <p key={question}>{question}</p>)}
        <button className="button button-secondary" type="button" onClick={() => setResponse(null)}>Dismiss</button>
      </>}
    </div>}
  </div>;
}
