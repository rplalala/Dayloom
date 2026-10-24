# Live smoke execution

Read before preparing or executing a live smoke test. This policy replaces the former
requirement to use a separate conversation titled `smoke tests`.

## Ownership and delegation

The current session's parent agent owns plans, budgets, acceptance criteria, tool
adaptation, implementation, offline validation and result assessment. Delegate only
execution of a prepared, explicitly authorized smoke test and reporting to a child
agent in the current session. No dedicated chat, fixed thread ID or cross-chat
coordination is required or authorized by this policy.

Configure every live-smoke execution child with:

- Model: **GPT-6.1 Sol**, tool identifier `gpt-6.1-sol`.
- Reasoning effort: **medium**.
- With `collaboration.spawn_agent`, explicitly set `model="gpt-6.1-sol"`,
  `reasoning_effort="medium"` and `fork_turns="none"` (or a bounded positive turn
  count supported by the client). Provide a self-contained execution handoff.
- If the client cannot select that model/effort or spawn the required child, report
  the blocker; do not silently substitute another configuration or execution chat.

This authorization is for execution delegation only. The child reports blockers;
it does not design solutions, change implementation or expand the test scope.

## Execution handoff and limits

Before dispatch, the parent must provide the approved plan, exact commands/inputs,
source revision and frozen hashes where applicable, acceptance criteria, evidence
output paths, and approved request/cost/token/time/retry limits and stopping rules.
Include credentials/configuration prerequisites without copying secrets into the
handoff. Missing approval or prerequisites is a blocker, not authority to improvise.

Python harnesses using async PostgreSQL must reuse
`scripts.run_api.create_api_loop` through
`asyncio.run(main(), loop_factory=create_api_loop)`, as the Product launcher does.
Verify loop selection offline before freezing the execution source; Windows Proactor
cannot run psycopg async connections. Preserve previously frozen source and evidence
when preparing a corrected harness. A local readiness check does not establish live
retrieval, embedding or search coverage.

The child executes only that handoff and preserves original evidence. It stops at
approved limits or blocking conditions and reports deviations. Spawning a child
never authorizes additional live calls, retries, mode substitution or budget growth.
Existing no-live instructions, approvals, budgets and exclusions remain binding;
changes require the user's explicit authorization.

## Required report and parent assessment

Return to the parent in the current session: process/commands, actual results,
request/usage/cost evidence and missing billing where applicable, blockers, issues
requiring fixes or further verification, deviations from the current project spec,
and relevant evidence/document paths. Distinguish observed facts, inferences and
missing evidence; do not infer PASS from missing facts or count agent inspection
as genuine human review.

The parent assesses the results against the plan and owns any authorized fixes,
offline retests, review and documentation. Report this as development smoke evidence,
not a formal benchmark or automatic version freeze. Follow the
[task and Git rules](workflow.md) and [record admission rules](domain.md#record-admission-and-topic-ownership).
