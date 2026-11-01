# Verify the findings

Use the saved twelve-case study to check reported scores, rankings, resources and
blinded assessments. These checks do not generate new trips or acquire new travel
facts. To repeat generation and evaluation, use [Reproduce an experiment](experiments.md).

## Run the offline checks

From the repository root:

```bash
uv sync --locked --group retrieval
uv run rtpeval verify
```

After dependency installation, verification needs no network, provider keys,
database, TripWorld dump, vocabularies or Node.js. Exit 0 means both retained
verifiers passed; a failed check returns 2.

The command checks the study as one set:

- Twelve original requests and 48 selected V0–V3 final outputs.
- Current case-report hashes and recorded lengths after LF normalization, separate
  from historical source bindings.
- Automatic score decomposition, exact rankings and 24 V3 paired stages.
- Forty-eight selected-generation resource rows and their source bindings.
- Bilingual blinded questionnaires, 24 confirmed answers and reported mean ranks.

The retained blinded results contain one human and one model assessment of each case.

## Trace the reported conclusions

| Finding or claim | Inspect | What the check establishes |
| --- | --- | --- |
| Automatic score order and per-case rankings | [Automatic report](../../benchmark/report.md), [results JSON](../../benchmark/automatic-results.json) | Arithmetic and ranks from the selected reports, including density deductions |
| Blinded preference, pace and usefulness | [Blinded report](../../benchmark/blinded-results/report.md), confirmed answer exports | Questionnaire/output correspondence, accepted answer revisions and aggregate ranks |
| Generation time, tokens, requests and reference cost | Each case's `analysis/resources/` and `generation/` | Retained source-linked resource values; availability remains explicit |
| Repair behavior | Each case's `analysis/repair/` and paired evaluation | Same-run draft/final observations, separate from independent V0–V3 comparisons |
| Evidence limitations | Each case's `report.md` and automatic report | Retained FAIL/UNKNOWN, missing evidence and applicability distinctions |

Start from the [case index](../../benchmark/README.md#accepted-selections), then open
that case's `material-index.json`. It locates the original input, selected four
outputs, generation provenance, evaluations and analyses. Public JSON may use
references or lossless deltas; the verifier resolves them before checking.

The automatic mean-score order is V3 > V2 > V1 > V0 for these selected cases.
A consistent saved calculation does not independently certify every itinerary
fact, establish a causal ablation, or extend the finding to other trips. The
reports retain the study's historical policy and evidence differences.

## Verify resource and cost claims

Keep selected-generation usage, all attempted work and independent evaluation
costs separate. Price-derived costs are estimates unless supported by billing;
missing observations remain unavailable rather than zero.

For supplied native four-version usage files:

```bash
uv run rtpeval usage v0-usage.json v1-usage.json v2-usage.json v3-usage.json
uv run rtpeval cost --usage usage.json --prices prices.json --output cost.json
```

The [accounting contract](../contracts/0002-intake-identity-usage.md#offline-cost-accounting)
defines price validity, repeated observations and billing reconciliation. The
synthetic acceptance examples in the test suite demonstrate the wire format;
use real captured usage and a dated price book for research claims.

## Replay native evidence

Public case projections are sufficient for the checks above. Recomputing a native
evaluation additionally requires complete evidence archives, original preparations
and receipts, reviewed inputs, and their exact historical implementation.
These archives and producer-code bundles are distributed separately from the
public source tree; their [retention guide](../../benchmark/README.md#private-archive-retention)
and each archive manifest describe recovery.

Verify the archive checksums and use its own helper to restore logical paths.
Select the declared historical code and dependency environment. For a compatible
restored native directory:

```bash
uv run rtpeval evaluate replay restored-evaluation
```

If the selected report includes a separately prepared incremental opening run:

```bash
uv run rtpeval evaluate replay-opening restored-opening
```

Both replay commands use saved evidence without provider requests. Absolute paths
and implementation hashes can prevent replay under a moved directory or current
code. Preserve those bindings and use the documented recovery layout; do not edit
receipts or hashes to bypass compatibility checks. Historical versions may require
their own recorded interface.

## Inspect additional reports

These commands read explicitly supplied material; they do not discover a research
population or turn absent evidence into an observation:

| Command | Purpose |
| --- | --- |
| `rtpeval quality` | Compose quality from native saved identity, schedule and evidence inputs |
| `rtpeval pair report` | Report source-linked V3 draft/final diagnostics |
| `rtpeval mechanism report` | Report captured mechanism observations, preserving missing capture |
| `rtpeval review report` | Recompute a blinded report from its presentation, mapping and actual answers |
| `rtpeval research validate` | Validate a declared population and selected saved track |
| `rtpeval research report` | Write a fresh report from that declaration |
| `rtpeval suite report` / `replay` | Inspect or replay a declared multi-case package |

For example, with an existing `rtpeval_research_declaration_1`:

```bash
uv run rtpeval research validate research.json -t population
uv run rtpeval research report research.json -t population -o population-report
```

Other tracks cover opportunities, relevance/coverage, Repair and generation
tradeoffs. Use `--help` for the allowed track names and the
[research artifact contract](../contracts/0001-evaluation-artifacts.md#original-input-research-declarations-and-attempt-census)
for source references. Optional suite report refreshes attach supplied reviewed
study material under a new receipt; they do not rerun the primary evaluation.

## Material needed for each level

| Task | Required material |
| --- | --- |
| Verify published calculations | Source tree and complete tracked `benchmark/` |
| Replay native evaluations | Matching historical code plus complete evidence/receipt archives |
| Repeat V0/V1 generation | Provider access and planner vocabulary |
| Repeat V2/V3 generation | Also compatible TripWorld data and embedding vocabulary/access |
| Rebuild preprocessing | Pinned raw TripWorld Parquet with upstream notices |

[Deployment](deployment.md) owns runtime resources. The
[TripWorld manifest](../../data/tripworld/manifest.json) pins the raw source and
checksum; the database release supplies processed data and saved vectors.
Keep provider/reviewer archives under their applicable access restrictions and
retain dataset and photograph notices.
