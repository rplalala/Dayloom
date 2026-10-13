# Case-01: Sydney evaluation report

The [original request](../inputs/case-01.json) is for Sydney, Australia, on
13-15 October 2026: three days, one traveler and AUD 900 for the whole trip,
with no additional preferences. Generation, independent primary evaluation and
the separately authorized diagnostics completed on 13 October 2026 Sydney time.
These are pre-refactor Repair observations, not an accepted case package.
[Case #127](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/127) remains
open under the [post-refactor acceptance requirements](#post-refactor-acceptance).
Human assessment has not been conducted.

## Post-refactor acceptance

The acceptance boundary established on 13 October 2026 requires all of the following,
in order:

1. The [Repair redesign #139](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/139)
   is implemented and its engineering checks pass.
2. An authorized, scoped case-01 rerun passes its agreed checks. Report the V0-V3
   primary scores and limitations, then wait for the user's instruction before
   supplementary acquisition or mechanism diagnostics.
3. Case-01 results and acceptance documents are updated for the refactored Repair
   and verified. This includes selected itineraries, RAG attribution, actual V3
   draft/final changes, scoring, affected analysis, usage/provenance and material references.
4. The corresponding retained evidence and compact archive are updated and pass
   integrity, restoration and applicable native replay checks. Preserve original
   evidence bytes and prior receipts with distinct run/source bindings; deduplicate
   shared material and remove unnecessary intermediates after verification.
5. The human user explicitly confirms acceptance of that exact updated package,
   including its results and remaining limitations.

[Revalidation #140](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/140)
tracks this work. Until these conditions hold, case-01 remains unaccepted and its
related acceptance Issues remain open. Git push, PR publication or merge, and
engineering checks do not grant acceptance or Issue-closure authority.

Prepare rerun scope, source/date treatment, reuse decisions and budgets separately;
this requirement does not renew exhausted allowances or start execution. Reuse
unaffected material only with compatible inputs, runtime, evaluation semantics and
provenance. Do not silently shift dates, backdate the application clock or present
scripted checks as a real case result. Retain the observations below as historical
evidence until genuine post-refactor outcomes are available.

## Case materials

The [material index](material-index.json) identifies the canonical files, their
publication hashes and their original source hashes/subtree locations. Materials
are retained once; shared content uses relative `$case_material_ref` references
with JSON Pointers as defined in the index. Expanding them recovers the original
JSON values. The publication views are distinct from a closed native replay bundle.

| Material | Files |
| --- | --- |
| Readable itineraries and changes | [V0-V3 schedules, RAG POI labels and V3 draft/final comparison](itinerary.md) |
| Reviewed requirements and interests | [RequirementSpec](requirements/reviewed-requirements.json), [interest inventory](interests/interests.json) |
| Selected itineraries | [V0](generation/v0/itinerary.json), [V1](generation/v1/itinerary.json), [V2](generation/v2/itinerary.json), [V3 final](generation/v3/itinerary.json) |
| Same-run V3 draft | [Lossless draft delta](generation/v3/draft.json) from the final itinerary; apply its `replace` fields after expanding references |
| Recorded generation usage | [V0](generation/v0/usage.json), [V1](generation/v1/usage.json), [V2](generation/v2/usage.json), [V3](generation/v3/usage.json) |
| Producer provenance | [V0](generation/v0/provenance.json), [V1](generation/v1/provenance.json), [V2](generation/v2/provenance.json), [V3](generation/v3/provenance.json); [shared runtime policy](generation/runtime-policy.json) |
| Independent scoring | [Primary quality](evaluation/primary/quality-report.json), [V3 draft/final pair](evaluation/v3-pair/pair-report.json) |
| Candidate process | [Stage memberships, sources and omissions](analysis/poi-process/opportunities.json), [shared V2/V3 RAG origins](generation/rag-origins.json), [relevance applicability](analysis/poi-process/relevance.json) |
| Repair outcomes | [Same-run and four-final comparison](analysis/repair/repair.json) |
| Attempts and resources | [Population](analysis/resources/population.json), [tradeoffs](analysis/resources/tradeoffs.json), [service accounting](analysis/resources/accounting.json) |

The [itinerary view](itinerary.md#v3-draft-versus-final) details the preserved
draft/final difference. Original native provenance/report bindings identify the original
retained source package; they are not rewritten as publication-file bindings.

## Selection and requirements

Batch `case01-20261012T220558Z`, revision `1`, contains one first-dispatched,
completed attempt for each of V0-V3. No retry or replacement was selected.
Run IDs follow `case01-v<version>-20261012T232752Z`; that shared suffix identifies
prospective issuance, rather than each run's actual dispatch time. Original
results, usage, completion, configuration and provenance remain preserved.

Distinct source-only author and reviewer executions produced the RequirementSpec.
Its subjects, obligations, soft preferences and unresolved items are empty.
The independently reviewed POI-interest inventory is also empty. Destination and
generated sightseeing choices do not create unstated user interests.

## Primary scoring

The selected primary report includes one separately approved missing-hours model
assessment. Counts below are PASS / FAIL / UNKNOWN. Overall scores include the
native auxiliary pace adjustment, so perfect observed evidence counts do not
necessarily give an overall score of 100.

| Version | Overall / 100 | Grounding | Opening | Routes | Generation reference USD |
| --- | ---: | --- | --- | --- | ---: |
| V0 | 73.3333 | 8 / 0 / 1 | 7 / 1 / 1 | 4 / 0 / 2 | 0.00241055 |
| V1 | 93.3333 | 8 / 0 / 0 | 8 / 0 / 0 | 5 / 0 / 0 | 1.638289475 |
| V2 | 96.6667 | 7 / 0 / 0 | 7 / 0 / 0 | 4 / 0 / 0 | 1.985985875 |
| V3 | 93.3333 | 8 / 0 / 0 | 8 / 0 / 0 | 5 / 0 / 0 | 2.02191637 |

The initial primary report contained 14 UNKNOWN checks. The supplement resolved
the ten eligible missing-hours checks; four V0 UNKNOWN checks remain across
identity, opening and routes. The V0 opening FAIL remains an observed result.
These independently generated itineraries support a description of this case,
without establishing a causal or version-wide ranking.

## Candidate POI process

| Stage | V1 distinct places | V2 distinct places | V2 gained / V1-only / retained |
| --- | ---: | ---: | --- |
| Discovered | 56, complete | 66 observed, partial | Complete comparison unavailable |
| Admitted | 48 | 48 | 14 / 14 / 34 |
| Enriched | 24 | 30 | 12 / 6 / 18 |
| Supplied | 12 | 12 | 2 / 2 / 10 |
| Scheduled | 8 | 7 | 1 / 2 / 6 |

V2 discovery has 47 observed Google-only, ten RAG-only and nine mixed-source
identities, including ten incremental observed RAG identities. Its complete
discovery count is unavailable. Native memberships retain omissions: 44 observed
discovered places were not supplied in V1 and 54 in V2. Scheduled membership uses
independent identity association and excludes nearby-only references.
Interest relevance is non-applicable because the request states no POI interests.
No corpus measurement was selected; these counts do not establish corpus recall
or isolate a causal RAG effect.

## V3 Repair and independent pair

Generation made one Repair attempt with two model calls. Its proposed Sydney
Tower Eye move was rejected because coverage and pace comparability did not
support accepting it; the draft was retained. Independent draft/final evaluation
found no added, removed or replaced visits and an overall delta of zero.

Each pair stage scored 83.9583 under its own evidence/profile boundary, with
five opening PASS and three opening UNKNOWN checks, eight grounding PASS and
five route PASS checks. This pair's absolute scores are distinct from the selected
primary scores. Primary opening-model verdicts were not imported as raw evidence.
All 31 identity and 23 evidence observations matched primary-evaluation responses
in this case. Valid original generation observations remain retained but were not
needed for these matches. Pair acquisition made no Google/model sends or retries.

V2/V3 independent final differences and the unchanged same-run V3 pair answer
different questions. Neither supports a claim that Repair improved this case.

## Resources and cost basis

| Service bucket | Reference USD |
| --- | ---: |
| V0-V3 generation | 5.64860227 |
| Primary evaluation | 1.262721675 |
| Missing-hours supplement | 0.002489925 |
| Paired acquisition: new service calls | 0 |
| Total | **6.91381387** |

The saved estimate uses dated 13 October 2026 official retail references and a
disclosed OpenAI proxy for Foundry pricing. Actual account rates and invoices are
unavailable. Codex actor token/billing telemetry is also unavailable; zero new
paired service calls does not establish zero Codex cost. Inherited evidence usage,
Repair calls and embedding/HTTP transport subsets are not charged twice.

Across the case, 254 Google sends and 16 model calls were recorded, including two
embeddings. Primary used 59 Google sends and one model call; the missing-hours
supplement used one model call. Six approved paid commands used 327.062 seconds
of active execution within the 3,600-second limit. Ten approved review operations
used 1,188.868426 seconds within their separate limits. A pre-native wrapper parse
failure took 0.455678 seconds and dispatched no provider call.

## System and external assistance

This records the actual case work on 13 October 2026 Australia/Sydney, including
subsequent material preparation. AI within the studied system and external Codex
assistance have distinct roles. The experiment was assisted, not unattended.

| Work | Actual performer | Contribution and influence | Verification or decision |
| --- | --- | --- | --- |
| Generate V0-V3 itineraries, retrieve candidates and propose V3 Repair | Native Planner; configured `gpt-6-luna`, with `text-embedding-3-small` in V2/V3 | Produced the selected outputs and internal judgments; V3 proposed but rejected a change | Native result, usage and provenance bindings; final itineraries were not manually edited |
| Acquire independent primary evidence and assess eligible missing hours | Native evaluator; Google services and its declared `gpt-6-luna / medium` assessments | Produced independent evidence/assessment inputs, including model-assisted V0 identity and the optional opening supplement | Saved snapshots/receipts, preserved FAIL/UNKNOWN and replay; model judgments were not human answers |
| Compute primary scores, paired outcomes and process/resource reports | Native deterministic evaluator/readers with external semantic inputs | Calculated results under the recorded rules; zero new paired service sends | Native integrity/reconstruction and arithmetic checks |
| Author and review requirements | `/root/requirements_author` and distinct `/root/requirements_reviewer`, external Codex | Created and reviewed the native RequirementSpec from the original request; no generated itinerary or score was supplied to either | Two source-only execution records and native handoff; empty additional requirements retained |
| Identify request interests | `/root/interests_reviewer`, external Codex | Confirmed the empty interest inventory; relevance was non-applicable | Source-bound execution record and native interest/relevance validation |
| Supply primary and paired semantic context | `/root/case01_primary_context` and `/root/case01_pair_context`, external Codex | Reviewed schedule/time-zone, route and occupancy associations used by native checks; these inputs can affect evaluation | Separate primary/pair records, pair schema correction and native source validation |
| Launch the six approved paid commands | `/root/case01_executor`, external Codex, `gpt-6.1-sol / medium` | Invoked installed tools sequentially within the selected plan; did not author independent reviews | Original command/completion records and actual resource accounting |
| Implement and check engineering corrections | Parent Codex operator; `/root/case01_standards` and `/root/case01_spec` performed independent code reviews | Corrected corpus-free presentation, source-labelled imports, equivalent departure-time matching and finalized provenance binding | TDD/regression checks, Standards/Spec reviews and corrective rechecks; implementation history preserved |
| Prepare sources, reconcile costs, replay, deduplicate material and write technical reports | Parent Codex operator | Orchestrated the handoff, verified sources and prepared the public account/materials; assistance includes technical documentation | Native report reproduction, source hashes, lossless material checks and tracked links |
| Set substantive intent, approve scope/budgets and decide case acceptance | Human user | Supplied the original request and execution decisions | Automatic acceptance is still pending; real raters have not supplied answers |

Codex assistance was needed because installed tools require reviewed semantic
inputs and explicit operational/source bindings. They do not independently author
the request's RequirementSpec, resolve every semantic association or reconcile
the complete experimental handoff. Engineering defects also needed correction and
checks before the evidence could be consumed consistently. Separate source-only
author/reviewer contexts reduce dependence on Planner outputs; they do not establish
human ground truth or independence between model families. Planner tuning was
outside this case's scope. This record supports later disclosure of development,
experimental annotation, execution and technical-writing assistance. Thesis prose
and final research conclusions were not produced under this case scope.

### Recorded actors and evidence limits

The bounded experimental review ledger records ten external Codex operations,
all `gpt-6.1-sol / high`: requirements author 1, requirements reviewer 1, interests
reviewer 1, primary-context reviewer 1, pair-context reviewer 2 (including its
correction), Standards reviewer 1 and Spec reviewer 3 (including two rechecks).
The separate executor is `gpt-6.1-sol / medium` and launched six paid commands.
These counts are not the total of all AI use across the project or subsequent
parent-operated documentation/storage work.

The retained parent-operator records do not establish its exact model/version,
complete activity duration, tokens or billing. The review transport also lacks
token/billing telemetry and complete internal transcripts; retained task bindings,
operation sidecars and available response excerpts do not imply complete transcripts.
Independent AI reviews and automated tests are recorded as such. Human case acceptance
and blinded human assessment remain separate pending decisions.

Private evidence identifiers are original logical paths in the archive manifest
at `benchmark/scratch/case-01/archive/manifest.json`:

| Record | SHA-256 |
| --- | --- |
| `analysis/resources/actors/operations.json` | `095ffe9501326854f64e8416169e6c9f9fc0385157dd32d48c7457ed3ad7d521` |
| `analysis/resources/commands/executions.json` | `6a6d0892a0e253054fd7c594e2289f915ba379171e870be5788cb4c40a32e983` |

The [case Issue's assistance record](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/127#ai-assistance-and-actual-performers)
contains the public execution/disclosure summary. The
[common recording convention](../README.md#ai-assistance-records) applies to later cases.

## Evidence identity and reproducibility

The execution-era scoring source is
`b3ddccd5b462367d35eff12f8aa9cfe10f840557`; the two corrected provenance-import
modules come from `ee73e274bf1cc5612b3f84605f9efa58feab6c23`. Private replay checks
the exact retained scoring files and adapters. This is a disclosed composed
source runtime, rather than a single-release replay claim.

| Evidence | SHA-256 / native content hash |
| --- | --- |
| Original request bytes | `81fd4a0cec27396d38e759cbcc8ca51e95a5507922ac32cc27c1eff75708de88` |
| Reviewed RequirementSpec bytes | `1a225da333fceb01d0f62bf35807982ad121a27bd10b024918232ab877a80f37` |
| Selected primary quality content | `c8eb50ec6a511fb5bb69106317fed0102f7c558047d53ff0ceecbc6dbbd73057` |
| Same-run pair content | `26d17225b1249b9d99048b03d557f89e30116da673ea0f77ddfe69aabd3aec3f` |

Selected original evidence and required native dependencies are retained in ignored
`benchmark/scratch/case-01/archive/`. The compact archive maps 4,184 original logical
paths to 1,185 unique byte sequences, stored once in a compressed data package.
Including its manifest, restore helper, guide and verification receipt, it occupies
about 6.34 MB, reduced from 348.23 MB of private working material.
Cleanup removed test/preflight trees, compiled caches, assembly scripts, redundant
paired import/working copies, superseded selections and unnecessary source exports.
Authentic generation/evidence captures, reviewed inputs, actor/command/usage
records, selected native reports and their replay dependencies remain retained.

Restoring the archive to a fresh temporary directory verified every retained file's
original hash and length. Network-denied native reconstruction reproduced all five
saved process/resource reports exactly, including their quality and pair dependencies.
The 25 public material entries also matched their restored original selected JSON
values or exact extracted subtrees after expanding shared references. Temporary
restoration and old working directories were then deleted; source evidence bytes,
itineraries and native receipts were not rewritten. This cleanup was authorized
while case acceptance remained pending and does not itself accept the experiment.

The private archive guide provides verify/restore and descriptor-based replay
commands. Original preparations retain historical absolute bindings; their standalone
acquisition commands remain non-portable after relocation. Public views are not
native replay bundles, and full replay requires private archived evidence plus the
repository's installed Python dependencies.

Storage and subsequent execution follow the [common workflow](../README.md).
Future runs report V0-V3 primary scores and pause for the user's instruction
before optional supplements, diagnostics and final case acceptance.
[Workflow #138](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/138)
tracks the workflow acceptance separately from the case decision.
