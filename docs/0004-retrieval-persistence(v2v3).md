# Retrieval corpus and persistence

V2/V3 retrieve prepared TripWorld entities from PostgreSQL/pgvector. The
[dataset README](../data/tripworld/README.md) covers sources, processing, release
artifacts and restoration. This document defines runtime and compatibility rules.

## Offline corpus versus runtime discovery

A pinned [manifest](../data/tripworld/manifest.json) binds source revision, bytes,
rows, checksum and schema. Projection retains FSQ identity/name/geography/categories
and Google identity/name/categories, excluding reviews, behavior and place attributes.
Download validation precedes deterministic processing; source/generated data is
separately distributed while builders, manifests and fixtures are versioned.

Runtime embeds bounded queries and retrieves existing entities. It never rebuilds
the corpus or regenerates document vectors. Google resolution and qualification
are still required before a retrieval opportunity enters authorized planning supply.

## Retrieval entities and text

Group by nonblank Google Place ID, otherwise FSQ ID. Preferred names use normalized
Google-name frequency, then FSQ names with stable ties and aliases. Deduplicate
Unicode/case-normalized aliases/categories; retain constituent FSQ IDs, geography,
spread and country-conflict flags. Choose an observed coordinate medoid, not an
invented average. Different entities may still resolve to one physical venue.

`clean_text` applies NFKC and whitespace collapse without textual null placeholders.
FSQ categories preserve nonempty ` > ` hierarchy segments; Google categories also
accept JSON-list strings and expand underscores. Invalid non-list categories yield
an empty collection.

Entity RAW text emits populated Name, Aliases, Localities, Regions, Countries, FSQ
categories and Google categories in that order, with stable semicolon unions.
ENRICHED appends Description when present. IDs/coordinates remain metadata.
This entity template supersedes the earlier row-text layer; static enrichment adds
retrieval meaning, not current experience or official facts. Established identities
include `tripworld-retrieval-entity-v1` and `tripworld-entity-text-v1`.

## Artifact integrity and ingestion

Enrichment retains selected source rows and appends normalized categories, rule IDs,
direct/inferred semantics, eligibility hints and text. Filtering occurs later.
Fingerprints bind input SHA, schema/artifact/mapping/description/template versions,
mapping payload and writer settings. Parquet 2.6/zstd/dictionary writes use `.part`
then atomic replacement and record output SHA, size and count.

| Table | Responsibility |
| --- | --- |
| `corpus_builds` | Artifact hash, complete manifest, row count and timestamp |
| `entities` | Names, geography, policy fields, exact ENRICHED text/hash and typed provenance |
| `embedding_spaces` | Immutable embedding configuration fingerprint |
| `embeddings` | One normalized vector(1536) per exact text hash/space with vector hash |
| `entity_embeddings` | Entity-to-vector mapping without merging result identities or Top-K slots |

Applied migrations are checksum-checked and immutable. Transaction/advisory locks
protect migration and corpus changes. Ingestion validates provenance, COPY-loads
staging and transactionally updates a full snapshot, removing stale entities.
Changed text requires a new vector; unchanged text can reuse vectors across metadata
updates. RAW vectors are not imported, and unreferenced vectors are not destructively
purged.

The offline builder resumes distinct-text checkpoints and committed batches. Recover
pending batches before changing partitioning. A paid response lost before durable
checkpoint cannot guarantee exactly-once billing. Runtime never invokes this job.

## Persistence and ranking

The established space is normalized `text-embedding-3-small`, 1,536 dimensions,
ranked by exact cosine with stable identity ties. Compatibility binds corpus, text
policy, embedding space, dimensions and integrity; a model name alone does not
promise identical regenerated vectors.

`tripworld-production-policy-v1` excludes, in priority order: ineligible, empty-text,
invalid-coordinate, country-conflict and strictly-over-10-km spread entities. Unknown
eligibility remains available; 1–10-km spread is flagged. Excluded metadata survives.
Coordinate bounding boxes and Haversine checks handle boundaries, poles and dateline;
locality text is not geography. There is no ANN index or arbitrary early truncation.

## Resolution, merge and queries

Known Google IDs reuse compatible evidence or acquire current Details. Missing/failed
IDs may use one bounded name/location fallback per entity, up to three results.
Unresolved ordinary candidates are skipped; required identity uncertainty retains
the shared clarification boundary. There is no corpus-wide Google validation.

Canonical Google IDs unify all actual origins and intent references without duplicate
reward. Resolution alone does not become Google discovery or invent a Google rank.
Early compatible Details may be reused, but static categories cannot become current
hours, price or Review/Profile facts. RAG failure continues with acquired evidence
inside the same request rather than rerunning V1 or interpretation.

Queries use interpreted discovery intents with stable normalization/deduplication and
strength/identity ordering. With no usable intent, use the versioned system-default
attractions query, not an invented user preference. Do not embed the whole structured
request. Query, token, result-scan, resolution and fallback ceilings are separate.

## Runtime lifecycle and observation

Connection/prepare, SQL, fetch/decode and domain construction have separate timings.
SQLSTATE, suboperation timeout, outer deadline, provider failure and cancellation
remain distinct. Cleanup is awaited; no hidden retry or background result mutation
occurs. API usage and actual HTTP sends are different observations; missing is not zero.
Opt-in captures can retain vectors/hashes for exact replay; default logs omit raw text/vectors.

### Passive candidate opportunity export

V1/V2 accept `opportunity_capture_path`; `uv run rtpeval generate` exposes
`--opportunity-capture PATH`. The exporter observes actual pre-RAG, merged, admitted,
qualified and supplied stages with complete origin/fate provenance. It adds no model,
provider, embedding or gate-replay calls and changes no budgets or ordering.

Capture is exclusive and best effort: existing destinations are not replaced, and
storage failure cannot replace the business outcome. Interrupted stages remain
missing. Local capture overhead is unmeasured; final-only outputs cannot reconstruct
history. [Selected generation bindings](contracts/0002-intake-identity-usage.md#selected-generation-opportunity-capture)
define run identity and registration.

## Pinned corpus coverage sidecars

Optional coverage studies use a saved eligible-entity census for an original-input-bound
radius or ordinary non-dateline-crossing box. Exact manifest bytes/hash, text policy,
space, numeric scope, measurement time and declaration timing bind each sidecar.
Entity counts are geographic proxies, not unique-venue coverage or citywide recall.
Independently coded samples retain their own denominators and uncertainty.

`uv run rtpeval research corpus prepare`, `measure` and `export` produce sidecars.
Preparation/export are offline; measurement uses a read-only repeatable-read database
view and checked build identity. Timeout, caps and partial scans cannot yield exact
counts. Complete census zero differs from missing/partial measurement. Research
reporting consumes sidecars without reconnecting to the database or providers.
See the [producer contract](contracts/0001-evaluation-artifacts.md#pinned-corpus-measurement-producer)
and [examples](guides/experiments.md#retrieval-corpus-coverage).

## Reproducibility and limits

Saved releases reuse original vectors without embedding again. Rebuilding through a
provider may differ; exact historical values need retained hashes/checkpoints.
The old Phase 4 validation utility requires local inputs and runs ANALYZE; it is not
a portable read-only check. A new connection does not prove a cold cache, and EXPLAIN
alone does not establish an optimization. Live planning still needs model/travel services.

Implementation: [runtime](../backend/app/tripworld/retrieval/runtime.py),
[migration](../tools/data/tripworld/migrations/001_retrieval.sql) and
[exact-retrieval ADR](adr/0003-persistent-exact-retrieval%28v2v3%29.md).
