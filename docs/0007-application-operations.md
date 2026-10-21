# Application interfaces and engineering operation

Status: Implemented application boundary, consolidated 2026-10-03.
The unified Product design is being implemented in slices. Accounts, the r7 shell,
authentication return and the Product migration entrypoint are implemented. Planning
still uses the existing HTTP/stream boundary until the durable task slice replaces it.

## Product and Developer surfaces

Product presents V3 through a version-agnostic API and an allowlisted user contract.
Developer mode selects V0-V3 independently and retains diagnostics needed for engineering.
React owns form state, progress and rendering. FastAPI validates input, invokes application
services and serializes outcomes. Long planning work uses the existing streaming boundary;
stale responses must not overwrite an edited request. Cancellation and errors are explicit.

Inputs share destination text, currency selection, ISO dates and optional preferences.
Server date policy owns admissibility; browser display must not change dates through
timezone conversion or locale-dependent parsing. An input change invalidates the appropriate
previous result. Product completion reasons are policy observations, not global feasibility.

## Input assistance

GeoDB suggestions are requested through a bounded backend adapter. Manual entry remains
available when suggestions fail or do not cover a place. GeoDB selection does not create
planner identity evidence. Preference polishing is an explicit, bounded single-call action
with preview, Apply/Dismiss and Undo. It neither auto-submits nor bypasses the unchanged
planning input gate. A schema-valid suggestion is not proof of semantic equivalence or
better gate acceptance. Old two-call polishing designs are historical.

Source task and acceptance: [planning input UX #25](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/25).

## HTTP contract map

| Endpoint | Input and result | Source of truth |
| --- | --- | --- |
| `POST /api/auth/register` | Normalized email, password and display name; atomic account/profile and browser session | [Account boundary](../backend/app/product/auth.py) |
| `POST /api/auth/login` | Email/password; generic credential failure or browser session | [Account boundary](../backend/app/product/auth.py) |
| `GET /api/auth/current` | Validated account, initials and session-bound CSRF token | [Account boundary](../backend/app/product/auth.py) |
| `POST /api/auth/logout` | Revoke every account token and clear the browser cookie | [Account boundary](../backend/app/product/auth.py) |
| `POST /api/planning` | Shared `PlanningRequest`; V3 Product response discriminated by `status` | [Product router](../backend/app/api/product/planning.py), [HTTP schemas](../backend/app/api/schemas/planning.py) |
| `POST /api/planning/stream` | Same input and terminal result, delivered through request-lifetime SSE | [Product router](../backend/app/api/product/planning.py), [stream delivery](../backend/app/api/streaming.py) |
| `GET /api/planning/date-window` | `allowedStart`, `allowedEnd`, `maxTripDays` from server date policy | [Product router](../backend/app/api/product/planning.py), [date policy](../backend/app/policies/trip_dates.py) |
| `POST /api/dev/planning` | `{version, request, reference_date?}`; version is `v0` through `v3`, output is full `PlanningResult` | [Developer router](../backend/app/api/developer/planning.py), [HTTP schemas](../backend/app/api/schemas/planning.py) |
| `POST /api/dev/planning/stream` | Same version-selected input/result through an independent SSE request | [Developer router](../backend/app/api/developer/planning.py) |
| `GET /api/input-assistance/destinations?q=...` | Bounded normalized GeoDB suggestions for UI selection; no planner evidence | [Assistance router](../backend/app/api/input_assistance.py), [schemas](../backend/app/schemas/input_assistance.py) |
| `POST /api/input-assistance/preferences/polish` | `original_text`, `context`, `client_revision`; `suggested`, `unchanged` or `needs_input` | [Assistance router](../backend/app/api/input_assistance.py), [schemas](../backend/app/schemas/input_assistance.py) |
| `GET /health` | Process health response | [Application](../backend/app/main.py) |

The shared request uses `input_version=planning_request_2`, destination, ISO start/end
dates, traveler count, mandatory total budget/currency and optional preferences.
[PlanningRequest](../backend/app/schemas/request.py) owns field validation; do not copy
the complete schema into UI or operational prose. Product does not accept engine selection
or a research reference-date override. Developer's optional reference date supports explicit
engineering fixtures and does not authorize historical live evidence acquisition.

Product outcomes are `completed`, `needs_clarification`, `safety_blocked` and
`provider_blocked`. Clarification carries requirements/issues; safety/provider blocks
carry application-authored user actions without raw provider details or sensitive quotes.
`completed` means a result was produced; inspect its separate policy completion rather
than interpreting the HTTP outcome as globally feasible or fully validated.
Developer returns research metadata and reports clarification as HTTP 422. Invalid request/
date validation is 422; public planning/boundary failures are 502 and timeouts are 504.
Product's typed clarification/block outcomes remain distinct from those HTTP failures.

The [frontend Product API](../frontend/src/features/planning/api.ts) and
[Developer API](../frontend/src/features/developer-planning/api.ts) bind these wire contracts;
the [shared stream parser](../frontend/src/shared/api/planningStream.ts) handles delivery.
Changing a schema requires the corresponding backend and client seam checks.

## Information and security boundaries

Provider/model content is untrusted data and rendered as text. Product projection excludes
credentials, internal prompts, raw payloads and research-only internals. Missing costs,
weather or route facts remain honestly represented. Secrets belong in local environment
configuration, not committed documents, logs or client bundles. Provider URLs and requests
are constrained by their adapters; user prose is not arbitrary outbound-fetch authority.

PostgreSQL/pgvector supports retrieval; Product accounts use the separate `app` schema
in the same database. Saved itineraries remain pending under the
[unified Product design](#product-experience-and-persistence-design).
Per-process development limits are not account-wide billing enforcement or distributed
abuse controls; this design does not establish a public deployment guarantee.

<a id="accepted-product-persistence-design"></a>

## Product experience and persistence design

Status: Accounts and shell implemented; remaining lifecycle slices pending. Dayloom r7's visual/interaction baseline is
provisionally accepted. The unified specification
[#198](https://github.com/rplalala/Dayloom/issues/198) owns the detailed
frontend/backend requirements, confirmed integration choices and user-confirmed acceptance
seams. Thirteen implementation slices are published under #198, reusing #120-#123;
#119 is the historical design/mapping entry.

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
input-assistance reads remain guest-accessible. Developer authentication is unchanged.

The Product React shell exposes home, a shared minimal brief, login/register, guest
example cards, an authenticated empty library and an initials-only account page.
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
account content while preserving quarantined recovery. Server-side drafts, profile
editing, curated example detail and durable generation are implemented by later slices.

Product remains V3 over an allowlisted presentation, using the existing PostgreSQL
instance/database with `app` alongside `tripworld`. The accepted application lifecycle is
an editable brief, explicit task submission, a recoverable preview and explicit Save or
Discard. Browser navigation, reload and closure detach observation rather than cancelling
an accepted task. One account may have one active task while editing or saving other briefs.
Generated/imported previews stay outside My trips until saved; copying a saved trip or
keeping an example creates an independent snapshot without generation. Pending previews,
task state, drafts and saved content are durable Product data, separate from graph state.

The accepted ten-table model extends the seven original account/profile/trip snapshot
entities with planning drafts, tasks and previews. It retains owner isolation, transaction
rollback, idempotency, original dates/offsets, actual day/list order and honest uncertainty.
It adds explicit provenance for imported/copied content, free-window semantics and nullable
resolved Nearby associations with separately retained unresolved references. Imported status
claims are not backend verification. The old automatic-save/exactly-seven-table design is
not the implementation target.

The r7 interface is English without a language selector. Guests see example trip cards;
authenticated accounts see their own mixed saved-trip/draft collection or an empty state.
Defaults visibly prefill only new briefs. Pace is single-select; transport selections are
soft priorities, with an empty set expressing no preference. Editable preference text
and polish preview/apply/dismiss/undo remain part of the unified flow. Account images use
initials; avatar upload and its storage design are deferred.

Detail preserves the desktop two-column layout. Nearby groups by day and exact activity
ID, with a count entry and explicit bidirectional location/highlight; mobile uses an inline
activity-card disclosure. Unresolved associations stay in Other nearby references; no
favorites or saved-place collection is introduced. Google Places Photos require a verified
identity binding and safe media presentation; Unsplash supplies destination/atmosphere
imagery. Missing facts/images remain unavailable rather than invented.

The remaining task/storage mechanisms are specified in #198. Confirmed acceptance uses Product APIs with real isolated PostgreSQL,
browser journeys through those APIs with external providers mocked, and the public migration
entrypoint. Only touched V0-V3/Developer boundaries receive offline compatibility checks.
Runnable account/migration checks are in the [development guide](guides/development.md#product-account-setup-and-acceptance).

## Configuration, evidence and verification

[runtime.yaml](../config/runtime.yaml) and typed loaders own active tunable values;
[configuration guide](../config/README.md) explains them. Avoid copying historic budgets
from execution plans. Usage counters, actual HTTP sends, output tokens and billed cost
are separate measurements. Missing evidence stays unknown. Opt-in captures and ignored
raw artifacts support development diagnosis without becoming a fresh-clone dependency.

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
failure omits introductions without discarding the itinerary. Developer and Nearby do not
trigger this call, and introductions cannot change validation or research output.

## Streams, progress and cancellation

[Stream delivery](../backend/app/api/streaming.py) sends `event: <type>` and JSON `data`
frames. Types are `started`, `stage`, optional Developer `detail`, and terminal `result`,
`error` or `cancelled`. Every observed event has request-local `run_id`, monotonically
increasing `sequence`, `type` and `elapsed_ms`; Developer adds `version`. Stage messages
carry stage/occurrence/status identifiers, parent linkage and public text; diagnostic details
are Developer-only. [ProgressObserver](../backend/app/observability/progress.py) owns fields
and bounded buffering, including an explicit `dropped_events` count when applicable.
Heartbeat comments (`: keep-alive`) are sent after 15 seconds without an event.

A terminal `result` embeds the same typed response as ordinary HTTP. An `error` carries
`http_status` and public `detail`; once streaming starts, that event does not change the
already-sent HTTP status. Input/date errors can occur before stream creation. A disconnected
client may not receive a terminal cancellation frame; server cleanup still cancels and
awaits the producer. No stream event establishes that an already-dispatched external call
was cancelled or unbilled.

Product uses one stream; `/dev` launches four independent streams from a copied input snapshot.
Forms lock during active work. Per-run/all-stop, same-snapshot reruns and unmount cancellation
use controller/group identities to reject late superseded results. Editing an idle form clears
the result group. Only terminal successful results render itineraries. Sequence duplicates,
UTF-8/chunk boundaries, heartbeat comments and premature EOF are handled without automatic retry.
Developer event history is bounded and reports losses; complete final JSON is retained separately.

Progress is a monotonic workflow-position estimate driven by observed stages, not elapsed-time
percentage or a remaining-time prediction. Skipped/unknown stages do not advance it; repeated
Repair occupies a bounded region. Only success completes the bar; stop/error retains position.
Stage completion is not proof of successful repair and overlapping durations are not summed.

API request ownership includes the underlying HTTP transports, not just adapter wrappers.
Partial setup closes already-created resources; cancellation awaits owned cleanup. Independent
requests must remain usable after another closes. Local cancellation cannot guarantee termination
or billing cancellation of work already dispatched to external providers. Streaming provides
no reconnect/resume or public multi-user service guarantee. Planned saved-trip history uses
the proposed task/preview boundary described above; these request-lifetime Product
semantics remain the implemented behavior until that coordinated migration.
