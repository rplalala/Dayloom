# Quality scores and anonymous human review

Current implemented Tickets 08-10 contract, updated 2026-10-04. Automatic verified compliance,
paired diagnostics, human preference, resources and mechanism/controlled-Repair tracks have separate meanings.
[Evaluation architecture](../0006-independent-evaluation.md) owns status; formal comparative
analysis and new implementation require separately authorized work.

## Units, states and metric ownership

Each metric preserves sources, unit/scope, applicable/known/unresolved populations, raw
counts, evidence coverage, reason codes and rule hashes. PASS meets the applicable rule;
FAIL has sufficient contradiction; UNKNOWN retains applicable unresolved facts; N/A has no
applicable checks. Material failure requires correction, not a zero quality score. Empty or
unestablished denominators produce null rates rather than perfect compliance.

| Dimension/measurement | Authoritative owner and units |
| --- | --- |
| Requirement fulfillment | [Reviewed obligations](0003-requirement-schedule.md#obligations): one parent obligation, all count/date/time components retained |
| Grounding / claimed-ID consistency | [Independent identity](0002-intake-identity-usage.md#identity): primary source occurrences; wrong supplied ID remains separate from intended-place resolution |
| Non-overlap / occupied time | [Schedule](0003-requirement-schedule.md#non-overlap): logical commitments, pair/union measurements and protected boundaries |
| Opening | [Opening](0004-opening-routes.md#opening): primary visits; complete evidence versus partial decisive verdicts and outside-duration lower bounds |
| Routes / transfer burden | [Routes](0004-opening-routes.md#route-verdicts): same-day occurrence legs; one combined verdict with separate cap/time/distance evidence |
| Date coverage, density, canonical repetition | [Descriptive schedule](0003-requirement-schedule.md#descriptive): raw counts and adopted identities; [daily density](#daily-density) adds a reviewed pace deduction to the overall score |
| Latency, calls, tokens, HTTP/cache events | [Usage](0002-intake-identity-usage.md#usage): observed scope/namespace; Repair subsets are not added twice |

Conditional `P/(P+F)` is diagnostic compliance and accompanies coverage/UNKNOWN. It is not
the auxiliary score formula. Unresolved lookup is not a hallucination rate; shorter travel,
more activities and fewer repetitions are not automatic subjective improvement. Visits and
six within-group version pairs are correlated; request-level records remain the comparison
unit. Formal aggregation, inference and post-result weight tuning are not implemented here.

<a id="scores"></a>

## Exact final-report scores, common masks and availability

`quality_report.build_quality_report` reuses the three independent offline scorers and
validated primary-visit identity records. It accepts intake, identity report, snapshot
directory and optional reviewed schedule/occupancy/route/coordinate envelopes, with an
optional trusted `expected_plan` and required offset-aware `generated_at`. It returns an
immutable `QualityReportResult`; `to_dict()` exports `rtpeval_quality_report_2`.
No provider client, planner graph or extra dependency is constructed.

Optional source-bound `opening_judgment` selects `rtpeval_access_quality_4`: opening PASS
can use API schedules or the [missing-hours access assessment](0004-opening-routes.md#missing-hours-access-judgment).
Arithmetic, populations and denominators remain unchanged. Model-supported PASS is a
policy judgment, not verified hours. Ordinary viewing at public landmarks may be inferred;
restricted activities and museum admission retain separate access-evidence requirements.
Opening primary metrics retain factual coverage,
unknown durations and separate model-assessed/decidable counts. API-only reports retain
their original profile. Scoring/import never invokes a model.

Executable commands are in the [package guide](../../backend/evaluation/README.md).

All options are optional for CLI replay; missing independent evidence retains the
existing scorer policy. An absent `--generated-at` uses current UTC. Final-only
`paired=False` evidence is required; a valid paired snapshot receives the explicit
`unsupported_snapshot_scope` diagnostic. Optional V3 projection availability is exposed
without paired scores/deltas. Exit 0 means complete replay, including quality FAIL,
UNKNOWN and unavailable totals; material/replay correction emits empty groups and exit 2.

Root `components` preserves each scorer's schema, rules and source/hash metadata.
`source_hashes.artifacts` preserves intake's exact artifact hashes; independent identity/
review/audit/reference, preparation and snapshot/plan digests remain explicit. CLI exact
preparation-file SHA-256 is separate from canonical object hashing. `content_hash` covers
all output fields except `generated_at` and itself, including CLI file hashes. Explicit
time plus identical sources/rules reproduces sorted JSON. Sources are never mutated.

Each group exports the ordered common `included_dimensions`, exact rational
`dimension_weights`, included count, four keyed `versions` and `all_totals_available`.
Each version exports raw `primary_metrics`, normalized `dimensions`, `auxiliary_total`,
`daily_density`, `overall_total`,
descriptive/schedule/occupancy measurements and untouched component row hashes.

For established N=P+F+U>0, verified score is 100*P/N. Rates in 0-1 and exact count
fractions accompany coverage (P+F)/N, U/N, F/N and conditional P/(P+F). UNKNOWN remains
UNKNOWN; conditional compliance does not determine the score. Parent obligations,
logical commitments, primary visits and combined route legs retain one weight.
Grounding uses source occurrences/validated identity records rather than caller summary
counts. Under the current version-specific policy, replayed `grounding_verdict` supplies PASS,
FAIL or UNKNOWN: confirmed incorrect addresses and different venues are FAIL without canonical
adoption. A separately verified physical association can support opening/routes while
grounding FAIL remains counted. Occurrence matching follows the separate
[requirement count contract](0003-requirement-schedule.md#count-bounds-and-completeness);
physical association alone does not prove fulfillment or change the original output.
Downstream PASS never cancels a claim error. Earlier explicitly replayed legacy
reports retain their original resolved/unresolved classification. This changes claim classification, not
score arithmetic or denominators. Missing evidence remains UNKNOWN. Claimed-ID conflicts and
unknown role populations remain separate records.

All-four proven N=0 excludes a dimension jointly. Included single-version N=0 keeps
raw N/A/null rates and contributes zero. Unresolved applicability preserves partial
checks but makes its dimension/contribution and affected version total null, retaining
the mask and weights. Empty masks return null totals and an upstream reconciliation
diagnostic. Means use unrounded rational contributions, not rounded percentages.
Different requests retain their own masks; no pooled comparison or ranking is computed.

`stage_availability` distinguishes resource/human/mechanism reports (`not_integrated`)
from linked usage envelopes and optional projection availability. Raw density measurements
feed the reviewed daily deduction below. Repetition, raw transfer burden, resources and
V3 internal findings add no additional penalties.
Findings-only source changes preserve numeric scores after correct relinking/replay;
source/report hashes may change, and stale evidence remains invalid.

[Acceptance](../records/evaluation/quality-report.md#rtpeval-ticket-08-acceptance) records consequential
defects, bounded regressions and limitations. The [preflight](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/20#issuecomment-5955702362)
preserves the original no-implementation checkpoint and subsequent scope approval.

For a fixed established population, replacing PASS with UNKNOWN reduces verified credit;
replacing FAIL with UNKNOWN leaves it unchanged. UNKNOWN is not relabelled FAIL. This
lower-bound verified-compliance accounting does not prove immunity to activity deletion or
changed applicability; retain counts, coverage and unresolved populations. Totals with
different common masks do not measure identical content. Equal weights are a transparent
choice, not proof of statistical independence or overall travel usefulness.

<a id="daily-density"></a>

### Daily density policy and overall score (2026-10-04)

The current numeric authority is the final approved table in
[Issue #52](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/52), implemented
as `rtpeval_daily_density_2`. Earlier density curves are historical only. Final and
paired report wire shapes stay at version 2; their embedded density profile and rule
hash identify the current deductions.

The user's approved development-time scoring change preserves the five-dimensional
`auxiliary_total` and adds `overall_total = max(0, auxiliary_total - mean_daily_penalty)`.
The mean gives every inclusive requested date equal weight, including missing/empty
days. Calculate with exact rational values before emitting numeric percentages.
The rule/profile versions distinguish this report from historical five-dimensional-only
reports; old artifacts are not rewritten. `all_totals_available` now describes overall
totals. An unavailable auxiliary score or unresolved daily deduction keeps the overall
score null; even a 100-point deduction cannot make missing feasibility evidence available.

| Primary visit count | Ordinary | Relaxed | Rich |
| --- | ---: | ---: | ---: |
| 0 | 100 | 100 | 100 |
| 1 | 40 | 20 | 60 |
| 2 | 0 | 0 | 0 |
| 3 | 10 | 40 | 0 |
| 4 | 50 | 70 | 30 |
| 5 | 80 | 90 | 70 |
| 6 or more | 100 | 100 | 100 |

For four and five visits, deductions strictly increase from rich to ordinary to
relaxed. Ordinary pace now deducts 10 for three visits; relaxed pace deducts 40.
Uncertain ordinary counts spanning two and three visits therefore have deduction
bounds 0..10 and an unavailable exact deduction; they are not a zero-cost interval.

Counts reuse the requirement/schedule scorer's source-distinct primary occurrences;
transport, breaks and Nearby suggestions are excluded. Same-venue repeat occurrences
remain occurrences; canonical repetition is separately reported. This change does not
replace the legacy `<2`, `2..5`, `>5` descriptive categories or planner V3 quantity rules.
The 2..5 window is not a blanket exemption from busyness deductions.

`--density-reviews` supplies `rtpeval_density_reviews_1` with `batch_id`,
`batch_revision` and a `groups` array. Each reviewed group has `group_id`,
`input_sha256`, `reviewer_ref`, offset-aware `reviewed_at`, `review_origin` (`human`
or `agent`), `rationale`, a `default` policy and `days` overrides. A policy has exactly
`profile` (`ordinary`, `relaxed`, `rich`, `unresolved`), `exact_count` (null or a
nonnegative integer) and nonempty `source_refs` quoting original Input through
`field_path`, `quote` and optional existing quote occurrence/offset fields. A dated
override adds `date`; dates must be requested and unique. The reviewer must examine
the full original request for pace and count exceptions; mechanical quote validation
does not independently prove that its semantic interpretation is correct. Planner
requirements, internal findings and planner density summaries are never policy evidence.
Canonical review hashes and exact CLI file hashes bind this additional preparation.
Foreign, stale, duplicate or malformed material fails the whole batch.

Dated policies override the trip default. To retain the default profile while changing
only the count, repeat that profile explicitly in the dated policy. An explicit count
matching the actual count deducts zero, including requested rest days or 1/4/5/6+ visits.
A confirmed mismatch deducts 100 in this daily policy and is labelled
`explicit_count_mismatch`; it does not fabricate another named-place obligation in the
five-dimensional requirements metric. This requires an actual reviewed exact number:
relaxed/rich descriptions alone cannot supply one. A trip-wide explicit daily number
belongs in `default.exact_count`; a date-specific number belongs only in its override.

Without a review, a request with no `additional_preferences` defaults to ordinary.
Nonempty free text may contain pace/count exceptions, so missing review retains an
unresolved policy and unavailable deduction rather than silently choosing ordinary.
An explicitly reviewed unresolved profile also stays unavailable unless an exact count
determines the deduction. For uncertain visit populations, evaluate every reachable
penalty, retaining minimum/maximum bounds: penalty curves are nonmonotonic. Emit an
exact deduction only when all possible counts produce the same value. UNKNOWN is never
automatically zero, FAIL, or an assumed midpoint.

<a id="human"></a>

## Anonymous packages, answers and descriptive human reports

The human track is independent of automatic reports. It reads accepted, exact-byte-linked
final v0-v3 material and needs neither route/opening snapshots nor complete resource
observations. Real assessment requires separate approval.

The three dimensions are `preference`, `pace` and `usefulness`. Public A/B/C/D labels
stay fixed across dimensions within a task. Render the original request and the same
activity/place/time/notes/amount fields through one template for all versions. Nearby is
hidden; authoritative transport claims are displayed without duplicate journeys. Do not
invent ambiguous correspondence or use an LLM to rewrite travel meaning. Public material
and answers expose neither private version assignments, canonical IDs, raw source filenames,
internal validation/provider badges nor automatic scores. Content itself can still suggest
a version, so blinding is not an absolute guarantee.

Wire owners are `rtpeval_human_preparation_1`, `rtpeval_human_config_1`,
`rtpeval_human_display_reviews_1`, `rtpeval_human_package_1`, `rtpeval_human_mapping_1`,
`rtpeval_human_answer_1`, `rtpeval_human_answers_1`, `rtpeval_human_import_1` and
`rtpeval_human_report_1`. Root envelopes use `schema_version`; each answer uses
`answer_schema_version`. An answer contains public `batch_id`, `batch_revision`,
`presentation_id`, `presentation_hash`, `rater_ref`, `task_id`, positive `answer_revision`,
aware `updated_at`, `state=draft|submitted` and keyed `responses`. A response uses
`status=ranked|unable_to_judge|not_applicable|pending` with optional reason; pending is
draft-only. Ranked `tie_groups`, such as `[["A","C"],["B"],["D"]]`, partition all four
labels in a submitted response; unassessable responses contain no ordering. Bundles have
exactly `schema_version=rtpeval_human_answers_1` and an `answers` array. Submitted answers
require all three dimensions; drafts may be incomplete. The exact frozen presentation hash
links the public material, while the private mapping retains source/review hashes and actual
assignments. Report generation time must be offset-aware; pin it for reproducible replay.

Configuration uses `schema_version=rtpeval_human_config_1`, three opaque 32-character
lowercase hexadecimal identifiers (`public_batch_id`, `presentation_id`, `rater_ref`),
positive integer `revision`, explicit integer `seed`, positive `duplicate_min_gap` and
an ordered `tasks` array. A main entry is `{"group_id":"g"}`; a duplicate entry adds
`"duplicate_of":0`, the zero-based original main-task index. Repeated main groups,
references to duplicates, unknown groups and insufficient spacing are errors. There
are no fixed task/sample quotas. Seeded shuffled Latin blocks balance version/label
positions across all shown tasks; main/duplicate/combined counts are private diagnostics.
Use a fresh presentation identifier/revision when preparing a new assessment.

Executable commands are in the [package guide](../../backend/evaluation/README.md).

All output paths must be new. The public directory contains only `review.html` and
`presentation.json`; keep mapping/preparation/review files outside it and give only the
public files to the rater. Open `review.html` directly in a local browser; no server,
account, CDN, hosted submission or database is needed. Runtime CSP blocks network access.
Source text renders as inert text and dates/offsets are preserved. Missing arrivals may
add an explicitly labelled inferred arrival from supplied valid departure/duration;
the original arrival remains absent and inference never feeds automatic scoring.

The Time zone dropdown defaults to UTC and uses browser IANA zones, with a small
common-zone fallback on older runtimes. Explicit-offset start/end/departure and supplied/
inferred arrivals display converted dates and HH:mm clocks, including midnight/DST.
Original day headings retain source grouping. Local clocks without an offset remain
unconverted; invalid values retain their original text and missing values show Not supplied.
Date-only request fields and free text are unchanged. Zone selection affects only the
current view, not frozen artifacts, answers or scoring; local Intl supplies the rules.

The renderer hides dedicated uncertainty fields, item notices, conversion warnings and
original-timestamp controls. It retains the Inferred arrival label, ordinary notes/
preferences and duration basis. Frozen material still retains exact strings, unknowns,
notices and hashes; suppression does not verify a claim. The
[display history](../records/evaluation/blinded-ranking-record.md#integrated-display-revisions)
records the separately approved changes.

Preparation is researcher-only. Its `fields` list records `field_ref`, exact source-file
`source_sha256`, source pointer, `original`, canonical `original_sha256` and likely leakage
flags. A review has `schema_version=rtpeval_human_display_reviews_1`, the exact
`preparation_hash`, `reviewer_ref`, aware `reviewed_at`,
`preserves_facts_and_uncertainty=true`, `redactions` and `allowed_flags` arrays.
Each redaction names the field and both hashes, with `display_text` and `reason`.
Only remove explicit version/provider/internal-review identifiers; keep travel facts
and uncertainty. An allowed flag uses the same field/hash linkage and reason for a
legitimate name or meaning resembling an identifier; it is not permission to expose
version metadata. Review the entire prospective material, including unflagged prose;
lexical checks cannot guarantee semantic blinding. Unresolved flagged text blocks delivery.
Changing original bytes requires relinking the delivered batch and repeating review.

Rank each dimension with positions 1-4, equal positions for ties, or an explicit
unable-to-judge/N/A response. Save drafts before navigating and download JSON before
closing. Local storage is best-effort; a failure is visible and portable JSON remains
available. Import is atomic and validates the exact presentation/rater, states and
rank partition. Corrections create a higher complete submitted revision; it supersedes
old effective answers while old revisions stay audit-only. Drafts do not supersede
submissions; importing identical revisions is idempotent and contradictory same-revision
content blocks processing. Multiple answer files can be supplied to import/report.

The researcher report preserves effective revisions/hashes, all retained revisions,
six mapped pair outcomes per assessable dimension, available denominators and distinct
missing/unjudgeable/N/A/draft-only counts. Hidden duplicates contribute version-based
consistency only; no comparable pairs yields null agreement. Pairs from one request
are correlated. No overall human score, inferential analysis or automatic-quality
integration is supplied. Frozen mapping hashes verify integrity, not cryptographic
authorship. [Acceptance](../records/evaluation/blinded-ranking-record.md#rtpeval-ticket-09-acceptance) records actual
test/review/browser evidence and remaining limitations.

Suite attachment retains each native human package/rater as a separate report.
Verification binds presentation, private source mapping and retained answer revisions
to one selected accepted case, then reproduces the original native report at its saved
generation time. Public blinded identifiers need not equal suite case aliases; private
preparation source hashes establish linkage. Effective answer revisions remain native.
Later answer imports produce another native report before an explicit suite refresh;
there is no cross-rater aggregation or overall human quality score. The
[attachment contract](0001-evaluation-artifacts.md#existing-study-attachments-and-refresh)
owns exact references, separate controlled populations and closed refresh lineage.

### Staged automatic acceptance and deferred blinded review

Benchmark cases undergo automatic acceptance first, followed by a separately
authorized consolidated blinded-review stage. These are workflow milestones, not
new artifact statuses or a combined score.

The [benchmark workflow](../../benchmark/README.md#workflow-and-responsibilities)
defines the automatic steps and their required material: independent primary
evaluation, V1/V2 candidate POI process analysis, V2/V3 Repair process analysis
with the same-run V3 pair, and actual all-attempt resources/completion. Mechanism
reports remain descriptive and do not change primary scores. A compact RAG
return/adoption table can summarize candidate evidence but cannot replace captured
stage history or applicable independent relevance judgments.

Corpus measurement, corpus coverage sidecars and corpus coverage reporting are
[optional studies](../../benchmark/README.md#optional-work-compared-with-the-initial-plan).
Their native contracts remain available when explicitly selected. Retain runtime
RAG source identity without requiring a database-wide scan. The
[final-case layout](../../benchmark/README.md#layout) preserves native dependencies
and later human material in ignored private scratch storage, with a public case
report and deduplicated selected materials. The
[private archive retention rules](../../benchmark/README.md#private-archive-retention)
require compact long-term evidence, deletion of unnecessary working copies and
restored offline validation before removal. Each case Issue owns readiness and decisions;
the primary-score handoff pauses for the user's next instruction.

1. **Automatic acceptance:** the user jointly accepts the exact input revision,
   independently reviewed requirements, selected V0-V3 outputs, admitted manifest,
   actual primary evaluation and the case's declared applicable research/resource
   reports. Check source integrity, judgments, arithmetic, processing completion and
   limitations. Genuine FAIL, UNKNOWN and justified non-applicability remain valid
   observations; interpretation-invalidating defects must be resolved. Record
   automatic acceptance and human review deferred/not conducted separately.
2. **Handoff preservation:** retain original input/result/requirements bytes,
   selection and attempt identities, completion/usage/provenance, configurations,
   independent snapshots, rules, reports, receipts and the explicit acceptance
   decision. Later human packages must bind these same accepted outputs. Do not
   regenerate itineraries, shift their dates or replace runs merely because review
   happens later. Changed sources form a new revision and require affected review.
3. **Consolidated blinded review:** separately approve the selected accepted cases,
   raters and presentation/review plan. Prepare and review anonymous material under
   the human contract above. Keep version mappings and automatic scores private;
   record known prior exposure rather than claiming complete blinding. Real raters
   supply preference, pace and usefulness answers, including ties or inability to
   judge. Execution approval alone is not an answer, and agent judgments cannot be
   recorded as human responses.
4. **Offline report attachment:** import source-bound answer revisions and build
   native human reports. Retain standalone reports beside the accepted case evidence;
   when a suite is explicitly selected, attach each compatible case/package/rater
   through `tracks.human` and offline `report --attachments`, then replay the new
   closed revision. Preserve earlier reports/receipts and primary scores. This step
   acquires no provider evidence and does not rerun planning or primary evaluation.

Deferred human review does not block sequential automatic case acceptance or reopen
an accepted case solely to add answers. Complete the human stage only when its
separately approved inventory has actual reports and explicit missing/unjudgeable
coverage; automatic acceptance alone cannot establish completed human assessment
or final research conclusions. Human results add descriptive pair outcomes and,
where configured, duplicate consistency. They do not alter automatic density
deductions, factual verdicts or totals, merge raters, or establish an overall human
score or statistical conclusion. Research design/analysis and version freezes retain
their separate authorization boundaries.

## Follow-up reporting boundary

Ticket 10 supplies a separate [V3 paired diagnostic](#v3-pairs), with source-driven
correspondence and independent checks. It does not alter the four-final report above.
Controlled Repair and mechanism/official-evidence reporting remain Tickets 11-12; their
accepted independent outcome/eligibility boundaries are in
[follow-up scope](0001-evaluation-artifacts.md#planned). No optional-track metric becomes
part of this final four-version total by implication. Human results remain separate from
automatic scores; no overall human total or inferential analysis is supplied.

<a id="v3-pairs"></a>

## V3 draft/final-primary diagnostic

The [accepted Ticket 10 specification](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/22#issuecomment-5955706453)
owns the source-first decision. `build_v3_pair_report` and `v3_pair_cli` compare only
the selected same-run `/v3/draft` and `/v3/final_primary`. Every selected group remains
inventoried. Missing/invalid optional stages yield `pair_unavailable`, original intake
diagnostics and null paired deltas. `/itinerary` is never a substitute. Available
stages can retain standalone observations. If all pairs are unavailable, no fictional
snapshot is required. Otherwise require a verified `paired=True` evidence snapshot
and current identity replay, with the same original input and RequirementSpec.
The explicit [paired acquisition workflow](0001-evaluation-artifacts.md#paired-evidence-acquisition)
prepares, acquires, replays and exports this material independently of primary scoring.

Suite pairing is explicit per case through `tracks.pair`. An omitted pair is
`not_requested`; an explicit empty or incomplete optional declaration retains
unavailable reasons. Nonempty supplied pair material requires `identity` to validate native lineage.
Supplied `identity`, `snapshot`, `context` and reviewed material
are declaration-relative paths, byte-bound and validated before primary sends.
Final-only evidence never supplies draft coverage. Complete material produces the
unchanged native `tracks/NNNN/pair.json`, with its own comparison mask, signed deltas,
correspondence uncertainty and null unavailable values. A genuine complete unchanged
no-Repair pair may have zero deltas. No paired acquisition, opening supplement or
Repair is launched, and primary four-final arithmetic remains independent.

The report calls the public requirement/schedule, opening and route scorers, verifies
all expected final/optional rows and source hashes, then selects the two V3 stages.
The reviewed-coordinate and saved identity-snapshot paths retain Ticket 07 semantics.
Foreign/stale supplied sources, preparation/reviews or corrupt snapshots fail atomically;
they do not silently shrink the cohort or become itinerary FAIL.

Controlled opening facts and exact venue selectors use the check's verified
`associated_place_id` under the current identity policy, falling back to canonical ID
only for historical checks without that field. A reviewed timetable can resolve missing
hours while the original grounding FAIL and execution hash remain intact. This physical
venue selection applies only to opening; grounding, requirements and repetition selectors
retain canonical-claim semantics. Human facts still cannot override independently
confirmed hours or bypass unavailable identity.

The five dimensions retain exact P/(P+F+U) arithmetic and equal weights. The **pair's**
common mask excludes a dimension only when both stages establish zero denominators.
An included true no-check stage has null raw rates and zero accounting contribution.
An unresolved denominator retains the dimension but makes its contribution and affected
total unavailable. An empty mask has null totals. Signed changes are final minus draft,
including exact rational score differences and percentage points. Defined identical
metrics give zero; unavailable values never acquire zero through imputation. This mask
and its auxiliary totals are distinct from Ticket 08's four-final comparison.

`rtpeval_v3_pair_report_2` applies the same reviewed density policy to both stages.
Each stage exports daily deductions and `overall_total`; `deltas.overall_total` is
the exact final-minus-draft overall change, while `deltas.auxiliary_total` preserves
the original five-dimensional delta. Mean deduction changes are also exported.
Independent mechanism preparation accepts historical pair report 1 and current report 2
with the same exact source/hash checks. Density improvement is not proof of repairing a
different feasibility conflict or of general travel usefulness.

Each stage preserves original checks, P/F/U/N/A counts, denominators, schedule commitments,
conflicts, evidence/basis coverage, duration subtotals, lower bounds and observed traffic
burden. The report exports population, date coverage, density/repetition and measurement
differences. A subtotal difference describes its observed populations; it is not an exact
full-trip difference when coverage changes or evidence is partial. Visit losses/additions,
venue replacements, role losses and unresolved correspondence remain separate.

### Source correspondence and review

`read_v3_result_sources` rereads selected manifest artifacts through the safe relative-path
and byte-hash rules. `prepare_v3_correspondence` emits immutable
`rtpeval_v3_edit_provenance_1`; its optional source envelope is
`rtpeval_v3_result_sources_1` with batch/revision and records containing group/run,
input/result SHA256 and original UTF-8 result bytes. Verify exact associations and stage
observations before using embedded material. A supplied preparation is recomputed against
original sources; an arbitrary caller-written edit summary is not accepted.

Within a checked chain, unique producer IDs identify edited slots. Validate Repair original,
ordered round inputs/adopted states, result original/final and cumulative final. Only
actually adopted changes, effective edits and accepted component membership establish
relations. Rejected/pending/rolled-back components do not enter adopted lineage. Compose
retime/move/replace/delete/add and free-time fragments across rounds; validate parent/root/
child membership, fragment complements, dates and collision-free IDs. Record edit pointers.
Sorting, source-ledger place-name normalization and transfer refresh are reconciled
separately. Identical validated source snapshots also support unchanged IDs without Repair.

Source lineage, canonical venue identity and quality are three separate facts. Replacement
can preserve a slot while changing the independently confirmed venue, or retaining the same
venue. Identity UNKNOWN does not invalidate known source lineage. Internal accepted/resolved/
PASS judgments never establish independent identity or compliance. Complex recorded edits
are automatically traceable; they do not require review solely because they are complex.

Missing/inconsistent embedded lineage gives explicit local diagnostics, then uniquely
unchanged content or globally unique independent canonical matching supplies weaker
fallback. Do not use title semantics, nearest time, array position, favorable outcomes or
greedy leftover venue matching. Residual occurrences produce review requests and coverage
counts; unresolved local correspondence does not erase valid aggregate deltas.

Optional `rtpeval_v3_correspondence_1` reviews carry batch/revision and records with
group/run/result SHA256, full `before`/`after` stage source refs, `relation`, `reviewer_ref`,
offset-aware `reviewed_at`, `rationale`, and optional string `supporting_refs`. Relations
are unchanged/modified/moved/replaced/split/merged/complex/added/removed. Check exact
membership, disjoint participation, cardinality and observable unchanged/moved claims.
A review cannot override contradictory established correspondence. Many-to-many groups
retain constituent checks without invented one-to-one edges or new success denominators.

### Independent continuity

Match requirements by original obligation ID; retain count/date/time components and
regressions. Compare opening/grounding only for independently compatible continued visits.
Deletion records removal; venue replacement retains old/new checks without repairing the
old venue's fact. Directed route endpoints retain connection lineage separately from venue
compatibility; inserted visits yield removed direct legs and added legs. Query/date/mode/
departure context changes remain explicit and each stage uses its own applicable evidence.

Overlap continuity uses independently continued participants, rather than generated check
IDs or equal clock spans. Protection continuity retains the original obligation/scope.
Removal is not resolution. Introduced conflicts require confirmed before non-conflict or
established new participants; uncertainty retains unresolved attribution. Compatible
FAIL-to-PASS can be resolved, FAIL-to-UNKNOWN is unverified change, and PASS-to-UNKNOWN is
lost verification. Partial improvement requires comparable exact FAIL magnitudes under the
same rule; missing or lower-bound magnitudes do not qualify. The native pair report supplies no overall Repair-success classification, causal conclusion,
live acquisition or planner instrumentation.

The current wire is `rtpeval_v3_pair_report_2`; `_1` remains a historical format
accepted by independent mechanism preparation. Reports preserve rule/component/source
hashes, per-group stage
availability, mask, exact deltas, correspondence and continuity. Content hashing excludes
creation time. CLI file-byte hashes remain distinct from canonical preparation digests.
Exit 0 means complete processing, including unavailable pairs and quality FAIL/UNKNOWN;
material/replay correction exits 2. Commands are in the [package guide](../../backend/evaluation/README.md).

## Declared research Repair view

The [#116 specification](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/116)
adds `rtpeval research report --track repair` over the
[declared research population](../0006-independent-evaluation.md#planned-batch-and-research-extensions). Its
`rtpeval_research_repair_1` material binds the population/profile identifiers and
revisions, with optional `quality_reports`, `pair_reports`, `mechanism_reports`
arrays and a separately declared `controlled` study.

Quality and pair descriptors require `manifest_ref`, `identity_ref` and
`report_ref`; `snapshot_ref` names the native snapshot's `manifest.json`.
Final quality requires a snapshot; an unavailable native pair can omit it.
Optional native inputs use the builder argument name followed by `_ref`, including
`schedule_context_ref`, `coordinate_evidence_ref`, `density_reviews_ref` and
pair correspondence/edit provenance. `identity_snapshot_ref` supplies saved
identity evidence where the native reader requires it. Mechanism descriptors use
`manifest_ref` and `report_ref`. References follow the common research source
contract.

The adapter invokes the existing intake, snapshot and report builders, reproduces
the saved report under its native rules and source bindings, and checks the selected
first attempts. A matching self-declared content hash alone is insufficient.
Supplied census usage/provenance references must match the native selected sources
byte for byte; absent optional census observations retain their availability state.
Native CLI preparation file hashes remain distinct from canonical content hashes.

Every declared V3 generation slot remains in the same-run and V3-minus-V2 final
inventories, including missing, no-repair, unchanged, skipped and rejected runs.
Comparability follows native score availability. Descriptive improved/unchanged/worse
counts use the sign of the exact native overall delta; missing scores remain
unavailable. Final-quality and same-run masks, auxiliary totals, density deductions
and evidence coverage remain separate. The conditional attempted-Repair view uses
only source-replayed native mechanism observations and retains unknown attempt coverage.

Native continuity preserves resolution, residual failures, regressions, lost
verification, conflict changes, removal, replacement and unresolved correspondence.
Deleting or replacing an occurrence does not establish resolution of its original
condition. Controlled target resolution, guard preservation and case-level joint
success use their separate [declared study rules](0001-evaluation-artifacts.md#research-controlled),
without changing these native pair metrics.


## Implementation and historical decisions

Code: [quality report](../../backend/evaluation/quality_report.py),
[human packages](../../backend/evaluation/human_tasks.py),
[answer validation](../../backend/evaluation/human_answers.py),
[human report](../../backend/evaluation/human_report.py) and
[renderer](../../frontend/src/features/blind-review/BlindReview.tsx).
Commands are in the [package guide](../../backend/evaluation/README.md).
The [score preflight](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/20#issuecomment-5955702362),
[score acceptance](../records/evaluation/quality-report.md#rtpeval-ticket-08-acceptance),
[human preflight](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/21#issuecomment-5955704071)
and [human acceptance](../records/evaluation/blinded-ranking-record.md#rtpeval-ticket-09-acceptance)
preserve approval/validation and the superseded UI controls. Current rendering uses IANA
zones and HH:mm, keeps Inferred arrival, and hides dedicated uncertainty/item-warning hints;
source artifacts retain their original uncertainty. This view choice is not factual verification.
