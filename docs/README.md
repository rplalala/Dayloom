# Core design documentation

[PROJECT.md](../PROJECT.md) owns current scope and authorization. Start with the
[project proposal](proposal.md), then read the responsibility relevant to your task.
These core files consolidate current behavior; development diaries do not
belong in this directory. Task specifications and iteration state live in GitHub Issues.

[Domain terminology](../GLOSSARY.md) defines Repair exploration and final selection.

## Core designs

| Owner | Contents |
| --- | --- |
| [0001 System architecture](0001-system-architecture.md) | Layers, Product V3, independent V0-V3 and lifecycle |
| [0002 Requirements and evidence](0002-requirements-evidence.md) | Interpretation, source provenance, semantic policy and supply |
| [0003 Itinerary and transport](0003-itinerary-transport.md) | Primary/reference roles, transport ownership and uncertainty |
| [0004 Retrieval (V2/V3)](0004-retrieval-persistence%28v2v3%29.md) | Corpus, persistent exact search and compatibility |
| [0005 Validation and repair (V3)](0005-validation-repair%28v3%29.md) | Permissions, components, re-validation and adoption |
| [0006 Independent evaluation](0006-independent-evaluation.md) | Native quality, research populations and track boundaries |
| [0007 Application and operations](0007-application-operations.md) | Product account/task/preview/trip lifecycle, API/UI and operational verification |

The accepted [Dayloom r7 unified Product specification #198](https://github.com/rplalala/Dayloom/issues/198)
connects the provisionally accepted frontend prototype with accounts, drafts, tasks,
previews and manual saving. The [application contract](0007-application-operations.md#product-experience-and-persistence-design)
owns implemented behavior and links its acceptance evidence. Native child Issues own
the thirteen-slice implementation state; #119 retains the historical mapping.

## Architecture decisions

- [0001 Version isolation](adr/0001-version-isolation.md)
- [0002 Application-owned transport](adr/0002-transport-ownership.md)
- [0003 Persistent exact retrieval (V2/V3)](adr/0003-persistent-exact-retrieval%28v2v3%29.md)
- [0004 Independent evaluation](adr/0004-independent-evaluation.md)

These ADRs record established consequential decisions, not a new implementation or freeze.

## Detailed technical contracts

Evaluation has five consolidated contract references: [artifacts](contracts/0001-evaluation-artifacts.md),
[intake/identity/usage](contracts/0002-intake-identity-usage.md),
[requirements/schedule](contracts/0003-requirement-schedule.md),
[opening/routes](contracts/0004-opening-routes.md), and
[quality/human review and V3 pairs](contracts/0005-quality-human-review.md).
These are continuous current rules with one owner per topic. Important decisions, results and limitations remain in topic histories and linked Issues;
legacy deep links resolve
to the corresponding current topic. Implementation status stays explicit in the evaluation
core design. Read only relevant contract sections.

The [version-specific identity contract](contracts/0002-intake-identity-usage.md#version-specific-identity-requirement)
owns deterministic V1-V3 API checks and V0-only model correspondence; historical uniform
LLM reports retain an explicit replay path.

The [offline research guide](../backend/evaluation/README.md#installed-offline-research)
locates installed commands, original-input/generation material preparation and
report outputs. The [suite research attachment flow](../backend/evaluation/README.md#optional-research-attachments-and-offline-refresh)
locates optional integrated reports, append revisions and offline replay; detailed
definitions remain in the topic contracts above.
The [paired access refresh](records/evaluation/v3-pair-report.md#paired-access-refresh-2026-10-17)
records the common two-stage policy's implementation, bounded calls and current
case-01–07/09 outcomes, while original primary evidence and acceptance dates remain intact.
The [combined offline acceptance](records/evaluation/intake-identity-usage.md#post-integration-offline-acceptance-2026-10-12)
records main-worktree verification and the boundaries of reused regression evidence.
The [accepted-case compatibility audit](records/evaluation/accepted-case-compatibility.md)
checks all twelve accepted selections against the 18 October integrated code,
separating unchanged saved-material calculations from source-bound policy upgrades
and the completed bounded generation/Primary checks. It also records the authorized
completed direct replacement for 04/05/09/11, matched dependent analyses,
canonical input alignment, bounded consumption and retained evidence limitations.
The [case-04 Rich-policy Primary](records/evaluation/2026-10-24-rich-primary.md)
records one new V3 reaching three visits per day, a fresh four-final evaluation and
the application-completion limitation; replacement acceptance remains separate.
The [post-generation review readiness contract](contracts/0002-intake-identity-usage.md#post-generation-review-readiness)
separates missing output-specific review work from completed unresolved judgments
before primary acquisition, without changing Planner generation or score policies;
the [engineering acceptance](records/evaluation/intake-identity-usage.md#post-generation-review-readiness-2026-10-15)
records the saved-case checks and synthetic-control limits.

[Phase-2 activity semantics](0003-itinerary-transport.md#activity-semantics-contract-phase-2)
implements explicit roles/time use and a separately versioned numerical-population
profile approved on 2026-10-16. Its [accepted-case impact audit](records/evaluation/intake-identity-usage.md#activity-semantics-design-and-accepted-case-audit-2026-10-15)
records the five selections accepted at the audit cutoff and case-07's actual
supplementary review. The approved implementation and the subsequently accepted
[case-07 revision](../benchmark/case-07/report.md#acceptance) are delivered through
[PR #174](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/174) under
[Issue #172](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/172).
Historical results retain their original contracts and scores; this integration
does not refresh accepted datasets.

## Other responsibilities

- [Final benchmark report](../benchmark/report.md): completed comparison of the
  12 accepted cases, with final ranking **V3 > V2 > V1 > V0**, separate evaluation
  results, reasons for differences and selected-run cost/time trade-offs. The
  V1/V0 distinction is weak; the report states the historical policy boundaries.
- [Blinded-review report](../benchmark/blinded-results/report.md): completed human
  and GPT-6.1 sol xhigh assessments, dimension and task-level rankings, agreement
  and differences. The accepted English/Chinese questionnaires and separate answer
  exports are retained beside the report. [#196](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/196)
  records completed publication of both reports and the final review artifacts.
- [Benchmark workflow and case material](../benchmark/README.md): accepted datasets,
  public itinerary views, source-linked reports, private archive boundaries,
  optional studies and historical ID mappings. [#124](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/124)
  owns completed dataset acceptance; [#126](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/126)
  owns the shared execution and child-Issue rules.
- [AI assistance records](../benchmark/README.md#ai-assistance-records): actual
  performers, contributions, validation and evidence gaps for later thesis disclosure;
  [case-01](../benchmark/case-01/report.md#system-and-external-assistance) records the
  observed work, with its case Issue owning the public decision/disclosure summary.
- [Development commands](guides/development.md) and [runtime configuration](../config/README.md).
- [Historical records](records/README.md): milestone freezes, development evidence,
  topic-specific validation and benchmark-design history. They do not override core design.
- [Agent entry point](../AGENTS.md) routes to [task/Git/skill workflow](agents/workflow.md),
  [version lifecycle](agents/versions.md) and [live smoke delegation](agents/smoke-tests.md).
  [Tracker conventions](agents/issue-tracker.md), [triage labels](agents/triage-labels.md)
  and [document ownership/archive rules](agents/domain.md) configure the engineering skills.

For documentation maintenance, use [AGENTS.md](../AGENTS.md#documentation).
Historical records summarize decisions and evidence; they are not prerequisites for
understanding current behavior. Local artifact identifiers in records locate retained
evidence but do not replace the public explanation or command guides.
