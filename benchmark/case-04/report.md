# Case-04: Singapore automatic selection

## Current selection

Singapore, 24–25 October 2026, two adults, SGD 800, walking and public transport.
The [original request](../inputs/case-04.json) and reviewed requirements are unchanged.
The [selection](selection.json) binds V0/V1 to source `62f04cd`, V2 to `986ff39`,
and the new V3 invocation `case-04-rich3-v3-a1` to `a391c2c`.
Primary and the same-run Pair use `rtpeval_daily_density_3`.

This replacement is **pending researcher acceptance**. It is published for complete
inspection; prior acceptance remains bound to the earlier selected artifacts.

## Materials

| Material | Current view |
| --- | --- |
| Input and semantic inputs | [Original request](../inputs/case-04.json), [reviewed requirements](requirements/reviewed.json), [interest inventory](interests/inventory.json) |
| Schedules and actual origins | [Complete daily schedules](itinerary.md) |
| Final scoring | [Primary](evaluation/primary/report.json), [native quality](evaluation/primary/quality.json) |
| Same-run V3 pair | [Independent report](evaluation/v3-pair/report.json), [exact source binding](evaluation/v3-pair/source-binding.json) |
| Candidate process | [All stages, origins and omissions](analysis/poi-process/opportunities.json), [independent relevance](analysis/poi-process/relevance.json), [actual review records](interests/relevance-reviews.json) |
| Repair | [Draft](analysis/repair/draft.json), [final primary](analysis/repair/final-primary.json), [complete Repair](analysis/repair/repair.json), [validation](analysis/repair/validation.json), [mechanism](analysis/repair/mechanism.json), [native research](analysis/repair/research.json) |
| Resources | [All-attempt ledger](analysis/resources/all-attempt-resources.json), [selected-cohort tradeoffs](analysis/resources/selected-tradeoffs.json), [new batch consumption](analysis/resources/refresh-execution.json) |
| Publication integrity | [Material index](material-index.json) |
| V0 selected generation | [Itinerary](generation/v0/itinerary.json), [usage](generation/v0/usage.json), [usage summary](generation/v0/usage-summary.json), [provenance](generation/v0/provenance.json), [runtime](generation/v0/runtime-policy.json), [cost](generation/v0/cost-report.json) |
| V1 selected generation | [Itinerary](generation/v1/itinerary.json), [usage](generation/v1/usage.json), [usage summary](generation/v1/usage-summary.json), [provenance](generation/v1/provenance.json), [runtime](generation/v1/runtime-policy.json), [cost](generation/v1/cost-report.json) |
| V2 selected generation | [Itinerary](generation/v2/itinerary.json), [usage](generation/v2/usage.json), [usage summary](generation/v2/usage-summary.json), [provenance](generation/v2/provenance.json), [runtime](generation/v2/runtime-policy.json), [cost](generation/v2/cost-report.json) |
| V3 selected generation | [Itinerary](generation/v3/itinerary.json), [usage](generation/v3/usage.json), [usage summary](generation/v3/usage-summary.json), [provenance](generation/v3/provenance.json), [runtime](generation/v3/runtime-policy.json), [cost](generation/v3/cost-report.json) |

## Results

| Version | Final / 100 | Auxiliary / 100 | Mean density deduction | Daily primary visits |
| --- | ---: | ---: | ---: | --- |
| V0 | 66.6667 | 96.6667 | 30 | 4 / 4 |
| V1 | 60.0000 | 100.0000 | 40 | 5 / 2 |
| V2 | 85.0000 | 100.0000 | 15 | 4 / 3 |
| V3 | 100.0000 | 100.0000 | 0 | 3 / 3 |

The final score is the five-dimensional auxiliary score minus the equal-date mean
density deduction, floored at zero. The native reports retain exact fractions.

| Version | Dimension | PASS | FAIL | UNKNOWN |
| --- | --- | ---: | ---: | ---: |
| V0 | grounding | 8 | 0 | 0 |
| V0 | non_overlap | 14 | 0 | 0 |
| V0 | opening | 8 | 0 | 0 |
| V0 | requirements | 1 | 0 | 0 |
| V0 | routes | 5 | 1 | 0 |
| V1 | grounding | 7 | 0 | 0 |
| V1 | non_overlap | 12 | 0 | 0 |
| V1 | opening | 7 | 0 | 0 |
| V1 | requirements | 1 | 0 | 0 |
| V1 | routes | 5 | 0 | 0 |
| V2 | grounding | 7 | 0 | 0 |
| V2 | non_overlap | 12 | 0 | 0 |
| V2 | opening | 7 | 0 | 0 |
| V2 | requirements | 1 | 0 | 0 |
| V2 | routes | 5 | 0 | 0 |
| V3 | grounding | 6 | 0 | 0 |
| V3 | non_overlap | 10 | 0 | 0 |
| V3 | opening | 6 | 0 | 0 |
| V3 | requirements | 1 | 0 | 0 |
| V3 | routes | 4 | 0 | 0 |

V0 has one route FAIL: Botanic Gardens to National Gallery requires 2,612 seconds
against a 2,100-second submitted gap; the 512-second deficit exceeds the 300-second
tolerance. All other common checks pass. Primary has no unresolved independent
checks or acquisition failures. No missing-hours model assessment was needed.

## Process and Repair

The [independent same-run Pair](evaluation/v3-pair/report.json) scores the new V3
draft **50 → 100**. Its auxiliary score stays 100; the density deduction falls
from 50 to zero. Counts are **5/4 → 3/3**, with three actual deletions and no
additions or replacements. These are the two stages of one V3 run.

| Attempt | Operation | Decision |
| --- | --- | --- |
| 1 | Delete Saturday Botanic Gardens | Adopted |
| 2 | Delete Saturday Buddha Tooth Relic Temple | Adopted |
| 3 | Delete Sunday Gardens by the Bay | Rejected: sourced experience goal satisfaction decreased |
| 4 | Delete Sunday Singapore Skyline View | Adopted |

All four proposals are deterministic `system_delete`; Repair made no model calls.
Both retained dates meet the three-visit target. The overall Repair result remains
`ACCEPTED_PARTIAL`, with stop reason `authorized_targets_complete`, target state
`reached` and completion **`unavailable`**. The first-day coverage check is UNKNOWN
because `same_day_remaining_hours_unsupported`. Planner suitability, budget and
semantic findings also remain visible in [validation](analysis/repair/validation.json).
Independent Primary/Pairs passing their own checks does not certify these separate
Planner return conditions. This run is not counted as fully successful Rich Repair.

V1/V2 [candidate opportunities](analysis/poi-process/opportunities.json) and
[relevance](analysis/poi-process/relevance.json) retain the captured donor results.
Their joins were rebuilt against the new Primary canonical identities through the
native offline research path. The 267 existing relevance verdicts remain 65 relevant
and 202 unknown; only selection bindings change. Author, dates, evidence and
rationales are retained. Partial discovery and UNKNOWN relevance remain limitations.

## Resources and limitations

| Authorized stage | Reference allowance, USD | Recorded reference cost, USD |
| --- | ---: | ---: |
| V3 generation | 10 | 2.12482589 |
| Primary | 6 | 1.1608993 |
| Pair | 4 | 1.205 |
| Total | 20 | 4.49072519 |

Each stage ran once, with zero outer retries. Pair sent 61 Google requests
(24 Details, 20 Search, 17 Routes), all HTTP 200, with no model calls.
Its native offline replay and the source-bound Repair, opportunity, relevance,
population and selected-tradeoff reports pass. Copies and replays incur no new calls.

The [cumulative ledger](analysis/resources/all-attempt-resources.json) retains
16 invocation identities and 890 distinct observed charge/transport events,
including the replaced V3 and earlier failures. Its priced subtotal is
USD 18.30296590; the complete total is unavailable because 15 historical events
have conflicting prices. Transport-only observations have zero additional cost;
their model charges are counted once. The selected-generation population contains
exactly one V3 run. Actual account billing and external Codex assistance costs are
unavailable; these are reference estimates, not invoices.

## AI assistance

External Codex coordinator `/root` prepared the 23–24 October 2026 source bindings,
qualified saved outputs, replayed reports, computed density/resource summaries and
wrote the reader material from the original request, selected captures, evaluator
evidence and retained histories. This influenced selection and presentation, not
new relevance judgments. `/root/execute_217_v3`, `/root/execute_217_primary` and
`/root/execute_218_pair` executed the approved prepared jobs using
`gpt-6.1-sol / medium`, one invocation each with zero outer retries. These external
roles are separate from the studied Planner/evaluator model calls recorded in usage.

`/root/review_217_claims` reviewed only the original request and submitted claims;
its output-specific role assessment entered Primary preparation. An earlier role
exposed to Planner annotations was excluded, as documented in the
[Primary record](../../docs/records/evaluation/2026-10-24-rich-primary.md).
`/root/standards_review_218` and `/root/spec_review_218` reviewed the committed
replacement against repository standards and #218. The coordinator validated exact
source projections, native replays, arithmetic, indexes and published references;
agent review is not researcher acceptance.

Reused semantic author/reviewer identities and dates remain in the
[requirements](requirements/reviewed.json) and [interest inventory](interests/inventory.json).
The retained October 18 selection was coordinated by `/root`, executed by
`/root/refresh_live_executor` using `gpt-6.1-sol / medium`, and inspected by
`/root/refresh_standards_review` and `/root/refresh_spec_review`.
Independent relevance performer `/root/relevance04_clean` received the source
request, reviewed requirements/interests and unranked venue identities, excluding
itineraries, scores and Planner relevance. A preceding handoff exposed case-status
summaries and was excluded; only the clean-context judgments are selected.
[Actual lookup limits and gaps](interests/relevance-assistance.json) remain available.

The researcher authorized scope, data destinations and budgets; acceptance of this
replacement remains pending. Exact external model identifiers outside the verified
execution roles, complete transcripts, external token totals and billing are
unavailable. Recorded source provenance is retained rather than inferred.

## Acceptance

The complete replacement, its three-per-day itinerary and disclosed incomplete
Planner return checks await the researcher's decision under
[#218](https://github.com/rplalala/Dayloom/issues/218). Publication and merge do not
constitute acceptance. The actual decision must precede
[#219](https://github.com/rplalala/Dayloom/issues/219) content synchronization.
Existing blinded answers remain tied to the itinerary shown to each reviewer.

Earlier acceptance records and original receipts remain immutable in private
evidence and Git history; the exact preceding publication is recorded in the index.
