# Offline evaluation CLI workflow validation

2026-10-04. Status: Offline Validated and independently reviewed. This record summarizes
public workflow behavior and the separate renderer defect found during release review.

## Public workflows and observed outcomes

The new subprocess tests exercise public `python -m backend.evaluation...` commands,
reusing the existing synthetic development fixtures. They retain input JSON, snapshots,
command argv/exit code and UTF-8 stdout/stderr in ignored `artifacts/evaluation-usage/`.
Each invocation checks pre-existing packet source hashes for immutability. External socket
connections are guarded; loopback is permitted for the event loop's internal socket pair.
The controlled executor additionally retains its existing frozen ports/clock/network guard.
Regression subprocesses use the same synthetic tokenization convention as the parent
test suite, avoiding a dependency on downloaded vocabulary. No payload measurement is claimed.

| Workflow | Bounded result |
| --- | --- |
| Four-version quality and resources | All V0-V3 appear. Synthetic V1 auxiliary score is 50; its two opening checks remain UNKNOWN. Unavailable token usage is null and adds no quality penalty. Reviewed empty hard obligations are N/A; the architecture preference is not promoted to a hard requirement. |
| V3 paired overlap/retime | An adopted edit moves visit B from 09:30-10:30 to 11:00-12:00 while visit A remains 09:00-10:00. Confirmed overlap is resolved through source lineage, with no removed visits. Grounding delta is exactly 0/1. Other incomplete route/occupancy evidence leaves the auxiliary-total delta null. |
| Controlled overlap | Real frozen V3 replay retimes B from 10:30-11:30 to 11:30-12:30, resolving its overlap with A at 10:00-11:00. Independent target outcome is `resolved`. |
| Unchanged control | A valid one-visit fixture stays unchanged: `valid_no_change`, with zero model attempts. |
| Lawful addition | Independent checks support adding a second visit: `lawful_change`, with one frozen model attempt. |
| Exclusive addition | Original text says “Exactly one primary visit on this day.” The fixture deliberately omits this restriction from the planner interpretation. Internal Repair accepts the addition, but the independent guard changes PASS to FAIL and reports `regressed`. |
| Mechanism reporting | Actual controlled preparations yield one V3 run rather than invented V0-V2 runs. Four-version selected material retains all four runs; missing observations remain unavailable. |
| Blinded package/import/report | The acceptance packet embeds the existing built React renderer, keeps private mapping outside the public directory and exposes labels A-D. Synthetic answers import at revision 1 and produce one descriptive main task. No actual rater session occurs. |
| Invalid input | A missing manifest and a disposable changed-result copy with its old expected hash both exit 2. Diagnostics identify the file; the latter says `Artifact hash mismatch`. Original selected files remain unchanged. |

Complete processing is distinct from independent PASS. The regression control and UNKNOWN
examples intentionally process successfully. Synthetic capture occurrences and ranking answers demonstrate linkage and reporting only;
they are not actual recorded model submissions or research observations.

## Validation and real renderer evidence

Implementation `c877b6ec9dc78e4803fb7f6df10a4a31bbd8f2ed` was reviewed from
`b003c49e7f79c9d38dd8cf896673fcf1dca4ee07` for [Issue #49](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/49).
The final synthetic usage gate selected the real built renderer: **9 passed in 92.25
seconds**, with 40 module processes (38 exit 0; two intended invalid-input cases exit 2).
Full backend: **2490 passed, 10 skipped in 319.18 seconds**. Existing local PostgreSQL
opt-ins and host symlink checks skipped; no live-service acceptance is inferred.
Ruff, formatting, diff checks and the TypeScript/Vite blind-review build passed.

Embedded renderer JS/CSS matched the build bytes:
`cab999fb2c18f5979d4a033ea4f095f61c95727817d57925d4f9b12ade5d3a7c` and
`14c23164703086562b4fabebf5d845ede3c7713ea76058ded3e3eba5eb97b71d`.
The harness prohibits external connections, permits event-loop loopback and uses
structural synthetic tokenization, making no real token measurement. A paired snapshot
correctly failed final-only quality scoring with `unsupported_snapshot_scope`; the
examples now use distinct final/paired scopes. Other mistaken fixture assertions were
corrected against public contracts, without changing production behavior.

Independent Standards/Spec reviews found no blocking issues. The PowerShell 7 JSON-saving
example was verified as UTF-8 without BOM using accented text. Local packets and logs
are under `artifacts/evaluation-usage/`, including `accepted-packet/`, `final-packet/`,
`usage-gate.txt`, `backend-gate.txt` and per-test `cli-output/`. The
[package guide](../../guides/verification.md#verify-resource-and-cost-claims)
provides a reproducible demonstration; published observations above stand independently
of those ignored paths.

## Asynchronous import correction during release review

[PR #50](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/50) reviewed the
complete Evaluation/documentation release from `ecb01cc67be2d5b659747444756d606a6b2485bb`
at initial head `59adc5ea63ba33f9ab70c7111cac5d7076feecab`. Concurrent documentation
was incorporated separately, without overwriting it.

Standards found that delayed FileReader imports could lose a revision saved while reading
or restore the prior task's form after navigation. Failing regressions preceded `8d3b387`,
which uses the latest saved answers and selected task at completion, preserving Clear
invalidation. This correction affects only the standalone renderer/component tests.

| Corrected checkpoint | Observed result |
| --- | --- |
| Frontend suite | **100 passed / 13 files**; affected component **14 passed** |
| Real-renderer usage gate | **9 passed**, 137.05 seconds; 40 CLI subprocesses |
| Static/build checks | Lint, TypeScript/product build and isolated blind build passed |

An interrupted rerun without selecting built assets is not passing evidence. Backend
code was unchanged, so its earlier 2490/10 gate was reused rather than rerun. Hosted
CI had no checks, and mypy/pyright were not configured. Release packets/logs are local
under `artifacts/git-delivery/`; the actual merge state belongs to the PR timeline,
not this pre-merge checkpoint.

## Limits

These synthetic workflows demonstrate linkage, reporting and successful processing,
including UNKNOWN and deliberate regression. They are not actual model submissions,
real rater sessions or research observations. No production module,
planner behavior or scoring policy changed in the usage task. Prior user-reported native
storage/download acceptance was reused; packet generation is not a new browser pass.
No live provider/model/database execution or formal comparison was performed.
