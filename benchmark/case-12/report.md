# Case-12: Sydney, Australia

## Current status

Revision r03 stopped on **17 October 2026 Australia/Sydney** before Primary.
V0-V2 completed; V3 generated an initial itinerary but failed during subsequent
Repair candidate semantic preparation. No qualified V3 final exists. Primary was
not prepared or executed, no attempt was retried, and case acceptance is pending.

The unchanged [original request](../inputs/case-12.json) covers Sydney,
22-28 October 2026, two adults, AUD 3,200 for the group, nature and harbour views,
relaxed pace, exactly one sightseeing visit on 22 October, and a full rest day
without planned activities or travel on 25 October. Input SHA-256:
`954cc256063f6118cc0001342be230c437944a77bbe082372008dae912a9b4b1`.
The scenario retains former case-14's identity under
[Issue #163](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/163).

The researcher explicitly authorized one new sequential V0-V3 selection and one
Primary under the **cumulative USD 40 reference allowance**, preserving previous
attempts and stopping at Primary handoff or a blocker. All r03 versions used
`215a3dfa5c29b2bc0751ed8d5cb7da0b8afc0339`, including the local shared serialization
correction `d523dd4`, on `codex/case-12-r02`. No application or input changes were
made during r03. Source/configuration bindings were frozen before execution.

## Requirements and observations

The independently authored and reviewed r02 RequirementSpec revision `"2"` remains
applicable to the identical original input. Its exact bytes, source-only author and
distinct reviewer records, times and available message excerpts were reused, not
represented as fresh review. Schedule/density/transport copies change only batch
identity/revision headers for r03, retaining original judgments and provenance.
Current native schema checks accepted these copies offline.

| Source requirement | Independent representation |
| --- | --- |
| Exactly one sightseeing visit on 2026-10-22 | `daily_visit_count`, `scope=primary_visits`, exact 1; no invented named subject. |
| No activities or travel on 2026-10-25 | `protected_time`, full local day, `scope=scheduled_commitments`. |

Reviewed density uses a relaxed default with exact one and zero on those dates;
it does not replace the hard obligations. Transport modes are unrestricted outside
the separate rest-day travel prohibition. Schedule context is `Australia/Sydney`.
Nature, harbour views and flexibility remain soft preferences without invented quotas.
The independently authored r01 interest meaning remains applicable; later relevance
and candidate-process studies have not run.

| r03 observation | First-day primary count / product diagnostic | Rest-day activities / transfers |
| --- | --- | --- |
| V0 submitted final | 1 / PASS | 0 / 0 |
| V1 submitted final | 1 / PASS | 0 / 0 |
| V2 submitted final | 1 / PASS | 0 / 0 |
| V3 initial generation only | 1 / PASS | 0 / 0 |

These are submitted-role and product observations, not independent factual scores.
V1 completed the previously failing prompt serialization boundary. V2's producer
records retrieval completed with a partial observation; its partial discovery is
retained rather than retried. V3 also captured initial partial retrieval before its
later failure; its failed top-level completion does not establish a completed final.

## V3 stop and evidence limits

The native failure is `SemanticAssessmentError`. The trace records initial
`generation_completed`, date validation, generation diagnostics, transfer binding
and initial retrieval fate, followed by the third `poi_semantic_assessment` failing
with `TimeoutError` after **13.593 seconds**. Earlier semantic calls were accepted
at approximately 21.646 and 21.465 seconds. The failed call has no token usage.

The relevant shared path is
[Repair candidate preparation](../../backend/app/versions/v3/repair_candidates.py),
called by [Repair service](../../backend/app/versions/v3/repair_service.py), using
[POI semantic assessment](../../backend/app/services/poi_semantics.py).
Candidate preparation passes its bounded I/O deadline to the semantic service.
The service uses the minimum of its per-call ceiling, remaining semantic allowance
and applicable caller/request deadlines. The observed 13.593-second timeout alone
does not establish exhaustion of the configured 45-second per-call ceiling or the
600-second request ceiling; the exact selected remaining deadline was not retained.

Usage attributes one model call to the Repair phase. It is a semantic preparation
call, not proof of a generated itinerary patch. No complete V3 outcome, repair
proposal/comparison/adoption record or final result is available. The saved initial
model response and initial count diagnostics remain evidence; they were not promoted
to a final itinerary, and no synthetic repair opportunity was created.

One HTTP send is incomplete. Its linked model event and HTTP event are both marked
`charge_uncertain`; they refer to one uncertain request, not two independent bills.
Native result and complete V3 cost total are absent. Registration correctly remains
blocked, so the four-final Primary cannot be run on this selection.

The case-local execution wrapper then attempted `Decimal(None)` while adding that
unknown cost, producing a secondary TypeError after the native failure. Its original
`execution-v3.json` remains start-only. Native stdout, failure, completion, usage,
cost and trace files are intact. A separate reconciliation note records the native
exit 1 and the wrapper failure without fabricating a completion timestamp. Neither
shared code nor the frozen wrapper was changed during this attempt.

## All-attempt resources

Standard reference rates were checked on 17 October against official
[model](https://developers.openai.com/api/docs/models/gpt-6-luna),
[embedding](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[tool](https://developers.openai.com/api/docs/pricing) and
[Google](https://developers.google.com/maps/billing-and-pricing/pricing) sources.
OpenAI rates are a disclosed Foundry proxy. Account invoices and external Codex
usage/billing are unavailable; no discount, free quota or tax adjustment is assumed.

| Attempt | Outcome | Native seconds | Model calls including embeddings | HTTP sends | Observed tokens | Reference USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| r01 V0 | Completed | 62.063 | 2 | 2 | 26,275 | 0.004371665 |
| r01 V1 | Completed | 119.766 | 4 | 68 | 84,990 | 2.364824325 |
| r01 V2 | Completed | 145.922 | 6 | 98 | 85,629 | 2.972827120 |
| r01 V3 | Clarification before generation | 26.938 | 1 | 1 | 18,758 | 0.001643150 |
| r02 V0 | Completed | 47.344 | 2 | 2 | 23,269 | 0.003886710 |
| r02 V1 | Prompt serialization failed | 69.422 | 3 | 64 | 22,438 | 2.259815495 |
| r03 V0 | Completed | 37.735 | 2 | 2 | 21,701 | 0.002839330 |
| r03 V1 | Completed | 92.922 | 4 | 68 | 77,537 | 2.363358560 |
| r03 V2 | Completed; partial retrieval | 124.734 | 6 | 85 | 84,052 | 2.712882170 |
| r03 V3 | Semantic timeout; no final | 140.047 | 7 | 104 | 81,468; one call missing | 3.036190545 priced subtotal; total unknown |

Across all ten invocations: **866.893 native seconds, 37 model calls, 494 HTTP sends
and 526,117 observed tokens**, plus the missing usage from one call. The priced
reference subtotal is **USD 15.722639070**. Complete cumulative cost and exact
remaining allowance are **unknown**, pending the uncertain charge; the subtotal is
not a complete total. Native V3 reports two unpriced linked events, one incomplete
HTTP send and no failed HTTP response. Primary and paired-access consumption are zero.

Before r03, all six earlier invocations totaled USD 7.607368465 with no unpriced
events. The available reference allowance was USD 32.392631535. The frozen r03
reservations were generation USD 22 (V0 0.25, V1 6, V2 7, V3 8.75) and Primary
USD 10, leaving USD 0.392631535 unallocated. Generation has no native USD hard stop;
request/token/time ceilings remained unchanged and costs were checked between versions.
The current stop reflects missing final material and uncertain usage, not evidence
that the USD 40 allowance was exhausted.

## Checks, assistance and preservation

r03 preflight passed unchanged input/date admission, worktree-local Python 3.12.14,
imports/CLI, locked dependencies, both pinned local tokenizers, query-only TripWorld
compatibility and original-review reuse/schema checks. The prior correction's 660
related offline checks and Standards/Spec reviews remain applicable to the unchanged
application; no new full-suite or live all-version success is claimed.

Parent `/root` owns preparation, orchestration, bounded saved-evidence inspection,
accounting and documentation; its exact runtime model and external billing are not
exposed. `/root/case12_r03_execution` was explicitly configured as
`gpt-6.1-sol/medium`, fresh context, for frozen execution only. It ran V0-V3 once,
reported the native/wrapper failures, and stopped without Primary or retry. Earlier
source-only review provenance is reused explicitly; no new author/reviewer operation
is claimed. Agent inspection is not human review.

Private evidence roots are logical identifiers, not public dependencies:
`benchmark/scratch/case-12/work/run-r01/`, `run-r02/`, `run-r03/`, and the separate
`serialization-fix/` checks. The r03 preservation index verified **3,590 prior files**
unchanged. Raw provider/model captures, failed attempts, actual commands, receipts,
usage/costs and source bindings remain retained. V1/V2 passive candidate captures
are available for completed r03 versions. Available authentic agent message excerpts
are retained; full internal/tool transcripts and external invoices remain unavailable.
No old-baseline output was inserted into r03, and no consumed source was overwritten.

| r03 evidence | SHA-256 |
| --- | --- |
| V0 saved result | `8d4eafb8068994555689aaf34fad51f4bfb61a082ee50ea7d4dfef70da61691c` |
| V1 saved result | `d27bb7bef8f75f3f6f64f3936cf6bc308b4623d7dfaa6779a8ac921bb0569824` |
| V2 saved result | `15efdb82acc3317e2a4e24b98436297bdc8eb4ba885a01e9b581aa833560f323` |
| V3 initial response only | `f0277e4b8c0fdfbde6b9740a2dc4c24bc930933b2e87d8eaf392f0f945c6cd20` |
| Reused reviewed requirements | `6601f742a2fa7ccb903b31c45c2580cad6d6a74524bdee781b0b5b5ca00114b9` |
| Frozen generation commands | `e0ff44fd5209a9b06a8add2bdc538c20f4399fe891ceb9ca7946fcb860320dba` |

## Historical context

r01 used `b73c8eed09fafb6d54bee8684c5b2e7766515357`. V0-V2 completed with one
first-day primary visit and an empty rest day. V3's separate interpretation emitted
hard `semantic_3`, unsupported by the then-current shared gate. Its independent
spec retained that total as unsupported; numerical preparation was blocked. The
historical unsupported records remain unchanged. r01 passed 109 scoped checks;
an initial reviewer exposed to historical project outcomes was excluded, and a
distinct source-only replacement supplied the admitted review with exposure limits.

r02 merged main `cc779bb2ece7b312ab3d985cebdd5d6b64b209c3`, including
[PR #180](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/180) and
[PR #181](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/181), at execution
source `ba464335ea7765996b98e819bb31f9ed329ccf31`. A new independent spec used
`daily_visit_count` prospectively. V0 completed; V1 failed because its supply
projection left a Python date for `json.dumps`. The user authorized local repair:
`d523dd4` uses JSON-mode projection with graph and round-trip regression tests.
The graph test failed before the fix and passed afterward. Of 660 selected checks,
642 passed initially and 18 fixture setup errors passed after creating the missing
temporary parent and rerunning those 18. Ruff and both independent review axes passed;
the actual failed response also serialized correctly offline. No live r02 retry ran.

Earlier source-only authors, reviewers and interest actor were configured as
`gpt-6.1-sol/high`; execution actors used `gpt-6.1-sol/medium`. Local correction
reviewers inherited the parent configuration, whose exact runtime is unavailable.
Actual identities, times, hashes, excluded-review disclosure and authentic available
messages remain in the corresponding private roots and Git history. None of the
three revisions supplies independent Primary scores or an accepted case.
