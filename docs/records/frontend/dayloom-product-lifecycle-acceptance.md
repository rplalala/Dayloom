# Dayloom Product lifecycle acceptance

Lifecycle validation uses isolated PostgreSQL and Chromium with controlled external
adapters. A separately authorized one-use check also validates the complete local
runtime against real providers; the two scopes remain distinct below.

## Event and scope

Engineering implementation and acceptance on 2026-10-21–23 (Australia/Sydney), originating in [Dayloom #198](https://github.com/rplalala/Dayloom/issues/198) and its thirteen native children. The fixed implementation/review base is `26dc1455ec23b931a3245aa6d03e996e5e06db03`; the visual and interaction reference is [r7 at b30eb381](https://github.com/rplalala/Dayloom/tree/b30eb3814513b12d7869ca8a5c59f0b7401d45d6/r7). Existing main-worktree changes to `.env.example` and `GLOSSARY.md` were excluded from task commits. The current contract belongs in [application operations](../../0007-application-operations.md), rather than this dated record.

The event covers the durable account/profile, brief/draft, task, preview, manual Save/Discard, mixed library, import/export, copy/replan and media lifecycle. The browser-local prototype remains a simulation.

## Consequential failures and corrections

### Durable ownership and recoverable operations

Independent review exposed a test-database guard that trusted a `test` substring in a connection query instead of the actual database name. The correction validates the parsed database identity before destructive test setup. Real PostgreSQL acceptance subsequently exercised the corrected guard and public migrations.

Task review identified recovery paths that could overwrite a valid lease, a PostgreSQL owner/task/preview foreign-key lock deadlock, and Decimal context rounding that could collapse different request fingerprints. Separate correction commits introduced row-locked recovery, compatible owner locks and exact tuple-based fingerprints. The browser also reproduced a deferred preflight from an old brief creating or rebinding a later intent. Session, navigation, editor and attempt fences now prevent that stale write without cancelling an already accepted account-owned task.

Preview decisions and saved snapshots are transactional. Actual concurrency, application recreation and public deletion tests established that replay returns the original saved/discarded/deleted receipt, while a late Save cannot resurrect a deleted result. Import deletion acceptance includes three concurrent same-key requests after application recreation and an explicitly new key creating a separate preview and saved trip.

### Authentication, editing and presentation boundaries

Expired-cookie and held-auth-refresh browser tests exposed private profile/library/preview content remaining visible or old recovery callbacks adopting a new browser session. The corrections quarantine private content immediately and restore the same owner's intended state only through explicit recovery. They do not replay a generation/import/Save write on login. A draft Save response arriving after opening another draft also previously changed the active identity; operation and navigation fences preserve the new draft.

The mixed-library review found a partial r7 implementation at intermediate widths. The correction retains the compact toolbar above 560px and restores the card Manage dialog, including focus, keyboard, Escape and backdrop behavior. Visual verification rejected an initial scroll explanation for a blank viewport: the task-notice wrapper inherited a full-page minimum height. An actual browser regression failed with header y=1000 and passed at y=0 after the scoped layout correction. The integrated gate later exposed a stale keyboard expectation after Copy became available for saved trips. An actual DOM/focus probe established Rename → Copy → Delete; the test now explicitly checks Copy for both card kinds while retaining Delete, Escape, backdrop and focus-restoration assertions. All four library browser cases passed; production behavior was unchanged.

Replan review exposed a cross-feature mismatch: an unknown original currency correctly stayed blank, but the existing draft schema rejected that incomplete state. Actual Save draft returned 422. The editor-only correction permits blank currency to persist and reopen after a profile update; generation still rejects it with a located error and performs no execution. Related actual API/PG/browser checks passed 29 tests. Both hero and secondary saved-detail actions use the same original-request mapping.

### Historical import and storage admission

Initial review found malformed source metadata raising exceptions, a deferred file read overwriting another accepted import, blocking synchronous database work on the async event loop, and valid zero/overlap connection gaps being rejected. Separate corrections return located errors, fence file ownership, offload blocking work, and preserve historical conflict gaps independently of positive actual activity/transfer durations. Explicit exported provenance remains a source claim on reimport; it never restores ownership or verified media authority.

Additional actual API/PostgreSQL red tests confirmed NUL text produced 503, while an extreme activity cost imported successfully but failed Save with the preview still pending and no saved trip. Located admission now rejects invalid text/keys and amounts outside PostgreSQL's actual numeric domain before creating a receipt. Exact tuple arithmetic preserves significant digits and only removes unnecessary excess scale; large original-request budgets remain JSON strings. The final storage regression passed 19 tests with no skips. A contention test proved health and a real pending-task Stop remain responsive while an import waits on an owner lock; it does not establish a separate running-heartbeat result.

A subsequent integration probe found JSON numeric exponents beyond Decimal's representable exponent range escaping the parser's exception boundary. Actual HTTP/PG red established 500 with no receipt for both signs. The separate parse-only correction now returns root-located 422. Its final 27-case import/storage/receipt set preserves exact representable large/small request budgets, without imposing a new magnitude cap or changing activity storage admission.

### Credential-bearing test diagnostics

A failed early browser fixture inherited the host environment, and pytest's failure representation exposed real AWS credential values. The corrected harness admits a strict subprocess environment and opaque metadata; connection strings use `SecretStr`, with failure-frame regression tests. Four affected temporary raw logs were replaced by verified sanitized copies and removed locally. Subsequent bounded scans of committed diffs and retained text artifacts found no matching current credential values. This local cleanup cannot revoke content already emitted in an earlier tool transcript, and is not evidence of credential rotation or global erasure. No credential values belong in this record.

During deployment consolidation on 23 October 2026 (`00fb103` plus an uncommitted
launcher regression), a new Compose launcher fixture repeated this failure pattern by returning inherited environment values as a
pytest fixture argument. Its intentional red diagnostic exposed host AWS credentials
in the tool transcript. Separate correction `c99330c` restricts the fixture to explicit
OS/tool paths and verifies an actual child-pytest failure with a synthetic credential.
The final 32-case launcher/database/Product configuration set passed. A bounded scan
found no exact current host credential values in retained task text artifacts under
`.scratch/deployment-config/`; private backups were excluded. The user was informed
and advised to rotate the affected AWS access key. Rotation was not performed, and
the prior output cannot be revoked by this source or artifact correction.

The first broad media run passed 304 tests and failed 28 because its pytest host lacked complete isolated Product settings; browser children already had them. After correcting the host environment, those 28 passed without source changes. Raw Pydantic input representations contained dotenv configuration fragments. A designated sanitized log removes 56 input-value lines while preserving the failure counts, trace and cause; the raw diagnostic is excluded from the retained archive. A fake-sentinel red/green test now verifies Product settings suppress input representations. Exact complete-value scans do not prove absence of truncated fragments in the original output.

The integrated backend gate enabled real TripWorld database acceptance in a separate disposable database. Two installed offline V1/V2 CLI tests inherited that pytest host's database environment; the unchanged credential guard then rejected `RawCapture` enumerating environment variables for redaction. The original guard event files and a minimal fake-sentinel-only contrast both recorded the same forbidden password-name read. A stack-only diagnostic identified environment enumeration rather than settings bootstrap, real retrieval or a missing provider substitute. Explicit fake-host-password regressions reproduced both failures; strict OS/tool/TEMP admission for the test subprocess made both pass. Production redaction, the zero-read/network/import guards and the 60-second subprocess timeout remain unchanged.

A host pause/clock discontinuity inflated one diagnostic's wall duration to over two hours and produced a subprocess timeout. That duration does not measure ordinary CLI performance. Original outputs are retained separately from causal probes and any justified retest; neither raising the timeout nor removing guards is an accepted correction.

The broader fixture-consumer check exposed a separate Windows path-length problem in its runner's long scratch basetemp. Raw-response writes failed, causing interruption-capture and downstream native suite checks to stop before their expected outcomes. Two exact long-path red/short-path green controls held environment, code and assertions constant. The final affected-node retest changed only basetemp to a shorter directory inside the same worktree. All 63 actual failure nodes then passed; the original non-green invocation remains part of the evidence.

### Media authority and readable attribution

At initial lifecycle acceptance, private media bindings originated in final adopted Google identities and the strict final Nearby association ledger. Generated preview Save carried them into the owned normalized snapshot; the original prototype examples had no bindings. Imports and exported text cannot confer that authority. Fresh public migration applied six files, reran zero, rejected a changed checksum and preserved ten domain tables and the seeded TripWorld marker. Integration upgrade applied only 006 and reran zero with all six checksums verified.

Initial Spec review found that legacy Nearby thumbnail dimensions constrained the new whole image figure. Although presence checks passed, full author/source captions overflowed the desktop row and clipped on mobile. Real V3/API/PostgreSQL/Chromium geometry failed at 1440, 800 and 390px. The separate correction retains thumbnail and Details side by side, with full-width credits below both in normal flow. Actual geometry, clipping-ancestor and keyboard regressions passed; final related backend/API/PG/browser checks passed 41 tests with zero skips, and affected frontend checks passed 26. Both final review axes were clear at `4c09a8acf80092c909609ffbea9eb16b7e0fd6cf`. No provider request, binding schema or production header change was needed for the layout correction.

### Copy recovery across sources

Core review identified three recovery defects: a single storage slot discarded unresolved source A when source B was copied; deletion of A prevented its recovery controls from mounting; and accepted printable operation keys containing a slash could not be addressed through a path segment. Actual API/PostgreSQL red additionally confirmed control-character keys caused Copy/Import/task lookup failures. The separate correction keeps normal legacy paths and the import header, adds query-based recovery for printable slash keys, validates storable keys before persistence, and retains the existing task character domain. Browser recovery now keeps independent owner/kind/source intents and exposes status-only recovery without requiring source content; only explicit intent can submit a new copy.

The first five-failure recovery browser invocation reached two product failures; three other cases stopped in seeding at `KeyError: csrf_token`. It is not evidence that all five product assertions ran. After setup and behavior corrections, all 15 Copy browser cases passed, including actual source/result deletion, cross-source recovery and same-account relogin without extra POST. Following the accepted media merge, final bounded checks passed 104 API/public-migration/constraint/compatibility tests, 17 Copy/media browser cases and 28 affected frontend tests. Private bindings survived Copy/copy-of-copy and source deletion while staying absent from receipts, imports and downloaded JSON. These bounded stage checks preceded the integrated regression below.

### r7 fidelity correction

User inspection on 2026-10-22 rejected the delivered presentation as substantially different from r7. The initial lifecycle gate established functional behavior, not complete visual fidelity. Correction began at `8f7095705fb4decd9a5f2cd956d5016868efccbf`, after the Dayloom browser title and actual-clock calendar correction. The pinned r7 HTML SHA-256 is `7b69c4bf0d93e56e2b3fc5bbd1914f2e9696d21fded8c877c4f4a326932e09aa`.

The implementation had omitted `prototype.css` and `nearby.css`, retained competing component styles, and admitted legacy global styles into Product. The correction restores all four original layers in order, with Product selector and keyframe scoping, and excludes Product from legacy styles without redesigning Developer. Home, Plan, Library, Detail, Auth and Account now use the source hierarchy, icons, illustrations, controls and responsive rules. Native dialogs restore the source menu structure, close controls, Escape/backdrop behavior and focus restoration. Draft cards open a read-only detail page before an explicit Continue planning; reading a draft cannot replace the active brief. Normal naming stays in Library Rename. Review contains the source facts, with a read-only notice only for a different recovered historical name.

Preserving real behavior required more than replacing styles. Browser acceptance exposed a logout error lost when the profile form unmounted, and a missing explicit media refresh action. The former now belongs to the account page with session/attempt fences; the latter is available inside the existing source-information disclosure. Export success shows the source toast, while clipboard failure alone exposes the selectable summary. Auth panes retain independent values and visibility, and Account previews edited initials without saving.

The first broad correction diagnostic failed 105 of 263 cases. It exposed both obsolete UI expectations and actual storage compatibility defects: newly projected display hints were incorrectly sent to SQL columns, and neutral optional fields changed historical import fingerprints. Commit `e1bc6e8` persists allowlisted hints separately through migration 007, omits absent hints from serialization and preserves original receipt fingerprints. The focused actual-PostgreSQL compatibility set then passed 83 tests. Later browser diagnostics also failed while obsolete selectors and the logout/media defects were being corrected; those invocations are not all-green evidence.

Display hints cannot create request facts, verified place identity or media authority. The public migration entrypoint applied 007 once and reran zero on the retained manual database. The Pydantic minimum is 2.12 because the DTOs use `exclude_if`; all 73 locked package versions remain unchanged. Actual dates, the fourteen-date window, ten-day trip limit and approved initials-only avatar release remain in force. Prototype simulation notices are replaced by truthful Product wording.

Independent review identified a missing completed-but-unviewed task entry, omission
of the new draft detail route from the authentication return allowlist, and a lost
no-wrap rule for Google Maps attribution. Paired-page inspection also found that
detail/import route aliases lost the source My trips navigation selection. The
correction separates viewing a result
from observing/dismissing its notification and retains the strict UUID return boundary.
An offline Chromium negative case measured the provider label on two lines at 800px;
restoring no-wrap alone still overflowed its caption by 3.375px. Narrow runtime caption
padding then kept the full 12px label inside its figure without changing photo dimensions
or crop. Author names continue to wrap. The same correction consolidates the duplicated
mood mapping and native-dialog backdrop predicate while leaving close/busy policies local.

### Complete guest examples and compact planning

The 23–24 October 2026 refinement in [#212](https://github.com/rplalala/Dayloom/issues/212),
[#213](https://github.com/rplalala/Dayloom/issues/213) and
[#214](https://github.com/rplalala/Dayloom/issues/214) starts from `d1aa66a`.
The two original accepted Sydney/London V3 outputs were projected through the normal
Product boundary, with source digests retained in the bundled server fixtures.
Original primary visits, request facts, dates, weather and transfer outcomes were
preserved. Actual photo inspection found the London Metaverse optional reference had
no provider photo; Jubilee Gardens from the same run's acquired Nearby ledger replaced
it under the same London Eye anchor. This was editorial selection of an optional
reference, with no new planning or research run.

A failing copy round-trip assertion exposed deliberate omission of weather attribution
and source URLs from normalized storage. Nullable migration 008 and the shared writer
now preserve them, alongside copied private photo bindings. API/storage checks then
passed for copies, descendants, source deletion and recreated applications. The old
ambiguous-anchor example moved to a test-only fixture, keeping keyboard/breakpoint
coverage without exposing a third guest itinerary.

Manual checks used the normal built Product application on an isolated local database.
Both city covers and all nine bound place photos per example loaded; normal example
views contained no missing weather/route placeholders. Computed muted-text contrast
was 4.87:1–5.51:1 on the common light surfaces. At a 390px viewport, the compact
planning page placed Generate at approximately y=708px, with optional preferences
collapsed and no empty progress/result panels. Detail checks also covered 800px and
1440px, keyboard navigation and horizontal overflow. Local screenshots under
`.scratch/product-polish/` are historical evidence identifiers, not published assets.
Media availability remains dependent on configured providers; these observations do
not establish future image availability or current travel conditions.

Implementation commits `410f784` and `2eee32b` passed the full 255-test frontend suite,
119 related backend/API/storage tests, TypeScript/Vite build and lint (zero errors;
two existing Fast Refresh warnings). The affected browser run passed 43 of 47 cases;
the four failures expected the former third card or old sample notice. Updating those
expectations produced a 13-pass focused run covering all four failures, two public
example browser cases and seven API/copy cases. Thus all 49 affected browser cases
passed across the scoped runs. A final fixture/frontend retest passed 24 tests.
Initial browser setup also encountered occupied loopback ports; using alternate
test-only ports resolved it without changing application configuration. Automated
external transports remained substituted, while the manual image check used real
display providers and submitted no planning task.
Independent Standards and Spec reviews of `d1aa66a...2eee32b` each returned zero
findings. Existing `.env.example` and `GLOSSARY.md` work remained excluded; delivery
at this event is local commits, not a published deployment.

## Verification and evidence

### Published Product integration

Delivery on 23 October 2026 is tracked by [PR #210](https://github.com/rplalala/Dayloom/pull/210)
and [#208](https://github.com/rplalala/Dayloom/issues/208). Its fixed published-main base
is `ed1a51329f02c32dd25f6b012e4d91d91e99f747`; accepted local source `f91226c`
contains 97 outgoing Product/runtime commits. Separate test corrections `aee24ec`
and `9856f50` retain the implementation history. The delivery includes the shared
non-secret `product.yaml` source and Compose launcher; current configuration ownership
is defined in the [development guide](../../guides/development.md#complete-local-product-runtime).

The complete backend invocation ran **4,963 cases: 4,944 passed, 12 failed and 7 skipped in
2,765.68 seconds** with actual isolated
PostgreSQL, public migrations and Chromium enabled. The fresh delivery worktree initially lacked
its ignored offline tokenizer vocabularies. After restoring both verified local caches without
downloads, the exact 12-node follow-up passed nine and failed three editor cases. Those cases
depended on a transient start notification that the fixture's immediate failure can replace;
test-only correction `9856f50` verifies HTTP 202 task acceptance and the Plan progress area
instead. All three then passed, establishing 4,956 distinct passed backend cases across the full
run and precise follow-ups. The seven skips cover two unavailable Windows symlink privileges and
five alternate-volume cases without a configured writable second volume. Three warnings remain:
one Starlette/AnyIO deprecation and two Windows subprocess UTF-8 reader warnings in an otherwise
passed census-export case.
The exact original failure-node set equals the first follow-up's collection; its
remaining failure-node set equals the final follow-up's collection. No all-green
single whole-backend invocation is claimed.

The full frontend initially passed 251 tests and failed one authentication-return
assertion because routing preceded React's DOM commit. Correction `aee24ec` waits
for the visible destination heading; the complete rerun passed **252 tests in 41 files**.
TypeScript production build and lint passed with two existing Fast Refresh warnings
and the existing 514.39 kB bundle-size advisory. All 107 changed Python files and the
later editor-test delta passed Ruff. No mypy/pyright project configuration exists.

Independent Standards and Spec reviews covered the combined fixed-base change.
Standards identified one P2 stale architecture-status paragraph; the in-place
correction was rechecked. Both axes reported zero remaining findings, including the
test-only corrections. Five pre-existing development-toolchain dependency audit
findings are tracked by [#209](https://github.com/rplalala/Dayloom/issues/209); the
frontend lockfile is unchanged from published main and the production dependency
audit reports zero findings. Current-credential exact scans of outgoing history
found zero matches. This is a bounded scan, not a global secret-erasure claim.

Local evidence identifiers under the delivery worktree's `.scratch/delivery/` are
`product-20261023-152214.{log,xml}`, `followup-20261023-154451.{log,xml}`,
`followup-20261023-155218.{log,xml}`, `validation-summary.json`,
`frontend-tests-final.log`, `frontend-build.log`, `frontend-lint.log`, `ruff.log`
and the two review reports. The original parent log/XML remain intact; browser
module scratch paths were reused by follow-ups, so they are not claimed as a complete
archive of every initial screenshot. Main-worktree readiness passed without provider
calls. Public hosting, new live checks, benchmark execution and AWS changes are
outside this delivery.

### Unified local database and configuration

On 23 October 2026 (Australia/Sydney), configuration consolidation started at
`c1200b38a9e4ba63d8564d8d29422af68b7ae556`. Implementation `32e5537` and separate
compatibility correction `abb8a28` unify Product, retrieval and maintenance connections
under `DAYLOOM_DB_*`, merge the ignored environment files into root `.env`, and share
`GOOGLE_MAPS_API_KEY` between planning and Product photos. Root `product.yaml` remains
separate from planning policy. Existing unrelated environment values, passwords,
signing credentials, the sample's Unsplash addition and `GLOSSARY.md` edits were preserved.

The actual local migration renamed `tripworld`/`tripworld_test` to
`dayloom`/`dayloom_test` and the login role to `dayloom`. Before-and-after checks
preserved database, schema, role and table identities, ownership and all 21 table
content fingerprints: sixteen runtime tables and five retained test tables. The
runtime retains 647,057 entities and 577,011 vectors. Compose still mounts the same
`reliable-tripworld_tripworld_pgdata` volume, now declared external. Full custom-format
database backups, a role snapshot and original environment files were retained locally
before the rename; they contain private data and are excluded from tracked evidence.

Post-migration readiness exposed pgvector in the retained `tripworld` schema while
PostgreSQL's default `$user` search path now resolved the renamed role. An isolated
regression reproduced the missing-vector-type error. The shared connection policy
now explicitly searches `tripworld,public`, without moving the extension or rebuilding
the corpus. The regression fixture also needed the existing embedding-space record
before its search assertion could run. The final 59-case configuration, real PostgreSQL
and retrieval set passed, covering extensions in both supported schemas. Public Product
migrations reran with zero changes; local readiness and HTTP health/home checks passed.

The full backend invocation ran 4,952 cases: 4,879 passed, 71 skipped and two failed.
The failures were CLI fixtures intentionally loading synthetic dotenv files while the
isolated runner disabled dotenv loading. Scoped fixture corrections were followed by
all fifteen tests in that file passing; this is not a single all-green full-suite run.
The gate reported three warnings, including Windows subprocess decoding warnings.
Nineteen affected packet/API cases and six actual Chromium account/media journeys
also passed with external services substituted. Standards and Spec reviews were clear
for the implementation and correction. These checks preserve independent V0–V3 entry
points and do not repeat the earlier authorized real-provider journey.

Credential-free fingerprints and original validation outputs are identified locally
under `.scratch/dayloom-db-unification/` by `before-migration.json`,
`after-migration.json`, `runtime-final.json`, `validation-summary.json` and the two
review reports. They are evidence identifiers, not published dependencies. The normal
built frontend and FastAPI runtime were restored together at `http://localhost:5173`.

### Final local Product acceptance

On 23 October 2026 (Australia/Sydney), the user explicitly accepted the complete local
Product at `b40fcfa55f919a570fbfcec10bde110ac7029a89`. The confirmation follows the final
photo-layout implementation `3a107dba85596b7822c1be14c85338a67454d9f4`: square Nearby
thumbnails, top-aligned landscape activity photos and responsive mobile crops. Direct
photographs and the selected Details-only attribution presentation remain governed by
the [current media contract](../../0007-application-operations.md#verified-place-media-and-curated-atmosphere).

Before that confirmation, the final layout checks passed 252 frontend tests, the
production build, changed-test Ruff checks and both isolated PostgreSQL/Chromium media
journeys. A long-description browser regression first reproduced the 58×67px Nearby
thumbnail and an activity photo displaced 34.1875px below its text. The correction
passed at 1440, 800 and 390px, with cover cropping, aligned content and no page overflow.
Independent Standards and Spec reviews found no remaining issues. These are the
actual focused follow-up results, not a new complete backend or real-service run.
Local evidence identifiers are under `.scratch/photo-layout/`: `frontend.log`,
`product-20261023-085547.{log,xml}`, the responsive `browser/layout-*.{json,png}` files,
and the two review reports.

The accepted runtime serves the built frontend and normal API at `http://localhost:5173`.
Its Docker Compose project/container are `dayloom`/`postgres` on port 55432. Renaming
retained the original physical volume, database identity, all sixteen table counts and
Product content hashes; automated test databases are stopped. The existing `.env.example`
and `GLOSSARY.md` edits remain uncommitted and excluded. A read-only post-acceptance
HTTP check returned 200 and matched the current frontend build. The user's confirmation
records local Product acceptance. Code delivery is tracked by
[PR #210](https://github.com/rplalala/Dayloom/pull/210) and
[#208](https://github.com/rplalala/Dayloom/issues/208); public hosting and version-level
research freezes remain separate decisions.

### Complete local runtime and bounded real-service acceptance

On 22 October 2026, implementation `21ad0bc` and startup documentation `a93b547`
added delivery of the built r7 frontend and normal API on one local origin. The
normal provider factories replace the substituted walkthrough entrypoint; `.env`
and `.env.tripworld` retain their existing values. The existing Unsplash key alias
now works, with the dedicated Product
key taking precedence. No frontend or independent planner policy changed.

At frozen revision `a93b547ab239ab66a61ec759a84229e865f26d21`, 107 related
API/Product/media/retrieval cases passed, as did the frontend production build and
changed-file Ruff checks. Both independent review axes reported zero findings.
The daily database applied migration 007 through the public entrypoint and reran
with zero changes. Read-only readiness verified both tokenizer vocabularies and
TripWorld corpus/embedding-space compatibility. A preliminary built-runtime browser
check passed actual registration, durable draft/reload, My trips and Developer access
at 1440, 800 and 390px while explicitly blocking provider-triggering requests.

The user then authorized exactly one real-service journey: Sydney on 24 October 2026,
one day, two travelers and AUD 1000, with no additional preferences. The allowance
was twelve minutes, existing configured call/token limits, no new dollar hard cap and
no second generation after failure. A one-use command checked frozen source/configuration
hashes before execution. Existing `.env.example` and `GLOSSARY.md` edits stayed excluded.

The real browser run passed in **80.88 seconds**, with exactly one generation POST,
task completion, preview, explicit Save and My trips reload. Its generated snapshot
contained two activities, one provider-confirmed Google Routes connection (812m,
701 seconds, PASS), Open-Meteo weather for the day and complete minimum daily coverage.
Five owned Google photo slots returned available metadata. Screenshots at all three
widths showed real images/credits without horizontal overflow; no browser page error
or external-browser denial was recorded. One curated HTTP-200 response body was not
captured by the asynchronous observer; other curated metadata and the displayed hero
image were available. This capture gap is not evidence of a provider failure or a
complete per-response body ledger.

Sanitized existing runtime HTTP metadata recorded successful responses from the model
(4), Google Places (51), Google Routes (19), Open-Meteo (1), query embeddings (1) and
Unsplash (5). These observations supplement the public projection but are not a complete
SDK request, SQL execution, token-usage or billing ledger. No zero-cost claim or general
retrieval/provider-quality conclusion follows. This single journey does not establish
all destinations, dates, failure modes, concurrency or scale; it does not refresh the benchmark.

Local evidence identifiers under `.scratch/product-final/` are
`product-20261022-154812.{log,xml}`, `runtime-browser.json`, `live-freeze.json`,
`live-execution.log`, `live-result.json`, `live-detail.json`, `live-http-metadata.json`
and `live-preview-{1440,800,390}.png`. They identify retained local evidence, not
published dependencies. No push, PR or deployment occurred.

### Initial lifecycle delivery

The initial production-code checkpoint is `74d1603b946dc393e46e5121b2986e31724a7d4c`.
The final test-only corrections are `2fcff169c265dfbbac8587a4d5218676dba7a4fd`
(library keyboard navigation) and `e2c19925c97253705f8c2d43e0dd63bfe5c6886a`
(installed CLI environment admission). No application, frontend, launcher, tool or
dependency-lock content changed between that checkpoint and the initial delivery. The Product gate
ran on a clean `2fcff169` tree. CLI tests ran with only the two test-file edits later
committed as `e2c19925`; the handoff verifies their normalized bytes match that commit.

| Actual check | Result and interpretation |
| --- | --- |
| Complete backend at `74d1603` | 4,918 cases: 4,907 passed, seven skipped and four failed. The failures were the stale Copy keyboard expectation, two inherited-password guard failures and the paused population CLI timeout. Nine opted-in real TripWorld database cases passed. |
| Complete Product after the keyboard correction | 263 passed, zero skipped; includes 62 real Chromium cases across all eleven browser modules. Pytest took 658.53 seconds; runner elapsed 661.24 seconds. |
| All 27 installed-CLI fixture consumer files | First invocation: 878 passed, 63 failed, six skipped in 1,313.19 seconds. The overlong scratch basetemp affected native raw-response and downstream suite evidence. |
| Exact CLI failure-node follow-up | The same 63 failed node IDs all passed with only a shorter worktree-local basetemp, zero skips, in 341.50 seconds. The two runs establish 941 distinct passed CLI cases, not one all-green 947-case invocation. |
| Previously paused population `schema_ref` case | Passed in the complete remapped whole-host environment in the original 947-case invocation, 0.390 seconds; its earlier JUnit time was 8,153.345 seconds with a 60-second subprocess timeout. |
| Complete frontend | 174 tests in 27 files passed at `74d1603`; build/typecheck and lint passed. Two Fast Refresh warnings introduced with the account shell remained. Frontend source did not change again before initial delivery. |
| Final static boundary | All 80 changed Python files passed Ruff at `e2c19925`; full-base diff checks passed. V0–V3, API and installed RTPEval help checks passed without Product configuration at the unchanged production checkpoint. |
| Public migration entrypoint | Fresh six-file application, zero-change rerun and checksum rejection were exercised in the media slice. Final integration at `e2c19925` applied zero and reran zero, verifying all six checksums, ten domain tables and the unchanged TripWorld sentinel after each run. |

All four original failures passed their affected follow-up checks. The initial
whole-backend result remains non-green; no single all-green whole-backend rerun
is claimed. The seven original skips are two unavailable Windows symlink-privilege
cases and five unconfigured alternate-volume cases. Six of those appear in the CLI
impact collection; they are not additional distinct skips. Product/browser and real
TripWorld database acceptance were actually enabled rather than skipped by opt-out.

Independent whole-source Standards and Spec reviews covered all 54 ordered commits
from the fixed base through `74d1603`, with zero remaining findings on each axis.
The separately committed library and CLI test corrections also received both review
axes with zero findings. Final documentation delta review and local delivery completion
are recorded with the originating Issue; this runtime evidence does not infer them.

### r7 correction validation

The correction implementation is `e1bc6e8` followed by `3a04a18`; independent review
and paired-page corrections are separately committed as `0d7a9fc`. The broad
gate ran with `3a04a18`'s application/frontend bytes and the browser selector before
its final test-only correction. That gate passed 291 of 292 cases in 720.53 seconds.
Its sole failure was an unscoped View details locator matching both the saved trip
and the newly restored draft detail link. Scoping it to the saved-trip card changed
no application behavior; the exact failed case then passed in 26.60 seconds.
Together these establish 292 distinct passed cases, including 63 actual Chromium
cases across eleven browser modules and 24 Product HTTP/API cases. The separate
four browser-harness security cases are not counted as Chromium journeys. No
single all-green 292-case invocation or new whole-backend run is claimed.

The affected Task, Draft, Media, Library and Import browser follow-up then passed
28 of 29 cases in 285.48 seconds. Its only failure was a previous test expecting
to dismiss the notification after it had already opened the preview. The reviewed
view-acknowledgement behavior had correctly cleared it. The assertion now verifies
that both notification and ready entry stay absent after returning to Library;
the same case's original keyboard/menu/geometry assertions remain. This exact case
passed in 36.51 seconds after the test-only correction. Narrow navigation-class/ARIA
changes made after the 29-case gate were independently checked in 21 offline browser assertions
across three widths and seven routes, with no writes. Backend-test formatting changes
passed Ruff and did not change expressions or assertions.

| Actual check | Result and interpretation |
| --- | --- |
| Complete frontend | 207 tests in 37 files passed before formal review; the final corrected source passed 225 in 38 files. Typecheck/build passed. Lint reported zero errors and the two existing session Fast Refresh warnings. The final 512.27 kB minified JavaScript bundle triggers Vite's 500 kB advisory; its threshold was not raised. |
| Fixed CSS comparison | All four layers' selectors, declarations, media rules and keyframes match the pinned source after the documented scoping adaptations. Original local SVG illustration bytes remain unchanged. |
| Responsive page comparison | Thirty reference/current captures at 1440, 800 and 390px show no horizontal overflow. Home, initial Plan and Login match every collected rectangle, font/color metric and total height at all three widths. Library and itinerary detail retain real record counts and honest source text, so their total heights are not asserted equal to different fixture content. |
| Matched draft and dialogs | Draft detail's seven measured sections match source rectangles at all three widths. Offline matched-state browser checks cover activity/Nearby/route dialog geometry and source photo sizing; Auth, profile preview, Review, clipboard outcomes and About close/focus behavior also pass at every width. Mock-response comparison is distinct from the actual API/PostgreSQL journeys above. |
| Manual date persistence | Actual API/PostgreSQL/browser acceptance generated 23–24 October and 3–4 November journeys, then saved and reloaded each. The observed window was 22 October–4 November 2026 with a ten-day trip maximum; no external browser request or page error was recorded. |
| Public migration and static checks | The manual database applied migration 007 once and reran zero through `scripts/migrate_product.py`. Product regression includes fresh migration/checksum and legacy import receipt tests. Changed Python files passed Ruff; staged diff checks and the offline 73-package lock check passed. |

Independent rechecks at `0d7a9fc` closed all three Standards findings (one contract
violation and two duplication heuristics) and all three Spec findings. Each axis
reported zero remaining findings; the Spec delta identified no scope expansion.

The correction evidence is retained under the main worktree's ignored
`.scratch/r7-fidelity/`: `product-20261022-105539.{log,xml,json}` is the broad
non-green run, and `product-20261022-110805.{log,xml,json}` is its exact failed-node
follow-up. `draft-final-frontend.log`, `draft-detail-build.log`,
`draft-final-lint.log`, `accepted-v2/`, `css-layer-equality.json`,
`draft-detail-captures/`, `final-shell-browser.json`, `dialog-comparison/`,
`calendar-verification.json` and `manual-migration.log` identify the other checks.
`product-20261022-112030.{log,xml,json}` and
`product-20261022-112659.{log,xml,json}` identify the affected browser gate and
exact Library follow-up. `review-fixes/` retains the failing and passing behavioral
and geometry checks, final frontend/build/lint outputs and navigation/dialog proof.
Diagnostic `before` captures were taken while CSS isolation had already begun;
they do not establish an exact fixed-base render. Intermediate captures labelled
`final` are not substituted for the later `accepted-v2` page captures.

The later Plan consolidation on 22 October uses review base `e7a97e0`, implementation
`337e7d7` and separate correction `980b738`. Progress, Stop and recovery now occupy the
existing r7 Plan sections and header entry; the separate task page is removed. The
immutable submitted trip remains separate from a different edited brief. Spec review
caught an acknowledgement incorrectly following the active task when another preview
was viewed. A failing route-level regression reproduced it; the correction acknowledges
the displayed preview's source task. Standards and Spec rechecks each found zero
remaining issues.

That consolidation passed 238 frontend tests in 40 files, production build/typecheck
and lint with the existing two Fast Refresh warnings and bundle-size advisory. The
three affected API/PostgreSQL/browser modules ran 18 cases: 17 passed initially; one
asserted resource cleanup immediately after releasing a controlled model. Waiting for
completion corrected its timing, and that exact case passed its follow-up. This is not
a single all-green whole-module rerun. The public migration entrypoint applied zero
changes. A separate real manual-API/PostgreSQL journey exercised two explicit generations,
one-active-task conflict, Stop, saving brief B before restoring A, completion and older
preview selection within Plan, explicit Save and persisted reload. Captures at 1440,
800 and 390px showed no horizontal overflow; external requests and browser page errors
were both zero. Main-worktree evidence is retained in `.scratch/plan-integration/`:
`frontend-final.log`, `review-{red,green,build,lint}.log`, `browser.json`, the responsive
captures, `product-20261022-123954.{log,xml}` and its exact failed-case follow-up
`product-20261022-124335.{log,xml}`. The existing unrelated environment-example and
glossary changes remained excluded.

The failure-notification follow-up on 22 October uses review base `a069838`,
implementation `5e4df65` and separate correction `07b5576`. Off-page failures previously
lost their header entry and produced no notification. The follow-up retains recovery
through dismissal, viewing and refresh while preserving a different edited brief.
Spec review then reproduced an older completion toast replacing the latest failure
on a later poll. A failing mixed-history regression established the problem, and the
correction gives the current failure priority while retaining older previews. Both
review axes found zero remaining issues after correction.

The follow-up passed 246 frontend tests in 41 files, build/typecheck and lint with
the existing advisories. Five actual API/PostgreSQL/Chromium cases passed for clarification,
safety/provider blocks, ordinary failure and interruption. They exercised notification
on My trips, refresh, entry navigation to the exact Plan task, retained editor B,
explicit restoration and no repeat generation. The public migration entrypoint ran
successfully. Separate read-only viewport checks at 320, 390, 800 and 1440px confirmed
readable header labels without truncation or horizontal overflow; recorded external
requests and writes were zero. Evidence identifiers under `.scratch/failure-notice/`
are `frontend-final.log`, `priority-{red,green}.log`, `review-{build,lint}.log`,
`product-20261022-130352.{log,xml}`, `visual.json` and `responsive-*.png`. The unchanged
`.env.example` and `GLOSSARY.md` work remained excluded from commits.

Local evidence paths are historical identifiers, not published dependencies. The integration worktree's ignored `.scratch/final-backend-initial/` retains hash-verified original whole-run log/XML/result files. `.scratch/final-product*`, `final-frontend*`, `final-static*` and `final-delta-static*` identify the later root gates. `.scratch/coordination/` contains exact-head reviews, merger/public-migration receipts and Issue mutation readbacks; task `.scratch/handoff-*.md` files locate retained raw logs and screenshots. The correction tree's `correction-validation-summary.json` verifies that the short-path retest set equals the original 63 failed nodes. Earlier #203 full backend133/frontend150 results survive as original tool receipts, but their complete local raw logs were not retained. Later focused correction logs do not retroactively replace those missing raw logs.

Automated lifecycle and controlled-browser acceptance use isolated disposable databases
and ports, with external transports substituted. The separately authorized real-runtime
journey above uses the normal daily database on port 55432 and real providers; it does
not change the safety boundary for automated tests. These engineering results establish
neither a provider-quality comparison, formal benchmark, research conclusion, version
freeze nor scale guarantee. PR #210 tracks remote code delivery; public deployment
remains separate.
