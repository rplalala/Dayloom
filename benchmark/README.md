# Benchmark workflow and case material

This directory contains 20 English travel-planning requests as working drafts,
not a frozen benchmark set, and provides the final reader-facing entry point for
each case's source-linked generation, evaluation and mechanism-analysis material.
The requests may be revised after inspecting generated itineraries and their
handoff to and processing by the evaluator. Revisions can address scenario choices,
request wording, constraints and dates. Record the rationale, update the scenario
index and affected requirement interpretations, and repeat the relevant offline
checks. Directory placement does not initiate evaluation or certify itinerary quality.

Each file in `inputs/` is a standalone original request for the shared
`planning_request_2` interface. Case IDs belong to filenames and the scenario index,
rather than extra request fields. The schema is defined in
[request.py](../backend/app/schemas/request.py). Budget amounts apply to the whole
group for the entire trip. Pace, walking comfort and lower-cost experiences remain
soft preferences unless the text states an explicit constraint.

The original requests are sent to the planner. Subsequent evaluation material
combines each request with independently reviewed requirements, selected version
results, usage and provenance under the existing
[artifact contract](../docs/contracts/0001-evaluation-artifacts.md).

## Per-case execution and joint review

Prepare and complete cases one at a time in case-ID order, from case-01 to case-20.
Create a scenario child Issue when preparing that case; it tracks request revisions,
attempts, findings and the matched evaluation report. The user confirms automatic
joint acceptance of the input and its declared reports before proceeding to the
next case. Consolidated blinded review follows separately and does not block this
sequence. Native material admission alone does not complete this review; the
[evaluation architecture](../docs/0006-independent-evaluation.md#material-admission-and-scenario-acceptance)
defines the distinct milestones.

[#124](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/124) owns overall
coverage and acceptance status, distinguishing completed automatic case reviews
from the deferred human stage and any later final research acceptance.
[#126](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/126) owns common
operational decisions and child-Issue lifecycle. The
[workflow/layout update plan #138](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/138)
owns adoption and fresh case-01 end-to-end acceptance. This README owns the detailed
reader-facing workflow, responsibility map, optional-study boundary, scenario index,
date rules and directory convention. Case Issues hold live scope, budgets, attempts
and acceptance decisions rather than duplicate the common rules.

The [staged acceptance contract](../docs/contracts/0005-quality-human-review.md#staged-automatic-acceptance-and-deferred-blinded-review)
defines both stages. Preserve each automatically accepted revision and its matched
generation/evaluation evidence for later anonymous packaging. Human answers and
reports bind those exact outputs; they add a separate assessment without replacing
the accepted input, automatic judgments or scores. The current decision defines
the workflow only; formal benchmark execution and real blinded assessment still
require their own explicit authorization.

### Workflow and responsibilities

| Step | Work | Executor | Material or outcome |
| --- | --- | --- | --- |
| 1 | Check input meaning, dates and suitability | Codex; user clarification when needed | Exact original request; stop before a necessary input change. |
| 2 | Author and independently review RequirementSpec | Two distinct source-only Codex agents, `gpt-6.1-sol / high` | Native reviewed spec, real execution records and available authentic task/response transcripts. |
| 3 | Identify interests stated in the original request | Independent agent | Source-bound POI interest inventory; explicit empty interests when none are stated. |
| 4 | Prepare configuration, prices, budgets and capture | Codex | Concrete scope/limits, V1/V2 passive candidate-stage capture and V3 same-run draft/final retention. |
| 5 | Generate V0-V3 sequentially and inspect each outcome | Installed tools, orchestrated by Codex | Selected results, exact sources, actual usage/completion, failure records and required mechanism material. |
| 6 | Independently evaluate final itineraries | Evaluator and applicable independent semantic reviewers | Native qualified four-final material, actual primary report, independent evidence, scores and limitations. |
| 7 | **Candidate POI process analysis (V1-V2)** | Tools and Codex; independent relevance reviewer when interests apply | Discovery/admission/enrichment/supply/scheduled sets, counts and sources; recorded omissions; gained/lost/retained POIs and applicable relevance/conversions. |
| 8 | **Repair process analysis (V2-V3)** | Tools and applicable independent reviewers | V2/V3 final differences, plus same-run V3 draft/final independent evidence, findings, changes, continuity and outcomes. |
| 9 | Reconcile attempts/resources and verify offline | Tools and Codex | All-attempt consumption/completion, explicit missing prices/usage, source consistency and available native replay. |
| 10 | Joint automatic case acceptance | Codex presents; user decides | Accepted exact input/material/reports and limitations; human review deferred, then advance to the next case. |
| 11 | Consolidated blinded review | Codex prepares; real raters answer | Anonymous questionnaires, private mappings, actual answer revisions and separate native human reports. |

Step 7 explores the POI-selection mechanism added between V1 and V2. It retains
the full captured process, not merely a RAG-return/adopted-POI brief table. Count
canonical places once per stage while preserving their real Google/RAG origins,
unresolved entities, recorded omissions and complete/partial/unavailable status.
Nearby-only references do not count as scheduled visits. Independent relevance
labels use original-request interests and independent venue evidence, not Planner
judgments, query labels or similarity. An independently reviewed empty interest
inventory makes relevance non-applicable; the stage/source report remains required.

Step 8 explores validation/Repair added between V2 and V3. Independent version
finals describe observed differences; the same-run V3 draft/final pair traces
actual Repair effects. A V3 draft is not an independent V2 run. Preserve genuine
no-Repair, unchanged, skipped and unavailable observations. Neither process
analysis changes primary scoring or establishes causal improvement from independent
generations. Source contracts remain authoritative for report arithmetic and units.

### User intervention and execution boundaries

After an explicit start instruction and concrete authorized scope/numeric budgets,
Codex advances steps 1-9 without repeated permission for covered tool or agent
operations. The user supplies substantive clarification for blocking personal
intent, approves necessary input changes or uncovered work/budget, decides step 10
and selects the later human assessment. Real raters must actually read the anonymous
material and answer; approval and agent inspection do not substitute for responses.

Resolve routine issues within the authorized scope. Stop when execution is paused,
required personal meaning cannot be established, access is restricted, limits are
reached, or a defect cannot be resolved without changing scope. No automatic retries,
budget increases or silent input edits are implied. Genuine low scores, FAIL,
UNKNOWN and no-Repair outcomes remain observations for joint acceptance. Separate
generation, independent-agent, evaluator and paired-acquisition consumption;
unknown prices or missing usage are not zero. Before a full regression, explain
the reason and expected duration. Git delivery and version/research authorization
retain their existing boundaries.

### Optional work compared with the initial plan

| Work | Current boundary |
| --- | --- |
| Corpus measurement and eligible-entity census | Optional study; no default database-wide scan or generation/acceptance gate. |
| Corpus coverage sidecar export | Optional with the selected corpus study; not needed for candidate-process analysis. |
| Corpus geography/strata/sample coverage reports | Optional study; ordinary process reports omit corpus sections and make no corpus-denominator, city-coverage or recall claim. |
| Suite integration (#106/#118) | Remains optional; standalone native reports suffice. |
| Controlled Repair experiments | Remain outside the ordinary per-case workflow unless explicitly selected. |
| Human assessment timing | Deferred to step 11; not an automatic-case closure gate. It remains actual human work when selected. |

Detailed candidate-stage reporting (#114), applicable independent relevance within
step 7 (#115 without corpus reporting), Repair/pair diagnostics (#116), and attempt/
resource accountability (#113/#117) remain in the automatic workflow. V1/V2 passive
candidate capture is a different file from a corpus-measurement sidecar and must be
enabled before generation. Existing corpus tools remain available; optional means
not selected by default, not deleted or disabled. Retain runtime RAG source and
configuration identity without requiring a separate corpus scan.

Installed tools provide the native captures, intake and reports. Corpus-free
relevance presentation omits corpus sections unless coverage material or a profile
is explicitly selected. The final-case handoff remains tracked in #138; no general
directory-assembly command is implied. Source-labelled paired evidence reuse is
available through the [installed import flow](../backend/evaluation/README.md#installed-paired-acquisition).

## Layout

```text
benchmark/
  README.md
  .gitignore
  inputs/
    case-01.json
    ...
    case-20.json
  <case-id>/
    input.json
    requirements/                 # step 2: spec and actual author/reviewer records
    interests/                    # step 3: source-bound independent inventory
    material/                     # complete native finalized batch root/manifest
    generation/                   # steps 4-5: selected captures and configuration
      configuration/
      v0/
      v1/
      v2/
      v3/
    evaluation/                   # steps 6 and 8: native evidence/reports/receipts
      primary/
      v3-pair/
    analysis/                     # steps 7-9: native reports and bound dependencies
      poi-process/
      repair/
      resources/
    human/                        # step 11 only; absent before human preparation
      packages/
      private/
      answers/
      reports/
```

The `inputs/` files are tracked source requests. `benchmark/<case-id>/` presents
only the currently selected complete acceptance package, without visible `r1/r2`
or `a1/a2` layers and without an ambiguous generic `reviews/` directory. Native
revision, run/attempt IDs, source hashes and schema fields remain inside artifacts;
omitting folder layers does not remove source identity or authorize overwrites.

`requirements/` retains the actual author draft, reviewed final, handoff and
execution/transcript material; `interests/` retains the independent inventory and
its record. Candidate relevance labels/evidence accompany `analysis/poi-process/`;
other semantic review inputs accompany their corresponding evaluation. Native
`opportunities` and applicable `relevance` outputs belong under POI process analysis,
native `repair` under Repair analysis, and population/tradeoff/resource views under
resources. Keep native file names and dependency layout; required declarations,
registration or paired export files may supplement this map.

Each selected generation retains its result, usage, provenance, dispatch/completion,
configuration and actual capture; V1/V2 also retain candidate-stage evidence and V3
retains the same-run draft/final. The full package includes verification evidence,
not just final itinerary JSONs. Original preparation and failed/nonselected attempts
stay in local `artifacts/`, with resource accounting and source dependencies needed
for replay, rather than cluttering the final-case view.

`human/packages/` holds anonymous questionnaires and presentation; `private/` holds
researcher-only mappings that are not delivered to raters; `answers/` and `reports/`
hold actual responses and native human reports. Create these only when the later
human stage starts. The live acceptance decision remains in the case and parent
Issues, not a competing local status file. No corpus directory is created by default.

## Scenario index

Dates and durations are inclusive. The initial date assignment uses 2026-10-11 as
the policy reference date. All trips start on 2026-10-13 except case-05, which starts
on Saturday 2026-10-17 and ends on Sunday 2026-10-18.

| Case | Category | Destination | Days | Travelers | Group budget | Scenario and design rationale |
| --- | --- | --- | --- | --- | --- | --- |
| [01](inputs/case-01.json) | Basic request | Sydney | 3 | 1 | AUD 900 | Empty preferences for a solo traveler; checks ordinary destination planning from structured fields alone. |
| [02](inputs/case-02.json) | Basic request | London | 3 | 2 | GBP 1,200 | Empty preferences for two travelers in a different destination; adds geographic and group-size variation to basic requests. |
| [03](inputs/case-03.json) | Travel preferences | Tokyo | 4 | 2 | JPY 160,000 | First-time visit with traditional culture and modern neighborhoods; checks balanced introductory sightseeing at a moderate pace. |
| [04](inputs/case-04.json) | Travel preferences | Paris | 4 | 2 | EUR 1,400 | Art, architecture and riverside walks; checks a coherent mix of indoor visits and outdoor sightseeing. |
| [05](inputs/case-05.json) | Travel preferences | Singapore | 2 | 2 | SGD 800 | A fairly full weekend using public transport; checks use of limited time without an explicit daily stop quota. |
| [06](inputs/case-06.json) | Travel preferences | Barcelona | 5 | 1 | EUR 1,300 | Solo architecture and art travel at a relaxed pace; checks depth and time at places rather than many daily stops. |
| [07](inputs/case-07.json) | Explicit constraints | Tokyo | 3 | 1 | JPY 90,000 | Repeat visitor seeking less familiar places while excluding Senso-ji Temple and Tokyo Skytree; checks exclusions alongside positive interests. |
| [08](inputs/case-08.json) | Travel preferences | London | 5 | 2 | GBP 1,800 | History, science and substantial museum visits with park walks; checks longer visits and relaxed pacing with little shopping interest. |
| [09](inputs/case-09.json) | Travel preferences | Sydney | 4 | 3 | AUD 2,200 | Two adults and a child prefer science, nature, breaks and driving; checks family preferences together with transport intent. |
| [10](inputs/case-10.json) | Travel preferences | Singapore | 3 | 3 | SGD 1,500 | Two adults and an older family member prefer nearby stops and less continuous walking; checks comfortable grouping without medical assumptions. |
| [11](inputs/case-11.json) | Travel preferences | Paris | 3 | 1 | EUR 650 | Lower-cost parks, neighborhoods and exterior architecture, with a few paid visits; checks cost-conscious selection without inventing a numeric quota. |
| [12](inputs/case-12.json) | Explicit constraints | Barcelona | 3 | 2 | EUR 1,000 | Exactly one Sagrada Familia visit and no Park Guell visit; checks required and excluded places together. |
| [13](inputs/case-13.json) | Explicit constraints | Sydney | 5 | 2 | AUD 2,200 | Exactly one Sydney Opera House visit with flexible surrounding choices; isolates a single required place. |
| [14](inputs/case-14.json) | Explicit constraints | Tokyo | 5 | 3 | JPY 300,000 | Ueno Park exactly once on day two and Tokyo National Museum exactly once on a flexible date; checks different date scopes for two required places. |
| [15](inputs/case-15.json) | Explicit constraints | London | 7 | 1 | GBP 2,200 | Exactly two British Museum visits on different dates; checks deliberate repetition rather than accidental duplicate visits. |
| [16](inputs/case-16.json) | Explicit constraints | Paris | 4 | 2 | EUR 1,500 | A two-hour online meeting block on day two; checks protection of both activities and travel within a local-time interval. |
| [17](inputs/case-17.json) | Explicit constraints | Singapore | 3 | 2 | SGD 1,100 | Exactly one National Museum of Singapore visit on day two, with a flexible preference for about 10:00 and 90 minutes; checks a dated required visit alongside soft timing preferences. |
| [18](inputs/case-18.json) | Travel preferences | Tokyo | 7 | 2 | JPY 300,000 | Modern art and design are the main focus, complemented by gardens and neighborhoods; checks interest priority across a fairly full longer trip. |
| [19](inputs/case-19.json) | Explicit constraints | Sydney | 7 | 2 | AUD 3,200 | An explicit day-one target of exactly one sightseeing visit and a full rest day on day four; checks dated pace/count guidance alongside whole-day protection. |
| [20](inputs/case-20.json) | Explicit constraints | Barcelona | 7 | 4 | EUR 4,200 | Two pairs have different interests, with one required place and a protected afternoon; checks a realistic combination of group preferences and constraints. |

The current draft contains two basic requests, nine preference scenarios and nine
explicit constraint scenarios. Eight trips last two or three days, eight last four or five
days, and four last seven days. Sydney and Tokyo have four cases each; London,
Paris, Singapore and Barcelona have three each. Similar interests appear with
different planning needs; the cases are not matched experimental pairs.

## Date update rules

The planner's shared [date policy](../backend/app/policies/trip_dates.py) uses the
application's configured time zone. On each execution date, the complete requested
range must fall between that day's date and 13 days later, inclusive, and trips
must last at most ten inclusive days. For reference date 2026-10-11, the allowed
window is 2026-10-11 through 2026-10-24.

1. Choose dates for the planned execution period and validate them against the
   actual application reference date. A later execution can invalidate an earlier
   assignment even when its JSON still passes schema validation.
2. Preserve each trip's duration and the relationships below. Update both the
   structured dates and every explicit date in `additional_preferences` together.
3. A common shift by a multiple of seven days preserves the initial weekdays.
   With another shift, assign case-05 a Saturday-to-Sunday interval separately;
   do not turn its weekend request into a weekday trip.
4. Keep local clock times and their destination-local meaning unchanged. Recheck
   official opening information for required places on the new dates, especially
   fixed-time visits. Date updates must not silently change interests, budgets,
   party sizes, visit counts or exclusions.
5. Before execution, review and record the resulting input revision. All compared
   versions must receive the same original request for each case. Once a request
   has been used, retain its exact bytes with the run material; later edits form a
   new revision rather than altering earlier evidence.

| Case | Relationship to preserve |
| --- | --- |
| 05 | Two consecutive days: Saturday and Sunday. |
| 14 | Ueno Park on day two, exactly once; Tokyo National Museum exactly once on a suitable date within the trip. |
| 16 | Day two: no planned activities or travel from 14:00 to 16:00, Paris local time. |
| 17 | Day two: exactly one museum visit during the trip. About 10:00, Singapore local time, and about 90 minutes are flexible preferences. |
| 19 | Day one: explicit pace/count target of exactly one sightseeing visit; day four: no planned activities or travel. |
| 20 | Day two: no planned activities or travel from 15:00 to 18:00, Barcelona local time. |

## Offline checks

After edits, parse all 20 files as UTF-8 JSON, validate each using
`PlanningRequest.model_validate_json`, and separately validate its dates using
`create_trip_date_window` and `validate_requested_trip_dates` with an explicit
reference date. Schema validation alone does not enforce the moving date window.

Check that the filenames cover case-01 through case-20 exactly once, the index
agrees with destination, duration, traveler count and budget, and the dated
preferences retain the relationships above. Also check that local index links
resolve. These checks are offline and do not invoke the planner or establish
itinerary feasibility, ticket availability or evaluation results.

## Accepted case bundles

### Admission

Admit a case only after its complete original request, independently authored and
reviewed RequirementSpec, selected V0-V3 results, usage envelopes, provenance and
producer completion declarations pass native intake. Usage may explicitly be
unavailable under the existing contract. Preserve FAIL and UNKNOWN outcomes; material
acceptance is distinct from scoring PASS.

Use the existing [material handoff](../backend/evaluation/README.md#installed-generation-and-material-handoff)
and [artifact contract](../docs/contracts/0001-evaluation-artifacts.md) for schemas,
qualification, source bindings and integrity checks. This directory adds a storage
convention, not another acceptance schema or an automatic admission command.

### Bundle handling

The referenced subdirectory names are preserved from the finalized material;
readers use manifest references rather than infer files from this example. An accepted
case revision contains one request group and its four selected version runs. Keep case
and run IDs unique when explicitly assembling a later multi-case evaluation batch.

For new material, point `rtpeval batch finalize --directory` at a fresh
`benchmark/<case-id>/material/` destination. Fix generation/evaluation paths before
execution, or copy a complete source-bound root before preparing its consumers.
For an existing accepted bundle, copy its complete batch root without changing
bytes or relative paths, retain the original evidence, and run `rtpeval validate`
against the copied manifest. Do not move existing prepared evaluation runs: their
bindings include original absolute paths. Reference roots must contain the files
they declare; this directory map never permits path escape or digest rewriting.

Accepted sources are immutable. Changed input/source material requires new native
identities and affected validation even though the reader-facing folder has no
revision suffix. Never overwrite a consumed native output directory; prepare a
fresh working root and update the current-case view only after a valid handoff.
Retain required earlier dependencies and all-attempt consumption. Delete old work
only under an explicit reset/cleanup instruction, without claiming it still
establishes readiness or replay. A reset does not alter unrelated engineering work.

Selected primary/paired evidence and process reports belong in the corresponding
case directories above, with explicit fresh native destinations. Later human
material binds the same accepted outputs and does not overwrite them. Preparation,
failed/nonselected work and optional controlled studies remain outside the selected
package in local `artifacts/`. Evaluation never automatically scans or runs every
case in this directory.

### Git storage

Accepted case bundles are ignored by Git; this README, the local ignore rules
and the original request JSON files in `inputs/` are tracked. Keep private prompts
and raw provider/model payloads out of commits. Shareable acceptance summaries
belong in the existing `docs/records/` owners. A source request is not an accepted
case bundle; case admission follows the rules above.
