# Benchmark automatic results

Across the twelve selected cases, the automatic mean-score order is
**V3 > V2 > V1 > V0**. [Exact results and resource rows](automatic-results.json)
bind every final and same-run V3 pair to its selected source. The
[case index](README.md#accepted-selections) links the accepted selections and limitations.

## Automatic ranking

| Version | Mean score / 100 | Mean rank | Sole / joint firsts |
| --- | ---: | ---: | ---: |
| V3 | 99.625 | 1.000 | 12 / 0 |
| V2 | 86.759 | 2.708 | 0 / 0 |
| V1 | 82.671 | 3.167 | 0 / 0 |
| V0 | 81.743 | 3.125 | 0 / 0 |

Ranks use exact fractions and averaged tied positions. These descriptive comparisons
span historical runtime and factual-evaluation policies; they are not causal ablations.

## Final scores and pace decomposition

Cells show **final score (within-case rank); auxiliary score − mean pace deduction**.
The eleven retained cases have unchanged final and Pair numbers under the current
density policy. All daily populations and exact fractions remain source-bound.

| Case | V0 | V1 | V2 | V3 |
| --- | --- | --- | --- | --- |
| [case-01](case-01/report.md) | 73.333 (4); 83.333 − 10 | 93.333 (3); 100.000 − 6.66667 | 96.667 (2); 100.000 − 3.33333 | 100.000 (1); 100.000 − 0 |
| [case-02](case-02/report.md) | 84.444 (3); 94.444 − 10 | 74.167 (4); 97.500 − 23.3333 | 90.208 (2); 96.875 − 6.66667 | 100.000 (1); 100.000 − 0 |
| [case-03](case-03/report.md) | 71.396 (4); 78.896 − 7.5 | 97.500 (2); 100.000 − 2.5 | 92.500 (3); 100.000 − 7.5 | 100.000 (1); 100.000 − 0 |
| [case-04](case-04/report.md) | 66.667 (2); 96.667 − 30 | 50.000 (4); 100.000 − 50 | 61.000 (3); 76.000 − 15 | 100.000 (1); 100.000 − 0 |
| [case-05](case-05/report.md) | 97.500 (2); 97.500 − 0 | 88.000 (3); 100.000 − 12 | 84.000 (4); 100.000 − 16 | 100.000 (1); 100.000 − 0 |
| [case-06](case-06/report.md) | 87.500 (3); 87.500 − 0 | 85.000 (4); 100.000 − 15 | 95.000 (2); 100.000 − 5 | 100.000 (1); 100.000 − 0 |
| [case-07](case-07/report.md) | 90.000 (4); 100.000 − 10 | 93.333 (3); 100.000 − 6.66667 | 96.667 (2); 100.000 − 3.33333 | 100.000 (1); 100.000 − 0 |
| [case-08](case-08/report.md) | 96.667 (2.5); 96.667 − 0 | 74.667 (4); 98.000 − 23.3333 | 96.667 (2.5); 100.000 − 3.33333 | 100.000 (1); 100.000 − 0 |
| [case-09](case-09/report.md) | 68.000 (4); 100.000 − 32 | 92.000 (2.5); 100.000 − 8 | 92.000 (2.5); 100.000 − 8 | 98.000 (1); 98.000 − 0 |
| [case-10](case-10/report.md) | 66.833 (4); 69.333 − 2.5 | 80.833 (3); 98.333 − 17.5 | 90.682 (2); 98.182 − 7.5 | 97.500 (1); 97.500 − 0 |
| [case-11](case-11/report.md) | 90.000 (3); 90.000 − 0 | 97.500 (2); 100.000 − 2.5 | 80.000 (4); 100.000 − 20 | 100.000 (1); 100.000 − 0 |
| [case-12](case-12/report.md) | 88.571 (2); 100.000 − 11.4286 | 65.714 (3.5); 80.000 − 14.2857 | 65.714 (3.5); 80.000 − 14.2857 | 100.000 (1); 100.000 − 0 |

## Same-run V3 Pair

10 cases improve, 2 are unchanged and 0 worsen. The paired population
contains 14 removed, 11 added and 0 replaced visits. Each pair uses
the draft and final of its own V3 invocation; a V3 draft is not a separate V2 run.

| Case | Draft | Final | Delta | Removed / added |
| --- | ---: | ---: | ---: | ---: |
| [case-01](case-01/evaluation/density-pair.json) | 85.833 | 100.000 | +14.167 | 3 / 0 |
| [case-02](case-02/evaluation/density-pair.json) | 80.208 | 100.000 | +19.792 | 2 / 0 |
| [case-03](case-03/evaluation/density-pair.json) | 86.667 | 100.000 | +13.333 | 2 / 0 |
| [case-04](case-04/evaluation/v3-pair/report.json) | 50.000 | 100.000 | +50.000 | 3 / 0 |
| [case-05](case-05/evaluation/density-pair.json) | 84.000 | 100.000 | +16.000 | 0 / 4 |
| [case-06](case-06/evaluation/density-pair.json) | 100.000 | 100.000 | +0.000 | 0 / 0 |
| [case-07](case-07/evaluation/density-pair.json) | 100.000 | 100.000 | +0.000 | 0 / 0 |
| [case-08](case-08/evaluation/density-pair.json) | 96.667 | 100.000 | +3.333 | 1 / 0 |
| [case-09](case-09/evaluation/density-pair.json) | 92.848 | 98.000 | +5.152 | 1 / 0 |
| [case-10](case-10/evaluation/density-pair.json) | 93.000 | 97.500 | +4.500 | 2 / 0 |
| [case-11](case-11/evaluation/density-pair.json) | 90.000 | 100.000 | +10.000 | 0 / 1 |
| [case-12](case-12/evaluation/density-pair.json) | 54.286 | 100.000 | +45.714 | 0 / 6 |

## Selected-generation resources

| Version | Median USD | Median seconds | Total tokens | HTTP sends |
| --- | ---: | ---: | ---: | ---: |
| V0 | 0.0043604875 | 42.141 | 237191 | 22 |
| V1 | 1.967271465 | 96.539 | 725238 | 805 |
| V2 | 2.2983045925 | 117.039 | 779746 | 962 |
| V3 | 2.2714044685 | 129.726 | 1099562 | 1028 |

The 48 selected-generation rows exclude evaluation and replaced/failed generations.
Per-case resource reports retain all-attempt ledgers and missing or conflicting
observations. Actual account billing and external AI-assistance costs are not established.

## Blinded results and interpretation

The [blinded report](blinded-results/report.md) retains its completed human and
model reviews, answers, ties, ranks and scoring structure. Its English/Chinese
questionnaires and confirmed results match the accepted twelve-case selection.
Blinded ranks remain separate from automatic scores.

## Reproducibility and acceptance

```bash
uv run rtpeval verify
```

The command checks all 48 finals, 24 paired stages, exact ranks, resource rows,
material bindings and confirmed blinded results offline. The
[verification guide](../docs/guides/verification.md) distinguishes public checks from
native saved-evidence replay. Original captures and receipts remain preserved;
the [selection index](README.md#accepted-selections) records case acceptance.
