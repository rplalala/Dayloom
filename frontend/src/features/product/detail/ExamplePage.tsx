import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { HttpError, requestJson } from "../../../shared/api/http";
import { TripDetail } from "./TripDetail";
import type { ProductDetail } from "./types";
import { CopyControls } from '../CopyControls';
import { useSession } from '../session';
import { replanBrief } from '../replan';

export function ExamplePage() {
  const navigate = useNavigate();
  const { replaceBrief } = useSession();
  const { exampleId } = useParams();
  const [result, setResult] = useState<{
    id?: string;
    detail?: ProductDetail;
    error?: string;
  }>({});
  useEffect(() => {
    const controller = new AbortController();
    requestJson<ProductDetail>(
      `/api/examples/${encodeURIComponent(exampleId || "")}`,
      { signal: controller.signal },
    )
      .then((detail) => setResult({ id: exampleId, detail }))
      .catch((error) => {
        if (!controller.signal.aborted)
          setResult({
            id: exampleId,
            error:
              error instanceof HttpError && error.status === 404
                ? "Example not found."
                : "Could not load this example. Please try again.",
          });
      });
    return () => controller.abort();
  }, [exampleId]);
  if (result.id !== exampleId)
    return (
      <p className="container page" role="status">
        Loading example…
      </p>
    );
  if (result.error || !result.detail)
    return (
      <div className="container page">
        <h1>{result.error}</h1>
        <Link to="/trips">Browse examples →</Link>
      </div>
    );
  return <TripDetail key={result.detail.id} detail={result.detail} onReplan={() => { replaceBrief(replanBrief(result.detail!.request), "replan"); navigate("/plan"); }} actions={<CopyControls buttonClassName="btn btn-glass" kind="example" source={result.detail.id} title={result.detail.title} />} />;
}
