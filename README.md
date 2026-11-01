# Dayloom

An LLM-powered travel planner that combines travel information, retrieval and
validation to build more feasible day-by-day itineraries.

Dayloom turns a destination, dates, budget and travel preferences into a trip you
can preview, save and revisit. Built as a Capstone project, it also includes four
independently runnable planners for exploring how external evidence, retrieval
and targeted repair affect itinerary quality.

[Explore the prototype](https://dingzh.cc/Dayloom/prototype/) ·
[Deployment](docs/guides/deployment.md) · [Reproduction](docs/guides/reproduction.md) ·
[Command line](#command-line) · [Documentation](docs/README.md) ·
[Benchmark results](benchmark/report.md)

## Features

- **Plan around your brief.** Set dates, traveler count, whole-trip budget and
  preferences, with destination suggestions and optional preference polishing.
- **Use travel context.** Combine place, route and weather information with
  TripWorld retrieval to inform activity selection and scheduling.
- **Check and refine.** V3 validates the generated itinerary, attempts targeted
  repairs where permitted, and checks the result again. Uncertainty remains visible.
- **Pick up where you left off.** Account-owned planning tasks survive navigation;
  drafts and completed previews can be recovered before you choose to save a trip.
- **Keep your trips together.** Search, rename and manage saved trips, browse
  activity-linked Nearby references, and import or export itinerary JSON.
- **Work from the terminal.** Generate itineraries with any V0–V3 planner and use
  RTPEval to evaluate selected outputs, inspect resource usage and replay saved evidence.

The online link is an interactive design prototype with browser-local accounts
and data. The full application runs locally with FastAPI and PostgreSQL; its
Product interface uses V3; independent command-line entry points expose all four versions.

## How it works

Each version builds on the previous one's planning capabilities:

| Version | Approach |
| --- | --- |
| **V0** | Plain LLM generation from the travel brief |
| **V1** | External place, weather, route and supported current evidence |
| **V2** | V1 plus TripWorld retrieval-augmented generation (RAG) |
| **V3** | V2 plus structured validation, targeted repair and re-validation |

The application is a modular monolith: **React + TypeScript** for the frontend,
**FastAPI + LangGraph** for the API and planning workflows, and
**PostgreSQL + pgvector** for application data and retrieval.
See the [architecture guide](docs/0001-system-architecture.md) for details.

## Project structure

| Path | Contents |
| --- | --- |
| `frontend/` | React/TypeScript Product and local configuration interface; npm lockfile |
| `backend/app/` | FastAPI, Product services, V0-V3 planners, evidence/retrieval and validation/Repair |
| `backend/cli/` | Installed `rtpeval` command dispatcher |
| `backend/evaluation/` | Independent scoring, saved-evidence replay and experiment tools |
| `backend/tests/` | Backend unit, integration and isolated application tests |
| `scripts/` | Product/API/database launchers, migrations and independent V0-V3 entry points |
| `tools/` | Explicit data preparation, validation and engineering diagnostics |
| `benchmark/` | Twelve accepted requests, selected outputs, reports, confirmed blinded answers and offline verifiers |
| `config/` and `product.yaml` | Versioned runtime policies and non-secret deployment settings |
| `data/tripworld/manifest.json` | Pinned retrieval source identity; large runtime data is distributed separately |
| `docs/` | Current architecture/contracts, deployment/reproduction guides and engineering records |
| `pyproject.toml`, `uv.lock`, `compose.yaml`, `.env.example` | Python environment, pinned dependencies, local database service and configuration template |

The [reproduction guide](docs/guides/reproduction.md#3-data-and-supporting-materials-for-submission)
identifies the additional datasets, native evidence and historical code needed for a
complete research hand-in. A source-only download does not contain all of those materials.

## Local development

Prerequisites: **Python 3.12**, **uv**, **Node.js/npm**, and a
**PostgreSQL database with pgvector**. Docker Compose is available for the local
database. Full V3 planning also needs the TripWorld release below and configured
model and travel-provider credentials.

Commands in this README work unchanged in Bash (Linux/macOS) and PowerShell
(Windows). The deployment guide provides both versions of shell-specific steps.
Run commands from the repository root:

1. Copy [`.env.example`](.env.example) to `.env` and set the database password
   and a signing secret of at least 32 characters. Provider credentials can be
   entered later in the local configuration console. Review
   [`product.yaml`](product.yaml) for database and model deployment settings.
2. Install dependencies with `uv sync --locked --group retrieval` and
   `npm --prefix frontend ci`.
3. Follow the [deployment guide](docs/guides/deployment.md) to create the database
   volume, restore TripWorld and prepare both tokenizer caches. It includes the
   complete first-install sequence and common setup failures.

Once those resources are ready, build and start the full application:

```bash
npm --prefix frontend run build
uv run python scripts/migrate_product.py
uv run python scripts/run_product.py
```

Click the settings icon in the bottom-right corner of Product, or visit
[local configuration](http://localhost:5173/config). It opens directly by default;
optional password verification can be enabled on the page. Configure the existing Foundry,
OpenAI and Google Maps services, save, and restart Dayloom. Missing local resources
are shown with preparation guidance; an incomplete installation starts in setup mode.
Optional Check API buttons verify saved service access with small, potentially
billed requests. Startup and Check local readiness do not call provider APIs.
The [configuration guide](docs/guides/development.md#local-configuration-console)
explains access, environment overrides and checks.

Once ready, open [localhost:5173](http://localhost:5173) and create an account to
submit planning tasks and save trips. Local readiness checks do not call external
providers; planning and other online features use real services.

For separate API/Vite development, database setup and troubleshooting, see the
[development guide](docs/guides/development.md).

## TripWorld database release

Download the processed dataset, retrieval text and saved vectors from the
[TripWorld release folder](https://drive.google.com/drive/folders/14VjxQU7jR8PGuiMWes5uaPLIOdrMNaQ0?usp=sharing).
Keep its directory structure, verify `SHA256SUMS.txt`, and follow the included
`README.md` to restore `tripworld.pgcustom` into an empty PostgreSQL database with
pgvector. The tested versions are PostgreSQL **17.10** and pgvector **0.8.2**.

Copy the two packaged sidecars to these repository paths:

```text
data/tripworld/artifacts/retrieval_entities.parquet.manifest.json
data/tripworld/reports/phase5_embedding_run.json
```

The release avoids rebuilding the corpus and its stored embeddings. Keep the
database dump outside Git; online planning still needs provider credentials.

## Benchmark results

Across the project's **12 accepted cases**, V3 ranks first in every automatic
evaluation, with an automatic mean-score order of **V3 > V2 > V1 > V0**.
These results describe the selected cases across historical runtime and evaluation
policies; they are not causal ablations or a guarantee for other trips.

The [benchmark report](benchmark/report.md) includes per-case scores, repair
outcomes, cost and latency. [Blinded review results](benchmark/README.md#final-blinded-results) provide
additional perspectives on itinerary quality.

To verify the saved published materials without provider credentials or a running
database, install the Python dependencies above and run:

```bash
uv run python benchmark/verify_automatic.py
uv run python benchmark/verify_blinded.py
```

The [reproduction guide](docs/guides/reproduction.md) explains the checks, expected
outputs, submission materials, native replay requirements and fresh-experiment boundary.

## Command line

**RTPEval** is the installed CLI for running planners and working with evaluation
material without the frontend. Install it with `uv sync --locked --group retrieval`;
use the same provider and retrieval setup as the application. Node.js, Product
accounts and Product migrations are not required for these commands.

```bash
uv run rtpeval --help
uv run rtpeval generate --help
```

### Generate an itinerary

Save your destination, dates, traveler count, whole-trip budget/currency and optional
preferences in `request.json`, following the
[request example](docs/guides/development.md#independent-version-execution).
Choose dates within the current supported planning window. To run V3:

```bash
uv run rtpeval generate --version v3 --input-json request.json --runtime-config config/runtime.yaml --output-directory artifacts/my-trip-v3 --group-id my-trip --run-id my-trip-v3 --execute
```

Choose `v0`, `v1`, `v2` or `v3` with `--version`; omit `--runtime-config` for V0.
`--execute` makes real provider calls. Without it, the command only prepares input
and configuration offline. Each invocation needs a fresh output directory.
Successful execution saves the itinerary as `result.json`, alongside usage,
provenance and cost reports. V2/V3 require the compatible TripWorld database.

The independent `scripts/run_v0.py` through `scripts/run_v3.py` entry points remain
available for direct planner execution; the
[version execution guide](docs/guides/development.md#independent-version-execution)
describes their runtime and timeout options.

### Evaluate and inspect results

| Command | Purpose |
| --- | --- |
| `generate` | Prepare or run one selected planner and capture its outputs |
| `batch collect / attach-requirements / finalize` | Collect selected outputs, attach independently reviewed requirements and produce an accepted manifest |
| `validate` | Check a manifest and its source material offline |
| `evaluate execute / prepare / replay` | Evaluate online, prepare a run offline, or replay saved evidence offline |
| `suite` | Run and report on multiple selected cases |
| `quality`, `usage`, `cost` | Inspect saved quality, resource usage and explicit-price accounting |

For an already accepted four-version `manifest.json`:

```bash
uv run rtpeval validate manifest.json
uv run rtpeval evaluate execute manifest.json --directory artifacts/my-evaluation --options options.json --prices prices.json --env-file .env
uv run rtpeval evaluate replay artifacts/my-evaluation
```

Online evaluation requires credentials, explicit limits in `options.json`, a dated
price book in `prices.json` and a fresh output directory. Replay uses the saved
evidence without provider calls. To prepare new material, follow the
[collection and requirements-review workflow](backend/evaluation/README.md#installed-generation-and-material-handoff).
The [evaluation guide](backend/evaluation/README.md) also covers V3 paired diagnostics,
blinded review and mechanism reports. Use command-group and leaf `--help` for parameters.

## Documentation

- [Deployment guide](docs/guides/deployment.md) — complete local installation and Product startup.
- [Reproduction guide](docs/guides/reproduction.md) — offline verification, research materials and replay/new-run instructions.
- [Documentation index](docs/README.md) — architecture, planning, retrieval and validation.
- [Development guide](docs/guides/development.md) — environment, application setup and checks.
- [Configuration reference](config/README.md) — provider settings and planning policies.
- [Evaluation guide](backend/evaluation/README.md) — RTPEval workflows and saved-evidence replay.
- [Project status](PROJECT.md) — current engineering state and scope.

## License

[MIT](LICENSE) © 2026 Zihang Ding.
