import { Link, useNavigate } from "react-router-dom";
import { useSession, type Brief } from "./session";

/** Shared Product brief surface. Subsequent editor/draft slices extend this form. */
export function BriefPage() {
  const session = useSession();
  const navigate = useNavigate();
  function change(field: keyof Brief, value: string) {
    session.editBrief({ ...session.brief, [field]: value });
  }
  if (session.status === "loading")
    return (
      <div className="page container" role="status">
        Checking your session…
      </div>
    );
  if (session.status === "expired")
    return (
      <div className="page container">
        <h1>Log in to continue your brief.</h1>
        <p>
          Your unsaved input is kept private until you return to the same
          account.
        </p>
        <Link to="/login?return=/plan" className="btn btn-primary">
          Log in
        </Link>
      </div>
    );
  return (
    <div className="page container plan-page">
      <div className="page-heading">
        <span className="eyebrow">YOUR JOURNEY, YOUR WAY</span>
        <h1>A city journey, made yours.</h1>
        <p>
          Pick a destination. Bring your ideas. Make every day a little clearer.
        </p>
      </div>
      <section className="flow-card form-card">
        <div className="flow-title">
          <span className="step-number">01</span>
          <div>
            <h2>Tell us how you like to travel</h2>
            <p>A few essentials, and the things that make it your trip.</p>
          </div>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (!session.actionId) session.setActionId(crypto.randomUUID());
            if (!session.account) navigate("/login?return=/plan");
          }}
        >
          <fieldset className="form-fields">
            <div className="form-grid">
              <label className="field field-destination">
                <span>Destination</span>
                <input
                  value={session.brief.destination}
                  onChange={(e) => change("destination", e.target.value)}
                  placeholder="Choose or enter a city"
                />
              </label>
              <label className="field">
                <span>Start date</span>
                <input
                  type="date"
                  value={session.brief.start_date}
                  onChange={(e) => change("start_date", e.target.value)}
                />
              </label>
              <label className="field">
                <span>End date</span>
                <input
                  type="date"
                  value={session.brief.end_date}
                  onChange={(e) => change("end_date", e.target.value)}
                />
              </label>
              <label className="field">
                <span>Travelers</span>
                <input
                  type="number"
                  min="1"
                  value={session.brief.travelers}
                  onChange={(e) => change("travelers", e.target.value)}
                />
              </label>
              <label className="field">
                <span>Whole-trip budget</span>
                <input
                  aria-label="Whole-trip budget"
                  type="number"
                  min="0"
                  value={session.brief.budget}
                  onChange={(e) => change("budget", e.target.value)}
                />
              </label>
              <label className="field">
                <span>Currency</span>
                <select
                  value={session.brief.currency}
                  onChange={(e) => change("currency", e.target.value)}
                >
                  {["AUD", "USD", "EUR", "GBP", "JPY", "CNY", "NZD", "SGD"].map(
                    (c) => (
                      <option key={c}>{c}</option>
                    ),
                  )}
                </select>
              </label>
            </div>
            <label className="field notes-wide">
              <span>Additional preferences</span>
              <textarea
                rows={5}
                value={session.brief.preferences}
                onChange={(e) => change("preferences", e.target.value)}
                placeholder="Tell us about slow mornings, accessibility needs, or anything else that matters…"
              />
            </label>
          </fieldset>
          <div className="form-bottom">
            <p>
              City sights and experiences. Accommodation, tickets and travel to
              your destination are not included.
            </p>
            <button type="submit" className="btn btn-primary btn-large">
              Generate itinerary →
            </button>
          </div>
          {session.account && (
            <p className="subtle-help">
              Your brief is ready. Review your details before you generate.
            </p>
          )}
        </form>
      </section>
      <section className="flow-card">
        <div className="flow-title">
          <span className="step-number">02</span>
          <div>
            <h2>Planning progress</h2>
            <p>Ready when you are.</p>
          </div>
        </div>
      </section>
      <section className="flow-card">
        <div className="result-placeholder">
          <strong>A new journey is waiting.</strong>
          <p>
            Fill in your travel brief. Your day-by-day itinerary will appear
            here.
          </p>
        </div>
      </section>
    </div>
  );
}
