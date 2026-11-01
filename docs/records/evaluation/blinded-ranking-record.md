# Blinded ranking engineering evidence

The 2 October 2026 implementation introduced source-bound anonymous packages, private
mappings, balanced labels, revision-aware answers and an isolated React renderer.
Current semantics belong to the [human-review contract](../../contracts/0005-quality-human-review.md#human).
This record concerns engineering acceptance, not actual participant study results.

## Blinding and travel representation

From base `541c684a4ae58001b513a9508b65a1d99507b0bf`, `6095877` / `d36b52d` fixed public
A–D assignments across dimensions while keeping mappings outside rater files. Hidden
duplicates did not add main-result weight; later drafts did not replace submitted answers.

Review corrected invalid clock rollover and compact `+0200` / `+02` timezone conversion
(`29df5fd`). Display standardized HH:mm and labelled inferred arrival rather than claiming
it was submitted. Timestamp controls and mechanism hints were removed without altering
travel facts, uncertainty, original public JSON or mapping/presentation hashes. Saved
package rechecks verified those bindings at `290ef203c20fa18e8d4f3ab05aa4e5b5ecf6cda7`.

## Recovery and asynchronous import corrections

Confirmed Clear was scoped to the active package/rater and retained data on failed/cancelled
persistence. Review found pending FileReader work could restore cleared answers; `d514508`
invalidated it only after successful Clear. A later release review found imports could
lose answers saved during reading or restore a previous task after navigation. `8d3b387`
used the latest persisted answers and selected task at completion, preserving Clear fences.
Failing regressions preceded both corrections.

## Verification and evidence

| Checkpoint | Observed result |
| --- | --- |
| Initial implementation | 2,299 backend passes/ten skips; 89 frontend passes |
| Clock/display revisions | Frontend 94 in 13 files at the respective checkpoints |
| Source/recovery recheck | 11 UI/answer and 26 backend tests |
| Clear/import race correction | Frontend 98 in 13 files |
| Later release import correction | Frontend 100 in 13 files; real-renderer CLI usage nine passes across 40 processes |

Build/typecheck/lint and independent review corrections passed at their stated scope.
User-reported native browser acceptance remained distinct from automated evidence.
Renderer changes preserved frozen sources and answer/scoring linkage; public packages
contained only `review.html` / `presentation.json`, with mappings separate. Local
`integrity.json`, imported synthetic answers and reports documented those checks.

## Limits

Synthetic rankings test import/aggregation, not human preference. Native browser reports
are not separately saved automation logs. Current real human/model results belong to the
[blinded study report](../../../benchmark/blinded-results/report.md), not these early tests.
