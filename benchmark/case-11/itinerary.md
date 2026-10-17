# Case-11 selected r02 itineraries

Final schedules generated on source `bc985c273afcf48c5f1d4da59be532c22d403efd`.
Times and fields remain submitted values. Recorded discovery origins are producer
observations; independent relevance is reported separately. Full notes and Nearby
references remain in each itinerary JSON; Nearby-only references are not scheduled visits.

V3 [draft](analysis/repair/draft.json) and [final-primary](analysis/repair/final-primary.json)
are identical: no Repair round, added/removed/replaced visit or retiming occurred.
The selected final itinerary also carries post-primary Nearby recommendations; these
remain distinct from Repair changes. The completed common-policy pair scores
100 for both stages, with a zero difference; the independent Primary is unchanged.

## V0

[Selected itinerary](generation/v0/itinerary.json)

### 2026-10-22

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:00:00+02:00 | 12:30:00+02:00 | Explore the Louvre's art collections | Model knowledge |
| 12:30:00+02:00 | 12:45:00+02:00 | Walk to Palais-Royal | No linked POI |
| 12:45:00+02:00 | 14:00:00+02:00 | See the Palais-Royal and its historic arcades | Model knowledge |

### 2026-10-23

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 09:30:00+02:00 | 11:00:00+02:00 | Visit Sainte-Chapelle | Model knowledge |
| 11:00:00+02:00 | 11:15:00+02:00 | Walk to the Conciergerie | No linked POI |
| 11:15:00+02:00 | 13:00:00+02:00 | Explore the Conciergerie | Model knowledge |

### 2026-10-24

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:00:00+02:00 | 11:30:00+02:00 | Visit the Basilica of Sacré-Cœur | Model knowledge |
| 11:30:00+02:00 | 12:00:00+02:00 | Walk to the Musée de Montmartre | No linked POI |
| 12:00:00+02:00 | 14:00:00+02:00 | Visit the Musée de Montmartre | Model knowledge |

### 2026-10-25

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:00:00+01:00 | 12:30:00+01:00 | Explore the Musée d'Orsay | Model knowledge |
| 12:30:00+01:00 | 13:00:00+01:00 | Travel to the Eiffel Tower area | No linked POI |
| 13:00:00+01:00 | 14:30:00+01:00 | See the Eiffel Tower and surrounding grounds | Model knowledge |

## V1

[Selected itinerary](generation/v1/itinerary.json)

### 2026-10-22

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 09:30:00+02:00 | 12:30:00+02:00 | Visit the Louvre Museum | Google discovery |
| 12:30:00+02:00 | 12:47:35+02:00 | WALK: 20261022-louvre to 20261022-sainte-chapelle | Application-bound transfer |
| 13:30:00+02:00 | 14:30:00+02:00 | Visit Sainte-Chapelle | Google discovery |
| 14:30:00+02:00 | 14:38:21+02:00 | WALK: 20261022-sainte-chapelle to 20261022-notre-dame | Application-bound transfer |
| 15:00:00+02:00 | 16:00:00+02:00 | Visit Notre-Dame Cathedral of Paris | Google discovery |

### 2026-10-23

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 09:30:00+02:00 | 11:30:00+02:00 | Visit the Eiffel Tower | Google discovery |
| 11:30:00+02:00 | 12:04:15+02:00 | WALK: 20261023-eiffel-tower to 20261023-arc-de-triomphe | Application-bound transfer |
| 12:15:00+02:00 | 13:30:00+02:00 | Visit the Arc de Triomphe | Google discovery |

### 2026-10-24

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:00:00+02:00 | 13:00:00+02:00 | Visit Musée d'Orsay | Google discovery |
| 13:00:00+02:00 | 13:35:36+02:00 | WALK: 20261024-orsay to 20261024-pantheon | Application-bound transfer |
| 14:00:00+02:00 | 15:30:00+02:00 | Visit the Panthéon | Google discovery |

### 2026-10-25

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:30:00+01:00 | 11:15:00+01:00 | Visit Place des Vosges | Google discovery |
| 11:15:00+01:00 | 11:27:11+01:00 | WALK: 20261025-place-des-vosges to 20261025-archives-museum | Application-bound transfer |
| 14:00:00+01:00 | 16:00:00+01:00 | Visit Musée des Archives Nationales | Google discovery |

## V2

[Selected itinerary](generation/v2/itinerary.json)

### 2026-10-22

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:00:00+02:00 | 13:00:00+02:00 | Louvre Museum | Google discovery |

### 2026-10-23

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 09:45:00+02:00 | 12:45:00+02:00 | Musée d'Orsay | Google discovery |

### 2026-10-24

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:00:00+02:00 | 12:00:00+02:00 | Eiffel Tower | Google discovery |
| 12:00:00+02:00 | 12:34:15+02:00 | WALK: paris-20261024-eiffel to paris-20261024-arc | Application-bound transfer |
| 13:00:00+02:00 | 14:30:00+02:00 | Arc de Triomphe | Google + RAG |

### 2026-10-25

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:00:00+01:00 | 11:15:00+01:00 | Notre-Dame Cathedral of Paris | Google discovery |
| 11:15:00+01:00 | 11:23:15+01:00 | WALK: paris-20261025-notredame to paris-20261025-sainte-chapelle | Application-bound transfer |
| 11:45:00+01:00 | 12:45:00+01:00 | Sainte-Chapelle | Google discovery |

## V3

[Selected itinerary](generation/v3/itinerary.json)

### 2026-10-22

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:00:00+02:00 | 13:00:00+02:00 | Visit Musée d'Orsay | Google tools; no RAG origin recorded |
| 13:00:00+02:00 | 13:36:56+02:00 | WALK: visit-orsay-20261022 to visit-eiffel-20261022 | Application-bound transfer |
| 15:00:00+02:00 | 16:30:00+02:00 | Visit the Eiffel Tower | Google tools; no RAG origin recorded |

### 2026-10-23

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 09:30:00+02:00 | 10:30:00+02:00 | Visit Notre-Dame Cathedral | Google tools; no RAG origin recorded |
| 10:30:00+02:00 | 10:38:15+02:00 | WALK: visit-notredame-20261023 to visit-saintechapelle-20261023 | Application-bound transfer |
| 11:00:00+02:00 | 12:00:00+02:00 | Visit Sainte-Chapelle | Google tools; no RAG origin recorded |

### 2026-10-24

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:00:00+02:00 | 13:00:00+02:00 | Visit the Louvre Museum | Google tools; no RAG origin recorded |
| 13:00:00+02:00 | 13:33:22+02:00 | WALK: visit-louvre-20261024 to visit-vosges-20261024 | Application-bound transfer |
| 15:00:00+02:00 | 16:00:00+02:00 | Explore Place des Vosges | Google tools; no RAG origin recorded |

### 2026-10-25

| Start | End | Scheduled activity / transfer | Recorded POI origin |
| --- | --- | --- | --- |
| 10:30:00+01:00 | 12:00:00+01:00 | Visit the Panthéon | Google + RAG |
| 12:00:00+01:00 | 12:28:53+01:00 | TRANSIT: visit-pantheon-20261025 to visit-arc-20261025 | Application-bound transfer |
| 14:00:00+01:00 | 15:30:00+01:00 | Visit the Arc de Triomphe | Google + RAG |
