# TripWorld retrieval data

Dayloom V2/V3 retrieve candidate places from a prepared TripWorld database.
The [database release](https://drive.google.com/drive/folders/14VjxQU7jR8PGuiMWes5uaPLIOdrMNaQ0)
includes saved vectors, so restoration requires no new document-embedding calls.

## Source

The source is [TripWorld at the pinned revision](https://huggingface.co/datasets/CRUISEResearchGroup/TripWorld/tree/421bc1dc63068bb398055b1ce987265fe22415db),
using `metadata/metadata_all.parquet`: **687,173 rows**, approximately **155.5 MB**.
[manifest.json](manifest.json) records the exact revision, SHA-256, size and selected
schema. Reviews and travel-behavior datasets are outside this retrieval corpus.
The upstream dataset card declares `cc-by-nc-4.0`; its original README and provenance
scripts are preserved in the release's `source-and-provenance.zip`.

## Processing

1. Select 11 fields: FSQ identity, name, coordinates, locality, region, country and
   categories, plus Google identity, name and categories.
2. Normalize Unicode, whitespace and category formats; deduplicate aliases and
   categories while retaining missing values and source provenance.
3. Group rows by Google Place ID when present, otherwise FSQ ID. Choose stable
   names and an observed representative coordinate; retain geographic anomaly flags.
4. Apply the versioned [category mapping](category_semantics.v1.json) and construct
   retrieval text from names, locations and categories. Category-derived clues aid
   retrieval; they do not establish current opening hours or other verified facts.
5. Apply retrieval eligibility rules and embed distinct eligible texts with
   `text-embedding-3-small`: 1,536 dimensions, normalized vectors and cosine ranking.
   Multiple entities can share a vector when their text is identical.

The 26 September 2026 release records **647,057 entities**, **580,795 eligible
entities** and **577,011 physical vectors**. Detailed rules belong to the
[retrieval contract](../../docs/0004-retrieval-persistence%28v2v3%29.md#retrieval-entities-and-text);
[tools/data/](../../tools/data/) contains the processing and database-build code.

## Files and outputs

| Material | Location |
| --- | --- |
| Source identity and selected fields | [manifest.json](manifest.json) |
| Category enrichment rules | [category_semantics.v1.json](category_semantics.v1.json) |
| Embedding configuration | [embedding_model.v1.json](embedding_model.v1.json) |
| Reference retrieval queries | [retrieval_queries.v1.json](retrieval_queries.v1.json) |
| Database, stored vectors and build metadata | Release: `tripworld.pgcustom` (approximately 4.43 GB) |
| Required runtime sidecars | Release: `runtime/artifacts/retrieval_entities.parquet.manifest.json` and `runtime/reports/phase5_embedding_run.json` |
| Source notices and reference configuration | Release: `source-and-provenance.zip` |
| Restore instructions and integrity checks | Release: `README.md`, `SHA256SUMS.txt` and `validation/` |

Raw and intermediate Parquet files and working reports stay in ignored local
directories. The pinned source and processing code support a new build; restoration
uses the published dump and sidecars. Regenerating vectors uses provider access and
may not reproduce the original vector bytes.

## Download and restore

Download the release folder beside the source checkout. Follow the
[deployment guide](../../docs/guides/deployment.md) to install dependencies and start
an **empty** local Compose database. From the repository root:

```bash
uv run dayloom prepare ../tripworld-vector-release-20260926
uv run dayloom restore ../tripworld-vector-release-20260926
```

`prepare` verifies the release checksums and installs both runtime sidecars under
`data/tripworld/`. `restore` imports the dump into the configured local database and
refuses an existing populated database. Existing installations retain their data
and skip restoration. Native PostgreSQL instructions are in the release README.

Current connections use `DAYLOOM_DB_*` and the deployment defaults in
`product.example.yaml` or local `product.yaml`. The default database/role is
`dayloom`; the retrieval schema remains `tripworld`. See the
[connection reference](../../config/README.md#deployment-settings) for overrides.

The release's `validation/topk.sql` and recorded results check stored-vector
retrieval parity without API calls. Complete the deployment guide's tokenizer and
provider setup before running V2/V3: new queries still need query embeddings and
live planning uses external services.
