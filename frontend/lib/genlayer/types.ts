/**
 * TypeScript mirrors of contracts/weather_resolve_cover.py's to_dict()
 * outputs. Field names and enum values are copied verbatim from the
 * contract's own constants (EVENT_STATUS_*, RETRIEVAL_*, COVER_*, etc.) --
 * nothing here is invented. If the contract's dict shape ever changes,
 * these types must be updated by re-reading the contract, not guessed.
 */

export type EventStatus = "PENDING" | "RESOLVING" | "RESOLVED" | "UNRESOLVED";

export type RetrievalStatus =
  | "PENDING"
  | "AVAILABLE"
  | "UNAVAILABLE"
  | "FETCH_FAILED"
  | "RENDER_FAILED"
  | "TIMEOUT"
  | "INVALID_RESPONSE"
  | "WRONG_LOCATION"
  | "WRONG_DATE"
  | "UNSUPPORTED_UNIT"
  | "CONFLICTING";

export type EvidenceStatus = "SUFFICIENT" | "INSUFFICIENT";

export type ResolutionReason =
  | "OK"
  | "INSUFFICIENT_SOURCES"
  | "MISSING_REQUIRED_CLASS"
  | "DISAGREEMENT"
  | "SOURCE_FAILURE_POLICY"
  | "NOT_YET_RESOLVED";

export type FetchMode = "get" | "render";

export type CoverOperator = "BELOW" | "ABOVE";

export type CoverStatus = "PENDING" | "TRIGGERED" | "NOT_TRIGGERED" | "UNRESOLVED";

export interface WeatherEvent {
  event_id: string;
  location: string;
  metric: string;
  observation_period: string;
  source_policy_id: string;
  created_at: string;
  status: EventStatus;
  consumer_count: number;
}

export interface SourceEvidence {
  source_id: string;
  url: string;
  fetch_mode: FetchMode;
  retrieval_status: RetrievalStatus;
  reported_value_raw: string;
  reported_unit: string;
  normalized_value_mm100: number;
  observation_timestamp: string;
  excerpt_fingerprint: string;
  location_match: string;
  location_detail: string;
}

export interface Observation {
  event_id: string;
  requested_location_id: string;
  status: "RESOLVED" | "UNRESOLVED";
  value_mm100: number;
  unit: string;
  source_count: number;
  evidence_status: EvidenceStatus;
  resolution_reason: ResolutionReason;
  resolved_at: string;
  evidence: SourceEvidence[];
}

export interface CoverPolicy {
  policy_id: string;
  owner: string;
  weather_event_id: string;
  location_id: string;
  metric: string;
  observation_date: string;
  operator: CoverOperator;
  threshold_mm100: number;
  simulated_payout: number;
  credited_amount: number;
  created_at: string;
  evaluated_at: string;
  status: CoverStatus;
}

export interface CoverPolicyDetail extends CoverPolicy {
  linked_observation: Observation | null;
}

export interface SourceSpec {
  source_id: string;
  url: string;
  fetch_mode: FetchMode;
  source_class: string;
  reported_unit: string;
}

export interface SourcePolicy {
  policy_id: string;
  min_source_count: number;
  required_source_classes: string[];
  disagreement_tolerance_mm100: number;
  unavailable_source_behavior: "SKIP" | "FAIL_POLICY";
  timeout_behavior: "SKIP" | "FAIL_POLICY";
  sources: SourceSpec[];
  version_locked: boolean;
}

export interface LocationProfile {
  location_id: string;
  canonical_name: string;
  country: string;
  aliases: string[];
  has_coordinates: boolean;
  lat_hundredths: number;
  lat_is_south: boolean;
  lon_hundredths: number;
  lon_is_west: boolean;
  radius_km: number;
}

/** Fixed-point helper: the contract stores mm values as integer
 * hundredths (mm100) everywhere, never floats, to stay deterministic
 * across validators. Display-only conversion, never sent back on-chain. */
export function mm100ToDisplay(mm100: number): string {
  return (mm100 / 100).toFixed(2);
}
