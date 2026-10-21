# Dayloom Product lifecycle acceptance

Validated in isolated PostgreSQL and Chromium with substituted external transports.

## Event and scope

Engineering implementation and acceptance on 2026-10-21–22 (Australia/Sydney), originating in [Dayloom #198](https://github.com/rplalala/Dayloom/issues/198) and its thirteen native children. The fixed implementation/review base is `26dc1455ec23b931a3245aa6d03e996e5e06db03`; the visual and interaction reference is [r7 at b30eb381](https://github.com/rplalala/Dayloom/tree/b30eb3814513b12d7869ca8a5c59f0b7401d45d6/r7). Existing main-worktree changes to `.env.example` and `GLOSSARY.md` were excluded from task commits. The current contract belongs in [application operations](../../0007-application-operations.md), rather than this dated record.

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

The first broad media run passed 304 tests and failed 28 because its pytest host lacked complete isolated Product settings; browser children already had them. After correcting the host environment, those 28 passed without source changes. Raw Pydantic input representations contained dotenv configuration fragments. A designated sanitized log removes 56 input-value lines while preserving the failure counts, trace and cause; the raw diagnostic is excluded from the retained archive. A fake-sentinel red/green test now verifies Product settings suppress input representations. Exact complete-value scans do not prove absence of truncated fragments in the original output.

The integrated backend gate enabled real TripWorld database acceptance in a separate disposable database. Two installed offline V1/V2 CLI tests inherited that pytest host's database environment; the unchanged credential guard then rejected `RawCapture` enumerating environment variables for redaction. The original guard event files and a minimal fake-sentinel-only contrast both recorded the same forbidden password-name read. A stack-only diagnostic identified environment enumeration rather than settings bootstrap, real retrieval or a missing provider substitute. Explicit fake-host-password regressions reproduced both failures; strict OS/tool/TEMP admission for the test subprocess made both pass. Production redaction, the zero-read/network/import guards and the 60-second subprocess timeout remain unchanged.

A host pause/clock discontinuity inflated one diagnostic's wall duration to over two hours and produced a subprocess timeout. That duration does not measure ordinary CLI performance. Original outputs are retained separately from causal probes and any justified retest; neither raising the timeout nor removing guards is an accepted correction.

The broader fixture-consumer check exposed a separate Windows path-length problem in its runner's long scratch basetemp. Raw-response writes failed, causing interruption-capture and downstream native suite checks to stop before their expected outcomes. Two exact long-path red/short-path green controls held environment, code and assertions constant. The final affected-node retest changed only basetemp to a shorter directory inside the same worktree. All 63 actual failure nodes then passed; the original non-green invocation remains part of the evidence.

### Media authority and readable attribution

Private media bindings originate in final adopted Google identities and the strict final Nearby association ledger. Generated preview Save carries them into the owned normalized snapshot; imported claims, public examples and exported text cannot confer that authority. Fresh public migration applied six files, reran zero, rejected a changed checksum and preserved ten domain tables and the seeded TripWorld marker. Integration upgrade applied only 006 and reran zero with all six checksums verified.

Initial Spec review found that legacy Nearby thumbnail dimensions constrained the new whole image figure. Although presence checks passed, full author/source captions overflowed the desktop row and clipped on mobile. Real V3/API/PostgreSQL/Chromium geometry failed at 1440, 800 and 390px. The separate correction retains thumbnail and Details side by side, with full-width credits below both in normal flow. Actual geometry, clipping-ancestor and keyboard regressions passed; final related backend/API/PG/browser checks passed 41 tests with zero skips, and affected frontend checks passed 26. Both final review axes were clear at `4c09a8acf80092c909609ffbea9eb16b7e0fd6cf`. No provider request, binding schema or production header change was needed for the layout correction.

### Copy recovery across sources

Core review identified three recovery defects: a single storage slot discarded unresolved source A when source B was copied; deletion of A prevented its recovery controls from mounting; and accepted printable operation keys containing a slash could not be addressed through a path segment. Actual API/PostgreSQL red additionally confirmed control-character keys caused Copy/Import/task lookup failures. The separate correction keeps normal legacy paths and the import header, adds query-based recovery for printable slash keys, validates storable keys before persistence, and retains the existing task character domain. Browser recovery now keeps independent owner/kind/source intents and exposes status-only recovery without requiring source content; only explicit intent can submit a new copy.

The first five-failure recovery browser invocation reached two product failures; three other cases stopped in seeding at `KeyError: csrf_token`. It is not evidence that all five product assertions ran. After setup and behavior corrections, all 15 Copy browser cases passed, including actual source/result deletion, cross-source recovery and same-account relogin without extra POST. Following the accepted media merge, final bounded checks passed 104 API/public-migration/constraint/compatibility tests, 17 Copy/media browser cases and 28 affected frontend tests. Private bindings survived Copy/copy-of-copy and source deletion while staying absent from receipts, imports and downloaded JSON. These bounded stage checks preceded the integrated regression below.

## Verification and evidence

The production-code checkpoint is `74d1603b946dc393e46e5121b2986e31724a7d4c`.
The final test-only corrections are `2fcff169c265dfbbac8587a4d5218676dba7a4fd`
(library keyboard navigation) and `e2c19925c97253705f8c2d43e0dd63bfe5c6886a`
(installed CLI environment admission). No application, frontend, launcher, tool or
dependency-lock content changed after the production checkpoint. The Product gate
ran on a clean `2fcff169` tree. CLI tests ran with only the two test-file edits later
committed as `e2c19925`; the handoff verifies their normalized bytes match that commit.

| Actual check | Result and interpretation |
| --- | --- |
| Complete backend at `74d1603` | 4,918 cases: 4,907 passed, seven skipped and four failed. The failures were the stale Copy keyboard expectation, two inherited-password guard failures and the paused population CLI timeout. Nine opted-in real TripWorld database cases passed. |
| Complete Product after the keyboard correction | 263 passed, zero skipped; includes 62 real Chromium cases across all eleven browser modules. Pytest took 658.53 seconds; runner elapsed 661.24 seconds. |
| All 27 installed-CLI fixture consumer files | First invocation: 878 passed, 63 failed, six skipped in 1,313.19 seconds. The overlong scratch basetemp affected native raw-response and downstream suite evidence. |
| Exact CLI failure-node follow-up | The same 63 failed node IDs all passed with only a shorter worktree-local basetemp, zero skips, in 341.50 seconds. The two runs establish 941 distinct passed CLI cases, not one all-green 947-case invocation. |
| Previously paused population `schema_ref` case | Passed in the complete remapped whole-host environment in the original 947-case invocation, 0.390 seconds; its earlier JUnit time was 8,153.345 seconds with a 60-second subprocess timeout. |
| Complete frontend | 174 tests in 27 files passed at `74d1603`; build/typecheck and lint passed. Two Fast Refresh warnings introduced with the account shell remain. Frontend source did not change afterward. |
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

Local evidence paths are historical identifiers, not published dependencies. The integration worktree's ignored `.scratch/final-backend-initial/` retains hash-verified original whole-run log/XML/result files. `.scratch/final-product*`, `final-frontend*`, `final-static*` and `final-delta-static*` identify the later root gates. `.scratch/coordination/` contains exact-head reviews, merger/public-migration receipts and Issue mutation readbacks; task `.scratch/handoff-*.md` files locate retained raw logs and screenshots. The correction tree's `correction-validation-summary.json` verifies that the short-path retest set equals the original 63 failed nodes. Earlier #203 full backend133/frontend150 results survive as original tool receipts, but their complete local raw logs were not retained. Later focused correction logs do not retroactively replace those missing raw logs.

All acceptance databases and API/frontend ports are isolated per worktree. Product acceptance never uses the existing TripWorld runtime on port55432. External model, retrieval-provider, map, weather and image transports are substituted; Product persistence, coordination and V3 execution remain real. These are engineering acceptance results, without a provider-quality comparison, formal benchmark, research conclusion, version freeze or scale guarantee. No live service call, push, PR or deployment is established by these results.
