# Case-05 all-attempt resources

Six actual generation invocations and one primary evaluator invocation are retained across the original execution and revision 2. Original V2/V3 were not dispatched. Repair is included once within V3, not charged again.

| Execution | Version | Outcome | Model calls | Tokens | HTTP sends | Reference USD |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| original-execution | v0 | completed | 2 | 18217 | 2 | 0.002901315 |
| original-execution | v1 | failed | 1 | 11252 | 1 | 0.0010237 |
| revision-02 | v0 | completed | 2 | 25253 | 2 | 0.005518225 |
| revision-02 | v1 | completed | 5 | 84547 | 91 | 2.80578068 |
| revision-02 | v2 | completed | 6 | 80964 | 92 | 2.80424982 |
| revision-02 | v3 | completed | 7 | 171894 | 94 | 2.847875495 |

Generation reference total: USD 8.467349235. Primary reference total: USD 1.079222475. Combined historical reference total: USD 9.546571710.

Primary native scoring completed; its subsequent CLI output failed with exit 1. That failure is preserved. Independent model/API namespaces and inherited paired-import usage must not be counted as new consumption. Actual invoices and external Codex usage/billing are unavailable. Current-stage business API sends and spend are zero.

## Scope and source binding

The [sanitized ledger](summary.json) preserves per-invocation model/token/HTTP observations, status and reference estimates. Complete native usage/cost reconstructions and hash-bound inputs remain private under the historical identifier `benchmark/scratch/case-05/work/post-primary-offline-01/reports/resources/`. Costs were rebuilt from each saved native usage/price pair and matched all six original saved generation cost reports. Primary cost was rebuilt separately from saved oracle usage/prices. No new primary evaluation was dispatched or report revision selected.

The census retains one original input and two distinct execution revisions. Retrospective non-start declarations for original V2/V3 cite the preserved original terminal record; they are not original producer captures, actual invocations or zero-usage measurements. There were no automatic retries. Missing invoices, external Codex usage and billing remain unavailable.

The case-05 Codex worker assembled this resource-only view with native all-attempt and cost readers. A subsequent independent Codex operation reviewed 171 venue-interest pairs. Its actual actor, times and output hashes are disclosed separately in summary.json; model/reasoning identity was not independently verified, and token usage and billing are unavailable. This external assistance is not a zero-cost business API event. No human rating or version benefit/quality study was selected. Original failed preparation records remain private.

The [V3 offline paired observation](../../evaluation/v3-pair/report.md) completed under the explicitly approved fresh 600-second package, with exact native replay, a byte-verified portable handoff and verified closed receipts. Google/model sends and retries were zero; current business API reference cost was USD 0. The earlier 120-second stopped package and its verified receipt remain preserved. Imported source consumption is informational and is not added to current costs; historical totals above remain unchanged.

These local views were updated on 2026-10-15 from source `f326208`; only paired/resource views changed during checks. Original generation sources remain `f49503a` and `0f365304`. Known relevance remains partial. Full V2/V3 Repair process presentation, full public case material, archive closeout, final integrated tests and explicit user acceptance remain pending. The case and repair Issues stay open.
