# Case-05 all-attempt resources

One scenario has two approved input revisions and three execution revisions. The ledger retains **10 actual generation invocations and two primary invocations**. Original V2/V3 non-start declarations are separate from consumption. Repair is included once within its V3 generation; imported paired usage is informational.

| Execution | Version | Outcome | Model calls | Tokens | HTTP sends | Reference USD |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| original-execution | v0 | completed | 2 | 18217 | 2 | 0.002901315 |
| original-execution | v1 | failed | 1 | 11252 | 1 | 0.0010237 |
| revision-02 | v0 | completed | 2 | 25253 | 2 | 0.005518225 |
| revision-02 | v1 | completed | 5 | 84547 | 91 | 2.80578068 |
| revision-02 | v2 | completed | 6 | 80964 | 92 | 2.80424982 |
| revision-02 | v3 | completed | 7 | 171894 | 94 | 2.847875495 |
| revision-03 | v0 | completed | 2 | 23895 | 2 | 0.0052401 |
| revision-03 | v1 | completed | 4 | 76140 | 68 | 2.363167335 |
| revision-03 | v2 | completed | 6 | 82626 | 92 | 2.790165025 |
| revision-03 | v3 | completed | 8 | 228323 | 76 | 2.418508775 |

Generation reference total: USD 16.044430470. Primary reference total: USD 2.607513575. Original generation/primary subtotal: USD 18.651944045. The current paired assessment adds USD 0.000398550, giving a known case total of **USD 18.652342595**. Selected revision-3 generation plus primary: **USD 9.105372335**, within its USD 40 allowance.

The revision-3 primary used two model sends, 14,487 observed tokens and 70 Google sends, with zero retries. Its CLI exited 0. The historical primary report was saved before its presentation-only GBK failure; its cost remains included. All native cost reconstructions match saved reports, with zero unpriced events.

The paired refresh used **one model send, zero Google sends and USD 0.000398550 reference cost**, with no retry. Actual invoices and external Codex author/reviewer/execution/orchestration tokens and billing are unavailable, not zero. The [summary](summary.json) separates input cohorts and every actual invocation. Historical consumption is retained for accountability, rather than treated as additional unique scenarios.
