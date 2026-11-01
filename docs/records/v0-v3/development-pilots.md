# Shared development pilot evidence

Bounded September–October 2026 pilots exercised generation, resource capture and selected
mechanisms. They are engineering observations rather than controlled version comparisons.
Local artifact paths identify original evidence; current contracts belong to the
[core designs](../../README.md).

## Berlin six-day capture and blind review

On 28 September, `e68d8e6a4297d50a98fcacb3241d392781dec022`, all versions returned six
ordered nonempty days. V0/V1/V2/V3 had 16/14/14/17 scheduled activities. V1 repeated four
canonical places; V2 had two below-target days. V3 Repair changed main counts
4/4/3/1/1/1→4/4/3/2/2/2, leaving 22 factual UNKNOWNs. All 61 activity costs were unknown.

The evidence gate failed because V3's 6,041,655-byte trace exceeded the original
1,000,000-byte cap, despite complete standalone budget counters. The later 10 MB cap
passed 92 offline truncation/redaction checks but did not recover the old trace.
A separately scoped itinerary-only blind review ranked V0 > V3 > V2 > V1, preferring
variety/pacing. It did not repair evidence eligibility or establish general preferences.
Evidence: `logs/berlin_six_day_20260928/`.

## Food preference and sparse-day diagnosis

On 27 September at `8f5e9b3`, saved-output replay reproduced four sparse dates without
changing generation. Sydney/Melbourne V1 each supplied 16 eligible main candidates,
leaving seven/three unused. Food preferences survived interpretation and acquisition,
but supported food candidates were all non-main and excluded from primary supply.
Generic meals correctly did not inflate main counts. This was a role/support limitation,
not demonstrated input loss or raw candidate exhaustion.

Unused candidates did not prove any date-specific insertion feasible. Completion covered
its narrower role/multiplicity/minimum obligations, not every preference or a hard two-to-five
quota. Proposed named non-main support and better sparse-output guidance were deferred.
Raising Details/K had no demonstrated benefit to these omissions. Twelve existing diagnostic/
supply checks passed; there was no red-to-green live quality result. Evidence:
`tools/validation/packets/food-sparse-diagnosis/`, `logs/food_sparse_diagnosis_20260927/`.

## V0 estimated transport and Nearby

The 28 September prompt-only change retained plain generation without extra tools or calls.
Berlin returned six days, 17 main visits, 11 estimated transport activities and one Nearby
reference. Related regression passed 176 tests. This demonstrated output structure,
not route feasibility or a renewed freeze. [V0 milestone](v0-milestone.md) retains the
original baseline boundary.

## Sydney natural-input generation

The first 7 October preparation inserted exact-two daily visits, confounding a route test
with a generation quota. The user clarified that density scoring is not a hard generation
request; the natural input removed the count. The stopped preparation and its consumed
work remained distinct from the later successful invocation.

Run `sydney-natural-v0-20261007` retained result SHA-256
`d8ca6c8ac44aa2438f2efe65534b57488be81dbed217bc7d66626801f78431c7`.
Faithful offline replay checked the submitted output and original source hashes without
claiming model regeneration. Subsequent identity and route diagnostics are in the
[evaluator record](../evaluation/intake-identity-usage.md).

## Sydney RAG stop and host resumption

On 8 October, completed V1 and a degraded V2 were retained when RAG connection failed.
A sandbox connection check did not establish host database absence: later host Docker
inspection showed healthy published PostgreSQL, and identical read-only connection passed
outside the sandbox in 0.031s. This did not identify the earlier failure's sole cause.
No credentials or project settings were reset.

A separately authorized host resumption at
`043cae393344d41f8e0dfe3e420b238c95682497` invoked V2 and V3 once each. Compatibility
checks passed before generation without embeddings/writes. Code, prompts and limits stayed
unchanged; earlier degraded V2 consumption remained counted.

| Observation | V2 host | V3 host |
| --- | ---: | ---: |
| Runtime through cleanup, seconds | 134.234 | 143.156 |
| Chat / embedding calls | 5 / 1 | 6 / 1 |
| Total HTTP sends | 83 | 98 |
| RAG queries / returned positions | 1 / 20 | 1 / 20 |
| Repair rounds | 0 | 1 |
| Reference cost USD | 2.37225918 | 2.415477415 |

Both RAG stages completed with partial bounded identity resolution, not SQL timeout.
V3 internally reported `ACCEPTED_COMPLETE`; no independent quality verdict followed from
that status. Actual captured normalized query vectors matched HTTP responses. All 181 HTTP
IDs had complete HTTP 200 captures; 541 prior files remained unchanged. The V1–V3 workflow,
including earlier attempts, totalled reference USD 9.175940885, not actual billing.

Selected run IDs were `sydney-v1-20261008-r1`, `sydney-v2-20261008-r2` and
`sydney-v3-20261008-r2`, alongside retained V0. Evidence:
`artifacts/sydney-four-version-live-20261008-r2` and
`artifacts/sydney-generation-evidence-handoff-20261008-r2`.
This established linked generation material, not reviewed evaluator intake or final scores.
