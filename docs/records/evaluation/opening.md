# Opening evidence policies and development results

This record synthesizes October 2026 opening-evaluator changes, distinct validation
checkpoints and two separately approved real access assessments. Current parsing,
eligibility and judgment rules belong to the
[opening contract](../../contracts/0004-opening-routes.md#opening). Original provider bytes,
hash-bound preparations, reports and receipts were preserved rather than relabelled.

<a id="rtpeval-ticket-06-acceptance"></a>

## Initial scorer, defects and native supplements — 2026-10-02

Ticket [06 / #18](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/18) introduced
immutable offline `score_opening` and a local CLI from
`ed4c9a9d4724263925748588878eadc22d21978a`. Independent raw snapshots/identity/time were
required; planner hours/findings were not truth. Material corruption failed whole-plan
preparation while failed sends/semantic defects retained visit UNKNOWN. Original rules
preferred applicable current hours and blocked regular fallback for current defects or
special-date uncertainty. Empty periods proved closure; absent/null did not. These
original rules were later revised, not silently overwritten as always-current behavior.

Consequential corrections distinguished missing/invalid periods, malformed endpoints,
missing-close/sentinel behavior and boolean clocks. Integer-microsecond complement spans
preserved a one-microsecond overrun FAIL. Full linkage reconstruction rejected corrupt
route legs; inconsistent literal dates/weekdays could not narrow unknown scope. Basis
and actual evidence availability were separated, including N/A empty scope.

Spec found a prior-week DST error erasing closure on an unrelated Wednesday. Correction
limited invalid scope; a follow-up half-open midnight case used end minus one microsecond
to identify the occupied last date, preserving UNKNOWN for an actually affected overnight
DST gap. Standards aligned the state summary and reused date validation.

| Validation stage | Observed result | Qualification |
| --- | --- | --- |
| Parsing/time development | **82 passed** scorer/CLI; earlier evaluator **309 passed, 1 skipped** | Overlapping synthetic selections; current/partial/timezone/DST cases |
| DST review corrections | **97 passed**, then related **11 passed** | Wednesday and midnight-end fixes; final reviews clear |
| Original full offline backend | **2148 passed, 10 skipped**, 149.88 seconds | Database opt-ins disabled and Windows symlink privilege skipped |
| Later database supplement | **8 passed, 1 failed**, 8.50 seconds; checksum retest **1 passed**, 0.70 seconds | Isolated `tripworld_test`; one stale migration-test path fixed to `tools/data/tripworld/migrations/001_retrieval.sql` |
| Elevated native symlink supplement | **1 passed**, 0.33 seconds | Real link creation and intake escape rejection; no test bypass or persistent OS security changes |
| Local closeout selection | **327 passed, 10 deselected**, 39.01 seconds | Previously checked native/database cases explicitly excluded, not skipped |

All ten original skips passed across separate supplements; the original full-suite result
remains 2148/10, not a fabricated combined unfiltered pass. A non-elevated run still
skipped symlink creation; only the later explicitly approved elevated token established
that check. Initial missing test credentials were setup errors, not scorer defects.
Ruff, compilation, CLI help, 194 document targets and diff checks passed; compilation
was not static type checking. Implementation: `ee085d3e1286990595c842eb44abf6fe88b79ad4`;
migration-test correction: `f62c07f6ed2034e223ef5951cb5a0655d9739b20`.
The scoped command outputs/test sources own supplement evidence; temporary reports/helpers
were removed and are not claimed as recoverable artifacts.

<a id="opening-access-boundary-proposal-2026-10-09"></a>

## Missing evidence and advisory access boundary — 2026-10-09

At [#88](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/88), preserved Sydney
sources had **14 opening UNKNOWNs, zero opening FAILs**. HTTP 200 omitted both requested
hours fields for Opera House, Harbour Bridge, Darling Harbour, Bondi Beach, The Rocks
and Powerhouse Museum; Powerhouse also had undated `CLOSED_TEMPORARILY`. A minute grace
could not resolve absent facts. API semantics came from the
[Places resource reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places):
current hours cover request-local seven-day applicability; regular hours, always-open
sentinel and business status have distinct meanings. Absence proved neither closure nor
unrestricted access.

The advisory proposal distinguished indoor entry, outdoor area, dated facts, regular
weekly evidence and closure dates. It proposed provisional regular-hours PASS, explicit
visit/access intent and separately captured official facts with source/time/area/date
scope. Arrival-only access or a future tolerance would have been different metrics.
That proposal was not implementation. #89 explicitly replaced provisional verdicts with
ordinary regular-basis PASS/FAIL; business-status/official-acquisition refinements were
not delivered by #89. Later #90/#91 introduced a distinct fallible model access policy.

## Regular opening fallback acceptance — 2026-10-09

[#89](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/89), base
`fb517bbd6e122432e852f593fd0ccf26ec25adca`, implementation `4043dba`, introduced rules 2.
Established current intervals retained priority; usable regular hours filled unresolved
time and retained mixed-basis provenance. Special-date markers without applicable hours
became diagnostics, not a veto. Query-instant `openNow=false` could not decide a later
visit. Undated closure/access intent and new acquisition were outside this fix.

Three current-defect regressions and a marker-only case first reproduced UNKNOWN instead
of regular PASS. Changed expectations for truncated final minutes and collection-midnight
uncertainty retained diagnostics. Guards preserved explicit current closure, regular FAIL
and UNKNOWN without usable fallback. Actual CLI tests showed a 02:00 query/10:00 visit
PASS from regular 09:00–17:00 despite `openNow=false`, explicit current-empty FAIL and
absent schedules UNKNOWN. Final scorer/CLI **96 passed**; full backend **3124 passed,
10 skipped**, 287.56 seconds. Ruff/format/diff checks and both review axes passed.

Offline original-source recalculation still left all **14 UNKNOWN** because neither
schedule existed. Identity, other dimensions, density and scores were unchanged from
#88: V0 **89.2857**, V1 **68.0000**, V2 **75.0000**, V3 **81.1111**. Repeated CLI output
was identical, with zero socket/DNS attempts. Trusted original code at
`ee0f4947edb32fe2f7a07f5b4fd7c1ee98fd6531` reproduced the original report exactly.

## Missing-hours model policy revisions

[#90](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/90) added policy 1,
opening rules/quality profile 3. Verified identity/time/zone and absent schedules were
required; explicit empty/malformed/incomplete periods were not rescued. Explicitly
supported exterior/public intent could PASS; ambiguous, indoor/ticketed or unsupported
intent stayed UNKNOWN. PASS changed verdict scoring with a model basis while factual
hours coverage/seconds and grounding FAIL remained unchanged.

[#91](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/91) introduced policy 2,
packet/material schemas 2, opening rules 4 and `rtpeval_access_quality_4`. Generic public
landmark sightseeing could be inferred without exterior wording; a possible tour/climb
alone did not force UNKNOWN. Explicit restrictions, negation/conditional wording and
museum admission retained separate interpretation. `intent_basis` / `venue_category`
made inference explicit. Invalid default PASSs for museum/indoor/other/unknown categories
and unresolved intent were rejected. Missing provider types remained null; categories
were model interpretations, not Google facts. Neither revision changed original outputs,
identity/grounding, route windows, score arithmetic or pace formulas.

| Revision/checkpoint | Observed validation | Consequential correction |
| --- | --- | --- |
| #90, base `8c687f162db4fd762239e4ffce054c76f0610564`, implementation `40fe066` | Initial **3150 passed, 1 failed, 10 skipped**; final implementation **3151 passed, 10 skipped**, 332.00 seconds; public flow **136 passed**, fallback **27 passed** | Register only approved isolated `opening_run` HTTP entry in import guard; scorer/import remain offline. `openNow` with absent periods remained eligible. |
| #90 review correction `017c548` | Evaluator **1216 passed, 1 skipped**, 228.81 seconds | Standalone preparation/import lacked implementation binding; every packet now includes/rebuilds evaluator hashes. This later gate was not another full backend run. |
| #91, base `ad1b72b26ac145acfe6bf197f912f9f854c3a979`, implementation `34506a6` | Public judgment **39 passed**, 24.55 seconds; actual CLI **7 passed**, 18.85 seconds; backend **3164 passed, 10 skipped**, 311.14 seconds | Category/intent gates, immutable quotes, raw types and API priority exercised with mocks. |
| #91 review correction `9f80a20` | Public scoring/CLI **41 passed**, 32.33 seconds | Spec's conditional-entry coverage gap corrected with exact original notes/request/import assertions; production unchanged since full gate. |
| #140 quotation clarification, 2026-10-13, base `9b7fb8b`, implementation `7739f0f` | Opening judgment/CLI **43 passed**, 30.78 seconds; Ruff/format/diff checks passed; Standards and Spec reviews found no issues | Request complete verbatim copies of an original activity field and put interpretation only in `rationale`. Schema, policy and strict substring validation remain unchanged. Initial test setup failed because sandbox temporary/cache paths were unwritable; a fresh workspace temporary directory and disabled pytest cache resolved the environment failure. |

Final reviews closed all findings; changed-file Ruff/format/diff checks passed and no
configured type checker was claimed. Mock gates do not establish real-model accuracy.
Historical policy-1 replay used all 70 trusted evaluator source bindings. Git-normalized
or uniform-CRLF content initially failed frozen byte hashes; matching exact retained
mixed-newline bytes restored replay without modifying repository sources/preparations.
The old packet/response was not rebound into policy 2.

The separately prepared #140 supplement on 2026-10-13 received HTTP 200 but stopped
with `Original activity quotation required`: V2 Opera House visit 006 substituted
"in the supplied evidence" for "by the supplied evidence". None of its nine decisions
was accepted; [case-01](../../../benchmark/case-01/report.md) retains the primary scores.
The consumed preparation and original request, response and usage remain unchanged.
A retained producer snapshot verified 332 Python file hashes, including 82 exact native
byte bindings, and reproduced the stopped report with zero network attempts. A derived
mock with the complete original field passed the quotation boundary; this proves the
validator accepts valid source text, not that real-model quotation reliability improved.

A fresh, separately approved preparation at `815fcae` then completed on 2026-10-13,
Sydney 21:18:46.505559–21:18:58.654406. Its `gpt-6-luna` / medium response contained
**nine PASS decisions**, each quoting a complete original field verbatim. The strict
native importer accepted all nine and network-denied replay reproduced the report
exactly. One send used **10665 input + 1728 output = 12393 tokens**, with 10662
cache-write tokens and zero cached reads; reference cost was **USD 0.00219705**,
with no actual invoice. The executor used `gpt-6.1-sol` / high. Native exit was 0;
an outer console echo hit a GBK encoding error after completion, without changing
saved evidence or causing a resend.

Supplemental scores were V0 **73.3333**, V1 **93.3333**, V2 **96.6667** and V3 **100**.
Only opening verdict coverage changed; factual hours coverage, the confirmed V0
museum-hours failure, identity/routes/occupancy and density remained unchanged.
Four UNKNOWN remained: one V0 identity, one V0 opening and two V0 routes. These
model access PASSs do not establish official opening hours or general model accuracy.
The [initial case-01 dataset](../../../benchmark/case-01/report.md#opening-assessment)
contains both API-only and supplemented scores, accepted with their limitations
on 2026-10-14. The independent
[Repair smoke](../v0-v3/v3-development.md#post-refactor-model-smoke) used separate
synthetic inputs. Local evidence identifier: `D:/Workspace/Capstone/case01-140/phase-c`,
including the original native opening execution, execution logs and parent assessment.

## Two real source-bound assessments

Both separate one-use preparations had **14 eligible occurrences** (V0 two, others four),
32000 input / 8000 output limits, zero Google sends, at most one model send, zero retries,
120-second request / 900-second overall bounds and USD 0.05 reference allowance. Saved
prices through 2026-10-10 reserved USD 0.008, distinct from actual billing. Executor was
a current-session `gpt-6.1-sol` / medium child; evaluator was `gpt-6-luna` / medium.
No request was repeated for ordinary inspection errors.

| Execution | Prepared digest / source | Actual usage and time | Outcome |
| --- | --- | --- | --- |
| Policy 1, #90 | `d2db8c5b37d99042e958210b99546edb3a4db92718772159ac357d87351f604c`, source `eee95c6`; wire estimate **17254** incl. 1024 margin | **15530 input + 2709 output = 18239**, zero cached reads, **15527** cache-write; Sydney 04:59:24.421839–04:59:42.998055, **18.576 seconds**; reference **USD 0.003295675** | HTTP 200/exit 0; 0 Google, 1 model, 0 retries; **8 PASS, 6 UNKNOWN** |
| Policy 2, #91 | `c0c7804dbdcdf9cd90c34fa9c1f68a1de6c4a41351c2f9f7b40eb556394b93ee`, source `9f80a20`; wire estimate **17687** incl. margin | **15928 + 2417 = 18345**, zero cached reads, **15925** cache-write; **711** reasoning tokens; request **14.680 seconds**, dispatch **21.266 seconds**; reference **USD 0.003199425** | HTTP 200/exit 0; 0 Google, 1 model, 0 retries; **13 PASS, 1 UNKNOWN** |

All judgments bound unchanged original activities/independent venues. Twelve policy-2
judgments used `public_landmark_default` (six landmarks, six public areas); V0 Opera
House retained explicit activity intent and Powerhouse museum admission intent.

| Ref | Version/place | Original interval, October 2026 | Policy 1 → 2 | Interpretation |
| --- | --- | --- | --- | --- |
| visit 001 | V0 Opera House | 14 th, 10:00–12:00 | PASS → PASS | Notes exclude interior/tours; building/harbour viewing |
| visit 002 | V0 Powerhouse Museum | 17 th, 10:00–12:15 | UNKNOWN → UNKNOWN | Indoor exploration; no admission/date-specific access evidence |
| visit 003 | V1 Opera House | 14 th, 10:00–11:30 | UNKNOWN → PASS | Generic building visit now ordinary public-landmark sightseeing |
| visit 004 | V1 Harbour Bridge | 14 th, 12:15–13:15 | UNKNOWN → PASS | Generic visit no longer needs viewing/crossing/climb disambiguation solely from possibility |
| visit 005 | V1 Darling Harbour | 15 th, 13:30–14:30 | PASS → PASS | Public waterfront; no specific indoor/paid activity |
| visit 006 | V1 Bondi Beach | 17 th, 10:00–11:00 | PASS → PASS | Outdoor visit, no swimming commitment |
| visit 007 | V2 Opera House | 14 th, 10:00–11:30 | UNKNOWN → PASS | Conditional interior-verification note does not commit to entry |
| visit 008 | V2 Harbour Bridge | 14 th, 12:30–13:30 | PASS → PASS | Harbour-view interpretation retained; basis now landmark default |
| visit 009 | V2 The Rocks | 14 th, 14:30–15:45 | PASS → PASS | Exploring public urban district |
| visit 010 | V2 Darling Harbour | 16 th, 14:00–15:30 | PASS → PASS | Public waterfront daytime interval |
| visit 011 | V3 Opera House | 14 th, 10:00–11:30 | UNKNOWN → PASS | Ordinary public-landmark viewing |
| visit 012 | V3 Harbour Bridge | 14 th, 12:30–13:30 | UNKNOWN → PASS | Ordinary viewing, no invented paid climb |
| visit 013 | V3 The Rocks | 14 th, 14:15–15:45 | PASS → PASS | Outdoor neighborhood sightseeing |
| visit 014 | V3 Bondi Beach | 17 th, 10:30–12:30 | PASS → PASS | Reasonable outdoor interval; no swimming commitment |

These are reasonableness judgments, not certified schedules. Generated drizzle/weather
notes remained source context, not independent weather evidence. The residual Powerhouse
UNKNOWN is missing museum admission evidence; undated temporary closure proves neither
closure nor access on October 17 in `Australia/Sydney`.

| Version | #90 overall; opening P/U | #91 overall; opening P/U | Preserved grounding FAIL |
| --- | --- | --- | ---: |
| V0 | **92.1429; 6/1** | **92.1429; 6/1** | 0 |
| V1 | **72.0000; 8/2** | **76.0000; 10/0** | 2 |
| V2 | **82.5000; 7/1** | **85.0000; 8/0** | 0 |
| V3 | **85.5556; 7/2** | **90.0000; 9/0** | 0 |

Opera House exact-once, non-overlap and applicable routes remained PASS. V1 Harbour Bridge
(Oct 14) and Maritime Museum (Oct 15) kept `api_address_mismatch` FAILs. Six soft pace
FAILs remained: V0 Oct 17 one visit; V1 Oct 14/16 three; V2 Oct 14 three/Oct 17 one;
V3 Oct 14 three. No extra hard FAIL or non-opening UNKNOWN was introduced.

Independent actual `replay-opening` reproduced each complete report with exact JSON
and zero sockets/DNS. All four original outputs, **205 parent receipt files** and prior
#90 report/receipt verified unchanged. Separate API-only baselines retained identity,
requirements/schedule, routes and factual opening status/basis/known-open/outside/unknown
seconds, including unassessed checks. Model PASS did not fill missing factual hours.

## Evidence bindings and limitations

Local evidence roots are historical identifiers, not published dependencies:

- Original run: `artifacts/sydney-fresh-evaluation-preparation-20261009-r1/run`.
- Rules-2 recalculation: `artifacts/sydney-opening-policy-recalculation-20261009-r1/`
  (`opening.json`, `quality.json`, `recalculation-check.json`, `original-rules-replay-check.json`).
- Policy 1: `artifacts/sydney-opening-access-preparation-20261009-r2/`; closed `run/execution/`
  contains HTTP/model/usage/report/receipt; dispatch/replay/API-baseline/audit files sit outside it.
- Policy 2: `artifacts/sydney-public-landmark-preparation-20261009-r1/`, same evidence layout;
  historical protection: `artifacts/issue91-historical-protection`.

| Artifact | SHA-256 |
| --- | --- |
| Original report | `09272f235cadc20aeb94f4c6a4f5945f35a77faaf89637611beb422695e0b459` |
| Original receipt | `ca5852385f6fcdeb1279afbb25ddfdc8da8d11a64514836b88bf824406bae0e1` |
| Rules-2 opening report | `7fbd06aa0bd789484162bde710a4caab555fbf2bc173f69a50f3c25d27f53471` |
| Rules-2 quality recalculation | `b8e9b3328680e137c2b078acb5850e53e6ead621285d5bf7ccfd23f4ff0695d3` |
| Policy-1 final report | `71a60426d3296c97fc10d6e8cdb7376a68c8351f20d5462653580ee4ccfe2ebc` |
| Policy-1 incremental receipt | `0f3b77f03e011b5a2f50bc678a15f048da013a8a9b460f972636ce30c40dbe6c` |
| Policy-2 final report | `8992422ca3953fd1d90f059674da68e1f18e1730f5816157a876a8b7d7c1c83b` |
| Policy-2 receipt | `5ea846bccf2ededed1275bbc3690b36659c46c2a262a32b7fbabb165a42e5c7c` |

Processing/acquisition completed while factual evidence stayed unresolved. Parent costs
were not counted again; actual account billing remained unavailable. Agent inspection
was not genuine human review. Bounded engineering acceptance does not establish universal
model/access correctness, formal version ranking, bookings or final human agreement.
Both one-use allowances were consumed; the record grants no new acquisition or execution.
