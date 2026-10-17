# Case-12: Sydney, Australia

## Current status

Revision **r04** completed V0-V3 once sequentially and one independent Primary on
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

All r04 executions used `189dfa51c8a86e79a3b6f911caceac8f943d9583` on
`codex/case-12-r02`, including the reviewed Repair timing and accounting correction.
The runtime and source bindings were fixed before execution. The user authorized
one fresh V0-V3 selection and one Primary under the cumulative **USD 40 reference
allowance**, preserving previous attempts and pausing after primary scoring.

## Requirements and observations

The independently authored and reviewed r02 RequirementSpec revision `"2"` applies
to the identical original input. Its exact bytes, distinct author/reviewer records,
original times and available authentic message excerpts were reused. Only the
schedule/density/transport batch identity and revision headers were rebound to r04;
this is not a fresh semantic review. Native admission accepted the reused material.

| Source requirement | Reviewed representation | r04 Primary result |
| --- | --- | --- |
| Exactly one sightseeing visit on 2026-10-22 | `daily_visit_count`, `primary_visits`, exact 1; no invented named subject. | PASS in V0-V3; each has a confirmed count of 1. |
| No activities or travel on 2026-10-25 | `protected_time`, full local day, `scheduled_commitments`. | PASS in V0-V3; submitted activities and touching transfers are both zero. |

Density uses a relaxed default with exact one and zero on those dates. Transport
modes are unrestricted outside the separate rest-day travel prohibition; the time
zone is `Australia/Sydney`. Nature, harbour views and flexibility remain soft
preferences without invented quotas. The original independently authored interest
meaning remains applicable; relevance and candidate-process studies have not run.

## Primary scores and limits

Native processing and acquisition are **complete**, evidence is **decidable**, and
there are no acquisition failures or UNKNOWN checks. The common dimensions are
requirements, grounding, non-overlap, opening and routes.

| Version | Five-dimension base | Mean daily density deduction | Primary score |
| --- | ---: | ---: | ---: |
| V0 | 100.00 | 5.714286 | **94.285714** |
| V1 | 80.00 | 14.285714 | **65.714286** |
| V2 | 80.00 | 14.285714 | **65.714286** |
| V3 | 100.00 | 2.857143 | **97.142857** |

All applicable five-dimension checks pass. V1/V2 have no applicable route checks:
`N/A / no_checks` contributes zero within the common five-dimension denominator,
so their base is 80 rather than 100. This is not a route FAIL. V0 has three PASS
route checks and V3 has four. Other dimensions contribute 100 in every version.

Density FAIL dates are 23 and 26 October for V0; 23, 24 and 26-28 October for
V1/V2; and 23 October for V3. Each has one primary visit and a default relaxed-pace
penalty of 20 on those dates. The mean uses all seven requested dates. The explicit
first-day count and rest day both match and receive zero density deduction. These
are pace-policy deductions, not failures of either hard source obligation.

The eligible missing-hours assessment completed for **13 cases** before the final
score. Model-supported public/exterior access PASS remains distinct from verified
API opening hours. Affordability and nature/harbour preference satisfaction remain
outside the two hard RequirementSpec obligations; the scores do not certify them.

V2/V3 retain partial-retrieval observations while their required workflow mechanisms
complete. V3 delivers the best retained final after five Repair rounds with
`ACCEPTED_PARTIAL / model_failed_no_retry`; the last proposal failed as
`StructuredOutputError:Invalid Repair patch`. The failed proposal was not adopted
or retried. No additional diagnosis or paired mechanism study was performed.

The previously failing third semantic call completed in **17.217 seconds**, with an
actual selected timeout of **45 seconds**; caller preparation had approximately
51.460 seconds remaining. All three semantic calls completed. This confirms the
new allocation worked in this attempt, without retrospectively establishing the
missing exact r03 deadline or a general latency guarantee.

## All-attempt resources and budget

Reference prices were rechecked on 17 October against official
[model](https://developers.openai.com/api/docs/models/gpt-6-luna),
[embedding](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[tool](https://developers.openai.com/api/docs/pricing) and
[Google](https://developers.google.com/maps/billing-and-pricing/pricing) sources.
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

The 14 Planner invocations total **1,349.706 native seconds, 61 model calls,
768 HTTP sends and 1,149,183 observed tokens**, with usage missing for one historical
call. Primary adds 58 Google sends (21 searches, 30 Details, seven route matrices),
two model calls and 44,640 tokens. Its usage interval is
`2026-10-17T04:52:24.211093Z` to `04:53:12.091106Z`; wrapper execution ran from
`04:52:22.507197Z` to `04:53:14.903902Z`. These timing scopes remain separate.
All r04 generation and Primary costs are priced, with no retries or new unpriced
events. Paired-access consumption remains zero.

The cumulative **priced subtotal is USD 25.393311030**. One r03 incomplete request
still has unknown usage/charge: its linked model/HTTP events are two unpriced
records for one request. A **USD 0.01 budget reservation** covers the conservative
standard-reference bound of USD 0.004695375, calculated from its saved 4,795-token
engineering input bound, 8,192 output cap and highest input/cache-write rate.
This is a reservation, not observed billing. Native historical cost totals remain
null and original records are unchanged.

Including that reservation, cumulative **reference budget accounting is
USD 25.403311030**, leaving **USD 14.596688970** within the USD 40 allowance.
The exact cumulative charge remains unknown. Before r04, accounted history was
USD 15.732639070; fresh generation reserved USD 14.10 (V0 0.10, V1 4, V2 4.50,
V3 5.50), Primary reserved USD 10, and USD 0.167360930 remained unallocated.
Actual new generation cost was USD 8.356277860 and Primary cost USD 1.3143941.
Generation has no native dollar hard stop; frozen runtime ceilings and cost checks
between versions bounded continuation. Primary had a native USD 10 cap.

## Checks, assistance and preservation

r04 preflight passed input/date admission, worktree-local Python/imports/CLI, 63
locked dependencies, both local tokenizers, read-only TripWorld compatibility and
native reviewed-context admission. Database preflight timed out inside the sandbox
and passed outside it without model/embedding sends; the uv check passed using a
workspace cache. No credentials or project configuration were reset.

Four-final intake was accepted, with zero missing role or occupancy reviews and a
ready declared-population profile. The parent checked that the actual preparation
contained the reviewed schedule, density and transport objects, enabled eligible
missing-hours assessment, and bound all four r04 finals. The Primary receipt's
closed file inventory and hashes were verified offline without rescoring.

Parent `/root` owns preparation, orchestration, saved-evidence inspection,
accounting and documentation. `/root/case12_r04_execution` was explicitly configured
as `gpt-6.1-sol/medium` with fresh context and executed the four frozen generation
commands and the single prepared Primary. A pre-execution automatic approval denial
was resolved by evidence of existing user authorization and the limited public-POI
provider data flow; the same command was approved before it started. The denial
caused no provider call or paid retry. Original source-only author/reviewer records
were reused; agent checks are separate from human review. Available parent/child
messages are retained, while full hidden/tool transcripts and external billing
remain unavailable.

Private roots are logical identifiers, not public dependencies:
`benchmark/scratch/case-12/work/run-r01/` through `run-r04/`, plus the local offline
correction aids. The r04 preservation audit verified **5,866 prior files unchanged**.
Raw failed and completed attempts, commands, manifests, source reviews, captures,
usage/cost reports and receipts remain retained. V1/V2 passive candidate captures
and the genuine V3 same-run draft/final are available for separately authorized
studies. No old-baseline final was inserted into r04. Source-only review exposure
limits and the excluded initial r01 reviewer remain documented in history.

| r04 evidence | SHA-256 |
| --- | --- |
| V0 final | `da650449164cfdad3578d6ea2d362982cd947c4fa406a87ad9f31b533570fd82` |
| V1 final | `0de56ebd4c151507ea80504ecc8a55f80b1f558727d767ac10b029c2e3cab303` |
| V2 final | `74f3098949eb9e549edf6ad9ca9eac6929a7d5d2ab20bbdcb672c8826204c429` |
| V3 final | `085cd31aa10a53fc11576a77b71ed6d9f6a7a543b65727928f5f1902f932513f` |
| Reused reviewed requirements | `6601f742a2fa7ccb903b31c45c2580cad6d6a74524bdee781b0b5b5ca00114b9` |
| Frozen generation commands | `06167c7e9bdb2dc9a74e4dc662e4e43d2ba142b227ba78803fc62152b3bbc39c` |
| Native Primary preparation | `0b16617bdead11ac358a8efa9e266bc3aff1363f74cbb1728b1869ab272bdf90` |
| Primary report | `3f0d151c502f87080e7c82f48331ce175ac2bf1761e148bb140718447e971e64` |

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
no independent Primary scores. The r04 Primary is a separate selection; case
acceptance remains pending.
