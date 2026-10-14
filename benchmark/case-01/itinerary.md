# Case-01 itineraries and V3 changes

These are the initial case-01 V0-V3 outputs for Sydney, 13-15 October 2026,
one traveler and an AUD 900 whole-trip budget. The [original request](../inputs/case-01.json)
and [evaluation report](report.md) retain the input and independent findings.
All clock times below are Sydney local time (UTC+11). Activity costs were not
recorded in these outputs; missing costs do not mean zero or confirm budget compliance.
The tables preserve generated schedules and recorded transfer estimates without
correcting their venues, addresses, hours or routes. Full notes remain in the
linked itinerary JSON; independent PASS/FAIL/UNKNOWN belongs to the report.

## Reading the POI origins

- **Google + RAG**: the canonical place was present in Google discovery and also
  matched a TripWorld RAG return. This is a recorded mixed origin, not proof that
  RAG introduced the place or caused the model to schedule it.
- **RAG-only discovery**: the captured RAG stage introduced a canonical place
  absent from its preceding Google candidate set. No scheduled place below has
  this recorded label in this case.
- **No recorded RAG match**: no canonical RAG association is recorded for that
  scheduled place. V2/V3 discovery is partial, so this does not certify complete
  absence from the corpus or every unresolved RAG return.
- V0/V1 did not use RAG. Nearby reference recommendations are unscheduled
  suggestions and are kept separate from visits.

The [run-specific RAG origin inventory](generation/rag-origins.json) retains separate V2 and selected V3 maps. Association labels use the corresponding source run.

## V0

Saved source: [itinerary JSON](generation/v0/itinerary.json).

### 2026-10-13

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 09:00-11:00 | Sydney Opera House | Bennelong Point, Sydney | Main POI | Model-generated; no RAG |
| 11:00-11:20 | Walk to the Royal Botanic Garden | Not recorded | WALK | Model estimate; no RAG |
| 11:20-13:00 | Royal Botanic Garden Sydney | Mrs Macquaries Road, Sydney | Main POI | Model-generated; no RAG |
| 13:00-13:25 | Walk to the Art Gallery of New South Wales | Not recorded | WALK | Model estimate; no RAG |
| 13:25-16:00 | Art Gallery of New South Wales | Art Gallery Road, Sydney | Main POI | Model-generated; no RAG |

### 2026-10-14

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 09:00-11:00 | Explore The Rocks | The Rocks, Sydney | Main POI | Model-generated; no RAG |
| 11:00-11:15 | Walk to the Museum of Contemporary Art Australia | Not recorded | WALK | Model estimate; no RAG |
| 11:15-13:00 | Museum of Contemporary Art Australia | Circular Quay West, Sydney | Main POI | Model-generated; no RAG |
| 13:00-13:45 | Travel to Taronga Zoo | Not recorded | TRANSIT | Model estimate; no RAG |
| 13:45-17:00 | Taronga Zoo Sydney | Bradleys Head Road, Mosman | Main POI | Model-generated; no RAG |

### 2026-10-15

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 09:30-12:00 | Australian Museum | 1 William Street, Sydney | Main POI | Model-generated; no RAG |
| 12:00-12:15 | Walk to Hyde Park | Not recorded | WALK | Model estimate; no RAG |
| 12:15-13:15 | Hyde Park | Sydney central business district | Main POI | Model-generated; no RAG |
| 13:15-13:35 | Walk to the Queen Victoria Building | Not recorded | WALK | Model estimate; no RAG |
| 13:35-15:00 | Queen Victoria Building | George Street, Sydney | Main POI | Model-generated; no RAG |

### Unscheduled reference recommendations

| Associated date | Place | Area | Recorded origin |
| --- | --- | --- | --- |
| 2026-10-14 | Sydney Observatory | The Rocks | Model suggestion; no RAG |
| 2026-10-15 | Hyde Park Barracks | Hyde Park | Model suggestion; no RAG |

## V1

Saved source: [itinerary JSON](generation/v1/itinerary.json).

### 2026-10-13

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 10:00-11:30 | Visit Sydney Opera House | Bennelong Point, Sydney NSW 2000, Australia | Main POI | Google; no RAG |
| 11:30-11:47:51 | Sydney Opera House → The Rocks | Between scheduled stops | WALK | Recorded Google route estimate |
| 12:15-13:30 | Explore The Rocks | The Rocks NSW 2000, Australia | Main POI | Google; no RAG |
| 13:30-13:45:40 | The Rocks → Sydney Harbour Bridge | Between scheduled stops | WALK | Recorded Google route estimate |
| 14:00-15:00 | Visit Sydney Harbour Bridge | Sydney Hbr Brg, Sydney NSW, Australia | Main POI | Google; no RAG |

### 2026-10-14

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 10:00-12:15 | Visit the Australian Museum | 1 William St, Darlinghurst NSW 2010, Australia | Main POI | Google; no RAG |
| 12:15-12:26:34 | Australian Museum → Art Gallery of New South Wales | Between scheduled stops | WALK | Recorded Google route estimate |
| 13:15-15:45 | Visit the Art Gallery of New South Wales | Art Gallery Rd, Sydney NSW 2000, Australia | Main POI | Google; no RAG |

### 2026-10-15

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 09:30-10:45 | Explore Queen Victoria Building | 455 George St, Sydney NSW 2000, Australia | Main POI | Google; no RAG |
| 10:45-10:48:45 | Queen Victoria Building → Sydney Tower Eye | Between scheduled stops | WALK | Recorded Google route estimate |
| 11:15-12:30 | Visit Sydney Tower Eye | Westfield Sydney, Level 5/108 Market St, Sydney NSW 2000, Australia | Main POI | Google; no RAG |
| 12:30-12:48:36 | Sydney Tower Eye → Royal Botanic Garden Sydney | Between scheduled stops | WALK | Recorded Google route estimate |
| 13:15-14:45 | Visit Royal Botanic Garden Sydney | Mrs Macquaries Rd, Sydney NSW 2000, Australia | Main POI | Google; no RAG |

### Unscheduled reference recommendations

| Associated date | Place | Area | Recorded origin |
| --- | --- | --- | --- |
| 2026-10-13 | Western Foyers | Shop 14/2 Circular Quay E, Sydney NSW 2000, Australia | Google Nearby Search; no recorded RAG origin |
| 2026-10-13 | Munich Brauhaus Sydney | 33 Playfair St &, Argyle St, The Rocks NSW 2000, Australia | Google Nearby Search; no recorded RAG origin |
| 2026-10-13 | Olympic Park | Olympic Dr before, Alfred St, Milsons Point NSW 2061, Australia | Google Nearby Search; no recorded RAG origin |

## V2

Saved source: [itinerary JSON](generation/v2/itinerary.json).

### 2026-10-13

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 10:00-12:30 | Explore the Australian Museum | 1 William St, Darlinghurst NSW 2010, Australia | Main POI | No recorded RAG match |
| 12:30-12:41:34 | Australian Museum → Art Gallery of New South Wales | Between scheduled stops | WALK | Recorded Google route estimate |
| 13:30-16:00 | Visit the Art Gallery of New South Wales | Art Gallery Rd, Sydney NSW 2000, Australia | Main POI | **Google + RAG** |

### 2026-10-14

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 10:00-11:30 | Visit Sydney Opera House | Bennelong Point, Sydney NSW 2000, Australia | Main POI | No recorded RAG match |
| 11:30-11:44:53 | Sydney Opera House → Museum of Contemporary Art Australia | Between scheduled stops | WALK | Recorded Google route estimate |
| 12:00-14:00 | Explore the Museum of Contemporary Art Australia | 140 George St, The Rocks NSW 2000, Australia | Main POI | No recorded RAG match |
| 14:00-14:04:02 | Museum of Contemporary Art Australia → The Rocks | Between scheduled stops | WALK | Recorded Google route estimate |
| 14:30-16:00 | Explore The Rocks | The Rocks NSW 2000, Australia | Main POI | No recorded RAG match |

### 2026-10-15

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 09:30-11:00 | Visit Royal Botanic Garden Sydney | Mrs Macquaries Rd, Sydney NSW 2000, Australia | Main POI | No recorded RAG match |
| 11:00-11:19:34 | Royal Botanic Garden Sydney → Sydney Tower Eye | Between scheduled stops | WALK | Recorded Google route estimate |
| 12:00-13:30 | Visit Sydney Tower Eye | Westfield Sydney, Level 5/108 Market St, Sydney NSW 2000, Australia | Main POI | **Google + RAG** |

### Unscheduled reference recommendations

| Associated date | Place | Area | Recorded origin |
| --- | --- | --- | --- |
| 2026-10-13 | Billabong Waterhole | Level 4/1 William St, Darlinghurst NSW 2010, Australia | Google Nearby Search; no recorded RAG origin |
| 2026-10-13 | The Gallery Café | Art Gallery Rd, Sydney NSW 2000, Australia | Google Nearby Search; no recorded RAG origin |
| 2026-10-14 | Western Foyers | Shop 14/2 Circular Quay E, Sydney NSW 2000, Australia | Google Nearby Search; no recorded RAG origin |

## V3

Recorded V3 run: `case01-v3-repair140-followup-20261013T064153Z`.
Saved source: [itinerary JSON](generation/v3/itinerary.json).
All times below are Australia/Sydney; recorded route estimates remain separate from visits.

### 2026-10-13

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 12:00-13:00 | Explore The Rocks | The Rocks NSW 2000, Australia | Main POI | No recorded RAG match |
| 13:00:00-13:24:28 | The Rocks → Art Gallery of New South Wales | Between scheduled stops | WALK | Recorded Google route estimate |
| 14:00-16:00 | Visit the Art Gallery of New South Wales | Art Gallery Rd, Sydney NSW 2000, Australia | Main POI | **Google + RAG** |

### 2026-10-14

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 15:30-16:15 | Explore the Queen Victoria Building | 455 George St, Sydney NSW 2000, Australia | Main POI | No recorded RAG match |
| 16:15:00-16:18:45 | Queen Victoria Building → Sydney Tower Eye | Between scheduled stops | WALK | Recorded Google route estimate |
| 16:30-17:30 | Visit Sydney Tower Eye | Westfield Sydney, Level 5/108 Market St, Sydney NSW 2000, Australia | Main POI | **Google + RAG** |

### 2026-10-15

| Local time | Activity or journey | Location | Kind / mode | Recorded origin |
| --- | --- | --- | --- | --- |
| 11:30-12:30 | See Sydney Harbour Bridge | Sydney Hbr Brg, Sydney NSW, Australia | Main POI | No recorded RAG match |
| 12:30:00-12:43:38 | Sydney Harbour Bridge → Susannah Place | Between scheduled stops | WALK | Recorded Google route estimate |
| 14:00-15:30 | Visit Susannah Place | 58/64 Gloucester St, The Rocks NSW 2000, Australia | Main POI | No recorded RAG match |

### Unscheduled reference recommendations

| Associated date | Place | Area | Recorded origin |
| --- | --- | --- | --- |
| 2026-10-13 | Munich Brauhaus Sydney | 33 Playfair St &, Argyle St, The Rocks NSW 2000, Australia | Google Nearby Search; unscheduled and unverified |
| 2026-10-13 | The Gallery Café | Art Gallery Rd, Sydney NSW 2000, Australia | Google Nearby Search; unscheduled and unverified |
| 2026-10-14 | Koko Black - Lower Ground QVB | Queen Victoria Building, Shop L-048, Sydney NSW 2000, Australia | Google Nearby Search; unscheduled and unverified |

## V3 draft versus final

The [lossless draft delta](generation/v3/draft.json) reconstructs the exact original draft from the selected final itinerary. Repair accepted three deterministic `system_delete` rounds; all six surviving activity records are unchanged.

| Date | Deleted draft activity | Original local time | Final count |
| --- | --- | --- | ---: |
| 2026-10-13 | Sydney Opera House | 10:00-11:30 | 2 |
| 2026-10-14 | Taronga Zoo Sydney | 10:00-13:30 | 2 |
| 2026-10-15 | Royal Botanic Garden Sydney | 09:00-10:30 | 2 |

Draft daily counts were 3/3/3; final counts are 2/2/2. No model edit, addition or cross-date move was used in this selected real run. Routes were recomputed after deletion. Final-only Nearby references are presentation additions outside Repair and primary visits.

The [independent pair](evaluation/v3-pair/pair-report.json) scores the draft at 77.5 and final at 91.6667, a 14.1667 percentage-point change under the paired evidence/profile. Opening remains partial: three draft UNKNOWN and two final UNKNOWN. The separately accepted four-final opening supplement raises the selected V3 final score to 100 under its model overlay; it does not alter this pair's saved evidence or draft/final scores.

## Scheduled RAG matches

Associations use each selected run's recorded `rag_default_1` (`top attractions`) query. Rank is retrieval position, not an independent relevance grade or causal attribution.

| Version | Scheduled POI | Canonical ID | RAG rank | Origin |
| --- | --- | --- | ---: | --- |
| V2 | Art Gallery of New South Wales | `ChIJPVqlfGyuEmsRHPcnCX1X1OE` | 15 | Google + RAG |
| V2 | Sydney Tower Eye | `ChIJy6BwuD-uEmsRyiRskH1UG-I` | 3 | Google + RAG |
| V3 | Art Gallery of New South Wales | `ChIJPVqlfGyuEmsRHPcnCX1X1OE` | 15 | Google + RAG |
| V3 | Sydney Tower Eye | `ChIJy6BwuD-uEmsRyiRskH1UG-I` | 3 | Google + RAG |
