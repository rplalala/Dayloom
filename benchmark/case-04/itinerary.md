# Case 04 itineraries

Submitted selected schedules in Singapore local time (UTC+08:00). Optional recommendations remain unscheduled. Internal nearby-request tokens in their provenance are replaced by within-file recommendation ordinals; all other submitted fields are preserved. Full native source dictionaries remain private. The original request is in [case-04.json](../inputs/case-04.json).

RAG origin labels use saved canonical associations and mixed/new inventories in [rag-origins.json](generation/rag-origins.json); they are not relevance judgments.

## V0

Full submitted data: [itinerary.json](generation/v0/itinerary.json).

### 2026-10-17

| Time | Activity | Generation origin |
| --- | --- | --- |
| 09:00–10:45 | Singapore Botanic Gardens | Model generation |
| 10:45–11:15 | Public transport to National Gallery Singapore (TRANSIT) | Model-estimated transfer |
| 11:15–13:00 | National Gallery Singapore | Model generation |
| 13:00–13:15 | Walk to Merlion Park (WALK) | Model-estimated transfer |
| 13:15–13:45 | Merlion Park and Marina Bay views | Model generation |
| 13:45–14:15 | Walk to Gardens by the Bay (WALK) | Model-estimated transfer |
| 14:15–17:30 | Gardens by the Bay | Model generation |
| 17:30–17:45 | Walk to Marina Bay Sands SkyPark (WALK) | Model-estimated transfer |
| 17:45–19:00 | Marina Bay Sands SkyPark | Model generation |

### 2026-10-18

| Time | Activity | Generation origin |
| --- | --- | --- |
| 09:00–10:30 | Chinatown and Buddha Tooth Relic Temple | Model generation |
| 10:30–10:50 | Public transport to Fort Canning Park (TRANSIT) | Model-estimated transfer |
| 10:50–12:30 | Fort Canning Park | Model generation |
| 12:30–13:00 | Public transport to Kampong Glam (TRANSIT) | Model-estimated transfer |
| 13:00–14:15 | Kampong Glam and Sultan Mosque precinct | Model generation |
| 14:15–14:45 | Public transport to Singapore Flyer (TRANSIT) | Model-estimated transfer |
| 14:45–16:15 | Singapore Flyer | Model generation |
| 16:15–16:45 | Walk to Marina Barrage (WALK) | Model-estimated transfer |
| 16:45–18:00 | Marina Barrage | Model generation |

## V1

Full submitted data: [itinerary.json](generation/v1/itinerary.json).

### 2026-10-17

| Time | Activity | Generation origin |
| --- | --- | --- |
| 10:00–10:40 | Visit Merlion Park | Google discovery |
| 11:15–11:45 | Walk across The Helix Bridge | Google discovery |
| 12:15–13:30 | Singapore Flyer | Google discovery |
| 14:00–17:00 | Explore Gardens by the Bay | Google discovery |

| Transfer | Mode | Departure–arrival | Provider seconds |
| --- | --- | --- | ---: |
| sg-20261017-merlion → sg-20261017-helix | WALK | 10:40:00–10:57:28 | 1048.0 |
| sg-20261017-helix → sg-20261017-flyer | WALK | 11:45:00–11:53:32 | 512.0 |
| sg-20261017-flyer → sg-20261017-gardens-bay | WALK | 13:30:00–13:54:26 | 1466.0 |

### 2026-10-18

| Time | Activity | Generation origin |
| --- | --- | --- |
| 07:30–09:00 | Explore Singapore Botanic Gardens | Google discovery |
| 10:00–10:45 | Visit Sultan Mosque | Google discovery |
| 11:30–13:30 | Explore the National Museum of Singapore | Google discovery |
| 14:00–15:00 | Walk through Fort Canning Park | Google discovery |
| 15:45–16:30 | Visit Buddha Tooth Relic Temple | Google discovery |

| Transfer | Mode | Departure–arrival | Provider seconds |
| --- | --- | --- | ---: |
| sg-20261018-botanic-gardens → sg-20261018-sultan-mosque | TRANSIT | 09:00:00–09:32:27 | 1947.0 |
| sg-20261018-sultan-mosque → sg-20261018-national-museum | WALK | 10:45:00–11:09:24 | 1464.0 |
| sg-20261018-national-museum → sg-20261018-fort-canning | WALK | 13:30:00–13:41:34 | 694.0 |
| sg-20261018-fort-canning → sg-20261018-buddha-tooth-temple | WALK | 15:00:00–15:28:28 | 1708.0 |

## V2

Full submitted data: [itinerary.json](generation/v2/itinerary.json).

### 2026-10-17

| Time | Activity | Generation origin |
| --- | --- | --- |
| 08:00–10:30 | Explore Singapore Botanic Gardens | Google + RAG |
| 11:15–12:00 | Visit Buddha Tooth Relic Temple | Google; no recorded RAG association |
| 13:00–15:30 | Explore the National Museum of Singapore | Google; no recorded RAG association |
| 16:00–17:15 | Walk through Fort Canning Park | Google; no recorded RAG association |

| Transfer | Mode | Departure–arrival | Provider seconds |
| --- | --- | --- | ---: |
| sg-20261017-botanic-gardens → sg-20261017-buddha-tooth-relic-temple | TRANSIT | 10:30:00–11:01:57 | 1917.0 |
| sg-20261017-buddha-tooth-relic-temple → sg-20261017-national-museum | WALK | 12:00:00–12:31:53 | 1913.0 |
| sg-20261017-national-museum → sg-20261017-fort-canning | WALK | 15:30:00–15:41:34 | 694.0 |

### 2026-10-18

| Time | Activity | Generation origin |
| --- | --- | --- |
| 09:00–12:00 | Explore Gardens by the Bay | Google + RAG |
| 13:00–14:00 | Take in the views at Singapore Flyer | Google; no recorded RAG association |
| 14:30–15:15 | Visit Merlion Park | Google + RAG |
| 16:00–17:00 | Visit Marina Barrage | Google + RAG |

| Transfer | Mode | Departure–arrival | Provider seconds |
| --- | --- | --- | ---: |
| sg-20261018-gardens-by-the-bay → sg-20261018-singapore-flyer | WALK | 12:00:00–12:23:40 | 1420.0 |
| sg-20261018-singapore-flyer → sg-20261018-merlion-park | WALK | 14:00:00–14:18:36 | 1116.0 |
| sg-20261018-merlion-park → sg-20261018-marina-barrage | WALK | 15:15:00–15:54:45 | 2385.0 |

## V3

Full submitted data: [itinerary.json](generation/v3/itinerary.json).

### 2026-10-17

| Time | Activity | Generation origin |
| --- | --- | --- |
| 13:30–14:30 | Explore Marina Bay Waterfront Promenade | RAG-only introduction |
| 15:15–15:45 | Visit Merlion Park | Google + RAG |
| 16:30–17:30 | Experience the Singapore Flyer | Google; no recorded RAG association |

| Transfer | Mode | Departure–arrival | Provider seconds |
| --- | --- | --- | ---: |
| sat-promenade → sat-merlion | WALK | 14:30:00–14:49:22 | 1162.0 |
| sat-merlion → sat-flyer | WALK | 15:45:00–16:03:41 | 1121.0 |

### 2026-10-18

| Time | Activity | Generation origin |
| --- | --- | --- |
| 12:00–12:45 | Visit Buddha Tooth Relic Temple | Google; no recorded RAG association |
| 14:00–14:45 | Visit Sultan Mosque | Google; no recorded RAG association |
| 15:45–16:30 | Explore Fort Canning Park | Google; no recorded RAG association |

| Transfer | Mode | Departure–arrival | Provider seconds |
| --- | --- | --- | ---: |
| sun-buddha-temple → sun-sultan-mosque | WALK | 12:45:00–13:25:20 | 2420.0 |
| sun-sultan-mosque → sun-fort-canning | WALK | 14:45:00–15:20:40 | 2140.0 |

## Same-run V3 draft and final

The draft has 5/4 primary visits; the final has 3/3. Three deterministic deletion rounds removed:

- Gardens by the Bay (2026-10-17, 09:00–11:30).
- Marina Barrage (2026-10-17, 12:00–12:45).
- Singapore Botanic Gardens (2026-10-18, 09:00–11:00).

Retained activity fields are unchanged.
The full [draft reference view](generation/v3/draft.json) expands against the final itinerary with the same declared provenance-token sanitization. Transfer and recommendation differences remain in those source views.

The final retains Fort Canning Park, but its two explicitly named garden venues were removed. The Primary score alone does not establish interest preservation.
