# Local deployment

Run the current Dayloom Product from the submitted source. For the project layout,
see [README](../../README.md#project-structure). To verify the published research
results without running the application, use the [reproduction guide](reproduction.md).

Run commands from the repository root, where `pyproject.toml`, `product.yaml` and
`compose.yaml` are located. Blocks marked **Both shells** work unchanged in Bash
(Linux/macOS) and PowerShell (Windows); shell-specific steps provide both versions.
Use one shell throughout so variables such as `release` remain available. This is
a local, loopback deployment; public hosting is a separate operation.

## 1. Prerequisites and dependencies

| Requirement | Reference |
| --- | --- |
| Python | 3.12; the project requires `>=3.12,<3.13` |
| Python environment | uv; dependency versions are recorded in `uv.lock` |
| Frontend | Node.js 24.x and npm; the reference environment used Node 24.21.0 and npm 11.19.0 |
| Database | Docker with Compose, or PostgreSQL 17.10 with pgvector 0.8.2 |
| Retrieval data | The complete [TripWorld database release](../../README.md#tripworld-database-release), including its checksums and runtime sidecars |
| Online planning | Compatible Azure Foundry deployment, OpenAI embeddings access and Google Maps access |

The Compose file pins its database image by digest. The frontend lockfile also
admits Node 22.12+ within the 22.x series. Install the locked project dependencies:

**Both shells**

```bash
uv sync --locked --group retrieval
npm --prefix frontend ci
```

Dependency installation downloads software packages. It does not execute a planning run.

## 2. Prepare local configuration

Create `.env` only if it does not already exist:

**PowerShell**

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

**Bash**

```bash
if [ ! -e .env ]; then cp .env.example .env; fi
```

Generate a signing secret:

**Both shells**

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use the generated value for `PRODUCT_JWT_SECRET`. Set `DAYLOOM_DB_PASSWORD` to a
private database password. These two settings are edited in `.env`; the configuration
page does not edit database credentials or signing secrets.

Review [product.yaml](../../product.yaml). Its default database is `dayloom`, role
`dayloom`, host `127.0.0.1` and port `55432`; the Product origin is
`http://localhost:5173`. The example Foundry endpoint identifies the author's resource:
replace it with your own endpoint through `/config` before sending provider requests.
The current runtime and dollar tariff recognize deployment identifier `gpt-6-luna`;
arbitrary model/provider selection is not implemented.

The standard setup uses one database for the separate `app` and `tripworld` schemas.
Existing process environment values override `.env` and YAML. Connection overrides
and retained-volume handling are defined in the
[database guide](development.md#local-postgresql-naming-and-storage).

## 3. Start an empty database and restore TripWorld

For a **new installation**, the Compose volume is external and must exist first:

**Both shells**

```bash
docker volume create dayloom_pgdata
uv run python scripts/run_database.py up -d --wait postgres
```

Existing installations must retain their configured volume. The restore below is
for a new, empty database, not a database containing existing application or retrieval
data. The dump already includes the retrieval schema, extension and migration history;
do not run corpus migration, ingestion or embedding first.

Download/extract the database release and set its location relative to the repository
root. These examples place the extracted release beside the source directory;
adjust the relative path if you store it elsewhere:

**PowerShell**

```powershell
$release = "../tripworld-vector-release-20260926"
Get-Content (Join-Path $release "SHA256SUMS.txt") | ForEach-Object {
    if ($_.Trim()) {
        $expected, $relative = $_ -split '\s+', 2
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $release $relative)).Hash
        if ($actual.ToLowerInvariant() -ne $expected) { throw "Checksum mismatch: $relative" }
    }
}
```

**Bash**

```bash
release="../tripworld-vector-release-20260926"
if command -v sha256sum >/dev/null 2>&1; then
    (cd "$release" && tr -d '\r' < SHA256SUMS.txt | sha256sum -c -)
else
    (cd "$release" && tr -d '\r' < SHA256SUMS.txt | shasum -a 256 -c -)
fi
```

Bash uses `sha256sum` on Linux or `shasum` on macOS. The pipeline accepts the release's
Windows line endings without modifying the checksum file. Continue only if every
checksum passes. The subshell keeps the repository as the working directory.

The release's original README illustrates a `tripworld` database and role. Adapt those
names to the current application configuration. With the unmodified `product.yaml`,
restore into **dayloom**, using the role **dayloom**:

**Both shells**

```bash
docker cp "$release/tripworld.pgcustom" postgres:/tmp/tripworld.pgcustom
docker exec postgres pg_restore --exit-on-error --no-owner --no-privileges --username dayloom --dbname dayloom /tmp/tripworld.pgcustom
```

Copy the runtime sidecars:

**PowerShell**

```powershell
New-Item -ItemType Directory -Force data/tripworld/artifacts, data/tripworld/reports | Out-Null
Copy-Item "$release/runtime/artifacts/retrieval_entities.parquet.manifest.json" data/tripworld/artifacts/
Copy-Item "$release/runtime/reports/phase5_embedding_run.json" data/tripworld/reports/
```

**Bash**

```bash
mkdir -p data/tripworld/artifacts data/tripworld/reports
cp "$release/runtime/artifacts/retrieval_entities.parquet.manifest.json" data/tripworld/artifacts/
cp "$release/runtime/reports/phase5_embedding_run.json" data/tripworld/reports/
```

Use the corresponding database/role/container names if you changed them. For a native
PostgreSQL server, run the equivalent PostgreSQL 17 `pg_restore` command against your
empty target database. The restore role must be able to create the `vector` extension.

The dump supplies saved vectors, so restoring does not call an embedding API. The
release's `validation/topk.sql` checks a fixed query using a saved vector; its README
describes comparison with `validation/source_topk.tsv` without an API call.

## 4. Prepare both tokenizer vocabularies

The runtime reads checksum-verified local vocabulary files and does not download
them automatically. Prepare the planner vocabulary:

**Both shells**

```bash
uv run python -m tools.data.prepare_tokenizer
```

Create the embedding cache directory and set its location for the current terminal:

**PowerShell**

```powershell
New-Item -ItemType Directory -Force data/tripworld/tokenizer_cache | Out-Null
$env:TIKTOKEN_CACHE_DIR = (Resolve-Path data/tripworld/tokenizer_cache).Path
```

**Bash**

```bash
mkdir -p data/tripworld/tokenizer_cache
export TIKTOKEN_CACHE_DIR="$(pwd)/data/tripworld/tokenizer_cache"
```

Prepare the embedding vocabulary and verify both caches in the same terminal:

**Both shells**

```bash
uv run python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
uv run python -c "from backend.app.runtime.token_counting import tokenizer; tokenizer(); from backend.app.tripworld.retrieval.query_tokens import tokenizer as embedding_tokenizer; embedding_tokenizer(); print('Both tokenizer vocabularies verified.')"
```

These preparation commands can download public vocabulary files, without model or
embedding inference. For offline installation, supply the existing cache files at
the paths required by [planner token counting](../../backend/app/runtime/token_counting.py)
and [embedding token counting](../../backend/app/tripworld/retrieval/query_tokens.py);
the final verification command remains offline.

## 5. Build and launch the Product

**Both shells**

```bash
uv run python scripts/migrate_product.py
npm --prefix frontend run build
uv run python scripts/run_product.py
```

Product migrations prepare its `app` schema. They do not rebuild the retrieval corpus.
Migration 010 adds image URL/attribution cache fields to the existing previews and trips
tables. Apply it before starting the updated Product API. Existing rows start with empty
caches and acquire images on demand; subsequent reads reuse the saved URLs until an
image fails, a user refreshes it or its resource changes. No image files or additional
cache service need to be deployed.
Click the settings icon in the bottom-right corner of Product, or visit
[local configuration](http://localhost:5173/config). New installations use the displayed
test password; replace it through Configuration access after opening the page.
Existing custom passwords and explicitly disabled verification remain unchanged.
The page saves Foundry endpoint/deployment in `product.yaml` and API credentials in
`.env`. Saved provider changes take effect after restarting Dayloom.

| Configuration card | Existing service use |
| --- | --- |
| Azure Foundry | Model responses and web search, sharing endpoint/deployment/key |
| OpenAI | TripWorld query embeddings |
| Google Maps | Places, Routes and place photographs |
| Unsplash | Optional atmosphere photographs |

Save the settings, finish active tasks, stop the server with Ctrl+C, and start it
again to apply the provider changes. Password verification persists across restarts
and its changes take effect immediately. Keys are stored locally and are not
displayed after saving. See the
[configuration guide](development.md#local-configuration-console) for clearing keys,
environment-locked fields and edit conflicts.

Missing resources or credentials leave the application in setup mode. `/config`
remains available while business APIs are paused. After completing setup, this
command checks local readiness and exits without provider requests:

**Both shells**

```bash
uv run python scripts/run_product.py --check
```

Start normally again, open [Dayloom](http://localhost:5173), create an account and
use the planning interface. The retired `/dev` page is not part of the Product.

Planning, optional API-check buttons, suggestions and image features can contact
external services. Startup and Check local readiness do not validate account access
or send provider requests. Use `/config` for configuration-only access. The optional
Check API buttons may incur charges; their exact bounds belong to the
[configuration contract](../0007-application-operations.md#local-configuration-console).
Web-search charges are excluded from the current dollar guard; its amount is not a
complete generation bill limit.

## 6. Stop and troubleshoot

Ctrl+C stops the application. To stop the database while retaining its volume:

**Both shells**

```bash
uv run python scripts/run_database.py stop postgres
```

| Symptom | Check |
| --- | --- |
| External volume is missing | Create the selected volume before Compose startup; existing installs retain their configured volume. |
| Setup mode or `local_setup_required` | Use Check local readiness and resolve the listed settings/resources, then restart. |
| Missing tokenizer vocabulary | Prepare both caches in step 4; a general tiktoken cache elsewhere does not satisfy the runtime paths. |
| Retrieval compatibility failure | Use the matching dump and both sidecars from the same release. |
| Configuration access rejected | Use the exact configured hostname/origin and the configuration password if enabled; use the documented local recovery procedure if it is forgotten. |
| Saved provider change has no effect | Restart; saved values do not reconfigure in-flight work. |

Separate API/Vite development, isolated test databases and advanced diagnostics are
documented in the [development guide](development.md).
