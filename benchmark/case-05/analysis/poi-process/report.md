# Case-05 candidate process

The selected Barcelona execution revision 3 uses the [current original request](../../../inputs/case-05.json), 16–20 October 2026. This descriptive report binds the selected passive captures and independent final identities.

| Canonical stage | V1 | V2 |
| --- | ---: | ---: |
| discovered | 57 | 53 |
| admitted | 57 | 53 |
| enriched | 32 | 53 |
| supplied | 16 | 16 |
| Independently scheduled | 6 | 8 |

All captured stages have complete membership records. V1 leaves 25 admitted candidates unenriched at `unprocessed_new_success_target` and 16 enriched candidates unsupplied at `not_selected`; V2 records 37 supply omissions. These are recorded selection outcomes, not missing stage histories. Scheduled/supplied conversion is 6/16 and 8/16. Nearby references are excluded.

| Set difference | Retained | V2-only | V1-only |
| --- | ---: | ---: | ---: |
| discovered | 49 | 4 | 8 |
| admitted | 49 | 4 | 8 |
| enriched | 26 | 27 | 6 |
| supplied | 8 | 8 | 8 |
| scheduled | 3 | 5 | 3 |

V2 retrieval returned no entities and introduces no canonical RAG-only candidates. Independent generation differences do not establish a RAG benefit. The [summary](summary.json) retains complete sets, omission reasons, origin partitions and relevance conversions.

## Independent relevance

A fresh independent Codex reviewer assessed 61 canonical subjects against three source-only interests: **183 judgments, 7 relevant, 0 not_relevant and 176 UNKNOWN**. Only 14 subjects have retained independent evaluator observations. The packet excludes stage/version membership, query labels, Planner judgments, itineraries, mechanisms and scores. Known labels cite explicit available venue fields; missing descriptions and unsupported facts remain UNKNOWN. Record coverage is complete while known relevance is partial; lower counts must not be presented as complete relevance or recall. No corpus study or new acquisition was selected.

The actor was `/root/case05_r03_relevance`, configured `gpt-6.1-sol/high`. Its actual input/output hashes, times and honestly partial transcript remain private. Provider-side runtime telemetry, external Codex tokens and billing are unavailable. This is model review; human assessment remains deferred. Native source/semantic digests and actual review coverage are retained in summary.json.
