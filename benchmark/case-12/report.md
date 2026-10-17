# Case-12: Sydney, Australia

## Current status

Revision **r07** completed V0-V3 once sequentially and one independent Primary on
**17 October 2026 Australia/Sydney**. The authorized candidate, independent relevance,
same-run Repair and all-attempt resource reports are complete. The selected outputs
and original Primary scores remain unchanged. The researcher granted **automatic
acceptance to r07 on 17 October 2026 (Australia/Sydney)** with the stated limitations.
Local main-worktree integration and private-evidence migration completed on
**18 October 2026 (Australia/Sydney)**; blinded human review remains deferred.

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
applicable; independent relevance and captured candidate stages are reported below.
Affordability and full preference fulfillment are not certified by the two hard
obligation scores.

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
observations; their independent paired interpretation is reported below.

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

Across the 35 instrumented usage envelopes, observed totals are **146 model calls
including embeddings, 1,870 HTTP sends and 2,933,190 recorded tokens**. One historical
model call still lacks usage. External Codex usage/billing is outside this
instrumentation.

r07 generation cost is **USD 7.900275260** and Primary is **USD 1.274556225**,
totalling **USD 9.174831485**. At its Primary handoff, cumulative priced subtotal was
USD 53.598392460 and reference accounting was USD 53.608392460 including the retained
USD 0.01 reservation. The r03 incomplete request still has unknown usage/charge: two
linked unpriced records represent one request. The reservation covers the saved
standard-reference upper bound of USD 0.004695375 from 4,795 input tokens and an
8,192 output cap; it is not observed billing and native historical totals remain null.

The completed continuation adds independently captured costs:

| Acceptance stage | Google sends | Model sends | Observed tokens | Reference USD |
| --- | ---: | ---: | ---: | ---: |
| Independent venue facts | 69 Details | 0 | 0 | 1.725000000 |
| Three independent relevance batches | 0 | 3 | 33,594 | 0.009553275 |
| V3 pair-only missing-hours access | 0 | 1 | 5,010 | 0.000862425 |
| Imported paired observations and offline reporting | 0 | 0 | 0 | 0 |
| **Continuation total** | **69** | **4** | **38,604** | **1.735415700** |

The authorized stage ceilings were 69 Google sends, four model sends, zero retries
and USD 2.08. All 69 Details responses and four model requests completed; new
unpriced/missing-token/incomplete-send events are zero. Google acquisition used the
explicit `editorialSummary` mask at the freshly verified USD 0.025 Enterprise +
Atmosphere rate ([pricing](https://developers.google.com/maps/billing-and-pricing/pricing),
[field trigger](https://developers.google.com/maps/documentation/places/web-service/place-details)).
The three relevance batches retained 24/24/22 subjects with medium `gpt-6-luna`,
64,000 input/8,192 output ceilings and USD 0.02 per call. Paired access used its
separate one-call preparation and the same ceilings. Model costs remain the
[official OpenAI standard proxy](https://developers.openai.com/api/docs/models/gpt-6-luna)
for Foundry; actual account invoices and external Codex billing are unavailable.

Current cumulative priced subtotal is **USD 55.333808160**; including the unchanged
historical reservation, reference accounting is **USD 55.343808160**, leaving
**USD 6.656191840** within the approved **USD 62**. Unused continuation allowance is
USD 0.344584300. Imported source usage is informational and is not charged twice.
Planner, Primary, relevance/venue acquisition and paired-access scopes remain
separate in [the resource accounting](analysis/resources/accounting.json).

Before r07, accounted history was USD 44.433560975. Each sequential generation
required its then-remaining allowance to cover the unchanged envelope and USD 3
Primary reserve: V0 0.10, V1 4, V2 4.50 and V3 5.51. Generation had no native dollar
hard stop; frozen runtime ceilings and between-version actual-cost gates bounded
continuation. Primary enforced its native USD 3 cap. Continuation used bounded,
one-use captured requests with no automatic retries; no generation or new Primary
was dispatched.

## Candidate process and independent relevance

[Candidate-stage observations](analysis/poi-process/opportunities.json) retain
canonical Google/RAG lineage, omissions and independently scheduled memberships.
Counts are unique canonical places; Nearby-only references do not count as visits.

| Stage | V1 observed | V2 observed | V2 Google-only / RAG-only / mixed |
| --- | ---: | ---: | --- |
| Discovered | 59 | 69, partial | 50 / 10 / 9 |
| Admitted | 59 | 64 | 46 / 9 / 9 |
| Enriched | 32 | 42 | 29 / 9 / 4 |
| Supplied | 16 | 16 | 9 / 4 / 3 |
| Scheduled | 6 | 6 | 5 / 0 / 1 |

Other counts are complete observations within their captured scope. V2 discovery
has no exhaustive total: RAG returned 20 entities, with 11 resolved, eight matched
to Google observations and one non-unique fallback. Ten observed canonical places
are RAG-only introductions; none becomes a RAG-only scheduled visit. V1 records
27 unprocessed enrichment and 16 unselected supply omissions; V2 records five
admission-capacity, 22 unprocessed enrichment and 26 unselected supply omissions.
Scheduled sets retain five common places, with one V1-only and one V2-only place.
These independent generations do not establish causal RAG benefit.

Fresh independent venue facts cover 69 canonical places. Three isolated model
packets contain only the original request, reviewed RequirementSpec, authentic
original-only interest inventory and independent Google facts. Planner semantic
labels, query/rank/similarity, stage/fate, itineraries and scores were excluded.
The unresolved entity remains unassociated and UNKNOWN. These are external model
judgments, not human review; known labels retain factual field citations.

The three actual responses confirmed one native compound interest, nature **or**
harbour views, linked to unchanged `case-12-nature-harbour-views` at
`/soft_preferences/0`. [Both original interest axes](analysis/poi-process/interest-axes.json)
remain separately reported; the compound criterion is POI opportunity relevance,
not proof of satisfying both interests or an invented visit quota. The original
input, RequirementSpec and Primary bindings were not rewritten.

| Axis across 69 canonical places plus one unresolved entity | Relevant | Not relevant | UNKNOWN |
| --- | ---: | ---: | ---: |
| Nature | 16 | 49 | 5 |
| Harbour views | 7 | 38 | 25 |
| Native compound criterion | 20 | 33 | 17 |

[Native relevance](analysis/poi-process/relevance.json) records the following known
relevant counts. UNKNOWN judgments keep the affected complete counts unavailable.

| Stage | V1 relevant / UNKNOWN | V2 relevant / UNKNOWN |
| --- | ---: | ---: |
| Discovered | 15 / 12 | 20 / 16 |
| Admitted | 15 / 12 | 19 / 15 |
| Enriched | 10 / 5 | 15 / 10 |
| Supplied | 7 / 4 | 9 / 4 |
| Scheduled | 4 / 0 | 4 / 0 |

All inventoried canonical places have reviews; absent reviews are zero. Exact
candidate-chain conversions and full end-to-end V2-minus-V1 relevance deltas remain
unavailable because stages/reviews are partial. The complete scheduled-relevance
comparison is 4 versus 4, retaining three relevant places and exchanging one per
version. No corpus measurement or corpus-coverage claim is included.

## Same-run Repair evaluation

The [paired report](evaluation/v3-pair/report.json) uses the actual r07 V3 draft and
final-primary, with the same source-linked schedule, density and transport reviews.
The independent V2 final is a different generation. Native offline import matched
33/33 identity requests (20 searches, 13 Details) and 18/18 evidence requests
(13 Details, five matrices), all from independently acquired r07 Primary observations.
Original bytes/times and inherited usage remain explicit. Current imported sends,
retries and matrix elements are zero; no new paired Google request was needed.

A fresh pair-only missing-hours call judged three unique contexts covering five
stage occurrences: Harbour Bridge and Opera House each share unchanged draft/final
contexts; Darling Harbour occurs only in final-primary. All three are model-supported
PASS. Existing Primary responses were not rebound, and API hours coverage was not
improved by this judgment. The original four-version Primary report is unchanged.

| Same-run V3 stage | Primary visits | Five-dimension base | Mean density deduction | Paired total |
| --- | ---: | ---: | ---: | ---: |
| Draft | 5 | 80 | 25.714286 | 54.285714 |
| Final-primary | 11 | 100 | 0 | 100.000000 |

The signed paired gain is **45.714286 percentage points**: 25.714286 from density
and 20 from the included route dimension changing from no checks/zero contribution
to five PASS checks. It does not mean five route FAILs were repaired. Both hard date
requirements already PASS in the draft and continue to PASS in the final. Native
lineage establishes five retained occurrences, six additions, no losses and no
unresolved correspondence. [Repair research](analysis/repair/research.json) keeps
this pair separate from the independent V2-final/V3-final difference of 34.285714
points and their different populations/masks.

The saved [round/process material](analysis/repair/process.json) records:

| Round | Adopted additions | Rejected proposals |
| --- | --- | --- |
| 1 | Hyde Park on 27 October | None |
| 2 | QVB on 23 October; MCA on 24 October; Sydney Tower Eye on 27 October | Additional MCA visits on 26/28 October: revisit not authorized |
| 3 | Darling Harbour on 26 October; Art Gallery of NSW on 28 October | None |

The first-day exact-one and full rest-day protections remain intact. The ordinary
blank 27 October is filled, and 26/28 October each reach two primary visits. Actual
26 October transport uses a basic DRIVE estimate of 964 seconds plus 600 reserve;
28 October uses WALK at 1,421 seconds over 1,707 metres. Both fit their saved gaps.
Car availability/cost and future traffic are not certified. Structured soft-pace
transport was presented and used; semantic rejection/refill and repeated-empty
proposal guards were not triggered live. Their earlier offline test coverage is
not presented as new live evidence.

## Material and archive readiness

[Daily schedules and POI origins](itinerary.md), reviewed requirements, interests,
selected generation usage/provenance, Primary/pair reports and process/resource
views are indexed in [the material index](material-index.json). Shared JSON
references expand losslessly; a delta reconstructs the complete V3 draft, including
recommendation differences. Public views exclude raw provider/model responses,
private prompts/transcripts and credentials. They are presentation material; native
closed evidence and original source bytes remain private.

Seven retrospective revision-specific native resource declarations preserve 28
planned slots: 26 dispatched, 23 native workflow completions, three failures and
two unstarted r02 slots. r01 V3's clarification-before-generation is retained under
its authentic failed workflow declaration. No historical attempt is silently
replaced by r07 success, and no pooled version-quality conclusion is inferred.
All-attempt consumption and the selected r07 comparison remain separate.

The private archive at `benchmark/scratch/case-12/archive/` retains **25,261 logical
files / 1,089,419,538 bytes**, with **2,911 unique byte sequences** stored once in a
**24,806,386-byte ZIP**. Ten compiled-cache files and 1,304 synthetic pytest-tree
files are explicitly excluded; original working evidence remains retained until
private-evidence migration and its verification permit later cleanup.

Fresh restoration verified every retained file, **45 public indexed files and 50
original-source bindings**, lossless shared references/draft reconstruction, four
current native report tracks and six historical resource reconstructions. Native
readers rebuilt the exact saved Primary quality and current same-run pair. Network
connections and access to original working data were blocked during reconstruction.
All 17,230 prior working files remain unchanged.
Original absolute preparation bindings, receipts and source hashes are preserved;
these source-based portable checks do not make consumed, path-bound execute/replay
commands reusable. The temporary restored tree is removed after verification.
Historical missing usage, actual invoices, complete hidden/tool transcripts and
external Codex billing remain unavailable.

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
human review. Continuation execution child `/root/case12_acceptance_execution` was
separately configured as `gpt-6.1-sol/medium` with fresh context and executed only the
frozen venue, three relevance and paired-access commands after parent budget/source
gates. Parent-owned offline preparation, source assessment, native report assembly,
public views and archive verification made no further provider/model sends.
Available parent/child messages are retained in the chat; complete hidden/tool
transcripts and external billing remain unavailable.

Private roots are historical evidence identifiers, not public dependencies:
`benchmark/scratch/case-12/work/run-r01/` through `run-r07/`, plus offline correction
aids. Failed/completed originals, commands, bindings, captures, usage/cost reports
and receipts remain retained. V1/V2 passive candidate captures and the genuine V3
same-run draft/final bind the completed process reports. No old final was inserted
into r07. Source-review exposure limits and the excluded r01
reviewer remain in history. The researcher's separate acceptance decision is recorded
below. All authorized paid stages are complete; unused allowance does not authorize
more calls.

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

## Acceptance

**Accepted on 17 October 2026 (Australia/Sydney).** The researcher explicitly accepted
case-12 r07 and its disclosed limitations. The accepted selection is the unchanged
original request, reused reviewed RequirementSpec revision 2, the exact r07 V0-V3 outputs
and original Primary, current same-run paired evidence, source-bound mechanism/
resource reports and verified private archive. The material index identifies the
public views and their original sources.

Steps 1-10 of the [case workflow](../README.md#workflow-and-responsibilities) are complete.
Acceptance retains partial RAG discovery, relevance UNKNOWNs, model-supported access,
unverified transport availability/cost and historical accounting limits. The semantic
refill and empty-proposal guards were not exercised live. This decision does not
certify affordability, complete preference fulfillment or general version superiority.
Step 11, real blinded human review, remains deferred.

### Main-worktree integration

Local merge `d6f3e8e` integrates worker head `6babb0d` into main baseline
`3fbb2ef`, preserving the original implementation, correction and acceptance commits.
The README resolution retains main's existing cases and workflow. Subsequent merge
`b41e8c7` includes remote main `7408df9201965386b755af07ca43a35bae00fc46`
(PR #189), whose five documentation changes preserve case-08's completed acceptance,
PR #188 delivery and completed Issues #157/#182. No shared fix was applied twice.

The full initial backend run completed with **4,608 passed, 16 skipped and seven
failures**. Three failures were sandbox-denied Windows junction fixtures; the
unchanged tests passed outside the sandbox (one plus two). Four passive-capture
parity failures compared newly recorded live deadline balances. The test-only
normalizer now excludes `remaining_seconds`, retaining exact itinerary and provider/
model-call comparisons; both affected modules pass **24 tests**. All failures are
resolved; the corrected full suite was not repeated. Ruff and formatting pass for
38 changed Python files. Both independent Standards and Spec reviews, including
the committed test correction, report zero actionable findings. Skipped environments
remain unverified; frontend code was unchanged and was not retested.

The complete private archive and delivery package were copied byte-for-byte to
`benchmark/scratch/case-12/` in the main worktree. Receiving checks verify every
retained file, public view and source binding. Current main rebuilds opportunities
and relevance exactly, but correctly rejects historical Repair rebuilding at the
strict opening-packet implementation fingerprint: newer evaluator files differ
from its recorded producer. This is not a current-main replay pass.

The exact committed producer source at `6babb0d` is retained separately. Its isolated
source readers rebuild all ten saved reports exactly with network connections and
both original working-evidence roots blocked. Original native bytes, scores,
preparations and consumed execution bindings are unchanged. The original and
receiving verification results remain separate; acceptance/integration metadata is
bound to unchanged indexed content. The temporary receiving restoration was removed;
the worker and its original private evidence remain retained.

Private receiving evidence and reproduction instructions are historical identifiers
under `benchmark/scratch/case-12/integration/`. This integration added no project
provider calls, generation, Primary, rescoring or human answers. Reference accounting
is unchanged. Git publication remains separate from this completed local integration.

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
no independent Primary scores. r04-r07 retain separate Primary selections; r07 is
the accepted automatic selection, while r04-r06 remain historical evidence.

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
