-- Presentation hints never establish original requests or verified photo identities.
ALTER TABLE app.trips ADD COLUMN display_metadata jsonb NOT NULL DEFAULT '{}'
    CHECK (jsonb_typeof(display_metadata) = 'object');
