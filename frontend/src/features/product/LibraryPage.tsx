import { Link } from "react-router-dom";
import { useSession } from "./session";
import { ExampleCards } from "./detail/ExampleCards";
import { LibraryCollection } from "./LibraryCollection";

export function LibraryPage() {
  const { account, status } = useSession();
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
    <div className="page container">
      <div className="page-heading">
        <span className="eyebrow">YOUR TRAVEL COLLECTION</span>
        <h1>My trips</h1>
        <Link to="/import" className="btn btn-light">Import itinerary</Link>
        <p>
          {account
            ? "The journeys you keep, and the ideas still taking shape."
            : "A little inspiration for your next city journey."}
        </p>
      </div>
      {account ? (
        <LibraryCollection key={account.id} />
      ) : (
        <>
          <div className="hint-strip">
            These are examples. Log in to keep your own travel collection.
          </div>
          <ExampleCards />
        </>
      )}
    </div>
  );
}
