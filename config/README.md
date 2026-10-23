# Runtime configuration reference

`config/runtime.yaml` is the single non-secret planner runtime policy source. This document explains
its current values; it is not another default file. The tables enumerate every YAML leaf.
English names identify application policies, not measured optimal settings or user demands.

Product options, shared database connections and Foundry endpoint/deployment settings
live separately in root `product.yaml`, beside `compose.yaml`. Credentials remain in
`.env`; `scripts/run_database.py` supplies resolved database settings to Compose. See [Product setup](../docs/guides/development.md#product-account-setup-and-acceptance)
for their keys, environment overrides and credential boundary.

## Loading, versions and overrides

`runtime.config_loader` loads and validates an immutable `RuntimeConfig`. The default loader
is process-cached; an explicit `--runtime-config PATH` loads that file once. The request receives
one resolved object through runner, acquisition/factory, V3 stage, round, projection and budget.
There is no per-round YAML reload. Restart/reload before a later request to change policy.
Duplicate/unknown keys and invalid values fail explicitly. V3 fields have strict numeric/boolean
types and finite/range/relationship checks. Legacy policies without `v3_repair` can still load for
V0/V1/V2; V3 refuses a missing group. Typed Repair objects have no independent numeric defaults.
Standalone offline helpers resolve the same default YAML only when no policy is injected.

V0 uses shared local calendar/logging/trace settings and its existing model entry; it does not
acquire external travel evidence. `budget`, `acquisition`, `main_generation`, `web_evidence` and
`reference_discovery` apply to the shared V1/V2/V3 tools path. `tripworld_discovery` applies to
V2/V3 initial discovery; V1 does not initialize RAG. `v3_repair` applies only to V3 after primary
planning. Product version selection and primary prompts/K are unchanged.

The V3 CLI supports `--repair-quantity-review` and `--no-repair-quantity-review`; an explicit
flag overrides YAML, absence retains YAML. No other Repair CLI or environment budget overrides
are introduced. `--development-timeout-seconds` remains explicit, positive, and bounded by
`development_timeout_seconds`; YAML alone never grants 600 seconds. V3 counts from request
entry before dependency assembly. Existing `--reference-date`, input arguments and
`--runtime-config` responsibilities are unchanged. `--rag-env-file` supplies the existing
RAG environment with override disabled. Provider credentials remain in environment settings; deployment defaults come from
root `product.yaml` with environment overrides. No secret values belong in either YAML
file or in this README.

`v3_request_policy` records base/effective runtime SHA-256 identifiers, review override source,
effective Repair values, shared Nearby reservation and entry deadline. Existing run configuration
snapshots remain redacted. Each round records cumulative counters and actual callback usage;
missing usage is empty/unavailable, not an offline estimate. Per-round callbacks are additive to
an existing outer usage callback. Do not add per-round totals to that same outer total twice.

## Counting, timing and invariants

Repair acquisition allowances are **stage totals, never multiplied by the round count**. Cache hits do not
consume new sends. Actual sent failures consume sending budget; failed pre-send reservations do
not become fictitious sends, but remain terminal attempts. Duplicate canonical processing does
not create another attempt. No phase name, round, Top-K change or failed provider call authorizes
hidden retries. The success cache and failure ledger survive every round. Zero acquisition
allowances stop that class of work; other existing materials may still support a model attempt.

At most one proposal model call occurs per round. An explanation over 240 Unicode characters
may use one separate batch compression call per entire stage; all overlong reasons from that
response share the batch. It does not consume or reset the six-proposal allowance. Compression
cannot change edits, identities or dispositions, and only reason-length validation errors qualify.
The original patch and returned compression remain in the bounded audit. Missing usage and actual
fees remain unavailable, while native usage/cost receipts include the separate call once.
Compression usage is already included in Repair round totals; its separate budget-summary
stage is a subset, not another charge.
More rounds can increase model usage even with unchanged tool budgets.
The 32-ID ceiling is a per-input union, not 32 additional POIs. The independent
identity ledger can be larger. Original supply and its unused count retain their original meaning.
No provider call, model explanation or policy pass changes UNKNOWN into a verified fact.
Identity, source, scope, REQUIRED/EXCLUDED, zero hidden retries and UNKNOWN semantics are contract
invariants, not configurable bypass switches. Reviews/Profile and Official Web additions remain
unsupported in Repair; their zero allowance is not an enable switch.

Repair defaults allow 420 seconds per stage, 150 per hard round, a 120-second
round reference and up to 60 seconds of preparation. With a full 420 seconds remaining,
the initial reference allocation is 140 seconds across three affordable rounds;
the six-proposal ceiling remains unchanged. Preparation leaves 30 seconds for model startup
and 20 for rechecking. Semantic calls retain their separate 45-second per-call and
120-second cumulative allowances. The 600-second development request deadline can
shorten the stage, so these settings do not guarantee six complete rounds.

Stage deadline = min(entry request deadline minus `reference_discovery.deadline_seconds`,
stage start plus stage_seconds). Nearby is reserved from its existing authoritative key, not a
second hard-coded ten seconds. Affordable rounds are bounded by remaining rounds and floor of
remaining time / round_reference_seconds. Their average allocation defines a soft reference
window for optional preparation. The hard round deadline is independently bounded by stage
deadline and round start plus round_seconds, including standalone rounds. Preparation I/O is
capped by preparation_seconds and leaves minimum_model_seconds plus recheck_reserve_seconds
inside the soft window. Cached reuse and bounded local input work may continue inside the hard
window. Local work is timed and checked after candidate preparation, route preparation, input
building and model-input projection; synchronous work is checked when it returns, not preempted.
Model timeout is min(model_seconds, hard round time remaining minus recheck_reserve_seconds),
recomputed immediately before charging and invoking the model. Insufficient minimum allocation
skips without a model charge or call. A late response with less than the recheck reserve is
rejected. Post-proposal I/O ends before finalization_reserve_seconds inside the hard deadline;
the complete synchronous revalidation is checked again before adoption. Hard timeout stops
the stage without another model send and preserves the best retained result. Unused time
remains within the same stage cap.
Compression uses at most 30 seconds and 32000 input / 8192 output tokens. Input includes
its system/user/schema and the shared Repair framing reserve. The timeout is recomputed before
dispatch from the remaining hard round/stage/request time minus the recheck reserve; no deadline
is extended. Failed attempts consume the single compression allowance. Failure, invalid or still
overlong output, insufficient time or exhausted allowance stops Repair with a specific compression
reason and retains the best result. There is no second compression or hard truncation.
Minimum model plus recheck must fit round reference, which must fit round cap, which must fit stage
cap. Model minimum must fit model maximum. Request exhaustion/cancellation stops new acquisition;
owned resource cleanup still runs. Later failure preserves the latest accepted itinerary.

Spatial kilometre/minute limits constrain automatic additions, not request execution time.
Coordinate checks are not Routes measurements. Time-applicable directed/mode-compatible Routes
can verify the minimum transfer check. Untimed WALK measurements support layout and burden but
retain future-time UNKNOWN. With no usable Routes, only the configured short WALK/default layout
fallback is allowed; obstacles/explicit unsupported transport requirements cannot be masked.
Daily burden is recomputed cumulatively against stage-original activities and identity changes.
No comparable original measurement means no credit: the conservative gross burden and missing
comparison are visible, not a claim that original travel took zero minutes. Baseline credits currently
cover insertion chains between retained adjacent original anchors. Identity replacement/deletion
without that supported comparison uses conservative gross load. REQUIRED remote visits
are not deleted by default compactness policy. The present adapter requests single-pair matrices,
so it may exhaust four calls before using 32 elements. No live WALK compatibility is claimed.

Schema ceilings below bound the approved engineering envelope, not universal provider limits.
The strict patch DTO separately caps edit count at 50. Runtime values may be lowered within
validated relationships; expanding the envelope requires an explicit code/policy change.
Quality-first keeps its existing coordinated C64/send40/K20/P8 and baseline 400/7/64 requirements;
profile/review capacity relationships and RAG query-position/token relationships still apply.
No historical compatibility field is silently repurposed as a Repair allowance.

## Current YAML values and every effective path

The unit and counting scope are described in each row. Values are copied from the current YAML;
a local documentation coverage test detects a missing path or stale value.

| Full configuration path | Current YAML value | Type / bounds | Meaning and scope |
| --- | --- | --- | --- |
| `schema_version` | `6` | integer; = 6 | Runtime loader schema discriminator; exactly 6. Not a planning version selector. Zero is invalid. |
| `input_assistance.destination.min_chars` | `2` | integer; = 2 | Minimum trimmed destination prefix length. |
| `input_assistance.destination.max_chars` | `100` | integer; = 100 | Maximum trimmed destination prefix length. |
| `input_assistance.destination.result_limit` | `5` | integer; 1..5 | Maximum normalized GeoDB suggestions per request. |
| `input_assistance.destination.timeout_seconds` | `3` | seconds; > 0, <= 3 | One GeoDB request deadline, with no retry. |
| `input_assistance.destination.minimum_interval_seconds` | `1.1` | seconds; >= 1.1 | Minimum spacing between outbound requests per process. |
| `input_assistance.destination.daily_attempts_per_process` | `100` | integer; 1..100 | UTC-day local send cap, including failed sends. |
| `input_assistance.polishing.source_max_chars` | `4000` | integer; 1..4000 | Maximum source length for optional polishing; normal planning keeps its own limit. |
| `input_assistance.polishing.source_max_tokens` | `1500` | integer; 1..1500 | Maximum source token count before any model construction. |
| `input_assistance.polishing.model_input_tokens_per_call` | `8000` | integer; 1..8000 | Prompt, context and schema estimate cap for the single draft call. |
| `input_assistance.polishing.draft_output_tokens` | `2000` | integer; 1..2000 | Maximum draft response tokens. |
| `input_assistance.polishing.call_timeout_seconds` | `20` | seconds; > 0, <= 20 | Deadline for each model call. |
| `input_assistance.polishing.total_timeout_seconds` | `40` | seconds; > 0, <= 40 | End-to-end model operation deadline. |
| `input_assistance.polishing.daily_operations_per_process` | `20` | integer; 1..20 | UTC-day admitted polishing operations per process. |
| `reference_discovery.policy_version` | `"nearby_references_1"` | string; = "nearby_references_1" | Final-primary Nearby reference contract identifier. |
| `reference_discovery.max_requests` | `3` | integer; >= 0, <= 3 | Nearby sending allowance per request, after the whole Repair stage. Zero disables the allowance. |
| `reference_discovery.max_result_count` | `10` | integer; >= 1, <= 10 | Provider result count per Nearby request. Zero is invalid. |
| `reference_discovery.radius_metres` | `800` | number; > 0, <= 800 | Nearby search radius around an actual final anchor. Zero is invalid. |
| `reference_discovery.anchor_reuse_metres` | `300` | number; >= 0, <= 300 | Maximum anchor separation for reusing a Nearby result. Zero removes the corresponding tolerance. |
| `reference_discovery.deadline_seconds` | `10` | number; > 0, <= 10 | Independent final Nearby phase cap; Repair subtracts this same value from remaining request time as its reservation. Zero is invalid. |
| `reference_discovery.request_timeout_seconds` | `4` | number; > 0, <= 4 | Per-Nearby-request timeout. Zero is invalid. |
| `reference_discovery.retries` | `0` | integer; = 0 | Fixed zero retry contract. Zero is the only supported value. |
| `reference_discovery.max_references` | `3` | integer; >= 0, <= 3 | Maximum attached references per final anchor policy. Zero disables the allowance. |
| `reference_discovery.rank_preference` | `"DISTANCE"` | string; = "DISTANCE" | Fixed provider distance ranking. |
| `reference_discovery.included_types` | `["restaurant", "cafe", "park", "museum"]` | array; schema-validated | Fixed four reference categories; changes require a reference policy contract change. |
| `app.time_zone` | `"Australia/Sydney"` | string; schema-validated | Backend trusted reference-day calendar. Existing date contract is unchanged. |
| `budget.candidates` | `64` | integer; 1..64 | Primary canonical candidate processing capacity per request, not scheduled visits. Zero is invalid. |
| `budget.final_pois` | `20` | integer; 1..20 | Maximum primary supply capacity. Duration policy selects the effective K; this does not force K20 for shorter trips. Zero is invalid. |
| `budget.places.destination_search_calls` | `1` | integer; 1..1 | Destination resolution searches per primary request. Zero is invalid. |
| `budget.places.candidate_search_calls` | `12` | integer; 1..12 | Initial candidate discovery search calls per primary request. Zero is invalid. |
| `budget.places.detail_calls` | `60` | integer; 1..60 | Shared primary Details sending allowance. Repair has a separate stage allowance and the same request cache/failure state. Zero is invalid. |
| `budget.places.review_detail_calls` | `8` | integer; 0..8 | Primary review-bearing Details allowance. Zero disables the allowance. |
| `budget.weather.calls` | `2` | integer; 0..3 | Primary weather operation allowance; Repair reuses weather. Zero disables the allowance. |
| `budget.routes.matrix_elements` | `64` | integer; 1..100 | Compatibility single-matrix counter retained in ToolBudgetLimits. Active baseline/alternative acquisition uses the dedicated counters below; it is not an extra V3 allowance. Zero is invalid. |
| `budget.routes.baseline_elements_per_request` | `64` | integer; 1..64 | Maximum actual origin count times destination count per primary baseline matrix. Zero is invalid. |
| `budget.routes.baseline_elements_per_run` | `400` | integer; 1..400 | Total directed primary baseline elements per request. Zero is invalid. |
| `budget.routes.baseline_calls` | `7` | integer; 1..7 | Primary baseline matrix calls per request. Zero is invalid. |
| `budget.routes.alternative_pairs` | `32` | integer; 0..16 | Primary alternative selected-pair capacity. Zero disables the allowance. |
| `budget.routes.alternative_matrix_calls` | `32` | integer; 0..16 | Primary alternative matrix call allowance. Zero disables the allowance. |
| `budget.routes.alternative_elements` | `64` | integer; 0..32 | Primary alternative actual matrix element allowance, including unavailable results. Zero disables the allowance. |
| `budget.web.evidence_tasks` | `8` | integer; 0..20 | Primary official-evidence tasks; not individual search tool invocations. Zero disables the allowance. |
| `budget.web.page_fetches` | `8` | integer; 0..20 | Primary page-fetch budget. Zero disables the allowance. |
| `budget.experience.review_enriched_places` | `8` | integer; 0..8 | Primary places selected for review enrichment. Zero disables the allowance. |
| `budget.experience.profile_llm_calls` | `8` | integer; 0..8 | Primary ExperienceProfile model invocations; no new profiles during Repair. Zero disables the allowance. |
| `web_evidence.reasoning_effort` | `"low"` | string; one of ["low", "medium"] | Official evidence reasoning model option, not primary or Repair reasoning. |
| `web_evidence.max_tool_calls` | `2` | integer; >= 1, <= 3 | Native web-search tool call ceiling per reasoning task. Zero is invalid. |
| `web_evidence.search_context_size` | `"low"` | string; one of ["low", "medium", "high"] | Native search response context option. |
| `web_evidence.timeout_seconds` | `20` | integer; >= 1, <= 60 | Official evidence reasoning task timeout. Zero is invalid. |
| `web_evidence.authority_domain_overrides` | `[]` | array; schema-validated | Explicit per-place, per-information-need approved domains. Empty list supplies no overrides; not credentials. |
| `web_evidence.page_retrieval.max_targets_per_need` | `2` | integer; = 2 | Page targets per official information need. Zero is invalid. |
| `web_evidence.page_retrieval.max_redirects` | `2` | integer; = 2 | Redirect hops per page request. Zero is invalid. |
| `web_evidence.page_retrieval.timeout_seconds` | `10` | integer; = 10 | Timeout per page retrieval. Zero is invalid. |
| `web_evidence.page_retrieval.max_response_bytes` | `262144` | integer; = 262144 | Maximum page response bytes. Zero is invalid. |
| `web_evidence.page_retrieval.max_text_chars` | `20000` | integer; >= 1, <= 20000 | Maximum extracted page text characters. Zero is invalid. |
| `web_evidence.claim_extraction.max_native_sources` | `3` | integer; >= 1, <= 3 | Maximum native search sources projected per extraction. Zero is invalid. |
| `web_evidence.claim_extraction.max_native_snippet_chars` | `1200` | integer; >= 1, <= 1200 | Characters retained per native search snippet. Zero is invalid. |
| `web_evidence.claim_extraction.max_candidates_per_call` | `3` | integer; >= 1, <= 3 | Structured claim candidates per extraction call. Zero is invalid. |
| `web_evidence.claim_extraction.max_calls_per_need` | `3` | integer; = 3 | Extraction call allowance per information need. Zero is invalid. |
| `web_evidence.claim_extraction.max_extraction_output_units` | `1200` | integer; >= 1, <= 1200 | Extraction output-unit protection, separate from Repair tokens. Zero is invalid. |
| `logging.level` | `"INFO"` | string; schema-validated | Minimum runtime logging level; uppercase standard value. |
| `logging.console` | `true` | boolean; schema-validated | Console logging switch; false does not disable trace files. |
| `trace.enabled` | `true` | boolean; schema-validated | Request trace switch. |
| `trace.directory` | `"logs"` | string; schema-validated | Trace output path; relative paths resolve against the repository root. |
| `trace.payload_level` | `"metadata"` | structured list; schema-validated | Trace projection mode; metadata is the current selection. |
| `trace.capture_llm` | `true` | boolean; schema-validated | LLM trace capture category, subject to payload level and byte ceiling. |
| `trace.capture_tools` | `true` | boolean; schema-validated | Tool trace capture category. |
| `trace.capture_evidence` | `true` | boolean; schema-validated | Normalized evidence trace capture category. |
| `trace.raw_provider_payloads` | `false` | boolean; schema-validated | Raw provider payload capture switch; remains false. Repair audit does not enable raw responses or internal reasoning. |
| `trace.max_payload_bytes` | `10000000` | integer; schema-validated | Per-artifact serialized UTF-8 payload threshold (10 MB, decimal). Redaction applies; oversized payloads retain an explicit truncated preview whose JSON wrapper can add bytes. Missing/truncated Repair artifacts carry explicit status. Zero is invalid. |
| `tripworld_discovery.version` | `"tripworld_runtime_1"` | string; = "tripworld_runtime_1" | RAG runtime contract identifier. |
| `tripworld_discovery.top_k` | `20` | integer; >= 1, <= 20 | Initial RAG rows per query, not Repair Top-K. Zero is invalid. |
| `tripworld_discovery.resolution_entities` | `30` | integer; >= 0, <= 30 | Primary RAG canonical resolution work allowance. Zero disables the allowance. |
| `tripworld_discovery.details_calls` | `30` | integer; >= 0, <= 30 | Primary RAG Details allowance. Zero disables the allowance. |
| `tripworld_discovery.fallback_calls` | `4` | integer; >= 0, <= 4 | Primary RAG Google fallback search allowance. Zero disables the allowance. |
| `tripworld_discovery.radius_km` | `15` | integer; = 15 | Initial destination retrieval radius; Repair derives its own target radius from v3_repair.spatial. Zero is invalid. |
| `tripworld_discovery.identity_radius_km` | `1` | integer; = 1 | Google-backed canonical identity matching radius, reused by RepairResolver. Zero is invalid. |
| `tripworld_discovery.deadline_seconds` | `360` | number; > 0, <= 360 | Initial RAG phase deadline; Repair uses its own stage and round deadlines, not this expired phase allocation. Zero is invalid. |
| `tripworld_discovery.embedding_timeout` | `8` | number; > 0, <= 8 | Per-embedding timeout, reused by Repair within its remaining stage time. Zero is invalid. |
| `tripworld_discovery.sql_timeout` | `60` | number; > 0, <= 60 | Per-retrieval timeout, reused by Repair within its remaining stage time. Zero is invalid. |
| `tripworld_discovery.connect_timeout` | `10` | number; > 0, <= 10 | Request-owned RAG database connection establishment tolerance. No independent connectivity probes. Zero is invalid. |
| `tripworld_discovery.google_timeout` | `4` | number; > 0, <= 4 | RAG Google search timeout, also reused by Repair discovery. Zero is invalid. |
| `tripworld_discovery.retries` | `0` | integer; = 0 | Fixed zero retry contract. Failed embedding texts/retrieval keys remain failed across stages/rounds. Zero is the only supported value. |
| `tripworld_discovery.max_queries` | `4` | integer; >= 1, <= 4 | Initial distinct retrieval-query allowance. Zero is invalid. |
| `tripworld_discovery.max_positions` | `80` | integer; >= 1, <= 80 | Initial query-result position processing ceiling; max_queries times top_k must fit. Zero is invalid. |
| `tripworld_discovery.total_query_tokens` | `2048` | integer; >= 1, <= 2048 | Initial query token budget; must cover max_queries times 512. Zero is invalid. |
| `acquisition.policy_id` | `"quality_first_1"` | string; one of ["conservative_1", "quality_first_1"] | Shared primary supply/acquisition policy. quality_first_1 validates the coordinated duration envelope. |
| `acquisition.details_deadline_seconds` | `120` | number; > 0, <= 120 | Primary candidate Details phase wall-clock limit; not reused as a stale Repair deadline. Zero is invalid. |
| `acquisition.details_timeout_seconds` | `20` | number; > 0, <= 20 | Primary Details call wall-clock limit. Zero is invalid. |
| `main_generation.enabled` | `true` | boolean; schema-validated | Shared primary serializer protection switch. Required by quality_first_1. |
| `main_generation.input_tokens` | `252000` | integer; >= 1, <= 252000 | Per-primary-call serialized input engineering ceiling. Zero is invalid. |
| `main_generation.output_tokens` | `16384` | integer; >= 1, <= 16384 | Per-primary-call structured output ceiling. Zero is invalid. |
| `main_generation.framing_tokens` | `2048` | integer; >= 2048, <= 2048 | Per-primary-call message framing token reserve. Zero is invalid. |
| `development_timeout_seconds` | `600` | integer; >= 1, <= 600 | Maximum permitted explicit development CLI request allowance. Presence alone does not enable this timeout; V3 requires an explicit allowance from entry. Zero is invalid. |
| `v3_repair.max_rounds` | `6` | integer; >= 1, <= 6 | Model rounds per Repair stage, shared across dates/targets. System deletions use their own attempt ceiling. Zero is invalid. |
| `v3_repair.max_model_calls` | `6` | integer; >= 0, <= 6 | Proposal model sending ceiling per entire stage; zero disables Repair model proposals. Must not exceed max_rounds. |
| `v3_repair.max_deletion_attempts` | `12` | integer; >= 0, <= 120 | System deletion attempts per stage, separately bounded from proposal model sends and sharing stage time/provider limits. Zero disables enumeration. |
| `v3_repair.reason_compression.max_calls` | `1` | integer; >= 0, <= 1 | Separate stage-wide explanation compression attempts; zero disables compression. |
| `v3_repair.reason_compression.input_tokens` | `32000` | integer; >= 1, <= 32000 | Complete compression system/user/schema/framing input ceiling; overflow stops before dispatch. |
| `v3_repair.reason_compression.output_tokens` | `8192` | integer; >= 1, <= 8192 | Output ceiling for the single batch. |
| `v3_repair.reason_compression.timeout_seconds` | `30` | number; > 0, <= 30 | Per-call ceiling, shortened by existing hard deadlines and recheck reserve. |
| `v3_repair.quantity_review_enabled` | `true` | boolean; schema-validated | Default coverage review-target activation; CLI can explicitly disable it. It never turns NEEDS_REVIEW into CONFIRMED. |
| `v3_repair.alternatives_per_gap` | `2` | integer; >= 1 | Distinct alternatives per authorized quantity gap as a preparation reference. Fewer options may still be used. Zero is invalid. |
| `v3_repair.exploration_positions` | `2` | integer; >= 0, <= 2 | Reusable exploration positions within the same input union across the stage, not extra candidates or per-date quotas. Zero removes reserved presentation opportunities. Zero removes the corresponding tolerance. |
| `v3_repair.timing.stage_seconds` | `420` | number; > 0, <= 420 | Maximum Repair wall-clock duration, additionally bounded by entry deadline minus Nearby reservation. Zero is invalid. |
| `v3_repair.timing.round_seconds` | `150` | number; > 0, <= 150 | Maximum wall-clock allocation for one candidate/model/recheck round. Zero is invalid. |
| `v3_repair.timing.model_seconds` | `70` | number; > 0, <= 70 | Maximum model wait per call; dynamically shortened by remaining round time minus recheck reserve. Zero is invalid. |
| `v3_repair.timing.preparation_seconds` | `60` | number; >= 0, <= 60 | Maximum optional candidate and pre-proposal route acquisition window per round. Zero disables new preparation work, not cached reuse or the model. Zero removes the corresponding tolerance. |
| `v3_repair.timing.recheck_reserve_seconds` | `20` | number; > 0 | Round time retained after model wait for route acquisition and application revalidation. Zero is invalid. |
| `v3_repair.timing.minimum_model_seconds` | `30` | number; > 0 | Minimum available model allocation required to start a call. Zero is invalid. |
| `v3_repair.timing.round_reference_seconds` | `120` | number; > 0 | Divisor used to estimate affordable remaining rounds and their soft preparation window. It does not shorten the hard model/recheck deadline or promise that many rounds. Zero is invalid. |
| `v3_repair.timing.finalization_reserve_seconds` | `1` | number; > 0 | Time withheld from post-proposal I/O for local finalization. Must be smaller than recheck reserve. Zero is invalid. |
| `v3_repair.input.input_tokens` | `252000` | integer; >= 1, <= 252000 | Per-model-call total system/user/schema/framing engineering ceiling; overflow preserves latest adopted itinerary. Zero is invalid. This application ceiling does not certify provider context capacity. |
| `v3_repair.input.output_tokens` | `16384` | integer; >= 1, <= 16384 | Per-model-call strict output limit forwarded without mutating primary client defaults. Zero is invalid. |
| `v3_repair.input.framing_tokens` | `2048` | integer; >= 1 | Per-call framing reserve included in input count; must be positive and below input_tokens. Zero is invalid. |
| `v3_repair.input.identity_capacity` | `32` | integer; >= 1, <= 32 | Per-call distinct canonical union: scheduled context plus presented additions plus other operation identities. Ledger is separate and is not serialized wholesale. Zero is invalid. |
| `v3_repair.input.activity_capacity` | `120` | integer; >= 1, <= 120 | Maximum protected plus editable itinerary activities per projection; necessary context is never truncated to pass. Zero is invalid. |
| `v3_repair.input.candidate_characters` | `12000` | integer; >= 1, <= 12000 | Maximum serialized characters per projected candidate; fail closed rather than delete facts. Zero is invalid. |
| `v3_repair.input.feedback_characters` | `12000` | integer; >= 1, <= 12000 | Maximum compact previous-round feedback characters; overflow stops iteration without rollback. Full raw history is not included. Zero is invalid. |
| `v3_repair.acquisition.google` | `6` | integer; >= 0, <= 6 | Stage-wide actual Google discovery/fallback sends; failures after send count. Zero disables the allowance. |
| `v3_repair.acquisition.fallback` | `1` | integer; >= 0, <= 1 | Stage-wide fallback subset of google; cannot exceed google. Zero disables the allowance. |
| `v3_repair.acquisition.embedding` | `1` | integer; >= 0, <= 1 | Stage-wide new query embedding batches; compatible query-vector cache hits do not consume sends. Zero disables the allowance. |
| `v3_repair.acquisition.retrieval` | `1` | integer; >= 0, <= 1 | Stage-wide new RAG retrieval sends. Zero disables the allowance. |
| `v3_repair.acquisition.canonical` | `30` | integer; >= 0, <= 30 | Stage-wide unique canonical processing attempts, including failures. Duplicate identities cannot obtain another attempt by changing round. Zero disables the allowance. |
| `v3_repair.acquisition.details` | `30` | integer; >= 0, <= 30 | Stage-wide actual Details sends; cached success does not consume sends and failure is not retried. Zero disables the allowance. |
| `v3_repair.acquisition.routes` | `24` | integer; >= 0, <= 24 | Stage-wide actual matrix requests, before and after proposals together. Zero disables the allowance. |
| `v3_repair.acquisition.elements` | `32` | integer; >= 0, <= 32 | Stage-wide actual matrix origin count times destination count; counts requested unavailable elements, not just successful returned rows. Zero disables the allowance. |
| `v3_repair.acquisition.top_k` | `10` | integer; >= 1, <= 10 | Rows per Repair RAG query and bounded Google discovery response projection. Does not create another retrieval allowance. Zero is invalid. |
| `v3_repair.acquisition.provider_timeout_seconds` | `20` | number; > 0, <= 20 | Per-Repair Details/Routes call timeout. Google/embedding/SQL timeouts reuse the existing tripworld_discovery values above. Zero is invalid. |
| `transport.walk_radius_km` | `2` | number; > 0 | Discovery/no-route coordinate filter and blank-day diameter for WALK or application nearby default. An applicable API route bypasses radius rejection, not leg/detour/daily burden checks. Zero is invalid. |
| `transport.motor_radius_km` | `5` | number; > 0 | Discovery/no-route coordinate filter and blank-day diameter for explicit DRIVE/TRANSIT. An applicable API route proceeds to leg/detour/daily burden checks. Zero is invalid. |
| `transport.max_leg_minutes` | `45` | number; > 0 | Maximum automatic-added adjacent-leg layout burden; these are itinerary minutes, not service execution seconds. Zero is invalid. |
| `v3_repair.spatial.detour_floor_km` | `1` | number; >= 0 | Floor for insertion extra-distance allowance between two retained anchors. Zero removes the corresponding tolerance. |
| `v3_repair.spatial.detour_ratio` | `0.5` | number; >= 0 | Relative insertion extra-distance allowance. Maximum allowed increment is max(detour_floor_km, ratio times original direct distance). Zero removes the corresponding tolerance. |
| `v3_repair.spatial.fallback_distance_km` | `1` | number; > 0 | Maximum adjacent straight-line distance for no-route conservative WALK/default layout; not a measured route length. Zero is invalid. |
| `v3_repair.spatial.fallback_reserve_minutes` | `45` | number; > 0 | Required no-route schedule gap and conservative burden reserve. Not a fabricated travel duration. Explicit motor-mode requirements cannot use this fallback. Zero is invalid. |
| `v3_repair.spatial.daily_added_minutes` | `90` | number; > 0 | Stage-cumulative added transport burden per day versus stage-original itinerary. Compatible measured original edges may earn credit; UNKNOWN original edges never earn invented credit. Zero is invalid. |


## A elastic-time contract interaction

A adds no new tunable defaults and does not change `runtime.yaml`. Existing
`v3_repair.spatial.fallback_reserve_minutes` remains the no-route itinerary reserve, not a
measured route duration. Fixed user intervals and already adopted transfer reservations cannot
be consumed as free time. `v3_repair.input.activity_capacity` also bounds the proposed itinerary
after application-owned placeholder splitting; `input_tokens` includes the protected-time,
lineage and residual-window projection. Overflow retains the latest adopted itinerary.

Root authorization, fixed-time provenance, historical unassessed/null semantics and atomic
rollback are invariants, not configuration switches. Shared DTO field cardinalities are contract
limits, not a second runtime budget. B/C review switches, cross-date moves and blank-day default
hours are not activated by this checkpoint. No new credentials or CLI overrides were added.


## B target and operation policy

These values are loaded once with the existing runtime snapshot. Quantity review defaults on;
overfull review defaults off. The quantity CLI override remains available. There is no optional
repetition-review flag; confirmed unauthorized repeats are automatic targets.
They change V3 post-primary authorization only, never first-generation supply or prompts.

| Configuration path | Current value | Type / units / behavior |
| --- | --- | --- |
| `v3_repair.overfull_review_enabled` | `false` | Boolean, per request. Independent maximum-count review. |
| `v3_repair.daily_main_min` | `2` | Integer, 1..5; per-date Repair coverage reference. Zero invalid. |
| `v3_repair.daily_main_max` | `5` | Integer, 1..10 and >= minimum; per-date Repair upper reference. Exactly this many is allowed. Shared generation diagnostics retain their own 2..5 generation observation. |
| `v3_repair.move_max_days` | `1` | Integer, 0..1; distance from original activity date for each explicitly scoped move. Zero disables moves. Never reset by a later round. |
| `v3_repair.blank_day_start_hour` | `9` | Integer, destination-local hour 0..23; originally empty/missing dates only. Zero means midnight, not disabled. |
| `v3_repair.blank_day_end_hour` | `18` | Integer, destination-local hour 1..24, strictly after start. 24 means next midnight; zero invalid. |

Blank windows need reliable destination timezone and assessed time protection; fixed rest wins.
Existing activity days retain their real occupancy, elastic roots and unoccupied calendar gaps,
without being clipped to the blank-day default. All B targets and conditional children share
the unchanged phase budget/deadline, cache/failure state and model-call ceiling. The obsolete
whole-stage coverage waiver field is compatibility-only and no longer grants permission.


## C confirmed operating and transfer obligations

C adds no new adjustable values or review switch. Confirmed opening/transfer targets are
independent of the optional quantity/overfull review flags. Rounds prioritize confirmed obligations and
record deferred review target IDs. All C targets and activated coverage children share the same
`v3_repair` phase totals, deadlines, identity/token ceilings and `move_max_days` boundary.
There are no new Reviews/Profile or Official Web acquisitions in Repair.

Ordinary visits use `application_default` place-hours scheduling; explicit exterior or other
scope is not overwritten. Applicable special evidence precedes structured current Places hours,
then regular weekly periods when fallback is permitted. Missing periods are not closed periods;
known special-day gaps cannot silently fall back. PASS describes adopted hours, not admission.
Directed valid WALK and basic-drive provider estimates support scheduling without an exact future
departure match. Traffic-aware/TRANSIT evidence retains exact-time checks. Provider status,
condition, direction, duration and fallback basis remain material. The no-route 1 km / 45 minute
reserve does not apply on top of an available route. These evidence semantics are contracts,
not configurable switches that bypass identity or user requirements.

Coverage regression permission for confirmed optional-visit removal names the parent, date,
trigger activities and removable canonical identities. It is not a blanket C deletion waiver.
Generated notes on changed retained/replaced activities are preserved verbatim under an explicit
historical/not-revalidated label; original notes also remain in proposal/draft audit. No text
classifier deletes risk warnings or rewrites user requirements. Notes-only changes cannot count
as arrangement improvement. These provenance/safety boundaries are not configurable bypasses.


## API evidence policy checkpoint (2026-09-24)

No numeric runtime values or CLI precedence changed. All acquisition, time, token and identity
limits above remain authoritative. The two discovery radii now apply only when no compatible
route is available, consistently in candidate preparation and proposal layout. The 45-minute leg,
insertion detour and 90-minute stage-cumulative daily burden remain enforced. Replacement edges
with the same activity IDs are compared using their actual canonical endpoints; missing original
routes receive no credit. Estimated provider minutes are itinerary burden, not runtime seconds.

Repair input remains `repair_input_2`, with projection revision `canonical_catalog_api_evidence_1`.
A canonical candidate object occurs once; operation groups carry identity references and scoped
authorizations. Catalog presence is not add permission. Selected opening/route evidence is retained
in finding audit, including unknown/invalid reasons, without raw provider tracing. This is offline
validated only; API availability and real model behavior need separately authorized live evidence.

## Historical capacity calibration (2026-09-25; superseded)

This dated record is not the current configuration; use the reference table and mixed-transport section.

Repair limits are stage-wide, shared across all rounds. Google total is 5 actual
sends; ordinary discovery is derived as `google - fallback` (4), reserving up to
1 fallback send within the total. No second configurable discovery value exists.
Zero google requires zero fallback; zero fallback removes that reservation.
Neither unused capacity nor an empty patch requires a send. Cache hits consume no
send allowance; sent failures do. Same-key failed attempts remain non-retryable.
Canonical attempts (30) remain distinct from Details sends (30), successful
identities and duplicate observations. Routes allows 6 requests but still only
32 actual matrix elements. Input union 32 and engineering ceiling 120000 are
preventive headroom; output 16384 and all time/spatial policies are unchanged.
These are engineering freeze-candidate limits, not empirically optimal settings.
Further expansion requires separate authorization. Budget denials are recorded
before adapter dispatch, separately from provider pre-send failures.

### Explicit Details allowance update (2026-09-25)

The user subsequently authorized primary Details 60, initial RAG Details 30,
and stage-wide Repair Details 30. Honolulu used historical lower allowances. quality_first_1 now reads the primary send allowance directly
from budget.places.detail_calls instead of replacing it with r_pool + 8. The
new-success target is unchanged. RAG resolution entities remain 16; Repair
canonical attempts remain 12. These independent limits may stop acquisition
before the larger Details allowance is spent. No timeout, retries, Reviews,
input capacity or acceptance policy changed. This is offline-only configuration
validation; the Honolulu live used the previous 40/20/10 values.


### Active-target locality and four-round headroom (2026-09-25)

Current limits are five stage-wide rounds/calls and 252000 engineering input tokens
per call. Output remains 16384; identity union remains 32. These values are loaded
from the same YAML snapshot, with no provider default or separate V3 config.
Five calls are an upper bound, not a promise that the shared 360-second stage
can fit five maximum-duration calls. Dynamic affordable-round allocation still
reserves 20 seconds for rechecking and requires at least 30 seconds to start a
model; model time is at most 70 seconds. Request deadline and Nearby reservation
remain authoritative. Cache/failure records and acquisition counters never reset.

Ordinary Details is owned by ToolBudget (60); initial RAG Details is owned by
TripWorldDiscovery (30); Repair Details is owned by RepairBudget (30). They share
request cache/attempt state, not an overlapping send counter. Failed sends count;
cache reuse does not. Following the explicit follow-up authorization, initial RAG
resolution entities and Repair canonical attempts are both 30. Their separate
30-send Details limits remain authoritative: fallback-assisted second Details
requests also consume that allowance. Cache reuse, failed resolution and early
supply completion mean 30 attempts do not guarantee 30 successful candidates.
Primary successful-supply targets still stop work before 60 when satisfied.

The Repair stage now allows at most 360 seconds, still bounded by the remaining
whole-request deadline minus Nearby reservation. Preparation remains at most 30
seconds per round, model at most 70, and five calls share all acquisition limits.
With 360 seconds available, the first five-round allocation is 72 seconds before
preparation; the 20-second recheck reserve leaves at most 52 for the model.
Preparation elapsed time reduces that allowance. No whole-request extension,
extra Google/Routes quota, larger input union or relaxed acceptance is implied.

CandidatePreparation.target_opportunities counts per target/date/operation;
association_edges and unique_candidate_identities are distinct concepts. The
identity_capacity_summary holds global matching capacity once, including a
separate input-only capacity. identity_free_operations records RETIME, MOVE and
DELETE without new-candidate allowances. UNKNOWN is still eligible; preparation
references and matching capacity never mean itinerary completion. Deferred review
targets cannot authorize current-round candidate acquisition or input slots.

### Authorized shared Repair allowance update (2026-09-25)

The current stage permits five rounds/calls, six Google sends (five ordinary
discovery sends plus one reserved fallback), and eight Routes requests. Routes
elements remain 32. Earlier capacity paragraphs describe historical checkpoints.
All rounds share the same 360-second stage and original request deadline; more
rounds do not guarantee more model time. Output, identity, spatial and other
acquisition policies are unchanged. These new limits have no new live evidence.

## Mixed transport and joint Repair configuration

The following additional leaves are read once in the effective request policy. Values in
runtime.yaml are authoritative; these are application defaults, not user requirements.

| Path | Current value | Type/unit and semantics |
| --- | --- | --- |
| `v3_repair.acquisition.post_proposal_route_reserve` | `8` | Nonnegative integer actual sends reserved from the stage total for legal proposals; zero disables reservation. Must not exceed routes. |
| `transport.walk_route_max_km` | `3` | Positive provider route kilometres for automatic WALK selection; distinct from geographic prefilter. |
| `transport.transit_max_minutes` | `45` | Positive provider total journey minutes, including provider-reported access walking; requires departure applicability. |
| `transport.drive_max_minutes` | `30` | Positive provider driving minutes per leg; reserve is additional. |
| `transport.drive_reserve_minutes` | `10` | Nonnegative application access/pickup/drop-off minutes per leg; zero removes this reserve, not provider time. |

`spatial.max_leg_minutes` is the WALK provider-duration limit (45 minutes).
The route preparation allowance is derived as routes minus post_proposal_route_reserve
(24 - 8 = 16), not another configuration source. All rounds and modes share total sends
and the independent 32-element limit. Cached hits do not spend sends; sent failures do.
Unused preparation allowance remains available after proposals; changing rounds never
renews either allowance. Preparation uses at most 45 runtime seconds and is dynamically
shortened to retain model/recheck/finalization time. The DRIVE reserve instead measures
itinerary occupancy and contributes to the stage-cumulative 90-minute daily burden.
Explicit supported transport restrictions take precedence over the default soft
WALK, TRANSIT, DRIVE preference. Missing evidence never creates a driving estimate.
These settings affect V3 Repair only; the optional transfers output is shared compatibility.


## Shared first-generation mixed transport checkpoint

The YAML `transport` group is the single authority for common WALK/TRANSIT/DRIVE
windows. Runtime parsing projects these values into the compatible V3 spatial object;
the repeated values in an effective snapshot are derived, not a second YAML source.
Repair-only detour, fallback and stage-added burden remain under `v3_repair.spatial`.
In particular, 90 added minutes is not a primary daily-total transport limit.

| Configuration path | Current value | Scope and relationship |
| --- | --- | --- |
| `budget.routes.alternative_pairs` | `32` | Distinct directed supplementary identities; mode/time changes reuse pair identity. Zero disables new pair admission. |
| `budget.routes.alternative_matrix_calls` | `32` | Actual supplementary sends across pre/post generation; failures count. Zero disables sends. |
| `budget.routes.alternative_elements` | `64` | Actual requested origins times destinations across all modes, not returned successes. Zero disables new elements. |
| `budget.routes.post_generation_reserved_pairs` | `16` | Nonnegative reserved pair admission capacity; cannot exceed total. |
| `budget.routes.post_generation_reserved_requests` | `16` | Nonnegative reserved sends; cannot exceed total. |
| `budget.routes.post_generation_reserved_elements` | `32` | Nonnegative reserved elements; cannot exceed total. |
| `budget.routes.work_seconds` | `120` | Positive cumulative monotonic route-work wall seconds, maximum 120. Overlap counted once; LLM/Web pauses excluded. |
| `budget.routes.post_generation_reserved_seconds` | `30` | Nonnegative post-generation time protection within total; not a guarantee of request time. |
| `budget.routes.provider_timeout_seconds` | `20` | Positive per-call seconds, at most 20; shortened by remaining allowance. |

Pre-generation allowances are totals minus reservations; post-generation can use all
remaining capacity. Pair admission occurs only on selection for supplementary processing,
not enumeration. Cache reuse bypasses new-send quotas. Initial acquisition and Repair
share request evidence/cache/failure history but retain separate send budgets. Baseline
remains 7 requests / 400 elements / 64 elements per request. The historical single-matrix
compatibility setting is not an extra allowance. Application envelopes for supplementary
pairs/requests/elements are now 32/32/64; these are not provider absolute limits.

`main_generation.input_tokens` is 252000 (positive; maximum 252000), independent from the
same-valued Repair ceiling. Output remains 16384 and framing 2048. Actual prompt/schema
counts fail closed on overflow. Provider context compatibility and actual completion remain
runtime concerns; offline sizing is not model usage. No new CLI overrides were added;
`--runtime-config` selects the immutable snapshot, and explicit development timeout retains
its existing opt-in semantics. The 600-second request deadline is never extended by route
or Repair phases. The V3 initial-route guard uses the existing minimum model and recheck
reserves as downstream headroom, in addition to the authoritative Nearby reserve.

All new transport/window values apply to V1/V2/V3 shared primary planning and V3 Repair;
V0 does not acquire routes. This checkpoint supersedes earlier V3-only ownership statements
for the migrated common transport fields. No new live evidence is claimed.


Minimum Daily Coverage is an invariant product rule, not another review toggle. The existing
quantity switch controls only optional 1->2 improvement. Blank-day coverage uses the
existing configured hours and full-day/source protections; this feature adds no budget,
policy threshold or configuration file. The latest Routes allowance remains 24 requests
with 8 reserved for post-proposal work and 32 elements shared by all rounds/modes.

## Engineering closeout (2026-09-25)

Current values were loaded and hashed during [V3 closeout](../docs/records/v0-v3/v3-closeout.md).
No runtime limits changed in that task. The final combined-tree offline regression passed;
historical live limits retain their original run configurations.

## POI semantics (request-wide)

V1/V2/V3 share one request-owned assessment ledger after normal Details. V0 remains tool-free. All values below are required positive engineering parameters; zero is invalid. Calls and elapsed model seconds accumulate across initial preparation and all Repair rounds; cache reuse spends neither. Failures consume sent calls and terminate the flow, whereas pre-send limits stop unassessed candidates from entering main authorization. Framing reuses `main_generation.framing_tokens`. No new CLI/environment overrides are introduced.

| Path | Current YAML value | Meaning |
| --- | --- | --- |
| `poi_semantics.max_calls` | `6` | Model invocations per request, not per stage or round; failures count. Actual HTTP sends are separate provider telemetry. |
| `poi_semantics.batch_size` | `32` | Distinct canonical identities per batch (at most 32). |
| `poi_semantics.input_tokens` | `32000` | Per-call engineering input ceiling; system, user, schema and framing. |
| `poi_semantics.output_tokens` | `8192` | Per-call output token cap. |
| `poi_semantics.call_timeout_seconds` | `45` | Seconds per call, clipped by remaining phase/request time. |
| `poi_semantics.total_seconds` | `120` | Cumulative model elapsed seconds per request. |
| `poi_semantics.exploration_fraction` | `0.3333333333333333` | Share of optional candidate processing opportunities; not an output quota. |
| `poi_semantics.exception_alternatives` | `2` | Alternatives per requested exception visit, inside existing K. |

Quantity review now defaults to enabled; overfull review remains disabled. The obsolete
`v3_repair.repetition_review_enabled` field has been removed from configuration and the
V3 `review_policy` report. Remove this key from custom YAML before loading it; unknown
keys are rejected. Unauthorized canonical repeats remain automatic policy targets,
authorized revisits remain protected, and unassessed multiplicity stays UNKNOWN.
The internal optional review-target list no longer accepts repetition. Historical captures
retain their original schemas and may require the matching historical code for replay.
Product and Dev V3 use the same YAML policy; restart existing backend processes to reload
cached configuration. CLI `--no-repair-quantity-review` still explicitly disables quantity
review for one run. Budgets, operation permissions and V0-V2 behavior are unchanged.
Semantic judgments and provenance rules are contracts, not configuration bypass switches.

The complete block is mandatory for current runtime loading, including custom runtime files.
Omission is a configuration error, not a switch to legacy classification. Old request contracts
are still readable independently of runtime configuration; no historical files are migrated.
The immutable effective snapshot and its hash are captured once; each request's semantic ledger
also reports its policy hash, input hashes, cache hits and per-call reported usage.
Each sent semantic call records `timeout_seconds`, `limiting_deadline` and
`remaining_seconds` for the call, cumulative total, caller phase and request limits
that apply. These values describe the allowance selected before sending, not provider
latency or proof of completed billing. Input/outcome captures and trace events retain
them; the bounded budget summary retains allowlisted timing fields even on failure.
Missing usage remains missing. A model timeout remains terminal and cannot qualify an
unassessed candidate or trigger an automatic retry.


POI semantic reference correction (2026-09-27): at most one correction per invalid-reference
batch shares the above request-owned limits; it does not add a separate allowance or change
runtime defaults. Feedback counts toward input sizing. Calls, timeouts, absolute deadlines
and capture caps apply to both attempts. Unavailable or unsuccessful correction is terminal.

The subsequent approved contract-correction expansion also covers identity-set mismatch
and exception authorization/ownership errors. All supported classes share the same single
correction per batch; switching error class does not reset it. Prompt 4 clarifies exact
exception permissions, and bounded feedback remains included in input sizing. No runtime
default, capture setting or quantity Repair configuration changes accompany this expansion.

The subsequent prompt-5 short-reference wire contract also keeps every default unchanged.
Canonical IDs and sources are application-owned; pNN/eNN references are batch-local model
identifiers, not configurable external IDs. Input accounting uses the actual projected
payload and wire schema. The one-correction allowance is unchanged. Normalized opt-in
capture now includes a reference mapping/hash/version and retains canonical accepted
outcomes; existing size caps and redaction still apply. Old capture payloads are historical
and must not be assumed to use the current wire format.

When file tracing is enabled, finalization also writes budget.json independently of
trace.max_payload_bytes and optional payload capture flags. The summary uses existing
numeric runtime events and final primary counters; it does not enable additional API or
LLM calls. Its fixed 64 KiB metadata ceiling and 32 call records per tracked stage are
storage limits, not runtime execution limits. Dropped records or exceptional size overflow
are marked collection_status=incomplete. Missing reported usage stays missing, never zero.
run.json records budget_summary_status when its own final write succeeds. A budget.json
write failure does not stop planning or ordinary trace finalization. A pending .tmp file
is not a finalized summary. Historical runs are not retroactively rewritten.

## Landmark nomination

`landmark_nomination` applies to initial V1-V3 discovery; V0 and V3 Repair do not invoke it.
It uses the existing model deployment, with independent accounting and the remaining
request deadline. No retries are added.

| YAML leaf | Default | Valid range / meaning |
| --- | --- | --- |
| `landmark_nomination.max_calls` | `1` | Exactly one maximum send |
| `landmark_nomination.max_names` | `12` | 1-12 ordered names |
| `landmark_nomination.input_tokens` | `8000` | 1-8000, prompt/schema/framing included |
| `landmark_nomination.output_tokens` | `2000` | 1-2000 |
| `landmark_nomination.call_timeout_seconds` | `20` | Greater than zero, at most 20; shortened by deadline |
| `landmark_nomination.supplementary_searches` | `4` | 0-4 actual sends within the existing candidate-search pool |

User-named searches precede general discovery and supplementary nomination queries.
Existing exact matches/cache are reused; unused opportunities return to ordinary discovery.
All existing C/G/K, Details, semantic, RAG, route and Repair ceilings remain unchanged.
Model-origin rank is selection metadata, not provider fact evidence. Bounds are engineering
starting values; live quality, latency and cost remain unmeasured. See
[landmark discovery](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/a6aff13a00af35467b9c88ec2906d10a96095f04/docs/shared_landmark_discovery.md) for identity and fallback behavior.

Ticket 03 (2026-09-28) adds no configuration keys or budget increase. Candidate balancing
uses the sourced final soft target plus one replacement opportunity; this is a selection
heuristic, not a final category quota. Existing exploration settings also admit resolved
landmarks that match preferences. See [supply policy](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/a6aff13a00af35467b9c88ec2906d10a96095f04/docs/shared_poi_supply.md).
