# Case-08 selected itineraries

Saved final V0-V3 schedules. Timestamps and offsets are submitted values, including any conflicts; presentation does not correct them. Generated costs, access and route claims are not independent certification. Nearby recommendations remain unscheduled. Full notes, addresses and diagnostics remain in the linked JSON.

Origin labels use saved canonical associations in the [candidate process](analysis/poi-process/opportunities.json) and [V3 origin capture](analysis/poi-process/v3-origins.json). Missing associations do not prove Google-only discovery.

## V0

[Selected final itinerary](generation/v0/itinerary.json).

### 2026-10-22

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-22T09:30:00+02:00 | 2026-10-22T11:00:00+02:00 | main_poi / scheduled | Visit Barcelona Cathedral / Barcelona Cathedral | Model knowledge / estimates |
| 2026-10-22T11:00:00+02:00 | 2026-10-22T11:20:00+02:00 | transport / scheduled | Walk to the Picasso Museum | Model knowledge / estimates |
| 2026-10-22T11:20:00+02:00 | 2026-10-22T13:00:00+02:00 | main_poi / scheduled | Visit the Picasso Museum / Picasso Museum | Model knowledge / estimates |

### 2026-10-23

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+02:00 | 2026-10-23T11:30:00+02:00 | main_poi / scheduled | Visit Sagrada Família / Sagrada Família | Model knowledge / estimates |
| 2026-10-23T11:30:00+02:00 | 2026-10-23T11:50:00+02:00 | transport / scheduled | Walk to Sant Pau Art Nouveau Site | Model knowledge / estimates |
| 2026-10-23T11:50:00+02:00 | 2026-10-23T13:20:00+02:00 | main_poi / scheduled | Explore the Sant Pau Art Nouveau Site / Sant Pau Art Nouveau Site | Model knowledge / estimates |

### 2026-10-24

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-24T09:30:00+02:00 | 2026-10-24T11:00:00+02:00 | main_poi / scheduled | Visit Casa Batlló / Casa Batlló | Model knowledge / estimates |
| 2026-10-24T11:00:00+02:00 | 2026-10-24T11:15:00+02:00 | transport / scheduled | Walk to Casa Milà | Model knowledge / estimates |
| 2026-10-24T11:15:00+02:00 | 2026-10-24T12:45:00+02:00 | main_poi / scheduled | Visit Casa Milà (La Pedrera) / Casa Milà (La Pedrera) | Model knowledge / estimates |

### Unscheduled references

| Reference | Associated day | Reason / uncertainty |
| --- | --- | --- |
| Palau de la Música Catalana | 2026-10-22 | An additional architectural landmark to consider alongside the planned historic center and El Born visits on this day. Model-knowledge suggestion; proximity and availability are estimates and have not been checked. |

## V1

[Selected final itinerary](generation/v1/itinerary.json).

### 2026-10-22

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-22T09:30:00+02:00 | 2026-10-22T12:00:00+02:00 | main_poi / scheduled | Visit the Basilica of the Sagrada Familia / Basilica of the Sagrada Familia | Google |
| 2026-10-22T13:00:00+02:00 | 2026-10-22T14:30:00+02:00 | main_poi / scheduled | Explore Casa Batlló / Casa Batlló | Google |
| 2026-10-22T16:00:00+02:00 | 2026-10-22T17:30:00+02:00 | main_poi / scheduled | Visit Casa de l'Arquitectura de Barcelona / Casa de l'Arquitectura de Barcelona | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| barcelona-20261022-sagrada-familia to barcelona-20261022-casa-batllo | WALK | 2026-10-22T12:00:00+02:00 | 2026-10-22T12:25:29+02:00 |
| barcelona-20261022-casa-batllo to barcelona-20261022-casa-arquitectura | WALK | 2026-10-22T14:30:00+02:00 | 2026-10-22T14:58:19+02:00 |

### 2026-10-23

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+02:00 | 2026-10-23T11:00:00+02:00 | main_poi / scheduled | Explore the Gothic Quarter / Gothic Quarter | Google |
| 2026-10-23T11:30:00+02:00 | 2026-10-23T12:15:00+02:00 | main_poi / scheduled | Visit Temple d'August / Temple d'August | Google |
| 2026-10-23T13:00:00+02:00 | 2026-10-23T14:30:00+02:00 | main_poi / scheduled | Visit Casa de la Seda / Casa de la Seda | Google |
| 2026-10-23T15:00:00+02:00 | 2026-10-23T16:00:00+02:00 | main_poi / scheduled | Browse Mercat de la Boqueria / Mercat de la Boqueria | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| barcelona-20261023-gothic-quarter to barcelona-20261023-temple-august | WALK | 2026-10-23T11:00:00+02:00 | 2026-10-23T11:03:11+02:00 |
| barcelona-20261023-temple-august to barcelona-20261023-casa-seda | WALK | 2026-10-23T12:15:00+02:00 | 2026-10-23T12:21:53+02:00 |
| barcelona-20261023-casa-seda to barcelona-20261023-boqueria | WALK | 2026-10-23T14:30:00+02:00 | 2026-10-23T14:41:24+02:00 |

### 2026-10-24

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+02:00 | 2026-10-24T11:30:00+02:00 | main_poi / scheduled | See Palau de la Música Catalana / Palau de la Música Catalana | Google |
| 2026-10-24T12:00:00+02:00 | 2026-10-24T14:30:00+02:00 | main_poi / scheduled | Visit the Museum of the History of Catalonia / Museum of the History of Catalonia | Google |
| 2026-10-24T15:30:00+02:00 | 2026-10-24T17:30:00+02:00 | main_poi / scheduled | Explore Montjuïc Castle / Montjuïc Castle | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| barcelona-20261024-palau-musica to barcelona-20261024-history-catalonia | WALK | 2026-10-24T11:30:00+02:00 | 2026-10-24T11:49:36+02:00 |
| barcelona-20261024-history-catalonia to barcelona-20261024-montjuic-castle | DRIVE | 2026-10-24T14:30:00+02:00 | 2026-10-24T14:57:25+02:00 |

### Unscheduled references

| Reference | Associated day | Reason / uncertainty |
| --- | --- | --- |
| Sagrada família | 2026-10-22 | Museum near Basilica of the Sagrada Familia (approximately 0 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Casa Amatller | 2026-10-22 | Museum near Casa Batlló (approximately 17 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| SABOR VITAL 66 SL | 2026-10-22 | Restaurant near Casa de l'Arquitectura de Barcelona (approximately 34 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |

## V2

[Selected final itinerary](generation/v2/itinerary.json).

### 2026-10-22

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-22T09:30:00+02:00 | 2026-10-22T11:30:00+02:00 | main_poi / scheduled | Visit the Basilica of the Sagrada Familia / Basilica of the Sagrada Familia | Google |
| 2026-10-22T12:30:00+02:00 | 2026-10-22T14:00:00+02:00 | main_poi / scheduled | Explore Casa Batlló / Casa Batlló | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| visit-sagrada-familia to visit-casa-batllo | WALK | 2026-10-22T11:30:00+02:00 | 2026-10-22T11:55:29+02:00 |

### 2026-10-23

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-23T10:00:00+02:00 | 2026-10-23T11:15:00+02:00 | main_poi / scheduled | Visit the Cathedral of Barcelona / Cathedral of Barcelona | Google |
| 2026-10-23T11:45:00+02:00 | 2026-10-23T12:15:00+02:00 | main_poi / scheduled | See the Temple d'August / Temple d'August | Google |
| 2026-10-23T13:15:00+02:00 | 2026-10-23T15:00:00+02:00 | main_poi / scheduled | Explore Casa Padellàs (Barcelona History Museum MUHBA) / Casa Padellàs (Barcelona History Museum MUHBA) | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| visit-barcelona-cathedral to visit-temple-daugust | WALK | 2026-10-23T11:15:00+02:00 | 2026-10-23T11:17:59+02:00 |
| visit-temple-daugust to visit-muhba-casa-padellas | WALK | 2026-10-23T12:15:00+02:00 | 2026-10-23T12:16:36+02:00 |

### 2026-10-24

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-24T10:30:00+02:00 | 2026-10-24T12:30:00+02:00 | main_poi / scheduled | Visit Montjuïc Castle / Montjuïc Castle | Google |
| 2026-10-24T14:00:00+02:00 | 2026-10-24T16:00:00+02:00 | main_poi / scheduled | Explore Poble Espanyol / Poble Espanyol | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| visit-montjuic-castle to visit-poble-espanyol | WALK | 2026-10-24T12:30:00+02:00 | 2026-10-24T13:09:40+02:00 |

### Unscheduled references

| Reference | Associated day | Reason / uncertainty |
| --- | --- | --- |
| Sagrada família | 2026-10-22 | Museum near Basilica of the Sagrada Familia (approximately 0 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Casa Amatller | 2026-10-22 | Museum near Casa Batlló (approximately 17 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Kottoya - Omakase & Sushi | 2026-10-23 | Restaurant near Casa Padellàs (Barcelona History Museum MUHBA) (approximately 29 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |

## V3

[Selected final itinerary](generation/v3/itinerary.json).

### 2026-10-22

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-22T11:20:00+02:00 | 2026-10-22T12:00:00+02:00 | main_poi / scheduled | See the Temple d'August / Temple d'August | Google tools; no recorded RAG origin |
| 2026-10-22T12:15:00+02:00 | 2026-10-22T14:00:00+02:00 | main_poi / scheduled | Explore Casa Padellàs (Barcelona History Museum MUHBA) / Casa Padellàs (Barcelona History Museum MUHBA) | Google tools; no recorded RAG origin |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| day1-temple to day1-muhba | WALK | 2026-10-22T12:00:00+02:00 | 2026-10-22T12:01:36+02:00 |

### 2026-10-23

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+02:00 | 2026-10-23T11:30:00+02:00 | main_poi / scheduled | Visit the Basilica of the Sagrada Familia / Basilica of the Sagrada Familia | Google tools; no recorded RAG origin |
| 2026-10-23T12:15:00+02:00 | 2026-10-23T14:15:00+02:00 | main_poi / scheduled | Visit Casa Batlló / Casa Batlló | Google tools; no recorded RAG origin |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| day2-sagrada to day2-casa-batllo | WALK | 2026-10-23T11:30:00+02:00 | 2026-10-23T11:55:29+02:00 |

### 2026-10-24

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-24T09:30:00+02:00 | 2026-10-24T10:30:00+02:00 | main_poi / scheduled | Browse Mercat de la Boqueria / Mercat de la Boqueria | Google tools; no recorded RAG origin |
| 2026-10-24T11:45:00+02:00 | 2026-10-24T13:45:00+02:00 | main_poi / scheduled | Explore Montjuïc Castle / Montjuïc Castle | Google tools; no recorded RAG origin |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| day3-boqueria to day3-montjuic-castle | TRANSIT | 2026-10-24T10:30:00+02:00 | 2026-10-24T11:10:10+02:00 |

### Unscheduled references

| Reference | Associated day | Reason / uncertainty |
| --- | --- | --- |
| Lasaaagna di Dana | 2026-10-22 | Restaurant near Temple d'August (approximately 15 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Sagrada família | 2026-10-23 | Museum near Basilica of the Sagrada Familia (approximately 0 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Casa Amatller | 2026-10-23 | Museum near Casa Batlló (approximately 17 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |

## Same-run V3 changes

One deterministic deletion removed the Cathedral visit on 22 October. The other six primary visits continue. No Repair model call occurred. The removed visit had independent grounding/opening PASS; its removal is not a factual repair. The saved pair is 96.6667 to 100, with density deduction 3.3333 to zero.

[Complete lossless stages](analysis/repair/stages.json), [Repair mechanism](analysis/repair/mechanism.json), [current paired summary](evaluation/pair/summary.json).

[Evaluation, acceptance and limitations](report.md).
