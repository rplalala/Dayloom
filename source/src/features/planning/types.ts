export interface Money {
  amount: string;
  currency: string;
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
