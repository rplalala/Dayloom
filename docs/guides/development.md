# Development guide

Current entry points, reconciled 2026-10-22. [PROJECT.md](../../PROJECT.md) owns status
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
Product routes include `/`, `/plan`, `/trips`, `/import`, `/login`, `/account`, `/planning`,
`/planning/:taskId` and `/previews/:previewId`; Developer is `/dev`.
The Product r7 shell has its own shared brief surface. Developer retains independent
V0-V3 and the existing structured form. Product generation HTTP endpoints require
authentication and submit the durable account-owned task lifecycle.

Populate local `.env` from [the non-secret example](../../.env.example).
Foundry endpoint/deployment/key and `GOOGLE_MAPS_API_KEY` serve planning;
`.env.tripworld` or process environment supplies `OPENAI_API_KEY` and
`TRIPWORLD_DB_HOST/PORT/NAME/USER/PASSWORD` for retrieval. Model and deployment names
are distinct settings. Never commit real credentials. Default local DB host/port are
127.0.0.1:55432. See [configuration](../../config/README.md) for exact current keys.

V2/V3 require the compatible TripWorld database and artifact/embedding sidecars.
The pinned vocabulary under `.cache/tokenizer` must also exist; the planner does not
download it. `python -m tools.data.prepare_tokenizer --help` describes explicit preparation.

For V2/V3 retrieval, also prepare the pinned embedding vocabulary under
`data/tripworld/tokenizer_cache`; follow the TripWorld readiness instructions before
claiming retrieval acceptance. A degraded retrieval fallback is not that acceptance.

## Complete local Product runtime

The built Product runs the React frontend and normal FastAPI application on one
origin. It uses the configured real model, Google Places/Routes, Open-Meteo,
TripWorld retrieval and media adapters. It does not load a test application factory,
provider substitutes or the offline walkthrough's external-link interception.

Prepare the ignored environment files and Product settings described below, then run:

```powershell
uv sync --locked --group retrieval
npm --prefix frontend ci
npm --prefix frontend run build
uv run python scripts/migrate_product.py
uv run python scripts/run_product.py --check
uv run python scripts/run_product.py
```

The default address is `http://localhost:5173`; set `PRODUCT_ORIGIN` to that exact
origin and enable the explicit HTTP loopback exception. `--port` must match the
configured origin's port. The launcher loads `.env` and `.env.tripworld` from the
repository root without overriding existing process values. It serves `frontend/dist`,
including direct navigation/reload of Product and Developer routes; missing APIs and
assets retain their HTTP errors. Rebuild the frontend after changing its source.

`--check` validates configuration, both local tokenizer vocabularies, Product database
access and TripWorld manifest/embedding-space compatibility. It reads local databases
without model, query-embedding, map, weather or image requests. Passing it establishes
local readiness, not live credential validity, provider availability or generation quality.
Generating, polishing, destination suggestions and media viewing use real services when
invoked; execute provider acceptance only within its separately authorized limits.

Use the existing daily database for this runtime. Disposable automated-test databases
and the substituted human-walkthrough database remain separate; accounts and drafts do
not move between them automatically. The normal API-only/Vite development commands
above remain available, and independent V0–V3 entrypoints are unchanged.

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
| `PRODUCT_GOOGLE_PLACES_MEDIA_KEY` | Optional server-only Places API key for verified Product photos; missing means illustration fallback |
| `PRODUCT_UNSPLASH_ACCESS_KEY` | Optional server-only Unsplash key for the curated atmosphere catalog; takes precedence over the existing `UNSPLASH_API_KEY` alias; missing both means illustration fallback |

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
The pytest host also needs complete isolated Product settings, even though browser
children construct their own strict environment. Point both Product URLs at the
same disposable database and use a synthetic signing secret. From the worktree root:

```powershell
$env:PRODUCT_DATABASE_URL = $env:PRODUCT_TEST_DATABASE_URL
$env:PRODUCT_JWT_SECRET = "isolated-tests-only-not-a-runtime-signing-secret"
$env:PRODUCT_ORIGIN = "http://127.0.0.1:5120"
$env:PRODUCT_ALLOW_INSECURE_LOOPBACK = "true"
uv run pytest backend/tests/product/test_accounts.py --basetemp=.scratch/pytest-product
uv run pytest backend/tests/product/test_profiles.py --basetemp=.scratch/pytest-profile
$env:PRODUCT_BROWSER_TESTS = "1"
$env:PRODUCT_TEST_API_PORT = "8120"
$env:PRODUCT_TEST_WEB_PORT = "5120"
uv run python -m playwright install chromium
uv run pytest backend/tests/product/test_browser.py --basetemp=.scratch/pytest-browser
uv run pytest backend/tests/product/test_editor_browser.py --basetemp=.scratch/pytest-editor
uv run pytest backend/tests/product/test_example_browser.py --basetemp=.scratch/pytest-examples
uv run pytest backend/tests/product/test_profile_browser.py --basetemp=.scratch/pytest-profile-browser
uv run pytest backend/tests/product/test_drafts.py --basetemp=.scratch/pytest-drafts
uv run pytest backend/tests/product/test_draft_browser.py --basetemp=.scratch/pytest-draft-browser
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
Profile acceptance checks supported domains, deduplication, owner isolation, literal
notes, database constraints/cascade and persistence after application recreation.
The real browser edits defaults, checks initials and the absence of avatar upload,
then verifies visible new-brief defaults while existing/reloaded editor content remains
unchanged. Profile screenshots belong to `.scratch/profile-browser`.

The combined profile/draft/task/replan acceptance is runnable with the same isolated
database and browser settings:

```powershell
uv run pytest backend/tests/product/test_replan_browser.py -q
```

It uses the real task coordinator, PlanningService, V3, retrieval lifecycle, API and
PostgreSQL, replacing only external adapters with controlled responses. The journey
updates persisted defaults while a task runs, reopens an existing draft, replans both
complete generated and partial historical imported sources, fills unknown values and
saves new previews independently. It checks current generation validation, owner isolation,
zero writes on form opening, unchanged source requests and latest defaults on a genuinely
new brief. Screenshots belong to `.scratch/replan-browser`; task signals and server logs
remain under `.scratch/task-browser`. The [replan contract](../0007-application-operations.md#replanning-saved-itineraries)
defines which original facts may seed the form.

The editor journey uses the same isolated database and strict subprocess environment,
with a test-only application factory replacing the external GeoDB HTTP transport and
polishing model. Production routes/services, authentication, date policy, bounded
assistance admission and PostgreSQL remain real. Its API process uses the supported
Windows Selector loop. Prepare the pinned offline tokenizer vocabulary as described
above; this journey does not download it or call a paid model. Screenshots and logs
are written to `.scratch/editor-browser` at 390px, 800px and desktop, with distinct
browser time zones. It exercises editable requirements, exact-span ownership,
polish preview/Apply/Dismiss/Undo and delayed revisions, recovery and validation.

Draft acceptance uses the same external-adapter substitutes and real account/API/database
boundary. It covers incomplete round trips, recreated application/browser state,
independent copies, owner isolation, simultaneous revision conflicts, stable server-side
pages, database constraints/cascades, guest return and expiry recovery. Draft screenshots
are written to `.scratch/draft-browser`. The [draft contract](../0007-application-operations.md#incomplete-drafts-and-the-collection-boundary)
defines schema bounds and listing parameters. Apply the public migration entrypoint before
starting the API; no additional configuration is required for drafts.

Public example endpoints also run without Product account/provider configuration.
`uv run pytest backend/tests/api/test_product_examples.py` checks their allowlisted
HTTP contract offline; the focused frontend detail tests exercise unresolved/undated
references, real day order and safe text rendering. The public fixtures are historical
source claims, not live provider verification.

### Product media setup and acceptance

Apply migrations before starting an updated API; migration 006 adds stable private
place bindings to previews/trips. Media keys are optional and separate from research
configuration. Keep them server-side. Without either key, the corresponding image
remains an explicitly labelled illustration and all planning, import, preview and Save
flows remain usable. See the [media contract](../0007-application-operations.md#verified-place-media-and-curated-atmosphere)
for identity, provider, refresh and request bounds. Before a future public Google-enabled
deployment, supply publicly accessible application Terms of Use and Privacy Policy
incorporating the provider terms/privacy requirements; local substituted acceptance does
not establish a deployment or live-provider acceptance.

With the isolated Product test database and browser ports configured, run:

```powershell
uv run pytest backend/tests/product/test_media.py backend/tests/product/test_media_projection.py --basetemp=.scratch/pytest-media-api
$env:PRODUCT_BROWSER_TESTS = "1"
uv run pytest backend/tests/product/test_media_browser.py --basetemp=.scratch/pytest-media-browser
```

The media journey executes the real PlanningService/V3, coordinator, Product APIs and
PostgreSQL. External place/model/weather/route/retrieval/media transports and browser
images use controlled replacements. It verifies final scheduled/Nearby photo bindings,
Google Maps and photographer attribution, image expiration, refresh/Save/reload recovery,
forged imports, dimension bounds, owner isolation and 390px/800px/desktop layout.
Lists remain illustrated before and after opening a place. Google photographs and
readable author/source credits appear together in place detail dialogs at all three
widths. Unsplash checks cover hover, keyboard focus, Escape and touch disclosure,
including collection image links and hero shading. Product overview and copyable
summary checks exclude internal review fields while preserving route uncertainty.
Provider/API checks also exercise redirects, foreign resources/URLs, bounded bodies and
work, migration constraints/checksum integrity and missing media access. Logs/screenshots
remain under the worktree's `.scratch/media-browser`, `.scratch/product-polish/browser`
and selected pytest basetemp.

Every Product browser fixture uses the same test-only media transport override and
installs external-request interception before context navigation. This includes older
auth/editor/task/example/import suites: Chromium's network is independent of pytest's
Python socket guard. These checks require neither a real media key nor any live image,
Unsplash API or Google Photos request.

### Durable task acceptance

Product Generate uses `POST /api/planning/tasks` with an owner-scoped `operation_key`,
confirmed `request` and optional editor snapshot. The legacy HTTP/SSE adapters require
`Idempotency-Key` and share the same coordinator. Migrations include tasks, previews
and normalized saved trips; rerun the public migration command before starting the application. No new
provider configuration or external queue is required. A process shutdown interrupts its
owned work; after an abrupt crash, expired pending/lease records reconcile on access or
periodically, retaining input without automatic execution restart.

`POST /api/planning/tasks/{id}/stop` uses the current account cookie, Origin and CSRF
token. Read the task after an ambiguous Stop response before explicitly trying again.
Pending work can stop immediately; running work remains `stopping` until its executing
application cleans up its connections, or its finite lease recovers as interrupted.
Late Stop preserves completed previews. The outcome page offers explicit input revision
and a preserve-or-replace choice for another open brief; opening inputs never generates.

With the explicitly isolated test database and browser ports above configured, run
`uv run pytest backend/tests/product/test_tasks.py backend/tests/product/test_task_stop.py backend/tests/product/test_task_races.py backend/tests/product/test_task_browser.py`.
The browser factory runs the actual application/V3 graph with controlled external model,
place, route, weather, retrieval and introduction adapters. Its completion signals,
logs and screenshots remain in that worktree's `.scratch/task-browser/`. These cases
cover lost accepted responses, changing/saving another brief, SSE/browser detachment,
logout, preview recovery, deterministic Stop/completion lock races, cross-instance
transport cleanup, typed outcomes, explicit revision/retry and stale execution authority;
they make no paid calls.

### Preview Save and Discard acceptance

Save explicitly creates an immutable saved trip; confirmed Discard removes pending
content. Both use the preview's durable decision identity. Refreshing a decided preview
recovers its receipt, and saved details read normalized rows without provider calls.
The library includes saved cards beside drafts with title-only rename and confirmed
deletion. Whole-trip Copy and Keep example use the independent-copy contract below. Weather attribution/source
URLs are excluded from saved storage; all other supported public detail facts retain
their supplied order and time text.

With the same isolated database configured, run:

```powershell
uv run pytest backend/tests/product/test_saved.py backend/tests/product/test_saved_constraints.py backend/tests/product/test_task_browser.py
```

These cases run public migration fresh/rerun/checksum rejection, SQL constraints,
atomic child-write rollback, concurrent decisions, repeated/lost-response recovery,
owner isolation, deleted-result tombstones and actual browser Save/confirmed Discard.
The browser includes a committed Save response delayed until another draft is open;
the late response cannot navigate or replace that draft. Screenshots/logs remain in
`.scratch/task-browser/`. The fresh migration case resets only the explicitly isolated
test database's `app` schema and verifies a separate `tripworld` marker survives.

### Independent Copy and Keep example acceptance

The detail hero and saved library cards expose explicit whole-trip copying. Public example
details offer Keep a copy, returning guests through login to the same example without an
automatic write. Copy is distinct from the shared detail's Copy summary export action.
The [copy contract](../0007-application-operations.md#independent-trip-copies-and-kept-examples)
defines operation identity, source ownership, independent snapshots and deleted-result receipts.

With the isolated database and browser ports configured above, run:

```powershell
uv run pytest backend/tests/product/test_copies.py backend/tests/product/test_operation_keys.py backend/tests/product/test_copy_browser.py -q
uv run pytest backend/tests/product/test_copy_media.py backend/tests/product/test_saved_constraints.py -q
```

These cases exercise real API/PostgreSQL transactions and Chromium journeys for historical
import/example content, simultaneous same-key copies, conflicting intents, deleted source
and result replay, child-write rollback, owner/CSRF isolation, lost responses and explicit
retry. Browser checks include guest brief preservation, same-account expiry recovery,
logout clearing, navigation fences and dialog keyboard/layout behavior at 390px, 800px
and desktop widths. Recovery covers separate A/B source identities and status-only checks
after source/result deletion, through both the unavailable detail and My trips recovery
entry. Key admission/query tests use real APIs/PostgreSQL for Copy/import punctuation,
unchanged normal lookup paths and rejected controls across Copy/import/task interfaces.
Media-copy acceptance carries an adopted server identity through actual projection,
preview, Save and independent copies; only controlled HTTP display adapters are replaced.
It checks empty decided-receipt bindings, unchanged public exports, source/result deletion,
forged import/Copy rejection and stable IDs without persisted photo resource names or URLs.
Screenshots belong to `.scratch/copy-browser`; API/Vite logs use
`.scratch/browser`. External display media must use the browser fixture's controlled
replacements; the copy mutation itself makes no provider calls.

### Historical import/export acceptance

Open `/import` to paste JSON or choose a file, then explicitly Preview and Save. Supported
formats, trust, partial known requests, time precision and operation recovery are defined
in the [import/export contract](../0007-application-operations.md#historical-json-import-and-export).
The shared detail's JSON export can be reimported with a new operation key; text export
and Copy summary use only the already loaded public detail. None runs generation or refresh.

With the isolated database and browser ports configured above, run:

```powershell
uv run pytest backend/tests/product/test_imports.py backend/tests/product/test_import_responsiveness.py backend/tests/product/test_import_browser.py
uv run pytest backend/tests/product/test_import_storage.py
```

These checks use actual APIs/PostgreSQL for concurrent operation identity, account isolation,
recreation, lost-response lookup, explicit retry, field errors and preview decisions. An actual
PostgreSQL lock wait checks concurrent health/Stop API responsiveness. Browser
acceptance covers historical differing-offset/nanosecond/empty-day/orphan content through
paste, Save, JSON download and file reimport, plus selectable summary, delayed-file/lost-response
recovery and historical zero/overlap connection gaps with unverified source provenance. Its screenshots live
under `.scratch/import-browser`; its API/Vite lifecycle uses the shared isolated browser fixture.
Storage admission checks cover located NUL/surrogate errors, exact activity-cost numeric
limits, insignificant scale/zero semantics and unchanged large original-request budgets.
Boundary integer reads return SQL booleans, avoiding expanded amounts in HTTP/log output.

### Mixed library acceptance

With the same isolated database and browser ports configured, run:

```powershell
uv run pytest backend/tests/product/test_library.py backend/tests/product/test_library_browser.py
```

These cases exercise mixed saved/draft creation-time and name ordering, exact UUID/kind
tie boundaries, literal title/destination search, bounded pages, historical detail,
revision conflicts, title/request immutability, confirmed deletion and retained
deleted-result receipts. Owner-scoped weather/Nearby/transfer views read the saved
snapshot without provider refresh. The actual browser covers cross-page navigation,
empty/no-match states, search after rename, cancel/confirm deletion and late Save;
desktop/800px/390px screenshots are written to `.scratch/library-browser/`.
An expired-cookie case delays the real session check and verifies immediate content
hiding after mutation 401, followed by same-account login without replaying the write.
Run `test_saved_constraints.py` above for public fresh/rerun migration, composite foreign
keys, normalized child cascades and database-level account cascades. See the
[collection contract](../0007-application-operations.md#incomplete-drafts-and-the-collection-boundary)
for sorting and bounds.

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
