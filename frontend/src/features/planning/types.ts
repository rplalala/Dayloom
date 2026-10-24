export interface Money {
  amount: string;
  currency: string;
}

export interface TravelRequirements {
  destination: string | null;
  start_date: string | null;
  end_date: string | null;
  traveler_count: number | null;
  budget: Money | null;
  required_activities: string[];
  excluded_activities: string[];
  preferences: string[];
  unresolved_fields: string[];
}

export interface Activity {
  time_use?: "scheduled" | "free_window" | null;
  introduction?: string | null;
  nearby?: Nearby[];
  activity_id: string;
  source_place_id?: string | null;
  title: string;
  place_name: string | null;
  location: string | null;
  start_time: string;
  end_time: string;
  estimated_cost: Money | null;
  notes: string | null;
}

export interface ItineraryDay {
  weather?: ProductWeather;
  date: string;
  activities: Activity[];
}

export interface ReferenceRecommendation {
  place_name: string;
  source_place_id: string | null;
  reason: string;
  associated_day: string | null;
  area: string | null;
  uncertainty: string | null;
  source_ref: string | null;
}

export interface Transfer {
  from_activity_id: string;
  to_activity_id: string;
  mode: "WALK" | "TRANSIT" | "DRIVE" | null;
  mode_source?: string;
  preceding_end_time?: string;
  following_start_time?: string;
  attribution?: string | null;
  estimate_kind?: "provider" | "derived" | "unverified";
  provider_duration_seconds: number | null;
  distance_meters: number | null;
  reserve_seconds: number;
  validation_state: "PASS" | "CONFIRMED" | "UNKNOWN";
  calculation_basis?: string;
  unknowns: string[];
}

export interface Itinerary {
  transfers?: Transfer[];
  output_version?: "itinerary_1" | "itinerary_2" | "itinerary_3";
  reference_recommendations?: ReferenceRecommendation[];
  destination: string;
  start_date: string;
  end_date: string;
  days: ItineraryDay[];
}

export interface ProductPlanningInput {
  destination: string;
  start_date: string;
  end_date: string;
  traveler_count: number;
  budget: Money;
  additional_preferences?: string;
}

export interface Nearby {
  place_name: string;
  reason: string;
  associated_day: string;
  anchor_activity_id: string;
  area: string | null;
  uncertainty: string | null;
  attribution: string | null;
}

export interface ProductWeather {
  status: "available" | "unavailable";
  forecast: {
    date: string;
    condition: string | null;
    min_temperature_c: number | null;
    max_temperature_c: number | null;
    precipitation_probability_percent: number | null;
    max_wind_speed_kph: number | null;
  } | null;
  attribution: string | null;
  source_url: string | null;
}

export interface MinimumDailyCoverage {
  date: string;
  countable_primary_activities: number;
  status: "satisfied" | "missing" | "exempt" | "unknown";
  reason: string;
}

export interface PreferenceCoverage {
  preference: string;
  target: 1 | 2;
  scheduled: number;
  remaining: number;
  status: "covered" | "gap" | "unassessed";
  target_origin: "ordinary_preference" | "current_trip_focus";
  basis: "model_semantic_judgment_not_operating_fact";
}

export interface CompletedPlanningResponse {
  preference_coverage?: PreferenceCoverage[];
  policy_completion?: "complete" | "incomplete" | "unassessed";
  policy_reasons?: string[];
  minimum_daily_coverage?: MinimumDailyCoverage[];
  status: "completed";
  requirements: TravelRequirements;
  itinerary: Itinerary;
}

export interface NeedsClarificationResponse {
  status: "needs_clarification";
  requirements: TravelRequirements;
  issues?: {
    code?: string;
    requirement_ids?: string[];
    input_disposition?: "VALID" | "CLARIFICATION_REQUIRED" | "REWRITE_REQUIRED";
    issues?: Array<{
      issue_type: string;
      source_refs: Array<{ quote: string; start: number; end: number }>;
      quote_status: "located" | "unavailable";
      related_field: string | null;
      current_value: string | number | null;
      reason: string;
      action: string;
    }>;
  };
}

export interface SafetyBlockedResponse {
  status: "safety_blocked";
  requirements: TravelRequirements;
  message: string;
  action: string;
}

export interface ProviderBlockedResponse {
  status: "provider_blocked";
  message: string;
  action: string;
}

export type ProductPlanningResponse =
  | CompletedPlanningResponse
  | NeedsClarificationResponse
  | SafetyBlockedResponse
  | ProviderBlockedResponse;
