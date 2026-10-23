# Case-04 Rich-policy generation and Primary

On 24 October 2026 (Australia/Sydney), [Issue #217](https://github.com/rplalala/Dayloom/issues/217)
executed one new V3 invocation and one independent four-final Primary at
`a391c2c18846f40a727038a0cf4bd176239ba904`, following the implementation in
[PR #222](https://github.com/rplalala/Dayloom/pull/222). The
[source-bound result record](2026-10-24-rich-primary.json) retains exact fractions,
per-date deductions, component counts, original source hashes and native receipt identities.
The [density contract](../../contracts/0005-quality-human-review.md#daily-density)
and [V3 completion contract](../../0005-validation-repair%28v3%29.md#final-rich-completion)
define the rules used here.

The original Singapore request, 24-25 October, two travelers, SGD 800 and
WALK/TRANSIT-only transport, remained byte-identical. The actual application date
was 24 October, inside the supported window; no clock or input date was changed.
Accepted V0-V2 outputs retained their original generation revisions. Only V3 was
regenerated. Unrelated local `.env.example` and `GLOSSARY.md` edits were excluded;
this execution made no Planner, Product or evaluator implementation change.

## Four-final Primary

All five dimensions were included: requirements, grounding, non-overlap, opening
and routes. The table uses scores on a 0-100 scale; the JSON also preserves native
normalized exact fractions. Density deductions are averaged equally across the
two requested dates under `rtpeval_daily_density_3`.

| Final | Visits, 24 / 25 October | Daily deductions | Mean deduction | Five-dimensional auxiliary score | Overall score |
| --- | --- | --- | --- | --- | --- |
| V0 | 4 / 4 | 30 / 30 | 30 | 290/3 (96.666667) | 200/3 (66.666667) |
| V1 | 5 / 2 | 70 / 10 | 40 | 100 | 60 |
| V2 | 4 / 3 | 30 / 0 | 15 | 100 | 85 |
| V3 | 3 / 3 | 0 / 0 | 0 | 100 | 100 |

The only five-dimensional FAIL was V0's Singapore Botanic Gardens to National
Gallery Singapore transit leg: independent duration 2,612 seconds exceeded its
2,100-second available interval by 512 seconds, beyond the 300-second tolerance.
Its route dimension contained five PASS and one FAIL. Every other included
component check passed. Independent UNKNOWN and acquisition-failure counts were
zero. Missing-hours assessment was enabled before scoring, but its eligible
population was empty, so no access-assessment model call was made.

These are the observed four-final results for this exact selection, not a new
twelve-case ranking or evidence that every Rich request will achieve the same score.

## Actual V3 outcome

The draft contained five and four primary visits. Four deterministic deletion
proposals produced the retained three/three final without a Repair model proposal:

| Proposal | Decision |
| --- | --- |
| Remove Singapore Botanic Gardens on 24 October | Adopted |
| Remove Buddha Tooth Relic Temple on 24 October | Adopted |
| Remove Gardens by the Bay on 25 October | Rejected because sourced experience-goal satisfaction decreased |
| Remove the Singapore skyline-view activity on 25 October | Adopted |

The native Repair status was `ACCEPTED_PARTIAL`, reason
`authorized_targets_complete`. Both dates reached the three-visit quantity target,
but final completion remained `unavailable`: the first date's coverage check was
UNKNOWN with `same_day_remaining_hours_unsupported` applicability. Visitor
suitability, budget and some semantic requirements also retained their original
Planner UNKNOWN observations. The independent Primary score of 100 does not turn
these different application checks into a fully successful Repair declaration.
No quality-driven retry, fabricated exception or manual itinerary edit was used.

## Execution and resources

The user authorized a USD 20 tool/API reference envelope, split as generation 10,
Primary 6 and later Pair 4, with one invocation per stage, concurrency one and zero
outer retries. Specific case-04 outbound data to Google Places/Routes and the
existing Azure Foundry endpoint was explicitly authorized before Primary dispatch.

Generation retained the frozen runtime: 600-second request deadline, 420-second
Repair stage, at most six proposal/replan model sends and twelve deterministic
deletion attempts. Primary retained its USD 6 native reference guard, at most 400
Google sends and two model sends, 900-second total timeout, 45-second request timeout
and native token limits of 64,000 input / 8,192 output. Both used `gpt-6-luna`;
Primary reasoning effort was `low`. Generation has no dollar-based hard stop.

| Stage | Actual use | Reference USD |
| --- | --- | --- |
| V3 | 152.25 seconds; 94 HTTP sends; six model calls including embedding; 55,539 tokens; zero Repair model proposals | 2.12482589 |
| Primary | 60 Google sends; one identity model call; 20,203 input and 748 output tokens; zero access-assessment calls | 1.1608993 |
| Combined | One generation and one Primary; zero outer retries | 3.28572519 |

Both native cost reports had zero unpriced events. These are reference estimates,
not account invoices; actual billing and external Codex costs remain unavailable.
Generation retained its 8 October reference basis. Primary used the 24 October
public [model](https://developers.openai.com/api/docs/models/gpt-6-luna) and
[Google API](https://developers.google.com/maps/billing-and-pricing/pricing) price
check, with the model rates serving as a Foundry proxy and account adjustments excluded.

## Verification and assistance

Source/input/runtime/donor hashes, the actual date, deployment and retrieval
identity passed pre-dispatch checks. Read-only retrieval preparation sent no
embedding request. Native intake accepted the four-final package; semantic review
coverage and numerical population were ready. Independent output review confirmed
the source-linked counts and applicability of role, occupancy and transport claims.
The unchanged original-request reviews retained their actual authors and timestamps.
Native offline Primary replay reproduced the entire saved execution report exactly.

The coordinator `/root` prepared bindings, verified artifacts and produced this
derived record. `/root/execute_217_v3` and `/root/execute_217_primary` used the required
`gpt-6.1-sol / medium` execution configuration. `/root/review_217_claims` reviewed
sanitized submitted claims and the original request; its inherited exact model and
effort were unavailable. External assistance is separate from the studied model
calls, and none of these agent checks constitutes human acceptance.

An initial output-review handoff exposed Planner transfer annotations. That review
was excluded and replaced with a fresh reviewer using sanitized claims. A separate
offline digest alarm came from Windows-default decoding of one UTF-8 place name;
the native UTF-8 reader verified the unchanged package. Automatic approval then
blocked process creation until the user explicitly authorized the outbound data.
Both events preceded the sole Primary invocation and consumed no Primary requests.

Private evidence identifiers are `.scratch/issue-217/captures/v3-a1`,
`.scratch/issue-217/assembled` and `.scratch/issue-217/primary-a1`, including original
draft/final/intermediate attempts, independent snapshots, receipts and usage.
They are local evidence identifiers, not public links. The linked JSON identifies
the exact native files and hashes needed by downstream work; original evidence is
unchanged.

## Handoff boundary

This completes the generation/Primary stage. The existing accepted case-04
selection remains the current publication. The new material is not yet
researcher-accepted. [Issue #218](https://github.com/rplalala/Dayloom/issues/218)
owns the same-run Pair, dependent analyses, other-case offline rescoring and
replacement acceptance after the required Primary continuation instruction.
[Issue #219](https://github.com/rplalala/Dayloom/issues/219) subsequently updates
blind-review presentation content while preserving existing answers and statistics.
