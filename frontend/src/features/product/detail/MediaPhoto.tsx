import { useContext, useEffect, useState, type ReactNode } from 'react';
import { PlaceMedia, type DisplayMedia } from './media';
import { requestJson } from '../../../shared/api/http';
import './media.css';
import { illustrationFor } from './display';

export function MediaPhoto({ media, label, atmosphere = false, fallback = atmosphere ? '/dayloom/hero.svg' : '/dayloom/nature.svg', className = '', onOpen, children }: {
  media?: DisplayMedia; label: string; atmosphere?: boolean; fallback?: string; className?: string; onOpen?: () => void; children?: ReactNode;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [media]);
  const available = media?.status === 'available' && media.image_url && !failed;
  const placeCredit = Boolean(available && !atmosphere);
  const visual = available ? <img src={media.image_url} alt={atmosphere ? media.alt || label : `${label} · place photograph`} onError={() => setFailed(true)} referrerPolicy="no-referrer" /> : atmosphere ? <img src={fallback} alt={`${label} · illustration`} /> : <div className="media-placeholder" aria-label="Illustration, not a place photograph"><img src={fallback} alt="" aria-hidden="true" /></div>;
  const picture = onOpen ? <button type="button" className="media-open" aria-label={`View ${label}`} onClick={onOpen}>{visual}</button> : visual;
  return <figure className={`media-photo ${atmosphere ? "atmosphere-photo" : "place-photo"} ${placeCredit ? "has-place-credit" : ""} ${className}`}>
    {children ? <div className="media-detail-row"><div className="nearby-photo">{picture}{!available && <span className="media-credit" aria-hidden="true">Illustration</span>}</div>{children}</div> : picture}
    <figcaption className={children && !available ? "visually-hidden" : undefined} aria-label={!available && !atmosphere ? "Place photograph unavailable · illustration" : undefined}>{available ? <>
      <span className="media-provider" translate="no">{media.provider}</span>
      {media.authors?.map((author, i) => <span key={i}> · {author.url ? <a href={author.url} target="_blank" rel="noopener noreferrer">{author.name}</a> : author.name}</span>)}
      {media.source_url && <> · <a href={media.source_url} target="_blank" rel="noopener noreferrer">Photo source</a></>}
      {atmosphere && <span> · Destination / atmosphere</span>}
    </> : 'Illustration'}</figcaption>
  </figure>;
}

export function PlacePhoto({ slot, label, className, onOpen, children, fallback }: { slot: string; label: string; className?: string; onOpen?: () => void; children?: ReactNode; fallback?: string }) {
  const media = useContext(PlaceMedia);
  return <MediaPhoto fallback={fallback || illustrationFor(label)} media={media[slot]} label={label} className={className} onOpen={onOpen}>{children}</MediaPhoto>;
}

export function CuratedPhoto({ image = 'nature', label, className, fallback }: {
  image?: 'sydney' | 'nature'; label: string; className?: string; fallback?: string;
}) {
  const [result, setResult] = useState<{ key: string; media: DisplayMedia } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    requestJson<DisplayMedia>(`/api/media/curated/${image}`, { signal: controller.signal })
      .then(media => { if (!controller.signal.aborted) setResult({ key: image, media }); })
      .catch(() => {});
    return () => controller.abort();
  }, [image]);
  return <MediaPhoto atmosphere media={result?.key === image ? result.media : undefined} label={label} fallback={fallback || `/dayloom/${image}.svg`} className={className} />;
}
