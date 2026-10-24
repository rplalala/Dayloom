# POI semantics and quantity-review acceptance

September 2026 closeout with separately authorized October corrections. This is engineering
evidence, not a version freeze or benchmark.
Current rules belong to [requirements/evidence](../../0002-requirements-evidence.md) and
[validation/repair](../../0005-validation-repair(v3).md). This record separates semantic
interpretation, captured pilot results, Product propagation and the later review-policy change.
The original [implementation record](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/a6aff13a00af35467b9c88ec2906d10a96095f04/docs/shared_poi_semantics_plan.md)
retains the earlier source history.

## Semantic meaning and completion corrections

The delivery distinguished ordinary interests, source-grounded category goals, exact/
minimum counts, distinct dates and primary-role exceptions. Named revisits used
`VisitRequirement` without a duplicate unsupported-hard semantic obligation. Request-owned
candidate assessment added role/goal/provenance support; four Spec corrections unified
canonical counting across labels, enforced category count/date goals, propagated named
completion and prioritized explicit goals within existing supply capacity.

The first live batch stopped on transport dependency failure. A separately authorized
batch completed A (**8 distinct visits**) and B (**exact two museums on different dates,
at least two parks**), then stopped C at unsupported-hard interpretation. After named-
visit routing correction, C completed British Museum exactly twice on different dates,
with complete policy status and no duplicate hard semantic obligation.

D initially stopped at rich-trip ambiguity. Prompt 16 retained ordinary rich wishes as
soft meaning. Its next attempt passed interpretation but failed semantic evidence-reference
validation; semantic prompt 2 required exact same-candidate references, with bounded
capture and prompt-aware cache identity. The dual-capture retest completed **14 distinct
visits** and **four quantity gaps**. Repair had not run because quantity review was off,
not because rounds were exhausted. This was accepted semantics, not complete trip quality.

## Product completion and review-policy changes — 2026-09-26

The Product route rebuilt only three legacy fields, losing policy-completion/reason values
in JSON and SSE. Correction converts the complete allowlisted Product result, excludes
runtime diagnostics and displays adopted incomplete itineraries with an unmet-requirements
message. Request `completed` remains distinct from policy completion. Four API regressions
failed before correction; complete/incomplete/unassessed JSON/SSE and page checks passed
without changing the strict frontend transport parser.

Quantity was still disabled during that API checkpoint; the captured D override did not
change production. The later approved policy enabled default V3 quantity review for
Product/Dev and removed the obsolete `repetition_review_enabled` schema/target/report key.
Overfull stayed false; explicit disabling remained possible. Confirmed unauthorized
repeat correction, lawful count/date revisits and UNKNOWN protections were retained.
The complete comparison pool was already wired into Repair; no new selection policy,
London/date rule, budget or local-operation authority was introduced. Shared interpretation
applies to V0–V3, candidate judgments to evidence-bearing versions, Repair to V3.
Custom YAML had to remove the obsolete key; cached backend configuration required restart.
Old typed snapshots retain their historical code for replay.

## Latest D quantity pilot

Run `8ebe8b6a-6a62-4e98-806b-b2efbc21807f`, London October 1-8, one traveler, AUD3000,
unchanged mountain/zoo/rich-trip input. One authorized run, exit0, 183.844 seconds.
The newly generated itinerary had three gaps (October 3/7/8), distinct from the prior D
sample's four dates. Two Repair rounds added three visits, from15 to18 distinct canonical
IDs. Final daily counts: **3/3/2/2/2/2/2/2**. Original activities remained unchanged.

Two additions came from the comparison pool and one from unused selected supply. Repair
reused37 qualified candidates, with no new search, Details, embedding, retrieval or semantic
calls. Usage was2/5 Repair model calls,18/24 route sends and18/32 elements; request-wide
semantic usage stayed2/6 calls and36.478/120 seconds. The existing limits/defaults were not
changed. Two requirement records, six semantic records and a1,395,829-byte Repair snapshot
were captured; typed offline replay and14 acceptance checks passed. Final findings include
22 PASS and26 UNKNOWN, with no confirmed violation or unresolved quantity-review target.

Evidence is local and ignored: `artifacts/poi_semantics_acceptance/20260926_D_quantity_review/`.
Its `report.md`, `checks.json`, `execution.json` and `offline_replay.json` provide the bounded
observations. Raw captures are not proposed for Git. This development pilot is not a benchmark
or a controlled comparison with the earlier D generation.

## Bounded validation checkpoints

| Checkpoint | Observed result | Scope and causal qualification |
| --- | --- | --- |
| Initial Spec fixes | **1590 passed, 9 skipped, 1 failed**, then **1591 passed, 9 skipped** | Old fixture violated confirmed-repeat priority; corrected fixture retained its loss assertion |
| Named C routing | **1602 passed, 9 skipped** | Before separate C live revalidation |
| Prompt 16 ambiguity | **1611 passed, 9 skipped** | Nine controlled interpretation regressions; before D reference failure |
| Semantic/capture corrections | **1625 passed, 9 skipped** | Partial-write capacity and telemetry-stability corrections |
| Quantity capture/replay | **1640 passed, 9 skipped**, 75.77 seconds; focused V3 **421 passed** | Includes 15 added package tests; typed replay no provider/model calls |
| Product propagation | **1646 passed, 9 skipped**, 80.96 seconds; frontend **59 passed / 8 files** | JSON/SSE and incomplete-state fixes; TypeScript/Vite/scoped Ruff passed |
| Default review policy | **1648 passed, 9 skipped**, 72.84 seconds | Migration regressions retain repeat/legal/UNKNOWN safeguards; frontend unchanged, prior gate reused |

An interrupted default-policy run stalled near retrieval timeout/cancellation tests;
isolated retrieval **16 passed** and the fresh full gate passed with no timeout report.
No retrieval code changed. Checkpoints overlap and are not additive. Backend Ruff and
changed-file compilation passed; earlier frontend **56/8** was superseded by the 59-test
correction gate, not new evidence of deployed/live Product behavior.

## Offline integration and source provenance

The approved integration exercised real Product/Dev routing, Vite proxy, FastAPI SSE,
services, RequestPlannerRuntime and independent version runners; only external collaborators
were synthetic. Product displayed the default-on quantity addition and incomplete warning;
Dev completed all four flows with quantity=true, overfull=false, no obsolete repetition
field and an `ACCEPTED_PARTIAL` fixture. All business cases passed first submission;
setup corrections were not retried business requests. Temporary processes were stopped.
Local evidence: `artifacts/offline_integration_20260926/`.

The exported candidate tree initially lacked local virtualenv/tokenizer assets, yielding
**30 failed, 1578 passed, 9 skipped**. With those unchanged dependencies supplied, backend
passed **1608, 9 skipped**, 72.92 seconds; the separate tooling group passed **40**, 6.47
seconds. Implementation hashes matched the 1648-pass workspace. These subset gates do
not sum into another full run. Reviewed revisions were `0652222`, `014c726`, `29647ef`,
`9c910b2`, `40b0b26`; all 105 inventoried files were committed at that closeout.

## Decisions and limitations

Penguin Beach is an internal exhibit and London Zoo its parent, not identical names.
Visiting the exhibit then other areas can be reasonable. The user declined further work;
that relationship alone established no defect or open blocker. P3 pending-reason heuristic
remained deferred. UNKNOWN access/hours/suitability/cost remained UNKNOWN; indoor climbing
was labelled a related alternative, not actual mountain climbing. Quantity success does
not establish richness, feasibility, stable interpretation or a controlled comparison
with the earlier regenerated D output.

## Shared case-derived reliability corrections — 2026-10-17

[Issue #175](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/175) owns four
shared corrections against `b73c8eed09fafb6d54bee8684c5b2e7766515357`, with children
[#176](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/176),
[#177](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/177),
[#178](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/178) and
[#179](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/179). The researcher
authorized main-directory implementation, local commits and offline verification;
case continuation remained with the individual case chats.

The originating observations were literal-name rejection for Sagrada Família / the
provider's basilica name and British Museum / The British Museum (one shared defect),
model-corrupted long source endpoints in case-10, the Paris DST offset propagated in
case-11, and an unsupported dated total count in case-12. These causes come from the
case diagnoses supplied with the approval; this correction did not repeat the original
executions. Existing source validation correctly rejected the corrupt IDs. The identity
policy's exact-name limitation, missing IANA acceptance check and missing count operator
were separate implementation gaps. V0-V2's apparently correct case-12 output was not
evidence that its hard total had been executable.

The implementation commits are `2835f66` (compact source selections), `ed42a49`
(named correspondence), `c14fede` (civil time) and `7a76632` (dated counts and independent
evaluation), with compatibility corrections `cbf7d7a` / `132a8f8`, lossless serialization
`4b10569` and review corrections `2180b5c` / `cfb3cb0`. Detailed current rules belong
to [requirements](../../0002-requirements-evidence.md),
[civil time](../../0003-itinerary-transport.md#civil-time-and-iana-acceptance),
[Repair protection](../../0005-validation-repair%28v3%29.md#dated-count-protection) and
the [independent operator](../../contracts/0003-requirement-schedule.md#dated-total-visits).

Red/green checks exposed omitted structured generation counts and known non-main objects
being counted, then verified both fixes. Broader regression found missing-zone duck-typed
evidence compatibility and obsolete timezone-test assumptions. A new naive-duration check
also showed host-zone interpretation before its correction. The initial integrated subset
reported 1,920 passes and four timezone expectation failures; the corrected related gate
passed 83 tests. Count/source/evaluator checks passed 140 tests; the native mocked
execution/replay subset passed 82. These overlapping gates are not additive.

Review against `b73c8ee` found no hard Standards breach, two maintenance suggestions,
and five actionable Spec gaps: hard minimums conflicted with soft pace and default
overfull targets, day windows assumed one fixed offset, transfer-window cuts retained an
obsolete offset, and final transport omitted new-place timezone evidence. New regressions
reproduced the faulty boundaries; one test scope first needed its required permissions
field. The corrections give dated hard counts and feasible pace ownership of quantity
targets, map both civil boundaries, map derived reservations through UTC/IANA and carry
the merged final evidence. Minimum counts retain their open upper bound. The maintenance
corrections centralize wire-version selection and type the daily assessment. The V3/time
gate passed 579 tests; current/historical source and capture wiring passed 65. The final
minimum/overfull correction passed 127 related tests, including actual totals of six and
seven under a hard minimum of six with all quantity reviews enabled.

Real cached o200k counts measured lossless JSON syntax only. For synthetic ASCII inputs
of 400 / 4,000 / 24,000 characters, current system/user/schema totals changed from
16,561 / 63,211 / 325,711 to 14,960 / 47,210 / 229,710 tokens. The schema stayed at
5,127 tokens. These omit the remaining trip envelope and provider framing, are not billed
usage, and do not prove semantic accuracy or universal input fit. No limit increase,
per-name budget or automatic retry was introduced.

An initial complete-suite attempt was stopped before completion to apply the review
corrections. Its observed Windows junction failure reproduced in the sandbox and passed
outside it on identical source. Credentials, system permissions and project configuration
were unchanged. The final complete backend run on `cfb3cb0` passed 4,421 tests with
16 skips and one warning in 1,954.26 seconds. The skips were two host symlink-privilege
checks, five alternate-volume checks and nine opt-in isolated PostgreSQL checks. Ruff
lint and format checks passed for all 61 changed Python files. Final Standards and Spec
rechecks had no outstanding findings. All 189 local links in the seven updated documents
resolved to tracked files and valid Markdown anchors.

Provider/model tests use offline fixtures and doubles; they verify contract behavior,
not real-model correspondence accuracy or case acceptance. Original case inputs, failed
attempts, provider captures and scores were not rewritten, and no paid call or case rerun
was part of this correction.

## Required-category admission and Product feedback — 2026-10-24

The reported Paris brief had valid dates and an unspecified required category visit.
Its persisted Product task (`40c313b4-9f93-4bd9-8a0c-884b890e6f58`) retained
`needs_clarification` with an empty public issue list. The original interpretation
capture was unavailable, so the exact historical model decision cannot be established.
An offline reproduction did establish two defects: a hard category goal was rejected
before discovery, and the public projection discarded its code and source-linked reason.
Changing the requirement to a preference would bypass the gate but alter user intent;
the approved correction retained the original text and hard strength.

Against base `ac279230`, implementation commits `d07e45b` and `2243102` added the
[generic required-category contract](../../0002-requirements-evidence.md#required-category-visits)
and durable Product coverage/feedback. Actual V1-V3 graph regressions exposed a second
hard gate in candidate acquisition; it was corrected as well as intake. Supply tests
reproduced an optional target displacing the only required-category option at capacity.
Coverage and Repair tests verified related alternatives, unknown matches, free windows,
exact/minimum counts and preservation of the sole required match. Test categories include
art museums, botanical gardens, science centres and craft workshops; there is no category
keyword branch. Model responses are controlled fixtures, not measured language accuracy.

The relevant backend gate passed **2,071 tests, 29 skipped**; frontend passed **264 tests
in 43 files**. Windows default temporary-directory permission failures were resolved by
running tests with an explicit workspace temporary directory, without changing permissions
or credentials. Skips require isolated database or local historical evidence prerequisites.
The first Standards review passed. Spec review identified two remaining feedback paths:
empty qualified supply and capability limits still requested a rewritten brief.
Commit `cc063db` corrected both; new assertions first produced **7 backend failures**
and **1 frontend failure**, then related regression passed **791 backend tests** and
**40 frontend tests**. These gates overlap. TypeScript/Vite, changed Python Ruff and
ESLint passed; existing bundle-size and two Fast Refresh warnings remain.
Standards and Spec rechecks closed both findings without new issues; the Spec reviewer
independently reran the 27 intake, graph and feedback regressions successfully.

Required coverage survives typed detail serialization and preview/saved-view rendering;
JSON/text export assertions retain unresolved obligations. An isolated database Save/reopen
acceptance run and real-provider generation were not performed. Local diagnostic logs under
`.scratch/required-categories-*` are ignored evidence identifiers. Unrelated `.env.example`
and `GLOSSARY.md` work remained outside these commits. No paid execution or original
task-result rewriting was part of this correction.
