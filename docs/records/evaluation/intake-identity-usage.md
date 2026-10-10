# Intake, identity, usage and material workflow history

This record synthesizes evaluator engineering from September 29 through October 9,
2026. Current interfaces and compatibility rules belong to the
[intake contract](../../contracts/0002-intake-identity-usage.md),
[artifact contract](../../contracts/0001-evaluation-artifacts.md) and
[requirement/schedule contract](../../contracts/0003-requirement-schedule.md).
Policy numbers and test results below describe their stated checkpoints; later
success does not replace earlier failures or turn historical rules into defaults.

The Sydney and Seoul runs are bounded engineering cases, not formal comparisons,
rankings or research conclusions. Agent review is distinguished from human review.
Local artifact paths identify historical evidence, not publicly downloadable assets.
Raw inputs, responses and receipts were preserved; this Markdown is explanatory history.

## Intake and independent capture foundations

### Source binding and ordinary-output intake

Tickets 01–03 established original-output intake, source-bound role/occupancy review,
identity evidence and inclusive usage capture. The September 29 review at
`364f91f` exposed missing provenance, overlap acceptance and five consequential
findings: a P1 and four P2 findings affecting null Repair, absent arrays treated as zero,
duplicate cached usage and source matching. The existing 91-pass/1-skip gate had
not covered them. Added boundary regressions produced 113 passes/1 skip.

Automatic occupancy association excludes overlapping candidates; explicit reviewed
association remains possible. Absent records mean unavailable evidence, not zero
activity, usage or failure. Capture is opt-in, and inclusive events are not additive
physical billing. Ticket 02's final reader/capture slices passed 51/1 skipped and
13 tests respectively. Three reader corrections used the same 113/1 checkpoint;
they are not additional independent test populations.

The initial identity path used human review for high-impact facts. Review found a
country bypass (Standards P1), search/Details contradictions (Spec P1), title conflicts
and malformed unhashable candidates that could abort a batch (P2). Twenty new
regressions brought the identity gate from 58/1 skipped to 78/1. Later model/program
policies below superseded this default while retaining historical replay.

### Immutable snapshot boundary

Ticket 04 at `1eb441f35` introduced evaluator-owned offline snapshots, injected
transport and manifest/raw-byte binding. UTC timestamp validation, an allowlisted
ledger and validation before directory creation prevent ambiguous or partial
publication. Cancelled or failed acquisitions are not automatically resumed.
The complete backend checkpoint passed 1,957 tests/10 skipped. Synthetic transport
proved boundaries, not live credential validity or independent factual truth.

<a id="rtpeval-transport-correction-acceptance"></a>

Transport responsibility was then aligned across versions: V0 retains model-authored
transport activities; V1–V3 derive application-owned Transfers. A contradictory
prompt clause was removed. The final shared backend checkpoint was 1,973/10 skipped;
an earlier interrupted run was not treated as successful verification.
The [transport smoke](../v0-v3/transport-responsibility-smoke.md) owns live coverage.

## Structural claims, prose and V0 transport

### Structured claims and title precedence

The October 2 design and October 3 acceptance separated structured claims from
free-text interpretation. Review corrected lost parsed claims and typed locality/city
contradictions. The pre-review full gate was 2,329/10 skipped; post-correction gates
were 124/1 and 502/1, with no replacement full run. The implementation/correction
bindings were `e1b89ae`, `898b3bc` and `b32e997`.

On October 4, source structure became authoritative for role, title and identity;
movement titles such as walking/exploring cannot silently override it. Projection
and density rules advanced to 3 and 2. The complete checkpoint passed 2,532/10
skipped at `9039466`.

Further prose corrections retained these distinctions:

- A structured title can veto identity; it does not create a different venue.
- Ambiguous free-time coffee visits retain possible-count bounds 2..3.
- Only the first title clause establishes mode; later notes cannot contaminate it.
- Endpoint notes are not a whitelist for accepting an estimated route.

The first full checkpoint passed 2,574/10 skipped. Review found a first-clause spacing
case; correction `62c7` produced the final 2,576/10 checkpoint. Intermediate focused
runs are not separate full acceptance results.

<a id="prose-publication-and-seoul-replay-2026-10-05"></a>

### Seoul replay under the revised prose and density rules

PR [#55](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/55) published the
corrected rules; its final documented gate was 2,576/10 rather than the stale 2,477.
Two network-blocked replays reused identical evidence, with zero new acquisition.
The source-linked observation IDs changed only to follow the new binding; raw bytes,
capture times and original requests did not. The 313 original materials and five
density inputs remained unchanged.

| Scope | Before | After | Primary visits by day | Mean daily deduction |
| --- | ---: | ---: | --- | ---: |
| V0 final | Unavailable | Unavailable | 2, 2, 2, 2 | 0 |
| V1 final | 85 | 85 | 2, 1, 1, 1 | 15 |
| V2 final | 90 | 90 | 2, 2, 1, 1 | 10 |
| V3 final | 100 | 100 | 2, 2, 2, 2 | 0 |
| V3 draft | 95 | 95 | 2, 2, 2, 1 | 5 |
| V3 final-primary | 100 | 100 | 2, 2, 2, 2 | 0 |

V0 still had eight known non-overlap checks and four unresolved units, four route
UNKNOWNs and one identity UNKNOWN; grounding was 7 PASS/1 UNKNOWN. This replay did
not establish a complete V0 score or acquire missing evidence. The
[density record](2026-10-04-daily-density.md) owns the scoring rationale.

<a id="v0-structured-transport-2026-10-05"></a>

### Explicit V0 declarations and their first live output

Issue #57 added a V0-only provider activity DTO mapped to optional shared Activity
transport data. Directed endpoint IDs refer to original activities; independent
provider identity remains a separate evaluator step. Missing/null shared objects
are omitted to preserve historical and V1–V3 wire compatibility. Ordinary prose
no longer substitutes for declared mode/endpoints. Review corrected an overly generic wrapped-serializer type; final
shared validation passed 2,632/10 skipped after the pre-review 2,631/10 checkpoint.
The corrected serializer/schema/API slice passed 85 tests at `72ff`.

The October 5 Seoul smoke made two Luna calls in 30.516 seconds, reporting
12,675 input / 5,611 output / 18,286 total tokens. Original input/result bindings
begin `07be` and `b9cf`; the [route record](routes.md#new-v0-route-plan-2026-10-05)
retains their full hashes and subsequent independent acquisition.

| Day | Directed activity endpoints | Mode | Model-estimated interval |
| --- | --- | --- | --- |
| 2026-10-07 | `day1-gyeongbokgung` to `day1-contemporary-history-museum` | WALK | 12:00-12:20 +09:00 |
| 2026-10-08 | `day2-bukchon` to `day2-insadong` | WALK | 12:00-12:25 +09:00 |
| 2026-10-09 | `day3-seoul-museum-history` to `day3-gwangjang-market` | TRANSIT | 12:00-12:35 +09:00 |
| 2026-10-10 | `day4-changdeokgung` to `day4-jongmyo` | WALK | 12:00-12:20 +09:00 |

All four legs bound, with no transport diagnostics. Empty raw mechanism arrays were
not proof of zero wire calls: this smoke lacked wire capture. Preflight provenance
fields showed readiness and zero preflight network, not actual execution totals.

## Cost accounting and usage evidence

<a id="offline-cost-acceptance-2026-10-05"></a>

### Seoul historical retail estimates

Issue #59 introduced offline reference-cost estimates at `ff2085`, not account bills.
The dated Luna Standard reference used input/cache-read/output rates 0.1/0.01/0.5;
cache-write/regional quantities were missing, and the saved contexts were under the
272k short-context threshold. The original saved attempts remain distinct:

| Saved attempt | Observed input/output tokens | OpenAI model estimate USD |
| --- | --- | --- |
| Original Seoul V0 | 12,562 / 5,815 | 0.0041637 |
| Original Seoul V1 | 64,151 / 8,195 | 0.0105126 |
| Original Seoul V2 | 65,406 / 10,806 | 0.0119436 |
| Original Seoul V3 | 95,078 / 14,696 | 0.0168558 |
| New structured-transport V0 | 12,675 / 5,611 | 0.004073 |

Actual Google SKUs were unavailable. Two explicit price scenarios illustrate the
uncertainty rather than inventing a single observed charge:

| Scenario | Per 1,000 search / Details / matrix-element rates | V1 observed subtotal USD | V2 observed subtotal USD | V3 observed subtotal USD | V3 Repair subset USD |
| --- | --- | --- | --- | --- | --- |
| Pro / Enterprise / Essentials | $32 / $20 / $5 | 2.0565126 | 2.0679436 | 2.0988558 | 0.093523 |
| Highest field tiers | $40 / $25 / $15 | 4.4405126 | 4.4719436 | 4.6668558 | 0.273523 |

Repair's separate scenario was USD 0.0935/0.2735. Oracle captures were evaluator
acquisition costs, not allocated to planner versions:

| Frozen oracle snapshot | Actual recorded sends | Requested matrix elements | Retail estimate USD |
| --- | --- | --- | --- |
| Identity | 36: 23 searches + 13 Details | 0 | 1.065 |
| Final evidence | 23: 16 Details + 7 matrix | 7 | 0.355 |
| Paired evidence | 23: 16 Details + 7 matrix | 7 | 0.355 |
| Observed oracle subtotal | 82 | 14 | **1.775** |

The oracle had 82 recorded sends: 23 Search, 13 identity Details, two 16-Details opening batches
and two seven-element route batches. Their subtotals were 1.065 + 0.355 + 0.355 =
USD 1.775. Do not count a shared capture again for each consuming version.

The pre-review full gate was 2,655/10 skipped. Corrections `6e74`/`0f6` addressed
SDK `tools=None` and blinded model/HTTP suppression; final affected validation was
80 and 288 tests. Built-in SDK tool observations were excluded from physical HTTP
counts in a subsequent 95-test slice. No new billable run was used for these checks.

### Sydney usage and generation evidence capture

On October 8, the user chose readable retail estimates over a complex account-price
spend guard. The earlier generation scenario proposed USD 11/12/14 and a separate
USD 6 evaluator allowance; these were planning reservations, not implemented caps.
The full historical scenarios were:

| Stage | Google allowance calculation | Other reference costs/reserve | Scenario total | Proposed allowance |
| --- | --- | --- | --- | --- |
| V1, one original generation | 13 Text Search, 3 Nearby, 60 Details, 8 review Details, 464 Matrix elements = 6.552 | ordinary model 0.30088520; Web tool 0.160; Web model/content reserve 3.00 | 10.01288520 | 11 |
| V2, one original generation | V1 plus RAG 4 Text Search and 30 Details = 7.280 | V1 model/Web amounts; one 2048-token embedding batch 0.00004096 | 10.74092616 | 12 |
| V3, one original generation | V2 plus Repair 6 search, 30 Details and 32 Matrix elements = 8.392 | ordinary + Repair model 0.51919120; Web amounts; two embedding sends 0.00008192 | 12.07127312 | 14 |
| Final evidence and V0 identity replay | at most 68 search, 136 Details and 60 Matrix elements = 5.496 | one V0 identity request 0.00412500 | 5.50012500 | 6 |
| Total | | | 38.32520948 | **43** |

The total 43 allowance covered a 38.32520948 scenario. It assumed four days,
C56/R28/K14 generation profiles and seven preferences conservatively bounded by eight.
Preference/extraction tokens, weather, HTML, Web and later identity/route acquisition
remained planning assumptions where runtime enforcement or billing was unavailable.
Atomic spend enforcement was Proposed and later deprioritized, not Implemented.

Usage capture (`43ca770`, `ef596e9`, correction `c444274`) retained environment precedence,
base/provider/RAG coverage and shared source ownership. A mixed mocked fixture had
three HTTP sends, two Web observations, one reuse, six matrix elements and a retail
subtotal of USD 0.0821715; incomplete coverage kept the complete total null. Final
full validation passed 3,062/10 skipped, after the pre-review 3,060/10 checkpoint.

Generation capture (`0e1e2e81aed997718cd1d83dd926206b31e59d8b`, reviewed correction) added credential-filtered raw HTTP/
trace evidence, a 10 MB bound, partial-array handling, finite float32 NPZ digests and
mechanism/usage indexes. Capture failures cannot overwrite successful planner output.
The capture clock excludes final index IO. Review found unprotected JSON/partial NPZ
and normal selected-list trace loss; final affected validation passed 103 tests.
The full 3,072/10 gate preceded these corrections and was not rerun afterward.

Offline V1–V3 preparation made zero network attempts and provider sends; variable
presence did not establish valid credentials or DB compatibility. Proposed generation
execution used 600-second invocation deadlines and zero operator retries. The
[actual execution](../v0-v3/development-pilots.md#sydney-v1-v3-generation-execution-2026-10-08)
stopped on V2 RAG connection timeout; separately approved
[host resumption](../v0-v3/development-pilots.md#sydney-generation-host-resumption-2026-10-08)
completed V2/V3 while retaining the degraded attempt and costs. Generation binding
alone did not qualify independent intake or factual quality.

## Identity policy evolution and bounded V0 executions

### From human review to version-owned identity

The policy transitions were deliberate design changes, not interchangeable labels:

| Stage | Default identity path | Historical consequence |
| --- | --- | --- |
| Initial Tickets 01/03 | Human-reviewed high-impact identity | Historical manual review remains replayable |
| #72, October 5 | Uniform one-call low-reasoning LLM judgment | Missing address assessments prevented adoption of older responses |
| October 6 decision / #75 | V0 model correspondence; V1–V3 deterministic API checks | Literal ID/name/address validation; unavailable facts remain UNKNOWN |
| #76 | Explicit address-presence and destination correspondence | Recognizing a venue does not repair a wrong original address |
| #83 | Separate version-owned requirement targets | Shared user meaning does not imply shared adopted target identity |
| October 8 | Physical association separate from grounding | Trusted physical IDs can support hours/routes while grounding remains FAIL |
| #88, October 9 | Physical occurrence matching for requirements | Rules 3 narrows false potential-count bounds; old rules replay unchanged |
| #92, October 9 | Google-supported address equivalence | Policy 4 explains full address with verified long/short component pairs |

Current technical definitions and supported legacy wire formats belong to the intake
contract. Historical uniform arrays, correspondence versions and canonical-only
requirement matching retain their original replay branches.

#72 implementation `9f1cd71` corrected short-text handling in `e8a`. An unrelated
retrieval failure interrupted broad acceptance; a later serial full run passed
2,807/10 skipped. Nine older saved responses lacked required address assessments
and therefore stayed UNKNOWN, not retrospectively adopted.

The next binary rule (`1c43007`) made wrong-address/different-venue claims FAIL with
no adoption. Its final full gate was 2,825/10 skipped after correcting a legacy class
collision. V0 canonical nulls could not be filled from another version's venue.

### First uniform-model request: response rejected

The #73 package (`abc2663`) bound eight V0 visits plus a requirement target, nine
candidates and 69 source files/61 protected raw files. Low reasoning, no tools,
`store=false`, 20k input plus 1,024 reserve, 4k output, 60 seconds and one request
were bounded by a USD 0.005 reference allowance (USD 0.004 maximum estimate).

One approved POST returned HTTP 200 in 7.175079 seconds but exited 1 at strict import.
The response used unsupported `case.candidates.display_name` citations rather than
`candidate.display_name`, and assessed a null target location as `different_precision`
rather than `not_supplied`. Reported usage was 14,403 input (14,400 cache-write,
three normal) / 967 output / 15,370 total: USD 0.0019238 base or 0.0022838 adjusted.
Raw response binding begins `d6f747af929131e4cbd6667e709cb4bb9a42deaacc2ee26f0daf3272b2d262c9`. All nine outcomes remained UNKNOWN because no
report was accepted; they were not nine independent model errors or PASS judgments.

### Versioned correspondence and schema correction

The October 6 decision limited model correspondence to V0. PR #80's earlier uniform
implementation did not itself implement that decision. #75 (`ffa36`, `a53`) added
`versioned_api_identity_1`: V1–V3 check literal ID/name/address, with contract failures
FAIL and unavailable observations UNKNOWN. Review corrected malformed typed targets
that aborted batches and misleading terminology. The full 2,862/10 gate preceded
those corrections; the final focused gate was 246 tests.

#76 (`0e5aba`, `4c98`) made address fields/enums explicit, distinguished absent claims
from missing candidate location, and rejected destination conflicts. The final full
backend passed 2,913/10 skipped. This did not repair the earlier unsupported raw response.

<a id="fresh-v0-smoke-preparation-2026-10-06"></a>
<a id="post-merge-v0-smoke-refresh-2026-10-06"></a>
<a id="v0-identity-smoke-execution-2026-10-06"></a>

### Fresh eight-visit response and its target gap

The #77 package bound eight primary V0 occurrences and nine candidates. Measured
input was 12,652 plus 1,024 reserve, under 16k; output was capped at 3k, one call,
USD 0.004 allowance. #78 changed source bindings but not the wire; refreshed #82
preparation retained the exact wire and protected historical acquisitions rather
than silently reusing a stale manifest.

One October 6 call completed in 5.965 seconds: 10,842 input (10,839 cache-write,
three normal) / 808 output / 11,650 total tokens. Reference estimates were
USD 0.001759175 base / 0.0019350925 regional, raw binding `dbf3ff340a86ee7a7b771736ab26759b8c29c103b8751bb1be1bac8e4180fe7d`. Eight primary
identities passed; the separate shared requirement target remained UNKNOWN. This
was `needs_evidence`, not complete nine-case acceptance.

<a id="version-owned-requirement-targets-2026-10-06"></a>

#83 separated each version's adopted target from the shared RequirementSpec meaning.
V0 correspondence 3 bound eight primary cases plus one target to 14 appearances;
report policy advanced to 2. Programmatic target search kept typed regional constraints
and pagination: saturation/conflicts remain UNKNOWN rather than inferred matches.
Review corrected falsey pages, paginated coordinates and city/district masking.
The full checkpoint had 2,971 passes/10 skips/two failures; a later separate V3 test
correction produced 2,983/10. The earlier failed checkpoint was not relabeled green.

<a id="v0-target-smoke-refresh-2026-10-06"></a>
<a id="v0-target-identity-smoke-execution-2026-10-06"></a>

### Input-limit refusal followed by complete target judgment

#85 preparation measured 17,135 tokens including reserve against a 16k bound and
refused before directory creation. A separately approved 18k input / 3k output,
USD 0.0042 package retained the same wire (`f829`) and sources. This was a changed
admission bound, not an automatic retry. Mock passing tests did not qualify the
previous oversized packet.

Broad validation initially had 2,948 passes/40 failures/10 skips: fixed route dates
had become past relative to the wall clock. The historical constant could reproduce
the failure; temporary-clock success did not fix tracked tests. A separate authorized
clock-test correction (`f449`) then passed 172 related cases and the fresh full
checkpoint of **2,998/10 skipped**.

The accepted package's preparation SHA-256 begins `425a0684faeaee51763d9dc9a00467557c266df29d5c049d41e361580a4a1993`; 108 source files and 113
raw files were protected. One actual call completed in 7.536 seconds: 14,917 input
(14,914 cache-write, three normal), 1,064 output including 203 reasoning, 15,981 total.
Retail estimates were USD 0.00239655 / 0.002636205 regional; raw binding `8225a4cb6623d2606f0e9f36c4871c714fcf6294fe0ac985542699b85a0c0d4f`.
Eight primary and one requirement identities passed, with no FAIL/UNKNOWN. Null
address claims remained `not_supplied`, not guessed addresses. The preceding target
UNKNOWN remains a distinct historical result.

<a id="sydney-v0-identity-smoke-2026-10-07"></a>

### Sydney V0: recognition with a retained address FAIL

The October 7 natural Sydney input/result bindings begin `1b3c`/`d8ca`; full output
hashes are retained in the four-version table below. Independent acquisition made
eight Search Pro requests, retained 13 candidates (six for Art Gallery) and used
one low-reasoning model call. Estimated packet size was 15,827 under 18k; output
limit was 3k. Reported model usage was 13,570 input / 1,021 output / 14,591 total,
including 264 reasoning and 13,567 cache-write tokens. Reference estimates were
USD 0.256 Google + 0.002206675 model = 0.258206675 against a 0.2602 allowance.

Six primary identities and the target passed; Australian Museum was FAIL. The model
judged original `College Street, Sydney` against `1 William Street` as `incorrect_claim`
and left canonical identity null despite recognizing the venue. An entrance/corner
interpretation might explain it, but no further diagnosis changed the judgment.
Powerhouse's identity PASS did not imply that its future indoor visit was open.
Raw/report bindings begin `05b`/`2db272e6b93ab4e7a4400d43a8a3b15876676a956fb70ece0c4429d84aadacde`; 134 source and 153 dependency files were bound.

### Physical association without repairing grounding

The October 8 change (`536de`, correction `b511`) separated validated physical
association from canonical grounding. A recognized venue can supply trusted coordinates
for independent opening/routes while its original address remains FAIL. Unresolved
association still blocks acquisition; generation/RAG facts cannot become evaluator facts.

Review found that controlled-human opening selectors still used null canonical identity;
a centralized opening-venue selector corrected them. The full 3,041/10 gate preceded
review; 1,108 evaluator tests/one skip passed afterward, without another full run.
Saved Sydney results remained six PASS/one FAIL with seven physical IDs and 98 unchanged
hashes. Explicit historical-association and earlier policies retained their old behavior.

## Sydney material qualification and four-final evaluation

### Material review and the first offline four-version intake

October 8 preparation found only the V0 natural run in the inspected local inventory;
that did not prove V1–V3 outputs were absent elsewhere. V0's two-call producer receipt
reported 40.625 seconds and 19,695 tokens with partial usage coverage, not independent
quality completion. Derived sidecars could not substitute for producer qualification.

After explicit user confirmation, human-reviewed RequirementSpec revision 2 retained
the complete natural input: four days in Sydney, two travelers, AUD 1600, relaxed pace,
and Sydney Opera House exactly once as the sole named hard obligation. Interests,
transport and spacing remained soft; no daily quota, fixed slot or indoor-visit
requirement was invented. Agent source review kept generic Haymarket food as committed
non-primary occupancy, not free time. Original 12:40–14:00 food occupancy, seven primary
visits, three bound WALK legs, one unbound transport and two unscheduled optional
references were retained. New intake/evidence digests invalidated old model binding.

The selected `sydney-natural` originals after successful host resumption were:

| Version | Selected original run | Result SHA-256 |
| --- | --- | --- |
| V0 | `sydney-natural-v0-20261007` | `d8ca6c8ac44aa2438f2efe65534b57488be81dbed217bc7d66626801f78431c7` |
| V1 | `sydney-v1-20261008-r1` | `e9046d62d719eeca95247a46873ce1cd475d89fa33775281a76ec9d5ab5f63b1` |
| V2 | `sydney-v2-20261008-r2` | `b261eeba55abafc258e1b87dd0871cf42d8c1abe3aa1caeabdcfb1044da2476d` |
| V3 | `sydney-v3-20261008-r2` | `a86d1335f197dea1cd23c4de02a4a483921ee1c630dd04ef2825f6000e1e7fe6` |

Input SHA-256:
`1b3c50ad9ce9c58a4caf047388f3c4131faa0cddb0ffff2467dd8b2f1593d6ba`.
Reviewed RequirementSpec SHA-256:
`76682ad7b594daf6bef437a755d96194b3ece9f1c103e8fd7bf6013933d13eaf`.
V2's retained degraded attempt was not selected. Native completion receipts attested
producer completion, not human factual review or independent quality acceptance.
Revision 2 of `sydney-natural-identity-development` passed native batch intake.
V3 optional projections were excluded from final-only scoring.

Three evaluator-owned snapshots passed raw-byte, request, capture-time and historical
ledger validation. The native identity plan had 33 distinct keys: 21 Search/12 Details.
Eleven exact keys reused historical observations; 22 lacked a match. Three reused
Details had opening-only masks, so identity names/addresses were not manufactured.
All 12 claimed-ID Details therefore needed identity refresh; 13 missing Search keys
remained in the plan, not substitutes for V1–V3 claimed-ID checks.

Independent Opera House search resolved the three version-owned V1–V3 targets PASS;
primary identities stayed UNKNOWN. V0's seven primary occurrences and target needed a
new correspondence request. The old Museum address FAIL remained historical; missing
current judgment was UNKNOWN. One exact historical requirement-target Details capture
was imported for native scoring with original hashes/times, not new acquisition:

| Version | Primary grounding UNKNOWN | Opening UNKNOWN | Routes UNKNOWN | Decidable non-overlap PASS |
| --- | ---: | ---: | ---: | ---: |
| V0 | 7 | 7 | 3 | 11 |
| V1 | 10 | 10 | 6 | 16 |
| V2 | 8 | 8 | 4 | 12 |
| V3 | 9 | 9 | 5 | 14 |

All exact-once requirements were UNKNOWN. Known intersections totaled zero seconds.
V0's ambiguous final-day transport left the non-overlap denominator unavailable despite
11 decidable PASS checks. Daily source-distinct counts were V0 2/2/2/1, V1 3/2/3/2,
V2 3/2/2/1 and V3 3/2/2/2, producing mean soft deductions 5/20/15/10. V1–V3 auxiliary
values 20 reflected verified non-overlap only; unavailable factual dimensions contributed
zero under the existing formula, not proof of poor quality or a valid ranking.

All six native CLI consumers reproduced JSON and exit codes in a second guarded offline
invocation: identity exited 3 for missing evidence, the other five exited 0. Network
attempts and new expenditure were zero. The 56 directly referenced originals, 541-file
preservation inventory and 286 frozen generation/source/config files were unchanged.
Usage remained partial/unavailable where warranted. Evidence identifier:
`artifacts/sydney-four-version-evaluator-20261008-r2`.

### Formal final-only execution and replay implementation

Issue [#87](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/87) integrated
`prepare_run`, `execute_run`, `replay_run` and actual CLI with independent Search/Details,
one V0 correspondence call, version-owned identities, snapshot coordinates, hours,
directed routes and native scoring. The complete current-policy V0 case set became
the binding unit; wrapper changes can remap unchanged cases, while relevant claims,
candidates, raw provenance or RequirementSpec changes reject import. Historical/result-1
bindings keep exact old matching. Original planner outputs are never regenerated.

Known-time V0 transport keeps its own occupancy even when endpoints cannot bind;
invalid clocks stay UNKNOWN, established intersections FAIL, and route/mode uncertainty
remains visible. Schedule/routes rules advanced to 2. Earlier reports need their
original rule/code revision for exact reproduction.

Implementation at `affc639`, `cdd2fa3`, `276358c` corrected detached-response replay,
model transport failures escaping final receipts and discarded stopped-attempt cost.
Replay verifies HTTP/model/times/usage and regenerated route preparation before comparing
reports. The pre-review full backend passed 3,098/10 skipped. Review correction
`7fe0c52` added tokenizer preflight/runtime-error capture, metadata-only usage projection,
density UNKNOWN units and identity acquisition-failure links. The final 23 affected
public-boundary tests passed; the full gate predates this correction.

Mocked CLI/subprocess checks covered success, failed HTTP, dependency failure, cost
exhaustion, source drift, deadlines, consumed directories and detached response bytes.
WALK stayed time-independent, DRIVE `TRAFFIC_UNAWARE`, and TRANSIT preserved direction
and original departure. Synthetic tokenization tested structure, not real request size.

### Fresh four-original execution: complete processing, unresolved facts

The approved October 9 package digest was
`2debadce52a9278e7efad68cfe0fda955a7fac8ec9abbe33a6420269232a19fa`, operational code
`7fe0c52`, source HEAD `925bd0a19899ed7b16a6669db6a925e91b9b045a`.
Limits were 86 Google sends, one low-reasoning V0 Luna call, 18k input sizing/3k output,
120-second requests/900-second total, zero retries and USD 2 reference allowance.
The prospective retail scenario was USD 1.705750, not an invoice cap.

One formal execution ran 02:03:06.080827–02:03:34.221506 Australia/Sydney:
28.140679 seconds, exit 0, empty stderr. Actual sends were 64 Google: 21 Search,
28 Details, 15 one-cell directed matrices, plus one V0 model call. All 65 HTTP receipts
were 200/completed. Identity used 33 Google sends; the fresh second phase used 16
Details/15 matrices. No retry, historical substitution or planner regeneration occurred.

Model usage was 12,411 input / 979 output / 13,390 total, zero cached and 12,408
cache-write input. Dated retail estimate: USD 1.3090408, comprising 0.672 Search,
0.560 Details, 0.075 matrices and 0.0020408 model. Account billing remained null;
credits, discounts, free tiers and taxes were excluded. The frozen price book cited
[Google's global table](https://developers.google.com/maps/billing-and-pricing/pricing)
and [Luna model rates](https://developers.openai.com/api/docs/models/gpt-6-luna).
Those are dated historical references, not a fresh price verification.

A separate actual CLI replay blocked DNS/socket access, exited 0 with zero attempts,
and reconstructed the saved report exactly. It verified 205 receipt-covered files,
raw hashes, model/timing/usage linkage and newly derived route preparation. Original
Input, RequirementSpec and all four output hashes were unchanged. Report SHA-256:
`09272f235cadc20aeb94f4c6a4f5945f35a77faaf89637611beb422695e0b459`.
Evidence identifier: `artifacts/sydney-fresh-evaluation-preparation-20261009-r1/run`.

Processing/acquisition were complete with no acquisition failure; evidence remained
unresolved and identity `needs_evidence`. Native counts were PASS / FAIL / UNKNOWN:

| Version | Requirements | Grounding | Non-overlap | Opening | Routes | Mean density penalty | Overall score |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| V0 | 1 / 0 / 0 | 7 / 0 / 0 | 12 / 0 / 0 | 5 / 0 / 2 | 3 / 0 / 0 | 5 | 89.2857 |
| V1 | 0 / 0 / 1 | 8 / 2 / 0 | 16 / 0 / 0 | 6 / 0 / 4 | 6 / 0 / 0 | 20 | 48.0000 |
| V2 | 1 / 0 / 0 | 8 / 0 / 0 | 12 / 0 / 0 | 4 / 0 / 4 | 4 / 0 / 0 | 15 | 75.0000 |
| V3 | 1 / 0 / 0 | 9 / 0 / 0 | 14 / 0 / 0 | 5 / 0 / 4 | 5 / 0 / 0 | 10 | 81.1111 |

Optional V3 projections, human/controlled-Repair/official-audit tracks were excluded.
All retained UNKNOWNs were checked against the actual evidence:

| Item | Version | Date/scope | Original venue or obligation | Retained cause |
| --- | --- | --- | --- | --- |
| 1 | V1 | Whole trip | Sydney Opera House exactly once | `count`: bounds 1..3; one confirmed and two unadopted potential visits |
| 2 | V0 | 2026-10-14 | Sydney Opera House | `hours_missing` |
| 3 | V0 | 2026-10-17 | Powerhouse Museum | `hours_missing`; API also reports `CLOSED_TEMPORARILY` |
| 4 | V1 | 2026-10-14 | Sydney Opera House | `hours_missing` |
| 5 | V1 | 2026-10-14 | Sydney Harbour Bridge | `hours_missing` |
| 6 | V1 | 2026-10-15 | Darling Harbour | `hours_missing` |
| 7 | V1 | 2026-10-17 | Bondi Beach | `hours_missing` |
| 8 | V2 | 2026-10-14 | Sydney Opera House | `hours_missing` |
| 9 | V2 | 2026-10-14 | Sydney Harbour Bridge | `hours_missing` |
| 10 | V2 | 2026-10-14 | The Rocks | `hours_missing` |
| 11 | V2 | 2026-10-16 | Darling Harbour | `hours_missing` |
| 12 | V3 | 2026-10-14 | Sydney Opera House | `hours_missing` |
| 13 | V3 | 2026-10-14 | Sydney Harbour Bridge | `hours_missing` |
| 14 | V3 | 2026-10-14 | The Rocks | `hours_missing` |
| 15 | V3 | 2026-10-17 | Bondi Beach | `hours_missing` |

All 14 opening requests returned HTTP 200 while omitting both current and regular hours.
Names did not prove exterior access. Powerhouse's undated `CLOSED_TEMPORARILY` was not
turned into future closure or feasibility. The V1 1..3 count was policy-induced: two
address-FAIL visits had verified Harbour Bridge/Maritime Museum associations but no
canonical adoption, so canonical-only matching treated them as possible Opera House
visits. It was not evidence of three real Opera House visits.

The two literal-address grounding FAILs were:

| Version / original venue | Submitted address | New API formatted address |
| --- | --- | --- |
| V1 / Sydney Harbour Bridge | Sydney Harbour Bridge, Sydney NSW, Australia | Sydney Hbr Brg, Sydney NSW, Australia |
| V1 / Australian National Maritime Museum | 2 Murray St, Darling Harbour, Sydney NSW 2000, Australia | 2 Murray St, Darling Hbr, Sydney NSW 2000, Australia |

Abbreviation differences were not proof of different physical locations. No post-hoc
normalization or fallback changed the native results. Six daily-density FAILs remained
soft-profile deductions, not added user obligations:

| Version | Date | Primary visit count | Daily penalty |
| --- | --- | ---: | ---: |
| V0 | 2026-10-17 | 1 | 20 |
| V1 | 2026-10-14 | 3 | 40 |
| V1 | 2026-10-16 | 3 | 40 |
| V2 | 2026-10-14 | 3 | 40 |
| V2 | 2026-10-17 | 1 | 20 |
| V3 | 2026-10-14 | 3 | 40 |

No requirement, non-overlap, opening or route FAIL occurred. Completion fulfilled the
engineering workflow; address equivalence, count association, business status and
public-access semantics remained explicit limitations.

<a id="requirement-physical-association-correction-2026-10-09"></a>

### Separate requirement association recalculation

Issue [#88](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/88), implementation
`2f9dd6f`, changed requirement/schedule rules to 3. After complete source-bound identity
replay, occurrence matching can use verified physical association; targets still require
version-owned adopted canonical identity. Grounding failures, dates, roles and time
uncertainty remain intact. Historical policies keep canonical-only matching.

Public scorer/CLI tests covered counts, dates, exclusions, fixed times, same/different
venues, V0 correspondence, missing/conflicting evidence and forged associations.
The final full backend gate passed 3,112/10 skipped; both review axes had zero findings.

Guarded offline requirement/quality CLI recalculation made zero network attempts and
preserved all 205 originals/receipts. V1's exact-once bounds became 1..1/PASS and score
68.0000 rather than 48.0000, while grounding stayed 8 PASS/2 FAIL. The 14 opening
UNKNOWNs and all other dimensions stayed unchanged. Other scores remained V0 89.2857,
V2 75.0000, V3 81.1111. This was a separate result, not replacement acquisition:

| Material | SHA-256 |
| --- | --- |
| Original preparation | `2debadce52a9278e7efad68cfe0fda955a7fac8ec9abbe33a6420269232a19fa` |
| Original report, unchanged | `09272f235cadc20aeb94f4c6a4f5945f35a77faaf89637611beb422695e0b459` |
| Original receipt, unchanged | `ca5852385f6fcdeb1279afbb25ddfdc8da8d11a64514836b88bf824406bae0e1` |
| Corrected requirements | `e7011d0697813bc1d564b905a453112121d552135eef16ad887e00eed1377ebc` |
| Corrected quality | `664479d3fc9a4e8af6b6c09fd03815038f967ea42ce77e503be920f5a10f700a` |
| Current requirement scorer | `a4b12481969d8a156e26fa7111232e70d37a1d245e09bdef6f8490d656a83d6b` |

An isolated original-rules replay loaded trusted fixed-base scorer source without
checking out the repository and reproduced the original rules-2 report, exit 0 with
zero network. Corrected output identifier:
`artifacts/sydney-requirement-association-recalculation-20261009-r1`.
The [opening proposal](opening.md#opening-access-boundary-proposal-2026-10-09)
remained advice, not a scoring change or collection authorization.

<a id="google-address-equivalence-acceptance-2026-10-09"></a>

### Google-supported equivalence and identity-only recalculation

Issue [#92](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/92), `c77fbed` /
correction `590ac9d`, introduced `versioned_api_identity_4`. Verified Google long/short
component pairs must explain the complete original address after provenance/ID/name
checks. Unsupported or conflicting differences FAIL; unavailable independent observations
remain uncertain. V0 correspondence and historical policies 1–3 are unchanged.

Review rejected cross-linked alias endpoints that could excuse a different street and
retained a unique eligible requirement candidate's address FAIL rather than masking it
as search UNKNOWN. Multiple candidates remain independently uncertain. The full backend
passed 3,195/10 skipped at `32be42d`, before review correction. Final address/public-CLI
and V3 scope passed 483 tests at `0a4a96b`; complete evaluator regression then passed
1,248/1 skipped at that revision. The separate V3 pace correction belongs to its
[development record](../v0-v3/v3-development.md#soft-pace-repair-acceptance-2026-10-09).

Zero-network replay reconstructed policy 3 exactly, then separately applied policy 4:

| Original venue | Google-supported pair | Result |
| --- | --- | --- |
| Sydney Harbour Bridge | `Sydney Harbour Bridge` / `Sydney Hbr Brg` | PASS |
| Australian National Maritime Museum | `Darling Harbour` / `Darling Hbr` | PASS |

Only these two V1 grounding/canonical outcomes changed FAIL→PASS. The #91 accepted
full report SHA-256 stayed
`8992422ca3953fd1d90f059674da68e1f18e1730f5816157a876a8b7d7c1c83b`; receipt stayed
`5ea846bccf2ededed1275bbc3690b36659c46c2a262a32b7fbabb165a42e5c7c`.
All original outputs stayed unchanged. This was identity-only recalculation, not a
newly bound four-version quality report. Local receipt identifier:
`artifacts/address-pace-tests/retained-address-check.json`.

<a id="complete-v0-identity-coverage-acceptance-2026-10-09"></a>

### Complete V0 coverage: stopped attempts and final native acceptance

The preceding source-protected V3 execution received only one of eight required V0
judgments and omitted all seven visits. Strict import stopped; the original response
and stopped reports remain intact in the
[source-protected execution record](../v0-v3/v3-development.md#source-protected-v3-cli-execution-2026-10-09).
The separately authorized identity-coverage implementation
`779dc8aaef8f88c6801e0391344fc639cce2a586` replaced the
arbitrary-length current array with a strict decisions object requiring every owned
short ID. Explicit UNKNOWN is allowed; missing/foreign/duplicate cases, old current-wire
arrays and foreign candidates are rejected. Historical uniform/legacy arrays keep their
original branches. Provider bytes stay unchanged during internal conversion.

Final affected CLI/source/replay validation passed 204 tests in 136.27 seconds;
full backend passed 3,231/10 skipped in 672.12 seconds. Both review axes had zero findings.
Original V0–V2 and reviewed input/spec were retained. The source-protected new V3 hash is
`ecd6d368b4467fc3a49995dc925d983475fa14cf08beb9cdd4870e7d69ea7e6f`.
Batch revision 4 preserved source-linked role/occupancy/routes/density reviews.

The initial package digest was
`2979edd919a3ac0572d33385a47c83ace4768bd8fb7d3d918ad12989fa771da3`.
Its 15,606-token offline preview was below the 24k allowance; preview facts were not
fresh independent evidence. Limits: 86 Google, one medium Luna identity call,
24k input/3k output, 120-second request/900-second overall, USD 2.76 reference,
zero retries. The separate missing-hours stage allowed zero Google, one medium model,
32k input/8k output and USD 0.05.

| Attempt | Outcome | Actual usage | Reference USD | Closed receipt SHA-256 |
| --- | --- | --- | ---: | --- |
| Initial strict identity | Exit 2; 34.326 s, provider incomplete at output cap | 35 Google; one model; 15,132 input/3,000 output, including 2,346 reasoning | 0.967391425 | `d71e8f9621dad7fe91f690070cf80f4bbc984283a13ee7ffb19bf9bbf3f3f2e8` |
| Separate output-8k package | Exit 0; 42.969 s, all eight owned decisions | 67 Google; one model; 12,635 input/2,640 output, including 1,552 reasoning | 1.3818993 | `bb21c07cd07c3d8d6fb0d9592c653d5d6e739530ec7c590040dfeb9a4d423040` |
| Missing-hours assessment | Exit 0; 25.468 s | Zero Google; one model; 14,905 input/2,364 output, including 807 reasoning | 0.00304505 | `76e09abfa9d95b93e4b9bf4e04280295d42dfb087a9751ef07a9f6c89dca2ce2` |

The output-8k correction changed only the output allowance, retained medium reasoning,
24k input, code/sources/scoring/deadlines and required fresh acquisition in a separate
package. Its preview measured 17,564 input tokens; reservation USD 2.759 stayed within
2.76. Including the first stop, the bound was 121 Google/USD 3.727391425, below 5.50.
Preparation digest:
`a0a86549b778aba37c576d59536d0742fbc77fd5e3123bae93d38eb37e510774`.
No truncated material was accepted or automatically resumed.

The opening packet held 13 cases/16,638 framed input tokens and a USD 0.008 reservation,
digest `959445ff374d1cd0da96e5d77baa30b8e9844a281d89bb6cf7156c47c8da44db`.
Twelve ordinary outdoor/landmark cases passed as `llm_access_reasonableness`, not
API-certified opening hours. V0 Powerhouse indoor admission remained UNKNOWN; missing
hours and undated temporary closure did not prove future opening or closure.

Actual `replay`, `replay-opening` and manifest-based quality CLI ran with credentials
removed and DNS/TCP blocked: exit 0 and byte-identical repeated quality JSON. All 832
protected generation/preparation/execution files stayed unchanged. Three earlier stopped
attempts retained exit 2 and closed receipts. Final native report SHA-256:
`b45d2b5af5d817a73420a9bf06f44b589bb68ee69976a794177c911acbe5df7d`.

| Version | Overall score | Grounding FAIL | Opening UNKNOWN | Mean soft pace deduction |
| --- | ---: | ---: | ---: | ---: |
| V0 | 89.2857 | 1 | 1 | 5 |
| V1 | 80.0000 | 0 | 0 | 20 |
| V2 | 85.0000 | 0 | 0 | 15 |
| V3 | 100.0000 | 0 | 0 | 0 |

All Opera House exact-once requirements passed. V0 retained the Museum address FAIL
and `day4_powerhouse` UNKNOWN for indoor admission on October 17, 10:00–12:15 Sydney:
`hours_missing` / `llm_access_reasonableness_unknown`, despite successful HTTP acquisition.
Five soft pace deductions remained: V0 October 17 count 1/20 points; V1 October 14/16
count 3/40 each; V2 October 14 count 3/40 and October 17 count 1/20. New V3 already had
zero initial/final deduction and no Repair round, so this did not prove Repair improvement.

This evaluator task used 102 Google sends, three model calls, zero automatic retries and
USD 2.352335775 reference cost. Including two preceding stopped evaluator packages since
source-protected V3 generation, saved execution costs totaled USD 6.634772835.
Actual billing stayed unavailable. Evidence identifier:
`artifacts/sydney-v3-identity-coverage-evaluator-20261009-r1`, including stopped/successful
receipts and `final-acceptance` factual/unknown/pace inventories.

PR [#103](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/103) owns delivery of
accepted #85–#94 work, excluding the then-pending unified CLI #95–#102. Its review found
a stale operational policy-3 reference and a false grounding-FAIL coordinate prohibition;
documentation was corrected to policy 4/verified physical association without changing
scoring or retained reports. Published PR/Issues own lifecycle state.

## Installed CLI and reviewed material workflow

<a id="installed-rtpeval-validation-acceptance-2026-10-09"></a>

### Installed validation and one-step evaluation

Issue [#96](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/96) introduced
editable installation through bundled `uv_build` and the lazy `rtpeval` entry under
`backend/cli/`, outside preparation-bound evaluator sources. Dependency versions and
native scoring were unchanged. Validation delegates to native intake, preserving JSON,
accepted/correction statuses and exits. Review corrected leaf help/error usage to
`rtpeval validate` with parser-name restoration in `finally`.

The affected installed/native gate passed 188/1 skipped. Final corrected CLI gate:
20 tests in 12.66 seconds at `b8291fe`. The full backend 3,251/10 checkpoint began at
implementation `e418d94` before that help-only correction; the separate CLI gate tested
the final help assertions. Negative controls confirmed caught DNS/TCP, credential and
runtime attempts fail the offline harness. Editable metadata/lock/help were verified;
standalone distribution and actual paid execution were not tested.

<a id="one-step-rtpeval-evaluation-acceptance-2026-10-09"></a>

Issue [#97](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/97), implementation
`4044dab`, added one-step native prepare/execute with internal integrity-digest transfer,
plus explicit offline prepare/replay and exact-digest prepared execution. The digest is
integrity binding, not authorization. Consumed failed packages cannot resume automatically;
no implicit opening supplement or extra probe was added. Empty selectors are rejected
before evaluator initialization. Native planners/evaluators and dependency versions
were unchanged.

Public tests covered successful/partial acquisition, model connection failure, cost
refusal/deadline, reviewed contexts, missing dependencies/credentials, source drift,
tampering and consumed directories. One representative fixture had five Google and one
medium V0 model send, zero retries. Guarded installed/legacy replay retained exact native
reports, hashes and exits; processing success did not remove FAIL/UNKNOWN/unavailable
quality. Synthetic tokenization verified structure, not real payload size.

The final affected gate passed 1,327/1 skipped, including 42 new evaluate CLI tests;
full backend passed 3,293/10 skipped in 820.87 seconds on the final implementation.
Both implementation review axes had zero findings. Documentation review corrected the
runnable `uv run rtpeval` prefix; final rechecks were clear. #96/#97 delivery reused
these unchanged-source gates; Issues/PR own publication rather than this record's old
local-only state. Local evidence identifiers: `artifacts/rtpeval-96` and
`artifacts/rtpeval-97`. No frontend/standalone-distribution validation was implied.

<a id="unified-rtpeval-material-workflow-acceptance-2026-10-09"></a>

### Collection, external review lineage and selected generation

Issues #98–#102 under #95 integrated material collection, tool adapters, reviewed
finalization, selected generation/registration and the installed public workflow.
PR [#105](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/105) owns delivery.
Implementation was reviewed from `93ab3ba24049dd5321fea1c755e354f054c0625e` through
`c1280a1d3bde034809d2cb813975c5a571d2354d`. The four original runners and evaluator
hash-bound sources remained unchanged.

The consequential corrections were:

- Collection retained explicit missing/blocked attempts, verified original/copied
  hash/path/selection relationships and reconstructed staging through native intake.
- Finalization retained authored pending drafts, reviewer inputs and separate final
  outputs. Exact execution/transcript bindings rejected reuse after envelope edits;
  configuration comparison preserved actual additional options. Correction `74a8d23`
  retained transcript subdirectory layout while resolving embedded snapshot references
  against verified execution material.
- Registration qualified actual returned Planner observations under `selected_workflow_1`
  without replacing the operator's policy. Normal V3 partial/rejected/skipped outcomes
  could qualify; interruption, failed required retrieval or failed new usage capture
  remained blocked. Correction `4919591` reported malformed selection as registration
  failure without losing successful Planner status.
- Tools preserved native wire/status/hash/time differences. The offline guard retained
  SDK types while blocking construction/credentials and allowed only Windows asyncio's
  local socketpair; caught external attempts still failed the harness.

Representative child gates were collection 187/1 skipped, finalization/core 71,
merged generation 167 before correction and 33 after it, and integrated tool/core/
collection 111. They overlap and describe different checkpoints, not a summed final gate.

The installed public integration collected originals into `pending_review`, attached
synthetic external-reviewed lineage, finalized through native intake, validated all four
versions, ran MockTransport one-step evaluation and replayed exact saved reports.
The fixture made five Google/one V0 model send, zero retries and no implicit opening
supplement. Processing/acquisition completed with unresolved evidence and explicit
unavailable producer usage. Exact author/draft/reviewer/execution/transcript bytes were
preserved. Selected injected V3 partial Repair qualified and re-collected its exact
capture without inventing RequirementSpec or missing versions.

The final public gate passed three tests in 25.64 seconds at `c268859`; integrated
native intake/evaluation/planner-usage passed 176/1 skipped. Synthetic transcripts prove
recorded lineage, not authenticity or semantic quality of a real external review.
Those implementation gates did not run actual external author/reviewer sessions.
Operational ownership is now split
between concise root commands, detailed `backend/evaluation/README.md` parameters and
current intake lineage rules; the CLI does not dispatch external authors/reviewers.

### Combined verification and evidence limits

Initial full fixed-base Standards/Spec reviews had zero implementation findings.
Final documentation review found a stale #97 current checkpoint in `PROJECT.md`;
separate correction `e7fa98e` made its two sections refer to the same dated gate.
Both correction rechecks had zero remaining findings. Thirteen changed Python files
passed Ruff lint/format; no configured mypy/pyright or frontend gate was claimed.

A complete backend invocation from the wrong parent directory failed: 52 failures,
3,418 passes, 11 skips and two GBK reader warnings. Missing relative config/runner/
script paths and a cwd-relative inventory explained the failed gate; it was not
successful validation or a demonstrated source defect. Without changing code/tests/
dependencies, rerunning from the repository root passed **3,471 tests/10 skipped in
673.89 seconds** on unchanged `c1280a1`. Nine skips were opt-in PostgreSQL cases and
one required host symlink privileges. Earlier #97 gates were not substituted for it.

Evidence identifiers include `artifacts/rtpeval-95/102-native-gate.xml`,
`102-stable-public.xml`, and the parent artifact inventory's `final-95.xml` /
`final-root.xml`. Local diagnostics remain local; the public facts and limitations are
recorded here. Those gates established synthetic/offline acceptance; subsequent
real-material acceptance has a separate source and evidence scope.

The authorized 2026-10-10 Sydney acceptance used unchanged implementation `3ae30b7`
with only the pre-existing `.gitignore` edit present. It selected the saved runs
`sydney-natural-v0-20261007`, `sydney-v1-20261008-r1`, `sydney-v2-20261008-r2` and
`sydney-v3-source-cli-20261009-r1` against original input SHA-256
`1b3c50ad9ce9c58a4caf047388f3c4131faa0cddb0ffff2467dd8b2f1593d6ba`.
Completion receipts and observed stages supported generation for all versions,
completed V2/V3 retrieval and completed V3 validation; V3 Repair was not applicable.
Independent Codex `gpt-6.1-sol`/high author and reviewer instances received fresh,
isolated contexts with the complete request and no Planner/scoring evidence.
The reviewer retained the draft semantics with no findings. Retained transcripts
contain the actual dispatch and structured final response with normalized JSON
whitespace; private reasoning and intermediate tool messages were not exported.

Public `collect`, `attach-requirements`, `finalize` and `validate` accepted the
source-bound directory without hand-editing its manifest. Offline preparation
passed before one public `evaluate execute` invocation. Fresh Google acquisition
and automatic processing completed with 22 Search, 30 Details and 15 Matrix sends,
one medium V0 model request and zero retries. Model usage was 15,160 input and
1,804 output tokens. Reference cost was USD 1.381796925 under the USD 3 allowance;
OpenAI retail model pricing was an explicit Azure proxy, not an account invoice.
Limits were 86 Google sends, one model send, 24,000/8,000 input/output tokens,
120 seconds per request and 900 seconds overall. All 1,530 frozen material files
and 73 bound implementation files remained unchanged. A separate replay process
denied socket connections and DNS resolution, removed evaluator credentials,
made zero network attempts and reproduced the report exactly while preserving
all 216 saved evaluation files and 758 bound original files.

The original report retains 48 UNKNOWN inventory entries: two requirement/schedule,
13 opening, 17 route and 16 daily-density entries. It omitted activity-role,
occupancy, route and density reviews and supplemental opening judgments. The local
evidence identifier is `artifacts/rtpeval-real-e2e-20261010-r1`, including the accepted
`finalized/manifest.json`, execution report/receipt and `replay-verification.json`.
This acceptance covers preserved real material through finalization, fresh independent
evaluation and replay; it does not exercise new Planner generation or establish
comparative research.

The authorized offline follow-up on 2026-10-10 at `6dfa77b`, with the same pre-existing
`.gitignore` edit, reviewed the complete original Input and the V0 Haymarket activity.
The generic food block is non-primary but occupies its submitted interval; walking
and public transport are soft preferences without a hard mode restriction; relaxed
pace has no explicit daily count or dated exception. New agent review envelopes bind
these decisions to exact source hashes and actual review time, without human confirmation.
A separate derived manifest adds the activity review. Native identity replay preserves
every identity source and association using the original captured V0 model response;
derived snapshots reuse exact request keys, response bytes and observation timestamps.
Their ledgers retain historical attempts and do not describe additional sends.

The original execution replay matched. Two native quality CLI runs over the reviewed
material completed with identical reports under socket/DNS denial. All 3,666 checked
original/current and preceding-case evidence files remained unchanged. Of the 48 original
UNKNOWN entries, 35 became decidable: 17 route PASS, one required-visit count PASS,
11 daily-density PASS, five daily-density FAIL and one available occupancy denominator.
The 13 remaining entries are opening checks; both inspected independent snapshots lack
usable hours for them. The preceding access-model material contains 12 PASS and one
UNKNOWN but its import correctly rejects stale/foreign packet bindings. Those decisions
were not transplanted. A fresh 13-case opening packet was prepared without execution.

That offline follow-up used zero provider/model sends and incurred no additional API
cost. Its local evidence identifier is `artifacts/rtpeval-offline-context-20261010-r1`,
including source-linked reviews, `quality-report.json`, `verification.json` and
`resolution-summary.json`.

The subsequently approved 2026-10-10 access assessment at `d8b14a9`, with only the
same `.gitignore` edit, bound a fresh packet to that reviewed material. A reviewed
offline recalculation is not a native paid-run parent, so the supported independently
captured-material import route preserved its source bindings. The task-local adapter
used native `EvaluationTransport` for one actual Azure Responses request, retained raw
HTTP/material and usage, and completed native opening import and quality CLIs. The
execution child used `gpt-6.1-sol`/medium; the requested API model was `gpt-6-luna`/medium.
Limits were zero Google sends, one model send, zero retries, 24,000/8,000 input/output
tokens, 120 seconds per request, 900 seconds overall and USD 0.10 incremental reference
cost. Actual usage was 14,905 input and 2,796 output tokens; incremental reference cost
was USD 0.00326105, bringing this acceptance's total to USD 1.385057975. Actual account
billing remains unavailable; model prices are an explicit OpenAI retail proxy for Azure.

The 13 model decisions were 12 PASS under the public-landmark/public-area access policy
and one UNKNOWN for V0 Powerhouse Museum indoor admission. No dated admission evidence
was available; undated temporary closure does not prove future closure. The original
48 UNKNOWN entries are now one in the separately saved completed quality report.
Access PASS is a model reasonableness assessment, not supplied opening hours. Socket/DNS-
blocked native opening and quality replay matched exactly with zero network attempts;
factual hours, intervals and all non-opening dimensions remained unchanged. All 4,527
frozen source files, 74 implementation/adapter files and 11 captured receipt files passed
hash checks. Report usage and final saved usage differ only in their closing timestamp;
both original snapshots and their identical token/provider ledgers are retained.
Local evidence is `artifacts/rtpeval-opening-access-20261010-r1`, including the actual
`execution/model-result.json`, full native quality report, receipt,
`replay-verification.json` and `acceptance-summary.json`. This completes the bounded
real-material acceptance with one explicit uncertainty; original executions and their
source material remain unchanged. Another identical Google query has no demonstrated
coverage benefit; museum admission requires applicable authoritative evidence.
