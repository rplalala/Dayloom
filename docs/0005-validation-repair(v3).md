# Structured validation and targeted Repair

V3 validates the shared V2 primary result, proposes bounded authorized edits and
revalidates the selected itinerary. Internal findings guide Repair; independent
quality remains the evaluator's responsibility. [Development evidence](records/v0-v3/v3-development.md)
records consequential design changes and observed limitations.

## Validation is a separate stage

The read-only validator consumes normalized evidence and source-linked requirements.
It emits PASS, CONFIRMED, NEEDS_REVIEW or UNKNOWN; only CONFIRMED is a violation.
A finding is not operation permission, and plausible model reasoning cannot promote
an unknown fact to PASS.

### Supported findings and factual limits

| Family | Supported boundary |
| --- | --- |
| Named/semantic requirements | Source-linked inclusion/count/date and supported category goals; arbitrary prose remains unassessed |
| Dated total visits | All-primary occurrence bounds; proven hard mismatch is CONFIRMED, uncertain role/date is UNKNOWN |
| Schedule/policy | Overlap, unauthorized canonical repetition and minimum coverage; optional quantity remains review |
| Opening | Complete visit containment in adopted applicable intervals, not admission/ticket certification |
| Routes | Actual directed transition and mode/departure-applicable evidence |
| Access and budget | Reservation possession, special-area access, suitability and whole-trip affordability are not verified capabilities |

Opening selection prefers applicable adopted official date/range facts, then
request-window current Places periods and eligible regular weekly periods. Missing,
invalid or conflicting material remains UNKNOWN. Explicit exterior/non-entry binding
cannot receive an entry-hours PASS; otherwise the recorded `obey_place_hours` policy
applies. Overnight intervals are supported. A missing venue zone may use one recognized
consistent planning context, independently of evaluator timezone evidence.

## Authority precedes editing

Application-owned targets and permissions protect fixed time, required/excluded
identities, count/date obligations and accepted state. Opening/route conflicts may
permit duration-preserving retiming and bounded moves. Delete/replace requires a
dispensable visit and all relevant protections; shortening a visit to fit is not an
implicit operation. Removed-obligation progress is distinct from verified resolution.

Repair receives current activities with computed `duration_seconds`, canonical
candidates, target worksheets, allowed operations, routes and bounded feedback.
The model proposes edits/dispositions, never provider facts or its own authority.
`scope.permissions` controls existing-activity edits; dated `addition_candidates`
can independently authorize additions even with no existing-edit permissions.
Malformed structured output fails before adoption without partial JSON salvage.

Required category repair shares the bounded count path and protects attained hard
count/distinct-date coverage. Unverified category coverage is UNKNOWN, not an
invented automatically repairable deficit.

### Dated-count protection

[Daily count semantics](0002-requirements-evidence.md#dated-total-primary-visit-counts)
govern findings, bounds and target dates. Proven shortage/surplus can authorize
additions/deletions within other protections. Hard counts replace default quantity
on that date; zero exempts minimum coverage without clearing full-day protection.

For a hard minimum, `hard_daily_count_feasible_pace_1` restricts soft optimization to
counts at/above the floor and subtracts the best feasible baseline. Ordinary minimum
three therefore targets three, not two; four remains legal with greater soft penalty.
This is a planner projection, not a change to independent density scoring.

Every complete patch, affected-day replan and adoption comparison protects both
source and destination dates: PASS cannot become failed/uncertain; UNKNOWN cannot
become proven failure; existing failure cannot worsen or become uncertain. Aggregate
soft gains never offset hard regression. Final selection repeats these checks.

## Components, adoption and fallback

Dependency components determine atomic acceptance. A rejected independent component
preserves earlier checked improvements; uncertain facts cannot establish successful
repair. The selected itinerary always retains matching evidence and validation.

## Transport and resource boundaries

Repair intersects scoped modes with authoritative hard allowed modes before candidate
work. Cached/unchanged disallowed transfers cannot bypass that set. Both sides of
changed adjacency need applicable checks at their actual departure. Representative
options are preparation, not insertion feasibility.

One whole-request deadline begins before lazy retrieval setup. Stage work shares
request caches, counters and failures; a later round resets none. Product uses the
[acceptance profile](../config/README.md#product-acceptance-profile), with development
defaults separately selectable. [Configuration](../config/README.md#counting-timing-and-invariants)
owns current ceilings and reserves. Cancellation, exhaustion, rejection, no authorized
target and accepted Repair remain distinct outcomes.

A factory-created runtime is released once; no runtime exists if timeout precedes
factory entry. Caller-owned runtimes remain caller-owned. Final normalization uses
original supply plus verified Repair identities, preserving provider names/addresses
on retained and retimed visits. Nearby runs once after normal final selection and
cannot continue after terminal failure, cancellation or request expiry.

## Soft pace objective

Optional `quantity_review_enabled` optimization targets zero deductions under
`rtpeval_daily_density_3`; residual deductions do not invalidate generation.
Hard Repair and minimum coverage remain active when optional quantity is disabled.
A resolved pace supersedes generic two-to-five quantity targets.

`soft_pace` findings retain source policy, count, penalty and zero-penalty counts.
Known positive deductions are review targets, not CONFIRMED violations. Unknown
roles/policy provide no guessed edit authority. Counting uses assessed main visits,
including applicable legacy generic declarations; new-wire roles retain the
[activity contract](0003-itinerary-transport.md#activity-semantics).
Numeric curves live in `backend/pace_policy.py`; evaluator inputs remain independent.

Fixed full-day protection projects feasible count to zero through
`full_day_protection_pace_1`: known zero has zero penalty, known positive has 100,
and unresolved roles remain UNKNOWN. Empty protection dates apply to every trip date.
The projection leaves original pace/count requirements unchanged. Partial or unresolved
protections receive no projection; scheduled non-visit activities remain protected too.

Bounded add/remove/move operations reuse ordinary requirement, coverage, role, route,
occupancy and cost checks. Aggregate search may explore worse soft states; relabeling
is not an operation. Outcome summaries retain before/after days and means,
`reached`/`residual`/`unavailable`, policy ID and `is_failure_constraint=false`.

### Final Rich completion

After revalidating the best retained result, inspect every date governed by default
Rich. Each needs exactly three known primary occurrences; a mean of three cannot
substitute. Missing dates and unresolved counts remain residual/unavailable, including
unresolved overrides under a Rich default. Sourced counts, hard-count projections
and full-day protection take precedence without becoming default-three satisfaction.

| Status | Meaning |
| --- | --- |
| `complete` | Retained Repair meets applicable Rich dates and supported return checks |
| `already_satisfied` | Verified initial itinerary already meets them |
| `partial` | A date remains unmet or a supported return check fails |
| `unavailable` | Required evidence is unresolved, with no known failure taking priority |
| `not_attempted` | Optional quantity review disabled |
| `source_overridden` | All Rich dates have satisfied sourced exceptions |

Each day retains count, target, override kind and state. Short windows, missing
candidates, routes or limits do not invent user exceptions. Completion requires no
confirmed conflict or unresolved executable return check. A generic missing-binding
limitation is nonblocking only when no actual adjacent route/transfer requires it.
The same-day generic quantity UNKNOWN is nonblocking only with satisfied Rich target,
minimum coverage and classified roles. Findings remain visible; neither exception
certifies remaining-hour planning, budget, access or unsupported semantics.

For Rich, stage/final `ACCEPTED_COMPLETE` requires completion `complete`; otherwise
accepted edits remain `ACCEPTED_PARTIAL`. Recompute from final validation rather than
trusting a round or generic objective. An already-satisfied plan needs no fabricated
Repair call. Product exposes a compatible [public projection](0007-application-operations.md#http-contract-map).

## Request flow and ownership

V3's post-primary hook runs after identity/date binding and before final Nearby.
The immutable draft, original report, fairly reassessed draft, proposals, exploration
and best retained result are distinct. Shared request counters and the entry deadline
survive every strategy. Final schedule, semantics, transfers and validation bind the
selected result; Nearby contributes no primary coverage.

## Per-leg mixed transport

Use allowed WALK, TRANSIT, DRIVE options in soft priority order, reusing applicable
evidence first. A failed query retains its key; a distinct allowed mode may follow.

| Mode | Configurable automatic window | Occupancy |
| --- | --- | --- |
| WALK | Provider distance ≤3 km and duration ≤45 min | Provider duration |
| TRANSIT | Applicable total duration ≤45 min | Provider total, without duplicate access walking |
| DRIVE | Provider duration ≤30 min | Provider duration + 10 min reserve |

Geographic discovery filters (2 km WALK / 5 km motor) are not permanent venue labels.
Missing-route fallback is limited to conservative WALK ≤1 km with 45-minute reservation;
coordinates create no DRIVE estimate. Each leg must fit one continuous interval and
preserve stage-original added daily traffic ≤90 minutes, including reserves. No
comparable original route means no invented baseline credit.

Prepare rotating authorized candidate/date opportunities near real anchors, not the
whole pool in three modes. Options bind directed endpoints, mode, timing basis, target,
provider duration and reserve. Conditional compensation routes follow parent dependency.
Final changed chains check both actual neighboring legs; TRANSIT remains exact-time-sensitive.

## Joint repair and component atomicity

`repair_input_2`, projection `qualified_opportunities_feedback_1`, separates catalog,
operation authority, protected/current context, targets, routes and feedback.
Disposition reasons are limited to 240 Unicode characters. If excess reason length
is the only structural error, one batch compression may replace those explanations
only, after reference/length checks. It cannot change edits, targets or shorter text.
Original/compressed material is audited; semantic equivalence is not mechanically
proved. Failure stops proposals while retaining the best result; no truncation or retry.

At most 50 parsed edits are partitioned by activity, identity obligation, affected
dates/adjacency, elastic roots, burden, cost, parent compensation and shared target.
Same-date edits are conservatively atomic; a common validator kind alone does not
link unrelated dates. New-identity competition is resolved sequentially.

Components run once in deterministic confirmed/compensation/review order with stable
edit-index ties, using the latest exploration state. Each checks permissions, schedule,
routes, occupancy, spatial policy, validation and business progress. Dependent removal
and compensation stay together except narrowly authorized excluded/unexecutable removals.
Final global checks reject illegal combinations; safe fallback is the round input.
There is no exponential subset search, and consumed calls/evidence never roll back.

## Target priority and stage accounting

Hard/confirmed goals precede activated compensation, minimum coverage and optional
review. Deferred targets cannot acquire candidates or edit. Historical unknown
multiplicity cannot authorize deletion. Model proposals, day replans, deterministic
deletions, explanation compression and semantic assessment have separate accounting
under shared deadlines and acquisition budgets. No hidden retry or new Review/Profile/
official-web acquisition is part of Repair. Expired recheck allowance blocks adoption
even after a useful provider response; preparation reserves time for finalization.
Current numeric ceilings belong to the configuration reference, not historical run plans.

## Pending compensation and publishable state

Deduplication cannot evade counts by moving or relabeling a visit. Source obligations,
windows and routes determine the retained occurrence; explicit repeated/date-bound
visits stay protected. A checked group awaiting coverage compensation may remain
unpublished with its base fingerprint and descendants. Only a matching current base
can reactivate it. Independent accepted edits remain publishable; exhaustion discards
pending dependencies without waiving coverage. Failed system alternatives do not
accumulate pending edits.

Previously assessed candidates may be reused after assessment limits. New identities
require qualification before add/replace authority. Settle bounded pending assessments
before declaring sufficient/novel opportunities; rejected or unassessed candidates
cannot consume that reference. Continue the same bounded queues when qualification
removes apparent supply. Terminal semantic contract failures remain failures.

## Bounded search

Repair separates checked exploration from final retention. See the
[glossary](../GLOSSARY.md) for these terms.

### Exploration and retained result

Compare aggregate pace over the fixed original dates with known deductions. Never
drop a comparable date or treat unavailable data as zero; newly known dates cannot
silently change the denominator. Intermediate equal/worse soft states are legal only
within hard protections and required checks. Promote a publishable priority-respecting
improvement and retain it through later rejection or exhaustion. Return it with its
matching context, or the draft if none improved. Internal gain is not independent gain.

### Proposal strategy and affected-day replanning

First enumerate bounded authorized dispensable deletions without a proposal-model
call; ordinary rechecks may still consume provider resources. Prefer viable local
edits, switching on nonprogress to a distinct affected-day arrangement while allowance
remains. Linked moves/compensation may involve several dates; unrelated dates stay
unchanged. All proposals traverse the same permission/adoption path. Original move
bounds are not rebased after moving. Reuse evidence first; replenish only for an
authorized next step within shared limits.

### Feedback, deduplication and applicability

Feedback identifies attributable rejection causes without disqualifying unrelated
candidates. Equivalent proposals are keyed by base, edits and effective permissions,
time and directed evidence, not explanations or observational metadata. Detect repeated
exploration states. Unchanged evidence alone does not exhaust different operations.

An empty local proposal permits the first transition to replanning. A second send from
the same strategy after empty output needs a real effective-material change. Try bounded
replenishment first; otherwise stop with `no_new_material_after_empty_proposal` before
sending. `empty_proposal_guard` retains fingerprint, strategy and discovery outcome.
Quantity applicability, deletion authority, minimum coverage and routes are separate:
unassessable quantity neither prohibits independently authorized deletion nor supplies
its missing checks.

### Outcomes and compatibility

Stop on completed applicable goals, exhausted limits, missing required evidence or
exhausted bounded strategies. Preserve terminal failure/cancellation and best-result
semantics. Record proposal bases, strategies, checks, exploration transitions, best
promotions, actual calls and stop reasons.

`search_version=1` distinguishes exploration records from historical adopted-state
chains. Null selected round returns the original draft; selected lineage includes
necessary ancestors and excludes later discarded states. Historical records do not
acquire invented strategy/usage observations. Missing measurements remain unavailable.

## Limits and implementation

No global route optimizer, parking/vehicle state, rideshare pricing, detailed transit
navigation or arbitrary access inference is implemented. Nearest-anchor preparation
is not exhaustive; conservative components can reject otherwise feasible edits.
Offline checks establish behavior, not universal live quality or availability.

Owners: [runner](../backend/app/versions/v3/runner.py),
[validation](../backend/app/versions/v3/validation.py),
[acceptance](../backend/app/versions/v3/repair_acceptance.py),
[components](../backend/app/versions/v3/repair_components.py),
[search](../backend/app/versions/v3/repair_search.py),
[replanning](../backend/app/versions/v3/repair_replan.py) and
[pending groups](../backend/app/versions/v3/repair_pending.py).
