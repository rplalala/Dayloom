# V1 milestones and reopening

These checkpoints identify historical scope, not current freezes. [V1 development](v1-development.md)
explains provider/supply decisions; [current designs](../../README.md) define behavior today.

## Freeze stages and changed responsibility

| Date | Accepted boundary |
| --- | --- |
| 12 September 2026 | Original V1-A: Places/Weather/Routes, without Reviews, Web, RAG or Repair |
| 14 September | Revised V1-A: review enrichment, separate ExperienceProfile and deterministic selection |
| 15 September | Complete V1: selected-place official/current Web and graph integration |
| 19 September | Reopened selection through B1/B2 to deterministic supply, without a new freeze |

Review responsibilities moved into V1-A; Reddit/TripAdvisor acquisition was excluded.
Ratings remained separate from Profile. Historical masks and prompt revisions retain
their recorded scope rather than becoming present defaults.

## Named identity and evidence-following checks

An initial required Opera House identity stayed unresolved despite selection. Typed named
intent and exact identity reconciliation resolved it on a separate identical-input check.
A broader search then covered nine supported intents: 123 observations/85 identities,
36 admitted candidates, 18 rich candidates and 16 supplied. Reviews changed one membership;
four WALK chunks supplied 256 elements. The revised V1-A gate passed 507 backend tests.

Generation still attributed route numbers incorrectly and sometimes visited outside supplied
hours. Prompt corrections did not create deterministic feasibility: one plan reserved about
15 minutes against about 28 minutes WALK evidence. Web truncation/inaccessible pages retained
UNKNOWN. An unsupported-price rejection's original cause was unrecoverable. Later 158-test
prompt regression did not constitute another complete live flow.

## Shared baseline developments after freeze

The 20 September quality-first V1 run had 24 ordinary successes/comparisons, twelve supplied
and eight scheduled places, with independent Nearby. The [V2 milestone](v2-milestone.md)
records the paired scope and later failed full gate/targeted corrections. Neither result
re-froze V1 or established a V3-only benefit.

Optional transfers and application-owned mixed modes followed on 25 September, preserving
independent execution. This was offline-validated and did not extend prior live acceptance.
The [shared transport record](v1-development.md#shared-mixed-transport) owns that evidence;
the [V3 milestone](v3-milestone.md#delivered-mechanism-and-historical-boundary) records
Product/version boundaries then.

## Limits

Relevant supply is not guaranteed suitability or scheduling. Representative TRANSIT and
mirrored reverse durations are not timetable proof. Sparse/repeated or factually uncertain
plans can complete. Historical freeze and bounded integration are not statistical reliability.
