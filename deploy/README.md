# Local Docker deployment

Versioned deployment archives contain the Compose definition, public configuration
template, Bash launcher and these instructions. GitHub Releases and GHCR are the
distribution targets; local builds can use the same bundle before publication.
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

## Normal operation

From the extracted bundle directory:

```bash
bash start.sh
docker compose --env-file config/.env stop
docker compose --env-file config/.env logs -f app
docker compose --env-file config/.env restart app
docker compose --env-file config/.env run --rm --no-deps app reset-management-password --directory /instance
```

Use restart after saving provider settings. Changing environment-injected deployment
wiring requires recreation. Every application process waits for the matching
database installation receipt and applies pending checksum-protected migrations.
Repeated startup reuses the installed baseline and preserves subsequent user data;
it does not replay old planning tasks or refresh stored photo URLs. Initialization
failure remains non-ready and must not trigger an automatic data reset.

Keep the database and log volumes plus the configuration directory when stopping
or replacing containers. Never point deployment acceptance at an existing runtime
database or volume. Upgrade and backup procedures must distinguish compatible app
rollback from recovery requiring a pre-upgrade database/configuration backup.
