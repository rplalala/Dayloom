# Case-07: Paris, France

## Status and selected material

Execution revision 3 is complete through primary scoring and authorized offline
follow-up analysis. **Accepted by the human researcher on 16 October 2026
Australia/Sydney, with the disclosed limitations.** The selected
[date-only input revision](requirements/input-r02.json) covers 22–24 October 2026,
one traveler and EUR 650. The unchanged [original input](../inputs/case-07.json)
covers 15–17 October. Neither earlier results nor scores are replaced.

The [case Issue](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/156)
owns acceptance. This stage performed no generation, scoring, rescoring or project
API calls. Case-11/12 remain unstarted. No human study or corpus study was selected.
These are case observations, not formal version-level research conclusions.

| Material | Reader view |
| --- | --- |
| Full saved schedules, transfers, Nearby references and origins | [Itineraries](itinerary.md) |
| Source paths, exact hashes, extraction pointers and publication format | [Material index](material-index.json) |
| Independent requirements / interests | [Reviewed specification](requirements/reviewed.json), [interest inventory](interests/inventory.json) |
| Selected outputs | [V0](generation/v0/itinerary.json), [V1](generation/v1/itinerary.json), [V2](generation/v2/itinerary.json), [V3](generation/v3/itinerary.json) |
| Primary results and closed-inventory identity | [Saved checks and totals](evaluation/primary/report.json), [receipt summary](evaluation/primary/receipt-summary.json) |
| Candidate pipeline and independent thematic judgments | [Opportunities](analysis/poi-process/opportunities.json), [relevance](analysis/poi-process/relevance.json), [individual reviews](analysis/poi-process/reviews.json) |
| V3 mechanism and actual edits | [Mechanism](analysis/repair/mechanism.json), [structural observations](analysis/repair/observations.json), [native summary](analysis/repair/research.json) |
| Every consumed attempt, including failures | [All-attempt resource ledger](analysis/resources/all-attempts.json) |

## Primary scoring

The preserved primary report uses `rtpeval_declared_population_1`, prepared against
source `2b6a80b437e30dd14826db92f447d52627820e24`. Acquisition completed and the
evidence was decidable. Grounding, non-overlap, opening and routes each received
100/PASS in all four outputs, with no FAIL, UNKNOWN or acquisition failure in
those included checks. These four dimensions receive equal weights.

| Version | Auxiliary score | Main visits by day | Density deduction | Overall score |
| --- | ---: | --- | ---: | ---: |
| V0 | 100 | 3 / 3 / 3 | 10 | 90 |
| V1 | 100 | 3 / 3 / 2 | 6.666667 | 93.333333 |
| V2 | 100 | 3 / 2 / 2 | 3.333333 | 96.666667 |
| V3 | 100 | 2 / 2 / 2 | 0 | 100 |

The source-only specification contains no executable hard obligations (`N=0`), so
requirements are jointly excluded. Daily density is ordinary, without an exact
numeric quota. The included numerical scores are complete; they do not measure
every qualitative preference. The outdoor/exterior interest is collective, not
three separate quotas. Few paid visits and lower cost are qualitative preferences.
Every saved activity cost is unspecified, so these scores do not establish that
the complete trip is affordable within EUR 650.

Six eligible missing-hours/access items received the authorized independent model
assessment before primary scoring. Those judgments remain identifiable separately
from verified Google opening hours. They are not new API facts. Primary scoring
used 69 Google sends and two model sends, with no retry. Its saved report SHA-256
is `3fbe64817e9ef595b393bc750dbb91685e045f24282a9af84d51c35936c45001`;
the 225-file receipt SHA-256 is
`42c52a93c52c77a292db155814ff1f763dbebc30b73890b05b5206147f01f1c9`.

## Candidate opportunities and interests

The live package omitted optional `--opportunity-capture`; no native producer
sidecar was created. Saved ordered searches and trace events do preserve the
candidate stages. The [V1 import](analysis/poi-process/candidate-v1.json) and
[V2 import](analysis/poi-process/candidate-v2.json) are explicitly retrospective
saved-trace imports, with source hashes. Scheduled identity associations were
reconstructed through the native independent identity reader using saved primary
evidence. No candidate membership was inferred from a final itinerary alone.

| Version | Discovered unique IDs | Admitted | Enriched | Supplied | Independently scheduled |
| --- | ---: | ---: | ---: | ---: | ---: |
| V1 | 63 | 48 | 24 | 12 | 8 |
| V2 | 83 observed, partial | 48 | 35 | 12 | 7 |

V2 has 59 Google candidate IDs and 34 RAG-associated IDs, including ten overlapping
IDs and 24 RAG-only introductions. Its saved RAG discovery status is `partial`.
The exact discovered V2-minus-V1 delta is therefore unavailable. Later-stage
membership comparisons remain available for these captured runs. Neither bounded
pipeline counts nor RAG positions measure the complete Paris POI population.
Saved RAG provenance is available for [V2](generation/v2/rag-origins.json) and
[V3](generation/v3/rag-origins.json); origin and relevance have separate meanings.

A fresh independent reviewer judged the 121 unique V1/V2 candidate IDs against the
single reviewed collective interest. The packet excluded stage, version, Planner
queries, RAG ranks, schedules and scores. Existing independent primary identity
evidence supplied venue facts for 17 IDs. It contained mostly names and addresses;
no additional evidence was acquired.

The reviewer returned 13 relevant, zero not relevant and 108 UNKNOWN: 104 IDs had
no independent venue facts, and four had insufficient facts for the thematic
judgment. UNKNOWN is not non-relevance. The exact relevant pipeline totals and
cross-version relevance differences remain unavailable.

| Version | Known relevant discovered | Known relevant independently scheduled | Known relevant end-to-end |
| --- | ---: | ---: | ---: |
| V1 | 11 of 63; 52 UNKNOWN | 7 of 8; 1 UNKNOWN | At least 7 |
| V2 | 12 of 83 observed; 71 UNKNOWN | 4 of 7; 3 UNKNOWN | At least 4 |

End-to-end requires relevance, admission, supply and independent scheduling.
The lower bounds do not establish that V1 is more relevant than V2. The primary
score does not consume these later thematic judgments, so these UNKNOWNs do not
invalidate its available numerical totals.

## V3 Repair and resource interpretation

The saved V3 reason is `no_authorized_targets`: the original internal review had
22 findings but no authorized improvement targets. No model Repair ran. Draft
and final-primary days, activities and transfers are identical. The only
draft-to-final-primary difference is route diagnostics; the final published
itinerary then adds Nearby references. Both differences are retained in the
lossless [draft delta](generation/v3/draft-delta.json) and
[final-primary delta](generation/v3/final-primary-delta.json).

V2 and V3 are separate generations. Their saved final scores differ by 3.333333
points through density, which does not establish a Repair effect. A paired quality
score was not computed: native pair import/replay invokes quality scoring and the
current scope prohibits scoring. Consequently, the native Repair summary honestly
marks its quality comparisons unavailable. Structural observations are complete.

| Reference cost, USD | Current revision | Cumulative case |
| --- | ---: | ---: |
| Generation | 5.992815210 | 11.926259195 |
| Primary evaluation | 1.381919350 | 2.510566450 |
| Total | 7.374734560 | 14.436825645 |

The cumulative ledger includes nine generation attempts and two primary executions,
including the original failed V0. Generation consumed 41 model invocations
(including embeddings), 460,157 observed tokens and 471 HTTP sends across those
attempts. The case retains USD 25.563174355 of its USD 40 reference allowance.
Repair is counted once as a generation subset. All recorded execution limits
passed; native invocation time and the longer operator guard time retain distinct
boundaries. Failure time is not pooled with successful elapsed times.

Costs use each execution's saved dated retail/proxy prices. HTTP sends are transport
observations, not confirmed charges. Actual account invoices and external Codex
token usage/billing are unavailable. No new cost was inferred for this offline stage.

## Preservation and validation

Original failed and successful captures, source-only reviews, supplemental reviews,
scores, reports and native receipts retain their original bytes. The former public
report was copied byte-for-byte before this current reader report was refreshed.
The material index distinguishes exact subtrees, safe projections and shared JSON
references; public views are not native closed acquisition bundles.
The public primary view omits the private identity-model packet and response;
judgments and source identifiers remain available.

The private closeout archive maps original logical paths to deduplicated bytes.
Its verification record covers protected-source hashes, both closed primary
receipts, public expansion/source equivalence, archive integrity and restored
native analysis reports with network and scoring entry points blocked. It does
not claim historical scoring replay or new semantic judgments. No originals are
deleted by that closeout. The closeout did not change application behavior or
previously accepted case data; the separately authorized main integration adopts
Issue #172's prospective contract while preserving those historical materials.

The local main integration also passed 4324 backend tests (16 environment
skips), followed by an AST-preserving formatting correction and 55
affected tests; frontend validation passed 101 tests, build and lint. Current-main
readers accepted 28 saved outputs / 267 activities, and six non-scoring reports
matched their saved semantic hashes. A fresh unexecuted preparation retained the
same declared population. Originals, the exact private archive and both receipts
passed preservation checks. This verifies compatibility without recomputing a
historical primary or paired quality score.

## Acceptance

The researcher explicitly accepted execution revision 3 / input revision 2, its
selected V0–V3 results and reports, and the disclosed limitations on 16 October
2026 Australia/Sydney. This includes partial V2 discovery, 108 relevance UNKNOWNs,
absence of a new paired quality score and unverified EUR 650 affordability. The
decision preserves historical results and supplies no blinded human quality ratings.
Additional evidence acquisition or scoring requires separate authorization. Local
main integration and its checks are authorized; push and PR merge remain deferred.

## Actual AI assistance

The human authorized the date revision, contracts, budgets and execution scope,
and supplied the acceptance decision. External Codex assistance is separate
from the `gpt-6-luna` calls recorded inside the Planner and evaluator.

| Contribution | Actual performer | Inputs and influence |
| --- | --- | --- |
| Original source-only requirements | `/root/case07_author`, `/root/case07_reviewer` | Original request and contracts; supplied the historical independent specification and review |
| Original and post-166 execution | `/root/case07_live`, `/root/case07_post166_live` | Approved execution packages; produced historical generation and primary evidence |
| Supplemental activity review | `/root/case07_activity_review` | Submitted activity claims and independent review material; left five historical items unresolved |
| Revised source-only requirements | `/root/case07_r03_author`, `/root/case07_r03_reviewer` | Revised request and contracts in fresh contexts; supplied the selected independent specification and interest inventory |
| Revised execution through primary | `/root/case07_r03_live` | Frozen approved package; produced the four selected outputs and saved primary score |
| Independent candidate relevance | `/root/case07_r03_relevance` | Blind 121-ID packet and 17 independent venue records; supplied the 13 relevant / 108 UNKNOWN judgments |
| Independent engineering review | `/root/case07_closeout_standards`, `/root/case07_closeout_spec` | Committed material against fixed base `2b6a80b`; Standards identified and verified removal of the private identity-model packet/response from the public view; both axes finished with zero remaining findings |
| Contract implementation, orchestration and closeout | Parent Codex session `/root` | Saved code and evidence; prepared bindings, structural/resource analysis, offline validation and reader presentation |

The selected semantic author/reviewer and relevance reviewer were requested as
`gpt-6.1-sol` / `high`; live execution was requested as `gpt-6.1-sol` / `medium`.
Requested settings are not runtime attestation. Actual model/configuration
attestation, complete platform transcripts, external tokens and billing are
unavailable where the retained actor record says so. The latest relevance review
has [observed execution metadata](interests/relevance-review-execution.json),
including its offset-aware 16 October 2026 times. Private actual tasks, available
transcripts and completion/hash records remain bound to their original sources.
Six bounded case-semantic contributors have been used; engineering review is a
separate role and does not add venue judgments.

## Historical context

The initial V0 failed on `RequirementBoundaryError` / `invalid_daily_pace_scope`.
PR #166 aligned that boundary. The subsequent original-input evaluation retained
V0=90 and unavailable V1–V3 totals because seven generic activities lacked role or
time-occupancy decisions. Supplemental review left five unresolved. Issue #168 and
PR #171 introduced review handoff and pre-primary interception; Issue #172's
second phase introduced the explicit activity contract, new scoring profile and
historical adaptation. The approved date-only revision was independently authored
and reviewed before the current execution. Historical results remain historical;
they were neither rescored nor relabeled as this revision.
