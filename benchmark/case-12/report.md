# Case-12: Sydney, Australia

## Status and request

Revision r02 **stopped before the four-version Primary handoff** on 17 October
2026 Australia/Sydney. V0 completed; V1 failed while constructing its generation
prompt. V2, V3 and Primary were not started. No r02 V3 draft, Repair or final
exists. Its prompt serialization blocker is now fixed and verified offline in this
worktree; no subsequent live revision has run. Primary and case acceptance remain pending.

The [original request](../inputs/case-12.json) remains unchanged: Sydney,
22-28 October 2026, two adults, whole-group budget AUD 3,200, nature and harbour
views, relaxed pace, exactly one sightseeing visit on 22 October, and no planned
activities or travel on 25 October. Input SHA-256:
`954cc256063f6118cc0001342be230c437944a77bbe082372008dae912a9b4b1`.
The scenario retains former case-14's identity under
[Issue #163](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/163).

The researcher authorized synchronization and one new sequential V0-V3 selection
followed by one Primary, with a **cumulative USD 40 reference allowance including
r01**, zero retries, and a stop on another shared implementation blocker. Branch
`codex/case-12-r02` preserves the original case commit and merges `origin/main`
at `cc779bb2ece7b312ab3d985cebdd5d6b64b209c3`. The actual execution source is
merge commit `ba464335ea7765996b98e819bb31f9ed329ccf31`, incorporating
[PR #180](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/180) and
[PR #181](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/181).
The r02 attempts used the merged application without case modifications. A later
local correction changes only dated-count prompt serialization; input is unchanged.

## Reviewed obligations and observed interpretation

A new source-only author and a distinct reviewer produced RequirementSpec revision
`"2"`. Its hard obligations are:

| Date | Native obligation | Meaning |
| --- | --- | --- |
| 2026-10-22 | `daily_visit_count`, `scope=primary_visits`, exact 1 | Total primary visit occurrences, without an invented venue. |
| 2026-10-25 | `protected_time`, full day, `scope=scheduled_commitments` | No planned activities or travel throughout the local day. |

Nature, harbour views, relaxed pace and other-date choice flexibility remain soft
preferences without invented quotas. Reviewed density uses a relaxed default,
exact one on 22 October and exact zero on 25 October. Density does not replace
the hard obligations; zero primary visits alone does not prohibit travel.
Transport modes are unrestricted outside the rest-day prohibition. The schedule
context uses `Australia/Sydney`.

Current native spec, schedule and density validators accepted these materials
offline. Both actual r02 interpretations passed the shared hard-requirement
boundary. V1's exact saved response, restored with the request-bound indexed
source mapping, contains the correct hard daily total and fixed full-day rest
protection. Its count requirement has registered predicate
`daily_primary_visit_count`, version `1`, and disposition `enforce`.

V0 contains one primary visit on 22 October and no activities or transfers on
25 October. Its product count diagnostic is PASS with lower/upper bounds 1/1.
These are submitted-role/product observations, not independent factual scores.
Its primary counts over 22-28 October are **1, 2, 1, 0, 1, 1, 1**.

## V1 prompt-construction blocker

The original V1 `failure.json` records only `error_type=TypeError`, without a full
traceback. Its trace reaches `generation_started` and
`opening_hours_planning_views_created`, then `run_failed`. Only interpretation,
landmark nomination and POI semantics model calls occurred; the primary itinerary
model request was not sent. No V1 itinerary result exists.

The affected boundary is the
[candidate supply projection](../../backend/app/services/planning_supply_pipeline.py)
and its [V1 graph JSON serialization](../../backend/app/versions/v1/graph.py).
The new `daily_visit_constraints` projection calls
`model_dump(exclude={"source_refs"})`, leaving a Python `date`. The graph then
calls `json.dumps(planner_supply_projection(...))`.

A separate zero-network minimal reproduction restored the actual V1 captured
interpretation through unchanged current readers, retained its dated constraint,
supplied empty unrelated candidate data, and invoked the same projection/JSON
boundary. It deterministically raised:

```text
TypeError: Object of type date is not JSON serializable
```

Two original in-memory controls serialized successfully: omitting the daily constraint
projection, and retaining it with `model_dump(mode="json", ...)`. This reproduction
and the online trace locate the serialization blocker; the detailed local exception
is not presented as a recovered full online traceback.

The researcher then authorized a local shared correction, to be integrated with
later case material. Commit `d523dd4f7003348c9bf36890280e3ea737dbb4b7` changes the
dated-count projection to JSON mode, preserving the domain `date` and source exclusion.
The regression covers the actual graph caller, not only the helper's field values.
No generic string fallback, schema, constraint meaning, Repair or evaluator rule changes.
Full online graph replay was not attempted; r02 captures retain their original source.

The failed attempt was retained without retry. V2/V3 use the shared tools path,
but their behavior was not observed in r02. Primary was not prepared or executed
because a qualified four-final selection is absent.

## Attempts and resources

Native usage and costs include failed invocations. Reference rates were rechecked
on 17 October against official
[model](https://developers.openai.com/api/docs/models/gpt-6-luna),
[embedding](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[tool](https://developers.openai.com/api/docs/pricing), and
[Google](https://developers.google.com/maps/billing-and-pricing/pricing) sources.
OpenAI rates are an explicit Foundry proxy. Account invoices and external Codex
usage/billing are unavailable; no discounts, free quotas or tax are assumed.

| Revision/version | Outcome | Native invocation seconds | Model calls, including embeddings | HTTP sends | Observed tokens | Reference USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| r01 V0 | Completed | 62.063 | 2 | 2 | 26,275 | 0.004371665 |
| r01 V1 | Completed | 119.766 | 4 | 68 | 84,990 | 2.364824325 |
| r01 V2 | Completed | 145.922 | 6 | 98 | 85,629 | 2.972827120 |
| r01 V3 | Clarification before generation | 26.938 | 1 | 1 | 18,758 | 0.001643150 |
| r02 V0 | Completed | 47.344 | 2 | 2 | 23,269 | 0.003886710 |
| r02 V1 | Prompt construction failed | 69.422 | 3 | 64 | 22,438 | 2.259815495 |
| Total | All six invocations | 471.455 | 18 | 235 | 261,359 | 7.607368465 |

The r02 increment is **USD 2.263702205**; the remaining cumulative allowance is
**USD 32.392631535**. No failed HTTP response, incomplete send or unpriced event
was recorded. V1's absent result hash does not erase its observed consumption.
No evaluator or paired-access consumption occurred. The r02 reservations were
generation USD 24.25 and Primary USD 10, within the post-r01 allowance; generation
has no native USD hard stop. Runtime request/token/time ceilings were unchanged
and costs were checked between versions.

Actual wrapper times on 17 October Australia/Sydney were V0 14:34:18-14:35:12
and V1 14:35:21-14:36:38. Native durations above exclude the wrapper's additional
startup/finalization overhead.

## Checks, assistance and retained evidence

The r02 preflight passed input/date admission, worktree-local Python 3.12.14,
imports/CLI, locked dependencies, both pinned tokenizers and query-only TripWorld
compatibility. The initial database probe lacked environment loading; loading the
existing files corrected the local probe without changing credentials or config.
Git metadata access needed sandbox escalation. Related source-wire, daily-count,
V3 and independent requirement tests passed **131 tests in 18.35 seconds**.
Those preflight checks preceded the live failure and did not cover the missing
serialization seam. Corrective verification subsequently exercised it:

- The new mocked V1 graph regression failed with the same date-serialization
  TypeError before the fix and passed after it.
- Complete projection JSON round trips cover exact zero, exact one and minimum
  three, preserving the ISO date, hard strength and requirement links. Existing
  graph tests retain coverage for requests without dated totals.
- Affected projection services and V1-V3 regressions passed 642 tests initially;
  18 fixture setup errors came from a missing parent for the operator-selected
  temporary directory. Creating that directory and rerunning just those 18 passed
  all of them. All 660 selected tests passed across the two runs; no application
  or environment configuration was changed to resolve setup.
- Ruff lint/format checks passed for all three changed Python files. Restoring
  the actual failed V1 response through current readers and serializing its fixed
  projection also passed, with zero provider calls.
- Independent Standards and Spec reviews of `0f08e83...d523dd4` found no actionable
  issues. This is scoped offline verification, not a full-repository or live pass.

Parent `/root` performed synchronization, preflight, orchestration, saved-evidence
diagnosis, the later correction/tests and documentation. Its runtime model and billing are not
exposed. Actual external assistance for r02:

| Actor | Configured model/effort | Work |
| --- | --- | --- |
| `/root/case12_r02_author` | `gpt-6.1-sol/high`, fresh context | Original-request-only author draft. |
| `/root/case12_r02_reviewer` | `gpt-6.1-sol/high`, distinct fresh context | Independent review, schedule, density and transport material. |
| `/root/case12_r02_execution` | `gpt-6.1-sol/medium`, fresh context | Frozen V0 then V1 commands; stopped on failure. |
| `/root/serialization_standards_review` | Inherited parent; exact runtime unavailable | Read-only Standards review of committed correction/tests. |
| `/root/serialization_spec_review` | Inherited parent; exact runtime unavailable | Separate read-only review against the approved correction scope. |

Configuration is recorded from actual parent orchestration requests; child-side
model telemetry is unavailable. Requirements actors saw only allowlisted original
input, draft/provenance and contract/schema material. Notes disclose adjacent
code, truncated reads and a narrowly expanded pace-enum inspection. They did not
see Planner outputs, interpretations, scores or mechanisms. Actual actor IDs,
times, drafts, reviewed bytes and authentic available message excerpts are retained;
separate execution UUIDs and complete internal/tool transcripts are unavailable.
Agent review is not human review. The r01 independent interest draft remains
applicable to the unchanged input; no later inventory/relevance study ran.

Private roots are logical evidence identifiers, not public dependencies:
`benchmark/scratch/case-12/work/run-r01/` and `run-r02/`. They retain all successful
and failed captures, source-only reviews, commands and execution receipts,
usage/prices/costs, candidate captures where executed, wire/trace evidence, and
the r02 reproduction/control outputs. The r01 preservation index covers 2,067
existing files. No raw r01 evidence or consumed capture was overwritten, and no
old-baseline output was inserted into r02.
Local corrective replay/check material is retained separately under
`benchmark/scratch/case-12/work/serialization-fix/`.

| Evidence | SHA-256 |
| --- | --- |
| r02 V0 saved result | `35034b7a2f6f94379dcdab246aad61aca9b3552f8c0beebdb2297592c0492423` |
| r02 V1 saved interpretation response | `d915708ee1685da96a6389392bdf008d13e9d062fd7f0c43c3114d2f9ccc66cc` |
| r02 reviewed requirements | `6601f742a2fa7ccb903b31c45c2580cad6d6a74524bdee781b0b5b5ca00114b9` |
| r02 frozen generation command manifest | `eae226655fcbe2ba3c247eb092d0df7597a961f06a1ad7d2e09dc4e671af1a58` |

## Historical context

On the same Sydney date, r01 used source
`b73c8eed09fafb6d54bee8684c5b2e7766515357`. V0-V2 completed with first-day primary
counts 1/1/1 and no activities or transfers on the rest day. V3's separate
interpretation added hard `semantic_3`, which the then-current shared gate could
not enforce and stopped as `unsupported_hard_requirements` before generation.
The independent r01 spec retained the generic daily count as unsupported, and a
source-only population precheck blocked numerical preparation. Those records
remain unchanged; r02 uses the new operator prospectively. r01 passed 109 scoped
offline tests.

r01 used separately operated author, interest, source-review and execution agents.
An initial reviewer exposed to historical project outcomes was excluded; its
replacement disclosed only generic schema/policy headings without case results.
Available message excerpts, actor/configuration records, source hashes and the
excluded-operation disclosure remain in r01. Neither revision supplies independent
Primary scores, a real V3 Repair observation or an accepted case.
