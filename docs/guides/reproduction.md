# Research verification and reproduction

This guide locates the submitted source, datasets and experiment scripts, and gives
the shortest path to verify the published findings. The
[deployment guide](deployment.md) covers running the Product; [README](../../README.md#project-structure)
describes the source tree.

Run commands from the repository root. All command blocks below work unchanged in
Bash (Linux/macOS) and PowerShell (Windows). Shell-specific installation steps are
paired in the deployment guide.

## Choose a verification level

| Goal | Required material | Provider requests |
| --- | --- | --- |
| Verify published arithmetic, ranks, source bindings and confirmed answers | Source tree and tracked `benchmark/` files; the optional case-04 completion check also needs the planner vocabulary | None |
| Replay native evaluation from saved evidence | Matching historical producer/evaluator code and complete native evidence archives | None for the documented offline replay |
| Run the current Product or generate new V0-V3 results | Deployment resources, compatible TripWorld data for V2/V3, provider credentials and explicit execution | Live features and execution can make paid requests |

New model/provider runs are not expected to reproduce historical text, facts, timing
or charges byte-for-byte. Current Product configuration is distinct from each accepted
experiment's recorded runtime policy and producer revision. Preserve the accepted
inputs and reported outputs rather than updating their dates or configurations.

## 1. Verify the published results offline

Open the submitted source directory and install the locked Python environment:

```bash
uv sync --locked --group retrieval
uv run python benchmark/verify_automatic.py
uv run python benchmark/verify_blinded.py
```

Dependency installation may download packages. Once installed, these two checks
require no `.env`, provider credentials, PostgreSQL, TripWorld dump, tokenizer cache
or Node.js. They consume the tracked source/materials and do not run new experiments.

Successful commands print:

```text
Verified 48 finals, 24 paired stages, exact ranks, 48 resource rows, and case-04 index/event identities.
Verified 12 current tasks, 48 selected plans, bilingual questionnaires, 24 confirmed answers, published mean ranks and current source hashes.
```

For the additional case-04 Rich-completion check, first supply the checksum-pinned
planner vocabulary at the path in
[token_counting.py](../../backend/app/runtime/token_counting.py). It can be copied
from the submitted cache or prepared explicitly:

```bash
uv run python -m tools.data.prepare_tokenizer
uv run python benchmark/review_case04.py
```

Preparation may download the public vocabulary; it does not call a model. The verifier
then runs offline and prints `Verified four new-date outputs, matched Primary/Pair and
native Rich completion (3/3).` It does not need the embedding vocabulary or a database.

| Check | What it verifies | Main report |
| --- | --- | --- |
| [verify_automatic.py](../../benchmark/verify_automatic.py) | Saved score decomposition, exact aggregate ranks, selected-generation resources and relevant material identities | [Automatic report](../../benchmark/report.md), [machine-readable results](../../benchmark/automatic-results.json) |
| [verify_blinded.py](../../benchmark/verify_blinded.py) | Current questionnaire/source bindings, the two confirmed answer sets and published mean ranks | [Blinded report](../../benchmark/blinded-results/report.md) |
| [review_case04.py](../../benchmark/review_case04.py) | Current case-04 input/four selected outputs, matching Primary/Pair dates and recorded Rich completion; requires planner vocabulary | [Case-04 report](../../benchmark/case-04/report.md) |

These checks establish consistency of retained materials and calculations. They do
not acquire fresh opening hours, rerun the human assessment or certify all itinerary
claims. Existing FAIL/UNKNOWN and evidence limitations remain part of the results.

## 2. Locate inputs, results and scripts

| Material | Source location and role |
| --- | --- |
| Twelve original requests | `benchmark/inputs/case-01.json` through `case-12.json` |
| Accepted case selection | [Selection index](../../benchmark/README.md#accepted-selections), then each case's `report.md` and `material-index.json` |
| Four selected planner outputs per case | `benchmark/case-XX/generation/v0/` through `v3/`, with usage/provenance and applicable runtime policies |
| Independent evaluation and V3 Pair | Each case's `evaluation/` directory; the report links its exact selected evidence |
| Supporting process/Repair/resource observations | Each case's `analysis/` directory, as located by its material index |
| Confirmed blinded materials | `benchmark/blinded-results/`: bilingual questionnaires, answer exports, binding summary and report |
| Independent planner entry points | `scripts/run_v0.py` through `scripts/run_v3.py`; implementation in `backend/app/versions/` |
| Installed experiment/evaluation CLI | `backend/cli/`; `uv run rtpeval --help` lists generation, collection, validation, evaluation and suite commands |
| Independent scoring and replay | `backend/evaluation/`; [operational guide](../../backend/evaluation/README.md) |
| Retrieval preparation and diagnostics | `tools/data/`, `tools/validation/`, `tools/diagnostics/`; current runtime in `backend/app/tripworld/` |

Public case views may use `$case_material_ref` and lossless deltas to avoid repeating
large objects. The verifiers expand supported references. A public `material-index.json`
is a navigation/integrity index, not an RTPEval native input manifest or a complete
provider-evidence replay bundle.

## 3. Data and supporting materials for submission

Keep the final source tree together, including both guides, dependency locks,
configuration templates and the complete tracked benchmark. Additional data/evidence
must be supplied separately from a source-only Git export:

| Component | Include or provide access to | Purpose |
| --- | --- | --- |
| Processed TripWorld release | `tripworld.pgcustom`, both `runtime/` sidecars, `source-and-provenance.zip`, `validation/`, `README.md`, `SHA256SUMS.txt` | Run V2/V3 retrieval without rebuilding embeddings; verify saved-vector parity |
| Raw TripWorld source, when rebuilding preprocessing | The pinned Parquet identified by [data/tripworld/manifest.json](../../data/tripworld/manifest.json), with upstream notices | Rebuild source projections/corpus; not required for the published-result checks above |
| Tokenizer vocabularies | Planner and embedding cache files, or the explicit preparation steps in the deployment guide | Offline runtime sizing and the case-04 planner-vocabulary dependency; not model weights |
| Native experiment evidence | Selected native outputs, preparations, evidence, receipts, reviewed inputs, all-attempt usage and their archive manifests | Native evaluation/process replay and provenance inspection |
| Historical code | The exact producer/evaluator revisions or producer-source archives declared by native evidence | Satisfy implementation-hash and source-version bindings |
| Final thesis PDF | The separately maintained final accepted PDF, for the school's complete archival submission | Final written research submission; it is not included in this source repository |

The TripWorld source identity is dataset `CRUISEResearchGroup/TripWorld`, revision
`421bc1dc63068bb398055b1ce987265fe22415db`, file `metadata/metadata_all.parquet`, SHA-256
`bd94d73c8443a18b5c7d31c0bd0b855cd141763b63841ee90646be1d73f9345e`.
The [database release](../../README.md#tripworld-database-release) contains processed
data and saved vectors; its provenance archive does not include the raw Parquet.
Preserve the upstream notices bundled with that release. The application's MIT license
does not replace the data's own distribution conditions.

The database dump is approximately 4.43 GB. Arrange large-data delivery through the
school's permitted artifact/LFS or linked-storage mechanism, with checksums and access
instructions; it is not a normal small Git source file. Native evidence can include
provider content or private transcripts and needs the agreed restricted-access
arrangement. Review the distribution for credentials. Preserve immutable originals;
any sanitized copy needs its own inventory and hashes and cannot silently replace
an original native replay dependency.

### Hand-in layout and integrity

Construct the hand-in directory **outside** the development checkout. One suitable
layout is the complete tracked source at the root, with separately supplied materials:

```text
dayloom-submission/
  README.md
  docs/guides/deployment.md
  docs/guides/reproduction.md
  backend/ frontend/ scripts/ tools/ benchmark/ config/ data/
  pyproject.toml  uv.lock  product.yaml  compose.yaml
  SOURCE_REVISION.txt
  SHA256SUMS.txt
  materials/
    tripworld-vector-release-20260926/
    native-evidence/
    historical-source/
    final-thesis.pdf
```

The names under `materials/` are a proposed submission layout, not files committed to
this repository. Record the actual locations or access links in the hand-in inventory.
For each native bundle, identify its case/selected revision, archive manifest, exact
source version, restore procedure and supported replay command. Files ignored by Git
are not included by `git archive`; a public case index alone is not a substitute.

After the final documentation commit, record its full `git rev-parse HEAD` in
`SOURCE_REVISION.txt` and export the source with `git archive`. Generate an outer
checksum manifest for the delivered files, retaining the original inner manifests.
Exclude `.env`, real keys, application-account databases, `.venv`, `node_modules` and
unrelated local scratch. Keep `frontend/package-lock.json`, `uv.lock`, `.env.example`,
LICENSE and all source/data notices.

## 4. Replay native saved evidence

Native evidence is outside the public source export. The
[archive contract](../../benchmark/README.md#private-archive-retention) defines what
must be retained. Obtain the matching archive and its declared historical code;
verify the archive checksums and restore the logical paths using its own manifest
and helper. Archive layouts differ across cases and selected revisions.

For a qualified, restored native evaluation directory, the installed command is:

```bash
uv run rtpeval evaluate replay path/to/restored-native-evaluation
```

Use the matching implementation and per-bundle instructions. Some historical
preparations contain absolute paths or implementation fingerprints, so moving a
directory and running current `main` is not guaranteed to replay it. Do not edit
hashes, original receipts or accepted outputs to bypass compatibility checks.
The [bundle-handling guide](../../benchmark/README.md#bundle-handling) and each case
report describe these limits; stage-specific Pair/process replay uses its declared
native reader rather than assuming the automatic-evaluation command covers every track.

## 5. Generate or evaluate new material

This is a new experiment, distinct from verifying the retained results. Use the Python
environment and applicable provider/tokenizer prerequisites from the
[deployment guide](deployment.md). Pure CLI execution does not need Node.js, Product
accounts or Product migrations; V2/V3 require the retrieval database. Choose fresh dates
in the supported window for your own [request.json](development.md#independent-version-execution);
do not modify accepted benchmark inputs.

Inspect the interfaces before selecting inputs and output directories:

```bash
uv run rtpeval generate --help
uv run rtpeval validate --help
uv run rtpeval evaluate --help
```

Choose distinct group/run identifiers and fresh output directories for new work.
For example, this prepares one V3 invocation offline in a fresh directory:

```bash
uv run rtpeval generate --version v3 --input-json request.json --runtime-config config/runtime.yaml --output-directory artifacts/reproduction/v3-prepared --group-id reproduction --run-id reproduction-v3
```

Preparation does not create an itinerary or call providers. Actual generation requires
an explicit `--execute` invocation with a **different fresh output directory** and
the required account access. V0 omits the runtime-config flag; V1-V3 use their selected
policy and V2/V3 need the compatible retrieval database.

Follow [generation and material handoff](../../backend/evaluation/README.md#installed-generation-and-material-handoff)
for source capture, independently reviewed requirements, collection and finalization.
`rtpeval validate` checks a qualified native manifest offline. Fresh evaluation is
documented under [automatic evaluation](../../backend/evaluation/README.md#installed-automatic-evaluation);
it requires explicit limits, a price book, credentials and a new execution directory.
Keep new runs separate from reported selections and retain failures/unknowns, actual
usage availability, model/deployment identities and exact code/configuration hashes.
