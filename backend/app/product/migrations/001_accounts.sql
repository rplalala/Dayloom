CREATE TABLE app.users (
    id uuid PRIMARY KEY,
    email text NOT NULL UNIQUE CHECK (email = lower(btrim(email))),
    password_hash text NOT NULL,
    token_version integer NOT NULL DEFAULT 0 CHECK (token_version >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE app.user_profiles (
    user_id uuid PRIMARY KEY REFERENCES app.users(id) ON DELETE CASCADE,
    display_name text NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 80),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
