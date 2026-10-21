# Dayloom

Dayloom is an LLM-based travel-planning Capstone project with four independently runnable versions: V0
uses plain model generation, V1 adds external travel information, V2 adds TripWorld retrieval,
and V3 adds validation, targeted repair and re-validation. [PROJECT.md](PROJECT.md) records
the current engineering state and evidence boundaries.

## Product design and prototype

- [Try the online prototype](https://dingzh.cc/Dayloom/prototype/)
- [GitHub Pages default address](https://rplalala.github.io/Dayloom/prototype/)
- [Fixed r7 source and build instructions](https://github.com/rplalala/Dayloom/tree/b30eb3814513b12d7869ca8a5c59f0b7401d45d6/r7)
- [Unified frontend/backend specification #198](https://github.com/rplalala/Dayloom/issues/198)

The provisionally accepted r7 prototype defines the Product visual and interaction
baseline: editable travel briefs, accounts, multiple drafts, recoverable planning tasks,
itinerary previews, manual saving and activity-linked Nearby references. Its source and
preview are maintained on the dedicated `prototype/dayloom` branch.

Accounts, tasks and persistence in the prototype are browser-local simulations. The
implemented application has a separate FastAPI/PostgreSQL lifecycle, described below
under [Current application](#current-application).

## Benchmark results

The [final benchmark report](benchmark/report.md) compares 12 accepted cases. For
reliable, feasible itineraries, the final ranking is **V3 > V2 > V1 > V0**.

V3 ranks first in automatic evaluation in all 12 cases and has the best overall
mean rank in both blinded reviews. Validation and repair reduce overcrowded
schedules, with selected-run costs and times in a similar range to V2. V2 is the
strongest alternative; V0 is much faster and cheaper for initial drafts. The
V1/V0 distinction is weak: each wins six automatic comparisons against the other.

The human review agrees with the final order; the model review places V0 second.
The report keeps the three evaluations separate and explains score gaps,
experience differences, cost trade-offs and historical evaluation-policy limits.

## Command line

Run `uv sync --locked --group dev` from the repository root to install the editable
project. Use `uv run rtpeval --help`, group help and leaf help to inspect parameters.
The primary flow is selected material -> external requirements review -> accepted
manifest -> automatic report -> offline replay.

| Command | Does | Requests and main output |
| --- | --- | --- |
| `generate` | Prepares or explicitly runs one selected V0–V3 Planner; optional registration | Preparation offline; `--execute` online; capture and separate registration status |
| `batch collect` | Copies explicitly selected existing sources | Offline; unqualified `staging.json` |
| `batch attach-requirements / finalize` | Attaches external reviewed requirements, then gates a complete batch through native intake | Offline; `attachment.json`, then accepted `manifest.json` |
| `validate` | Checks a source-bound native manifest | Offline; intake JSON, without scoring |
| `evaluate execute / prepare / replay` | Produces the automatic report, optionally prepares or replays saved evidence | Execute online; prepare/replay offline; report, source bindings and receipts |
| `quality`, `usage`, `cost` | Reads saved independent quality, usage or explicit prices/bills | Offline; separate descriptive reports |
| `pair`, `controlled`, `review`, `mechanism` | Operates distinct specialized tracks | Offline; controlled replay runs frozen V3; external review participation stays separate |
| `advanced`, `dev` | Exposes individual evidence tools and development tools | Inspect leaf help; explicit opening/smoke execution can be online |

For an already accepted four-version manifest, the shortest report route is:

```powershell
uv run rtpeval evaluate execute manifest.json --directory artifacts/fresh-evaluation --options options.json --prices prices.json --env-file .env
uv run rtpeval evaluate replay artifacts/fresh-evaluation
```

Execute requires explicit limits, a dated price book, credentials and a fresh directory;
applicable reviewed contexts can be supplied explicitly. It emits the automatic quality
report without manual preparation/digest copying or a subsequent scoring command. No
retry, resume or supplemental opening assessment runs implicitly. Exit 0 means processing
completed and can coexist with FAIL, UNKNOWN or unavailable values. Processing, acquisition
and evidence statuses remain separate. See [automatic evaluation](backend/evaluation/README.md#installed-automatic-evaluation).

For new material, save the complete original `planning_request_2` request and declare
explicit group/run IDs and capture slots in `selection.json`. The configuration uses
`selected_workflow_1`; every selected version has its own invocation and fresh capture.
This example executes only its declared V0 slot:

```powershell
uv run rtpeval generate --version v0 --input-json material/input.json --output-directory material/captures/v0 --group-id case-1 --run-id case-1-v0 --execute --register-batch material/selection.json --registration-directory artifacts/staging-v0
```

Repeat only explicitly selected V1, V2 and V3 invocations with their matching slots and
runtime/RAG settings. Each registration preserves other slots; unstarted slots stay
blocked. The last complete staging remains `pending_review`. Generation needs no
RequirementSpec. Planner invocation and registration have separate statuses; a successful
Planner with failed registration retains the result and exits 2. See
[generation and registration](backend/evaluation/README.md#installed-generation-and-material-handoff).

An alternative uses four existing results: declare their exact result, usage, provenance
references and producer completion in `collection.json`. No latest/best run is selected
and collection never regenerates material:

```powershell
uv run rtpeval batch collect material/collection.json --directory artifacts/staging
```

Operate external **Codex `gpt-6.1-sol`, reasoning effort `high`** separately: an author
reads the complete original request and produces a draft RequirementSpec; a distinct
reviewer checks that draft against the same request and saves the final reviewed spec.
Retain actual source/hash bindings, execution identities/configuration/times, transcript
exports and the draft-to-final lineage in `handoff.json`. Planner interpretation, generated
outputs, scores and mechanisms are excluded from that review. The CLI neither authors
requirements nor launches/messages the agent. Review is agent review, with semantic
completeness and actual provenance remaining operator responsibilities.

After either collection route, attach the corresponding staging and finalize:

```powershell
uv run rtpeval batch attach-requirements artifacts/staging/staging.json material/handoff.json --directory artifacts/attached
uv run rtpeval batch finalize artifacts/attached/attachment.json --directory artifacts/finalized
uv run rtpeval validate artifacts/finalized/manifest.json
uv run rtpeval evaluate execute artifacts/finalized/manifest.json --directory artifacts/fresh-evaluation --options options.json --prices prices.json --env-file .env
uv run rtpeval evaluate replay artifacts/fresh-evaluation
```

For the generation route, substitute the latest explicit registration's `staging.json`
for `artifacts/staging/staging.json`. Every destination above must be fresh. Keep original
selection, capture, source and handoff files accessible and byte-identical until
finalization. `incomplete`, `blocked` and `pending_review` staging is unqualified even when
collection exits 0. Required workflow completion is distinct from quality/PASS: normal V3
partial or rejected Repair can qualify, while failed required retrieval cannot. Explicit
unavailable usage remains unavailable; new capture failures are not relabelled successful.
Native validation exits 0 for accepted material and 2 for correction/argument errors.
A standard manifest alone establishes no formal benchmark.

Detailed schemas and handoff parameters: [material operations](backend/evaluation/README.md#installed-generation-and-material-handoff),
[current producer contract](docs/contracts/0002-intake-identity-usage.md#producer-material-handoff).
Accepted benchmark candidate bundles belong in [`benchmark/`](benchmark/README.md),
with an immutable validated manifest and source material per case revision. Evaluation
outputs remain in explicit fresh directories under `artifacts/`.
Legacy module commands and historical switches retain their meaning in the
[evaluation package guide](backend/evaluation/README.md); smoke/history remain separate
under the [development guide](docs/guides/development.md).
Commands are operational references and grant no live-run authorization.

## Current application

The Product page at `/plan` provides an editable V3 travel brief. Guests can prepare
requirements and read examples; an account is required to submit a planning task,
save drafts or manage private trips. Submitted tasks survive browser navigation and
can be recovered or explicitly stopped. A completed task creates a preview; Save
creates a trip, while Discard records the decision without saving it.

My trips combines saved itineraries and incomplete planning drafts, with search,
sorting, renaming and confirmed deletion. Historical JSON imports open a separate
preview for review, saving and faithful text/JSON export. Detail shows completion,
provenance and uncertainty separately from itinerary content, with activity-linked
Nearby references. Copy and Keep example create independent saved snapshots;
Replan starts another brief from known original inputs. Verified place photos
and curated destination imagery retain separate attribution and fallback rules.
[Application operations](docs/0007-application-operations.md) defines ownership,
recovery and persistence behavior.

The Developer page at `/dev` retains independent V0–V3 runs. Generation requires a
destination, valid dates, traveler count and whole-trip budget/currency, with optional
preferences; incomplete drafts and historical imports can retain unknown fields.

Shared input assistance includes a selectable currency, locale-independent date input and
GeoDB city suggestions. Selecting a suggestion fills the city/region/country label; manual
destination entry remains available. FastAPI calls the public free GeoDB service over HTTPS
and normalizes its response. The browser does not call GeoDB directly.

The optional **Polish preferences** action makes at most one model call. A schema-valid rewrite
is displayed beside the original for the user to Apply or Dismiss; an applied rewrite can be
undone. The prompt asks the model to preserve meaning, but the application does not perform
a second preservation review or suppress a rewrite based on local semantic comparisons.
The normal planning Gate still runs when the user submits the form. Profile defaults
initialize a genuinely new brief; existing editor content retains its own requirements.
Daily weather is shown compactly alongside the itinerary.

## Local development

Use Python 3.12, the repository's virtual environment, and private local credentials based on
`.env.example`. On Windows, start FastAPI with the project's event-loop-compatible launcher:

```powershell
.\.venv\Scripts\python.exe scripts/run_api.py --host 127.0.0.1 --port 8000
```

In a separate terminal, start the frontend:

```powershell
cd frontend
npm ci
npm run dev
```

The backend health endpoint is `GET /health`; Vite proxies `/api` and `/health` to the
backend. The version entry points are `scripts/run_v0.py`, `scripts/run_v1.py`,
`scripts/run_v2.py` and `scripts/run_v3.py`. V2/V3 retrieval requires an existing compatible
PostgreSQL/pgvector database and its configured local environment. See the
[Product setup](docs/guides/development.md#product-account-setup-and-acceptance) for
account/session settings and the public Product migration command, and the
[development guide](docs/guides/development.md) for version-specific dependencies.

## TripWorld database release

The project owner's [TripWorld database release folder](https://drive.google.com/drive/folders/14VjxQU7jR8PGuiMWes5uaPLIOdrMNaQ0?usp=sharing)
contains the processed entities, retrieval text and saved vectors. Download the complete
release while preserving its directory structure, then verify the files against
`SHA256SUMS.txt`. The release `README.md` gives the import steps and validation results.

Restore `tripworld.pgcustom` into an empty PostgreSQL database with pgvector available.
The tested versions are PostgreSQL 17.10 and pgvector 0.8.2. For the current retrieval
runtime, copy the two packaged sidecars into these repository paths:

```text
data/tripworld/artifacts/retrieval_entities.parquet.manifest.json
data/tripworld/reports/phase5_embedding_run.json
```

Importing the release avoids downloading the TripWorld source data and regenerating the
stored embeddings. Online planning still needs the configured model and travel providers.
Keep the database dump outside Git.

## Documentation and evidence

[docs/README.md](docs/README.md) indexes current design and dated development records.
The [planning input UX specification](https://github.com/rplalala/Dayloom/issues/25) owns the assistance
contract and limits. Local `logs/` and `artifacts/` contain development evidence, including
potential provider/model data, and are not part of a source commit.
