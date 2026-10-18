# Benchmark workflow and case material

The active set contains 12 English travel-planning requests in four groups of three. Pending inputs remain
working drafts; directory placement does not freeze the set. Each public case
directory contains a reader-facing report and selected source-linked materials
without duplicate copies. Raw capture,
preparation and execution work stays in ignored `scratch/<case-id>/` storage;
after review, this becomes a compact private archive rather than a permanent
collection of every temporary working directory.
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

Cases may progress concurrently in coordinator-assigned worker queues. Each case
has its own child Issue tracking request revisions, attempts, findings and matched
reports; children may be prepared together for an approved batch. Queue order is
local to its worker, not a dependency between workers. The user explicitly accepts
each exact input/report selection; another case can progress while that decision
is pending. Consolidated blinded review follows separately. Native material
admission alone does not complete automatic acceptance; the
[evaluation architecture](../docs/0006-independent-evaluation.md#material-admission-and-scenario-acceptance)
defines the distinct milestones.

[#124](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/124) owns overall
coverage and acceptance status, distinguishing completed automatic case reviews
from the deferred human stage and any later final research acceptance.
[#126](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/126) owns common
operational decisions and child-Issue lifecycle. The
[workflow/layout update plan #138](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/138)
owns workflow adoption and case-01 end-to-end acceptance. This README owns the detailed
reader-facing workflow, responsibility map, optional-study boundary, scenario index,
date rules and directory convention. Case Issues hold live scope, budgets, attempts
and acceptance decisions rather than duplicate the common rules.
[Parallel batch #151](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/151)
owns active case-03 through case-12 and their native case children, including the
[historical ID mapping](#selection-revision).

### Parallel sessions and integration

The coordinator uses the existing main worktree. Each worker uses an independent
managed worktree created from the same recorded latest delivered commit. Record
that starting revision and any subsequently integrated workflow/shared-fix commits;
new runtime changes require compatible preparation and affected checks before use.
Keep one active case per worker. V0-V3 generation remains sequential within a case;
independent workers may run concurrently within centrally approved limits.

| Worker | Assigned queue |
| --- | --- |
| A | 03, 09 |
| B | 04, 12 (former 14; Issue #163) |
| C | 05 |
| D | 06, 08, 10 |
| E | 07, 11 |

These are ownership queues, not active-process or live-run assignments. Retired
worker worktrees need fresh qualified setup before future execution. Former
case-12/13/15 are historical selections, not further queue work.

Workers own their assigned `inputs/case-XX.json`, public `case-XX/` and ignored
`scratch/case-XX/` paths and case Issues. Input changes still need their applicable
approval. The coordinator owns shared workflow/index documents, application code,
runtime configuration, dependency files, overall Issues and integration. Proposed
shared fixes return to the coordinator for scoped work. Existing case-01–07 inputs,
results and private archives remain unchanged.

Before a worker is ready, rebuild its own `.venv` from the pinned `uv.lock`, including
retrieval/development dependencies; copying another worktree's environment can
retain incorrect editable imports and CLI paths. Migrate required local ignored
environment files, both checksum-verified tokenizer vocabularies and the retrieval
manifest/completed-build metadata used by V2/V3. Keep database connection settings
bound to the existing query-only corpus. Verify settings, local import/CLI paths,
schemas, cache checksums and applicable read-only database compatibility without
model/Google requests. Keep credentials, caches and private material out of Git,
Issues and public handoffs. Recheck configuration and accessibility before dispatch.

The coordinator records per-case/stage budgets and aggregate concurrency/resource
allowances in the batch Issue before live dispatch. A worker proceeds only within
an explicitly covered start/continuation scope. A primary-score pause, blocked case
or pending acceptance affects that case; it does not stop unrelated workers.
Within each worker, continue the assigned queue after acceptance unless an explicit
batch instruction covers a different progression. Prepared sessions wait for the
coordinator; setup alone does not start reviews, generation or paid acquisition.

Return the starting/head commits, owned changed paths, case Issue/status, exact
source bindings, completed checks, resources/limits and private archive locations.
Distinguish primary completion, further analysis, user acceptance and readiness for
integration. After all assigned work is complete, the coordinator integrates reviewed
worker commits into the main worktree, resolves conflicts and runs affected offline
checks. Preserve original implementation and correction commits. Resolve overlapping
shared edits by their current authority, not by blindly selecting one side; verify
accepted sources against recorded byte hashes before and after integration.

Git integration does not transfer ignored evidence. Preserve its source-bound roots
under the [bundle handling](#bundle-handling) and [private archive rules](#private-archive-retention)
until native dependencies, absolute-path preparations and restored archive replay
are accounted for. Worker worktrees can be archived only after needed ignored
material is preserved and verified. Git publication and human acceptance retain
their separate authorization and completion meanings.

### Accepted selections

Automatic case acceptance applies only to the exact selection and limitations in
its linked report. Decision dates use Australia/Sydney. User-authorized current-data
replacement preserves the previous selection and acceptance as history, while
updating the canonical generation, scoring and reader views together. Original
native evidence and frozen receipts remain immutable; dependent analyses must match
the replacement sources or explicitly retain historical/pending status.
Git publication and Issue closure require their own authorization. Separate Repair engineering diagnostics do
not contribute to case scores. Blinded human assessment is deferred.

| Case | Researcher acceptance date | Accepted selection and limitations |
| --- | --- | --- |
| 01 | 2026-10-14 | [Initial Sydney dataset](case-01/report.md#acceptance) |
| 02 | 2026-10-14 | [London selection](case-02/report.md#acceptance-and-material) |
| 03 | 2026-10-15 | [Tokyo selection](case-03/report.md#acceptance-status) |
| 04 | 2026-10-15 | [Singapore selection](case-04/report.md#acceptance) |
| 05 | 2026-10-16 | [Barcelona revision 3 / input revision 2, integrated CLI GBK and Repair timing corrections](case-05/report.md#acceptance) |
| 06 | 2026-10-15 | [Sydney family revision 5](case-06/report.md#acceptance-and-selected-material) |
| 07 | 2026-10-16 | [Paris revision 3 / input revision 2, with partial discovery, relevance UNKNOWNs and unverified affordability](case-07/report.md#acceptance); [delivery PR #174](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/174) |
| 08 | 2026-10-17 | [Barcelona r02 selection](case-08/report.md#acceptance), completed same-run pair, retained FAIL/UNKNOWN, partial relevance and unverified affordability; [PR #188](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/188) merged; #157/#182 completed; blinded review deferred |
| 09 | 2026-10-17; current data updated 2026-10-18 | [Tokyo current selection](case-09/report.md#acceptance): replacement V0/V1, exact accepted V2/V3 donors and fresh current-policy Primary; V3 pair retained on its unchanged source; new V1 process/relevance joins incomplete |
| 10 | 2026-10-17 | [London revision 2, exact-two British Museum visits on distinct dates, retained time/access uncertainty, relevance UNKNOWNs and unverified affordability](case-10/report.md#acceptance-status) |
| 11 | 2026-10-17; current data updated 2026-10-18 | [Paris current selection](case-11/report.md#acceptance): replacement V3 with one Repair round, exact accepted r02 V0–V2 donors and fresh current-policy Primary; protected interval passes; old no-Repair pair is historical, with no independent pair for the replacement V3 |
| 12 | 2026-10-17 | [Sydney r07, with partial discovery/relevance, model-supported access, transport/cost uncertainty and historical accounting limits](case-12/report.md#acceptance); [PR #190](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/190) merged; #163/#184 completed; main synchronized and private-evidence migration verified; blinded review deferred |

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
| 6 | Independently evaluate final itineraries | Evaluator and applicable independent semantic reviewers | Qualified four-final material and reviewed context; independent identity/evidence, eligible missing-hours access assessment, then one final primary calculation; report each version and pause. |
| 7 | **Candidate POI process analysis (V1-V2)** | Tools and Codex; independent relevance reviewer when interests apply | Discovery/admission/enrichment/supply/scheduled sets, counts and sources; recorded omissions; gained/lost/retained POIs and applicable relevance/conversions. |
| 8 | **Repair process analysis (V2-V3)** | Tools and applicable independent reviewers | V2/V3 final differences, plus same-run V3 draft/final independent evidence under the [common paired access policy](../docs/contracts/0005-quality-human-review.md#v3-pairs), findings, changes, continuity and outcomes. |
| 9 | Reconcile attempts/resources and verify offline | Tools and Codex | All-attempt consumption/completion, explicit missing prices/usage, source consistency and available native replay. |
| 10 | Joint automatic case acceptance | Codex presents; user decides | Accepted exact input/material/reports and limitations; human review deferred, then follow the worker's covered queue instruction. |
| 11 | Consolidated blinded review | Codex prepares; real raters answer | Anonymous questionnaires, private mappings, actual answer revisions and separate native human reports. |

Steps 7-9 begin only after the user instructs continuation following the primary
score handoff. Step 6 includes [eligible missing-hours access assessment](../docs/contracts/0004-opening-routes.md#missing-hours-access-judgment)
within its prepared model, pricing and execution allowance, before final scoring.
No eligible visits means no assessment call. An explicitly selected API-only run
records that assessment is disabled. Supplemental rescoring remains available for
historical API-only material or corrections, rather than a normal second scoring stage.

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

### AI assistance records

The workflow table describes intended responsibilities. Each case's public
`report.md` must separately record the work and its **actual performer**, including
external AI assistance. Its case Issue holds the current disclosure summary and
pending human decisions. This provides evidence for later thesis AI-use disclosure;
it is not a substitute for the institution's applicable submission requirements.

Distinguish AI calls inside the studied Planner/evaluator from external Codex help
with development, testing, experimental judgments, orchestration and documentation.
For each material contribution, retain:

- The work, purpose, actual human/tool/agent identity and verified model/configuration
  where available; dates, operation IDs and source revisions identify its scope.
- The inputs made available to that actor, the output used and whether it influenced
  code, reviewed semantic inputs, evidence interpretation, selection or presentation.
- The actual review or validation performed, including who made the human decisions.
  Separate agents and automated checks do not establish real human review.
- Source/evidence identifiers and known gaps. Missing model identity, complete
  transcripts, token counts or billing remain unavailable rather than inferred.

Record actual assistance and corrections even when the final itinerary is unchanged.
Explain why external assistance was needed and which decisions still required the
researcher. Maintain the case report and Issue in place as later work occurs; do
not generate an extra disclosure document for every operation. Private original
records remain retained for verification without publishing prompts, credentials
or raw provider/model responses. Public documentation links only to tracked sources
or accessible remote evidence. Before repository publication, the Issue gives a
self-contained account rather than linking unpublished files or local commits.

### User intervention and execution boundaries

After an explicit start instruction and concrete authorized scope/numeric budgets,
Codex advances through primary scoring in steps 1-6 within that scope. After
reporting the V0-V3 primary scores, FAIL/UNKNOWN findings and limitations, pause
and wait for the user's next instruction before separately selected studies, mechanism
analysis or final case acceptance. Covered operations within a subsequently
authorized stage need no repeated approval. The user supplies clarification for blocking personal
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

For all current and subsequent cases, the [paired contract](../docs/contracts/0005-quality-human-review.md#v3-pairs)
defines the common missing-hours access policy for both V3 stages. A refresh updates the
current paired view and its source mappings in place, while preserving original
generation, primary scores, receipts and historical reports. Eligible model
assessment requires covered execution authorization; ordinary offline report import
does not call a service. Section-derived Repair views identify current same-run
sources separately from preserved historical four-final sources. The
[17 October refresh](../docs/records/evaluation/v3-pair-report.md#paired-access-refresh-2026-10-17)
covers cases 01–07 and 09; case-09's [automatic acceptance](case-09/report.md#acceptance)
retains the refreshed pair and disclosed limitations, with blinded review deferred.

## Layout

```text
benchmark/
  README.md
  .gitignore
  inputs/
    case-01.json
    ...
    case-12.json
  history/2026-10-16-selection/    # retired original inputs, not active cases
  <case-id>/
    report.md                     # reader-facing observations and material links
    itinerary.md                  # daily schedules, POI origins and draft/final changes
    material-index.json           # canonical paths, hashes and original sources
    requirements/
    interests/
    generation/                   # selected final V0-V3 and their metadata only
      v0/
      v1/
      v2/
      v3/                         # selected final itinerary, usage and provenance
    evaluation/
      primary/
      v3-pair/
    analysis/
      poi-process/
      repair/                     # V3 draft/final-primary, lossless differences, mechanism
      resources/
      history/                    # retained earlier public observations and failures
  scratch/
    <case-id>/                     # ignored private storage
      work/                        # active execution/preparation and temporary files
      archive/                     # compact long-term evidence after cleanup
        README.md                  # retention and offline restoration instructions
        manifest.json              # original logical paths, SHA-256 and lengths
        blobs.zip                  # one compressed copy of each unique byte sequence
        archive.py                 # standard-library verify/restore helper
        verification.json          # archive integrity and restored replay checks
```

The public case contains both material and explanation. `itinerary.md` presents
the saved V0-V3 daily schedules, recorded RAG POI origins and actual V3 draft/final
changes. Use captured canonical source associations, distinguish mixed Google/RAG
origins from RAG-only introductions, and preserve partial/unavailable attribution.
Keep full schedules in this reader view; `report.md` retains evaluation conclusions
and links to it instead of repeating the schedules. `report.md` also links the
reviewed requirements, interest inventory, selected itineraries, usage/provenance,
primary and paired scoring, candidate process, Repair and resource outputs.
`material-index.json` records canonical public paths, publication hashes, original
source hashes and exact JSON-subtree locations where material is extracted.
Reference tracked `inputs/<case-id>.json` rather than copy the request. Store shared
configuration and identical RAG-origin inventories once, and use references for
repeated output content. Public material
must exclude credentials, private transcripts and raw provider/model responses.

`generation/` contains exactly one selected final itinerary for each version, its
usage/provenance and applicable shared runtime policy or origin metadata. Current
materials use canonical category paths directly, such as `generation/v0/`,
`requirements/` and `evaluation/primary/`, without an `r02/` or other revision
directory. Revision IDs remain in provenance, run metadata and historical evidence;
native schemas and original execution paths need not match across cases. V3
draft/final-primary stages and validation traces belong in `analysis/repair/`, not
additional generation selections.
Earlier published generation observations and failures belong in `analysis/history/`.
Superseded requirement contexts and scoring reports also belong there rather than
beside the final material in current categories. Their source bytes and historical
evaluation policies remain preserved.

In the public material view, repeated large JSON objects use `$case_material_ref`
with a relative file path, JSON Pointer and expanded semantic hash. The material index
defines the path base (containing file or case directory) and publication format.
Expand references to recover the original JSON
values; these views are not closed native acquisition/replay bundles. A V3 draft
may use a lossless delta from its final itinerary when their common content would
otherwise be copied. Preserve every actual difference, including recommendations.

Maintain one reader-facing report per case by rewriting the applicable sections;
routine tasks do not create another report. Common rules remain in this README
and contracts. The case Issue owns live acceptance and pending decisions. Public
navigation and shared material references resolve within tracked sources.

Publication completeness and researcher acceptance are separate facts. Preserve the
original step-10 decision, its exact selection and hashes when correcting reader
materials. The current index records the preceding publication revision and any
relocated reader paths; a frozen historical index resolves at its own recorded Git
revision. Updating navigation or extracting saved evidence does not rescore results
or extend the accepted selection.

Before declaring a public case complete, check required categories independently of
the existing index: original input, reviewed requirements, explicit interest inventory
(including a valid empty inventory), four selected final itineraries and their
usage/provenance/runtime policy, primary and paired scoring, captured candidate
stages/origins/omissions and relevance applicability, complete V3 stage reconstruction,
Repair observations, and all-attempt resource accounting. Verify index coverage in
both directions, reader navigation, file hashes, declared reference/delta semantics
and original source/subtree bindings. A hash check of already indexed files cannot
detect an omitted category. Retain genuine empty/no-Repair/partial observations;
unavailable evidence stays explicitly unavailable rather than being reconstructed
from assumptions. Native execution/replay closures remain private.

When human review is authorized, private `human/packages/`, `private/`, `answers/`
and `reports/` retain anonymous presentation, researcher mappings, real responses
and native reports. No human or corpus directories are created by default.

### Private archive retention

During execution, retain the native working layout needed by preparation and
consumed outputs. After case review, clean up that case's private storage as part
of the handoff: keep original requests, reviewed semantic inputs and actual actor
records, selected generation captures/results, all-attempt identities and usage,
configuration/source versions, independent evidence, final reports, receipts and
their required native dependencies. Preserve consequential failure/correction
evidence and explicit unavailable telemetry. Storage cleanup does not itself record
user acceptance or authorize another run; an explicit earlier cleanup instruction
may compact completed evidence while acceptance remains pending.

Delete synthetic test/preflight trees, compiled caches, assembly scripts,
unreferenced intermediate views and superseded preparation/registration/export
copies after checking their dependencies. Failed or nonselected attempts with real
consumption retain their authentic usage/completion and necessary failure evidence;
redundant copied source trees are not required solely because they once belonged
to those attempts. Do not remove another case's or shared engineering evidence.

Store repeated immutable bytes once in the private archive, with a manifest mapping
each retained original logical path to its SHA-256 and byte length. Native closed
inventories can require multiple logical paths; restore those paths from shared
bytes into a fresh temporary root for offline verification. Do not modify native
receipts, source hashes or absolute preparation bindings to hide relocation. Validate
archive contents, public-source equivalence and native offline replay from the
restored tree before deleting the old working directories. Remove the temporary
restoration after validation; it is not another permanent archive copy. Retained
original paths in public material indexes and actor tables identify archive manifest
entries, rather than live files beside the compressed archive.

## Scenario index

The active selection has four groups of three. Each case belongs to one group by
its primary planning demand; the groups do not imply matched difficulty or
experimental pairs. Group A includes ordinary mixed interests, not only empty
preferences. Group C constrains visits to named places; group D constrains the
itinerary's available modes, time or daily visit capacity.

| Group | Cases | Primary demand |
| --- | --- | --- |
| A. General sightseeing | 01, 02, 03 | Basic requests and balanced first-visit sightseeing |
| B. Contextual preferences | 05, 06, 07 | Relaxed depth, family needs and lower-cost experience preferences |
| C. Place obligations | 08, 09, 10 | Required/excluded places, dated visits and deliberate repeated visits |
| D. Itinerary boundaries | 04, 11, 12 | Allowed transport modes, protected intervals and dated count/rest-day rules |

Case-01–07 retain their existing input bytes, selected revisions, results, scores,
reports, receipts, original dates and acceptance limitations. Historical accepted
dates need not satisfy today's moving window. The five inputs revised on 16 October
use the dates below. Current acceptance states and selected revisions are listed above.
Case-12 r07 is [automatically accepted](case-12/report.md#acceptance), with
local main-worktree integration and private-evidence migration complete. It is the former Sydney case-14.

Dates and durations are inclusive. Selected reports are indexed
[above](#accepted-selections). Case-05 uses the approved 2026-10-16 through
2026-10-20 interval; case-07's accepted
[input revision 2](case-07/requirements/input-r02.json) uses 2026-10-22 through
2026-10-24. Before executing a pending input, revalidate its stored dates against
the actual application reference date.

| Case | Category | Destination | Days | Travelers | Group budget | Scenario and design rationale |
| --- | --- | --- | --- | --- | --- | --- |
| [01](case-01/report.md) | A. General sightseeing | Sydney | 3 | 1 | AUD 900 | Empty preferences for a solo traveler; checks ordinary destination planning from structured fields alone. |
| [02](case-02/report.md) | A. General sightseeing | London | 3 | 2 | GBP 1,200 | Empty preferences for two travelers in a different destination; adds geographic and group-size variation to basic requests. |
| [03](inputs/case-03.json) | A. General sightseeing | Tokyo | 4 | 2 | JPY 160,000 | First-time visit with traditional culture and modern neighborhoods; checks balanced introductory sightseeing at a moderate pace. |
| [04](inputs/case-04.json) | D. Itinerary boundaries | Singapore | 2 | 2 | SGD 800 | A fairly full garden/city weekend using only walking and public transport; checks an explicit transport restriction on a short trip. |
| [05](inputs/case-05.json) | B. Contextual preferences | Barcelona | 5 | 1 | EUR 1,300 | Solo architecture and art travel at a relaxed pace; checks depth and time at places rather than many daily stops. |
| [06](inputs/case-06.json) | B. Contextual preferences | Sydney | 4 | 3 | AUD 2,200 | Two adults and a child prefer science, nature, breaks and driving; checks family preferences and soft transport intent. |
| [07](inputs/case-07.json) | B. Contextual preferences | Paris | 3 | 1 | EUR 650 | Lower-cost parks, neighborhoods and exterior architecture, with a few paid visits; checks cost-conscious selection without inventing a numeric quota. |
| [08](inputs/case-08.json) | C. Place obligations | Barcelona | 3 | 2 | EUR 1,000 | Exactly one Sagrada Familia visit and no Park Guell visit; checks required and excluded places together. |
| [09](inputs/case-09.json) | C. Place obligations | Tokyo | 5 | 3 | JPY 300,000 | Ueno Park exactly once on day two and Tokyo National Museum exactly once on a flexible date; checks different date scopes for two required places. |
| [10](inputs/case-10.json) | C. Place obligations | London | 4 | 1 | GBP 1,300 | Exactly two British Museum visits on different dates; checks deliberate repetition within a shorter trip. |
| [11](inputs/case-11.json) | D. Itinerary boundaries | Paris | 4 | 2 | EUR 1,500 | Day-two 14:00-16:00 meeting with no activities or travel; checks a protected local-time interval. |
| [12](case-12/report.md) | D. Itinerary boundaries | Sydney | 7 | 2 | AUD 3,200 | Exactly one sightseeing visit on day one and no activities or travel on day four; checks dated count and whole-day protection. |

Five trips last two or three days, six last four or five days, and one lasts seven
days. Sydney has three cases; Tokyo, Barcelona, London and Paris have two each;
Singapore has one. Budgets describe whole-group trip inputs, not verified local
travel prices or affordability.

### Selection revision

On 16 October 2026 Australia/Sydney, the user approved reducing the active set from
15 to 12 while preserving case-01–07. Cases 08–11 retain their identities; former
14 becomes new 12. All five pending inputs move seven days later, preserving
durations, weekdays, request meaning, party sizes, budgets and destination-local
clock times. Selection follows request coverage, not observed scores.

| Previous 15-case ID | Current disposition | Issue and retained source |
| --- | --- | --- |
| 01–07 | Unchanged | Existing accepted case records and source bindings |
| 08–11 | Same IDs; pending dates revised | #157, #158, #159, #160 |
| 12: Singapore museum | Retired unexecuted | [#161](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/161); [original input](history/2026-10-16-selection/case-12.json) |
| 13: Tokyo art/design | Retired unexecuted | [#162](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/162); [original input](history/2026-10-16-selection/case-13.json) |
| 14: Sydney count/rest day | New case-12 | [#163](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/163); [previous input](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/73686a071fa4fda5b5c68b4b451a38f8b973e467/benchmark/inputs/case-14.json) |
| 15: Barcelona mixed group | Retired unexecuted | [#164](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/164); [original input](history/2026-10-16-selection/case-15.json) |

The retired originals retain their exact bytes outside the active `inputs/`
directory. Old Singapore case-12 and new Sydney case-12 have distinct source
histories and Issues; #161 is never reassigned to Sydney. Native historical Issue
links remain traceable even after retirement.

Retirement reduces specialized coverage: former 12 isolated hard dates versus soft
start/duration preferences; former 13 isolated primary/secondary interests; former
15 combined within-group interest differences, a required landmark and a protected
interval. Retained cases cover the principal visit/date/count, preference and
itinerary-boundary mechanisms, without claiming equivalent coverage of every
retired combination.

The earlier 20-to-15 selection was approved on 14 October 2026 and preserved
accepted 01/02. Its complete predecessor mapping and three substantive request
revisions remain in the [published 15-case index](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/6b11572c1c2331b61f263727dd7901ba8353752c/benchmark/README.md#selection-revision).

## Date update rules

The shared [date policy](../backend/app/policies/trip_dates.py) requires the entire
trip to fall between the actual execution reference date and 13 days later,
inclusive, with at most ten inclusive days. At reference date **2026-10-16**, the
window is **2026-10-16 through 2026-10-29**.

| Pending case | Travel dates | Explicit dated requirement |
| --- | --- | --- |
| 08 | 2026-10-22–2026-10-24 | One required visit and one exclusion; dates otherwise flexible |
| 09 | 2026-10-22–2026-10-26 | Ueno Park on day two, 2026-10-23; the one Tokyo National Museum visit has a flexible date |
| 10 | 2026-10-22–2026-10-25 | Exactly two British Museum visits on different dates |
| 11 | 2026-10-22–2026-10-25 | Day two, 2026-10-23, 14:00–16:00 Paris local time: no activities or travel |
| 12, former 14 | 2026-10-22–2026-10-28 | Exactly one sightseeing visit on 2026-10-22; no activities or travel on day four, 2026-10-25 |

These future trips can be generated before their start date. The dates currently
pass the window for execution reference dates 2026-10-16 through 2026-10-22;
recheck at every actual dispatch. This selection/date update authorizes no live
execution, semantic-review dispatch, new paid call or rescoring.

1. Preserve the consumed bytes and original dates of accepted cases. A future
   request change creates a new revision rather than replacing old evidence.
2. Revalidate pending inputs against the actual configured-zone application date;
   do not backdate the runtime. Update structured dates and every explicit prose
   date together, preserving day-relative relationships and local clock times.
3. Retain duration and weekdays with a seven-day shift. Accepted case-04 keeps its
   original Saturday-to-Sunday interval. Do not change interests, visit counts,
   exclusions, budgets or traveler counts as a side effect of a date update.
4. Before execution, review the input revision, actual source/runtime and official
   opening information for required places. An offline date/schema check does not
   establish opening, route, ticket or affordability feasibility. All compared
   versions receive the same case request.

## Offline checks

Parse exactly `case-01.json` through `case-12.json` in `inputs/` as UTF-8 JSON and
validate every input with `PlanningRequest.model_validate_json`. Check each pending
case with `create_trip_date_window` and `validate_requested_trip_dates` using an
explicit execution reference date. Accepted dates and retired historical inputs
are exempt from today's new-run window, not from source-integrity checks.

Verify four disjoint groups of three, the origin/retirement mapping and Issue
identities, scenario fields and all local index links. Case-01–07 must match their
pre-change bytes; retired 12/13/15 must match the retained originals. The five new
pending requests must equal their prior counterparts after only the authorized
seven-day date shift and former-14 renaming. Retain existing acceptance and
regression limitations; this revision changes no runtime code or scoring policy
and does not establish a full-backend regression gate.

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
`benchmark/scratch/<case-id>/work/material/` destination. Fix private generation and
evaluation paths before execution. For an existing bundle, preserve its complete
source-bound root, bytes and relative dependencies during an authorized relocation.
Native preparations may pin absolute paths: moving files does not make their old
execute/replay commands portable. Retain those original declarations and verify
relocated data with applicable native descriptor/portable readers and the exact
declared runtime. Document unsupported old-path replay explicitly; do not rewrite
source hashes, receipts or preparations to claim portability. Reference roots must
contain the files they declare; this map never permits path escape.

Accepted sources are immutable. Changed input/source material requires new native
identities and affected validation even though the reader-facing folder has no
revision suffix. Never overwrite a consumed native output directory; prepare a
fresh working root and update the current-case view only after a valid handoff.
Retain required earlier dependencies and all-attempt consumption under the
[private archive retention rules](#private-archive-retention). Routine post-review
cleanup removes unnecessary work after the required integrity and replay checks.
A reset does not alter unrelated engineering work.

Selected primary/paired evidence and process reports belong in the corresponding
case directories above, with explicit fresh native destinations. Later human
material binds the same accepted outputs and does not overwrite them. Preparation,
failed/nonselected work and optional controlled studies use the private case's
`work/` directory while active; retain their necessary evidence in the compact
archive and discard unnecessary working copies after review. Evaluation never
automatically scans or runs every case in this directory.

### Git storage

Public case materials and canonical inputs are eligible for Git by default;
the benchmark ignore rules exclude only the private `scratch/` tree. Repository-wide
environment, cache and build exclusions still apply. Keep raw provider/model payloads,
private prompts, native execution bundles and temporary files in `scratch/` rather
than public case directories. Case observations belong in
their one public report; distinct engineering events remain in their existing
`docs/records/` owner without duplicating the case report. Tracking a report does
not publish it remotely or establish case acceptance.
