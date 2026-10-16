# Case-12: Sydney, Australia

## Status and request

Attempt r01 ran on **17 October 2026 Australia/Sydney**, using application source
`b73c8eed09fafb6d54bee8684c5b2e7766515357`. V0-V2 completed. V3 stopped at the shared
hard-requirement boundary before generating an itinerary. No V3 draft, validation
or Repair result exists. Automatic case acceptance remains pending; this attempt
does not supply a qualified four-final batch or independent primary scores.

The [original request](../inputs/case-12.json) is a seven-day Sydney trip,
22-28 October 2026, for two adults with a whole-group budget of AUD 3,200. It
requests nature and harbour views at a relaxed pace, exactly one sightseeing
visit on 22 October, and no planned activities or travel on 25 October. Its
SHA-256 is `954cc256063f6118cc0001342be230c437944a77bbe082372008dae912a9b4b1`.
The scenario retains former case-14's identity under
[Issue #163](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/163).

## Reviewed meaning and actual interpretation

Independent source-only authoring and review retained the first-day exact count
as a hard obligation. The native subject-specific visit operators cannot express
a total daily count without a named venue, so the reviewed specification records
that obligation as unsupported rather than inventing a place or weakening the
count. The rest day uses `protected_time`, `full_day`, and
`scope=scheduled_commitments`, covering planned activities and travel. Independently
reviewed density uses a relaxed default, exact one on 22 October, and exact zero
on 25 October. Density does not replace either hard obligation. Transport mode
choice is unrestricted; this does not waive the rest-day travel prohibition.

The four separately captured Planner interpretation responses all contain
`daily_pace.exact_count=1` for 22 October and fixed full-day protection for
25 October. None contains a zero-count density override for the rest day. V3's
response additionally creates the following sourced semantic goal:

```json
{
  "requirement_id": "semantic_3",
  "normalized_text": "Plan exactly one sightseeing visit on 2026-10-22.",
  "strength": "hard",
  "scope": "selected_poi_set",
  "experience_goal": {"frequency": "exact", "count": 1, "target": "category"}
}
```

This is a selected-field view of the restored canonical interpretation, not a
new model response. The unchanged wire, DTO and canonicalization readers restored
each original captured response offline. V0-V2 have no hard semantic item requiring
clarification in their respective responses. V3's `semantic_3` has
`capability=semantic_only`, no registered predicate, and `disposition=clarify`.
The shared
[hard-requirement boundary](../../backend/app/policies/interpreted_requirements.py)
therefore raises `ClarificationRequired` with code
`unsupported_hard_requirements` and stage `hard_requirements`.

All versions use this shared boundary. The different observed outcomes arise
from their separately generated interpretation responses; they do not establish
a V3-specific input rule. The original first-day request is clear. The stop
reflects unsupported execution capability, not missing personal intent.

## Generation observations and consumption

Each version was dispatched once through installed `rtpeval generate`, with exact
source/input/configuration bindings, native usage capture, and private HTTP/trace
evidence. V1/V2 also retained passive candidate captures. No attempt was retried
or replaced. Counts below use submitted `activity_kind=main_poi`; they are not
independently verified venue visits or factual feasibility judgments.

| Date | V0 main POIs | V1 main POIs | V2 main POIs |
| --- | ---: | ---: | ---: |
| 2026-10-22 | 1 | 1 | 1 |
| 2026-10-23 | 2 | 1 | 2 |
| 2026-10-24 | 2 | 1 | 1 |
| 2026-10-25 | 0 | 0 | 0 |
| 2026-10-26 | 2 | 1 | 1 |
| 2026-10-27 | 1 | 1 | 2 |
| 2026-10-28 | 1 | 1 | 2 |

The three completed outputs contain no activities or transfers on 25 October.
V3 has no output to count. Its successful interpretation HTTP response was followed
by the application capability stop; this is not a provider connection failure or
a successful no-Repair outcome. The producer completion envelope records failed
required mechanisms, while the trace shows retrieval initialization, generation,
validation and Repair were not entered.

| Version | Outcome | Invocation seconds | Model calls, including embeddings | HTTP sends | Observed tokens | Reference USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| V0 | Completed | 62.063 | 2 | 2 | 26,275 | 0.004371665 |
| V1 | Completed | 119.766 | 4 | 68 | 84,990 | 2.364824325 |
| V2 | Completed | 145.922 | 6 | 98 | 85,629 | 2.972827120 |
| V3 | Clarification before generation | 26.938 | 1 | 1 | 18,758 | 0.001643150 |
| Total | Three outputs; one stopped attempt | 354.689 | 13 | 169 | 215,652 | 5.343666260 |

Usage covers all four invocations, including the stopped V3 attempt. No failed
HTTP response, incomplete send or unpriced event was recorded. V3's missing result
hash reflects its absent result. Actual invoices and external Codex usage/billing
are unavailable. Costs are dated retail/proxy estimates, not actual bills. The
17 October reference check confirmed the saved rates against official
[model pricing](https://developers.openai.com/api/docs/models/gpt-6-luna),
[embedding pricing](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[tool pricing](https://developers.openai.com/api/docs/pricing), and
[Google global pricing](https://developers.google.com/maps/billing-and-pricing/pricing).
OpenAI model rates are an explicit Foundry proxy; no free-quota, account-discount
or tax adjustment is assumed.

## Independent evaluation boundary

The native registration remains blocked because V3 has no completed result.
Four-final qualification, primary preparation/execution and case acceptance were
not completed. The independent evaluator's USD 10 reference reservation remains
unused; actual generation reference consumption is USD 5.343666260 of the USD 30
generation allowance.

A separate source-obligation precheck, with no selected itinerary population or
provider calls, returned `needs_population_resolution` and
`executable_obligation_population_unresolved`. The current
[declared-population policy](../../backend/evaluation/declared_population.py)
blocks new-format numerical scoring before acquisition while a reviewed hard
obligation remains unsupported. Thus completing generation alone would not resolve
the independent evaluation boundary.

## Assistance, evidence and checks

The human researcher selected observation of the existing implementation before
deciding whether to change it. The parent Codex agent `/root` performed preflight,
orchestration, saved-source diagnosis and documentation; its exact model identity
and token billing are not exposed by the execution surface. External assistance:

| Actual actor | Work and admitted result |
| --- | --- |
| `/root/case12_author`, `gpt-6.1-sol/high` | Original-request-only requirements draft. |
| `/root/case12_interests`, `gpt-6.1-sol/high` | Independent original-request interest draft identifying nature and harbour views, without invented quotas. Native research-inventory attachment remains deferred. |
| `/root/case12_reviewer`, `gpt-6.1-sol/high` | Nonselected review operation: incidental exposure to project-home historical scores/mechanism observations; excluded from admitted source-only review. No output file was created. |
| `/root/case12_source_reviewer`, `gpt-6.1-sol/high` | Admitted distinct source-only review and schedule/density/transport policies; corrected the draft revision's wire type from integer to string without changing meaning. |
| `/root/case12_execution`, `gpt-6.1-sol/medium` | Prepared execution only: sequential native invocations and actual resource/outcome reporting. |

The admitted reviewer saw generic schema/CLI/score-field names and policy/history
headings during a README search, but no numeric result, submitted itinerary,
Planner interpretation or case-specific outcome. This exposure is disclosed in
its notes. Available authentic agent-to-parent message excerpts, actor/configuration,
times, source hashes, original draft and reviewed final are retained. Complete
internal/tool transcripts are unavailable; agent review is not human review.

Private evidence is retained under the logical root
`benchmark/scratch/case-12/work/run-r01/`: source-only review records, immutable
original request/configuration, `captures/v0` through `captures/v3`, native
registration staging, all-attempt usage/costs, the stopped V3 failure, and exact
saved-response diagnosis. These private identifiers are not public dependencies
or an admitted portable evaluation bundle. No consumed capture was overwritten.

| Evidence | SHA-256 |
| --- | --- |
| V0 saved result | `9a13b2df4fd0ec431be476a3890a5e137c65d094bbe1c05247633e41dd9c8cec` |
| V1 saved result | `db3498543c90dac66e33c5909d8f75c437eb2a912af657c5f3470fa6f4ffd59f` |
| V2 saved result | `015e512e344b51aa053a5bc22a59f6fe33a0ea623bcd54b939bd86f21855a187` |
| V3 saved interpretation response | `c1b4d52c40a3a689b0f800febc2d91fc0fb3917dc9218acecf510b7107080f8c` |
| Reviewed requirements | `68de20cd7b50e1482d79e6a7191b746326a5de27105cfb75d5c40f6bc28c771a` |

Offline startup checks passed current-date/schema/input hashes, the worktree-local
Python/import/CLI paths, locked dependencies, both checksum-pinned tokenizers and
query-only corpus compatibility. Related tests passed 105 plus four protection
cases. Sandbox/cache/temp-directory access failures were isolated and rechecked
outside the sandbox or in a fresh owned temporary directory; no credentials,
system permissions or application configuration were changed. The original input,
runtime configuration and prior accepted cases remain unchanged. These scoped
checks are not a new full-suite pass.
