# Candidate POI process

Canonical places are counted once per stage. Scheduled membership is independently associated from the selected final outputs.

| Version | Discovered observed / complete | Admitted | Enriched | Supplied | Scheduled |
| --- | ---: | ---: | ---: | ---: | ---: |
| V1 | 62 / 62 | 48 | 20 | 10 | 9 |
| V2 | 73 / UNKNOWN | 48 | 48 | 10 | 8 |

V1 omitted 14 discovered places at admission capacity, left 28 enrichment candidates unprocessed after the new-success target, and did not select 10 enriched places. V2 omitted two ineligible/excluded places and 23 at admission capacity, enriched its entire 48-place admitted queue, and did not select 38 places.

V2 discovery is partial because the saved RAG observation is partial. Its 73 observed canonical places partition into 54 Google-only, 12 RAG-only and seven mixed. Three RAG-only places reached admission/enrichment, but none reached supply or the final itinerary. Four mixed-origin places were supplied and scheduled. These are within-run origin observations, not corpus recall or proof of a causal RAG benefit.

| Stage | V1 only | Retained | V2 only | Basis |
| --- | ---: | ---: | ---: | --- |
| discovered | 21 | 41 | 32 | observed_only |
| admitted | 15 | 33 | 15 | complete |
| enriched | 2 | 18 | 30 | complete |
| supplied | 3 | 7 | 3 | complete |
| scheduled | 2 | 7 | 1 | complete |

The discovered-set comparison is observed-only; partial V2 capture prevents an exact discovery gain/loss claim. Later complete-stage set differences describe these two saved generations. They are separate from the same-run V2 Google/RAG partitions.

The [stage inventories and omissions](opportunities.json) retain all supplied canonical IDs and Google/RAG origins. The [relevance view](relevance.json) uses the [independent judgments](../../interests/relevance.json): 94 venues × 3 interests, with 7 relevant and 275 UNKNOWN judgments. Only 19 venues have independent Primary metadata. No corpus coverage study was selected.

Missing facts remain UNKNOWN; no exact relevance gain, conversion or full-discovery count is inferred from a lower bound.
