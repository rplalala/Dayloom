import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { requestJson } from "../../../shared/api/http";
import type { ExampleCard } from "./types";
import { Icon } from "../Icon";
import { CopyControls } from "../CopyControls";
import { destinationCover, dottedDate } from "./display";
import { CuratedPhoto } from './MediaPhoto';

export function ExampleCards() {
  const [cards, setCards] = useState<ExampleCard[] | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("newest");
  useEffect(() => {
    const controller = new AbortController();
    requestJson<ExampleCard[]>("/api/examples", { signal: controller.signal })
      .then((data) => {
        if (!Array.isArray(data)) throw new Error("Invalid example collection");
        setCards(data);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, []);
  if (error)
    return (
      <p role="alert">Examples are unavailable. Please try again later.</p>
    );
  if (!cards) return <p role="status">Loading examples…</p>;
  const shown = cards.filter(card => `${card.title} ${card.destination}`.toLowerCase().includes(query.toLowerCase())).slice().sort((a, b) => sort === "name" ? a.title.localeCompare(b.title, "en") : sort === "oldest" ? (a.created_at || "").localeCompare(b.created_at || "") : (b.created_at || "").localeCompare(a.created_at || ""));
  return (
    <>
    <section className="library-intro"><div className="library-count"><span className="eyebrow">A LITTLE INSPIRATION</span><strong>{String(cards.length).padStart(2, "0")}</strong><span>example itineraries</span></div><div className="library-copy"><h2>Good places.<br /><em>Worth keeping.</em></h2><p>See how a few days can come together.</p></div><Link className="btn btn-primary btn-large" to="/plan"><Icon name="plus" size={18} />Create a trip</Link></section>
    <div className="trips-toolbar"><label className="search-box"><Icon name="search" size={18} /><input aria-label="Search trips" placeholder="Search by trip name or destination" value={query} onChange={event => setQuery(event.target.value)} /></label><label className="sort-box"><Icon name="sliders" size={16} /><select aria-label="Sort trips" value={sort} onChange={event => setSort(event.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="name">By name</option></select></label></div>
    <div className="trip-grid">
      {shown.map((card, i) => (
        <article className="trip-card" key={card.id}>
          <div
            className={`trip-card-photo dayloom-example example-${i}`}
          >
            <CuratedPhoto link={{ to: `/examples/${card.id}`, label: `Read ${card.title}` }} image={destinationCover(card.destination)} label={`${card.destination} destination atmosphere`} fallback={card.illustration_key ? `/dayloom/${card.illustration_key}.svg` : undefined} />
            <span className="trip-status">Example itinerary</span>
          </div>
          <div className="trip-card-body">
            <div className="trip-card-kicker">TRIP ITINERARY</div><h3><Link to={`/examples/${card.id}`}>{card.title}</Link></h3>
            <div className="trip-date"><Icon name="calendar" size={16} />{dottedDate(card.start_date)}{card.end_date ? ` — ${dottedDate(card.end_date)}` : ""}</div>
            <p>{card.description || "A journey worth looking forward to."}</p>
            <div className="trip-card-stats"><span><Icon name="calendar" size={15} />{card.day_count} days</span><span><Icon name="pin" size={15} />{card.stop_count == null ? "Stops to confirm" : `${card.stop_count} stops`}</span><span><Icon name="walk" size={15} />{card.transfer_count == null ? "Connections to confirm" : `${card.transfer_count} connections`}</span></div>
            <div className="trip-card-foot"><Link className="text-link" to={`/examples/${card.id}`}>View details <Icon name="arrow" size={17} /></Link><CopyControls buttonClassName="btn btn-quiet btn-tiny" kind="example" source={card.id} title={card.title} label="Copy" buttonIcon={<Icon name="copy" size={15} />} /></div>
          </div>
        </article>
      ))}
      {!query && <Link className="new-trip-card" to="/plan"><span className="new-trip-icon"><Icon name="plus" size={32} /></span><strong>Another journey, waiting to be written.</strong><p>Choose a destination and begin a new travel brief.</p><span className="new-trip-arrow">Create a trip <Icon name="arrow" size={16} /></span></Link>}
    </div>{shown.length === 0 && <div className="empty-state"><Icon name="search" size={32} /><h3>No trips found</h3><p>Try a shorter name or a different destination.</p></div>}<div className="pagination"><span>{shown.length} examples · Page 1 of 1</span><div className="pagination-controls"><button className="page-btn" aria-label="Previous page" disabled><Icon name="back" size={17} /></button><button className="page-btn active" aria-label="Page 1" aria-current="page">1</button><button className="page-btn" aria-label="Next page" disabled><Icon name="arrow" size={17} /></button></div></div></>
  );
}
