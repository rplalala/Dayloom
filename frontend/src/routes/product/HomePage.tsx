import { Link } from "react-router-dom";
import { useSession } from "../../features/product/session";

export function HomePage() {
  const { account } = useSession();
  return (
    <>
      <section className="home-hero minimal-hero">
        <div className="container hero-grid">
          <div className="hero-copy">
            <p className="hero-kicker">A BETTER WAY TO WANDER</p>
            <h1>
              So much to discover.
              <br />
              <em>So easy to plan.</em>
            </h1>
            <p className="hero-summary">
              A destination, a few ideas, a rhythm that feels like you. Bring
              your days together in one clear itinerary.
            </p>
            <div className="hero-actions">
              <Link className="btn btn-primary btn-large" to="/plan">
                Start planning →
              </Link>
              <Link className="btn btn-light btn-large" to="/trips">
                {account ? "Explore your trips →" : "View examples →"}
              </Link>
            </div>
            <p className="hero-disclaimer">
              Thoughtful city experiences, with time for what matters.
            </p>
          </div>
          <div className="hero-visual">
            <div className="hero-image">
              <img
                className="hero-photo"
                src="/dayloom/hero.svg"
                alt="Illustrated mountain landscape"
              />
            </div>
            <div className="floating-stamp">
              Your next chapter<span>YOUR NEXT DESTINATION</span>
            </div>
            <div className="hero-floating-card">
              <span className="floating-top">✧ YOUR JOURNEY, YOUR WAY</span>
              <strong>A little structure. A little spontaneity.</strong>
              <span>Daily places · Easy connections · Nearby discoveries</span>
              <div className="tiny-progress">
                <i />
                <i />
                <i />
              </div>
            </div>
          </div>
        </div>
      </section>
      <div className="container home-discovery">
        <div className="intro-rail">
          {[
            [
              "◷",
              "Built around your time",
              "Your dates, daily activities and room to explore.",
            ],
            [
              "⌁",
              "The details, together",
              "Weather and travel estimates beside your plans.",
            ],
            [
              "ⓘ",
              "Clarity where it counts",
              "See which details still need confirmation.",
            ],
          ].map(([icon, title, text]) => (
            <div key={title}>
              <span aria-hidden="true">{icon}</span>
              <div>
                <strong>{title}</strong>
                <p>{text}</p>
              </div>
            </div>
          ))}
        </div>
        <section className="section">
          <div className="section-heading">
            <div>
              <span className="eyebrow">START WITH WHAT YOU LOVE</span>
              <h2>What will this trip feel like?</h2>
            </div>
            <p>
              Start with the experiences you enjoy. Your interests become part
              of your travel brief.
            </p>
          </div>
          <div className="mood-grid">
            {[
              [
                "art",
                "01",
                "Follow your curiosity",
                "Find art, culture and stories in galleries and old streets.",
              ],
              [
                "nature",
                "02",
                "Take the scenic way",
                "Make time for green spaces, waterfronts and open skies.",
              ],
              [
                "city",
                "03",
                "Leave room for the everyday",
                "Slow down and discover the city one neighborhood at a time.",
              ],
            ].map(([kind, number, title, text]) => (
              <Link to="/plan" className="mood-card" key={kind}>
                <div className={`mood-art ${kind}`}>
                  <span className="art-no">{number}</span>
                  <span aria-hidden="true">
                    {kind === "art" ? "▥" : kind === "nature" ? "♧" : "⌂"}
                  </span>
                </div>
                <div className="mood-body">
                  <h3>{title}</h3>
                  <p>{text}</p>
                  <span className="text-link">Begin here →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
        <section className="section last-cta">
          <div>
            <span className="eyebrow">MAKE ROOM FOR DISCOVERY</span>
            <h2>Your next journey starts with an idea.</h2>
          </div>
          <Link to="/plan" className="btn btn-primary btn-large">
            Plan my trip →
          </Link>
        </section>
      </div>
    </>
  );
}
