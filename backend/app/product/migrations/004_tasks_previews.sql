CREATE TABLE app.planning_tasks (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    operation_key text NOT NULL CHECK (length(operation_key) BETWEEN 1 AND 120),
    fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    request jsonb NOT NULL CHECK (jsonb_typeof(request) = 'object' AND request @> '{"input_version":"planning_request_2"}'),
    editor_snapshot jsonb CHECK (editor_snapshot IS NULL OR (jsonb_typeof(editor_snapshot) = 'object' AND editor_snapshot @> '{"editor_version":1}')),
    reference_date date NOT NULL,
    state text NOT NULL CHECK (state IN ('pending','running','stopping','completed',
        'needs_clarification','safety_blocked','provider_blocked','failed','cancelled')),
    revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
    progress jsonb NOT NULL DEFAULT '{"message":"Waiting to start","stage":"pending"}',
    outcome jsonb,
    pending_deadline timestamptz NOT NULL CHECK (isfinite(pending_deadline)),
    execution_id uuid,
    fence bigint NOT NULL DEFAULT 0 CHECK (fence >= 0),
    lease_deadline timestamptz CHECK (lease_deadline IS NULL OR isfinite(lease_deadline)),
    preview_id uuid,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (owner_id, operation_key),
    UNIQUE (owner_id, id),
    CHECK (state NOT IN ('running','stopping') OR
        (execution_id IS NOT NULL AND lease_deadline IS NOT NULL)),
    CHECK ((state = 'completed') = (preview_id IS NOT NULL))
);
CREATE UNIQUE INDEX planning_tasks_one_active ON app.planning_tasks(owner_id)
    WHERE state IN ('pending','running','stopping');
CREATE INDEX planning_tasks_recent ON app.planning_tasks(owner_id,created_at DESC,id);

CREATE TABLE app.itinerary_previews (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    source_task_id uuid,
    source_kind text NOT NULL CHECK (source_kind IN ('generated_v3','imported','copied','example')),
    operation_key text NOT NULL CHECK (length(operation_key) BETWEEN 1 AND 120),
    fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    schema_version text NOT NULL DEFAULT 'product_detail_1' CHECK (schema_version = 'product_detail_1'),
    snapshot jsonb CHECK (snapshot IS NULL OR (jsonb_typeof(snapshot) = 'object' AND snapshot @> '{"schema_version":"product_detail_1"}')),
    original_request jsonb,
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','saved','discarded')),
    saved_trip_id uuid,
    source_id text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    decided_at timestamptz,
    UNIQUE (owner_id,id),
    UNIQUE (owner_id,source_task_id,id),
    UNIQUE (owner_id,source_kind,operation_key),
    UNIQUE (source_task_id),
    FOREIGN KEY (owner_id,source_task_id) REFERENCES app.planning_tasks(owner_id,id),
    CHECK ((state = 'pending') = (snapshot IS NOT NULL)),
    CHECK ((state = 'saved') = (saved_trip_id IS NOT NULL)),
    CHECK ((state = 'pending') = (decided_at IS NULL)),
    CHECK (source_kind <> 'generated_v3' OR source_task_id IS NOT NULL)
);
ALTER TABLE app.planning_tasks ADD CONSTRAINT task_preview_same_owner
    FOREIGN KEY (owner_id,id,preview_id) REFERENCES app.itinerary_previews(owner_id,source_task_id,id)
    DEFERRABLE INITIALLY DEFERRED;
