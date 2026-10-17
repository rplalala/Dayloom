# V3 paired diagnostic development

Ticket [10 / #22](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/22),
2026-10-03. Status: Implemented, offline Validated and independently reviewed.
The [paired contract](../../contracts/0005-quality-human-review.md#v3-pairs) owns current
wire and semantics. The accepted [source-driven preflight](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/22#issuecomment-5955706453)
separated occurrence lineage, independently established venue identity and compliance.

## Source lineage and population accounting

The immutable preparation/report/CLI reads exact same-run V3 draft/final-primary sources,
paired snapshots and public scorers. Validated adopted rounds/components and free-time
fragments establish edit lineage, including repeated visits, moves, replacement and
splits. Rejected, pending and rolled-back components do not count as adopted edits.
Producer sorting, source-ledger name normalization and refreshed transfers are reconciled
without changing source records. Missing/inconsistent lineage retains local diagnostics;
aggregate deltas can remain available when particular correspondence is unresolved.

Global canonical uniqueness replaced greedy leftover matching that falsely resolved
repeated venues. Same-slot replacement with UNKNOWN venue identity initially certified
a protection fix; correction requires independently established same-venue continuity.
A valid source lineage never makes an internal Repair PASS independent truth.

The two-stage union mask uses exact rational signed deltas, retains unavailable totals,
raw checks, coverage, losses and replacements, and remains separate from the four-final
mask. Shared arithmetic was extracted without changing Ticket 08's final-only policy.

## Review corrections and causal attribution

| Finding | Correction |
| --- | --- |
| Multi-occurrence manual additions/removals were counted once per relation. | Count source occurrences while retaining the reviewed relation. |
| Traffic conflict removal compared Transfer references with Activity references. | Link independent endpoints and topology before attributing a change. |
| Complex many-to-many sets falsely established concrete new journeys or venue-change participants. | Require unique endpoint correspondence or explicit additions/removals; require 1:1 venue-change attribution. Complex groups retain unresolved attribution. |

The first two P2 corrections were committed in `e24ce0e`; the third, found on recheck,
in `45b13d9`. Four public regressions reproduced the first defects; the final independent
Spec recheck passed nine original/correction cases. Standards' P3 duplicated content
comparison was consolidated through `_content`. Final reviews closed all three P2 findings
and the maintenance finding.

## Validation checkpoints

Implementation: `f65cd0f`. Review base:
`d08083d5d50573e0bec6345f45ed12beb2b77855`.

| Checkpoint | Observed result | Scope |
| --- | --- | --- |
| Before final UNKNOWN-venue protection fix | **2402 passed, 10 skipped**, 230.18 seconds | Intermediate backend evidence |
| Pre-review after that fix | **2403 passed, 10 skipped**, 211.62 seconds | Backend; contained **574 passed, 1 skipped** evaluator and 46 new pair tests |
| First review correction | **76 passed**, 19.09 seconds; **578 passed, 1 skipped**, 92.49 seconds | Pair/quality selection, then evaluator |
| Complex correspondence correction | **78 passed**, 16.89 seconds | Pair/quality selection |
| Final post-review | **2409 passed, 10 skipped**, 216.22 seconds; zero deselections | Backend; contained **580 passed, 1 skipped** evaluator and 52 new pair tests |

Contained subsets and overlapping checkpoints are not additional independent runs.
Skips were nine PostgreSQL opt-ins and one Windows symlink case. Tests cover source/hash
atomicity, stage availability, accepted component membership, edits/topology, protection
and other independent continuity, partial magnitudes, immutable CLI and findings-only
numeric invariance after relinking. Ruff, formatting, CLI help and diff checks passed;
seven changed documents and 143 local targets were checked. Synthetic snapshots used
injected transport; no live model, provider, database or formal case was executed.
Local fixture/JUnit evidence is under `artifacts/ticket10-dev/`.

## Equivalent delivery revisions

Read-only preflight at `296460dfbab442f066a87798e44b800800f995d8` found the original
review revisions outside the delivery ancestry. Local Git tree hashes and empty tree
diffs established these exact correspondences:

| Historical evidence revision | Reachable delivery revision | Role |
| --- | --- | --- |
| `d08083d5d50573e0bec6345f45ed12beb2b77855` | `45a04567067bf0c5aa6909b1bf3dd147086d9c24` | Review fixed point |
| `f65cd0f8370136afacfabc14a1af7251ba8fc197` | `3ebefb62db9264fd7146dd60f0dc209650db0a33` | Implementation and direct tests |
| `e24ce0ee628a7e8de99aab6f82bf36a7a336ecda` | `645becd09bc1637a8527f46c676b51f0bfd9d92b` | First review correction |
| `45b13d926ff8b2d6b667c599f3c812fcfe24d995` | `bd406b3007552cf7ea6e26ee4e1fe97f294e1cfb` | Second review correction |

These bindings support reusing validation of identical code, not claiming a new test
run or relabeling old evidence. Later Ticket 12 publication is recorded in the
[engineering closeout](2026-10-04-mechanism-report.md#publication-checkpoint).

## Limits

Indistinguishable or contradictory legacy observations cannot uniquely reconstruct
history. Partial/lower-bound magnitudes do not establish exact improvement. Removal is
not resolution; aggregate changes describe observed populations, not causal Repair
success. Controlled Repair retains its separate study and denominators.

## Paired access refresh 2026-10-17

The researcher authorized refreshing the current V3 before/after views for cases
01–07 and 09, including accepted cases, with the same missing-hours access policy
applied to both original stages. The [contract](../../contracts/0005-quality-human-review.md#v3-pairs)
owns the rule. Implementation `1bf8f50` and separate correction `45f8c33` add V3-only
source-bound packets, shared identical contexts, one-use execution and exact offline
import through paired, suite and research interfaces. Generation behavior is unchanged.
Original outputs, primary scores, raw receipts and historical reports remain retained.
Current reader sections and source mappings replace their previous paired presentation.

| Case | Draft overall | Final-primary overall | Overall change, percentage points | Opening UNKNOWN, draft/final | New model sends | Reference USD |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| 01 | 85.833333 | 100 | +14.166667 | 0 / 0 | 1 | 0.00089080 |
| 02 | 80.208333 | 100 | +19.791667 | 1 / 0 | 1 | 0.00105055 |
| 03 | 86.666667 | 100 | +13.333333 | 0 / 0 | 1 | 0.00118730 |
| 04 | 44.285714 | 100 | +55.714286 | 0 / 0 | 0 | 0 |
| 05 | 84 | 100 | +16 | 0 / 0 | 1 | 0.00039855 |
| 06 | 100 | 100 | 0 | 0 / 0 | 1 | 0.00092980 |
| 07 | 100 | 100 | 0 | 0 / 0 | 1 | 0.00047330 |
| 09 | 92.848485 | 98 | +5.151515 | 1 / 1 | 1 | 0.00195030 |

Displayed values are rounded; native reports retain exact fractions. This is one
same-run diagnostic per selected case, not an independent V2/V3 experiment or a causal
Repair estimate. Case-02's draft access uncertainty and case-09's Tokyo Dome City
uncertainty remain unresolved. Case-04 has no eligible access gap; its route UNKNOWNs
remain. Case-06/07 performed no model Repair and retain exact zero paired change.
Case-07 now has a computed pair; its former unavailable paired presentation is replaced.
Case-06's selected a2 pair remains separate from the first-attempt research census,
which includes failed a1; that census was not rebound. Native research same-run views
for cases 03/05/07/09 were rebuilt, while historical four-final sections retain their
original sources. Section-derived reader views identify those sources separately.

The frozen batch covered 38 stage occurrences / 21 distinct access contexts in seven
`gpt-6-luna / medium` calls. Case-04 used no model. Actual recorded input/output tokens
are **31,929 / 5,780**, total **37,709**. Google sends and retries are **0**. Reference
spend is **USD 0.00688060** against the authorized USD 0.25; per-run USD 0.035 ceilings
sum to USD 0.245. Input/output caps total 73,728 / 114,688 tokens. Prices use the dated
OpenAI retail proxy for the existing Azure deployment; actual account invoices and
external Codex token/billing telemetry remain unavailable. All seven call slots are
consumed; remaining money grants no additional call or retry.

The first automatic approval request was rejected before process creation because
destination/data authorization was insufficiently explicit. The researcher then
explicitly authorized the existing Azure endpoint and frozen activity/venue/time/source
data scope. The unchanged batch made its first actual execution after approval; this
was not a provider retry. Its file SHA-256 is
`aa6b0f48e0583b53a54e48e96d0787b7c9735d299353300a5426febb4828d402`.
Native model responses, HTTP journals, usage, receipts, original source closures and
review/authorization observations remain private, indexed by each case's material index.
All eight archives passed fresh-root SHA/length, packet/HTTP receipt and native pair
replay with zero network attempts and zero old temporary-evidence-root reads; cases
03/05/07/09 also reproduced their current native same-run research view. Case-07's
first restoration hit the Windows path-length limit; a short fresh root passed with
the same archive bytes. The public reference checker also validated case-specific
delta formats; an initial compaction cycle was removed before final projection checks.
Historical four-final and mechanism subtrees retain their original values and sources.

Public-interface TDD and affected checks passed 114 tests, then an overlapping
154-test gate. Independent Standards review found no issue; Spec review found one P2:
null/list access packets raised an uncaught exception. Three public regressions first
reproduced the defect; type validation corrected it, and 79 affected tests passed.
Both reviewers rechecked with zero remaining findings. Changed Python Ruff/format and
diff checks passed. An offline operator price file initially lacked its schema tag;
correction preceded preparation/execution and made no service request. An existing
reviewed-edit provenance replay defect was also reproduced and corrected without
resuming case-09's stopped historical package. No full backend regression was run.

`/root/pair_access_standards` and `/root/pair_access_spec` independently reviewed code;
`/root/paired_access_execute` used `gpt-6.1-sol / medium` for frozen execution only.
The parent owns source binding, native offline replay, sanitized projections and
documentation. Agent review does not constitute human quality ratings. Case-09 remains
pending final researcher acceptance. Work stays in the current worktree; main-worktree
integration and Git publication await a separate instruction.
