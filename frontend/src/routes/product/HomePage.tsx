import { Link } from "react-router-dom";
import { useSession } from "../../features/product/session";
import { CuratedPhoto } from '../../features/product/detail/MediaPhoto';
import { Icon } from '../../features/product/Icon';

export function HomePage() {
  const { account } = useSession();
  return (
    <>
      <section className="home-hero minimal-hero">
        <div className="container hero-grid">
          <div className="hero-copy">
            <span className="hero-kicker">A BETTER WAY TO WANDER</span>
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
                Start planning <Icon name="arrow" size={19} />
              </Link>
              <Link className="btn btn-light btn-large" to={account ? "/trips" : "/examples/sydney-example"}>
                {account ? "Explore your trips" : "View an example"} <Icon name="chevron" size={17} />
              </Link>
            </div>
            <p className="hero-disclaimer">
              <Icon name="leaf" size={14} /> Thoughtful city experiences, with time for what matters.
            </p>
          </div>
          <div className="hero-visual">
            <div className="hero-image">
              <CuratedPhoto label="Mountain landscape" />
              <div className="hero-img-mask" />
            </div>
            <div className="floating-stamp">
              <Icon name="pin" size={16} /> Your next chapter<span>YOUR NEXT DESTINATION</span>
            </div>
            <div className="hero-floating-card">
              <span className="floating-top"><Icon name="spark" size={17} /> YOUR JOURNEY, YOUR WAY</span>
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
              "calendar",
              "Built around your time",
              "Your dates, daily activities and room to explore.",
            ],
            [
              "route",
              "The details, together",
              "Weather and travel estimates beside your plans.",
            ],
            [
              "checklist",
              "Clarity where it counts",
              "See which details still need confirmation.",
            ],
          ].map(([icon, title, text]) => (
            <div key={title}>
              <Icon name={icon} size={23} />
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
              <Link to="/plan" state={{ mood: kind }} className="mood-card" key={kind}>
                <div className={`mood-art ${kind}`}>
                  <span className="art-no">{number}</span>
                  <Icon name={kind === "art" ? "museum" : kind === "nature" ? "tree" : "walk"} size={52} />
                </div>
                <div className="mood-body">
                  <h3>{title}</h3>
                  <p>{text}</p>
                  <span className="text-link">Begin here <Icon name="arrow" size={14} /></span>
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
            Plan my trip <Icon name="arrow" size={16} />
          </Link>
        </section>
      </div>
    </>
  );
}
