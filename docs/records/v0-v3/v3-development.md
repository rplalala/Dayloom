# V3 validation and Repair engineering evidence

September–October 2026 development progressed from read-only findings to bounded,
permissioned Repair and separate best-result retention. Current rules belong to
[validation/Repair](../../0005-validation-repair%28v3%29.md); the
[milestone](v3-milestone.md) identifies the original engineering closeout.
Historical tests below establish their stated revision, not later live effectiveness.

## Initial validation and bounded Repair

The 22–25 September implementation reused V2 primary planning before final Nearby.
Application-owned requirements, permissions and evidence constrained proposals.
Elastic windows, actual adjacency, targeted additions, mixed modes and dependency
components replaced simplistic free-time/whole-patch handling. Same-date dependent
edits stayed atomic; independent accepted components survived later rejection.

Key corrections prevented unrelated later gaps from satisfying a journey, protected
required count/date progress during deduplication, and separated provider timing from
application DRIVE reserves. Material feedback tracked attributable failures without
poisoning unedited candidates. Serializer stress tests established input/output
admission behavior, not model reliability or production capacity.

## Honolulu capacity and minimum coverage

The original Honolulu overflow remained a failed execution. Later preparation refined
active-target locality and capacity rather than increasing every global ceiling.
The nine-day minimum-coverage run `f9bd621d-0eb5-47d7-8af8-03825d57524b` changed visits
10→18 and missing coverage dates 3→0 over five rounds. In round 2 one component was
accepted while another failed for insufficient unoccupied transfer time. Two adopted
TRANSIT observations were 1845s and 686s with applicable-time PASS. A later empty
rejected patch preserved prior adoption. One optional quantity target remained.

The separate mixed run `8b7db82f-9c52-4cdc-b802-2c273406ee66` had empty rounds followed
by genuinely changed material; this does not justify repeated unchanged empty sends.
Evidence: `logs/v3_honolulu_9day_shared_mixed_20260927/` and
`logs/v3_honolulu_9day_minimum_coverage_20260927/`. Live exemptions, all operation
combinations and cancellation/dependency branches were not comprehensively exercised.

## Pace optimization and source facts

On 9 October, optional pace optimization was aligned with reviewed density curves
while hard constraints retained precedence. A separately bounded real Repair smoke
and independent evaluation exposed distinct factual and CLI defects; later success
never replaced stopped packages.

Google-backed output normalization corrected model-authored names/partial addresses
for supplied identities. Application facts now survive retain/retime as well as add/
replace without making validation mutate source or adding provider calls. Opening
serialization and incomplete V0 correspondence separately blocked evaluator composition.
Two stopped identity preparations retained their actual responses/usage; subsequent
complete evaluator acceptance is in the [intake record](../evaluation/intake-identity-usage.md).
The later source-protected V3 started with zero pace deduction and made no Repair call,
so it is not evidence that Repair caused its quality.

## Exploration and retained-result redesign

Specification #139, implementation `b9a29e1` through `a0b1114` on 13 October, separated
checked exploration from final retention. Equal/worse intermediate soft states became
possible without hard regression. Deterministic deletions, local proposals and affected-day
replanning shared ordinary permission/adoption checks.

Regressions exposed accumulated failed deletion alternatives, adoption after expired
recheck, unknown dates blocking known-date progress and discarded states inflating final
adoption. Fixed original comparison dates and versioned selected lineage corrected these.
Review correction `6d41bbb` tied status to retained improvement: system-only exploration
that returned the unchanged draft could no longer claim accepted progress.

The full backend at `a0b1114` recorded 4,161 passes, five failures and 16 skips. One
failure needed a narrow pure-stdlib import allowance; four depended on local launcher
assets. `3709d0e` isolated mocked launchers from ignored configuration. Final affected
verification passed 708 tests with one skip, including all five prior failures; the
full suite was not repeated. Logs are preserved under `logs/v3-repair-139-offline-20261013/`
with source/size/hash metadata. A later model smoke used synthetic identities/routes,
so it established proposal integration rather than real-place feasibility.

## Deadline and round-allocation diagnosis

A 6 October deadline regression was made phase-deterministic: setup explicitly reached
the owned runtime phase before advancing beyond the deadline. This avoided mistaking
pre-initialization timeout for a cleanup defect. The 15 October round diagnosis kept
entry, preparation, proposal and recheck timing separate; expired rounds could not
adopt late responses. These were offline checks, not increased live allowances.

## Reason-length recovery and full-day rest

On 17 October, bounded explanation compression addressed overlong disposition reasons
without altering proposed edits or target identities. The original response and one
compression attempt remain auditable; failed compression preserves the best result.

Case-12 r05 exposed a pace-applicability error: a fully protected rest day with zero
visits received penalty 100 under relaxed default, leaving an impossible insertion target.
Correction `b292a10` projected full-day protection to feasible zero without rewriting
requirements or forced success. The affected network-blocked gate passed 646 tests after
owned temporary directories resolved 11 setup errors. No full regression or case rerun
followed; historical scores/statuses stayed intact.

## Opportunity preparation and empty proposals

Case-12 r06 repeatedly returned empty edits on unchanged effective material. Soft-pace
additions lacked structured routes, and qualification could remove an apparent opportunity
after acquisition had already stopped. Implementation `7d1fe3c` / correction `421a83d`
added active-authorized route context, settled qualification before sufficiency and
stopped unchanged empty-input resends per strategy.

Review reproduced two rejected identities consuming the exploration reference and an
unpublished audit field. Failing controls preceded fixes; final affected verification
passed 713 network-blocked tests. Synthetic small-input sizing was 5,568 local / 5,821
replan tokens, not a worst-case capacity study. No case rerun or full backend pass was
claimed at that checkpoint. Original evidence remains under
`benchmark/scratch/case-12/work/run-r06/captures/v3/result.json`.

## Rich completion and density policy revision (2026-10-24)

Issue #216 used `8cfbf5f` / `5ae7208` and review corrections `9265a2a` / `ee62de6`,
from `2eee32b`. Completion became a final per-date check with sourced override precedence,
separate from aggregate pace progress. Regressions corrected unmet soft counts labelled
satisfied, unresolved dates disappearing, and no-transition rest days blocked by a generic
route limitation. Actual unknown route obligations remain blocking.

The initial full gate recorded 4,908 passes, 82 skips and one obsolete weather-attribution
test assertion. The corrected Product/Rich selection passed 16; final Repair/validation/
schedule checks passed 206, including 21 Rich tests. Frontend passed 261 plus build/typecheck.
A UTF-8 subprocess control passed the earlier junction-warning case. Full backend was
not repeated after corrections. Original evidence: `.scratch/issue-216/`.

## Limits

Internal adoption and soft progress are not independent score gains. Bounded discovery
and conservative components can leave feasible goals unresolved; no global optimizer,
access verifier or universal improvement claim follows. Synthetic external dependencies
and historical live runs retain different provenance. Later current selections/results
belong to the [benchmark](../../../benchmark/README.md), not this engineering history.
