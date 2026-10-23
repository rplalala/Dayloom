# Case-04 itineraries

Singapore, **25-26 October 2026**, Sunday and Monday, local time UTC+08:00.

These [date-revised schedules](rescheduled/revision.json) retain the selected V0-V3
visit identities, order and local clock times. They are an offline one-day shift,
not new model generations. Opening/access, transit and weather are not verified
for these dates. Original Primary/Pair scores apply only to 24-25 October.
Proposed transfer windows below carry no provider feasibility verdict.

The [current request](../inputs/case-04.json) says two-day trip because the revised
dates span Sunday and Monday. Original outputs retain all notes, weather, costs,
Nearby recommendations and provenance. [Completion review](analysis/repair/completion-review.json)
uses the original dates and unchanged validation evidence.

## V0

[Revised schedule](rescheduled/v0.json) · [Original output](generation/v0/itinerary.json)

### 2026-10-25

| Start | End | Activity / place | Address | Role |
| --- | --- | --- | --- | --- |
| 09:00 | 11:30 | Explore Singapore Botanic Gardens / Singapore Botanic Gardens | Singapore | main_poi / scheduled |
| 11:30 | 12:05 | Public transport to National Gallery Singapore / — | — | transport / scheduled |
| 12:05 | 14:00 | Visit National Gallery Singapore / National Gallery Singapore | Civic District | main_poi / scheduled |
| 14:00 | 14:20 | Walk to Merlion Park / — | — | transport / scheduled |
| 14:20 | 15:00 | Take in the waterfront and city views at Merlion Park / Merlion Park | Marina Bay | main_poi / scheduled |
| 15:00 | 15:35 | Walk along Marina Bay to Gardens by the Bay / — | — | transport / scheduled |
| 15:35 | 18:30 | Explore Gardens by the Bay / Gardens by the Bay | Marina Bay | main_poi / scheduled |

### 2026-10-26

| Start | End | Activity / place | Address | Role |
| --- | --- | --- | --- | --- |
| 09:00 | 10:30 | Walk through Fort Canning Park / Fort Canning Park | Central Singapore | main_poi / scheduled |
| 10:30 | 11:00 | Public transport to Chinatown / — | — | transport / scheduled |
| 11:00 | 12:15 | Visit Buddha Tooth Relic Temple / Buddha Tooth Relic Temple | Chinatown | main_poi / scheduled |
| 12:15 | 12:50 | Public transport toward Singapore Flyer / — | — | transport / scheduled |
| 12:50 | 14:20 | Enjoy elevated city views from Singapore Flyer / Singapore Flyer | Marina Bay | main_poi / scheduled |
| 14:20 | 14:40 | Walk to ArtScience Museum / — | — | transport / scheduled |
| 14:40 | 16:30 | Explore ArtScience Museum / ArtScience Museum | Marina Bay | main_poi / scheduled |

## V1

[Revised schedule](rescheduled/v1.json) · [Original output](generation/v1/itinerary.json)

### 2026-10-25

| Start | End | Activity / place | Address | Role |
| --- | --- | --- | --- | --- |
| 08:00 | 09:00 | Visit Buddha Tooth Relic Temple / Buddha Tooth Relic Temple | 288 S Bridge Rd, Singapore 058840 | main_poi / scheduled |
| 09:45 | 10:30 | See Merlion Park / Merlion Park | 1 Fullerton Rd, Singapore 049213 | main_poi / scheduled |
| 10:45 | 13:00 | Explore National Gallery Singapore / National Gallery Singapore | Singapore 178957 | main_poi / scheduled |
| 13:30 | 14:30 | Walk around Fort Canning Park / Fort Canning Park | Singapore | main_poi / scheduled |
| 15:30 | 16:15 | Walk across The Helix Bridge / The Helix Bridge | Singapore | main_poi / scheduled |

### 2026-10-26

| Start | End | Activity / place | Address | Role |
| --- | --- | --- | --- | --- |
| 08:00 | 11:30 | Explore Singapore Botanic Gardens / Singapore Botanic Gardens | 1 Cluny Rd, Singapore 259569 | main_poi / scheduled |
| 13:00 | 14:00 | Take in city views at Singapore Flyer / Singapore Flyer | 30 Raffles Ave., Singapore 039803 | main_poi / scheduled |

### Proposed transfers

| From | To | Mode | Departure | Arrival |
| --- | --- | --- | --- | --- |
| day1-buddha-tooth-relic-temple | day1-merlion-park | WALK | 2026-10-25T09:00:00+08:00 | 2026-10-25T09:23:27+08:00 |
| day1-merlion-park | day1-national-gallery | WALK | 2026-10-25T10:30:00+08:00 | 2026-10-25T10:38:39+08:00 |
| day1-national-gallery | day1-fort-canning | WALK | 2026-10-25T13:00:00+08:00 | 2026-10-25T13:16:59+08:00 |
| day1-fort-canning | day1-helix-bridge | WALK | 2026-10-25T14:30:00+08:00 | 2026-10-25T15:04:40+08:00 |
| day2-botanic-gardens | day2-singapore-flyer | TRANSIT | 2026-10-26T11:30:00+08:00 | 2026-10-26T12:09:01+08:00 |

## V2

[Revised schedule](rescheduled/v2.json) · [Original output](generation/v2/itinerary.json)

### 2026-10-25

| Start | End | Activity / place | Address | Role |
| --- | --- | --- | --- | --- |
| 08:30 | 09:40 | Explore Fort Canning Park / Fort Canning Park | Singapore | main_poi / scheduled |
| 10:00 | 12:00 | Visit the National Museum of Singapore / National Museum of Singapore | 93 Stamford Rd, Singapore 178897 | main_poi / scheduled |
| 12:30 | 14:30 | Explore National Gallery Singapore / National Gallery Singapore | Singapore 178957 | main_poi / scheduled |
| 14:50 | 15:30 | See Merlion Park and the waterfront views / Merlion Park | 1 Fullerton Rd, Singapore 049213 | main_poi / scheduled |

### 2026-10-26

| Start | End | Activity / place | Address | Role |
| --- | --- | --- | --- | --- |
| 09:00 | 12:00 | Explore Gardens by the Bay / Gardens by the Bay | 18 Marina Gardens Dr, Singapore 018953 | main_poi / scheduled |
| 12:30 | 13:30 | Take in the views from Marina Barrage Green Roof / Marina Barrage Green Roof | Unnamed Road, Marina Barrage, open space, Singapore | main_poi / scheduled |
| 14:00 | 15:00 | Visit Buddha Tooth Relic Temple / Buddha Tooth Relic Temple | 288 S Bridge Rd, Singapore 058840 | main_poi / scheduled |

### Proposed transfers

| From | To | Mode | Departure | Arrival |
| --- | --- | --- | --- | --- |
| 2026-10-24-fort-canning | 2026-10-24-national-museum | WALK | 2026-10-25T09:40:00+08:00 | 2026-10-25T09:49:32+08:00 |
| 2026-10-24-national-museum | 2026-10-24-national-gallery | WALK | 2026-10-25T12:00:00+08:00 | 2026-10-25T12:16:40+08:00 |
| 2026-10-24-national-gallery | 2026-10-24-merlion | WALK | 2026-10-25T14:30:00+08:00 | 2026-10-25T14:38:35+08:00 |
| 2026-10-25-gardens-by-the-bay | 2026-10-25-marina-barrage-roof | WALK | 2026-10-26T12:00:00+08:00 | 2026-10-26T12:16:22+08:00 |
| 2026-10-25-marina-barrage-roof | 2026-10-25-buddha-tooth-relic-temple | TRANSIT | 2026-10-26T13:30:00+08:00 | 2026-10-26T13:47:23+08:00 |

## V3

[Revised schedule](rescheduled/v3.json) · [Original output](generation/v3/itinerary.json)

### 2026-10-25

| Start | End | Activity / place | Address | Role |
| --- | --- | --- | --- | --- |
| 12:45 | 14:45 | Explore National Gallery Singapore / National Gallery Singapore | Singapore 178957 | main_poi / scheduled |
| 15:15 | 15:45 | See Merlion Park / Merlion Park | 1 Fullerton Rd, Singapore 049213 | main_poi / scheduled |
| 16:15 | 17:15 | Singapore Flyer / Singapore Flyer | 30 Raffles Ave., Singapore 039803 | main_poi / scheduled |

### 2026-10-26

| Start | End | Activity / place | Address | Role |
| --- | --- | --- | --- | --- |
| 09:00 | 13:00 | Explore Gardens by the Bay / Gardens by the Bay | 18 Marina Gardens Dr, Singapore 018953 | main_poi / scheduled |
| 19:15 | 19:45 | Walk across The Helix Bridge / The Helix Bridge | Singapore | main_poi / scheduled |
| 20:00 | 20:15 | Watch Spectra - A Light & Water Show / Spectra - A Light & Water Show | 10 Bayfront Ave, Event Plaza Marina Bay Sands, Singapore 018972 | main_poi / scheduled |

### Proposed transfers

| From | To | Mode | Departure | Arrival |
| --- | --- | --- | --- | --- |
| sat-national-gallery | sat-merlion-park | WALK | 2026-10-25T14:45:00+08:00 | 2026-10-25T14:53:35+08:00 |
| sat-merlion-park | sat-singapore-flyer | WALK | 2026-10-25T15:45:00+08:00 | 2026-10-25T16:03:41+08:00 |
| sun-gardens-by-the-bay | sun-helix-bridge | WALK | 2026-10-26T13:00:00+08:00 | 2026-10-26T13:15:08+08:00 |
| sun-helix-bridge | sun-spectra-show | WALK | 2026-10-26T19:45:00+08:00 | 2026-10-26T19:53:00+08:00 |
