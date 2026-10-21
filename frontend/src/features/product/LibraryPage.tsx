import { Link } from "react-router-dom";
import { useSession } from "./session";
import { ExampleCards } from "./detail/ExampleCards";

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
        <p>
          {account
            ? "The journeys you keep, and the ideas still taking shape."
            : "A little inspiration for your next city journey."}
        </p>
      </div>
      {account ? (
        <section className="flow-card result-placeholder">
          <h2>Your next journey starts here.</h2>
          <p>No trips yet. Start with an idea and make it yours.</p>
          <Link to="/plan" className="btn btn-primary">
            Plan a trip →
          </Link>
        </section>
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
