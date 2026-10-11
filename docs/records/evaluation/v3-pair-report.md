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
