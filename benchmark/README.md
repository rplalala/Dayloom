# Twelve-case study material

The study contains **12 original requests and 48 selected V0–V3 final outputs**.
Start with the [automatic report](report.md) or [blinded results](blinded-results/report.md).
Use [findings verification](../docs/guides/verification.md) to trace their sources and
[experiment reproduction](../docs/guides/experiments.md) to run a new comparison.

```bash
uv run rtpeval verify
```

This checks all twelve public cases and confirmed blinded results offline. Accepted
material can retain FAIL, UNKNOWN and unavailable observations; acceptance does not
certify every itinerary fact or establish generalization beyond these cases.

## Accepted selections

Each report identifies the exact accepted material, sources and limitations.
Decision dates use Australia/Sydney. Historical selections remain in Git and native
archives; the current directory presents one selected revision per case.

| Case | Current selection accepted | Sources and limitations |
| --- | --- | --- |
| 01 | 2026-10-14 | [Case report](case-01/report.md#acceptance) |
| 02 | 2026-10-14 | [Case report](case-02/report.md#acceptance-and-material) |
| 03 | 2026-10-15 | [Case report](case-03/report.md#acceptance-status) |
| 04 | 2026-10-24 | [Case report](case-04/report.md#acceptance) |
| 05 | 2026-10-18 | [Case report](case-05/report.md#acceptance) |
| 06 | 2026-10-15 | [Case report](case-06/report.md#acceptance-and-selected-material) |
| 07 | 2026-10-16 | [Case report](case-07/report.md#acceptance) |
| 08 | 2026-10-17 | [Case report](case-08/report.md#acceptance) |
| 09 | 2026-10-18 | [Case report](case-09/report.md#acceptance) |
| 10 | 2026-10-17 | [Case report](case-10/report.md#acceptance-status) |
| 11 | 2026-10-18 | [Case report](case-11/report.md#acceptance) |
| 12 | 2026-10-17 | [Case report](case-12/report.md#acceptance) |

### Final blinded results

The [blinded report](blinded-results/report.md) links English/Chinese questionnaires,
separate human and model answer exports, task-level rankings and mean ranks. Both
reviewers' answers were confirmed on 24 October 2026. Answers bind the exact assessed
outputs and remain a separate assessment from automatic scores.

## Scenario index

Four groups of three cover general sightseeing, contextual preferences, named-place
obligations and itinerary boundaries. The groups describe primary demand; they do
not imply matched difficulty or experimental pairs.

| Case | Category | Destination | Days | Travelers | Group budget | Scenario and design rationale |
| --- | --- | --- | --- | --- | --- | --- |
| [01](case-01/report.md) | A. General sightseeing | Sydney | 3 | 1 | AUD 900 | Empty preferences for a solo traveler; checks ordinary destination planning from structured fields alone. |
| [02](case-02/report.md) | A. General sightseeing | London | 3 | 2 | GBP 1,200 | Empty preferences for two travelers in a different destination; adds geographic and group-size variation to basic requests. |
| [03](inputs/case-03.json) | A. General sightseeing | Tokyo | 4 | 2 | JPY 160,000 | First-time visit with traditional culture and modern neighborhoods; checks balanced introductory sightseeing at a moderate pace. |
| [04](inputs/case-04.json) | D. Itinerary boundaries | Singapore | 2 | 2 | SGD 800 | A fairly full two-day garden/city trip using only walking and public transport; checks an explicit transport restriction on a short trip. |
| [05](inputs/case-05.json) | B. Contextual preferences | Barcelona | 5 | 1 | EUR 1,300 | Solo architecture and art travel at a relaxed pace; checks depth and time at places rather than many daily stops. |
| [06](inputs/case-06.json) | B. Contextual preferences | Sydney | 4 | 3 | AUD 2,200 | Two adults and a child prefer science, nature, breaks and driving; checks family preferences and soft transport intent. |
| [07](inputs/case-07.json) | B. Contextual preferences | Paris | 3 | 1 | EUR 650 | Lower-cost parks, neighborhoods and exterior architecture, with a few paid visits; checks cost-conscious selection without inventing a numeric quota. |
| [08](inputs/case-08.json) | C. Place obligations | Barcelona | 3 | 2 | EUR 1,000 | Exactly one Sagrada Familia visit and no Park Guell visit; checks required and excluded places together. |
| [09](inputs/case-09.json) | C. Place obligations | Tokyo | 5 | 3 | JPY 300,000 | Ueno Park exactly once on day two and Tokyo National Museum exactly once on a flexible date; checks different date scopes for two required places. |
| [10](inputs/case-10.json) | C. Place obligations | London | 4 | 1 | GBP 1,300 | Exactly two British Museum visits on different dates; checks deliberate repetition within a shorter trip. |
| [11](inputs/case-11.json) | D. Itinerary boundaries | Paris | 4 | 2 | EUR 1,500 | Day-two 14:00-16:00 meeting with no activities or travel; checks a protected local-time interval. |
| [12](case-12/report.md) | D. Itinerary boundaries | Sydney | 7 | 2 | AUD 3,200 | Exactly one sightseeing visit on day one and no activities or travel on day four; checks dated count and whole-day protection. |

Trip duration is inclusive and budgets cover the whole group for the whole trip.
These inputs do not verify local prices or affordability. Historical accepted dates
need not satisfy today's moving generation window.

## Layout

```text
benchmark/
  inputs/case-XX.json          # original requests
  report.md                   # aggregate automatic results
  automatic-results.json
  blinded-results/            # questionnaires, answers and report
  case-XX/
    report.md                 # observations, limitations and source links
    itinerary.md              # daily schedules and recorded V3 changes
    material-index.json       # paths, hashes and original bindings
    requirements/             # independent reviewed requirements
    interests/                # source-bound interest inventory, including empty
    generation/v0/ ... v3/     # one selected final per version, usage/provenance
    evaluation/               # primary and same-run V3 paired results
    analysis/                 # POI process, Repair and resources
  scratch/case-XX/             # ignored working evidence and compact archive
```

`material-index.json` is the entry point for each case. It records public paths,
publication hashes, original source hashes and extracted JSON-subtree locations.
`report.md` explains findings; `itinerary.md` presents full schedules. V3 draft and
final-primary material belongs under `analysis/repair/`, separate from the four
final generation selections.

Repeated JSON uses `$case_material_ref` with a relative path, JSON Pointer and
expanded semantic hash. The index declares the path base and format. V3 drafts may
use lossless deltas from final outputs; all actual differences remain recoverable.
These public projections support verification. Native replay additionally requires
the complete private dependencies described below.

## Per-case execution and joint review

### Workflow and responsibilities

The [experiment guide](../docs/guides/experiments.md) owns runnable commands; the
[artifact contract](../docs/contracts/0001-evaluation-artifacts.md) owns schemas.

1. Confirm the exact request; independently author and review requirements and interests.
2. Record code, policies, prices, budgets and capture settings; generate V0–V3 sequentially.
3. Qualify the four selected finals and perform independent primary evaluation.
4. Present scores, FAIL/UNKNOWN and limitations; continue analysis within covered scope.
5. Analyze V1/V2 candidate process, same-run V3 Repair and all-attempt resources.
6. Accept the exact selection and separately package any selected blinded review.

Candidate analysis counts canonical places once per stage while retaining Google/RAG
origins, unresolved identities, omissions and independently reviewed relevance.
Nearby references are separate from scheduled visits. Independent V2/V3 final
comparisons and same-run V3 draft/final observations answer different questions;
a V3 draft is not an independent V2 run. Neither establishes a causal ablation.

### User intervention and execution boundaries

Execution needs concrete scope and numeric limits. Pause after primary score
handoff for the next stage instruction, and for blocking intent, uncovered input
changes, restricted access or exhausted limits. Routine corrections within an
approved stage need no repeated approval. No automatic rerun, budget increase or
silent request revision is implied. Real raters must read and answer questionnaires;
agent inspection cannot substitute for their responses.

Case Issues own scope, attempts, budgets and pending decisions. Shared workflow
belongs here and in contracts. Git delivery, case acceptance and research execution
remain distinct decisions.

### AI assistance records

Each case report identifies actual performers and external AI assistance separately
from model calls inside the studied planner/evaluator. Retain the work and purpose,
verified actor/model configuration when known, source revisions and operation IDs,
inputs supplied, outputs used, and actual review or human decisions. Missing model
identity, transcripts, usage or billing remains unavailable. Keep authentic private
records for verification; disclose contributions without exposing credentials or
raw provider/model responses.

### Optional work compared with the initial plan

Corpus census/coverage, controlled Repair studies and suite integration are opt-in.
Ordinary process analysis retains candidate-stage capture, applicable independently
reviewed relevance, Repair observations and attempt/resource accounting without
claiming a corpus denominator or recall. Optional tools remain available through
RTPEval; selecting a report does not start live acquisition.

## Accepted case bundles

### Admission

Native intake requires the original request, independently reviewed RequirementSpec,
four selected finals, usage envelopes, provenance and producer completion declarations.
Usage can explicitly be unavailable. All versions receive the same case request;
material qualification remains separate from quality PASS.

Check required categories independently of the existing index: input, reviewed
requirements, explicit interest inventory, four finals and resource/provenance/policy
files, primary/paired scoring, candidate stages/origins/omissions, V3 reconstruction,
Repair observations and all-attempt resources. Verify index coverage in both
directions, hashes, reference/delta expansion, source/subtree bindings and links.
Checking only indexed hashes cannot reveal an omitted category.

### Bundle handling

Preserve original bytes and source-bound dependencies. Native preparations can pin
absolute paths; relocation does not make old commands portable. Use the declared
historical runtime and applicable native/portable readers, retain original receipts
and hashes, and disclose unsupported replay. Paths stay within declared roots.

A new selection needs new native identities and a fresh execution directory.
Update the reader-facing case in place after valid handoff; preserve earlier bytes
in Git/history and native archives. `analysis/history/` can retain substantive
failure observations rather than a competing cohort. Public text hashes follow
their declared LF/CRLF convention; native hashes identify exact original bytes.

### Private archive retention

Keep the working layout while execution depends on it. After review, retain requests,
reviewed inputs and actor records, selected captures, all-attempt identities/usage,
code/configuration versions, evidence, reports, receipts and native dependencies.
Keep consequential failure/correction evidence and explicit telemetry gaps. Remove
redundant synthetic/preflight outputs, caches and unreferenced temporary copies only
after checking dependencies; preserve other cases and shared evidence.

Archive identical immutable bytes once. Its manifest maps every original logical
path to SHA-256 and byte length. Restore required logical paths into a fresh temporary
root, verify integrity and public-source equivalence, then perform native offline
replay before removing the old working tree. Do not rewrite receipts, hashes or
absolute preparation bindings to hide relocation. Original paths in public indexes
identify archive entries, not necessarily live files beside the archive. The archive's
README, manifest and standard-library helper explain restoration.

### Git storage

Track public inputs, case projections and reports. Keep native execution bundles,
raw provider/model payloads, private transcripts, secrets and temporary files in
ignored private storage. Maintain one case report; distinct engineering events
belong in their existing `docs/records/` owner.

## Date update rules

New runs must satisfy the actual application reference date through 13 days later,
with at most ten inclusive days. Preserve accepted historical requests unchanged.
A date update creates a new input revision, updates structured and prose dates
together, and preserves local times/day-relative relationships. Preserve weekdays
and duration unless a different change is authorized. Interests, counts, exclusions,
budgets and party size do not change as a side effect. Check current required-place
evidence before execution; an offline date check does not prove opening, transport,
ticket or affordability feasibility.

## Offline checks

`uv run rtpeval verify` checks public selections, automatic arithmetic, source bindings
and confirmed blinded results without provider calls. See
[verification](../docs/guides/verification.md) for its scope and native replay.
New inputs also require schema validation and a fresh date-window check. Retired
inputs and accepted dates retain historical source-integrity checks.

## Historical changes

### Selection revision

The set was reduced from 20 to 15, then to 12 on 16 October 2026. Current 01–11 retain
their identities; former Sydney case-14 became case-12. Former 12, 13 and 15 were
retired unexecuted, reducing specialized coverage. Original identities, inputs and
rationale remain in the
[published predecessor index](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/6b11572c1c2331b61f263727dd7901ba8353752c/benchmark/README.md#selection-revision)
and case Issues. Later accepted replacements retain their source histories in the
linked reports; current selections and assessed outputs remain explicit.

### Parallel sessions and integration

Historical worker queues and integration decisions belong to
[batch #151](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/151).
They are not current dispatch assignments. Future execution needs compatible code,
local dependencies/data, concrete budgets and fresh covered scope. Git integration
does not transfer ignored evidence; preserve and verify native archive dependencies
before retiring a worktree.
