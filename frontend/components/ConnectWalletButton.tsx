"use client";

import { useWallet, isWrongChain } from "@/lib/wallet/WalletProvider";

export function ConnectWalletButton() {
  const {
    address,
    chainId,
    connecting,
    error,
    hasProvider,
    connect,
    disconnect,
    switchNetwork,
    switchingNetwork,
  } = useWallet();

  if (address && isWrongChain(chainId)) {
    return (
      <div className="flex flex-col items-end gap-1">
        <button
          className="wc-btn-primary text-xs sm:text-sm"
          style={{ background: "var(--wc-plum-ledger)", borderColor: "var(--wc-plum-ledger)" }}
          onClick={switchNetwork}
          disabled={switchingNetwork}
        >
          {switchingNetwork ? "Switching…" : "Wrong network — switch to StudioNet"}
        </button>
        {error ? (
          <span className="wc-mono text-xs" style={{ color: "var(--wc-plum-ledger)" }}>
            {error}
          </span>
        ) : null}
      </div>
    );
  }

  if (address) {
    return (
      <button
        className="wc-btn-secondary wc-mono flex items-center gap-2 text-xs transition-colors hover:border-[var(--wc-network-green)]"
        onClick={disconnect}
        title="Click to disconnect"
      >
        <span className="wc-dot wc-dot-confirmed" style={{ margin: 0 }} />
        {address.slice(0, 6)}…{address.slice(-4)}
      </button>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        className="wc-btn-primary text-xs transition-opacity hover:opacity-90 sm:text-sm"
        onClick={connect}
        disabled={connecting || !hasProvider}
      >
        {connecting ? "Connecting…" : hasProvider ? "Connect Wallet" : "No wallet found"}
      </button>
      {error ? (
        <span className="wc-mono max-w-[220px] text-right text-xs" style={{ color: "var(--wc-plum-ledger)" }}>
          {error}
        </span>
      ) : null}
    </div>
  );
}
