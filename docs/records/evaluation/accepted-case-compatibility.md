# Accepted-case compatibility audit

## Scope and baseline

On 18 October 2026 (Australia/Sydney), an offline engineering audit checked the
12 automatically accepted cases against
`9361f9a37fb5845b2837410f65f75e875b9ca019`. The starting worktree was clean.
The scope covered source selection, change impact, saved-material compatibility,
deterministic recalculation and existing regression tests. No Planner generation,
provider acquisition, new model judgment or historical-score replacement occurred.

The [accepted selection index](../../../benchmark/README.md#accepted-selections)
and each linked case report define the exact accepted input, outputs and
limitations. This audit adds current-code evidence to those selections; it does
not turn historical generations into outputs produced by the current Planner.

Task-local scripts and detailed JSON results are retained under the local evidence
identifier `artifacts/accepted-case-audit-20261018/`. They include a 48-row
case/version change matrix, source inventories, current intake/preparation results,
native recalculations, packet comparisons, regression outcomes and before/after
hashes. These ignored files are execution evidence, not a second specification.

## Source preservation and checks

All 604 tracked benchmark files and 1,142 private files retained their initial byte
hashes. The public inventory verified 574 indexed case files and 4,013 resolved
shared-reference links. Archive verification checked 21,321 unique blobs summed
per case, including retained addenda; this is not a global deduplicated count.
All 12 selected native Primary execution receipts verified against their exact
preparation digests and complete file inventories.

Public itineraries were matched to their declared native source projections.
Case-04's documented Nearby-reference redactions were excluded only from that
publication comparison. Case-05/12 publish the V3 `final_primary` subtree, which
omits final-only Nearby recommendations. Every executable check used the complete
archived result bytes, not those public projections.

The current readers accepted all 48 full results and all 36 retained V1-V3
canonical requirement contracts. The 36 canonical contracts round-tripped without
value changes. Some full V3 model round-trips reorder permission-operation sets;
the archived results and submitted itineraries were never serialized back or
replaced. All 12 current native intakes exactly equal their saved producer intakes,
including their optional projection diagnostics.

Historical-profile requirement service checks passed for 39 saved nonempty-input
responses; eight empty-input controls verified that interpretation skips the model.
These are injected saved responses, not new provider responses. Case-07 V2 is the
one unavailable raw-response check: its preserved transport capture contains the
literal key `daily_pace.trip_[REDACTED]`. The required `trip_default` key cannot be
read from those bytes. The current reader rejects them with
`invalid_daily_pace_default`; the separately retained canonical contract, full
result and native intake all validate. The redacted key was not reconstructed.

Case-07 also requires its accepted
[input revision 2](../../../benchmark/case-07/requirements/input-r02.json), dated
22-24 October. The general `benchmark/inputs/case-07.json` still describes 15-17
October and is not the accepted selection. The audit selected the archived input
by its provenance hash. No input file was changed.

## Per-case results

All rows have accepted current intake, valid closed Primary receipts, ready
semantic/numerical populations and complete current requirement/schedule and route
calculations. The complete requirement/schedule and route components exactly
match the original native reports on their saved identity policies. Grounding
identity reports also pass their native source/policy replay checks.

`Bound access` means the current full report correctly rejects an old missing-hours
judgment packet's implementation binding. It does not mean a factual FAIL or a
Planner regression. `Current 6` means the saved source material can also reconstruct
`versioned_api_identity_6` / `requirement_subject_correspondence_2`; `Saved` means
the original identity policy remains replayable but cannot be relabeled as policy 6.

| Case | V0-V2 generation source | V3 generation source | Current preparation | Full quality on saved policy | Identity policy adoption |
| --- | --- | --- | --- | --- | --- |
| [01](../../../benchmark/case-01/report.md) | `b3ddccd5` | `a970002b` | Ready | Native API-only exact; selected supplementary access remains bound | Saved |
| [02](../../../benchmark/case-02/report.md) | `8808340c` | `8808340c` | Ready | Native and corrected API-only exact; supplementary access remains bound | Saved |
| [03](../../../benchmark/case-03/report.md) | `f49503a3` | `f49503a3` | Ready | Bound access | Saved |
| [04](../../../benchmark/case-04/report.md) | `941f4986` | `941f4986` | Ready | Exact native report | Saved |
| [05](../../../benchmark/case-05/report.md) | `b1ab089f` | `b1ab089f` | Ready | Bound access | Saved |
| [06](../../../benchmark/case-06/report.md) | `f49503a3` | `2f53f87f` | Ready | Bound access | Saved |
| [07](../../../benchmark/case-07/report.md) | `2b6a80b4` | `2b6a80b4` | Ready | Bound access | Saved |
| [08](../../../benchmark/case-08/report.md) | `19a4f4d9` | `19a4f4d9` | Ready | Bound access | Current 6 |
| [09](../../../benchmark/case-09/report.md) | `b73c8eed` | `b73c8eed` | Ready with separately sourced subject-price row | Bound access | Saved |
| [10](../../../benchmark/case-10/report.md) | `cc779bb2` | `cc779bb2` | Ready | Bound access | Current 6 |
| [11](../../../benchmark/case-11/report.md) | `bc985c27` | `bc985c27` | Ready | Bound access | Saved |
| [12](../../../benchmark/case-12/report.md) | `3a727628` | `3a727628` | Ready | Bound access | Saved |

Every case also completed a separately labelled API-only calculation and an
explicit `rtpeval_declared_population_1` API-only calculation. These diagnostic
views deliberately omit model-supported access. They do not replace the accepted
access-supported totals or demonstrate a new independent acquisition. Selecting
the declared profile is a separate calculation, not retroactive conversion of a
historical report's profile.

For the nine integrated access packets in cases 03/05-12, all fields outside
`implementation_hashes` and `content_sha256` match the current reconstructed packet:
eligibility, original activities, evidence/source hashes, prompt, schema and request
are unchanged. The selected supplementary packets for cases 01/02 have the same
property. Case-01 also retains an older, unselected phase-B packet whose instruction
text differs; it was not substituted for the selected phase-C assessment.
No fingerprint, request hash or captured judgment was changed to make a report pass.
Exact historical full-access replay remains a producer-code operation; this audit
verified closed bytes and current packet compatibility, not a fresh complete
producer-code replay for every package.

Case-09's original price table lacks the now-required `requirement_subject`
operation. Preparation first stopped with
`Subject stage price unavailable: missing_price_or_billing_context`.
A separate derived price table copied the exact same-model/provider subject row
from case-08's saved selected Primary preparation, with its original reference dates
and source binding. Current native preparation then passed. This is an offline
reference-price compatibility check, not a current live price check or execution
allowance. Original prices, historical costs and billing gaps remain unchanged.

For the other ten cases' identity upgrade attempts, the native consumer rejects the
old V0 model packet with `Identity model original packet/source mismatch`. Cases
08/10 reconstruct policy 6 successfully. The ten failures are policy/source-bound
admission results, not ten new identity verdict failures. A uniform fresh policy-6
evaluation would require compatible new judgment material and any evidence missing
from its prepared plan; the original policy reports remain usable as historical
evidence.

## Change impact and selection rationale

The change matrix compares actual Git file content from each version's recorded
producer to the target, including shared backend modules, version dependencies,
configuration, entry points and dependency locks. File-level ownership is a
conservative screen; shared-file changes were inspected at the hunk level before
making the recommendations below. Matching files do not establish identical live
provider responses or unchanged database contents.

| Change family | Relevant existing coverage | Remaining current-generation question |
| --- | --- | --- |
| Requirement wire/source selections, explicit visit obligations and named-place binding | All saved contracts; historical-wire checks; current-profile accepted 08/10/11/12; regression modules | Earlier hard-transport and dated named-visit paths are useful targeted generation checks in 04/09 |
| Activity roles, numerical populations and IANA/transport handling | All 12 ready populations and unchanged saved requirement/route calculations; time/role regressions | Exercise 04's restricted modes and 11's protected interval through selected current paths |
| V3 best-result search, deadlines, reason compression and protected quantities | Current Repair regressions and accepted 12 r07; historical actual-Repair 05 and no-Repair 11 | Active Repair on 05 and preservation/no-unnecessary-Repair on 11 are complementary checks |
| New common requirement subjects and paired subject policy | Current policy-6 reconstruction for 08/10; historical-policy identity replay for all 12 | If uniform current-policy scoring is requested, refresh evaluator material separately from Planner generation, especially 09's dated subjects |

Case-12 r07's generation source has **no content differences** from the target in
the audited Planner backend, shared generation modules, runtime configuration,
entry points or dependency declarations. Its evaluator source differs. It therefore
does not need another generation merely to adopt the integrated Planner changes.

For cases 08/10/11, shared-file differences include V3-only compression/deadline
configuration and telemetry; the primary supply change serializes nonempty dated
daily visit constraints, which those three requests do not contain. These changes
do not by themselves justify redoing all four versions. Older cases 01-07/09 have
broader changes; their current material-readability results are not end-to-end
generation passes.

## Prepared supplementary scope

On 18 October, authorized steps 2-3 prepared the following bounded engineering
checks at `9d953384e58a0358d232b5e3d04904a353dcfe38`. That revision adds the audit
documentation only; its production content matches the audited target. No Planner
generation, project provider acquisition, database access or independent Primary
execution occurred during preparation. External Codex source-only authoring and
review did occur; public price documentation was consulted separately.

| Case | New generations | Input and check | Independent Primary |
| --- | --- | --- | --- |
| 04 | V0, V1 | New 24-25 October input revision; preserve weekend duration and WALK/TRANSIT-only restriction; check current interpretation and submitted travel | None: partial-version check |
| 05 | V3 | New 26-30 October input revision; preserve five-day request, avoid the Barcelona daylight-saving transition; inspect native best-result/Repair behavior | None: partial-version check |
| 09 | V0, V1 | Exact accepted 22-26 October input; dated Ueno Park visit and Tokyo National Museum quantity | One fresh evaluation combining new V0/V1 with exact accepted V2/V3 |
| 11 | V3 | Exact accepted 22-25 October input; protected 23 October 14:00-16:00 Europe/Paris interval, including travel | One fresh evaluation combining exact accepted V0/V1/V2 with new V3 |

The base scope is **six generations and two independent Primary evaluations**.
Cases 01-03/06-08/10/12 retain existing supporting evidence. No full-suite generation
or blanket identity/opening refresh is included. The two Primary cohorts explicitly
mix generation revisions; neither represents four newly generated versions.
Cases 04/05 cannot use old-date outputs to fill missing version slots or publish
new four-version Primary scores. Case-05 has no explicit weekday requirement, but
its changed dates can still change live availability. Its functional check is not
directly comparable to the original accepted score.

The new requests changed only `start_date` and `end_date`. Distinct source-only
Codex `gpt-6.1-sol/high` agents authored and reviewed their requirements, timezone,
transport, density and interest inventories. Native handoff validation verifies
actual separate identities, ordered UTC times, original inputs, author drafts and
reviewed output hashes. Native requirement, timezone, route, density and interest
consumers accepted the final materials. Interests initially used numeric revision
`1`; the reviewer corrected it to the required string and refreshed final bindings.
Original author drafts remain intact. Agent review is not human review; retained
message transcripts are explicitly partial and external-agent billing is unavailable.

Cases 09/11 reuse byte-identical reviewed requirements and existing source-linked
interest inventories for unchanged original inputs. Only batch/revision envelopes
and relocated inventory references were rebound; original review identities, times
and meaning remain unchanged. Both reused interest inventories pass native
validation after verified public-reference expansion. Recursive restoration and
native collection qualified all five unchanged donor finals. Old occupancy
decisions are not applied to new outputs.

Six native generation preparations completed without `--execute`, using an
unchanged runtime snapshot and distinct future capture paths. Collection correctly
leaves unstarted selected runs unqualified and the batches blocked. A Windows path
length failure during dependency copying was resolved with short task-local paths,
not a collector or system configuration change. Local evidence identifiers are
`artifacts/bounded-revalidation-20261018/` and `.scratch/rv18/`; they are ignored
preparation evidence, not published specifications. Validation confirmed all
1,746 protected original files remain unchanged. No implementation or test changed,
so the earlier 359-test result was not rerun or relabeled as a new test execution.

### Reference allowance and limits

The authorized execution allowance is **USD 40** in reference reservations:

| Reservation | Reference USD |
| --- | ---: |
| 04 V0 / V1 | 0.25 / 4.00 |
| 05 V3 | 7.00 |
| 09 V0 / V1 | 0.25 / 4.50 |
| 11 V3 | 6.00 |
| Two Primary evaluations | 3.00 each |
| One global correction/retest allowance | 10.00 |
| Unallocated price margin | 2.00 |
| Total | 40.00 |

The base reservation is USD 28. The correction allowance permits at most one
additional generation, reserved at up to USD 7, and one additional Primary,
reserved at up to USD 3, across the whole task, not per case. Including correction,
the limits are seven generations and three Primary evaluations, sequentially with
concurrency one. No discretionary retries, score chasing or scope expansion are
included. Any implementation fix still requires its own authorized change scope.

Generation retains the exact native call/token/provider limits in the frozen
runtime snapshot: 600 seconds per run, V3 Repair stage/round limits of 420/150
seconds, at most six proposal model calls and one separate reason-compression call.
Each Primary is limited to 400 Google sends, USD 3 reference cost, 45 seconds per
provider call, 900 seconds total, and model input/output ceilings of 64,000/8,192
tokens. Current native model-stage ceilings are three for 09 and two for 11,
including eligible missing-hours assessment; no model retries are added.

Public [OpenAI pricing](https://developers.openai.com/api/docs/pricing) and
[Google Maps pricing](https://developers.google.com/maps/billing-and-pricing/pricing)
were checked on 18 October. Native generation's original price-basis capture is
preserved; a dated sidecar records the recheck, while derived Primary tables cover
18-22 October. OpenAI retail rates are a reference proxy, not verified Foundry
account billing. Discounts, free quotas, regional differences, tax and external
Codex usage are not established by project telemetry.

Generation has **no in-flight monetary hard stop**. USD 40 is therefore a reference
admission envelope, not an invoice guarantee. Each invocation was admitted after
checking observed usage and remaining reservations. New or unbounded unknown
accounting, insufficient allowance or native limit failures stop dispatch; a
generation overrun cannot be retroactively prevented.

For the preserved first case-05 failure, the authorized correction admitted one
specific **USD 0.05 contingent hold**, taken from the existing USD 2 margin. The
captured request has one Matrix element; the hold exceeds the highest published
standard first-tier Matrix element rate in the checked
[Google price list](https://developers.google.com/maps/billing-and-pricing/pricing).
[Google's reporting guidance](https://developers.google.com/maps/reporting-and-monitoring/reporting)
distinguishes billable and nonbillable HTTP 400 categories, so that status alone
does not establish a zero charge. This hold is neither a priced native event nor
an actual bill, does not rewrite the old null total and does not waive any new
unknown event. Remaining unallocated margin is USD 1.95.

### Bounded execution and correction

The batch and its single authorized correction completed on 18 October, within
the 18-22 October execution window: **six selected qualified new generations,
one preserved failed generation, and two independent Primary executions**. No
corrective Primary or further generation was dispatched.

Execution started at `62f04cddad8635bbef12d116ea84346d0f9788a5`. The first case-05
capture exposed two independent problems and triggered the accounting stop:

- Repair round-2 revalidation sent `DRIVE`, `TRAFFIC_UNAWARE` and `departureTime`
  together. Google returned HTTP 400 because a timestamp is invalid for that
  routing mode. The returned itinerary and three Repair rounds remain preserved,
  but that capture is not the selected successful V3 check.
- RAG connection preparation timed out at its 10-second connection limit, with
  no embedding send or retrieval query. Native qualification correctly marked
  retrieval failed; `deadline_limited` did not mean exhaustion of the 360-second
  RAG phase budget. The same endpoint timed out inside the sandbox but connected
  outside it. Subsequent native read-only preparation outside the sandbox verified
  authentication, corpus/embedding-space compatibility and read-only transaction
  state without embedding, model or Google requests.

Correction `2579e7f71fc2318d3469c8b7b126fd42c4d2a2e8` omits the timestamp at the
Google adapter boundary for default/explicit traffic-unaware driving, preserving
the chosen mode and pricing tier. Traffic-aware/optimal driving and TRANSIT retain
their times; request objects and V0 behavior are unchanged. Remaining executions
used this revision outside the sandbox with the same ignored credentials and
query-only corpus. No project configuration, database content, system permissions
or credentials were changed. Case-04's retained V1 capture made only WALK/TRANSIT
route requests, so the corrected DRIVE branch does not affect its checked path.

| Generation | Selected observation | Reference USD |
| --- | --- | ---: |
| 04 V0 | All six adjacent primary-visit pairs have allowed WALK/TRANSIT declarations | 0.0054891 |
| 04 V1 | Hard mode policy retained; all five adjacent pairs have allowed application-owned transfers | 1.344135235 |
| 05 V3 correction | All required mechanisms completed; one natural Repair round; read-only RAG query completed with an empty result | 2.452579185 |
| 09 V0 | Qualified new final for the unchanged original request | 0.003254585 |
| 09 V1 | Exact-one Ueno Park visit on 23 October and exact-one Tokyo National Museum visit retained in the executable contract | 2.281874900 |
| 11 V3 | RAG returned 20 entities; one natural Repair round; submitted activities and transfers avoid the protected interval | 2.349849695 |

Case-05's corrected capture contains successful traffic-unaware DRIVE responses
without the invalid timestamp. For corrected 05 and new 11, selected round 1
matches Repair final, V3 final-primary and the submitted state; retained proposal
reports support the recorded promotion. These are native same-run consistency
checks, not independent quality or exhaustive-search proofs. Case-04's mode checks
likewise do not prove universal live feasibility. Cases 04/05 remain partial-version
new-date checks without independent four-version Primary scores.

The first CLI registration attempt was rejected before Planner dispatch because
planned slots included pending producer declarations. Separate raw-slot selectors
and byte-verified relocated donor references passed native offline registration
checks. This preparation correction did not consume an extra generation.

### Independent Primary results

Both exact-input cohorts passed native intake, semantic readiness and declared
numerical-population readiness. Prepared timezone, transport and density context
actually entered each package. Case-09 reused 19 role and 19 occupancy decisions
only for unchanged V2/V3 donor outputs; occupancy source batch/record identifiers
were relocated to the new batch with exact input/run/result/pointer/projection
bindings and original-source mappings retained. Review decisions, identities and
times were preserved. No donor judgment was copied onto a newly generated result.
New wire declarations supplied the required new-output coverage without invented
external reviews.

Exact preparation digests were admitted separately before each fresh acquisition.
Current identity/subject policies and eligible missing-hours model assessment were
used; neither evaluation substituted API-only mode. These mixed-generation cohorts
were initially supplementary evidence. The subsequently authorized current-data
replacement is defined below.

| Case | V0 final | V1 final | V2 final | V3 final | Mean daily-density deductions, V0/V1/V2/V3 |
| --- | ---: | ---: | ---: | ---: | --- |
| 09 | 68 | 92 | 92 | 98 | 32 / 8 / 8 / 0 |
| 11 | 90 | 97.5 | 80 | 100 | 0 / 2.5 / 20 / 0 |

The common dimensions are requirements, grounding, non-overlap, opening and routes.
Case-09's five-dimensional auxiliary scores are 100/100/100/98; all versions pass
both visit obligations. One retained V3 opening UNKNOWN concerns Tokyo Dome City:
the submitted activity does not establish public-area versus indoor/ticketed access.
Case-11's auxiliary scores are 90/100/100/100. Its retained V0 has one grounding
FAIL, `model_address_different_place`, with associated opening/route UNKNOWNs from
unresolved identity. V3's protected-time check passes, including travel occupancy.
These failures, unknowns and density deductions were not repaired or hidden.

Primary 09 used 67 Google sends and three model sends, at USD 1.441668275 reference
cost; Primary 11 used 57 and two, at USD 1.190533350. Both completed acquisition and
eligible opening assessment with no acquisition failure or unpriced new event.
Evidence status remains `unresolved` because the disclosed UNKNOWNs remain.

### Completion and limits

The **observed reference subtotal is USD 13.541426140**, including USD 2.472041815
from the preserved failed case-05 attempt. With its separate USD 0.05 hold, budget
admission accounts for **USD 13.591426140**, below USD 40. The full native grand
total and actual invoice remain unavailable because the original failed event is
still `charge_uncertain`; no assumption of zero billing was introduced. Unused
allowance does not authorize more calls.

All seven generation captures passed source-bound staging verification and exact
offline cost-report reconstruction; six selected captures are completion-qualified.
Both closed Primary inventories verified and their complete reports replayed
exactly, including identity/subject judgments, access packets, usage and final
scores. Replay made zero external connections. At bounded-batch closure, all 1,746
original protected files, scores and acceptance decisions retained their original
hashes. Subsequent public-data replacement does not rewrite those frozen native
sources or historical acceptance. Detailed captures,
original failure/stop snapshots, source relocations, runtime/pricing bindings and
final verification remain under the existing task-local evidence identifiers.

The bounded batch and single correction are complete. Reason compression and
deadline exhaustion were not exercised live; an empty case-05 retrieval establishes
the query path, not a positive RAG contribution. No paired, relevance, corpus study
or genuine human review was run. No all-case latest-policy refresh, uniform new
four-version generation, version ranking or automatic version freeze is implied.

## Current-data replacement

On 18 October, the researcher explicitly requested using the qualified reruns to
update the original current data rather than leaving a supplementary report.
The fixed public predecessor is `a85a539680d0a7cc0aab8ce273aa091150b3f121`.
Case-09's canonical selection now uses the new V0/V1 and exact accepted V2/V3
donors; case-11 uses exact accepted r02 V0–V2 and the new V3. Both current Primary
datasets use the completed current-policy evaluations above. Generation sources
remain explicit; unchanged donors are not relabeled as new current-system runs.

The [case-09](../../../benchmark/case-09/report.md) and
[case-11](../../../benchmark/case-11/report.md) reader views, selected itineraries,
source indexes and resource views follow those replacements. Superseded public
material is retained under each case's `analysis/history/pre-current-20261018/`,
with immutable original native evidence and receipts preserved. Case-09's old V1
process/relevance population is no longer current; the new passive capture is
published without inventing independent joins. Case-11's old no-Repair pair is
historical: its replacement has one native Repair round, but no independently
scored draft/final pair. Exact-source donor analyses retain their original bindings.

Case-04/05 retain their original current selections. Their reruns changed dates
and cover only V0/V1 and V3 respectively; mixing those outputs with old-date donor
versions would not form a valid complete case. Promoting those new dates requires
the missing five generations and two independent Primary evaluations under a
separately admitted live scope. No additional live calls are part of this data
replacement. Cases 01–03, 06–08, 10 and 12 remain unchanged.

Promotion verification accepted both native intakes, matched all eight selected
public itinerary projections to their full native results, and replayed both
closed Primary reports exactly without network access. All 271 indexed JSON files
passed public-byte and expanded-value hashes; 110 local Markdown links resolved.
The 1,142 protected private files and all other 373 protected files outside the
two case folders and the shared benchmark index retained their original hashes.
A publication review identified repeated large Repair objects; 67 lossless public
references reduced the replacement Repair view from 3,179,682 to 605,963 bytes.
Its recursively expanded value still exactly matches the private native subtree.

## Regression and limitations

Fourteen existing modules covering requirements, transport time, activity roles,
identity, schedule, declared populations, semantic readiness and V3 Repair search/
timing completed with **359 passed**. No full backend or frontend run was performed.

The routing correction separately reproduced two timestamp assertions before the
fix; its default/explicit unaware, traffic-aware/optimal and existing TRANSIT
controls then passed. Nine relevant adapter, route, hard-mode, Repair and accounting
modules completed with **166 passed**, and scoped Ruff/diff checks passed. Standards
and Spec review found no actionable issue. This does not relabel the earlier 359
tests as newly executed or relax failed-request accounting.

The first guarded test run produced 93 failures and 266 passes because the audit
wrapper also blocked Windows asyncio's internal loopback socket pair. The same
affected semantic module passed 17 tests under the normal repository safeguards.
After the wrapper allowed local event-loop plumbing while continuing to block
external connections, the complete selected set passed all 359 tests. No project
implementation or test was changed. Corrected audit/regression processes recorded
zero external connection attempts; no model, Google or database request was sent.

The offline audit alone does not establish new live output quality. The bounded
batch adds only the stated current-path checks and two mixed-cohort evaluations,
not uniform latest-policy scores, complete historical raw-response reconstruction
or regeneration of research tracks. Existing FAIL/UNKNOWN outcomes, partial evidence
and deferred human review retain their case-specific meanings. Original acceptance
decisions and scores remain historical evidence; the two promoted current selections
use their new Primary data and explicitly scoped dependent analyses.
