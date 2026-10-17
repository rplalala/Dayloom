# Case-08: Barcelona, Spain

## Selection and status

**Steps 1-9 complete; step 10 awaits the researcher's acceptance decision.** The selected r02 V0-V3 outputs, historical Primary and separately authorized corrected Primary are retained. Same-run V3 pairing, independent continuity, all-attempt reconciliation and retained-evidence archive verification are complete. Blinded human review is deferred separately. [Issue #157](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/157) owns case lifecycle; this local preparation does not close it or [#182](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/182).

The unchanged [original request](../inputs/case-08.json) covers Barcelona, 22-24 October 2026, two adults and EUR 1,000 for the whole trip. It requires exactly one Sagrada Família visit, excludes Park Güell and expresses architecture/history interests. Input SHA-256 is `769a0b33a4eb9eb42e7414f847465ce42b8ed2070c864515d20f61eb07ff394a`.

All four selected generations use source `19a4f4d97e4c8cb5e441ebc3239e7ef5111b86bd`. The corrected Primary completed on 17 October 2026, Australia/Sydney, under evaluator source `d3cab596d9ba81ae9b72c4ec4d8cc4ec79b39a6c`. Its scores retain that executed source and policy; later code integration does not rebind or recalculate them.

| Material | Reader view |
| --- | --- |
| Reviewed original-request obligations | [Requirements](requirements/reviewed.json) |
| Selected schedules and usage | [V0](generation/r02/v0/itinerary.json), [V1](generation/r02/v1/itinerary.json), [V2](generation/r02/v2/itinerary.json), [V3](generation/r02/v3/itinerary.json); adjacent usage summaries |
| Current workflow | [Steps 1-10 checklist](analysis/acceptance.json); step 10 pending researcher decision |
| Same-run V3 pair | [Summary](evaluation/pair/summary.json), [complete native report](evaluation/pair/report.json) |
| Corrected Primary | [Summary](evaluation/primary-corrected-r01/summary.json), [complete saved quality subtree](evaluation/primary-corrected-r01/report.json) |
| Historical Primary | [Summary](evaluation/primary/summary.json), [complete saved quality subtree](evaluation/primary/report.json) |
| Candidate process and relevance | [Candidates](analysis/offline-r01/candidates.json), [independent decisions](analysis/offline-r01/relevance.json) |
| Repair structure and earlier checklist | [Repair](analysis/offline-r01/repair.json), [historical offline checklist](analysis/offline-r01/acceptance.json) |
| Original r01 observations | [Unevaluated V0](generation/v0/itinerary.json), [V1 failure](generation/v1/failure.json) |
| Current publication bindings | [Material index](material-index.json) |
| Frozen pre-correction index | [Historical source index](evaluation/primary/source-material-index.json) |

The current index distinguishes publication byte hashes, original source hashes and native JSON pointers. The historical source index retains its original bytes and earlier costs/status; its relative paths refer to the case directory. It is not the current acceptance authority. All four offline analysis JSON files are saved stage snapshots. Their historical pending-work descriptions are not current requirements: paired-policy compatibility is integrated through PR #187, and the current pair/checklist below supersede their unperformed-pair and open-archive status. The historical checklist has only a local temporary-root spelling removed from its publication view.

## Primary results

| Version | Corrected overall | Corrected auxiliary | Mean density deduction | Historical overall |
| --- | ---: | ---: | ---: | ---: |
| V0 | 96.6667 | 96.6667 | 0 | 96.6667 |
| V1 | 74.6667 | 98.0000 | 23.3333 | 52.6667 |
| V2 | 96.6667 | 100.0000 | 3.3333 | 76.6667 |
| V3 | 100.0000 | 100.0000 | 0 | 80.0000 |

These are saved native totals, not newly computed scores. The corrected run uses preparation 3, subject policy 2 and identity policy 6. All eight named-subject projections PASS; both exact-once Sagrada Família and Park Güell exclusion obligations PASS for every version.

V0 retains one grounding FAIL: its matched Sant Pau venue is in Horta-Guinardó, while its submitted location said Eixample. V1 retains one Casa de la Seda opening UNKNOWN (`hours_missing` and `llm_access_reasonableness_unknown`). The three eligible missing-hours contexts were assessed once: two decidable and one UNKNOWN. Model-supported access does not certify API opening hours. V1 daily density penalties are 10/50/10; V2 has 0/10/0; V0/V3 have 0/0/0.

The historical policy-4 Primary retains its original FAIL/UNKNOWN findings, including unresolved Sagrada Família correspondence and Park Güell address mismatch. These were evaluator target-resolution defects, not verified excluded visits. Corrected evidence and judgments were acquired separately; differences cannot be attributed solely to code. Affordability, all qualitative interests and human preference fulfillment remain unverified. No causal version ranking is implied.

## Candidate process and Repair

| Version | Discovered | Admitted | Enriched | Supplied | Scheduled unique places |
| --- | ---: | ---: | ---: | ---: | ---: |
| V1 | 32 | 31 | 24 | 12 | 10 |
| V2 | 16 | 15 | 15 | 12 | 7 |

RAG retrieval was empty; the observed candidate origins were Google. Discovery and supply are bounded-run observations, not city-wide opportunity coverage. One independent source-only review supplied all 96 interest/venue judgments: **4 relevant, 14 not relevant and 78 UNKNOWN**. It did not invent positive labels for missing independent facts. Three independently known relevant places were scheduled in V1 and two in V2; exact thematic conversion totals remain unavailable. Reviewed output and all 45 source citations remain bound to the saved packet and independent snapshots.

The same-run V3 draft had seven primary visits; one deterministic accepted deletion removed Barcelona Cathedral on day 1, leaving six. The six retained activities are unchanged. Repair made zero model calls. Native `coverage_regressions` and `main_visits_lost` flags remain visible. V2 is a separate run and its final is not V3's draft.

The current independent [same-run pair](evaluation/pair/summary.json) uses source-labelled offline imports from the corrected Primary under identity policy 6 and subject policy 2. All 34 identity and 25 fact requests have compatible retained observations. Both stages have zero eligible missing-hours contexts; no access model invocation is required. Original observation times, raw hashes, HTTP receipts and inherited consumption are retained. No Planner judgment is used as independent evidence.

The native pair gives draft **96.6667** and final **100.0000**, with auxiliary scores **100.0000** for both. The average density deduction falls from 3.3333 to zero. Grounding and opening retain six unchanged continued visits and one removed visit; requirements retain two unchanged PASS obligations; routes retain three unchanged legs and one structural leg removal. The compared five-dimensional checks have no FAIL/UNKNOWN at either stage. The Cathedral's grounding and opening were PASS before deletion: removal is not resolution of an old factual failure. The native loss/coverage flags are not erased by the new report.

The paired export and native replay match the selected report. These descriptive diagnostics provide no overall Repair-success classification, controlled experiment, causal version ranking or independent thematic-retention judgment. Qualitative thematic retention remains UNKNOWN.

## Consumption and evidence retention

Six Planner invocations comprise r01 V0 and failed V1 plus the four selected r02 runs. Two separate Primary invocations are retained. No r01 V2/V3 generation or Primary was dispatched.

| Scope | Frozen reference USD |
| --- | ---: |
| r01, including the V1 failure | 0.261204570 |
| r02 V0-V3 generation | 4.466643965 |
| Historical Primary | 1.344814100 |
| Corrected Primary | 1.344929025 |
| Current same-run pair and step-9 verification | 0 |
| Cumulative | **7.417591660** |
| Remaining within USD 30 | **22.582408340** |

Saved all-attempt usage records 28 model calls including embeddings, 314 HTTP sends including model transports, and 260,272 tokens. Repair is a generation subset and is not added again. These are dated retail/proxy references, not invoices. Account totals and external Codex tokens/billing remain unavailable. Unused allowance does not authorize another invocation.

Public schedules preserve the selected `/itinerary` subtrees; each complete Primary file preserves its own saved `/quality` subtree. The complete quality files contain structured findings and raw-observation path/hash references, not the corresponding raw bodies or model request/response envelopes. Raw provider/model payloads, private prompts, author/reviewer transcripts, original receipts, preparations and full V3 lineage remain in ignored storage. Public presentation is not a standalone native execution bundle.

Retained private storage identifiers are `benchmark/scratch/case-08/work/r01/`, `benchmark/scratch/case-08/work/r02/`, `benchmark/scratch/case-08/next-r01/primary/` and `benchmark/scratch/case-08/acceptance-r02/`. These identify evidence rather than published navigation dependencies. Absolute historical preparation bindings remain unchanged.

The retained-evidence archive contains 7,367 logical files in 1,314 content-addressed blobs. Fresh restoration matched every byte/hash. With original case-evidence reads blocked, the restored portable paired export passed native intake and rebuilt the exact selected pair report; restored historical/corrected closed facts verified all 430 Primary receipt entries. The new pair closes another 453 receipt entries. The verified temporary restoration was removed; original evidence has not been deleted or relocated. All 3,308 pre-existing protected source hashes still match.

Both original Primaries replay exactly under their own frozen evaluator implementations (19a4f4d and d3cab59; 90 and 92 implementation-file hashes verified). Current-policy import rejected the old Primary's opening replay; the successful pair instead uses the supported closed-fact/common-subject import of the corrected Primary. Native preparations retain their absolute original bindings; the source worktrees must remain until any separately authorized migration. Archive verification does not relabel those historical preparations as directly relocatable. The current public narrative/index remains in Git; the private archive binds immutable evidence and the portable native pair.

The external-network guard initially interfered with Python SSL imports and Windows asyncio loopback IPC before native execution began. Its local harness was corrected without repository code changes. Exactly one native pair execution started and completed; no consumed package was retried, and no provider/model request was sent.

## Step 10 acceptance decision

| Item | Current disposition |
| --- | --- |
| Original request, source-only requirements, selected schedules and r01 failure | Preserved and source-bound |
| Both Primaries and their genuine FAIL/UNKNOWN findings | Complete, original policies retained |
| Candidate, relevance and Repair structural reports | Complete within disclosed evidence limits |
| Independent common-policy V3 pair and continuity | Complete through source-labelled offline reuse; exact native replay |
| Retained-evidence archive and native restored pair | Verified; original absolute Primary dependencies retained unchanged |
| Researcher final case acceptance and publication | Pending |
| Blinded human review | Deferred separately |

The generic target corrections are integrated through [PR #185](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/185); the paired policy/material compatibility extension is integrated through [PR #187](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/187). Those fixes need no further case-specific code merge. The current case pair uses those integrated contracts; code integration alone never establishes case acceptance.

The former USD 3.10 paid-pair planning reservation was unused. Actual selected pairing has zero current model/Google sends and zero incremental project-provider reference cost; inherited Primary consumption is not charged again.

Step 10 asks the researcher to accept the exact r02 outputs, corrected Primary, current pair, process reports and retained limitations in the [checklist](analysis/acceptance.json). Genuine V0 FAIL, V1 UNKNOWN, partial relevance, unverified affordability/thematic fulfillment and billing gaps remain observations, not unfinished attempts to force PASS. Step 11 human review is deferred. No researcher decision, publication, merge or Issue closure is inferred from completion of steps 1-9. The public view is accompanied by verified private dependencies; it is not a standalone native execution bundle.

## Assistance and history

The researcher approved input, stage scope, budgets and the corrected Primary, but has not yet accepted the final case. Parent Codex `/root` coordinated material, accounting, evidence binding and presentation. It prepared the offline package and completed steps 8-9 using saved files, native import, zero-send pair execution, replay and export. No new independent reviewer or external model was dispatched, and no generation or Primary invocation was added. Paired scoring and deterministic replay are separate from the preserved Primary score histories.

Independent `/root/case08_author`, `/root/case08_requirement_reviewer` and `/root/case08_interests` were dispatched as `gpt-6.1-sol / high`. Their original r01 source-only decisions were reused unchanged for r02. The interest actor's incidental exposure to a historical Sydney summary in PROJECT.md is retained as a limitation; its record says that it did not inform the decisions. The actual relevance reviewer `/root/case08_relevance_review` received only the original input and frozen source-only packet. It inherited parent configuration with no model/effort override; no semantic retry was selected. A Unicode display correction changed neither packet nor judgments.

The r02 execution actor `/root/case08_r02_execution` and corrected-Primary actor `/root/case08_corrected_primary_execution` were dispatched as `gpt-6.1-sol / medium`; each ran only the individually frozen authorized commands. Planner/evaluator calls used configured `gpt-6-luna`; embeddings used the existing deployment. Independent engineering Standards/Spec actors reviewed the committed shared fixes; the paired reviewers inherited parent configuration and supplied no venue-quality judgments. Runtime model proof, complete transcripts, external tokens and billing are unavailable where not explicitly retained. Agent judgments are not human ratings.

r01 used source `b73c8eed09fafb6d54bee8684c5b2e7766515357`. V0 completed; V1 stopped at `ClarificationRequired/unresolved_named_identity` because the original exact-name resolver rejected the provider-standard name. Its authentic failure and consumption remain selected as history. r02 selected four fresh outputs rather than replacing first-attempt records. Two automatic execution refusals preceded process creation and dispatched nothing; subsequent explicit researcher authorization preceded actual calls. Earlier Issue publication refusals remain disclosed in the original record. Steps 8-9 make no Issue write or new live execution attempt.
