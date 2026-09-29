"use client";

import Link from "next/link";
import { useWallet } from "@/lib/wallet/WalletProvider";
import { useContractRead } from "@/hooks/useContractRead";
import { listPolicyIdsByOwner, getCoverPolicy, getObservation, getSimulatedBalance } from "@/lib/genlayer/contract";
import { PolicyCard } from "@/components/PolicyCard";
import type { CoverPolicy } from "@/lib/genlayer/types";
import { useState, useEffect } from "react";

export default function DashboardPage() {
  const { address, connect, hasProvider } = useWallet();

  const policyIdsState = useContractRead(
    () => (address ? listPolicyIdsByOwner(address) : Promise.resolve<string[]>([])),
    [address],
  );

  const balanceState = useContractRead(
    () => (address ? getSimulatedBalance(address) : Promise.resolve<bigint>(0n)),
    [address],
  );

  const [policies, setPolicies] = useState<
    { policy: CoverPolicy; observedValueMm100: number | null }[] | null
  >(null);

  useEffect(() => {
    if (policyIdsState.status !== "ready") return;
    let cancelled = false;
    Promise.all(
      policyIdsState.data.map(async (id) => {
        const policy = await getCoverPolicy(id);
        let observedValueMm100: number | null = null;
        try {
          const observation = await getObservation(policy.weather_event_id);
          if (observation.status === "RESOLVED") observedValueMm100 = observation.value_mm100;
        } catch {
          // No observation yet -- leave as null, PolicyCard shows "not yet resolved".
        }
        return { policy, observedValueMm100 };
      }),
    ).then((results) => {
      if (!cancelled) setPolicies(results);
    });
    return () => {
      cancelled = true;
    };
  }, [policyIdsState.status, policyIdsState.status === "ready" ? policyIdsState.data : null]);

  if (!address) {
    return (
      <div className="wc-card mx-auto max-w-md text-center">
        <p className="wc-display text-lg">Connect your wallet</p>
        <p className="mt-2 text-sm" style={{ color: "var(--wc-graphite)" }}>
          Your dashboard shows the policies your connected wallet owns on StudioNet.
        </p>
        <button className="wc-btn-primary mt-4" onClick={connect} disabled={!hasProvider}>
          {hasProvider ? "Connect Wallet" : "No wallet found"}
        </button>
      </div>
    );
  }

  const active = policies?.filter((p) => p.policy.status === "PENDING") ?? [];
  const completed = policies?.filter((p) => p.policy.status !== "PENDING") ?? [];

  return (
    <div className="flex flex-col gap-10">
      <div className="flex items-center justify-between">
        <h1 className="wc-display text-2xl">Your Policies</h1>
        <div className="wc-card !py-3 !px-4 text-right">
          <p className="text-xs" style={{ color: "var(--wc-steel)" }}>
            Simulated balance
          </p>
          <p className="wc-mono text-lg" style={{ color: "var(--wc-network-green)" }}>
            {balanceState.status === "ready" ? balanceState.data.toString() : "…"} units
          </p>
        </div>
      </div>

      {policies === null ? (
        <p className="text-sm" style={{ color: "var(--wc-steel)" }}>
          Loading policies…
        </p>
      ) : policies.length === 0 ? (
        <div className="wc-card text-center">
          <p style={{ color: "var(--wc-graphite)" }}>You have no policies yet.</p>
          <Link href="/create-policy" className="wc-btn-primary mt-4 inline-block">
            Create your first policy
          </Link>
        </div>
      ) : (
        <>
          <section>
            <h2 className="mb-3 text-sm font-medium" style={{ color: "var(--wc-steel)" }}>
              ACTIVE ({active.length})
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {active.map((p, i) => (
                <PolicyCard
                  key={p.policy.policy_id}
                  policy={p.policy}
                  observedValueMm100={p.observedValueMm100}
                  revealDelayMs={i * 60}
                />
              ))}
              {active.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--wc-steel)" }}>
                  No policies awaiting evaluation.
                </p>
              ) : null}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-sm font-medium" style={{ color: "var(--wc-steel)" }}>
              COMPLETED ({completed.length})
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {completed.map((p, i) => (
                <PolicyCard
                  key={p.policy.policy_id}
                  policy={p.policy}
                  observedValueMm100={p.observedValueMm100}
                  revealDelayMs={i * 60}
                />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
