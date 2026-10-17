# Case-12: Sydney, Australia

## Current status

Revision **r05** completed V0-V3 once sequentially and one independent Primary on
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

All r05 executions used `5be3d028e1cf30889667309b09025d7872e66f8b` on
`codex/case-12-r02`, including the reviewed bounded explanation compression and
its audit correction. Source, runtime and commands were bound before execution.
The user authorized one fresh V0-V3 selection and one Primary under the cumulative
**USD 40 reference allowance**, preserving previous attempts and pausing after
primary scoring. This selection uses the existing Planner behavior and scoring
contracts without changing the input or adjusting scores after seeing results.

## Requirements and observations

The independently authored and reviewed r02 RequirementSpec revision `"2"` applies
to the identical original input. Exact spec bytes, distinct author/reviewer records,
original times and available authentic message excerpts were reused. Only batch
identity/revision headers in the schedule/density/transport contexts were rebound
to r05. Native admission accepted this reuse; it is not a fresh semantic review.

| Source requirement | Reviewed representation | r05 Primary result |
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

Native processing and acquisition are **complete**. Evidence is **unresolved**
because V0 retains two opening UNKNOWN checks and one route UNKNOWN, with no
acquisition failures. Common dimensions are requirements, grounding, non-overlap,
opening and routes.

| Version | Five-dimension base | Mean daily density deduction | Primary score |
| --- | ---: | ---: | ---: |
| V0 | 86.909091 | 0.000000 | **86.909091** |
| V1 | 80.000000 | 14.285714 | **65.714286** |
| V2 | 100.000000 | 5.714286 | **94.285714** |
| V3 | 100.000000 | 0.000000 | **100.000000** |

Dimension cells show score followed by **PASS/FAIL/UNKNOWN** counts:

| Dimension | V0 | V1 | V2 | V3 |
| --- | ---: | ---: | ---: | ---: |
| requirements | 100.000000 (2/0/0) | 100.000000 (2/0/0) | 100.000000 (2/0/0) | 100.000000 (2/0/0) |
| grounding | 81.818182 (9/2/0) | 100.000000 (6/0/0) | 100.000000 (9/0/0) | 100.000000 (11/0/0) |
| non_overlap | 100.000000 (16/0/0) | 100.000000 (6/0/0) | 100.000000 (12/0/0) | 100.000000 (16/0/0) |
| opening | 72.727273 (8/1/2) | 100.000000 (6/0/0) | 100.000000 (9/0/0) | 100.000000 (11/0/0) |
| routes | 80.000000 (4/0/1) | N/A; contributes 0 (0/0/0) | 100.000000 (3/0/0) | 100.000000 (5/0/0) |

V0's independent identity judgments reject two address claims: Watsons Bay's
submitted address refers to another place, and Sydney Observatory's address is incorrect.
The Observatory visit also contains 5,100 seconds confirmed closed by the retained
opening evidence. Manly Beach remains UNKNOWN because optional swimming conditions
were explicitly unchecked; Watsons Bay's unresolved physical identity leaves its
opening check and associated route UNKNOWN. These observations remain in the
original report without corrective rescoring.

V1 has no applicable same-day route checks. Its `N/A / no_checks` contributes zero
within the common five-dimension denominator, giving an 80-point base; it is not
a route FAIL or PASS. V2/V3 have three/five PASS route checks. V1 density FAIL dates
are 23, 24 and 26-28 October; V2's are 26 and 28 October. Each has one primary visit
and a relaxed-pace penalty of 20 on those dates. The mean uses all seven requested
dates. V0/V3 have no density deduction. The exact first day and rest day both match.

Eligible missing-hours assessment completed for **16 cases**: 15 received
model-supported access PASS and one remained UNKNOWN. Complete API evidence counts
for V0-V3 are 4/3/6/7; model-supported decidable counts are 5/3/3/4. Model-supported
public/exterior access does not supply verified API hours. V3's 100-point Primary
is this selection's result, not a general quality or affordability guarantee.

V2/V3 retain partial-retrieval observations while their required workflow mechanisms
complete. V3 returns `ACCEPTED_PARTIAL / no_executable_candidate_operation` after
six rounds, retaining round five. It made five proposal sends; the final round
was skipped. No explanation-compression send was observed: all six round records
have empty `reason_compression` objects and native model stages contain no
compression event. This attempt does not exercise the new live compression path.

V3's physical `run.json` exists but is marked truncated: the 19,796,641-byte source
payload exceeded the trace limit and produced a 10,740,182-byte preview artifact.
Its evidence index therefore lacks a usable `finished_trace` and marks collection
partial. The complete 19,012,246-byte native result retains the genuine draft/final,
Repair records and selected itinerary; native intake admitted the four finals.
The source trace remains unchanged. This limits later trace inspection without
invalidating the already admitted Primary sources.

## All-attempt resources and budget

r05 reuses r04's frozen official reference prices dated 17 October, valid for this
same-day execution, rather than claiming another price lookup. Sources are the
official [model](https://developers.openai.com/api/docs/models/gpt-6-luna),
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

The 18 Planner invocations total **1,840.066 native seconds, 85 model calls,
1,036 HTTP sends and 1,708,760 observed tokens**; one historical call still lacks
usage. r04 Primary adds 58 Google sends, two model calls and 44,640 tokens.
r05 Primary adds **73 Google sends** (26 searches, 35 Details and 12 route matrices),
two model calls and **36,698 tokens**. Its native usage interval is
`2026-10-17T05:44:09.872535Z` to `05:45:04.403783Z` (54.531248 seconds);
the wrapper ran from `05:44:08.380848Z` to `05:45:07.381828Z` (59.000980 seconds).
These timing scopes remain separate. All new costs are priced; retries and
paired-access consumption are zero.

New generation cost is **USD 8.259449425** and Primary is **USD 1.598520975**,
totalling **USD 9.857970400**. Cumulative priced subtotal is **USD 35.251281430**.
The r03 incomplete request still has unknown usage/charge: two linked unpriced
records represent one request. Its retained **USD 0.01 reservation** covers the
standard-reference upper bound of USD 0.004695375 from the saved 4,795-token input
bound and 8,192 output cap. It is not observed billing; native historical totals
remain null.

Including that reservation, cumulative reference budget accounting is
**USD 35.261281430**, leaving **USD 4.738718570** within the USD 40 allowance.
Before r05, accounted history was USD 25.403311030. Each sequential generation
required its current reference envelope plus the USD 3 Primary reserve to fit
the then-remaining allowance. The generation envelopes were V0 0.10, V1 4,
V2 4.50 and V3 5.51; future versions were contingent on actual prior costs, not
simultaneously reserved. Generation has no native dollar hard stop; frozen runtime
ceilings and checks between versions bounded continuation. Primary enforced its
native USD 3 cap. Exact cumulative billing remains unknown.

## Checks, assistance and preservation

r05 preflight passed input/date admission, worktree-local Python/imports/CLI,
63 locked dependencies, both local tokenizers, read-only TripWorld compatibility
and reviewed-context admission. Database preflight timed out inside the sandbox
and passed outside it without model/embedding sends. The uv check made no changes;
no credentials or project configuration were reset.

The actual Primary package contains all four r05 final hashes, the original input,
reviewed spec and the source-bound schedule, density and unrestricted transport
objects. Semantic/population readiness is ready, with zero missing role or occupancy
reviews and eligible missing-hours assessment enabled. Post-execution verification
checked **237 closed-inventory native files** and **9,685 prior files unchanged**.
It read saved results and hashes only, without replay or rescoring.

Parent `/root` owns preparation, orchestration, saved-evidence assessment,
accounting and documentation. Execution child `/root/case12_r05_execution` was
explicitly configured as `gpt-6.1-sol/medium` with fresh context and executed only
the frozen four generation commands and the later exact Primary handoff. Existing
source-only author/reviewer records were reused. Agent checks are distinct from
human review. Available parent/child messages are retained in the chat; full
hidden/tool transcripts and external billing remain unavailable.

Private roots are logical evidence identifiers rather than public dependencies:
`benchmark/scratch/case-12/work/run-r01/` through `run-r05/`, plus the offline
correction aids. Failed and completed originals, commands, bindings, captures,
usage/cost reports and receipts remain retained. V1/V2 passive candidate captures
and the genuine V3 same-run draft/final are available for separately authorized
studies, subject to the disclosed r05 trace truncation. No old final was inserted
into r05. Source-review exposure limits and the excluded r01 reviewer remain in
history. No candidate/paired study, final acceptance or Git publication occurred.

| r05 evidence | SHA-256 |
| --- | --- |
| V0 final | `b1d6f291b02954d5d9cdb5f60444f76dd70f96e823377608c9e231b0dd0760e9` |
| V1 final | `f7be662a796bf5eac37bf0e57afd6ade4dee06c486b0ef58bbe4c75bae518d47` |
| V2 final | `65a11e3a160bfc45838aef4da5ab041859271c6d18fb715c1c78dadf9614cc01` |
| V3 final | `5d9e4b1de2e4efb481f23276c426e5ae7830a7922f71b1d50b0f24047054120e` |
| Reused reviewed requirements | `6601f742a2fa7ccb903b31c45c2580cad6d6a74524bdee781b0b5b5ca00114b9` |
| Frozen generation commands | `4326f5d1c7e68730ecccd588a9c05c947d9791e6d1501d1ec78c29c1baa41d19` |
| Native Primary preparation | `f4cd55efa281ae8156e3429706f1109a5f4d23c461b5ca7e0c273622ee355fd2` |
| Primary report | `ed1ceae50c5a6b32cdcf7e6d0dd0300f3c57b6784c1a5f08499ee262fb468159` |

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
no independent Primary scores. r04 and r05 retain separate Primary selections;
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
