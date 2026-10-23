-- Stable application-controlled identities only. Expiring photo metadata is never stored.
ALTER TABLE app.itinerary_previews ADD COLUMN media_bindings jsonb NOT NULL DEFAULT '{}'
    CHECK (jsonb_typeof(media_bindings) = 'object'
        AND NOT jsonb_path_exists(media_bindings, '$.* ? (@.type() != "string")')
        AND NOT jsonb_path_exists(media_bindings, '$.* ? (!(@ like_regex "^[A-Za-z0-9_-]+$"))'));
ALTER TABLE app.trips ADD COLUMN media_bindings jsonb NOT NULL DEFAULT '{}'
    CHECK (jsonb_typeof(media_bindings) = 'object'
        AND NOT jsonb_path_exists(media_bindings, '$.* ? (@.type() != "string")')
        AND NOT jsonb_path_exists(media_bindings, '$.* ? (!(@ like_regex "^[A-Za-z0-9_-]+$"))'));
