import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useSession } from './session';
import { taskRequest, TaskFailure } from './taskClient';
import { TripDetail } from './detail/TripDetail';
import type { ProductDetail } from './detail/types';
import { replanBrief } from './replan';
import { CopyControls } from './CopyControls';
import { invalidatePhotos, photoGeneration } from './detail/photoSession';

export function SavedPage() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  const { account, refresh, replaceBrief } = useSession();
  const authorization = account ? JSON.stringify([account.id, account.csrf_token, photoGeneration(account.id)]) : '';
  const [result, setResult] = useState<{ authorization?: string; id?: string; detail?: ProductDetail; error?: string }>({});
  useEffect(() => {
    if (!account) return;
    const controller = new AbortController();
    taskRequest<ProductDetail>(`/api/trips/${encodeURIComponent(tripId || '')}`, { signal: controller.signal }).then(detail => {
      if (!controller.signal.aborted) setResult({ authorization, id: tripId, detail });
    }, error => {
      if (!controller.signal.aborted) {
        invalidatePhotos({ owner: account.id, resource: `/api/trips/${encodeURIComponent(tripId || '')}/media` });
        setResult({ authorization, id: tripId, error: 'This saved itinerary is unavailable.' });
        if (error instanceof TaskFailure && error.status === 401) void refresh();
      }
    });
    return () => controller.abort();
  }, [account, tripId, refresh, authorization]);
  if (!account) return <div className="container page"><h1>Log in to view your saved itinerary.</h1><Link to={`/login?return=${encodeURIComponent(`/trips/${tripId}`)}`}>Log in</Link></div>;
  if (result.authorization !== authorization || result.id !== tripId) return <p className="container page" role="status">Loading itinerary…</p>;
  if (!result.detail) return <div className="container page"><h1>{result.error}</h1><CopyControls buttonClassName="btn btn-glass" kind="copied" source={tripId || ''} statusOnly /><Link to="/trips">Back to My trips</Link></div>;
  const detail = result.detail;
  return <TripDetail mode="saved" mediaOwner={account.id} key={detail.id} detail={detail} mediaEndpoint={`/api/trips/${detail.id}/media`} actions={<CopyControls buttonClassName="btn btn-glass" kind="copied" source={detail.id} title={detail.title} />} onReplan={() => {
    replaceBrief(replanBrief(detail.request), 'replan');
    navigate('/plan');
  }} />;
}
