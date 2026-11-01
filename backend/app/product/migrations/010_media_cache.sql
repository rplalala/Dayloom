-- Display URLs live with their owning resource; no independent cache table.
ALTER TABLE app.itinerary_previews ADD COLUMN media_cache jsonb NOT NULL DEFAULT '{}'
    CHECK (jsonb_typeof(media_cache) = 'object');
ALTER TABLE app.trips ADD COLUMN media_cache jsonb NOT NULL DEFAULT '{}'
    CHECK (jsonb_typeof(media_cache) = 'object');

CREATE FUNCTION app.invalidate_resource_media() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.media_cache = '{}';
    RETURN NEW;
END;
$$;
CREATE TRIGGER preview_media_changed BEFORE UPDATE OF state,snapshot,media_bindings
    ON app.itinerary_previews FOR EACH ROW EXECUTE FUNCTION app.invalidate_resource_media();
CREATE TRIGGER trip_media_changed BEFORE UPDATE OF destination,media_bindings
    ON app.trips FOR EACH ROW EXECUTE FUNCTION app.invalidate_resource_media();
