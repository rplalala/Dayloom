# Blinded review results

## Main findings

Across 12 itinerary comparisons, V3 received the lowest overall mean rank from
both reviewers. The human placed V2 next, while GPT-6.1 sol xhigh placed V0 next.
Their judgments were most similar on pace and differed most on practical
usefulness. The human used ties more often than the model.

## Final average rankings

Lower mean rank indicates a higher placement. The overall mean gives equal weight
to all 12 cases and all three dimensions.

| Version | Human overall mean | Model overall mean |
| --- | ---: | ---: |
| V0 | 2.958 | 1.958 |
| V1 | 2.653 | 3.486 |
| V2 | 2.236 | 2.667 |
| V3 | **2.153** | **1.889** |

The human's overall order is **V3 > V2 > V1 > V0**; the model's is
**V3 > V0 > V2 > V1**. V3 is close to the next-ranked version in both reviews:
its advantage in mean rank is 0.083 over V2 for the human and 0.069 over V0 for
the model.

### Means by dimension

| Reviewer | Version | Preference match | Pace | Practical usefulness |
| --- | --- | ---: | ---: | ---: |
| Human | V0 | 2.500 | 3.208 | 3.167 |
| Human | V1 | 2.875 | 2.542 | 2.542 |
| Human | V2 | 2.292 | 2.208 | 2.208 |
| Human | V3 | 2.333 | 2.042 | 2.083 |
| Model | V0 | 1.542 | 2.667 | 1.667 |
| Model | V1 | 3.542 | 3.125 | 3.792 |
| Model | V2 | 2.625 | 2.500 | 2.875 |
| Model | V3 | 2.292 | 1.708 | 1.667 |

For the human, V2 leads on preference match and V3 leads on pace and usefulness.
For the model, V0 leads on preference match, V3 leads on pace, and V0 and V3
have exactly the same usefulness mean before rounding.

## Agreement and notable differences

Each four-plan ranking determines six pair judgments: which plan is preferred,
or whether the pair ties. Agreement counts a shared tie as a match; an identical
ranking means all six judgments match.

| Dimension | Identical rankings / 12 | Matching pair judgments / 72 |
| --- | ---: | ---: |
| Preference match | 1/12 | 38/72 (52.8%) |
| Pace | 3/12 | 48/72 (66.7%) |
| Practical usefulness | 0/12 | 22/72 (30.6%) |

Overall, 108 of 216 pair judgments matched (50.0%). Of the 108 disagreements,
84 involved a tie on one side and a strict ordering on the other; 24 involved
opposite preferences. The human tied 91 pairs, compared with 29 for the model.
For usefulness alone, the human tied all four plans in five cases, while the
model distinguished plans in every case.

Three examples show the different patterns:

- **Task 5, Barcelona, pace:** both reviewers gave the same order,
  `A = D > B > C`, for the relaxed trip.
- **Task 3, Tokyo, usefulness:** the human placed A last and B first, while the
  model placed A first. The model's reason emphasized clear descriptions of the
  East Gardens and named neighbourhood visits.
- **Task 12, Sydney, preference match:** the human tied all four plans, while the
  model ordered them `A > C > D > B`. None of the six pair judgments matched,
  although the human had not expressed a preference opposite to the model's.

## Evaluation method

One human and one GPT-6.1 sol xhigh reviewer each assessed the same 12 requests
and four anonymous plans per request in the assessed questionnaire linked below.
Both completed all 36 rankings across preference match, pace and practical usefulness.
The current English/Chinese displays contain the accepted automatic itineraries;
the retained ratings assess the archived questionnaire, including its case-04 content.

Tied plans receive the average of their occupied positions: `A = B > C > D`
becomes 1.5, 1.5, 3 and 4. Each dimension mean averages 12 ranks; the overall
mean averages all 36, separately for each reviewer. Results are rounded to three
decimal places after calculation.

Version correspondence was derived by uniquely matching the assessed plans' complete
activity content to their selected sources at the [recorded publication](https://github.com/rplalala/Dayloom/tree/77ac8a4858ee6b08ea41a8012f9983a726298d02/benchmark).
This content-derived correspondence is retained; it is not a recovered private
assignment file. The [source binding](source-binding.json) identifies the assessed
questionnaire and current display separately. No retained rating assesses the
current case-04 itinerary or establishes a reviewer judgment of its Repair behavior.

### GPT-6.1 sol xhigh

> Act as an independent AI reviewer and complete this travel-itinerary assessment.
> Use only the original requests and plans A-D shown in the questionnaire. Do not
> consult version mappings, automatic scores or other reviewers' answers.
>
> Rank all four plans separately for each task on:
>
> - **Preference match:** how well the selected experiences fit the original request
>   and interests.
> - **Pace:** how well the schedule fits the requested rhythm, time at each stop and
>   opportunities to rest.
> - **Practical usefulness:** how clear, specific and usable the itinerary is.
>
> Judge the three dimensions independently. Allow ties without forcing distinctions,
> and select "Unable to judge" when information is insufficient. Do not automatically
> reward more sights, longer descriptions or emptier schedules. Do not treat
> unverified transport, opening hours or costs as established facts.
>
> Complete all 12 tasks, provide one or two sentences explaining each dimension's
> ranking, and export the answers using the questionnaire's original JSON schema.

## Limitations

These results describe one human and one model assessment of this set. Mean
ranks summarize placements, not the size of a quality difference or evidence of
general planner superiority. Pair judgments within a case are correlated. The
human gave no written reasons, limiting explanation of disagreements; the model
provided reasons for all 36 rankings.

## Appendix: task-level rankings and source files

`A > B = C > D` means A is preferred to the tied B and C, followed by D.
Letters within ties are alphabetical for readability. A-D identify plans within
a task and do not represent fixed versions across tasks.

### Preference match

| Task | Destination | Human ranking | Model ranking | Matching pairs / 6 |
| --- | --- | --- | --- | ---: |
| 1 | Sydney | A > B > D > C | A > C > B > D | 4 |
| 2 | London | B > C > A > D | B = D > C > A | 3 |
| 3 | Tokyo | A > B = C = D | A > D > C > B | 3 |
| 4 | Singapore | A = D > C > B | B = D > A > C | 2 |
| 5 | Barcelona | A = B = C = D | C > B > A = D | 1 |
| 6 | Sydney | D > A > B = C | A = D > B = C | 5 |
| 7 | Paris | A = B = C = D | A = B = C = D | 6 |
| 8 | Barcelona | B = D > A = C | A = B = D > C | 3 |
| 9 | Tokyo | B = D > C > A | D > B > C > A | 5 |
| 10 | London | C > A = B > D | C > A > B > D | 5 |
| 11 | Paris | A = B = C = D | B = C > D > A | 1 |
| 12 | Sydney | A = B = C = D | A > C > D > B | 0 |

### Pace

| Task | Destination | Human ranking | Model ranking | Matching pairs / 6 |
| --- | --- | --- | --- | ---: |
| 1 | Sydney | A > B = D > C | A > B = D > C | 6 |
| 2 | London | B > A > C > D | B > D > C > A | 3 |
| 3 | Tokyo | B = C > D > A | C > B > A = D | 4 |
| 4 | Singapore | A = C = D > B | D > A = B > C | 1 |
| 5 | Barcelona | A = D > B > C | A = D > B > C | 6 |
| 6 | Sydney | A > B = C > D | A > B = C > D | 6 |
| 7 | Paris | B = D > A = C | C = D > B > A | 2 |
| 8 | Barcelona | A = B = D > C | B > A = D > C | 4 |
| 9 | Tokyo | A = B = C = D | A > D > B = C | 1 |
| 10 | London | D > C > A = B | D > C > A > B | 5 |
| 11 | Paris | D > B > A = C | D > B > C > A | 5 |
| 12 | Sydney | C = D > A = B | C = D > A > B | 5 |

### Practical usefulness

| Task | Destination | Human ranking | Model ranking | Matching pairs / 6 |
| --- | --- | --- | --- | ---: |
| 1 | Sydney | A > B > D > C | A > C > B > D | 4 |
| 2 | London | B > A = C > D | B = D > C > A | 2 |
| 3 | Tokyo | B > D > C > A | A > D > B > C | 2 |
| 4 | Singapore | A = B = C = D | D > B > A > C | 0 |
| 5 | Barcelona | A = B = C = D | C > B > A > D | 0 |
| 6 | Sydney | A > C > B > D | A = D > C > B | 3 |
| 7 | Paris | D > B > A > C | C = D > B > A | 3 |
| 8 | Barcelona | B = D > A = C | B > A > D > C | 3 |
| 9 | Tokyo | B = C = D > A | D > B = C > A | 4 |
| 10 | London | A = B = C = D | D > C > A > B | 0 |
| 11 | Paris | A = B = C = D | C > B > D > A | 0 |
| 12 | Sydney | A = B = C = D | A = B > C > D | 1 |

### Source files

Current itinerary displays: [English](review.html), [Chinese](review.zh-CN.html).
Task 4 presents the accepted Singapore selection for 25–26 October 2026; the
other eleven tasks and the three-dimensional ranking format are unchanged.

Assessed questionnaires: [English](https://github.com/rplalala/Dayloom/blob/daaf9ba7ebe2cb7d881946bdce47e4f757f4f626/benchmark/blinded-results/review.html),
[Chinese](https://github.com/rplalala/Dayloom/blob/daaf9ba7ebe2cb7d881946bdce47e4f757f4f626/benchmark/blinded-results/review.zh-CN.html).
Answers: [Human](answers_human.json), [GPT-6.1 sol xhigh](answers_6.1sol.json).
These assessed questionnaires and original answer exports were accepted on
19 October 2026 (Australia/Sydney). All answer text, rankings, ties and reported
statistics remain attached to that presentation. Current displays have a distinct
presentation identity and hash; old answer imports are rejected by the existing
binding checks. [Source hashes](source-binding.json) preserve both populations.

Content synchronization uses the native source-linked display projection and the
existing anonymous letter order. External Codex `/root` prepared the content,
Chinese display translations, source bindings and equality checks under #219.
`/root/review219_standards` and `/root/review219_spec` independently reviewed the
committed content against repository standards and the Issue specification,
including the bilingual changes. Exact inherited model metadata, session tokens
and billing are unavailable.
No reviewer answers were authored or reassessed. Thesis #220 consumes the accepted
automatic selection and these source-bound blinded results as separate populations.
