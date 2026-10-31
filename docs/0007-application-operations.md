# Application interfaces and engineering operation

Current application boundary, consolidated 2026-11-01.
Product implements the account-owned brief/draft → task → recoverable preview →
explicit Save/Discard lifecycle, with a mixed library, historical import/export,
independent copies, known-input replanning and credited media. Product HTTP/stream
entrypoints observe that same durable task. Actual verification and consequential
corrections are recorded in [lifecycle acceptance](records/frontend/dayloom-product-lifecycle-acceptance.md).

## Product and independent planner surfaces

Product presents V3 through a version-agnostic API and an allowlisted user contract.
Command-line and programmatic entry points select V0-V3 independently and retain diagnostics
needed for engineering. The Developer web page and its dedicated APIs are removed;
`/dev` and its child routes display the existing not-found page.
React owns form state, progress and rendering. FastAPI validates input, invokes application
services and serializes outcomes. An application-owned coordinator runs Product work;
observers read persisted snapshots.
Stale responses must not overwrite an edited request.

Inputs share destination text, currency selection, ISO dates and optional preferences.
Server date policy owns admissibility; browser display must not change dates through
timezone conversion or locale-dependent parsing. An input change invalidates the appropriate
previous result. Product completion reasons are policy observations, not global feasibility.

## Local configuration console

`/config` is a standalone React route outside traveler session/task providers. The
normal Product launcher enables its management interface only for an HTTP loopback
origin and loopback listener. The API-only application leaves management disabled.
No configuration database or account role is introduced. Operational steps belong
to the [local configuration guide](guides/development.md#local-configuration-console).

| Editable setting | Existing consumer |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_KEY` | Current Foundry model calls and web search |
| `OPENAI_API_KEY` | TripWorld query embeddings |
| `GOOGLE_MAPS_API_KEY` | Planning and place photographs |
| `PRODUCT_UNSPLASH_ACCESS_KEY` | Optional atmosphere photographs; existing `UNSPLASH_API_KEY` remains an alias |

The console validates existing Foundry v1 endpoint/deployment syntax and writes
only these fields. It adds neither model selection nor provider adaptation.
Database credentials, JWT signing secrets, planning policies and retrieval data
remain outside its write surface. Process environment values take precedence over
dotenv, including alias selection and interpolation; YAML supplies deployment
defaults. A read captures dotenv once; its opaque revision covers that text and
the resolved editable values, including YAML deployment defaults.

Management requires an in-memory, randomly generated process token. Successful
unlock creates a separate 30-minute HttpOnly, SameSite=Strict cookie scoped to
`/api/config`, with a session-bound CSRF token for writes. Access checks require a
loopback peer, the exact configured Host, and exact Origin on writes; forwarded
client headers are disabled by the Product launcher. Failed unlock attempts are
bounded, as are active management sessions and request-body size. API responses
use `Cache-Control: no-store`; validation/errors exclude submitted values.

Secret fields return presence only. An omitted field is retained; an explicit
empty change clears it. Writes preserve unrelated dotenv bindings, use a cross-process
file lock and atomic replacement, and reject stale revisions with HTTP 409. The
running Product pins editable provider settings at startup, so saves require a
restart and cannot reconfigure in-flight work. Setup mode leaves configuration and
static delivery available while business APIs return HTTP 503; a successful restart
is required to enable business operations. Check local readiness returns local
resource readiness without external provider requests or a claim of valid credentials.

Check API on each provider card and Check all APIs explicitly invoke
`POST /api/config/check` with a saved revision and a fixed service identifier.
They use the same management protections as saves. The server captures the saved
effective values, rejects an old revision before sending, and marks results stale
if configuration changes during the check. The browser clears results on edits,
save, reload and lock, and does not display stale results as successful. Results
remain in page memory only. A new saved key can be checked before restart without
changing the running planner's pinned settings.

| Service | Capability checked | Maximum HTTP attempts |
| --- | --- | --- |
| Azure Foundry | One tiny strict structured Responses result and one completed web search from the saved deployment | 2 |
| OpenAI | `text-embedding-3-small` with 1,536 finite dimensions | 1 |
| Google Maps | One Places text search, a 1-by-1 walking route matrix, photo details and photo media URI | 4 |
| Unsplash (optional) | Metadata for one existing catalog photograph | 1 |

Each invocation allows at most eight outbound HTTP attempts and a 60-second shared
deadline. Individual requests allow 15 seconds, or 30 seconds for web search,
within the remaining deadline. There are no automatic retries or redirects; only
one check runs per local instance. Response bodies are limited to 128 KiB. Foundry
uses the same approved HTTPS Azure v1 endpoint admission as the editor; all other
hosts are fixed. Google photo resource identifiers are validated before use.
Credentials stay in request headers and never enter URLs or returned diagnostics.

Checks use fixed public sample queries and coordinates, not traveler inputs.
They do not run planning, download images or alter planning budgets. They may
incur provider charges; HTTP/time limits are not a monetary spending cap. Startup,
page loading and local readiness never trigger these checks. Missing settings,
authentication, permission/API enablement, billing, quota, rate limit, network,
timeout and unverified responses have separate safe outcomes. A timeout does not
prove an invalid key; missing sample photos are inconclusive. Provider error text,
payloads and credentials are excluded from results. A passing sample establishes
only that capability at the check time, not all permissions or planning readiness.

Implementation: [configuration](../backend/app/product/configuration.py),
[management interface](../backend/app/product/configuration_api.py),
[local probes](../backend/app/product/local_readiness.py),
[API checks](../backend/app/product/api_checks.py).

## Product diagnostics

Product retains server-side diagnostics alongside its public progress stream. HTTP
requests receive a server-generated `X-Request-ID`; background execution additionally
records `task_id`, `execution_id`, `run_id`, account UUID and fence. A task execution
uses its execution UUID as the run UUID. These identifiers associate submission,
planner work and the eventual persistence decision without relying on email addresses.

The local operation log records request method, route template, HTTP status, duration,
bounded result/path identifiers and public error codes, including UUID resources in
empty deletion responses. It covers accounts/profiles, drafts,
planning tasks, previews, Save/Discard, trips, copies, imports, examples, input assistance
and media. Service logs and sanitized exception chains retain exception types and code
locations; request bodies, response bodies, credentials and URL query strings are excluded.
Media availability counts and explicit missing-credential, missing-photo, invalid-metadata
and provider-failure reasons distinguish display fallback from HTTP success. Task failure
logs separately identify committed outcomes and failed or rejected terminal writes.

Planning diagnostics reuse native planner events and payload controls while retaining
the progress observer. Each run has policy/input metadata, ordered events, optional
payloads, a numeric budget summary and an independent final summary. Available records
cover requirements, candidate acquisition and RAG, identity/semantic decisions, generation,
validation, Repair proposals/admission/retention and finalization. Initial/final itineraries
and validation reports are separated from the large final event under existing size limits.
`run.json` has a separate metadata allowance below 64 KiB, preserving run/task identity,
timestamps and the configuration digest when large outcome or configuration fields receive
explicit truncation markers. Repair input sizing is emitted independently before its
decision, including overflow without a model call; numeric total, candidate, context,
evidence and schema counts survive in both the final and budget summaries.
The separate 64 KiB final summary preserves the stopping reason, Repair status, selected
round, pace completion, compact validation findings and Product completion even when
detailed events are truncated. V3 emits compact completion before truncating its full
outcome. Per-stage timings retain their inclusive, non-additive scope. Truncation and
collection/write failures remain explicit. A completed
planning service invocation is distinct from the coordinator's committed `task_completed`
event; stale results have `task_result_not_committed` instead.

Numeric observation uses the existing model callbacks and HTTP adapters, including
request-local hook cleanup. Usage includes stage/call identity, timings and reported
tokens where available; missing or uninstrumented usage is not inferred as zero.
Cancellation retains consumed tool counts and limits; unavailable budget sources are
explicitly incomplete. Active spending reservations are retained on success, failure and
cancellation and labelled conservative upper bounds rather than invoices.
Diagnostic collection neither authorizes retries nor changes planning budgets or policies.

The browser reports uncaught errors, unhandled rejections, React render errors and
failed same-origin API requests. It sends error types, bounded code locations, route
structure and the failed response's request ID, without error messages, form text or
query parameters. Local exports and clipboard outcomes use explicit action names;
requesting a download does not prove the file was saved. All browser reports are
untrusted client observations, not authenticated account audit evidence.
`POST /api/diagnostics/client-errors` requires the configured exact Origin, limits the
body to 4 KiB, validates an allowlist and accepts at most 20 reports per direct peer
per minute per process. The browser deduplicates and limits itself to 10 reports per
minute. Abort-driven fetch cancellation is not a reported network failure; diagnostic
requests cannot recursively report themselves.

Operation files rotate under an inter-process write lock. Finished run retention is
applied when a new run starts or by the local maintenance command; active runs are
protected, with abandoned markers eligible after 24 hours. Cleanup only traverses the
owned Product run namespace and excludes symlink directories and unrelated files.
Storage failures warn without replacing the business result or taking ownership of
cancellation. Diagnostics stay outside Product DTOs and Git. Configuration, retention
limits and lookup commands are in the [development guide](guides/development.md#product-diagnostics).
Independent V0-V3 entrypoints keep their existing tracing and planning behavior.

## Input assistance

GeoDB suggestions are requested through a bounded backend adapter. Manual entry remains
available when suggestions fail or do not cover a place. GeoDB selection does not create
planner identity evidence. Preference polishing is an explicit, bounded single-call action
with preview, Apply/Dismiss and Undo. It neither auto-submits nor bypasses the unchanged
planning input gate. A schema-valid suggestion is not proof of semantic equivalence or
better gate acceptance. Old two-call polishing designs are historical.
The original and suggested text retain literal whitespace so client revision matching
and exact editor span ownership remain valid. Whitespace-only input is rejected.

Source task and acceptance: [planning input UX #25](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/25).

## HTTP contract map

| Endpoint | Input and result | Source of truth |
| --- | --- | --- |
| `/api/config`, `/session`, `/readiness` | Local management unlock/lock, redacted reads, revision-checked provider writes and read-only resource checks | [Local configuration](#local-configuration-console) |
| `POST /api/config/check` | Saved revision and fixed service identifier; bounded explicit API capability results, attempt count and stale flag | [Local configuration](#local-configuration-console) |
| `POST /api/auth/register` | Normalized email, password and display name; atomic account/profile and browser session | [Account boundary](../backend/app/product/auth.py) |
| `POST /api/auth/login` | Email/password; generic credential failure or browser session | [Account boundary](../backend/app/product/auth.py) |
| `GET /api/auth/current` | Validated account, initials and session-bound CSRF token | [Account boundary](../backend/app/product/auth.py) |
| `POST /api/auth/logout` | Revoke every account token and clear the browser cookie | [Account boundary](../backend/app/product/auth.py) |
| `GET /api/profile`, `PUT /api/profile` | Read or replace the authenticated owner's display name and travel defaults | [Profile boundary](../backend/app/product/profiles.py) |
| `/api/drafts` and item/copy operations | Versioned incomplete editor snapshots and revision-checked owner mutations | [Draft collection](#incomplete-drafts-and-the-collection-boundary) |
| `GET /api/examples`, `/{example_id}`, `/{example_id}/media` | Two public historical itineraries and server-authorized photo metadata | [Examples](#public-examples-and-reusable-detail) |
| `GET /api/library` | Bounded server-side card search, ordering and pages | [Collection boundary](#incomplete-drafts-and-the-collection-boundary) |
| `GET`, `PATCH`, `DELETE /api/trips/{id}` | Immutable owner detail, revision-checked title-only update and confirmed cascade deletion | [Saved trips](#explicit-preview-decisions-and-normalized-saved-trips) |
| `GET /api/trips/{id}/weather`, `/nearby`, `/transfers` | Owner-only ordered read views over the saved snapshot | [Saved trips](#explicit-preview-decisions-and-normalized-saved-trips) |
| `POST /api/copies`, `GET /api/copies?source_kind=...&operation_key=...` | Explicit owner copy/Keep and durable operation receipt lookup | [Independent copies](#independent-trip-copies-and-kept-examples) |
| `POST /api/planning` | Shared `PlanningRequest` plus `Idempotency-Key`; 202 durable task snapshot | [Product router](../backend/app/api/product/planning.py), [HTTP schemas](../backend/app/api/schemas/planning.py) |
| `POST /api/planning/stream` | Same submission identity; observe durable task revisions and final public detail with task/preview IDs | [Product router](../backend/app/api/product/planning.py), [stream delivery](../backend/app/api/streaming.py) |
| `POST /api/planning/tasks` | `{operation_key, request, editor_snapshot?}`; 202 immutable task snapshot or 409 active/key conflict | [Task lifecycle](#durable-planning-tasks-and-previews) |
| `GET /api/planning/tasks`, `/recent`, `/active`, `/{id}` | Owner-only bounded recent/active reads, operation-key lookup and canonical snapshots | [Task API](../backend/app/product/tasks.py) |
| `POST /api/planning/tasks/{id}/stop` | Owner-only idempotent Stop; preserves completed tasks/previews, otherwise cancels pending work or requests running transport cleanup | [Task lifecycle](#durable-planning-tasks-and-previews) |
| `GET /api/previews`, `/{id}` | Paged pending summaries and owner-only full public detail/decision receipt | [Task lifecycle](#durable-planning-tasks-and-previews) |
| `POST /api/previews/{id}/save`, `/discard` | Explicit owner-scoped decision with a durable saved/discarded/deleted-result receipt | [Preview decisions](#explicit-preview-decisions-and-normalized-saved-trips) |
| `POST /api/imports`, `GET /api/imports?operation_key=…` | Bounded historical import and status-first owner operation recovery | [Import/export](#historical-json-import-and-export) |
| `GET /api/previews/{id}/media`, `/api/trips/{id}/media` | Owner-authorized display metadata for private verified bindings | [Media](#verified-place-media-and-curated-atmosphere) |
| `GET /api/media/curated/{key}` | Fixed public destination/atmosphere catalog metadata | [Media](#verified-place-media-and-curated-atmosphere) |
| `GET /api/planning/date-window` | `allowedStart`, `allowedEnd`, `maxTripDays` from server date policy | [Product router](../backend/app/api/product/planning.py), [date policy](../backend/app/policies/trip_dates.py) |
| `GET /api/input-assistance/destinations?q=...` | Bounded normalized GeoDB suggestions for UI selection; no planner evidence | [Assistance router](../backend/app/api/input_assistance.py), [schemas](../backend/app/schemas/input_assistance.py) |
| `POST /api/input-assistance/preferences/polish` | `original_text`, `context`, `client_revision`; `suggested`, `unchanged` or `needs_input` | [Assistance router](../backend/app/api/input_assistance.py), [schemas](../backend/app/schemas/input_assistance.py) |
| `POST /api/diagnostics/client-errors` | Exact-origin, size/rate-limited untrusted browser error or export-action report | [Product diagnostics](#product-diagnostics) |
| `GET /health` | Process health response | [Application](../backend/app/main.py) |

The shared request uses `input_version=planning_request_2`, destination, ISO start/end
dates, traveler count, mandatory total budget/currency and optional preferences.
[PlanningRequest](../backend/app/schemas/request.py) owns field validation; do not copy
the complete schema into UI or operational prose. Product does not accept engine selection
or a research reference-date override. Programmatic planners' optional reference date supports explicit
engineering fixtures and does not authorize historical live evidence acquisition.

Product task outcomes distinguish `completed`, `needs_clarification`, `safety_blocked`,
`provider_blocked`, `failed` and `cancelled`. Typed actions retain the immutable submitted
input. Clarification may show the owner's sourced quote; safety/provider block messages
exclude sensitive source text and raw provider diagnostics.
Requirement failures retain allowlisted codes, canonical requirement references and
validated original quotations where available. Evidence, candidate and capacity
shortfalls produce `failed` / `requirements_unmet` with specific reasons, rather than
asking the traveler to clarify already clear wording. Unsupported hard capabilities
remain explicit; the submitted requirement is never silently weakened.
A completed task means that a preview is available. It retains separate policy
completion and uncertainty; persistence does not imply global feasibility.
Optional `completion.required_experiences` preserves each supported
[required category visit](0002-requirements-evidence.md#required-category-visits), its
original quote, target, scheduled count and satisfied/unmet/unverified explanation.
Optional `planned_visits` carries only supported final activity/date/place associations.
Preview, Save, reopening and export retain this projection. Matching is a semantic
judgment grounded in supplied place information, not an operating-fact guarantee.
Historical records without the field or without a captured failure reason are not
backfilled with inferred diagnoses. The detail and text summary use each normalized
experience label, separating Trip highlights, Needs confirmation and Still to arrange.
Satisfied experiences appear as highlights; unverified experiences ask the traveler to
confirm their exact place or route, while unmet experiences remain to arrange. A generic
supporting activity can already be scheduled while its corresponding experience remains
unverified; a matching title does not change fulfillment. Text summaries use the same
distinction without rewriting native statuses or counts. Raw matching counts, thresholds,
shared source sentences and evidence-state prose are not displayed.
Optional `completion.attention_items` preserves named-place and dated hard-request gaps
as traveler-facing titles/descriptions, with known associations where available. Existing
legacy named-gap reason codes receive a conservative explanation without inventing a
place name/date. Unverified imports do not acquire fulfilled highlights or trusted navigation.
The JSON artifact retains the original supported diagnostic projection as source content.
Place links use only activity/date/name combinations actually present in the detail;
replanning remains the explicit existing action and restores only basic trip information.
For new Rich results, optional `completion.pace_review` preserves the
[final V3 completion](0005-validation-repair%28v3%29.md#final-rich-completion) status and
each applicable day's `date`, `count`, `target_count` and `state`. It carries no internal
scores, finding IDs or debug flags. The same projection survives task result delivery,
preview, Save and reopening. A partial preview remains a valid returned itinerary and
does not acquire a successful-Repair badge. The detail page explains a genuinely lighter
Rich schedule in plain travel language; generic unavailable/not-attempted checking
warnings are omitted, while local route, opening and price uncertainty remains visible.
Sourced exceptions retain a
separate indication. Historical records without this optional field keep their original
completion content, without backfilling or relabelling.

Rich chosen in the form, inherited from new-brief account defaults, restored in a draft or
selected again after replanning uses the same active V3 rule. Preference text and span
ownership remain unchanged; the option does not inject a hard exact-three requirement.
Invalid submission/date/currency fields fail with 422
before external work. Programmatic planners retain full results and exception behavior.

The [frontend Product API](../frontend/src/features/planning/api.ts) binds these wire contracts;
the [shared stream parser](../frontend/src/shared/api/planningStream.ts) handles delivery.
Changing a schema requires the corresponding backend and client seam checks.

## Information and security boundaries

Provider/model content is untrusted data and rendered as text. Product projection excludes
credentials, internal prompts, raw payloads and research-only internals. Missing costs,
weather or route facts remain honestly represented. Secrets belong in local environment
configuration, not committed documents, logs or client bundles. Provider URLs and requests
are constrained by their adapters; user prose is not arbitrary outbound-fetch authority.

PostgreSQL/pgvector supports retrieval; Product accounts, drafts, tasks, previews
and normalized saved snapshots use the separate `app` schema in the same database.
The public Product migrator maintains its own checksums and leaves TripWorld unchanged.
Per-process development limits are not account-wide billing enforcement or distributed
abuse controls; this design does not establish a public deployment guarantee.

<a id="accepted-product-persistence-design"></a>

## Product experience and persistence design

The implemented lifecycle uses the Dayloom r7 visual and interaction foundation,
with Product presentation refinements and initials replacing the deferred avatar upload.
The unified specification
[#198](https://github.com/rplalala/Dayloom/issues/198) owns originating requirements and
confirmed acceptance seams; its native children own task state. #119 retains the
historical design/mapping role. The sections below define current behavior.

### Implemented account and browser session boundary

`app.users` stores UUID identity, a unique trimmed/lowercase email, an Argon2 password
hash and `token_version`. Exactly one initials-only `app.user_profiles` row is created
in the registration transaction. A failed profile insert rolls back the account.
No image field or avatar upload endpoint is present. `app.schema_migrations` records
the SHA-256 of each applied Product migration under an advisory transaction lock;
matching reruns skip and changed applied migrations fail atomically. TripWorld
migrations and tables are not altered by the Product entrypoint.

Browser access uses a one-hour signed JWT in `dayloom_session`, with HttpOnly,
SameSite=Lax and Secure under HTTPS. An explicit insecure-cookie exception is limited
to loopback development origins. Register/login require the configured exact origin.
Cookie-authenticated writes also require the session-bound `X-CSRF-Token` returned by
login/current; bearer clients use the same user-existence and revocation checks.
Conflicting cookie/bearer credentials are rejected. Missing, expired, malformed and
revoked sessions return 401; account validation never echoes submitted passwords.
Logout increments `token_version`, invalidating previously issued tokens across clients.
Product planning POST endpoints require the same authentication; date-window and
input-assistance reads remain guest-accessible.

The Product React shell exposes home, a shared brief editor, login/register, guest
example cards, an authenticated saved-trip/draft library with a genuine empty state,
and an initials-only account page.

Product copy explains traveler actions and travel information; development histories,
internal operation identifiers and research controls stay outside these pages. About
describes the travel experience, and the home confirmation feature uses a checklist glyph.
The login tab displays the public test-account hint without filling or submitting the
form; registration remains separate. This test
hint is distinct from the private provider/deployment credentials excluded above.

An empty owned library shows a responsive journey illustration and one primary planning
action, without redundant collection counts or search/sort controls. A search with no
matches retains its controls and distinct no-results guidance. The planning action starts
a new brief through the existing initialization policy.

Authentication restores a guest brief and return intent without generating. Editor
recovery and a pending action identity stay in tab-local session storage, never in the
JWT or shared local storage. Expiry hides account/editor content and quarantines it
under its previous account. Successful same-account login restores it without a write;
different-account login, explicit logout and confirmed revocation erase it. Shared
storage contains only account IDs, opaque invalidation/login generations and notices.
Recovery records retain their account's generation, so an invalidation remains effective
while Product is unmounted and after later login notices. Logout fences refresh until
it settles and blocks implicit session adoption until a new explicit login, including
after an ambiguous network response; the failure is shown to the user.
Focus and periodic session checks detect remote revocation; network failure hides
account content while preserving quarantined recovery. Durable generation has a
separate task lifecycle.

### Profile defaults and new-brief initialization

The owner-only profile API and `/account` form maintain display name, supported currency,
deduplicated interests, nullable pace, deduplicated soft transport priorities and literal
additional preference text. Initials derive from the display name; email is read-only.
The profile migration adds database domain and uniqueness checks. Account deletion
cascades to the profile at the database boundary, without exposing an account-deletion UI.

Defaults are read once when a genuinely new brief is opened and appear as editable
currency, choices and preference sentences. Explicit origin and initialization metadata
distinguish unopened session state from edited, restored, draft and replan content,
including an intentionally cleared or restored blank brief. A stale defaults response
cannot overwrite an intervening edit, accepted draft or account change. Explicitly
starting another brief resets that initialization and reads the latest defaults once.
Profile updates never mutate an open editor, and planning services do not read profiles
to overlay confirmed requests. Draft identity and revision share the account-scoped
recovery boundary so expiry can quarantine them alongside their editor content.

### Durable planning tasks and previews

The authenticated explicit Generate action freezes the confirmed `PlanningRequest` and
optional `editor_version=1` restoration snapshot by value. Profile/draft changes cannot
alter task input. Product validates supported currency and current dates before providers,
and retains the accepted calendar reference date across queued execution. Operation keys
are owner-scoped and separate from `request_id`; the complete canonical request fingerprint
includes literal preference text, normalized Decimal amount and omitted/null request ID.
Same-key/same-request reads the original task; changed reuse returns 409. A PostgreSQL
partial unique index enforces one pending/running/stopping task per owner across instances.
A conflicting Generate returns `planning_task_active` with its existing task ID, while
editing and saving another draft remains available.

Acceptance commits a finite pending claim deadline before scheduling. The application
supervisor holds worker/heartbeat references independently of HTTP/browser sessions. A
short atomic claim grants a private execution ID, fencing generation and finite lease;
renewal, progress, terminal outcome and preview publication require current unexpired
authority after row locking. Public progress revisions are separate from private fencing.
Public reads and periodic reconciliation fail expired pending/running/stopping work with
`planning_interrupted`, retain its input and release the slot. They preserve live leases
and completed records, and never restart providers. Database operations run off the async
loop and never hold transactions across provider awaits. Shutdown cleans up owned workers;
abrupt loss is recovered through persisted deadlines.

Stop locks the same task row as completion. Pending Stop commits `cancelled` before a
worker can claim, so no provider is entered. Running Stop commits `stopping` without
renewing its finite lease. The execution owner's heartbeat observes rejected renewal,
cancels its worker and awaits the existing runtime transport cleanup. Only that matching,
unexpired execution/fence may acknowledge `cancelled`; abandoned stopping work still
recovers as `failed/planning_interrupted`. Already committed completion, its preview and
all terminal outcomes remain unchanged by late/repeated Stop. Stale publication is
rejected. External work dispatched before cancellation may still finish or be billed.

Trusted final V3 presentation becomes one `product_detail_1` snapshot in
`app.itinerary_previews`, atomically with the completed task reference. Uncertainty,
canonical source names, final transfers and policy completion survive projection. The
preview is separate from the saved library and survives app/browser recreation. Pending
summaries use bounded `limit`/`offset` pages; pending item reads return the full snapshot.
Save/Discard decisions use the same receipt row, with retained operation identity and
saved-result tombstones. Task/preview foreign keys enforce same owner and source task;
account deletion cascades both. No queue, event log or graph checkpoint is introduced.

Plan uses three lifecycle sections: 01 travel brief, 02 planning progress and
03 itinerary preview. A fresh brief shows the required fields and Generate action,
with optional preferences in a native disclosure; existing optional values open it
initially, and preference validation opens it to expose the error. Collapsing it
does not clear its values. Progress mounts when a task, recovery/error state or an
explicit progress anchor needs it. With no selected task/result, the preview area
shows only available unsaved previews for an account or a compact guest example link.
The global desktop/mobile task entry returns to section 02 while
running or needing attention, or section 03 when ready. It shows the submitted
destination independently of the editable brief. `?task=<id>` selects an owner-only durable task; `?preview=<id>`
selects an unsaved or decided result. Legacy `/planning` and `/planning/:id` bookmarks
redirect to Plan; there is no separate task-management page.

Observation uses one in-flight request per observer, periodic GET polling while active,
and focus/online refresh. Network recovery and login only read existing receipts; neither
replays generation. Completion neither redirects nor changes the current brief. An
outcome notification appears at the upper right below navigation and stays fixed while scrolling. An
unviewed completed preview remains available as **Itinerary ready**, independently of
dismissing its notification. Viewing the result in section 03 or its full detail acknowledges
it per owner, task and revision. An **Unsaved previews** disclosure in section 03 lists
paged pending results other than the currently selected preview and selects them within
Plan. Its badge counts the loaded alternatives; the entry and count are hidden when
there are none. Pagination retains the unfiltered server offset. Save/Discard remain
explicit, and the disclosure refreshes after the current decision. `/previews/:id` retains the full
itinerary view and read-only recovery of decision receipts. Login return targets preserve
the exact UUID task/preview selection and allowlisted Plan section.

The newest task's failure, interruption, clarification or safety/provider block produces
a non-navigating **Planning needs attention** notification, including on My trips. Its
**View details** action and header entry open that exact task in section 02 without
replacing the editable brief. The narrow header label is **Needs attention**. Dismissing
the notification, viewing the reason, editing or refreshing does not clear the entry;
a newer accepted task supersedes it. Older unseen successes cannot replace the current
failure notification, but their previews remain recoverable in section 03. Deliberate
Stop is not announced as failure. Notifications are deduplicated within each tab by
owner, task and revision independently of entry retention; neither observation nor recovery retries work.

An ambiguous submit response triggers only an operation lookup; its immutable intent
and key stay account-scoped through expiry. Explicit logout/revocation clears it. A late
response cannot overwrite another edited brief or submit it with an unresolved earlier
operation identity. The HTTP adapter returns 202; SSE observes revision snapshots, then
emits the same task/preview IDs with its allowlisted public detail. Disconnect detaches
only the observer. Independent V0–V3 entrypoints retain their own execution lifecycle.

Clarification, safety/provider blocks, infrastructure failure, interruption and
cancellation retain immutable submitted input. Section 02 renders public action text
and allowlisted clarification quotes/fields without internal diagnostics. Explicit
**Revise submitted brief** opens the saved editor snapshot, or known original request
fields for older tasks, with no profile overlay. If a different brief is open, the
traveler chooses to retain it, save it as a draft before replacement, or replace it.
Viewing an outcome or stopping a task never changes that brief. Recovery clears the old
submission identity. When the valid editor still matches the submitted request, **Generate again**
creates a fresh task only after an explicit click. A different editor requires the existing
restore/keep/save confirmation first. Stop is terminal cancellation, not checkpoint pause;
network reconnection resumes observation of the existing task, not its execution.
Revision continuations belong to the initiating navigation, operation, session and
editor/draft context; a late Save response may persist B but cannot restore A or change
a newer page. Terminal cards show their safe outcome instead of announcing the retained
last running stage as current progress.

The Product dependency factory adds English writing policy only to primary/Repair
provider system prompts, preserving request/source text and proper names. It admits the
final effective prompt under existing limits and records effective sizing separately.
It adds no translation send or retry. Direct V0–V3 calls keep their default factory;
adapter tests verify policy placement, not universal live-model language compliance.

### Explicit preview decisions and normalized saved trips

`POST /api/previews/{id}/save` accepts an empty body and serializes the owner's preview
row with `FOR UPDATE`. A pending preview becomes one independent saved identity only
when its header, actual days, activities, Nearby references, final transfers and saved
receipt all commit together. A child-write failure rolls back the transaction, keeping
the original pending preview. Save does not generate, refresh providers or read profile
defaults. Repeated and concurrent Save requests return the same identity.

`POST /api/previews/{id}/discard` requires `confirmed=true` and locks that same row.
The first committed decision wins; repeating it is idempotent, while an opposing
decision returns 409 `preview_already_decided` with the safe existing decision. Decided
receipts retain operation identity and the original saved ID, but clear pending content
and redundant original request material. A deleted saved result returns 409 with
`saved_result_deleted`; late Save cannot recreate it. Account deletion cascades owned
domain content.

Migration `005_saved_trips.sql` completes the ten-domain-table model with `trips`,
`trip_weather`, `trip_activities`, `trip_nearby` and `trip_transfers`.
`GET /api/trips/{id}` reconstructs the public detail from normalized rows in one
repeatable-read transaction. No second saved itinerary JSON is retained. The header
holds known original request/completion metadata, server-owned origin/trust and nullable
generation completion time. All saved and preview boundaries return 404 for missing
or other-owner records and use the existing session/CSRF/origin checks.

`PATCH /api/trips/{id}` accepts only `title` and the current positive integer `revision`.
Titles are trimmed, nonblank and at most 120 characters. The locked update increments
revision and updates its metadata timestamp without changing the original request,
provenance, itinerary or children. `DELETE /api/trips/{id}` requires a JSON body with
`revision` and `confirmed=true`; it removes the trip and normalized children and returns
204. Stale mutations return 409 `trip_revision_conflict` with the current revision.
Independent saved identities survive deletion, and the source preview's minimal decision
receipt remains available to reject late Save without recreating the trip.

The weather, Nearby and transfer GET views each return `{trip_id, items}` from the same
normalized detail reader. Weather items contain each actual day's date and nullable
weather, including empty days. Nearby retains supplied anchors/dates and unresolved
references; transfers retain their final directed endpoints and source/uncertainty states.
These views preserve list order and make no provider requests or current-date checks.

Explicit positions retain actual day, activity, Nearby and transfer list order, including
empty days and nonchronological lists; the header span never creates missing days.
Original ISO time strings retain their offsets and fraction spelling without timestamp
round-tripping. Unknown facts/costs remain distinct from zero, free windows remain
distinct from scheduled activities, and incomplete/unassessed policy, UNKNOWN and
CONFIRMED conflict states remain visible. Weather facts, availability, attribution and
source URLs persist, as do Nearby and transfer attribution. Migration
`008_weather_sources.sql` adds nullable weather source fields; older saved rows keep
null where no source was stored. Saving or copying a current snapshot preserves its
source credit without fetching providers or reconstructing missing historical data.

Nearby stores supplied anchor ID/date independently from its nullable resolved composite
foreign key. Only an exact scheduled activity ID with a compatible supplied date resolves;
orphans and free-window references remain unresolved without invented days or name guesses.
Transfer endpoints must be distinct and belong to the same trip/day. Database constraints
also enforce legal domains, nonblank IDs/titles, nonnegative positions/finite measurements
and paired cost fields. Historical detail/save/import does not apply current generation windows.

The preview page offers Save to My trips and a confirmed Discard dialog. An ambiguous
write response triggers a decision GET, never an automatic write replay; failed recovery
offers an explicit status check. Mounted preview, account, session and invalidation guards
prevent late responses from changing another brief or page. Saved results offer a user
controlled detail link. HTTP/SSE completed-task adapters read normalized saved detail when
available and otherwise expose a safe `preview_decision`, including discarded/deleted
receipts, so clearing a pending snapshot does not break completed observation.

### Activity roles and timeline presentation

The final planner's `activity_kind` survives Product projection, preview, normalized
Save/read, application recreation and independent copy. Its values are `main_poi`,
`generic_activity`, `transport`, `free_time` and `unknown`; role is independent of
`time_use`. A scheduled meal, rest or exploration activity remains scheduled and
does not become a free window or add a principal visit. Tools-based principal eligibility
uses the [shared source/assessment boundary](0003-itinerary-transport.md); persistence
does not reinterpret historical roles or time-use declarations.

Principal visits use prominent place cards. Supporting (`generic_activity`) activities
use compact, solid-border white cards with their own timeline dot, start/end times,
title, description and accessible Details action. They remain distinct without a photo,
including on mobile. Directed transfers retain the existing dashed connector, duration,
distance and uncertainty. An explicitly declared transport activity uses that connector
structure with its supplied interval and no activity dot/photo; it does not create a
new transfer or imply new endpoint identities. Nearby remains optional and unscheduled,
with the existing anchor/date rules.

Migration `009_activity_roles.sql` adds role and nullable `atmosphere_theme` columns
without modifying prior migration checksums. Optional themes pass through the existing
strict model DTO/mapper and Product lifecycle; missing supporting themes use the general
fallback without another model call or title classification. The
[supporting atmosphere adapter](#supporting-atmosphere-photos) owns their bounded mapping.
Transport is excluded from fresh activity-photo bindings.

Missing historical roles remain unknown, and missing themes remain absent. Neither
titles, illustrations, photo bindings nor map links establish a role. Neutral unknown/null
fields are omitted from detail JSON to preserve legacy canonical import fingerprints
and same-key receipt recovery. Non-neutral role/theme declarations survive JSON export
and import as display claims; imported details retain `unverified_import` trust and
never gain verified place/media identity or requirement fulfillment from these fields.
No historical role backfill runs automatically. A future targeted backfill requires
a dry-run and exact matching to trustworthy final-role material; intermediate/proposal
traces alone cannot authorize it.

### Independent trip copies and kept examples

Saved details and library cards offer explicit whole-trip Copy; public example details
offer Keep a copy. `POST /api/copies` accepts only `source_kind` (`copied` or `example`),
`source_id` (canonical saved UUID or bundled example slug) and `operation_key`. The
authenticated cookie, exact Origin and CSRF token are required. The operation creates
an independent normalized trip and an already-saved preview receipt in one transaction,
without a planning task or pending preview. It copies the current title with ` (copy)`
and preserves public content, partial/null original requests, ordering and historical
time spelling under the saved-detail contract. Current generation date windows do not
apply. It performs no generation, validation refresh or provider request.

The receipt is unique per owner, source kind and operation key. A server-computed intent
fingerprint binds the canonical source identity, independently of later title/content
changes. Same-owner serialization resolves simultaneous requests to one result. Receipt
lookup precedes source lookup, so the same operation still recovers its original saved ID
after source or result deletion; `saved_result_deleted` prevents resurrection. A conflicting
source under an existing key returns 409. A genuinely new key can copy only a still-existing
owner source. Source locking keeps its header and immutable child lists coherent with
rename/delete, and a child-write failure rolls back both the new trip and receipt.

Immediate lineage is retained as server-owned source kind/ID on the receipt and trip.
Underlying `provenance` and `trust` remain unchanged: a copy of an import stays unverified,
and a copy of a historical example stays a source fixture. Copies of copies remain separate
identities; title changes and deletion never cascade between source and copied trips.

`GET /api/copies?source_kind=...&operation_key=...` recovers the owner's minimal decision
receipt without fetching providers. Query transport preserves accepted key text such as
slashes and URL punctuation; the existing normal single-segment path remains supported.
Copy/import keys contain 1–120 nonblank characters without Unicode control/format or
invalid code points. Task keys retain their existing ASCII alphanumeric/`_.:-` domain;
submission and lookup reject invalid keys before database access. Keys are never rewritten.
After an ambiguous response, the browser offers this
read before an explicit same-key retry; it never automatically repeats a write. Tab-local
action identities are kept separately per owner, source kind and source identity, so
working with another source cannot overwrite an unconfirmed operation. They are quarantined
on expiry, restored only for the same account and cleared
on logout/account invalidation. Mounted component, account, CSRF and invalidation fences
exclude late replies after navigation or account changes. Guest Keep preserves the brief
and returns after login to the allowlisted example review surface; another explicit click
is required. Authenticated My trips retains its real saved/draft collection and empty state.
Its pending-copy link opens `/copy-recovery`, an owner-fenced status-only review of retained
actions. An unavailable saved-source page also offers its retained action's status check.
These entry points require neither source detail nor a new write; deleted results keep
their original receipt and never recreate content. Only an explicit new-copy action
allocates another operation identity.

### Historical JSON import and export

`/import` accepts pasted or uploaded UTF-8 JSON up to 5 MiB. `POST /api/imports`
uses the authenticated cookie, Origin and CSRF token, with an operation key in the
`X-Import-Key` header outside the artifact. `GET /api/imports?operation_key=...` returns
the owner's original preview/decision receipt, including saved/discarded/deleted outcomes;
the existing normal single-segment lookup path remains compatible. Import uses the
shared storable-key admission and query recovery described in the Copy contract above.
Account-row serialization and the existing owner/kind/key unique constraint atomically
create one imported preview. Replays compare a server-computed canonical fingerprint of
validated content and known request metadata; object key order, JSON whitespace and
monetary decimal scale are insignificant, while list order, IDs and ISO spelling remain
significant. Conflicting content returns 409. Save/Discard use the shared decision service;
minimal identity/fingerprint receipts survive content removal. An ambiguous response
requires a status read before explicit same-key retry. A new key starts another import.
Bounded normalization and synchronous PostgreSQL work run outside the API event loop,
so a contended import row does not block task observation, Stop or coordinator scheduling.

Supported envelopes are bare itineraries, the unversioned r7 `itinerary` wrapper, and
`schema_version: dayloom_export_1`. Explicit output versions `itinerary_1`, `itinerary_2`
and `itinerary_3` share the bounded public day/activity field mapping; research `draft`,
traces and arbitrary nested envelopes are not searched. Request aliases are `request`,
`input` and `_prototype.input`, with `people`/`activity_budget`/`currency` mapped only
when supplied. Missing/null request means no known original facts. A partial request
contains `known_fields`, the sorted canonical field names explicitly supplied, including
explicit nulls. A nonnull budget requires amount and currency together. Itinerary span,
visits, profile defaults and requirements never reconstruct missing request facts.

The validator requires 1–400 actual unique calendar days and unique nonblank activity
IDs (missing IDs use deterministic source positions). It retains input order and empty
days, deriving a missing outer span from actual dates without filling gaps. Supported ISO
timestamps use `YYYY-MM-DDTHH:MM[:SS[.1–9 digits]][Z|±HH:MM]`; original strings survive
Save/read/export. Integer nanosecond comparisons enforce positive actual duration and
consistent endpoint awareness. Activity starts belong to their actual day. Actual transfer
endpoints must exist, differ and share a day. Connections retain zero or negative available
gaps (`preceding_end_time` to
`following_start_time`) as source conflicts: those boundaries require valid clocks and
matching awareness, rather than a positive journey duration. Departure/arrival and activity
intervals still require positive actual elapsed time. Optional Nearby retains supplied orphan,
conflicting or undated references separately; only absent nested anchor/date fields inherit
the real parent. Known measurements/costs must be finite and valid; public floating-point
measurements must fit their storage representation. Missing facts stay unknown. Supplied
`source_claims` must be an array of strings. Errors identify the failing field, and invalid
imports create no preview.

Import rejects NUL and unpaired Unicode surrogates in text or JSON keys before persistence;
valid Unicode and literal escape text remain unchanged. Persisted activity costs must fit
[PostgreSQL's exact numeric domain](https://www.postgresql.org/docs/17/datatype-numeric.html):
at most 131072 integer digits and 16383 fractional digits. Exact Decimal tuple arithmetic
checks the mathematical value without context rounding or fixed-point expansion. Zero is
canonicalized, and excess insignificant scale is removed only when required for storage;
ordinary accepted monetary scale is retained. These storage limits apply to activity costs,
not known original-request budgets, whose exact amounts remain JSON strings.

Artifact ownership, operation identity and private media binding declarations are rejected.
Allowlisted imported content is always `provenance=imported`, `trust=unverified_import`.
Google/origin/PASS/completion claims remain unverified source claims; imported completion
is unassessed and transfer claims cannot acquire trusted generated feasibility. No provider,
generation, profile inference or media refresh occurs during import or export.

Every shared detail offers versioned JSON, plain-text download and a copyable summary with
a selectable-text dialog fallback. Exports retain supported public content and known request
metadata, omit record authority/private diagnostics and distinguish unknown facts, free
windows, connections, optional Nearby and source trust. JSON `origin` explicitly records
the source snapshot's provenance/trust with `assertion=source_snapshot_only`; reimport
retains it as a source claim and always crosses the unverified boundary.
The structured origin allowlist contains only `provenance`, `trust` and `assertion` strings;
historical r7 string origins remain supported. Guest input survives
login; expired account input remains quarantined for same-account recovery. Logout/account
invalidation clears its session-stored intent.
File completions are fenced by edit/submission revision, component lifetime and session:
a late file read cannot overwrite a later paste or clear an accepted operation key.

### Implemented visible brief editor

`BriefPage` is the sole Product editor. It retains editable destination, ISO date-only
strings, traveler count, whole-trip budget/currency, required/avoided experiences and
free text. Date controls use the public server window and shared calendar arithmetic;
validation covers real dates, ordering, inclusive duration, positive integer travelers,
finite nonnegative budget and supported currency. Incomplete input remains editable
and recoverable. The composition boundary adds visible required/avoided wording to
`additional_preferences` and otherwise retains the existing `PlanningRequest` contract.
The server remains authoritative for its token ceiling and current generation window.

Interests, nullable pace (`relaxed`, `balanced`, `rich`) and transport priorities
(`walk`, `transit`, `drive`) add visible English sentences. Pace allows one or none;
transport allows any subset, including none for no preference. Transport is a soft preference,
never an allowlist. `editor_version=1` snapshots retain selections and exact span
bindings in tab-local recovery. Only untouched inserted text is owned: outside edits
shift offsets, inside edits detach the affected control, and deselection removes only
its still-owned sentence. Native edit ranges disambiguate repeated text; ambiguous
whole-text replacements relinquish possible ownership rather than guessing. Manually
written identical sentences remain unowned. Restoration accepts only exact valid
versioned bindings and does not search for or reclaim matching text.

The existing bounded assistance APIs supply destination suggestions with manual entry
and user-reviewed polish. Text/context revisions fence late responses; Apply and Undo
reconcile ownership without reclaiming detached wording. Dismiss, polish and login
return never generate an itinerary. Draft persistence stores the editor snapshot;
task submission validates the separate confirmed planning request.

### Replanning itineraries

The **Plan again** and **Plan another journey** actions in saved details, previews and
examples open the editable brief and clear its prior draft and submission identity.
Only the snapshot's original `request` seeds destination, dates, travelers and
budget/currency. Imported `known_fields` limits that mapping; absent or explicit null
values remain blank, including a visibly unselected currency. Missing basics are not
filled from itinerary dates, activities, generated descriptions or profile defaults.
All **Personalize your trip** fields start empty: interests, pace, transport preferences,
required/avoided places and additional preferences. Original composed preference text,
current editor choices and preference bindings are not carried into the new brief.

Opening or reopening this brief sends no generation or provider-refresh request. Replan
uses the same origin fence as drafts and restored editors, so a late new-brief initializer
or subsequent profile update cannot overwrite it. The user can edit every field; explicit
Generate applies the current date/budget/traveler validation and creates a new account-owned
task. Completion yields a new recoverable preview, and explicit Save creates a new trip.
The source saved snapshot, its known-request completeness and the submitted source task
remain unchanged. Historical source dates remain readable and editable, but require
correction to current generation dates before submission.

### Incomplete drafts and the collection boundary

`app.planning_drafts` stores owner, nonblank title, versioned incomplete editor JSON,
positive revision and timestamps. `POST /api/drafts` creates an independent idea;
`GET/PUT /api/drafts/{id}` resumes or revision-updates it. `PATCH` renames it,
`POST /api/drafts/{id}/copy` creates an independent copy, and revision-checked `DELETE`
removes it after browser confirmation. Missing and other-owner IDs both return 404.
Every mutation uses the account CSRF/origin boundary. No draft operation generates
an itinerary or consults profile defaults.

Snapshot validation accepts blank or generation-invalid field strings, while enforcing
`editor_version=1`, supported currency/interest/pace/transport values (with an empty
currency representing an unknown editor fact), unique controls,
field and collection bounds and valid Unicode. Exact span ownership uses browser
UTF-16 offsets. Stale, repeated or overlapping bindings are discarded and their controls
detached without searching for matching text; user wording remains intact.

The editor retains draft identity, last accepted revision and a recovered local title within the
same account-scoped recovery record as its brief. Saving again updates that identity;
Save as new allocates another. A 409 leaves local work intact and offers explicit reload
or Save as new. Reload confirms replacement of local edits. Expiry quarantines this
record; same-account login restores it without replaying a write. Logout and account
switching clear it. Typing during a pending save is retained locally. Responses from
an earlier editor navigation cannot attach its identity or errors to a newly opened brief.

`GET /api/library` is the single server-side collection boundary. Draft cards expose
`kind=draft`, source/draft identity, minimal destination/date fields and created/updated
timestamps. Literal case-insensitive title/destination search, newest/oldest creation-time
ordering and case-insensitive name ordering use ascending UUID and then kind tie-breaks.
Renaming does not move creation-ordered cards. Count and page read one repeatable-read
snapshot. `limit` is 1–50
(default 24), `offset` is 0–10000, and search is at most 100 characters. The browser
requests pages of four; missing fields use neutral placeholders. Saved cards join this
server-side union with `kind=saved` and server-owned source; equal UUIDs in different
tables remain distinct. Both card kinds open View details. `/drafts/{draft_id}` reads
the owned editor snapshot without changing the current brief, creating an itinerary or
writing anything. Authentication retains that private detail destination. Continue
planning explicitly opens the existing `/plan?draft=...`
editor and its revision-aware recovery. Draft detail preserves unknown/invalid input
as unconfirmed facts; it never fabricates a generated/imported provenance or request.
Naming uses Library Rename; the brief-review modal summarizes recorded inputs without
an editable title. A differing historical local name remains visible as read-only
recovery context and is preserved by Save.

The browser routes saved cards to immutable detail and offers
rename, independent Copy and confirmed deletion for both kinds. Saved Copy follows the
[saved snapshot operation contract](#independent-trip-copies-and-kept-examples).
Revision conflicts offer an explicit collection reload. A mutation 401 immediately hides
cards and the management dialog while canonical session recovery runs; login never
replays the mutation. Previews stay outside the library.

### Accepted application lifecycle

The English r7 Product interface has no language selector and uses V3 over an
allowlisted presentation. Its ten Product domain tables share the existing
PostgreSQL database with TripWorld.
[Tasks and previews](#durable-planning-tasks-and-previews),
[explicit decisions](#explicit-preview-decisions-and-normalized-saved-trips),
[imports](#historical-json-import-and-export) and
[drafts/library](#incomplete-drafts-and-the-collection-boundary) define durable
ownership, recovery and mutation rules. Profile initialization belongs to the
[new-brief contract](#profile-defaults-and-new-brief-initialization); historical
detail and source trust belong to the following shared presentation contract.

The fixed r7 pages remain the visual reference for Product layout, colors, icons and
controls. Readability refinements raise essential text sizes and muted-text contrast,
flatten nested activity frames on narrow screens and compact the initial planning form.
The `original.css`, `refinements.css`, `prototype.css` and
`nearby.css` layers retain their order under the Product scope. Real authentication,
progress, decisions and source
claims replace the prototype's browser simulations within that visual language.
My trips remains selected in desktop and mobile navigation while reading trip, draft,
example or preview details, or importing an itinerary.

### Public examples and reusable detail

`GET /api/examples` exposes exactly two curated cards: `sydney-example` and
`london-example`. `GET /api/examples/{example_id}` returns the same shared detail
presentation used by generated and saved trips. Each has three original travel days,
six scheduled visits, three source-backed transfers, complete historical daily weather
and three optional Nearby references. A visible historical-example note distinguishes
the retained dates and evidence from a current forecast or route check.

The bundled Product projections come from accepted V3 runs
`case01-v3-repair140-followup-20261013T064153Z` and `case-02-r1-v3-a1`.
Their server-only source metadata records input, final-result and matching-weather
digests. Editorial titles/tags do not change original request facts or primary visits.
London selects Jubilee Gardens instead of the photo-less Metaverse optional reference
from the same run's acquired Nearby ledger, retaining the London Eye anchor and
canonical identity. No generation or provider evidence refresh is part of curation.

Public detail needs no account, provider key or database and creates no example table;
photographs use the configured media providers. The guest library links to
`/examples/{example_id}`; signed-in users can also read those routes. The former
prototype cities and `nearby-linking` return 404; ambiguous-anchor scenarios remain
test fixtures rather than public itineraries.
Cards expose fixed-source creation timestamps for the original newest/oldest ordering;
the public collection's allowlisted API order does not change.

`backend/app/product/detail.py:ProductDetail` owns the `product_detail_1` contract,
mirrored by `frontend/src/features/product/detail/types.ts` and rendered by
`TripDetail`. It is separate from engine/research DTOs. Actual
ordered day/activity arrays, including empty days, are preserved. ISO date/time strings
are validated without datetime reserialization, retaining supplied precision and offsets.
Weather, costs, introductions, original request information and completion information
are optional. `request` contains only known original input; examples do not reconstruct
it from an itinerary. Provenance (`example`, `generated`, `imported`) and trust
(`source_fixture`, `generated_projection`, `unverified_import`) remain explicit.
This contract renders examples, previews and saved/imported snapshots; lifecycle
operations use their dedicated services.

Optional `illustration_key` values select the five bundled r7 illustrations;
`display_tags` retain supplied presentation labels without becoming request facts.
Activity and Nearby hints use the same illustration allowlist. Saved snapshots keep
these hints separately in `app.trips.display_metadata`, including independent copies
after source deletion. Empty hints are omitted from serialization so legacy import
fingerprints and operation receipts remain recoverable. These hints never confer a
verified place identity or provider photo authority.

The fixture adapter validates the public Product schema and excludes private provider
identity/evidence references. Curated examples retain the accepted final projection's
route metrics, estimate type and validation outcome, with `example`/`source_fixture`
provenance. Trusted generated transfers and server-curated examples can retain their final
`validation_state` (`PASS`, `CONFIRMED`, `UNKNOWN`) and provider/derived estimate kind.
For these snapshots, the connector, connections list and Details distinguish
fitting supplied timing (`PASS`), a confirmed timing conflict (`CONFIRMED`) and unverified
feasibility (`UNKNOWN` or absent) in plain language. Validation, evidence availability
and estimate type remain in public detail data and versioned JSON rather than raw UI
diagnostics. Legacy `source_claim` transfers and imported claims cannot acquire trusted
outcomes by supplying a status field; their travel time needs confirmation. Reimporting
an exported example remains unverified and cannot restore private photo authority.
Missing costs stay unknown, including when no total can be established. A zero amount
or zero weather metric is a known value. Place lists display authorized photographs
under the [media contract](#verified-place-media-and-curated-atmosphere), with illustration
fallbacks and full source details in place dialogs.
Map queries are URL-encoded; weather source links
admit only HTTP(S), and source text is rendered as text.

Daily weather starts collapsed on one line with its date, condition icon, estimated
average temperature and rain probability. The estimate is the midpoint of the supplied
daily low and high, marked `≈`; either missing bound leaves the average unknown.
Rain probability remains a percentage, not rainfall in millimetres. Clicking the row
or using the keyboard expands its condition, low/high temperatures, wind, attribution
and source details. Zero remains a known value in both the summary and expanded view.

Detail preserves the desktop two-column layout. Nearby references remain a flat ordered
list with their exact supplied `anchor_activity_id` and optional `associated_day`.
Resolution requires one scheduled activity with that exact ID and, when supplied, that
date. A unique exact anchor can resolve without a supplied date; names and prose never
establish links. Counts include only resolved references. Date and activity groups start
expanded, with separate disclosure and locate controls. Explicit pointer/keyboard location
expands the target day/group, focuses it and briefly highlights both surfaces; hover and
scroll do not select. Day filters apply to both surfaces. Missing, mismatched or ambiguous
anchors stay in Other nearby references; their exact identifiers/dates remain in source
data, while the visible rows show place names and Details without internal anchor IDs.
Undated unresolved references survive every filter.

At widths up to and including 800px, resolved references use an initially collapsed
disclosure inside the activity card below its actions, without a new timeline marker or
time. The resolved sidebar is hidden and Other nearby references remains available.
Breakpoint changes preserve visible focus, and reduced motion disables the pulse and
smooth location. Details use a native modal dialog with keyboard focus containment and
restoration. No favorites or saved-place collection is introduced.

Acceptance uses real isolated PostgreSQL through Product APIs, browser journeys
and the public migration entrypoint, with external transports substituted. The
[development guide](guides/development.md#product-account-setup-and-acceptance)
owns runnable commands; the dated lifecycle record owns actual results and limits.

### Verified place media and curated atmosphere

Product media is a display boundary outside independent planner/evaluator serialization.
The application binds a scheduled activity only when its final `source_place_id` belongs
to Google-sourced `result.v3.final_places`. Removed candidates, free windows, displayed
names and early evidence cannot grant authority. Nearby uses the final reference and its
strict discovery ledger: exact place ID, adopted anchor activity/source ID and date must
agree. Imports reject private binding declarations; imported Google claims cannot
establish a verified place photo identity. The two server-curated examples carry
bindings from the same final projection and acquired Nearby identity checks; a public
caller cannot add a place ID or URL to that allowlist.

Application-private slots (`activity:{activity_id}` and `nearby:{ordered_position}`)
map to stable Google place IDs in `media_bindings` JSONB on previews and saved trips.
Migration 006 adds columns without another domain table. Save carries the map into the
trip transaction. Whole-trip Copy reads this server-owned map inside the same owner/source
transaction and carries it into the independent trip through the normalized writer;
directly decided Copy receipts keep an empty map. Imported claims and client Copy bodies
cannot supply bindings. Keep a copy carries a curated example's private map into the
same independent saved representation. Copies resolve display metadata separately after persistence.
Public detail, JSON/text export and research results omit the map. The database does
not persist expiring photo resource names, image URLs, author metadata or image bytes.

`GET /api/previews/{id}/media` and `/api/trips/{id}/media` return display metadata only
after the same owner check as detail; missing/other-owner IDs return 404. Saved-preview
receipts delegate to the surviving owned trip, while discarded/deleted outcomes return
no images. Public `GET /api/examples/{example_id}/media` resolves only the two bundled
maps, with identical response and work bounds. Each request admits 200–1280px dimensions,
at most 12 ordered slots, three parallel resolutions and a 30-second batch deadline.
There is no itinerary-wide slot cap. Repeated `slot` parameters select only server-authorized
bindings; an unknown slot is unavailable without a provider call. Without explicit slots,
`offset` and `next_offset` page through all bindings. The browser requests verified-place
activity slots in itinerary order followed by Nearby, in sequential batches, rather than
using JSONB key order. Supporting slots use their separate authorized atmosphere path.
Each Google slot performs at most
one fresh `photos` Details request and one media metadata request, with an 8-second HTTP
timeout, an 8-second complete-slot deadline and 256 KiB response limit. The complete-slot
deadline includes any provider fallback. Completed photos
survive another slot's timeout or a later failed batch. Redirects and arbitrary fetch destinations are
rejected. Responses retain `Cache-Control: no-store`; the backend has no photo metadata
cache or automatic retry. The browser's explicit session cache below determines which
slots need fresh metadata. Activity and Nearby lists display authorized photographs
when an owned itinerary or curated example opens. **Refresh photo** in a place dialog
resolves only the selected slot, without replanning or refreshing itinerary facts.

#### Place photo fallback

For authorized activity and Nearby slots, Google remains the first provider. A successful
Google Details response with absent or empty `photos` triggers an Unsplash search. The
bounded query uses only the owned detail's structured place name and destination, falling
back to destination or the fixed general search when labels are absent. Activity titles,
private notes, preferences and complete itinerary bodies are not sent. Client query text,
unbound slots and imported place-ID claims cannot authorize a search.

Only a valid empty result list advances to a second search using the normalized structured
destination alone. If that query equals the first query ignoring case, it is not repeated.
The chain is **Google → Unsplash place name plus destination → destination atmosphere →
illustration**, with at most two distinct Unsplash searches and only the first result of
each. Both searches use the same [first-result validation and adoption rules](#supporting-atmosphere-photos)
as supporting imagery. A missing key, unsafe or malformed first result, tracking failure,
HTTP error or timeout stops resolution with an illustration; it does not broaden the search.
Google authentication, quota, timeout, malformed-metadata and invalid-image-reference
failures do not masquerade as confirmed photo absence. All stages share the original
8-second complete-slot and 30-second batch deadlines, without additional retries or a
server cache. Preview, Save/read, independent Copy and curated examples retain the chain.
The legacy curated London endpoint uses its existing Tower Bridge binding; its fallback
alt describes London atmosphere, while a verified Google photo retains the landmark alt.

The display result carries `kind: atmosphere`, `theme: general` and
`fallback: google_no_photos`. Details shows Atmosphere photo, Unsplash and the supplied
photographer/source links as static text; the list keeps its original main-visit or
Nearby layout. This imagery establishes neither a verified photograph of that place nor
new identity, role or fulfillment authority. No native itinerary or saved binding is rewritten.

#### Browser tab photo session

The local/private Product uses `sessionStorage` to retain successful verified-place,
place-fallback, supporting-atmosphere and cover photo URLs with supplied attribution and safe author/source
links. An omitted
optional source link does not prevent caching a valid photograph. The cache does not
store image bytes, credentials, tokens, full itineraries or private media bindings.
This is an application-managed metadata cache, independent of HTTP image caching;
it does not change the media endpoint's `no-store` response directive.

Each entry expires **one hour after successful acquisition**. Reads and reloads never
extend expiry. Storage is bounded to **1,000 entries and approximately 5 MiB of serialized
data**, evicting the oldest entries first. Corrupt/unsupported records, future timestamps,
disallowed URLs, denied storage and quota failures fall back to ordinary media loading.
Only successful photos are retained; loading, unavailable and error states are not cached.

Keys separate account, login/invalidation generation, endpoint/resource identity,
detail snapshot fingerprint, provider, media kind, controlled theme, requested dimensions
and slot. Saved trips, previews,
independent copies and public examples cannot share private entries. Bundled examples
use a guest scope. The snapshot fingerprint detects changes; it grants no authorization.
Private photos remain hidden until authentication and the server's owned-detail read
succeed. Reads validate the current scope, entry shape, expiry and provider URL rules.
Valid hits bypass the media endpoint for those slots; only misses/expired entries enter
the existing ordered batches of at most 12. Successful batches remain reusable if a
later batch fails. Concurrent same-slot consumers share requests, including development
StrictMode effects. Abandoned requests are canceled when their last consumer leaves,
and late responses cannot render or persist into an invalidated scope.

Logout, session expiry/revocation, account switch and cross-tab session invalidation
clear private entries and hide their active photos. Confirmed trip deletion and preview
decisions invalidate the relevant resource. Changed snapshots or slot sets cannot reuse
old entries. Google and supporting endpoints share the same resource invalidation identity,
including size-query variants, so these events fence both provider families. A media 401
clears the owner's photos; 403/404 invalidates the resource.
Normal authentication and ownership checks remain required after every page reload.

A cached URL that fails image loading is evicted and receives **one automatic
reacquisition per slot per display cycle**. A further failure shows an illustration
with **Retry photo**. Manual refresh/retry affects only that slot and cannot extend
neighboring entries' expiry. A failed supporting image instead removes the thumbnail,
retaining the compact activity card. Photographs load directly from the provider image host;
cache hits do not guarantee zero image network requests or zero billing.

Reload retains the tab's storage session, and normal tab closure ends it. Browser
closed-tab, crash and session restoration may restore `sessionStorage`; restored entries
still undergo the fixed expiry check. This is not secure deletion or a guarantee of
isolation for browser-created duplicate tabs. External application links use `noopener`.
There is no unconditional `beforeunload`/`pagehide` purge, durable browser storage,
server/CDN image cache, service worker or cross-tab photo-sharing mechanism.

Destination covers and the fixed atmosphere catalog share this cache's lifetime, count and
byte budget with itinerary activity and Nearby slots. Cover keys use the canonical request
endpoint (including destination and requested dimensions), account/login generation,
provider/kind and a dedicated cover snapshot/slot identity. Same-destination cards, results,
drafts and detail heroes reuse metadata within an account; guest examples and the login
image use a separate public scope. A cover is destination-level display metadata, so deleting
an individual itinerary does not remove a cover shared with another itinerary. Account
invalidation still clears all private covers and rejects their delayed writes. Provider-license review
and public deployment are outside [Issue #233](https://github.com/rplalala/Dayloom/issues/233).

Successful place fallbacks use distinct Unsplash/atmosphere/place-fallback keys within the
original owner, resource, snapshot, dimensions and slot boundaries. They never borrow
supporting-theme aliases or another place's slot. A hit bypasses both provider stages and
preserves acquisition time; unavailable results remain uncached. Selected refresh evicts
only that slot's Google/fallback alternatives before resolving the chain again. Existing
resource/account fences also reject delayed fallback writes. Valid legacy Google entries
retain their original acquisition timestamps during compatibility handling.

#### Supporting atmosphere photos

`GET /api/{previews|trips}/{id}/supporting-media` reads the owner's actual detail and
admits only explicitly scheduled `generic_activity` slots. Unknown historical roles,
principal visits, transport and free windows do not acquire atmosphere slots from a
title, photo or map link. Imported declarations remain display hints; an atmosphere
photo never creates a verified place binding or requirement fulfillment.

The search prefixes the following fixed theme suffix with the owner's normalized
structured destination, bounded to 120 characters. For example, the `walk` theme searches
`Melbourne scenic walk` or `New York scenic walk`. Missing destinations leave the card
without imagery. Client destination/query overrides, activity titles and private text do
not influence this server-owned context.

| Structured theme | Fixed public search suffix |
| --- | --- |
| `meal` | `relaxed meal` |
| `rest` | `peaceful rest` |
| `explore` | `neighborhood exploration` |
| `walk` | `scenic walk` |
| `general` | `travel moments` |

The existing server-side Unsplash key and provider boundary search page 1 with
`per_page=1`, `order_by=relevant`, `orientation=landscape` and `content_filter=high`.
Only `results[0]` may be adopted. The adapter validates the image, photographer/source
links and exact returned photo download-tracking path, preserving hotlink parameters.
Automatic selection records one adoption through the returned `download_location`;
ordinary display/reload of valid cached metadata records none. There is no second-result
choice, second Unsplash query, LLM picker, arbitrary query/URL proxy or retry. Private notes,
preferences and itinerary bodies are not sent to this search.

The existing slot, parallelism, HTTP/slot and batch bounds apply. Same-theme work is
merged within a batch and across concurrent browser consumers. Session aliases stay
within the same account/login/resource/snapshot/provider/kind/theme/dimension boundary,
retain slot ownership and copy the original acquisition timestamp. Failure states may
be shared during the active page attempt but are not persisted. A search-version marker
prevents reuse of older theme-only images after destination-aware search is deployed;
destination changes also change the existing detail snapshot fingerprint. Valid pre-extension
Google cache keys are upgraded on read without resetting timestamps or refetching.
Google-specific URL rules remain separate and unchanged.

Supporting cards request 360×240 metadata and display 4:3 thumbnails at 112×84px on desktop
and 88×66px at widths up to 800px, with 10px rounded crops. Thumbnails open the
existing Details dialog. The Atmosphere photo label, Unsplash provider, photographer and
source links appear only in Details as static, readable content, with keyboard/touch access.
The image container accommodates the full caption and label without clipping; Escape
closes the dialog even when a source link has focus. Missing credentials,
empty/unsafe first results, tracking failure, timeout, rate limits or image failure leave
the compact white card without imagery. Its time, title, notes and navigation remain
usable; detail Refresh photo targets only its slot. Destination covers use their
[separate cover boundary](#destination-covers) and cache identity within the shared budget.

#### Photo presentation

Principal and historical activity thumbnails use a 4:3 crop and align with the text's
top edge on desktop and tablet, including long introductions. At widths up to 560px they use a full-width
16:9 crop above the text. Nearby thumbnails remain square across sidebar and inline
rows. Both use cover cropping, consistent rounded corners and restrained spacing.

Verified-place activity and Nearby lists show photographs without provider or author captions. The
place detail dialog contains Google Maps attribution, all supplied author names and
safe profile/source links beside the photograph. The label uses `translate="no"`,
an unwrapped 12px normal-weight sans serif label and gray text on a light background.
Unavailable metadata, absent identity/keys and expired/failed image loads retain the
labelled illustration. Unattempted slots show Photo pending and active batches show Loading photo;
neither is labelled unavailable before an attempt finishes. Preview access and Save remain independent of media success.
Destination covers and fixed hero images retain their existing atmosphere-credit disclosure.
Supporting images follow the [Details attribution rule](#supporting-atmosphere-photos).

This list/detail split does not meet Google's documented requirement to include
provided author attribution wherever the photograph is displayed. Keeping attribution
only inside a dialog is not asserted to satisfy that requirement. See
[Place Photos](https://developers.google.com/maps/documentation/places/web-service/place-photos)
and [Places attribution policies](https://developers.google.com/maps/documentation/places/web-service/policies).

Product detail omits internal completion reviews, policy reason codes, raw route
claims and source anchor IDs. Route timing conflicts and uncertainty remain visible
in plain language. The copyable/plain-text itinerary summary uses the same travel
vocabulary without serialized internal objects; the versioned JSON export retains
its existing compatibility contract. Independent research data and entry points are
unchanged.

#### Destination covers

Itinerary detail, My trips and example cards, planning results and draft covers use public
`GET /api/media/destination?destination=...`. The only search text is the structured
destination label: whitespace is normalized and the query is bounded to 120 Unicode code
points. Empty labels do not initiate provider work. The endpoint admits 200–1280px dimensions,
uses `Cache-Control: no-store`, and shares the existing server-side Unsplash adapter and
first-result validation/adoption rules. One search and its adoption share an eight-second
complete deadline; the query is the destination itself, without an additional theme or
fallback query. Only the first result is eligible. Missing credentials, empty or unsafe
metadata, failed adoption, provider errors/timeouts and failed image loads display the
stable local illustration. They never substitute a fixed photo from another city.

Successful cover metadata uses the [browser tab photo session](#browser-tab-photo-session).
Valid reload/navigation hits bypass both the metadata endpoint and its provider search/adoption.
Reads do not renew acquisition time. Same-key concurrent mounts, including StrictMode,
share request leases; abandoned work is canceled when its final consumer leaves. A failed
cached image is evicted and receives one automatic reacquisition per display cycle; a
further failure shows the illustration. Unavailable/error metadata is not cached. Denied
storage and quota errors preserve ordinary display without reusable metadata. This stores
URLs and credits, not image bytes, and does not guarantee zero image-host network traffic.
Changing the destination cancels the previous request and fences its late response.
The alt describes destination atmosphere, without granting verified place,
role or experience fulfillment authority. Different queries may still yield the same
provider-selected first photograph; no randomization or cross-city deduplication is added.

Login retains its fixed Sydney image. The existing public
`/api/media/curated/{sydney|london|nature}` catalog remains compatible: Sydney/nature resolve
fixed Unsplash metadata, and London uses its curated example's Tower Bridge binding. These
catalog choices no longer select itinerary destination covers.

Unsplash hotlink tracking parameters survive bounded image resizing, and photographer/source
links carry application referral parameters. Cover credits appear on image hover or keyboard focus;
a small information control also opens them on touch devices, with explicit Close and
Escape support. Credits remain operable above image navigation links and hero shading.
No image-byte archive, avatar storage, manual image picker or download proxy is added.
This adapter follows the [Unsplash API documentation](https://unsplash.com/documentation)
and [API guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines).
Optional server keys and controlled acceptance are documented in the
[development guide](guides/development.md#product-media-setup-and-acceptance).

## Configuration, evidence and verification

[runtime.yaml](../config/runtime.yaml), [runtime.acceptance.yaml](../config/runtime.acceptance.yaml)
and typed loaders own the selectable development and Product acceptance values;
[configuration guide](../config/README.md) explains them. Avoid copying historic budgets
from execution plans. Usage counters, actual HTTP sends, output tokens and billed cost
are separate measurements. Missing evidence stays unknown. Opt-in captures and ignored
raw artifacts support development diagnosis without becoming a fresh-clone dependency.

Product defaults to the [acceptance resource profile](../config/README.md#product-acceptance-profile).
Optional input assistance uses account-level cooldowns and provider concurrency instead of
small process-wide daily cutoffs. Guests remain supported by direct client-address identity.
Terminal outcomes distinguish resource limits, timeout, provider failure and insufficient
requirement evidence; these failures keep the original requirements and allow an explicit
retry without asking the user to rewrite them. Unsupported hard capabilities and genuinely
ambiguous input retain their separate feedback paths.

Operational commands and verification entry points are in
[the development guide](guides/development.md). Dated engineering evidence is indexed in
[records](records/README.md); collaboration and testing rules belong to
[AGENTS.md](../AGENTS.md).

## Product projection and optional introductions

Product maps only final identity/date-matched evidence: daily weather, final-adjacency transfers,
nested Nearby and policy completion. It omits research versions, canonical source IDs, repair
reports and route ledgers. Confirmed final connection conflicts remain visible rather than
being silently removed. Provider seconds/metres and application reserves display separately.
One optional primary-POI introduction batch runs after successful planning inside the remaining
request deadline. It can use normalized summaries or explicitly unverified model knowledge;
failure omits introductions without discarding the itinerary. Independent planners and Nearby do not
trigger this call, and introductions cannot change validation or research output.

## Streams, progress and cancellation

Product's task observation and cancellation authority are defined in the
[durable task contract](#durable-planning-tasks-and-previews). Its SSE adapter emits
persisted `task` revision snapshots and a completed `result` containing task/preview
identity plus the public detail. Navigation, disconnect and logout detach observation;
none is an explicit Stop action. The browser uses canonical reads for reconnect recovery,
without resending generation automatically.

The internal [request-owned stream helper](../backend/app/api/streaming.py) remains available:
`started`, `stage`, optional `detail`, and terminal `result`, `error` or `cancelled`.
Events carry request-local `run_id`, increasing `sequence`, `type`, `elapsed_ms` and
`version`. Stage text is allowlisted; diagnostic detail requires the internal debug mode.
[ProgressObserver](../backend/app/observability/progress.py) bounds buffering and reports
`dropped_events`. Heartbeat comments follow 15 seconds without an event. Terminal
errors cannot change the already-sent HTTP status. Disconnect cancels and awaits that
request's producer/owned transports; it does not guarantee external termination or billing.

The helper is not exposed through a Developer HTTP endpoint. Product's shared stream
parser handles sequences, UTF-8/chunk framing, comments and premature EOF without
automatic execution retry. Workflow position follows observed stages, rather than
elapsed-time percentage or an arrival-time promise; stage completion is not proof
that Repair succeeded.
