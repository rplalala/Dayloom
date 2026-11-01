# Run Dayloom locally

For the Bash-first, complete Docker deployment bundle, use the
[Docker deployment guide](../../deploy/README.md). This guide covers installation
from a source checkout and retains the existing host-based workflow.

This guide installs the full web application. To check the saved research results
without running it, use [findings verification](verification.md).

Run commands from the repository root. Except for copying `.env`, the commands
below work in both PowerShell and Bash.

## 1. Install dependencies

You need **Python 3.12**, **uv**, **Node.js 24.x with npm**, and **Docker Compose**.
The local database image supplies PostgreSQL 17 and pgvector. A native installation
can instead use PostgreSQL 17.10 with pgvector 0.8.2.

```bash
uv sync --locked --group retrieval
npm --prefix frontend ci
```

## 2. Configure local secrets

For a new installation, copy `.env.example` to `.env`:

PowerShell:

```powershell
Copy-Item .env.example .env
```

Bash:

```bash
cp .env.example .env
```

Keep an existing `.env`. Set `DAYLOOM_DB_PASSWORD` to the password of your
PostgreSQL role before starting the database. The supplied defaults are database/role
`dayloom`, port `55432`, and application address `http://localhost:5173`.

[product.example.yaml](../../product.example.yaml) is the portable template.
If you need different Product options, copy it to ignored `product.yaml` and edit
that local copy. Provider credentials and database connections can also be entered
at `/config` after startup. Process environment overrides take precedence.

Leave `PRODUCT_JWT_SECRET` blank on a new local installation: `dayloom start`
generates and saves it automatically. Existing keys are retained. The configuration
page supports a custom key or explicit replacement generation.

## 3. Prepare retrieval data and vocabularies

Download and extract the [TripWorld release](../../README.md#tripworld-database-release)
beside the source directory. The [data guide](../../data/tripworld/README.md) explains
the upstream source, processing and release contents.

```text
workspace/
  Dayloom/
  tripworld-vector-release-20260926/
```

Verify its checksums and install the two runtime sidecars:

```bash
uv run dayloom prepare ../tripworld-vector-release-20260926
```

This checks the complete release, including the approximately 4.43 GB dump, and
copies its retrieval metadata into `data/tripworld/`. Conflicting existing metadata
is preserved and reported.

Prepare both pinned tokenizer vocabularies:

```bash
uv run dayloom tokenizers
```

This may download public vocabulary files; it makes no model or embedding requests.
For an offline installation, supply the planner cache under `.cache/tokenizer/`
and the embedding cache under `data/tripworld/tokenizer_cache/`, then use
`uv run dayloom tokenizers --offline` to verify them.

## 4. Start and populate the database

For a **new installation**, create the external volume and start PostgreSQL:

```bash
docker volume create dayloom_pgdata
uv run dayloom db up -d --wait postgres
uv run dayloom restore ../tripworld-vector-release-20260926
```

The restore command verifies the release and imports its stored vectors into the
empty local Compose database. It refuses existing user schemas or tables and
restores in one transaction. Existing installations should skip restoration and
retain their configured volume. No corpus rebuild or embedding calls are needed.

The shortcut targets the supplied Docker container `postgres`. With native
PostgreSQL, use `pg_restore --no-owner --no-privileges` against your empty database
as described in the release README, using your configured database and role.
For connection or volume overrides, see [database configuration](development.md#local-postgresql-naming-and-storage).

## 5. Build, migrate and launch

```bash
npm --prefix frontend run build
uv run dayloom migrate
uv run dayloom start
```

Open [localhost:5173/config](http://localhost:5173/config), or use the bottom-right
settings button. New installations display the local configuration test password;
change it after entering. Configure the database connection and services you use:

| Service | Purpose |
| --- | --- |
| PostgreSQL | Host, port, database, role and password; optional complete connection URL |
| Account sessions | Retained or automatically generated JWT key; custom key and generation controls |
| Azure Foundry | Planner model and web search; use the supported `gpt-6-luna` deployment profile |
| OpenAI | TripWorld query embeddings |
| Google Maps | Places, routes and place photographs |
| Unsplash | Optional atmosphere photographs (`UNSPLASH_API_KEY`) |

Save your settings, stop with Ctrl+C, and run `uv run dayloom start` again.
Foundry endpoint/deployment are stored in ignored `product.yaml`; database overrides
and secrets are stored in ignored `.env`. Changing a connection does not migrate data
or update an existing PostgreSQL role password.
Incomplete installations open in setup mode so configuration remains available.

Once ready, open [Dayloom](http://localhost:5173), create an account and plan a trip.
Planning and online features use your provider accounts. Optional API checks can
also incur charges; web-search charges are outside the current spending guard.

## Check, stop and troubleshoot

Check local configuration, database access, migrations, vocabularies and retrieval
compatibility without contacting providers:

```bash
uv run dayloom check
```

Ctrl+C stops the application. Stop the database while retaining its data with:

```bash
uv run dayloom db stop postgres
```

| Problem | Action |
| --- | --- |
| Missing external volume | Create the configured volume before database startup. |
| Setup mode | Resolve the resources listed on `/config`, then restart. |
| Missing vocabulary | Run `dayloom tokenizers`; caches elsewhere do not satisfy the runtime paths. |
| Retrieval mismatch | Use both sidecars and the dump from the same release. |
| Restore refuses existing data | Skip restoration for an already prepared database. |
| Saved settings have no effect | Restart; process environment overrides still take precedence. |
| Configuration password forgotten | Follow [local access recovery](development.md#local-configuration-console). |

For separate API/Vite development, automated tests and diagnostics, continue with
the [development guide](development.md).
