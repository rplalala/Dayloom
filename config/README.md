# Configuration reference

Dayloom separates installation settings from planner policies:

| File | Purpose |
| --- | --- |
| `product.example.yaml` | Portable Product, database and Foundry defaults |
| `product.yaml` | Optional local deployment settings; ignored by Git |
| `.env` | Private credentials and local overrides; ignored by Git |
| `config/runtime.yaml` | Independent V0–V3 development policy |
| `config/runtime.acceptance.yaml` | Product acceptance policy |

Use [deployment](../docs/guides/deployment.md) to install the application and
[development](../docs/guides/development.md#local-configuration-console) to edit local
settings. This reference owns field names, precedence and policy limits.

## Deployment settings

Without `product.yaml`, every runtime reads `product.example.yaml`. To customize
Product options, copy the template to `product.yaml`; `/config` creates or updates
the local file when saving a Foundry deployment. No personal endpoint ships in the
template. Database fields edited through `/config` are saved as `.env` overrides.

| Setting | Environment key | Default / use |
| --- | --- | --- |
| `origin` | `PRODUCT_ORIGIN` | `http://localhost:5173`; exact application origin |
| `allow_insecure_loopback` | `PRODUCT_ALLOW_INSECURE_LOOPBACK` | `true` for the supplied HTTP loopback setup; disable for HTTPS hosting |
| `session_seconds` | `PRODUCT_SESSION_SECONDS` | `3600`; accepted range 1–86400 |
| `runtime_profile` | `PRODUCT_RUNTIME_PROFILE` | `acceptance` for Product; independent planners default to development |
| `database.host` | `DAYLOOM_DB_HOST` | `127.0.0.1` |
| `database.port` | `DAYLOOM_DB_PORT` | `55432`; accepted range 1–65535 |
| `database.name` | `DAYLOOM_DB_NAME` | `dayloom` |
| `database.user` | `DAYLOOM_DB_USER` | `dayloom` |
| — | `DAYLOOM_DB_PASSWORD` | Private PostgreSQL role password |
| — | `DAYLOOM_DB_URL` | Optional complete connection; overrides split fields, and must name the database. Blank uses split fields. |
| — | `DAYLOOM_DB_VOLUME` | `dayloom_pgdata` for new Compose storage; retain the actual volume on existing installations |
| `foundry.endpoint` | `AZURE_OPENAI_ENDPOINT` | Configure your supported HTTPS endpoint ending in `/openai/v1` |
| `foundry.deployment` | `AZURE_OPENAI_DEPLOYMENT` | `gpt-6-luna`; use a deployment compatible with the selected policy |
| — | `AZURE_OPENAI_API_KEY` | Foundry model and web-search credential |
| — | `OPENAI_API_KEY` | TripWorld query embeddings |
| — | `GOOGLE_MAPS_API_KEY` | Planning and place photographs |
| — | `PRODUCT_UNSPLASH_ACCESS_KEY` | Optional atmosphere photos; `UNSPLASH_API_KEY` remains an alias |
| — | `PRODUCT_JWT_SECRET` | Private signing key, at least 32 characters; local startup generates one only when absent |

Explicit settings arguments take precedence over process environment, dotenv,
secret-file settings, deployment YAML and code defaults. Product resolves default
paths from the repository root. Unknown/duplicate YAML keys and credentials in YAML
are rejected without echoing values. The console shows process-managed fields as
locked, masks secrets and requires a restart for saved connection/provider/JWT changes.
It retains existing signing keys; **Generate signing key** replaces one explicitly.

The database launcher uses these same resolved fields when invoking Compose;
Compose does not parse YAML itself. A URL used for local Compose must explicitly
supply an IPv4 loopback host, port, database, user and password. Application clients
can use separately hosted databases. Connection settings do not migrate existing
data, rename roles or update their passwords.

## Diagnostics and development server

Set backend diagnostic options in ignored `.env` or the process environment and
restart the backend. Relative log paths resolve from the repository root.

| Environment key | Default | Purpose |
| --- | --- | --- |
| `PRODUCT_LOG_ENABLED` | `true` | Write Product operation and planning logs |
| `PRODUCT_LOG_DIRECTORY` | `logs/product` | Server diagnostic root |
| `PRODUCT_LOG_MAX_FILE_BYTES` | `5000000` | Operation-log rotation threshold |
| `PRODUCT_LOG_BACKUPS` | `5` | Retained operation-log backups |
| `PRODUCT_LOG_MAX_EVENT_BYTES` | `128000` | Detailed event/payload content limit |
| `PRODUCT_LOG_MAX_RUN_BYTES` | `50000000` | Per-run detailed collection budget; metadata and final summaries are separate |
| `PRODUCT_LOG_MAX_STORAGE_BYTES` | `500000000` | Finished-run retention budget applied during maintenance |
| `PRODUCT_LOG_RETENTION_DAYS` | `30` | Maximum age of inactive finished runs |
| `VITE_PRODUCT_DIAGNOSTICS` | enabled | Set `false` at frontend build time to disable browser collection |
| `PRODUCT_API_PROXY` | `http://127.0.0.1:8000` | Vite process proxy for `/api` and `/health` |

The selected runtime's `trace` settings control categories and payload levels:
`metadata` retains structured events, summaries and bounded validation snapshots;
`normalized` adds eligible normalized payloads; `raw` permits eligible model payloads.
Raw tool payloads also require `trace.raw_provider_payloads`. These settings change
collection, not provider execution. See the
[diagnostic contract](../docs/0007-application-operations.md#product-diagnostics) for
correlation/privacy and [log commands](../docs/guides/development.md#product-diagnostics)
for local inspection and pruning.

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
planning. Version selection and primary prompt structure are shared; the selected profile
controls effective supply budgets.

The V3 CLI supports `--repair-quantity-review` and `--no-repair-quantity-review`; an explicit
flag overrides YAML, absence retains YAML. No other Repair CLI or environment budget overrides
are introduced. `--development-timeout-seconds` remains explicit, positive, and bounded by
`development_timeout_seconds`; CLI YAML alone does not activate a request timeout. V3 counts from request
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

## Product acceptance profile

Product selects `acceptance` through `product.yaml: runtime_profile`; an explicit
`PRODUCT_RUNTIME_PROFILE=development` restores the development policy after restart.
Independent V0-V3 entry points retain development defaults. An explicit
CLI `--runtime-config config/runtime.acceptance.yaml` opts a tools runner into acceptance.
Snapshots record the complete selected policy and its digest. New optional/default fields
are omitted from legacy development serialization, preserving old snapshot hashes.

| Resource | Development | Product acceptance |
| --- | --- | --- |
| Main/Repair input / output tokens | 252000 / 16384 | 900000 / 32768 |
| Canonical candidates / candidate searches / Details sends | 64 / 12 / 60 | 256 / 24 / 160 |
| Initial supply ceiling | 20 | 60 |
| Review Details / enriched places / profile calls | 8 / 8 / 8 | 12 / 12 / 12 |
| Semantic calls / cumulative seconds | 6 / 120 | 12 / 240 |
| Semantic input / output tokens / per-call seconds | 32000 / 8192 / 45 | 64000 / 16384 / 60 |
| Baseline route elements / calls / elements per request | 400 / 7 / 64 | 3600 / 64 / 64 |
| Alternative route pairs / calls / elements | 32 / 32 / 64 | 64 / 64 / 128 |
| Route work / post-generation reserved seconds | 120 / 30 | 120 / 30 |
| RAG queries / Top-K / returned positions | 4 / 20 / 80 | 4 / 20 / 80 |
| RAG resolution / Details / fallback sends | 30 / 30 / 4 | 30 / 30 / 4 |
| RAG query tokens / stage seconds | 2048 / 360 | 2048 / 360 |
| Official evidence tasks / page fetches | 8 / 8 | 8 / 8 |
| Official search tool calls per request | 2 | 2 |
| Repair input identity union / rounds / proposal calls | 32 / 6 / 6 | 128 / 10 / 10 |
| Repair Google / fallback / Details sends | 6 / 1 / 30 | 8 / 2 / 30 |
| Repair route calls / elements | 24 / 32 | 32 / 64 |
| Repair stage / hard round / model seconds | 420 / 150 / 70 | 720 / 210 / 120 |
| Repair preparation / reference round seconds | 60 / 120 | 60 / 180 |
| Whole application request seconds | 600 | 1200 |
| Nearby searches / references / stage seconds | 3 / 3 / 10 | Up to 10 / 20 / 45 |
| Destination assistance | 100 attempts/process/UTC day | No daily cutoff; 1.1-second user cooldown, 1 concurrent provider call |
| Preference polishing | 20 operations/process/UTC day, 1 concurrent | No daily cutoff; 2-second user cooldown, 4 concurrent provider calls |

The typed ceilings distinguish provider capacity from the profile's operating allowance.
For the current Foundry GPT-6 Luna deployment, the published limits are 922,000 input
tokens, 128,000 output tokens and a shared 1,050,000-token context. Acceptance leaves
input headroom below that bound. The retained optional OpenAI search adapter has a
32,768-token output ceiling; larger auxiliary settings are capped at that adapter boundary.
Sources: [Azure model capabilities](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure#gpt-6),
[OpenAI GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) and
[OpenAI GPT-4.1 Mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
These are documented capabilities, not an account-specific quota or long-request live test.

Development and Product acceptance use Azure Foundry web search with the configured
Foundry endpoint, deployment and key. Explicit `provider: azure_foundry` selects this
adapter; omitting the field preserves the same adapter and legacy configuration digest.
Search retains domain filtering, `max_tool_calls`, timeouts, caller-input/output limits
and zero SDK retries. The existing optional `provider: openai` adapter remains available
to explicitly configured runtimes, but is not selected by either standard profile.
`OPENAI_API_KEY` is still required for TripWorld query embeddings.

`generation_spend_usd: 25` enables one request-local allowance across Product generation
and introductions, the programmatic runtime, and the tools CLI with explicit acceptance
configuration. Protected requests reserve their maximum recognized charge before HTTP dispatch.
Concurrent provider calls within that planning run share the allowance. Failed, cancelled and incomplete responses keep
the full reservation; only complete reported model usage can release a conservative
unused difference. Missing usage never means zero cost. A blocked allowance prevents
subsequent protected sends and cannot produce a successful Product result.

Requests whose sole hosted tool is `web_search` are explicitly excluded from dollar
admission and accounting, including their search-model tokens. This applies to the
Azure adapter and the retained OpenAI adapter. They neither reserve the allowance nor
fail its tariff check. Their existing task/call/time/input/output limits still apply.
The spending snapshot lists attempted exclusions in `excluded_operations`; absence of
a search reservation is not a zero-cost observation. Consequently, US$25 bounds only
protected operations and is not an upper bound on the complete generation bill.
The larger resource ceilings do not increase this allowance or promise every maximum
can be consumed together. More evidence, model work or context can increase actual cost
and latency; the same monetary protection can stop a run before its count or time ceiling.

The tariff boundary admits these protected operations; outside the web-search exemption,
unsupported models, hosted tools, streaming/background execution and unpriced route
options fail before dispatch:

| Operation | Conservative reservation/accounting |
| --- | --- |
| Places search/Details | US$0.04 per request, retained on errors |
| Routes Essentials matrix | US$0.005 per origin/destination element |
| Foundry Luna without hosted tools | Full 1,050,000-token context plus explicit output cap; US$1/M input and US$2/M output, above verified Global Standard long-context/cache rates |
| `text-embedding-3-small` | US$0.006 per request, covering the 300,000-token endpoint maximum |
| Existing Open-Meteo endpoint | No incremental API charge |

Sources: [OpenAI pricing](https://developers.openai.com/api/docs/pricing),
[Azure rates](https://azure.microsoft.com/en-us/blog/gpt-6-astra-sol-and-luna-for-production-agents-in-microsoft-foundry/),
and [Maps pricing](https://developers.google.com/maps/billing-and-pricing/pricing).
These are conservative API-charge bounds, not invoices or tax calculations. Photos,
atmosphere media and fixed infrastructure are separate from generation. Local token checks
remain engineering admission; monetary reservations use provider context maxima instead.
The allowance never truncates requirements or substitutes a weaker evidence condition.
Injected external transports remain responsible for honoring the same send boundary.

The 10-day trip duration, 14-day date horizon, provider model-context bounds, source and ownership
requirements, provider constraints and zero hidden retries are unchanged. A configured ceiling
does not guarantee every round fits the request deadline. Rollback selects development;
existing saved trips and original requirements are not migrated or weakened.

## Counting, timing and invariants

Numerical examples in this section use the development profile. Acceptance overrides are
defined above; both profiles use the same counting, deadline and adoption rules.

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
Compression uses the selected profile's per-call time and input/output allowances. Input includes
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
Quality-first validates coordinated candidate, Details, supply and full baseline-matrix capacities;
profile/review capacity relationships and RAG query-position/token relationships still apply.
No historical compatibility field is silently repurposed as a Repair allowance.

## Development YAML values and effective paths

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
| `input_assistance.destination.daily_attempts_per_process` | `100` | integer 1..100 or null with admission | UTC-day local send cap, including failed sends. |
| `input_assistance.polishing.source_max_chars` | `4000` | integer; 1..4000 | Maximum source length for optional polishing; normal planning keeps its own limit. |
| `input_assistance.polishing.source_max_tokens` | `1500` | integer; 1..1500 | Maximum source token count before any model construction. |
| `input_assistance.polishing.model_input_tokens_per_call` | `8000` | integer; 1..8000 | Prompt, context and schema estimate cap for the single draft call. |
| `input_assistance.polishing.draft_output_tokens` | `2000` | integer; 1..2000 | Maximum draft response tokens. |
| `input_assistance.polishing.call_timeout_seconds` | `20` | seconds; > 0, <= 20 | Deadline for each model call. |
| `input_assistance.polishing.total_timeout_seconds` | `40` | seconds; > 0, <= 40 | End-to-end model operation deadline. |
| `input_assistance.polishing.daily_operations_per_process` | `20` | integer 1..20 or null with admission | UTC-day admitted polishing operations per process. |
| `reference_discovery.policy_version` | `"nearby_references_1"` | string; = "nearby_references_1" | Final-primary Nearby reference contract identifier. |
| `reference_discovery.max_requests` | `3` | integer; 0..10 | Nearby sending allowance per request, after the whole Repair stage. Zero disables the allowance. |
| `reference_discovery.max_result_count` | `10` | integer; >= 1, <= 10 | Provider result count per Nearby request. Zero is invalid. |
| `reference_discovery.radius_metres` | `800` | number; > 0, <= 800 | Nearby search radius around an actual final anchor. Zero is invalid. |
| `reference_discovery.anchor_reuse_metres` | `300` | number; >= 0, <= 300 | Maximum anchor separation for reusing a Nearby result. Zero removes the corresponding tolerance. |
| `reference_discovery.deadline_seconds` | `10` | seconds; > 0, <= 45 | Independent final Nearby phase cap; Repair subtracts this same value from remaining request time as its reservation. Zero is invalid. |
| `reference_discovery.request_timeout_seconds` | `4` | number; > 0, <= 4 | Per-Nearby-request timeout. Zero is invalid. |
| `reference_discovery.retries` | `0` | integer; = 0 | Fixed zero retry contract. Zero is the only supported value. |
| `reference_discovery.max_references` | `3` | integer; 0..20 | Maximum attached references per final anchor policy. Zero disables the allowance. |
| `reference_discovery.rank_preference` | `"DISTANCE"` | string; = "DISTANCE" | Fixed provider distance ranking. |
| `reference_discovery.included_types` | `["restaurant", "cafe", "park", "museum"]` | array; schema-validated | Fixed four reference categories; changes require a reference policy contract change. |
| `app.time_zone` | `"Australia/Sydney"` | string; schema-validated | Backend trusted reference-day calendar. Existing date contract is unchanged. |
| `budget.candidates` | `64` | integer; 1..256 | Primary canonical candidate processing capacity per request, not scheduled visits. Zero is invalid. |
| `budget.final_pois` | `20` | integer; 1..60 | Maximum primary supply capacity. Duration policy selects the effective K; this does not force K20 for shorter trips. Zero is invalid. |
| `budget.places.destination_search_calls` | `1` | integer; 1..2 | Destination resolution searches per primary request. Zero is invalid. |
| `budget.places.candidate_search_calls` | `12` | integer; 1..48 | Initial candidate discovery search calls per primary request. Zero is invalid. |
| `budget.places.detail_calls` | `60` | integer; 1..240 | Shared primary Details sending allowance. Repair has a separate stage allowance and the same request cache/failure state. Zero is invalid. |
| `budget.places.review_detail_calls` | `8` | integer; 0..24 | Primary review-bearing Details allowance. Zero disables the allowance. |
| `budget.weather.calls` | `2` | integer; 0..6 | Primary weather operation allowance; Repair reuses weather. Zero disables the allowance. |
| `budget.routes.matrix_elements` | `64` | integer; 1..100 | Compatibility single-matrix counter retained in ToolBudgetLimits. Active baseline/alternative acquisition uses the dedicated counters below; it is not an extra V3 allowance. Zero is invalid. |
| `budget.routes.baseline_elements_per_request` | `64` | integer; 1..64 | Maximum actual origin count times destination count per primary baseline matrix. Zero is invalid. |
| `budget.routes.baseline_elements_per_run` | `400` | integer; 1..3600 | Total directed primary baseline elements per request. Zero is invalid. |
| `budget.routes.baseline_calls` | `7` | integer; 1..128 | Primary baseline matrix calls per request. Zero is invalid. |
| `budget.routes.alternative_pairs` | `32` | integer; 0..128 | Primary alternative selected-pair capacity. Zero disables the allowance. |
| `budget.routes.alternative_matrix_calls` | `32` | integer; 0..256 | Primary alternative matrix call allowance. Zero disables the allowance. |
| `budget.routes.alternative_elements` | `64` | integer; 0..512 | Primary alternative actual matrix element allowance, including unavailable results. Zero disables the allowance. |
| `budget.web.evidence_tasks` | `8` | integer; 0..20 | Primary official-evidence tasks; not individual search tool invocations. Zero disables the allowance. |
| `budget.web.page_fetches` | `8` | integer; 0..20 | Primary page-fetch budget. Zero disables the allowance. |
| `budget.experience.review_enriched_places` | `8` | integer; 0..24 | Primary places selected for review enrichment. Zero disables the allowance. |
| `budget.experience.profile_llm_calls` | `8` | integer; 0..24 | Primary ExperienceProfile model invocations; no new profiles during Repair. Zero disables the allowance. |
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
| `tripworld_discovery.top_k` | `20` | integer; >= 1, <= 30 | Initial RAG rows per query, not Repair Top-K. Zero is invalid. |
| `tripworld_discovery.resolution_entities` | `30` | integer; >= 0, <= 60 | Primary RAG canonical resolution work allowance. Zero disables the allowance. |
| `tripworld_discovery.details_calls` | `30` | integer; >= 0, <= 60 | Primary RAG Details allowance. Zero disables the allowance. |
| `tripworld_discovery.fallback_calls` | `4` | integer; >= 0, <= 8 | Primary RAG Google fallback search allowance. Zero disables the allowance. |
| `tripworld_discovery.radius_km` | `15` | integer; = 15 | Initial destination retrieval radius; Repair derives its own target radius from v3_repair.spatial. Zero is invalid. |
| `tripworld_discovery.identity_radius_km` | `1` | integer; = 1 | Google-backed canonical identity matching radius, reused by RepairResolver. Zero is invalid. |
| `tripworld_discovery.deadline_seconds` | `360` | number; > 0, <= 600 | Initial RAG phase deadline; Repair uses its own stage and round deadlines, not this expired phase allocation. Zero is invalid. |
| `tripworld_discovery.embedding_timeout` | `8` | number; > 0, <= 20 | Per-embedding timeout, reused by Repair within its remaining stage time. Zero is invalid. |
| `tripworld_discovery.sql_timeout` | `60` | number; > 0, <= 120 | Per-retrieval timeout, reused by Repair within its remaining stage time. Zero is invalid. |
| `tripworld_discovery.connect_timeout` | `10` | number; > 0, <= 20 | Request-owned RAG database connection establishment tolerance. No independent connectivity probes. Zero is invalid. |
| `tripworld_discovery.google_timeout` | `4` | number; > 0, <= 10 | RAG Google search timeout, also reused by Repair discovery. Zero is invalid. |
| `tripworld_discovery.retries` | `0` | integer; = 0 | Fixed zero retry contract. Failed embedding texts/retrieval keys remain failed across stages/rounds. Zero is the only supported value. |
| `tripworld_discovery.max_queries` | `4` | integer; >= 1, <= 8 | Initial distinct retrieval-query allowance. Zero is invalid. |
| `tripworld_discovery.max_positions` | `80` | integer; >= 1, <= 240 | Initial query-result position processing ceiling; max_queries times top_k must fit. Zero is invalid. |
| `tripworld_discovery.total_query_tokens` | `2048` | integer; >= 1, <= 4096 | Initial query token budget; must cover max_queries times 512. Zero is invalid. |
| `acquisition.policy_id` | `"quality_first_1"` | string; one of ["conservative_1", "quality_first_1"] | Shared primary supply/acquisition policy. quality_first_1 validates the coordinated duration envelope. |
| `acquisition.details_deadline_seconds` | `120` | number; > 0, <= 240 | Primary candidate Details phase wall-clock limit; not reused as a stale Repair deadline. Zero is invalid. |
| `acquisition.details_timeout_seconds` | `20` | number; > 0, <= 30 | Primary Details call wall-clock limit. Zero is invalid. |
| `main_generation.enabled` | `true` | boolean; schema-validated | Shared primary serializer protection switch. Required by quality_first_1. |
| `main_generation.input_tokens` | `252000` | integer; >= 1, <= 922000 | Per-primary-call serialized input engineering ceiling. Zero is invalid. |
| `main_generation.output_tokens` | `16384` | integer; >= 1, <= 128000 | Per-primary-call structured output ceiling. Zero is invalid. |
| `main_generation.framing_tokens` | `2048` | integer; >= 2048, <= 2048 | Per-primary-call message framing token reserve. Zero is invalid. |
| `development_timeout_seconds` | `600` | integer; 1..2700 | Maximum permitted explicit development CLI request allowance. Presence alone does not enable this timeout; V3 requires an explicit allowance from entry. Zero is invalid. |
| `v3_repair.max_rounds` | `6` | integer; 1..20 | Model rounds per Repair stage, shared across dates/targets. System deletions use their own attempt ceiling. Zero is invalid. |
| `v3_repair.max_model_calls` | `6` | integer; 0..20 | Proposal model sending ceiling per entire stage; zero disables Repair model proposals. Must not exceed max_rounds. |
| `v3_repair.max_deletion_attempts` | `12` | integer; >= 0, <= 120 | System deletion attempts per stage, separately bounded from proposal model sends and sharing stage time/provider limits. Zero disables enumeration. |
| `v3_repair.reason_compression.max_calls` | `1` | integer; >= 0, <= 1 | Separate stage-wide explanation compression attempts; zero disables compression. |
| `v3_repair.reason_compression.input_tokens` | `32000` | integer; >= 1, <= 64000 | Complete compression system/user/schema/framing input ceiling; overflow stops before dispatch. |
| `v3_repair.reason_compression.output_tokens` | `8192` | integer; >= 1, <= 16384 | Output ceiling for the single batch. |
| `v3_repair.reason_compression.timeout_seconds` | `30` | number; > 0, <= 60 | Per-call ceiling, shortened by existing hard deadlines and recheck reserve. |
| `v3_repair.quantity_review_enabled` | `true` | boolean; schema-validated | Default coverage review-target activation; CLI can explicitly disable it. It never turns NEEDS_REVIEW into CONFIRMED. |
| `v3_repair.alternatives_per_gap` | `2` | integer; >= 1 | Distinct alternatives per authorized quantity gap as a preparation reference. Fewer options may still be used. Zero is invalid. |
| `v3_repair.exploration_positions` | `2` | integer; >= 0, within identity capacity | Reusable exploration positions within the same input union across the stage, not extra candidates or per-date quotas. Zero removes reserved presentation opportunities. |
| `v3_repair.timing.stage_seconds` | `420` | seconds; > 0, <= 1800 | Maximum Repair wall-clock duration, additionally bounded by entry deadline minus Nearby reservation. Zero is invalid. |
| `v3_repair.timing.round_seconds` | `150` | seconds; > 0, <= 420 | Maximum wall-clock allocation for one candidate/model/recheck round. Zero is invalid. |
| `v3_repair.timing.model_seconds` | `70` | seconds; > 0, <= 240 | Maximum model wait per call; dynamically shortened by remaining round time minus recheck reserve. Zero is invalid. |
| `v3_repair.timing.preparation_seconds` | `60` | number; >= 0, <= 120 | Maximum optional candidate and pre-proposal route acquisition window per round. Zero disables new preparation work, not cached reuse or the model. Zero removes the corresponding tolerance. |
| `v3_repair.timing.recheck_reserve_seconds` | `20` | number; > 0 | Round time retained after model wait for route acquisition and application revalidation. Zero is invalid. |
| `v3_repair.timing.minimum_model_seconds` | `30` | number; > 0 | Minimum available model allocation required to start a call. Zero is invalid. |
| `v3_repair.timing.round_reference_seconds` | `120` | number; > 0 | Divisor used to estimate affordable remaining rounds and their soft preparation window. It does not shorten the hard model/recheck deadline or promise that many rounds. Zero is invalid. |
| `v3_repair.timing.finalization_reserve_seconds` | `1` | number; > 0 | Time withheld from post-proposal I/O for local finalization. Must be smaller than recheck reserve. Zero is invalid. |
| `v3_repair.input.input_tokens` | `252000` | integer; >= 1, <= 922000 | Per-model-call total system/user/schema/framing engineering ceiling; overflow preserves latest adopted itinerary. Zero is invalid. This application ceiling does not certify provider context capacity. |
| `v3_repair.input.output_tokens` | `16384` | integer; >= 1, <= 128000 | Per-model-call strict output limit forwarded without mutating primary client defaults. Zero is invalid. |
| `v3_repair.input.framing_tokens` | `2048` | integer; >= 1 | Per-call framing reserve included in input count; must be positive and below input_tokens. Zero is invalid. |
| `v3_repair.input.identity_capacity` | `32` | integer; 1..128 | Per-call distinct canonical union: scheduled context plus presented additions plus other operation identities. Ledger is separate and is not serialized wholesale. Zero is invalid. |
| `v3_repair.input.activity_capacity` | `120` | integer; >= 1, <= 240 | Maximum protected plus editable itinerary activities per projection; necessary context is never truncated to pass. Zero is invalid. |
| `v3_repair.input.candidate_characters` | `12000` | integer; >= 1, <= 12000 | Maximum serialized characters per projected candidate; fail closed rather than delete facts. Zero is invalid. |
| `v3_repair.input.feedback_characters` | `12000` | integer; >= 1, <= 12000 | Maximum compact previous-round feedback characters; overflow stops iteration without rollback. Full raw history is not included. Zero is invalid. |
| `v3_repair.acquisition.google` | `6` | integer; >= 0, <= 16 | Stage-wide actual Google discovery/fallback sends; failures after send count. Zero disables the allowance. |
| `v3_repair.acquisition.fallback` | `1` | integer; >= 0, <= 4 | Stage-wide fallback subset of google; cannot exceed google. Zero disables the allowance. |
| `v3_repair.acquisition.embedding` | `1` | integer; >= 0, <= 2 | Stage-wide new query embedding batches; compatible query-vector cache hits do not consume sends. Zero disables the allowance. |
| `v3_repair.acquisition.retrieval` | `1` | integer; >= 0, <= 2 | Stage-wide new RAG retrieval sends. Zero disables the allowance. |
| `v3_repair.acquisition.canonical` | `30` | integer; >= 0, <= 60 | Stage-wide unique canonical processing attempts, including failures. Duplicate identities cannot obtain another attempt by changing round. Zero disables the allowance. |
| `v3_repair.acquisition.details` | `30` | integer; >= 0, <= 60 | Stage-wide actual Details sends; cached success does not consume sends and failure is not retried. Zero disables the allowance. |
| `v3_repair.acquisition.routes` | `24` | integer; >= 0, <= 64 | Stage-wide actual matrix requests, before and after proposals together. Zero disables the allowance. |
| `v3_repair.acquisition.elements` | `32` | integer; >= 0, <= 128 | Stage-wide actual matrix origin count times destination count; counts requested unavailable elements, not just successful returned rows. Zero disables the allowance. |
| `v3_repair.acquisition.top_k` | `10` | integer; >= 1, <= 20 | Rows per Repair RAG query and bounded Google discovery response projection. Does not create another retrieval allowance. Zero is invalid. |
| `v3_repair.acquisition.provider_timeout_seconds` | `20` | number; > 0, <= 30 | Per-Repair Details/Routes call timeout. Google/embedding/SQL timeouts reuse the existing tripworld_discovery values above. Zero is invalid. |
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


## Evidence and candidate invariants

Discovery radii apply when no compatible route exists. Applicable routes still
undergo leg, detour and cumulative daily-burden checks. Missing original routes earn
no invented improvement credit. Provider travel minutes describe itinerary burden;
runtime seconds describe execution limits.

Repair candidate catalog membership is separate from scoped operation permission.
Target/date/operation opportunities, association edges and unique candidate counts
are distinct. Global matching capacity is reported once; identity-free operations
retain their own authorization. Deferred targets cannot acquire candidates for the
current round. Ordinary, initial-RAG and Repair Details share cache/failure history
but retain separate send budgets. Failed sends count; cached reuse does not.

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
Common transport settings apply to V1–V3 primary planning and V3 Repair; detour and added-burden limits apply only to Repair.


## Shared primary transport

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
| `budget.routes.work_seconds` | `120` | Positive cumulative monotonic route-work wall seconds, maximum 300. Overlap counted once; LLM/Web pauses excluded. |
| `budget.routes.post_generation_reserved_seconds` | `30` | Nonnegative post-generation time protection within total; not a guarantee of request time. |
| `budget.routes.provider_timeout_seconds` | `20` | Positive per-call seconds, at most 30; shortened by remaining allowance. |

Pre-generation allowances are totals minus reservations; post-generation can use all
remaining capacity. Pair admission occurs only on selection for supplementary processing,
not enumeration. Cache reuse bypasses new-send quotas. Initial acquisition and Repair
share request evidence/cache/failure history but retain separate send budgets. Baseline
uses the selected profile's call/element ceilings and the unchanged per-request bound. The historical single-matrix
compatibility setting is not an extra allowance. Supplementary pair/request/element allowances come from the selected profile; they are not provider absolute limits.

`main_generation.input_tokens` is 252000 in development and 900000 in acceptance,
within the typed maximum of 922000. Repair has its own input ceiling; the profile
table above records output allowances. Framing is 2048. Actual prompt/schema
counts fail closed on overflow. Provider context compatibility and actual completion remain
runtime concerns; offline sizing is not model usage. No new CLI overrides were added;
`--runtime-config` selects the immutable snapshot, and explicit development timeout retains
its existing opt-in semantics. The selected request deadline is never extended by route
or Repair phases. The V3 initial-route guard uses the existing minimum model and recheck
reserves as downstream headroom, in addition to the authoritative Nearby reserve.

All new transport/window values apply to V1/V2/V3 shared primary planning and V3 Repair;
V0 does not acquire routes.


Minimum Daily Coverage is an invariant product rule, not another review toggle. The existing
quantity switch controls only optional 1->2 improvement. Blank-day coverage uses the
existing configured hours and full-day/source protections. Stage-wide Routes allowances
and the post-proposal reservation follow the selected resource profile and remain shared
across all rounds and modes.

## POI semantics (request-wide)

V1/V2/V3 share one request-owned assessment ledger after normal Details. V0 remains tool-free. All values below are required positive engineering parameters; zero is invalid. Calls and elapsed model seconds accumulate across initial preparation and all Repair rounds; cache reuse spends neither. Failures consume sent calls and terminate the flow, whereas pre-send limits stop unassessed candidates from entering main authorization. Framing reuses `main_generation.framing_tokens`. No new CLI/environment overrides are introduced.

| Path | Development value | Meaning |
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
Product selects acceptance while independent V3 defaults to development;
restart existing backend processes to reload cached configuration.
CLI `--no-repair-quantity-review` still explicitly disables quantity
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


At most one correction per invalid semantic batch shares the existing call,
input and deadline limits. Supported correction classes include invalid references,
identity-set mismatch and exception authorization/ownership errors. A different
error class does not renew the allowance; unsuccessful correction is terminal.

Canonical identities and sources remain application-owned. Batch-local short
references are restored before domain checks, and input accounting uses the actual
projected payload and wire schema. Opt-in captures retain the reference mapping,
hash/version and canonical accepted outcome within the existing size/redaction caps.
Historical captures retain their original formats.

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
Nomination shares the selected profile's C/G/K, Details, semantic, RAG, route and Repair
allowances. Model-origin rank is selection metadata, not provider fact evidence. See
[landmark discovery](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/a6aff13a00af35467b9c88ec2906d10a96095f04/docs/shared_landmark_discovery.md) for identity and fallback behavior.

Ticket 03 (2026-09-28) adds no configuration keys or budget increase. Candidate balancing
uses the sourced final soft target plus one replacement opportunity; this is a selection
heuristic, not a final category quota. Existing exploration settings also admit resolved
landmarks that match preferences. See [supply policy](https://github.com/rplalala/Reliable-Trip-Plan-Agent/blob/a6aff13a00af35467b9c88ec2906d10a96095f04/docs/shared_poi_supply.md).

The acceptance policy retains large input and supply capacity while bounding actual work.
Its floor is the original acceptance policy at `413fe7f`: no numerical allowance is
lower than that revision. Repair count and time limits return to that original policy;
the request budget is 20 minutes, with at most 12 minutes for Repair and ten shared
proposal rounds. Remaining phase/request time can end Repair before every round is used.
Nested deadlines are not additive, and timeout cleanup may finish after the budget expires.
The development column is a separate policy, not the original acceptance floor.
Details acquisition has 180 seconds; Maps requests retain a 20-second timeout, official
search has 30 seconds, and Repair reason compression has 30 seconds. RAG embedding and
Google timeouts are 10 and 8 seconds. Other RAG transport limits retain the original policy.
These are engineering allowances, not measured latency or quality guarantees.

Acceptance supply estimates daily demand from sourced pace and hard dated totals, skips
fixed full-day protections, and reserves for named identities plus category obligations and alternatives. Their overlap is not assumed before evidence.
The supply target is a resource allocation, never a new visit quota. Resolved required
identities use the selected supply ceiling instead of the development-only 16-identity gate.
Acceptance review capacity follows the configured review budgets and half the supply
target, rounded up, rather than a fixed eight-place ceiling. A nine-day Rich request
normally reserves 36 supply identities and permits 12 review-enriched places under this policy.
Acquisition, Details and semantic budgets can still limit available evidence; requirements
are retained and final validation remains authoritative. The baseline budget must accommodate
the square of the configured supply ceiling, and every provider request retains its own cap.

Nearby uses at most one search and two references per trip day, within the configured
ceilings. Cached anchor groups remain usable when the external-send allowance is zero.
Assistance uses verified account IDs or the direct guest client address; untrusted forwarded
headers cannot choose a rate-limit identity. Cooldowns and concurrency are process-local,
with no queue or cross-worker quota coordination. GeoDB's global send interval remains binding.
The optional `admission` group configures `per_user_interval_seconds` and `max_concurrent`;
a null legacy daily allowance requires this group. Cancellation and failure release permits.

Acceptance also enables `auxiliary_model_limits` for requirement interpretation, review
profiles, official search, evidence extraction and Product introductions. Caller-supplied
input includes schema and a 2,048-token framing reserve within the acceptance token
allowance in the table. Lower extraction/introduction output caps remain applicable.
Oversized input fails before dispatch without truncating requirements or evidence.
The optional group is absent from legacy snapshots and default development behavior.
It applies through the Product/programmatic dependency factory and explicit tools-CLI policy
selection; injected external clients retain responsibility for their own limits.


## Historical changes

September capacity calibration and transport integration changed operating limits
and moved common transport policy into the shared V1–V3 path. Their original values,
rationale and checks remain in [V3 development](../docs/records/v0-v3/v3-development.md)
and [closeout](../docs/records/v0-v3/v3-closeout.md). The current profile tables above
supersede those historical operating values. Later semantic corrections and short
references retained the same request-owned limits and source-ownership rules.
