# Case 06: Sydney family trip

## Acceptance and selected material

**Case-06 revision 5 final package accepted on 15 October 2026 Australia/Sydney.**
The researcher accepted the exact selected input/results, primary scores, offline
analyses and all stated limitations as the final case-06 data and documentation
baseline. The reviewed package is local commit `6ce08f5`; recording its acceptance
changed status metadata only. Blinded human ratings remain deferred. Case-08/10
are explicitly paused pending a separate start instruction.

The [original request](../inputs/case-06.json) is a Sydney trip on 15–18 October 2026
for three travelers, with a whole-group budget of AUD 2,200. Two adults and a child
enjoy science, nature and outdoor spaces, prefer breaks and less continuous walking,
and have a rental car with a preference for driving. The request bytes and dates are
unchanged. Independently reviewed semantics retain three soft interests, unrestricted
transport, relaxed density and `Australia/Sydney`; there are no hard visit obligations.

The selected data consists of the original V0–V2 results and the authorized V3 a2
result. Each selected generation is complete. V2/a2 retain partial retrieval
observations; producer completion does not establish complete corpus measurement.
Original failed/nonselected evidence is retained separately and contributes to the
all-attempt resource account. It is not substituted for a selected final result.

[Issue #155](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/155) owns the
live acceptance state; [parent #151](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/151)
owns the first-wave budget. This package makes no general version ranking, causal
Repair claim, corpus recall estimate or version-freeze decision. Case-08/10 remain
unstarted, with no automatic queue or backfill.

### Post-fix offline compatibility

The [derived compatibility summary](analysis/compatibility/post-fix.json) records a
passing check on 15 October 2026 against merged source
`8326fb8c017f17df2426275a8634e35b91325394`, Windows CPython 3.12.14, with the original
reference date pinned. All four selected interpretation responses, including V3 a2,
passed the current complete historical-reader service. Three saved canonical v4 contracts
and four complete results read without value changes. The unchanged revision-5 manifest
passed current native intake with no material/projection diagnostics and available V3
paired projections. Relaxed pace and the soft DRIVE preference remain intact; neither an
exact count nor a hard mode restriction is introduced.

Four current-wire controls converted those response values in memory and preserved their
canonical content; they are not new model outputs. No complete generation-graph replay or
primary rescoring was performed. The shared audit's 89-file preservation check predates
this report/index display refresh. The summary retains its result digest and the prior
published report/index bindings. All 35 original indexed JSON materials, selected runs,
revision-5 acceptance, historical scores and source/usage bindings remain unchanged.

The earlier full backend run was 4196 passed / 17 failed / 16 skipped and overlapped
corrections. Sixteen failures have fixes and passing affected retests; one original
mock-provider anomaly did not reproduce and its cause remains unknown. The final full
suite was not rerun, and skipped coverage remains unverified. The malformed legacy pace
quote control still lacks a diagnostic field path despite rejection. The
[shared compatibility record](../../docs/records/v0-v3/semantic-reference-correction.md#post-fix-real-material-compatibility)
owns the detailed execution; this update adds no live calls or new case dispatch.

## Material map

| Material | Final reader view |
| --- | --- |
| Complete schedules, transfers, unscheduled references and recorded POI origins | [Itineraries](itinerary.md) |
| Exact public hashes, original sources, selected runs and lossless reference format | [Material index](material-index.json) |
| Independently reviewed source meaning | [Requirements](requirements/reviewed-requirements.json), [interests](interests/interests.json) |
| Reviewed timezone, transport, density and occupancy | [Schedule](requirements/schedule.json), [transport](requirements/transport.json), [density](requirements/density.json), [occupancy](requirements/occupancy.json) |
| Selected itineraries | [V0](generation/v0/itinerary.json), [V1](generation/v1/itinerary.json), [V2](generation/v2/itinerary.json), [V3](generation/v3/itinerary.json) |
| Selected usage | [V0](generation/v0/usage.json), [V1](generation/v1/usage.json), [V2](generation/v2/usage.json), [V3](generation/v3/usage.json) |
| Selected provenance | [V0](generation/v0/provenance.json), [V1](generation/v1/provenance.json), [V2](generation/v2/provenance.json), [V3](generation/v3/provenance.json) |
| Shared configuration and recorded RAG origins | [Runtime policy](generation/runtime-policy.json), [V2 origins](generation/v2/rag-origins.json), [V3 origins](generation/v3/rag-origins.json) |
| Final independent primary report | [Primary](evaluation/primary/report.json) |
| Candidate stages and independent interest judgments | [Opportunities](analysis/poi-process/opportunities.json), [relevance](analysis/poi-process/relevance.json), [review records](interests/relevance-reviews.json) |
| Same-run V3 stages and Repair observations | [Lossless draft delta](generation/v3/draft-delta.json), [validation](generation/v3/validation.json), [paired diagnostics](evaluation/v3-pair/report.json), [Repair view](analysis/repair/repair.json), [mechanisms](analysis/repair/mechanism.json) |
| Selected and all-attempt resources | [Accounting](analysis/resources/accounting.json) |

Public JSON values use indexed `$case_material_ref` links to store repeated large
objects once. Expanding those references recovers the exact source JSON value.
V3's draft delta reconstructs its original draft from the delivered itinerary.
The index identifies original hashes and subtree pointers. Intrinsic native source
paths are private evidence identifiers; public views are not relocated native
execution bundles. Raw provider/model payloads and private transcripts remain private.

## Final primary results

| Version | Grounding | Non-overlap | Opening | Routes | Auxiliary score | Density deduction | Final primary score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V0 | 87.5 | 100 | 87.5 | 75 | 87.5 | 0 | **87.5** |
| V1 | 100 | 100 | 100 | 100 | 100 | 15 | **85** |
| V2 | 100 | 100 | 100 | 100 | 100 | 5 | **95** |
| V3 | 100 | 100 | 100 | 100 | 100 | 0 | **100** |

The four common dimensions each have weight 1/4. Requirements has no hard checks
and is uniformly excluded. No common-dimension FAIL was found. V0's Sydney Observatory
visit on 18 October retains `model_conflicting_assessment`; unresolved identity
propagates to its opening check and one route. Grounding/opening each have 7 PASS and
1 UNKNOWN, while routes has 3 PASS and 1 UNKNOWN. UNKNOWN remains in the denominator
and reduces verified scores without being asserted as a violation.

Relaxed daily-density deductions are averaged over four requested dates. V1 counts
2/1/3/2 primary visits, giving daily deductions 0/20/40/0 and a mean of 15. V2 counts
2/1/2/2, giving 0/20/0/0 and a mean of 5. V0/V3 each have two visits daily and no
pace deduction. The independent missing-hours assessment covered 10 eligible visits
before final scoring. Model-supported access remains distinct from API-verified hours.

The approved single primary operation completed in 51.75 seconds with exit 0 and its
owned process ended. Acquisition and processing are complete; evidence remains
`unresolved` because of V0's retained UNKNOWN. Limits were USD 10 reference cost,
250 Google sends, two model sends, 64,000 input/8,192 output tokens per model request,
90 seconds per HTTP request and a 1,200-second outer deadline, with zero retries.

## Candidate process and interest relevance

Canonical Google Place IDs are counted once per stage. Nearby-only references are
excluded from scheduled visits. `G/R/M` means Google-only / RAG-only introduction /
mixed Google and RAG origins within the same captured run.

| Stage | V1 canonical places | V2 canonical places | V2 G/R/M | V2 added / V1-only / retained |
| --- | ---: | ---: | --- | --- |
| Discovered | 62 complete | 70 observed, partial | 51/11/8 | Unavailable: V2 inventory is partial |
| Admitted | 56 | 56 | 44/8/4 | 19/19/37 |
| Enriched | 28 | 36 | 24/8/4 | 13/5/23 |
| Supplied | 14 | 14 | 10/1/3 | 4/4/10 |
| Independently confirmed scheduled | 8 | 7 | 6/0/1 | 3/4/4 |

V1's captured origins are Google-only throughout. V2 records 11 observed RAG-only
introductions at discovery, one supplied RAG-only venue and three supplied mixed-origin
venues. Its seven scheduled places contain one mixed-origin venue and no RAG-only
introduction. The report retains query origins, omissions, admission/enrichment/supply
fates and the partial discovery boundary. These sets describe two independent
realizations; they do not isolate a causal RAG effect.

A fresh independent reviewer judged all 91 inventoried subjects against the three
source interests using only saved independent venue evidence. Only 13 subjects have
such evidence. Of 273 interest–venue judgments, seven are relevant (four nature and
three outdoor-spaces judgments), 266 are UNKNOWN and none is established not relevant.
All science judgments remain UNKNOWN because the saved fields do not establish the
needed function. Literal park/garden/zoo/beach functions support the positive labels;
missing descriptions and ambiguous names are not filled from Planner labels or memory.

There are four confirmed relevant supplied venues in each version, and confirmed
relevant scheduled lower bounds of four for V1 and three for V2. Complete relevance
counts, relevant-stage conversion rates and relevance gain/loss comparisons remain
unavailable because of UNKNOWN judgments. No corpus coverage study or additional
venue acquisition was performed.

## Repair and same-run V3 observations

V3 a2 declares `no_authorized_targets`, `repair=null` and zero Repair model sends.
Its draft and final_primary values are identical, including their scheduled visits
and transfers. The delivered itinerary adds only three unscheduled Nearby references;
the lossless draft delta preserves that distinction. Internal validation findings are
retained as producer observations, separate from independent quality judgments.

Native paired diagnostics reused the primary's closed independent observations with
explicit zero-send/zero-cost limits. Both original V3 stages are available, and their
paired primary-score difference is exactly zero. This API-only diagnostic gives
90.625 to each stage with the same three opening UNKNOWNs; it does not import the
primary's model-supported missing-hours judgments. These separate pair scores do not
replace the accepted V3 primary score of 100. Paired source charges are inherited,
not billed again.

The independent V2 and V3 final primary scores differ by +5 points, entirely from
mean density deductions of 5 versus 0; their common-dimension auxiliary scores are
both 100. Since V3 performed no Repair and its own stages are unchanged, this
cross-generation difference is not evidence of Repair improvement.

## Resource account

| Selected generation | Model calls | Google sends | Observed tokens | Native elapsed seconds | Reference USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| V0 | 2 | 0 | 21,232 | 132.437 | 0.00573635 |
| V1 | 11 | 50 | 67,857 | 139.203 | 2.07843713 |
| V2 | 12 | 66 | 73,237 | 150.453 | 2.44711137 |
| V3 | 12 | 75 | 71,837 | 151.532 | 2.627493645 |

V2/V3 model counts each include one embedding call. Selected generation totals are
234,163 tokens and USD 7.158778495 reference cost. The all-attempt ledger includes
five actual generation dispatches: 38 model calls and 232 HTTP sends. One earlier
nonselected failed attempt has one incomplete model HTTP send, unavailable provider
tokens and two unpriced events. Complete all-attempt token/cost totals therefore
remain null; the known subtotal is not presented as a complete total.

Primary evaluation used 65 Google sends and two model sends, with 24,240 input and
2,930 output tokens. Reference cost is USD 1.34649485 (Google 1.342; models
0.00449485). Known generation plus primary consumption is **261,333 tokens and
USD 8.505273345**. The offline follow-up adds zero provider sends and zero current
reference cost. Repair is counted as a subset; paired inherited usage is counted
once; oracle consumption is not assigned to a Planner version.

Actual account invoices and external Codex token/billing data are unavailable.
Reference prices exclude credits, free quotas, discounts and tax. Case USD 40 and
batch USD 200 remain reference allowances rather than invoice hard guards.

## Integrity and retained evidence

The input, selected results and consumed primary report retain their original bytes.
All 35 public JSON materials passed lossless expansion and source-value/subtree
comparison. Native source/receipt replay passed for the accepted primary and for the
zero-send paired operation. The native opportunity, relevance, mechanism and
all-attempt accounting reports retain deterministic source/semantic digests.

Private evidence remains separately under the original ignored case work roots and
`benchmark/scratch/case-06/archive/`. The archive maps original logical paths to exact
SHA-256 blobs and lengths, retaining failed attempts, registration/preparation copies,
raw captures, actual actor records and native dependencies. Originals remain in place.
The archive retains 13,411 logical files in 1,679 unique blobs (4,628,252 compressed
bytes). Fresh restoration reproduced native opportunities, relevance, resources,
mechanisms, V3 paired diagnostics and the primary report. The source-byte recheck
passed. Its `verification.json` records these checks; native absolute-path
declarations are preserved rather than edited.

| Binding | SHA-256 / identity |
| --- | --- |
| Exact input | `fdd5b2c9c0f80ca220dbed91108058b619c5bd9232363c928bd231f8b976796a` |
| V0 result | `326246140a2ca791d6bd73433a606c80cc1eccce354e85ea9a2d36fc814c5942` |
| V1 result | `8e61f4d5aceb0188c5252353c5ddb8cda353ec822b9919fd793592e71d398fc6` |
| V2 result | `0c22b9a3be6d5a09d7ac1a9794363df39f5e7a05c066c10ad0930ce19c6ac962` |
| V3 selected result | `23146d0b67b2e81f6010cfcbe2ce643083899671b2a51bdb7189d57d4de07a1e` |
| Qualified revision 5 manifest | `0cd4ed9a0870428724302c99033cdd560469f11f8eb9593be785d2e1d11f305b` |
| Accepted package source / index | `6ce08f5`; reviewed index `042b44660904803d7914074251aa63eefc831403fafc4efda5db19d6c2dc5540` |
| Primary preparation digest | `16ab31a5aa52c268b241903f69b5f90541a7462ff88b6ad9f7d52f13b3d0c478` |
| Primary final native report | `e2ec4fd28f13479e00191eaf28df89b5bba4376453affe4f1c54073c4e7cf613` |
| Primary closed receipt | `6bffaa787e7d3ec6a705828d7c2f1e0ae5fede709b8143ffc235f85201e9cd23` |
| Generation sources | V0–V2 `f49503a3359ddb6ed64c79465fc010143a5b141c`; V3 a2 `2f53f87f32d9ae45fca5c8b3aa6d6d616757ce24` |
| Primary dispatch source | `5e296d2ccd268dd88fbdcfd8fac628ca59bb3b3b` |
| Offline analysis starting source | `de0a0c7`; no application or evaluator implementation changes |

## Actual assistance and review

| Contribution | Actual performer | Scope and evidence limits |
| --- | --- | --- |
| Source semantics | `/root/case06_author` and distinct `/root/case06_reviewer`, `gpt-6.1-sol/high`, fresh contexts | Independently authored/reviewed original request meaning. Author's acceptance-status-only case-01 index exposure is disclosed; no case-01 quality/results. Original spec, interests and genuine partial records retained. |
| Generation, authorized a2 and primary execution | `/root/case06_execution`, `/root/case06_a2_execution`, `/root/case06_primary_execution`, `gpt-6.1-sol/medium` | Actual prepared commands, outcomes and reported usage retained. Separate execution children did not supply human ratings. |
| Independent relevance | `/root/case06_relevance_review`, fresh context; exact inherited model identity unavailable | Original interests and saved independent venue fields only; no Planner labels, version/stage membership, itineraries or scores. Actual 273 judgments and execution hashes/times retained. |
| Preparation, registration correction, offline analyses and final presentation | Parent Codex agent | Source binding, original preservation, native reports, lossless public views, archive/restoration checks and documentation. No new Planner/provider invocation in this stage. |
| Registration implementation review | `/root/case06_registration_standards` and `/root/case06_registration_spec`, fresh contexts | Standards and Spec checks completed without findings. Detailed correction evidence stays private; exact inherited review-model identity is unavailable. |
| Decisions | Researcher | Authorized the selected generation/replacement, accepted revision 5 primary scores/limitations and approved existing-evidence follow-up. Accepted the complete final package and all limitations as the final case-06 baseline; case-08/10 paused and human quality ratings deferred. |

Complete external-agent transcript exports, exact tokens and invoices remain unavailable;
authentic partial messages and actual outputs are retained. Agent inspection and user
scope approval are separate from real blinded-rater responses.
