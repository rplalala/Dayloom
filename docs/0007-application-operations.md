# Application interfaces and engineering operation

Status: Implemented application boundary, consolidated 2026-10-03.
The accepted Product persistence design below is pending implementation; the HTTP map
describes existing endpoints.

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

PostgreSQL/pgvector currently supports retrieval. Accounts and saved itineraries are pending
under the [accepted Product persistence design](#accepted-product-persistence-design).
Per-process development limits are not account-wide billing enforcement or distributed
abuse controls; this design does not establish a public deployment guarantee.

## Accepted Product persistence design

Status: Accepted; not implemented. The detailed field definitions, relationships,
constraints and backend acceptance criteria are owned by
[#119](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/119).
Its implementation slices are accounts/JWT (#120), profiles (#121), final V3 save/detail
(#122), and history/child lists/rename/delete (#123). GitHub owns dependencies and live state.

Reuse the existing PostgreSQL instance and database. The new `app` schema coexists with
`tripworld`, preserving retrieval data and migrations. Exactly seven Product domain tables
are planned:

| Table | Responsibility |
| --- | --- |
| `app.users` | Normalized unique email, password hash and JWT `token_version` |
| `app.user_profiles` | One profile per account, created atomically with registration |
| `app.trips` | Owner, backend save key, title/destination/dates, confirmed request and public metadata snapshots, timestamps |
| `app.trip_weather` | One row per actual final Product day, including unavailable weather and empty-activity days |
| `app.trip_activities` | Ordered scheduled activities, original local datetimes and offsets, public costs and introductions |
| `app.trip_nearby` | Ordered optional unscheduled recommendations anchored to an activity on the same trip/day |
| `app.trip_transfers` | Ordered final adopted transport legs with same-trip/day endpoints and public uncertainty |

Email/password authentication uses expiring signed Bearer JWTs, with user existence and
PostgreSQL `token_version` checked on each authenticated request. Logout increments the
version and invalidates all previously issued account tokens. Redis, refresh tokens and
per-device sessions are outside this scope.

Profiles support display name, optional avatar URL, default currency, interests and
additional preferences. `preferred_pace` is a nullable single choice of `relaxed`,
`balanced` or `rich`; `preferred_transport` is a deduplicated multiselect subset of
`walk`, `transit` and `drive`, including the empty set. Future form prefill stays visible
and editable; the confirmed planning request remains authoritative without a hidden
profile overlay.

Authenticated Product generation saves only the trusted final V3 Product projection
after adoption and optional enrichment. Ordinary HTTP and SSE share one transactional
save boundary. A backend-owned save key makes repeated saves of the same result idempotent;
any child-write failure rolls back the complete new snapshot. Save failure preserves the
generated response with explicit unsaved metadata and does not trigger another generation.
Clarification, blocked outcomes, generation errors and cancellation before saving create
no trip; a disconnect after commit cannot undo a saved result. Developer, V0-V2 and
research/evaluator artifacts remain outside Product persistence.

Saved detail preserves actual day/activity/Nearby/transfer order, original datetimes and
offsets, unknown costs and public policy/transport statuses, including incomplete results
and `UNKNOWN`/`CONFIRMED` transfers. Weather stores no attribution or source URL and
does not refresh automatically. Graph state, raw provider payloads and private research
diagnostics are not saved as Product history.

Owner-scoped APIs will provide account/profile access, paginated history, complete detail,
separate weather/Nearby/transfer lists, title-only rename and cascade deletion. Missing or
other-user trip IDs return 404. Saved contents are immutable apart from title; replanning
starts from the saved confirmed request and creates a new result without changing history.

Acceptance covers backend Product APIs and migrations against a real isolated test
PostgreSQL database, with external providers/models mocked. It includes authentication,
ownership, domain constraints, HTTP/SSE save behavior, rollback/idempotency, faithful
round trips, restart persistence, cascade deletion and preservation of `tripworld`.
Frontend implementation, refactoring and tests are deferred. Migration/configuration
commands will be documented when runnable entrypoints exist; no migration or feature
test execution is implied by this accepted design.

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
the separate Product persistence boundary described above.
