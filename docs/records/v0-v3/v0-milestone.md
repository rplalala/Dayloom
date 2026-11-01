# V0 milestone and later shared changes

V0's original milestone was completed on 2026-09-11 at `34943c7`. It established a
plain-LLM baseline; later shared changes do not rewrite that historical freeze or
validate earlier runs. Current behavior belongs to the [design index](../../README.md).

## Original frozen research boundary

Successful runs used requirement extraction then itinerary generation in a two-node
graph with exactly two LLM calls. The frozen boundary covered semantic prompt/planning
behavior, reference-date handling, strict Azure DTO/domain mapping, fail-fast missing
critical requirements, shared `PlanningResult` / `SystemVersion.V0` and independent
`scripts/run_v0.py`. It excluded tools, external information, retry/regeneration,
constraint-validation loops and Repair. Compatible shared changes required preserving
that intended research behavior and passing V0 regressions; a freeze was not file immutability.

The original offline gate passed **50 tests**, Ruff and diff checks. Coverage included
topology/call order, provider configuration, strict mapping, failure behavior, CLI exits,
network isolation and cp 936 Unicode round-trip.

## Consequential later changes

| Date | Change | Validation boundary |
| --- | --- | --- |
| 2026-09-19 | Authorized common `planning_request_2`, authoritative structured facts and optional semantic preference interpretation; empty preferences skip interpretation. | Shared **769 passed, 9 skipped**, Ruff/diff; no live or old-output parity claim. Old-input V0 and revised V1 cannot be a tools-only matched comparison. Frontend alignment was then pending. |
| 2026-09-20 | V0 remained tool-free while the joint V1/V2 quality-first work continued. | V0 was not rerun in that joint event; quality-first limits did not extend its CLI or rewrite old freeze configuration. |
| 2026-09-25 | Optional transfer-output compatibility and shared startup correction. | Fresh V0 CLI failed before `--help` from eager service exports reentering its graph. Lazy exports fixed the cycle; fresh-process checks covered V0–V3. Shared prompt 13 budget scope was offline-only. |
| 2026-09-28 | Authorized prompt request for estimated transport Activities and nearby references by date/area. | Plain LLM plus prompt retained; no new call/tool/validator/Repair. Berlin revalidation returned six days, **17 main visits, 11 estimated transport activities, 1 Nearby reference**; combined **176-pass** regression and clear reviews. |

The [transfer compatibility record](v1-development.md#shared-mixed-transport)
and [shared closeout](v3-milestone.md#delivered-mechanism-and-historical-boundary) locate startup/output boundaries. The
[transport/Nearby acceptance](development-pilots.md#v0-estimated-transport-and-nearby)
locates the Berlin result; the original [shared output design](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/a6aff13a00af35467b9c88ec2906d10a96095f04/docs/shared_itinerary_output.md)
records its initial **80-pass** offline check. The
[shared milestone notice](v3-milestone.md#delivered-mechanism-and-historical-boundary)
locates Product/default and recovery limits at that checkpoint.

## Known Limitations

- Travel facts come only from model pretraining and may be outdated or inaccurate.
- Opening hours, availability, prices, routes, travel times, weather, and disruptions
  are not verified.
- UTC offsets are supplied by the model and checked for format, not geographic or
  date-specific correctness.
- Itinerary feasibility and user constraints are not programmatically validated.
- Missing critical requirements are not resolved through an interactive clarification
  flow.
- Provider, DTO, mapping, or domain failures terminate the run without recovery.
- V0 has no persistence, memory, or repair mechanism.

These limitations distinguish baseline output from independently verified travel facts.
Prompt-level estimated transport supplies no provider-backed journey evidence, and
bounded content validation establishes neither real-world feasibility nor a new freeze.
