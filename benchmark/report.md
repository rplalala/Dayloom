# Final benchmark report

## Final ranking

For the 12 accepted case selections, the final assessment is **V3 > V2 > V1 > V0**
for a planner that prioritizes reliable, feasible itineraries. V3 leads every
case in automatic evaluation and has the best overall mean rank in both blinded
reviews. V2 is the strongest alternative. The distinction between V1 and V0 is
much weaker, and V0 remains an attractive option for inexpensive first drafts.

This conclusion gives priority to automatic evaluation, checks the result against
the human review, and uses the model review to identify differences in perceived
travel experience. The three evaluations retain their own scales and are not
combined into a weighted score.

| Final rank | Version | Automatic mean rank | Automatic mean score / 100 | Human mean rank | Model mean rank | Automatic firsts: sole / joint |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | V3 | 1.000 | 99.625 | 2.153 | 1.889 | 12 / 0 |
| 2 | V2 | 2.625 | 88.759 | 2.236 | 2.667 | 0 / 0 |
| 3 | V1 | 3.167 | 83.921 | 2.653 | 3.486 | 0 / 0 |
| 4 | V0 | 3.208 | 81.743 | 2.958 | 1.958 | 0 / 0 |

**Automatic mean rank** averages a version's positions across the 12 cases,
ranked by final automatic score within each case; lower is better. Ties share the
average of their occupied positions (e.g., tied second and third each receive
2.5). **Automatic mean score** averages the 12 final scores out of 100 with equal
weight; higher is better. Human and model mean ranks cover the same cases and
additionally average the three review dimensions. The model reviewer is GPT-6.1
sol with xhigh reasoning effort.

The automatic and human orders agree: **V3 > V2 > V1 > V0**. The model instead
orders them **V3 > V0 > V2 > V1**. Its preference-match mean favors V0, while
both reviewers favor V3 on pace. The [blinded-review report](blinded-results/report.md)
contains the complete dimension results and anonymous rankings.

## Why the versions differ

### V3: the most consistent final result

V3 achieves 100 in ten cases, 98 in case 09 and 97.5 in case 10. All twelve
outputs have zero daily-density deduction. This matters because many V1 and V2
outputs already score highly on factual and scheduling checks, with remaining
losses coming from the number of visits scheduled per day. V3's validation and
Repair stage directly addresses that source of loss.

The same-run evidence makes this explanation concrete. In [case 05](case-05/report.md#process-and-repair),
V3 improves from 84 before Repair to 100 afterward. In
[case 10](case-10/report.md#repair-and-continuity), its draft improves from 93 to
97.5 after two deterministic deletions, with no Repair model calls. That change
also removes National Gallery, illustrating a real trade-off: a less crowded
schedule can lose an art experience. Both reviewers still give V3 their best
mean pace rank, while the model favors V0 on preference match.

Density is therefore an important explanation for V3's lead, rather than a claim
that every factual component improves. In case 09, for example, V3's base score
is 98 versus 100 for V1 and V2; its zero density deduction still produces the
highest final score.

### V2: stronger results than V1, with uneven retrieval benefits

V2 beats V1 in seven cases, ties in two and loses in three. Its second-place
human rank supports its position as the strongest alternative to V3. The gains
vary with the selected experiences and daily schedule: V1 beats V2 in cases 03,
05 and 11, so the extra retrieval stage does not produce a uniform improvement.

The [London candidate records](case-02/report.md#candidate-poi-process) show why
retrieval volume and final itinerary quality can diverge. V2 discovers 73 places
versus V1's 60, including 12 RAG-only discoveries. None of those 12 reaches the
final supplied set; four mixed-origin places are supplied and scheduled.
Retrieval expands the available choices, while selection and scheduling determine
which opportunities reach the traveler.

### V1 and V0: a narrow lower-order distinction

V1's automatic mean rank is only 0.042 better than V0's, and each beats the other
in six cases. The human ranking supports V1 above V0, which resolves the final
ordering under the report's priority on reliable planning. The model ranking and
V0's resource advantage provide substantial counterpoints; the evidence for this
boundary is weaker than the evidence for V3's first place.

V0 can offer an appealing plan while retaining unresolved operational details.
In [case 10](case-10/report.md#primary-results), conflicting UTC offsets leave
14 overlap checks unresolved and contribute to a final score of 66.833. Conversely,
in the relaxed [Barcelona case 05](case-05/report.md#results), V0 scores 97.5,
ahead of both V1 and V2. External evidence acquisition adds useful capabilities,
but the resulting visit choices and schedule still determine much of the outcome.

## Quality and resource trade-offs

The table summarizes the 12 selected generation runs for each version. Elapsed
time covers the invocation through cleanup. Reference costs use the saved price
estimates for those runs, with Repair already included in V3.

| Version | Median generation time, seconds | Median reference cost, USD |
| --- | ---: | ---: |
| V0 | 43.7 | 0.0044 |
| V1 | 96.1 | 1.9673 |
| V2 | 125.6 | 2.2983 |
| V3 | 129.7 | 2.2714 |

The largest resource step is from the plain-LLM baseline to versions that acquire
external evidence. V0 offers a practical speed and cost advantage for drafting.
V2 adds a median 18.6 seconds and USD 0.3139 relative to V1 within corresponding
cases, alongside its seven automatic-score wins.

V3 and V2 occupy a similar overall resource range. Within corresponding cases,
V3 costs more in nine of twelve runs, with a median increase of USD 0.0495;
six V3 runs are faster and six are slower. These within-case differences and the
separate version medians answer different questions: V3's slightly lower cost
median does not mean it is usually cheaper than V2. The comparison covers whole,
independently generated plans, so differences include provider work and itinerary
choices as well as Repair.

For this selected set, V3 offers the most consistent final quality at a resource
level close to V2. V2 remains a reasonable alternative when its retrieved options
are valuable, while V0 suits low-cost exploratory drafting followed by further
checking. The cost table excludes evaluation, failed or replaced attempts and
external assistance; it measures selected-run expense rather than the total
cost of producing the accepted dataset. Source accounting is listed below.

## Method and scope

Automatic ranks use each case's accepted final overall score, including its
existing daily-density deduction. Cases 01 and 02 use their accepted
opening-supplemented results. All 48 final scores are available;
calculations use exact fractions before rounding the displayed values.

The blind reviews assess preference match, pace and practical usefulness. Their
version correspondence was checked against the same selected itineraries. Their
separate mean ranks inform the final interpretation rather than modifying the
automatic scores. Version descriptions follow the [project architecture](../PROJECT.md#2-architecture-and-version-boundaries).

The dataset contains historical runtime and evaluation-policy differences, so
mean scores are descriptive summaries of the accepted cases. Some opening
decisions are model-supported rather than verified API hours. One
human review and one model review provide limited subjective evidence. The
ranking is a synthesis of these accepted selections, not a controlled causal
ablation or a population-wide result. Resource figures are recorded reference
estimates, not invoices, and selected-run timing does not measure first-attempt
completion reliability.

## Appendix: final automatic scores and case ranks

Cells show **score out of 100 (rank within the case)**. Case links lead to the
accepted reports and their source material; equal displayed scores are ranked
using their exact underlying values.

| Case | V0 | V1 | V2 | V3 |
| --- | ---: | ---: | ---: | ---: |
| [01 Sydney](case-01/report.md) | 73.333 (4) | 93.333 (3) | 96.667 (2) | 100.000 (1) |
| [02 London](case-02/report.md) | 84.444 (3) | 74.167 (4) | 90.208 (2) | 100.000 (1) |
| [03 Tokyo](case-03/report.md) | 71.396 (4) | 97.500 (2) | 92.500 (3) | 100.000 (1) |
| [04 Singapore](case-04/report.md) | 66.667 (3) | 65.000 (4) | 85.000 (2) | 100.000 (1) |
| [05 Barcelona](case-05/report.md) | 97.500 (2) | 88.000 (3) | 84.000 (4) | 100.000 (1) |
| [06 Sydney](case-06/report.md) | 87.500 (3) | 85.000 (4) | 95.000 (2) | 100.000 (1) |
| [07 Paris](case-07/report.md) | 90.000 (4) | 93.333 (3) | 96.667 (2) | 100.000 (1) |
| [08 Barcelona](case-08/report.md) | 96.667 (2.5) | 74.667 (4) | 96.667 (2.5) | 100.000 (1) |
| [09 Tokyo](case-09/report.md) | 68.000 (4) | 92.000 (2.5) | 92.000 (2.5) | 98.000 (1) |
| [10 London](case-10/report.md) | 66.833 (4) | 80.833 (3) | 90.682 (2) | 97.500 (1) |
| [11 Paris](case-11/report.md) | 90.000 (3) | 97.500 (2) | 80.000 (4) | 100.000 (1) |
| [12 Sydney](case-12/report.md) | 88.571 (2) | 65.714 (3.5) | 65.714 (3.5) | 100.000 (1) |

### Resource sources

Selected-run costs are drawn from the case accounting and selected-cohort records:
[01](case-01/analysis/resources/accounting.json),
[02](case-02/analysis/resources/accounting.json),
[03](case-03/analysis/resources/tradeoffs.json),
[04](case-04/analysis/resources/selected-tradeoffs.json),
[05](case-05/analysis/resources/selected-tradeoffs.json),
[06](case-06/analysis/resources/accounting.json),
[07](case-07/analysis/resources/all-attempts.json),
[08](case-08/analysis/resources/accounting.json),
[09](case-09/analysis/resources/selected-tradeoffs.json),
[10](case-10/analysis/resources/summary.json),
[11](case-11/analysis/resources/selected-tradeoffs.json), and
[12](case-12/analysis/resources/selected-r07.json).
Timing comes from each selected version's linked generation usage record. The
[accepted selection index](README.md#accepted-selections) locates the case reports,
inputs and material indexes.
