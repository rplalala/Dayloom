# Benchmark agent instructions

Apply [repository rules](../AGENTS.md) to all benchmark work, including ignored scratch.
[README](README.md) owns workflow, roles and storage; evaluator contracts own schemas
and scoring. Read the relevant linked sections rather than entire case archives.

## External Codex handoffs

- Explicitly include this file in each handoff. Specify the role, permitted inputs,
  task, source revision/hashes, output destination, completion criteria and limits.
- Use [role settings](README.md#workflow-and-responsibilities) and applicable
  [execution policy](../docs/agents/smoke-tests.md), honoring session overrides.
  Distinguish external Codex settings from models called by the Planner/evaluator.
- Give source-only semantic authors/reviewers fresh context: complete original
  request, applicable contract sections and the author's material when reviewing it.
  Exclude itineraries, Planner interpretations, scores, traces and result-bearing
  summaries. Disclose accidental exposure before selecting their work.
- Independent quality judgments use submitted claims and evaluator evidence;
  process analysts receive the separately authorized mechanism material.

## Primary evaluation gate

Before execution, the orchestrator checks exact input/attempt bindings and native
intake, reviewed requirements/interests, destination time/occupancy context,
[transport constraints](../docs/contracts/0004-opening-routes.md#route-wire) and
[density applicability](../docs/contracts/0005-quality-human-review.md#daily-density).
No transport restrictions still requires an explicit `unrestricted` review.
Verify required reviews actually entered the prepared package; CLI success alone
does not establish completeness. Missing preparation is a defect, while reviewed
unresolved meaning remains explicit.

Bind prices and call/token/time/cost/retry limits to the approved package, including
conditional [missing-hours assessment](../docs/contracts/0004-opening-routes.md#missing-hours-access-judgment).
Complete applicable assessment before computing the single final primary score.
Use the explicit API-only option only within the selected scope; preserve the reason
when assessment is skipped or disabled. Report model-supported access separately
from verified API hours.

## Handoff and evidence

Report four final scores, common dimensions, density deductions, FAIL/UNKNOWN causes,
resources and limitations; follow the [stage pause](README.md#user-intervention-and-execution-boundaries).
Process, paired and human reports retain separate meanings. Corrections create new
bound reports and preserve original evidence; post-score rescoring is not a routine stage.
The parent validates returned artifacts and offline replay. Maintain actual
[AI assistance](README.md#ai-assistance-records) and [private evidence](README.md#private-archive-retention),
including metadata gaps. Update existing authorized reports/Issues in place with
sanitized summaries; agent review is not human review.
