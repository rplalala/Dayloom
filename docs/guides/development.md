# Develop and test Dayloom

Use [deployment](deployment.md) for a first installation,
[experiments](experiments.md) for new V0–V3 runs, and
[verification](verification.md) for the saved twelve-case results.
This guide covers editing, testing and maintaining a local installation.

## Environment and local application

From the repository root, install the locked Python environment and frontend:

```bash
uv sync --locked --group retrieval
npm --prefix frontend ci
```

For API and frontend development, run these in separate terminals:

```bash
uv run python scripts/run_api.py
npm --prefix frontend run dev
```

Vite proxies `/api` and `/health` to `http://127.0.0.1:8000`. The API launcher
selects the Windows event loop required by async PostgreSQL. `/health` checks the
process; it does not check providers or retrieval data.

## Complete local Product runtime

To use the built application and API together:

```bash
npm --prefix frontend run build
uv run dayloom start
```

Open the configured origin, normally `http://localhost:5173`. Use
`uv run dayloom check` for local readiness without provider requests. An incomplete
local installation opens `/config` in setup mode; business APIs remain paused until
the resources are ready and Dayloom restarts.

Product uses the acceptance policy. Independent V0–V3 commands use development
policy unless explicitly overridden. See the
[profile comparison](../../config/README.md#product-acceptance-profile).

## Local configuration console

Open `/config` at the exact configured hostname, or use the Product settings button.
It works without a traveler account or a database connection. New installations
show the configuration password `dayloom-config-2026`; change it after entering.
Existing passwords and disabled verification preferences are retained.

The page edits database connections, provider credentials, Foundry deployment and
JWT signing keys. Blank secret inputs retain their saved values; **Clear** removes
an optional credential or connection URL. Process environment overrides are locked.
After saving, finish active tasks, stop Dayloom and run `uv run dayloom start` again.
The running process keeps its original settings until then.

The signing key is separate from the configuration password. Local startup retains
an existing `PRODUCT_JWT_SECRET`; when absent, it generates and saves a private key
in `.env`. Enter a custom key of at least 32 characters, or choose **Generate signing
key**. Replacing it signs out existing traveler accounts after restart. Saved keys
are never displayed or returned by the API.

**Check local readiness** makes no provider requests. **Check API** and **Check all
APIs** make small, billable requests using saved settings. A passing sample checks
that capability at that time; it does not apply pending settings or certify trip
quality. The [configuration contract](../0007-application-operations.md#local-configuration-console)
owns access controls, request limits and save semantics.

Password verification can be enabled, changed or disabled in **Configuration access**.
Protected pages require the password on every entry; access changes apply immediately.
To recover a forgotten password, stop Dayloom and move `.config-access.json` to an
unused backup name, then restart and set a new password:

```powershell
Move-Item -LiteralPath .config-access.json -Destination .config-access.backup
```

In Bash, use `test ! -e .config-access.backup && mv .config-access.json .config-access.backup`.
This restores the default configuration password and retains provider keys.
The console is available only through the Product launcher on an HTTP loopback
origin; the API-only launcher does not expose local management.

For multiple instances or mounted configuration, select an existing directory with
`DAYLOOM_CONFIG_DIR` as described in the [configuration reference](../../config/README.md#deployment-settings).
Run configuration-access recovery commands from that directory when one is selected.

## Local PostgreSQL naming and storage

The shared PostgreSQL database contains `app` for accounts, drafts, tasks and trips,
and `tripworld` for retrieval. The supplied connection uses database/role `dayloom`
and port `55432`. Start or stop its Compose service with:

```bash
uv run dayloom db up -d --wait postgres
uv run dayloom db stop postgres
```

`product.example.yaml` supplies portable defaults. An optional, ignored
`product.yaml` stores local deployment settings; `/config` saves database overrides
and secrets to ignored `.env`. See the
[settings reference](../../config/README.md#deployment-settings) for precedence,
connection URLs and all environment keys.

The external volume defaults to `dayloom_pgdata`. New installations create it once
with `docker volume create dayloom_pgdata`. Existing installations must retain their
actual `DAYLOOM_DB_VOLUME`; changing the name selects different storage. Connection
edits do not rename an existing database or role, change its password, or move data.
Use `uv run dayloom db config --quiet` to validate Compose settings.

Apply Product migrations after pulling schema changes:

```bash
uv run dayloom migrate
```

Migrations preserve checksums and the separate TripWorld schema. They require
only the database connection, not provider keys or JWT configuration.

## Product account setup and acceptance

Run ordinary offline checks without a database:

```bash
uv run pytest backend/tests -q
uv run ruff check .
npm --prefix frontend test -- --maxWorkers=2
npm --prefix frontend run lint
npm --prefix frontend run build
```

Database and browser acceptance tests are opt-in. Prepare a **disposable database
whose actual name contains `test`** and set `DAYLOOM_DB_TEST_URL` to its complete
connection string. Never select the runtime/retrieval database. Both URL and
PostgreSQL conninfo forms must explicitly name the isolated database; a username,
query option or default does not satisfy the guard.

In a separate PowerShell terminal, configure the test host:

```powershell
$env:DAYLOOM_DB_URL = $env:DAYLOOM_DB_TEST_URL
$env:PRODUCT_JWT_SECRET = "isolated-tests-only-not-a-runtime-signing-secret"
$env:PRODUCT_ORIGIN = "http://127.0.0.1:5120"
$env:PRODUCT_ALLOW_INSECURE_LOOPBACK = "true"
uv run pytest backend/tests/product/test_accounts.py -q
```

For browser acceptance, build the frontend, install Chromium and enable the tests:

```powershell
uv run python -m playwright install chromium
$env:PRODUCT_BROWSER_TESTS = "1"
$env:PRODUCT_TEST_API_PORT = "8120"
$env:PRODUCT_TEST_WEB_PORT = "5120"
uv run pytest backend/tests/product -q
```

Choose unused ports. Browser fixtures start their own API/Vite processes and use
controlled external adapters and images; no paid provider calls are needed. They
cover accounts, drafts, tasks, Save/Discard, copies, imports, media and replanning.
Logs and screenshots stay under `.scratch/`. For corpus persistence tests, also set
`DAYLOOM_DB_TESTS=1` and run `uv run pytest backend/tests/tripworld/test_database.py`;
these tests replace the isolated database's `tripworld` schema.

On sandboxed Windows, an inaccessible temporary directory can prevent tests from
starting. Set `TEMP` and `TMP` to an existing worktree-local `.scratch/tmp` directory;
use a fresh `--basetemp` when necessary. Explicitly decode UTF-8 child-process
output as UTF-8; the Windows locale may otherwise select GBK.

### Product media setup and acceptance

Public examples use bundled photographs with [per-image credits](../../frontend/public/dayloom/examples/README.md)
and need no media keys. Live place photos use the shared Google Maps key; atmosphere
photos optionally use Unsplash. Missing or failed photos show labelled illustrations.
The [media contract](../0007-application-operations.md#verified-place-media-and-curated-atmosphere)
owns attribution, refresh and cache behavior. Focused tests are
`test_media.py`, `test_media_cache.py`, `test_media_browser.py` and
`test_photo_session_browser.py` under `backend/tests/product/`.

## Product diagnostics

Inspect local operation logs and per-run summaries:

```bash
uv run dayloom logs --summary
uv run dayloom logs --task-id TASK_UUID
uv run dayloom logs --run-id RUN_UUID --summary
uv run dayloom logs --prune --summary
```

Logs default to `logs/product`. Correlate the task/execution IDs in operation events
with `run.json`, `summary.json` and `budget.json`; a completed planner alone does not
prove its preview was persisted. The [diagnostic contract](../0007-application-operations.md#product-diagnostics)
defines event correlation and privacy; the
[diagnostic settings reference](../../config/README.md#diagnostics-and-development-server)
lists collection levels, storage limits and environment keys. Keep logs local: they may contain
travel requests and normalized evidence. Never remove a running server's logs to
reset diagnostics.

## Independent version execution

Save a complete `planning_request_2` as `input.json`; the
[experiment guide](experiments.md#generate-v0v3-outputs) provides the request shape
and registration workflow. Prepare a run offline by omitting `--execute`:

```bash
uv run rtpeval generate v0 input.json --execute
uv run rtpeval generate v1 input.json --execute
uv run rtpeval generate v2 input.json --execute
uv run rtpeval generate v3 input.json --execute
```

Each command prints a fresh output directory. Online generation uses your provider
accounts. V2/V3 require the compatible TripWorld data and sidecars; independent
planners do not need Product accounts, migrations or a signing key.

## Retrieval restore and reproducibility

Use the [release preparation and restore steps](deployment.md#3-prepare-retrieval-data-and-vocabularies)
to install the saved corpus without repeating ingestion or embedding. Keep the dump,
entity manifest and embedding sidecar from the same release. Runtime loading never
downloads missing tokenizers. The [retrieval contract](../0004-retrieval-persistence%28v2v3%29.md)
defines compatibility and query behavior.

## Code and tool navigation

| Area | Start here |
| --- | --- |
| Version runners and shared services | [Architecture code map](../0001-system-architecture.md#concrete-code-map) |
| Product lifecycle and HTTP API | [Application contracts](../0007-application-operations.md#http-contract-map) |
| Evaluation commands | [RTPEval](../../backend/evaluation/README.md) |
| Data preparation and maintenance | `tools/data/` |
| Offline diagnostics and bounded acceptance helpers | `tools/diagnostics/`, `tools/validation/` |

## Verification and evidence

Select tests for the changed public interfaces; shared schemas and graph changes
need broader regression. Fixture-based tests check behavior without establishing
live provider permissions or research outcomes. Use the
[verification guide](verification.md) to check published results and the
[record index](../records/README.md) for dated engineering evidence.
