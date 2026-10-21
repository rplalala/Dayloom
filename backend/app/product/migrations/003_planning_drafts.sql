CREATE TABLE app.planning_drafts (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 120),
    editor jsonb NOT NULL CHECK (jsonb_typeof(editor) = 'object' AND editor @> '{"editor_version":1}'::jsonb),
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX planning_drafts_owner_updated ON app.planning_drafts(owner_id, updated_at DESC, id);
