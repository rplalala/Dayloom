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

- `{"from_activity_id":"20261022-louvre","to_activity_id":"20261022-sainte-chapelle","origin_place_id":"ChIJD3uTd9hx5kcR1IQvGfr8dbk","destination_place_id":"ChIJR3122B9u5kcRaCck3PlB9DM","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-22T12:30:00+02:00","arrival_time":"2026-10-22T12:47:35+02:00","provider_duration_seconds":1055.0,"distance_meters":1308,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`
- `{"from_activity_id":"20261022-sainte-chapelle","to_activity_id":"20261022-notre-dame","origin_place_id":"ChIJR3122B9u5kcRaCck3PlB9DM","destination_place_id":"ChIJATr1n-Fx5kcRjQb6q6cdQDY","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-22T14:30:00+02:00","arrival_time":"2026-10-22T14:38:21+02:00","provider_duration_seconds":501.0,"distance_meters":593,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+02:00 – 2026-10-23T11:30:00+02:00 | Visit the Eiffel Tower | Eiffel Tower; Av. Gustave Eiffel, 75007 Paris, France | main_poi/scheduled | Google |  |
| 2026-10-23T12:15:00+02:00 – 2026-10-23T13:30:00+02:00 | Visit the Arc de Triomphe | Arc de Triomphe; Pl. Charles de Gaulle, 75008 Paris, France | main_poi/scheduled | Google |  |

**Saved transfers:**

- `{"from_activity_id":"20261023-eiffel-tower","to_activity_id":"20261023-arc-de-triomphe","origin_place_id":"ChIJLU7jZClu5kcR4PcOOO6p3I0","destination_place_id":"ChIJjx37cOxv5kcRPWQuEW5ntdk","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-23T11:30:00+02:00","arrival_time":"2026-10-23T12:04:15+02:00","provider_duration_seconds":2055.0,"distance_meters":2350,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+02:00 – 2026-10-24T13:00:00+02:00 | Visit Musée d'Orsay | Musée d'Orsay; Esplanade Valéry Giscard d'Estaing, 75007 Paris, France | main_poi/scheduled | Google |  |
| 2026-10-24T14:00:00+02:00 – 2026-10-24T15:30:00+02:00 | Visit the Panthéon | Panthéon; Pl. du Panthéon, 75005 Paris, France | main_poi/scheduled | Google |  |

**Saved transfers:**

- `{"from_activity_id":"20261024-orsay","to_activity_id":"20261024-pantheon","origin_place_id":"ChIJG5Qwtitu5kcR2CNEsYy9cdA","destination_place_id":"ChIJc8mX0udx5kcRWKcjTwDr5QA","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-24T13:00:00+02:00","arrival_time":"2026-10-24T13:35:36+02:00","provider_duration_seconds":2136.0,"distance_meters":2483,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T10:30:00+01:00 – 2026-10-25T11:15:00+01:00 | Visit Place des Vosges | Place des Vosges; Pl. des Vosges, 75004 Paris, France | main_poi/scheduled | Google | Date-specific opening hours are unknown in the supplied evidence. |
| 2026-10-25T14:00:00+01:00 – 2026-10-25T16:00:00+01:00 | Visit Musée des Archives Nationales | Musée des Archives Nationales; 60 Rue des Francs Bourgeois, 75003 Paris, France | main_poi/scheduled | Google |  |

**Saved transfers:**

- `{"from_activity_id":"20261025-place-des-vosges","to_activity_id":"20261025-archives-museum","origin_place_id":"ChIJUeiI4P9x5kcRqEwHl6V32GQ","destination_place_id":"ChIJDwZjvgNu5kcR92V2clFCGMk","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-25T11:15:00+01:00","arrival_time":"2026-10-25T11:27:11+01:00","provider_duration_seconds":731.0,"distance_meters":877,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

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

- `{"from_activity_id":"paris-20261024-eiffel","to_activity_id":"paris-20261024-arc","origin_place_id":"ChIJLU7jZClu5kcR4PcOOO6p3I0","destination_place_id":"ChIJjx37cOxv5kcRPWQuEW5ntdk","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-24T12:00:00+02:00","arrival_time":"2026-10-24T12:34:15+02:00","provider_duration_seconds":2055.0,"distance_meters":2350,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T10:00:00+01:00 – 2026-10-25T11:15:00+01:00 | Notre-Dame Cathedral of Paris | Notre-Dame Cathedral of Paris; 6 Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris, France | main_poi/scheduled | Google |  |
| 2026-10-25T11:45:00+01:00 – 2026-10-25T12:45:00+01:00 | Sainte-Chapelle | Sainte-Chapelle; 10 Bd du Palais, 75001 Paris, France | main_poi/scheduled | Google |  |

**Saved transfers:**

- `{"from_activity_id":"paris-20261025-notredame","to_activity_id":"paris-20261025-sainte-chapelle","origin_place_id":"ChIJATr1n-Fx5kcRjQb6q6cdQDY","destination_place_id":"ChIJR3122B9u5kcRaCck3PlB9DM","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-25T11:15:00+01:00","arrival_time":"2026-10-25T11:23:15+01:00","provider_duration_seconds":495.0,"distance_meters":593,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

[Complete transfer and Nearby fields](generation/v2/itinerary.json) retain all optional fields without counting references as visits.

## V3

[Exact itinerary](generation/v3/itinerary.json)

### 2026-10-22

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-22T10:00:00+02:00 – 2026-10-22T13:00:00+02:00 | Visit the Louvre Museum | Louvre Museum; 75001 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |
| 2026-10-22T14:00:00+02:00 – 2026-10-22T15:30:00+02:00 | Visit Sainte-Chapelle | Sainte-Chapelle; 10 Bd du Palais, 75001 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |

**Saved transfers:**

- `{"from_activity_id":"paris-20261022-louvre","to_activity_id":"paris-20261022-sainte-chapelle","origin_place_id":"ChIJD3uTd9hx5kcR1IQvGfr8dbk","destination_place_id":"ChIJR3122B9u5kcRaCck3PlB9DM","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-22T13:00:00+02:00","arrival_time":"2026-10-22T13:17:35+02:00","provider_duration_seconds":1055.0,"distance_meters":1308,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-23

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23T09:30:00+02:00 – 2026-10-23T11:00:00+02:00 | Visit Notre-Dame Cathedral of Paris | Notre-Dame Cathedral of Paris; 6 Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |
| 2026-10-23T11:10:00+02:00 – 2026-10-23T12:10:00+02:00 | Tours de la cathédrale Notre-Dame de Paris | Tours de la cathédrale Notre-Dame de Paris; Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris, France | main_poi/scheduled | RAG-introduced canonical ID |  |

**Saved transfers:**

- `{"from_activity_id":"paris-20261023-notre-dame","to_activity_id":"repair_r1_new_1","origin_place_id":"ChIJATr1n-Fx5kcRjQb6q6cdQDY","destination_place_id":"ChIJvcVRUwBx5kcRod72V2bB-EI","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-23T11:00:00+02:00","arrival_time":"2026-10-23T11:01:44+02:00","provider_duration_seconds":104.0,"distance_meters":126,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-24

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-24T10:00:00+02:00 – 2026-10-24T12:30:00+02:00 | Visit the Eiffel Tower | Eiffel Tower; Av. Gustave Eiffel, 75007 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |
| 2026-10-24T14:00:00+02:00 – 2026-10-24T17:00:00+02:00 | Visit Musée d'Orsay | Musée d'Orsay; Esplanade Valéry Giscard d'Estaing, 75007 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred |  |

**Saved transfers:**

- `{"from_activity_id":"paris-20261024-eiffel-tower","to_activity_id":"paris-20261024-orsay","origin_place_id":"ChIJLU7jZClu5kcR4PcOOO6p3I0","destination_place_id":"ChIJG5Qwtitu5kcR2CNEsYy9cdA","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-24T12:30:00+02:00","arrival_time":"2026-10-24T13:07:06+02:00","provider_duration_seconds":2226.0,"distance_meters":2653,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

### 2026-10-25

| Time | Activity | Place / address | Role | Captured origin | Saved notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-25T10:00:00+01:00 – 2026-10-25T11:30:00+01:00 | Visit the Panthéon | Panthéon; Pl. du Panthéon, 75005 Paris, France | main_poi/scheduled | Google + RAG | Hours shown for this date are a regular weekly baseline, not a date-specific guarantee. |
| 2026-10-25T13:00:00+01:00 – 2026-10-25T15:00:00+01:00 | Visit Musée de Cluny | Musée de Cluny; 28 Rue du Sommerard, 75005 Paris, France | main_poi/scheduled | No captured RAG association; other origin not inferred | Hours shown for this date are a regular weekly baseline, not a date-specific guarantee. |

**Saved transfers:**

- `{"from_activity_id":"paris-20261025-pantheon","to_activity_id":"paris-20261025-cluny","origin_place_id":"ChIJc8mX0udx5kcRWKcjTwDr5QA","destination_place_id":"ChIJLxPh9d1x5kcRf7M1U0pu1gU","mode":"WALK","mode_source":"APPLICATION_DEFAULT_WALK","departure_time":"2026-10-25T11:30:00+01:00","arrival_time":"2026-10-25T11:38:11+01:00","provider_duration_seconds":491.0,"distance_meters":636,"reserve_seconds":0.0,"routing_preference":null,"evidence_refs":["google_routes:compute_route_matrix"],"calculation_basis":"walk_provider_estimate","validation_state":"PASS","unknowns":[]}`

[Complete transfer and Nearby fields](generation/v3/itinerary.json) retain all optional fields without counting references as visits.

## Same-run V3 changes

[Complete draft](analysis/repair/draft.json), [complete final primary](analysis/repair/final-primary.json), and [lossless Repair](analysis/repair/repair.json) retain every real change, including unchanged/skipped attempts.

| Activity ID | Change | Saved before | Saved after |
| --- | --- | --- | --- |
| repair_r1_new_1 | added | null | ["2026-10-23", {"activity_kind": "main_poi", "time_use": "scheduled", "activity_id": "repair_r1_new_1", "title": "Tours de la cathédrale Notre-Dame de Paris", "place_name": "Tours de la cathédrale Notre-Dame de Paris", "source_place_id": "ChIJvcVRUwBx5kcRod72V2bB-EI", "location": "Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris, France", "start_time": "2026-10-23T11:10:00+02:00", "end_time": "2026-10-23T12:10:00+02:00", "estimated_cost": null, "notes": null}] |

Transfer, route-diagnostic and recommendation differences remain in the complete stage JSON, even when no activity row changes. Candidate source attribution is observational; no causal improvement is inferred from independent generations.
