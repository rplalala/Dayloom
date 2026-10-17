# Case-02: London evaluation report

The [original request](../inputs/case-02.json) is London, United Kingdom,
15–17 October 2026 inclusive, two travelers and a GBP 1,200 whole-group,
whole-trip budget, with empty additional preferences. Independent source-only
review records no additional obligations or POI interests and unrestricted
transport. The selected batch is `case-02-batch`, revision `case-02-material-r2`.

The final model-supplemented primary scores are **84.4444, 74.1667, 90.2083 and
100.0000** for V0–V3. Six missing-hours visits receive model-supported access
PASS; three Westminster Abbey admission checks remain UNKNOWN. V0's British
Museum opening FAIL is retained. A score of 100 does not establish verified
opening hours for the model-supported visit.

## Acceptance and material

The human user accepted the selected input, results and all stated limitations on
**14 October 2026 Australia/Sydney**, authorizing archival of the reviewed material
at commit `9a82d33334199169f33f1e977437dec5af9fc6a9`. Automatic generation,
evaluation, candidate/Repair analysis and all-attempt resource reconciliation are
complete. Blinded human assessment remains a separate deferred stage.

The private archive retains 4,589 original logical files backed by 727 unique byte
sequences, compressed to 3,330,822 bytes. Original requests, selected and failed
captures, semantic/actor records, reports, receipts and consumed native dependencies
retain their original hashes and byte lengths. The [common retention policy](../README.md#private-archive-retention)
governs restoration and cleanup; acceptance does not itself authorize another live
run, Git publication or Issue closure.

Fresh restoration verified every retained file's hash and length, all public
source bindings, exact original/corrected primary reports, supplemented opening,
paired evidence and four native process/resource reports. Replay used restored
case bytes with read-only historical-path mapping and zero network attempts.
Redundant working copies and the temporary restoration were removed after checks.

The [material index](material-index.json) records exact original sources, subtree
locations, publication hashes and transformations. These public views preserve
selected schedules and reported metrics; the original closed native bundles
remain the replay authority. Source-labelled public projections do not replace
their native preparations or receipts.

| Material | Reader view |
| --- | --- |
| Original request | [case 02](../inputs/case-02.json) |
| Reviewed requirements | [reviewed requirements](requirements/reviewed-requirements.json) |
| Independent interests | [interests](interests/interests.json) |
| Daily schedules and origins | [itinerary](itinerary.md) |
| Recorded RAG origins | [poi origins](generation/poi-origins.json) |
| V0 selected generation | [itinerary](generation/v0/itinerary.json), [usage](generation/v0/usage.json), [provenance](generation/v0/provenance.json), [runtime policy](generation/runtime-policy.json) |
| V1 selected generation | [itinerary](generation/v1/itinerary.json), [usage](generation/v1/usage.json), [provenance](generation/v1/provenance.json), [runtime policy](generation/runtime-policy.json) |
| V2 selected generation | [itinerary](generation/v2/itinerary.json), [usage](generation/v2/usage.json), [provenance](generation/v2/provenance.json), [runtime policy](generation/runtime-policy.json) |
| V3 selected generation | [itinerary](generation/v3/itinerary.json), [usage](generation/v3/usage.json), [provenance](generation/v3/provenance.json), [runtime policy](generation/runtime-policy.json) |
| Primary scoring | [quality report](evaluation/primary/quality-report.json) |
| Same-run V3 pairing | [pair report](evaluation/v3-pair/pair-report.json) |
| Candidate process and relevance | [selected process](analysis/poi-process/selected-process.json) |
| Repair and complete stages | [draft](analysis/repair/draft.json), [final primary](analysis/repair/final-primary.json), [repair summary](analysis/repair/repair-summary.json) |
| All-attempt resources | [accounting](analysis/resources/accounting.json), [population summary](analysis/resources/population-summary.json) |
| Canonical publication hashes and original sources | [Material index](material-index.json) |

## Primary scores and evidence

Grounding, non-overlap, opening and routes have equal weight. Requirements are
N/A. Grounding, non-overlap and routes score 100 in every selected final. Ordinary
daily-density deductions apply after the common-dimension score. Counts below
are opening PASS / FAIL / UNKNOWN.

| Version | Corrected API-only primary | Final primary | Auxiliary | Density deduction | API basis | Model basis |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| V0 initial | 78.8889 | 84.4444 | 94.4444 | 10.0000 | 5 / 1 / 0 | 2 / 0 / 1 |
| V1 second attempt | 69.1667 | 74.1667 | 97.5000 | 23.3333 | 7 / 0 / 0 | 2 / 0 / 1 |
| V2 initial | 87.0833 | 90.2083 | 96.8750 | 6.6667 | 6 / 0 / 0 | 1 / 0 / 1 |
| V3 initial | 95.8333 | 100.0000 | 100.0000 | 0.0000 | 5 / 0 / 0 | 1 / 0 / 0 |

Google hours are still absent for 3, 3, 2 and 1 visits respectively. The model
does not fill those fields or invent exact hours. It assesses the submitted
access intent and full visit interval. Buckingham Palace, Big Ben and Covent
Garden account for the six model-supported public outdoor/exterior PASS checks.
The remaining UNKNOWN is Westminster Abbey on 15 October in V0, V1 and V2:
the original activity implies indoor/ticketed admission without applicable hours.
V0's British Museum visit on 17 October extends 1,800 seconds beyond the
supported opening interval and remains FAIL.

All 33 final activities pass independent identity grounding, and all 21 route
checks PASS. The original primary preparation omitted an explicit transport
review. An independent source-only review corrected that omission; the evidence
request plan was unchanged. Historical corrected API-only reports and the
subsequent access assessment remain distinct, bound outputs. New normal runs
complete applicable access assessment before their single final score.

## Candidate POI process

The selected-final view compares V1's successful second attempt with V2's first
attempt. Canonical places are counted once per stage; nearby references do not
count as scheduled visits. Discovery, admission, enrichment and supply captures
are complete, and scheduled memberships use independent final identity evidence.

| Selected run | Discovered | Admitted | Enriched | Supplied | Scheduled |
| --- | ---: | ---: | ---: | ---: | ---: |
| V1 second attempt | 60 | 48 | 24 | 12 | 10 |
| V2 first attempt | 73 | 48 | 29 | 12 | 8 |

| Stage | Retained | Gained in V2 | Lost from V1 |
| --- | ---: | ---: | ---: |
| Discovered | 60 | 13 | 0 |
| Admitted | 41 | 7 | 7 |
| Enriched | 22 | 7 | 2 |
| Supplied | 10 | 2 | 2 |
| Scheduled | 7 | 1 | 3 |

V2 discovery has 53 Google-only, 12 RAG-only and 8 mixed-origin places. Its
12 RAG-only discoveries are incremental against its own pre-RAG Google set.
None enters the final supplied set. Four mixed-origin places are supplied and
independently scheduled, alongside four Google-only scheduled places. RAG used
one default query, returned 20 unique entities and recorded 12 detail sends,
one embedding send, no fallback sends and no cache hits. These are mechanism
observations, not independent relevance judgments or causal attribution.

The empty independently reviewed interest inventory makes relevance and
interest conversion N/A. No corpus coverage or recall claim is made. The failed
first V1 attempt separately captured 62 / 48 / 24 / 12 places across the four
candidate stages, but produced no final itinerary. Its scheduled set is unavailable.

## Same-run Repair and independent final differences

V3's eight-visit draft became a six-visit final through two `system_delete`
rounds, with no Repair model call. Westminster Abbey and Big Ben on 16 October
were removed; the final has two visits per day. Producer completion records
`ACCEPTED_COMPLETE` / `authorized_targets_complete`. Its recorded day-coverage
regression remains visible in the Repair summary.

The [same-run paired report](evaluation/v3-pair/pair-report.json) applies the same source-bound missing-hours
access policy to the original V3 draft and final-primary stages. Saved Google
observations retain their exact provenance; eligible access gaps receive a fresh
assessment. Identical activity/time/evidence contexts share one decision. Primary
scores, original activities and factual API-hours coverage are unchanged.

| Same-run stage | Overall / 100 | Auxiliary / 100 | Density deduction | Opening P / F / U | Route UNKNOWN |
| --- | ---: | ---: | ---: | --- | ---: |
| Draft | 80.208333 | 96.875 | 16.666667 | 7 / 0 / 1 | 0 |
| Final primary | 100 | 100 | 0 | 6 / 0 / 0 | 0 |

The paired overall change is **+19.791667 percentage points**.
The 17 October 2026 refresh used one model call, zero Google sends
and zero retries, for **USD 0.00105055** reference cost. Native source, model-response
and receipt replay passed offline. Model-supported access is not certified opening
hours, and the paired mask remains separate from the historical primary mask.
Removed visits and denominator changes do not prove repair of their old facts.

The [shared refresh record](../../docs/records/evaluation/v3-pair-report.md#paired-access-refresh-2026-10-17)
owns the execution limits and provenance. Original evidence and historical reports
remain retained; this current view replaces the earlier paired presentation.

Six visits continue and two are removed; no visit is added or replaced. The final
display adds only unscheduled reference recommendations after final-primary scoring.

Independent V2 and V3 model-supplemented finals differ by 9.7917 points. V2 is
not the V3 draft; this descriptive difference does not establish causal Repair
improvement. Native first-dispatched research reports remain separate from the
retry-selected four-final quality package, rather than relabeling V1's retry.

## Attempts, resources and verification

Native first-dispatched completion is 3 / 4; the authorized V1 retry succeeds,
giving four selected finals across five total attempts. The failed first V1
attempt remains in the census and consumption denominator.

| Attempt | Outcome | Model calls | HTTP sends | Observed tokens | Reference priced USD |
| --- | --- | ---: | ---: | ---: | ---: |
| V0 initial | Completed | 1 | 1 | 7,235 | 0.002514175 |
| V1 initial | Failed | 3 | 55 | 4,201 subtotal | 1.537179100 subtotal |
| V1 second | Completed | 3 | 57 | 36,086 | 1.606435525 |
| V2 initial | Completed | 4 | 69 | 36,527 | 1.814211425 |
| V3 initial | Completed | 4 | 70 | 35,874 | 1.846007550 |

Generation totals are 15 model calls, 252 HTTP sends and 119,923 observed model
tokens, with four embedding tokens reported separately;
the failed main call's tokens and charge remain unknown. Selected successful
generation estimates sum to USD 5.269168675; all-attempt generation priced
subtotals sum to USD 6.806347775. Repair is a subset counted once.

Original primary acquisition used 59 Google requests and one identity request,
11,240 input and 1,256 output tokens, and zero retries; reference USD 1.272032925.
Access assessment used one `gpt-6-luna / medium` request, 10,541 input and 2,277
output tokens, and zero retries/Google sends; reference USD 0.002456050. Its
USD 0.05 stage allowance stayed within the original USD 50 case allowance
(generation 40, evaluation 10). Known priced reference consumption is
**USD 8.081887300**, including the paired refresh. Actual account invoices, the failed V1 main charge and external
Codex usage/billing are unavailable. Reference allowances are not invoice caps.

Parent verification confirms exact denied-network replay for supplemented
opening, paired evidence and all four native population/opportunities/relevance/
resource reports. The preserved original primary was also replayed successfully.
Public itinerary JSON subtrees and metric projections match their declared
sources. Offline preparation corrections and the wrapper's anomalous shell exit
remain in private observations; a separate native paired replay exited 0 and
matched exactly.

## AI assistance and source revisions

Generation source is `8808340ceae7f6bd5688eccf4f4b461a98934b2b`. Current access,
paired and process verification uses `ab78e0ed8c4f3b92f39ed04ee67f6c05fae5f4a3`.
Original dates, result hashes, attempts and native receipts are retained.

Distinct external Codex executions authored and reviewed source-only requirements
and interests; another source-only execution reviewed transport. A current-session
execution child ran the bound live access assessment and reported its observations;
the parent checked artifacts and replay and assembled process/public views.
Session-requested external settings were `gpt-6.1-sol / high`; complete platform
telemetry, transcripts and provider billing are not available for every execution.
Available authentic records and their gaps remain private. Agent review is not
human review.

Studied generation/identity/access calls use `gpt-6-luna`; native access reasoning
is `medium`. The first access dispatch was rejected before process creation by
automatic approval review. Explicit human authorization of the nine-visit payload
and existing provider then allowed the single successful call. The rejected
dispatch sent nothing and incurred no studied-provider consumption.
