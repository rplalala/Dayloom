# Case-11: selected schedules and origins

Full saved final activities and transfers are shown below. Optional Nearby recommendations remain unscheduled. Exact structured values and source hashes are in the linked itineraries and material index.

## V0

[Exact itinerary](generation/v0/itinerary.json)

### 2026-10-22

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+02:00 – 2026-10-22T12:30:00+02:00 | Explore the Louvre's art collections | Musée du Louvre; Louvre area, Paris | main_poi/scheduled | Model generation; no RAG provenance | Allow time to focus on a selection of the collections rather than trying to see everything. |
| 2026-10-22T12:30:00+02:00 – 2026-10-22T12:45:00+02:00 | Walk to Palais-Royal | ;  | transport/scheduled | Model generation; no RAG provenance | Model estimate: roughly 15 minutes on foot; route and duration are not live-verified. |
| 2026-10-22T12:45:00+02:00 – 2026-10-22T14:00:00+02:00 | See the Palais-Royal and its historic arcades | Palais-Royal; Palais-Royal, Paris | main_poi/scheduled | Model generation; no RAG provenance | A relaxed look at the palace architecture and arcades. |

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+02:00 – 2026-10-23T11:00:00+02:00 | Visit Sainte-Chapelle | Sainte-Chapelle; Île de la Cité, Paris | main_poi/scheduled | Model generation; no RAG provenance | Focus on the Gothic architecture and stained glass. |
| 2026-10-23T11:00:00+02:00 – 2026-10-23T11:15:00+02:00 | Walk to the Conciergerie | ;  | transport/scheduled | Model generation; no RAG provenance | Model estimate: roughly 15 minutes on foot; route and duration are not live-verified. |
| 2026-10-23T11:15:00+02:00 – 2026-10-23T13:00:00+02:00 | Explore the Conciergerie | Conciergerie; Île de la Cité, Paris | main_poi/scheduled | Model generation; no RAG provenance | A historic palace with notable medieval architecture. |

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+02:00 – 2026-10-24T11:30:00+02:00 | Visit the Basilica of Sacré-Cœur | Basilica of Sacré-Cœur; Montmartre, Paris | main_poi/scheduled | Model generation; no RAG provenance | Take time to appreciate the architecture and the Montmartre setting. |
| 2026-10-24T11:30:00+02:00 – 2026-10-24T12:00:00+02:00 | Walk to the Musée de Montmartre | ;  | transport/scheduled | Model generation; no RAG provenance | Model estimate: roughly 30 minutes on foot; route and duration are not live-verified. |
| 2026-10-24T12:00:00+02:00 – 2026-10-24T14:00:00+02:00 | Visit the Musée de Montmartre | Musée de Montmartre; Montmartre, Paris | main_poi/scheduled | Model generation; no RAG provenance | An art-focused visit in the Montmartre neighborhood. |

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T10:00:00+01:00 – 2026-10-25T12:30:00+01:00 | Explore the Musée d'Orsay | Musée d'Orsay; Left Bank, Paris | main_poi/scheduled | Model generation; no RAG provenance | Allow time for a considered visit to selected galleries and the former station's architecture. |
| 2026-10-25T12:30:00+01:00 – 2026-10-25T13:00:00+01:00 | Travel to the Eiffel Tower area | ;  | transport/scheduled | Model generation; no RAG provenance | Model estimate: roughly 30 minutes by public transit; route and duration are not live-verified. |
| 2026-10-25T13:00:00+01:00 – 2026-10-25T14:30:00+01:00 | See the Eiffel Tower and surrounding grounds | Eiffel Tower; Champ de Mars, Paris | main_poi/scheduled | Model generation; no RAG provenance | A relaxed exterior visit focused on the landmark's architecture and its setting. |

[Complete transfer and Nearby fields](generation/v0/itinerary.json) retain all optional fields without counting references as visits.

## V1

[Exact itinerary](generation/v1/itinerary.json)

### 2026-10-22

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-22T09:30:00+02:00 – 2026-10-22T12:30:00+02:00 | Visit the Louvre Museum | Louvre Museum; 75001 Paris, France | main_poi/scheduled | Google |  |
| 2026-10-22T13:30:00+02:00 – 2026-10-22T14:30:00+02:00 | Visit Sainte-Chapelle | Sainte-Chapelle; 10 Bd du Palais, 75001 Paris, France | main_poi/scheduled | Google |  |
| 2026-10-22T15:00:00+02:00 – 2026-10-22T16:00:00+02:00 | Visit Notre-Dame Cathedral of Paris | Notre-Dame Cathedral of Paris; 6 Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris, France | main_poi/scheduled | Google |  |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| 20261022-louvre → 20261022-sainte-chapelle | WALK / APPLICATION_DEFAULT_WALK | 2026-10-22T12:30:00+02:00 → 2026-10-22T12:47:35+02:00 | 1055.0 s / 1308 m | 0.0 s / PASS /  |
| 20261022-sainte-chapelle → 20261022-notre-dame | WALK / APPLICATION_DEFAULT_WALK | 2026-10-22T14:30:00+02:00 → 2026-10-22T14:38:21+02:00 | 501.0 s / 593 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+02:00 – 2026-10-23T11:30:00+02:00 | Visit the Eiffel Tower | Eiffel Tower; Av. Gustave Eiffel, 75007 Paris, France | main_poi/scheduled | Google |  |
| 2026-10-23T12:15:00+02:00 – 2026-10-23T13:30:00+02:00 | Visit the Arc de Triomphe | Arc de Triomphe; Pl. Charles de Gaulle, 75008 Paris, France | main_poi/scheduled | Google |  |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| 20261023-eiffel-tower → 20261023-arc-de-triomphe | WALK / APPLICATION_DEFAULT_WALK | 2026-10-23T11:30:00+02:00 → 2026-10-23T12:04:15+02:00 | 2055.0 s / 2350 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+02:00 – 2026-10-24T13:00:00+02:00 | Visit Musée d'Orsay | Musée d'Orsay; Esplanade Valéry Giscard d'Estaing, 75007 Paris, France | main_poi/scheduled | Google |  |
| 2026-10-24T14:00:00+02:00 – 2026-10-24T15:30:00+02:00 | Visit the Panthéon | Panthéon; Pl. du Panthéon, 75005 Paris, France | main_poi/scheduled | Google |  |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| 20261024-orsay → 20261024-pantheon | WALK / APPLICATION_DEFAULT_WALK | 2026-10-24T13:00:00+02:00 → 2026-10-24T13:35:36+02:00 | 2136.0 s / 2483 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T10:30:00+01:00 – 2026-10-25T11:15:00+01:00 | Visit Place des Vosges | Place des Vosges; Pl. des Vosges, 75004 Paris, France | main_poi/scheduled | Google | Date-specific opening hours are unknown in the supplied evidence. |
| 2026-10-25T14:00:00+01:00 – 2026-10-25T16:00:00+01:00 | Visit Musée des Archives Nationales | Musée des Archives Nationales; 60 Rue des Francs Bourgeois, 75003 Paris, France | main_poi/scheduled | Google |  |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| 20261025-place-des-vosges → 20261025-archives-museum | WALK / APPLICATION_DEFAULT_WALK | 2026-10-25T11:15:00+01:00 → 2026-10-25T11:27:11+01:00 | 731.0 s / 877 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

[Complete transfer and Nearby fields](generation/v1/itinerary.json) retain all optional fields without counting references as visits.

## V2

[Exact itinerary](generation/v2/itinerary.json)

### 2026-10-22

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+02:00 – 2026-10-22T13:00:00+02:00 | Louvre Museum | Louvre Museum; 75001 Paris, France | main_poi/scheduled | Google |  |

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T09:45:00+02:00 – 2026-10-23T12:45:00+02:00 | Musée d'Orsay | Musée d'Orsay; Esplanade Valéry Giscard d'Estaing, 75007 Paris, France | main_poi/scheduled | Google | Morning visit; no activities or travel are scheduled during 14:00–16:00. |

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+02:00 – 2026-10-24T12:00:00+02:00 | Eiffel Tower | Eiffel Tower; Av. Gustave Eiffel, 75007 Paris, France | main_poi/scheduled | Google |  |
| 2026-10-24T13:00:00+02:00 – 2026-10-24T14:30:00+02:00 | Arc de Triomphe | Arc de Triomphe; Pl. Charles de Gaulle, 75008 Paris, France | main_poi/scheduled | Google + RAG |  |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| paris-20261024-eiffel → paris-20261024-arc | WALK / APPLICATION_DEFAULT_WALK | 2026-10-24T12:00:00+02:00 → 2026-10-24T12:34:15+02:00 | 2055.0 s / 2350 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T10:00:00+01:00 – 2026-10-25T11:15:00+01:00 | Notre-Dame Cathedral of Paris | Notre-Dame Cathedral of Paris; 6 Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris, France | main_poi/scheduled | Google |  |
| 2026-10-25T11:45:00+01:00 – 2026-10-25T12:45:00+01:00 | Sainte-Chapelle | Sainte-Chapelle; 10 Bd du Palais, 75001 Paris, France | main_poi/scheduled | Google |  |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| paris-20261025-notredame → paris-20261025-sainte-chapelle | WALK / APPLICATION_DEFAULT_WALK | 2026-10-25T11:15:00+01:00 → 2026-10-25T11:23:15+01:00 | 495.0 s / 593 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

[Complete transfer and Nearby fields](generation/v2/itinerary.json) retain all optional fields without counting references as visits.

## V3

[Exact itinerary](generation/v3/itinerary.json)

### 2026-10-22

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+02:00 – 2026-10-22T13:00:00+02:00 | Visit the Louvre Museum | Louvre Museum; 75001 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |
| 2026-10-22T14:00:00+02:00 – 2026-10-22T15:30:00+02:00 | Visit Sainte-Chapelle | Sainte-Chapelle; 10 Bd du Palais, 75001 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| paris-20261022-louvre → paris-20261022-sainte-chapelle | WALK / APPLICATION_DEFAULT_WALK | 2026-10-22T13:00:00+02:00 → 2026-10-22T13:17:35+02:00 | 1055.0 s / 1308 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+02:00 – 2026-10-23T11:00:00+02:00 | Visit Notre-Dame Cathedral of Paris | Notre-Dame Cathedral of Paris; 6 Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |
| 2026-10-23T11:10:00+02:00 – 2026-10-23T12:10:00+02:00 | Tours de la cathédrale Notre-Dame de Paris | Tours de la cathédrale Notre-Dame de Paris; Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris, France | main_poi/scheduled | RAG-introduced canonical ID |  |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| paris-20261023-notre-dame → repair_r1_new_1 | WALK / APPLICATION_DEFAULT_WALK | 2026-10-23T11:00:00+02:00 → 2026-10-23T11:01:44+02:00 | 104.0 s / 126 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+02:00 – 2026-10-24T12:30:00+02:00 | Visit the Eiffel Tower | Eiffel Tower; Av. Gustave Eiffel, 75007 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |
| 2026-10-24T14:00:00+02:00 – 2026-10-24T17:00:00+02:00 | Visit Musée d'Orsay | Musée d'Orsay; Esplanade Valéry Giscard d'Estaing, 75007 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| paris-20261024-eiffel-tower → paris-20261024-orsay | WALK / APPLICATION_DEFAULT_WALK | 2026-10-24T12:30:00+02:00 → 2026-10-24T13:07:06+02:00 | 2226.0 s / 2653 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T10:00:00+01:00 – 2026-10-25T11:30:00+01:00 | Visit the Panthéon | Panthéon; Pl. du Panthéon, 75005 Paris, France | main_poi/scheduled | Google + RAG | Hours shown for this date are a regular weekly baseline, not a date-specific guarantee. |
| 2026-10-25T13:00:00+01:00 – 2026-10-25T15:00:00+01:00 | Visit Musée de Cluny | Musée de Cluny; 28 Rue du Sommerard, 75005 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred | Hours shown for this date are a regular weekly baseline, not a date-specific guarantee. |

**Saved transfers:**

| Endpoints | Mode / source | Departure → arrival | Duration / distance | Reserve / status / uncertainty |
| --- | --- | --- | --- | --- |
| paris-20261025-pantheon → paris-20261025-cluny | WALK / APPLICATION_DEFAULT_WALK | 2026-10-25T11:30:00+01:00 → 2026-10-25T11:38:11+01:00 | 491.0 s / 636 m | 0.0 s / PASS /  |

Exact route evidence references, diagnostics and optional transfer fields remain in the linked complete itinerary.

[Complete transfer and Nearby fields](generation/v3/itinerary.json) retain all optional fields without counting references as visits.

## Same-run V3 changes

[Complete draft](analysis/repair/draft.json), [complete final primary](analysis/repair/final-primary.json), and [lossless Repair](analysis/repair/repair.json) retain every real change, including unchanged/skipped attempts.

Only fields that actually differ are listed. For added/removed activities, the absent side is marked absent; `null` is a saved null value, not an inferred value.

| Activity ID | Changed field | Before | After |
| --- | --- | --- | --- |
| repair_r1_new_1 | `activity_id` | absent | repair_r1_new_1 |
| repair_r1_new_1 | `activity_kind` | absent | main_poi |
| repair_r1_new_1 | `date` | absent | 2026-10-23 |
| repair_r1_new_1 | `end_time` | absent | 2026-10-23T12:10:00+02:00 |
| repair_r1_new_1 | `estimated_cost` | absent | `null` |
| repair_r1_new_1 | `location` | absent | Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris, France |
| repair_r1_new_1 | `notes` | absent | `null` |
| repair_r1_new_1 | `place_name` | absent | Tours de la cathédrale Notre-Dame de Paris |
| repair_r1_new_1 | `source_place_id` | absent | ChIJvcVRUwBx5kcRod72V2bB-EI |
| repair_r1_new_1 | `start_time` | absent | 2026-10-23T11:10:00+02:00 |
| repair_r1_new_1 | `time_use` | absent | scheduled |
| repair_r1_new_1 | `title` | absent | Tours de la cathédrale Notre-Dame de Paris |

Transfer, route-diagnostic and recommendation differences remain in the complete stage JSON, even when no activity field changes. Candidate source attribution is observational; no causal improvement is inferred from independent generations.
