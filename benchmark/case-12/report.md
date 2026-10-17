# Case-12: Sydney, Australia

## Current status

Revision **r07** completed V0-V3 once sequentially and one independent Primary on
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

All r07 executions used `3a7276284c428b9dce3bc59e643117cdc9bc8307` on
`codex/case-12-r02`, including the reviewed opportunity-preparation and empty-proposal
correction in [Issue #184](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/184).
The user authorized one fresh V0-V3 selection and one Primary, preserving previous
attempts and pausing after scoring. Before dispatch, the cumulative reference
allowance was raised from USD 55 to **USD 62**: the existing USD 44.433560975
accounting plus unchanged generation envelopes and Primary reserve required
USD 61.543560975. Source, runtime, commands and actual budget admission were frozen.
The input and evaluator scoring contracts remain unchanged; no result was rescored.

## Requirements and observations

The independently authored and reviewed r02 RequirementSpec revision `"2"` applies
to the identical original input. Exact spec bytes, distinct author/reviewer records,
original times and available authentic message excerpts were reused. Only batch
identity/revision headers in the schedule/density/transport contexts were rebound
to r07. Native admission accepted this reuse; it is not a fresh semantic review.

| Source requirement | Reviewed representation | r07 Primary result |
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

Native processing and acquisition are **complete**, evidence is **decidable**, and
acquisition failures and reported UNKNOWNs are empty. Common dimensions are
requirements, grounding, non-overlap, opening and routes. These statements concern
this declared scoring scope; model-supported access and actual billing retain the
separate limits below.

| Version | Five-dimension base | Mean daily density deduction | Primary score |
| --- | ---: | ---: | ---: |
| V0 | 100.000000 | 11.428571 | **88.571429** |
| V1 | 80.000000 | 14.285714 | **65.714286** |
| V2 | 80.000000 | 14.285714 | **65.714286** |
| V3 | 100.000000 | 0.000000 | **100.000000** |

Dimension cells show score followed by **PASS/FAIL/UNKNOWN** counts:

| Dimension | V0 | V1 | V2 | V3 |
| --- | ---: | ---: | ---: | ---: |
| requirements | 100.000000 (2/0/0) | 100.000000 (2/0/0) | 100.000000 (2/0/0) | 100.000000 (2/0/0) |
| grounding | 100.000000 (7/0/0) | 100.000000 (6/0/0) | 100.000000 (6/0/0) | 100.000000 (11/0/0) |
| non_overlap | 100.000000 (8/0/0) | 100.000000 (6/0/0) | 100.000000 (6/0/0) | 100.000000 (16/0/0) |
| opening | 100.000000 (7/0/0) | 100.000000 (6/0/0) | 100.000000 (6/0/0) | 100.000000 (11/0/0) |
| routes | 100.000000 (1/0/0) | N/A; contributes 0 (0/0/0) | N/A; contributes 0 (0/0/0) | 100.000000 (5/0/0) |

There are no FAIL or UNKNOWN checks in these five common dimensions. V1/V2 have
no applicable same-day route checks: native `N/A / no_checks` contributes zero
within the five-dimension denominator, producing an 80-point base. Density has
separate FAIL dates: 24 and 26-28 October for V0; 23, 24 and 26-28 for V1/V2.
Each of those dates has one primary visit and a 20-point deduction. V3 has no
density FAIL dates; its independently counted daily primary totals are
`1, 2, 2, 0, 2, 2, 2`. Means include all seven requested dates. No hard obligation
failure is inferred from a default pace deduction.

Eligible missing-hours assessment completed before scoring for **10 contexts**, all
with model-supported access PASS. Complete API opening evidence covers **5/7, 4/6,
3/6 and 8/11** V0-V3 checks; model-supported decidable counts are **2/2/3/3**.
Model-supported public/exterior access is not verified API hours. Scores describe
this selection and these evidence rules, not general travel quality or affordability.

V2/V3 retain partial-retrieval observations while their required workflow mechanisms
complete. V3 returns **`ACCEPTED_COMPLETE / authorized_targets_complete`**, retaining
round three after three proposal sends. Original/final native pace penalty totals
are **180/0**, with means **25.714286/0**; no adopted improvement targets remain.
The first-day and rest-day protections remain intact. Two candidate-semantic calls
and three proposal calls are included in V3's nine model events, including its
embedding. No explanation-compression send occurred. These are native operational
observations; candidate/paired mechanism studies remain deferred.

The V3 result is complete at **9,203,113 bytes** and its physical trace is complete,
untruncated at **9,724,182 bytes**. Its evidence index reports collection available
with no missing fields. The earlier truncated r05/r06 traces remain preserved; they
do not describe r07's trace. Native intake admitted the four new finals.

## All-attempt resources and budget

r07 reuses r06's unchanged same-day frozen official reference prices, valid
16-18 October 2026; no fresh lookup is claimed. Sources are the official
[model](https://developers.openai.com/api/docs/models/gpt-6-luna),
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

| r07 V0 | Completed | 40.812 | 2 | 2 | 21,885 | 0.004734975 |
| r07 V1 | Completed | 94.890 | 4 | 68 | 76,546 | 2.363043545 |
| r07 V2 | Completed; partial retrieval | 123.719 | 6 | 85 | 81,877 | 2.712065045 |
| r07 V3 | Completed; complete Repair; partial retrieval | 170.500 | 9 | 104 | 294,640 | 2.820431695 |
| r07 Primary | Completed; evidence decidable | 43.908855 | 2 | 58 | 25,474 | 1.274556225 |

The 26 Planner invocations total **2,775.393 native seconds, 134 model calls,
1,549 HTTP sends and 2,760,060 observed tokens**; one historical call still lacks
usage. The separate r04/r05/r06 Primaries retain 60/75/55 HTTP sends and
44,640/36,698/27,714 tokens. r07 generation adds 21 model calls, 259 HTTP sends,
474,948 tokens and 429.921 native seconds. r07 Primary adds **56 Google sends**
(20 searches, 30 Details and six route matrices), two model sends and **25,474 tokens**.
Its native usage interval is `2026-10-17T08:12:07.290603Z` to
`08:12:51.199458Z` (43.908855 seconds); the wrapper interval is `08:12:05.770392Z`
to `08:12:55.159631Z` (49.389239 seconds). These scopes remain separate. All new
costs are priced; execution retries and paired-access consumption are zero.

New generation cost is **USD 7.900275260** and Primary is **USD 1.274556225**,
totalling **USD 9.174831485**. Cumulative priced subtotal is **USD 53.598392460**.
The r03 incomplete request still has unknown usage/charge: two linked unpriced
records represent one request. Its retained **USD 0.01 reservation** covers the
standard-reference upper bound of USD 0.004695375 from the saved 4,795-token input
bound and 8,192 output cap. This is a reservation, not observed billing; historical
native totals remain null.

Including that reservation, cumulative reference budget accounting is
**USD 53.608392460**, leaving **USD 8.391607540** within the approved **USD 62**.
Before r07, accounted history was USD 44.433560975. Each sequential generation
required its reference envelope plus the USD 3 Primary reserve to fit the then-remaining
allowance: V0 0.10, V1 4, V2 4.50 and V3 5.51. The increased starting allowance
covered their sum and Primary. Generation has no native dollar hard stop; frozen
runtime ceilings and actual-cost checks between versions bounded continuation.
Primary enforced its native USD 3 cap. Exact cumulative billing remains unknown.

## Checks, assistance and preservation

r07 preflight passed input/date admission, worktree-local Python/imports/CLI,
63 locked dependencies, both local tokenizers, read-only TripWorld compatibility
and reviewed-context admission. The database check ran outside the already established
sandbox connectivity restriction, with zero embedding/model sends. The uv check
made no changes; credentials and project configuration were not reset.

The actual Primary package contains all four r07 final hashes, original input,
reviewed spec and source-bound schedule, density and unrestricted transport objects.
Semantic/population readiness is ready, with zero missing role or occupancy reviews
and eligible missing-hours assessment enabled. Post-execution verification checked
**186 closed-inventory native files** and **17,230 prior files unchanged**. It read
saved results and hashes only, without replay, rescoring or studies 7-9.

Parent `/root` owns preparation, orchestration, saved-evidence assessment, accounting
and documentation. Execution child `/root/case12_r07_execution` was explicitly configured
as `gpt-6.1-sol/medium` with fresh context and executed only the frozen generation
commands, each after a parent gate, and the exact later Primary handoff. Original
source-only author/reviewer records were reused. Agent checks are distinct from
human review. Available parent/child messages are retained in the chat; complete
hidden/tool transcripts and external billing remain unavailable.

Private roots are historical evidence identifiers, not public dependencies:
`benchmark/scratch/case-12/work/run-r01/` through `run-r07/`, plus offline correction
aids. Failed/completed originals, commands, bindings, captures, usage/cost reports
and receipts remain retained. V1/V2 passive candidate captures and the genuine V3
same-run draft/final remain available for separately authorized studies. No old
final was inserted into r07. Source-review exposure limits and the excluded r01
reviewer remain in history. No candidate/paired study, final acceptance or Git
publication occurred. Unused allowance grants no further execution authority.

| r07 evidence | SHA-256 |
| --- | --- |
| V0 final | `da3ac570fbcf939fcf32611a5e150a0d2e183a50057f25b76379da11f4b85240` |
| V1 final | `29016b1916c6ae493ff76e81274b6c9ee00aced9349aa611034498dae14a8191` |
| V2 final | `299f5cfea2b9492aab9cf6f5bec4b2c8a93cabd5195bd3c863531dde7da497af` |
| V3 final | `4a4bfa560d2e6a3ca6b1cdbde499aac735f70f42efe8606de2c90228f03af849` |
| Reused reviewed requirements | `6601f742a2fa7ccb903b31c45c2580cad6d6a74524bdee781b0b5b5ca00114b9` |
| Frozen generation commands | `28c3ba61f5aa207c4b1abdbce8425232ffaa2e8f036138e6d1c963ebbbab0f7a` |
| Native Primary preparation | `d306f408473c22998965089813167cf009ada17c7e6f49e2688d1f98f9c95e12` |
| Primary report | `9ce1bd6aac0d41b08043f63a2d7eedc35ba16727ab9a8d7991df19fa246357b2` |

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
no independent Primary scores. r04-r07 retain separate Primary selections;
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

r06 used `5aabd1c45c5c5d6180424fb920fbb324822b2bd9` and retained Primary scores
V0 71.428571, V1 54.285714, V2 88.571429 and V3 94.285714. Both hard obligations
passed in every version. Repair retained round one after six proposals, leaving
26 and 28 October at one visit and 20 pace points each; the former false rest-day
target was absent. Its complete native result and truncated physical trace remain
unchanged. The subsequent correction in #184 added structured soft-pace transport,
post-filter replenishment and empty-input handling. Implementation `7d1fe3c`, review
correction `421a83d` and documentation `3a72762` passed 713 selected offline tests
and final Standards/Spec review. The
[development record](../../docs/records/v0-v3/v3-development.md#repair-opportunity-preparation-and-empty-proposal-correction-2026-10-17)
owns those diagnoses and corrections. r07 is a separately authorized fresh generation;
its scores do not establish a causal gain from independent version/run differences.
