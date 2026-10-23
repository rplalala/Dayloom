-- Retain weather source credit when a preview or curated example becomes a saved trip.
ALTER TABLE app.trip_weather ADD COLUMN attribution text;
ALTER TABLE app.trip_weather ADD COLUMN source_url text;
