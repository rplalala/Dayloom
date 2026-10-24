# Case-04: Singapore automatic selection

## Current selection

Singapore, **25–26 October 2026**, two adults, SGD 800, gardens, major city sights
and views, with walking and public transport only. All four versions were newly
generated once from the same [request](../inputs/case-04.json) at source `4f4d0b5`.
[Primary](evaluation/primary/report.json) and the same-run V3
[Pair](evaluation/v3-pair/report.json) use `rtpeval_daily_density_3`.

The complete replacement is **pending researcher acceptance** under
[#218](https://github.com/rplalala/Dayloom/issues/218).

## Materials

| Material | Current view |
| --- | --- |
| Source binding | [Selection](selection.json), [material index](material-index.json), [evaluated input](evaluation/input.json) |
| Semantic preparation | [Reviewed requirements](requirements/reviewed.json), [interests](interests/inventory.json), [claims review](evaluation/preparation-review.json) |
| Itineraries | [Complete daily schedules and transfers](itinerary.md) |
| Final scoring | [Primary](evaluation/primary/report.json), [quality](evaluation/primary/quality.json) |
| Same-run Pair | [Report](evaluation/v3-pair/report.json), [binding](evaluation/v3-pair/source-binding.json) |
| Candidate process | [Stages and origins](analysis/poi-process/opportunities.json), [relevance](analysis/poi-process/relevance.json), [judgments](interests/relevance-reviews.json) |
| Repair | [Draft](analysis/repair/draft.json), [final primary](analysis/repair/final-primary.json), [decisions](analysis/repair/repair.json), [validation](analysis/repair/validation.json), [mechanism](analysis/repair/mechanism.json), [research](analysis/repair/research.json) |
| Completion verification | [Original interpreted contract](analysis/repair/completion-input.json), [offline verifier](../review_case04.py) |
| Resources | [Selected tradeoffs](analysis/resources/selected-tradeoffs.json), [current execution](analysis/resources/refresh-execution.json), [all-attempt ledger](analysis/resources/all-attempt-resources.json) |

## Results

| Version | Final / 100 | Auxiliary / 100 | Mean pace deduction | Daily primary visits |
| --- | ---: | ---: | ---: | --- |
| V0 | 66.6667 | 96.6667 | 30 | 4 / 4 |
| V1 | 50.0000 | 100.0000 | 50 | 5 / 4 |
| V2 | 61.0000 | 76.0000 | 15 | 4 / 3 |
| V3 | 100.0000 | 100.0000 | 0 | 3 / 3 |

Final scores subtract the equal-date mean pace deduction from the five-dimensional
auxiliary score, floored at zero. Native reports retain exact fractions.

| Version | Dimension | PASS | FAIL | UNKNOWN |
| --- | --- | ---: | ---: | ---: |
| V0 | grounding | 8 | 0 | 0 |
| V0 | non_overlap | 14 | 0 | 0 |
| V0 | opening | 8 | 0 | 0 |
| V0 | requirements | 1 | 0 | 0 |
| V0 | routes | 5 | 1 | 0 |
| V1 | grounding | 9 | 0 | 0 |
| V1 | non_overlap | 16 | 0 | 0 |
| V1 | opening | 9 | 0 | 0 |
| V1 | requirements | 1 | 0 | 0 |
| V1 | routes | 7 | 0 | 0 |
| V2 | grounding | 7 | 0 | 0 |
| V2 | non_overlap | 12 | 0 | 0 |
| V2 | opening | 7 | 0 | 0 |
| V2 | requirements | 0 | 0 | 1 |
| V2 | routes | 4 | 0 | 1 |
| V3 | grounding | 6 | 0 | 0 |
| V3 | non_overlap | 10 | 0 | 0 |
| V3 | opening | 6 | 0 | 0 |
| V3 | requirements | 1 | 0 | 0 |
| V3 | routes | 4 | 0 | 0 |

V0 fails the Singapore Botanic Gardens → National Museum transit check: the
2,583-second route exceeds the 2,100-second scheduled gap by 483 seconds, beyond
the 300-second tolerance. V2 omits the Sultan Mosque → Garden Rhapsody transfer claim; preparation
preserves that omission. Its scheduled Suntec City break occupies its declared
16:00–17:00 interval and is not a freely reusable window.

## Process and Repair

The same-run Pair scores **50 → 100**.
V3 changes from **6/3 → 3/3** primary visits, with 3 removed, 0 added
and 0 replaced visits. The result is `ACCEPTED_COMPLETE`;
Rich completion is `complete` and the stop reason is `authorized_targets_complete`.
Applicable return checks have no blocking findings or unverified checks. Other
diagnostic UNKNOWN observations remain visible and are not relabelled PASS.

All retained operations are reported in the [Repair decisions](analysis/repair/repair.json).
The draft/final Pair measures two stages of this V3 invocation; independent V2
generation is a separate comparison.

The independent relevance review covers **112 venues × 3 interests**: **66 relevant
and 270 UNKNOWN**. It retains 206 compatible historical judgments with their actual
authors, timestamps and evidence, replaces four historical UNKNOWN labels with
new official evidence, and adds 126 labels for 42 new candidates. The twelve-query,
sixteen-open bound and unavailable official pages limit coverage. UNKNOWN labels
remain unresolved; candidate names and discovery queries do not establish relevance.

## Resources

| Stage | Reference allowance USD | Observed reference USD |
| --- | ---: | ---: |
| v0 | 2 | 0.00551885 |
| v1 | 8 | 1.90571106 |
| v2 | 10 | 1.95410831 |
| v3 | 10 | 2.127166475 |
| primary | 6 | 1.120294175 |
| pair | 4 | 1.056 |

Total reference consumption is **USD 8.168798870 / 40**.
Each stage ran once, sequentially, with zero outer retries. Generation uses the
native 8 October retail reference basis; independent evaluation uses the catalog
checked on 24 October. These are estimates, not account invoices or hard dollar
stops for generation. External Codex session costs are separate and unavailable.

Cumulative accounting retains **22 invocation identities**,
**1291 distinct observed events** and a priced subtotal of
**USD 26.471764770**. Its 15 historical unpriced/conflicting
events prevent a complete total. Replaced generations and failed historical
attempts remain in that population; copied artifacts and offline replay add no sends.

## Verification and AI assistance

All four exact native captures passed input/source binding and workflow qualification.
Primary and Pair replay against their saved evidence without network calls. Native
population, opportunity, relevance, Repair and tradeoff reports verify their selected
sources. The public verifiers check the twelve-case exact arithmetic, ranks, usage,
material hashes and new-date V3 completion. Product/runtime code is unchanged.

| Work | Actual external Codex performer |
| --- | --- |
| Requirements author | `/root/oct25_clean_author`, `gpt-6.1-sol / high` |
| Independent requirements, interests and input context | `/root/oct25_source_reviewer`, `gpt-6.1-sol / high` |
| Generation execution | `/root/oct25_execute_generations`, `gpt-6.1-sol / medium` |
| Output-claim preparation | `/root/oct25_clean_output_review`, inherited configuration |
| Primary / Pair execution | `/root/oct25_execute_primary`, `/root/oct25_execute_pair`, `gpt-6.1-sol / medium` |
| Independent venue relevance | `/root/oct25_relevance_review`, inherited configuration |
| Binding, offline reconstruction, publication and verification | `/root`, inherited configuration |

The selected source-only roles did not receive itineraries or scores. The output
review received submitted claims; relevance received stripped venue identities and
independent official evidence. Two preliminary contexts were excluded after
unintended result-summary/internal-field exposure and replaced with fresh contexts.
Actual assistance is separate from Planner/evaluator calls and from human review.
Full external transcripts, exact inherited model metadata, session token usage and
billing are unavailable where not captured; retained partial records are labelled.

Private evidence identifier: `.scratch/case04-oct25/`, containing exact original
captures, source reviews, preparations, receipts, journals and offline reports.
This identifier is not a public navigation dependency.

## Acceptance

The replacement and its limitations are presented for researcher acceptance.
Publication and merge do not supply that decision. Existing blinded answers remain
bound to the itineraries actually shown; #219 and thesis synchronization await
acceptance and are outside this delivery.

## Historical context

The prior 24–25 October publications and the intermediate offline date projection
remain recoverable at [the preceding revision](https://github.com/rplalala/Dayloom/tree/4f4d0b5444faa2dbd42cee19bf18bd04e0b79371/benchmark/case-04).
Original native evidence and earlier acceptance remain bound to those sources.
