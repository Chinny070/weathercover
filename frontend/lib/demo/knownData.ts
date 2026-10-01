/**
 * The contract has no "list all events" method (by design -- see
 * docs/PRODUCT_ARCHITECTURE.md: WeatherResolve is a registry keyed by a
 * deterministic event_id, not an indexed feed). A real product would
 * index events off-chain or require the caller to already know an
 * event_id (e.g. from creating it, or from a link). For this demo
 * environment, the event/policy IDs listed here were created directly
 * on the CANONICAL contract (see docs/CANONICAL_DEPLOYMENT.md) so the
 * landing page and dashboard have real on-chain data to point at
 * immediately.
 *
 * This file is demo convenience only -- every ID below is independently
 * verifiable by reading the deployed contract directly (see
 * docs/DEPLOYMENT.md for the exact `genlayer call` commands used to
 * produce these values). If the contract is redeployed again, these IDs
 * (and the source policy IDs) will need updating to match -- see
 * docs/MANUAL_DEPLOYMENT.md §6 and docs/CANONICAL_DEPLOYMENT.md.
 */

export const KNOWN_LOCATION_ID = "LAGOS_NG";
export const KNOWN_METRIC = "RAIN_24H";

/** A real, RESOLVED observation: 3 model-specific Open-Meteo historical
 * archive queries, median 12.30mm, verified on canonical StudioNet. */
export const RESOLVED_DEMO_EVENT_ID = "3d603813dbd7ae98";
export const RESOLVED_DEMO_SOURCE_POLICY_ID = "AUDIT_V1";
export const RESOLVED_DEMO_OBSERVATION_DATE = "2026-08-30";

/** A real, UNRESOLVED observation: a source deliberately queried at the
 * wrong coordinates, correctly rejected as WRONG_LOCATION -> INSUFFICIENT_
 * SOURCES. Demonstrates UNRESOLVED is a first-class, honest outcome. */
export const UNRESOLVED_DEMO_EVENT_ID = "f96bbf7bf2a964ae";
export const UNRESOLVED_DEMO_SOURCE_POLICY_ID = "AUDIT_UNRES_V1";
export const UNRESOLVED_DEMO_OBSERVATION_DATE = "2026-08-25";

/** Cover policies created and evaluated against the events above on the
 * canonical contract: TRIGGERED (cover-1), NOT_TRIGGERED (cover-2), and
 * UNRESOLVED (cover-3). */
export const DEMO_COVER_POLICY_IDS = ["cover-1", "cover-2", "cover-3"] as const;

/**
 * Source policies available for creating a NEW demo weather event from
 * the Create Policy page. Registering a source policy's sources is an
 * owner-only infrastructure action (see contracts/weather_resolve_cover.py
 * policy_add_source) and is intentionally not exposed here -- an end user
 * picks from source policies an operator has already configured, exactly
 * like choosing a weather station network in a real parametric product.
 */
export const AVAILABLE_SOURCE_POLICIES = [
  {
    id: RESOLVED_DEMO_SOURCE_POLICY_ID,
    label: "Open-Meteo historical (3 sources, StudioNet-verified)",
  },
] as const;
