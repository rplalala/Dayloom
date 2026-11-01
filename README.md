# Dayloom

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker: linux/amd64](https://img.shields.io/badge/Docker-linux%2Famd64-2496ED?logo=docker&logoColor=white)](docs/guides/deployment.md#option-1-docker-recommended)
[![Release](https://img.shields.io/github/v/release/rplalala/Dayloom?label=release)](https://github.com/rplalala/Dayloom/releases/latest)

An LLM-powered travel planner that combines current travel information, retrieval
and validation to build day-by-day itineraries. Enter a destination, dates, budget
and preferences, then preview, save and revisit your trip.

[Prototype](https://dingzh.cc/Dayloom/prototype/) ·
[Deployment Guide](docs/guides/deployment.md) ·
[Verification Guide](docs/guides/verification.md) ·
[Reproduce Guide](docs/guides/experiments.md) ·
[Datasets](data/tripworld/README.md) ·
[Benchmark](benchmark/report.md)

The online prototype uses browser-local data. The full application runs locally
with React, FastAPI and PostgreSQL. It supports accounts, recoverable planning
tasks, saved trips, place photographs and itinerary import/export.

> [!TIP]
> **Quick deployment → [Run the full application with Docker](docs/guides/deployment.md#option-1-docker-recommended)**
>
> Start with Bash, Docker Engine and Compose. The images include the database baseline
> and stored vectors; instance configuration is created automatically. Enter provider
> settings during setup or finish them later at `/config`.

## How it works

Four planners can run independently; the web application uses V3.

| Version | Approach |
| --- | --- |
| V0 | Plain LLM generation from the travel brief |
| V1 | External place, weather, route and current evidence |
| V2 | V1 plus TripWorld retrieval-augmented generation |
| V3 | V2 plus structured validation, targeted repair and re-validation |

The modular monolith uses **React + TypeScript**, **FastAPI + LangGraph** and
**PostgreSQL + pgvector**. See the [architecture](docs/0001-system-architecture.md).

## Local development

For source development and direct V0–V3 execution, use Python 3.12, uv,
Node.js/npm, PostgreSQL with pgvector and the TripWorld release. Follow
[source setup](docs/guides/deployment.md#option-2-run-from-source), or use the
[Docker bundle](docs/guides/deployment.md#option-1-docker-recommended) to run the app.

Once configured, build and start Dayloom from the repository root:

```bash
npm --prefix frontend run build
uv run dayloom start
```

Open [localhost:5173](http://localhost:5173). The bottom-right settings button opens
the local configuration page for providers, database connections and signing keys.
Settings stay in ignored local files. `uv run dayloom check` checks local readiness.

## Verify the research results

The benchmark contains **12 cases and 48 selected V0–V3 outputs**. Verify the saved
automatic results and confirmed blinded assessments without a database or API keys:

```bash
uv sync --locked --group retrieval
uv run rtpeval verify
```

The [verification guide](docs/guides/verification.md) explains the checks, data and
saved-evidence replay. Across these selected cases, the automatic mean-score order
is **V3 > V2 > V1 > V0**. The [report](benchmark/report.md) describes per-case results,
resources and study limitations.

## Command line

Generate an itinerary from a [request JSON](docs/guides/experiments.md#generate-v0v3-outputs):

```bash
uv run rtpeval generate v3 request.json --execute
```

Choose `v0`, `v1`, `v2` or `v3`. The command creates a fresh output directory and
prints its location; `-o DIRECTORY` chooses it explicitly. Omit `--execute` to prepare
the run offline. Online execution uses your provider accounts and can incur charges.

Use `uv run dayloom --help` for local setup commands and `uv run rtpeval --help`
for generation, evaluation and analysis. Follow the
[experiment guide](docs/guides/experiments.md) for the complete research workflow.

## Project structure

| Path | Contents |
| --- | --- |
| `frontend/` | React application and local configuration interface |
| `backend/app/` | API, Product services, V0–V3 planners, retrieval and Repair |
| `backend/cli/` | Installed `dayloom` and `rtpeval` commands |
| `backend/evaluation/` | Independent scoring, saved-evidence replay and analysis |
| `backend/tests/` | Backend unit and integration tests |
| `deploy/` | Bash/Compose installation, Docker images and baseline/release tools |
| `scripts/` | Direct launchers, migrations and V0–V3 entry points |
| `tools/` | Data preparation, validation and diagnostics |
| `benchmark/` | Twelve cases, selected outputs, reports and offline verifiers |
| `config/`, `product.example.yaml` | Runtime policies and portable deployment defaults |
| `data/tripworld/` | Dataset identity and retrieval configuration |
| `docs/` | Guides, architecture, contracts and engineering records |

Python and frontend dependencies are pinned in `uv.lock` and
`frontend/package-lock.json`. `.env.example` lists private settings;
the root `compose.yaml` defines the source workflow's local database.
The separate `deploy/compose.yaml` runs the complete Docker installation.

## TripWorld database release

Docker installations obtain the corpus and stored vectors through the baseline image.
For source-based V2/V3 execution, download the [TripWorld release](https://drive.google.com/drive/folders/14VjxQU7jR8PGuiMWes5uaPLIOdrMNaQ0?usp=sharing)
to reuse existing embeddings. It contains processed data, saved
vectors, provenance and checksums. The [data guide](data/tripworld/README.md) explains
its source, processing and contents; the [deployment guide](docs/guides/deployment.md)
covers setup and restoration. Large runtime data is distributed separately from source.

## Documentation

- [Deployment](docs/guides/deployment.md): install, configure and run the application.
- [Experiment reproduction](docs/guides/experiments.md): generate, review and evaluate new runs.
- [Findings verification](docs/guides/verification.md): check the twelve-case study and replay saved evidence.
- [Development](docs/guides/development.md): API/Vite development, tests and diagnostics.
- [Evaluation reference](backend/evaluation/README.md): complete RTPEval workflows.
- [Design index](docs/README.md): architecture, contracts and implementation records.

## License

[MIT](LICENSE) © 2026 Zihang Ding. Dataset and photograph notices retain their
respective licenses.
