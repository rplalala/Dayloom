# Case-09: Tokyo evaluation and analysis

The selected request covers Tokyo, Japan, **22–26 October 2026**, three adults and a
JPY 300,000 whole-group trip budget. The [original request](../inputs/case-09.json)
requires exactly one Ueno Park visit on 23 October and exactly one Tokyo National
Museum visit on a suitable trip date. Traditional culture and modern art remain
soft interests without venue quotas. The [independently reviewed requirements](requirements/reviewed.json)
preserve these boundaries.

Batch `case-09-batch`, revision `1`, contains one first-dispatched generation per
version, produced on source `b73c8eed09fafb6d54bee8684c5b2e7766515357`. Primary evaluation
and the authorized analyses completed on **17 October 2026,
Australia/Sydney**. Native material admission passed; **researcher acceptance is
pending**. Work is paused before that decision. The [material index](material-index.json)
owns source hashes, publication mappings and shared-value expansion rules.
[Daily itineraries and recorded POI origins](itinerary.md) present all four selected
schedules and the actual V3 draft/final change.

## Primary results

| Version | Overall / 100 | Five-dimension auxiliary / 100 | Mean pace deduction | Factual FAIL units | UNKNOWN units |
| --- | ---: | ---: | ---: | ---: | ---: |
| V0 | 86 | 86 | 0 | 4 | 0 |
| V1 | 98 | 98 | 0 | 0 | 1 |
| V2 | 92 | 100 | 8 | 0 | 0 |
| V3 | 98 | 98 | 0 | 0 | 1 |

All four versions pass both named-visit requirements. Grounding and non-overlap
checks pass throughout. The [primary summary](evaluation/primary/summary.json)
retains dimension counts, daily counts, source-linked findings and native report
bindings under `rtpeval_declared_population_1`.

- **V0 opening FAIL:** Imperial Palace East Gardens is scheduled on 26 October,
  09:30–11:30 JST. Independent regular-hours evidence marks the entire interval
  closed.
- **V0 route FAILs:** Google returns `ROUTE_NOT_FOUND` for the declared TRANSIT
  journeys Meiji Jingu → Mori Art Museum (22 October), Senso-ji → Nezu Museum
  (24 October), and Imperial Palace East Gardens → Kiyosumi Garden (26 October).
  These remain native provider-evidence FAILs; they do not establish that no
  real-world public-transport connection exists.
- **V1/V3 opening UNKNOWN:** Tokyo Dome City on 26 October lacks applicable hours
  and sufficiently specific access evidence. The activities do not distinguish
  public outdoor sightseeing from indoor or ticketed attractions. The access
  assessment retains UNKNOWN for both outputs.
- **V2 pace deduction:** 26 October contains one primary visit. The ordinary
  density policy deducts 40 for that date, averaging 8 across five requested dates.
  This is a soft pace deduction, not a violation of an invented daily visit quota.

Acquisition and processing both completed, with no acquisition failures. The
conditional missing-hours assessment covered 14 eligible visits before the single
final primary calculation. Model-supported access judgments remain distinct from
certified API opening hours; the two unresolved access judgments remain visible.

## Resources and checks

| Operation | Dispatched attempts | Observed tokens | Model calls, including embeddings | HTTP sends | Reference USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| V0 generation | 1 | 27,478 | 2 | 2 | 0.004531040 |
| V1 generation | 1 | 76,770 | 4 | 69 | 2.395026625 |
| V2 generation | 1 | 83,799 | 6 | 90 | 2.800815285 |
| V3 generation | 1 | 85,485 | 6 | 103 | 3.073493600 |
| Primary evaluation | 1 | 41,833 | 2 | 79 | 1.646084475 |
| Paired access refresh | 1 | 10,287 | 1 | 1 | 0.0019503 |
| Total | 6 | 325,652 | 21 | 344 | 9.921901325 |

Generation used USD 8.273866550 of its USD 30 reference allowance; primary used
USD 1.646084475 of USD 10, with 77 Google sends and two model sends. There were no
service retries or unpriced observed events. These are complete estimates for the
instrumented adapters, not account invoices. Generation retains its native 8 October
price basis; the relevant official price references were checked on 17 October.
Primary uses a separately frozen 17 October price book. Discounts, free quota, tax,
actual account billing and external Codex billing are unavailable.

The exact original-input binding, current-date admission, Python/dependency paths,
both tokenizer checksums and query-only corpus compatibility passed. Sandbox cache
and database access failures were resolved by authorized checks outside the sandbox,
without credential, permission or project-configuration changes. An initial module
command exited before entering the native CLI and sent no service requests; its
original log remains retained. The corrected installed entry point performed the
four first native Planner invocations listed above.

Native requirements attachment, four-version intake and semantic readiness passed.
Independent decisions bind all 44 final activities and 39 non-transport occupancy
records. The frozen primary preparation binds input, selected results, reviews,
prices, limits and evaluator implementation. Zero-network native replay reproduced
the saved report exactly. Public itinerary projections match the selected native
itineraries. Public JSON uses UTF-8/LF; the material index distinguishes public
projection hashes from immutable native-original hashes. Application code and runtime policy are
unchanged; no new application regression result is claimed.

## Candidate opportunity and independent relevance

The native [candidate process](analysis/poi-process/opportunities.json) binds passive
V1/V2 captures to the selected attempts and independently resolved final identities.
Counts are unique canonical places, not query positions or scheduled visit events.

| Version | Discovered | Admitted | Enriched | Supplied | Independently scheduled |
| --- | ---: | ---: | ---: | ---: | ---: |
| V1 | 48 complete | 48 | 32 | 16 | 10 |
| V2 | 65 observed, partial | 63 | 47 | 16 | 9 |

V1 stopped enrichment after its new-success target: 16 candidates were unprocessed
and 16 enriched candidates were not selected for supply. V2 records two ineligible,
16 unprocessed and 31 not-selected candidates. Its discovery observation remains
partial (`rag_partial`), even though the producer's required retrieval workflow
completed. Of 65 observed discoveries, 46 are Google-only, 17 RAG-only and two mixed;
the supplied set contains 15 Google-only and one RAG-only place. These are opportunity
origins, not independent relevance judgments or evidence that RAG caused a better plan.

The [interest inventory](interests/inventory.json) preserves two ordinary interests
from the original request. Two independent batches inspected 68 venue identities,
with exactly one official-page open attempt per venue and no failed-page retries.
Saved factual descriptions distinguish page content, indexed official descriptions,
independent primary identity facts and evidence gaps. A separate
[cross-review](interests/cross-review.json) accepted 130 judgments and changed six
to UNKNOWN, covering brand/address scope, historical single-exhibition evidence,
Japanese-style painting and architectural-aesthetic inferences.

All **136 venue/interest judgments** are present: **57 relevant, 40 not relevant and
39 UNKNOWN**. These are judgment counts across two interests, not 136 venues.
[Reviewed labels](interests/relevance-reviews.json) retain evidence hashes and
reviewer provenance; [native relevance](analysis/poi-process/relevance.json) applies
them without adopting Planner/query labels.

| Version | Known relevant discoveries | Known relevant supplied | Known relevant scheduled / end-to-end |
| --- | ---: | ---: | ---: |
| V1 | 36 | 11 | 7 |
| V2 | 48 | 11 | 7 |

These are observed counts of places relevant to at least one interest. UNKNOWN
labels and V2's partial discovery leave complete relevant counts, exact conversion
fractions and exact V2-minus-V1 relevance effects unavailable. A museum or attraction
inside a larger park/complex is a venue-level opportunity; the generated activity
does not automatically include that sub-venue. Relevance does not certify an
exhibition on the trip dates, activity-level interest fulfillment or human usefulness.
No corpus study or corpus-denominator/recall claim is included.

## Repair and same-run evidence

The primary V2/V3 final totals differ by **+6 points**: auxiliary quality differs by
-2, while the mean density deduction improves by 8. This describes two separately
generated plans; it does not isolate the effect of Repair.

The [native mechanism report](analysis/repair/mechanism.json) and
[Repair analysis](analysis/repair/report.json) retain one deterministic deletion and
zero Repair model calls. Independent review of the actual 11 draft and 10 final
primary activities establishes ten unchanged occurrences and one deletion:
**ART FRONT GALLERY on 24 October**. There are no additions or replacements.
[Lossless stage patches](generation/v3/stages.json) retain every actual difference,
including transfers and recommendations.

The [same-run paired report](evaluation/v3-pair/report.json) applies the same source-bound missing-hours
access policy to the original V3 draft and final-primary stages. Saved Google
observations retain their exact provenance; eligible access gaps receive a fresh
assessment. Identical activity/time/evidence contexts share one decision. Primary
scores, original activities and factual API-hours coverage are unchanged.

| Same-run stage | Overall / 100 | Auxiliary / 100 | Density deduction | Opening P / F / U | Route UNKNOWN |
| --- | ---: | ---: | ---: | --- | ---: |
| Draft | 92.848485 | 94.848485 | 2 | 10 / 0 / 1 | 1 |
| Final primary | 98 | 98 | 0 | 9 / 0 / 1 | 0 |

The paired overall change is **+5.151515 percentage points**.
The 17 October 2026 refresh used one model call, zero Google sends
and zero retries, for **USD 0.0019503** reference cost. Native source, model-response
and receipt replay passed offline. Model-supported access is not certified opening
hours, and the paired mask remains separate from the historical primary mask.
Removed visits and denominator changes do not prove repair of their old facts.

The [shared refresh record](../../docs/records/evaluation/v3-pair-report.md#paired-access-refresh-2026-10-17)
owns the execution limits and provenance. Original evidence and historical reports
remain retained; this current view replaces the earlier paired presentation.

The ten surviving visits are unchanged. Deleting ART FRONT GALLERY and one
unresolved route check, plus removing the draft density deduction, contributes to
the paired difference. Tokyo Dome City remains the one access UNKNOWN in both stages.
The primary V3 score remains 98.

The original zero-send acquisition stopped on the reviewed edit-provenance replay
defect; its failure receipt remains unchanged. The corrected tool validates reviewed
provenance consistently. The current report is a fresh offline reconstruction using
the original observations and newly bound access material; the stopped package was
not resumed or retried.

## Attempt accountability and storage

The [population report](analysis/resources/population.json) retains four planned,
first-dispatched Planner attempts, four completed workflows and no selected retries.
Selection timing is explicitly **retrospective**. The earlier module-entry command
that never entered the CLI remains a zero-dispatch operator event, not a fabricated
Planner attempt. The [resource report](analysis/resources/tradeoffs.json) accounts
for all four real Planner invocations: 273,532 tokens, 18 model calls including two
embedding calls, and 264 HTTP sends. Repair is a subset counted once; primary and
offline analytical work have separate namespaces.

The four original per-event price books were concatenated without changing any row
or rate, enabling a shared-basis native cost comparison. Generation estimates remain
exactly USD 8.273866550. V2-minus-V1 uses 7,029 more tokens, 21 more HTTP sends and
USD 0.405788660 more reference cost; V3-minus-V2 uses 1,686 more tokens, 13 more HTTP
sends and USD 0.272678315 more reference cost. These are one-case descriptive
differences. Generation and primary retain reference **USD 9.919951025**. The
current paired assessment adds USD 0.0019503; the combined reference total is
**USD 9.921901325**. Google sends and retries for the refresh are zero.
External Codex review billing remains unavailable.

The private compact archive is the local identifier
`benchmark/scratch/case-09/archive/`. Its manifest maps retained original logical
paths under `work/` and implementation snapshots to immutable SHA-256/length entries;
`blobs.zip` stores each byte sequence once. Original captures, reviews, actual actor
records, independent evidence, final reports, stopped-attempt receipts and frozen
preparations remain byte-exact. Redundant staging/attachment copies, assembly helpers
and superseded derived research reports are excluded after dependency checks.

Archive integrity, fresh-root restoration, all five native research tracks, primary
quality, independent paired source replay and public/native projection equivalence
were verified before removing the redundant working layout. Absolute preparation
bindings are not rewritten. Relocated legacy execution replay is not claimed; restore
to the original root for that interface. Root-bounded native report readers independently
verify the restored source closure. Public JSON remains a reader-facing projection,
with shared objects expanded through the material index, rather than an executable
native acquisition bundle.

All submitted activity cost fields remain unspecified, so whole-trip affordability
is unverified. Researcher automatic-case acceptance and blinded human review remain
pending. Earlier raw evidence and historical acceptance decisions are preserved; their current
paired presentations follow the shared authorized refresh.

## AI assistance and human decisions

| Work | Actual performer and supplied context |
| --- | --- |
| Requirements authoring | `/root/case09_author`; complete original request and schema/contract sources only |
| Independent requirements/context review | `/root/case09_requirements_review`; exact authored draft, original request and schema/contract sources; also reviewed timezone, unrestricted transport and ordinary density |
| Independent interests | `/root/case09_interests`; complete original request and necessary schema sources; two categories later bound mechanically to the reviewed spec |
| Final activity roles and occupancy | `/root/case09_activity_review_a` (V0/V1), `/root/case09_activity_review_b` (V2), `/root/case09_activity_review_c` (V3); original request, reviewed spec and exact final activity packets, excluding Planner interpretations, scores and mechanisms |
| Prepared live execution | `/root/case09_execute`; frozen commands, source bindings and approved limits; no semantic decision authority |
| Independent candidate relevance | `/root/case09_relevance_a` and `/root/case09_relevance_b`; disjoint 34-venue identity packets, original request and interest inventory, with independent venue facts; no version, rank, Planner labels or scores |
| Relevance cross-review | `/root/case09_relevance_cross`; all 136 labels and their saved evidence; no new page opens or service requests |
| V3 draft roles, occupancy and correspondence | `/root/case09_draft_review`; exact 11 draft and 10 final-primary activities, original input and reviewed requirements; no Planner findings or scores |
| Paired access refresh | `/root/paired_access_execute`, `gpt-6.1-sol / medium`; seven frozen case packages, execution only; service model `gpt-6-luna / medium` |
| Tool review | `/root/pair_access_standards` and `/root/pair_access_spec`; committed implementation and separate correction, no semantic case acceptance |
| Orchestration and presentation | `/root`; preflight, preparation, exact-byte handoff, technical binding, native checks/replay and public projections/reporting |

The six initial independent review tasks and four offline-analysis review tasks were
dispatched as Codex `gpt-6.1-sol / high`, each with a 20-minute allowance; the execution
child used `gpt-6.1-sol / medium`. The offline stage used four of its five allowed
review tasks; no correction re-review or additional service acquisition was needed.
Actual operation identities, timestamps, input/output hashes and available task and
response messages are retained privately. Dispatch settings are operator evidence;
full platform/tool transcripts, runtime model self-attestation and external
token/billing telemetry are unavailable. Planner and evaluator service calls use the
configured `gpt-6-luna` deployment; retrieval uses the existing embedding space.

The researcher authorized the exact input, execution scope and reference allowances.
The researcher subsequently authorized steps 7-9 with zero new service fees and the
stated review/page limits. Agent review and automated checks do not constitute human
itinerary review or case acceptance. No final acceptance decision has been recorded.
