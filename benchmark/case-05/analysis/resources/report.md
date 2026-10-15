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

The current case-05 Codex worker assembled this resource-only view with the native all-attempt ledger and cost reconstruction readers. No version benefit/quality study, new independent review or human rating was selected. Original failed preparation records remain private.

These local views were assembled on 2026-10-15 at source `51458ee`; only these new report views were uncommitted during checks. Original generation sources remain `f49503a` and `0f365304`. Independent relevance, V3 paired closeout, full public case material, archive verification, final integrated tests and explicit user acceptance remain pending. The case and repair Issues stay open.
