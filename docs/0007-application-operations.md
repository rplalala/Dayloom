# Application interfaces and operations

Dayloom presents V3 through an account-owned brief/draft → durable task → recoverable
preview → explicit Save/Discard lifecycle. This document defines application contracts;
[deployment](guides/deployment.md) and [development](guides/development.md) contain
operating instructions. [Lifecycle evidence](records/frontend/dayloom-product-lifecycle-acceptance.md)
records actual checks and limitations.

## Product and independent planner surfaces

React handles editing, progress observation and rendering; FastAPI validates input,
coordinates execution and serializes allowlisted results. Product exposes no engine
selector. Independent command-line/programmatic interfaces retain V0–V3 diagnostics
and their own execution lifecycle. The former Developer page/APIs are removed;
`/dev` routes return the normal not-found page.

Server date policy is authoritative. Inputs retain ISO date-only strings rather
than browser timezone conversions. Edited input cannot be overwritten by stale
responses. Completion is a policy observation, not global feasibility.

## Local configuration console

`/config` runs outside traveler session/task providers. The host Product launcher
requires an HTTP loopback origin/listener. Explicit container-local mode permits
a container listener with a loopback public origin and a finite operator-configured
list of host-forwarding peer IPs. API-only/nonlocal management remains disabled.
Product pages expose a settings link when available.

| Settings | Saved location |
| --- | --- |
| Foundry endpoint/deployment | `product.yaml` |
| Azure, OpenAI, Google Maps and `UNSPLASH_API_KEY` | `.env` |
| `DAYLOOM_DB_HOST`, `DAYLOOM_DB_PORT`, `DAYLOOM_DB_NAME`, `DAYLOOM_DB_USER`, `DAYLOOM_DB_PASSWORD` | `.env` |
| `DAYLOOM_DB_URL` connection override | `.env` |
| `PRODUCT_JWT_SECRET` | `.env` |

Tracked `product.example.yaml` supplies defaults; ignored `product.yaml` overrides
it. The [configuration reference](../config/README.md#deployment-settings) owns
precedence. Process-managed fields are read-only. A complete database URL overrides
split fields; explicit blank selects split fields from the same chosen source.
Database edits neither migrate data nor change a PostgreSQL role password.

Unsplash is saved only as `UNSPLASH_API_KEY`. The old `PRODUCT_UNSPLASH_ACCESS_KEY`
is read compatibility: canonical wins within one source, including explicit empty;
process environment wins over dotenv. Either process name locks editing. Save/Clear
removes old dotenv bindings while preserving dependent bindings' resolved values.

Local startup retains an existing JWT key or generates/saves 48 random bytes when
absent. Custom keys need 32 characters. Explicit key generation uses the same access,
revision and environment locks as Save. Responses expose presence only; restart applies
the key and invalidates prior sessions. API-only/nonlocal launches need a configured key.
Legacy local Foundry dotenv fields migrate to YAML with dependent values preserved.

### Access and writes

New host installations display the test password `dayloom-config-2026` and change
instructions. Container bootstrap generates an independent random management password
and returns it once to the explicit host setup caller; normal application logs and
HTTP responses do not expose it or advertise the host test-password hint. Only its
Argon2id hash is persisted. A host-only reset command rotates management access without
changing provider credentials, the signing key or Product accounts. Existing
custom/disabled settings remain. Custom passwords are 10–128 characters, hashed in
ignored `.config-access.json`. Without password protection, the browser establishes
a separate 30-minute HttpOnly, SameSite=Strict management cookie.

Protected entry/reload requires unlocking again. An in-memory session-bound token
accompanies protected requests; an old cookie alone cannot recover access. Navigation
clears the token. Password changes/disabling require current-password verification,
recheck at commit and immediate cross-process revocation. Corrupt/unreadable/symlinked
access files fail closed. Host recovery is documented in the development guide.

All management operations require a loopback peer or an explicitly admitted container
forwarding IP, and exact Host; writes require exact Origin. A private subnet and
forwarded headers do not grant access. Unlock attempts, sessions and bodies are bounded.
Responses are `no-store`, secrets are presence-only, and errors exclude submitted values.
Omission retains a value; explicit empty clears it except the signing key.

An opaque revision binds saved texts and resolved values. Stale writes return 409.
Under one cross-process lock, Save stages both files, atomically replaces each and
rolls back completed replacements on I/O error. A host crash between replacements
is not a transaction. Unrelated settings/order are preserved where possible; complex
YAML may normalize. Running provider/database/signing settings are pinned until restart.

Setup mode keeps static/config routes available while business APIs return 503.
Readiness checks local resources with running pinned settings, not newly saved
connections; `uv run dayloom check` independently checks saved settings. Neither
validates provider credentials or makes provider calls.

### Explicit API checks

`POST /api/config/check` binds a saved revision and fixed service identifier. It
rejects stale input before sending and marks results stale if settings change.
The browser clears results on edit/save/reload/lock; results stay in memory.

| Service | Sample capability | Maximum HTTP attempts |
| --- | --- | ---: |
| Azure Foundry | Strict structured response and completed web search | 2 |
| OpenAI | 1,536-dimensional `text-embedding-3-small` vector | 1 |
| Google Maps | Text search, 1×1 WALK matrix, photo Details and URI | 4 |
| Unsplash | Existing catalog photograph metadata | 1 |

A check allows eight attempts within 60 seconds, with 15-second requests (30 for
web search), no retries/redirects, 128 KiB bodies and one active check per instance.
Hosts are fixed or admitted Azure HTTPS v1 endpoints. Credentials stay in headers.
Fixed public samples contain no traveler input. Checks may incur charges; limits
are not a monetary cap. Startup/readiness never triggers them. Timeout or absent
sample photos is inconclusive, and a sample PASS is not universal readiness.

Owners: [configuration](../backend/app/product/configuration.py),
[management API](../backend/app/product/configuration_api.py),
[readiness](../backend/app/product/local_readiness.py), [checks](../backend/app/product/api_checks.py).

## Product diagnostics

HTTP responses carry a server `X-Request-ID`. Background logs also bind task,
execution/run UUID, account UUID and fence. Operation logs record route template,
status, duration, bounded identifiers and safe codes; they exclude bodies, credentials,
query strings and raw exception messages. Sanitized exception chains retain types/locations.
A completed planner invocation differs from committed task completion or stale rejected publication.

Native planner diagnostics retain ordered events, optional payloads, numeric budgets
and a separate final summary. `run.json` and final-summary metadata each have a
64 KiB allowance with explicit truncation. Repair sizing and compact completion
survive oversized detailed events. Inclusive stage timings are not additive. Missing
usage is not zero; spending reservations are conservative bounds, not invoices.
Collection does not change retries, budgets or cancellation ownership.

Browser error reports contain bounded types/code locations, route structure and failed
request IDs, not message/form/query text. They are untrusted observations. Exact-origin
`POST /api/diagnostics/client-errors` admits 4 KiB and 20 reports per peer/minute/process;
the browser deduplicates to ten/minute and excludes aborts/recursive diagnostic failures.
An export click does not establish successful file saving.

Logs rotate under inter-process lock. Retention protects active runs; abandoned markers
become eligible after 24 hours. Cleanup stays inside the owned namespace, skips symlink
directories and preserves unrelated files. Storage failure warns without replacing the
business result. [Settings](../config/README.md#diagnostics-and-development-server)
and [commands](guides/development.md#product-diagnostics) own retention operations.

## Input assistance

GeoDB suggestions use a bounded backend adapter with manual fallback; selected IDs
are not planner evidence. Explicit one-call preference polish offers preview,
Apply/Dismiss and Undo. Literal whitespace and client revisions preserve edit-span
ownership. Empty text fails; a schema-valid suggestion proves neither equivalence
nor better input acceptance. No assistance action submits planning automatically.

## HTTP contract map

| Surface | Contract |
| --- | --- |
| `/api/config` and access/session/signing-key/readiness/check | Local redacted settings and explicit checks |
| `/api/auth/register`, `/login`, `/current`, `/logout`, `/account` | Account/session lifecycle and confirmed deletion |
| `/api/profile` | Owner defaults |
| `/api/drafts`, `/api/library` | Revisioned incomplete briefs and paged mixed collection |
| `/api/planning`, `/api/planning/stream` | Idempotent 202 task submission and persisted observation |
| `/api/planning/tasks`, `/recent`, `/active`, `/{id}`, `/{id}/stop` | Owner task lookup, recovery and explicit Stop |
| `/api/previews`, `/{id}`, `/{id}/save`, `/{id}/discard` | Recoverable detail and durable decisions |
| `/api/trips/{id}` and `/weather`, `/nearby`, `/transfers` | Saved detail, title mutation, deletion and ordered subviews |
| `/api/copies`, `/api/imports` | Explicit owner operations and query-based receipt lookup |
| `/api/examples`, `/{id}`, `/{id}/media` | Two read-only public historical examples |
| `/api/{previews\|trips}/{id}/media`, `/supporting-media`, `/cover-media` | Owner-authorized display metadata |
| `/api/media/destination`, `/api/media/curated/{key}` | Controlled public atmosphere metadata |
| `/api/planning/date-window`, `/api/input-assistance/...` | Public admission window and bounded input help |
| `/api/diagnostics/client-errors`, `/health` | Safe browser observations and process health |

[PlanningRequest](../backend/app/schemas/request.py), [Product router](../backend/app/api/product/planning.py)
and [ProductDetail](../backend/app/product/detail.py) own exact wire fields.
Product accepts no engine/reference-date override. Invalid fields return 422 before
external work. Outcomes distinguish completed, needs_clarification, safety_blocked,
provider_blocked, failed and cancelled. Clear-but-unfulfilled requirements return
specific failure, not a request to rewrite clear wording.

Public completion retains supported required experiences, planned-visit links,
attention items and optional Rich `pace_review` with dated counts/targets/states.
Preview, Save/read and export preserve the projection. UI distinguishes highlights,
needs confirmation and still to arrange without exposing internal scores/codes.
Historical missing fields are not backfilled. Partial Rich results remain usable
previews without a successful-Repair claim. Choosing Rich never inserts a hard quota.

## Information and security boundaries

Provider content is untrusted text. Public projections exclude credentials, prompts,
raw payloads and research internals. User prose grants no arbitrary fetch authority.
Product's checksum-checked migrator changes only `app`; TripWorld remains separate.
Per-process limits are not distributed abuse/billing enforcement or public deployment assurance.

## Product experience and persistence design

The r7 interface uses English, initials-only accounts, a shared brief editor and
reusable detail. Current behavior below replaces prototype browser simulations.

### Product tables and transaction boundaries

| Tables | Responsibility |
| --- | --- |
| `users`, `user_profiles` | Identity, credentials, revocation and defaults |
| `planning_drafts` | Incomplete revisioned snapshots |
| `planning_tasks`, `itinerary_previews` | Execution and decisions |
| `trips` | Saved headers/metadata |
| `trip_weather`, `trip_activities`, `trip_nearby`, `trip_transfers` | Ordered normalized content |
| `schema_migrations` | Applied names/checksums |

Registration, task-plus-preview completion and Save-plus-children/decision each commit
atomically. Cascading deletion is transactional. Row locks, revisions, operation keys,
a partial active-task index and composite owner foreign keys coordinate writes.
Multi-read detail/media uses repeatable-read. External work occurs outside transactions;
media publication uses a short rechecked transaction. Connections open per operation
without a pool; JSONB media updates lock/rewrite the resource row.

### Accounts and browser sessions

Accounts use UUIDs, unique trimmed/lowercase email, Argon2 hashes and token versions.
Registration creates exactly one profile atomically. Migrations use advisory locks
and immutable checksums. No avatar upload exists.

Browser sessions use a one-hour HttpOnly, SameSite=Lax JWT cookie, Secure under HTTPS
with a loopback-only insecure exception. Register/login require exact Origin;
cookie writes also require session CSRF. Bearer clients share existence/revocation
checks; conflicting credentials fail. Logout increments token version across clients.
Missing/expired/revoked sessions return 401.

Private editor/action recovery stays in tab session storage, owner/generation scoped.
Expiry hides private content and quarantines it while public examples and a separate
guest brief remain usable. Same-account login restores private input unless guest
edits take precedence; the prior private brief then remains explicitly restorable.
Different-account login transfers guest input only. Logout/revocation clears private
recovery, fences late replies and blocks implicit session adoption until explicit login.
Cross-tab notices contain IDs/generations only. Login/recovery never saves or generates.

### Account deletion

Deletion requires current password and `confirmed:true`, with normal Origin/CSRF.
The `admin@admin.com` test account is protected. The user lock shared with task
admission rejects deletion while tasks are pending/running/stopping (409).
Success atomically cascades owner content and invalidates tokens, returning 204
without expiring a potentially newer session cookie. Browser invalidation is
owner-fenced. An ambiguous response checks session status without retrying deletion.
Existing logs/backups are outside application deletion.

### Profile defaults and new-brief initialization

Profiles retain display name, currency, interests, nullable pace and soft transport
priorities. Compatibility `notes` is preserved but neither shown nor inherited.
New briefs read defaults once. Explicit planning entry can refresh untouched automatic
defaults, never edited/restored/draft/replan input. Clear remains blank until a later
explicit entry. Profile updates do not mutate open editors or overlay submitted tasks.

### Durable planning tasks and previews

Generate freezes request and optional `editor_version=1` snapshot. Owner-scoped keys
bind canonical request fingerprints, including literal preferences and Decimal values.
Same-key/same-input returns the original task; changed reuse or another active task
returns 409. Dates/currency validate before providers and retain the accepted reference date.

Pending deadlines, worker leases, execution UUIDs and fencing guard execution.
Heartbeats, progress and publication require current unexpired authority under row lock.
Public reads/reconciliation fail abandoned work as `planning_interrupted`, release the
slot and never restart providers. A supervisor owns workers independently of HTTP.
Shutdown awaits owned cleanup; database work does not block the async loop.

Pending Stop cancels before claim. Running Stop marks stopping without renewing lease;
the owner cancels and cleans up, then acknowledges only with valid authority.
Completion and Stop serialize on one row. Late Stop preserves committed completion;
late publication fails. Already dispatched external work may finish or be billed.

Completion atomically stores a trusted `product_detail_1` preview and task reference.
Previews survive browser recreation outside the saved library. Observers use bounded
polling/focus refresh or SSE; reconnect/login reads receipts without replaying generation.
Ambiguous submission performs operation lookup with the original retained key.

Plan separates brief, progress and preview. Editing/Clear never changes submitted tasks.
Notifications/header entries select exact task/preview identity without overwriting the
brief; failures retain an attention entry until superseded. Other pending previews remain
paged and recoverable. Revise submitted brief restores known source input only after any
replacement confirmation; Generate again requires explicit action with a fresh identity.
All late responses are fenced by owner, session, navigation and editor context.

Product adds English-writing policy to effective primary/Repair prompts within existing
input limits, without a translation call. Independent factories retain their defaults.

### Explicit preview decisions and normalized saved trips

Save locks the preview and atomically writes header, actual days/children and receipt.
Repeated/concurrent Save returns one identity. Discard requires confirmation. First
committed decision wins; opposing decisions return 409. Minimal receipts survive content
removal and saved-result deletion; late Save cannot resurrect deleted content.

Saved detail reconstructs normalized rows in repeatable-read without a duplicate
itinerary blob. Missing/other-owner resources return 404. Title-only PATCH requires
current positive revision and a trimmed nonblank title ≤120 characters. Confirmed
DELETE also checks revision and cascades children; stale writes return 409.

Preserve actual list order, empty days, ISO offsets/fraction spelling, unknown/zero
values, source attribution and completion state. Header span creates no missing days.
Nearby resolves only exact compatible anchor ID/date; supplied unresolved references
remain. Transfer endpoints must differ and share a day. Saved historical reads do not
apply current generation dates or call providers. Ambiguous decisions trigger GET recovery.

### Activity roles and timeline presentation

Kinds/time use survive projection, persistence, copies and export. Main visits have
prominent cards; supporting activities have compact cards; transport uses a connector;
free windows and optional Nearby keep separate semantics. Missing legacy roles/themes
stay unknown/absent; titles, media and links cannot establish them. Neutral missing
fields remain omitted for legacy import fingerprints. Imported declarations are display
claims with unverified trust; no automatic historical role backfill runs.

### Independent trip copies and kept examples

Explicit Copy/Keep supplies source kind/ID and operation key. Owner-serialized creation
writes an independent normalized trip plus saved receipt, preserving underlying trust,
known request, ordering and source lineage; title gains ` (copy)`. No task, generation,
validation refresh or provider call occurs. Rename/delete never cascades between copies.

Receipt lookup precedes source lookup, allowing recovery after source/result deletion.
Same key/conflicting source fails; deleted results are not recreated. Copy/import keys
are 1–120 nonblank characters without invalid/control/format code points; task keys
retain their stricter ASCII domain. Query lookup preserves punctuation. After ambiguous
responses, status lookup precedes explicit same-key retry. Account-scoped retained
identities and `/copy-recovery` permit recovery without a surviving source page.

### Historical JSON import and export

Import accepts UTF-8 paste/file ≤5 MiB and `X-Import-Key`. Account serialization creates
one unverified preview; equivalent canonical content recovers the receipt, conflict
returns 409. Object order/JSON whitespace/money scale are insignificant; array order,
IDs and ISO spelling are significant. Parsing/DB work runs outside the async event loop.

Supported envelopes are bare itinerary, r7 `itinerary` wrapper and `dayloom_export_1`,
with `itinerary_1/2/3`. Only explicit request aliases (`request`, `input`, `_prototype.input`)
are read; research drafts/arbitrary nesting are not searched. Partial request `known_fields`
retains explicit facts/nulls; missing basics are never inferred from itinerary or profiles.

Validation retains 1–400 unique actual dates, empty days and order; missing IDs use
source positions. ISO timestamps preserve up to nine fractional digits and original
awareness. Integer-nanosecond checks require positive activity/journey durations,
consistent awareness and valid day membership. Connections can retain zero/negative
available gaps as source conflicts. Transfers need valid distinct same-day endpoints;
Nearby can retain unresolved supplied anchors. Measurements/costs must be finite,
storable and paired where required; `source_claims` is a string array.

Reject NUL, unpaired surrogates, ownership/operation authority and private media bindings.
Exact activity costs respect PostgreSQL numeric limits (131072 integer/16383 fractional
digits) without rounded comparisons or fixed-point expansion; ordinary scale is retained.
Known original-request budgets remain exact JSON strings. Invalid import creates no preview.

Imported provenance is always `imported` / `unverified_import`. Claimed identity,
feasibility and completion remain unverified. Export offers versioned JSON, text and
copyable summary with dialog fallback, omitting private authority/diagnostics. Exported
`origin` is `source_snapshot_only`; reimport never restores generated trust. File reads
and recovery are editor/session fenced. No import/export action calls providers.

### Brief editor

`BriefPage` owns destination, ISO dates, travelers, budget/currency and visible preference
controls. Required/avoided experiences and selected interest/pace/transport sentences
compose `additional_preferences`. Transport selection is soft, not an allowed-mode set.
Only untouched inserted spans are control-owned: external edits shift offsets, internal
edits detach controls, ambiguous replacements relinquish ownership. Manual identical
sentences stay unowned. Restoration validates exact UTF-16 bindings without searching.
Polish Apply/Undo respects that ownership. Incomplete input remains recoverable.

### Replanning itineraries

Plan again opens a new brief from known original basic request fields only, respecting
`known_fields` and nulls. All personalized preferences start empty. It clears prior
draft/submission identity without changing source content or applying profile defaults.
No generation occurs until explicit Generate, which applies current date validation.
Completion creates a new preview and explicit Save a new trip.

### Incomplete drafts and the collection boundary

Drafts store owner/title, bounded `editor_version=1` snapshot, revision and timestamps.
Create/update/rename/copy/confirmed delete are owner-scoped; conflicts retain local work
and offer reload or Save as new. Invalid/blank generation fields remain editable, but
unsupported controls/Unicode fail. Bad/repeated/overlapping span bindings detach controls
without changing wording. Draft actions neither generate nor consult profiles.

`GET /api/library` unions saved/draft cards with literal case-insensitive title/destination
search, creation-time/name ordering and stable UUID/kind ties. Count/page share a snapshot;
limit 1–50 (default 24), offset ≤10000, search ≤100 characters. Browser pages contain four
cards. Draft detail is read-only until explicit Continue planning. Previews stay outside
the library. Mutation expiry hides private cards; login never replays writes.

### Public examples and reusable detail

Two bundled examples, `sydney-example` and `london-example`, each retain three historical
days, six visits, three transfers, weather and three optional Nearby references from
accepted V3 sources. Editorial labels do not alter request/visit facts. Local credited
photographs and server-only source digests accompany them. Public views require no
account, database or provider keys and make no media provider requests. The
[asset credits](../frontend/public/dayloom/examples/README.md) own provenance/licensing.
Guests view examples; copying/export/replanning controls require authentication.

`product_detail_1` preserves source order/time spelling, nullable facts, provenance and
trust. Optional display hints convey no identity authority. Trusted generated/curated
transfers retain PASS/CONFIRMED/UNKNOWN timing with plain-language explanations;
imports cannot gain trust through claimed statuses. Weather shows a labelled midpoint
estimate only when low/high exist. Nearby resolves exact unique anchors and compatible
dates, keeping mismatched/ambiguous references separate. Mobile references collapse
inside activity cards at ≤800px; locate expands/focuses without hover selection.

### Verified place media and curated atmosphere

Only final Google-sourced `result.v3.final_places` and strict acquired Nearby identity/
anchor/date ledgers authorize place photos. Private `media_bindings` map activity/ordered
Nearby slots to stable IDs; Save/Copy retains authority, imports cannot supply it.
Public detail, exports and research output omit bindings.

Owner media reads authorize before provider work. Batches admit 12 ordered slots,
three parallel resolutions, 200–1280px and 30 seconds; itinerary-wide paging has no
slot cap. A Google slot permits one photo Details plus one URI request within an
eight-second complete deadline, eight-second HTTP timeout and 256 KiB bodies. Redirects,
arbitrary URLs and unknown slots fail safely. Successful slots survive later batch failure.

#### Place photo fallback

Only successful Google Details with no photos permits Unsplash fallback: structured
place + destination, then destination alone only after a valid empty first result,
then illustration. Identical queries are not repeated. Adopt only each first result.
Authentication/quota/timeouts/malformed Google results do not mean photo absence;
unsafe metadata/tracking failure stops fallback. All stages share original deadlines.
Fallback is labelled atmosphere and confers no verified place or fulfillment claim.

#### Persistent itinerary image URLs

`media_cache` JSONB on previews/trips stores validated URL, credits, provider/kind/theme,
acquisition time and random revision, excluding raw responses, credentials, resource
names and image bytes. Binding/search/provider/dimensions form the identity. Each resource
holds at most 1000 entries/~5 MiB. URLs have no age expiry or scheduled provider refresh.

Save transfers cache metadata; independent copies start empty. Decisions, deletion and
binding/snapshot changes invalidate it; rename preserves it. Versioned single-slot refresh
replaces only the displayed revision; stale errors return current metadata without new
acquisition. Advisory locks coordinate workers. Provider I/O is outside transactions;
short publication rechecks prevent resurrection. Failed acquisition stores coordination
revision only and can be retried later.

#### Browser tab photo session

Successful URLs/credits use bounded `sessionStorage`: one-hour expiry from metadata
response, 1000 entries/~5 MiB shared with covers/atmosphere. Reads do not renew it;
unavailable/error states are uncached. Keys isolate account/login generation, resource,
snapshot, provider/kind/theme/dimensions and slot. A snapshot hash grants no authority;
private detail authentication precedes display. Bundled examples use local assets.

Cache hits bypass metadata calls; database hits make no provider call. Concurrent consumers
share requests, abandoned work cancels, and late writes are fenced. Logout/expiry/account
switch clears private entries; decisions/deletion invalidate resources. Media 401 clears
owner entries, 403/404 the resource. Corrupt/denied/full storage falls back normally.
Image failure evicts one slot and permits one automatic reacquisition per display cycle,
then illustration/explicit Retry; supporting failure removes only its thumbnail.
Image bytes use provider hosts/browser HTTP cache. Restored tabs still check expiry;
no durable browser store or cross-tab photo-sharing mechanism is used.

#### Supporting atmosphere photos

Only scheduled `generic_activity` slots receive supporting imagery. Search uses a
server-owned destination (≤120 characters) plus a controlled suffix:

| Theme | Suffix |
| --- | --- |
| `meal` | `relaxed meal` |
| `rest` | `peaceful rest` |
| `explore` | `neighborhood exploration` |
| `walk` | `scenic walk` |
| `general` | `travel moments` |

No title, private notes/preferences or client query override is sent. Unsplash searches
page 1, one relevant landscape result with high content filtering. Validate first-result
URL/credits and exact download-tracking path; adoption records one tracking request.
Normal cached display records none. There is no second-result picker or model call.
Same-theme work may share acquisition while each slot retains refresh identity.
Missing destination/key or unsafe/empty/failed results leaves a usable compact card.

#### Photo presentation

Main photos use 4:3 thumbnails (full-width 16:9 at ≤560px); Nearby stays square.
Supporting thumbnails open Details. Credits/source links remain in Details; covers
also expose accessible hover/focus/touch credits. Missing photos use illustrations
without blocking preview/Save. Google author attribution confined to Details is a
known policy limitation; it is not asserted to satisfy attribution wherever displayed.
See [Google photo policy](https://developers.google.com/maps/documentation/places/web-service/place-photos).

#### Destination covers

Owned cover endpoints derive destination from authorized detail and persist URLs in
the owner row. Public draft destination covers remain browser-cached. Search is only
the normalized destination, ≤120 code points, first result, one eight-second search/
adoption chain. Missing/failed results use illustration, never another city's fixed
photo. Destination changes fence delayed results. Different queries may yield the
same first image. Fixed login/catalog imagery remains separate. Unsplash hotlink/
referral parameters and credits survive resizing; no image archive or proxy is added.

## Product projection and optional introductions

Projection uses only final identity/date-matched weather, transfers, Nearby and
completion. Confirmed route conflicts stay visible; provider metrics and reserves
remain distinct. An optional primary-POI introduction batch runs after success within
the remaining deadline using normalized summaries or labelled model knowledge.
Failure omits introductions without losing the itinerary; no research output changes.

## Streams, progress and cancellation

Product SSE observes persisted task revisions and returns the same task/preview IDs
and public detail as canonical reads. Disconnect/logout/navigation detaches observation;
only Stop cancels durable work. Reconnection never resubmits generation.

The internal request-owned stream helper retains started/stage/detail/result/error/
cancelled events, run ID, sequence, elapsed time and version. It bounds buffering,
reports drops and sends heartbeat comments after 15 seconds. Its own disconnect cancels
and awaits its producer, unlike durable Product observation. Terminal errors cannot
change sent HTTP status. The shared parser handles chunked UTF-8/comments/premature EOF
without automatic retry. Observed stages indicate position, not elapsed-time percentage
or proof of Repair success.

## Configuration, evidence and verification

[Runtime configuration](../config/README.md) owns active development/acceptance values;
historical allowances are not defaults. Missing usage/billing stays unavailable.
Ignored diagnostic artifacts are local aids, not fresh-clone dependencies.
[Development](guides/development.md) owns checks and maintenance;
[records](records/README.md) owns dated evidence.
