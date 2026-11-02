Run `bash start.sh` from this extracted bundle to start one app service. It creates
private `config/` files and a logs volume, and downloads only the selected app image.
No local PostgreSQL service, baseline image, dataset import or embeddings are created.
Docker Engine 28+, Compose with `up --wait --wait-timeout`, Bash and Linux amd64
containers are required. Docker Desktop is optional.

Open the printed loopback URL at `/config` using the generated management password.
Database and provider settings may be entered later. Save and restart:

```bash
docker compose --env-file config/.env restart app
```

Use your own prepared PostgreSQL database with all matching Product migrations.
RAG is enabled by default and additionally requires pgvector, TripWorld data and
stored vectors. To use only the app schema, explicitly run:

```bash
PRODUCT_RAG_ENABLED=false bash start.sh
```

The launcher saves this override in `config/.env`. No OpenAI key, retrieval sidecars
or embedding tokenizer is required when RAG is disabled. V3 keeps Google discovery,
Foundry evidence, validation and Repair. The planner tokenizer, app database and
other required credentials remain necessary. The **Enable TripWorld retrieval (RAG)**
switch at `/config` can also save this override. The page shows the active policy
and skipped checks; changes require restart. Existing keys and database contents are
retained. This is a deployment option, with the full policy documented in the
[configuration reference](https://github.com/rplalala/Dayloom/blob/main/config/README.md#product-rag-policy).

A complete `DAYLOOM_DB_URL` can include
`sslmode=verify-full` and a trusted CA path under `/instance` (the mounted `config/`
directory). An unreachable database, TLS failure, missing/newer migrations, or
incompatible corpus/vector space (when RAG is enabled) keeps business APIs in setup mode. No database
restoration or schema migration is applied by light startup. Compatibility checks
make no paid model, embedding, map or photo requests.

The remote database administrator prepares or upgrades data separately. Use a
dedicated database/role per independent installation; do not distribute a shared
production database credential. Configuration belongs to this instance and is
retained between restarts. Provider requests after setup use this instance's keys.

Stop/start and inspect logs with:

```bash
docker compose --env-file config/.env stop
bash start.sh
docker compose --env-file config/.env logs -f app
```

Use a fresh directory for full versus light deployment. Back up the remote database
through its provider and retain private configuration separately; the full bundle's
database backup/restore and baseline-upgrade commands do not apply here.
For management-password recovery, run the app image's `reset-management-password`
command with the same `config/` mount. This mode supports loopback local access;
public hosting needs its own proxy and security configuration.
