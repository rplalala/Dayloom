# Benchmark agent instructions

These instructions apply to work under `benchmark/`, including ignored case work.
Inherit [repository rules](../AGENTS.md). This file owns agent dispatch and handoff
checks; [README](README.md) owns the detailed case workflow and storage conventions,
and linked evaluator contracts own schemas and scoring semantics.

## Dispatch and role boundaries

The orchestrator must explicitly include this file in external Codex handoffs;
automatic instruction discovery depends on the agent's working directory and client.
Each handoff identifies the role, allowed inputs, exact task, output destination,
source revision/hashes, completion criteria and applicable execution limits.
The receiving agent confirms missing prerequisites before dependent work begins.

Use the actor settings in [workflow responsibilities](README.md#workflow-and-responsibilities)
and applicable [execution policy](../docs/agents/smoke-tests.md), honoring explicit
session overrides. Record external Codex settings separately from the actual models
called by the studied Planner or evaluator; an executor's model does not identify
the model that produced a provider judgment.

| Role | Permitted task material | Completion criterion |
| --- | --- | --- |
| Requirement author and independent reviewer | Complete original request and applicable requirement/handoff contracts; the reviewer also receives the author's material | Reviewed native specification and authentic author/reviewer provenance, including explicit empty obligations or unresolved clauses |
| Interest, transport and pace reviewers | Complete original request and applicable policy/schema sections | Source-bound interpretation, explicit empty/unrestricted or unresolved outcomes, actual reviewer and review time |
| Generation executor | Approved original request, runtime configuration and bounded capture plan | Authentic attempt, completion, result, usage and mechanism evidence; failures retained |
| Independent evaluator and access assessor | Submitted claims, reviewed request context and independent evidence required by the assigned contract | Native source-bound reports and explicit PASS/FAIL/UNKNOWN, factual versus model-supported basis, and replay material |
| Process analyst | Authorized selected results, captured candidate stages, V3 draft/final and applicable independent reports | Source-bound process observations, coverage and limitations, separate from primary scoring |

Give source-only semantic authors/reviewers fresh context containing only their
permitted material and these instructions. They must not read generated itineraries,
Planner interpretations, mechanism traces, case reports, scores or result-bearing
project summaries. Supply relevant contract sections rather than the entire case
archive. Record accidental exposure and reassess independence before selecting work.
Independent quality judgments use evaluator evidence, not Planner caches or V3 verdicts.

## Before primary evaluation

The orchestrator checks the following before approving the execution package:

1. Bind the exact original request and selected V0-V3 attempts to their sources.
   Check dates at dispatch using the applicable application reference date; retain
   failed attempts and distinguish authorized retry selections. Validate the native
   [intake and external handoff](../docs/contracts/0002-intake-identity-usage.md).
2. Obtain independently reviewed [requirements](../docs/contracts/0003-requirement-schedule.md#rtpeval-requirement-spec-contract)
   and the original-request interest inventory. Empty preferences do not remove
   review/provenance requirements or invent obligations and interests.
3. Supply independent [time and occupancy context](../docs/contracts/0003-requirement-schedule.md#occupancy)
   for applicable checks, including the destination timezone and any required
   commitment/protection interpretation.
4. Supply an original-request [transport constraint review](../docs/contracts/0004-opening-routes.md#route-wire)
   for every evaluated request: explicitly record `unrestricted`, `restricted` or
   `unresolved`. Absence of restrictions still requires an `unrestricted` record.
   Missing review is not an unrestricted default; it leaves route policy UNKNOWN.
5. Check [density review applicability](../docs/contracts/0005-quality-human-review.md#daily-density)
   against the complete original request. Use the native ordinary default only
   where the contract permits it; preserve reviewed pace/count exceptions.
6. Verify the prepared package actually contains the intended context and review
   envelopes, with matching source hashes. A valid CLI preparation or exit code
   alone does not establish semantic preparation completeness. Stop for omitted
   required material; deliberately reviewed unresolved meaning remains explicit.
7. Bind the approved scope, prices and call/token/time/cost/retry limits. Execute
   only the prepared package and preserve its original receipt, evidence and report.

Transport review belongs before normal primary scoring. Adding a missing review
and rescoring afterward is error correction, not a routine later workflow stage.

## Score handoff and subsequent stages

Follow [staged acceptance](../docs/contracts/0005-quality-human-review.md#staged-automatic-acceptance-and-deferred-blinded-review):
report all four primary scores, common dimensions, density deductions, FAIL/UNKNOWN
reasons, resource consumption and limitations, then pause for the user's next instruction.
Explain whether an UNKNOWN comes from unavailable provider facts, unresolved reviewed
meaning, missing preparation material or unsupported checks. Processing completion,
mechanism acceptance and case acceptance are distinct.

[Missing-hours access assessment](../docs/contracts/0004-opening-routes.md#missing-hours-access-judgment)
is a separately instructed supplement for eligible visits. Model-supported access
PASS is distinct from verified API hours and itinerary Repair. Retain the original
API-only report and the separately bound supplemented report and scoring profile.
Candidate/Repair process analysis, V3 paired diagnostics, resources and human review
produce their own reports; they do not themselves rewrite four-final primary scores.
Corrections or changed sources/policies require dependent replay and a new bound
report; preserve earlier evidence rather than editing decisions or frozen receipts.

## Evidence and disclosure

Follow [AI assistance records](README.md#ai-assistance-records) and
[private archive retention](README.md#private-archive-retention). Each material
contribution retains actual actor/model settings where verifiable, permitted inputs,
selected output, source linkage and review/validation performed. Unavailable transcripts,
usage or billing remain unavailable; agent review is not human review.
The parent validates returned artifacts and replay against the assigned criteria.
Update the case's existing report and authorized Issue summary in place; publish only
sanitized status, results and limitations with accessible source links.
