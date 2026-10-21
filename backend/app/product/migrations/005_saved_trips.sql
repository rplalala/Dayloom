CREATE TABLE app.trips (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    source_preview_id uuid NOT NULL UNIQUE,
    source_kind text NOT NULL CHECK (source_kind IN ('generated_v3','imported','copied','example')),
    source_id text,
    title text NOT NULL CHECK (length(btrim(title)) > 0),
    destination text NOT NULL CHECK (length(btrim(destination)) > 0),
    start_date text,
    end_date text,
    description text,
    provenance text NOT NULL CHECK (provenance IN ('generated','imported','example')),
    trust text NOT NULL CHECK (trust IN ('generated_projection','unverified_import','source_fixture')),
    request jsonb CHECK (request IS NULL OR jsonb_typeof(request) = 'object'),
    completion jsonb CHECK (completion IS NULL OR jsonb_typeof(completion) = 'object'),
    generated_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
    UNIQUE (owner_id,id),
    FOREIGN KEY (owner_id,source_preview_id) REFERENCES app.itinerary_previews(owner_id,id)
);
CREATE INDEX trips_collection ON app.trips(owner_id,updated_at DESC,id);

-- A day exists independently of its weather availability and activity count.
-- Weather attribution and source URLs are deliberately excluded from storage.
CREATE TABLE app.trip_weather (
    trip_id uuid NOT NULL REFERENCES app.trips(id) ON DELETE CASCADE,
    position integer NOT NULL CHECK (position >= 0),
    day_date text NOT NULL CHECK (length(btrim(day_date)) > 0),
    has_weather boolean NOT NULL,
    summary text,
    temperature_min_c double precision CHECK (temperature_min_c > '-Infinity'::float8 AND temperature_min_c < 'Infinity'::float8),
    temperature_max_c double precision CHECK (temperature_max_c > '-Infinity'::float8 AND temperature_max_c < 'Infinity'::float8),
    precipitation_probability_percent double precision CHECK (precipitation_probability_percent BETWEEN 0 AND 100),
    max_wind_speed_kph double precision CHECK (max_wind_speed_kph >= 0 AND max_wind_speed_kph < 'Infinity'::float8),
    PRIMARY KEY (trip_id,position),
    UNIQUE (trip_id,day_date)
);
CREATE TABLE app.trip_activities (
    trip_id uuid NOT NULL,
    day_position integer NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    activity_id text NOT NULL CHECK (length(btrim(activity_id)) > 0),
    title text NOT NULL CHECK (length(btrim(title)) > 0),
    time_use text NOT NULL CHECK (time_use IN ('scheduled','free_window')),
    place_name text, location text, category text,
    start_time text NOT NULL CHECK (length(btrim(start_time)) > 0),
    end_time text NOT NULL CHECK (length(btrim(end_time)) > 0),
    cost_amount numeric CHECK (cost_amount >= 0 AND cost_amount < 'Infinity'::numeric),
    cost_currency text CHECK (cost_currency ~ '^[A-Z]{3}$'),
    notes text, introduction text,
    PRIMARY KEY (trip_id,activity_id),
    UNIQUE (trip_id,day_position,activity_id),
    UNIQUE (trip_id,day_position,position),
    FOREIGN KEY (trip_id,day_position) REFERENCES app.trip_weather(trip_id,position) ON DELETE CASCADE,
    CHECK ((cost_amount IS NULL) = (cost_currency IS NULL))
);
CREATE TABLE app.trip_nearby (
    trip_id uuid NOT NULL REFERENCES app.trips(id) ON DELETE CASCADE,
    position integer NOT NULL CHECK (position >= 0),
    place_name text NOT NULL CHECK (length(btrim(place_name)) > 0),
    supplied_anchor_id text,
    supplied_day text,
    resolved_day_position integer,
    resolved_activity_id text,
    reason text, area text, uncertainty text, attribution text,
    PRIMARY KEY (trip_id,position),
    FOREIGN KEY (trip_id,resolved_day_position,resolved_activity_id)
        REFERENCES app.trip_activities(trip_id,day_position,activity_id),
    CHECK ((resolved_day_position IS NULL) = (resolved_activity_id IS NULL))
);
CREATE TABLE app.trip_transfers (
    trip_id uuid NOT NULL REFERENCES app.trips(id) ON DELETE CASCADE,
    position integer NOT NULL CHECK (position >= 0),
    day_position integer NOT NULL,
    from_activity_id text NOT NULL,
    to_activity_id text NOT NULL,
    departure_time text, arrival_time text, preceding_end_time text, following_start_time text,
    mode text,
    provider_duration_seconds double precision CHECK (provider_duration_seconds >= 0 AND provider_duration_seconds < 'Infinity'::float8),
    distance_meters double precision CHECK (distance_meters >= 0 AND distance_meters < 'Infinity'::float8),
    reserve_seconds double precision CHECK (reserve_seconds >= 0 AND reserve_seconds < 'Infinity'::float8),
    estimate_kind text NOT NULL CHECK (estimate_kind IN ('provider','derived','unverified')),
    status text NOT NULL CHECK (status IN ('confirmed','unknown','source_claim')),
    validation_state text CHECK (validation_state IN ('PASS','CONFIRMED','UNKNOWN')),
    source_status text,
    unknowns text[] NOT NULL,
    attribution text,
    PRIMARY KEY (trip_id,position),
    FOREIGN KEY (trip_id,day_position,from_activity_id) REFERENCES app.trip_activities(trip_id,day_position,activity_id),
    FOREIGN KEY (trip_id,day_position,to_activity_id) REFERENCES app.trip_activities(trip_id,day_position,activity_id),
    CHECK (from_activity_id <> to_activity_id)
);
