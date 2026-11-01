# Local Docker deployment

Versioned deployment archives contain the Compose definition, public configuration
template, Bash launcher and these instructions. Obtain the public archive from
[GitHub Releases](https://github.com/rplalala/Dayloom/releases/latest), following
the [Docker quickstart](https://github.com/rplalala/Dayloom/blob/main/docs/guides/deployment.md#option-1-docker-recommended).
Images are distributed through GHCR; local builds can use the same bundle.
Docker Desktop is optional. Install Bash, Docker Engine 28+
and a Compose plugin supporting `up --wait --wait-timeout`; the first release
supports Linux amd64 container engines.

Extract the archive and run `bash start.sh`. The launcher resolves its own location,
so the caller's working directory can differ. It creates private configuration
automatically, downloads the selected images, initializes the complete database
baseline and starts Dayloom on `http://localhost:5173`. No source checkout,
Python/Node installation, dataset download or manual restore is needed.

Choose provider entry now or later. `bash start.sh --non-interactive` always
postpones entry and never prompts. Open `/config` afterward to enter Foundry,
OpenAI and Google settings; Unsplash is optional. The first bootstrap prints the
configuration-management password once. It is independent of the retained Product
test account `admin@admin.com` / `admin123456`. Only the management password hash is
stored. Recover management access through the documented host-side reset command,
rather than resetting the Product account or deleting the database.

The source checkout template deliberately uses local image tags and an unpublished
baseline placeholder. For local development select `DAYLOOM_APP_IMAGE`,
`DAYLOOM_BASELINE_IMAGE` and the verified `DAYLOOM_BASELINE_ID` before launching.
Release packaging replaces those defaults with exact release identities.

## Instance configuration

Runtime files live under the generated `config` directory. Provider edits remain
editable because Compose does not inject them as process-environment overrides.
The database service reads the same generated database credentials as the app.
Changing connection fields does not rename or migrate a database or change an
existing PostgreSQL role password. Existing configuration and keys are reused.

Public bootstrap overrides include `DAYLOOM_HOST_PORT`, `COMPOSE_PROJECT_NAME`,
`DAYLOOM_DB_NAME`, `DAYLOOM_DB_USER`, `DAYLOOM_RUN_UID` and `DAYLOOM_RUN_GID`.
The launcher probes the mounted directory's actual ownership and uses a compatible
runtime identity; UID/GID overrides are available for a deliberately prepared
directory. The Windows Docker bind metadata tested here reports root ownership.
The app image defaults to UID 1000, while a compatible explicit runtime mapping can
differ. Do not weaken host directory permissions to bypass an ownership failure.

The application port is published only on host loopback. The database is internal
to the project network. Configuration management authorizes the finite actual
forwarding gateway and preserves Host/Origin, authentication and CSRF checks.
Never expose this local management mode as a public server.

## Initialization recovery

The initializer verifies the release checksums and serializes concurrent imports.
It restores only an empty destination, including the absence of user-defined public
functions, types and extensions. Restoration is transactional; installation identity
is registered only after the restored schema and content match the baseline.
Catalog state outside the [v1 snapshot support boundary](release/README.md#export-and-verify)
is rejected before registration; preserve the target and use a supported snapshot
rather than deleting the additional objects as an automatic repair.

| Observed state | Safe next action |
| --- | --- |
| Database unavailable or still starting | Inspect `postgres` logs and retry startup after storage becomes available. The app independently waits on every process start. |
| Restore interrupted before commit | Retry `bash start.sh`; the incomplete transaction rolls back. |
| Restore committed before installation registration | Retry with the same baseline. Only an exact schema/content match can complete registration without another import. |
| Installed matching baseline | Startup reuses it, retaining later Product writes and media caches. |
| Checksum failure, unknown nonempty storage, different installation identity or incompatible migrations | Preserve the database/configuration and initializer logs. Correct the selected release or recover from a compatible backup before retrying. |

Inspect failures with `docker compose --env-file config/.env logs postgres init app`.
Retry does not authorize deleting volumes, cleaning schemas, editing migration
checksums or fabricating an installation receipt. A deliberate data reset is a
separate destructive operation; do not use it to repair an unclassified failure.
Migration checksums accept the same SQL file with LF or CRLF line endings while
retaining its recorded hash. Other content changes still fail compatibility checks.
An older app refuses migration history it does not recognize. Changing its image
tag alone cannot undo a database upgrade.

`/health` reports process liveness. Before verified installation the app does not
open its HTTP listener. After installation, missing providers permit `/config`
while business APIs return `503 local_setup_required`. This setup state needs
configuration, rather than another baseline import. Readiness checks do not call
providers, embed the corpus or refresh persisted photo URLs.

## Normal operation

From the extracted bundle directory:

```bash
bash start.sh
docker compose --env-file config/.env stop
docker compose --env-file config/.env start postgres app
docker compose --env-file config/.env logs -f app
docker compose --env-file config/.env restart app
docker compose --env-file config/.env up -d --no-deps --force-recreate app
docker compose --env-file config/.env run --rm --no-deps app reset-management-password --directory /instance
```

Use restart after saving provider settings. Changing environment-injected deployment
wiring requires recreation. Every application process waits for the matching
database installation receipt and applies pending checksum-protected migrations.
Repeated startup reuses the installed baseline and preserves subsequent user data;
it does not replay old planning tasks or refresh stored photo URLs. Expired work
retains the existing interruption/cancellation behavior and requires explicit
resubmission. Run one application instance with one worker.

Keep the database and log volumes plus the configuration directory when stopping
or replacing containers. Never point deployment acceptance at an existing runtime
database or volume. Upgrade and backup procedures must distinguish compatible app
rollback from recovery requiring a pre-upgrade database/configuration backup.

## Private operational backups

Finish or cancel active planning tasks first. Run one maintenance command at a
time and avoid editing configuration during it. The source PostgreSQL service
must be running; the app can already be stopped. Select the source by running its
bundle's launcher; maintenance uses only that bundle's `config/.env` and Compose
project. External database URLs or connection fields pointing outside the bundled
`postgres:5432` service are rejected rather than silently backing up another database.

```bash
mkdir -p "$HOME/dayloom-backups"
bash start.sh backup "$HOME/dayloom-backups/before-update.dayloom-backup"
bash start.sh verify-backup "$HOME/dayloom-backups/before-update.dayloom-backup"
```

Use a new absolute directory ending in `.dayloom-backup`, outside the deployment
bundle. The command briefly stops the app, captures a consistent complete logical
database snapshot and private configuration, verifies checksums and resumes an app
that was previously running. Active tasks, existing backup destinations and
unverified installation identities cause rejection. A failed capture can leave a
partial directory; preserve it for inspection and retry with a different name.

The backup retains installation receipt, migration history, accounts/ownership,
subsequent trips/previews/tasks, media metadata, provider settings, management
preferences, database credentials and JWT signing key. Files are restricted to the
runtime owner (`0700` directories, `0600` files where supported). These backups are
unencrypted secrets; keep their host storage private and do not distribute them as
release artifacts. Checksum verification detects changed/missing/extra files, not
the authenticity of an archive from an untrusted sender. Generated backup
directories are excluded from Git and ordinary image contexts.

This operational snapshot differs from a factory baseline export: factory exports
deliberately omit installation receipts and private configuration. Do not use a
factory export as an installed-instance recovery backup. Retain the referenced app
and baseline images with the backup. PostgreSQL roles/ACLs are recreated by Compose;
logs are diagnostics in a separate volume and are not included in this data/config
backup.

## Recover into independent storage

Extract a fresh deployment bundle into a separate directory with no existing
configuration. Choose a new project name and unused loopback port. From that new
bundle run:

```bash
bash start.sh restore-backup "$HOME/dayloom-backups/before-update.dayloom-backup" \
  --project dayloom-recovered --port 5183
```

The launcher verifies all files before copying configuration, refuses an existing
destination project/volume or nonempty database, restores the complete database in
one transaction, then verifies its installation receipt and content inventory.
Only destination project/port/origin, mount ownership and forwarding peer wiring
change; database identity, signing key, management access and provider settings
remain those of the backup. The restored app image comes from the backup, and the
existing installation keeps its original factory baseline identity. Reopen the
Product at the selected port and check account/library content before adopting the
recovered instance. Existing browser sessions can remain valid because the signing
identity is retained; do not run two recovered copies as interchangeable writers.

Recovery never replaces the source instance or deletes either instance's storage.
If restore fails, preserve the destination for inspection. Retry into another new
project and fresh bundle rather than clearing a database or rerunning factory
initialization over existing data.

## Compatible application upgrades

Use the explicit immutable application reference from the target release. Keep the
existing bundle directory and `config`; a new bundle's factory baseline defaults
do not describe an existing installation. For example, after assigning the target
release's digest reference to `IMAGE`:

```bash
bash start.sh upgrade "$IMAGE" \
  --backup "$HOME/dayloom-backups/pre-upgrade.dayloom-backup"
```

Upgrade first creates and verifies a private pre-upgrade backup while the app is
stopped. The candidate image checks local tokenizer/retrieval compatibility,
installation identity and checksum-protected migration history without provider
requests; missing provider keys remain a supported setup state. It applies only
pending supported migrations, retains the installed baseline image/identity, then
persists the selected application image and recreates only the app service. A
repeated compatible upgrade reuses data and does not replay migrations. Corpus
replacement is a separate migration, never an instruction to restore a new factory
baseline.

On rejection or failed startup the app may remain stopped. Keep the backup and
inspect private local logs. Returning to an older app image is supported only when
that image accepts the current migration checksums/history and retrieval resources.
Changing an image tag alone does not undo schema/data changes; an unknown newer
migration fails closed. When compatibility is uncertain or a migration changed data,
recover the pre-upgrade database and configuration into independent storage with
the matching prior image, verify Product content, and then deliberately adopt that
instance. There is no automatic destructive downgrade or factory reset.
