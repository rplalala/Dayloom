# Intake, identity, snapshots and usage

Current implemented contract for Tickets 01-04, including the 2026-10-03 ordinary-output
and 2026-10-05 structured V0 transport revisions. Source records are immutable; offline
replay and independent review are separate
from live acquisition. [Evaluation architecture](../0006-independent-evaluation.md) owns
implemented/deferred scope. This file owns preparation wire and provenance; scorer rules
live in the related topic contracts.

<a id="rtpeval-intake-projection-contract"></a>
## Intake and stable projection

Accept one explicitly selected batch. Emit material_diagnostics, inventory, projection_diagnostics and track_availability. A material error returns needs_material_correction for the submitted batch; do not silently evaluate a smaller cohort. Projection uncertainty does not revoke benchmark qualification. No producer runner, validator, requirement interpreter or workflow-completion check is invoked.

Fatal material errors: unreadable/ambiguous JSON (including duplicate object keys), missing mandatory input/result/RequirementSpec or required usage envelope, incorrect hashes or group/run/version linkage, unsupported artifact major version, path escaping the resolved batch root (including links/junctions), non-object itinerary, absent/non-array days or activities, non-object activity, missing/non-string required activity identifier/title, nonunique activity IDs or nonunique/unreadable declared day dates. These prevent stable interpretation; do not reconstruct them. A confirmed multi-POI visit block is an existing delivery-contract diagnostic, not a request to split it.

A declared unavailable usage envelope is valid and disables only resource measurements. Missing optional V3 draft/final-primary projections disable paired analysis; never reconstruct them from the selected final. A malformed optional projection records its own unavailable reason without replacing the selected final.

Use a versioned evaluation wire reader rather than running every product validator. itinerary_1 (including historically absent output_version) and itinerary_2 are explicitly recognized; original absence remains recorded. Missing historically optional roles become unknown in the derived view; missing optional transfer/reference arrays become empty with an absent-field marker. Preserve additional result fields without exposing them to quality readers. Unknown major versions require adapter support, not guessing.

Representable content issues remain diagnostic observations: date gaps, empty activities, unsorted records, overlap, output-versus-request date/destination discrepancy, unknown roles, invalid/missing time values, uncertain timezone, unknown place association and bad Transfer links. Do not silently repair, reject for low quality or use current live-request date limits. Retain source records even when dependent metrics cannot judge them. Original request hashes and producer-attested linkage establish which Input was run; a content discrepancy alone does not prove a wrong-file submission.

A source reference is (batch_id, group_id, run_id, artifact_sha256, JSON pointer). Derived record IDs use this tuple and projection-contract version, not canonical place ID. Preserve original array positions, declared day, original activity ID and raw values. Sorting makes a separate view; it never changes source pointers. Same activity IDs in draft/final or two runs do not imply correspondence.

Quality view exposes itinerary fields, reviewed requirements and later independent records only. Planner requirements, supply, RAG origins, validation findings, cost projections, route diagnostics and Repair records remain outside it. Preserve Transfer mode, endpoint/time/duration claims as claims; validation_state, unknowns, evidence_refs, mode_source and calculation_basis cannot decide quality. Mechanism readers access their own data channel. Human rendering must strip private source/version/provider identifiers while retaining meaningful itinerary text and uncertainty.

## Suite selection and generation resources

A suite selects already accepted single-group four-version manifests with explicit
native revisions; it does not establish producer completion, choose better runs or
invoke a Planner. Native intake binds all original Input, RequirementSpec, result,
usage and provenance bytes before suite preparation. Cross-case run identity
uniqueness prevents duplicated selected invocations. Optional unavailable usage or
missing pair stages retain their original meaning and do not revoke qualification.
The [suite artifact contract](0001-evaluation-artifacts.md#source-bound-suite-lifecycle)
owns declarations, budget admission, preparation and closed output inventories.

Default suite resources consume only selected saved generation usage. Oracle
acquisition and frozen controlled simulation are excluded from Planner comparisons.
The suite calls the native resource and cost readers without changing their coverage,
latency scope, observed subtotals, cache partitions, Repair subsets or billing rules.
Each case retains `tracks/NNNN/resources.json` and `cost.json` independently of whether
its primary evaluation completed, stopped or remained unstarted.

Case `tracks.resources` can reference explicit generation `prices`, optional `bills`
and `annotations`; these paths are resolved and byte-bound during preparation.
Bills or annotations require explicit generation prices.
Primary case `prices` bounds independent evaluator acquisition and is not silently
reused for generation. Missing generation prices produce a separate unavailable cost
wrapper with `reason=generation_prices_not_supplied` and `report=null`; no catalog or
zero total is invented. With supplied prices, the native cost report preserves actual
bills, estimates, unpriced events and partial subtotals. Malformed supplied material
requires correction before sends; valid unavailable usage remains qualified.

<a id="claims"></a>

## Structural claims and directed occurrence association

Emit `evaluation_role=primary_visit|transport|transition|unresolved`, role status, source
references, reasons and independent review linkage. An explicit `main_poi` with usable
`place_name` supplies the structural visit/place claim; an ordinary descriptive title does
not need to equal that name. Without usable place fields, retain the supported name-only/
review path rather than manufacturing a venue. Explicit competing structural/content claims
retain `competing_claim`, its field/text/source and parsed destination/origin as applicable.

Title regexes do not veto declared visit or transport roles. A structured `main_poi`
remains a primary visit even without a place field or with a placeholder-like title;
this does not establish its factual venue identity. A declared `free_time` is non-POI,
including `Coffee break` or a named lounge, regardless of title wording. Independent
occupancy/protection review still decides whether it is a time commitment. A locationless
declared transport remains transport even with a `Visit`/`Tour` title. Independently
reviewed roles retain precedence. Unknown roles without usable place claims remain
unresolved; daily counts still retain genuine role and date-attribution uncertainty.

Bounded title parsing may retain source-linked `competing_claim` metadata and feed the
separate identity review. It cannot establish semantic role contradictions or factual
identity. Legacy endpoint parsing applies only without a structured transport declaration;
this revision adds no general semantic model or new LLM invocation.

Generic locationless activities are transition-like; named unresolved POIs stay visits.
Nearby is unscheduled. Unknown/inconsistent roles retain review and applicability counts.
Neither candidate membership nor costs establish independent role/identity.

Preserve delivered day membership. For a day with comparable valid timestamps, order visit candidates by start, then end, then original pointer for display stability. Equal/overlapping times remain conflicts/ambiguities, not corrected chronology. Invalid or incomparable clocks cannot establish adjacency by arbitrary lexical sorting; emit an adjacency-unresolved record with involved sources.

Candidate legs connect consecutive primary visits within a day. Nearby, transition placeholders and transport records do not become POI endpoints. Protected intervals remain separate blockers. Possible intervening unresolved-role records prevent declaring a clean complete adjacency list for that span; preserve the candidate and uncertainty instead of skipping them. Canonical same-place N/A is decided later using independent identity, not equality of claimed IDs.

V0 preserves the optional Activity `transport` object with `mode`, `from_activity_id`
and `to_activity_id`. Independently reviewed mode and endpoint pairs take precedence
separately. Otherwise a present declaration takes precedence over title/notes, including
null/unsupported mode and invalid endpoint IDs. Automatic binding requires a directed,
consecutive, same-day candidate pair with resolved chronology and an interval fully
contained in its gap. Self, reversed, dangling, cross-day, nonadjacent, overlapping,
unresolved or malformed associations stay unbound. A malformed declaration never
enables favorable prose fallback. Null/unsupported mode remains unknown even with a
valid association. Known endpoints and clocks can establish occupancy independently
of unknown route mode; association, occupancy and route feasibility remain separate.
The existing independently reviewed endpoint path may associate a same-day candidate
pair despite a time conflict, which remains visible to the scorers.

Absent/null objects retain the legacy path below; object `mode=null` does not.
Legacy V0 transport supports complete `from NAME to NAME` clauses, optionally prefixed by `walk`,
`walking`, `drive`, `driving`, `transit`, `public transit`, `transfer` or `travel`.
Only complete supported title/notes declarations supply legacy endpoint pairs. All recognized
pairs must agree; unrelated prose and generic estimate notes neither supply a pair nor
block association. A bare supported mode title (or `Transport`/`Transfer`) without any
recognized endpoint declaration can associate through exactly one containing gap.
An unsupported non-bare title remains unbound without independent endpoint review.
Match complete NFC/casefold/whitespace-normalized scheduled labels,
resolved chronology and exactly one same-day occurrence gap containing the whole transport
interval. Repeated labels are acceptable if only one occurrence pair survives. Contradictory,
reversed, unsupported, overlapping or ambiguous claims retain review; no nearest/favorable
pair or positional override is chosen. Independent reviewed endpoints can associate despite
a separate time conflict; the review does not clear that conflict.

Without a structured object or independent mode review, legacy V0 mode comes from
a bounded explicit title declaration.
Supported bare labels include walk/walking/on foot, public transit/public transport,
bus/train/metro/subway/tram, and drive/driving/by car. Recognized directed movement
clauses may supply the leading mode label. The first semicolon-separated title clause
must declare a supported mode; later recognized mode declarations must agree. Missing,
unsupported or conflicting mode declarations remain UNKNOWN. Notes are not mode fields;
incidental conditional/transport keywords and narrative negations are not interpreted.
Original prose is preserved for independent review rather than treated as semantic proof.

V1-V3 associate Transfers through directed consecutive same-day activity IDs. Wrong/dangling/
nonadjacent/cross-day IDs remain unbound; place-ID disagreement stays a separate claim.
Authority is V0 Activity and V1-V3 Transfer. `transport_source`, `transport_applicable`,
`ignored_transport` and diagnostics preserve ignored representations without occupancy or
fallback. Missing transfers remain missing. Same-source duplicate claims share source sets,
segments remain segments, and conflicts stay alternatives rather than summed or shortened.
Association status and agreement are separate. No claimed arrival is synthesized from duration.
Display-only inferred arrival follows [human review](0005-quality-human-review.md#human).

`policy_version=structural_claims_directed_occurrences_5`; immutable source-reference
`projection_version=rtpeval_projection_1`. Internal-finding-only source changes can preserve
semantic projections while still changing exact artifact hashes and source identities.
Replay derived identity/evidence/report preparations when classification changes; preserve
original source artifacts and historical reports. The density table remains
`rtpeval_daily_density_2`.

<a id="identity"></a>

## Independent identity and adjudication

<a id="version-specific-identity-requirement"></a>

### Version-specific identity evaluation

Accepted by the user on 2026-10-06 and published in
[parent #74](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/74).
V0 introduces an LLM primarily to correspond original freely generated POI claims
with supplied independent API candidates, when available. Correspondence is distinct
from original-claim correctness: recognizing a venue cannot repair a wrong submitted
address or certify opening/route feasibility. Insufficient support remains UNKNOWN.

V1-V3 identity and requirement evaluation uses independent API evidence and deterministic
program rules, without an identity model call, model-result dependency or model fallback.
The subsequently approved [missing-hours access assessment](0004-opening-routes.md#missing-hours-access-judgment)
is a narrow opening-only model exception shared by V0-V3; it does not change identity rules.
Original API-backed names/addresses are compared with corresponding API facts;
differences count as errors without model-based precision, translation or semantic
equivalence. User-named requirements and optional V3 projections follow this same
version rule. Verifiable bindings identify claims; planner decisions/caches do not
replace independent evidence. Unresolved/ambiguous evidence remains visible without
borrowing V0 model judgments. Wrong original addresses and different venues are FAIL;
failed/missing API evidence is UNKNOWN. Original claims and erroneous endpoints are
never repaired, and score arithmetic is unchanged.

Implemented under [#75](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/75),
with version-owned requirement targets corrected locally under
[#83](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/83).
`resolve_identities(intake, evidence, *, model_result=None)` produces
`association_policy_version=versioned_api_identity_4`. Every V1-V3 final/optional
primary visit requires its original `source_place_id`, structured `place_name` and
`location`. Proven missing fields are FAIL even without an API response. Independent
Details must have an available observation with retrieval provenance, the requested ID
equal to the original ID and the returned ID equal to that request. Missing/failed,
malformed or unlinked Details are UNKNOWN. Names retain literal equality. Address
comparison is binary PASS/FAIL: exact text, case/Unicode/whitespace formatting, or
complete equivalence explained by `longText`/`shortText` pairs supplied by the same
independent Google observation. Remaining words, punctuation and numbers must agree.
No abbreviation dictionary, similarity threshold or model fallback is used. Conflicting
alias mappings and unexplained differences are FAIL. Missing acquisition/identity
provenance is a separate uncertainty; it cannot author an address comparison PASS.
`address_comparison` retains the original/provider strings, binary verdict, basis and
used pairs. Policy 3 retains literal address behavior during historical reconstruction;
policies 1/2 and historical V0 correspondence also keep their original replay paths.
Only PASS adopts a canonical ID. FAIL/UNKNOWN retain null canonical IDs and original claims.

Accepted on 2026-10-08, primary-visit `place_association` independently records
`state` (`verified` or `UNKNOWN`), `place_id` and `reason`. It does not change
`grounding_verdict`, `resolution`, `canonical_place_id` or original claims.
V1-V3 verify the original submitted ID using independent available Details, offset-aware
retrieval provenance and identical requested/returned IDs. This check still runs when
the original name/address is missing or incorrect. Missing or unverified IDs have no
association; search candidates never replace the original ID. No evaluator model is used.
V0 uses the existing source-bound, validated model correspondence: a selected supplied
candidate with decision `match`, consistent destination and supported address assessment
(`equivalent`, `different_precision`, `incorrect_claim` or `not_supplied`). Missing/ambiguous
correspondence, different-place/unknown address assessment, contradictory destination,
conflicting candidate observations or unverifiable provenance leave association UNKNOWN.
Candidate presence/rank alone never establishes eligibility. An `incorrect_claim` address
remains grounding FAIL while a trustworthy association permits independent physical checks.

Snapshot, coordinate, opening and route consumers use this physical association.
Opening checks the associated API venue's hours against the original visit interval;
routes use its API coordinates with the original order, mode, departure and reserved duration.
WALK, DRIVE and TRANSIT remain their original modes. No original output is repaired.
Requirement occurrence matching also uses verified associations under the
[requirement count contract](0003-requirement-schedule.md#count-bounds-and-completeness),
against each version's adopted target identity. Target grounding, count/date/time conditions,
canonical repetition and paired venue correspondence remain separately applicable.
A downstream PASS never cancels grounding FAIL or proves full requirement fulfillment. The report policy versions this change; the unchanged
V0 correspondence packet remains `v0_identity_correspondence_3` and existing validated
material can be consumed offline without another model request.

Reviewed requirement subjects can retain an optional `source_place_id`; it is a claim
binding, not factual evidence. Identity planning independently requests its Details.
RequirementSpec meaning and acquisition references remain shared, but target identity
results belong to each submitted version. Target reference IDs hash their source with
the version; `evidence_reference_id` links to the original shared acquisition reference.
V0 targets use only V0 model correspondence. V1-V3 targets use program rules and never
borrow a V0 decision. Each version's projections share its target result.

Without a binding, V1-V3 resolution requires the exact original query, declared
20-result scope, independent-source/retrieval provenance and the complete retained set.
The candidate count must equal the declared result count; a full 20-result page or
retained next-page token remains UNKNOWN because completeness is unverified. A present
pagination field with an empty or non-string value is malformed and also UNKNOWN. Malformed
candidates or conflicting facts for one ID also remain UNKNOWN. Filter all candidates
by literal original name, verified destination and any supplied equivalent formatted
address, then require one distinct surviving ID. A complete search with exactly one
name/destination-eligible ID and a supplied address mismatch gives FAIL, retaining
`address_comparison`. `candidate_address_comparisons` preserves each eligible ID's
binary comparison even when multiple identities leave resolution UNKNOWN. Zero eligible
identities and multiple surviving matches remain UNKNOWN; rank never chooses a candidate.
Identical repeated observations of one ID are allowed. Ambiguous mappings include any
long or short endpoint paired with multiple different endpoints.
Destination tokens use literal typed long/short component values, with explicit locality
or administrative region and country evidence; without typed components they require
exact formatted-address tokens. Hierarchical sublocality levels remain separate and
do not conflict through their generic sublocality tag. Conflicting/malformed typed
components cannot be overridden by formatted text. Historical address rules are unchanged.
Missing source/retrieval/query provenance remains a local UNKNOWN; false source declarations,
invalid batch/reference linkage and impossible count structure remain material errors.

Default `prepare_identity_judgment(..., model=MODEL)` includes V0 primary visits and
V0 requirement targets only, with packet policy `v0_identity_correspondence_3`;
source digests and short-reference
ownership bind eligibility. Foreign decisions, historical all-version packets and edited policy/version
markers cannot pass current import. Absence of a V0 result leaves V0 UNKNOWN while V1-V3
targets still evaluate. Confirmed target FAIL is retained as a component of that
version's associated requirement checks. No identity resolver or `identity_cli` command
executes a model or provider.

Explicit `--historical-association` replays `versioned_api_identity_2`, including
version-owned targets and the former FAIL/UNKNOWN downstream block. It reconstructs
the original report without `place_association`; historical consumers use only canonical
adoption. Relabeling a saved report does not migrate it. Current reports must be rebuilt
from source-linked evidence; historical snapshots and smoke results remain unchanged.
Explicit `--historical-program` replays `versioned_api_identity_1`, including shared
programmatic targets, the original single-result rule and V0 packet policy
`v0_identity_correspondence_2`. Old packets cannot pass current import; saved reports
replay against their original policy. Historical raw smoke files are never rewritten.
Snapshot coordinate consumers select evidence derivation from the replay-verified report
policy; explicit historical V0 material loaders and CLI modes preserve the original wire
without adding new pagination metadata. `snapshot_cli identity-evidence --historical`
derives that original wire. Current derivation retains pagination uncertainty; historical
compatibility never removes it from a current-policy report.

The V0 response correction is implemented locally under
[#76](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/76). The model's primary
purpose is correspondence to supplied independent candidates, or insufficient support;
it cannot invent candidates, facts, coordinates, opening/route evidence or corrected output.
`evidence_fields` uses the same supported-path set as import validation:
`claim.place_name`, `claim.destination`, `claim.location`, `claim.claimed_place_id`,
`claim.original_title`, `candidate.display_name`, `candidate.formatted_address`,
`candidate.address_components`, `candidate.observations` and `case.candidates`.
Citations must refer to actual nonempty fields owned by that claim and selected candidate,
or the case's supplied candidate set. Returned paths are never normalized or repaired.
Matches require claim name/destination and candidate name/address, plus original location
and claimed ID when supplied. Cited address components must retain their typed structure.

The schema partitions owned short reference IDs by original-address presence. Every
decision for an absent/null/blank original location requires `not_supplied` and its citation
enum excludes `claim.location`; decisions with a supplied address cannot use `not_supplied`.
Instructions and import enforce the same rule. Absence alone does not prove an address error.
Complete unique reference coverage and candidate ownership remain mandatory.
Current requests encode `decisions` as an object keyed by every prepared short reference:
all keys are required and extra keys are forbidden. Shared address-present/absent `$defs`
retain the citation and assessment alternatives. Instructions enumerate the exact count
and IDs, including every visit and requirement subject; insufficient facts require an
explicit UNKNOWN decision rather than an omitted case.
Import requires the exact owned key set and each value's `reference_id` equal to its key.
Duplicate raw JSON keys, duplicate/foreign references, incomplete objects and arrays
are rejected before converting valid judgments to the existing internal rows. Saved
request strings, raw responses and receipts are never rewritten by that conversion.
Historical uniform and legacy V0 request arrays remain unchanged. Earlier current-policy
packets retain their original producer implementation for replay; the new request schema
does not rebind or relabel their consumed responses. Correspondence and scoring policies
remain unchanged. Azure's supported structured-output subset supplies required objects
and references; array cardinality/uniqueness keywords are not used as a coverage guarantee.
Validated V0 records expose `candidate_correspondence` (restored candidate ID and decision)
separately from `grounding_verdict` and original claims. Supported `incorrect_claim` or
`different_place` assessments remain FAIL even for a recognized candidate; they require
original name/destination/location and independent candidate name/address, or the complete
nonempty `case.candidates` when no candidate is selected. Insufficient correctness support
remains UNKNOWN. Neither FAIL nor UNKNOWN adopts a canonical ID or a corrected endpoint.
A supported `destination_assessment=contradictory` also produces FAIL, including when the
original address is absent. It requires original name/destination and candidate name/address,
or the complete nonempty candidate set without a selection. Missing original or independent
support is rejected at import; the model must use UNKNOWN when evidence is insufficient.
Historical uniform replay retains its original destination-conflict behavior.

The new V0 instructions/schema/policy produce new packet and request hashes; current import
requires that exact packet and response provenance. The historical uniform schema/instructions
remain unchanged under explicit replay. Old V0 policy-1 packets and the rejected #73 envelope
cannot be relabeled as accepted current reports. Raw responses and consumed execution evidence
are retained unchanged. This contract grants no new call.

Fresh preparation under #77 uses `rtpeval_identity_smoke_preparation_2`, recomputes the
current V0 primary population, and freezes original/candidate material, implementation,
strict request/schema, reference map, HTTPS destination and a new execution directory.
The offline pending report supplies no new V0 model evidence. The private handoff owns
exact proposed limits, source revision, data/destination scope, counts, output paths and
stops. Prices retain ordinary/cached/write input categories and output (including reasoning);
missing categories use a labelled conservative reference upper bound, with the original
usage preserved. Reference prices and regional scenarios are distinct from unavailable
provider invoices. One attempt consumes the bound directory, even on HTTP/import failure.
Neither preparation nor ticket completion authorizes execution: a new exact-plan approval
and the current-session child required by smoke policy are mandatory. Historical #73
failure evidence, raw response and consumed directory remain untouched; FAIL/UNKNOWN are
valid outcomes without an all-match acceptance target. See the
[operational guide](../../backend/evaluation/README.md#prepared-one-call-identity-development-smoke)
and [preparation record](../records/evaluation/intake-identity-usage.md#fresh-v0-smoke-preparation-2026-10-06).

The complete `identity_versioned_replay` stores independent evidence and the optional
V0 result. Consumers reconstruct the exact report from the original intake before using
it. Programmatic record/replay markers trigger verification even after policy substitution.
`programmatic_judgment`, `grounding_verdict`, original claims and observation hashes remain
visible. Quality and paired reports count grounding FAIL directly. Requirement/schedule
descriptions retain identity checks; coordinate preparation's legacy-named
`unadopted_references` lists physically unavailable references under the current policy;
opening and route checks retain identity verdicts separately from their own feasibility
verdicts. Grounding FAIL alone supplies no coordinates or context; only the separately
verified association enables physical evidence. Opening and route facts can remain UNKNOWN
when their independent evidence is unavailable.
Score arithmetic, masks, denominators and planner generation behavior are unchanged.
Status is `complete` when all identity verdicts are decisive (including FAIL), otherwise
`needs_evidence`; UNKNOWN is never dropped from downstream populations.

Explicit historical replay preserves the old policies and evidence, without relabeling
them as current programmatic reports. New implementation does not rewrite original files
or grant paid execution, publication, formal-run or freeze authorization.

### Complete V0 case-set binding

`rtpeval_identity_model_result_2` preserves `binding_source` with the exact intake and
independent evidence used for its original current-policy V0 packet. The applicability
unit is the complete V0 case set. Original packet, request, response hash and capture
times are retained. Reconstruct that packet before applying decisions to another batch;
never rewrite the receipt into a fresh response.

Occurrences bind group/run/output hash/pointer/projection version, original claim,
complete ordered candidates, captured observation facts and raw evidence hash. Requirement
targets bind source input, exact subject and all related obligations. Only observation/
reference wrapper identifiers and raw file location are excluded from the fact fingerprint.
Batch revision and unrelated V1-V3 content may change when all V0 cases and relevant facts
remain identical. Changed claims, requirement meaning, candidates, capture provenance,
raw bytes, policy or case membership reject import. Decode short references against the
original packet, map to current occurrences, then enforce normal citation/ownership rules.

Result-1 retains exact whole-packet matching. Historical policy/all-version packets cannot
enter result-2. Historical files retain their original policy/code for exact reproduction.
Applicability is separate from freshness: admissible old material cannot replace evidence
for a newly required live run.

### Formal automatic execution

The [formal CLI](../../backend/evaluation/README.md#fresh-automatic-evaluation-cli) wraps
native acquisition/scoring. Preparation freezes originals, reviewed schedule/occupancy/
route/density contexts, explicit send/token/time/cost limits, caller-supplied dated USD
prices and code hashes without sending. Execution verifies the exact digest and sources,
creates a new one-use directory and acquires both snapshots afresh. V1-V3 use API/program
rules; one V0-only Responses request is allowed with no fallback or automatic retries.

Identity execution options may specify `reasoning_effort=low|medium`; absence preserves
the historical low request without altering saved option data. The explicit value is
part of the preparation digest and must match both the sent Responses body and the
HTTP body verified by offline replay. Unsupported values fail before execution.
This option does not apply to the separately fixed-medium opening-access workflow.

Search retains original name/destination/location and page size 20. Search/Details masks
include ID, name, address, typed address components, business status, coordinates and
timezone; Details includes current/regular opening hours. A next-page token remains
incomplete evidence rather than triggering unseen requests. Matrix uses one original
directed coordinate pair, declared mode, native options and departure only for time-dependent
queries. No mode/date substitution is permitted. Identical requests may share a fresh
response within a phase; version/occurrence judgments stay separate.

Journals omit credential headers and retain exact wire, attempts, times, HTTP outcomes
and raw bytes. Result-2 binds the captured response; replay checks HTTP bytes/usage,
derives coordinates/routes again and recomposes native reports. Failed directories stay
consumed and retain stopped reports, usage and receipts. Reports distinguish processing,
acquisition and evidence completion, retaining every in-scope UNKNOWN's check/reason/source
and a separate acquisition-failure inventory. Excluded optional/human/controlled/official
tracks are not acquired-but-UNKNOWN units. Costs cover evaluator-only observed sends and
reported tokens against dated references; unavailable actual billing is null, never zero.

## Historical identity replay and supported legacy formats

These paths reproduce explicitly selected older policies. They do not define the
default version-specific identity workflow above. Saved facts, decisions and wire
formats retain their original policy; legacy selection does not certify current acceptance.

### Explicit historical replay

`resolve_legacy_identities`, `resolve_legacy_v0_identities`, and CLI `--legacy` reproduce
the prior contracts below for frozen evidence. Historical human decisions are preserved;
they are not fabricated or rewritten as model decisions. Default API/CLI calls reject
human/audit inputs unless this explicit legacy path is selected. Consumers retain old
policy compatibility for historical reproduction.
Uniform LLM reports use `resolve_llm_identities` and CLI `--historical-llm`, preserving
the exact old packet and report shape. `--legacy` and `--historical-llm` cannot be combined.

Ticket 03 reads accepted projection references, reviewed REQUIRED/EXCLUDED/fixed-time
subjects, independent observations, a predeclared audit and optional decisions. It uses
neither planner evidence nor provider rank as confidence. Each established primary visit is
a grounding unit even without an ID; unresolved roles retain a separate population count.
Requirement subjects and high-impact possible obligation matches require independent review.
A visit is high-impact when its normalized name matches a subject or independent candidate/
claimed IDs can overlap. If a same-group subject has no usable independent candidates, all
primary visits in that group need review rather than assuming they cannot match.
Nearby/transport are outside main grounding. Resolution and claimed-ID consistency differ:
a reviewed intended venue A can resolve while its incorrect supplied ID B remains conflicting.
Unresolved identity is not proof of fabrication, and resolved identity is not opening/route PASS.

`rtpeval_identity_evidence_1` has `batch_id`, `batch_revision` and `records`. A record is keyed by Ticket 01 `reference_id`, has a unique `observation_id`, declares `source_kind=independent_google_places`, and may carry `details` and/or `search`. Missing records mean unavailable evidence. An available details observation retains `requested_place_id`, `retrieved_at` and `place`; search retains `query`, `requested_page_size`, `actual_result_count`, `retrieved_at` and raw-order `candidates`. Candidates carry Google ID, display name and formatted address; rank, business status and additional provider fields may be retained but rank never acts as confidence. Failed/unavailable/malformed observations retain their status. Invalid envelope linkage, duplicate references or impossible count structure are rejected rather than producing a partial report. A declared independent source is provenance metadata, not proof that an external service was contacted.

`rtpeval_identity_audit_1` has the same batch/revision plus a nonempty seed and positive `sample_count`. The plan is a required, separately frozen input. Among strict automatic proposals, choose the lowest hash of seed, batch/revision and a semantic audit key, then select up to the declared count. The key includes group/version/projection/source pointer and visible place claim, but excludes the result file hash and V3 internal findings. Selected proposals require review before entering resolved grounding counts. An absent plan or zero sample count is rejected. The module verifies deterministic replay and records plan hashes; benchmark preparation must establish that the plan was fixed before result inspection.

`rtpeval_identity_reviews_1` has batch/revision and per-reference decisions. Each decision supplies the current observation hash, consecutive positive revision, reviewer reference, review time, rationale, and `confirm`, `reject` or `unresolved`. A confirmation names an ID present in independent observation candidates. Stale evidence, duplicate/missing review revisions and unsupported candidate IDs are rejected. The report retains the entire history and uses the latest decision. A rejection leaves identity unresolved; it does not automatically prove a fictional place. A new artifact source reference or evidence observation needs new reviewed linkage.

### Automatic association and typed addresses

Structured place claims and independent evidence determine association. Title-derived
`competing_claim` metadata is diagnostic and cannot veto automatic proposals, including
`Visit Museum A in the morning` or `Museum A and its gardens`. Required review/audit
gates and independently evidenced name/ID/address/destination conflicts still apply.

Names use NFC, casefold and whitespace normalization only. Aliases, translations, competing
branches and approximate names remain review cases. Supplied-ID details must return the
requested ID and corroborate the structural name/destination/location; lookup success alone
is insufficient. Without the supported independently matching numbered-street shortcut,
full-page independent name search must show the same sole raw/usable candidate. A supplied
search remains contradiction evidence even when the shortcut applies. Name-only search
uses the submitted name, page size 20 and exactly one raw/usable candidate. The bounded
observation does not prove global uniqueness. Generic country/admin/postcode agreement
cannot activate the shortcut. The legacy numbered English street recognizer accepts only
`street/st`, `road/rd`, `avenue/ave`, `lane/ln`, `drive/dr`, `boulevard/blvd`,
`way` and `court/ct` (optional terminal period). Other forms need typed support or review.

Independent candidates retain original formatted address and optional typed
`address_components` (`longText`, optional `shortText`, `types`). The snapshot bridge copies
raw `addressComponents`, never synthesizing it. Typed locality supports city association;
explicit destination qualifiers must agree. Country/state/postcode/street occurrences of
the same word do not substitute for locality. Street-number/route components support street
locations and provider short forms; generic locality agreement is not a numbered-street match.

For equal ID/compatible name, differing formatted strings can agree through complete typed
street-number/route/locality/country evidence; optional admin/postal components must agree on
both sides. Missing/conflicting components do not prove equivalence. With components absent,
exact legacy comma/semicolon address-component matching remains available. With typed locality
available, unsupported location tokens cannot borrow favorable formatted prose. Malformed
components remain diagnostic. No substring city test, geocoding, alias inference, extra request,
LLM call or old-snapshot backfill is added. Planner field masks/budgets are unchanged.

The historical native replay path requires
`association_policy_version=structural_claims_typed_addresses_3` downstream. The explicit
V0-only policy below has a separate replay-aware consumer boundary.
`subject_scope_version=required_excluded_fixed_time_1` and `reference_set_digest` bind the
recomputed reference population. Old derived reports require offline replay and new affected
plans; fixed-time subjects may change high-impact review even with unchanged source hashes.
Missing observation remains UNKNOWN; missing/stale preparation linkage requires replay.

Reports retain independent decision path, candidate/observation/rule/audit hashes, latest
review and complete history, resolved/unresolved states and consistent/conflicting/unverifiable/
absent claimed-ID association. High-impact/audit queues hide source versions. Reviewed rejection
is unresolved, not automatically fictional; an empty queue does not imply every venue grounded.

### V0-only model-assisted offline adoption

`resolve_v0_identities(intake, bundle_path, reviews=None)` explicitly selects
`association_policy_version=v0_model_assisted_association_1`. It imports saved model
material; it does not call a model or provider. Native `resolve_identities` and its CLI
retain their existing policy. Model assistance applies only to the selected group's V0
final visits. Requirement-subject proposals are retained for review. Other versions and
planner execution remain unchanged.

The `rtpeval_v0_identity_material_1` bundle declares `artifact_root`, `group_id`, an
IANA `authorization_timezone`, and `artifacts` with root-relative paths and byte SHA-256
values. Required roles are `intake`, `result`, `input`, `provenance`, `snapshot`,
`judge_input`, `reference_maps`, `requests`, `response` and `audit_plan`. The saved
`freeze`, `authorization` and `attempts` establish the historical audit binding;
missing freeze/authorization retains `audit_freeze_unverified` for new model-supported
adoptions, preserving native accepted decisions and audit selection. Paths cannot escape
the declared root. The result must actually be V0, match
the selected run/input/provenance hashes and reproduce its stored final projection.

Replay the independent identity snapshot against the recomputed plan. Each judging case
must contain the exact structured claim and independent candidate facts for its reference;
candidate ordering may differ, facts may not. Require complete unique V0/subject packet
coverage, exact short-reference map/schema/request correspondence, a completed response
from the requested model, and exact restoration with per-reference candidate ownership.
Unexpected tools or stale/corrupt/foreign material reject the import without partial adoption.

For a `match`, require citations to `candidate.display_name` and
`candidate.formatted_address`. The only additional supported paths are
`candidate.address_components`, `claim.place_name`, `claim.destination` and
`claim.location`. Each cited field must exist, be nonempty and have its declared wire
shape; claim fields are comparison inputs, not independent facts. Invalid citations
remain explicit per-reference ineligibility. Preserve unknown/no-match decisions and
all citations; do not classify rationale/title wording, provider rank or confidence.

Cited raw address components require a nonempty list of objects with nonempty `longText`;
optional `shortText` is a string and optional `types` is a list of nonempty strings.
Absent types and repeated valid provider types are preserved, not synthesized or rejected
by the native semantic comparator. Uncited optional malformed fields remain diagnostic.
Scoped records retain `native_reason` and the restored `model_proposal`, including its
eligibility. This policy does not independently adjudicate raw geographic meaning.

Latest genuine human decisions and native candidate support take precedence. An eligible
ordinary unmatched V0 visit may resolve with `decision_route=model_assisted`; protected
subjects/visits and selected audits remain pending without genuine confirmation. Extend
deterministic selection across scoped native/model automatic candidates using the saved
positive count and seed. Native V1-V3 audits retain their existing selections. The
authorized preflight manifest must bind the source, judging packet, map and audit plan;
the saved send must bind the exact request and response. Date-only authorization uses
the explicitly declared timezone; precise authorization timestamps require an offset and
must precede the send. Provider clock timestamps are retained as provenance,
not an arbitrary tolerance-based freeze test. Local authorization/receipt records are
supplied evidence, not cryptographic proof of human identity or chronology.

Reports carry bound artifact/model/map/proposal/audit provenance, original review input,
`adoption_counts` and directed `leg_identity_eligibility`. Consumers recompute the report
from the bound bundle and supplied reviews and require exact equality before identity
readiness, coordinate extraction or evidence/route preparation. A substituted policy stamp
or changed IDs/audit/review state does not unlock those consumers. The bundle and its source
files must remain available locally; an isolated report is insufficient. Supplied human
reviews retain the native review trust boundary; replay does not certify the reviewer.
Score/mask formulas are unchanged. Identity eligibility proves neither coordinates nor
route feasibility. See the [CLI guide](../../backend/evaluation/README.md#intake-and-identity)
and [dated acceptance](../records/evaluation/routes.md#v0-identity-adoption-acceptance-2026-10-05).

### Historical uniform LLM identity judgment

Accepted 2026-10-05 under [Issue #72](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/72).
Explicit `resolve_llm_identities(intake, evidence, *, model_result=None)` uses
`association_policy_version=llm_identity_judgment_2` for every V0-V3 primary visit,
relevant REQUIRED/EXCLUDED/fixed-time subject, and available V3 optional projection.
High-impact metadata remains descriptive. No reference requires human identity confirmation
or sampling. Planner behavior, score formulas and unrelated human quality tasks are unchanged.

`prepare_identity_judgment(intake, evidence, *, model, historical=True)` returns an immutable
`rtpeval_identity_judgment_packet_1` with the complete source-bound request and short-ID map.
Cases contain original name/title, destination, location and claimed ID, independent
candidates, supplied provider observations and source references. Equal IDs are deduplicated
for selection while conflicting observations remain visible. The caller supplies an explicit
model. The request uses no tools and a strict `IdentityJudgments` output schema. Preparing a
packet does not execute a model/provider. Planner claims and provider rank are not evidence.

Supply a saved `rtpeval_identity_model_result_1` envelope with `packet`, offset-aware
`requested_at`/`retrieved_at`, `response` and `response_sha256`. Its packet must exactly equal
fresh preparation for the current intake/evidence/model. The response must be completed,
have a nonempty ID and matching model, and have exactly one assistant `output_text` in
message/reasoning output; tool output is rejected. The response digest is
`canonical_digest(response)`. These supplied receipts support reproducibility, not
cryptographic proof of a send or model accuracy. New paid collection requires authorization.

Every decision contains `reference_id`, `decision` (`match`, `unknown`, `no_supported_match`),
`candidate_id`, nonempty `rationale`, `evidence_fields`, `address_assessment` and
`destination_assessment`. Exact short-ID restoration requires complete unique reference
coverage and per-reference candidate ownership. Address assessments are `equivalent`,
`different_precision`, `incorrect_claim`, `different_place`, `unknown` and `not_supplied`.
Destination assessments are `consistent`, `contradictory` and `unknown`. Only a `match` with
a consistent destination and an `equivalent`, `different_precision` or `not_supplied`
address assessment adopts. `not_supplied` must agree with the absence of an original location.
Under the user's subsequent 2026-10-05 clarification, both `incorrect_claim` (recognizable
intended venue, wrong submitted address) and `different_place` are delivered-claim failures.
They receive `grounding_verdict=FAIL`, an unresolved identity and a null canonical ID;
recognizing an intended venue must not provide corrected addresses, coordinates or downstream
route endpoints. Evidence insufficiency remains `UNKNOWN`. The same rule applies to V0-V3,
without presuming that any particular version must fail. Geographic meaning is judged by the
LLM; structural checks cannot guarantee semantic correctness. Opening/route evidence is still
independently needed. Score arithmetic, denominators and planner outputs are unchanged.

Every match cites `claim.place_name`, `claim.destination`, `candidate.display_name` and
`candidate.formatted_address`; supplied location/ID additionally require `claim.location`
and `claim.claimed_place_id`. Optional supported paths are `claim.original_title`,
`candidate.address_components` and `candidate.observations`. Every address failure additionally
requires original name, destination and location plus independent candidate name/address
citations. A failure without a selected candidate instead cites nonempty `case.candidates`,
the complete supplied independent set. Unsupported or insufficient failure support rejects
the import; it does not establish FAIL. Unsupported/empty citations,
malformed cited components (including non-string optional `shortText`), foreign/partial
decisions, stale packets and response-hash
changes reject material without partial adoption. Unknown/no-match and contradictory
assessments retain unresolved identities and their denominators. A missing result never
enables automatic name matching or a human fallback.

Reports retain `grounding_verdict` (`PASS`, `FAIL`, `UNKNOWN`), original claims, model judgments
and saved provenance; adopted records retain `decision_route=llm_judgment`. Claimed-ID
association can remain diagnostic against a selected candidate without adopting that ID.
`review_queue` and review histories are empty; `review_hash` and `audit_plan_hash`
are null and no human audit is selected. `judgment_queue` describes unresolved references,
not a retry instruction or human workload, and contains only UNKNOWN references. Confirmed
address failures are completed judgments, never automatic repair/retry requests. Status is
`complete` when no UNKNOWN references remain, otherwise `needs_model_judgment`; complete
processing can include FAIL. Consumers replay `identity_llm_replay` against the current
intake and require exact report equality before coordinates, evidence, schedule, quality
and routes. Substituting an earlier policy stamp cannot bypass replay. Policy 1 packets/reports
cannot establish current-policy judgments; historical files remain unchanged and require their
original code revision for reproduction. V0 route-request packages
also bind the original snapshot evidence. Schema/packet fingerprints identify this policy.

The V0 bundle resolver `resolve_v0_identities(intake, bundle_path, *, model_result=None)` verifies the
source-linked V0 material before applying version-specific dispatch. The historical proposal
response is not reinterpreted as a new-schema judgment. All identity CLIs support
`--prepare --model MODEL` and `--model-result FILE` without live execution; add
`--historical-llm` only for an explicitly selected uniform historical replay.

<a id="snapshots"></a>

## Request planning, injected acquisition and immutable replay

`build_identity_plan(intake, paired=False)` selects all final primary visits and relevant requirement subjects, plus available V3 optional projections when paired is requested. It creates independent name-search requests (page size 20, original destination/location retained) and supplied-ID details requests. Search is collected for supplied IDs too; rank never establishes identity. Missing names/malformed IDs remain explicit blocked reference entries. Original occurrences are never deduplicated, only identical request descriptors.

`build_evidence_plan(intake, identity_report, route_contexts, paired=False)` validates
report/source linkage and deduplicates Details requests for independently associated
venues (canonical adoption under historical policies). Every source occurrence remains
explicit, including physically unavailable references. Every candidate leg is inventoried;
missing route contexts remain pending. Explicit contexts identify source-reference endpoints
and retain mode, aware departure or explicit time-independent basis, routing options and
independently prepared coordinates with evidence hashes. API endpoint IDs must match the
verified physical associations. This records supplied context without certifying externally
prepared coordinates. Ticket 07 owns applicability; Ticket 04 never shifts dates.

Requests have canonical-JSON SHA-256 keys over operation and complete parameters. Route keys preserve direction, identities, coordinates/provenance, mode, departure context and routing options. Only necessary one-origin/one-destination matrix requests are emitted; there is no Cartesian union matrix. Requested matrix elements count each actual send, including retries.

`acquire_snapshot(plan, directory, transport, policy)` requires a fresh directory and an explicitly supplied async transport. This primitive provides operation/parameters and does not own credentials or URLs. Formal `evaluation_run` execution supplies the network transport under the approved preparation and limits described above. The transport returns status_code and exact response bytes. A transport failure is represented by a typed safe code; exception messages and credential headers are not persisted.

Policy requires an explicit positive max_sends, max_attempts (default 2), timeout_seconds (default 20), retry_delay_seconds (default 1). Sequential acquisition uses deterministic sorted request keys. Only transport failures/timeouts, HTTP 429 and HTTP 5xx are retried within both bounds. All attempts, errors, UTC request/retrieval times and raw response hashes are preserved. Malformed JSON and missing matrix elements are not silently retried or converted to no-route. Budget exhaustion records every remaining request as unavailable. Retry success does not erase earlier attempts.

The snapshot is an evaluation-owned immutable collection interval, not a simultaneous observation. Deduplication is per plan/snapshot; reruns require a new directory and snapshot. A versioned manifest is published last using exclusive creation. Interrupted directories without a manifest are not replayable. There is no planner cache access, cross-snapshot stale reuse, retention promise, or automatic resume.

`load_snapshot(directory, expected_plan=None)` validates schema, keys, raw response hashes, safe relative paths and required request coverage; it replays without transport access. It returns raw observations plus normalized summaries with original values intact. Failure/partial records remain in coverage; corrupt artifacts fail replay rather than shrinking it. Replay is deterministic and uses stored timestamps. Provider response bytes remain separate from derived JSON summaries.

`identity_evidence(snapshot)` creates the existing identity envelope with source-linked per-reference records, requested IDs/query/page size and actual raw search count. Malformed search candidates remain represented so Ticket 03 can block acceptance. Raw response files and hashes remain auditable via observation references. Details retain timezone/current/regular hours and coordinates in snapshot raw data for later tickets; no opening verdict is computed.

The [snapshot-coordinate bridge](0004-opening-routes.md#accepted-snapshot-coordinate-extension-2026-10-03)
reads linked raw identity-snapshot coordinates after verified physical association
(or canonical adoption under explicitly historical policies). The identity
wire remains unchanged; coordinate extraction preserves separate provenance and uncertainty.
This removes duplicate preparation when existing evidence suffices, without live acquisition.

Matrix summaries require a unique expected (0,0) element and preserve raw duration strings, status, condition and fallback. Missing/duplicate/unexpected indices are explicit incomplete evidence, not no-route or a substitute estimate. This slice does not compute Routes/opening/requirement verdicts or parse durations into rounded planner DTOs.

Oracle acquisition has a separate snapshot ledger (namespace=oracle), actual transport invocations, retries, requested matrix elements and within-snapshot request deduplication. It is not added to planner usage and makes no billing/delivery claim. Exact planner-to-oracle lag is unavailable without independently supplied planner timestamps; absence is explicit rather than invented.

`route_contexts` is an array; CLI input wraps it in `{"contexts": [...]}`. Each entry has `leg_id` from the evidence plan's leg inventory, `source_kind=independent_evaluation_context`, `mode` (WALK/TRANSIT/DRIVE), `departure`, `time_basis` (explicit_departure/time_independent), `origin`, `destination`, and `routing_options`. An explicit departure is offset-aware and preserved verbatim. Time-independent queries require null departure. Both endpoints contain exactly `place_id`, finite latitude/longitude, and a 64-character lowercase `evidence_sha256`. Options are restricted to routing_preference, avoid_tolls, avoid_highways, avoid_ferries, language_code and region_code. The transport integration owns provider support validation; an unsupported context returns a recorded failure, never a silently altered date/mode. Required context metadata and allowed parameter fields are validated before dispatch.

Replay validates UTC collection/attempt timestamps and their ordering as well as raw hashes, summaries, request coverage and derived ledger totals. A corrupt timestamp cannot reach the identity bridge as apparently valid evidence. Supplied identity reports must match intake source hashes and all original identity source records. These hashes provide integrity/linkage against the supplied plan and raw files, not cryptographic proof of an external acquisition. The caller must retain a trusted plan/manifest artifact hash when stronger external provenance verification is required.

The identity bridge additionally retains raw typed address components under the current
association policy. It does not normalize them into manufactured evidence. Query/response
applicability belongs to [opening/routes](0004-opening-routes.md). Formal automatic execution
supplies the Google client and per-run raw capture. Credentials and a new live execution
allowance remain caller-owned.

<a id="usage"></a>

## Opt-in usage capture and resource reporting

V0 returns no symmetric usage trace. Shared V1-V3 budget summaries contain useful counters but do not guarantee billing or physical sends. Primary Foundry calls return usage through LangChain callbacks; requirements also retain last_call_metadata, which is not safe as a concurrent global collector. Semantic/nomination/Repair calls already have per-call callbacks. Official search/reasoning use direct Responses SDK calls. Retrieval embedding uses its own SDK client and existing request hooks. These require complementary observation seams, not summation of historical trace totals.

A benchmark-owned caller invokes capture_attempt around its existing selected-version invocation and owned-client cleanup. Evaluation intake/scoring never calls that function to run planners. Dependency construction included inside invoke is timed; construction performed beforehand is explicitly outside this scope. The caller must use the same invocation boundary for all versions. Existing PlannerRuntime.run includes owned cleanup; direct runners with caller-owned clients require the cleanup callable. CLI scripts and production APIs do not automatically enable capture.

Capture is opt-in and request-local. It neither changes prompts, retries, timeouts, budgets nor adopts planner judgments. Existing observed stage decorators provide inclusive stage spans; unobserved stages remain unattributed. Structured generation includes V0/shared structured calls; requirements use their own nested stage. Repair/repair_round ancestry marks a subset with round IDs. Stage times are not summed into outer latency.

- Model events: unique LangChain run IDs for chat callbacks; unique SDK invocation IDs for official reasoning/search and embedding. Provider-returned input/output/total tokens are preserved; total may be derived only from both known components. Missing usage is null, including failures. Embedding prompt/total usage is retained without inventing output tokens.
- Provider transport events: one event per actual HTTP transport entry on instrumented clients, including repeated sends. Counts do not prove successful delivery, paid requests, or billable matrix elements. Matrix requested elements are observed from request cardinality, never provider billing. The same `provider_events` collection can also retain SDK tool billing observations explicitly marked `source="sdk_output_tool_calls"`; these are excluded from every HTTP send/response metric and remain available to cost accounting.
- Response hooks record HTTP status. An attempt with no response remains incomplete; outer failure/cancellation is recorded separately, without inventing a server status. Response latency measures time to response hook, not full parsing time.
- Cache events: get_or_create cache reuse is separate from lookup hits (which may merely inspect availability). Neither implies a saved API call; cache keys and request content are not persisted.
- Retry attempts are distinct transport events; no guessed retry cause or grouping is derived from identical URLs. Current default SDKs disable automatic retries. Internal provider web-search operations and model reasoning are not equated with application HTTP sends.

Only allowlisted numeric/identity/status metadata is retained. No prompts, user text, result contents, URLs, credentials, request bodies, response bodies or exception messages are stored in usage. Model/config names are metadata; errors retain type only. Existing trace callbacks are not replayed or added to event totals.

Envelope schema is rtpeval_usage_1 with group_id, run_id, version, namespace, exact result_sha256, timing, model_calls, provider_events, cache_events, stage_summaries, repair_summary, coverage, missing_fields and diagnostics. A caller-supplied serializer must return the exact bytes later saved as result; capture stops its clock before serialization and sink work. Failed attempts have no adopted result hash. Failure envelopes are retained by benchmark construction, not made into qualified batches.

namespace separates planner and oracle ledgers. Nested capture is rejected to avoid double counting. Concurrent attempts use isolated contexts. Exceptions/cancellation and cleanup are preserved; a cleanup error does not replace an existing primary error. Sink failure is reported on the supplied ledger's diagnostics and does not turn a successful planner result into failure. The producer must check that a valid usage artifact was actually saved before handoff.

Default adapter coverage is unverified: custom injected clients may bypass all hooks. A producer using the checked, instrumented default adapter paths may explicitly declare default_adapters. This is a recorded collection configuration, not inferred from zero observed calls. Unverified capture reports observed subtotals and unavailable whole-run counts/tokens, never false zero. It does not establish capture coverage for arbitrary new adapters.

Available/partial collection requires explicit `model_calls`, `provider_events` and
`cache_events` arrays; empty differs from absent/null. Unavailable envelopes can omit them,
but present collections must be arrays. Each collection rejects duplicate event IDs.
Repair token subtotal is null when no referenced event has observed token usage; measured
zero remains zero, and a partial subtotal does not become a complete total.

Each selected group/version retains elapsed scope/outcome, complete comparable totals where supported, observed token subtotal, missing-token call count, observed HTTP sends, cache reuse versus lookup counts and Repair event subsets. Resource reports are separate from quality scoring and human blind tasks. Duplicate selected versions or event IDs are rejected rather than silently double-weighted.

Within-request comparisons give absolute difference and candidate/baseline ratio only for compatible namespace/outcome and, for latency, the same selected-invocation-through-cleanup boundary. Zero baselines have a difference but no ratio; missing observations remain unavailable. Descriptive medians include available counts and separate namespace/outcome/scope cohorts; the request rows remain available. There is no efficiency score, PASS threshold, inferential test, cost conversion or claim that lower usage is better quality.

## Code, commands and acceptance

Implementation owners: [intake](../../backend/evaluation/intake.py),
[projection](../../backend/evaluation/projection.py), [identity](../../backend/evaluation/identity.py),
[snapshot](../../backend/evaluation/snapshot.py) and [usage](../../backend/app/observability/usage.py).
[Package commands](../../backend/evaluation/README.md) describe invocation and exits.
[Intake/identity/usage records](../records/evaluation/intake-identity-usage.md) preserve executed
checks, earlier conservative rules, corrections and the ordinary-output acceptance.
Original plans remain in [parent #12](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12)
and Tickets [01](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/13),
[02](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/14),
[03](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/15),
[04](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/16).
Earlier title-equivalence/equal-transport-authority restrictions are not current rules.

<a id="offline-cost-accounting"></a>

## Offline cost accounting

[Issue #59](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/59) supplements
completed usage Ticket 02. `build_cost_report` and `python -m
backend.evaluation.cost_report` read one or more saved envelopes and optional verified
native oracle snapshots. They do not require a four-version comparison, invoke planners,
fetch bills/prices or contact providers. Capture remains opt-in; planning behavior and
quality scores are unchanged.

Optional numeric capture retains SDK/LangChain cached-input, cache-write and reasoning
token details, with allowlisted numeric originals in `usage_details`.
Reasoning is already included in output tokens; it is not added to the total again.
Google HTTP observations retain only bounded Places endpoint/field mask and route
mode/routing preference, alongside requested matrix elements. Unique active model
invocations can supply exact backing-HTTP event/provider bindings. SDK web-search output can
retain numeric tool-call counts separately from model usage, as provider events marked
`source="sdk_output_tool_calls"`. These observations do not represent application HTTP
transport entries; resource reports exclude them from HTTP metrics while cost reports
retain their tool-call units. Missing details stay missing.
No prompts, query text, coordinates, URLs, keys or raw responses are added to this ledger.

`rtpeval_prices_1` has an explicit currency and unique price rows with `price_id`, source,
`as_of`, inclusive `valid_from`, exclusive `valid_until`, exact event `match`, positive
decimal-string `per` and decimal-string `rates`. Match includes kind, provider, operation
and model identity for model rows; optional exact billing context selects an explicitly
supplied SKU. Supported units are input, cached input, cache-write input, output tokens,
requests, matrix elements and observed tool calls. Cached reads and writes are partitioned out of
total input before applying their rates; their sum cannot exceed reported input.
Observed nonzero writes without a write price leave the estimate unavailable. Embeddings
can have input-only prices. Unsupported or overlapping
prices, missing counts, incomplete outcomes and out-of-scope context leave costs unpriced.
The calculator does not interpret free text to infer a SKU.

The caller supplies hashes of original usage file bytes to the library; the CLI computes
them itself. Optional historical annotations bind exact usage SHA-256, event kind/ID,
source SHA-256, source reference and explanation. The research reader requires an
object-valued `fields` and object-valued supplied `billing_context` in annotations
or observed events before native rebuilding; omitted context remains missing.
Annotations can supplement missing billing context or an explicitly stated cache
assumption, but cannot overwrite observations or
replace status, model identity, input/output tokens or artifact lineage. An assumption is
retained beside the estimate rather than becoming observed provider data. An explicit
unit-rate scenario may use a price row's `assumption`; it is not confirmed SKU evidence.

Normalized bill import is a JSON array. Every row has a unique `bill_id`, `scope`,
`currency`, decimal-string `amount` and `source`. Event rows additionally bind
`usage_sha256`, `result_sha256`, `kind` and `event_id`; run rows bind the artifact hashes
and require `complete: true`. Event actuals supersede estimates for best-available
accounting. Complete run actuals do not invent category/Repair allocation. Event and run
bills cannot overlap, and a model's backing HTTP bill must bind its model event or run.
Aggregate account/resource/month rows remain unallocated and retain their own currencies;
no proportional allocation or implicit FX occurs. Vendor exports must be normalized
according to their real scope, not assigned event IDs without evidence.

`rtpeval_cost_report_1` distinguishes actual, estimated and best-available values, observed
subtotals and complete totals; unpriced components and unverified adapter coverage prevent
a complete estimate. Totals describe observed instrumented adapters only. Models,
embeddings and API categories remain separate; Repair is a subset, never an additional
charge. Successful explicitly linked model backing HTTP sends are transport observations
rather than additional charges. Failed, incomplete, unlinked or mismatched backing sends
retain uncertainty; legacy envelopes without links cannot acquire a complete total merely
because model usage exists. Independent oracle snapshots are separate shared runs, not assigned
to planner versions. Verified raw hashes, actual attempts (including failures/retries) and
duplicate-capture checks protect native snapshot replay. Output cannot overwrite inputs
or any material inside an imported snapshot.

Retail estimates exclude account credits, free caps, volume discounts and tax. No supplied
bill means actual amounts remain unavailable. The user explicitly selected OpenAI official
GPT-6 Luna pricing for this task's Foundry estimates; that proxy is a documented assumption,
not a claim about Azure charges. Current-source prices used retrospectively and missing
cache/service-tier details must be stated. The [package guide](../../backend/evaluation/README.md#offline-cost-report)
contains runnable import examples; dated acceptance belongs to the existing
[usage record](../records/evaluation/intake-identity-usage.md#offline-cost-acceptance-2026-10-05).

### Selected-version usage preparation and capture

`backend.evaluation.tools.planner_usage_cli` prepares a one-use output directory with
original input/configuration bytes, the effective runtime policy/digest, source revision,
trusted current date, run identity and dated price basis. Preparation constructs no
provider runtime and sends no request. `--execute` selects the existing
`RequestPlannerRuntime` for one V0, V1, V2 or V3 invocation; live authorization remains
owned by the current-session smoke policy. The runtime retains configured timeouts,
version behavior and dependency cleanup. Execution loads the repository `.env` (or
`--env-file`) after the optional RAG environment; process values take precedence, then
RAG values, then base values. Preparation reads neither credential file, and values are
not serialized. This interface adds no spend reservation guard.

Completed execution saves exact serialized result bytes, `rtpeval_usage_1`,
`rtpeval_provenance_1`, usage summary, `rtpeval_prices_1` and cost report. Result version
and original structured trip facts must match before a result hash can be adopted.
Failed/cancelled execution keeps observed usage and a cost report, with error type only
and no adopted result. Output reuse is rejected. Injected clients retain unverified
coverage; the checked default adapters are explicitly declared in the envelope.

`reference_prices` binds dated official unit rates to saved event identity and observed
billing context. GPT-6 Luna and `text-embedding-3-small` use exact known model identities;
unknown deployments remain unpriced. GPT-6 Luna input above 272,000 tokens applies the
published long-context multipliers. Known Places masks select the highest requested
supported SKU; unknown fields or wildcard masks remain unpriced. Matrix prices use
observed mode/routing preference and actual requested element counts. Retail references
exclude account discounts, free quota, tax and credits. Foundry estimates explicitly use
OpenAI prices as a proxy. Public HTML/noncommercial Open-Meteo use a declared free-use
scenario. Search-content token cost is covered only insofar as provider usage reports it.

A model price row may set `unreported_cache_policy="uncached_write_rate"` with input,
read and write rates; the write rate must be at least the ordinary rate. Missing cache
reads then assume no discount, and missing writes price all non-read input at the write
rate. Pricing records assumed billable units and explanations, while usage retains
missingness. Without this policy or a supported source annotation, missing quantities
remain unpriced. These are estimates; account invoices and cache observations remain
separate evidence.

Default capture covers usage and original result/configuration lineage. The opt-in
generation evidence extension below connects raw provider, query-vector and mechanism
observations. Producer completion and qualified four-version intake retain their existing
separate requirements. This command performs no independent
evaluator acquisition or quality scoring. Its preparation/capture output cannot attest
a completed four-version batch. Runnable instructions belong to the
[package guide](../../backend/evaluation/README.md#planner-usage-capture-cli).

<a id="planner-generation-evidence"></a>

### Opt-in generation evidence

`--capture-evidence` records evidence intent during offline preparation and enables capture
only with explicit execution. Existing mechanism observations, a RAW local run tracer,
owned HTTP usage hooks and retrieval query vectors share the selected invocation. These
observers add no requests, retries or planner decisions. Usage timing stops after invocation
and cleanup, before final mechanism/raw serialization and inventory writes.

`mechanism.json` uses `rtpeval_mechanism_capture_1`; accepted catalog, prepared/submitted
model observations and actual V3 rule selection retain their existing semantics and
missingness. `evidence/trace/` captures local LLM/tool/evidence payloads, retaining
runner-owned completion and tool usage rather than replacing them with CLI defaults.

`evidence/wire/` contains credential-filtered UTF-8 representations; JSON bodies are
normalized objects. Safe metadata includes method, filtered URL/allowlisted headers,
provider status, the original usage HTTP event ID, body form/status and observed-body
SHA-256. Known credentials from the environment, request metadata and labelled JSON fields
are filtered, including unlabelled echoes, duplicate sensitive query parameters and
individual Cookie values. Credential files and Authorization/Cookie headers are excluded.

Streaming follows normal consumption without draining unread bodies. Decoded SDK content
includes normally consumed gzip responses; direct raw HTML streams retain their normally
read bytes. Unsupported encoding, non-UTF-8 content, unread/interrupted streams and bodies
above 10 MB retain explicit missingness without an unsafe preview. The observed digest
identifies the recorded body form, which may differ from physical encoded wire bytes.
Stored artifacts have their own exact-byte hashes after filtering. Trace payload capacity
uses the configured trace limit; truncation remains partial evidence.

`evidence/vectors/` uses existing normalized float32 NPZ capture with space/corpus metadata,
text digests, vector digest and shape. It adds no embedding or DB request. Existing explicit
capture directories take precedence; the ambient directory resets after execution. A failed
vector write preserves planning and reports missing vectors for completed embedding calls.
The index counts only bundles that load without pickle and pass metadata/space, shape,
dtype, finiteness, normalization and vector-digest checks. Partial files remain inventoried
but cannot establish capture coverage.

`rtpeval_generation_evidence_1` in `evidence-index.json` binds original input, exact result,
policy, source revision and run identity to saved file digests, HTTP events, diagnostics and
collection status. The index excludes itself, provenance and mutable manifest to avoid
hash cycles; provenance binds the index and mechanism file hashes. Invocation failures and
cancellation retain observed evidence without an adopted result. Optional evidence failures
do not replace planner outcomes; a missing usage file exits as capture failure while retaining
an available original result and index. Injected coverage stays unverified.
Trace payloads may be objects, lists or other valid JSON values. Malformed/unreadable
JSON and unreadable files remain unavailable inventory units rather than interrupting
successful planner completion; readable malformed files retain their exact hashes.

Available local evidence is distinct from producer completion, independent source review,
qualified four-version intake, quality PASS and actual billing. Storage limits are capture
capacity, not a spending guard. Live dispatch still requires the prepared, explicitly
approved [smoke handoff](../agents/smoke-tests.md), and performs no independent evaluation.

### Selected-generation opportunity capture

Installed `rtpeval generate` and its native usage CLI accept default-off
`--opportunity-capture PATH` for V1/V2. Preparation records only
`opportunity_capture_requested=true`; candidate observations require execution.
V0/V3 reject the option before preparation. The destination must not collide with
input/configuration sources, generation-owned files or the evidence directory.

The dispatcher forwards `opportunity_capture_path` and explicit
`opportunity_capture_run_id` to the existing passive exporter. Capture `run_id`
equals the selected usage/registration run ID; the local trace retains its separate
UUID. Independent runner callers may omit the override and retain trace-based identity.
The existing `rtpeval_candidate_capture_1` schema and stage statuses remain unchanged.

After execution, the capture manifest records `opportunity_capture_ref` with a
path relative to the output on the same volume, exact-byte SHA-256, schema, media
type and availability. Existing
destinations, absent/unreadable exports and run/version mismatches remain unavailable
with a reason; sidecar failure does not change the Planner outcome. Partial or failed
captures can be available files without complete stages or a final result.
The same manifest retains original input/configuration hashes and an available final
result hash. Registration follows this reference and preserves sidecar bytes/layout
within the selection's reference root, including captures outside the output directory
but inside that root. Cross-volume exports retain an absolute path and must be kept
separately; they cannot provide a relative registration dependency.

Registration does not create an attempt census or declare research completeness.
The caller separately binds the selected attempt, original input, exact configuration,
available result (or explicit null) and capture reference in the
[opportunity declaration](0001-evaluation-artifacts.md#canonical-candidate-opportunity-observations).
Research readers retain source-hash, run/version and final semantic-hash checks.
Capture adds no provider requests, prompt changes, selection or quality judgments.

## Producer material handoff

The installed producer flow uses `rtpeval_collection_1` configuration and
`rtpeval_staging_1` staging independently of native `rtpeval_batch_1` intake. Explicit
batch/revision/time/policy fields, ordered groups and selected run IDs own selection.
No newest/best selection, replacement, retries, generation or cohort reduction occurs.
All references resolve relative to their declaring artifact's root and must remain
within it. Required source artifacts use exact byte SHA-256, JSON media type,
`availability=available` and the applicable envelope schema. Input, result, usage,
provenance and optional generation evidence retain exact bytes and relative layout.
Generation evidence remains producer evidence, not independent evaluator ground truth.

A group declares its original `input_ref` and `selected_runs` keyed by V0-V3. Each
existing run supplies result/usage/provenance refs and completion. Missing result/usage
may be retained as blocked material; a no-result producer provenance records
`result_sha256=null`. Missing provenance requires a traceable source-bound
`rtpeval_provenance_1` `producer_declaration`, with actual declarer/time/rationale;
it cannot coexist with `provenance_ref` or be inferred from filenames.
Explicit unavailable usage uses the existing usage envelope and remains unavailable.

Completion declares `declared_by`, `declared_at`, `policy_ref`, `workflow_status` and
`required_mechanisms`. The policy must match `qualification_policy_ref` and the workflow
must be completed. Required generation is completed for every version; retrieval is
completed for V2/V3; validation is completed and Repair completed/not-applicable for V3.
Any additional required mechanism must also complete. A normally finished V3 may qualify
with partial/rejected/skipped Repair, retained draft or unresolved internal findings.
Whole-workflow failure/cancellation/timeout, required retrieval failure/degraded fallback,
validation failure and failed new usage capture do not automatically qualify.
Completion is distinct from exit 0, file existence, quality/PASS, `policy_completion`
and Repair acceptance. Native intake consumes producer qualification; it does not rerun
Planner or independently select/requalify the cohort.

Selected generation may declare pending slots with only `run_id` and `capture_directory`.
The chosen version/group/run/output must exactly match one slot; explicit registration
requires execution and a fresh destination. Observed required workflows use fixed
`selected_workflow_1`, binding exact native provenance/manifest, completion and original
operator selection snapshots. An unrelated operator policy remains unchanged and blocks
with `completion_policy_mismatch`. Normally completed bounded partial entity resolution
can qualify; unavailable/deadline-limited retrieval cannot. Other declared slots remain
selected, including unstarted attempts. Planner invocation and registration statuses are
separate; registration failure does not replace a successful Planner result.

Staging always has `qualified_four_version_batch=false` and
`pending_requirement_review=true`. Its `incomplete`, `blocked` or `pending_review`
status reports missing versions/material or completion blockers. Successful collection
can exit 0 without qualification. Saved source/config bindings and reconstructed
metadata protect both originals and copied files against drift. Original source and
selection/capture/config files must remain accessible and unchanged through finalization.
No collection or finalization step loads credentials or constructs an online runtime.

## External requirements handoff

`rtpeval_requirement_handoff_1` explicitly declares batch identity and ordered groups
matching staging. Each group binds original `input_ref`, final `requirement_spec_ref`,
`authoring_ref`, `review_ref` and normally `authored_requirement_spec_ref`. The latter
may be omitted only when the exact final artifact was accurately the author output.
Native specs remain `rtpeval_requirements_1`; author/review record artifacts use
`rtpeval_requirement_agent_execution_1`.

External author and reviewer are separately operated Codex `gpt-6.1-sol` with reasoning
effort `high`. Requirements derive from the complete original request, excluding Planner
interpretation, generated outputs, scores and mechanisms. Explicit obligations, soft
preferences and unresolved meaning retain native source-reference rules; review does
not invent quotas. The CLI does not launch/message an agent, author/review requirements
or replace this work with model requests. Agent review is not human review. This external
configuration does not change Planner/evaluator model settings.

Each execution record contains `operation=authoring|review`, `origin=external_codex`,
actual `actor_ref` and `execution_id`, `group_id`, exact `input_sha256` and output
`requirement_spec_sha256`, offset-aware `started_at/completed_at`, configuration with
`agent=Codex`, `model=gpt-6.1-sol`, `reasoning_effort=high`, and context with
`source=complete_original_request` and `excluded` containing exactly
`planner_interpretation`, `generated_outputs`, `scores`, `mechanisms`. Additional actual
configuration is retained. `source_input_ref` and `requirement_spec_ref` bind the complete
original request and actual output spec. Author/reviewer actor and execution identities
must differ. Each start precedes or equals completion; author completion precedes or
equals review start. Equal times can be valid at the recorded clock precision.

Review additionally binds `input_requirement_spec_ref` and
`input_requirement_spec_sha256` to the exact authored draft. The final spec's
`review.status=reviewed`, `reviewer_ref` and `reviewed_at` match reviewer actor and
completion. An author output already marked reviewed cannot record review after author
completion. The original author artifact, reviewer input and final reviewer output remain
unchanged; do not back-edit the draft or fabricate times for a same-artifact route.

`transcript_ref` binds available JSON `rtpeval_requirement_agent_transcript_1`: its
`execution` is the exact execution object excluding `transcript_ref`, and `messages`
is a nonempty array of nonempty textual messages with native system/developer/user/
assistant/tool roles. Actual transcript exports/sidecars may be retained through standard
artifact refs and are copied recursively with original layouts. A transcript bound to
old input/spec/config/time cannot be reused by changing only envelope hashes.
Offline verification establishes recorded byte/hash/configuration lineage. It cannot
authenticate a real external-agent session, message truth, semantic completeness,
independent review quality or absence of invented quotas; actual provenance and complete
original-request review remain operator responsibilities.

Attachment emits `attached_pending_finalization`. Finalization rechecks original and
copied staging/handoff sources, copies all bound material and submits a candidate native
manifest to intake. Only accepted complete four-version material publishes
`manifest.json` in a fresh directory. Native rejection leaves retained diagnostic
material without an accepted manifest; another attempt needs a different fresh destination.
A changed original request requires fresh requirements authoring/review rather than edited
hashes. Accepted standardized input does not establish a formal benchmark or research
selection policy. Runnable schema templates and parameters belong to the
[material guide](../../backend/evaluation/README.md#installed-generation-and-material-handoff).


## Research completion and selection

The separate [research population/census contract](0001-evaluation-artifacts.md#original-input-research-declarations-and-attempt-census)
retains original requests and every planned version/repetition slot. Native
qualified four-version intake still requires its existing producer completion,
reviewed requirements, result, usage, and provenance material; research census
registration neither weakens that gate nor introduces failed attempts into scoring.

An explicitly declared native mapping normalizes producer outcomes to `completed`,
`clarification_required`, `failed`, `cancelled`, `incomplete`, `unstarted`, and
`unknown_pending`. Known native statuses retain their meanings: `not_started`
maps to unstarted, `pending` to unknown/pending, and `required_mechanism_failed`
to failed. Additional producer-specific states need an explicit mapping. Completed
normalization still requires native `workflow_status=completed` and all required
mechanisms: generation for every version, retrieval for V2/V3, validation and
completed/not-applicable Repair for V3, plus completion of any additional required
mechanism. A normally finished workflow may contain quality FAIL/UNKNOWN or skipped
Repair. Missing completion declaration remains unknown, including when result and
usage files exist. Processing completion is independent of workflow completion.

Every supplied native usage envelope is validated at the common census boundary,
regardless of the selected research track. Its explicit planner namespace,
collection status, event arrays, coverage/timing objects and Repair event subsets
must remain structurally valid and source-matched. Evaluator/oracle namespaces and
explicit frozen simulation are invalid generation material. A completed producer
workflow contradicts explicitly failed, cancelled or incomplete capture usage;
required-mechanism workflow failure can coexist with completed capture usage.
Absent optional fields in a declared unavailable envelope remain valid.

An undispatched attempt may retain a source-matched unavailable usage placeholder
without model/provider/cache events, stage spans, measured invocation timing,
Repair consumption or a capture outcome implying dispatch. Empty Repair subsets
and zero observed Repair rounds describe no consumption. The placeholder remains
in the census and source inventory but is excluded from actual consumption.
Observed generation usage on an undispatched attempt requires material correction.

Primary selection uses the earliest dispatched attempt in the ordered per-slot
census. A preliminary non-dispatch declaration is not a first invocation; later
retries cannot replace a failed primary result. The optional `last_dispatched`
retry-policy view reports the last explicitly linked retry separately and never
selects by score. All-attempt inventory retains failed/cancelled usage references,
while planner-only resource semantics remain owned by [usage](#usage) and
[offline cost accounting](#offline-cost-accounting).

Population summaries retain status/reason counts and the following measures:

| Measure | Numerator / denominator and missingness |
| --- | --- |
| Planned completion | Confirmed completed selected slots / every declared planned slot. Unknown/pending slots remain unresolved. With `C` completed, `P` planned, and `U` unresolved, bounds are `C/P` and `(C+U)/P`; exact `fraction` is null until `U=0`. |
| Conditional completion | Confirmed completed first dispatches / known dispatched first attempts. Pending dispatched records remain unresolved. Missing slot records can hide additional dispatches, so `unknown_dispatch_slots` and lower/upper denominator bounds remain explicit. |
| All-four completion | Completed V0-V3 request/repetition groups / groups explicitly planned for all four. A known non-completion settles group failure; otherwise an unknown member leaves it unresolved. Partial-version plans remain not applicable with an excluded count. |
| Repetition summaries | Per-version, per-repetition, per-version/repetition, and original-request views. Repetitions are not additional unique requests. |
| Attempt census | All declared records, actual dispatches, and dispatches after the first in each slot. Unstarted declarations are records, not invocations or resource consumption. |

For conditional completion, let `D` be known first dispatches, `C` their confirmed
completions, `U` their pending/unknown outcomes, and `M` slots with no census record.
The possible dispatch denominator spans `D` through `D+M`. When `D>0`, conservative
completion bounds are `C/(D+M)` through `(C+U+M)/(D+M)`; exact fraction requires
`U=M=0`. `confirmed_fraction` describes observed completed/known-dispatched values,
not a settled full-census estimate. When `D=0`, the conditional rate and its bounds
remain unavailable, even if unknown records might conceal dispatches. Zero
all-four denominators likewise have no rate. Every fraction retains integer
numerator/denominator, units, availability, and unresolved counts.

`quality_candidate_material` reports completed selected attempts, available versus
missing result references, and non-completed/unresolved slots. It is a material
inventory with `native_qualification=not_performed`, not a qualified quality subset
or a replacement for unconditional completion. Track-specific qualified/comparable
benefit/resource subsets keep their own exclusion and source validation rules.

## Generation research tradeoffs

`rtpeval research validate|report DECLARATION --track tradeoffs` reads the declared
population and census without acquiring evidence, invoking Planner or fetching
prices/bills. `report` additionally requires a fresh `--directory`, writes
`tradeoffs.json` and `tradeoffs.md`, and preserves all source bytes. The output is
`rtpeval_research_tradeoffs_report_1`; its processing status, profile IDs,
population digest, exact-byte source bindings, measurement/review coverage and
semantic SHA-256 remain separate from workflow completion and native quality.

The optional declaration `track_refs.tradeoffs` binds a JSON
`rtpeval_research_tradeoffs_1` object. It accepts these fields:

| Field | Meaning |
| --- | --- |
| `quality_reports` | Array of saved native final-quality descriptors. Each supplies `report_ref`, `manifest_ref`, `identity_ref`, `snapshot_ref` and the native optional argument references used to build that report. The reader reloads accepted four-version intake and replays the unchanged native quality builder against saved evidence. Recomputed semantic hashes alone cannot authenticate modified scores. |
| `cost_ledgers` | Array of explicit generation accounting descriptors: unique `attempt_ids`, `prices_ref`, nonempty declared `accounting_basis`, and optional `bills_ref`, `annotations_ref`, `report_ref`. Prices remain native `rtpeval_prices_1`; bill/annotation sidecars wrap arrays in `bills`/`annotations`. Optional saved `rtpeval_cost_report_1` output must exactly equal the native reconstruction. |
| `comparisons` | Optional nonempty ordered array of `{baseline, candidate}` version pairs. Defaults are V2-minus-V1 and V3-minus-V2. Any other pair requires explicit declaration. |

All source references use the population contract's bounded exact-byte reference
format. Quality joins bind the case/revision/repetition, every selected native
run, original input and result, and supplied census usage/provenance hashes.
Cost joins use the exact census usage bytes and native bill/event/result linkage.
Foreign attempts, duplicate ledger assignments, source drift, forged saved
reports and contradictory supplied material require material correction. Missing
optional quality/cost material remains unavailable. The census continues to own
first-dispatched selection; a completed retry never replaces its failed primary.

`paired_comparisons` retains every request/repetition planned for both requested
versions, including non-completed selected attempts. `eligible`, `completed`,
`excluded`, `not_applicable_groups` and `native_quality_pairs` state distinct units.
Resource differences require completed selected workflows; elapsed differences
also require successful native usage outcomes and
`selected_invocation_through_cleanup` timing. Native final-quality rows retain
both complete per-version values, the original common dimension mask, rule profile,
coverage, density and exact score fractions. Differences subtract those existing
values; they create no new score. Descriptive medians retain comparable pair counts.

Resource rows reuse native usage summaries and adapter coverage. Input and total
tokens include observed model and embedding calls; output tokens apply to
non-embedding calls, because embeddings do not invent output observations.
Embedding calls/input/total are also reported separately. Each token view retains
known/missing call counts and observed subtotals. Missing token observations or
unverified adapter coverage produce null complete metrics. Model calls, application
HTTP sends and billable events remain different units; SDK output-tool billing
observations are excluded from application sends. Repair model/provider IDs define
subsets counted once, rather than additional consumption or a sum of inclusive spans.

Native actual, estimated and best-available money fields retain currency, dated
prices, billing coverage, event evidence, assumptions and unallocated bills.
Comparisons conservatively require matching declared accounting basis, native
scope, price bytes and price assumptions as well as currency. Best-available
comparisons additionally distinguish complete-run bills, event bills, estimates
and mixed billing bases; confirmed empty zero-event runs remain valid zero
baselines. A compatible zero baseline retains its difference with a null ratio.
Cost medians group by mode, currency, accounting basis and price hash. No shared
account charge, credit, tax or free usage is inferred.

`all_attempts` reports each dispatched attempt, its primary/retry identity,
workflow status, usage coverage and native cost separately from successful pairs.
Failed/cancelled attempts and retries contribute observed consumption. Workflow
failure can coexist with completed capture usage when a required mechanism failed;
that observation remains in the failed/censored elapsed cohort. Successful elapsed
cohorts distinguish selected primaries from retries, version and timing scope.
Usage validity and unavailable placeholder retention follow the common census
validation above.

Overall and per-version consumption have complete totals only when census dispatch
coverage and native adapter observations are complete and all required measures are
known. Otherwise observed subtotals remain explicit. Cost consumption preserves
both native event subtotals and known complete-run total subtotals, so an observed
run bill remains visible when a pending repetition prevents a complete population
total. Partial price or token detail cannot become zero expenditure.

Full `population_completion` remains alongside benefit/resource subsets. Compatible
version completion differences use every planned slot, exact fractions only when
resolved, and conservative difference bounds when pending. Different planned
populations disable a direct difference. Per-case caveats retain unequal or
unverified cache/order/concurrency/configuration/timing conditions. These are
descriptive observations with no efficiency score, causal effect or significance
claim; native four-final qualification and scoring remain unchanged.
