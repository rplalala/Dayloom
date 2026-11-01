# Dayloom

An LLM-powered travel planner that combines current travel information, retrieval
and validation to build day-by-day itineraries. Enter a destination, dates, budget
and preferences, then preview, save and revisit your trip.

[Try the prototype](https://dingzh.cc/Dayloom/prototype/) ·
[Run locally](docs/guides/deployment.md) ·
[Verify the results](docs/guides/verification.md) ·
[Reproduce experiments](docs/guides/experiments.md) ·
[Benchmark report](benchmark/report.md)

The online prototype uses browser-local data. The full application runs locally
with React, FastAPI and PostgreSQL. It supports accounts, recoverable planning
tasks, saved trips, place photographs and itinerary import/export.

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

First installation requires Python 3.12, uv, Node.js/npm, PostgreSQL with pgvector,
the TripWorld release and your own model/travel-provider access. Follow the
[deployment guide](docs/guides/deployment.md) to prepare them.

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
| `scripts/` | Direct launchers, migrations and V0–V3 entry points |
| `tools/` | Data preparation, validation and diagnostics |
| `benchmark/` | Twelve cases, selected outputs, reports and offline verifiers |
| `config/`, `product.example.yaml` | Runtime policies and portable deployment defaults |
| `data/tripworld/` | Dataset identity and retrieval configuration |
| `docs/` | Guides, architecture, contracts and engineering records |

Python and frontend dependencies are pinned in `uv.lock` and
`frontend/package-lock.json`. `.env.example` lists private settings;
`compose.yaml` defines the local database.

## TripWorld database release

Download the [TripWorld release](https://drive.google.com/drive/folders/14VjxQU7jR8PGuiMWes5uaPLIOdrMNaQ0?usp=sharing)
to use V2/V3 without rebuilding embeddings. It contains processed data, saved
vectors, provenance and checksums. The [deployment guide](docs/guides/deployment.md)
covers verification and restoration; large runtime data is distributed separately
from the source tree.

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
