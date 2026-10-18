# Case-09: selected schedules and origins

Full saved final activities and transfers are shown below. Optional Nearby recommendations remain unscheduled. Exact structured values and source hashes are in the linked itineraries and material index.

## V0

[Exact itinerary](generation/v0/itinerary.json)

### 2026-10-22

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+09:00 – 2026-10-22T12:00:00+09:00 | Visit Meiji Jingu | Meiji Jingu; Shibuya, Tokyo | main_poi/scheduled | Model generation; no RAG provenance | A traditional shrine visit to begin the trip; opening details have not been checked. |

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+09:00 – 2026-10-23T11:00:00+09:00 | Visit Ueno Park | Ueno Park; Ueno, Taito City, Tokyo | main_poi/scheduled | Model generation; no RAG provenance | The requested single visit to Ueno Park, scheduled on October 23. |
| 2026-10-23T11:00:00+09:00 – 2026-10-23T11:20:00+09:00 | Walk from Ueno Park to Tokyo National Museum | ;  | transport/scheduled | Model generation; no RAG provenance | Model estimate: about 20 minutes on foot via the park grounds; route and duration are not live-verified. |
| 2026-10-23T11:20:00+09:00 – 2026-10-23T14:00:00+09:00 | Visit Tokyo National Museum | Tokyo National Museum; Ueno Park, Taito City, Tokyo | main_poi/scheduled | Model generation; no RAG provenance | The requested single museum visit, with time for its traditional Japanese and Asian art collections. Opening details have not been checked. |

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+09:00 – 2026-10-24T12:00:00+09:00 | Visit Sensō-ji | Sensō-ji; Asakusa, Taito City, Tokyo | main_poi/scheduled | Model generation; no RAG provenance | Explore this historic Buddhist temple and its traditional surroundings. Opening details have not been checked. |

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T10:30:00+09:00 – 2026-10-25T13:00:00+09:00 | Visit Mori Art Museum | Mori Art Museum; Roppongi, Minato City, Tokyo | main_poi/scheduled | Model generation; no RAG provenance | A focused modern-art visit. Current exhibitions, opening details, and admission costs have not been checked. |

### 2026-10-26

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-26T10:00:00+09:00 – 2026-10-26T11:30:00+09:00 | Visit Kanda Myojin | Kanda Myojin; Chiyoda City, Tokyo | main_poi/scheduled | Model generation; no RAG provenance | A traditional Shinto shrine visit to round out the trip. Opening details have not been checked. |

[Complete transfer and Nearby fields](generation/v0/itinerary.json) retain all optional fields without counting references as visits.

## V1

[Exact itinerary](generation/v1/itinerary.json)

### 2026-10-22

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+09:00 – 2026-10-22T11:30:00+09:00 | Visit Sensō-ji | Sensō-ji; 2-chōme-3-1 Asakusa, Taito City, Tokyo 111-0032, Japan | main_poi/scheduled | Google | A traditional-culture visit. Date-specific opening hours were not supplied. |
| 2026-10-22T12:15:00+09:00 – 2026-10-22T14:00:00+09:00 | Visit Tokyo Skytree | Tokyo Skytree; 1-chōme-1-2 Oshiage, Sumida City, Tokyo 131-0045, Japan | main_poi/scheduled | Google |  |

**Saved transfers:**

- `{"from_activity_id":"tokyo-20261022-sensoji","to_activity_id":"tokyo-20261022-skytree","origin_place_id":"ChIJ8T1GpMGOGGARDYGSgpooDWw","destination_place_id":"ChIJ35ov0dCOGGARKvdDH7NPHX0","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-22T11:30:00+09:00","arrival_time":"2026-10-22T11:54:55+09:00","provider_duration_seconds":1495.0,"distance_meters":1713,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+09:00 – 2026-10-23T10:30:00+09:00 | Visit Ueno Park | Ueno Park; 4 Uenokoen, Taito City, Tokyo 110-0007, Japan | main_poi/scheduled | Google | The requested single Ueno Park visit, scheduled on 2026-10-23. |
| 2026-10-23T11:00:00+09:00 – 2026-10-23T14:00:00+09:00 | Visit Tokyo National Museum | Tokyo National Museum; 13-9 Uenokōen, Taito City, Tokyo 110-8712, Japan | main_poi/scheduled | Google | The requested single museum visit. Supplied hours for this date are 09:30–20:00; date-specific closure exceptions were not established. |

**Saved transfers:**

- `{"from_activity_id":"tokyo-20261023-ueno-park","to_activity_id":"tokyo-20261023-national-museum","origin_place_id":"ChIJw2qQRZuOGGARWmROEiM2y7E","destination_place_id":"ChIJEX3XFIOOGGAR3XdJvRjWLyM","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-23T10:30:00+09:00","arrival_time":"2026-10-23T10:37:15+09:00","provider_duration_seconds":435.0,"distance_meters":530,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T09:30:00+09:00 – 2026-10-24T11:00:00+09:00 | Visit Meiji Jingu | Meiji Jingu; 1-1 Yoyogikamizonochō, Shibuya, Tokyo 151-8557, Japan | main_poi/scheduled | Google | A traditional-culture visit. Date-specific opening hours were not supplied. |
| 2026-10-24T12:00:00+09:00 – 2026-10-24T12:30:00+09:00 | See Shibuya Scramble Crossing | Shibuya Scramble Crossing; 21 Udagawacho, Shibuya, Tokyo 150-0042, Japan | main_poi/scheduled | Google |  |

**Saved transfers:**

- `{"from_activity_id":"tokyo-20261024-meiji-jingu","to_activity_id":"tokyo-20261024-shibuya-crossing","origin_place_id":"ChIJ5SZMmreMGGARcz8QSTiJyo8","destination_place_id":"ChIJK9EM68qLGGARacmu4KJj5SA","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-24T11:00:00+09:00","arrival_time":"2026-10-24T11:30:52+09:00","provider_duration_seconds":1852.0,"distance_meters":2307,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T09:30:00+09:00 – 2026-10-25T11:30:00+09:00 | Visit Shinjuku Gyoen National Garden | Shinjuku Gyoen National Garden; 11 Naitōmachi, Shinjuku City, Tokyo 160-0014, Japan | main_poi/scheduled | Google | The supplied regular weekly baseline lists hours of 09:00–16:30; date-specific exceptions were not established. |
| 2026-10-25T13:00:00+09:00 – 2026-10-25T13:30:00+09:00 | See Godzilla Head | Godzilla Head; 1-chōme-19-1 Kabukichō, Shinjuku City, Tokyo 160-0021, Japan | main_poi/scheduled | Google | Date-specific operating hours were not supplied. |

**Saved transfers:**

- `{"from_activity_id":"tokyo-20261025-shinjuku-gyoen","to_activity_id":"tokyo-20261025-godzilla-head","origin_place_id":"ChIJPyOTG8KMGGARh_IXobWxHmo","destination_place_id":"ChIJzRzI3HSNGGARRwZW6AtJfi0","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-25T11:30:00+09:00","arrival_time":"2026-10-25T11:52:51+09:00","provider_duration_seconds":1371.0,"distance_meters":1633,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-26

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-26T10:00:00+09:00 – 2026-10-26T11:30:00+09:00 | Visit Tokyo Tower | Tokyo Tower; 4-chōme-2-8 Shibakōen, Minato City, Tokyo 105-0011, Japan | main_poi/scheduled | Google | The supplied regular weekly baseline lists hours of 09:00–23:00; date-specific exceptions were not established. No supplied candidate specifically supports a modern-art visit, so a dedicated modern-art venue is not scheduled. |

[Complete transfer and Nearby fields](generation/v1/itinerary.json) retain all optional fields without counting references as visits.

## V2

[Exact itinerary](generation/v2/itinerary.json)

### 2026-10-22

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-22T10:30:00+09:00 – 2026-10-22T11:45:00+09:00 | Visit Meiji Jingu | Meiji Jingu; 1-1 Yoyogikamizonochō, Shibuya, Tokyo 151-8557, Japan | main_poi/scheduled | Google | Opening hours for this date are unknown in the supplied evidence. |
| 2026-10-22T13:00:00+09:00 – 2026-10-22T14:30:00+09:00 | Visit Tokyo Opera City Art Gallery | Tokyo Opera City Art Gallery; 3-chōme-20-2 Nishishinjuku, Shinjuku City, Tokyo 163-1403, Japan | main_poi/scheduled | RAG | Supplied evidence identifies an art museum/gallery but does not establish a specifically modern-art focus. |

**Saved transfers:**

- `{"from_activity_id":"tokyo-20261022-01","to_activity_id":"tokyo-20261022-02","origin_place_id":"ChIJ5SZMmreMGGARcz8QSTiJyo8","destination_place_id":"ChIJCaoz7S3zGGARrAnbz14VDcw","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-22T11:45:00+09:00","arrival_time":"2026-10-22T12:11:03+09:00","provider_duration_seconds":1563.0,"distance_meters":1800,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T10:00:00+09:00 – 2026-10-23T13:00:00+09:00 | Visit Tokyo National Museum | Tokyo National Museum; 13-9 Uenokōen, Taito City, Tokyo 110-8712, Japan | main_poi/scheduled | Google | Current Places hours indicate 09:30–20:00; a date-specific exception is unknown. |
| 2026-10-23T13:45:00+09:00 – 2026-10-23T15:15:00+09:00 | Visit Ueno Park | Ueno Park; 4 Uenokoen, Taito City, Tokyo 110-0007, Japan | main_poi/scheduled | Google |  |

**Saved transfers:**

- `{"from_activity_id":"tokyo-20261023-01","to_activity_id":"tokyo-20261023-02","origin_place_id":"ChIJEX3XFIOOGGAR3XdJvRjWLyM","destination_place_id":"ChIJw2qQRZuOGGARWmROEiM2y7E","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-23T13:00:00+09:00","arrival_time":"2026-10-23T13:07:15+09:00","provider_duration_seconds":435.0,"distance_meters":530,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T10:30:00+09:00 – 2026-10-24T12:00:00+09:00 | Visit Sensō-ji | Sensō-ji; 2-chōme-3-1 Asakusa, Taito City, Tokyo 111-0032, Japan | main_poi/scheduled | Google | Opening hours for this date are unknown in the supplied evidence. |
| 2026-10-24T13:15:00+09:00 – 2026-10-24T14:45:00+09:00 | Visit Tokyo Skytree | Tokyo Skytree; 1-chōme-1-2 Oshiage, Sumida City, Tokyo 131-0045, Japan | main_poi/scheduled | Google | Regular weekly hours are listed as 09:00–22:00; date-specific exceptions are not established. |

**Saved transfers:**

- `{"from_activity_id":"tokyo-20261024-01","to_activity_id":"tokyo-20261024-02","origin_place_id":"ChIJ8T1GpMGOGGARDYGSgpooDWw","destination_place_id":"ChIJ35ov0dCOGGARKvdDH7NPHX0","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-24T12:00:00+09:00","arrival_time":"2026-10-24T12:24:55+09:00","provider_duration_seconds":1495.0,"distance_meters":1713,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T09:30:00+09:00 – 2026-10-25T11:15:00+09:00 | Visit Hamarikyu Gardens | Hamarikyu Gardens; 1-1 Hamarikyūteien, Chuo City, Tokyo 104-0046, Japan | main_poi/scheduled | Google | Regular weekly hours are listed as 09:00–17:00; date-specific exceptions are not established. |
| 2026-10-25T12:15:00+09:00 – 2026-10-25T13:45:00+09:00 | Visit Tokyo Tower | Tokyo Tower; 4-chōme-2-8 Shibakōen, Minato City, Tokyo 105-0011, Japan | main_poi/scheduled | Google | Regular weekly hours are listed as 09:00–23:00; date-specific exceptions are not established. |

**Saved transfers:**

- `{"from_activity_id":"tokyo-20261025-01","to_activity_id":"tokyo-20261025-02","origin_place_id":"ChIJwfegutyLGGARGjiY-L2eSps","destination_place_id":"ChIJCewJkL2LGGAR3Qmk0vCTGkg","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-25T11:15:00+09:00","arrival_time":"2026-10-25T11:51:55+09:00","provider_duration_seconds":2215.0,"distance_meters":2494,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-26

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-26T10:30:00+09:00 – 2026-10-26T12:00:00+09:00 | Visit Shibuya Sky | Shibuya Sky; Japan, 〒150-6145 Tokyo, Shibuya, 2-chōme−24−１２ スクランブルスクエア 14階・45階 46階・屋上 | main_poi/scheduled | Google | Regular weekly hours are listed as 10:00–22:30; date-specific exceptions are not established. |

[Complete transfer and Nearby fields](generation/v2/itinerary.json) retain all optional fields without counting references as visits.

## V3

[Exact itinerary](generation/v3/itinerary.json)

### 2026-10-22

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+09:00 – 2026-10-22T13:00:00+09:00 | Visit Tokyo National Museum | Tokyo National Museum; 13-9 Uenokōen, Taito City, Tokyo 110-8712, Japan | main_poi/scheduled | No captured RAG association; other origin not inferred | Planned within the supplied date-specific hours of 09:30–17:00. Exhibition details and admission costs are not established by the supplied evidence. |
| 2026-10-22T14:00:00+09:00 – 2026-10-22T15:30:00+09:00 | Visit Sensō-ji | Sensō-ji; 2-chōme-3-1 Asakusa, Taito City, Tokyo 111-0032, Japan | main_poi/scheduled | No captured RAG association; other origin not inferred | Date-specific opening hours are unknown in the supplied evidence. |

**Saved transfers:**

- `{"from_activity_id":"tokyo-national-museum-20261022","to_activity_id":"sensoji-20261022","origin_place_id":"ChIJEX3XFIOOGGAR3XdJvRjWLyM","destination_place_id":"ChIJ8T1GpMGOGGARDYGSgpooDWw","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-22T13:00:00+09:00","arrival_time":"2026-10-22T13:33:12+09:00","provider_duration_seconds":1992.0,"distance_meters":2309,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T10:00:00+09:00 – 2026-10-23T12:00:00+09:00 | Visit Ueno Park | Ueno Park; 4 Uenokoen, Taito City, Tokyo 110-0007, Japan | main_poi/scheduled | No captured RAG association; other origin not inferred |  |
| 2026-10-23T13:00:00+09:00 – 2026-10-23T15:00:00+09:00 | Explore Akihabara Electric Town | Akihabara Electric Town; Akihabara Electric Town, Tokyo, Japan | main_poi/scheduled | No captured RAG association; other origin not inferred | The supplied evidence does not establish current operating status or hours for this district. |

**Saved transfers:**

- `{"from_activity_id":"ueno-park-20261023","to_activity_id":"akihabara-electric-town-20261023","origin_place_id":"ChIJw2qQRZuOGGARWmROEiM2y7E","destination_place_id":"ChIJzdWdgh2MGGARh4kg2pVZL3c","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-23T12:00:00+09:00","arrival_time":"2026-10-23T12:24:08+09:00","provider_duration_seconds":1448.0,"distance_meters":1731,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T13:45:00+09:00 – 2026-10-24T15:00:00+09:00 | Visit Shibuya Sky | Shibuya Sky; Japan, 〒150-6145 Tokyo, Shibuya, 2-chōme−24−１２ スクランブルスクエア 14階・45階 46階・屋上 | main_poi/scheduled | No captured RAG association; other origin not inferred | Hours are a regular weekly baseline; date-specific exceptions are unknown. |
| 2026-10-24T15:30:00+09:00 – 2026-10-24T16:00:00+09:00 | See Shibuya Scramble Crossing | Shibuya Scramble Crossing; 21 Udagawacho, Shibuya, Tokyo 150-0042, Japan | main_poi/scheduled | No captured RAG association; other origin not inferred |  |

**Saved transfers:**

- `{"from_activity_id":"shibuya-sky-20261024","to_activity_id":"shibuya-crossing-20261024","origin_place_id":"ChIJ4Rr2JWiLGGARcyRSHuZ-9G8","destination_place_id":"ChIJK9EM68qLGGARacmu4KJj5SA","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-24T15:00:00+09:00","arrival_time":"2026-10-24T15:04:38+09:00","provider_duration_seconds":278.0,"distance_meters":313,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T10:00:00+09:00 – 2026-10-25T11:30:00+09:00 | Visit Meiji Jingu | Meiji Jingu; 1-1 Yoyogikamizonochō, Shibuya, Tokyo 151-8557, Japan | main_poi/scheduled | No captured RAG association; other origin not inferred | Date-specific opening hours are unknown in the supplied evidence. |
| 2026-10-25T12:15:00+09:00 – 2026-10-25T14:15:00+09:00 | Visit Shinjuku Gyoen National Garden | Shinjuku Gyoen National Garden; 11 Naitōmachi, Shinjuku City, Tokyo 160-0014, Japan | main_poi/scheduled | No captured RAG association; other origin not inferred | Planned within the supplied regular weekly hours of 09:00–16:30; date-specific exceptions are unknown. |

**Saved transfers:**

- `{"from_activity_id":"meiji-jingu-20261025","to_activity_id":"shinjuku-gyoen-20261025","origin_place_id":"ChIJ5SZMmreMGGARcz8QSTiJyo8","destination_place_id":"ChIJPyOTG8KMGGARh_IXobWxHmo","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-25T11:30:00+09:00","arrival_time":"2026-10-25T11:54:47+09:00","provider_duration_seconds":1487.0,"distance_meters":1805,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-26

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-26T10:00:00+09:00 – 2026-10-26T11:30:00+09:00 | Visit the Imperial Palace | Imperial Palace; 1-1 Chiyoda, Chiyoda City, Tokyo 100-8111, Japan | main_poi/scheduled | No captured RAG association; other origin not inferred | Date-specific visitor access and hours are unknown in the supplied evidence. |
| 2026-10-26T12:30:00+09:00 – 2026-10-26T14:30:00+09:00 | Explore Tokyo Dome City | Tokyo Dome City; 1-chōme-3-61 Kōraku, Bunkyo City, Tokyo 112-0004, Japan | main_poi/scheduled | No captured RAG association; other origin not inferred | Date-specific operating details are unknown in the supplied evidence. |

**Saved transfers:**

- `{"from_activity_id":"imperial-palace-20261026","to_activity_id":"tokyo-dome-city-20261026","origin_place_id":"ChIJTQbYAg2MGGARt22eNwtfGtE","destination_place_id":"ChIJuxkVQeCNGGARfFgbeDEPG6g","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-26T11:30:00+09:00","arrival_time":"2026-10-26T12:04:56+09:00","provider_duration_seconds":2096.0,"distance_meters":2451,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

[Complete transfer and Nearby fields](generation/v3/itinerary.json) retain all optional fields without counting references as visits.

## Same-run V3 changes

[Complete draft](analysis/repair/draft.json), [complete final primary](analysis/repair/final-primary.json), and [lossless Repair](analysis/repair/repair.json) retain every real change, including unchanged/skipped attempts.

| Activity ID | Change | Saved before | Saved after |
| --- | --- | --- | --- |
| art-front-gallery-20261024 | removed | ["2026-10-24", {"activity_kind": "main_poi", "time_use": "scheduled", "activity_id": "art-front-gallery-20261024", "title": "Visit ART FRONT GALLERY", "place_name": "ART FRONT GALLERY", "source_place_id": "ChIJ1d8x9UWLGGARlBR79HRq4eg", "location": "Japan, 〒150-0033 Tokyo, Shibuya, Sarugakuchō, 29−１８ HILLSIDE TERRACE Building E, A棟", "start_time": "2026-10-24T11:00:00+09:00", "end_time": "2026-10-24T13:00:00+09:00", "estimated_cost": null, "notes": "The supplied evidence identifies an art gallery but does not specify its current exhibitions. Hours are a regular weekly baseline; date-specific exceptions are unknown."}] | null |

Transfer, route-diagnostic and recommendation differences remain in the complete stage JSON, even when no activity row changes. Candidate source attribution is observational; no causal improvement is inferred from independent generations.
