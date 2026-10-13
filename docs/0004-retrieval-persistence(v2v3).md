# Retrieval corpus and persistence

Status: Implemented V2/V3 retrieval architecture, consolidated 2026-10-03.

## Offline corpus versus runtime discovery

TripWorld metadata is prepared offline into deterministic entity/text artifacts. The
[entity and text rules](#retrieval-entities-and-text) define grouping and representation;
retrieval relevance does not establish current factual availability.

Only the established metadata input is required; reviews, travel-behavior and place-attribute
datasets are not implicitly part of the corpus. Exact revision, checksums, field selection
and schema are owned by versioned manifests and preparation code. Large source/generated
artifacts remain ignored; small fixtures and build logic are versioned.

The pinned [source manifest](../data/tripworld/manifest.json) owns revision, bytes, rows,
checksum and logical input schema. Projection retains FSQ identity/name/coordinates/locality/
region/country/categories and Google name/categories/identity; reviews, behaviors and attributes
are excluded. Download validation checks size/hash/schema/count before deterministic processing.
Profiles inspect identity/coordinate coverage, category distribution, duplicate identities and
geographic anomalies. Source-row counts and historical anomalies remain dated observations;
they are not silently recomputed or assumed to describe a new artifact.

Runtime V2/V3 embeds bounded queries and retrieves candidate entities. It does not rebuild
the corpus or regenerate document vectors. Google resolution and canonical merging then
feed the shared supply pipeline. Retrieval opportunity must still pass admission and
evidence policy before it can become an authorized planning candidate.

## Persistence and ranking

PostgreSQL plus pgvector is the primary retrieval store. The established embedding space
uses `text-embedding-3-small`, 1536 dimensions, normalized vectors and cosine ranking.
Compatibility checks bind corpus, text policy, embedding space, dimensions and integrity.
Provider model names alone do not guarantee byte-identical regenerated embeddings.

Search applies production eligibility and coordinate-based geography, then exact cosine
ranking with stable identity tie-breaks. Bounding boxes and Haversine circle checks handle
boundaries, poles and the dateline; locality strings are not a geographic substitute.
Known country contradictions differ from missing country information. The current design
has no ANN index, shadow-table migration or arbitrary early candidate truncation.

Database migrations record schema versions and checksums. Ingestion can resume from its
declared checkpoints without silently mixing incompatible corpus/space identities. A new
offline build or index change is separately scoped work, not a runtime side effect.

## Runtime lifecycle and observation

Runtime retrieval distinguishes connection/prepare, query execution, fetch/decode and domain
construction. SQLSTATE is recorded when available; outer deadlines, SQL suboperation timeout,
provider errors and user cancellation remain distinct. Owned cleanup is awaited and there
is no background result mutation or hidden retry. Offline embedding retry/batch policies
must not be confused with runtime single-request limits.

Opt-in development captures retain actual vectors and hashes for replay. Default production
logging does not save raw user text/vectors. API usage and observed HTTP sends are different
measurements; missing historical usage does not become zero. Exact replay requires matching
artifacts and configuration, not simply a matching model name.

### Passive candidate opportunity export

The V1/V2 public runner accepts optional `opportunity_capture_path`; both its native
CLI and installed `rtpeval generate` expose `--opportunity-capture PATH`.
Installed generation binds the capture to the selected run ID rather than the trace
UUID; [generation handoff](contracts/0002-intake-identity-usage.md#selected-generation-opportunity-capture)
owns identity forwarding, manifest references, missingness and registration boundaries.
With no path, the existing acquisition flow is unchanged. The
[benchmark workflow](../benchmark/README.md#workflow-and-responsibilities) selects
this capture for V1/V2 candidate-process analysis; runtime use outside that
workflow remains opt-in.
The caller-owned exporter observes the actual pre-RAG Google pool, merged discovery,
admission, normally qualified Details and selected supply at their existing seams.
It preserves Google query origins and complete native RAG provenance/fates. It adds
no search, embedding, model call, gate replay or corpus operation, and changes no
prompt, planner/model schema, search order, budget or domain output.

Export is exclusive and best effort: an existing destination is not replaced, and
serialization/storage failure cannot turn success into failure or replace the
original exception/cancellation. Failure/cancellation exports retain stages reached
before interruption; missing stages remain missing. Runtime clocks remain real;
optional local normalization/storage overhead is not measured as a performance result.
Historical traces and final-only results do not reconstruct missing stage history.
The source-bound artifact and independent scheduling contract belongs to
[canonical opportunity observations](contracts/0001-evaluation-artifacts.md#canonical-candidate-opportunity-observations).

## Pinned corpus coverage sidecars

Corpus measurement and these coverage sidecars are an explicitly selected optional
study under the [benchmark workflow](../benchmark/README.md#optional-work-compared-with-the-initial-plan).
Ordinary candidate POI process analysis uses passive stage captures and applicable
independent relevance reviews without a corpus census. The runtime database and
its source identity remain part of RAG generation; the tools below are retained.

When corpus coverage is selected, the offline relevance research track imports a
saved eligible-entity census for an original-input-bound fixed geographic scope.
The pinned manifest's exact bytes,
artifact hash, text policy and embedding space remain part of that sidecar's
identity; selected RAG provenance must match. Each profile fixes case scopes and
declaration timing before assigning coverage strata; each sidecar retains its
measurement method and time.
Radius scopes and ordinary non-dateline-crossing bounding boxes have explicit
numeric coordinate bounds. The report does not infer a scope from locality text.

Eligible corpus entities can share one resolved Google venue, so their count is a
geographic/entity proxy. Optional interest coverage describes an independently
coded saved sample with its own denominator and uncertainty. These measurements
do not establish citywide recall or unique venue coverage. Complete census zero
is distinct from a partial subtotal or missing measurement; SQL timeout,
truncation and retrieval failure retain unavailable counts and reasons.

Installed `research corpus prepare/measure/export` produces source-bound sidecars
for numeric radius or ordinary bounding-box scopes. Preparation and saved export
stay offline; database measurement requires explicit access and a read-only
repeatable-read view. Exact artifact bytes or checked database build identity bind
the measured corpus to its manifest. Production eligibility, text policy and
embedding space remain unchanged. Bounded scans count entities rather than venues;
caps, timeouts and unavailable observations cannot supply exact counts. The
[producer contract](contracts/0001-evaluation-artifacts.md#pinned-corpus-measurement-producer)
owns source formats, budgets, completion records and export validation;
[installed examples](../backend/evaluation/README.md#measuring-and-exporting-pinned-corpus-coverage)
show the caller-prepared material and commands.

Research reporting consumes these sidecars without connecting to PostgreSQL,
collecting provider evidence, regenerating vectors or replacing sparse inputs.
Wire schemas, snapshot/scope checks, sample coding and predeclared/retrospective
strata are defined once in the
[independent relevance contract](contracts/0001-evaluation-artifacts.md#independent-interest-relevance-and-corpus-coverage).

## Operational limits

Coverage and performance vary with geography, source identity quality and database state.
A new connection is not proof of a cold cache, and EXPLAIN observations are not a completed
optimization. Setup, backup and validation commands live in the
[development guide](guides/development.md); no command in this document authorizes
live model calls, maintenance or a corpus rebuild.

Implementation: [runtime retrieval](../backend/app/tripworld/retrieval/runtime.py) and the tracked
[retrieval migration](../tools/data/tripworld/migrations/001_retrieval.sql).
See [ADR: persistent exact retrieval](adr/0003-persistent-exact-retrieval%28v2v3%29.md).

## Retrieval entities and text

Group by nonblank Google Place ID, otherwise FSQ ID. Source identity does not mean current Google
verification. Preferred names use normalized Google-name frequency then FSQ names with stable
ties/aliases/categories. Unicode/case normalization removes duplicated aliases/categories. Use
an observed coordinate medoid, not an invented average; preserve constituent FSQ IDs, geographic
values and spread/country-conflict flags. Different IDs may still represent one real place.

Documents contain names/alternative names, locality/region/country and categories. IDs and
latitude/longitude remain metadata, not embedding text. RAW/ENRICHED entity texts are deterministic;
versioned category enrichment adds retrieval meaning, not experience/official facts. Null handling
must not invent descriptions. The exact template/policy remains in corpus/entity builders and
versioned data/tripworld manifests. retrieval_entities.parquet, tripworld-retrieval-entity-v1 and
tripworld-entity-text-v1 identify the established entity layer. Its original hashes/counts and
earlier observed anomalies remain in [V2 development](records/v0-v3/v2-development.md).

## Artifact integrity and text layers

Projected Arrow schema follows manifest logical types. Corpus enrichment retains all selected
source rows and appends normalized FSQ/Google categories, semantic rule IDs, direct/inferred semantics,
eligibility hints, retrieval_description and retrieval_text. Production filtering happens later,
not by silently deleting source rows during enrichment. Fingerprints include selected artifact SHA,
schema/artifact/mapping/description/template versions, mapping payload and Parquet writer settings.
A compatible artifact plus matching manifest can be reused; writes use a temporary .part then atomic
replacement, followed by output SHA/size/count metadata. Current writer uses Parquet2.6, zstd and
dictionary encoding. This repeatability contract does not imply provider/API regeneration is bit-identical.

## Null, category and entity-text formatting

clean_text applies NFKC and whitespace collapse; null/blank values remain absent. FSQ category
paths retain nonempty hierarchy segments separated by ` > `. Non-list category input produces
an empty collection. Google categories also expand valid JSON-list strings, replace underscores
with spaces, and casefold-deduplicate normalized values. No textual null placeholder is invented.

The entity-level RAW text emits only populated lines in this order: Name, Aliases, Localities,
Regions, Countries, FSQ categories, Google categories. Multi-values use stable semicolon-separated
unions. ENRICHED appends Description only when one exists. This entity template differs from the
earlier row-level Name/Alternative name/Location/Categories/Description formatting; they are
successive corpus layers, not two competing runtime templates. IDs and coordinates remain metadata.

## Schema, ingestion and resumability

corpus_builds records artifact hash, complete manifest, row count and timestamp. entities stores
Google ID, normalized names, geography/policy fields, exact ENRICHED text/hash, entity content hash
and typed JSONB metadata (aliases, FSQ provenance, categories, locality sets and anomaly flags).
embedding_spaces is keyed by immutable configuration fingerprint. embeddings stores one normalized
vector(1536) per exact text hash/space, plus vector hash and generation metadata. entity_embeddings
maps each eligible entity to its compatible text vector: text dedup saves physical storage without
merging distinct entity result identities or Top-K slots. RAW vectors are not imported.

Applied migration files cannot be edited. Initial migration
is transactional and advisory-locked. Ingestion validates Parquet hash, builder/text versions and
row provenance, COPY-loads staging, validates counts/duplicates, then performs transactional
content/version-aware upsert and removes stale entities for a full snapshot. Build locks prevent
corpus replacement during embedding. Changed text cannot reuse an old vector; unchanged text can
reuse vectors despite metadata changes. Unreferenced vectors are not destructively purged.

Production policy tripworld-production-policy-v1 excludes ineligible, empty-text, invalid-coordinate,
country-conflict and strictly-over-10-km spread entities. Unknown eligibility remains available;
excluded metadata is retained. Remaining 1-10-km spread flags are visible, not repaired identities.
The reason ordering above is the exclusion priority. Historical counts and cost/storage estimates
are in V2 development with their measurement conditions.

The offline builder processes missing distinct text hashes, content-addressed checkpoints and
binary COPY-upserts successful batches. Existing compatible vectors are skipped. A failed DB batch
rolls back only that batch; completed checkpoints remain recoverable. Recover pending batches before
changing batch partitioning. A lost paid response before durable checkpoint cannot guarantee exactly-once
billing. Runtime queries never execute ingestion, migration or this global embedding job.

## Resolution, merge and evidence

Known Google IDs reuse compatible evidence or request required current Details. Missing/failed
IDs may use bounded name/location fallback (one fallback per entity, up to three results).
Unresolved ordinary RAG candidates are recorded and skipped; unresolved REQUIRED identity keeps
the shared clarification boundary. No corpus-wide Google validation occurs.

Canonical Google ID determines one shared candidate. Preserve all real discovery origins and
intent references without duplicate rewards. Google resolution of a RAG place is not itself
Google discovery. Do not invent Google rank or equate cosine with rank. Early RAG Details can
be reused in shared acquisition, while cheap admission fields remain stage-aligned. Static
categories/enrichment cannot become current opening, price or Review/Profile facts.

RAG failure retains acquired Google and resolved RAG evidence and continues the same request;
it does not rerun V1, interpretation or paid work. V1 has no retrieval extension. Nearby remains
post-primary and uses actual scheduled anchors with unchanged independent budgets.

## Query construction and reproducibility boundary

Queries come from existing interpreted DiscoveryIntent, normalize/deduplicate text and merge
intent/requirement provenance in stable strength/identity order. No usable intent uses the
versioned system-default top-attractions query, never an invented user preference. Dates,
money, traveler count and internal identifiers are not embedded as a whole request. Query
count/length/token, result-scan, resolution and fallback ceilings remain separate runtime limits.
Unresolved ordinary entities are skipped; required identity uncertainty preserves clarification.

Functional reconstruction uses pinned source manifests, deterministic builders, migrations,
lockfile and an explicitly authorized offline embedding job. A source clone alone does not
distribute the original vectors or database volume. The separate [release/restore instructions](../README.md#tripworld-database-release)
describe a saved database dump and compatible sidecars for reusing stored vectors without
regeneration; verify the packaged checksums and runtime compatibility before import.
Rebuilding through the provider cannot guarantee identical vectors. Saved hashes/checkpoints
are needed for exact historical values. The historical validation
utility requires local Phase 4 inputs and executes ANALYZE; it is not a portable read-only
clean-room check. The external release does not recreate live provider evidence or make
online planning independent of its model/travel services.
