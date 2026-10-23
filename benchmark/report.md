# Benchmark automatic results

The current automatic order is **V3 > V2 > V1 > V0**. V3 is the sole leader in all
12 cases. The replacement automatic material is **pending researcher acceptance**
under [#218](https://github.com/rplalala/Dayloom/issues/218).

[Exact results and resource rows](automatic-results.json) bind every final and same-run
Pair to its selected source. The [case-04 report](case-04/report.md) contains the full
replacement, limits and acceptance boundary.

## Automatic ranking

| Version | Mean score / 100 | Mean rank | Sole / joint firsts |
| --- | ---: | ---: | ---: |
| V3 | 99.625 | 1.000 | 12 / 0 |
| V2 | 88.759 | 2.625 | 0 / 0 |
| V1 | 83.504 | 3.167 | 0 / 0 |
| V0 | 81.743 | 3.208 | 0 / 0 |

Ranks use exact scores, with tied positions averaged. V3 scores 100 in ten cases,
98 in case-09 and 97.5 in case-10, with zero density deduction in all cases. The
V1/V0 mean-rank gap is small. These are descriptive results across historical
runtime and factual-evaluation policies, not a controlled causal comparison.

## Final scores and pace decomposition

Cells show **final score (within-case rank); auxiliary score − mean pace deduction**.
The original factual rules, masks, opening judgments and evidence remain fixed in
the eleven offline cases. Their final and Pair numbers are unchanged under
`rtpeval_daily_density_3`. All daily populations, fractions and derivation hashes
are available in the linked current density reports.

| Case | V0 | V1 | V2 | V3 |
| --- | --- | --- | --- | --- |
| [case-01](case-01/report.md) | 73.333 (4); 83.333 − 10 | 93.333 (3); 100.000 − 6.66667 | 96.667 (2); 100.000 − 3.33333 | 100.000 (1); 100.000 − 0 |
| [case-02](case-02/report.md) | 84.444 (3); 94.444 − 10 | 74.167 (4); 97.500 − 23.3333 | 90.208 (2); 96.875 − 6.66667 | 100.000 (1); 100.000 − 0 |
| [case-03](case-03/report.md) | 71.396 (4); 78.896 − 7.5 | 97.500 (2); 100.000 − 2.5 | 92.500 (3); 100.000 − 7.5 | 100.000 (1); 100.000 − 0 |
| [case-04](case-04/report.md) | 66.667 (3); 96.667 − 30 | 60.000 (4); 100.000 − 40 | 85.000 (2); 100.000 − 15 | 100.000 (1); 100.000 − 0 |
| [case-05](case-05/report.md) | 97.500 (2); 97.500 − 0 | 88.000 (3); 100.000 − 12 | 84.000 (4); 100.000 − 16 | 100.000 (1); 100.000 − 0 |
| [case-06](case-06/report.md) | 87.500 (3); 87.500 − 0 | 85.000 (4); 100.000 − 15 | 95.000 (2); 100.000 − 5 | 100.000 (1); 100.000 − 0 |
| [case-07](case-07/report.md) | 90.000 (4); 100.000 − 10 | 93.333 (3); 100.000 − 6.66667 | 96.667 (2); 100.000 − 3.33333 | 100.000 (1); 100.000 − 0 |
| [case-08](case-08/report.md) | 96.667 (2.5); 96.667 − 0 | 74.667 (4); 98.000 − 23.3333 | 96.667 (2.5); 100.000 − 3.33333 | 100.000 (1); 100.000 − 0 |
| [case-09](case-09/report.md) | 68.000 (4); 100.000 − 32 | 92.000 (2.5); 100.000 − 8 | 92.000 (2.5); 100.000 − 8 | 98.000 (1); 98.000 − 0 |
| [case-10](case-10/report.md) | 66.833 (4); 69.333 − 2.5 | 80.833 (3); 98.333 − 17.5 | 90.682 (2); 98.182 − 7.5 | 97.500 (1); 97.500 − 0 |
| [case-11](case-11/report.md) | 90.000 (3); 90.000 − 0 | 97.500 (2); 100.000 − 2.5 | 80.000 (4); 100.000 − 20 | 100.000 (1); 100.000 − 0 |
| [case-12](case-12/report.md) | 88.571 (2); 100.000 − 11.4286 | 65.714 (3.5); 80.000 − 14.2857 | 65.714 (3.5); 80.000 − 14.2857 | 100.000 (1); 100.000 − 0 |

## Same-run V3 Pair

Ten cases improve, two are unchanged, and none worsens. The paired population
contains 14 removed and 11 added visits, with zero replacements. Counts describe
retained stage differences; they do not establish that every Repair return condition
succeeded. Per-case source reports retain actual edits, unchanged checks and
continuing-condition transitions.

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

Case-04 improves 50 → 100 with 5/4 → 3/3 visits. Its auxiliary score remains 100.
The three-per-day target is reached, but Planner completion remains `unavailable`
because first-day coverage cannot be verified. The final Repair status is
`ACCEPTED_PARTIAL`; no fully successful Rich Repair is claimed for this run.

## Selected-generation resources

Each version has 12 selected runs. Timing spans invocation through cleanup; V3
includes Repair. Tokens include embedding usage where reported. SDK billing-only
tool observations are excluded from physical HTTP-send counts. Native missing
token details remain unavailable rather than being replaced with zero.

| Version | Median seconds | Median reference USD | Total reference USD | Total tokens | HTTP sends | Google sends |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V0 | 43.7 | 0.0044 | 0.052482 | 237,169 | 22 | 0 |
| V1 | 96.1 | 1.9673 | 23.478792 | 720,006 | 776 | 707 |
| V2 | 125.6 | 2.2983 | 27.191269 | 781,145 | 972 | 878 |
| V3 | 134.4 | 2.2714 | 27.566670 | 1,101,869 | 1027 | 936 |

The [48 source-bound usage rows](automatic-results.json) retain run IDs, recorded
prices, latency, token details and provider counts. V0 is substantially cheaper and
faster; V2 and V3 occupy a similar resource range. These costs exclude evaluation
and replaced/failed generations. They do not estimate first-attempt reliability.

Case-04 cumulative observed consumption is reported separately in its
[all-attempt ledger](case-04/analysis/resources/all-attempt-resources.json):
USD 18.30296590 priced subtotal, 16 invocation identities and 890 observed events.
Its 15 historical price conflicts prevent a complete total. The replaced V3 remains
in this ledger and is absent from the selected cohort. The three current stages
cost USD 4.49072519 against the approved USD 20 reference allowance. Actual account
billing, external assistance charges, discounts, credits and taxes are not established.

## Blinded results and interpretation

The [blinded report](blinded-results/report.md) retains the completed human and
GPT-6.1 sol xhigh reviews: human mean ranks V3 2.153, V2 2.236, V1 2.653, V0 2.958;
model mean ranks V3 1.889, V0 1.958, V2 2.667, V1 3.486. No answers, scores, ties,
rankings or review structure are recomputed here. The case-04 answers remain bound
to the itinerary actually shown, not the replacement V3. Presentation-content
synchronization belongs to #219 after researcher acceptance.

The automatic ranking prioritizes verified feasibility and pace. Existing blinded
results provide separate evidence about perceived preference match, pace and
practical usefulness, with only one human and one model reviewer. They are not
combined into a weighted score and do not validate an unseen replacement itinerary.

## Reproducibility and acceptance

The eleven `evaluation/density-final.json` and `density-pair.json` files are new
density-only derivations with original source hashes, fixed factual rules and exact
daily populations. They are not new provider receipts. Original outputs, acquisitions
and acceptance evidence remain unchanged. Case-04 uses new source-bound native
Primary/Pair reports; the Pair and all five applicable research tracks replay offline.

Run `.venv/Scripts/python.exe benchmark/verify_automatic.py` to verify published
score arithmetic, exact ranking, resource totals, material hashes and event identities
without network access. Use the [selection index](README.md#accepted-selections)
to locate each case.
Researcher acceptance of the complete replacement remains pending; merge does
not supply that decision. Thesis prose and blinded assessment answers are outside
this delivery.
