import { isDialogBackdropClick } from '../../../shared/dialog';
import { useEffect, useRef, useState } from 'react';
import type { ProductDetail } from './types';
import { exportArtifact, summaryText } from './export';
import { Icon } from '../Icon';

export function ExportControls({ detail }: { detail: ProductDetail }) {
  const [modal, setModal] = useState<'export' | 'summary' | null>(null);
  const [fallbackText, setFallbackText] = useState('');
  const [notice, setNotice] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  const mounted = useRef(false);
  const currentDetail = useRef(detail.id);
  const copyGeneration = useRef(0);
  currentDetail.current = detail.id;
  const text = summaryText(detail);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(''), 4200);
    return () => window.clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    const element = dialog.current;
    if (!modal || !element) return;
    const opener = document.activeElement;
    element.showModal();
    return () => {
      if (element.open) element.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [modal]);
  function download(kind: 'json' | 'txt') {
    const blob = new Blob([kind === 'json' ? JSON.stringify(exportArtifact(detail), null, 2) : text], { type: kind === 'json' ? 'application/json' : 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = `${detail.title.replace(/[^a-z0-9_-]+/gi, '-').slice(0, 70) || 'itinerary'}.${kind}`;
    anchor.click(); setModal(null); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function copy() {
    const generation = ++copyGeneration.current;
    const id = detail.id;
    const stillCurrent = () => mounted.current && currentDetail.current === id && generation === copyGeneration.current;
    setNotice('');
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(text);
      if (stillCurrent()) setNotice('Itinerary summary copied.');
    } catch {
      if (stillCurrent()) { setFallbackText(text); setModal('summary'); }
    }
  }
  return <>
    <button type="button" className="btn btn-glass" onClick={() => setModal('export')}><Icon name="download" size={17} /> Export itinerary</button>
    <button type="button" className="btn btn-glass" onClick={() => void copy()}><Icon name="share" size={17} /> Copy summary</button>
    {modal && <dialog className="modal-card detail-dialog" ref={dialog} aria-labelledby={modal === 'export' ? 'export-title' : 'summary-title'} onCancel={event => { event.preventDefault(); setModal(null); }} onClick={event => {
      if (isDialogBackdropClick(event)) setModal(null);
    }}>
      <button type="button" className="modal-close" aria-label="Close dialog" onClick={() => setModal(null)}><Icon name="close" size={21} /></button>
      {modal === 'export' ? <>
        <div className="modal-icon"><Icon name="download" size={23} /></div><h2 id="export-title">Take your itinerary with you.</h2><p>{detail.title}</p>
        <div className="menu-stack"><button type="button" className="menu-option" aria-label="Export text" onClick={() => download('txt')}><Icon name="list" size={18} /> Download text itinerary</button><button type="button" className="menu-option" aria-label="Export JSON" onClick={() => download('json')}><Icon name="download" size={18} /> Download itinerary JSON</button></div>
        <p className="modal-section-note">Text is easy to read. JSON can be imported later. Missing information stays unknown.</p>
      </> : <>
        <h2 id="summary-title">Copy your itinerary summary</h2>
        <textarea className="share-textarea" aria-label="Itinerary summary" readOnly value={fallbackText} onFocus={event => event.target.select()} />
        <div className="modal-actions"><button type="button" className="btn btn-primary" onClick={() => setModal(null)}>Close</button></div>
      </>}
    </dialog>}
    {notice && <div className="toast show" role="status" aria-live="polite">{notice}</div>}
  </>;
}
