# Controlled V3 repair development evidence

Ticket [11 / #23](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/23),
2026-10-04. Status: Implemented and offline Validated. This checkpoint establishes
engineering behavior, not a formal target/control corpus or benchmark result.
The [controlled replay contract](../../contracts/0001-evaluation-artifacts.md#controlled-repair)
owns current semantics; the [package guide](../../guides/experiments.md#blinded-and-controlled-studies)
owns commands.

## Frozen execution and independent outcomes

The delivery executes the real V3 post-primary path with typed frozen external-call
scripts, complete cache/semantic state and logical time. Genuine V3-only sources are
accepted without fabricated V0–V2 outputs. Independent checks distinguish unchanged
controls, lawful additions, missed detection, adopted repairs, residual failures and
regressions. Verified supplements affect reviewed checks/continuity, preserving raw
paired metrics rather than claiming recalculated total scores.

Synthetic public-seam cases cover overlap repair, explicit-count regression, newly
closed visits, supported additions, supplements, corrupt material, strict call matching
and missing batch reports. They supply independent fixtures, reviewed coordinates and
injected snapshot responses; they are not the formal corpus.

## Consequential defects and corrections

| Defect | Correction and retained boundary |
| --- | --- |
| Logical service time advanced while asyncio timeouts still used real time, allowing a scripted late reply. | The exclusive replay loop and due timeout handles use logical time before reply delivery. A failing regression preceded the fix. |
| Malformed frozen Repair responses became ordinary model failures. | Validate the real `RepairPatch` shape and retain `execution_material_error` in the execution ledger. Shape-valid ineffective or unauthorized patches still face production acceptance. |
| An obligation-only protection goal could not establish resolution without activity selectors. | Reuse its independent `protected_time` check. Verified `primary_visits` can resolve; uncertain transport occupancy under `scheduled_commitments`, UNKNOWN checks and absent blockers remain unresolved. |

The static intake guard initially rejected the approved controlled executor's planner
imports (**1 failed, 1063 passed, 1 skipped**). Its exception was restricted to the nine
controlled modules; ordinary evaluation readers/scorers retain the planner-free boundary.
This was a guard compatibility correction, not permission for general planner imports.

## Validation checkpoints and evidence

| Checkpoint | Observed result | Scope |
| --- | --- | --- |
| Shared-seam implementation gate | **2433 passed, 10 skipped** | Full backend, before later offline corrections |
| Logical-time correction | **605 passed, 1 skipped** | Evaluator, including 25 controlled tests |
| Final review corrections | **23 passed** focused; **608 passed, 1 skipped** evaluator | Includes 26 controlled tests and two paired protection-goal cases |

The public CLI check passed three controlled tests. Ruff, formatting, compilation and
diff checks passed; no configured static type checker was available. These overlapping
gates are separate checkpoints, not additive evidence. The early full backend gate does
not validate the later report/material corrections.

Review base: `b6d9dd98af3dc6c7038a88a858df441dffd1bd63`.
Implementation: `91310cc`; malformed-response correction: `a816e27`;
protection-scope correction: `ae6b847`. Standards found no actionable issues; Spec's
two findings were corrected and independently rechecked, including three regression cases.

Local synthetic evidence is under `artifacts/ticket11-implementation/`; the historical
documentation checker is `artifacts/ticket11-preflight/check_docs.py`. These ignored
paths locate development material; the public result and limitations are stated here.

## Limitations

Replay requires a dedicated offline process, exclusive event loop and serial cases:
it temporarily patches process-wide sockets and the loop clock. Concurrent web-service
execution is unsupported. Evidence-only captures containing key hashes cannot supply
missing cache values or calls for executable replay.

Tokenizer assets must already be local; the structural test tokenizer does not measure
real model tokens, cost, latency or quality. Supplemental route facts cannot fabricate
transport occupancy. Acquisition at this checkpoint was an injected-transport API,
with no operational live client. No formal repair/control-harm rate, causal conclusion,
version comparison or research conclusion was established.
