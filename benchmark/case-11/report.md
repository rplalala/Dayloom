# Case-11: Paris, France

## Status and scope

Execution revision 1 started on 17 October 2026 Australia/Sydney and is
**blocked before independent primary evaluation**. V0 and V1 each completed one
selected generation. V1's submitted final-day timestamps fail the numerical
population preparation gate; V2, V3 and paid evaluation remain unstarted. There
are no primary scores and the case is not accepted.

The [original request](../inputs/case-11.json) is unchanged: Paris, 22–25 October
2026, two adults, EUR 1,500 for the whole group and trip, art and architecture
interests and moderate pace. On 23 October, 14:00–16:00 Paris local time must
contain no scheduled activities or travel. Source SHA-256 is
`60a5c7fc106d785f8f50e6a503f34010c8eb4979562a164f4b26612454972487`.
The live scope and USD 40 reference allowance were explicitly authorized in the
current individual case chat. [Issue #160](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/160)
is the case tracker; its remote status has not been changed during this local stage.

All attempts use application source
`b73c8eed09fafb6d54bee8684c5b2e7766515357`, runtime file SHA-256
`a6c932272e8d5037ed66fb057e629f8dcff44f3e12117d2dbcb16c8905454058`
and runtime snapshot SHA-256
`ed0853d6968c8b526a695e9a69b97e22dc2e331291e4051ddc8d305046cd5107`.
No application implementation or runtime configuration changed.

## Selected material and preparation

| Material | Reader view |
| --- | --- |
| Independent final requirements | [Reviewed specification](requirements/reviewed.json) |
| Independent source-only interests | [Art and architecture judgments](interests/source-review.json) |
| Independent source policies | [Transport](requirements/route-reviews.json), [density](requirements/density-reviews.json), [destination time](requirements/schedule-context.json) |
| Selected submitted itineraries | [V0](generation/v0/itinerary.json), [V1](generation/v1/itinerary.json) |
| Native V1 population gate and temporal evidence | [Preparation diagnostics](evaluation/population-v1.json), [locked-environment probes](evaluation/temporal-v1.json), [model-to-output origin](evaluation/timezone-origin-v1.json) |
| Attempt consumption and source hashes | [Primary-stage resource ledger](resources/primary-stage.json) |
| Source and publication bindings | [Material index](material-index.json) |

The reviewed specification has one resolved `protected_time` obligation with
`scope=scheduled_commitments`. It invents no named-venue obligation or visit quota.
The independently reviewed transport status is unrestricted, daily density is
ordinary with no exact count or dated override, and the destination zone is
`Europe/Paris`. Source-only interest judgments retain art and architecture
separately without adding counts; their reader view is not a native venue-relevance
report.

Python 3.12.14, all 63 installed distributions against the lock file, local
editable imports/CLI, both checksum-bound tokenizers and the query-only TripWorld
manifest/vector-space/policy checks passed. Four native offline generation
preparations passed with zero dispatches. The known sandbox database/temporary-file
restrictions passed verification outside the sandbox; live invocations therefore
used the approved escalated path from their first dispatch. No credential or
permission reset was performed.

Native requirements handoff validation passed. Both selected outputs use
`itinerary_3` and have complete role/occupancy review coverage without required
additional semantic decisions. V0's numerical population preparation is ready.
V1's role/occupancy coverage is ready, but its temporal population is not.
These are preparation states, not independent factual scores or feasibility PASSes.

## Temporal blocker and scoring availability

The independent IANA context, backed by installed `tzdata 2026.1`, changes Paris
from UTC+02:00 to UTC+01:00 on 25 October. V1 instead retains UTC+02:00 for all three
selected activities that day:

| Activity | Submitted interval on 25 October | Native reason |
| --- | --- | --- |
| Musee de Cluny | 10:00–12:00, +02:00 | `timezone_offset_conflict` |
| Sainte-Chapelle | 12:45–13:45, +02:00 | `timezone_offset_conflict` |
| Conciergerie | 14:30–16:00, +02:00 | `timezone_offset_conflict` |

The raw names and timestamps remain in the linked V1 itinerary. Native
`normalize_interval` returns UNKNOWN with no adopted span for each conflict.
`population_readiness` returns `needs_population_resolution` with the exact three
result-hash/pointer bindings. Two submitted transfers on the same date also retain
+02:00 and return the same temporal UNKNOWN; these are corroborating native time
probes, not an additional primary score or transport-association judgment. The
new-wire numerical gate requires this population
to be established before paid acquisition. Source preservation prohibits silently
changing the offsets, choosing a favorable clock/instant interpretation, replacing
the independently supported zone, or switching to an older scoring profile.

| Version | Generation | Primary score | Primary FAIL/UNKNOWN inventory |
| --- | --- | --- | --- |
| V0 | Completed | Unavailable: evaluation not started | Not computed |
| V1 | Completed; population blocked | Unavailable: evaluation not started | Not computed; three preparation time-UNKNOWNs above |
| V2 | Not started | Unavailable | Not computed |
| V3 | Not started | Unavailable | Not computed |

No qualified four-version manifest, executable primary package or evaluation receipt
exists. The three time-UNKNOWN preparation records are not a zero score, a completed
primary UNKNOWN inventory, or evidence that the meeting obligation passed or failed.

### Origin and application acceptance gap

The 17 October offline diagnosis locates the error in the original model output,
with a separate application acceptance gap. All 209 files in the V1 evidence index
retain their captured artifact hashes. The primary event
`06398975a5bc4278b0b7af602ce26bec` binds credential-filtered logical request/response
identifiers `evidence/wire/0060-request.json` and
`evidence/wire/0060-response.json`; these identify private evidence, not public links.
The captured response file SHA-256 is
`32220c72846aa8774a2f8a3d9cbdf23494dc443dd6d6f5d75b27d32bb21933f8`.
Observed HTTP-body hashes refer to a distinct pre-filter representation; the
artifact-file hashes verify the saved filtered JSON wrappers.

The model itself returned the October 25 activity components
`date=2026-10-25`, `time=10:00:00`, `utc_offset=+02:00`, and the same wrong offset
for the other five activity endpoints that day. Replaying the actual
`FoundryPrimaryItineraryDTO` and `map_foundry_v1_itinerary` over that saved response
preserved all eight activity start/end pairs exactly. The captured accepted
primary-generation trace and final itinerary contain those same times. There is
no evidence of an offset introduced or rewritten by DTO mapping or serialization.

The primary trace contained no transfers. Replaying real `route_option` with the
saved normalized Routes bundle, submitted activities and unchanged policy
reproduced both October 25 WALK transfers exactly: departure inherits the preceding
activity's end; arrival adds 597 or 139 seconds, with zero reserve. Program-owned
transport therefore propagates the model's bad offset rather than independently
creating it. No provider/client was constructed for these replays.

The actual model request already included `Europe/Paris` in all fourteen supplied
place timezone fields and in weather evidence. The system prompt required numeric
UTC-offset components but did not explicitly describe the DST transition or
provide per-date offsets. Wrong/missing IANA identity is ruled out for this case;
the effect of stronger prompting has not been tested and is not a demonstrated
standalone cure. The application schema requires aware endpoints and matching
civil dates, and the trip-date guard accepts this captured output; neither checks
that a supplied offset agrees with the identified IANA zone. Independent evaluation
correctly detects that conflict later.

A deterministic offline probe fails on the original three activities and remains
failing after reducing to the first interval. Synthetic in-memory controls with
the correct +01:00 offset, the preceding day, or no zone context normalize known.
The controls are not adopted source edits. Existing mapping, V1 itinerary adapter,
evaluator time and initial mixed-route tests passed: **81 tests in 4.55 seconds**.
These passing baseline tests do not establish a fix; application behavior is unchanged.

### Proposed minimum correction and verification

The proposal is not implemented. Keep the DTO and its exact-value mapping unchanged.
At the shared tools output-acceptance boundary in
[the output policy](../../backend/app/policies/itinerary_output.py), check each
known venue's supplied IANA zone against both submitted activity endpoints before
transfer construction. Reject a known offset/local-clock inconsistency with an
explicit source-linked diagnostic. Preserve unresolved zone evidence rather than
inventing a fixed offset or silently choosing between conflicting zones. Do not
rewrite timestamps, retry generation, or import evaluator scoring/evidence into
the Planner. The V0 `places=None` branch remains unchanged.

Add a short instruction to [the tools prompt](../../backend/app/versions/v1/prompts.py)
to derive each endpoint's offset from the supplied IANA zone and actual date,
including DST; a trip-wide constant is not sufficient. This adds no provider call,
new transport mode, response schema, evaluator rule or budget increase. The prompt instruction addresses the missing DST guidance; deterministic
acceptance prevents silent propagation even when the model still errs. This minimum does not guarantee that a future model run
will succeed.

Validation should cover the saved bad-offset pattern at the real DTO-to-acceptance
seam; valid Paris October 22–24 +02:00 and October 25 daytime +01:00; both valid
explicit offsets in an autumn fold; nonexistent spring local time; an interval
crossing a transition with different valid endpoint offsets; an ordinary non-DST
zone; missing/conflicting zone evidence; and unchanged input/output bytes. Mocked
graph tests must show no extra post-response Routes/Nearby sends or retry after a
rejection. V1/V2/V3 share initial acceptance, and V3 validation/final delivery also
call the output policy, so their wiring, Repair failure/retention behavior and valid
final acceptance need affected regression coverage. V0's independent branch and
historical evaluator/readers remain compatibility controls. The old captured V1
must still be rejected by the independent gate; it cannot become a corrected run
through a code or report change. A new live revision remains a separate decision.

## Resources

| Selected generation | Native elapsed seconds | Model calls | Tokens | HTTP sends | Reference USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| V0 | 65.344 | 2 | 27,772 | 2 | 0.006291725 |
| V1 | 112.641 | 4 | 67,817 | 64 | 1.982172725 |
| Total | 177.985 | 6 | 95,589 | 66 | 1.988464450 |

V1 sends comprise four Foundry model HTTP requests, eleven Google searches,
28 Details requests, twenty Matrix requests and one weather request. All observed
V0/V1 sends completed, and their native cost reports have zero unpriced events.
There were no retries, embedding sends, V3 Repair sends or independent evaluation
sends. USD 38.011535550 of the USD 40 reference allowance remains unspent.
The per-stage reservations were V0 1, V1 8, V2 10, V3 13 and primary evaluation 8.

Native generation prices retain their original 8 October reference basis, checked
against current official references during this chat's offline preparation. Foundry
cost uses the declared OpenAI retail proxy; actual account invoices, discounts,
credits and tax are unavailable. External Codex use is separate and its tokens and
billing are not observable. No missing bill or external-agent cost is treated as zero.

## AI assistance and current boundary

| Work | Actual performer and available configuration |
| --- | --- |
| Orchestration, preparation, source checks, offline origin diagnosis/replays, resource reconciliation and local presentation | Current parent Codex chat; exact parent model/effort not independently exposed |
| Source-only requirements author | `/root/case11_requirements_author`, explicitly dispatched `gpt-6.1-sol / high`, fresh context |
| Independent requirements review | `/root/case11_requirements_reviewer`, explicitly dispatched `gpt-6.1-sol / high`, fresh context |
| Source-only interest judgments | `/root/case11_interests`, explicitly dispatched `gpt-6.1-sol / high`, fresh context |
| Source-only transport, density and time review | `/root/case11_source_policies`, explicitly dispatched `gpt-6.1-sol / high`, fresh context |
| Corroborating literal V1 temporal review | `/root/case11_v1_temporal_review`, explicitly dispatched `gpt-6.1-sol / high`, fresh context; native probes independently reproduced by the parent |
| Two selected live invocations | `/root/case11_live_executor`, explicitly dispatched `gpt-6.1-sol / medium`; native Planner deployment `gpt-6-luna` |

Author and reviewer used the complete original request and exact authored draft in
ordered separate executions, excluding Planner interpretations, generated results,
scores and mechanisms. The author disclosed an overbroad read of generic contract
text; no case-result evidence was exposed. The actual author artifact, reviewer
artifact, observations, dispatch settings and available verbatim final-response
excerpts are retained privately. Full child conversation/tool exports and external
Codex token/billing telemetry are unavailable; no complete transcript was fabricated.
The independent reviewed spec kept the author's semantics and changed review metadata.

The temporal reviewer disclosed accidental exposure to nested itinerary route
diagnostics/validation fields and a discarded PowerShell display conversion of
timestamps. Its work is labelled corroborating, not uncontaminated/blinded review,
and supplies no adopted scoring override. The reviewer used system Python 3.13.5;
the parent reproduced all twelve raw interval probes with the locked Python
3.12.14 environment and obtained identical native results.

The researcher authorized the scope and budgets; no human review of itineraries or
case acceptance has occurred. Original V0/V1 native captures, logs, source snapshots,
registration artifacts, requirements provenance and preparation diagnostics remain
under private logical root `benchmark/scratch/case-11/work/r01`; the material index
maps the reader views to those unchanged sources. Existing accepted cases are untouched.

Execution is paused at the blocker. No input/output correction, replacement run,
additional paid acquisition, post-primary process analysis, paired scoring, human
study or remote publication is included in this stage. Continuation requires an
explicit decision on the preserved V1 timestamp conflict and the affected execution
scope; unused budget does not authorize a retry.
