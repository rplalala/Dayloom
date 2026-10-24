import { useContext, useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { PlaceMedia, type DisplayMedia } from './media';
import { requestJson } from '../../../shared/api/http';
import './media.css';
import { illustrationFor } from './display';
import { Icon } from '../Icon';
import { Link } from 'react-router-dom';

export function MediaPhoto({ media, label, atmosphere = false, fallback = atmosphere ? '/dayloom/hero.svg' : '/dayloom/nature.svg', className = '', onOpen, children, link, creditInDetails = false }: {
  creditInDetails?: boolean; link?: { to: string; label: string }; media?: DisplayMedia; label: string; atmosphere?: boolean; fallback?: string; className?: string; onOpen?: () => void; children?: ReactNode;
}) {
  const [failed, setFailed] = useState(false);
  const [creditsOpen, setCreditsOpen] = useState(false);
  const creditsId = useId();
  const creditToggle = useRef<HTMLButtonElement>(null);
  const closeCredits = () => {
    creditToggle.current?.focus();
    setCreditsOpen(false);
  };
  useEffect(() => setFailed(false), [media]);
  const available = media?.status === 'available' && media.image_url && !failed;
  const pendingLabel = !atmosphere && !failed && (!media || media.status === 'loading')
    ? media ? 'Loading photo…' : 'Photo pending' : 'Illustration';
  const placeCredit = Boolean(available && !atmosphere && !creditInDetails);
  const visual = available ? <img src={media.image_url} alt={atmosphere ? media.alt || label : `${label} · place photograph`} onError={() => setFailed(true)} referrerPolicy="no-referrer" /> : atmosphere ? <img src={fallback} alt={`${label} · illustration`} /> : <div className="media-placeholder" aria-label="Illustration, not a place photograph"><img src={fallback} alt="" aria-hidden="true" /></div>;
  const credit = available ? <>
    <span className="media-provider" translate="no">{media.provider}</span>
    {media.authors?.map((author, i) => <span key={i}> · {author.url ? <a href={author.url} target="_blank" rel="noopener noreferrer">{author.name}</a> : author.name}</span>)}
    {media.source_url && <> · <a href={media.source_url} target="_blank" rel="noopener noreferrer">Photo source</a></>}
  </> : pendingLabel;
  const picture = onOpen ? <button type="button" className="media-open" aria-label={`View ${label}`} onClick={onOpen}>{visual}</button> : link ? <Link className="media-image-link" to={link.to} aria-label={link.label}>{visual}</Link> : visual;
  return <figure data-photo-state={failed ? 'unavailable' : media?.status || 'unattempted'} aria-busy={media?.status === 'loading'} className={`media-photo ${atmosphere ? "atmosphere-photo" : "place-photo"} ${placeCredit ? "has-place-credit" : ""} ${className}`}
    onPointerEnter={event => { if (atmosphere && event.pointerType !== "touch") setCreditsOpen(true); }}
    onPointerLeave={event => { if (!event.currentTarget.contains(document.activeElement)) setCreditsOpen(false); }}
    onFocus={() => setCreditsOpen(true)}
    onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setCreditsOpen(false); }}
    onKeyDown={event => { if (atmosphere && event.key === "Escape") { event.preventDefault(); event.stopPropagation(); closeCredits(); } }}>
    {children ? <div className="media-detail-row"><div className="nearby-photo">{picture}{!available && <span className="media-credit" aria-hidden="true">{pendingLabel}</span>}</div>{children}</div> : picture}
    {available && atmosphere ? <figcaption className="atmosphere-credit">
      <button type="button" className="photo-credit-toggle" ref={creditToggle} aria-label="Photo credits" aria-expanded={creditsOpen} aria-controls={creditsId} onClick={() => setCreditsOpen(true)}><Icon name="info" size={15} /></button>
      <span id={creditsId} className="photo-credit-content" hidden={!creditsOpen}>{credit}<button type="button" className="photo-credit-close" aria-label="Hide photo credits" onClick={closeCredits}><Icon name="close" size={12} /></button></span>
    </figcaption> : available && creditInDetails ? null : <figcaption className={children && !available ? "visually-hidden" : undefined} aria-label={!available && !atmosphere ? "Illustration" : undefined}>{credit}</figcaption>}

  </figure>;
}

export function PlacePhoto({ slot, label, className, onOpen, children, fallback, fullCredit = false }: { fullCredit?: boolean; slot: string; label: string; className?: string; onOpen?: () => void; children?: ReactNode; fallback?: string }) {
  const media = useContext(PlaceMedia);
  return <MediaPhoto fallback={fallback || illustrationFor(label)} creditInDetails={!fullCredit} media={media[slot]} label={label} className={className} onOpen={onOpen}>{children}</MediaPhoto>;
}

export function CuratedPhoto({ image = 'nature', label, className, fallback, link }: {
  link?: { to: string; label: string }; image?: 'sydney' | 'london' | 'nature'; label: string; className?: string; fallback?: string;
}) {
  const [result, setResult] = useState<{ key: string; media: DisplayMedia } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    requestJson<DisplayMedia>(`/api/media/curated/${image}`, { signal: controller.signal })
      .then(media => { if (!controller.signal.aborted) setResult({ key: image, media }); })
      .catch(() => {});
    return () => controller.abort();
  }, [image]);
  return <MediaPhoto atmosphere link={link} media={result?.key === image ? result.media : undefined} label={label} fallback={fallback || `/dayloom/${image === 'london' ? 'city' : image}.svg`} className={className} />;
}
