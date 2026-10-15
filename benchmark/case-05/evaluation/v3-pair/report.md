# Case-05 V3 paired attempt

Status: **stopped by the frozen total timeout; no completed pair result selected**. Native stopped-result replay and the closed receipt verify exactly. The consumed directory was not retried or resumed, and no completed handoff was exported.

The selected sources are the original revision-2 V3 draft and final from the same invocation. Their saved itinerary values are equal and original Repair remains `REJECTED / insufficient_time_for_model_and_rechecks`. This observation is not a run of the later Repair timing correction.

| Control / observation | Value |
| --- | --- |
| Execution mode | Source-labelled offline reuse |
| Frozen total timeout | 120 seconds |
| Native stage elapsed until stopped closeout | 296.002 seconds |
| Google sends / model sends / retries | 0 / 0 / 0 |
| Current reference API cost | USD 0 |
| Stopped-report replay / closed receipt | Exact / verified |

Local verification and diagnostic construction exceeded the deadline. A native intermediate diagnostic file was written, but the enclosing operation stopped with `execution_timeout` and selected no pair. The intermediate file is retained as failure evidence; its metrics are not presented as a completed pair, substituted for the original primary score or exported as accepted material. No profiling conclusion about the exact local bottleneck is claimed.

The first wrapper initialization failed before native execution or package consumption because its socket guard intercepted the Windows event loop's local self-pipe. Constructing that local loop before enabling external-network blocking allowed the single native attempt. Business HTTP-client construction and external sockets remained denied throughout actual execution. Both the startup error and the genuine stopped attempt are retained.

A fresh **600-second proposal is prepared but unexecuted**, retaining the same source input, selection, contexts, evidence and prices. It retains zero Google/model sends, USD 0, and zero retries. It requires a new explicit approval; the old package and its limits remain unchanged. The proposed digest and exact original/stopped source hashes are in [summary.json](summary.json).

Evidence remains under the historical identifier `benchmark/scratch/case-05/work/post-primary-review-01/`, including the independent-review outputs, stopped replay verification and fresh proposal. The original producer reader is restored separately from exact source `0f365304`; project code is unchanged. These views were assembled on 2026-10-15 from worker source `9acc76f`, with only case report views uncommitted during checks.

The [candidate report](../../analysis/poi-process/report.md) distinguishes completed relevance judgments from partial known evidence. The [resource report](../../analysis/resources/report.md) separates original Planner/evaluator consumption from external Codex assistance and this zero-send attempt. No generation or primary evaluation was dispatched; case-15, full case closeout, integration and final user acceptance remain pending.
