# Dayloom application engineering evidence

This record summarizes consequential implementation decisions and verification from
September–November 2026. [Application operations](../../0007-application-operations.md)
owns current behavior. Mocked, isolated-database and real-provider checks below are
different scopes; earlier full runs do not validate later corrections automatically.
Local artifact paths are historical identifiers, not fresh-clone dependencies.

## Frontend and transport foundation

The original V0-backed frontend milestone completed on 11 September at `e119f6a`:
73 backend and 16 frontend tests, builds/lint and bounded Azure browser acceptance.
Later date UX adopted trusted server date-only admission. This historical checkpoint
preceded Product V3 and durable persistence.

September's Beijing Product V3 journey returned a three-day plan with real model,
place/route/weather success, introductions and Nearby. Subsequent independent V0–V3
calls all failed early: real SDK objects shared an underlying HTTP client, so cleanup
of one request closed another's transport. No quota exhaustion was established.
Explicit optional client injection isolated ownership. A real-SDK/no-network regression
reproduced the shared identity; targeted checks passed 191 after absent-keyword harness
compatibility was restored. The later offline gate passed 1,542 backend with nine skips
and 48 frontend tests; restarted V0–V3 all completed the bounded retest. Page-exit and
all Repair/retrieval branches were not covered live.

## Durable lifecycle and security corrections

The 21–23 October implementation, from review base
`26dc1455ec23b931a3245aa6d03e996e5e06db03`, delivered accounts/profiles, drafts, tasks,
previews, explicit saving, library, imports, copies and replanning under Dayloom #198.
The r7 reference was `b30eb3814513b12d7869ca8a5c59f0b7401d45d6`.

Review corrections strengthened the actual test-database name guard, owner/receipt
recovery, task fencing and late-response isolation. Browser/account recovery stopped
expired or changed-account responses from restoring private content or replaying writes.
A missing source page no longer prevented checking an earlier Copy receipt. r7 fidelity
and mobile readability were checked separately from backend correctness.

Import corrections retained exact decimals/time spelling, valid Unicode, source conflicts
and partial known requests while rejecting unsafe storage values/private authority.
Credentials accidentally echoed in test diagnostics were redacted from retained text;
no credential values are published here. Media bindings were restricted to final owned
source identities and acquired Nearby anchors, not imported claims or display names.

## Initial verification and live runtime

| Checkpoint | Result and scope |
| --- | --- |
| Initial Product acceptance | 263 API/PostgreSQL/browser tests, including 62 Chromium cases with no Product skips |
| Frontend at `74d1603` | 174 tests in 27 files, build/typecheck and lint; two Fast Refresh warnings |
| Initial full backend | 4,907 passes, seven platform skips, four failures |
| Corrections | Keyboard expectation and inherited CLI environment corrected; affected CLI checks covered 941 distinct cases across original/follow-up invocations, with six repeated platform skips |

No single all-green full invocation followed those corrections. Isolated PostgreSQL
used public migrations and substituted external transports; it was not live-provider
acceptance. Evidence includes `.scratch/r7-fidelity/` and initial Product acceptance logs.

One separately authorized Sydney one-day journey on 22 October completed generation,
preview, explicit Save and My trips reload with real model, Maps/Routes, weather,
embedding and image HTTP success. Windows startup reused the existing Selector event-loop
convention. This bounded path did not establish general provider quality, total billing,
public hosting or scale. Failed/stopped attempts and original captures stayed intact.

## Data, settings and local runtime

The unified launcher kept Product and TripWorld in one PostgreSQL database with separate
schemas. Database host/port/name/user/password and optional URL became local settings;
changing them does not migrate data or update role passwords. Personal YAML became an
ignored override of the tracked template. `DAYLOOM_DB_VOLUME` retains the existing Docker
volume identity independently of connection settings.

The loopback configuration page gained guarded redacted editing, stale-revision protection,
password/session access and explicit bounded API checks. Existing JWT signing keys are
preserved; missing local keys generate once and persist. Custom generation/input remains
available without embedding a real signing key in tracked source.

On 1–2 November, Unsplash converged on `UNSPLASH_API_KEY`; old-name reads remain compatible,
while Save/Clear removes old dotenv bindings and preserves interpolation dependents.
Implementation `8c6e23d` passed 148 targeted backend and 13 frontend tests plus build/lint.
Existing local credential value, database-volume binding and other settings were retained.

## Roles, completion and diagnostics

The 24 October Rich completion work preserved per-date states through task delivery,
Save/read and replanning; detailed Repair evidence belongs to the
[V3 record](../v0-v3/v3-development.md#rich-completion-and-density-policy-revision-2026-10-24).
On 31 October, main/supporting/free-window roles and optional atmosphere themes were
carried through the full Product lifecycle without historical role inference. Experience
highlights and unmet/unverified guidance retained source status while using travel language.

Product diagnostics separated request IDs, durable task execution and committed outcomes.
Bounded metadata preserved input-sizing/stop/completion observations despite trace truncation.
Client reports excluded text/query payloads. Storage cleanup stayed inside owned namespaces,
protected active runs and did not replace business results on failure.

Generation capacity moved to a selected Product acceptance profile with duration/pace-aware
supply and bounded deadlines, preserving independent development defaults and hard checks.
Graph/HTTP timeout controls exercised actual service boundaries; no full general-provider
reliability claim followed.

## Media behavior and validation

Local public examples were completed with historical source-bound weather/transfers and
bundled credited photographs. Opening guest examples requires no live media requests.
Owned activity/Nearby media gained paging and slot deadlines, preserving completed photos
when another slot/batch failed. Destination-aware atmosphere used structured destinations
and controlled themes rather than private prose.

Browser metadata caching retained successful URLs/credits for a fixed hour with owner,
resource and invalidation fences. Persistent preview/trip metadata later reused URLs across
sessions; versioned refresh/advisory locks prevented duplicate or stale publication.
Google confirmed photo absence alone permits bounded Unsplash fallback. Provider errors
remain errors rather than false absence. Imports never gain verified photo authority.

Responsive checks covered 1440, 800 and 390px with no page overflow. Full frontend checks
later passed 387 at two workers plus build/lint; an unrestricted run had a timeout, so
worker configuration is part of that observation. Image/attribution checks are separate
from provider licensing or public deployment approval. Google attribution confined to
Details remains a documented limitation in the current application contract.

## Latest regression corrections and limits

The 1 November full backend invocation collected 5,399 cases: 5,069 passed, 329 skipped
and one new database-settings test failed. The test inherited host `DAYLOOM_DB_*` values;
test-only environment isolation and SecretStr comparison were corrected in `8a2662c`.
A synthetic inherited-environment reproduction failed before correction and its focused
rerun passed. The prior thirteen baseline failures and four full-run/order-sensitive
failures were addressed and their seventeen targeted checks passed. The full suite was
not repeated at the user's request. Redacted local evidence is under
`.scratch/runtime-config-20261101/`.

Reviews and targeted passes do not replace that invocation's recorded failure/skips.
No comprehensive all-branch live test, production scaling assessment or provider invoice
is established. Native research outputs and V0–V3 entrypoints retain their own evidence
and behavior. Current user instructions belong to the guides, not this history.
