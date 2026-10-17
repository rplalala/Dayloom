# Case-11: Paris, France

## Status and selected material

Execution revision **r02** completed fresh V0–V3 generation and one independent
four-final Primary on **17 October 2026, Australia/Sydney**. Processing and
acquisition completed; all four totals are available. Candidate POI, independent
relevance, same-run paired access, Repair process and resource reports are complete.
The same-run no-Repair observation is verified. The researcher explicitly accepted
the current r02 selection and disclosed limitations on **17 October 2026,
Australia/Sydney**. [Automatic acceptance](#acceptance) defines the exact scope;
execution is paused, with blinded human review deferred. Git delivery is separately
authorized; the accepted native selection remains unchanged.

The [original request](../inputs/case-11.json) is unchanged: Paris, 22–25 October
2026, two adults, EUR 1,500 for the group and trip, art and architecture interests,
and moderate pace. On 23 October, 14:00–16:00 Paris local time must contain no
activities or travel. Input SHA-256 is
`60a5c7fc106d785f8f50e6a503f34010c8eb4979562a164f4b26612454972487`.
[Issue #160](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/160)
owns case acceptance and delivery state.

All four new runs use source `bc985c273afcf48c5f1d4da59be532c22d403efd`, which
merges actual `origin/main` at `cc779bb2ece7b312ab3d985cebdd5d6b64b209c3` while
retaining the earlier case commits. Runtime file SHA-256 remains
`a6c932272e8d5037ed66fb057e629f8dcff44f3e12117d2dbcb16c8905454058`;
the runtime snapshot SHA-256 remains
`ed0853d6968c8b526a695e9a69b97e22dc2e331291e4051ddc8d305046cd5107`.
No case-specific application, configuration or input change was made.

| Material | Reader view |
| --- | --- |
| Independently authored and reviewed requirements | [Reviewed specification](requirements/reviewed.json) |
| Independent interests and relevance | [Native inventory](interests/inventory.json), [reviews A](interests/relevance-a.json), [reviews B](interests/relevance-b.json); [original source review](interests/source-review.json) |
| r02 source-policy bindings | [Transport](requirements/r02/route-reviews.json), [density](requirements/r02/density-reviews.json), [destination time](requirements/r02/schedule-context.json) |
| Selected final schedules | [Daily schedules](itinerary.md); [V0](generation/r02/v0/itinerary.json), [V1](generation/r02/v1/itinerary.json), [V2](generation/r02/v2/itinerary.json), [V3](generation/r02/v3/itinerary.json) |
| Independent Primary | [Scores, dimensions and daily deductions](evaluation/primary/summary.json) |
| Candidate process | [Stage inventory](analysis/poi-process/opportunities.json), [independent relevance](analysis/poi-process/relevance.json), [venue labels](analysis/poi-process/venues.json) |
| Repair process and completed pair | [Native Repair view](analysis/repair/repair.json), [mechanism observations](analysis/repair/mechanism.json), [current pair](evaluation/v3-pair/report.json); [preliminary API-only pair](evaluation/v3-pair/api-only.json) |
| All-attempt stage consumption | [Resource ledger](resources/primary-stage.json), [native cost reconstruction](analysis/resources/all-attempt-cost.json), [selected-run resources](analysis/resources/tradeoffs.json) |
| Current analysis and completed access request | [Analysis status](analysis/summary.json) |
| Exact sources and publication hashes | [Material index](material-index.json) |

The same-input reviewed requirements, unrestricted transport, ordinary density and
`Europe/Paris` policies retain their actual original actors, review times and
evidence. The spec has one resolved `protected_time` obligation with
`scope=scheduled_commitments`, no named-venue requirement or exact visit quota.
A fresh source-only native interest binding uses the unchanged spec identity
`case-11-art-and-architecture`. Both named topics remain explicit; either can
support a venue judgment without inventing a topic quota. The earlier split-topic
source review remains historical evidence, not a native venue-relevance report.

## Primary results

| Version | Overall / 100 | Five-dimension auxiliary / 100 | Mean pace deduction | Factual FAIL units | Factual UNKNOWN units |
| --- | ---: | ---: | ---: | ---: | ---: |
| V0 | 100 | 100 | 0 | 0 | 0 |
| V1 | 97.5 | 100 | 2.5 | 0 | 0 |
| V2 | 80 | 100 | 20 | 0 | 0 |
| V3 | 100 | 100 | 0 | 0 | 0 |

Requirements, grounding, non-overlap, opening and routes all pass for the selected
finals under `rtpeval_declared_population_1`. In particular, all four versions pass
the protected meeting interval. The soft density policy accounts for every deduction:

- V1 has three primary visits on 22 October: a daily deduction of 10 averages to
  2.5 over the four requested dates.
- V2 has one primary visit on each of 22 and 23 October: two daily deductions of
  40 average to 20. Its other two dates have two visits each.
- V0 and V3 have two primary visits on every date, with no density deduction.

These are pace deductions, not violations of an invented hard daily count. The
Primary summary preserves the per-dimension PASS/FAIL/UNKNOWN counts and exact
fractions. Primary acquisition has no failed or unknown acquisitions. Eligible
missing-hours assessment completed for two visits before the single final score;
model-supported access remains distinct from verified API opening hours.

## Candidate POI process and independent relevance

The retrospective process declaration selects the four approved r02 first-dispatched
runs on the fixed application baseline. Earlier r01 attempts remain in cumulative
resource accounting; they are not substitute process observations. Native readers
replay the exact captures and independent Primary identities. Canonical Google
Place IDs are the unit; references and repeated query positions do not add visits.

| Version | Discovered | Admitted | Enriched | Supplied | Independently scheduled |
| --- | ---: | ---: | ---: | ---: | ---: |
| V1 | 63 complete | 56 | 28 | 14 | 9 |
| V2 | 76 complete | 56 | 40 | 14 | 6 |

V1 records seven admission-capacity omissions, 28 unprocessed candidates at its
new-success target and 14 enriched candidates not selected. V2 records 20, 16 and
26 respectively. These are preserved fates, not failed service requests. Both
native opportunity rows have complete stage/scheduling capture and no diagnostics.

V2's 76 discoveries partition into 56 Google-only, 14 RAG-only and six mixed-source
places. Its one retrieval returned 20 positions and 20 unique entities, with one
embedding call and 14 identity-resolution Details sends; no fallback send occurred.
The runtime corpus artifact, text hashes, embedding space, policy, 15 km scope and
configured limits remain in the native opportunity report. No corpus-wide coverage
study was selected.

Twelve RAG-only candidates were enriched, but none reached the final supplied set.
The two mixed-source supplied places were Panthéon and Arc de Triomphe; only the
latter was scheduled. This preserves real discovery origins rather than attributing
all resolved Google IDs to Google discovery or treating overlap as a RAG-only gain.

Two independent reviewers judged all 77 union candidates against the combined
interest using official venue/operator, city and official tourism descriptions:
**55 relevant, eight not relevant and 14 UNKNOWN**. Completed UNKNOWN judgments
retain ambiguous identity, insufficient official description or thematic-boundary
reasons. Producer labels identify targets only; query intent, ranks, similarity,
stage membership, schedules and scores were excluded from the judgments.

| Version | Relevant discovered, lower bound | Relevant admitted, lower bound | Relevant enriched, lower bound | Relevant supplied, lower bound | Relevant scheduled, exact |
| --- | ---: | ---: | ---: | ---: | ---: |
| V1 | 43 | 37 | 18 | 12 | 9 |
| V2 | 54 | 39 | 28 | 12 | 6 |

Unknown upstream labels keep complete relevance counts, full-chain conversion
rates and end-to-end signed differences unavailable. The observed end-to-end lower
counts are nine and six. Independently scheduled relevant venues are fully judged:
V2 retains six V1 venues, adds none and omits Musée des Archives Nationales, Place
des Vosges and Panthéon. This is a descriptive selected-output difference,
not evidence that RAG caused a particular outcome.

## Repair observations and paired access

V3 generation, retrieval and validation completed. Repair was `not_applicable`
with reason `no_authorized_targets`: zero attempted or accepted rounds and zero
Repair model calls. Original `/v3/draft` and `/v3/final_primary` are identical;
the source-linked diagnostic records eight retained visits, no additions, removals
or replacements, and zero signed change. There is no attempted-Repair success-rate
denominator.

Independent V2/V3 finals differ: V3 retains all six V2 places and adds Panthéon
and Place des Vosges. The Primary overall difference is +20 percentage points,
with zero five-dimension auxiliary difference and a 20-point reduction in mean
pace deduction. These are separate generations; the difference cannot be assigned
to Repair, which did not run.

Paired identity and evidence were imported offline from verified Primary and
source-labelled generation observations, preserving original observation times and
inherited accounting. Offline evidence acquisition sent zero Google/model requests. The
saved **API-only preliminary pair** has 97.5 for each stage and a zero delta,
with one opening UNKNOWN per stage for the same Place des Vosges visit. It is not
the completed current common-access-policy pair; the Primary V3 score remains 100.
The completed common-policy pair scores **100 for draft and 100 for final-primary**,
with a zero delta and eight opening PASS, zero FAIL and zero UNKNOWN per stage.
One model-supported access judgment covers the shared Place des Vosges context;
API opening-hours coverage remains seven of eight visits per stage. The native
research Repair view classifies the pair as unchanged while preserving
`repair_attempted=false` and the separate four-final comparison.

The V3-only access packet has one eligible context for 24 October, 15:00–16:00
+02:00, sharing unchanged draft/final source aliases. The original Primary model
answer cannot be rebound to this new packet. A single `gpt-6-luna / medium` request
completed under USD 1, zero Google sends, 128,000 input/16,384 output tokens,
60-second request/120-second total limits and no retries. Its prepared digest is
`89424500b5bc2f986b0dbaec14b316a448670ad306bcf2bfbbfbf075053571d0`.

The explicitly approved request used
`https://captone-trip.services.ai.azure.com/openai/v1/responses` and included only
the relevant activity/notes, venue/opening observations, timezone, interval, source
aliases and assessment policy. It contained no original traveler, budget or preference
object. The first actual invocation sent one model request, with zero retries and
zero Google sends. Its 2,103 input and 313 output tokens cost USD 0.000419300 by
the frozen reference prices. Native access receipt replay and source-bound paired
report reconstruction preserve the returned judgment without changing Primary.

## Time correction and verification

The integrated [civil-time contract](../../docs/0003-itinerary-transport.md#civil-time-and-iana-acceptance)
now makes V1–V3 local endpoint offsets application-owned using sourced IANA zones
and dates, rejects conflicts and invalid clocks, and uses UTC elapsed arithmetic
for transport. V0 retains its independent model-authored timestamps.

All r02 finals pass native semantic readiness and numerical population preparation.
The separate zero-provider Paris interval probes return known for all 46 activity
and transfer intervals across the four finals. New tools outputs use +02:00 before
the transition and +01:00 for the 25 October daytime visits; the r01 conflict does
not recur in these executions. This verifies the observed case, not universal
future-model success.

The locked environment, 63 distributions, both tokenizers, input dates and read-only
corpus compatibility passed. Four offline generation preparations dispatched zero
providers. Fourteen targeted civil-time/route-time tests and the UTC elapsed probe
across the autumn clock repetition passed. All 740 indexed r02 generation artifacts
match their captured hashes. Native requirements attachment, four-version intake,
preflight and population preparation passed with no missing semantic review work.

The first offline `validate` invocation encountered Windows GBK stdout encoding on
an accented venue name after intake. Process-only UTF-8 settings resolved the output
failure; the offline rerun was accepted. No provider request or project configuration
change resulted. Primary receipt verification and zero-network native replay passed;
the replayed report equals the saved report exactly.

Post-primary native population, opportunity, relevance, Repair and resource builders
completed. Local assembly corrections supplied required reference headers and
selected producer-declaration provenance; original independent judgments and native
captures were retained unchanged. The selected-run usage view and eight-operation
cost reconstruction use their distinct supported scopes. No application code changed.

## Resources

| Attempt | Native seconds | Model calls, including embeddings | Tokens | HTTP sends | Reference USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| r01 V0 | 65.344 | 2 | 27,772 | 2 | 0.006291725 |
| r01 V1 | 112.641 | 4 | 67,817 | 64 | 1.982172725 |
| r02 V0 | 45.407 | 2 | 22,662 | 2 | 0.003796960 |
| r02 V1 | 90.016 | 4 | 63,367 | 64 | 1.981359640 |
| r02 V2 | 98.015 | 6 | 64,730 | 80 | 2.261463995 |
| r02 V3 | 103.313 | 6 | 66,107 | 81 | 2.267072995 |
| r02 Primary | 25.538 | 2 | 17,398 | 54 | 1.051620100 |
| r02 paired access | 5.474 | 1 | 2,416 | 1 | 0.000419300 |
| Total | 545.748 | 27 | 332,269 | 348 | 9.554197440 |

The cumulative USD 40 reference allowance includes r01. Remaining allowance is
USD **30.445802560**. r02 generation cost USD 6.513693590 and Primary cost
USD 1.051620100. All observed events are priced; service retries are zero. V2/V3
each include one completed two-token embedding call. Primary used 52 Google and
two model sends. Post-primary offline imports/reporting added no provider sends or
cost; paired access added the single model send listed above. Reconstructed native
costs include all eight observed operations, preserve the seven earlier rows exactly
and do not recharge inherited paired evidence. External Codex usage, offline-analysis
timing and actual account invoices are unavailable.

The r02 reservations were V0/V1/V2/V3/Primary USD 1/7/9/13/8. Generation retained
its native 600-second invocation limit; those reservations are not a hard
per-send spend guard. Primary froze USD 8, 240 Google sends, two model sends,
128,000 input/16,384 output tokens per call, 60-second requests, 900-second total
and zero retries. Its missing-hours assessment remained enabled.

Generation retains the native 8 October price reference, checked against official
sources on 17 October; Primary uses a separately frozen 17 October price book.
Foundry model cost uses the disclosed OpenAI retail proxy. Estimates cover observed
instrumented adapters; discounts, free quota, tax and actual invoices are unavailable.

## AI assistance and boundaries

| Contribution | Actual performer and available configuration |
| --- | --- |
| Orchestration, preparation, offline diagnosis/gates, resource reconciliation and presentation | Current parent Codex chat; exact parent model/effort not independently exposed |
| Original source-only requirements author and separate reviewer | `/root/case11_requirements_author` and `/root/case11_requirements_reviewer`, each `gpt-6.1-sol / high`, fresh context |
| Original interests and source-policy judgments | `/root/case11_interests` and `/root/case11_source_policies`, each `gpt-6.1-sol / high`, fresh context |
| r01 corroborating temporal review | `/root/case11_v1_temporal_review`, `gpt-6.1-sol / high`, fresh context |
| Two r01 and five r02 live invocations | `/root/case11_live_executor` and `/root/case11_r02_live_executor`, `gpt-6.1-sol / medium`; one parent-dispatched invocation at a time |
| Fresh native interest binding | `/root/case11_analysis_interests`; source-only, model/effort not exposed |
| Independent official-source relevance | `/root/case11_relevance_a` and `/root/case11_relevance_b`; 39 and 38 subjects, fresh contexts, model/effort not exposed |
| Authorized paired access invocation | `/root/case11_r02_live_executor`, `gpt-6.1-sol / medium`; one evaluator model send, zero retries |
| Planner/evaluator provider model | `gpt-6-luna`; embedding model `text-embedding-3-small` where observed |

Primary identity used `low` reasoning effort; eligible access assessment used
`medium`, as required by the native access stage.

Original author/reviewer operations used the complete request and exact draft,
excluding generated results, scores and mechanisms. The author disclosed an
over-broad read of generic contract text; no case-result exposure was identified.
Actual drafts, review outputs, execution settings and available authentic response
excerpts remain private. Full child transcripts and external token/billing telemetry
are unavailable and were not fabricated. Generation-stage r02 requirements and source-policy reviews reuse their original
provenance. The post-primary interest and relevance operations are separately
identified fresh executions.

The r01 temporal reviewer disclosed exposure to nested route/validation fields and
a discarded PowerShell timestamp display conversion. Its work remains corroborating,
not blinded evidence. The parent reproduced its probes using locked Python 3.12.14.
New-wire role/occupancy gates required no additional output-specific review for r02.
The fresh interest/relevance actors retained actual observations and source evidence.
Mechanical reference corrections created separately bound copies while preserving
original inventory/review files, judgment times, meanings and evidence. Their full
transcripts and external billing remain unavailable. Agent checks do not constitute
human review.

## Private evidence archive

The local private archive identifier is `benchmark/scratch/case-11/archive/`.
Its manifest maps original case-relative logical paths to immutable SHA-256 and byte
lengths; `blobs.zip` stores each byte sequence once. The 6,641 retained logical paths
include 5,246 original private paths, both r01/r02 application-source snapshots and
the accepted reader/input snapshot. They share 1,707 unique blobs. Original requests,
selected results, actual semantic actor records, failure evidence, usage, independent
observations, frozen preparations, native reports and receipts remain byte-exact.
The 3,403 excluded files are dependency-checked staging/export copies, superseded
derived views and temporary assembly/check scripts. Historical r01 logical aliases
remain available from shared archive bytes.

Fresh-root restoration verified all archived bytes, 123 public/source projections,
556 r01 preservation bindings and 740 indexed r02 generation artifacts. Archived
native code exactly reproduced Primary receipt/HTTP/report replay, paired-access
receipt/HTTP/report replay, independent quality/pair reports, all five current research
tracks and the eight-operation cost report. Network operations and reads from the
original working evidence were denied during these checks. The initial case-local
restoration exceeded the Windows path-length limit; a fresh short destination in
the authorized workspace passed without altering evidence or source bindings.

After successful restoration and a final 8,649-file original-inventory check, the
working and preservation copies, temporary assembly script and both temporary
restoration trees were removed. Private storage decreased from approximately
168.4 MB to 10.4 MB, including archive metadata and verification tools. Environment
files remain outside the archive, with their original hashes unchanged. No other
case or shared runtime data was cleaned.

All nine archive files were migrated byte-for-byte into the main worktree on
17 October 2026, Australia/Sydney. A second fresh-root restoration there reproduced
the same native reports and all eight cost operations, with network and original
working-evidence reads denied. Source and destination hashes matched before worker
cleanup; environment and retrieval metadata already present in main also matched.

Original absolute preparation bindings are unchanged. Relocated legacy directory-bound
CLI replay is not claimed: that interface requires the original roots and matching
implementation/dependencies. The verified fresh-root checks use native offline
readers/composers with explicit restored directories. Source paths in the
[material index](material-index.json) now identify archive manifest entries rather
than live working files; public selections remain reader views, not native replay
bundles. The archive includes standard-library integrity/restoration instructions
and the actual verification records. Archival incurred zero provider sends and did
not regenerate or rescore the selected outputs. Original acquisition/analysis status
fields retain their checkpoint meanings; the decision below owns acceptance.

## Acceptance

**Automatically accepted by the human researcher on 17 October 2026,
Australia/Sydney**, through an explicit decision in the current Codex chat.
Acceptance binds batch `case-11-r02`, revision `2`, as recorded in local material
commit `2fc49fa3f16aff4088814d4e1e82676c83eae2ce`: the unchanged original input,
independently reviewed requirements and interests, source-policy context, selected
first-dispatched runs `case-11-r02-v0` through `case-11-r02-v3`, admitted manifest,
independent Primary, candidate/relevance analysis, Repair mechanism and completed
same-run pair, and all-attempt resources including r01. The
[material index](material-index.json) retains the selected source hashes and the
pre-decision index SHA-256
`00cca4d1f46cc66203e12835189cf7c9367c3d2588a1f73924ce2d5bc125c1ed`.
r01 remains historical failure evidence and resource history, not a selected result.

The accepted [Primary results](#primary-results) remain **100 / 97.5 / 80 / 100**;
requirements each have one PASS, zero FAIL and zero UNKNOWN. The accepted current
V3 pair is **100 → 100**, with no attempted Repair. The
[candidate analysis](#candidate-poi-process-and-independent-relevance) retains
14 UNKNOWN relevance labels and unavailable complete relevance counts/full-chain
conversion rates. Independent version differences do not establish causal RAG or
Repair improvement, and no attempted-Repair success rate is available.

Model-supported access is distinct from API-verified opening hours. All submitted
activity cost fields are unspecified, so the EUR 1,500 whole-trip affordability is
unverified. The [resource ledger](#resources) retains USD **9.554197440** of the
cumulative USD 40 reference allowance, including earlier attempts; actual invoices
and external Codex consumption remain unavailable. These are accepted evidence
limits, not additional quality passes or replacement judgments.

The pre-decision checks verified 123 public material/source bindings, 556 original
r01 files, 740 indexed r02 generation artifacts and both local environment files;
paired-access receipt replay, native paired reconstruction and native Repair report
reconstruction matched exactly. Acceptance recording checks the unchanged selection
and documentation bindings; no new generation, evaluation acquisition or scoring
was performed. Native reports, original observations, scores and receipts remain
unchanged.

This decision completes step 10 for this selection only. Blinded human review has
not been conducted and remains deferred; it is separate from researcher acceptance
and agent review. Remote publication, Issue updates/closure, further case execution
and reruns are not part of this decision. Work pauses after the local acceptance
record; no version freeze or final research conclusion is established.

## Historical context

Automatic approval initially refused paired access before subprocess or provider
dispatch because explicit payload/destination approval was missing. Approval of
the exact prepared packet and Azure destination then enabled the first actual
invocation. The refusal, approval and successful receipt remain separate original
records; the refusal incurred no provider usage.

r01 generated V0 and V1 on source `b73c8eed09fafb6d54bee8684c5b2e7766515357`
and stopped before V2/V3/Primary. Its V1 model supplied +02:00 for three 25 October
activities; DTO mapping preserved all eight activity endpoint pairs and program-owned
routing propagated the bad offset to two transfers. Independent preparation returned
three activity time UNKNOWNs and blocked acquisition. The immutable
[old V0](generation/v0/itinerary.json), [old V1](generation/v1/itinerary.json),
[population diagnostics](evaluation/population-v1.json),
[temporal probes](evaluation/temporal-v1.json) and
[model-to-output diagnosis](evaluation/timezone-origin-v1.json) retain that evidence.
The shared correction arrived through PR #180; r02 used four fresh same-baseline
runs, without rewriting old outputs or mixing old successes into the new batch.
