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

## Change impact and bounded follow-up

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

The proposed execution allowance is **USD 40**, subject to explicit live approval:

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
admission envelope, not an invoice guarantee. The parent admits one invocation at
a time after checking observed usage and all remaining reservations. Unknown
accounting, insufficient remaining allowance or any native limit failure stops
subsequent dispatch. A generation overrun cannot be retroactively prevented.

### Remaining execution gates

The execution window is 18-22 October inclusive, Australia/Sydney. Check the actual
date before dispatch; expiration stops execution rather than forging a runtime
date. Unchanged production content and frozen input/runtime/price hashes are
required. Environment-file presence was checked, but credential authentication and
database/RAG access remain untested; no secrets were loaded during preparation.

After generation, newly submitted outputs require genuine output-specific review.
Only then can cases 09/11 assemble complete native manifests, pass intake/semantic
readiness, derive exact acquisition plans and produce native preparation digests.
The parent must verify required context/reviews actually entered those packages,
check their resource estimates and admit each exact digest. Prepared command
templates do not claim these output-dependent packages already exist or authorize
their execution. New current-policy judgments belong only to these two cohorts.

If case-05 naturally does not exercise Repair, report that coverage gap; do not
force Repair or repeat the run. Report violations, UNKNOWN and missing evidence
without changing intended V0-V3 behavior. The remaining finite stages are the
approved batch, at most the single bounded correction/retest cycle if applicable,
and one consolidated update to this record. Stop at the present preparation gate
until live scope and allowance are explicitly approved.

## Regression and limitations

Fourteen existing modules covering requirements, transport time, activity roles,
identity, schedule, declared populations, semantic readiness and V3 Repair search/
timing completed with **359 passed**. No full backend or frontend run was performed.

The first guarded test run produced 93 failures and 266 passes because the audit
wrapper also blocked Windows asyncio's internal loopback socket pair. The same
affected semantic module passed 17 tests under the normal repository safeguards.
After the wrapper allowed local event-loop plumbing while continuing to block
external connections, the complete selected set passed all 359 tests. No project
implementation or test was changed. Corrected audit/regression processes recorded
zero external connection attempts; no model, Google or database request was sent.

The audit does not establish current-model output quality, new live provider
behavior, uniform latest-policy scores, complete historical raw-response
reconstructibility or a complete regeneration of candidate/Repair research tracks.
Existing FAIL/UNKNOWN outcomes, partial evidence and deferred human review retain
their case-specific meanings. Original acceptance decisions and scores stand;
remaining validation is explicitly bounded to the uncovered paths above.
