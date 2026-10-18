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

A bounded next stage should first prepare current-path checks around cases
04/05/09/11, selecting only versions and stages needed to cover those questions.
Keep 01-03/06/07/08/10 as preserved supporting selections unless a specific uncovered
path or detected regression requires expansion. This is a proposed coverage set,
not an authorized live dispatch or a claim that unexecuted paths passed.

Date and native-intake constraints affect that preparation:

- On 18 October, original accepted inputs 01-06 fail the current new-run start-date
  gate; accepted inputs 07-12 pass. Historical date controls do not authorize a
  forged runtime clock. Any future-date variant needs a separate input revision
  and consistent date-dependent constraints/reviews.
- Native Primary intake requires four selected finals for one exact input.
  A partial-version generation check is not a new complete Primary dataset. If
  new dates are necessary, old-date outputs cannot fill its other version slots.
  A complete new evaluated case may therefore require four generations for that
  revised input, while the other cases remain untouched.
- New outputs require their own output-specific review coverage. Reuse old
  evidence or reviewed judgments only where native source/plan contracts admit
  it; otherwise prepare the missing acquisition explicitly. Report mixed producer
  revisions where applicable rather than claiming uniform new generation.

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
