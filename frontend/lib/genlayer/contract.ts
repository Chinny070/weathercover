import type { GenLayerChain, GenLayerClient, TransactionHash } from "genlayer-js/types";
import { CalldataAddress, TransactionHashVariant, TransactionStatus } from "genlayer-js/types";
import { getAddress, hexToBytes } from "viem";
import { CONTRACT_ADDRESS, readClient } from "./config";
import type {
  CoverPolicy,
  CoverPolicyDetail,
  LocationProfile,
  Observation,
  SourcePolicy,
  WeatherEvent,
} from "./types";

export type AnyClient = GenLayerClient<GenLayerChain>;

/**
 * This contract's view methods return plain GenVM dicts/lists directly
 * (verified against contracts/weather_resolve_cover.py's own to_dict()
 * methods and the `genlayer call` output captured during the Stage 7
 * StudioNet verification run) -- decode as-is, no JSON.parse. Read/write
 * split and the `readContract`/`writeContract`/`TransactionHashVariant`
 * API itself are reused verbatim from a working StudioNet frontend
 * already in this workspace (protocolcourt/frontend/lib/genlayer/contract.ts).
 */
async function read<T>(
  functionName: string,
  args: unknown[] = [],
  client: AnyClient = readClient,
): Promise<T> {
  const raw = await client.readContract({
    address: CONTRACT_ADDRESS,
    functionName,
    args: args as never[],
    transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
  });
  return raw as T;
}

/** GenLayer's calldata format has a dedicated address wire type -- a plain
 * hex string sent as an argument gets encoded as generic text instead, and
 * the contract's `Address`-typed parameter rejects it. Required for every
 * `Address`-typed parameter this contract accepts from a caller
 * (`cover_list_policy_ids_by_owner`, `cover_get_simulated_balance`),
 * verified against the same requirement in protocolcourt/frontend/lib/
 * genlayer/contract.ts, a working StudioNet frontend already in this
 * workspace. */
function toCalldataAddress(hex: string): CalldataAddress {
  return new CalldataAddress(hexToBytes(getAddress(hex)));
}

async function write(
  client: AnyClient,
  functionName: string,
  args: unknown[],
): Promise<TransactionHash> {
  const hash = await client.writeContract({
    address: CONTRACT_ADDRESS,
    functionName,
    args: args as never[],
    value: 0n,
  });
  return hash as TransactionHash;
}

// ---- reads: Weather Event Registry -----------------------------------------

export const getWeatherEvent = (eventId: string) =>
  read<WeatherEvent>("event_get_weather_event", [eventId]);

export const eventExists = (eventId: string) => read<boolean>("event_exists", [eventId]);

export const computeEventId = (
  location: string,
  metric: string,
  observationPeriod: string,
  sourcePolicyId: string,
) => read<string>("event_compute_id", [location, metric, observationPeriod, sourcePolicyId]);

// ---- reads: Source Policy Registry ------------------------------------------

export const getSourcePolicy = (policyId: string) =>
  read<SourcePolicy>("policy_get_source_policy", [policyId]);

export const sourcePolicyExists = (policyId: string) => read<boolean>("policy_exists", [policyId]);

// ---- reads: Location Resolution Profile Registry ----------------------------

export const getLocationProfile = (locationId: string) =>
  read<LocationProfile>("location_get_profile", [locationId]);

export const locationExists = (locationId: string) => read<boolean>("location_exists", [locationId]);

// ---- reads: Observation Registry (WeatherResolve) ---------------------------

export const getObservation = (eventId: string) => read<Observation>("observation_get_observation", [eventId]);

export const getResolutionStatus = (eventId: string) =>
  read<string>("observation_get_resolution_status", [eventId]);

// ---- reads: WeatherCover -----------------------------------------------------

export const getCoverPolicy = (policyId: string) => read<CoverPolicy>("cover_get_policy", [policyId]);

export const getCoverPolicyDetail = (policyId: string) =>
  read<CoverPolicyDetail>("cover_get_policy_detail", [policyId]);

export const listPolicyIdsByOwner = (owner: string) =>
  read<string[]>("cover_list_policy_ids_by_owner", [toCalldataAddress(owner)]);

export const getSimulatedBalance = (owner: string) =>
  read<bigint>("cover_get_simulated_balance", [toCalldataAddress(owner)]);

export const coverPolicyExists = (policyId: string) => read<boolean>("cover_policy_exists", [policyId]);

// ---- writes: WeatherResolve (event creation / resolution) -------------------
//
// Not owner-gated: any account can request an event or trigger resolution
// on an already-configured location/source-policy pair, exactly like the
// StudioNet verification runs performed with the genlayer CLI. Registering
// a new source policy (which evidence sources are trusted) remains an
// owner-only infrastructure-setup action, not exposed here. Registering a
// new LOCATION is open to any caller, by product decision -- see
// registerLocation below.

export const registerLocation = (
  client: AnyClient,
  locationId: string,
  canonicalName: string,
  country: string,
  hasCoordinates: boolean,
  latHundredths: number,
  latIsSouth: boolean,
  lonHundredths: number,
  lonIsWest: boolean,
  radiusKm: number,
) =>
  write(client, "location_register_profile", [
    locationId,
    canonicalName,
    country,
    hasCoordinates,
    latHundredths,
    latIsSouth,
    lonHundredths,
    lonIsWest,
    radiusKm,
  ]);

export const createWeatherEvent = (
  client: AnyClient,
  location: string,
  metric: string,
  observationPeriod: string,
  sourcePolicyId: string,
) => write(client, "event_create_weather_event", [location, metric, observationPeriod, sourcePolicyId]);

export const resolveWeatherEvent = (client: AnyClient, eventId: string) =>
  write(client, "resolve_weather_event", [eventId]);

// ---- writes: WeatherCover -----------------------------------------------------

export const createCoverPolicy = (
  client: AnyClient,
  weatherEventId: string,
  operator: "BELOW" | "ABOVE",
  thresholdMm100: number,
  simulatedPayout: number,
) => write(client, "cover_create_policy", [weatherEventId, operator, thresholdMm100, simulatedPayout]);

export const evaluateCoverPolicy = (client: AnyClient, policyId: string) =>
  write(client, "cover_evaluate_policy", [policyId]);

// ---- transaction lifecycle (GenLayer transaction layer, not a contract method) --

/**
 * Never trust a write call's return value (a transaction hash) as proof
 * anything succeeded -- GenLayer's consensus can settle on something other
 * than ACCEPTED even when the leader's own execution looked fine. Always
 * wait for a real status, then re-read contract state. Same discipline
 * every prior GenLayer project in this workspace has required.
 */
export async function waitForStatus(
  client: AnyClient,
  hash: TransactionHash,
  status: TransactionStatus = TransactionStatus.ACCEPTED,
  opts: { retries?: number; interval?: number } = {},
) {
  return client.waitForTransactionReceipt({
    hash,
    status,
    retries: opts.retries ?? 150,
    interval: opts.interval ?? 2000,
  });
}

export async function getTransaction(hash: TransactionHash, client: AnyClient = readClient) {
  return client.getTransaction({ hash });
}

export { TransactionStatus };
