# Dayloom

An LLM-powered travel planner that combines travel information, retrieval and
validation to build more feasible day-by-day itineraries.

Dayloom turns a destination, dates, budget and travel preferences into a trip you
can preview, save and revisit. Built as a Capstone project, it also includes four
independently runnable planners for exploring how external evidence, retrieval
and targeted repair affect itinerary quality.

[Explore the prototype](https://dingzh.cc/Dayloom/prototype/) ·
[Documentation](docs/README.md) · [Benchmark results](benchmark/report.md)

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

The online link is an interactive design prototype with browser-local accounts
and data. The full application runs locally with FastAPI and PostgreSQL; its
Product interface uses V3, while Developer mode exposes all four versions.

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

## Local development

Prerequisites: **Python 3.12**, **uv**, **Node.js/npm**, and a
**PostgreSQL database with pgvector**. Docker Compose is available for the local
database. Full V3 planning also needs the TripWorld release below and configured
model and travel-provider credentials.

From the repository root:

1. Copy [`.env.example`](.env.example) to `.env` and fill in the private credentials,
   database password and a signing secret of at least 32 characters. Review
   [`product.yaml`](product.yaml) for database and model deployment settings.
2. Install dependencies with `uv sync --locked --group retrieval` and
   `npm --prefix frontend ci`.
3. Prepare the database, restore TripWorld, and set up both tokenizer caches using
   the [environment setup guide](docs/guides/development.md#environment-and-local-application).

Once those resources are ready, build and start the full application:

```powershell
npm --prefix frontend run build
uv run python scripts/migrate_product.py
uv run python scripts/run_product.py --check
uv run python scripts/run_product.py
```

Open [localhost:5173](http://localhost:5173). Create an account to submit planning
tasks and save trips. The readiness check verifies local resources without calling
external providers; planning and other online features use real services.

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

## Command line

The four planners have independent entry points at `scripts/run_v0.py` through
`scripts/run_v3.py`; see [version execution](docs/guides/development.md#independent-version-execution)
for inputs and runtime options.

**RTPEval** provides generation, material collection, validation, evaluation and
offline replay. Run `uv run rtpeval --help` to explore the commands. Its material
workflow is selected generation or collection → external requirements review →
attachment and finalization → accepted manifest → automatic report → offline replay.
See the [evaluation guide](backend/evaluation/README.md) for commands, schemas,
credentials and explicit execution limits.

## Documentation

- [Documentation index](docs/README.md) — architecture, planning, retrieval and validation.
- [Development guide](docs/guides/development.md) — environment, application setup and checks.
- [Configuration reference](config/README.md) — provider settings and planning policies.
- [Evaluation guide](backend/evaluation/README.md) — RTPEval workflows and saved-evidence replay.
- [Project status](PROJECT.md) — current engineering state and scope.

## License

[MIT](LICENSE) © 2026 Zihang Ding.
