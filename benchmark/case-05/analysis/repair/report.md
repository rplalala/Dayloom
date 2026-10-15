# Case-05 Repair process

The selected revision-3 V3 run ends `ACCEPTED_COMPLETE / authorized_targets_complete`. Four original soft-pace targets are addressed by four added visits on 16, 17, 18 and 20 October; all six original visits remain. The resulting schedule has two primary visits on every requested day. Independent version finals score V2=92 and V3=100, but those invocations do not isolate Repair's effect. The [same-run pair](../../evaluation/v3-pair/report.md) supplies that descriptive before/after view.

## Execution and timing

Repair contains two patch-model rounds and one candidate-preparation model call: three Repair-scoped model calls and 149,869 observed tokens. These are internal operations within one V3 stage attempt. The first local round is rejected because evidence/binding changes alone do not improve the arrangement. The second replan round has four accepted components and is the selected lineage. No SDK automatic retry occurred.

At model dispatch, round 1 retains 67.1724 seconds in its soft reference window but admits the configured 70-second model timeout under its hard window. Round 2 retains only 36.5902 reference seconds, while its hard round window has 85.687 seconds and still admits 70 seconds for the model. The corrected allocation therefore exercises the intended distinction between a soft preparation/reference target and the hard model/recheck deadline. Existing request, stage, round, recheck and finalization reserves remain unchanged; `preparation_reference_met` is retained as an observed stop reason.

Both model rounds are actually dispatched, the selected changes are rechecked and adopted, and the final producer report has no remaining soft-pace targets. The independent paired report verifies four added visits, no venue loss and no unresolved correspondence. Source data and both round outcomes remain in the original capture. Full integrated acceptance of the timing correction remains pending main-worktree integration and relevant tests.

The [summary](summary.json) preserves native mechanism fractions, exact timing snapshots, selected lineage, source hashes and independent continuity. Internal target resolution and independent quality remain separate observations.
