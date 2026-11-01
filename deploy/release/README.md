# Complete database baseline

These maintainer tools export a consistent Product and TripWorld snapshot and
restore it into an empty independent database. They preserve the approved test
admin, account ownership, stored vectors, application migration records and media
cache. They never generate embeddings, download photos or call provider APIs.

## Tool environment

Use PostgreSQL 17 client tools, Python 3.11 or later and psycopg 3. The deployment
utility image supplies them without installing the full application:

```bash
docker build --target tools -f deploy/docker/baseline.Dockerfile \
  -t dayloom-baseline-tools:local .
```

Supply the connection through `DAYLOOM_DB_URL`, or the `DAYLOOM_DB_HOST`,
`DAYLOOM_DB_PORT`, `DAYLOOM_DB_NAME`, `DAYLOOM_DB_USER` and
`DAYLOOM_DB_PASSWORD` environment fields. The standalone tool's default port is
5432. It does not load the checkout's private dotenv configuration. The
`--dsn-env NAME` option selects another environment variable for an explicit
source or destination. Never place connection strings on command lines.

For a utility container, pass the variable by name with Docker's environment
option, join the appropriate database network and mount input/output directories.
The initializer itself uses PostgreSQL directly and requires no Docker socket.

## Export and verify

Choose a new output directory, the pinned runtime metadata directory and the exact
producer revision. Include the applicable dataset, application and example-media
provenance notices as explicit input files. Notice basenames must be distinct.
Do not include runtime credentials or unrelated private material as notices.

```bash
python -m deploy.release.baseline export \
  --output /output/baseline \
  --runtime-root /resources/tripworld \
  --source-revision SOURCE_COMMIT \
  --notice /notices/TripWorld-README.md \
  --notice /notices/LICENSE
python -m deploy.release.baseline verify /output/baseline
```

Export requires no active planning tasks. It holds a read-only repeatable-read
transaction and shares its exported snapshot with `pg_dump`. The manifest records
the capture time, revision, schema identity, row counts and incremental SHA-256
fingerprints of primary-key-ordered binary table streams. Vector rows are not
aggregated into an in-memory JSON document. The dump excludes database roles and
ACLs, so source database-role credentials are not distributed.

The v1 manifest supports permanent heap tables, ordinary views, their admitted
catalog settings and the constraints, indexes, enabled triggers and ordinary
functions represented in its schema fingerprint. Extension-owned objects and
internal arrays are admitted by the pinned extension version and namespace.
Before export or content comparison, catalog admission rejects objects or settings
that v1 cannot identify: standalone custom types (including enums, domains, ranges
and composites), sequences, aggregates/window functions, event triggers, policies,
nondefault table/column/trigger state and other unrepresented schema/global
objects. Such state requires a separately supported artifact format; it is never
accepted merely because the existing v1 hashes match. This does not change v1
manifest identities or compare factory rows when a valid installed receipt exists.

The command reports the actual dump byte size and an identity derived from the
manifest. The artifact contains the custom-format dump, checksums, matching small
retrieval sidecars and notices. Keep it outside Git history. A failed export is an
incomplete directory, not an installable baseline; existing output is never
overwritten automatically. Checksums detect corruption, while the release's
pinned image digest and expected baseline identity provide the trusted selection.

## Restore and reuse

Set the destination connection and pin the expected baseline identity from the
release manifest:

```bash
python -m deploy.release.baseline restore /baseline --expect-id BASELINE_ID
```

The initializer verifies every artifact, PostgreSQL major version and available
extension version, then takes a session advisory lock. A first restore requires
an empty database and uses one `pg_restore` transaction. Full schema/content
verification precedes insertion of the versioned `app.deployment_baseline`
receipt. All diagnostic messages omit raw PostgreSQL client/driver errors.

A repeat launch with a matching receipt checks compatibility and reports `reused`
without comparing factory rows against later user writes. If restoration committed
but registration was interrupted, exact schema/content fingerprints recognize
that state and complete registration as `recovered`. Other nonempty databases are
preserved and rejected; no clean, truncate or factory-reset operation is provided.
Changing baseline identity does not authorize replacement of an installed database.

Build the separate baseline image from a verified explicit artifact directory:

```bash
docker build --target baseline -f deploy/docker/baseline.Dockerfile \
  --build-context baseline-data=/output/baseline \
  -t dayloom-baseline:local .
```

The image verifies its embedded artifact during the build and restores it on
startup. Application-image and public release integration are separate deployment
stages. Do not infer public availability from a successful local build.

## Controlled acceptance

The CLI tests accept an explicit `DAYLOOM_BASELINE_TEST_URL` whose database name
contains `test`, with PostgreSQL tools available. They create and drop uniquely
named disposable databases; use a separate test cluster with controlled test-only
credentials, never a private runtime connection. A minimal local test image is
available through the `test` Docker target. Tests cover exact admin/cache/vector
preservation, subsequent destination writes, checksum and metadata rejection,
active-task refusal, unknown-target preservation and registration-gap recovery.
Final acceptance additionally restores the approved full baseline in independent
storage and checks its saved-vector parity.

For versioned application archives, initial baseline image bootstrap and the manual
publication workflow, see [controlled release preparation](publishing.md).
