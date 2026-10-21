import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { requestJson } from "../../../shared/api/http";
import type { ExampleCard } from "./types";

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
          <Link
            className={`trip-card-photo dayloom-example example-${i}`}
            to={`/examples/${card.id}`}
            aria-label={`Read ${card.title}`}
          >
            <span className="example-art-label">Landscape illustration</span>
          </Link>
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
