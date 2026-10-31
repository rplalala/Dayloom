import { useContext, useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { PlaceMedia, PlaceMediaActions, type DisplayMedia } from './media';
import { requestJson } from '../../../shared/api/http';
import './media.css';
import { illustrationFor } from './display';
import { Icon } from '../Icon';
import { Link } from 'react-router-dom';
import { isPlaceFallback, validPhoto } from './photoSession';

export function MediaPhoto({ media, label, atmosphere = false, fallback = atmosphere ? '/dayloom/hero.svg' : '/dayloom/nature.svg', className = '', onOpen, onImageError, onRetry, children, link, creditInDetails = false, staticCredits = false, creditLabel, slot }: {
  creditLabel?: string;
  staticCredits?: boolean;
  slot?: string;
  onImageError?: () => void; onRetry?: () => void;
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
  const placeCredit = Boolean(available && (!atmosphere || staticCredits) && !creditInDetails);
  const visual = available ? <img src={media.image_url} alt={atmosphere ? media.alt || label : `${label} · place photograph`} onError={() => { setFailed(true); onImageError?.(); }} referrerPolicy="no-referrer" /> : atmosphere ? <img src={fallback} alt={`${label} · illustration`} /> : <div className="media-placeholder" aria-label="Illustration, not a place photograph"><img src={fallback} alt="" aria-hidden="true" /></div>;
  const credit = available ? <>
    {creditLabel && <><span>{creditLabel}</span> · </>}
    <span className="media-provider" translate="no">{media.provider}</span>
    {media.authors?.map((author, i) => <span key={i}> · {author.url ? <a href={author.url} target="_blank" rel="noopener noreferrer">{author.name}</a> : author.name}</span>)}
    {media.source_url && <> · <a href={media.source_url} target="_blank" rel="noopener noreferrer">Photo source</a></>}
  </> : pendingLabel;
  const picture = onOpen ? <button type="button" className="media-open" aria-label={`View ${label}`} onClick={onOpen}>{visual}</button> : link ? <Link className="media-image-link" to={link.to} aria-label={link.label}>{visual}</Link> : visual;
  return <figure data-photo-slot={slot} data-photo-state={failed ? 'unavailable' : media?.status || 'unattempted'} aria-busy={media?.status === 'loading'} className={`media-photo ${atmosphere ? "atmosphere-photo" : "place-photo"} ${placeCredit ? "has-place-credit" : ""} ${className}`}
    onPointerEnter={event => { if (atmosphere && !staticCredits && event.pointerType !== "touch") setCreditsOpen(true); }}
    onPointerLeave={event => { if (!event.currentTarget.contains(document.activeElement)) setCreditsOpen(false); }}
    onFocus={() => setCreditsOpen(true)}
    onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setCreditsOpen(false); }}
    onKeyDown={event => { if (atmosphere && !staticCredits && !creditInDetails && event.key === "Escape") { event.preventDefault(); event.stopPropagation(); closeCredits(); } }}>
    {children ? <div className="media-detail-row"><div className="nearby-photo">{picture}{!available && <span className="media-credit" aria-hidden="true">{pendingLabel}</span>}</div>{children}</div> : picture}
    {available && atmosphere && !staticCredits && !creditInDetails ? <figcaption className="atmosphere-credit">
      <button type="button" className="photo-credit-toggle" ref={creditToggle} aria-label="Photo credits" aria-expanded={creditsOpen} aria-controls={creditsId} onClick={() => setCreditsOpen(true)}><Icon name="info" size={15} /></button>
      <span id={creditsId} className="photo-credit-content" hidden={!creditsOpen}>{credit}<button type="button" className="photo-credit-close" aria-label="Hide photo credits" onClick={closeCredits}><Icon name="close" size={12} /></button></span>
    </figcaption> : available && creditInDetails ? null : <figcaption className={children && !available ? "visually-hidden" : undefined} aria-label={!available && !atmosphere ? "Illustration" : undefined}>{credit}</figcaption>}

    {!available && onRetry && (failed || media?.status === 'unavailable') && <button type="button" className="inline-action media-refresh" onClick={onRetry}>Retry photo</button>}
  </figure>;
}

export function PlacePhoto({ slot, label, className, onOpen, children, fallback, fullCredit = false }: { fullCredit?: boolean; slot: string; label: string; className?: string; onOpen?: () => void; children?: ReactNode; fallback?: string }) {
  const media = useContext(PlaceMedia);
  const actions = useContext(PlaceMediaActions);
  const atmosphere = validPhoto(media[slot]) && isPlaceFallback(media[slot]);
  return <MediaPhoto slot={slot} atmosphere={atmosphere} staticCredits={atmosphere} creditLabel={atmosphere && fullCredit ? 'Atmosphere photo' : undefined} fallback={fallback || illustrationFor(label)} creditInDetails={!fullCredit} media={media[slot]} label={label} className={className} onOpen={onOpen}
    onImageError={media[slot] && actions ? () => actions.imageFailed(slot, media[slot]) : undefined}
    onRetry={actions ? () => actions.refresh(slot) : undefined}>{children}</MediaPhoto>;
}

export function SupportingPhoto({ slot, label, className = '', onOpen, fullCredit = false }: {
  slot: string; label: string; className?: string; onOpen?: () => void; fullCredit?: boolean;
}) {
  const media = useContext(PlaceMedia)[slot];
  const actions = useContext(PlaceMediaActions);
  if (media?.kind !== 'atmosphere' || !validPhoto(media)) return null;
  return <div className={`supporting-photo ${className}`}>
    <MediaPhoto slot={slot} atmosphere staticCredits creditInDetails={!fullCredit} media={media} label={label} onOpen={onOpen}
      onImageError={() => actions?.imageFailed(slot, media)} />
    {fullCredit && <span className="supporting-photo-label">Atmosphere photo</span>}
  </div>;
}

function useCoverMedia(endpoint?: string) {
  const [result, setResult] = useState<{ key: string; media: DisplayMedia } | null>(null);
  useEffect(() => {
    if (!endpoint) return;
    const controller = new AbortController();
    requestJson<DisplayMedia>(endpoint, { signal: controller.signal })
      .then(media => { if (!controller.signal.aborted) setResult({ key: endpoint, media }); })
      .catch(() => {});
    return () => controller.abort();
  }, [endpoint]);
  return result?.key === endpoint ? result?.media : undefined;
}

export function CuratedPhoto({ image = 'nature', label, className, fallback, link }: {
  link?: { to: string; label: string }; image?: 'sydney' | 'london' | 'nature'; label: string; className?: string; fallback?: string;
}) {
  const media = useCoverMedia(`/api/media/curated/${image}`);
  return <MediaPhoto atmosphere link={link} media={media} label={label} fallback={fallback || `/dayloom/${image === 'london' ? 'city' : image}.svg`} className={className} />;
}

export function DestinationPhoto({ destination, label, className, fallback, link }: {
  destination: string; label: string; className?: string; fallback?: string;
  link?: { to: string; label: string };
}) {
  const query = destination.trim().replace(/\s+/g, ' ').slice(0, 120);
  const media = useCoverMedia(query ? `/api/media/destination?destination=${encodeURIComponent(query)}` : undefined);
  return <MediaPhoto atmosphere link={link} media={media} label={label} fallback={fallback || '/dayloom/nature.svg'} className={className} />;
}
