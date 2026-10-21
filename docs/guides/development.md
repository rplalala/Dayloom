# Development guide

Current entry points, reconciled 2026-10-09. [PROJECT.md](../../PROJECT.md) owns status
and authorization; [architecture](../0001-system-architecture.md) and
[application contracts](../0007-application-operations.md) explain the code and APIs.
Commands below are references, not evidence of execution or approval for a live run.

## Environment and local application

Use Python 3.12 and the existing uv environment. From the repository root:

```powershell
uv sync
uv sync --group retrieval
npm --prefix frontend ci
.\.venv\Scripts\python.exe scripts/run_api.py --host 127.0.0.1 --port 8000
```

`uv sync` also installs this repository editable, exposing `rtpeval` in `.venv`.
From the repository root, `uv run rtpeval --help` discovers the task groups.
The [root command guide](../../README.md#command-line) gives selected generation,
existing-material collection, external requirements handoff, finalization and the
shortest accepted-manifest-to-report route. The
[operational evaluation guide](../../backend/evaluation/README.md#installed-generation-and-material-handoff)
owns producer schema templates, exact parameters, pending/blocked states and source
preservation. `validate` is offline native intake; `evaluate execute` prepares and emits
the automatic report in one invocation, while preparation/replay stay offline.
Provider execution requires its own authorization and fresh one-use directory. See
[automatic evaluation](../../backend/evaluation/README.md#installed-automatic-evaluation)
for budgets, credentials, reviewed contexts and the retained prepared/digest route.
Normal material operations do not launch external author/reviewer agents. Development
smoke and historical session-specific reproduction remain separate below.

Start the frontend in another terminal with `npm --prefix frontend run dev`.
Vite proxies `/api` and `/health` to `http://127.0.0.1:8000`.
The [API launcher](../../scripts/run_api.py) selects the Windows event loop needed by
async PostgreSQL access. Use it for local Windows API development. `GET /health`
checks the application process; it does not certify provider or corpus readiness.
Product routes are `/`, `/plan`, `/trips`, `/login` and `/account`; Developer is `/dev`.
The Product r7 shell has its own shared brief surface. Developer retains independent
V0-V3 and the existing structured form. Product generation HTTP endpoints require
authentication; the durable generation UI is connected in its implementation slice.

Populate local `.env` from [the non-secret example](../../.env.example).
Foundry endpoint/deployment/key and `GOOGLE_MAPS_API_KEY` serve planning;
`.env.tripworld` or process environment supplies `OPENAI_API_KEY` and
`TRIPWORLD_DB_HOST/PORT/NAME/USER/PASSWORD` for retrieval. Model and deployment names
are distinct settings. Never commit real credentials. Default local DB host/port are
127.0.0.1:55432. See [configuration](../../config/README.md) for exact current keys.

V2/V3 require the compatible TripWorld database and artifact/embedding sidecars.
The pinned vocabulary under `.cache/tokenizer` must also exist; the planner does not
download it. `python -m tools.data.prepare_tokenizer --help` describes explicit preparation.

## Product account setup and acceptance

Use the existing PostgreSQL database for application runtime, with a role permitted
to create the separate `app` schema. Product migration/account settings are optional
for the independent V0-V3 and research commands. Keep these keys in ignored `.env`
or the process environment:

| Key | Meaning |
| --- | --- |
| `PRODUCT_DATABASE_URL` | PostgreSQL connection URL for Product persistence |
| `PRODUCT_JWT_SECRET` | Independently generated signing secret, at least 32 characters |
| `PRODUCT_ORIGIN` | Exact public HTTPS origin, or the explicitly allowed loopback development origin |
| `PRODUCT_ALLOW_INSECURE_LOOPBACK` | Default false; set true only for HTTP development on localhost/127.0.0.1/::1 |
| `PRODUCT_SESSION_SECONDS` | Default 3600; accepted range 1–86400 |
| `PRODUCT_API_PROXY` | Vite process setting; defaults to `http://127.0.0.1:8000` |

Run `uv sync --locked` and `npm --prefix frontend ci`, then apply migrations with
`uv run python scripts/migrate_product.py`. The entrypoint applies only Product SQL,
retains SHA-256 integrity and never rebuilds the TripWorld corpus. Start the API using
the normal launcher. For local browser development, configure
`PRODUCT_ORIGIN=http://localhost:5173` and the explicit loopback exception; open that
same origin in the browser. Production uses same-origin HTTPS routing.

Acceptance requires a separate disposable database whose name includes `test`.
Never point the acceptance URL at the runtime/retrieval database. Prepare an isolated
PostgreSQL instance, choose unused ports and set its URL in
`PRODUCT_TEST_DATABASE_URL`.

Both URL and PostgreSQL conninfo forms require an explicitly supplied actual database
name containing `test`; query options, usernames and environment defaults do not satisfy
the safety check. Supplied unsafe values fail before migrations, connections or cleanup.
From the worktree root:

```powershell
uv run pytest backend/tests/product/test_accounts.py --basetemp=.scratch/pytest-product
$env:PRODUCT_BROWSER_TESTS = "1"
$env:PRODUCT_TEST_API_PORT = "8120"
$env:PRODUCT_TEST_WEB_PORT = "5120"
uv run python -m playwright install chromium
uv run pytest backend/tests/product/test_browser.py --basetemp=.scratch/pytest-browser
uv run pytest backend/tests/product/test_editor_browser.py --basetemp=.scratch/pytest-editor
uv run pytest backend/tests/product/test_example_browser.py --basetemp=.scratch/pytest-examples
```

The browser fixture starts/stops its own API and Vite processes, exercises real
accounts through PostgreSQL, and writes logs/screenshots only under `.scratch/browser`
and `.scratch/detail-browser`. Example acceptance covers real public APIs, guest/account
access, exact activity-linked Nearby, keyboard navigation and desktop/800px/390px layouts.
Acceptance subprocesses inherit only required OS/tool paths and explicit test settings.
The public browser fixture excludes environment/configuration, and sensitive setup
values use redacted diagnostic representations, including fixture failures.
Set `TEMP` and `TMP` to a worktree-local `.scratch/tmp` directory when sandboxed
Windows temporary storage is unavailable; a local `UV_CACHE_DIR` can be set similarly.
Existing Playwright Chromium installations can be reused. No model, map, weather or
image-provider call is needed for these account journeys. The migration acceptance
includes rerun/integrity checks and a seeded TripWorld sentinel preservation check;
account acceptance includes deliberate profile-insert failure and rollback.

The editor journey uses the same isolated database and strict subprocess environment,
with a test-only application factory replacing the external GeoDB HTTP transport and
polishing model. Production routes/services, authentication, date policy, bounded
assistance admission and PostgreSQL remain real. Its API process uses the supported
Windows Selector loop. Prepare the pinned offline tokenizer vocabulary as described
above; this journey does not download it or call a paid model. Screenshots and logs
are written to `.scratch/editor-browser` at 390px, 800px and desktop, with distinct
browser time zones. It exercises editable requirements, exact-span ownership,
polish preview/Apply/Dismiss/Undo and delayed revisions, recovery and validation.

Public example endpoints also run without Product account/provider configuration.
`uv run pytest backend/tests/api/test_product_examples.py` checks their allowlisted
HTTP contract offline; the focused frontend detail tests exercise unresolved/undated
references, real day order and safe text rendering. The public fixtures are historical
source claims, not live provider verification.

## Independent version execution

Save one complete `planning_request_2` object as a local `request.json`, not a batch
manifest. [PlanningRequest](../../backend/app/schemas/request.py) owns the schema:
destination, start/end ISO dates, traveler count, mandatory total budget/currency and
optional additional preferences. Example shape (replace dates before a live run):

```json
{
  "input_version": "planning_request_2",
  "destination": "Tokyo, Japan",
  "start_date": "2026-10-05",
  "end_date": "2026-10-07",
  "traveler_count": 3,
  "budget": {"amount": "180000", "currency": "JPY"},
  "additional_preferences": "I definitely want to visit Meiji Jingu. I prefer small museums and local architecture."
}
```

The shared date policy admits today through today+13, inclusive duration at most ten
days, using Australia/Sydney reference time. Check `GET /api/planning/date-window`
for a fresh request. An offline fixture can pin `--reference-date`; a historical
override must not disguise stale dates in a live run.

```powershell
.\.venv\Scripts\python.exe scripts/run_v0.py --input-json request.json
.\.venv\Scripts\python.exe scripts/run_v1.py --input-json request.json --runtime-config config/runtime.yaml --development-timeout-seconds 600
.\.venv\Scripts\python.exe scripts/run_v2.py --input-json request.json --runtime-config config/runtime.yaml --development-timeout-seconds 600 --rag-env-file .env.tripworld
.\.venv\Scripts\python.exe scripts/run_v3.py --input-json request.json --runtime-config config/runtime.yaml --development-timeout-seconds 600 --rag-env-file .env.tripworld
```

V0 is tool-free and accepts neither runtime configuration nor development-timeout flags.
V1 adds normalized external evidence; V2 adds retrieval; V3 adds validation and targeted
repair. V3 requires an explicit positive development timeout no greater than 600 seconds.
These entry points can call paid services and require an approved live plan and budget.
The ordinary CLI does not recreate an acceptance capture, saved query vectors or a
missing observation. Opt-in library capture belongs to the caller.

Current tunable values come from [runtime.yaml](../../config/runtime.yaml) and its typed
loaders. For example, the main-generation input ceiling is 252000 tokens; old acceptance
budgets/hashes describe their own revisions. Use the configuration reference rather
than copying checkpoint hashes into a new run.

## Retrieval restore and reproducibility

Use the [TripWorld release/restore instructions](../../README.md#tripworld-database-release)
to restore the saved database without repeating ingestion or embedding. The database,
compatible vectors, `retrieval_entities.parquet.manifest.json` and
`phase5_embedding_run.json` have different roles and must remain compatible.
Git contains source and static contracts, not the generated corpus or Docker volume.
Release availability does not make provider calls offline or recreate original live evidence.

The [retrieval design](../0004-retrieval-persistence%28v2v3%29.md) owns compatibility and
query behavior. [V2 development records](../records/v0-v3/v2-development.md) preserve
historical builds, failures and validation. Deleted source/config recovery snapshots are
unavailable; historical paths are not recovery instructions. The old broad `validate`
operation uses historical query artifacts and maintenance ANALYZE, so it is not a default
read-only clean-clone check. Do not rebuild vectors or destroy a volume to follow this guide.

## Code and tool navigation

| Entry | Responsibility |
| --- | --- |
| [Version runners](../0001-system-architecture.md#concrete-code-map) | Independent execution and shared graph seams |
| [API boundary](../0007-application-operations.md#http-contract-map) | Product/Developer request, result and stream contracts |
| [Evaluation package](../../backend/evaluation/README.md) | Offline intake, independent review, scoring and human package commands |
| [Evaluation development tools](../../backend/evaluation/tools/route_requests_cli.py) | V0 smoke request/budget preparation; not Product runtime or final quality scoring |
| [Data tools](../../tools/data/tripworld_database.py) | Explicit ingestion, embedding, integrity and query operations |
| [Source preparation](../../tools/data/prepare_tripworld.py) | Source projection/profiling and corpus preparation |
| [Retrieval tools](../../tools/data/tripworld_retrieval.py) | Entity construction and exact retrieval reference tools |
| [Runtime acceptance](../../tools/validation/runtime_acceptance.py) | Owned-resource/capture library, not an autonomous live launcher |
| [Short-reference smoke](../../tools/validation/short_reference_packet.py) | Freeze and preflight six development adapter cases; separately authorized one-shot execution |
| [Requirement acceptance](../../tools/validation/requirement_acceptance.py) | Explicit frozen matrices and execution |
| [Retrieval validation](../../tools/validation/retrieval_validation.py) | Explicit database validation |
| [Retrieval timing](../../tools/diagnostics/retrieval_performance.py) | Bounded SQL timing/plans |
| [Payload sizing](../../tools/diagnostics/itinerary_payload.py) | Offline synthetic serializer checks |
| [Candidate diagnostics](../../tools/diagnostics/candidate_supply.py) | Offline supplied-capture analysis |

Use module invocation, for example `python -m tools.data.tripworld_database --help`.
Runtime application code does not import `tools` or tests. Runtime identity/vector
compatibility lives in `backend/app/tripworld`; persistence/build/schema tooling lives
under `tools/data/tripworld`. Requirement fingerprints have one runtime definition in
[fingerprints.py](../../backend/app/runtime/fingerprints.py); development captures use
the optional port from [requirement_capture.py](../../tools/validation/requirement_capture.py).

Evaluation's development-only V0 route tool uses
`python -m backend.evaluation.tools.route_requests_cli`. This is separate from the
repository-level `tools/validation` helpers. Ordinary evaluator CLIs remain in
`backend.evaluation`; they are command entries into actual evaluator functionality.
Neither location makes smoke a required product execution step.

## Verification and evidence

For implementation changes, choose checks for affected seams. Standard commands:

```powershell
uv run pytest
uv run ruff check .
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run build:blind-review
```

Shared schema/core changes need broader regression; milestones need the full relevant
suite. Prefer mocks/fixtures for provider ports. Tests, a milestone and a user-approved
freeze are separate gates. Consequential failures, corrective decisions and scoped
verification results belong in existing [version records](../records/README.md) and
Issues, with their revision and scope. Routine execution belongs in Git, Issues or chat.
Preference-provider diagnostics describe observed responses only, never reconstructed
explanations of older failures or additional billable usage. Nothing here authorizes a
formal benchmark, new live calls, a dataset rebuild or publication.
