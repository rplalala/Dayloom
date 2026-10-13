# V3 development record

This history tracks the progression from read-only validation to bounded Repair,
its failed development cases and later corrections. Current behavior is maintained
in the [V3 contract](../../0005-validation-repair%28v3%29.md); accepted boundaries
and evidence are summarized in the [milestone](v3-milestone.md) and
[September 25 closeout](v3-closeout.md). Historical statements retain their own status.

The September 26 semantic implementation and default-on quantity review followed
closeout; obsolete optional repetition configuration was removed while unauthorized
repeat repair remained automatic. The [policy decision](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/36)
records that transition. Earlier default-off values below are historical, not current
requirements. Post-closeout departure-window, adopted-summary and injected-policy
corrections are recorded in [closeout](v3-closeout.md#mechanism-boundaries-and-shared-corrections).

Unless a section records actual execution, validation here used injected providers
and offline tokenization. Synthetic sizing and reconstructed fixtures establish
neither live model behavior nor factual travel feasibility. These are development
observations rather than formal benchmarks or version freezes; historical permissions
do not authorize further execution. Raw evidence and failed outcomes remain unchanged.

## Shared baseline update (2026-09-22)

Open-Meteo Weather and the 14-selectable-date/10-travel-day input boundary are shared V0/V1/V2
baseline changes (V0 still fetches no weather). This checkpoint is implemented + bounded
development-live-validated. Offline checks passed; the Tokyo smoke exercised the shared date
contract, and V1 and the separately authorized normal V2 run each obtained all five requested
weather fields for all ten trip dates with matching planner projection. The initial degraded
V2 attempt remains a separate historical result. See the
[Tokyo execution record](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/a6aff13a00af35467b9c88ec2906d10a96095f04/docs/development_record.md) and
[Profile closeout](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/a6aff13a00af35467b9c88ec2906d10a96095f04/docs/development_record.md).

This evidence does not guarantee future weather completeness, resolve itinerary-quality issues,
or constitute formal evaluation or re-freeze. Future V3 inherits this shared capability without
treating it as its contribution. V3 runtime and repair budget enforcement remain unimplemented.
No database reproduction/export work is included.

## Step 1 execution contract (2026-09-22)

Only the pure offline validator/report was implemented. CONFIRMED marked supported
conflicts; NEEDS_REVIEW marked optional observations; UNKNOWN retained unsupported facts.
Named-identity PASS was narrow. Coverage/repetition were review findings, route applicability
was UNKNOWN without per-leg bindings, and whole-budget/access claims remained unsupported.
Opening used scoped resolver evidence and could not certify admission or regular hours.

The accepted future path was snapshot, bounded preparation, one model proposal, application
acceptance/revalidation and one final Nearby stage. Repair, new-identity ledgers and route
rechecks were Proposed at this stage. Planned safeguards included no authorization expansion,
no role/count evasion, no CONFIRMED-to-UNKNOWN improvement and source-protected identity.
These intentions were implemented in subsequent independently approved stages.

### Future development ceilings (not active configuration)

| Resource | Ceiling |
| --- | --- |
| Repair rounds / Repair LLM calls | 1 / 1 |
| New Google discovery sends | 2, including at most 1 fallback |
| New RAG query / retrieval / Top-K | 1 / 1 / 10 |
| Query embedding | At most 1 batch, only when needed |
| New canonical processing attempts / Details sends | 8 / 8; failures count |
| Distinct Repair input candidates | 28 total, not 28 additional; original K20 plus at most 8 alternatives |
| New Reviews/Profile / Official Web | 0 / 0 |
| Additional Routes | 4 requests and 32 billable elements total, shared before and after Repair |
| Retries | 0 |
| Repair input engineering ceiling | 64,000 tokens, including system/user/schema and 2,048 framing reserve |
| Repair output ceiling | 16,384 tokens, matching current primary output protection |
| Single Repair model timeout | 90 seconds, further clamped by remaining phase/request time |
| Entire repair phase | 180 seconds |
| Weather / Nearby | Reuse Weather; once-only final Nearby stage with existing independent budget |

28 is a projection cap, not a supply enlargement or permission to acquire 28 places.
64k is a conservative development guard below the current primary 160k ceiling, not
a measured provider context limit or proof every repair fits. Bound each projected
candidate/evidence field, select only affected-day and protected-context dependencies,
and include only needed directional route pairs. Never serialize the full comparison
pool/matrix. If a faithful bounded projection cannot fit, skip Repair with an explicit
resource outcome; do not silently truncate constraints or evidence. These budgets do
not promise complete recovery of a severely under-filled ten-day draft.

The 180-second monotonic phase starts immediately after validated V2 draft/evidence
snapshot, before V3 findings and candidate preparation; it ends after acceptance and
re-validation, including any post-Repair Routes. It is nested within the existing
whole-request deadline and never extends it. Reserve the current Nearby stage's up to
10 seconds when computing the repair deadline: min(phase start + 180s, request deadline
- Nearby reserve). Exhausted time means skip/stop repair, not a fresh 180s allocation.
Nearby is still bounded by remaining request time and its own three-request/10-second
budget. A 600-second request remains explicit development-only authorization.
Propagate cancellation normally; never catch it as ordinary repair failure and continue
to tools/Nearby. A model timeout must not consume time reserved for required rechecks;
future integration must reserve/recompute that time before dispatch.

### Step 1 verification

The final affected regression passed 154 tests, including 55 V3 tests, in 5.66 seconds.
An initial 48-pass/one-failure test incorrectly expected mixed within-day timezones
to reach V3; existing shared sorting raised TypeError and was not bypassed.
Network/HTTP/model/embedding/DB guards exercised immutable itinerary/order/cost
projections, provenance, narrow identity PASS, unsupported routes and cancellation.
Ruff/diff passed; no full suite was repeated for the isolated additions.

The Step 1 measurement used
the actual primary prompt/DTO serializer and cached offline o200k tokenizer on synthetic
3-day/K12 and 10-day/K20 fixtures. This is a shared serialization reference only: the
Repair DTO, prompt and serializer did not yet exist, so final Repair payload acceptance
was **not established**. The real bounded projection was measured separately in the
standalone Repair checkpoint below.

| Synthetic primary fixture | System | User | DTO schema | Framing | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 days / K12 / 80 preference characters | 1,180 | 39,317 | 792 | 2,048 | 43,337 |
| 10 days / K20 / 80 preference characters | 1,180 | 102,110 | 792 | 2,048 | 106,130 |
| 10 days / K20 / 24,000 preference characters | 1,180 | 127,968 | 792 | 2,048 | 131,988 |

All fit the current 160k primary ceiling; the latter two exceed the proposed 64k Repair
ceiling. This supports bounded projection rather than copying the primary payload.
These are fabricated development fixtures, not live captures or worst-case proofs.
Reproduce without credentials/captures by loading `config/runtime.yaml`, calling
`tools.diagnostics.itinerary_payload.fixtures(days, K, long_text)` for `(3,12,False)`,
`(10,20,False)`, `(10,20,True)`, then `measure(ITINERARY_GENERATION_SYSTEM_PROMPT, prompt,
config.main_generation, metadata)` outside pytest (whose tokenizer fixture is mocked).
The real offline tokenizer fails rather than fetching a missing vocabulary.

Only the validator/report was implemented at Step 1. Repair/integration and formal
evaluation remained subsequent scopes; primary serialization did not validate Repair.

## Step 2 standalone repair checkpoint

Standalone Repair was implemented without graph/runner integration. The application
owned scope, original/allowed/scheduled identity ledgers, candidate qualification and
patch acceptance. Models proposed bounded edits and dispositions; unsupported or malformed
results were rejected. Unused qualified supply preceded bounded new acquisition. Explicit
visit/route bindings replaced Step 1's whole-venue-only limitation; no unverified access or
whole-budget PASS was introduced. Current interfaces are in
[the V3 contract](../../0005-validation-repair%28v3%29.md).

### Actual Repair payload sizing

Reproduce with `.venv/Scripts/python.exe -m tools.diagnostics.repair_payload`. This uses the
actual Repair system/user serializer and actual output DTO JSON schema with the cached real
offline o200k tokenizer, outside pytest's mocked tokenizer fixture. It creates no clients.

| Synthetic fixture | System | User | Schema | Framing | Total | Outcome |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 day / 3 candidates | 133 | 1,185 | 322 | 2,048 | 3,688 | Fits |
| 10 days / 28 candidates, minimal evidence | 133 | 8,314 | 322 | 2,048 | 10,817 | Fits |
| 10 days / 28 candidates, adversarial long fields | 133 | 115,642 | 322 | 2,048 | 118,145 | Rejected before model |
| 10 days / 28 candidates, 24 requirements and conflicting hours | 133 | 74,202 | 322 | 2,048 | 76,705 | Rejected before model |

The 50-edit synthetic DTO output serializes to 2,956 tokens. This is an output-size example,
not a completion guarantee within 16,384 tokens. Candidate objects are bounded to 12,000
serialized characters; excess fields/evidence/requirements are never silently truncated.
Only affected-date directed adjacency elements are projected, even if given a full matrix.
Complex valid evidence can exceed 64k; current behavior is an explicit skip retaining the
draft, not raising the limit or discarding evidence. These fixtures do not establish a
universal sufficient budget or live model/provider compatibility. The earlier primary
payload measurements remain a separate historical reference, not Repair acceptance.

### Standalone validation

The affected standalone gate passed 165 tests in 4.88 seconds. Windows loop
socketpair initialization had to precede strict external-network guards; no provider
request was needed. The final 104-test V3 slice added unbound-leg UNKNOWN and matrix
projection coverage. All four sizing outcomes above were preserved, including overflow.
Scope, deadlines, accounting, cancellation, mock acquisition and post-patch routes
were validated; graph/runner/resource/final-Nearby wiring remained unimplemented.

## Step 3: independent offline integration checkpoint

The separate V3 graph/runner integrated post-primary assessment, scope, Repair and
finalization. V0-V2 retained independent behavior. Draft/report/proposal/adopted state
remained separate; accepted improvements survived later failed proposals. Request resources
and budgets were shared, with once-only final Nearby. This was offline integration, without
live execution or a version freeze.

### Integration validation

Integration corrected caller-facing cancellation after LangGraph wrapped
`CancelledError`, while retaining optional Nearby failure. The broad affected
V0–V3/provider/service/Product set passed 290 tests in 6.91 seconds before the
ownership correction; the final wiring/lifecycle/policy suite passed 43 in 4.27 seconds
with strict network guards and resource/Nearby checks. The broader gate was not rerun
after that correction. Real serializer measurements stayed separate from mocked
tokenizer control-flow checks.
Complete access, cost and all-mode evidence remained unavailable.

## Targeted addition candidate revision (2026-09-22)

Candidate preparation was narrowed to active sourced gaps, qualified original/comparison
pool reuse and bounded new discovery. Real candidate opportunities and successful acceptance
were kept separate; stale/failed candidates could not acquire whitelist authority. This
offline revision did not establish the cause or resolution of the historical seven-day
REJECTED run. The three-day run had not exercised Repair; both captures remained unchanged.

### Candidate revision validation

Verification corrected comparison against a missing baseline while preserving
strict intent/date admission. The final affected diagnostics/date/trace gate passed
198 tests; pending-Details/discovery reservation passed 67, operation wiring 32,
and the final wiring/trace subset 32. These overlap and used mocked boundaries.
No full suite or new live observation resolved the original seven-day rejection.

### Actual Repair sizing

Measured with the revised DTO, prompt, strict patch schema, serializer and local checksum-checked
o200k tokenizer. Every case has system=164, schema=322 and framing=2048 tokens. Component counts
below tokenize separate JSON projections; they need not add exactly to the user message count.
These are engineering measurements, not provider usage or a model completion guarantee.

| Synthetic case | Identity union | Options | Context | Candidates | Evidence | Requirements/findings | User | Total | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Retime only | 2 | 0 | 264 | 10 | 9 | 484 | 771 | 3305 | fits |
| One addition date | 28 | 27 | 133 | 5816 | 9 | 468 | 6430 | 8964 | fits |
| Three addition dates | 28 | 25 | 307 | 8786 | 9 | 803 | 9909 | 12443 | fits |
| Ten-day other operations | 28 | 28 | 2257 | 5891 | 9 | 2135 | 10296 | 12830 | fits |
| Long text | 28 | 28 | 46977 | 68499 | 9 | 2135 | 117624 | 120158 | rejected |
| 24 requirements/conflicting hours | 28 | 28 | 2257 | 5891 | 63234 | 4798 | 76184 | 78718 | rejected |

The 50-edit synthetic patch is 2956 tokens. Neither pressure case was made to fit by deleting
protected information or enlarging ceilings. Primary-generation sizing is not Repair acceptance.

This revision needs separately authorized live observation. It does not prove that the historical
seven-day proposal would now be accepted or that a future accepted addition improves overall
quality or satisfies the user's relaxed intent. No commit, push, freeze or next stage is implied.

## Bounded feedback rounds and spatial policy (2026-09-22)

Bounded multiround feedback replaced the earlier single-call development limit. Rounds
continued only for material remaining opportunities under one stage ledger/deadline. Spatial
checks used real anchors and route context rather than model proximity claims. This was
offline validation; it did not turn the old seven-day rejection into an accepted repair.

### Multiround validation

The final V3/config and V0–V2 runner gate passed 249 tests in 8.31 seconds.
Later targeted deadline/CLI/usage checks passed 35, five and three respectively;
confirmed-route protection passed 103 plus one directed-chain regression.
They cover actual graph feedback, a single Nearby stage, UNKNOWN additions,
two-sided detour, cumulative burden, protection, cancellation and YAML propagation.
Scopes overlap, use synthetic boundaries and are not summed or live evidence.

### Actual Repair serializer sizing

Uses the modified DTO, system prompt, strict schema, serializer, compact feedback helper,
coordinate candidate-pair projection and offline o200k tokenizer. Synthetic fixtures are sizing
inputs, not model executions or empirical evidence that the limits suffice. Second/third-round
fixtures represent only the latest feedback, not concatenated history. An initial sizing run
used the same feedback specimen for both later labels; the final third-round specimen uses a
distinct partial-acceptance feedback envelope. No limit was enlarged to pass a stress sample.

System = 232, schema = 322, framing = 2048 tokens in every row below. Component counts are
independently serialized measurements and need not add exactly to the combined user payload.

| Fixture | ID union / candidates | Context | Candidates | Evidence/spatial/feedback | Requirements/findings | User | Total | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Retime only | 2 / 0 | 318 | 10 | 93 | 484 | 918 | 3520 | Fits |
| Single-date addition | 28 / 27 | 171 | 5816 | 13432 | 468 | 19900 | 22502 | Fits |
| Three-target addition | 28 / 25 | 377 | 8786 | 15694 | 803 | 25673 | 28275 | Fits |
| Ten-day other operations | 28 / 28 | 2599 | 5891 | 1158 | 2135 | 11796 | 14398 | Fits |
| Long text | 28 / 28 | 47319 | 68499 | 1158 | 2135 | 119124 | 121726 | Rejected |
| 24 requirements/conflicting hours | 28 / 28 | 2599 | 5891 | 64383 | 4798 | 77684 | 80286 | Rejected |
| Round 2 compact feedback | 28 / 25 | 377 | 8786 | 15799 | 803 | 25778 | 28380 | Fits |
| Round 3 compact feedback | 28 / 25 | 377 | 8786 | 15800 | 803 | 25779 | 28381 | Fits |

The synthetic 50-edit output measured 2956 tokens against 16384. This is not a completion
length guarantee. Input overflow preserves the latest adoption; necessary protection and
facts are not deleted to force a pass. Full public-access semantics, complete costs, all-mode
routing, global route optimization and empirical multi-round success remain unsupported or
unvalidated. Any new live run requires separate authorization; no automatic rerun is scheduled.

## A elastic time and real adjacency checkpoint (2026-09-24)

A introduced application-owned elastic free-time scheduling and actual directed adjacency
views. Explicit fixed commitments stayed protected; generic unknown-location activities were
not fictitious endpoints. Linked elastic roots/fragments were applied atomically. Shared
schedule adaptation was distinguished from V3's mechanism. B/C remained approved directions
rather than implemented capabilities at this checkpoint.

### Historical fixture evidence and limitations

`backend/tests/fixtures/v3/historical_free_time.json` extracts the draft, three parsed patches and
relevant Places from the recorded result, with run ID and source SHA-256. The tests explicitly add
**synthetic** `time_protections=[]`; the historical run did not observe that new assessment.
Recorded route matrices are not included, so this is a minimal regression, not an exact live
replay or evidence that the same provider response would occur today.

| Historical patch | Offline result under the explicit synthetic context |
| --- | --- |
| 1 | Rejected: insufficient unoccupied transfer window (30-minute gap versus existing 45-minute no-route reserve). No successful fully adjusted proposal is claimed. |
| 2 | Rejected after atomic placeholder adjustment and revalidation: `no_route_fallback_distance`. No confirmed free-time overlap in the adjusted proposal. |
| 3 | Rejected after atomic placeholder adjustment and revalidation: `no_route_fallback_distance`. No confirmed free-time overlap in the adjusted proposal. |

The elastic-placeholder endpoint obstruction is removed; the remaining spatial/time rejections
are retained. No historical patch, input, evidence or log was rewritten to make it pass.

### Elastic scheduling validation

Validation corrected missing accepted-window audit aggregation. Final affected
A/Repair/time-protection scopes passed 164, 78 and 90 tests separately, with fixture
provenance checked. Historical route matrices were unavailable; the three retained
patch rejections are minimal synthetic regressions rather than exact live replay.

### Actual serializer sizing

The real Repair DTO, schema, prompt, serializer and installed offline o200k tokenizer were used.
Each row includes system 263, schema 322 and framing 2048 tokens. Component columns are separately
serialized and need not add exactly to combined user tokens. All A samples use the 28-identity
union; later samples use an actual application split and only compact previous-round feedback.

| A fixture | Context | Candidates | Evidence/spatial/feedback | Requirements/findings | User | Total |
| --- | --- | --- | --- | --- | --- | --- |
| Fixed time and elastic window | 600 | 5816 | 13432 | 532 | 20393 | 23026 |
| Later residual split | 875 | 5601 | 12549 | 526 | 19564 | 22197 |
| Later multi-target, 24 soft requirements | 1855 | 8435 | 14551 | 3526 | 28380 | 31013 |

Other totals: retime 3574; single-date 22556; three-target 28329; ten-day operations 14452;
round-2 feedback 28434; round-3 feedback 28435. Long text 121780 and conflicting-hours/24-requirement
stress 80340 both raise `repair_input_overflow`. No protection was truncated and no limit raised.
The synthetic 50-edit output is 2956 tokens versus 16384; this is not a completion guarantee.

### Deferred B/C and live boundary

Deduplication/overfull review switches (approved default off), adjacent-date moves with explicit
source/target activity permissions, associated targets, REQUIRED-copy protection, opening/route
target expansion and visit/access semantics remain B/C. The approved configurable 09:00-18:00
blank/missing-day default is not implemented here; existing activity days are not clipped to it.
Quantity review stays default off. This A checkpoint adds no new live evidence, benchmark result
or quality guarantee. Further implementation and live execution require separate authorization.

## B target and operation checkpoint (2026-09-24)

B implemented source-linked count/date/coverage/repetition targets and bounded operations.
Satisfaction and authorization stayed separate; hard requirements and conditional compensation
constrained deletion/addition. Shared source/role adaptations applied across versions rather
than becoming V3-only gains. Opening/route-conflict targets and access-mode semantics were
not yet implemented. Historical Tokyo rejected patches retained their original outcome.

### Configuration and capacity

See `config/runtime.yaml` and `config/README.md`: new independent review flags false/false,
`daily_main_min=2`, `daily_main_max=5`, `move_max_days=1` (0 disables), blank local hours 9..18.
New review flags are YAML-only; existing quantity CLI override behavior is unchanged. Values load
once into the effective runtime snapshot with type/range/relationship validation.

All targets share the existing three rounds/calls, 300-second phase, at most 70 seconds/model,
64k input, 16384 output, 28 input-identity union and unchanged tool totals. New child targets do
not replenish them. No required context is truncated to force a fit.

### Target/operation validation

Validation exposed missing child-result aggregation; correcting it preserved
scoped permissions, revisit protection, unassessed context and partial completion
when unrelated overlaps remained. A 28-way overlap fixture exceeded the real input
ceiling; narrowing that capacity-only test did not enlarge production limits.
Final V3/time/visit validation passed 272 tests, with 220 shared interpreter/provider/
V0–V2/config checks separately. Service/graph checks covered compensation, REQUIRED
satisfaction, dates/rest, adjacent moves, prohibited chains and prior adoption.
C remained unimplemented at this checkpoint.

### Actual Repair serializer sizing

Measured using the real `repair_input_2` payload, prompt, strict patch schema and offline o200k
serializer/tokenizer. System 330, schema 325 and framing reserve 2048 tokens are included in totals.
Component columns are independently tokenized diagnostics; JSON composition adds its own framing.

| Input | Context | Candidates | Evidence | Requirements/findings | User | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dedup + conditional compensation, union 28 | 1227 | 21045 | 13649 | 580 | 36511 | 39214 |
| Adjacent two-day move, union 28 | 2005 | 6411 | 7345 | 566 | 16337 | 19040 |
| Missing date, union 28 | 508 | 5965 | 12475 | 565 | 19523 | 22226 |
| Later adopted compensation + child audit + remaining target, union 28 | 1771 | 7249 | 10649 | 573 | 20252 | 22955 |
| A residual split / later round | 1091 | 5601 | 12555 | 532 | 19792 | 22495 |
| Long time/requirements context | 2433 | 8435 | 14557 | 3532 | 28970 | 31673 |

Other passing totals: retime 3700; single addition 22664; three-target addition 28437; ten-day
operations 14740; elastic/fixed 23324; prior round-2/3 feedback 28542/28543. Long text 122068 and
conflicting-hours evidence 80628 reject with `repair_input_overflow`. Synthetic 50-edit output is
2956 tokens, not a completion guarantee. These are synthetic serializer measurements, not live
model usage, evidence that all 28-identity inputs fit, or proof of real-world repair quality.

### Remaining limits and stop boundary

C remains deferred: no automatic opening/route-conflict repair target expansion, access-mode
adaptation, complete public access/cost checking or different-ID experience deduplication.
Missing reliable timezone or unassessed relevant obligations can prevent blank/destructive scope;
UNKNOWN facts are not upgraded. Discovery opportunity is bounded and may not serve every target.
Real route/spatial policy may still reject validly authorized edits, including historical proposals.
No new live or formal evaluation is authorized by this checkpoint. B does not establish that the
historical seven-day rejection's complete cause has been solved.

## C operating and transfer checkpoint (2026-09-24)

C added supported operating-hour/transfer conflicts, automatic permissions and comparison
under the existing stage priority. Explicit visit bindings and applicable directed routes
constrained acceptance; access/admission and whole-budget facts remained unsupported.
Source provenance was preserved in shared output. This offline checkpoint did not establish
that the old Tokyo seven-day rejection was solved.

### Operating/transfer validation

Graph verification retained `explicit_motor_mode_requires_route_evidence` for a
TRANSIT replacement without route facts. The business-magnitude filter was aligned
with the date-specific evidence used for confirmation, avoiding a contradictory
general baseline; 81 targeted tests and a negative baseline case passed.
Final V3/shared checks passed 298 tests, with 220 V0–V2/interpreter/config tests
separately. Routes, exterior entry, closure provenance, rollback and automatic scope
used fixtures, not newly acquired facts.

### Actual serializer sizing

Real DTO/prompt/schema/serializer and offline o200k; system 377, schema 325, framing 2048 tokens.
Component columns are diagnostic independent tokenizations; total includes the complete JSON.

| Sample | Context | Candidates | Evidence | Requirements/findings | User | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Opening retime, two context identities | 795 | 10 | 665 | 566 | 2046 | 4796 |
| Timed route reorder/options, union 28 | 916 | 14744 | 13196 | 562 | 29428 | 32178 |
| Opening replacement/compensation and adjacent move scope, union 28 | 886 | 14744 | 13041 | 566 | 29247 | 31997 |
| C scope plus later-round compact feedback, union 28 | 886 | 14744 | 13146 | 566 | 29352 | 32102 |

These are input scenarios and capacity checks, not successful model completions. Long-text input
122127 and conflicting-evidence input 80687 reject above 64000, without dropping protection data.
Synthetic 50-edit output is 2956 tokens versus the unchanged 16384 ceiling. The later-round sizing
uses compact synthetic feedback, not a replay or estimate of live model usage.

### Live boundary

Real interpreter access-mode extraction, provider date-specific evidence coverage, new route
acquisition and actual model C patch behavior still require separately authorized live validation.
Unbound normal visits can remain UNKNOWN/review and will not trigger C merely because their notes
mention hours. No claim is made that all required visits are executable, all UNKNOWN facts are
resolved, every confirmed conflict can be repaired within the budgets, or historical Tokyo output
is repaired. This checkpoint stops at offline implementation and validation. B/C checks retained
the historical multi-round result hash and A-fixture provenance.

## Google API evidence adoption checkpoint (2026-09-24)

At baseline `9d429cde7ef4d75442f7f63876a123cfe0a91c3b`, structured API hours and actual
transport evidence were integrated into shared adoption and V3 checks. Applicable current,
regular and official facts retained explicit provenance; missing/conflicting facts stayed
UNKNOWN. This offline change did not alter deployment, primary prompt, K, Weather, date
policy, SQL or vector artifacts.

### API adoption validation

Verification retained real route deficits, visit duration and unresolved coverage
child debt. It found duplicate `adopted_evidence` construction in route auditing;
the corrected combined affected gate passed 461 tests in 9.15 seconds after an
interrupted attempt that did not complete. A separate final 33-test slice preserved
special-day/timezone UNKNOWN rather than falling back to regular hours. No full
backend or live run is claimed for these bounded corrections.

### Actual serializer sizing

Command: `.venv/Scripts/python.exe -m tools.diagnostics.repair_payload --api-policy-comparison`.
Real DTO, prompt, schema, serializer and offline tokenizer. System 408, schema 325, framing 2048;
input 64000 and output 16384 unchanged. Component tokenizations are diagnostic, not additive totals.

| Synthetic sample | Context | Candidate groups/catalog | Evidence | Requirements/findings | User | Total | Group-only saving | New-field delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Retime | 390 | 14 | 259 | 505 | 1192 | 3973 | -4 | 168 |
| Overlapping groups, 28 identities | 936 | 7765 | 2539 | 888 | 12152 | 14933 | 2747 | 2604 |
| C route/options, 28 identities | 990 | 32453 | 15207 | 983 | 49654 | 52435 | 3283 | 2646 |
| Structured weekly periods, 28 identities | 936 | 13589 | 3947 | 888 | 19384 | 22165 | 7323 | 8520 |
| Same periods plus compact later feedback | 936 | 13589 | 3976 | 888 | 19413 | 22194 | 7323 | 8520 |
| Long-text pressure, 28 identities | 47553 | 69309 | 3603 | 2228 | 122717 | 125498 | not measured | not measured |

Group-only saving compares identical candidate content/permissions using inline groups versus a
catalog; it does not include removal of the legacy hours alias. New-field delta is a controlled field
ablation on the same new payload, not a reproduction of the old serializer or live usage. Retime pays
four tokens for the empty catalog. Richer evidence costs tokens; no claim of universally smaller inputs.
Pressure fails closed above 64000, without deleting protection or enlarging limits. Earlier and final
comparison runs were consistent; C route coverage was added to the final comparison set.

### Limitations and next boundary

No new live evidence exists for this policy. Source data can be missing, conflicting or invalid;
explicit sub-area/exterior access, reservation completion, tickets and complete costs remain limited.
Traffic-sensitive routes retain strict applicability. No ability guarantees completion within three
rounds. The historical ABC deduplication improvement remains its original result; new API-based
validation coverage is not another itinerary repair, nor proof that all twelve historical opening
checks or seven legs now pass. Further implementation changes or live runs require separate approval.

## Material feedback checkpoint (2026-09-24)

Feedback preparation was corrected to expose material authorized progress/opportunities,
not cosmetic output or an unchanged round number. Rejected proposals did not erase accepted
state; terminal contract failures remained failures. Historical fixture evidence below is
separate from a fresh model run. Shared interpretation, V0-V2, Google policy and primary
generation were unchanged.

### Historical fixture and offline evidence

`backend/tests/fixtures/v3/tokyo_api_feedback.json` records source run ID and result SHA-256.
Original draft, contract, scope, saved patches, Details and selected route facts are extracted without
rewriting historical logs. Route envelopes are reconstructed from saved selected-route facts.
The complete candidate-anchor matrix was not retained in the CLI result. Tests explicitly supply
synthetic candidate-route support to reproduce the observed five-option context; this is not historical
Google evidence. Saved Odaiba Details and its actual acquired route are injected as available evidence,
not replayed network calls. A separate novel-candidate branch uses explicitly synthetic Details.

The real stage accepts the historical Odaiba patch, retains it after the second empty patch, and
skips the third model call when preparation produces no material change. With a synthetic pending
candidate, the third actual projection changes; its empty result still preserves the first adoption.
Neither branch claims the real model would now complete the trip. Other tests exercise rotation
without search, bounded discovery with acceptance, empty query/capacity/deadline stops, identity
matching, UNKNOWN qualification, fixed windows, one-second potential ranges, route-policy scope,
attributable atomic failures, new times without search, multi-date allocation and actual graph/Nearby
closure. No live API is used.

### Material-feedback validation

Verification preserved unchanged-input, empty-proposal and skipped-versus-attempted
round distinctions. Historical extraction used transparently synthetic missing routes,
so it did not certify the original live outcome. The broader affected gate passed
336 tests; final opportunity/A/B checks passed 137 after the acquisition guard stopped
work on dates without an authorized insertion window. Application-only audit metadata
remained outside business comparisons, without deleting protected model context.

### Serializer sizing and boundaries

Actual prompt, DTO, strict schema, serializer and offline tokenizer were used. Initial measurement
included internal opportunity signatures/default unassessed fields in every authorization reference;
that increased two dense samples to 65961 and 67260 tokens. These internal audit fields are now kept
out of model input. Actual opportunity state/windows, protected context, evidence and authorization
remain intact. This is not truncation of facts and no ceiling was raised.

Final representative engineering totals:

| Sample | Total input tokens | Result |
|---|---:|---|
| Three-target actual preparation, 28-identity union | 37778 | Within 64000 |
| Same preparation with no-op feedback | 37894 | Within 64000 |
| Specific new time constraint, 28 identities | 38067 | Within 64000 |
| Dense C route/reorder fixture, 28 identities | 59255 | Within 64000 |
| Dense B dedup/compensation fixture, 28 identities | 60759 | Within 64000 |
| Long-text pressure | 125987 | repair_input_overflow |
| Tokyo control fixture round 1 / round 2 / skipped preparation | 21325 / 17715 / 17580 | Within 64000 |

These are offline engineering sizes, not provider usage or measurements of the historical live input.
System/schema/framing contribute 436/325/2048 tokens. Synthetic 50-edit output is 2956 tokens,
not proof that real completions fit the 16384 output allowance. Dense inputs remain close to the
ceiling; other stress samples also reject. Overflow retains the latest adopted draft. Sizing records
are under artifacts/v3_material_feedback_sizing*.json and v3_tokyo_feedback_offline_sizing*.json.
Earlier measurements are retained, including pre-compaction-of-audit-fields results.

### Remaining limits

Opportunity preparation is intentionally incomplete: exact visit duration, variable-departure transit,
complex insertion chains and unclear requirements still require proposal construction/re-validation
or remain unresolved. No prefilter guarantees an arrangement. Presentation rotation does not prove
preference suitability, and empty patches still do not explain the model's unrecorded reasoning.
Live effectiveness of changed third-round inputs remains untested. The previous seven-day failure's
complete root cause is not claimed solved. All historical artifacts, .gitignore and local thesis notes
remain untouched; no automatic next stage or live is authorized.

## Capacity calibration checkpoint (2026-09-25)

Status before the authorized Honolulu smoke: implemented + offline-validated;
resource limits are an engineering freeze candidate, not a version freeze.
Google total 5 includes a derived ordinary cap of google minus fallback (4),
reserving 1 fallback send. Stage canonical 12, Details 10, Routes requests 6
and elements 32 remain shared across rounds. Per-call union 32/input 72000
are preventive headroom. Output 16384, activity/text limits, three rounds,
300/70/600-second stage/model/request ceilings and all spatial/evidence policies
remain unchanged. No automatic future expansion is authorized.

RepairBudget checks application limits before adapter entry and again at send.
Explicit Google total/discovery/fallback, Details and Routes request/element
reasons are separate from provider_pre_send_error. Canonical exhaustion has
its own stop. Request success/failure/cache state is not reset. Compact
acquisition_audit rows save round, purpose, hashed request key, ordinary target
date/intent, sent flag, outcome, budget snapshots and raw hits where available.
Candidate preparation retains separate duplicate/identity decisions; audit is
not added to model input. Old pending Details reserve both attempt and send
capacity for exploration under the changed 12/10 ratio. No shared cache/client
behavior or V0-V2 mechanism changed.

Offline capacity migration exposed a real reservation gap: pending Details needed
both canonical-attempt and send headroom. After that correction, the shared V3/runtime/
opening/Google gate passed 372 tests. Four additional budget/control tests verified
that later overflow preserves adoption and canonical totals span rounds. These mocked
checks preceded the separately authorized live below.

Actual DTO/prompt/schema/serializer/offline tokenizer sizing: 32-identity dense
route 69567; dense dedup/compensation 71965; material opportunities 46114; no-op
feedback 46230; specific-time next-round constraints 46403. The dense sample
has only 35 tokens of engineering headroom: fitting one fixture is not a
guarantee for other inputs. Conflicting long evidence 96295 and 32-identity
long text 137547 are explicitly rejected. Historical-size 28-identity pressure
is retained separately. No protection text was removed or ceiling increased
to accept stress. artifacts/v3_capacity_calibration_sizing_final.json contains
component counts and additional A/B/C/time-window samples. Latest Tokyo live
used 19 identities/26454 tokens; it did not prove the old input limit inadequate.

Historical runs and their original policies remain unchanged. The prior
ProviderNotSentError is not retroactively relabeled as a proven budget error.

Historical-size 28-ID long-text pressure measured 125987 and was rejected.
Offline acceptance made no actual provider calls.

### Honolulu execution admission

Automatic approval blocked two submissions before process creation; no provider
failure or charge occurred. Explicit later chat confirmation admitted the single
execution below. The preparation alone was offline-validated and had no run ID.

### Honolulu capacity smoke (2026-09-25 local; explicit chat confirmation)

Following the documented pre-execution approval blocks, the user explicitly
confirmed execution in chat. Exactly one process ran: a84b4286-8e9b-4665-a9fd-14e7179e29bc,
exit 0, trace span 119.131 seconds. Runtime/config/source hashes are in
logs/v3_honolulu_9day_capacity_smoke_20260927/. The fixed request and gpt-6-luna
deployment were unchanged. No implementation edits or second live followed.

Initial and final primary are identical: 14 visits/13 distinct identities,
five coverage review dates (one with zero main visits), one repeated identity,
two confirmed WALK transfer deficits. Opening 13 PASS (8 current, 5 regular),
1 UNKNOWN; routes 4 PASS, 2 CONFIRMED; visitor suitability 14 UNKNOWN, budget
and open semantics one UNKNOWN each. Both route targets were prioritized over
six deferred review targets. No operating conflict was observed.

Round 1 preparation reached identity union 32 and 30 operation candidates with
202 authorization associations. Actual serializer counted 154653 engineering
tokens (candidate component 85204, evidence 58868, context 5339, requirements/
findings 2398; component counts are diagnostic, not additive partitions).
The 72000 guard skipped before the Repair model. No patch, proposal, comparison,
fingerprint or presentation history was constructed; no multi-round recovery
was exercised. The latest draft and reports were preserved. This is a safe
bounded overflow, not successful repair or an invalid user request.

Repair used ordinary Google 1/4 (total 1/5), fallback 0/1, canonical 10/12,
Details 10/10, Routes 0/6 and 0/32 elements, retrieval/embedding 0. Explicit
stop details_budget_exhausted was recorded, not ProviderNotSentError. There
was no needless attempt to spend the remaining Google quota. However targeted
scope correctness needs attention before engineering closeout:
- Route findings have empty dates. candidate_targets maps them to every scope
  add date; active September 27/October 3 route obligations acquired associations
  on unrelated sparse dates. Actual Google discovery targeted October 1 despite
  its review target being deferred. The local scope expansion is evidenced by
  the saved audit and code; its exact contribution to total overflow is not isolated.
- Per-target opportunity counts do not filter add versus replace, and repeat a
  global independent identity capacity. These rows cannot be read as distinct
  per-operation/date supply counts. This is an audit correctness limitation.

No automatic threshold increase or fix occurred in this run. Its scope/accounting
findings prevented engineering closeout; the subsequent locality/capacity follow-up
provided offline corrections without replacing the failed live outcome. No evidence
established that 72k should be increased to accommodate this payload.

RAG initialized and closed once, four queries/80 positions, 16 resolution
attempts, 12 Details, 4 fallback sends, partial bounded status; 12 new canonical
and 6 mixed-source IDs. Embedding usage 17 tokens. Primary baseline Routes used
6 requests/324 elements plus 3 alternative calls. HTTP logs show 2 model calls,
10 searchText, 54 Details, 1 embedding, 1 Weather, 9 Routes and 3 Nearby calls.
Official Web had zero tasks. Callback usage 132298 input +8040 output =140338;
Repair model usage is zero. Primary engineering input 129829/160000. Repair
preparation/skip snapshot used approximately 17.97 seconds, not the 300s cap.

Nearby ran once after final-primary with three requests and three references:
Pavilion Cafe, Ku's Canoe, Bites & Bev Snack Shop. Primary activities were equal
before/after Nearby. Request-owned RAG closed=true; no invented per-client close
records. Full application result (~10 MB), round audit, initial/final itineraries,
reports and integrity checks were separately saved; truncated trace summaries
are not the sole evidence. Source hashes were unchanged during the live.

### Explicit Details allowance update (2026-09-25)

Following separate user authorization, ordinary primary Details is now 60,
initial RAG Details 30, and Repair stage Details 30. YAML remains authoritative.
The quality_first_1 adapter now uses the configured primary send allowance
instead of r_pool + 8; its new-success goal remains unchanged (32 for seven/nine
days). This shared change applies to V1/V2/V3, not V0. RAG resolution remains
16 entities; Repair canonical attempts remain 12, so neither larger send budget
is a promise to acquire 30 distinct candidates. All time, input, review, search,
route and acceptance limits remain unchanged. Honolulu used the previous limits;
no live was executed for this update. Offline checks passed 135 related cases and two policy-adapter configuration cases.
This update
does not fix the documented target-scope or payload-overflow issues.

## Active-target locality and capacity follow-up (2026-09-25)

Preparation was restricted to currently active target locality and source-linked identity
opportunities, with shared stage counters/deadlines. The Honolulu saved-material reconstruction
below diagnoses observed scope/capacity; it does not constitute a new live run. Honolulu's
historical Repair remained skipped with two route conflicts.

### Honolulu saved-material reconstruction and attribution

Read-only source: run `a84b4286-8e9b-4665-a9fd-14e7179e29bc`,
`logs/v3_honolulu_9day_capacity_smoke_20260927/result.json`, SHA-256
`bd636bc6e898a2ce9b4f693119f9d8216479cfa24e36cf3ebb201f5b1c6dba4b`.
The compact regression fixture retains draft/contract/scope/schedule, saved ledger
and six selected historical route elements. The original full matrix was not saved
in this artifact. No replacement routes or operating facts are synthesized. The
post-acquisition ledger is reused, so this is not a replay of historical acquisition.

| Measurement | Historical live | Old scope, saved routes | Scope-only ablation | Actual new preparation |
| --- | ---: | ---: | ---: | ---: |
| Active / deferred targets | 2 / 6 | 2 / 6 | 2 / 6 | 2 / 6 |
| Input identity union | 32 | 32 | 28 | 32 |
| Operation candidate IDs | 30 | 30 | 26 | 30 |
| ADD associations | 156 | 156 | 19 | 22 |
| REPLACE associations | 46 | 46 | 46 | 51 |
| Candidate tokens | 85204 | 85204 | 45488 | 53306 |
| Evidence tokens | 58868 | 23454 | 13277 | 15335 |
| Engineering total | 154653 | 119239 | 68635 | 78511 |

Scope-only ablation filters the same saved authorizations to current legal
operations/dates and recomputes their spatial projection, without new facts or
acquisition. Its reduction is 50604 tokens under identical retained route evidence.
The missing historical matrix accounts for another 35414 tokens in the old-scope
reconstruction; that difference cannot be claimed as a locality improvement. The
new preparation legitimately fills freed optional positions using saved material.
Thus the complete historical 154653-to-78511 delta is not a controlled causal
measurement. New input has 41489 tokens of engineering headroom, not a guarantee
for all requests. The union already reaches 32, so identity capacity is the earlier
bound for additional identities in this fixture.

New input has 14 ADD identities and 30 REPLACE identities (overlapping groups, not
44 independent resources), 73 selected authorization edges, and global matching
capacity 12 against preparation reference 12. The eligible pool has 41 unique IDs
and 94 edges; pool capacity is not the number sent to the model. Its per-operation
pool UNRESOLVED counts are ADD 9/13 and REPLACE 32/40 for the two respective dates;
selected REPLACE counts are 22/29. UNKNOWN remains selectable. The real stage with
mock empty patches can rotate existing candidates for a materially different
second input, then stops on duplicate failed patch, preserving the original draft.
The fixture is not evidence of successful route repair or real model behavior.

### Actual serializer sizing

Commands: `python -B -m tools.diagnostics.repair_payload` and the same command
with `--locality`. Actual DTO, system prompt, strict schema, JSON serializer and
offline o200k tokenizer are used. Every row has system 436, schema 325 and framing
2048 tokens; total is user + 2809. Output remains capped at 16384; synthetic
50-edit output is 2956 tokens, not a completion guarantee.

| Sample | User | Total | Result at 120000 |
| --- | ---: | ---: | --- |
| Honolulu actual new preparation | 75702 | 78511 | Within ceiling |
| Retime only | 1197 | 4006 | Within ceiling |
| C opening retime | 2386 | 5195 | Within ceiling |
| C route reorder, 32 IDs | 54038 | 56847 | Within ceiling |
| C replacement/compensation/move | 40041 | 42850 | Within ceiling |
| B repetition/compensation, 32 IDs | 56860 | 59669 | Within ceiling |
| B adjacent move | 28050 | 30859 | Within ceiling |
| Missing date | 29076 | 31885 | Within ceiling |
| Three-target quantity, 32 IDs | 39758 | 42567 | Within ceiling |
| Round 2 feedback | 39874 | 42683 | Within ceiling |
| Round 3 / Round 4 feedback envelope | 39875 | 42684 | Within ceiling |
| Actual material preparation | 43305 | 46114 | Within ceiling |
| No-op feedback | 43421 | 46230 | Within ceiling |
| Changed time constraint | 43594 | 46403 | Within ceiling |
| Dense conflicting hours / 24 requirements | 93486 | 96295 | Within ceiling |
| Separate near-limit 548-unit text sample | 116954 | 119763 | Within ceiling |
| Separate 550-unit text sample | 117266 | 120075 | Overflow |
| Unchanged historical-size 28-ID pressure | 123178 | 125987 | Overflow |
| Unchanged longer 32-ID pressure | 134738 | 137547 | Overflow |

The near-limit pair is separately constructed synthetic text, not truncation of a
rejected historical input. Original 126k/138k samples remain intact. Round-feedback
sizing measures compact envelope capacity; it does not assert that identical
feedback permits another model call. Actual four-round service tests separately
verify material inputs, partial adoption and unchanged shared accounting.

### Locality/capacity validation

Two initial minimal real-validator tests failed on trip-wide ADD leakage and retime-only
candidate acquisition; correction passed 56 locality/B/C checks. Saved-material tests
returned 2/1 because legitimate unpresented options permitted a second material input.
The first V3/config set 364/2 also required updating a synthetic stress fixture now
below120k; original pressure measurements were preserved. Focused 39 and later
Details/deadline tests corrected fixture initialization/assertions. Final affected
V3/runtime/RAG/supply/opening/provider set passed 407 with Ruff/diff clear.
The four-round fake-clock case used 160 seconds/140 remaining under one 300-second
stage, retaining earlier partial adoption after fourth-round rejection. This closes
the reproduced locality blocker offline, not Honolulu's historical repair or real-model
four-round efficacy. No test invoked actual providers.

### Authorized processing and stage-time alignment (2026-09-25)

The follow-up configuration is implemented and offline-validated: initial RAG
resolution_entities 16 -> 30, Repair canonical attempts 12 -> 30, and Repair stage
300 -> 360 seconds. YAML and typed upper-bound validation agree. Initial RAG
changes apply to V2/V3; Repair changes apply only to V3. This is capacity alignment,
not a new research mechanism or live validation.

Preparation stays 30 seconds, rounds/calls 4/4, model cap 70 seconds, explicit whole
request 600 seconds, Routes 6/32, Google 5, both RAG/Repair Details 30, identity
union 32 and input 120000. All other policies are unchanged. Four rounds share one
360-second maximum stage and acquisition state; the entry request deadline and
Nearby reservation may shorten it. First allocation with a full stage is 90
seconds; preparation reduces the model allowance below its 70-second maximum.
The old 16/12 processing caps no longer prevent reaching the 30-send allowance,
but fallback, cache reuse, input capacity, sufficiency and time can still stop work
earlier. No quota is a requirement to spend or a promise of successful candidates.

Validation sequence: 98 tests passed first (initial RAG, runtime config, Repair
capacity and multiround); targeted locality/material-feedback/graph regression
then passed 53 tests. Ruff passed. No runtime service was called. Prompt, DTO and
serializer were unchanged, so no repeated sizing was necessary. Historical live
records and earlier checkpoint numbers remain historical; no live or freeze is
claimed, and no files were staged or committed.

## Mixed transport and joint components (2026-09-25)

Per-leg mixed-mode policy and dependency-based components replaced whole-round atomic
acceptance. Same-date/dependent edits remained atomic; independent components ran against
latest accepted state, retaining earlier improvements after later rejection. Actual changed
adjacencies required applicable routes, with provider durations and application reserves
separate. Malformed JSON was not partially salvaged. This checkpoint was offline-only;
old failed/accepted proposals were not rewritten. Current details are in
[the component contract](../../0005-validation-repair%28v3%29.md#joint-repair-and-component-atomicity).

### Mixed-component validation

Early Repair/multiround sets returned 94/12,96/10,108/3; audit was corrected to distinguish
an unchanged constructed proposal from absent illegal proposal. The affected V3 set
334/15 exposed unnecessary preparation routes, while later active coverage children
legitimately acquired their own routes. Targeted mixed/C checks 36, actual graph 1,
and mixed/C/wiring 68 passed;28+10 minutes in 35 reports a180-second deficit.
The shared affected set passed 560; subsequent V3/component checks 357 and final 59
configuration/material checks passed separately. Frontend 8 tests, TypeScript/Vite build
and changed-file ESLint passed. These overlapping gates are also summarized in
[V3 closeout](v3-closeout.md), not additive full-suite evidence.

### Final actual serializer sizing

Command: `.venv/Scripts/python.exe -m tools.diagnostics.repair_payload --mixed`.
Uses the actual DTO, system/user prompts, strict output schema, serializer and offline tokenizer.
The dense synthetic fixture has3 active worksheets,32 identity union (29 operation candidates),
87 directed target options, including WALK, TRANSIT and DRIVE, with route evidence filtered
through the actual projection. No provider ports are supplied. It is deliberately dense,
not a statement that87 options or three queries per candidate will be acquired live.

| Sample | System | User | Schema | Framing | Engineering total |
| --- | ---: | ---: | ---: | ---: | ---: |
| First round | 554 | 77060 | 492 | 2048 | 80154 |
| Second-round compact feedback | 554 | 77205 | 492 | 2048 | 80299 |
| Third/fourth/fifth compact feedback | 554 | 77207 | 492 | 2048 | 80301 |
| Long protected context | 554 | 221365 | 492 | 2048 | 224459 |
| Near ceiling, protection retained | 554 | 248365 | 492 | 2048 | 251459 |
| Explicit overflow | 554 | 251365 | 492 | 2048 | 254459: rejected |
| Larger overflow | 554 | 271365 | 492 | 2048 | 274459: rejected |

First-round diagnostic views: context1107, candidate10398, evidence64688,
requirements/findings840 tokens. These JSON views are not an additive token partition.
The synthetic50-edit/50-disposition output is4162 tokens against16384. This does not prove
that every valid maximum-text completion fits; the actual output cap remains authoritative.
Later-round samples measure bounded feedback shapes, not successful live iterations. Input
ceiling breaches remain fail-closed and preserve latest adoption. No protection was removed.

### Completion and remaining evidence

The independent bad-component/good-component counterexample is closed offline, and a real
service call can adopt multiple independent targets. Same-day invalid members remain atomic;
shared identity competition cannot duplicate a visit. Existing A/B/C protection, source/cost,
fixed time, fair comparison and cancellation tests continue passing. Actual graph mocks verify
mode-aware adoption and final Nearby/resource ownership. This is not retrospective proof that
Honolulu's complete historical failure is fixed.

Remaining limits: conservative same-day grouping; nearest-anchor provisional preparation;
no exhaustive insertion search; no parking/vehicle continuity, fare or public admission
verification; no transit instructions. Exact-time provider support, realistic model dispositions,
latency and joint-component throughput still require separately authorized development live.
A252k ceiling and16 requests are bounded engineering headroom, not demonstrated optimal values.
No new correctness blocker remains in the exercised offline paths; this is not a global proof.

## Shared first-generation mixed transport (current offline checkpoint)

V3 uses the shared 2026-09-25 mixed-transport baseline. The [retained checkpoint summary](v1-milestone.md#shared-first-generation-mixed-transport-current-offline-checkpoint)
records mode applicability, compact evidence, route diagnostics, limits and reservations.
V3 consumes those facts in its existing validation/Repair; its distinct development
results remain in this record. This shared checkpoint was offline-only; it adds no version freeze or new live acceptance.

## Minimum Daily Coverage checkpoint (2026-09-25)

Implementation and offline validation precede the separately authorized single Honolulu live.
See the [minimum coverage contract](../../0003-itinerary-transport.md) for current rules. Generic activities retain
occupancy and unknown location; they are not converted to elastic free_time or false route
endpoints. The system offers authorized gaps but does not guarantee an admissible addition.

Offline verification found a real comparison-adaptation defect: unchanged missing
coverage on another day lacked a comparable magnitude. The correction preserved
production guards and source identities. Final combined minimum/wiring/multiround/B/
Repair validation passed 181 tests; shared diagnostics/wire/Gate/initial routes/V0–V2/
API checks passed 203, and frontend 24. These overlapping slices used no external
provider and are not a new full backend result.

Historical reconstruction uses run 8b7db82f-9c52-4cdc-b802-2c273406ee66, preserving its source
SHA-256. The small fixture retains original draft/contract and a reduced identity/location
projection, not all route/opening evidence. Oct 5 becomes the active minimum target; Oct 1
and other ordinary reviews are deferred. Fake empty proposals preserve the generic walk and
stop on no material change. This is offline reconstruction, not historical repair success.

Actual serializer/tokenizer: minimum reconstruction rounds 13074 / 13259 tokens; mixed-mode
32-identity rounds 80283 / 80428 / 80430 / 80430 / 80430. Protected-text stress inputs
224502 and 251502 fit; 254502 and 274502 exceed 252000 and retain overflow behavior. Synthetic
output 4162 / 16384. Diagnostic token groups overlap and must not be summed. Updated
interpretation normal input sum 7071 (excluding provider framing), including strict wire
schema 3464. Sizing is offline, not actual usage. Artifacts: logs/minimum_coverage_offline_20260925/.

Known limits: no new experience identity, public-access guarantee, generic-activity relocation,
TRANSIT coverage, or Preference Gate Step 1 blocker fix. No full-day exemption is inferred
from relaxed or partial fixed occupancy. The new full-day interpretation branch remains
without real-model evidence unless the authorized live actually exercises it.

Final affected C/API-evidence/mixed/B/minimum regression: 111 passed / 2 failed initially.
A real interaction was corrected: an actually activated, narrowly scoped hard-obligation
removal may leave a visible minimum-coverage debt, subject to the existing loss-specific
coverage authorization. Ordinary deletions cannot use that exception. The other failure
was a synthetic second-day visit outside its provider fixture's hours; adjusting its time
alone still failed because Sunday hours were absent. The fixture now explicitly supplies
both days. Intermediate reruns: 112 passed / 1 failed, followed by two diagnostic single-test
failures; final affected suite: 113 passed. Final targeted Ruff passed; frontend production
build passed. These are offline results, not provider or live validation.

### Authorized single Honolulu live: minimum coverage

Run `f9bd621d-0eb5-47d7-8af8-03825d57524b`, records in
`logs/v3_honolulu_9day_minimum_coverage_20260927/`. Reference date 2026-09-25;
request Sep 27-Oct 5, two travelers, USD3000, original relaxed preferences.
Actual deployment gpt-6-luna; three run-local reviews on; repository defaults unchanged.
Unchanged effective limits: five calls, 360s stage, 600s request, 252000/16384 tokens,
32 identities, 24 route requests/32 elements (8 requests reserved post-proposal).

Initial main counts: 2,1,3,2,0,0,1,1,0. Final: 2,2,3,2,2,2,1,2,2.
Round 1 prioritizes Oct1/2/5 minimum targets and adds one visit to each; ordinary reviews
are deferred. Round 2 adds one visit, rejecting the separate Chinatown insertion for
insufficient unoccupied transfer window. Round 3 adds three visits; round 4 adds one
with route UNKNOWN and the existing conservative reserve; round 5 returns empty edits.
Final ACCEPTED_PARTIAL / round_or_model_limit retains all eight accepted additions.
All nine minimums satisfied, Oct3 ordinary quantity review remains. Generic Downtown
activity is unchanged, not counted. Authorized free-time fragments retain their lineage.

Repair engineering inputs: 92975,88896,92730,57565,52605; primary87607. All below252000.
Real Repair input/output usage: 373661/11121, already included in callback464989/18848.
Embedding prompt/total16/16. Ordinary Details32/60 (20 cached qualified), initial RAG
resolution30/30, Details25/30, fallback4/4; no Repair discovery/Details sends.
Routes baseline6/324, initial alternatives18/18, Repair24/24 requests/elements.
Repair includes one HTTP400/ProviderHTTPError and three later pre-send budget stops;
no retries or additional run. Final opening16 PASS/3 UNKNOWN; route9 PASS/1 UNKNOWN;
visitor suitability19 UNKNOWN, budget1 UNKNOWN, semantic requirements1 UNKNOWN,
quantity1 NEEDS_REVIEW, zero CONFIRMED. These include the generic area where applicable.

Nearby one stage, three requests, three references; final primary fields unchanged.
Source hashes unchanged; request-owned RAG reports closed. Exit0, process200.969s.
Exact model request strings are not separately captured; full result DTOs and extracted
rounds are authoritative over truncated trace previews. Per-round deadline/remaining
values are not elapsed measurements. No independent socket-level close audit is claimed.

Status: implemented + offline-validated + bounded development-live-validated for the
observed 0->1 priority/repair path. Review-off behavior, exemptions, unassessed restrictions,
and hard-removal coverage-debt exception retain offline evidence only. No benchmark,
freeze, whole-trip feasibility or historical repair claim. Existing Preference Gate Step1
contract mismatch is unchanged and was not exercised by this successful normal input.

## Offline V3 deadline-phase regression correction (2026-10-06)

The user approved offline diagnosis and correction of the V3 timeout baseline failure,
regressions, local commits and independent Standards/Spec review. Generation semantics,
production limits and zero-paid-call/no-push/PR/merge boundaries remain unchanged. The
fixed review base is `54a59427f2a3233196c92068cdde048ace1e9bef` on
`feature/evaluation`; the unrelated pre-existing `.gitignore` edit remains excluded.
This is a subsequent engineering correction, not a new V3 freeze or formal evaluation.

The immediate context is the full backend failure retained by the
[#83 identity acceptance](../evaluation/intake-identity-usage.md#version-owned-requirement-targets-2026-10-06).
The original `test_whole_request_expiry_during_primary_prevents_postwork` used a
0.1-second wall-clock allowance and asserted one retrieval close without establishing
that primary generation or lazy retrieval initialization had started. An isolated
rerun reproduced `runtime.closes == 0` versus expected one, in 3.67 seconds including
test setup. Ranked hypotheses were premature expiry, a real cleanup omission, and
another stage changing the terminal error. An offline public-entry probe recorded
only synthetic stage names and resource counts, not provider payloads or credentials.
At 0.1 seconds, primary generation was never entered and retrieval enter/prepare/close
were all zero. A 2.0-second diagnostic allowance reached primary generation and
enter/prepare/close were all one; both cases raised TimeoutError and skipped Nearby.
The evidence identifies a test phase-selection assumption, not a demonstrated runtime
resource leak. Increasing a production budget or eagerly creating unused resources
would not be a correction for that test assumption.

The corrected regression freezes the time boundary during setup, advances it beyond
the existing request deadline only when the injected primary model operation begins,
then waits for real `asyncio.timeout_at` cancellation. It asserts that primary actually
started and was cancelled, owned retrieval entered/prepared/closed once, and neither
Repair nor Nearby followed. The complementary pre-graph expiry test calls public
`run_v3` with a forbidden retrieval factory and verifies that no place query, model,
semantic model, Repair or Nearby operation begins. Time and external provider boundaries
are substituted; the real graph, timeout scheduler and resource-release implementation
remain in use. No internal dispatcher or cleanup method is mocked.

The original failing test was run before correction. Its corrected single-test gate
passed, followed by both deadline-phase tests (**2 passed**), and the full V3 version
suite (**425 passed**, 22.14 seconds). Ruff, compilation and whitespace checks passed.
The test plus current lifecycle clarification were committed before review as
`4c466d5` (`test: trigger V3 deadline expiry in the intended phase`). Independently
reviewing all committed changes against the fixed base found **zero Standards findings**
and **zero Spec findings**; no correction commit was needed. Production application
code, dependency versions, runtime configuration, generation/scoring policies and
V0-V2 behavior were unchanged. The change clarifies the existing distinction between
an uncreated lazy runtime and an owned runtime requiring cleanup, including caller
ownership.

Local evidence identifiers are `artifacts/v3-timeout-baseline/repro-01.txt`,
`probe-01.txt`, `primary-green-01.txt`, `phase-green-01.txt` and `v3-green-01.txt`
in that directory. The diagnostic probe is clearly marked as debug-only scratch,
outside tracked test ownership. All tests use injected synthetic responses and the
normal external-network prohibition; Windows asyncio internal loopback is permitted.
Actual model, Places, Routes, database and embedding service calls are zero, as are
paid calls. No live smoke, benchmark, remote code publication or branch switch occurred.

The final fresh full backend gate passed **2983 tests / 10 skipped / zero failures**
in 332.87 seconds. Its local receipt is
`artifacts/v3-timeout-baseline/full-green-01.txt`. This actual complete run includes
the prior #83 identity corrections and the stronger V3 timeout tests; it resolves
the previously recorded baseline limitation without deriving a green result from
separate partial runs. Final documentation checks verify new prose is English,
new local links/anchors resolve through tracked files, and production code/configuration/
dependencies have no difference from the fixed base. No new runtime instrumentation
was introduced, and no further broad rerun was necessary after this passing gate.

<a id="soft-pace-repair-acceptance-2026-10-09"></a>

## V3 soft pace Repair objective acceptance (2026-10-09)

Status: implemented and offline-validated under
[#93](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/93). The user clarified
that zero deductions is a V3 Repair optimization objective, not an output validity gate
or cause of Repair failure. Public TDD seams and Issue publication were approved. The
fixed review base is `35499b65fabebdfe1cb572123d7fb9bdeabfcd15`; implementation is
`32be42d`, with review correction `0a4a96b`. Concurrent address work is independently
owned by the [address acceptance](../evaluation/intake-identity-usage.md#google-address-equivalence-acceptance-2026-10-09).
The four existing original outputs were preserved.

### Implementation and observed behavior

The existing interpretation call obtains bounded, source-linked daily pace, exact daily
counts and requested-date exceptions. Canonicalization validates quotes and dates;
no validator keyword inference or additional model stage is introduced. Empty preferences
use ordinary pace locally; historical null/absent metadata remains unassessed. Wire
`PreferenceDraftV10` and prompt `preference_prompt_19` identify the optional extension.
Pure numeric curves are shared with RTPEval while interpretation and evidence remain
independent. V0-V2 and V3 draft acceptance acquire no zero-deduction constraint.

V3 quantity review produces diagnostic soft targets and bounded legal permissions.
Read-only validation counts primary visit occurrences, including independently assessed
visits labeled generic. Candidate qualification, mandatory visits/counts/dates, role,
route/occupancy, coverage, and existing budgets still govern acceptance. A proposed patch
must reduce its authorized objective without increasing another comparable date's penalty
or losing its evidence. It cannot relabel visits to evade counting. Before/after summaries
report reached, residual or unavailable targets, explicitly without a failure constraint.

Mocked public `run_repair_stage` demonstrates relaxed three visits becoming two, reducing
the daily penalty **40 to 0**; immutable draft and accepted patch are retained. A four-visit
day becomes three with **70 to 40** after one authorized model call, then stops at the model
limit as ACCEPTED_PARTIAL, preserving that legal improvement. A protected mandatory visit
cannot be deleted. An exhausted stage sends no model request and preserves its usable
draft and residual penalty. Existing disabled/no-op/rejected/budget paths remain covered
by the full V3 suite. The actual V3 runner consumes the existing interpretation call's
pace metadata and exposes separate original/final diagnostics. Public evaluator reporting
and V3 validation agree on the tested literal numeric examples and date override.

### Validation and limitations

Test-first public behavior exposed the absent soft target/progress before implementation.
Integration required migrating only synthetic provider fixtures and current wire/prompt
assertions; frozen original artifacts were not edited. The broader failure/correction
sequence and shared full-backend checkpoint (**3195 passed, 10 skipped**, 464.36 seconds)
are recorded once in the linked address acceptance. This full checkpoint is at `32be42d`.
Subsequent address/V3 review-correction tests passed **483** at `0a4a96b`. Standards review
found one P3 possible duplicate computation: authorization and acceptance independently
implemented the same pace-permitted coverage floor. `pace_coverage_floor` now owns that
pure formula; both checks still apply it independently. Standards and Spec rechecks report
zero remaining findings. Ruff and whitespace checks pass. The subsequent full evaluator
gate passed **1248 / 1 skipped** in 425.16 seconds at the same revision; its shared
source-binding/replay scope is detailed in the address acceptance.

Local gate identifiers are `artifacts/address-pace-tests/review-green.log` and
`full-stable.log`, not published dependencies. No real generation, model/provider request,
budget increase, version freeze, push or PR occurred. Numeric agreement and controlled
Repair behavior establish the implementation paths, not a general quality guarantee.
The retained real V3 output and the existing four-version run's six soft penalty findings
were not changed retroactively. Fresh V3 generation followed by a newly bound evaluator report
requires a separate approved execution package; residual penalties remain valid outcomes.

### Real Repair smoke and evaluator effort preflight (2026-10-09)

Status: one authorized real generation completed; source-bound density reduction was
checked offline. The corrected medium evaluator stopped before provider dispatch;
new independent factual evaluation remains incomplete.
Generation source revision is `7db7a562da20c24827dfe845d5057b16150bc0b3`. The approved one-use generation handoff digest is
`8cb9744db64896b9d3d4a2f4435d1184457b4355ed906e4870c70ef3571e44ab`.
The native runner was launched through a frozen local main-model configuration
adaptation: `gpt-6-luna`, medium, 16,384 default output tokens, retaining explicit
nomination/semantics/primary/Repair limits. All nine actual model request bodies were
checked for medium. No application generation source was changed by this adaptation.

The same original Sydney Input and reviewed requirements were used. Original V0-V3
outputs and their accepted report/receipt stayed unchanged. One new V3 was captured
under a 600-second whole-request limit, 360-second Repair limit, at most five Repair
calls, zero retries and USD 14 retail reference allowance. A sandbox read-only RAG
check timed out; the elevated read-only compatibility check passed in 0.047 seconds
with no embedding sends or database mutations. The execution child was selected as
`gpt-6.1-sol`, medium, in the current session.

The generation exited successfully in 188.297 seconds. Actual HTTP sends were
75 Google (15 Search, 40 Details, 20 Matrix; 212 elements), nine model, one embedding
and one weather request. Web search/page sends were zero. All 86 HTTP request and
response bodies were complete. Reported total tokens were 290,600, including the
embedding call; four Repair calls accounted for 223,505 tokens. The captured retail
estimate was USD 2.384446085, not a provider invoice.

Repair retained four rounds: REJECTED, REJECTED, ACCEPTED_PARTIAL and
ACCEPTED_COMPLETE. The adopted primary counts changed from `[2,3,2,1]` to
`[2,2,2,2]`. October 15 removed Observatory Hill Park; October 17 added
Mrs Macquarie's Chair. Native mean soft pace deduction changed from 15 to zero.
Independent evaluator density rules gave the same source-only result after a new
agent-origin activity review: the generic, unnamed flexible food stop has no concrete
venue and uses the same non-primary transition classification as the retained V0
food activity. Final, draft and adopted-primary source pointers were reviewed separately;
no human review was invented. Before that review, count uncertainty was preserved.
This numeric assessment does not certify identities, opening, routes or hard facts.

The original new-result hash is
`de49df697b71df2e9a6e21b389965a2870bb8e2dc5e63b3af1d6b9cc0de4e66a`;
usage is `237765411e6f6e310c7e5f501892062a1af17eeb86f0060321aee16192bb40b9`.
Local evidence identifiers are `artifacts/sydney-v3-pace-live-20261009-r1/v3` and
`artifacts/sydney-v3-pace-preparation-20261009-r1`; these ignored paths are historical
identifiers, not published dependencies. Result JSON retains complete draft, round,
patch and adopted history. Mechanism evidence is available with no missing fields.
The generation evidence index remains partial: the 10,033,415-byte final trace summary
was stored as a truncated preview wrapper, so `finished_trace` is unavailable.
Original evidence was neither repaired nor relabeled complete.

Fresh four-final preparation binds original V0-V2 plus the new V3, independent Input/
RequirementSpec and source-linked reviews. The actual source population permits a
96-Google-send ceiling and USD 3.20 reference allowance, reduced from the provisional
160 / USD 5.50 scenario. The first approved evaluator package,
`c17ca14def6ebc7eb8bfc4908fac811e0fc23e95eb3f18c470ac49f92486b600`, was blocked before
any send: the handoff required medium, but native identity execution and replay
implicitly used low. Execution preflight verified sources/code and then stopped;
Google/model sends and cost were zero. This package remains unexecuted.

Commit `0f324cd` adds an optional frozen identity effort field, preserving old low
preparations and leaving opening's separate fixed-medium contract unchanged. The
public CLI regression first failed because the new option was rejected, then passed
after preparation, sending and replay consumed the same option. Final evaluator and
opening CLI regressions passed **28 tests** in 39.18 seconds, including historical
defaults, low/medium wire capture, invalid-option rejection and rejection of a
resealed HTTP journal with the wrong effort. Ruff passed; independent Standards and
Spec review of `0f324cd` against `7db7a56` reported zero findings on each axis. A new code-bound medium
preparation and exact authorization are required before live evaluation. Missing-hours
assessment remains a separately prepared/approved stage; no additional generation,
retry, formal benchmark, version freeze or remote publication occurred.

The explicitly approved corrected-medium preparation digest
`76ad5f5e16e079cc0c0eb1c5c22a64bc22cf19ab67a3c5ab744c1803351a03ee`
was invoked once at source `ac15fffc28b62a59c7f8b97678aa2d7494d4ac90`. It stopped with
`Execution price unavailable: missing_price_or_billing_context` before dispatch:
zero Google/model sends, zero tokens and USD 0 reference cost. The usage timestamp
was `2026-10-08T22:04:17.219420+00:00`, already October 9 in Sydney. All six price rows
started on October 9, but native reservation uses the UTC usage date. Exact field
masks and fee rates matched; the effective-date window did not. This was a preparation
configuration error, not provider unavailability or an observed billing charge.

Native replay with DNS/TCP disabled reproduced the stopped report and verified the
closed receipt. Processing was stopped, acquisition partial and evidence not completed.
No quality report exists for this invocation; FAIL/UNKNOWN counts cannot be inferred
as zero. Retained report/receipt hashes are
`f5b809f9da141a5da261182ead9e284690af37f85b396e4dfe87d53e2754465b` and
`95828bb401fd337f963c84ddf07811bb1f8605f80632f335f035d79b9a8379b5`.
The consumed execution is preserved at the local historical identifier
`artifacts/sydney-v3-pace-preparation-20261009-r1/evaluator-reviewed/run-medium/execution`.

A separate local preparation corrects only UTC price coverage to October 8 through
the exclusive October 10 boundary; selectors, rates, source outputs, context, code
and execution limits are unchanged. Offline native transport probes passed 94
reservations across both UTC dates: all 42 actual identity requests, fresh Details,
three configured Matrix modes and a maximum-token medium identity reservation on
each date. All six old price contexts reproduced the observed date failure; twelve
outside-window checks still rejected pricing. DNS/TCP were blocked and HTTP sends
were zero.

The 96-send worst-case retail reservation is USD 3.07575, including the one maximum-token
identity request, below the unchanged USD 3.20 reference allowance. This is a conservative
configuration calculation, not actual billing. Source/intake, review/context, options,
identity plan and all 73 implementation hashes match the consumed preparation. New
preparation digest is
`1d925719b74a1a89211f0d819465bdc8f2ffcfe8776252c3544fde203127ab30`;
local preflight identifier is
`artifacts/sydney-v3-pace-preparation-20261009-r1/evaluator-utc-price-preflight.json`.
The one-use, zero-retry instruction prevents reinvoking the consumed directory. The
new preparation requires its own exact authorization; no opening model or generation
was run, and the existing partial generation-trace limitation remains visible.

The UTC-corrected digest was subsequently explicitly approved and executed once at
`eb370b57e38ed3f048a8772a36df217747c080b0`. Native execution and credential-free,
DNS/TCP-blocked replay both exited zero. Parsed execution output, saved report and
replay output were identical; the receipt remained unchanged. Processing and acquisition
were complete, with unresolved judgments retained. All 76 HTTP events completed:
28 Google Search, 31 Details, 16 Matrix and one identity model call. Actual identity
wire used `gpt-6-luna` / medium; reported input/output/total tokens were
14,247 / 2,332 / 16,579. Zero retries were used. Reference cost was USD 1.5989468;
account billing remains unavailable. Generation plus evaluator reference estimates
sum to USD 3.983392885, excluding any later opening call. Native usage timing spans
36.874161 seconds. Report hash is
`16751da4944137c1683f214a1c5482f54ddb04a449f15629b1ac556797abf7d7`;
receipt hash is `dd1e13d7a02bcf13529cdecaa5a9318906c74ef398a99b572d834e07ebab30ed`
and closes 238 files. All original outputs, Input, old accepted report/receipt and
the unrelated `.gitignore` edit remained unchanged.

### Post-acquisition review completion and current findings

The original live preparation omitted the route-mode review and did not contain a
new V3 food-activity occupancy review. The native report therefore has 30 UNKNOWN
entries: 17 route policy checks, one unresolved V3 occupancy denominator and 12
missing-hours checks. V3's native total is unavailable. These preparation omissions
are preserved in the immutable original report, rather than erased or attributed to
provider acquisition.

The parent completed independent source reviews after acquisition. The complete
original Input states a soft walking/public-transport preference, without an exclusive
mode restriction, so the reviewed request-mode policy is unrestricted. The new
13:30-14:30 flexible food activity is committed occupancy: choosing a venue flexibly
does not release its original timed block for travel. It remains non-primary for POI
density. Final, draft and adopted-primary pointers were reviewed separately using
the same occupancy interpretation as V0. Review provenance explicitly identifies the
agent; no human judgment, concrete food venue, protected-time obligation or transport
endpoint was invented.

The public `quality_report_cli` recalculated quality from this run's fresh snapshots,
unchanged identity report and completed reviews, with DNS/TCP blocked. Exact repeated
CLI output agreed and the parent execution receipt remained unchanged. All 17 route
policy checks now PASS, and V3 has 13 decided non-overlap commitments with no unresolved
denominator. The resulting report is an explicitly separate offline recalculation,
not a rewritten native execution. Local historical identifiers are
`artifacts/sydney-v3-pace-preparation-20261009-r1/evaluator-reviewed/post-acquisition-reviews`
and its `recalculation-receipt.json`. New external sends were zero.

Current API-only results, before a new missing-hours model judgment:

| Version | Overall score | Grounding FAIL | Opening UNKNOWN | Mean soft pace deduction |
| --- | ---: | ---: | ---: | ---: |
| V0 | 86.4286 | 1 | 2 | 5 |
| V1 | 72.0000 | 0 | 4 | 20 |
| V2 | 75.0000 | 0 | 4 | 15 |
| New V3 | 77.5000 | 7 | 2 | 0 |

All four exact-once Opera House obligations PASS. No non-overlap or route FAIL remains.
The eight grounding FAILs are retained under current rules: the V0 identity model
assesses Australian Museum's College Street claim as incorrect relative to Google's
1 William Street address; this is a model judgment, not a separate official entrance
audit. Seven new V3 addresses fail whole-address equivalence: Opera House, Art Gallery
of New South Wales, Harbour Bridge, Queen Victoria Building, Sydney Tower Eye,
Darling Harbour Woodward Water Feature and Royal Botanic Garden. Claims omit parts
of the Google address such as state/postal/country qualifiers; Tower also omits the
floor, and Harbour Bridge gives a broad harbour location. The approved component-alias
rule explains abbreviations but does not waive omitted or changed address content.
The current binary verdicts are retained; no address-policy expansion occurred.

Five final density deductions remain outside new V3: V0 October 17 (one visit, 20);
V1 October 14/16 (three visits each, 40 each); V2 October 14 (three, 40) and October 17
(one, 20). Independent paired density assessment using the new identity report confirms
new V3 draft/adopted-final mean deduction **15 to 0**, counts `[2,3,2,1]` to `[2,2,2,2]`,
over four retained Repair rounds. This verifies the targeted pace improvement without
making zero a validity gate or asserting factual correctness of every address.

All twelve remaining UNKNOWN entries lack current and regular hours in fresh evidence:
V0 Opera House (October 14) and Powerhouse (October 17); V1 Opera House/Harbour Bridge
(October 14), Darling Harbour (October 15), Bondi Beach (October 17); V2 Opera House/
Harbour Bridge/The Rocks (October 14), Darling Harbour (October 16); new V3 Opera House
(October 14) and Harbour Bridge (October 15). Current public-landmark rules require a
separate source-bound access model judgment before applying their inference branch.
No old opening response was reused, and API factual hours were not manufactured.

A fresh incremental opening preparation binds those twelve cases to this completed
parent receipt and current code. Digest is
`c47f42c0b55f3e40c137b08e41362a08fb0c6b4b55f07ca8875155104efda968`.
It permits zero Google sends, at most one `gpt-6-luna` / medium model call, 32,000
input / 8,000 output tokens, 120-second request / 900-second overall limits, zero
retries and USD 0.05 reference allowance. Full request input plus tokenizer margin
is 15,514 tokens; worst-case model reservation is USD 0.008. Both UTC price dates
and fresh parent/source/code bindings pass offline checks. This stage remains
prepared but unexecuted pending exact approval. After its receipt, the public quality
CLI can consume the new opening material and completed route/occupancy reviews;
all original native receipts remain immutable. Formal ranking, version freeze,
remote delivery and the partial generation trace remain outside this acceptance.

## Google-backed output facts 2026-10-09

Status: Implemented and validated offline; no fresh generation or version freeze.
[Issue #94](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/94) owns the
approved planner fix. Fixed review base is `a1309e0fe27aa9ae85fc7043c4715779a7429d6f`;
implementation and tests are committed as `202a59d6a2eaaa6573d5e83ef718364db84fa92c`.

### Observed failure and correction

Captured Google Details and the complete primary request contained all seven full
addresses involved in the new-V3 grounding failures above. Primary model response
`0078` shortened each address. The accepted draft and final output retained those
seven shortened claims unchanged. The Repair-added visit already had its canonical
provider address. This source chain isolates an application ownership gap: shared
acceptance restored the supplied name but left `location` model-authored; retained
and retimed Repair visits inherited that field. It does not establish bad Google data
or justify relaxing independent whole-address comparison.

Three first regression cases failed on absent, shortened and incorrect model locations.
The minimal production correction copies the same authorized PlaceEvidence's
`formatted_address` alongside its name at `validate_output_sources`. A missing provider
address becomes null instead of adopting a model guess. The existing V3 final boundary
already uses original supply plus verified Repair identities, so no duplicated V3
normalizer, new finding type or extra request was introduced. Titles, times, costs,
role, notes and private diagnostic attribution remain unchanged; V0 and null-ID
generic activities keep their original behavior.

### Validation and retained evidence

The user confirmed public `validate_output_sources` and actual `run_v1/run_v2/run_v3`
test seams. Focused coverage passes 21 cases, including identity rejection, raw object
immutability, canonical null addresses, V0 preservation, idempotence, real mocked
version runners and V3 successful/rejected/no-Repair/new-addition paths. The policy
and complete version regression gate initially returned 771 passes and three failures:
old preservation fixtures lacked their source's canonical address. Updating only those
fixtures retained the original equality, time/Repair/Nearby assertions; the gate then
passed **774 tests in 28.06 seconds**. Full backend validation then passed
**3222 tests, 10 skipped in 447.45 seconds** on the unchanged implementation.
Ruff lint on the six changed Python files, formatting of both new test files,
English additions, tracked documentation targets/anchors and whitespace checks pass.
The policy file's unrelated existing formatter differences are also present at the
fixed base and were preserved rather than included in this correction.

Implementation/tests were committed before independent Standards and Spec review.
Both implementation reviews and final-documentation rechecks report zero findings.
Final documentation is consolidated after validation; no review correction commit
was needed.

DNS/TCP-blocked retained reproduction first failed the canonical-address invariant and
passes after the fix. A separate in-memory derived acceptance applies the real public
boundary to the retained draft/final. It restores all seven affected final addresses,
preserves the other activity fields and leaves all originals untouched. Ten protected
hashes include five old/new outputs, old and fresh reports/receipts and `.gitignore`;
all agree. The fresh native receipt's **238 closed files** also match their hashes.
Local historical identifiers are
`artifacts/sydney-v3-pace-preparation-20261009-r1/google-address-generation-diagnosis.json`
and `google-address-fix-offline-acceptance.json` in that same directory. They are local
diagnosis/derived-proof aids, not a new generation, evaluator report or replacement receipt.

Actual external sends and new charges are zero. Historical seven new-V3 grounding
FAILs, twelve missing-hours UNKNOWNs, pending opening-package authorization and partial
generation-trace coverage remain unchanged. A future real V3 generation needs its own
prepared and approved package; current independent evaluator rules remain unchanged.
No push, PR, merge, branch switch, formal comparison or freeze occurred.

## Fresh opening assessment and final composition 2026-10-09

Status: Authorized execution complete; native opening CLI and frozen-intake public
quality API replay validated. Quality CLI composition has a diagnosed serialization
gap and is not accepted as a complete final-report CLI path. No new generation occurred.
Execution source is `51033fbf226838ba3f554d1ebc8857889115cab7` after the authorized
three-doc squash; product code is unchanged from the tested address-protection state.

### One approved request and fresh findings

The user explicitly approved opening preparation
`c47f42c0b55f3e40c137b08e41362a08fb0c6b4b55f07ca8875155104efda968`.
The parent rechecked all 73 implementation files, parent receipt, original sources,
unconsumed execution directory, current UTC pricing, credentials and token bound
without network, refreshing only the execution handoff's source revision. A current-session
`gpt-6.1-sol` / medium child executed the prepared CLI once. Actual model wire was
`gpt-6-luna` / medium, HTTP 200; Google sends zero, model sends one, retries zero.
Reported input/output/total tokens were **13,821 / 2,891 / 16,712**; reasoning tokens
were 1,022 and cache-write input was 13,818. Request timestamps were
`2026-10-08T23:20:43.225123Z` through `23:20:59.269848Z`, approximately 16.04 seconds.
Reference incremental cost is **USD 0.00317305**; account billing is unavailable.
Combined independent evaluator reference cost is **USD 1.60211985**, excluding generation.

Eleven missing-hours decisions PASS under unchanged public-landmark access policy.
API hours were not invented or promoted to factual coverage. The remaining decision
is V0 Powerhouse Museum on October 17, 10:00-12:15 local time. Its original title
implies museum admission, which cannot use ordinary outdoor-landmark inference.
The model assesses the daytime window as reasonable but finds admission unsupported
and supplied temporary-closure status leaves future access uncertain. That undated
status does not prove October 17 closure; the result stays UNKNOWN with
`hours_missing` and `llm_access_reasonableness_unknown`.

### Replay, composition and diagnosed CLI gap

With credentials cleared and DNS/TCP prohibited, actual `replay-opening` CLI output
exactly equals the saved native report. Its immutable parent context still contains
the historical 17 route-review UNKNOWNs and unresolved V3 occupancy denominator;
the native report therefore retains 19 UNKNOWNs rather than rewriting its preparation.

The final quality CLI, supplied with already completed route/occupancy reviews and
the fresh model material, initially failed with `artifact_integrity_error`:
`Stale or foreign opening packet`. Read-only reconstruction isolated request-input
serialization: `load_batch.to_dict()` and frozen intake have equal source content but
different source-key insertion order. All cases, decoded input, remaining request fields
and remaining packet fields agree; the bound raw `request.input` strings and packet
digests differ. Frozen packet digest is
`659728e9420c0ba0707b6b5105bf05a7d31c96b77acce5c277ae3abd89d2617d`;
CLI reconstruction gives `6610e24a28a12c3c553bd91c8b3f4ca6da07ae1021bb283659230e2e9473bf5f`.
No raw model response, packet or importer rule was normalized to evade this rejection.

Public `build_quality_report` over the exact frozen intake accepts the same fresh
material and completed reviews, retaining binding validation. Exact repeated API
construction agrees, and independently recomputed opening/route/requirement components
complete. The separate derived report closes its own review/artifact hashes and links
both native receipts. It is not a replacement native receipt or a passed quality CLI run.
The local composition helper initially treated identity report status as a metric's
`complete` status; that helper-only assertion was corrected to check the three metric
reports separately. No product code, paid request or source evidence changed.

| Version | Final score | Grounding FAIL | Opening UNKNOWN | Mean soft pace deduction |
| --- | ---: | ---: | ---: | ---: |
| V0 | 89.2857 | 1 | 1 | 5 |
| V1 | 80.0000 | 0 | 0 | 20 |
| V2 | 85.0000 | 0 | 0 | 15 |
| New V3 | 82.5000 | 7 | 0 | 0 |

All four exact-once Opera House checks PASS; no non-overlap, opening or route FAIL
remains. The eight grounding failures retain the original claims described above.
Five source-linked daily pace deductions remain outside new V3. These are bounded
engineering-case results, not a formal research ranking. Address protection is
prospective and does not modify this already saved V3 result.

Native opening report SHA256 is
`bc6f629426013983b4785b6000a524fec278f6c0242372112e05f9e7fc52ea58`;
receipt SHA256 is `2bc095a94502dc79a32bda5463b6430ef35ccab3ecb9ef44481ea2d42956e7d8`.
Local historical identifiers under
`artifacts/sydney-v3-pace-preparation-20261009-r1/evaluator-reviewed` are
`opening-medium-utc/execution`, `final-reviewed-opening/final-report.json`, its
`recalculation-receipt.json`, `quality-cli-failure.json` and
`opening-quality-cli-key-order-diagnosis.json`. Native reports/receipts, ten protected
source hashes and 238 parent closed files remain unchanged. The whole model output,
actual usage and original HTTP response are retained locally; published records contain
no secrets or raw payload dumps.

The serialization gap was subsequently corrected in the next section, preserving historical replay. Museum admission needs applicable access evidence or explicit
disposition. The one-use opening allowance is consumed. A new V3 generation or other
paid request needs a new approved execution package. Partial generation-trace coverage,
formal research, remote Git delivery and version freeze remain outside this acceptance.

<a id="source-protected-v3-cli-execution-2026-10-09"></a>
## Source-protected V3 and CLI execution 2026-10-09

Recorded checkpoint: Serialization correction implemented and validated offline; fresh V3 generation
complete. Complete live evaluator acceptance is blocked by incomplete V0 model coverage.
No final scores were available at this checkpoint; older scores were not substituted.
The subsequent coverage correction and accepted full CLI run over the same outputs
are recorded in [identity coverage acceptance](../evaluation/intake-identity-usage.md#complete-v0-identity-coverage-acceptance-2026-10-09).

Review base was `6ad619c23ed159e67487f7e805ac0041a4929a50`; implementation is
`db92930c9848aee1a80d1f87301fb6c68b50221e`. The human approved the correction, public test seams and
fresh-generation/evaluator flow, then explicitly defaulted execution approvals while away.
The parent retained the USD 14 generation, USD 5.50 evaluator and USD 0.05 optional
opening reference envelopes. These are retail/proxy allowances, not account invoices.

### Serialization correction and offline validation

Both native-to-quality CLI regression cases first failed with stale opening packet
diagnostics. Sorting object keys only when constructing `request.input` fixed both;
array order, source facts, scoring and exact import/request/response/implementation
checks remain unchanged. Intake mapping order no longer changes a newly prepared
request. Rewriting the recorded request, original quotes or evidence still fails import.
Affected tests passed **57 in 32.58 seconds**; full backend passed **3224, 10 skipped
in 442.77 seconds**. Independent Standards and Spec implementation reviews found zero
issues. No frontend gate was rerun.

Historical opening CLI and derived quality API replay with the retained implementation
reproduced their saved results, without rebinding old responses to new code. Original
file-line-ending bytes were checked against frozen implementation hashes. The prior
quality CLI failure remains a historical failed execution; it was not rewritten as PASS.

### Fresh generation

Generation handoff SHA256 was
`68d35cef9cf39659a10a51c555ea8d709f635ca40fca86b3cbca281a5b21f0b7`.
The current-session `gpt-6.1-sol` / medium execution child invoked the frozen V3 command
once with `gpt-6-luna` / medium. Read-only TripWorld compatibility and offline wire
checks passed.

Only the request-local trace limit changed from 10 MB to 20 MB: the preceding final
trace had measured 10,033,415 bytes. Planner/tool/Repair policies and budgets were
unchanged. Generation exited zero in 118.223 seconds; usage reports 110.594 seconds.
Actual sends were **75 Google** (12 text search, 3 nearby, 40 Details, 20 matrix with
212 elements), **5 model**, **1 embedding** and **1 weather**; no Web/HTML requests
or retries. Model usage was 53,476 input and 12,281 output tokens, total 65,757;
4,937 reasoning tokens are included, not added again. Reference cost was **USD 2.352683635**.
All 259 indexed artifacts matched, with no missing capture fields or diagnostics.
The runtime-policy canonical configuration digest and enclosing file-byte hash are
intentionally distinct; both bindings were independently verified.

The new result SHA256 is
`ecd6d368b4467fc3a49995dc925d983475fa14cf08beb9cdd4870e7d69ea7e6f`.
All eight final sourced names/addresses match the captured generation ledger exactly.
Each day contains two primary visits and the draft/final pace deduction is zero.
Draft equals final; Repair made **zero rounds**, reason `no_authorized_targets`.
This run demonstrates an already satisfied objective, not a new nonzero-to-zero Repair
improvement or independent evaluator address PASS. Earlier Repair evidence remains separate.

### Independent evaluator stops and replay

Original V0-V2 and this new V3 were frozen as batch revision 4. Original-source route,
density, activity-role and occupancy reviews were included before preparation, with
agent provenance preserved. Fresh acquisition never reused an old identity report.
The initial package bound at most 86 Google requests, one identity model and USD 2.76;
preparation SHA256 was `f5c55aba14029659515ebc7554f7ab4e4b9c3872224c2361c1cd0ca4cd7cf0d0`.

That invocation stopped before the model: the complete request plus framing measured
**18,082 tokens**, exceeding its 18,000 allowance. It retained 35 successful Google
requests, zero model calls and **USD 0.964** reference usage. Its receipt is
`8f309d371e5618300f0a4cca481ddfb8f41f014a7824c4cf02dde72a7e029670`.
The parent prepared a separate correction under the current default approval:
input allowance **24,000**, unchanged medium/output/time settings, fresh independent
Google acquisition and no automatic retries. The corrected preparation is
`883ff5e705da277e08ba51c274e4445ddeb48690b82c7c14b6bc11a50c669c07`.
Including the first stop, its planning bound was 121 Google and USD 3.724, within the
existing stage envelope. The consumed first package was never rerun or overwritten.

The corrected invocation stopped with `Missing or duplicate identity proposal`.
The provider marked its response completed, but emitted only the Opera House requirement
subject (`r08`); all seven original V0 visit references were omitted. Required coverage
is eight decisions, returned coverage is one. The request schema has no array-count
bound; that observation does not establish why the model omitted the cases. Import
correctly rejected the incomplete material instead of fabricating UNKNOWNs or accepting
an incomplete scoring population. No new identity/route/quality report was produced.
Actual usage was 35 Google and one model, 13,144 input / 221 output tokens, zero retries,
reference **USD 0.965753425**. Receipt SHA256 is
`1497b24a088aef343f66955e0392a69d8470bd50f05687aa5d563df15c860b6c`.
No third invocation or opening assessment was sent after that stop.

With credentials cleared and DNS/TCP prohibited, both actual native `replay` commands
returned the expected exit 2 and reproduced their stopped reports exactly. Raw model
HTTP response and material agree; all **491** generation/preparation/execution files
remain unchanged. Original Input, V0-V2, prior V3 and unrelated `.gitignore` hashes agree.
Evaluator reference usage totals **USD 1.929753425**; whole-flow reference usage is
**USD 4.282437060**, with actual account billing unavailable.

Local historical identifiers are
`artifacts/sydney-v3-source-cli-live-20261009-r1/v3` and
`artifacts/sydney-v3-source-cli-preparation-20261009-r1` (`evaluator/run`,
`evaluator/run-input24k`, `partial-acceptance/acceptance.json`, and
`generation-offline-assessment.json`). They are ignored evidence, not published assets.
The incomplete decisions motivated a separately validated identity-coverage correction.
Its later bounded execution and complete native CLI outcomes are recorded in the
[identity acceptance history](../evaluation/intake-identity-usage.md#complete-v0-identity-coverage-acceptance-2026-10-09).
These original stopped packages retain their own incomplete status and source-bound
rejection; later success does not overwrite them.

## Bounded Repair search and selected-result integration (2026-10-13)

[Specification #139](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/139)
and implementation tickets #142-145 replaced the material-repeat stop and per-date
pace non-regression with checked exploration and a separate retained result. The
implementation starts at `b9a29e1` and reaches `a0b1114`, preserving the exploration
(`3aabcaa`), affected-date replan (`878bb41`), deterministic deletion (`426e3c3`),
integration (`26f1f2a`) and production/reader (`a0b1114`) commits. Corrections remain
separate commits, followed by a coherent contract and verification documentation update.

Controlled stage tests first exposed the blocked equal-deduction path
`3,2,3 -> 2,3,3 -> 2,2,3 -> 2,2,2`, then verified it and a temporarily worse path.
Separate regression cases exposed accumulated failed deletion alternatives and adoption
after a provider returned beyond the check deadline. The corrections isolate system
alternatives from pending model compensation and recheck the deadline before adoption.
Production/reader tests also exposed unknown dates blocking known-date pace progress,
discarded exploration being counted as final adoption, and a zero-round search being
read as a historical single round. Fixed original comparison dates, explicit selected
lineage and version-aware readers resolved those failures without changing independent
scoring. The actual V3 graph now exercises system deletion, local editing, replanning,
later failure or six-call exhaustion, selected-state fallback and one final Nearby phase.

Before full regression, the affected V3/native-reader suite passed 570 tests and the
installed controlled research CLI suite passed 13.
The full backend run at `a0b1114` completed in 2032.76 seconds with **4161 passed,
5 failed and 16 skipped**. One failure was a missing module-specific allowance for
the reader's pure offline `copy` import. Four were test-environment dependencies:
the PowerShell wrapper expected a local `.venv`, and three mocked launcher cases
expected an ignored `.env.tripworld` file. The wrapper also produced a GBK decoding
warning while its Python entry point was absent. A local environment junction resolved
the wrapper failure; its independent retest passed **1 in 6.33 seconds**, without warnings.

Independent Standards review found one nonblocking positional-objective concern;
Spec review exposed a final-status error not covered by the original suite. A
system-only `4 -> 3` exploration with an unchanged exact-count deduction of 100 could
return the original draft while reporting `ACCEPTED_PARTIAL`. Correction `6d41bbb`
binds the status to retained improvement, introduces a small named objective value
and adds the narrow import allowance. Its affected checks passed **225, 1 skipped
in 25.53 seconds**. Both review findings were independently rechecked and resolved;
the Spec reviewer also reran the new stage regression successfully.

Test-only correction `3709d0e` isolates the offline launchers from ignored local
configuration using temporary empty environment files and mocked child processes.
The three failures were reproduced before correction, then the launcher/runtime/network
checks passed **29 in 5.86 seconds**. Both reviewers confirmed that the production
guard and execution boundaries remain intact. Final integrated verification at `3709d0e`
passed **708 tests, 1 skipped in 209.28 seconds**, exit 0 and no warnings. It covers
the entire V3 test directory, five affected evaluator files, the installed controlled
research CLI, both launcher test files and the PowerShell case, including all five
original full-run failures. The remaining skip requires Windows symlink privileges.
The full backend suite was not repeated after correction; its original failures,
16 skips and warning remain recorded rather than replaced by an all-green full-run claim.
Final independent Standards and Spec rechecks have zero open findings. Backend/scripts
Ruff lint and all 39 changed Python format checks pass; unchanged global format
failures remain outside this scope. Test execution and final reviewers used
`gpt-6.1-sol` with `high` reasoning.

Earlier setup checks separated worktree failures from code regressions. Verified local
tokenizer cache copies and explicit test temporary directories restored tests blocked by
missing ignored assets or sandbox temporary-directory permissions. The shared editable CLI
loaded the original checkout, and its launcher failed inside the sandbox. Per-worktree
temporary virtual environments bound the installed CLI to the tested source while reusing
existing dependencies; offline installation used cached build dependencies. No project
configuration, shared environment or credentials were changed.

Local evidence identifiers are `.scratch/full-backend-139.log`,
`.scratch/powershell-regression-139.log` and `.scratch/final-backend-139.log`
in the retained integration worktree. These
ignored logs are historical evidence identifiers, not published dependencies.
Original case-01 evidence and its acceptance state are unchanged; post-refactor case
revalidation remains owned by [#140](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/140).
