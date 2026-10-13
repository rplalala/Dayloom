# Case-01: Sydney evaluation report

The initial case-01 dataset contains the selected V0-V3 outputs for the
[original request](../inputs/case-01.json): Sydney, Australia, 13-15 October 2026,
three days, one traveler and an AUD 900 whole-trip budget, with no additional
preferences. The source batch is `case01-20261012T220558Z`, revision `3`.
Generation, primary evaluation and opening assessment retain their actual execution
dates and producer identities.

The independently evaluated primary totals are **67.7778, 83.9583, 89.5238 and
91.6667** for V0-V3. With the accepted opening assessment, the totals are
**73.3333, 93.3333, 96.6667 and 100**. API-only and model-supplemented results
remain separate. The same-run V3 pair records the actual three-deletion Repair.

## Acceptance

The human user accepted the selected input, results and stated limitations on
**14 October 2026 Australia/Sydney**, then designated these selected results as the
initial case-01 dataset. The approved source package is commit `3d50891`; this
presentation preserves its selected itinerary and evaluation values.

The [material index](material-index.json) binds the selected sources and current
publication hashes. Requirements, generation/evaluation admission, primary-score
handoff, candidate/Repair analysis, source and resource consistency, private
retention, restoration and native offline replay are complete. Independent
Standards and Spec review found no outstanding issues. Blinded human assessment
remains a separate deferred stage. Git publication and Issue closure have not occurred.
The case follows the [common acceptance workflow](../README.md#per-case-execution-and-joint-review).

## Case materials

| Material | Files |
| --- | --- |
| Readable schedules and changes | [Itineraries and RAG labels](itinerary.md) |
| Reviewed request semantics | [RequirementSpec](requirements/reviewed-requirements.json), [interest inventory](interests/interests.json) |
| Selected itineraries | [V0](generation/v0/itinerary.json), [V1](generation/v1/itinerary.json), [V2](generation/v2/itinerary.json), [V3](generation/v3/itinerary.json) |
| Same-run V3 draft | [Lossless draft delta](generation/v3/draft.json) |
| Generation usage | [V0](generation/v0/usage.json), [V1](generation/v1/usage.json), [V2](generation/v2/usage.json), [V3](generation/v3/usage.json) |
| Producer provenance | [V0](generation/v0/provenance.json), [V1](generation/v1/provenance.json), [V2](generation/v2/provenance.json), [V3](generation/v3/provenance.json) |
| Runtime policies | [V0-V2](generation/runtime-policy.json), [V3](generation/v3/runtime-policy.json) |
| Independent evaluation | [API-only quality](evaluation/primary/quality-report.json), [V3 pair](evaluation/v3-pair/pair-report.json), [opening assessment](evaluation/opening/report.json), [supplemented quality](evaluation/opening/quality-report.json) |
| Candidate process | [Stage analysis](analysis/poi-process/opportunities.json), [RAG origins](generation/rag-origins.json), [interest applicability](analysis/poi-process/relevance.json) |
| Repair | [Actual lineage and independent final differences](analysis/repair/repair.json) |
| Resources | [Attempt inventory](analysis/resources/population.json), [descriptive tradeoffs](analysis/resources/tradeoffs.json), [accounting](analysis/resources/accounting.json) |

## Source provenance

| Version | Recorded generation source | Recorded run |
| --- | --- | --- |
| V0 | `b3ddccd5b462367d35eff12f8aa9cfe10f840557` | `case01-v0-20261012T232752Z` |
| V1 | `b3ddccd5b462367d35eff12f8aa9cfe10f840557` | `case01-v1-20261012T232752Z` |
| V2 | `b3ddccd5b462367d35eff12f8aa9cfe10f840557` | `case01-v2-20261012T232752Z` |
| V3 | `a970002b2373a0c9059040781fdba267cc01df91` | `case01-v3-repair140-followup-20261013T064153Z` |

Independent primary and pair scoring use source `a970002`; the opening assessment
uses `815fcae`. The dataset contains source-bound outputs from the recorded revisions,
with compatible inputs/evaluation contracts; it is not a single-revision generation
experiment. Original dates, source hashes, run IDs and native receipts are unchanged.

Distinct source-only requirement author/reviewer executions produced empty subjects,
obligations, soft preferences and unresolved requirements. The independent interest
inventory is also empty. Generated sightseeing choices do not create user interests.

## Primary scoring

Counts are PASS / FAIL / UNKNOWN. The common mask is grounding, non-overlap,
opening and routes; requirements are N/A because no checks apply. Overall totals
include the native pace deduction. All non-overlap checks PASS.

| Version | API-only overall / 100 | Pace deduction | Grounding | Opening | Routes |
| --- | ---: | ---: | --- | --- | --- |
| V0 | 67.7778 | 10.0000 | 8 / 0 / 1 | 5 / 1 / 3 | 4 / 0 / 2 |
| V1 | 83.9583 | 6.6667 | 8 / 0 / 0 | 5 / 0 / 3 | 5 / 0 / 0 |
| V2 | 89.5238 | 3.3333 | 7 / 0 / 0 | 5 / 0 / 2 | 4 / 0 / 0 |
| V3 | 91.6667 | 0.0000 | 6 / 0 / 0 | 4 / 0 / 2 | 3 / 0 / 0 |

API-only scoring has 13 UNKNOWN checks: one identity, ten opening and two routes.
V0's Australian Museum visit on 15 October, 09:30-12:00 Sydney time, overlaps
a confirmed closed interval by 1,800 seconds. Independent generation differences
do not establish a causal or version-wide quality ranking.

### Opening assessment

The evaluator's `gpt-6-luna / medium` assessment accepted nine PASS decisions
on 13 October at 21:18:46-21:18:58 Sydney time. Each quotes a complete original
activity field verbatim and passed native material validation. This assessment
fills eligible access gaps; it provides no new official hours or factual evidence.

| Version | Supplemented overall / 100 | Opening PASS / FAIL / UNKNOWN | Remaining factual UNKNOWN |
| --- | ---: | --- | ---: |
| V0 | 73.3333 | 7 / 1 / 1 | 4 |
| V1 | 93.3333 | 8 / 0 / 0 | 0 |
| V2 | 96.6667 | 7 / 0 / 0 | 0 |
| V3 | 100 | 6 / 0 / 0 | 0 |

Other dimensions and pace deductions are unchanged. V0 retains the confirmed
museum opening FAIL, one unresolved identity, one opening gap and two route gaps.
V3's 100 is a score under this profile and accepted model overlay, not complete
official evidence or a general performance guarantee. The pair retains its own
saved evidence/profile and does not inherit this four-final overlay.

The selected assessment used one model send, 10,665 input and 1,728 output tokens,
zero retries and zero additional Google/RAG sends. Network-denied native replay
reproduced the report exactly. Rejected acquisition material remains private and
is included in the separate rejected-attempt cost scope.

## Candidate POI process


| Stage | V1 distinct places | V2 distinct places | V2 gained / V1-only / retained |
| --- | ---: | ---: | --- |
| Discovered | 56, complete | 66 observed, partial | Complete comparison unavailable |
| Admitted | 48 | 48 | 14 / 14 / 34 |
| Enriched | 24 | 30 | 12 / 6 / 18 |
| Supplied | 12 | 12 | 2 / 2 / 10 |
| Scheduled | 8 | 7 | 1 / 2 / 6 |

V2 observed discovery contains 47 Google-only, ten RAG-only and nine mixed identities;
ten are incremental observed RAG identities. Complete discovery remains unavailable.
The full canonical memberships/origins/omissions are retained. Observed discovered
places not supplied total 44 in V1 and 54 in V2. Scheduled sets use current independent
identity association and exclude Nearby-only references. Empty interests make relevance
non-applicable. No corpus census, recall estimate or causal RAG benefit is claimed.

## V3 Repair and independent pair


The selected real V3 run accepted three `system_delete` rounds. Sydney Opera House,
Taronga Zoo Sydney and Royal Botanic Garden Sydney were removed from their respective
draft dates. Daily main-POI counts changed from 3/3/3 to 2/2/2. All six surviving
activity records are unchanged; no addition, replacement, retiming or cross-date move
was accepted. No local or replan model call was used. Final routes were recomputed;
three final-only Nearby suggestions are outside primary visits and Repair effects.

The native source-labelled pair imported saved observations without new provider calls.
Identity acquisition has 30 available and one unavailable request observation; evidence
has 22 available and one unavailable. Missing compatible observations remain UNKNOWN;
inherited usage is not charged again. Exact zero-network replay passed.

| Same-run stage | Overall / 100 | Auxiliary / 100 | Pace deduction | Opening P / F / U | Routes P / F / U |
| --- | ---: | ---: | ---: | --- | --- |
| Draft | 77.5 | 87.5 | 10 | 6 / 0 / 3 | 5 / 0 / 1 |
| Final primary | 91.6667 | 91.6667 | 0 | 4 / 0 / 2 | 3 / 0 / 0 |

The overall paired change is 14.1667 percentage points. There are three removed visits,
zero added/replaced visits and zero confirmed venue losses under native correspondence.
Protected commitments and protection conflicts are empty for this request; they do not
establish protected-activity test coverage. V2/V3 independent finals share three canonical
visits, with three V3-only and four V2-only visits. That comparison is descriptive and
separate from the same-run Repair lineage.

The final round returned `ACCEPTED_COMPLETE` with `authorized_targets_complete`:
all three daily soft-pace targets reached zero. The stage ended normally after
meeting its targets. No model retime or replan was required for this case.

## Resources and cost basis

| Selected result component | Reference USD |
| --- | ---: |
| V0 generation | 0.00241055 |
| V1 generation | 1.638289475 |
| V2 generation | 1.985985875 |
| V3 generation | 1.991064 |
| Four-final primary evaluation | 1.19074005 |
| Selected opening assessment | 0.00219705 |
| Selected result total | **6.810687000** |

Rejected case acquisition attempts add USD 1.643382200: an unqualified V3
retrieval attempt (USD 1.641240025) and an invalid opening response
(USD 0.002142175). Selected and rejected case acquisition together total
**USD 8.454069200**. Saved paired observations are not charged again.

Separate synthetic Repair engineering diagnostics consumed USD 0.003531110;
they are excluded from selected-result cost and case scores. Their observations
belong to the [Repair engineering record](../../docs/records/v0-v3/v3-development.md#post-refactor-model-smoke).
Ordinary cases execute only the Repair strategies needed by their actual targets.

The [accounting view](analysis/resources/accounting.json) distinguishes these scopes
without double-counting generation Repair or saved evidence. Dated retail/OpenAI
proxy rates are estimates; Foundry account rates, actual invoices and external
Codex token/billing telemetry are unavailable. Activity costs are also missing,
so the itinerary does not independently establish compliance with AUD 900.
The generator has no monetary hard guard; call/time limits do not imply an invoice cap.

## System and external assistance

| Work | Actual performer | Used output and verification |
| --- | --- | --- |
| V0-V3 generation | Native Planner, recorded `gpt-6-luna`; V2/V3 embedding `text-embedding-3-small` | Source-linked itineraries/usage; V3 retained three deterministic deletions. |
| Requirements and interests | Distinct `/root/requirements_author`, `/root/requirements_reviewer`, `/root/interests_reviewer`, recorded `gpt-6.1-sol / high` | Original-request-only reviewed inputs; empty semantics retained. |
| Primary schedule/route context | `/root/issue140_primary_context_high`, external Codex `gpt-6.1-sol / high` | Source-only Sydney time-zone and route interpretation checked by native consumers. |
| Selected V3 execution | `/root/issue140_v3_execution_high`, external Codex `gpt-6.1-sol / high` | Authentic generation capture and native selection/finalization. |
| Primary evaluation | `/root/issue140_primary_execution_high`, external Codex `gpt-6.1-sol / high`; evaluator `gpt-6-luna / medium` | Native reports, 55 Google sends and one identity-model send; raw receipts and replay. |
| Opening assessment | `/root/issue140_phase_c_execution_high`, external Codex `gpt-6.1-sol / high`; evaluator `gpt-6-luna / medium` | Nine source-quoted judgments checked by native validation and exact replay. |
| Material preparation, analysis and presentation | Parent Codex operator | Native candidate/pair readers, deterministic lineage, resource reconciliation, lossless expansion and archive verification. |
| Review | External Standards/Spec Codex reviewers configured `gpt-6.1-sol / high` | Independent material and source consistency checks. |
| Scope, budgets and case acceptance | Human user | Approved execution and accepted the selected results with their stated limitations. |

External Codex assistance influenced reviewed semantic inputs, orchestration,
interpretation and presentation. It supplies no human ground truth or blinded
assessment. The parent prepared materials not authored by installed tools; native
consumers and separate reviewers checked the used outputs. Original failed-attempt
actor/transport records remain private. The parent's exact backend model and full
internal transcripts/token billing are not independently attested by these artifacts.

## Evidence identity and reproducibility

The original input SHA-256 is
`81fd4a0cec27396d38e759cbcc8ca51e95a5507922ac32cc27c1eff75708de88`;
the source revision-3 manifest SHA-256 is
`bca79c972635e884e86569a5f78e3c48347ddb3cf97f75fdd0f70352fdf673f2`.
The [material index](material-index.json) records all publication/source hashes and
exact JSON-subtree locations. Shared references expand losslessly; the V3 draft
delta reconstructs its complete source value. Public views are selected publication
material, not closed native acquisition bundles.

The ignored compact archive at `benchmark/scratch/case-01/archive/` preserves raw
captures, reviewed inputs, native preparations/receipts, usage/prices, source snapshots
and required replay dependencies. Original bytes and execution dates remain intact;
other operational and engineering material is retained outside the initial dataset.
Integrity, fresh restoration, public-source equivalence and applicable native
offline replay passed before redundant working copies were deleted. Replay denies
network access and requires installed Python/runtime dependencies. Private model/
provider payloads and credentials are excluded from public material.
