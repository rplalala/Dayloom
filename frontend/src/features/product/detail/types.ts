import type {
  Money,
  MinimumDailyCoverage,
  PreferenceCoverage,
} from "../../planning/types";

export type IllustrationKey = "hero" | "sydney" | "art" | "city" | "nature";
export type RequiredExperience = {
  requirement: string;
  source_quotes: string[];
  target: number;
  scheduled: number;
  frequency: "one_off" | "minimum" | "exact";
  status: "satisfied" | "unmet" | "unverified";
  reason: "supported_visit_coverage" | "matching_evidence_incomplete" | "required_visits_not_scheduled" | "no_confirmed_match";
};
export type DetailNearby = {
  illustration_key?: IllustrationKey | null;
  place_name: string;
  anchor_activity_id?: string | null;
  associated_day?: string | null;
  reason?: string | null;
  area?: string | null;
  uncertainty?: string | null;
  attribution?: string | null;
};
export type DetailActivity = {
  illustration_key?: IllustrationKey | null;
  activity_id: string;
  activity_kind?: 'main_poi' | 'generic_activity' | 'transport' | 'free_time' | 'unknown';
  atmosphere_theme?: 'meal' | 'rest' | 'explore' | 'walk' | 'general' | null;
  title: string;
  time_use: "scheduled" | "free_window";
  place_name?: string | null;
  location?: string | null;
  category?: string | null;
  start_time: string;
  end_time: string;
  estimated_cost?: Money | null;
  notes?: string | null;
  introduction?: string | null;
};
export type DetailDay = {
  date: string;
  activities: DetailActivity[];
  weather?: {
    summary?: string | null;
    temperature_min_c?: number | null;
    temperature_max_c?: number | null;
    precipitation_probability_percent?: number | null;
    max_wind_speed_kph?: number | null;
    attribution?: string | null;
    source_url?: string | null;
  } | null;
};
export type DetailTransfer = {
  from_activity_id: string;
  to_activity_id: string;
  mode?: string | null;
  departure_time?: string | null;
  arrival_time?: string | null;
  preceding_end_time?: string | null;
  following_start_time?: string | null;
  provider_duration_seconds?: number | null;
  distance_meters?: number | null;
  reserve_seconds?: number | null;
  estimate_kind: "provider" | "derived" | "unverified";
  status: "confirmed" | "unknown" | "source_claim";
  validation_state?: "PASS" | "CONFIRMED" | "UNKNOWN" | null;
  source_status?: string | null;
  unknowns: string[];
  attribution?: string | null;
};
export type PaceReview = {
  status: "complete" | "already_satisfied" | "partial" | "unavailable" | "not_attempted" | "source_overridden";
  days: { date: string; count: number | null; target_count: number; state: "satisfied" | "residual" | "unavailable" | "source_overridden" }[];
};

export type ProductDetail = {
  illustration_key?: IllustrationKey | null;
  display_tags?: string[];
  schema_version: "product_detail_1";
  id: string;
  title: string;
  destination: string;
  start_date?: string | null;
  end_date?: string | null;
  description?: string | null;
  provenance: "example" | "generated" | "imported";
  trust: "source_fixture" | "generated_projection" | "unverified_import";
  request: {
    known_fields?: string[] | null;
    destination?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    traveler_count?: number | null;
    budget?: Money | null;
    additional_preferences?: string | null;
  } | null;
  days: DetailDay[];
  transfers: DetailTransfer[];
  nearby: DetailNearby[];
  completion?: {
    required_experiences?: RequiredExperience[];
    pace_review?: PaceReview | null;
    source_claims?: string[];
    policy_completion: "complete" | "incomplete" | "unassessed";
    policy_reasons: string[];
    preference_coverage: PreferenceCoverage[];
    minimum_daily_coverage: MinimumDailyCoverage[];
  } | null;
};
export type ExampleCard = Pick<
  ProductDetail,
  "id" | "title" | "destination" | "start_date" | "end_date" | "description"
> & { created_at?: string | null; day_count: number; stop_count?: number; transfer_count?: number; illustration_key?: IllustrationKey | null };
