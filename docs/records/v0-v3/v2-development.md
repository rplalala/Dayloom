# V2 retrieval engineering evidence

Engineering observations from September–October 2026. Current behavior belongs to
[retrieval design](../../0004-retrieval-persistence%28v2v3%29.md); data lineage and
restoration belong to the [dataset README](../../../data/tripworld/README.md).
Local paths below identify historical evidence, not shared installation dependencies.

## Corpus foundation and embedding choice

Phase 4 was accepted on 18 September 2026 before runtime integration. Grouping 687,173
source rows produced 647,057 entities: 526,682 Google-ID-backed and 120,375 FSQ-only.
30,633 Google IDs grouped multiple FSQ rows, removing 40,116 duplicate retrieval slots.
There were three empty texts, nine invalid/missing coordinate entities, 2,847 groups
with spread above 10 km and 449 country conflicts; anomaly categories overlap.
Observed medoids preserved coordinates without repairing upstream identity errors.

The entity artifact was 177,556,609 bytes, SHA-256
`a0de2721b0b8c1581d78496bfe06da1c3c7dc46cab2a7454c171504732c808f7`,
from TripWorld revision `421bc1dc63068bb398055b1ce987265fe22415db`.
The API strategy selected normalized 1,536-dimensional `text-embedding-3-small`;
no shortened-dimension comparison or immutable provider weight snapshot was claimed.

The sample embedded 2,118 entities per text variant and 24 queries: 69 successful
requests, no retries, 270,778 reported tokens and USD 0.00541556 reference cost.
Full-text estimates were 39,160,088 RAW / 49,605,198 ENRICHED tokens. These are dated
usage/price calculations, not invoices or promised regeneration costs.

## RAW and ENRICHED observations

Six destinations, 12 bilingual intents, two variants and two eligibility settings
produced 576 search cases. Enrichment improved several park/library/nightlife examples,
but also reinforced outdoor results for indoor queries and name/category contamination.
It supplied no reliable crowding or public-access evidence. RAW/ENRICHED overlap was
78.61% at Top-5; English/Chinese Top-5 overlap was 57.78% RAW and 61.39% ENRICHED.
Overlap measures ranking change, not accuracy; no relevance-labelled precision/recall
or population-weighted quality estimate was produced.

Explicit eligibility removed labelled ineligible results by construction while retaining
unknowns. No duplicate entity IDs or representative-coordinate radius violations appeared
in the measured Top-K, but anomalous merged entities remained. Increasing K widened supply
and off-intent exposure. The sample supported metadata filtering and exact geographic
ranking, not a universal similarity threshold or category ban.
Evidence: `data/tripworld/reports/phase4_spike.json`; offline gate: 644 tests passed.

## Persistent database and vector build

Phases 1–5 were accepted as a technical baseline on 18 September, before complete V2
runtime acceptance. PostgreSQL 17.10/pgvector 0.8.2 backed persistent retrieval.
The local Docker volume is `dayloom_pgdata`. Initial ingestion wrote 647,057 rows in 100.57s;
an unchanged rerun took 83.76s with zero changed/removed rows. Production filtering
left 580,795 eligible entities backed by 577,011 distinct text vectors.

ENRICHED entered production with content-addressed vectors, checkpointed batches and
checksum-locked migrations. Five Google-ID sanity lookups succeeded; this was no
corpus-wide identity audit. Exact cosine retained separate entity slots despite shared
vectors. Query/sample artifacts and vector hashes bind historical measurements.

## Runtime integration and initial failures

On 19 September, RAG joined discovery before shared admission, preserving canonical
origin unions and compatible Details reuse. A module-name collision stopped full-suite
collection; affected runner/discovery checks passed, but that was not a full pass.
The 20 September standard regression then passed 860 tests with nine database opt-ins
skipped. The first bounded live attempt exercised Google-only degradation, leaving
normal RAG unvalidated at that checkpoint.

SQL timing and identity failures were investigated separately. Existing joined/vector
storage involved EXTERNAL/TOAST access and highly variable execution; a new connection
was not a controlled cold-cache experiment. An inline-vector shadow-table proposal
was deferred. No storage optimization or ANN migration was performed.

## Bounded normal RAG validation

A separately selected development override used SQL 60s / RAG 180s, preserving original
SQL, corpus and work ceilings. It changed waiting bounds rather than performance.
The affected gate passed 94 tests. Two read-only Tokyo controls returned identical ten
IDs/scores with execution 23.914s then 0.962s, without cache flushing or new embeddings.

One fresh Tokyo V2 request on 20 September used two interpreted queries and one embedding
batch. Twenty distinct returned entities led to six successful direct-ID resolutions,
three admissions, one normally enriched/supplied RAG-only candidate and one scheduled
RAG-only visit (Beni Museum). Required Meiji Jingu was scheduled; five distinct places
were scheduled from eight supplied. Fourteen unprocessed entities were capacity omissions,
not failed identities. The observed path established bounded RAG contribution, not a
coverage estimate, performance SLA or quality advantage. Mixed-origin overlap and fallback
were not exercised. Actual query vectors were retained; earlier missing vectors stayed missing.

Evidence: `effective_config.json`, `live_manifest.json`, `local_results.json` and the
Phase 4/5 reports in the original local data/artifact trees. Deleted recovery snapshots
under `phase6_source_snapshots` cannot restore the uncommitted intermediate overlays.

## Embedding timeout test diagnosis

On 2 October, base `3427784b87d5864aba25dcba8b48430ec4de9dac`, the test's 20-ms deadline
could finish before a mock handler entered, while the test waited indefinitely on the
handler event. Cold SDK initialization triggered the race; minimal real-SDK/MockTransport
probes reproduced it without Retrieval, database or usage hooks. Metadata warming and
Selector loop policy did not fix the unbounded handshake. Runtime cancellation occurred;
no production retrieval defect was established.

Test-only correction `b18daef4af2fecba36d7b84315c8946a772aeae8` directly awaited the timeout
task, bounded caller-cancellation handshake and consumed children in cleanup. A five-second
test deadline allowed cold setup, with a separate ten-second watchdog. Original source
reproduced one failure/one pass; repaired parameters passed independently, the module
passed 16 tests, and the full backend passed 2,234 with ten skips. Production code and
limits were unchanged. Asyncio bounds remain cooperative, not preemption of synchronous work.
Evidence: `thesis_notes/evaluation/debug/2026-10-02-embedding-timeout/`.

## Interpretation limits

Engineering tests, bounded live contribution and corpus measurements are different
observations. Later shared supply/transport changes do not retroactively validate old
runs. Exact reconstruction needs compatible source/text/vector/configuration artifacts;
provider re-embedding is not guaranteed byte-identical. [V2 milestones](v2-milestone.md)
retain accepted lifecycle boundaries.
