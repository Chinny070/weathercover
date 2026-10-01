import { chains, createClient } from "genlayer-js";

/**
 * The deployed WeatherResolveCover contract address. Configurable via
 * NEXT_PUBLIC_CONTRACT_ADDRESS (see .env.example / docs/DEPLOYMENT.md) so
 * this frontend can be pointed at any StudioNet deployment without a code
 * change. Falls back to the canonical deployment address (see
 * docs/CANONICAL_DEPLOYMENT.md) purely so local dev has real on-chain
 * data by default.
 *
 * This constant is never written to by this app -- deployment remains a
 * manual, wallet-controlled step performed outside the frontend. See
 * docs/DEPLOYMENT.md and docs/CANONICAL_DEPLOYMENT.md.
 */
export const CONTRACT_ADDRESS = (process.env.NEXT_PUBLIC_CONTRACT_ADDRESS ??
  "0xFd7160411e5812bD873089368b1BF687e644a959") as `0x${string}`;

export const STUDIONET_CHAIN_ID = 61999;
export const STUDIONET_CHAIN_ID_HEX = "0xf22f";
export const STUDIONET_RPC = "https://studio.genlayer.com/api";

/**
 * Read-only client -- no account required, works before a wallet is
 * connected. Every browsing view in WeatherCover (landing, dashboard,
 * Evidence Explorer, policy result) uses this client, so a visitor gains
 * full value with no wallet at all. Verified pattern (createClient +
 * chains.studionet), reused from a working StudioNet frontend already in
 * this workspace (protocolcourt/frontend/lib/genlayer/config.ts).
 */
export const readClient = createClient({ chain: chains.studionet });

/** MetaMask "Add Network" params for StudioNet, used only when a wallet is
 * connected for a write action (creating or evaluating a policy). */
export const STUDIONET_WALLET_PARAMS = {
  chainId: STUDIONET_CHAIN_ID_HEX,
  chainName: "GenLayer Studio Network",
  nativeCurrency: { name: "GEN Token", symbol: "GEN", decimals: 18 },
  rpcUrls: [STUDIONET_RPC],
  blockExplorerUrls: ["https://explorer-studio.genlayer.com"],
};
