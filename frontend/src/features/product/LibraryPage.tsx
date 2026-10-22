import { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import { useSession } from "./session";
import { ExampleCards } from "./detail/ExampleCards";
import { LibraryCollection } from "./LibraryCollection";
import { Icon } from "./Icon";
import { CopyRecoveryLink } from './CopyRecoveryPage';

export function LibraryPage() {
  const { account, status } = useSession();
  const location = useLocation();
  const importLink = useRef<HTMLAnchorElement>(null);
  const focusedReturn = useRef<string | null>(null);
  useEffect(() => {
    if (location.pathname !== "/trips" || !location.state?.focusImport || status === "loading" || focusedReturn.current === location.key) return;
    focusedReturn.current = location.key;
    // A route modal loses its original trigger. Restore only when the user has
    // not already chosen another focus target while the session was loading.
    if (document.activeElement === document.body) importLink.current?.focus();
  }, [location.key, location.pathname, location.state, status]);
  if (status === "loading")
    return (
      <div className="page container" role="status">
        Checking your session…
      </div>
    );
  if (status === "expired")
    return (
      <div className="page container">
        <h1>Your trips are private.</h1>
        <p>Log in again to continue.</p>
        <Link to="/login?return=/trips" className="btn btn-primary">
          Log in
        </Link>
      </div>
    );
  return (
    <div className="page container trips-page">
      <div className="page-heading">
        <span className="eyebrow">YOUR TRAVEL LIBRARY</span>
        <h1>My trips</h1>
        <p>
          {account
            ? "Keep the places you have been, and the journeys still to come."
            : "A few journeys to explore before you write your own."}
        </p>
      </div>
      {account ? (
        <><CopyRecoveryLink /><LibraryCollection key={account.id} /></>
      ) : (
        <>
          <ExampleCards />
        </>
      )}
      <div className="quiet-links library-import"><Link ref={importLink} to="/import" className="inline-action"><Icon name="download" size={14} />Import an itinerary</Link></div>
    </div>
  );
}
