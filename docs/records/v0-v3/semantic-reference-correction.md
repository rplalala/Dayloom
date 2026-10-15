# Semantic Reference Correction

This history follows reference failures, bounded correction, short-reference adoption
and adapter validation. Current rules are in [model identity references](../../0001-system-architecture.md#model-identity-references)
and [shared requirements provenance](../../0002-requirements-evidence.md#input-gate-and-provenance-contract).
Historical replay assertions describe their recorded revision and grant no execution permission.

## September 27: failure classes and correction scope

At `339e7e4a4a9eac133f2bdff69217b8b35c6990b4`, the service admitted only complete
validated batches and allowed one citation-only correction. Saved responses under
`logs/semantic_reference_network_revalidation_20260927/<case>/attempt_1/semantics/`
were joined by call_id and replayed at the external-model boundary through the actual
`POISemanticsService.assess`. Repeated replay asserted each historical error, one
call and zero cached rows; single-candidate counterfactuals isolated each defect.
Source input/output remained unchanged. Replay/probe modules live under that evidence
root's `diagnosis/`; their old terminal/count assertions are not current acceptance.

Sydney V1 returned all 32 identities correctly, but ten food-service rows promoted
`semantic_3` to an exception. That continuing favor preference had
`explicit_primary_exception=false`, with no named requirements/application bindings.
The rejection respected the then-approved role contract; it did not prohibit ordinary
food activities. Prompt 3 omitted explicit flag/polarity and REQUIRED-binding conditions.
This supports a prompt-alignment explanation, not proof of internal model reasoning.
Serializer roundtrip equality ruled out loss of the supplied permission flag.
Removing claims or changing those rows to non_main passed counterfactual validation;
neither justified silent production stripping or endorsed all semantic judgments.

Sydney V3 and Melbourne V1 each returned 32 unique rows but corrupted one canonical ID:

- El Camino Cantina: `ChIJk8CcRwivEmsROPWHqq2Qlv0` became
  `ChIJk8CcRwivEmsROPWHqq2Qlv2`.
- Chinatown: `ChIJczgQh8lC1moR9r9gP44FRvY` became
  `ChIJczgQh8lC1moR9r9gP44FRvN`.

Both row IDs and match citations changed. Fixing only place_id exposed citation failure;
fixing that ID and its citations passed the original batch. Schema-valid arbitrary strings
are not batch membership checks. Input roundtrips matched; no service remapping defect was
found. Identity-set/unauthorized-exception errors were then terminal, so these runs did
not exercise or demonstrate regression of the citation correction. All used only 1/6
calls, roughly 20–26/120 seconds and under 8192 output tokens without timeout/truncation.
Raising budgets alone could not enter a branch excluded by error type.

The approved minimum extension kept strict validation and one shared correction per
batch across identity, citation and exception-authorization/ownership failures.
Bounded feedback supplied missing/unexpected/duplicate identities and affected requirement
conditions; whole-batch validation preceded atomic admission. Prompt 4 made favor plus
explicit permission or exact REQUIRED named binding explicit. Fuzzy matching, row-order
identity inference, partial admission and a separate retry per error class were rejected.
V0, acquisition capacities and quantity Repair remained outside the extension.

Revalidation used Sydney V1/V3 and Melbourne V1 once each, with original two-traveler
AUD 3000 inputs from `logs/live_smoke_20260926/`. Sydney ran September 28–October 2;
Melbourne ended October 5. The frozen prompt-4 change passed 1712 backend tests with
9 skips, then 72 focused tests and both reviews. These are offline checks, not proof
of live efficacy. Historical limits were 600 seconds/application, 660 outer; semantic
6 calls, 120 seconds total, 45/call, 32000 input/8192 output, at most two calls per batch.
Capture ceilings were 1 MiB/stage and 4 MiB/case with raw envelopes disabled.
First-call success did not exercise correction; downstream failure did not complete
itinerary acceptance. Original dates expired September 29 and must not be backdated.

## September 27: short references chosen over a second correction

In `logs/semantic_contract_revalidation_20260927`, Sydney V1 first corrupted an ID's
last character (4→5). Its second output repaired identity coverage but introduced
`7f` into a supported-match citation whose first version had been correct. The two
calls consumed 49.918/120 seconds, neither reaching 45 seconds. The batch attempt
ceiling, rather than the request-wide budget, prevented a third call.

Option A proposed a second correction (three total batch attempts), retaining global
6-call/time/token limits. A third whole-batch regeneration might correct or introduce
errors; no success probability was measured. Observed 32-row calls took 20–26 seconds,
about 4.1–4.7k input and 4.4–6.4k output tokens. A similar third call might bring the
phase to roughly 70–76 seconds, reducing later capacity; billed cost was unavailable.

Option B used predeclared bijective batch-local `pNN`/`eNN` mappings, stable across
corrections. Exact complete candidate coverage and same-candidate source ownership
preceded canonical restoration and existing semantic checks. The user later chose B,
retaining the existing one-correction and global budgets. Wire/domain DTO separation,
projection version in cache fingerprints, input accounting and bounded mapping/wire/
resolved capture were necessary; dynamic enums, extra retries and partial-row repair
were not part of this minimum implementation.

The offline o200k measurement below changed only exact known ID/source strings in
compact sorted JSON. Malformed strings stayed unchanged; schema/prompt/framing and
mapping-capture overhead were excluded. This was a serialization counterfactual,
not a model invocation, billed usage, latency or accuracy measurement.

| Captured output | Rows | Exact ID/source occurrences | Original input/output JSON tokens | Short input/output JSON tokens |
|---|---:|---:|---:|---:|
| Sydney V1 initial, failed | 32 | 89 | 2995 / 4169 | 1885 / 2594 |
| Sydney V1 correction, failed | 32 | 89 | 3140 / 4330 | 2011 / 2751 |
| Sydney V3 first batch, accepted | 32 | 81 | 2931 / 3994 | 1819 / 2560 |
| Sydney V3 second batch, accepted | 11 | 28 | 1283 / 1275 | 910 / 788 |
| Melbourne V1, accepted | 32 | 78 | 2942 / 3660 | 1828 / 2282 |

Accepted 32-row outputs shrank 35.9%/37.7% in content tokens, with input about 38%.
This identifies repeated opaque text, not improved model reliability: valid short
references can still be confused. B reduced copying burden without new calls;
A remained a possible lower-effort fallback rather than being proven ineffective.
They were not combined, which preserved interpretability of subsequent smoke evidence.

## September 27: recorded V3 budget reconstruction

Run `1eba61e8-ad9b-48cc-9998-6e5d8392b0af` was audited offline by
`tools/validation/packets/semantic-reference-correction/audit_v3_budget.py`, using
saved result/runtime/execution/events only. Output is
`logs/semantic_short_reference_revalidation_20260927/v3-budget-audit.json`.
Forty-five range checks passed; event sequences 1–212 were continuous with no malformed
JSON lines. Four source fingerprints and per-row locations preserve replay provenance.
Continuity does not prove uninstrumented network behavior. Cumulative/nested snapshots
were not added together; primary, RAG and Repair provider pools remained separate.

| Pool / metric | Recorded use / limit |
|---|---:|
| Primary destination / candidate searches | 1/1; 3/12 |
| Primary Details / weather | 32/60; 1/2 |
| Primary admitted candidates / final POIs at selection | 64/64; 16/20 |
| Primary review Details / experience model calls at selection | 0/8; 0/8 |
| Primary baseline routes / elements | 4/7; 256/400 |
| Primary alternative route calls / unique pairs / elements | 16/32; 11/32; 16/64 |
| Official web tasks / page fetches | 0/8; 0/8 |
| RAG retrieval queries / returned positions | 2/4; 40/80 |
| RAG Details / fallback | 26/30; 4/4 |
| RAG elapsed | 15.400/360 seconds |
| Semantic calls / elapsed | 2/6; 27.412/120 seconds |
| Semantic per-call elapsed | 15.533 and 11.879, each below 45 seconds |
| Semantic engineering input | 5210 and 4493, each below 32000 |
| Semantic reported output | 3270 and 2229, each below 8192 |
| Primary generation engineering input | 65807/252000 |
| Repair rounds / model calls | 1/5; 1/5 |
| Repair routes / elements | 12/24; 12/32 |
| Repair preparation routes | 12/16 (8 of 24 reserved for post-proposal) |
| Repair new Google / fallback / embedding / retrieval / canonical / Details | all 0, within their separate limits |
| Repair engineering input / reported output | 31970/252000; 1166/16384 |
| Nearby requests / elapsed | 3/3; 1.563/10 seconds |
| Application elapsed | 114.860/600 seconds |

One embedding send covered two retrieval queries and reported 7 tokens, not two model
calls. Semantic reported inputs 3023/2306 differ from conservative engineering counts.
RAG fallback reached 4/4 with two `fallback_budget` omissions; Nearby reached 3/3.
Primary pre-generation used 16 route calls, with 16 reserved post-generation. The 96
`alternative_route_matrix_calls` stop reasons are denied work, not 96 sends. Repair's
12 route calls are separate; these are coverage limits, not recorded overruns.

`run.json` had `original_bytes=4908309` against a 1,000,000-byte cap; its 1,090,256-byte
file was a preview wrapper. The event stream remained usable, while `v3_finalized`
was summarized/truncated and final result/individual Repair artifacts survived.
Requirement captures lacked usage and surviving main-generation usage was missing:
complete billed tokens, individual provider latency and monetary total could not be
reconstructed. The 38 null activity costs concern travel budget, not API resources.

The audit proposed a compact independent final budget/usage summary, written before
payload truncation, preserving counters/call IDs and explicit missing status. It was
not implemented by this audit. Raising the cap above 4,908,309 could preserve this run
but move the future cutoff; API/Repair budget changes were not justified by storage loss.

<a id="model-reference-audit-2026-10-05"></a>

## October 5: cross-chain mapping implementation

The approved audit began at `08b2cc477b779d3b168aa593a64ba4e07a166676`; it extended
reversible references across supplied-ID model boundaries. The earlier V0 pilot
[#63](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/63) remained separate;
[#64](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/64) records this work.

| Current model boundary | Observation and resulting change |
| --- | --- |
| V0 primary | No supplied external place ID to reproduce. Model-created activity/transport identities retain their existing contract. No external tools added. |
| Shared requirement interpretation | Source quotations and existing short local requirement references; no long-ID round trip found. Unchanged. |
| V1-V3 primary | Full canonical place IDs previously appeared in evidence and returned `source_place_id`. Shared aliases now cover evidence, compact directed routes, identity-based conflicts, official projections and candidate supply. |
| Review profiling | Canonical place ID previously returned alongside already-short `review_N` references. Only the place identity now uses an alias. |
| POI semantic classification | Existing `pNN`/`eNN` projection already protects canonical places and evidence. Unchanged. |
| Landmark nomination | Names and descriptions, with application identity resolution afterwards. No supplied long-ID round trip found. Unchanged. |
| V3 Repair | Full place/activity/target IDs previously had to be copied. Aliases now cover their structured permissions, feedback, route endpoints, temporal fragments, lineage keys/values and compensation permissions. Original patch authorization/adoption remains canonical. |
| Official evidence reasoning | Canonical place IDs and hashed source keys previously returned in assessments. Place, source and task fields now use aliases; original URLs, exact spans and source alignment remain required. |
| Product introductions | Supplied activity IDs previously returned in decoration output. Activity aliases are restored before existing result ownership checks. |
| Preference polishing, native web search, embeddings | No supplied long IDs that the model must repeat; provider-generated citation IDs and vectors are separate. Unchanged. |
| Native evaluator | No operational identity-assistance LLM caller. Added an offline proposal packet using reference/place aliases; no model client, live acquisition, human adjudication or native adoption was added. Controlled Repair continues using its isolated frozen ports. |

A data-only neutral mapping utility derives distinct namespaces from complete per-call
identities without SDK/planner/evaluator-policy dependencies, hash truncation or prose
inference. Exact restoration, nullable response enums and unchanged native permissions
precede acceptance. Evaluator packets enforce decision coverage/per-reference ownership;
primary/Repair sizing includes transmitted aliases, instruction and enum schema under
unchanged ceilings. No new sends or retries were introduced.

| Validation stage | Result and interpretation |
| --- | --- |
| Initial focused / affected | 224 passed; 481 passed plus an obsolete non-JSON Repair SDK fixture failure. |
| Expanded regressions | 654 passed after covering lineage, fragment/related/removable identities and excluding user prompt markers from owned JSON parsing. |
| First full suite | 2682 passed, 10 skipped, two failures: import guard and concurrent frozen-source hash change. |
| Dependency correction | Neutral helper plus JSON-only evaluator packet preserved the guard; 19 related tests passed. Stable-source acceptance passed separately. |
| Actual SDK adapter | 9 MockTransport tests covered constrained request and canonical restoration, without network. |
| Stable final full suite | 2686 passed, 10 skipped, 249.85 seconds; Ruff/diff and independent Standards/Spec reviews passed. |

Implementation commits: `a8b13d1` (planning adapters) and `e9567f6` (offline evaluator
proposal packet). Evidence: `artifacts/short-id-20261005/` focused/affected/full logs
and `v0-identity-{short-input,reference-map,offline-replay}.json`.
All 61 original V0 pilot-authorized file hashes remained unchanged. The packet covered
nine references and twelve distinct candidates, mapping SHA256
`4a7d36cc0e0ccf64138f1faf36a194b99fe606c8999538966b3cc16fbe66a36b`.
Existing proposals restored identically; engineering estimates changed 5017→4522 tokens,
not the old provider's reported 4213 or measured new billing/accuracy.
Native identity adoption remained zero and four V0 routes remained UNKNOWN.

## October 5: six-adapter live regression

[#66](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/66) followed the mapping
audit; [#67](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/67) owned a
separate Proposed V0 adoption design. The initial plan was preparation only; its
subsequent approval authorized the executor and six selected adapter calls, not full
four-planner orchestration, discovery/RAG/Google or adoption. Prior work was published
through [PR #65](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/65), merge
`62f9329903b53f76abb8ea2a37e119bd94d3f478`.

The runner freezes actual SDK requests/schemas/maps/dependency versions/source hashes,
journals attempts before transport and uses an exclusive one-use launch record.
Each boundary permits one send, no retries/tools/redirects; ceilings were six sends,
60 seconds/request, 600 total, 10000 estimated input including schema plus 1024 reserve,
4000 output except official reasoning's existing 1200. Valid unknown identity proposals
remain distinct from malformed reference transport. V0 still returns proposals only.

Preflight rebuilt nine references/fourteen candidate occurrences/twelve distinct
candidates and restored all nine old proposals; original V0 SHA256 was
`b9cf2d4c5ed9b50d2a73e87f93d3631021a0abf7cdea19d1fcc9d5c83d87582b`.
Original 61 hashes and mapping digest above were unchanged. Six uncached capped calls
estimated USD 0.018 using October 5 Luna Standard USD 0.10 input/0.01 cached/0.50 output
per million; the approved USD 0.05 allowance was a retail estimate, not an invoice cap.

| Offline stage | Result |
| --- | --- |
| Initial executor | 18 focused passed; full 2704 passed, 10 skipped, 246.51 seconds. |
| Independent review | Standards zero; Spec two P2: Repair bypassed `build_repair_input`, primary omitted `validate_output_sources`. |
| Corrected acceptance seams | Production `repair_input_2` and native source/name/date checks;19 focused, 89 executor/Repair, 42 date/source/order tests passed. Both reviews rechecked clear. |
| Final SDK preflight | Six MockTransport sends, zero live. Estimated inputs 3958/1853/4279/3383/1436/6158;581 source files frozen. |
| Later delivery full suite | 2705 passed, 10 skipped, 421.67 seconds; this includes corrected executor, unlike the earlier full gate. |

The fixed review base was `73c5412492438ae89882925ffc25a25700bad4ce`, implementation
`a90dd87fec27b8a1a2b2aa3a3d170fadde0edc03`, correction/frozen live revision
`c9fbd3a49df61f6a458a68ef4e42b7b09ddcf267`. No Python type-check command was configured.

One authorized execution completed six sends in 18.016 seconds, all HTTP200/completed/Luna,
with no baseline call or altered fixture. The five planner fixtures were synthetic;
the identity fixture reused the frozen real V0 candidate packet without acquisition.

| Boundary | Selected native check | Input / output tokens | Retail estimate USD |
| --- | --- | ---: | ---: |
| Shared V1-V3 primary | Two restored places; source/date/coverage acceptance | 2,508 / 362 | 0.0004318 |
| Review profile | Restored place; two-review ownership | 611 / 131 | 0.0001266 |
| V3 Repair | Restored activity/place/target; isolated `apply_patch` permissions | 2,815 / 154 | 0.0003585 |
| Official reasoning | Restored source/place; exact supplied URL/span alignment | 1,863 / 322 | 0.0003473 |
| Product introduction | Two restored activity keys; ownership and coverage | 279 / 64 | 0.0000599 |
| V0 identity | Nine unique reference proposals; per-reference candidate bounds | 4,756 / 571 | 0.0007611 |

Totals: 12832 input, 1604 output, 14436 overall, zero cached and 211 reasoning tokens
already included in output. Raw usage also reported11930 cache-write tokens.
The October 5 [Luna Standard basis](https://developers.openai.com/api/docs/models/gpt-6-luna)
gives USD 0.0020852 before separately priced cache-write/regional/invoice adjustments;
actual billing is unavailable. All nine `(reference_id,decision,candidate_id)` associations
matched the old pilot; different prose and structural agreement do not prove identity truth.

Independent offline `build_cost_report` reproduced six costs and classified linked HTTP
as transport-only. A source-hash-bound derived `oracle` envelope supplied run identity/time;
no cost was allocated to planner versions. Complete-run/invoice coverage remained unknown.
Evidence: `artifacts/short-id-live-20261005/packet/`, its `live/` canonical outputs,
attempts/usage/raw responses, and containing owner assessment/derived cost artifacts.
Original raw responses, six request/response hashes and source/V0 bindings were verified.

The later authorized publication checkpoint is [PR #68](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/68),
base `62f9329903b53f76abb8ea2a37e119bd94d3f478`, initial head
`a802724ce5040ac3897428d207ca2fd3ac52fecb`. Eight release files passed both reviews;
no hosted CI workflow was configured, so local checks formed the recorded gate.
The checkpoint did not yet assert merge/closure; PR/Issue retain definitive state.

Six selected samples had no new restoration failure. They establish neither general
error rate nor full orchestration, venue-policy truth, prose accuracy or a benchmark.
Native identity adoption was still zero, four V0 routes UNKNOWN, and #67 Proposed.
Short references reduce long-ID copying exposure without eliminating semantic errors.

## October 15: shared requirement boundary correction

[Issue #165](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/165) consolidates
three generation failures at `f49503a`: case-04 could not execute an exclusive
WALK/TRANSIT set; case-07 accepted an empty pace list before canonical rejection;
case-05 supplied four paraphrased source quotations. All three inputs were
`VALID/CLEAR`. These failures establish boundary defects, not ambiguous requests
or infeasible routes. The original attempts and case-05's successful V0 remain historical results.

The offline implementation starts from `9a834a665de89a709ffb62efa7d5898be807c900`.
Implementation commit `0f979a1` connects typed hard modes through V0-V3, source-ID
restoration, structural pace defaults, native diagnostics and independent evaluation.
For PR delivery, the eight task commits were replayed onto remote `main` at
`6b11572c1c2331b61f263727dd7901ba8353752c`, excluding unrelated unpublished case-03
and batch material. The original D-drive main worktree and commits remain intact.

| Original engineering commit | Delivery commit | Purpose |
| --- | --- | --- |
| `0f979a1` | `27159e3` | Shared requirement implementation and tests |
| `1aca1f7` | `6ab7682` | Prompt projection guard |
| `fb87a68` | `49fd164` | Exact source granularity and transport score ownership |
| `8c25e99` | `fea23ea` | Current-wire mock response mapping |
| `27b520c` | `f606146` | Generation CLI reference date |
| `3021b83` | `1e98e17` | Capture-collision fixture reference date |
| `da85c41` | `a7d0310` | Bounded test launcher wait |
| `16a078a` | `6eaa173` | Current contracts and offline acceptance record |

All 675 backend/tools Git blobs match original checkpoint `16a078a`; the 51 release
paths match the original reviewed task diff. Test and replay results below remain
evidence from the original worktree, not a newly executed suite on the delivery branch.
The full regression was not repeated after corrections or for delivery.

Current rules belong to the [requirements contract](../../0002-requirements-evidence.md#input-gate-and-provenance-contract),
[transport ownership](../../0003-itinerary-transport.md#transport-ownership),
[Repair resource boundary](../../0005-validation-repair%28v3%29.md#transport-and-resource-boundaries)
and [RequirementSpec](../../contracts/0003-requirement-schedule.md#rtpeval-requirement-spec-contract).

| Boundary | Historical reading | New production representation |
| --- | --- | --- |
| Interpretation | Prompt 19 / draft 12; quote/occurrence DTO | Prompt 20 / draft 13; request-bound source endpoints restored before provenance validation |
| Pace | Version-aware list/null; empty list remains invalid | Required `trip_default` and `date_overrides`, mapped to the canonical list |
| Requirements | Canonical versions 3/4 remain readable | Version 5 adds a source-linked hard mode set; unsupported hard semantics still clarify |
| Evaluation | Requirement rules 3 / route rules 2 remain unchanged without the new kind | Inputs containing `transport_modes` select rules 4 / 3; resolved mode verdicts have one requirement owner |

Standards review found no hard violation and one P3 prompt-projection fragility.
Commit `1aca1f7` checks every required replacement before a model send. Spec review
found two P2 defects: coarse token spans lost valid sub-scope boundaries, and nested
quotations could duplicate transport penalties. Commit `fb87a68` provides codepoint
endpoints and source-interval equivalence while retaining independent restrictions.
Both axes rechecked those corrections clear. Commit `8c25e99` subsequently adapts
soft-quality MockTransport responses to the current wire without rewriting the
historical JSON fixture; both reviewers also rechecked it clear.
The broader regression exposed six date-dependent installed-CLI checks; `27b520c`
and `3021b83` pin their existing test reference date without changing production date policy.
Three guarded CLI subprocesses exceeded their 30-second launcher timeout. Commit
`da85c41` raises only the test helper's startup wait to 60 seconds; network/credential
guards, native execution deadlines and provider budgets remain unchanged. Both review
axes rechecked the correction clear.

| Offline validation | Result and interpretation |
| --- | --- |
| Full backend run | 4196 passed, 17 failed, 16 skipped in 6126.73 seconds. The run overlapped corrections; it is not a final-revision green gate. |
| Final Azure/provider/evaluator regression | 422 passed in 168.29 seconds; six supplementary exact-scope, Unicode and source-ownership cases passed in 7.03 seconds. |
| Corrected mock-wire and dated CLI files | Soft-quality alignment: 9 passed in 11.00 seconds; generation CLI: 87 passed in 133.58 seconds; opportunities CLI: 21 passed in 126.62 seconds. |
| Bounded CLI startup retest | All three previously timed-out scenarios passed in 206.26 seconds with the 60-second test-helper timeout. |
| Final static-source provider retest | Both wrapped 401/503 mock-provider cases passed in 17.48 seconds. |
| Route/Repair and independent entry points | 44 route/Repair tests and three independent V1/V2/V3 runner-entry tests passed. |
| Static checks | Backend/scripts and affected validation-tool Ruff lint, 43 changed Python format checks and tracked document links passed. |

The 17 full-run failures comprise seven obsolete mock response shapes, six dated CLI
checks, three launcher timeouts and one mock-provider classification anomaly. The first
16 have explicit corrections and passing affected regressions. The classification
anomaly did not reproduce on the final static source; the full-run log does not expose
its underlying caught exception, so source changes during that run remain a possible
explanation rather than a proven cause. Original failure logs remain retained. An
earlier sandbox-limited full run stopped at 29% and supplied no suite verdict.
The full suite was not repeated after correction, and the 16 skipped tests remain
unverified. Affected suites overlap and their counts are not a combined coverage total.
No frontend validation was added by this backend task.

Preservation checks compare 478 original/public files, including all 388 files under
the case-04/05/07 private attempt roots, with zero changed hashes. A network-denied
saved-response probe still reproduces the original hard-gate, empty-pace and four
paraphrase failures; its ordinary-default control preserves all four case-07 semantics.
No captured response is corrected in place.

Case-01/02's eight public itineraries round-trip exactly through the current schema.
Current native intake also accepts both original source-bound manifests through
read-only archive-byte access, with networking denied.
Available archive replays reproduce case-01 primary, paired, stopped/accepted opening,
legacy processing and all retained global-search reports, plus case-02 original primary,
corrected API quality, supplemented opening, paired and processing reports and public
source bindings. All replay acquisition is denied. These are exact historical-policy
replays, not evaluation under the new transport operator.

Initial archive replay exposed a missing case-01 `rglob` relocation and rejected changed
case-02 producer hashes. Read-only relocation and exact retained producer bytes resolved
those failures without weakening native receipts or source pins. Temporary restoration
copies were removed after acceptance; original archives and reports remain unchanged.
Both archives pass their native verifier again: 11,156 case-01 and 4,589 case-02
logical files retain all original bytes.

The source inventory grows with preference length. A future live preparation must size
the expanded actual request and use fresh revision/run/attempt bindings. Offline
acceptance provides no new itinerary, primary score, route feasibility evidence or
case-continuation authority. Display/read compatibility does not relabel historical results.

### Post-fix real-material compatibility

On 15 October 2026, the accepted case-03 and case-06 material passed a dedicated
offline compatibility check against merged source
`8326fb8c017f17df2426275a8634e35b91325394`, using Windows CPython 3.12.14.
The check imported the current implementation; it did not substitute retained producer
code. The original request reference date, 2026-10-15, remained pinned for historical
response reading. The accepted [case-03](../../../benchmark/case-03/report.md) and
[case-06](../../../benchmark/case-06/report.md) reports retain their original generation,
primary scoring, evidence and acceptance identities.

| Real material | Case-03 | Case-06 |
| --- | --- | --- |
| Saved interpretation responses through the current complete service | Four V0-V3 responses accepted | Four selected responses accepted, including V3 a2 |
| Pace and transport | Ordinary default; WALK routing default; no hard mode set | Relaxed default; soft DRIVE preference; no hard mode set |
| Saved canonical contracts | Three V1-V3 version-4 contracts read without value changes | Three V1-V3 version-4 contracts read without value changes |
| Full selected result schema round-trip | All four complete results preserved | All four complete results preserved |
| Current native intake | Original revision 1 accepted; no material/projection diagnostics | Original revision 5 accepted; no material/projection diagnostics |

The saved wire name is `PreferenceDraftV10`; explicit `preference_draft_12` reader
configuration selects its historical quote/list interpretation path. For each actual
response, current canonicalization preserved the saved V1-V3 contract's content apart
from the deliberate version-4 to version-5 tag. Different generations' interpretations
were compared separately, not collapsed into a common model interpretation. Both cases
retain one null-date pace default with no exact count. Their independently reviewed
RequirementSpecs have no hard obligations; case-06's driving preference is not promoted
to a mandatory mode restriction.

Eight additional in-memory controls converted those same response values to the current
source-endpoint and required-default wire, then passed the complete service with identical
canonical content to the corresponding historical reader. These are explicitly derived
adapter controls, not captured responses from a new model invocation. Six negative controls
still reject a fabricated legacy pace quotation, a missing current default and a foreign
source ID, once per case. Their error codes remain `invalid_source_occurrence`,
`invalid_daily_pace_default` and `invalid_source_span`. The latter two retain field paths;
the fabricated legacy pace quotation currently reports canonicalization with no field path.
That diagnostic limit does not affect acceptance of the unchanged real responses.

Native intake read 30 unique archived files at their original logical locations through
a read-only archive-byte view. Original manifests, source hashes, run IDs, usage and
provenance were unchanged; V3's optional paired projections remain available for both
cases. No original receipt/source pin was edited to obtain acceptance. All 675 tracked
backend/tools files stayed fixed during the check. Before/after hashes match for 89
protected files: 79 tracked case/input files and ten private archive files. Archive blob
hashes and declared lengths were verified in memory. External sockets and DNS were denied,
with zero attempted network operations, provider calls or scoring operations.

The private verification script and full derived result are retained under the ignored
historical identifier `.scratch/case0306-compatibility/`. Case-specific sanitized projections
are published with the [case-03](../../../benchmark/case-03/analysis/compatibility/post-fix.json)
and [case-06](../../../benchmark/case-06/analysis/compatibility/post-fix.json) presentations.
Their report/index refresh follows the audit's 89-file preservation check and retains prior
publication hashes separately; original indexed data and acceptance bindings are unchanged.
This result completes real-material reading/intake compatibility; it creates no replacement
attempt, primary report or score.
It does not establish new-wire model behavior or new planning quality. The earlier full-suite
limitations above remain unchanged; no full regression was repeated for this check.
