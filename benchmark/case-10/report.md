# Case 10 London offline acceptance review

Current density-policy results: [final](evaluation/density-final.json) and [same-run Pair](evaluation/density-pair.json). Both are offline derivations under `rtpeval_daily_density_3`; factual evidence, policies and numeric results are unchanged. The [twelve-case replacement](../report.md) awaits researcher acceptance.


**Automatically accepted by the researcher on 2026-10-17, Australia/Sydney, with the disclosed limitations. Delivery and closure are tracked in [Issue #159](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/159).** The selected request covers London, 22–25 October 2026, one traveler and GBP 1,300 for the whole trip. Its hard place obligation is exactly two British Museum visits on different dates. Historic neighbourhoods, parks and art remain soft interests for the rest of the itinerary.

The [original request](../inputs/case-10.json), [reviewed requirements](requirements/reviewed.json), [interest inventory](interests/reviewed.json), [four daily itineraries](itinerary.md) and [material index](material-index.json) identify the exact selection. Generation revision 2 uses source `cc779bb2ece7b312ab3d985cebdd5d6b64b209c3`; the current Primary and process reports use evaluator source `6320785d5e8679cdaf588f334888c1e181a5b31b`.

| Material | Reader view |
| --- | --- |
| Original request | [case 10](../inputs/case-10.json) |
| Reviewed requirements | [reviewed](requirements/reviewed.json) |
| Independent interests | [reviewed](interests/reviewed.json) |
| Daily schedules and origins | [itinerary](itinerary.md) |
| Independent review records | [relevance reviews](interests/relevance-reviews.json) |
| V0 selected generation | [itinerary](generation/v0/itinerary.json), [usage](generation/v0/usage.json), [provenance](generation/v0/provenance.json), [runtime policy](generation/runtime-policy.json) |
| V1 selected generation | [itinerary](generation/v1/itinerary.json), [usage](generation/v1/usage.json), [provenance](generation/v1/provenance.json), [runtime policy](generation/runtime-policy.json) |
| V2 selected generation | [itinerary](generation/v2/itinerary.json), [usage](generation/v2/usage.json), [provenance](generation/v2/provenance.json), [runtime policy](generation/runtime-policy.json) |
| V3 selected generation | [itinerary](generation/v3/itinerary.json), [usage](generation/v3/usage.json), [provenance](generation/v3/provenance.json), [runtime policy](generation/runtime-policy.json) |
| Primary scoring | [summary](evaluation/primary/summary.json) |
| Same-run V3 pairing | [summary](evaluation/v3-pair/summary.json) |
| Candidate process and relevance | [opportunities](analysis/poi-process/opportunities.json), [relevance](analysis/poi-process/relevance.json), [v3 origins](analysis/poi-process/v3-origins.json) |
| Repair and complete stages | [draft difference](analysis/repair/draft-difference.json), [final_primary difference](analysis/repair/final_primary-difference.json), [mechanism](analysis/repair/mechanism.json), [summary](analysis/repair/summary.json) |
| All-attempt resources | [summary](analysis/resources/summary.json) |
| Canonical publication hashes and original sources | [Material index](material-index.json) |

## Primary results

| Version | Overall | Auxiliary | Mean density deduction | FAIL | UNKNOWN |
| --- | ---: | ---: | ---: | ---: | ---: |
| V0 | 66.8333 | 69.3333 | 2.5 | 0 | 18 |
| V1 | 80.8333 | 98.3333 | 17.5 | 0 | 1 |
| V2 | 90.6818 | 98.1818 | 7.5 | 0 | 1 |
| V3 | 97.5 | 97.5 | 0 | 0 | 1 |

All four exact-two, distinct-date British Museum obligations PASS with bounds 2–2. [Primary results](evaluation/primary/summary.json) preserve the final scores and dimension counts. The preceding Primary report remains historical evidence rather than the selected score.

V0 contains conflicting explicit local UTC offsets around its Greenwich activities. The conflict originates in the saved model output. Fourteen possible overlap checks, three opening checks and one route check remain UNKNOWN; possible overlaps are not established violations. Westminster Abbey lacks sufficiently applicable admission/opening evidence in all four versions. That uncertainty remains visible. A zero FAIL count therefore does not establish a conflict-free or fully verified itinerary. Model-supported public-access judgments do not certify API opening hours.

## Candidate process and relevance

| Version | Discovered | Admitted | Enriched | Supplied | Scheduled unique places | Scheduled visit occurrences |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V1 | 43 | 43 | 28 | 14 | 11 | 12 |
| V2 | 54 | 54 | 39 | 14 | 10 | 11 |

The [opportunity summary](analysis/poi-process/opportunities.json) preserves canonical gained/lost sets. V2 has 12 discovered IDs absent from V1, while one V1 discovered ID is absent from V2; 11 are recorded as incremental RAG IDs. Discovery counts describe bounded observed runs, not city-wide coverage.

One independent external-model task reviewed 55 venues against three original interests: 165 judgments, comprising 3 relevant, 109 not relevant and 53 UNKNOWN. Positive labels cover one park and two art venues; no historic-neighbourhood match is positively established by the supplied facts. These facts were largely saved raw Google observations acquired during generation, with separate Primary acquisition where available. Independent review does not make their acquisition independent. Limited venue descriptions leave full relevance/conversion fractions unavailable. The [relevance summary](analysis/poi-process/relevance.json) retains that distinction.

## Repair and continuity

The same-run V3 draft scored **93.0**, with 10 primary visit occurrences and a mean density deduction of 5. Its final primary scored **97.5**, with eight occurrences and no density deduction. Two deterministic accepted deletions removed National Gallery and York Watergate; Repair made no model calls. Both stages have zero FAIL and one Abbey opening UNKNOWN. Continuity has no residual proven failures or unresolved visit correspondence. Removed checks are not counted as repaired factual conditions.

The [paired summary](evaluation/v3-pair/summary.json) preserves these outcomes. The [Repair summary](analysis/repair/summary.json) separately records the descriptive V2/V3 final difference. Higher automatic scores do not establish stronger soft-interest fulfillment: deleting National Gallery is a material art-interest tradeoff. The empty native conditional model-attempt subset does not mean deterministic Repair was absent.

## Resources and verification

[All-attempt accounting](analysis/resources/summary.json) includes four failed revision-1 generation attempts, four completed revision-2 generations, both separately authorized Primaries and the single paired access call. Cumulative observed consumption is **31 chat model calls, two embedding calls, 361 Google requests and 366,534 tokens**. Automatic retries are zero. The frozen conservative reference is **USD 9.718364512**, leaving **USD 30.281635488** within the USD 40 allowance. Account invoices and external Codex tokens/billing remain unavailable.

The final offline review sends no model or Google requests, performs no generation/evaluation reruns and changes no application/evaluator code. Checks cover immutable source hashes, both closed Primary receipts, the paired access receipt, selected publication equivalence, archive contents and restored receipt integrity. Existing successful replay evidence is retained: the current Primary and paired access replay under the current source; the old Primary replays under `ca5e302` with all 90 saved implementation hashes matched. Current-code replay of the old packet refuses changed implementation fingerprints; its original binding is preserved. This review does not claim fresh scoring replay after relocation. Absolute execution paths remain original dependencies.

## System and external assistance

Planner generations, independent requirement authors/reviewers, source-context reviewers, the interest author and the relevance reviewer have separate saved actor records. Requirement review and relevance review are external-model assistance, not human ratings. The relevance task was configured as `gpt-6.1-sol / high`; live execution orchestration used `gpt-6.1-sol / medium`, and the one paired access call used `gpt-6-luna`. The current parent performed source binding, deterministic evidence composition, report assembly, accounting and offline archive checks. Actual external Codex tokens/billing are unavailable.

## Acceptance status

The researcher accepted this exact original input, selected revision-2 outputs, current Primary and completed process analyses with the disclosed limitations. Acceptance concerns faithful, complete and accountable case material; individual itineraries retain their quality uncertainty. Hard museum-count/date obligations are verified, while soft-interest quality and GBP 1,300 affordability are not established by the hard-requirement score.

The remaining limitations are the V0 time conflict, Abbey opening uncertainty, 53 relevance UNKNOWNs, the V3 deletion tradeoff, unavailable account/external-assistance billing, absolute-path historical replay dependencies and deferred blinded human review. Corpus-wide coverage and controlled Repair experiments are outside this selection. This case does not establish causal version superiority, statistical conclusions or a version freeze. Automatic acceptance was confirmed on 2026-10-17, Australia/Sydney. The [case Issue](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/159) owns delivery and closure status. Acceptance does not authorize another case or paid execution.
