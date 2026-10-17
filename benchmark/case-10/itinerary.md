# Case-10 selected itineraries

Saved final V0-V3 schedules. Timestamps and offsets are submitted values, including any conflicts; presentation does not correct them. Generated costs, access and route claims are not independent certification. Nearby recommendations remain unscheduled. Full notes, addresses and diagnostics remain in the linked JSON.

Origin labels use saved canonical associations in the [candidate process](analysis/poi-process/opportunities.json) and [V3 origin capture](analysis/poi-process/v3-origins.json). Missing associations do not prove Google-only discovery.

## V0

[Selected final itinerary](generation/v0/itinerary.json).

### 2026-10-22

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+01:00 | 2026-10-22T13:00:00+01:00 | main_poi / scheduled | British Museum — first visit / British Museum | Model knowledge / estimates |
| 2026-10-22T13:00:00+01:00 | 2026-10-22T13:25:00+01:00 | transport / scheduled | Walk to Fitzrovia | Model knowledge / estimates |
| 2026-10-22T13:25:00+01:00 | 2026-10-22T15:00:00+01:00 | main_poi / scheduled | Explore Fitzrovia / Fitzrovia | Model knowledge / estimates |

### 2026-10-23

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-23T10:00:00+01:00 | 2026-10-23T12:15:00+01:00 | main_poi / scheduled | National Gallery / National Gallery | Model knowledge / estimates |
| 2026-10-23T12:15:00+01:00 | 2026-10-23T12:35:00+01:00 | transport / scheduled | Walk to St James's Park | Model knowledge / estimates |
| 2026-10-23T12:35:00+01:00 | 2026-10-23T13:35:00+01:00 | main_poi / scheduled | St James's Park / St James's Park | Model knowledge / estimates |
| 2026-10-23T13:35:00+01:00 | 2026-10-23T13:55:00+01:00 | transport / scheduled | Walk to Westminster Abbey | Model knowledge / estimates |
| 2026-10-23T13:55:00+01:00 | 2026-10-23T15:30:00+01:00 | main_poi / scheduled | Westminster Abbey / Westminster Abbey | Model knowledge / estimates |

### 2026-10-24

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+01:00 | 2026-10-24T13:00:00+01:00 | main_poi / scheduled | British Museum — second visit / British Museum | Model knowledge / estimates |
| 2026-10-24T13:00:00+01:00 | 2026-10-24T13:25:00+01:00 | transport / scheduled | Walk to Covent Garden | Model knowledge / estimates |
| 2026-10-24T13:25:00+01:00 | 2026-10-24T15:00:00+01:00 | main_poi / scheduled | Explore Covent Garden / Covent Garden | Model knowledge / estimates |

### 2026-10-25

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-25T10:00:00+01:00 | 2026-10-25T11:30:00+01:00 | main_poi / scheduled | Explore historic Greenwich / Greenwich | Model knowledge / estimates |
| 2026-10-25T11:30:00+01:00 | 2026-10-25T11:45:00+01:00 | transport / scheduled | Walk to Greenwich Park | Model knowledge / estimates |
| 2026-10-25T11:45:00+01:00 | 2026-10-25T13:15:00+01:00 | main_poi / scheduled | Greenwich Park / Greenwich Park | Model knowledge / estimates |

### Unscheduled references

| Reference | Associated day | Reason / uncertainty |
| --- | --- | --- |
| Grant Museum of Zoology | 2026-10-22 | An optional additional museum to consider near the Bloomsbury area planned for the British Museum visits, offering a different subject from the itinerary's art and history. Proximity and availability are model estimates and have not been checked. |
| Queen's House | 2026-10-25 | An optional art and architecture stop to consider in the Greenwich area visited on the final day. Proximity and availability are model estimates and have not been checked. |

## V1

[Selected final itinerary](generation/v1/itinerary.json).

### 2026-10-22

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+01:00 | 2026-10-22T12:00:00+01:00 | main_poi / scheduled | First British Museum visit / The British Museum | Google |
| 2026-10-22T13:00:00+01:00 | 2026-10-22T15:00:00+01:00 | main_poi / scheduled | The National Gallery / The National Gallery | Google |
| 2026-10-22T15:15:00+01:00 | 2026-10-22T16:00:00+01:00 | main_poi / scheduled | Trafalgar Square / Trafalgar Square | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| bm-visit-1 to national-gallery-1 | WALK | 2026-10-22T12:00:00+01:00 | 2026-10-22T12:18:27+01:00 |
| national-gallery-1 to trafalgar-1 | WALK | 2026-10-22T15:00:00+01:00 | 2026-10-22T15:00:43+01:00 |

### 2026-10-23

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-23T10:00:00+01:00 | 2026-10-23T12:00:00+01:00 | main_poi / scheduled | Second British Museum visit / The British Museum | Google |
| 2026-10-23T12:30:00+01:00 | 2026-10-23T13:00:00+01:00 | main_poi / scheduled | York Watergate / York Watergate | Google |
| 2026-10-23T14:00:00+01:00 | 2026-10-23T15:30:00+01:00 | main_poi / scheduled | Westminster Abbey / Westminster Abbey | Google |
| 2026-10-23T15:45:00+01:00 | 2026-10-23T16:15:00+01:00 | main_poi / scheduled | Big Ben / Big Ben | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| bm-visit-2 to york-watergate-1 | WALK | 2026-10-23T12:00:00+01:00 | 2026-10-23T12:20:47+01:00 |
| york-watergate-1 to westminster-abbey-1 | WALK | 2026-10-23T13:00:00+01:00 | 2026-10-23T13:17:11+01:00 |
| westminster-abbey-1 to big-ben-1 | WALK | 2026-10-23T15:30:00+01:00 | 2026-10-23T15:34:51+01:00 |

### 2026-10-24

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-24T09:30:00+01:00 | 2026-10-24T12:30:00+01:00 | main_poi / scheduled | Tower of London / Tower of London | Google |
| 2026-10-24T13:00:00+01:00 | 2026-10-24T14:00:00+01:00 | main_poi / scheduled | Tower Bridge / Tower Bridge | Google |
| 2026-10-24T14:30:00+01:00 | 2026-10-24T15:30:00+01:00 | main_poi / scheduled | Borough Market / Borough Market | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| tower-london-1 to tower-bridge-1 | WALK | 2026-10-24T12:30:00+01:00 | 2026-10-24T12:37:57+01:00 |
| tower-bridge-1 to borough-market-1 | WALK | 2026-10-24T14:00:00+01:00 | 2026-10-24T14:18:14+01:00 |

### 2026-10-25

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-25T10:00:00Z | 2026-10-25T11:30:00Z | main_poi / scheduled | Hyde Park / Hyde Park | Google |
| 2026-10-25T12:30:00Z | 2026-10-25T15:00:00Z | main_poi / scheduled | Natural History Museum / Natural History Museum | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| hyde-park-1 to natural-history-museum-1 | WALK | 2026-10-25T11:30:00Z | 2026-10-25T12:01:07Z |

### Unscheduled references

| Reference | Associated day | Reason / uncertainty |
| --- | --- | --- |
| British museum | 2026-10-22 | Museum near The British Museum (approximately 0 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Muriel's Espresso Bar | 2026-10-22 | Cafe near The National Gallery (approximately 19 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Treats Sandwich Bar | 2026-10-23 | Restaurant near York Watergate (approximately 39 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |

## V2

[Selected final itinerary](generation/v2/itinerary.json).

### 2026-10-22

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+01:00 | 2026-10-22T13:00:00+01:00 | main_poi / scheduled | The British Museum — first visit / The British Museum | Google |
| 2026-10-22T14:00:00+01:00 | 2026-10-22T16:00:00+01:00 | main_poi / scheduled | The National Gallery / The National Gallery | Google |
| 2026-10-22T16:15:00+01:00 | 2026-10-22T16:45:00+01:00 | main_poi / scheduled | York Watergate / York Watergate | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| bm-visit-1 to national-gallery | WALK | 2026-10-22T13:00:00+01:00 | 2026-10-22T13:18:27+01:00 |
| national-gallery to york-watergate | WALK | 2026-10-22T16:00:00+01:00 | 2026-10-22T16:06:12+01:00 |

### 2026-10-23

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-23T10:00:00+01:00 | 2026-10-23T12:30:00+01:00 | main_poi / scheduled | The British Museum — second visit / The British Museum | Google |
| 2026-10-23T13:30:00+01:00 | 2026-10-23T14:00:00+01:00 | main_poi / scheduled | Big Ben / Big Ben | Google + RAG |
| 2026-10-23T14:15:00+01:00 | 2026-10-23T15:30:00+01:00 | main_poi / scheduled | Westminster Abbey / Westminster Abbey | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| bm-visit-2 to big-ben | WALK | 2026-10-23T12:30:00+01:00 | 2026-10-23T13:01:28+01:00 |
| big-ben to westminster-abbey | WALK | 2026-10-23T14:00:00+01:00 | 2026-10-23T14:04:36+01:00 |

### 2026-10-24

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+01:00 | 2026-10-24T12:30:00+01:00 | main_poi / scheduled | Tower of London / Tower of London | Google + RAG |
| 2026-10-24T12:45:00+01:00 | 2026-10-24T13:45:00+01:00 | main_poi / scheduled | Tower Bridge / Tower Bridge | Google + RAG |
| 2026-10-24T14:15:00+01:00 | 2026-10-24T15:30:00+01:00 | main_poi / scheduled | Borough Market / Borough Market | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| tower-of-london to tower-bridge | WALK | 2026-10-24T12:30:00+01:00 | 2026-10-24T12:37:57+01:00 |
| tower-bridge to borough-market | WALK | 2026-10-24T13:45:00+01:00 | 2026-10-24T14:03:14+01:00 |

### 2026-10-25

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-25T10:00:00Z | 2026-10-25T12:00:00Z | main_poi / scheduled | Kensington Palace / Kensington Palace | Google + RAG |
| 2026-10-25T12:30:00Z | 2026-10-25T14:30:00Z | main_poi / scheduled | Hyde Park / Hyde Park | Google |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| kensington-palace to hyde-park | WALK | 2026-10-25T12:00:00Z | 2026-10-25T12:25:22Z |

### Unscheduled references

| Reference | Associated day | Reason / uncertainty |
| --- | --- | --- |
| British museum | 2026-10-22 | Museum near The British Museum (approximately 0 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Muriel's Espresso Bar | 2026-10-22 | Cafe near The National Gallery (approximately 19 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Treats Sandwich Bar | 2026-10-22 | Restaurant near York Watergate (approximately 39 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |

## V3

[Selected final itinerary](generation/v3/itinerary.json).

### 2026-10-22

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+01:00 | 2026-10-22T12:00:00+01:00 | main_poi / scheduled | First British Museum visit / The British Museum | Google tools; no recorded RAG origin |
| 2026-10-22T15:15:00+01:00 | 2026-10-22T15:45:00+01:00 | main_poi / scheduled | Look around Trafalgar Square / Trafalgar Square | Google tools; no recorded RAG origin |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| museum-visit-1 to trafalgar-square | WALK | 2026-10-22T12:00:00+01:00 | 2026-10-22T12:19:18+01:00 |

### 2026-10-23

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-23T10:00:00+01:00 | 2026-10-23T12:00:00+01:00 | main_poi / scheduled | Second British Museum visit / The British Museum | Google tools; no recorded RAG origin |
| 2026-10-23T13:30:00+01:00 | 2026-10-23T15:00:00+01:00 | main_poi / scheduled | Visit Westminster Abbey / Westminster Abbey | Google tools; no recorded RAG origin |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| museum-visit-2 to westminster-abbey | WALK | 2026-10-23T12:00:00+01:00 | 2026-10-23T12:33:12+01:00 |

### 2026-10-24

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+01:00 | 2026-10-24T11:30:00+01:00 | main_poi / scheduled | Explore Tower Bridge / Tower Bridge | Google + RAG |
| 2026-10-24T12:00:00+01:00 | 2026-10-24T15:00:00+01:00 | main_poi / scheduled | Explore the Tower of London / Tower of London | Google + RAG |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| tower-bridge to tower-of-london | WALK | 2026-10-24T11:30:00+01:00 | 2026-10-24T11:37:50+01:00 |

### 2026-10-25

| Start | End | Role / time use | Activity / venue | Recorded origin |
| --- | --- | --- | --- | --- |
| 2026-10-25T11:00:00Z | 2026-10-25T12:30:00Z | main_poi / scheduled | Spend time in Hyde Park / Hyde Park | Google tools; no recorded RAG origin |
| 2026-10-25T13:15:00Z | 2026-10-25T13:45:00Z | main_poi / scheduled | Brief exterior look at Buckingham Palace / Buckingham Palace | Google tools; no recorded RAG origin |

| Transfer | Mode | Departure | Arrival |
| --- | --- | --- | --- |
| hyde-park to buckingham-palace | WALK | 2026-10-25T12:30:00Z | 2026-10-25T12:55:40Z |

### Unscheduled references

| Reference | Associated day | Reason / uncertainty |
| --- | --- | --- |
| British museum | 2026-10-22 | Museum near The British Museum (approximately 0 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| PRETZELMARIE | 2026-10-22 | Restaurant near Trafalgar Square (approximately 56 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |
| Cellarium Cafe & Terrace | 2026-10-23 | Restaurant near Westminster Abbey (approximately 89 m straight-line). Availability, prices and accessibility are unverified; straight-line distance is not a walking route. |

## Same-run V3 changes

Two deterministic deletions removed National Gallery on 22 October and York Watergate on 23 October. The two British Museum visits remain on distinct dates. No primary visit was added and no Repair model call occurred. The saved pair is 93 to 97.5; Westminster Abbey access remains UNKNOWN in both stages.

[Lossless draft difference](analysis/repair/draft-difference.json), [final-primary difference](analysis/repair/final_primary-difference.json), [mechanism](analysis/repair/mechanism.json), [paired summary](evaluation/v3-pair/summary.json).

[Evaluation, acceptance and limitations](report.md).
