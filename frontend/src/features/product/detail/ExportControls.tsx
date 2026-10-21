import { useEffect, useRef, useState } from 'react';
import type { ProductDetail } from './types';
import { exportArtifact, summaryText } from './export';

export function ExportControls({ detail }: { detail: ProductDetail }) {
  const [fallback, setFallback] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const text = summaryText(detail);
  useEffect(() => { if (fallback) dialog.current?.showModal(); }, [fallback]);
  function download(kind: 'json' | 'txt') {
    const blob = new Blob([kind === 'json' ? JSON.stringify(exportArtifact(detail), null, 2) : text], { type: kind === 'json' ? 'application/json' : 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = `${detail.title.replace(/[^a-z0-9_-]+/gi, '-').slice(0, 70) || 'itinerary'}.${kind}`;
    anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="preview-decision-actions">
    <button className="btn btn-light" onClick={() => download('json')}>Export JSON</button>
    <button className="btn btn-light" onClick={() => download('txt')}>Export text</button>
    <button className="btn btn-light" onClick={() => { void navigator.clipboard?.writeText(text).then(() => setFallback(true), () => setFallback(true)); setFallback(true); }}>Copy summary</button>
    {fallback && <dialog className="detail-dialog" ref={dialog} aria-labelledby="summary-title" onCancel={() => setFallback(false)}><h2 id="summary-title">Copyable itinerary summary</h2><p>Select and copy this text if clipboard access is unavailable.</p><textarea aria-label="Itinerary summary" readOnly value={text} rows={16} style={{ width: '100%' }} onFocus={event => event.target.select()} /><button className="btn btn-primary" onClick={() => { dialog.current?.close(); setFallback(false); }}>Close</button></dialog>}
  </div>;
}
