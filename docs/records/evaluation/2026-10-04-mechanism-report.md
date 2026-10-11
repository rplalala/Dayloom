# Mechanism reporting development

Ticket [12 / #24](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/24),
2026-10-04. Status: Implemented, offline Validated and independently reviewed.
The [mechanism contract](../../contracts/0001-evaluation-artifacts.md#mechanism)
owns current definitions and wire; this record explains the design gap, resulting
capabilities, consequential corrections and bounded validation.

## Capture gap and design decision

At inspection revision `7c9783bdeb1b57b7fe6fdfc258dec47cc5c3dcf7`, complete saved
`V3Outcome` and Repair round records already supported triggers, authorization, attempts,
adoption and stopping observations. The cumulative result was not another round. Typed
official claims, source references and effective representations existed in memory,
but ordinary final results lacked a complete accepted-claim catalog.

Primary evidence preparation preceded budget checks/model invocation; preparation did
not prove submission. Repair traces chiefly retained fingerprints/sizing, and best-effort
traces could be disabled or truncated. Actual opening-rule selections were traceable
only where the relevant reports survived. Existing numeric usage supplied a separate
linked channel. The missing capability was provenance of actual exposure/use, not a
reason to rerun old validation and label reconstructed facts as historically used.

The approved design combined saved-material readers with minimum opt-in capture, rather
than readers alone. The read-only interface preflight passed **77 tests**. Implementation
then added selected-source preparation, mechanism reports, local commands and a
caller-owned default-off capture wrapper.
Four-version and genuine V3-only selections were supported without inventing absent runs.

## Delivered observation boundaries

Mechanism reports retain distinct original/related targets, authorized scopes, attempts,
rounds, components and internal progress. Trace copies and cumulative summaries cannot
inflate child counts. Missing observations preserve null totals and available cells.
Independent Ticket 10/11 outcomes and resource observations remain separate.

Capture records Gate-accepted catalogs, actual default-adapter primary/Repair submissions
and actual V3 opening-rule selections. It preserves prompts, call counts, planner results,
budgets and exception/cancellation behavior. Injected unobserved clients, capacity limits,
secret-bearing observations and failed writes retain partial coverage.

## Integrity and missingness corrections

Spec review found that matching trace copies compared status alone, accepting contradictory
continuation, cumulative counters or usage. Correction `877dc89` compares those shared
fields and invalidates only the contradictory trace channel, preserving valid saved-result
observations. The affected findings passed independent recheck; no runtime hook, prompt,
budget or quality score wire changed in this report-only correction.

## Validation and implementation provenance

Review base: `21986f542cd5ec72ec519709c5882477c80c7413`.
Implementation: `8e945fd45b1b0e26ec55a71e748e13f8ccf8660d`.

| Checkpoint | Observed result | Coverage |
| --- | --- | --- |
| Implementation regressions | **978 passed, 1 skipped**; dedicated **40 passed** | Evaluator, observability, official integration, multiround/V3 and default adapters |
| Implementation full gate | **2477 passed, 10 skipped**, 318.11 seconds | Backend before report-only corrections |
| Corrected evaluator gate | **640 passed, 1 skipped**, 100.09 seconds | Later correction coverage |

Checks covered actual prompt/call/result parity with capture off/on, usage-off selection,
budget aborts, failure/cancellation, exact joins, duplicates/conflicts, related targets,
pending components and missing observations. Ruff, compilation and fourteen-file formatting
passed. No mypy/pyright result was available. Gates overlap and must not be summed; the
earlier full backend result is not a later full-suite correction result.

## Publication checkpoint

Subsequent authorized publication delivered Tickets 05–12 and their corrections at
`bab0d5315f9a6dcaecb8327c1017bfe94269f2c1`, advancing the feature branch from
`fc9996803b05b9b444583f0985274bee75c4ed0f`. Linked contract/record blob parity was
verified. Tickets 10–12 and then parent #12 were closed with accepted engineering scope:
[10](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/22#issuecomment-5973113398),
[11](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/23#issuecomment-5973121380),
[12](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/24#issuecomment-5973124658),
[parent](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12#issuecomment-5973135724).
Earlier local/open states describe earlier checkpoints. Publication reused validation;
it added no live observations or formal research results.

## Limitations

Synthetic/offline checks do not establish provider receipt, model attention, causal
influence, real capture overhead, corpus coverage or version rankings. Rule-use capture
covers actual V3 operating/opening selections, not universal admission or whole-trip
affordability. Surviving trace fragments cannot establish
complete historical denominators. Source-linked local claims/excerpts are evidence
material, not publicly committed raw payloads or cryptographic proof of a real review.
