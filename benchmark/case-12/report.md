# Case-12: Sydney, Australia

## Current status

Revision **r06** completed V0-V3 once sequentially and one independent Primary on
**17 October 2026 Australia/Sydney**. Work is paused at the primary-score handoff.
Candidate-process studies, paired Repair evaluation, blinded review and case
acceptance remain pending.

The unchanged [original request](../inputs/case-12.json) covers Sydney,
22-28 October 2026, two adults, AUD 3,200 for the group, nature and harbour views,
relaxed pace, exactly one sightseeing visit on 22 October, and a full rest day
without planned activities or travel on 25 October. Input SHA-256:
`954cc256063f6118cc0001342be230c437944a77bbe082372008dae912a9b4b1`.
The scenario retains former case-14's identity under
[Issue #163](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/163).

All r06 executions used `5aabd1c45c5c5d6180424fb920fbb324822b2bd9` on
`codex/case-12-r02`, including the reviewed full-day protection pace correction.
Source, runtime and commands were bound before execution. The user raised the
cumulative reference allowance from USD 40 to **USD 55** before dispatch and
authorized one fresh V0-V3 selection and one Primary, preserving previous attempts
and pausing after primary scoring. The original input and evaluator scoring
contracts remain unchanged; results were not rescored after inspection.

## Requirements and observations

The independently authored and reviewed r02 RequirementSpec revision `"2"` applies
to the identical original input. Exact spec bytes, distinct author/reviewer records,
original times and available authentic message excerpts were reused. Only batch
identity/revision headers in the schedule/density/transport contexts were rebound
to r06. Native admission accepted this reuse; it is not a fresh semantic review.

| Source requirement | Reviewed representation | r06 Primary result |
| --- | --- | --- |
| Exactly one sightseeing visit on 2026-10-22 | `daily_visit_count`, `primary_visits`, exact 1; no invented named subject. | PASS in V0-V3; each has a confirmed count of 1. |
| No activities or travel on 2026-10-25 | `protected_time`, full local day, `scheduled_commitments`. | PASS in V0-V3; submitted activities and touching transfers are both zero. |

Each version's requirement dimension is **100**, with two PASS, zero FAIL and zero
UNKNOWN. Density uses a relaxed default with exact one and zero on those dates.
Transport is unrestricted outside the separate rest-day travel prohibition;
the zone is `Australia/Sydney`. Nature, harbour views and flexibility remain soft
preferences without invented quotas. Original source-only interest meaning remains
applicable; relevance and candidate-process studies have not run. Affordability and
these soft preferences are not certified by the two hard obligation scores.

## Primary scores and limits

Native processing and acquisition are **complete**, with zero acquisition failures.
Evidence is **unresolved** because V0 retains two identity/opening UNKNOWN checks
and one route UNKNOWN. Common dimensions are requirements, grounding, non-overlap,
opening and routes.

| Version | Five-dimension base | Mean daily density deduction | Primary score |
| --- | ---: | ---: | ---: |
| V0 | 80.000000 | 8.571429 | **71.428571** |
| V1 | 80.000000 | 25.714286 | **54.285714** |
| V2 | 100.000000 | 11.428571 | **88.571429** |
| V3 | 100.000000 | 5.714286 | **94.285714** |

Dimension cells show score followed by **PASS/FAIL/UNKNOWN** counts:

| Dimension | V0 | V1 | V2 | V3 |
| --- | ---: | ---: | ---: | ---: |
| requirements | 100.000000 (2/0/0) | 100.000000 (2/0/0) | 100.000000 (2/0/0) | 100.000000 (2/0/0) |
| grounding | 75.000000 (6/0/2) | 100.000000 (5/0/0) | 100.000000 (7/0/0) | 100.000000 (9/0/0) |
| non_overlap | 100.000000 (10/0/0) | 100.000000 (5/0/0) | 100.000000 (8/0/0) | 100.000000 (12/0/0) |
| opening | 75.000000 (6/0/2) | 100.000000 (5/0/0) | 100.000000 (7/0/0) | 100.000000 (9/0/0) |
| routes | 50.000000 (1/0/1) | N/A; contributes 0 (0/0/0) | 100.000000 (1/0/0) | 100.000000 (3/0/0) |

The five common dimensions contain no FAIL checks. V0's claims for Manly to Shelly
Beach Walk and Sydney Harbour Bridge Pylon Lookout have no independently supported
identity match (`model_no_supported_match`). Their opening checks and the
Pylon Lookout-to-Barangaroo Reserve route retain UNKNOWN (`identity_unresolved`).
These source claims remain unverified in the saved report.

V1 has no applicable same-day route checks. Its `N/A / no_checks` contributes zero
within the common five-dimension denominator, producing an 80-point base. V2/V3
have one/three PASS route checks. Density FAIL dates are 24, 26 and 27 October for
V0; 23, 24 and 26-28 for V1; 24 and 26-28 for V2; and 26 and 28 for V3. V1's
unprotected blank day on 24 October has zero primary visits and a 100-point daily
deduction; the other FAIL dates have one visit and deduct 20 each. Means use all
seven requested dates. Every version's first-day and rest-day exact counts match.

Eligible missing-hours assessment completed for **10 cases**, all with
model-supported access PASS. Complete API evidence counts for V0-V3 are 4/3/3/7;
model-supported decidable counts are 2/2/4/2. Model-supported public/exterior access
does not supply verified API hours. Scores describe this selection under these
rules and evidence, not general travel quality or affordability.

V2/V3 retain partial-retrieval observations while their required workflow mechanisms
complete. V3 returns `ACCEPTED_PARTIAL / round_or_model_limit` after six proposal
sends, retaining round one. Its original/final native pace penalty totals are
100/40, with means 14.285714/5.714286. The only remaining targets are 26 and
28 October, each one visit with penalty 20. The rest day is PASS with penalty zero
in both reports; `full_day_protection_pace_1` retains its sourced zero-count
projection. The former false rest-day target is absent. Native Repair's ten model
calls include six proposals and four semantic assessments. No explanation-compression
send occurred: all six round compression records are empty, and no native model
stage is a compression event.

V3's physical `run.json` exists but is marked truncated: its 14,767,335-byte source
exceeded the trace limit and produced a 10,729,914-byte preview. The evidence index
therefore lacks a usable `finished_trace` and marks collection partial. The complete
14,260,688-byte native result retains the genuine draft/final and Repair records;
native intake admitted all four finals. This limits trace inspection without
invalidating the admitted Primary sources. Original trace bytes remain unchanged.

## All-attempt resources and budget

r06 reuses the same-day frozen official reference prices retained in r05, with a
validity interval covering this execution; no new price lookup is claimed. Sources
are the official [model](https://developers.openai.com/api/docs/models/gpt-6-luna),
[embedding](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[tool](https://developers.openai.com/api/docs/pricing) and
[Google](https://developers.google.com/maps/billing-and-pricing/pricing) references.
OpenAI prices are a disclosed Foundry proxy. Account invoices and external Codex
usage/billing are unavailable; free quotas, discounts and taxes are not inferred.

| Attempt | Outcome | Native seconds | Model calls including embeddings | HTTP sends | Observed tokens | Reference USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| r01 V0 | Completed | 62.063 | 2 | 2 | 26,275 | 0.004371665 |
| r01 V1 | Completed | 119.766 | 4 | 68 | 84,990 | 2.364824325 |
| r01 V2 | Completed | 145.922 | 6 | 98 | 85,629 | 2.97282712 |
| r01 V3 | Clarification before generation | 26.938 | 1 | 1 | 18,758 | 0.00164315 |
| r02 V0 | Completed | 47.344 | 2 | 2 | 23,269 | 0.00388671 |
| r02 V1 | Prompt serialization failure | 69.422 | 3 | 64 | 22,438 | 2.259815495 |
| r03 V0 | Completed | 37.735 | 2 | 2 | 21,701 | 0.00283933 |
| r03 V1 | Completed | 92.922 | 4 | 68 | 77,537 | 2.36335856 |
| r03 V2 | Completed; partial retrieval | 124.734 | 6 | 85 | 84,052 | 2.71288217 |
| r03 V3 | Semantic timeout; no final | 140.047 | 7 | 104 | 81,468; one call missing | 3.036190545 subtotal; total unknown |
| r04 V0 | Completed | 45.063 | 2 | 2 | 22,953 | 0.005263725 |
| r04 V1 | Completed | 90.563 | 4 | 68 | 76,903 | 2.363315045 |
| r04 V2 | Completed; partial retrieval | 116.609 | 6 | 89 | 81,372 | 2.791938605 |
| r04 V3 | Completed; partial Repair | 230.578 | 12 | 115 | 441,838 | 3.195760485 |
| r04 Primary | Completed | 47.880 | 2 | 60 | 44,640 | 1.3143941 |
| r05 V0 | Completed | 57.937 | 2 | 2 | 24,196 | 0.0058841 |
| r05 V1 | Completed | 92.360 | 4 | 68 | 77,884 | 2.36337917 |
| r05 V2 | Completed; partial retrieval | 120.859 | 6 | 85 | 82,094 | 2.71241542 |
| r05 V3 | Completed; partial Repair and trace | 219.204 | 12 | 113 | 375,403 | 3.177770735 |
| r05 Primary | Completed; retained unresolved evidence | 54.531248 | 2 | 75 | 36,698 | 1.598520975 |
| r06 V0 | Completed | 42.062 | 2 | 2 | 21,856 | 0.0047636 |
| r06 V1 | Completed | 107.672 | 4 | 68 | 79,194 | 2.36411967 |
| r06 V2 | Completed; partial retrieval | 119.156 | 6 | 85 | 81,825 | 2.71240242 |
| r06 V3 | Completed; partial Repair and trace | 236.516 | 16 | 99 | 393,477 | 2.834059005 |
| r06 Primary | Completed; retained unresolved evidence | 45.317531 | 2 | 55 | 27,714 | 1.25693485 |

The 22 Planner invocations total **2,345.472 native seconds, 113 model
calls, 1,290 HTTP sends and 2,285,112 observed tokens**; one historical call
still lacks usage. The separate r04/r05 Primaries retain 60/75 total HTTP sends and
44,640/36,698 tokens. r06 Primary adds **53 Google sends** (21 searches, 28 Details,
four route matrices), two model sends and **27,714 tokens**. Its native usage
interval is `2026-10-17T07:16:06.796489Z` to `07:16:52.114020Z`
(45.317531 seconds); the wrapper interval is `07:16:05.432248Z` to
`07:16:54.124551Z` (48.692303 seconds). These scopes remain separate. All new costs
are priced; execution retries and paired-access consumption are zero.

New generation cost is **USD 7.915344695** and Primary is **USD 1.256934850**,
totalling **USD 9.172279545**. Cumulative priced subtotal is **USD 44.423560975**.
The r03 incomplete request still has unknown usage/charge: two linked unpriced
records represent one request. Its retained **USD 0.01 reservation** covers the
standard-reference upper bound of USD 0.004695375 from the saved 4,795-token input
bound and 8,192 output cap. This is a reservation, not observed billing; historical
native totals remain null.

Including that reservation, cumulative reference budget accounting is
**USD 44.433560975**, leaving **USD 10.566439025** within the USD 55 allowance.
Before r06, accounted history was USD 35.261281430. Each sequential generation
required its current reference envelope plus the USD 3 Primary reserve to fit
the then-remaining allowance. Generation envelopes were V0 0.10, V1 4,
V2 4.50 and V3 5.51; the starting allowance covered their sum and the Primary
reserve. Generation has no native dollar hard stop; frozen runtime ceilings and
actual-cost checks between versions bounded continuation. Primary enforced its
native USD 3 cap. Exact cumulative billing remains unknown.

## Checks, assistance and preservation

r06 preflight passed input/date admission, worktree-local Python/imports/CLI,
63 locked dependencies, both local tokenizers, read-only TripWorld compatibility
and reviewed-context admission. The database check ran outside the already established
sandbox connectivity restriction, with zero embedding/model sends. The uv check
made no changes; credentials and project configuration were not reset.

The actual Primary package contains all four r06 final hashes, the original input,
reviewed spec and source-bound schedule, density and unrestricted transport objects.
Semantic/population readiness is ready, with zero missing role or occupancy reviews
and eligible missing-hours assessment enabled. Post-execution verification checked
**177 closed-inventory native files** and **13,485 prior files unchanged**. It read
saved results and hashes only, without replay or rescoring.

Parent `/root` owns preparation, orchestration, saved-evidence assessment,
accounting and documentation. Execution child `/root/case12_r06_execution` was
explicitly configured as `gpt-6.1-sol/medium` with fresh context and executed only
the frozen generation commands, each after a parent gate, and the exact later
Primary handoff. Original source-only author/reviewer records were reused. Agent
checks are distinct from human review. Available parent/child messages are retained
in the chat; complete hidden/tool transcripts and external billing remain unavailable.

Private roots are logical evidence identifiers rather than public dependencies:
`benchmark/scratch/case-12/work/run-r01/` through `run-r06/`, plus offline correction
aids. Failed/completed originals, commands, bindings, captures, usage/cost reports
and receipts remain retained. V1/V2 passive candidate captures and the genuine V3
same-run draft/final are available for separately authorized studies, subject to
the disclosed trace limitation. No old final was inserted into r06. Source-review
exposure limits and the excluded r01 reviewer remain in history. No candidate/paired
study, final acceptance or Git publication occurred.

| r06 evidence | SHA-256 |
| --- | --- |
| V0 final | `2c65185113a3d1fabcf06f31d5b85ae359aca20d20bcab257821f24bda0c4a6a` |
| V1 final | `958426e894c411c6d1bf02e27a98e0bcd2b33732795fdb207d441f7b5d896588` |
| V2 final | `8ba81e3705dca5372c0523a4508066b355c5616cf1f180de2b07a17cf1777439` |
| V3 final | `578f7e002eb0b1bfa7c33be27d1a70b32e4ffbe5bc22cd0032e8d3639b24ded5` |
| Reused reviewed requirements | `6601f742a2fa7ccb903b31c45c2580cad6d6a74524bdee781b0b5b5ca00114b9` |
| Frozen generation commands | `f4d009387f1fb6e0fa985360b2d5fe31dee37095569e556679599fbcbaefb976` |
| Native Primary preparation | `cd4283a4c7c9bc13d2b5929ba46ff0fcff06eacd479219df7f2c9c655ac63572` |
| Primary report | `a6ce9d8c932e3c12a8b841f0c5698a28bbefc587d4f39c0644a7aa6f8dc491e6` |

## Historical context

r01 used `b73c8eed09fafb6d54bee8684c5b2e7766515357`. V0-V2 completed with one
first-day primary visit and an empty rest day. V3's separate interpretation emitted
hard `semantic_3`, unsupported by the then-current shared gate. Its independent
spec retained that total as unsupported; numerical preparation was blocked. The
historical unsupported records remain unchanged. r01 passed 109 scoped checks;
an initial reviewer exposed to historical project outcomes was excluded, and a
distinct source-only replacement supplied the admitted review with exposure limits.

r02 merged main `cc779bb2ece7b312ab3d985cebdd5d6b64b209c3`, including
[PR #180](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/180) and
[PR #181](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/181), at execution
source `ba464335ea7765996b98e819bb31f9ed329ccf31`. A new independent spec used
`daily_visit_count` prospectively. V0 completed; V1 failed because its supply
projection left a Python date for `json.dumps`. The user authorized local repair:
`d523dd4` uses JSON-mode projection with graph and round-trip regression tests.
The graph test failed before the fix and passed afterward. Of 660 selected checks,
642 passed initially and 18 fixture setup errors passed after creating the missing
temporary parent and rerunning those 18. Ruff and both independent review axes passed;
the actual failed response also serialized correctly offline. No live r02 retry ran.

r03 used `215a3dfa5c29b2bc0751ed8d5cb7da0b8afc0339`. V0-V2 completed;
V3 generated a draft but its third candidate-semantic call timed out after 13.593
seconds, before a qualified final. The selected effective deadline was not saved.
Its wrapper then failed on `Decimal(None)`, leaving the original start-only receipt;
a separate reconciliation record retained the native failure without inventing a
wrapper end time. Native failure, usage, uncertain-cost and capture evidence remain
unchanged. No Primary ran for r03.

The offline correction from `ff645856` produced `174581a` (Repair allocation and
effective deadline records), `4848c7c` (null-safe completion receipts) and
`189dfa5` (documentation). Current policy values belong to the
[configuration reference](../../config/README.md#counting-timing-and-invariants).
Of 917 scoped offline checks, 914 passed initially; three old timing expectations
were corrected and all 90 tests in their modules passed. Controlled stage tests
reproduced the legacy short window and allowed 22/44-second semantic work under the
new policy while retaining the semantic ceiling and hard deadline checks. Ruff,
diff checks and independent Standards/Spec review passed. That correction itself
made no live provider calls; r04 is the separate authorized fresh execution.

Earlier source-only authors, reviewers and the interest actor were configured as
`gpt-6.1-sol/high`; execution actors used `gpt-6.1-sol/medium`. Local correction
reviewers inherited the parent configuration, whose exact runtime is unavailable.
Actual identities, times, hashes, excluded-review disclosure and available authentic
messages remain in the private roots and Git history. The r01-r03 revisions supply
no independent Primary scores. r04-r06 retain separate Primary selections;
case acceptance remains pending.

r04 used `189dfa51c8a86e79a3b6f911caceac8f943d9583` and completed all four versions
and one Primary. Its retained scores are V0 94.285714, V1/V2 65.714286 and V3
97.142857; both hard requirements passed in every version. Repair retained round
three after a later 255-character reason violated the 240-character application
bound. Its completed raw response contained no edits. The r04 third semantic call
completed within its 45-second allowance; no r03 failure or uncertain fee was erased.

The subsequent explanation correction `e4985d0` and audit correction `471f194`
passed 1,169 selected offline tests and Standards/Spec review before r05. The
[development record](../../docs/records/v0-v3/v3-development.md#repair-reason-length-recovery-2026-10-17)
owns that failure/correction evidence.

r05 used `5be3d028e1cf30889667309b09025d7872e66f8b` and retained Primary scores
V0 86.909091, V1 65.714286, V2 94.285714 and V3 100. All hard obligations passed.
Native Repair resolved five pace targets but retained a false 100-point rest-day
target, ending `ACCEPTED_PARTIAL / no_executable_candidate_operation`. Its complete
native result and truncated trace remain unchanged. Correction `b292a10` passed
646 selected offline tests and independent Standards/Spec review before r06;
`5aabd1c` documents that checkpoint. The
[development record](../../docs/records/v0-v3/v3-development.md#full-day-rest-pace-applicability-correction-2026-10-17)
owns that diagnosis and correction. These independent fresh generations are distinct
selections; their score differences do not establish the correction's causal effect.
