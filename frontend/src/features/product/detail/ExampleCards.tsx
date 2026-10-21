import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { requestJson } from "../../../shared/api/http";
import type { ExampleCard } from "./types";
import { CuratedPhoto } from './MediaPhoto';

export function ExampleCards() {
  const [cards, setCards] = useState<ExampleCard[] | null>(null);
  const [error, setError] = useState(false);
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
  return (
    <div className="trip-grid">
      {cards.map((card, i) => (
        <article className="trip-card" key={card.id}>
          <div
            className={`trip-card-photo dayloom-example example-${i}`}
          >
            <CuratedPhoto image={card.destination.toLowerCase().startsWith('sydney') ? 'sydney' : 'nature'} label={`${card.destination} destination atmosphere`} />
            <Link className="media-cover-link" to={`/examples/${card.id}`} aria-label={`Read ${card.title}`} />
          </div>
          <div className="trip-card-body">
            <span className="eyebrow">
              EXAMPLE · {card.destination.split(",")[0].toUpperCase()}
            </span>
            <h2>{card.title}</h2>
            <p>{card.description || "Ideas for a thoughtful city escape."}</p>
            <p>
              {card.day_count} days · {card.start_date || "Dates unavailable"}
            </p>
            <Link className="text-link" to={`/examples/${card.id}`}>
              View itinerary →
            </Link>
          </div>
        </article>
      ))}
    </div>
  );
}
