import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useSession } from './session';
import { taskRequest, TaskFailure } from './taskClient';
import { TripDetail } from './detail/TripDetail';
import type { ProductDetail } from './detail/types';
import { replanBrief } from './replan';
import { CopyControls } from './CopyControls';

export function SavedPage() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  const { account, refresh, replaceBrief } = useSession();
  const [result, setResult] = useState<{ owner?: string; id?: string; detail?: ProductDetail; error?: string }>({});
  useEffect(() => {
    if (!account) return;
    const controller = new AbortController();
    taskRequest<ProductDetail>(`/api/trips/${encodeURIComponent(tripId || '')}`, { signal: controller.signal }).then(detail => {
      if (!controller.signal.aborted) setResult({ owner: account.id, id: tripId, detail });
    }, error => {
      if (!controller.signal.aborted) {
        setResult({ owner: account.id, id: tripId, error: 'This saved itinerary is unavailable.' });
        if (error instanceof TaskFailure && error.status === 401) void refresh();
      }
    });
    return () => controller.abort();
  }, [account, tripId, refresh]);
  if (!account) return <div className="container page"><h1>Log in to view your saved itinerary.</h1><Link to={`/login?return=${encodeURIComponent(`/trips/${tripId}`)}`}>Log in</Link></div>;
  if (result.owner !== account.id || result.id !== tripId) return <p className="container page" role="status">Loading itinerary…</p>;
  if (!result.detail) return <div className="container page"><h1>{result.error}</h1><CopyControls kind="copied" source={tripId || ''} statusOnly /><Link to="/trips">Back to My trips</Link></div>;
  const detail = result.detail;
  return <><div className="container preview-state"><strong>Saved itinerary</strong><Link to="/trips">Back to My trips</Link></div><TripDetail key={detail.id} detail={detail} mediaEndpoint={`/api/trips/${detail.id}/media`} actions={<CopyControls kind="copied" source={detail.id} title={detail.title} />} onReplan={() => {
    replaceBrief(replanBrief(detail.request), 'replan');
    navigate('/plan');
  }} /></>;
}
