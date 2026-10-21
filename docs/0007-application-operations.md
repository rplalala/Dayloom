# Application interfaces and engineering operation

Status: Implemented application boundary, consolidated 2026-10-03.
The unified Product design is being implemented in slices. Accounts, the r7 shell,
authentication return, the editable travel brief and the Product migration entrypoint
and durable generation tasks with recoverable unsaved previews are implemented.
Product HTTP/stream entrypoints submit and observe that same account task lifecycle.

## Product and Developer surfaces

Product presents V3 through a version-agnostic API and an allowlisted user contract.
Developer mode selects V0-V3 independently and retains diagnostics needed for engineering.
React owns form state, progress and rendering. FastAPI validates input, invokes application
services and serializes outcomes. An application-owned coordinator runs Product work;
observers read persisted snapshots. Developer retains request-owned streaming and cancellation.
Stale responses must not overwrite an edited request.

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
The original and suggested text retain literal whitespace so client revision matching
and exact editor span ownership remain valid. Whitespace-only input is rejected.

Source task and acceptance: [planning input UX #25](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/25).

## HTTP contract map

| Endpoint | Input and result | Source of truth |
| --- | --- | --- |
| `POST /api/auth/register` | Normalized email, password and display name; atomic account/profile and browser session | [Account boundary](../backend/app/product/auth.py) |
| `POST /api/auth/login` | Email/password; generic credential failure or browser session | [Account boundary](../backend/app/product/auth.py) |
| `GET /api/auth/current` | Validated account, initials and session-bound CSRF token | [Account boundary](../backend/app/product/auth.py) |
| `POST /api/auth/logout` | Revoke every account token and clear the browser cookie | [Account boundary](../backend/app/product/auth.py) |
| `GET /api/profile`, `PUT /api/profile` | Read or replace the authenticated owner's display name and travel defaults | [Profile boundary](../backend/app/product/profiles.py) |
| `/api/drafts` and item/copy operations | Versioned incomplete editor snapshots and revision-checked owner mutations | [Draft collection](#incomplete-drafts-and-the-collection-boundary) |
| `GET /api/library` | Bounded server-side card search, ordering and pages | [Collection boundary](#incomplete-drafts-and-the-collection-boundary) |
| `POST /api/planning` | Shared `PlanningRequest` plus `Idempotency-Key`; 202 durable task snapshot | [Product router](../backend/app/api/product/planning.py), [HTTP schemas](../backend/app/api/schemas/planning.py) |
| `POST /api/planning/stream` | Same submission identity; observe durable task revisions and final public detail with task/preview IDs | [Product router](../backend/app/api/product/planning.py), [stream delivery](../backend/app/api/streaming.py) |
| `POST /api/planning/tasks` | `{operation_key, request, editor_snapshot?}`; 202 immutable task snapshot or 409 active/key conflict | [Task lifecycle](#durable-planning-tasks-and-previews) |
| `GET /api/planning/tasks`, `/recent`, `/active`, `/{id}` | Owner-only bounded recent/active reads, operation-key lookup and canonical snapshots | [Task API](../backend/app/product/tasks.py) |
| `GET /api/previews`, `/{id}` | Paged pending summaries and owner-only full public detail/decision receipt | [Task lifecycle](#durable-planning-tasks-and-previews) |
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

Product task outcomes distinguish `completed`, `needs_clarification`, `safety_blocked`,
`provider_blocked`, `failed` and `cancelled`. Typed clarification/block/failure actions
retain the immutable submitted input without raw provider diagnostics or sensitive quotes.
A completed preview retains its separate policy completion and uncertainty; persistence
does not imply global feasibility. Invalid submission/date/currency fields fail with 422
before external work. Developer retains its research responses and HTTP failure policy.

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

Status: Accounts, profiles, shell, drafts, brief editor, durable tasks and previews implemented;
saving/import/copy lifecycle slices remain pending.
Dayloom r7's visual/interaction baseline is provisionally accepted. The unified specification
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

The Product React shell exposes home, a shared brief editor, login/register, guest
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

Trusted final V3 presentation becomes one `product_detail_1` snapshot in
`app.itinerary_previews`, atomically with the completed task reference. Uncertainty,
canonical source names, final transfers and policy completion survive projection. The
preview is separate from the saved library and survives app/browser recreation. Pending
summaries use bounded `limit`/`offset` pages; pending item reads return the full snapshot.
Save/Discard decisions use the same receipt row, with retained operation identity and
saved-result tombstones. Task/preview foreign keys enforce same owner and source task;
account deletion cascades both. No queue, event log or graph checkpoint is introduced.

The global desktop/mobile entry and `/planning` rehydrate task state with one in-flight
bounded poll, reconnect/focus reads and an observed completion notice. Completion neither
redirects nor changes the current brief. `/previews/:id` reads immutable unsaved detail.
An ambiguous submit response triggers only an operation lookup; its immutable intent
and key stay account-scoped through expiry. Explicit logout/revocation clears it. A late
response cannot overwrite another edited brief or submit it with an unresolved earlier
operation identity. The HTTP adapter returns 202; SSE observes revision snapshots, then
emits the same task/preview IDs with its allowlisted public detail. Disconnect detaches
only the observer. Developer streaming and independent V0–V3 entrypoints are unchanged.

The Product dependency factory adds English writing policy only to primary/Repair
provider system prompts, preserving request/source text and proper names. It admits the
final effective prompt under existing limits and records effective sizing separately.
It adds no translation send or retry. Developer/direct V0–V3 keep their default factory;
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
`saved_result_deleted`; late Save cannot recreate it. Saved deletion management belongs
to the subsequent library slice. Account deletion cascades owned domain content.

Migration `005_saved_trips.sql` completes the ten-domain-table model with `trips`,
`trip_weather`, `trip_activities`, `trip_nearby` and `trip_transfers`.
`GET /api/trips/{id}` reconstructs the public detail from normalized rows in one
repeatable-read transaction. No second saved itinerary JSON is retained. The header
holds known original request/completion metadata, server-owned origin/trust and nullable
generation completion time. All saved and preview boundaries return 404 for missing
or other-owner records and use the existing session/CSRF/origin checks.

Explicit positions retain actual day, activity, Nearby and transfer list order, including
empty days and nonchronological lists; the header span never creates missing days.
Original ISO time strings retain their offsets and fraction spelling without timestamp
round-tripping. Unknown facts/costs remain distinct from zero, free windows remain
distinct from scheduled activities, and incomplete/unassessed policy, UNKNOWN and
CONFIRMED conflict states remain visible. Weather facts and availability persist;
weather attribution and source URLs are explicitly excluded from storage, so normalized
saved reads expose those two fields as null. Nearby and transfer attribution is retained.

Nearby stores supplied anchor ID/date independently from its nullable resolved composite
foreign key. Only an exact scheduled activity ID with a compatible supplied date resolves;
orphans and free-window references remain unresolved without invented days or name guesses.
Transfer endpoints must be distinct and belong to the same trip/day. Database constraints
also enforce legal domains, nonblank IDs/titles, nonnegative positions/finite measurements
and paired cost fields. Historical detail/save does not apply current generation windows;
the separate import slice owns public import validation.

The preview page offers Save to My trips and a confirmed Discard dialog. An ambiguous
write response triggers a decision GET, never an automatic write replay; failed recovery
offers an explicit status check. Mounted preview, account, session and invalidation guards
prevent late responses from changing another brief or page. Saved results offer a user
controlled detail link. HTTP/SSE completed-task adapters read normalized saved detail when
available and otherwise expose a safe `preview_decision`, including discarded/deleted
receipts, so clearing a pending snapshot does not break completed observation.

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
(`walk`, `transit`, `drive`) add visible English sentences. Transport is a soft preference,
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

### Incomplete drafts and the collection boundary

`app.planning_drafts` stores owner, nonblank title, versioned incomplete editor JSON,
positive revision and timestamps. `POST /api/drafts` creates an independent idea;
`GET/PUT /api/drafts/{id}` resumes or revision-updates it. `PATCH` renames it,
`POST /api/drafts/{id}/copy` creates an independent copy, and revision-checked `DELETE`
removes it after browser confirmation. Missing and other-owner IDs both return 404.
Every mutation uses the account CSRF/origin boundary. No draft operation generates
an itinerary or consults profile defaults.

Snapshot validation accepts blank or generation-invalid field strings, while enforcing
`editor_version=1`, supported currency/interest/pace/transport values, unique controls,
field and collection bounds and valid Unicode. Exact span ownership uses browser
UTF-16 offsets. Stale, repeated or overlapping bindings are discarded and their controls
detached without searching for matching text; user wording remains intact.

The editor retains draft identity, last accepted revision and unsaved title within the
same account-scoped recovery record as its brief. Saving again updates that identity;
Save as new allocates another. A 409 leaves local work intact and offers explicit reload
or Save as new. Reload confirms replacement of local edits. Expiry quarantines this
record; same-account login restores it without replaying a write. Logout and account
switching clear it. Typing during a pending save is retained locally. Responses from
an earlier editor navigation cannot attach its identity or errors to a newly opened brief.

`GET /api/library` is the single server-side collection boundary. Draft cards expose
`kind=draft`, source/draft identity, minimal destination/date fields and created/updated
timestamps. Literal case-insensitive title/destination search, newest/oldest updated
ordering and case-insensitive name ordering use UUID tie-breaks. `limit` is 1–50
(default 24), `offset` is 0–10000, and search is at most 100 characters. The browser
requests pages of 12; missing fields use neutral placeholders. Saved cards join this
server-side union with `kind=saved` and server-owned source; a kind tie-break keeps
cross-table UUID collisions distinct. The browser routes saved cards to immutable saved
detail and preserves draft-only mutation controls. Complete saved management and mixed
discovery acceptance remain the subsequent library slice. Previews stay outside the library.

### Accepted application lifecycle

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

### Public examples and reusable detail

`GET /api/examples` exposes three curated cards; `GET /api/examples/{example_id}`
returns their detail. The allowlist contains `sydney-example`, `kyoto-design`,
`melbourne-design` and the additional `nearby-linking` interaction example. The bundled
fixtures come from the fixed r7 source at commit
`b30eb3814513b12d7869ca8a5c59f0b7401d45d6`. They require neither an account nor
provider/database configuration, and create no example table. Home and the guest
library link to `/examples/{example_id}`; signed-in users can also read those routes.

`backend/app/product/detail.py:ProductDetail` owns the `product_detail_1` contract,
mirrored by `frontend/src/features/product/detail/types.ts` and rendered by
`TripDetail`. It is separate from engine/research DTOs and the Developer view. Actual
ordered day/activity arrays, including empty days, are preserved. ISO date/time strings
are validated without datetime reserialization, retaining supplied precision and offsets.
Weather, costs, introductions, original request information and completion information
are optional. `request` contains only known original input; examples do not reconstruct
it from an itinerary. Provenance (`example`, `generated`, `imported`) and trust
(`source_fixture`, `generated_projection`, `unverified_import`) remain explicit.
This contract is the rendering boundary for subsequent preview, save and import slices;
those lifecycle operations are implemented separately.

The fixture adapter allowlists public fields and excludes provider identity/evidence
references. Example transfers retain supplied route metrics and source status as
`source_claim`/`source_status`, with an unverified estimate kind. They are not a fresh
route check. Trusted generated transfers can retain their final
`validation_state` (`PASS`, `CONFIRMED`, `UNKNOWN`) and provider/derived estimate kind.
For trusted generated snapshots, the connector, connections list and Details distinguish
fitting supplied timing (`PASS`), a confirmed timing conflict (`CONFIRMED`) and unverified
feasibility (`UNKNOWN` or absent). Evidence availability/type is shown separately from
timing feasibility. Example/import claims cannot acquire these trusted outcomes by
supplying a status field; their displayed source claims remain explicitly unverified.
Missing costs stay unknown, including when no total can be established. A zero amount
or zero weather metric is a known value. Place slots use labelled illustrations while
verified media integration is pending. Map queries are URL-encoded; weather source links
admit only HTTP(S), and source text is rendered as text.

Detail preserves the desktop two-column layout. Nearby references remain a flat ordered
list with their exact supplied `anchor_activity_id` and optional `associated_day`.
Resolution requires one scheduled activity with that exact ID and, when supplied, that
date. A unique exact anchor can resolve without a supplied date; names and prose never
establish links. Counts include only resolved references. Date and activity groups start
expanded, with separate disclosure and locate controls. Explicit pointer/keyboard location
expands the target day/group, focuses it and briefly highlights both surfaces; hover and
scroll do not select. Day filters apply to both surfaces. Missing, mismatched or ambiguous
anchors stay in Other nearby references with their supplied identifiers/dates; undated
unresolved references survive every filter.

At widths up to and including 800px, resolved references use an initially collapsed
disclosure inside the activity card below its actions, without a new timeline marker or
time. The resolved sidebar is hidden and Other nearby references remains available.
Breakpoint changes preserve visible focus, and reduced motion disables the pulse and
smooth location. Details use a native modal dialog with keyboard focus containment and
restoration. No favorites or saved-place collection is introduced.

The remaining saved-trip/import mechanisms are specified in #198. Confirmed acceptance uses Product APIs with real isolated PostgreSQL,
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

Product's task observation and cancellation authority are defined in the
[durable task contract](#durable-planning-tasks-and-previews). Its SSE adapter emits
persisted `task` revision snapshots and a completed `result` containing task/preview
identity plus the public detail. Navigation, disconnect and logout detach observation;
none is an explicit Stop action. The browser uses canonical reads for reconnect recovery,
without resending generation automatically.

Developer retains [request-owned stream delivery](../backend/app/api/streaming.py):
`started`, `stage`, optional `detail`, and terminal `result`, `error` or `cancelled`.
Events carry request-local `run_id`, increasing `sequence`, `type`, `elapsed_ms` and
`version`. Stage text is allowlisted; diagnostic detail is Developer-only.
[ProgressObserver](../backend/app/observability/progress.py) bounds buffering and reports
`dropped_events`. Heartbeat comments follow 15 seconds without an event. Terminal
errors cannot change the already-sent HTTP status. Disconnect cancels and awaits that
request's producer/owned transports; it does not guarantee external termination or billing.

`/dev` launches four independent streams from a copied input, locks the active form,
and retains per-run/all-stop and same-snapshot reruns. Controller/group identities fence
late results; idle edits clear the result group. Its event history is bounded and the
complete final JSON is retained separately. The shared parser handles sequences,
UTF-8/chunk framing, comments and premature EOF without automatic execution retry.
Workflow position follows observed stages, rather than elapsed-time percentage or an
arrival-time promise; stage completion is not proof that Repair succeeded.
